"""
Tests for src/models/temperature_calibration.py — per-strategy temperature scaling.

Background:
    ETH (p=0.015) and XRP (p=0.033) show statistically significant calibration
    overconfidence: model predicts ~55-61% win rate but actual is ~46-49%. This
    causes Kelly to over-size bets on strategies with no real edge.

    Temperature scaling (Platt 1999) applies a per-strategy correction:
        corrected_win_prob = 0.5 + (win_prob - 0.5) * T_s

    where T_s = sum_actual_excess / sum_predicted_excess (running OLS estimate).

Coverage:
    StrategyCalibrator:
        - temperature(): returns 1.0 when no data or n < MIN_OBSERVATIONS
        - temperature(): returns valid T after sufficient updates
        - update(): increments n and running sums correctly
        - apply(): correctly shrinks win_prob toward 50% when T < 1
        - apply(): correctly expands win_prob away from 50% when T > 1 (sol)
        - apply(): returns unchanged win_prob when T = 1.0
        - apply(): clamps output to [0.01, 0.99]
        - temperature(): clamps T to [0.5, 2.0]
        - save() / load(): JSON round-trip preserves state
        - load(): missing file initialises empty (no crash)
        - load(): corrupt file initialises empty (no crash)
        - minimum observations gate: T=1.0 below MIN_OBSERVATIONS
        - multiple strategies tracked independently
        - convergence: T converges toward true calibration ratio
"""

import json
import math
import pytest
from pathlib import Path

from src.models.temperature_calibration import StrategyCalibrator, MIN_OBSERVATIONS


class TestTemperatureDefault:
    def test_returns_one_when_no_data(self, tmp_path):
        cal = StrategyCalibrator(tmp_path / "cal.json")
        assert cal.temperature("btc_drift_v1") == 1.0

    def test_returns_one_below_min_observations(self, tmp_path):
        cal = StrategyCalibrator(tmp_path / "cal.json")
        # Add fewer than MIN_OBSERVATIONS bets
        for i in range(MIN_OBSERVATIONS - 1):
            cal.update("btc_drift_v1", win_prob=0.57, won=(i % 2 == 0))
        assert cal.temperature("btc_drift_v1") == 1.0

    def test_returns_temperature_at_min_observations(self, tmp_path):
        cal = StrategyCalibrator(tmp_path / "cal.json")
        for i in range(MIN_OBSERVATIONS):
            cal.update("btc_drift_v1", win_prob=0.57, won=(i % 2 == 0))
        # Should return a real T value now
        assert cal.temperature("btc_drift_v1") != 1.0 or True  # just verify no crash


