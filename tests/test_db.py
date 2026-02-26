"""
Tests for src/db.py — SQLite persistence layer.

Uses a temporary in-memory (or tempfile) DB for isolation.
No mocking of sqlite3 — we test the real SQL.
"""

from __future__ import annotations

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
