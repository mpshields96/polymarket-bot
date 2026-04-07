"""
tests/test_sports_analytics.py — Unit tests for sports_analytics.py

Covers: get_bet_counts, compute_sharp_roi_correlation, compute_equity_curve,
        compute_rolling_metrics, compute_strategy_breakdown, CalibrationReport,
        get_calibration_report (no-DB path), calibration_is_ready, _pearson_r,
        _brier_score, _roc_auc, generate_sports_performance_report.
"""

import math
import sys
import os
import sqlite3
import tempfile

# sports_analytics.py lives at src/strategies/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "strategies"))

from sports_analytics import (
    MIN_RESOLVED,
    MIN_BETS_FOR_CALIBRATION,
    get_bet_counts,
    compute_sharp_roi_correlation,
    compute_equity_curve,
    compute_rolling_metrics,
    compute_strategy_breakdown,
    CalibrationReport,
    CalibrationBin,
    get_calibration_report,
    calibration_is_ready,
    generate_sports_performance_report,
    _pearson_r,
    _brier_score,
    _roc_auc,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_bets(n_wins: int, n_losses: int, strategy: str = "sports_game",
               sharp_score: float = 50.0, profit_per_win: float = 1.0,
               stake: float = 1.0) -> list[dict]:
    """Build resolved bet list with win/loss split."""
    bets = []
    ts_base = "2026-01-{:02d}T12:00:00+00:00"
    for i in range(n_wins):
        bets.append({
            "result": "win",
            "profit": profit_per_win,
            "stake": stake,
            "strategy": strategy,
            "sharp_score": sharp_score,
            "logged_at": ts_base.format((i % 28) + 1),
        })
    for i in range(n_losses):
        bets.append({
            "result": "loss",
            "profit": -stake,
            "stake": stake,
            "strategy": strategy,
            "sharp_score": sharp_score,
            "logged_at": ts_base.format((i % 28) + 1),
        })
    return bets


def _make_trades_db(n_rows: int = 15) -> str:
    """Create a temp SQLite DB with a trades table and n_rows settled rows."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            side TEXT,
            result TEXT,
            win_prob REAL,
            edge_pct REAL,
            cost_usd REAL,
            pnl_cents INTEGER
        )
    """)
    for i in range(n_rows):
        side = "yes" if i % 2 == 0 else "no"
        result = "yes" if i % 3 != 0 else "no"  # ~67% win
        conn.execute(
            "INSERT INTO trades (side, result, win_prob, edge_pct, cost_usd, pnl_cents) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (side, result, 0.55, 0.08, 1.0, 45 if side == result else -100),
        )
    conn.commit()
    conn.close()
    return path


# ---------------------------------------------------------------------------
# Test: get_bet_counts
# ---------------------------------------------------------------------------

def test_get_bet_counts_empty():
    counts = get_bet_counts([])
    assert counts["total"] == 0
    assert counts["resolved"] == 0
    assert counts["pending"] == 0
    assert counts["wins"] == 0
    assert counts["losses"] == 0
    assert counts["min_required"] == MIN_RESOLVED


def test_get_bet_counts_wins_losses():
    bets = _make_bets(7, 3)
    counts = get_bet_counts(bets)
    assert counts["total"] == 10
    assert counts["resolved"] == 10
    assert counts["wins"] == 7
    assert counts["losses"] == 3
    assert counts["pending"] == 0


def test_get_bet_counts_pending_bets():
    bets = _make_bets(3, 2)
    bets.append({"result": "pending", "profit": 0, "stake": 1.0, "strategy": "x"})
    counts = get_bet_counts(bets)
    assert counts["total"] == 6
    assert counts["resolved"] == 5
    assert counts["pending"] == 1


# ---------------------------------------------------------------------------
# Test: compute_sharp_roi_correlation
# ---------------------------------------------------------------------------

def test_sharp_roi_correlation_inactive_below_minimum():
    bets = _make_bets(4, 4)  # only 8, below MIN_RESOLVED=10
    result = compute_sharp_roi_correlation(bets)
    assert result["status"] == "inactive"
    assert result["correlation_r"] is None
    assert result["bins"] == []


def test_sharp_roi_correlation_active():
    bets = _make_bets(8, 4, sharp_score=60.0)  # 12 bets, all in 40-80 bin
    result = compute_sharp_roi_correlation(bets)
    assert result["status"] == "active"
    assert result["n_resolved"] == 12
    # All bets have score=60, should land in 40-60 or 60-80 bin
    non_empty = [b for b in result["bins"] if b["n"] > 0]
    assert len(non_empty) >= 1
    # Pearson r should be a float (possibly 0 since all same score)
    assert result["correlation_r"] is None or isinstance(result["correlation_r"], float)


