"""Tests for _check_edge_convergence bridge in strategy_health_scorer.py.

Tests verify the convergence detection correctly identifies:
- STABLE: consistent win rate above break-even
- OSCILLATING: alternating above/below break-even
- CONVERGING: consecutive losing sessions (discard streak)
- INSUFFICIENT: < 3 sessions of history
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "analysis"))

from strategy_health_scorer import _check_edge_convergence


def _make_history(win_rates: list[float], cusum_s: float | None = None) -> list[dict]:
    """Build bucket history list from win rate sequence."""
    entries = [{"win_rate": wr, "n": 10} for wr in win_rates]
    if cusum_s is not None:
        # Set cusum_s on latest entry only (reflects current state)
        entries[-1]["cusum_s"] = cusum_s
    return entries


class TestCheckEdgeConvergence:
    def test_insufficient_data_below_3(self):
        history = _make_history([0.95, 0.96])
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "INSUFFICIENT"

    def test_stable_all_above_breakeven(self):
        # 93c bucket needs 93% WR. All entries well above.
        history = _make_history([0.96, 0.95, 0.97, 0.94, 0.96])
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "STABLE"

    def test_oscillating_alternating_above_below(self):
        # Alternates above/below 93% break-even
        history = _make_history([0.90, 0.96, 0.89, 0.95, 0.88, 0.97])
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "OSCILLATING"

    def test_converging_discard_streak(self):
        # 3 consecutive sessions below break-even = discard streak
        history = _make_history([0.96, 0.95, 0.88, 0.87, 0.89])
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "CONVERGING"

    def test_breakeven_from_bucket_key_90c(self):
        # 90c bucket needs 90% WR. Entries just above.
        history = _make_history([0.91, 0.92, 0.93, 0.91])
        result = _check_edge_convergence("KXBTC|90|yes", history)
        assert result == "STABLE"

    def test_breakeven_from_bucket_key_94c(self):
        # 94c bucket needs 94% WR. All below = converging
        history = _make_history([0.92, 0.91, 0.90, 0.93])
        result = _check_edge_convergence("KXBTC|94|yes", history)
        assert result == "CONVERGING"

    def test_stable_with_exactly_3_sessions(self):
        # Minimum viable sample
        history = _make_history([0.95, 0.96, 0.95])
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "STABLE"

    def test_insufficient_empty(self):
        result = _check_edge_convergence("KXBTC|93|yes", [])
        assert result == "INSUFFICIENT"

    def test_cusum_s_high_returns_converging(self):
        # cusum_s >= 4.0 overrides win_rate history → CONVERGING
        history = _make_history([0.96, 0.95, 0.97], cusum_s=4.5)
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "CONVERGING"

    def test_cusum_s_negative_returns_diverging(self):
        # cusum_s < 0 → DIVERGING
        history = _make_history([0.96, 0.95, 0.97], cusum_s=-0.5)
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "DIVERGING"

    def test_cusum_s_low_uses_win_rate_oscillation(self):
        # cusum_s in [0, 4) → falls back to win_rate oscillation check
        history = _make_history([0.90, 0.96, 0.89, 0.95, 0.88, 0.97], cusum_s=1.0)
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "OSCILLATING"

    def test_cusum_s_low_stable_bucket(self):
        # cusum_s in [0, 4) + consistent WR → STABLE
        history = _make_history([0.96, 0.95, 0.97, 0.94, 0.96], cusum_s=0.5)
        result = _check_edge_convergence("KXBTC|93|yes", history)
        assert result == "STABLE"
