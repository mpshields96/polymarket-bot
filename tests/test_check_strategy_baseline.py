"""
Tests for scripts/check_strategy_baseline.py — strategy win-rate DB checker.

This module is used by scripts/verify_change.sh to gate strategy parameter
changes: if live settled bets show a win rate below the baseline after a
change, verify_change.sh reverts the change automatically.
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util
spec = importlib.util.spec_from_file_location(
    "check_strategy_baseline",
    Path(__file__).parent.parent / "scripts" / "check_strategy_baseline.py",
)
csb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(csb)

query_strategy_baseline = csb.query_strategy_baseline
check_passes = csb.check_passes


# ── Fixtures ─────────────────────────────────────────────────────────

def _make_db(trades: list[dict]) -> str:
    """Create a temp SQLite DB with trades table, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    conn = sqlite3.connect(tmp.name)
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            strategy TEXT,
            side TEXT,
            result TEXT,
            pnl_cents INTEGER,
            is_paper INTEGER,
            settled_at REAL
        )
    """)
    for t in trades:
        conn.execute(
            "INSERT INTO trades (strategy, side, result, pnl_cents, is_paper, settled_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (t["strategy"], t["side"], t["result"], t["pnl_cents"], t["is_paper"], t.get("settled_at", 1000.0)),
        )
    conn.commit()
    conn.close()
    return tmp.name


def _win(strategy="expiry_sniper", side="yes", pnl=180):
    return {"strategy": strategy, "side": side, "result": side, "pnl_cents": pnl, "is_paper": 0}


def _loss(strategy="expiry_sniper", side="yes", pnl=-190):
    return {"strategy": strategy, "side": side, "result": "no", "pnl_cents": pnl, "is_paper": 0}


def _paper_win(strategy="expiry_sniper", side="yes", pnl=50):
    return {"strategy": strategy, "side": side, "result": side, "pnl_cents": pnl, "is_paper": 1}


# ── query_strategy_baseline tests ────────────────────────────────────

class TestQueryStrategyBaseline:

    def test_perfect_win_rate(self):
        db = _make_db([_win() for _ in range(10)])
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert result["bets"] == 10
        assert result["win_rate"] == 1.0
        assert result["total_pnl_usd"] > 0

    def test_win_rate_calculation(self):
        trades = [_win()] * 9 + [_loss()]
        db = _make_db(trades)
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert result["bets"] == 10
        assert abs(result["win_rate"] - 0.9) < 0.001

    def test_only_live_trades_counted(self):
        # Paper wins should NOT be counted in baseline
        trades = [_win()] * 5 + [_paper_win()] * 10
        db = _make_db(trades)
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert result["bets"] == 5

    def test_last_n_limit_respected(self):
        # 20 trades total, but last_n=10 should only use 10
        trades = [_win() for _ in range(20)]
        db = _make_db(trades)
        result = query_strategy_baseline(db, "expiry_sniper", last_n=10)
        assert result["bets"] == 10

    def test_wrong_strategy_returns_zero_bets(self):
        db = _make_db([_win()])
        result = query_strategy_baseline(db, "nonexistent_strategy", last_n=30)
        assert result["bets"] == 0
        assert result["win_rate"] is None

    def test_no_settled_trades_returns_none_win_rate(self):
        db = _make_db([])
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert result["bets"] == 0
        assert result["win_rate"] is None

    def test_no_side_bets_only_paper_returns_none(self):
        db = _make_db([_paper_win() for _ in range(5)])
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert result["bets"] == 0

    def test_pnl_calculated_correctly(self):
        trades = [_win(pnl=200), _win(pnl=150), _loss(pnl=-190)]
        db = _make_db(trades)
        result = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        assert abs(result["total_pnl_usd"] - (200 + 150 - 190) / 100.0) < 0.01

    def test_strategy_isolation(self):
        # Trades for different strategies don't mix
        trades = [_win(strategy="expiry_sniper")] * 5 + [_loss(strategy="btc_drift_v1")] * 5
        db = _make_db(trades)
        result_sniper = query_strategy_baseline(db, "expiry_sniper", last_n=30)
        result_drift = query_strategy_baseline(db, "btc_drift_v1", last_n=30)
        assert result_sniper["bets"] == 5
        assert result_sniper["win_rate"] == 1.0
        assert result_drift["bets"] == 5
        assert result_drift["win_rate"] == 0.0

    def test_no_side_wins_counted_correctly(self):
        # NO-side bets win when result == "no"
        no_win = {"strategy": "btc_drift_v1", "side": "no", "result": "no", "pnl_cents": 180, "is_paper": 0}
        no_loss = {"strategy": "btc_drift_v1", "side": "no", "result": "yes", "pnl_cents": -190, "is_paper": 0}
        db = _make_db([no_win, no_win, no_loss])
        result = query_strategy_baseline(db, "btc_drift_v1", last_n=30)
        assert result["bets"] == 3
        assert abs(result["win_rate"] - 2 / 3) < 0.001


# ── check_passes tests ────────────────────────────────────────────────

class TestCheckPasses:

    def test_passes_when_win_rate_above_threshold(self):
        result = {"bets": 20, "win_rate": 0.95, "total_pnl_usd": 50.0}
        passed, reason = check_passes(result, min_win_rate=0.90)
        assert passed is True
        assert "PASS" in reason

    def test_fails_when_win_rate_below_threshold(self):
        result = {"bets": 20, "win_rate": 0.80, "total_pnl_usd": -5.0}
        passed, reason = check_passes(result, min_win_rate=0.90)
        assert passed is False
        assert "FAIL" in reason
        assert "0.80" in reason or "80" in reason

    def test_fails_when_no_data(self):
        result = {"bets": 0, "win_rate": None, "total_pnl_usd": 0.0}
        passed, reason = check_passes(result, min_win_rate=0.90)
        assert passed is False
        assert "no data" in reason.lower() or "insufficient" in reason.lower()

    def test_passes_exactly_at_threshold(self):
        result = {"bets": 10, "win_rate": 0.90, "total_pnl_usd": 20.0}
        passed, reason = check_passes(result, min_win_rate=0.90)
        assert passed is True

    def test_reason_includes_win_rate_and_bets(self):
        result = {"bets": 15, "win_rate": 0.933, "total_pnl_usd": 42.0}
        passed, reason = check_passes(result, min_win_rate=0.90)
        assert "15" in reason
        assert passed is True

    def test_fails_with_fewer_than_min_bets(self):
        result = {"bets": 2, "win_rate": 1.0, "total_pnl_usd": 5.0}
        passed, reason = check_passes(result, min_win_rate=0.90, min_bets=5)
        assert passed is False
        assert "insufficient" in reason.lower() or "bets" in reason.lower()

    def test_passes_with_exact_min_bets(self):
        result = {"bets": 5, "win_rate": 0.95, "total_pnl_usd": 20.0}
        passed, reason = check_passes(result, min_win_rate=0.90, min_bets=5)
        assert passed is True
