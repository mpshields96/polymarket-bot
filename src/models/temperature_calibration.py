"""
Per-strategy temperature calibration for drift signal win probabilities.

Motivation (Session 107 research — 2026-03-18):
    Statistical analysis of 307 live drift bets revealed systematic calibration
    overconfidence for ETH, BTC, and XRP drift strategies:

    Strategy    n     Predicted WR    Actual WR    Error    p-value
    eth_drift   149   54.8%           46.3%        -8.5pp   0.015  ← significant
    btc_drift    68   57.0%           48.5%        -8.5pp   0.063  ← borderline
    xrp_drift    47   61.0%           48.9%       -12.1pp   0.033  ← significant
    sol_drift    43   65.3%           69.8%        +4.4pp   0.325  ← well-calibrated

    The shared Bayesian model (single posterior for all 4 strategies) cannot
    individually calibrate each strategy because SOL (70% WR) and ETH/BTC/XRP
    (~46-49% WR) have fundamentally different signal qualities. SOL inflates the
    shared posterior while ETH/BTC/XRP remain uncorrected.

Academic basis:
    Platt (1999) "Probabilistic Outputs for Support Vector Machines" — temperature
    scaling as a post-hoc calibration layer applied to classifier outputs.
    Guo et al. (2017) "On Calibration of Modern Neural Networks" — temperature
    scaling is the simplest and most effective single-parameter calibration method.

Method:
    T_s = sum_actual_excess / sum_predicted_excess  (running OLS estimate)
    where excess = value - 0.5

    corrected_win_prob = 0.5 + (win_prob - 0.5) * T_s

    T_s > 1: model underpredicts (e.g. sol_drift) → boost win_prob slightly
    T_s < 1: model overpredicts (e.g. eth_drift) → shrink win_prob toward 50%
    T_s = 1: no correction needed (default until MIN_OBSERVATIONS met)

Self-improving:
    update() is called from bayesian_settlement.py after each live drift bet.
    T_s converges toward the true calibration ratio automatically.
    State persists to data/calibration.json between restarts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Minimum live bets before applying temperature correction.
# Below this threshold T_s = 1.0 (no correction — insufficient data).
MIN_OBSERVATIONS: int = 20

# Clamp T_s to [T_MIN, T_MAX] to prevent extreme corrections.
_T_MIN: float = 0.5
_T_MAX: float = 2.0

_DEFAULT_PATH: Path = Path(__file__).parent.parent.parent / "data" / "calibration.json"


class StrategyCalibrator:
    """
    Per-strategy temperature scaling calibrator.

    Tracks running sum of predicted excess and actual excess per strategy,
    computes T_s = actual_excess / predicted_excess as a running OLS estimate,
    and applies it as a post-hoc correction to win_prob predictions.

    Thread-safety: NOT thread-safe. Intended for single-threaded use inside
    the asyncio settlement loop.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path: Path = path if path is not None else _DEFAULT_PATH
        # {strategy_name: {"n": int, "sum_pred": float, "sum_actual": float}}
        self._data: dict[str, dict[str, float]] = {}
        self._load()

    # ── Public API ────────────────────────────────────────────────────────

    def update(self, strategy: str, win_prob: float, won: bool) -> None:
        """
        Update calibration after a live drift bet settles.

        Args:
            strategy: strategy name (e.g. "btc_drift_v1")
            win_prob: the win probability predicted at bet time (0..1)
            won:      True if the bet won
        """
        if strategy not in self._data:
            self._data[strategy] = {"n": 0, "sum_pred": 0.0, "sum_actual": 0.0}

        pred_excess = win_prob - 0.5
        actual_excess = (1.0 if won else 0.0) - 0.5  # +0.5 or -0.5

        d = self._data[strategy]
        d["n"] += 1
        d["sum_pred"] += pred_excess
        d["sum_actual"] += actual_excess

        self._save()
        logger.debug(
            "[calibration] %s updated (n=%d): T=%.3f",
            strategy, d["n"], self.temperature(strategy),
        )

    def temperature(self, strategy: str) -> float:
        """
        Return T_s for the given strategy.

        Returns 1.0 (no correction) if:
          - strategy has no data
          - n < MIN_OBSERVATIONS
          - sum_predicted_excess is near zero (degenerate case)

        Returns T_s clamped to [T_MIN, T_MAX] otherwise.
        """
        d = self._data.get(strategy)
        if d is None or d["n"] < MIN_OBSERVATIONS:
            return 1.0

        sum_pred = d["sum_pred"]
        if abs(sum_pred) < 1e-6:
            return 1.0

        T = d["sum_actual"] / sum_pred
        return max(_T_MIN, min(_T_MAX, T))

    def apply(self, strategy: str, win_prob: float) -> float:
        """
        Apply temperature correction to win_prob.

        Returns corrected_win_prob = 0.5 + (win_prob - 0.5) * T_s,
        clamped to [0.01, 0.99].

        If T_s = 1.0 (insufficient data or well-calibrated), returns win_prob
        unchanged.
        """
        T = self.temperature(strategy)
        if T == 1.0:
            return win_prob
        corrected = 0.5 + (win_prob - 0.5) * T
        return max(0.01, min(0.99, corrected))

    def summary(self, strategy: str) -> str:
        """Return a human-readable summary for the given strategy."""
        d = self._data.get(strategy)
        if d is None:
            return f"[{strategy}] no data"
        T = self.temperature(strategy)
        return (
            f"[{strategy}] n={d['n']} "
            f"sum_pred={d['sum_pred']:.3f} sum_actual={d['sum_actual']:.3f} "
            f"T={T:.3f}"
        )

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self) -> None:
        """Load calibration data from JSON. Silently initialises empty on error."""
        try:
            if self._path.exists():
                raw = json.loads(self._path.read_text())
                self._data = raw.get("strategies", {})
        except Exception as exc:
            logger.warning(
                "[calibration] Failed to load %s (%s) — starting empty",
                self._path, exc,
            )
            self._data = {}

    def _save(self) -> None:
        """Persist calibration data to JSON. Logs warning on failure."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps({"strategies": self._data}, indent=2))
        except Exception as exc:
            logger.warning("[calibration] Failed to save %s: %s", self._path, exc)