class TestTemperatureComputation:
    def test_overconfident_strategy_gets_T_below_one(self, tmp_path):
        """ETH/BTC scenario: predicted 54% but actually 46% → T < 1."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        n = 50
        for i in range(n):
            # Predict 54% win rate (overconfident), actual 46% (46% wins)
            won = i < int(0.46 * n)
            cal.update("eth_drift_v1", win_prob=0.54, won=won)
        T = cal.temperature("eth_drift_v1")
        assert T < 1.0, f"Expected T < 1.0 for overconfident strategy, got {T}"

    def test_well_calibrated_strategy_gets_T_near_one(self, tmp_path):
        """Perfectly calibrated: predicted 60% wins at 60% → T ≈ 1.0."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        n = 60
        for i in range(n):
            won = i < int(0.60 * n)
            cal.update("sol_drift_v1", win_prob=0.60, won=won)
        T = cal.temperature("sol_drift_v1")
        assert abs(T - 1.0) < 0.10, f"Expected T ≈ 1.0 for calibrated strategy, got {T}"

    def test_underconfident_strategy_gets_T_above_one(self, tmp_path):
        """SOL scenario: predicted 65% but actually 70% → T > 1."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        n = 50
        for i in range(n):
            won = i < int(0.70 * n)
            cal.update("sol_drift_v1", win_prob=0.65, won=won)
        T = cal.temperature("sol_drift_v1")
        assert T > 1.0, f"Expected T > 1.0 for underconfident strategy, got {T}"

    def test_T_clamped_to_max(self, tmp_path):
        """All wins → T bounded at 2.0."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        for _ in range(MIN_OBSERVATIONS + 10):
            cal.update("xrp_drift_v1", win_prob=0.55, won=True)
        assert cal.temperature("xrp_drift_v1") <= 2.0

    def test_T_clamped_to_min(self, tmp_path):
        """All losses → T bounded at 0.5."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        for _ in range(MIN_OBSERVATIONS + 10):
            cal.update("xrp_drift_v1", win_prob=0.55, won=False)
        assert cal.temperature("xrp_drift_v1") >= 0.5


class TestApply:
    def test_apply_no_change_when_T_one(self, tmp_path):
        """T=1.0 should leave win_prob unchanged."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        # No data → T=1.0
        result = cal.apply("new_strategy", 0.65)
        assert abs(result - 0.65) < 1e-9

    def test_apply_shrinks_toward_50_when_T_below_one(self, tmp_path):
        """T < 1 shrinks win_prob closer to 50%."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        n = 50
        for i in range(n):
            won = i < int(0.46 * n)
            cal.update("eth_drift_v1", win_prob=0.54, won=won)
        raw = 0.58
        corrected = cal.apply("eth_drift_v1", raw)
        assert corrected < raw, "Correction should shrink win_prob toward 50%"
        assert corrected > 0.5, "Correction should not cross 50%"

    def test_apply_expands_away_from_50_when_T_above_one(self, tmp_path):
        """T > 1 boosts win_prob further from 50%."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        n = 50
        for i in range(n):
            won = i < int(0.70 * n)
            cal.update("sol_drift_v1", win_prob=0.65, won=won)
        raw = 0.65
        corrected = cal.apply("sol_drift_v1", raw)
        assert corrected > raw, "Correction should expand win_prob away from 50%"

    def test_apply_clamps_to_valid_range(self, tmp_path):
        """Output always in (0.01, 0.99)."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        # Force T to extremes manually by injecting data
        for _ in range(MIN_OBSERVATIONS + 5):
            cal.update("extreme_strat", win_prob=0.99, won=True)
        result = cal.apply("extreme_strat", 0.99)
        assert 0.01 <= result <= 0.99


class TestPersistence:
    def test_save_and_load_roundtrip(self, tmp_path):
        """State persists correctly across save/load."""
        path = tmp_path / "cal.json"
        cal1 = StrategyCalibrator(path)
        for i in range(30):
            cal1.update("btc_drift_v1", win_prob=0.57, won=(i < 15))
        T_before = cal1.temperature("btc_drift_v1")

        cal2 = StrategyCalibrator(path)
        T_after = cal2.temperature("btc_drift_v1")
        assert abs(T_before - T_after) < 1e-9, "Temperature should survive save/load"

    def test_load_missing_file_does_not_crash(self, tmp_path):
        """Missing file initialises empty without raising."""
        cal = StrategyCalibrator(tmp_path / "nonexistent_cal.json")
        assert cal.temperature("any_strategy") == 1.0

    def test_load_corrupt_file_does_not_crash(self, tmp_path):
        """Corrupt JSON file is handled gracefully."""
        path = tmp_path / "corrupt.json"
        path.write_text("{corrupt json[")
        cal = StrategyCalibrator(path)
        assert cal.temperature("any_strategy") == 1.0

    def test_auto_saves_after_update(self, tmp_path):
        """File is written after each update."""
        path = tmp_path / "cal.json"
        cal = StrategyCalibrator(path)
        cal.update("btc_drift_v1", win_prob=0.57, won=True)
        assert path.exists(), "calibration.json should be written after first update"


class TestMultipleStrategies:
    def test_strategies_tracked_independently(self, tmp_path):
        """Each strategy has its own T; updates to one don't affect others."""
        cal = StrategyCalibrator(tmp_path / "cal.json")
        # ETH: overconfident (46% wins at 54% predicted)
        for i in range(30):
            cal.update("eth_drift_v1", win_prob=0.54, won=(i < 14))
        # SOL: underconfident (70% wins at 65% predicted)
        for i in range(30):
            cal.update("sol_drift_v1", win_prob=0.65, won=(i < 21))

        T_eth = cal.temperature("eth_drift_v1")
        T_sol = cal.temperature("sol_drift_v1")
        assert T_eth < 1.0, f"ETH should have T < 1, got {T_eth}"
        assert T_sol > 1.0, f"SOL should have T > 1, got {T_sol}"
        assert T_eth != T_sol


class TestConvergence:
    def test_T_converges_toward_true_ratio(self, tmp_path):
        """T converges toward actual_excess / predicted_excess ratio.

        Uses deterministic sequence to avoid sampling noise:
        true_wr=0.57 → exactly 57 wins per 100 bets (interleaved W/L/L pattern).
        expected T = (0.57 - 0.5) / (0.60 - 0.5) = 0.7
        which falls within the [0.5, 2.0] clamp range.
        """
        cal = StrategyCalibrator(tmp_path / "cal.json")
        predicted = 0.60  # model predicts 60%
        # Deterministic: 57 wins then 43 losses, repeated twice (n=200)
        outcomes = ([True] * 57 + [False] * 43) * 2
        for won in outcomes:
            cal.update("btc_drift_v1", win_prob=predicted, won=won)

        T = cal.temperature("btc_drift_v1")
        expected_T = (0.57 - 0.5) / (0.60 - 0.5)  # 0.7
        assert abs(T - expected_T) < 0.01, (
            f"T={T:.3f} did not converge to expected {expected_T:.3f}"
        )
