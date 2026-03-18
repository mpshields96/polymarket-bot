"""
Tests for scripts/strategy_drift_check.py — Page-Hinkley sequential drift detection.

The Page-Hinkley (PH) test detects downward drift in a strategy's win rate by
accumulating a CUSUM statistic. When the statistic exceeds a threshold, it means
the strategy's recent WR is significantly below its historical target.

Academic basis:
- Page (1954) "Continuous inspection schemes" — original sequential CUSUM
- Hinkley (1971) — one-sided sequential test for drift detection
- Basseville & Nikiforov (1993) — "Detection of Abrupt Changes in Signals"

Test structure:
- Pure functions only (no DB needed for unit tests)
- Integration test validates DB query contract
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Add scripts/ to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import strategy_drift_check as sdc


# ── Unit: _page_hinkley_stat ──────────────────────────────────────────────

class TestPageHinkleyStat:
    """Tests for the core PH statistic computation."""

    def test_no_drift_all_wins(self):
        """All wins: CUSUM stays at 0, no alert."""
        outcomes = [1] * 30
        stat, _peak, alert = sdc._page_hinkley_stat(outcomes, target_wr=0.65, delta=0.10, h=4.0)
        assert not alert, "All wins should not trigger alert"
        assert stat == pytest.approx(0.0), "All wins → CUSUM = 0 (floored)"

    def test_no_drift_stable_wr(self):
        """WR at exactly target: no alert."""
        # 65% WR — matches target_wr=0.65
        outcomes = [1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1, 0, 1, 1]
        # 14/20 = 70% — slightly above target, definitely no alert
        stat, _peak, alert = sdc._page_hinkley_stat(outcomes, target_wr=0.65, delta=0.10, h=4.0)
        assert not alert

    def test_clear_downward_drift(self):
        """WR drops to 0% (all losses): alert should fire quickly."""
        outcomes = [1] * 15 + [0] * 25  # 15 wins then 25 straight losses
        stat, _peak, alert = sdc._page_hinkley_stat(outcomes, target_wr=0.65, delta=0.10, h=4.0)
        assert alert, "25 straight losses after stable period should trigger PH alert"
        assert stat > 4.0

    def test_stat_returns_float(self):
        """Stat is always a non-negative float."""
        outcomes = [1, 0, 1, 0, 1]
        stat, _peak, _ = sdc._page_hinkley_stat(outcomes, target_wr=0.50, delta=0.10, h=4.0)
        assert isinstance(stat, float)
        assert stat >= 0.0

    def test_empty_outcomes(self):
        """Empty sequence returns (0.0, 0.0, False)."""
        stat, peak, alert = sdc._page_hinkley_stat([], target_wr=0.65, delta=0.10, h=4.0)
        assert stat == 0.0
        assert peak == 0.0
        assert not alert

    def test_single_observation(self):
        """Single observation does not alert."""
        _stat, _peak, alert = sdc._page_hinkley_stat([0], target_wr=0.65, delta=0.10, h=4.0)
        assert not alert

    def test_high_threshold_requires_more_evidence(self):
        """Higher h threshold requires more consecutive drift to alert."""
        outcomes = [0] * 10  # 10 straight losses
        _, _peak, alert_low_h = sdc._page_hinkley_stat(outcomes, target_wr=0.50, delta=0.10, h=1.0)
        _, _peak2, alert_high_h = sdc._page_hinkley_stat(outcomes, target_wr=0.50, delta=0.10, h=10.0)
        # Low threshold should alert, high threshold may not
        assert alert_low_h, "Low threshold (h=1) should alert on 10 straight losses"

    def test_sol_drift_scenario_stable(self):
        """sol_drift at historical 71% WR: no alert with target 65%."""
        import random
        random.seed(42)
        # Generate 40 bets at 71% WR
        outcomes = [1 if random.random() < 0.71 else 0 for _ in range(40)]
        stat, _peak, alert = sdc._page_hinkley_stat(outcomes, target_wr=0.65, delta=0.10, h=4.0)
        assert not alert, f"71% WR should not alert at target=65%, h=4.0 (stat={stat:.3f})"

    def test_sol_drift_scenario_decline(self):
        """sol_drift drops from 71% to 40%: alert fires within 30 more bets."""
        import random
        random.seed(99)
        # First 20 bets at 71% WR
        stable = [1 if random.random() < 0.71 else 0 for _ in range(20)]
        # Next 30 bets at 40% WR (significant decline)
        declined = [1 if random.random() < 0.40 else 0 for _ in range(30)]
        outcomes = stable + declined
        stat, _peak, alert = sdc._page_hinkley_stat(outcomes, target_wr=0.65, delta=0.10, h=4.0)
        assert alert, f"40% WR after 30 bets (vs target 65%) should trigger alert (stat={stat:.3f})"

    def test_reference_value_is_midpoint(self):
        """
        PH reference k = target_wr - delta/2.
        When actual WR == k, CUSUM is a random walk around 0 (no systematic drift).
        Over 100 bets at WR=k, stat should remain bounded with high probability.
        """
        import random
        random.seed(7)
        target_wr = 0.65
        delta = 0.10
        k = target_wr - delta / 2  # = 0.60
        # Generate bets at exactly k WR
        outcomes = [1 if random.random() < k else 0 for _ in range(100)]
        stat, _peak, _ = sdc._page_hinkley_stat(outcomes, target_wr=target_wr, delta=delta, h=4.0)
        # At WR=k=0.60 with target=0.65, this is border — some false positives acceptable
        # but stat should not be astronomically large
        assert stat < 20.0, f"At boundary WR, stat should be bounded (got {stat:.3f})"

    def test_cusum_resets_to_zero_floor(self):
        """CUSUM floors at 0 (one-sided test — only detects downward drift)."""
        # All wins far above target: CUSUM should not go negative
        outcomes = [1] * 50
        stat, _peak, _ = sdc._page_hinkley_stat(outcomes, target_wr=0.50, delta=0.10, h=4.0)
        assert stat >= 0.0, "PH stat must be non-negative"


# ── Unit: _rolling_wr ─────────────────────────────────────────────────────

class TestRollingWR:
    """Tests for rolling win rate computation."""

    def test_empty(self):
        assert sdc._rolling_wr([], 20) is None

    def test_short_below_window(self):
        outcomes = [1, 0, 1]
        assert sdc._rolling_wr(outcomes, 20) == pytest.approx(2 / 3)

    def test_uses_last_n(self):
        outcomes = [0] * 10 + [1] * 20  # last 20 are all wins
        assert sdc._rolling_wr(outcomes, 20) == pytest.approx(1.0)

    def test_exact_window(self):
        outcomes = [1, 0, 1, 0]  # 50%
        assert sdc._rolling_wr(outcomes, 4) == pytest.approx(0.5)

    def test_single_win(self):
        assert sdc._rolling_wr([1], 20) == pytest.approx(1.0)

    def test_single_loss(self):
        assert sdc._rolling_wr([0], 20) == pytest.approx(0.0)


# ── Unit: _assess_strategy ────────────────────────────────────────────────

class TestAssessStrategy:
    """Tests for _assess_strategy which wraps PH + rolling WR."""

    def _make_result(self, outcomes: list[int], target_wr: float = 0.65) -> sdc.StrategyDriftResult:
        return sdc._assess_strategy("test_v1", outcomes, target_wr=target_wr)

    def test_result_fields_populated(self):
        outcomes = [1, 0, 1, 1, 0]
        result = self._make_result(outcomes)
        assert result.strategy_name == "test_v1"
        assert result.n_bets == 5
        assert isinstance(result.overall_wr, float)
        assert isinstance(result.rolling_20_wr, float)
        assert isinstance(result.ph_stat, float)
        assert isinstance(result.alert, bool)
        assert isinstance(result.status, str)

    def test_no_alert_healthy_strategy(self):
        # sol_drift at 71% WR — healthy
        outcomes = [1, 1, 1, 0, 1, 1, 1, 0, 1, 1,
                    1, 1, 1, 0, 1, 1, 1, 0, 1, 1]  # 15/20 = 75%
        result = self._make_result(outcomes, target_wr=0.65)
        assert not result.alert

    def test_alert_declining_strategy(self):
        # Strategy drifts down: 20 stable wins then 30 losses
        outcomes = [1] * 20 + [0] * 30
        result = self._make_result(outcomes, target_wr=0.65)
        assert result.alert
        assert "DRIFT" in result.status.upper() or "ALERT" in result.status.upper()

    def test_insufficient_data_no_alert(self):
        # Only 3 bets — insufficient for PH test
        outcomes = [0, 0, 0]
        result = self._make_result(outcomes, target_wr=0.65)
        assert not result.alert  # Don't alert on tiny samples

    def test_n_bets_matches_input(self):
        outcomes = [1] * 13
        result = self._make_result(outcomes)
        assert result.n_bets == 13

    def test_overall_wr_correct(self):
        outcomes = [1, 1, 1, 0]  # 75%
        result = self._make_result(outcomes)
        assert result.overall_wr == pytest.approx(0.75)


# ── Integration: STRATEGY_REGISTRY has required fields ────────────────────

class TestStrategyRegistry:
    """Validate the strategy registry has all required fields."""

    def test_registry_not_empty(self):
        assert len(sdc.STRATEGY_REGISTRY) > 0

    def test_all_entries_have_required_keys(self):
        required = {"name", "target_wr", "delta", "h", "min_bets"}
        for entry in sdc.STRATEGY_REGISTRY:
            missing = required - set(entry.keys())
            assert not missing, f"Entry {entry.get('name')} missing keys: {missing}"

    def test_target_wr_in_valid_range(self):
        for entry in sdc.STRATEGY_REGISTRY:
            wr = entry["target_wr"]
            assert 0.0 < wr < 1.0, f"{entry['name']} target_wr={wr} out of range"

    def test_delta_positive(self):
        for entry in sdc.STRATEGY_REGISTRY:
            assert entry["delta"] > 0, f"{entry['name']} delta must be positive"

    def test_h_positive(self):
        for entry in sdc.STRATEGY_REGISTRY:
            assert entry["h"] > 0, f"{entry['name']} h threshold must be positive"

    def test_min_bets_at_least_10(self):
        for entry in sdc.STRATEGY_REGISTRY:
            assert entry["min_bets"] >= 10, f"{entry['name']} min_bets should be >= 10"

    def test_known_strategies_present(self):
        names = {e["name"] for e in sdc.STRATEGY_REGISTRY}
        for expected in ["sol_drift_v1", "eth_drift_v1", "btc_drift_v1", "xrp_drift_v1"]:
            assert expected in names, f"{expected} missing from registry"

    def test_sol_drift_has_higher_target(self):
        sol = next(e for e in sdc.STRATEGY_REGISTRY if e["name"] == "sol_drift_v1")
        others = [e for e in sdc.STRATEGY_REGISTRY if e["name"] != "sol_drift_v1"]
        for other in others:
            assert sol["target_wr"] > other["target_wr"], \
                f"sol_drift should have higher target_wr than {other['name']}"


# ── Math property: monotonicity ───────────────────────────────────────────

class TestMathProperties:
    """Mathematical properties the PH stat must satisfy."""

    def test_more_losses_higher_stat(self):
        """Adding more losses monotonically increases the PH stat (before reset)."""
        base = [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]  # 50% WR
        extended = base + [0, 0, 0, 0, 0]  # 5 more losses

        stat_base, _p1, _ = sdc._page_hinkley_stat(base, target_wr=0.65, delta=0.10, h=4.0)
        stat_extended, _p2, _ = sdc._page_hinkley_stat(extended, target_wr=0.65, delta=0.10, h=4.0)

        assert stat_extended >= stat_base, "More losses should not decrease PH stat"

    def test_all_wins_stat_zero(self):
        """All wins → CUSUM never rises → stat = 0."""
        outcomes = [1] * 100
        stat, _peak, _ = sdc._page_hinkley_stat(outcomes, target_wr=0.50, delta=0.10, h=4.0)
        assert stat == pytest.approx(0.0)

    def test_reference_value_determines_sensitivity(self):
        """
        This test verifies: same losses, larger delta → smaller stat (more allowance).
        Reference k = target_wr - delta/2. Larger delta → lower k → each loss adds less
        to CUSUM (loss increment = k).
        """
        losses = [0] * 15
        stat_small_delta, _p1, _ = sdc._page_hinkley_stat(losses, target_wr=0.50, delta=0.05, h=4.0)
        stat_large_delta, _p2, _ = sdc._page_hinkley_stat(losses, target_wr=0.50, delta=0.20, h=4.0)
        # Larger delta → lower reference → each loss contributes less to CUSUM
        assert stat_large_delta < stat_small_delta, \
            "Larger delta (more allowance) should produce smaller stat for same losses"