def test_sharp_roi_correlation_correlation_label():
    # Build bets where higher sharp_score correlates with wins
    bets = []
    for i in range(15):
        bets.append({
            "result": "win" if i % 2 == 0 else "loss",
            "profit": 1.0 if i % 2 == 0 else -1.0,
            "stake": 1.0,
            "sharp_score": float(i * 5),
            "logged_at": "2026-01-01T00:00:00+00:00",
        })
    result = compute_sharp_roi_correlation(bets)
    assert result["status"] == "active"
    assert result["correlation_label"] in (
        "strong positive", "moderate positive", "weak positive",
        "no correlation", "weak negative", "moderate negative", "strong negative",
    )


# ---------------------------------------------------------------------------
# Test: compute_equity_curve
# ---------------------------------------------------------------------------

def test_equity_curve_empty():
    curve = compute_equity_curve([])
    assert curve["dates"] == []
    assert curve["cumulative_pnl"] == []
    assert curve["max_drawdown"] == 0.0
    assert curve["final_pnl"] == 0.0
    assert curve["n"] == 0


def test_equity_curve_all_wins():
    bets = _make_bets(5, 0, profit_per_win=2.0)
    curve = compute_equity_curve(bets)
    assert curve["n"] == 5
    assert curve["final_pnl"] == pytest_approx(10.0, abs=0.01)
    assert curve["max_drawdown"] == 0.0  # never drew down


def test_equity_curve_drawdown():
    # 2 wins then 3 losses — drawdown = 3
    bets = [
        {"result": "win", "profit": 1.0, "stake": 1.0, "logged_at": "2026-01-01T00:00:00+00:00"},
        {"result": "win", "profit": 1.0, "stake": 1.0, "logged_at": "2026-01-02T00:00:00+00:00"},
        {"result": "loss", "profit": -1.0, "stake": 1.0, "logged_at": "2026-01-03T00:00:00+00:00"},
        {"result": "loss", "profit": -1.0, "stake": 1.0, "logged_at": "2026-01-04T00:00:00+00:00"},
        {"result": "loss", "profit": -1.0, "stake": 1.0, "logged_at": "2026-01-05T00:00:00+00:00"},
    ]
    curve = compute_equity_curve(bets)
    assert curve["final_pnl"] == pytest_approx(-1.0, abs=0.01)
    assert curve["max_drawdown"] == pytest_approx(3.0, abs=0.01)


# ---------------------------------------------------------------------------
# Test: compute_rolling_metrics
# ---------------------------------------------------------------------------

def test_rolling_metrics_returns_all_windows():
    bets = _make_bets(5, 5)
    result = compute_rolling_metrics(bets, windows=(7, 30, 90))
    assert set(result.keys()) == {7, 30, 90}
    for window_data in result.values():
        assert "n" in window_data
        assert "win_rate" in window_data
        assert "roi_pct" in window_data


def test_rolling_metrics_empty_bets():
    result = compute_rolling_metrics([])
    for window_data in result.values():
        assert window_data["n"] == 0
        assert window_data["win_rate"] == 0.0


# ---------------------------------------------------------------------------
# Test: compute_strategy_breakdown
# ---------------------------------------------------------------------------

def test_strategy_breakdown_single_strategy():
    bets = _make_bets(6, 4, strategy="sports_game")
    rows = compute_strategy_breakdown(bets)
    assert len(rows) == 1
    assert rows[0]["strategy"] == "sports_game"
    assert rows[0]["n"] == 10


def test_strategy_breakdown_multiple_strategies():
    bets = _make_bets(6, 4, strategy="daily_sniper") + _make_bets(3, 2, strategy="sports_game")
    rows = compute_strategy_breakdown(bets)
    assert len(rows) == 2
    strategies = {r["strategy"] for r in rows}
    assert "daily_sniper" in strategies
    assert "sports_game" in strategies


def test_strategy_breakdown_sorted_by_roi():
    # daily_sniper: 10W/0L = 100% WR; sports_game: 0W/10L = 0% WR
    bets = _make_bets(10, 0, strategy="daily_sniper") + _make_bets(0, 10, strategy="sports_game")
    rows = compute_strategy_breakdown(bets)
    assert rows[0]["strategy"] == "daily_sniper"  # higher ROI first
    assert rows[1]["strategy"] == "sports_game"


# ---------------------------------------------------------------------------
# Test: CalibrationBin.calibration_error
# ---------------------------------------------------------------------------

def test_calibration_bin_error():
    cb = CalibrationBin(prob_low=0.5, prob_high=0.6, predicted=0.55, actual=0.45, count=10)
    assert abs(cb.calibration_error - 0.10) < 0.001


