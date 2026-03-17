"""
Tests for src/models/bayesian_settlement.py — Bayesian drift model wiring.

Tests apply_bayesian_update() — the helper that updates the posterior after
each settled LIVE drift bet in settlement_loop.

Coverage:
    - drift strategy → model.update() called with reconstructed drift_pct
    - non-drift strategy → model.update() NOT called
    - win_prob missing or at boundary → model.update() NOT called
    - drift_model=None → no crash
    - model.save() called after every successful update
    - all 4 drift strategies trigger the update
    - correct drift_pct math: logit(win_prob) / sensitivity
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from src.models.bayesian_drift import BayesianDriftModel
from src.models.bayesian_settlement import apply_bayesian_update, _DRIFT_STRATEGY_NAMES


# ── helpers ───────────────────────────────────────────────────────────────────


def _trade(strategy: str = "btc_drift_v1", side: str = "yes",
           win_prob: float = 0.7, is_paper: bool = False) -> dict:
    return {
        "id": 1,
        "strategy": strategy,
        "side": side,
        "win_prob": win_prob,
        "is_paper": int(is_paper),
        "price_cents": 60,
    }


# ── tests ─────────────────────────────────────────────────────────────────────


class TestApplyBayesianUpdateBasics:
    def test_none_model_does_not_raise(self):
        """drift_model=None → silently skip, no crash."""
        apply_bayesian_update(None, _trade(), won=True)  # must not raise

    def test_non_drift_strategy_skips_update(self):
        """expiry_sniper_v1 should never update the drift model."""
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="expiry_sniper_v1"), won=True)
        model.update.assert_not_called()
        model.save.assert_not_called()

    def test_btc_lag_strategy_skips_update(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="btc_lag_v1"), won=True)
        model.update.assert_not_called()

    def test_win_prob_zero_skips_update(self):
        """win_prob=0 would cause log(0) — must be skipped."""
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(win_prob=0.0), won=True)
        model.update.assert_not_called()

    def test_win_prob_one_skips_update(self):
        """win_prob=1 would cause log(inf) — must be skipped."""
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(win_prob=1.0), won=True)
        model.update.assert_not_called()

    def test_win_prob_none_skips_update(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(win_prob=None), won=True)
        model.update.assert_not_called()


class TestApplyBayesianUpdateSuccess:
    def test_btc_drift_calls_update_and_save(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="btc_drift_v1", win_prob=0.7), won=True)
        model.update.assert_called_once()
        model.save.assert_called_once()

    def test_eth_drift_calls_update_and_save(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="eth_drift_v1", win_prob=0.6), won=False)
        model.update.assert_called_once()
        model.save.assert_called_once()

    def test_sol_drift_calls_update_and_save(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="sol_drift_v1", win_prob=0.8), won=True)
        model.update.assert_called_once()

    def test_xrp_drift_calls_update_and_save(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(strategy="xrp_drift_v1", win_prob=0.55), won=False)
        model.update.assert_called_once()

    def test_correct_side_passed(self):
        """side="no" in trade → model.update(..., side="no", ...) called."""
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(side="no", win_prob=0.7), won=False)
        _, kwargs = model.update.call_args
        assert kwargs["side"] == "no"

    def test_correct_won_passed(self):
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        apply_bayesian_update(model, _trade(win_prob=0.6), won=False)
        _, kwargs = model.update.call_args
        assert kwargs["won"] is False

    def test_drift_pct_derived_from_win_prob(self):
        """
        drift_pct = logit(win_prob) / sensitivity.
        At win_prob=0.7, sensitivity=300: logit=0.847, drift_pct≈0.00282.
        """
        model = MagicMock(spec=BayesianDriftModel)
        model.sensitivity = 300.0
        win_prob = 0.7
        apply_bayesian_update(model, _trade(win_prob=win_prob), won=True)
        _, kwargs = model.update.call_args
        expected = math.log(win_prob / (1.0 - win_prob)) / 300.0
        assert abs(kwargs["drift_pct"] - expected) < 1e-9


class TestDriftStrategyNamesSet:
    def test_all_four_drift_strategies_recognised(self):
        assert "btc_drift_v1" in _DRIFT_STRATEGY_NAMES
        assert "eth_drift_v1" in _DRIFT_STRATEGY_NAMES
        assert "sol_drift_v1" in _DRIFT_STRATEGY_NAMES
        assert "xrp_drift_v1" in _DRIFT_STRATEGY_NAMES

    def test_non_drift_not_in_set(self):
        assert "expiry_sniper_v1" not in _DRIFT_STRATEGY_NAMES
        assert "btc_lag_v1" not in _DRIFT_STRATEGY_NAMES
