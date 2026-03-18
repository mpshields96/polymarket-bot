"""
Bayesian settlement helper — wires BayesianDriftModel and StrategyCalibrator
updates into the settlement loop after each live drift bet settles.

Extracted from main.py into its own module for clean testability.
"""

from __future__ import annotations

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)

# Strategy names that feed the Bayesian drift posterior and temperature calibrator.
# Sniper / lag / imbalance bets are excluded — different signal model.
_DRIFT_STRATEGY_NAMES: frozenset[str] = frozenset([
    "btc_drift_v1",
    "eth_drift_v1",
    "sol_drift_v1",
    "xrp_drift_v1",
])


def apply_bayesian_update(drift_model, trade: dict, won: bool,
                          calibrator=None) -> None:
    """
    Update the Bayesian drift posterior (and temperature calibrator) after a
    settled live drift bet.

    Called from settlement_loop for LIVE drift bets only (paper trades are
    excluded upstream by the `if not trade["is_paper"]:` guard).

    Args:
        drift_model: BayesianDriftModel instance, or None (model not loaded).
        trade:       settled trade dict from db.get_open_trades()
        won:         True if the bet's side matched the market result
        calibrator:  StrategyCalibrator instance, or None (skip calibration update)

    Reconstructs drift_pct from stored win_prob via sigmoid inversion:
        logit = log(win_prob / (1 - win_prob))
        drift_pct ≈ logit / sensitivity
    This avoids a DB schema change while still providing informative updates
    to both the intercept and the sensitivity parameters.
    """
    strategy = trade.get("strategy", "")
    if strategy not in _DRIFT_STRATEGY_NAMES:
        return

    win_prob = trade.get("win_prob") or 0.0
    if win_prob <= 0.0 or win_prob >= 1.0:
        return

    # ── 1. Update Bayesian posterior ──────────────────────────────────────
    if drift_model is not None:
        logit = math.log(win_prob / (1.0 - win_prob))
        drift_pct = logit / drift_model.sensitivity

        drift_model.update(drift_pct=drift_pct, side=trade["side"], won=won)
        drift_model.save()
        logger.debug(
            "[bayesian] Updated posterior after %s trade #%d (side=%s won=%s drift_pct=%.4f) — %s",
            strategy, trade.get("id", "?"), trade["side"], won, drift_pct,
            drift_model.summary(),
        )

    # ── 2. Update per-strategy temperature calibrator ─────────────────────
    if calibrator is not None:
        calibrator.update(strategy=strategy, win_prob=win_prob, won=won)
        logger.debug(
            "[calibration] %s", calibrator.summary(strategy),
        )