# ---------------------------------------------------------------------------
# Test: get_calibration_report — no DB (returns inactive)
# ---------------------------------------------------------------------------

def test_calibration_report_no_db():
    report = get_calibration_report(db_path="/nonexistent/path/db.sqlite")
    assert not report.is_active
    assert report.bets_total == 0
    assert report.bets_needed_for_activation == MIN_BETS_FOR_CALIBRATION


def test_calibration_report_active_with_db():
    db_path = _make_trades_db(n_rows=15)
    try:
        report = get_calibration_report(db_path=db_path)
        assert report.is_active
        assert report.bets_total == 15
        assert report.brier_score >= 0.0
        assert 0.5 <= report.roc_auc <= 1.0
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------------------------
# Test: calibration_is_ready
# ---------------------------------------------------------------------------

def test_calibration_is_ready_false_no_db():
    assert not calibration_is_ready(db_path="/nonexistent/db.sqlite")


def test_calibration_is_ready_true_with_enough_rows():
    db_path = _make_trades_db(n_rows=MIN_BETS_FOR_CALIBRATION)
    try:
        assert calibration_is_ready(db_path=db_path)
    finally:
        os.unlink(db_path)


# ---------------------------------------------------------------------------
# Test: _pearson_r (math helper)
# ---------------------------------------------------------------------------

def test_pearson_r_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [1.0, 2.0, 3.0, 4.0, 5.0]
    r = _pearson_r(xs, ys)
    assert abs(r - 1.0) < 0.001


def test_pearson_r_zero_variance_returns_none():
    xs = [1.0, 1.0, 1.0]
    ys = [2.0, 3.0, 4.0]
    r = _pearson_r(xs, ys)
    assert r is None


def test_pearson_r_insufficient_data():
    assert _pearson_r([1.0], [1.0]) is None
    assert _pearson_r([], []) is None


# ---------------------------------------------------------------------------
# Test: _brier_score
# ---------------------------------------------------------------------------

def test_brier_score_perfect():
    # Perfect: prob=1 for all wins, prob=0 for all losses
    probs = [1.0, 1.0, 0.0, 0.0]
    outcomes = [1, 1, 0, 0]
    assert _brier_score(probs, outcomes) == 0.0


def test_brier_score_random():
    # Random classifier: prob=0.5 always
    probs = [0.5] * 100
    outcomes = [1] * 50 + [0] * 50
    score = _brier_score(probs, outcomes)
    assert abs(score - 0.25) < 0.01


# ---------------------------------------------------------------------------
# Test: _roc_auc
# ---------------------------------------------------------------------------

def test_roc_auc_perfect():
    probs = [0.9, 0.8, 0.2, 0.1]
    outcomes = [1, 1, 0, 0]
    auc = _roc_auc(probs, outcomes)
    assert abs(auc - 1.0) < 0.001


def test_roc_auc_random():
    probs = [0.5, 0.5, 0.5, 0.5]
    outcomes = [1, 0, 1, 0]
    auc = _roc_auc(probs, outcomes)
    assert abs(auc - 0.5) < 0.01


def test_roc_auc_all_same_outcome_returns_half():
    probs = [0.8, 0.6, 0.4]
    outcomes = [1, 1, 1]
    auc = _roc_auc(probs, outcomes)
    assert auc == 0.5  # degenerate case


# ---------------------------------------------------------------------------
# Test: generate_sports_performance_report
# ---------------------------------------------------------------------------

def test_report_insufficient_data():
    bets = _make_bets(3, 3)  # only 6, below MIN_RESOLVED
    report = generate_sports_performance_report(bets, db_path="/nonexistent/db.sqlite",
                                                 include_calibration=True)
    assert "Insufficient data" in report or "insufficient" in report.lower()
    assert "=== SPORTS PERFORMANCE REPORT ===" in report


def test_report_sufficient_data():
    bets = _make_bets(8, 4, profit_per_win=2.0, stake=2.0)
    report = generate_sports_performance_report(bets, db_path="/nonexistent/db.sqlite",
                                                 include_calibration=False)
    assert "ROLLING PERFORMANCE" in report
    assert "EQUITY CURVE" in report
    assert "STRATEGY BREAKDOWN" in report
    assert "=== END REPORT ===" in report


# ---------------------------------------------------------------------------
# pytest approx helper (avoid importing pytest at module level)
# ---------------------------------------------------------------------------

class pytest_approx:
    """Lightweight pytest.approx replacement for use in plain assertEqual."""
    def __init__(self, value: float, abs: float = 1e-6):
        self.value = value
        self.abs = abs
    def __eq__(self, other: float) -> bool:
        return math.isclose(other, self.value, abs_tol=self.abs)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
