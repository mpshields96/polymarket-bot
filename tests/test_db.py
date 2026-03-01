"""
Tests for src/db.py — SQLite persistence layer.

Uses a temporary in-memory (or tempfile) DB for isolation.
No mocking of sqlite3 — we test the real SQL.
"""

from __future__ import annotations

import csv
import tempfile
import time
from pathlib import Path

import pytest

from src.db import DB


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    """Fresh DB in a temp directory per test."""
    d = DB(tmp_path / "test.db")
    d.init()
    yield d
    d.close()


def _save_trade(db, *, ticker="KXBTC15M-TEST", side="yes", price_cents=44,
                count=10, cost_usd=4.40, is_paper=True):
    return db.save_trade(
        ticker=ticker,
        side=side,
        action="buy",
        price_cents=price_cents,
        count=count,
        cost_usd=cost_usd,
        strategy="btc_lag",
        edge_pct=0.12,
        win_prob=0.62,
        is_paper=is_paper,
    )


# ── Bankroll ──────────────────────────────────────────────────────


class TestBankroll:
    def test_latest_bankroll_none_if_empty(self, db):
        assert db.latest_bankroll() is None

    def test_save_and_retrieve_bankroll(self, db):
        db.save_bankroll(50.0, source="api")
        assert db.latest_bankroll() == 50.0

    def test_latest_bankroll_returns_most_recent(self, db):
        db.save_bankroll(50.0, source="api")
        db.save_bankroll(47.50, source="paper_simulation")
        assert db.latest_bankroll() == 47.50

    def test_bankroll_history_length(self, db):
        for i in range(5):
            db.save_bankroll(50.0 - i, source="api")
        history = db.get_bankroll_history()
        assert len(history) == 5


# ── Trades — save + retrieve ──────────────────────────────────────


class TestSaveTrade:
    def test_save_returns_integer_id(self, db):
        trade_id = _save_trade(db)
        assert isinstance(trade_id, int)
        assert trade_id >= 1

    def test_saved_trade_appears_in_get_trades(self, db):
        _save_trade(db, ticker="KXBTC15M-001", side="yes")
        trades = db.get_trades()
        assert len(trades) == 1
        assert trades[0]["ticker"] == "KXBTC15M-001"
        assert trades[0]["side"] == "yes"

    def test_trade_is_unsettled_on_creation(self, db):
        _save_trade(db)
        trades = db.get_open_trades()
        assert len(trades) == 1
        assert trades[0]["result"] is None

    def test_paper_flag_stored(self, db):
        _save_trade(db, is_paper=True)
        _save_trade(db, is_paper=False)
        paper = db.get_trades(is_paper=True)
        live = db.get_trades(is_paper=False)
        assert len(paper) == 1
        assert len(live) == 1

    def test_get_trades_limit(self, db):
        for _ in range(10):
            _save_trade(db)
        assert len(db.get_trades(limit=5)) == 5


# ── Settlement ────────────────────────────────────────────────────


class TestSettleTrade:
    def test_settle_sets_result(self, db):
        trade_id = _save_trade(db, side="yes")
        db.settle_trade(trade_id, result="yes", pnl_cents=560)
        trades = db.get_trades()
        assert trades[0]["result"] == "yes"
        assert trades[0]["pnl_cents"] == 560

    def test_settled_trade_not_in_open_trades(self, db):
        trade_id = _save_trade(db)
        db.settle_trade(trade_id, result="yes", pnl_cents=100)
        open_trades = db.get_open_trades()
        assert len(open_trades) == 0

    def test_loss_settlement_negative_pnl(self, db):
        trade_id = _save_trade(db, side="yes", price_cents=44, count=10)
        db.settle_trade(trade_id, result="no", pnl_cents=-440)
        trades = db.get_trades()
        assert trades[0]["pnl_cents"] == -440


# ── Win rate ──────────────────────────────────────────────────────


