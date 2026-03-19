"""
Tests for scripts/sniper_monthly_wr.py — Sniper Monthly WR Tracker.

Motivation: CCA (Session 111) flagged that FLB may be weakening (Whelan VoxEU March 2026).
We need rolling WR tracking to detect sustained degradation before it becomes
expensive. Threshold: flag if rolling 30-day WR drops below 93% sustained over 100+ bets.

Coverage:
  compute_monthly_wr:  correct grouping, WR computation, P&L aggregation
  compute_rolling_wr:  correct 30-day window, empty window, partial month
  flag_threshold:      fires at <93% with n>=30, silent above, silent with n<30
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.sniper_monthly_wr import (
    compute_monthly_wr,
    compute_rolling_wr,
    MonthlyWRResult,
    RollingWRResult,
    WR_FLAG_THRESHOLD,
    WR_FLAG_MIN_BETS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_db(trades: list[dict]) -> sqlite3.Connection:
    """Create in-memory DB with trades table."""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            strategy TEXT,
            is_paper INTEGER,
            side TEXT,
            result TEXT,
            pnl_cents INTEGER,
            settled_at REAL
        )
    """)
    for t in trades:
        conn.execute(
            "INSERT INTO trades (strategy, is_paper, side, result, pnl_cents, settled_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (t["strategy"], t["is_paper"], t["side"], t["result"], t["pnl_cents"], t["settled_at"])
        )
    conn.commit()
    return conn


def _ts(year: int, month: int, day: int = 1) -> float:
    """Return unix timestamp for a date."""
    import calendar
    return float(calendar.timegm((year, month, day, 12, 0, 0, 0, 0, 0)))


def _sniper_win(ts: float, pnl_cents: int = 30) -> dict:
    return {"strategy": "expiry_sniper_v1", "is_paper": 0,
            "side": "yes", "result": "yes", "pnl_cents": pnl_cents, "settled_at": ts}


def _sniper_loss(ts: float, pnl_cents: int = -1900) -> dict:
    return {"strategy": "expiry_sniper_v1", "is_paper": 0,
            "side": "yes", "result": "no", "pnl_cents": pnl_cents, "settled_at": ts}


# ── Tests: compute_monthly_wr ─────────────────────────────────────────────────

class TestComputeMonthlyWR:
    def test_single_month_all_wins(self):
        trades = [_sniper_win(_ts(2026, 3, d)) for d in range(1, 11)]
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        assert len(results) == 1
        r = results[0]
        assert r.month == "2026-03"
        assert r.n_bets == 10
        assert r.wins == 10
        assert abs(r.win_rate - 1.0) < 0.001

    def test_single_month_mixed(self):
        trades = (
            [_sniper_win(_ts(2026, 3, d)) for d in range(1, 20)]  # 19 wins
            + [_sniper_loss(_ts(2026, 3, 20))]  # 1 loss
        )
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        assert len(results) == 1
        r = results[0]
        assert r.n_bets == 20
        assert r.wins == 19
        assert abs(r.win_rate - 0.95) < 0.001

    def test_two_months_separate(self):
        trades = (
            [_sniper_win(_ts(2026, 2, d)) for d in range(1, 6)]   # 5 wins Feb
            + [_sniper_win(_ts(2026, 3, d)) for d in range(1, 11)]  # 10 wins Mar
        )
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        months = [r.month for r in results]
        assert "2026-02" in months and "2026-03" in months
        feb = next(r for r in results if r.month == "2026-02")
        mar = next(r for r in results if r.month == "2026-03")
        assert feb.n_bets == 5
        assert mar.n_bets == 10

    def test_paper_trades_excluded(self):
        trades = [
            {"strategy": "expiry_sniper_v1", "is_paper": 1,
             "side": "yes", "result": "yes", "pnl_cents": 30, "settled_at": _ts(2026, 3, 1)},
        ]
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        assert len(results) == 0

    def test_other_strategies_excluded(self):
        trades = [
            {"strategy": "btc_drift_v1", "is_paper": 0,
             "side": "yes", "result": "yes", "pnl_cents": 30, "settled_at": _ts(2026, 3, 1)},
        ]
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        assert len(results) == 0

    def test_pnl_aggregation(self):
        trades = [
            _sniper_win(_ts(2026, 3, 1), pnl_cents=100),
            _sniper_win(_ts(2026, 3, 2), pnl_cents=200),
            _sniper_loss(_ts(2026, 3, 3), pnl_cents=-1900),
        ]
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        r = results[0]
        assert abs(r.pnl_usd - (-16.0)) < 0.01  # (100+200-1900)/100

    def test_empty_db(self):
        conn = _make_db([])
        results = compute_monthly_wr(conn)
        assert results == []

    def test_results_sorted_by_month(self):
        trades = (
            [_sniper_win(_ts(2026, 3, d)) for d in range(1, 4)]
            + [_sniper_win(_ts(2026, 1, d)) for d in range(1, 4)]
            + [_sniper_win(_ts(2026, 2, d)) for d in range(1, 4)]
        )
        conn = _make_db(trades)
        results = compute_monthly_wr(conn)
        months = [r.month for r in results]
        assert months == sorted(months)


