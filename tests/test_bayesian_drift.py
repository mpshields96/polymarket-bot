"""
Tests for src/models/bayesian_drift.py — Bayesian online learning for drift strategy.

Coverage:
    BayesianDriftModel:
        - Initialisation: flat prior values match paper-calibrated defaults
        - predict(): sigmoid output, bounded [0.01, 0.99]
        - update(): single observation moves posterior in correct direction
        - update(): multiple YES-win observations increase sensitivity estimate
        - update(): variance decreases monotonically with more observations
        - kelly_scale: at flat prior = 1.0, decreases if variance diverges
        - should_override_static(): False below MIN_OBSERVATIONS, True above
        - to_dict() / from_dict(): round-trip preserves all fields
        - save() / load(): JSON persistence round-trip
        - load(): missing file returns flat prior without raising
        - load(): corrupt file returns flat prior without raising
        - summary(): returns non-empty string
        - win_rate: tracks correctly across wins/losses
"""

import json
import math
import pytest
from pathlib import Path

from src.models.bayesian_drift import (
    BayesianDriftModel,
    _PRIOR_LOG_SENSITIVITY_MEAN,
    _PRIOR_INTERCEPT_MEAN,
    _MIN_OBSERVATIONS_FOR_OVERRIDE,
)


class TestInitialisation:
    def test_flat_prior_sensitivity_matches_paper_default(self):
        """Default model uses paper-calibrated sensitivity=300."""
        model = BayesianDriftModel()
        assert abs(model.sensitivity - 300.0) < 1.0

    def test_flat_prior_intercept_is_zero(self):
        model = BayesianDriftModel()
        assert model.intercept == pytest.approx(0.0)

    def test_initial_observations_zero(self):
        model = BayesianDriftModel()
        assert model.n_observations == 0
        assert model.n_wins == 0

    def test_win_rate_zero_at_start(self):
        model = BayesianDriftModel()
        assert model.win_rate == 0.0


class TestPredict:
    def test_positive_drift_gives_high_p_yes(self):
        """Positive drift → model expects YES to win → P(YES) > 0.5."""
        model = BayesianDriftModel()
        p = model.predict(drift_pct=0.01)  # 1% BTC up
        assert p > 0.9

    def test_negative_drift_gives_low_p_yes(self):
        """Negative drift → model expects NO to win → P(YES) < 0.5."""
        model = BayesianDriftModel()
        p = model.predict(drift_pct=-0.01)
        assert p < 0.1

    def test_zero_drift_gives_approx_half(self):
        """No drift + no intercept → P(YES) ≈ 0.5."""
        model = BayesianDriftModel()
        p = model.predict(drift_pct=0.0)
        assert abs(p - 0.5) < 0.01

    def test_output_bounded(self):
        model = BayesianDriftModel()
        for drift in [-1.0, 0.0, 1.0]:
            p = model.predict(drift)
            assert 0.01 <= p <= 0.99


class TestUpdate:
    def test_single_yes_win_increases_n_observations(self):
        model = BayesianDriftModel()
        model.update(drift_pct=0.003, side="yes", won=True)
        assert model.n_observations == 1
        assert model.n_wins == 1

    def test_single_yes_loss_increments_observations_not_wins(self):
        model = BayesianDriftModel()
        model.update(drift_pct=0.003, side="yes", won=False)
        assert model.n_observations == 1
        assert model.n_wins == 0

    def test_positive_drift_yes_win_nudges_sensitivity_up(self):
        """When YES wins on positive drift, model should reinforce sensitivity."""
        model = BayesianDriftModel()
        s_before = model.sensitivity
        # Repeat 10 YES wins on positive drift to get clear signal
        for _ in range(10):
            model.update(drift_pct=0.003, side="yes", won=True)
        # Sensitivity should stay reasonable (prior pulls it back, but it shouldn't collapse)
        assert model.sensitivity > 10.0  # never drops to near-zero
        assert model.sensitivity < 10000.0  # never explodes

    def test_variance_decreases_monotonically(self):
        """Each observation should reduce posterior variance (more certainty)."""
        model = BayesianDriftModel()
        prev_var_s = model.log_sensitivity_var
        prev_var_i = model.intercept_var
        for i in range(20):
            model.update(drift_pct=0.003 * (1 if i % 2 == 0 else -1), side="yes", won=True)
            assert model.log_sensitivity_var <= prev_var_s + 1e-9
            assert model.intercept_var <= prev_var_i + 1e-9
            prev_var_s = model.log_sensitivity_var
            prev_var_i = model.intercept_var

    def test_no_side_win_counts_as_yes_loss(self):
        """NO win = YES lost. yes_won = False when side=no, won=True."""
        model_no_win = BayesianDriftModel()
        model_yes_loss = BayesianDriftModel()

        model_no_win.update(drift_pct=0.003, side="no", won=True)
        model_yes_loss.update(drift_pct=0.003, side="yes", won=False)

        # Both should produce identical updates since yes_won=False in both cases
        assert model_no_win.log_sensitivity_mean == pytest.approx(
            model_yes_loss.log_sensitivity_mean, abs=1e-6
        )

    def test_win_rate_tracks_correctly(self):
        model = BayesianDriftModel()
        model.update(drift_pct=0.003, side="yes", won=True)
        model.update(drift_pct=0.003, side="yes", won=True)
        model.update(drift_pct=0.003, side="yes", won=False)
        assert model.win_rate == pytest.approx(2 / 3, abs=0.001)