class TestWinRate:
    def test_win_rate_none_if_no_settled_trades(self, db):
        _save_trade(db)
        assert db.win_rate() is None

    def test_win_rate_100_pct_all_wins(self, db):
        # Bet YES, market resolves YES → win
        for _ in range(3):
            t = _save_trade(db, side="yes")
            db.settle_trade(t, result="yes", pnl_cents=560)
        assert db.win_rate() == pytest.approx(1.0)

    def test_win_rate_0_pct_all_losses(self, db):
        # Bet YES, market resolves NO → loss
        for _ in range(3):
            t = _save_trade(db, side="yes")
            db.settle_trade(t, result="no", pnl_cents=-440)
        assert db.win_rate() == pytest.approx(0.0)

    def test_win_rate_50_pct_mixed(self, db):
        t1 = _save_trade(db, side="yes")
        db.settle_trade(t1, result="yes", pnl_cents=560)  # win
        t2 = _save_trade(db, side="yes")
        db.settle_trade(t2, result="no", pnl_cents=-440)  # loss
        assert db.win_rate() == pytest.approx(0.5)

    def test_win_rate_correct_for_no_side_wins(self, db):
        # Critical regression test for the bug we fixed:
        # Betting NO and winning (result=="no"==side) must count as a WIN.
        t = _save_trade(db, side="no", price_cents=56)
        db.settle_trade(t, result="no", pnl_cents=440)  # won
        assert db.win_rate() == pytest.approx(1.0)

    def test_win_rate_correct_for_no_side_loss(self, db):
        # Betting NO and losing (result=="yes"!=side) must count as a LOSS.
        t = _save_trade(db, side="no", price_cents=56)
        db.settle_trade(t, result="yes", pnl_cents=-560)  # lost
        assert db.win_rate() == pytest.approx(0.0)

    def test_win_rate_mixed_yes_and_no_sides(self, db):
        # YES bet, wins
        t1 = _save_trade(db, side="yes")
        db.settle_trade(t1, result="yes", pnl_cents=560)
        # NO bet, wins
        t2 = _save_trade(db, side="no")
        db.settle_trade(t2, result="no", pnl_cents=440)
        # YES bet, loses
        t3 = _save_trade(db, side="yes")
        db.settle_trade(t3, result="no", pnl_cents=-440)
        # 2/3 wins
        assert db.win_rate() == pytest.approx(2 / 3)

    def test_win_rate_respects_paper_filter(self, db):
        # Paper win
        t1 = _save_trade(db, side="yes", is_paper=True)
        db.settle_trade(t1, result="yes", pnl_cents=560)
        # Live loss
        t2 = _save_trade(db, side="yes", is_paper=False)
        db.settle_trade(t2, result="no", pnl_cents=-440)

        assert db.win_rate(is_paper=True) == pytest.approx(1.0)
        assert db.win_rate(is_paper=False) == pytest.approx(0.0)
        assert db.win_rate() == pytest.approx(0.5)


# ── Total P&L ─────────────────────────────────────────────────────


class TestTotalPnL:
    def test_total_pnl_zero_if_no_settled(self, db):
        _save_trade(db)
        assert db.total_realized_pnl_usd() == pytest.approx(0.0)

    def test_total_pnl_sums_correctly(self, db):
        t1 = _save_trade(db)
        db.settle_trade(t1, result="yes", pnl_cents=560)  # +$5.60
        t2 = _save_trade(db)
        db.settle_trade(t2, result="no", pnl_cents=-440)  # -$4.40
        # net = +1.20
        assert db.total_realized_pnl_usd() == pytest.approx(1.20)

    def test_total_pnl_negative_when_losing(self, db):
        t = _save_trade(db)
        db.settle_trade(t, result="no", pnl_cents=-440)
        assert db.total_realized_pnl_usd() == pytest.approx(-4.40)


# ── Kill switch events ────────────────────────────────────────────


class TestKillSwitchEvents:
    def test_save_and_retrieve_event(self, db):
        db.save_kill_switch_event("hard_stop", "Test reason", bankroll_at_trigger=40.0)
        events = db.get_kill_switch_events()
        assert len(events) == 1
        assert events[0]["trigger_type"] == "hard_stop"
        assert events[0]["reason"] == "Test reason"
        assert events[0]["bankroll_at_trigger"] == pytest.approx(40.0)

    def test_events_ordered_newest_first(self, db):
        db.save_kill_switch_event("soft_stop", "First")
        time.sleep(0.01)
        db.save_kill_switch_event("hard_stop", "Second")
        events = db.get_kill_switch_events()
        assert events[0]["trigger_type"] == "hard_stop"


# ── Dashboard DB path resolution ──────────────────────────────────

