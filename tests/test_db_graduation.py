"""
Tests for DB.graduation_stats() method.

Behavior cases:
- Empty DB returns dict with all None/0 values
- 50 settled paper trades returns correct stats
- Win/loss streak correctly computes consecutive_losses
- Only counts is_paper=1 trades
- brier_score computed from win_prob when available
- first_trade_ts = earliest paper trade timestamp
- days_running = (now - first_trade_ts) / 86400
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path

import pytest

from src.db import DB


@pytest.fixture
def fresh_db(tmp_path):
    """Provide a freshly initialized in-memory-like DB for each test."""
    db_path = tmp_path / "test_graduation.db"
    db = DB(db_path)
    db.init()
    yield db
    db.close()


def _insert_trade(db: DB, strategy: str, side: str, result: str | None,
                  win_prob: float | None = None, pnl_cents: int = 0,
                  is_paper: bool = True, ts: float | None = None):
    """Helper to insert a trade and optionally settle it."""
    if ts is None:
        ts = time.time()
    cursor = db._conn.execute(
        """INSERT INTO trades
           (timestamp, ticker, side, action, price_cents, count, cost_usd,
            strategy, win_prob, is_paper, result, pnl_cents, settled_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            ts, f"KXBTC-{strategy[:3].upper()}", side, "buy",
            50, 1, 0.50,
            strategy, win_prob, int(is_paper),
            result, pnl_cents if result is not None else None,
            ts if result is not None else None,
        ),
    )
    db._conn.commit()
    return cursor.lastrowid


# ── Test: empty DB ─────────────────────────────────────────────────────────

class TestGraduationStatsEmptyDB:
    def test_returns_dict_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert isinstance(result, dict)

    def test_settled_count_zero_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["settled_count"] == 0

    def test_win_rate_none_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["win_rate"] is None

    def test_brier_score_none_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["brier_score"] is None

    def test_consecutive_losses_zero_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["consecutive_losses"] == 0

    def test_first_trade_ts_none_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["first_trade_ts"] is None

    def test_days_running_zero_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["days_running"] == 0.0

    def test_total_pnl_usd_zero_on_empty_db(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["total_pnl_usd"] == 0.0


# ── Test: 50 settled paper trades ─────────────────────────────────────────

class TestGraduationStatsWith50Trades:
    def test_settled_count_is_50(self, fresh_db):
        # Insert 40 wins and 10 losses
        for i in range(40):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", win_prob=0.65)
        for i in range(10):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "no", win_prob=0.65)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["settled_count"] == 50

    def test_win_rate_is_float(self, fresh_db):
        for i in range(30):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes")
        for i in range(20):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "no")

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert isinstance(result["win_rate"], float)
        assert abs(result["win_rate"] - 0.60) < 0.01

    def test_days_running_non_negative(self, fresh_db):
        for i in range(50):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes")

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["days_running"] >= 0

    def test_consecutive_losses_is_int(self, fresh_db):
        for i in range(50):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes")

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert isinstance(result["consecutive_losses"], int)


# ── Test: consecutive_losses calculation ──────────────────────────────────

class TestConsecutiveLosses:
    def test_w_w_l_l_l_gives_3(self, fresh_db):
        """Pattern W, W, L, L, L → consecutive_losses = 3."""
        base_ts = time.time() - 1000

        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=base_ts + 0)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=base_ts + 1)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  ts=base_ts + 2)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  ts=base_ts + 3)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  ts=base_ts + 4)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["consecutive_losses"] == 3

    def test_all_wins_gives_zero_consecutive_losses(self, fresh_db):
        for i in range(5):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes")
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["consecutive_losses"] == 0

    def test_win_at_end_resets_streak(self, fresh_db):
        """W, L, L, W → consecutive_losses = 0."""
        base_ts = time.time() - 1000
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=base_ts + 0)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  ts=base_ts + 1)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  ts=base_ts + 2)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=base_ts + 3)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["consecutive_losses"] == 0

    def test_no_side_bet_wins_when_result_is_no(self, fresh_db):
        """NO-side bet: side='no', result='no' → WIN."""
        _insert_trade(fresh_db, "btc_lag_v1", "no", "no")  # WIN
        _insert_trade(fresh_db, "btc_lag_v1", "no", "yes")  # LOSS

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["consecutive_losses"] == 1
        assert abs(result["win_rate"] - 0.5) < 0.01