# ── Tests: compute_rolling_wr ─────────────────────────────────────────────────

class TestComputeRollingWR:
    def test_basic_rolling_window(self):
        now = _ts(2026, 3, 19)
        # 10 wins in last 30 days, 5 losses before window
        old_loss = _ts(2026, 2, 1)   # > 30 days ago
        recent_win = _ts(2026, 3, 10)  # within 30 days
        trades = (
            [_sniper_loss(old_loss)] * 5
            + [_sniper_win(recent_win)] * 10
        )
        conn = _make_db(trades)
        result = compute_rolling_wr(conn, as_of_ts=now)
        assert result.n_bets == 10
        assert result.wins == 10
        assert abs(result.win_rate - 1.0) < 0.001

    def test_empty_window(self):
        conn = _make_db([])
        result = compute_rolling_wr(conn, as_of_ts=_ts(2026, 3, 19))
        assert result.n_bets == 0
        assert result.win_rate == 0.0
        assert result.flagged is False

    def test_flag_fires_below_threshold_with_sufficient_bets(self):
        # 90% WR with 50 bets should flag (below 93%, n>=30)
        now = _ts(2026, 3, 19)
        recent = _ts(2026, 3, 10)
        trades = (
            [_sniper_win(recent)] * 45
            + [_sniper_loss(recent)] * 5
        )
        conn = _make_db(trades)
        result = compute_rolling_wr(conn, as_of_ts=now)
        assert result.win_rate < WR_FLAG_THRESHOLD
        assert result.n_bets >= WR_FLAG_MIN_BETS
        assert result.flagged is True

    def test_flag_silent_above_threshold(self):
        now = _ts(2026, 3, 19)
        recent = _ts(2026, 3, 10)
        # 95% WR — above threshold
        trades = [_sniper_win(recent)] * 38 + [_sniper_loss(recent)] * 2
        conn = _make_db(trades)
        result = compute_rolling_wr(conn, as_of_ts=now)
        assert result.flagged is False

    def test_flag_silent_below_threshold_but_insufficient_bets(self):
        # 90% WR but only 20 bets — don't flag (not enough data)
        now = _ts(2026, 3, 19)
        recent = _ts(2026, 3, 10)
        trades = [_sniper_win(recent)] * 18 + [_sniper_loss(recent)] * 2
        conn = _make_db(trades)
        result = compute_rolling_wr(conn, as_of_ts=now)
        assert result.flagged is False


# ── Constants check ───────────────────────────────────────────────────────────

class TestConstants:
    def test_wr_flag_threshold(self):
        assert WR_FLAG_THRESHOLD == 0.93

    def test_wr_flag_min_bets(self):
        assert WR_FLAG_MIN_BETS == 30