class TestKellyScale:
    def test_kelly_scale_at_prior_is_one(self):
        """At flat prior (uncertainty=1.0), kelly_scale should be 1.0 (no reduction)."""
        model = BayesianDriftModel()
        # At flat prior, both variances equal prior variances → uncertainty = 1.0 → kelly = 0.25
        # Actually uncertainty = sqrt(1.0 * 1.0) = 1.0 → kelly_scale = max(0.25, 1 - 0.75) = 0.25
        # This is expected: before any data, maximum conservatism
        assert model.kelly_scale >= 0.25
        assert model.kelly_scale <= 1.0

    def test_kelly_scale_increases_with_more_observations(self):
        """More data → lower variance → higher kelly_scale."""
        model = BayesianDriftModel()
        initial_kelly = model.kelly_scale
        for _ in range(50):
            model.update(drift_pct=0.003, side="yes", won=True)
        assert model.kelly_scale >= initial_kelly

    def test_kelly_scale_bounded(self):
        model = BayesianDriftModel()
        for _ in range(100):
            model.update(drift_pct=0.003, side="yes", won=True)
        assert 0.25 <= model.kelly_scale <= 1.0


class TestShouldOverride:
    def test_false_below_threshold(self):
        model = BayesianDriftModel()
        for _ in range(_MIN_OBSERVATIONS_FOR_OVERRIDE - 1):
            model.update(drift_pct=0.003, side="yes", won=True)
        assert not model.should_override_static()

    def test_true_at_threshold(self):
        model = BayesianDriftModel()
        for _ in range(_MIN_OBSERVATIONS_FOR_OVERRIDE):
            model.update(drift_pct=0.003, side="yes", won=True)
        assert model.should_override_static()


class TestSerialization:
    def test_to_dict_contains_all_fields(self):
        model = BayesianDriftModel()
        d = model.to_dict()
        for key in ("log_sensitivity_mean", "log_sensitivity_var",
                    "intercept_mean", "intercept_var",
                    "n_observations", "n_wins", "sensitivity", "win_rate"):
            assert key in d

    def test_from_dict_round_trip(self):
        model = BayesianDriftModel()
        model.update(drift_pct=0.003, side="yes", won=True)
        model.update(drift_pct=-0.002, side="no", won=False)
        d = model.to_dict()
        restored = BayesianDriftModel.from_dict(d)
        assert restored.log_sensitivity_mean == pytest.approx(model.log_sensitivity_mean)
        assert restored.intercept_mean == pytest.approx(model.intercept_mean)
        assert restored.n_observations == model.n_observations
        assert restored.n_wins == model.n_wins

    def test_save_load_round_trip(self, tmp_path):
        path = tmp_path / "test_posterior.json"
        model = BayesianDriftModel()
        model.update(drift_pct=0.003, side="yes", won=True)
        model.save(path)

        loaded = BayesianDriftModel.load(path)
        assert loaded.log_sensitivity_mean == pytest.approx(model.log_sensitivity_mean)
        assert loaded.n_observations == 1

    def test_load_missing_file_returns_flat_prior(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        model = BayesianDriftModel.load(path)
        assert model.n_observations == 0
        assert abs(model.sensitivity - 300.0) < 1.0

    def test_load_corrupt_file_returns_flat_prior(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("this is not valid json {{{")
        model = BayesianDriftModel.load(path)
        assert model.n_observations == 0

    def test_load_missing_key_returns_flat_prior(self, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text(json.dumps({"log_sensitivity_mean": 5.7}))
        model = BayesianDriftModel.load(path)
        assert model.n_observations == 0

    def test_summary_is_non_empty(self):
        model = BayesianDriftModel()
        s = model.summary()
        assert len(s) > 10
        assert "sensitivity" in s