# ── Test: only paper trades counted ──────────────────────────────────────

class TestPaperOnlyFilter:
    def test_live_trades_excluded(self, fresh_db):
        """is_paper=False trades must NOT count."""
        # 10 live wins
        for i in range(10):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", is_paper=False)
        # 3 paper losses
        for i in range(3):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "no", is_paper=True)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["settled_count"] == 3
        assert result["win_rate"] == 0.0

    def test_unsettled_paper_trades_excluded_from_settled_count(self, fresh_db):
        """Unsettled (result IS NULL) paper trades must not count."""
        # Insert 5 settled wins
        for i in range(5):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes")
        # Insert 3 open/unsettled trades
        for i in range(3):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", None)  # no result

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["settled_count"] == 5

    def test_different_strategy_excluded(self, fresh_db):
        """Another strategy's trades must not appear in btc_lag_v1 stats."""
        for i in range(20):
            _insert_trade(fresh_db, "eth_lag_v1", "yes", "yes")
        for i in range(2):
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "no")

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["settled_count"] == 2


# ── Test: brier_score ─────────────────────────────────────────────────────

class TestBrierScore:
    def test_brier_none_when_no_win_prob_recorded(self, fresh_db):
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", win_prob=None)
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["brier_score"] is None

    def test_perfect_prediction_gives_zero_brier(self, fresh_db):
        """win_prob=1.0 and result=win → Brier = 0."""
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", win_prob=1.0)
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["brier_score"] is not None
        assert abs(result["brier_score"] - 0.0) < 1e-9

    def test_worst_prediction_gives_one_brier(self, fresh_db):
        """win_prob=1.0 but result=loss → Brier = (1-0)^2 = 1."""
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no", win_prob=1.0)
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["brier_score"] is not None
        assert abs(result["brier_score"] - 1.0) < 1e-9

    def test_brier_is_mean_over_trades_with_win_prob(self, fresh_db):
        """Two trades: (0.0, win)=1.0 brier and (1.0, win)=0.0 brier → mean = 0.5."""
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", win_prob=0.0)  # brier=1.0
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", win_prob=1.0)  # brier=0.0
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["brier_score"] is not None
        assert abs(result["brier_score"] - 0.5) < 1e-9


# ── Test: first_trade_ts and days_running ─────────────────────────────────

class TestFirstTradeAndDays:
    def test_first_trade_ts_is_earliest_paper_trade(self, fresh_db):
        early_ts = time.time() - 86400 * 7  # 7 days ago
        late_ts = time.time() - 86400 * 2   # 2 days ago

        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=late_ts)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=early_ts)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["first_trade_ts"] is not None
        assert abs(result["first_trade_ts"] - early_ts) < 1.0

    def test_days_running_reflects_first_trade(self, fresh_db):
        """If first trade was 7 days ago, days_running should be ~7."""
        ts_7days_ago = time.time() - 86400 * 7
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=ts_7days_ago)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert 6.9 < result["days_running"] < 7.1

    def test_first_trade_includes_unsettled_trades(self, fresh_db):
        """first_trade_ts from all paper trades, not just settled ones."""
        early_unsettled_ts = time.time() - 86400 * 10
        settled_ts = time.time() - 86400 * 3

        _insert_trade(fresh_db, "btc_lag_v1", "yes", None, ts=early_unsettled_ts)  # unsettled
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", ts=settled_ts)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert abs(result["first_trade_ts"] - early_unsettled_ts) < 1.0


# ── Test: total_pnl_usd ───────────────────────────────────────────────────

class TestTotalPnlUsd:
    def test_total_pnl_from_pnl_cents(self, fresh_db):
        """pnl_cents=150 → total_pnl_usd = 1.50."""
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", pnl_cents=150)
        _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  pnl_cents=-50)

        result = fresh_db.graduation_stats("btc_lag_v1")
        assert abs(result["total_pnl_usd"] - 1.00) < 0.001

    def test_total_pnl_zero_on_empty(self, fresh_db):
        result = fresh_db.graduation_stats("btc_lag_v1")
        assert result["total_pnl_usd"] == 0.0