class TestDashboardDbPath:
    """Verify _resolve_db_path reads config.yaml and falls back gracefully.

    streamlit is not installed in the test environment, so we mock it before
    importing src.dashboard — this avoids an ImportError while still exercising
    the pure-Python _resolve_db_path function.
    """

    @pytest.fixture(autouse=True)
    def mock_streamlit(self, monkeypatch):
        """Inject a mock streamlit so src.dashboard can be imported without it installed."""
        import sys
        from unittest.mock import MagicMock
        mock_st = MagicMock()
        mocks = {
            "streamlit": mock_st,
            "streamlit_autorefresh": MagicMock(),
        }
        with pytest.MonkeyPatch.context() as mp:
            for name, mock in mocks.items():
                if name not in sys.modules:
                    mp.setitem(sys.modules, name, mock)
            yield
            # Remove cached dashboard module so next test gets a fresh import
            sys.modules.pop("src.dashboard", None)

    def test_resolve_returns_absolute_path(self):
        from src.dashboard import _resolve_db_path
        path = _resolve_db_path()
        assert path.is_absolute()

    def test_resolve_points_to_config_value(self):
        """Should return data/polybot.db (as configured in config.yaml)."""
        from src.dashboard import _resolve_db_path
        path = _resolve_db_path()
        assert path.name == "polybot.db"
        assert "data" in path.parts

    def test_resolve_fallback_on_bad_config(self, tmp_path):
        """Malformed config.yaml should fall back gracefully, not raise."""
        import sys
        bad_config = tmp_path / "config.yaml"
        bad_config.write_text("{ invalid yaml: [")
        sys.modules.pop("src.dashboard", None)
        import src.dashboard as dash
        import unittest.mock as mock
        with mock.patch.object(dash, "PROJECT_ROOT", tmp_path):
            path = dash._resolve_db_path()
        assert isinstance(path, Path)

    def test_resolve_fallback_on_missing_config(self, tmp_path):
        """Missing config.yaml should fall back gracefully, not raise."""
        import sys
        sys.modules.pop("src.dashboard", None)
        import src.dashboard as dash
        import unittest.mock as mock
        with mock.patch.object(dash, "PROJECT_ROOT", tmp_path):
            path = dash._resolve_db_path()
        assert isinstance(path, Path)


# ── count_trades_today ────────────────────────────────────────────


class TestCountTradesToday:
    """count_trades_today() counts bets placed in the current UTC day by strategy."""

    def _save_with_ts(self, db, timestamp: float, strategy: str = "btc_lag",
                      is_paper: bool = True):
        """Insert a trade row with a custom timestamp (bypasses save_trade's time.time())."""
        db._conn.execute(
            """INSERT INTO trades
               (timestamp, ticker, side, action, price_cents, count, cost_usd,
                strategy, edge_pct, win_prob, is_paper)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (timestamp, "TEST-001", "yes", "buy", 44, 10, 4.40,
             strategy, 0.12, 0.62, int(is_paper)),
        )
        db._conn.commit()

    def test_zero_when_empty(self, db):
        assert db.count_trades_today("btc_lag") == 0

    def test_counts_trade_placed_now(self, db):
        self._save_with_ts(db, time.time(), strategy="btc_lag")
        assert db.count_trades_today("btc_lag") == 1

    def test_multiple_trades_same_strategy(self, db):
        for _ in range(3):
            self._save_with_ts(db, time.time(), strategy="btc_lag")
        assert db.count_trades_today("btc_lag") == 3

    def test_filters_by_strategy(self, db):
        self._save_with_ts(db, time.time(), strategy="btc_lag")
        self._save_with_ts(db, time.time(), strategy="btc_drift")
        assert db.count_trades_today("btc_lag") == 1
        assert db.count_trades_today("btc_drift") == 1
        assert db.count_trades_today("weather_forecast_v1") == 0

    def test_filters_by_paper_flag(self, db):
        self._save_with_ts(db, time.time(), strategy="btc_lag", is_paper=True)
        self._save_with_ts(db, time.time(), strategy="btc_lag", is_paper=False)
        assert db.count_trades_today("btc_lag", is_paper=True) == 1
        assert db.count_trades_today("btc_lag", is_paper=False) == 1
        assert db.count_trades_today("btc_lag") == 2  # no filter → both

    def test_old_trade_not_counted(self, db):
        """A trade from 2 days ago should not appear in today's count."""
        two_days_ago = time.time() - 2 * 86400
        self._save_with_ts(db, two_days_ago, strategy="btc_lag")
        assert db.count_trades_today("btc_lag") == 0

    def test_settled_trade_still_counts(self, db):
        """Settlement doesn't remove a trade from today's count."""
        trade_id = _save_trade(db)
        db.settle_trade(trade_id, result="yes", pnl_cents=560)
        assert db.count_trades_today("btc_lag") == 1


# ── has_open_position ─────────────────────────────────────────────


class TestHasOpenPosition:
    """has_open_position() returns True when an unsettled trade exists on ticker."""

    def test_false_when_empty(self, db):
        assert db.has_open_position("KXBTC15M-TEST") is False

    def test_true_after_saving_trade(self, db):
        _save_trade(db, ticker="KXBTC15M-TEST")
        assert db.has_open_position("KXBTC15M-TEST") is True

    def test_false_after_settlement(self, db):
        trade_id = _save_trade(db, ticker="KXBTC15M-TEST")
        db.settle_trade(trade_id, result="yes", pnl_cents=560)
        assert db.has_open_position("KXBTC15M-TEST") is False

    def test_different_ticker_no_conflict(self, db):
        _save_trade(db, ticker="KXBTC15M-001")
        assert db.has_open_position("KXBTC15M-002") is False

    def test_paper_filter_true(self, db):
        _save_trade(db, ticker="KXBTC15M-TEST", is_paper=True)
        assert db.has_open_position("KXBTC15M-TEST", is_paper=True) is True
        assert db.has_open_position("KXBTC15M-TEST", is_paper=False) is False

    def test_paper_filter_false(self, db):
        _save_trade(db, ticker="KXBTC15M-TEST", is_paper=False)
        assert db.has_open_position("KXBTC15M-TEST", is_paper=False) is True
        assert db.has_open_position("KXBTC15M-TEST", is_paper=True) is False

    def test_no_filter_matches_both(self, db):
        _save_trade(db, ticker="KXBTC15M-TEST", is_paper=True)
        assert db.has_open_position("KXBTC15M-TEST") is True

    def test_multiple_open_positions_same_ticker(self, db):
        """Two unsettled bets on same ticker → still returns True (any open)."""
        _save_trade(db, ticker="KXBTC15M-TEST")
        _save_trade(db, ticker="KXBTC15M-TEST")
        assert db.has_open_position("KXBTC15M-TEST") is True


# ── CSV Export ────────────────────────────────────────────────────


class TestExportTradesCsv:
    def test_creates_file(self, db, tmp_path):
        _save_trade(db)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        assert out.exists()

    def test_header_row(self, db, tmp_path):
        _save_trade(db)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        with open(out) as f:
            reader = csv.DictReader(f)
            assert "id" in reader.fieldnames
            assert "placed_at" in reader.fieldnames
            assert "pnl_usd" in reader.fieldnames
            assert "is_paper" in reader.fieldnames
            assert "won" in reader.fieldnames

    def test_row_count_matches_trades(self, db, tmp_path):
        _save_trade(db, ticker="KXBTC15M-A")
        _save_trade(db, ticker="KXBTC15M-B")
        _save_trade(db, ticker="KXBTC15M-C", is_paper=False)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 3

    def test_is_paper_label(self, db, tmp_path):
        _save_trade(db, is_paper=True)
        _save_trade(db, ticker="KXBTC15M-LIVE", is_paper=False)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        labels = {r["is_paper"] for r in rows}
        assert "paper" in labels
        assert "live" in labels

    def test_settled_trade_pnl_and_won(self, db, tmp_path):
        tid = _save_trade(db, side="no", is_paper=False)
        db.settle_trade(tid, result="no", pnl_cents=350)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        row = rows[0]
        assert row["result"] == "no"
        assert float(row["pnl_usd"]) == 3.5
        assert row["won"] == "True"

    def test_open_trade_empty_pnl(self, db, tmp_path):
        _save_trade(db)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["pnl_usd"] == ""
        assert rows[0]["won"] == ""

    def test_overwrites_on_second_call(self, db, tmp_path):
        _save_trade(db)
        out = tmp_path / "out.csv"
        db.export_trades_csv(out)
        _save_trade(db, ticker="KXBTC15M-B")
        db.export_trades_csv(out)
        with open(out) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_creates_parent_dir(self, db, tmp_path):
        out = tmp_path / "subdir" / "nested" / "out.csv"
        _save_trade(db)
        db.export_trades_csv(out)
        assert out.exists()


# ── daily_live_loss_usd ─────────────────────────────────────────────


class TestDailyLiveLossUsd:
    """daily_live_loss_usd() returns today's settled live losses as a positive USD amount."""

    def _live_trade(self, db, ticker="KXBTC15M-T", side="yes", price_cents=50):
        return db.save_trade(
            ticker=ticker, side=side, action="buy", price_cents=price_cents,
            count=100, cost_usd=5.0, is_paper=False,
            strategy="btc_lag_v1", edge_pct=0.05, win_prob=0.6,
        )

    def test_returns_zero_if_no_settled_trades(self, db):
        assert db.daily_live_loss_usd() == pytest.approx(0.0)

    def test_returns_zero_if_only_paper_losses(self, db):
        t = db.save_trade(
            ticker="KXBTC15M-T", side="yes", action="buy", price_cents=50,
            count=100, cost_usd=5.0, is_paper=True,
            strategy="btc_drift_v1", edge_pct=0.05, win_prob=0.6,
        )
        db.settle_trade(t, result="no", pnl_cents=-500)
        assert db.daily_live_loss_usd() == pytest.approx(0.0)

    def test_counts_live_losses(self, db):
        t = self._live_trade(db)
        db.settle_trade(t, result="no", pnl_cents=-500)  # $5 loss
        assert db.daily_live_loss_usd() == pytest.approx(5.0)

    def test_excludes_live_wins(self, db):
        t = self._live_trade(db)
        db.settle_trade(t, result="yes", pnl_cents=560)  # win
        assert db.daily_live_loss_usd() == pytest.approx(0.0)

    def test_sums_multiple_live_losses(self, db):
        t1 = self._live_trade(db, ticker="KXBTC15M-A")
        t2 = self._live_trade(db, ticker="KXBTC15M-B")
        db.settle_trade(t1, result="no", pnl_cents=-500)  # $5 loss
        db.settle_trade(t2, result="no", pnl_cents=-480)  # $4.80 loss
        assert db.daily_live_loss_usd() == pytest.approx(9.80, abs=0.01)


# ── all_time_live_loss_usd ───────────────────────────────────────────


class TestAllTimeLiveLossUsd:
    """all_time_live_loss_usd() returns total live losses ever, regardless of date."""

    def _live_trade(self, db, ticker="KXBTC15M-T", side="yes", price_cents=50):
        return db.save_trade(
            ticker=ticker, side=side, action="buy", price_cents=price_cents,
            count=100, cost_usd=5.0, is_paper=False,
            strategy="btc_lag_v1", edge_pct=0.05, win_prob=0.6,
        )

    def test_returns_zero_if_no_settled_trades(self, db):
        assert db.all_time_live_loss_usd() == pytest.approx(0.0)

    def test_returns_zero_if_only_paper_losses(self, db):
        t = db.save_trade(
            ticker="KXBTC15M-T", side="yes", action="buy", price_cents=50,
            count=100, cost_usd=5.0, is_paper=True,
            strategy="btc_lag_v1", edge_pct=0.05, win_prob=0.6,
        )
        db.settle_trade(t, result="no", pnl_cents=-500)
        assert db.all_time_live_loss_usd() == pytest.approx(0.0)

    def test_counts_live_losses(self, db):
        t = self._live_trade(db)
        db.settle_trade(t, result="no", pnl_cents=-500)  # $5 loss
        assert db.all_time_live_loss_usd() == pytest.approx(5.0)

    def test_excludes_live_wins(self, db):
        t = self._live_trade(db)
        db.settle_trade(t, result="yes", pnl_cents=560)  # win
        assert db.all_time_live_loss_usd() == pytest.approx(0.0)

    def test_excludes_unsettled_live_trades(self, db):
        """Unsettled trades (open positions) must not be counted."""
        self._live_trade(db)  # no settle_trade call
        assert db.all_time_live_loss_usd() == pytest.approx(0.0)

    def test_sums_losses_across_multiple_trades(self, db):
        t1 = self._live_trade(db, ticker="KXBTC15M-A")
        t2 = self._live_trade(db, ticker="KXBTC15M-B")
        t3 = self._live_trade(db, ticker="KXBTC15M-C")
        db.settle_trade(t1, result="no", pnl_cents=-500)   # $5 loss
        db.settle_trade(t2, result="no", pnl_cents=-480)   # $4.80 loss
        db.settle_trade(t3, result="yes", pnl_cents=560)   # $5.60 win — excluded
        assert db.all_time_live_loss_usd() == pytest.approx(9.80, abs=0.01)

    def test_does_not_filter_by_date(self, db):
        """Unlike daily_live_loss_usd, all_time must include old losses."""
        import time
        t = self._live_trade(db, ticker="KXBTC15M-OLD")
        # Settle first, then backdate settled_at to 30 days ago
        db.settle_trade(t, result="no", pnl_cents=-500)  # $5 loss
        db._conn.execute(
            "UPDATE trades SET settled_at = ? WHERE id = ?",
            (time.time() - 86400 * 30, t),
        )
        db._conn.commit()
        # daily_live_loss_usd filters by today — should be 0 for old trade
        assert db.daily_live_loss_usd() == pytest.approx(0.0)
        # all_time_live_loss_usd has no date filter — must still return $5
        assert db.all_time_live_loss_usd() == pytest.approx(5.0)
