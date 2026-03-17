"""
Bayesian Drift Model — online posterior update for BTCDriftStrategy.

JOB:    After each settled live drift bet, update the posterior over the
        sigmoid parameters (intercept, slope/sensitivity). Over time, the
        posterior narrows around the true live-market parameters, replacing
        the static paper-calibrated values with live-validated ones.

BACKGROUND (academic basis):
    Jaakkola & Jordan (1997) — "A Variational Approach to Bayesian Logistic
    Regression Models and Their Extensions." AISTATS.
    Key result: a Gaussian approximation to the logistic regression posterior
    can be maintained analytically, updated via a simple closed-form rule.

    Simplified approach used here:
    - Prior: Gaussian over (log_sensitivity, intercept)
      log_sensitivity ~ N(log(300), sigma_s^2)   — centred on current value
      intercept       ~ N(0.0,      sigma_i^2)    — no intercept bias assumed
    - Observation model: each settled bet is P(win | drift) where
      P(win=YES | drift) = sigmoid(sensitivity * drift + intercept)
    - Update rule: MAP update via gradient descent on log-posterior (one step)
      This approximates the full Bayesian update without full MCMC.
    - Posterior mean = MAP estimate after all observations
    - Posterior variance = inverse negative Hessian at MAP (Fisher information)

WHY THIS MATTERS:
    The current BTCDriftStrategy uses sensitivity=300 calibrated on paper data.
    Live bets may reveal different dynamics (HFT hedging, market regime changes).
    After 30+ live bets this model will have a tighter posterior than the paper prior,
    making the predicted probability more accurate and Kelly sizing more appropriate.

    Quantitatively: if live bets show the market responds to 0.05% drift differently
    than paper predicted, the posterior intercept shifts and edge_pct adjusts
    automatically on the next bot restart.

STORAGE:
    data/drift_posterior.json — loaded at startup, updated after each settled bet.
    If file missing: use flat prior (paper-calibrated values as prior mean).

USAGE (in main.py settlement loop):
    from src.models.bayesian_drift import BayesianDriftModel
    _drift_model = BayesianDriftModel.load()
    # ... after settling a live drift bet:
    _drift_model.update(drift_pct=0.003, side="yes", won=True)
    _drift_model.save()

    # In BTCDriftStrategy.generate_signal() (optional override):
    posterior_sensitivity = _drift_model.posterior_sensitivity()
    posterior_intercept   = _drift_model.posterior_intercept()
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_POSTERIOR_PATH = PROJECT_ROOT / "data" / "drift_posterior.json"

# ── Prior hyperparameters ──────────────────────────────────────────────────
# Centred on current paper-calibrated values.
# log_sensitivity=log(300)≈5.70, intercept=0.0.
# Prior variance reflects uncertainty: sigma=1.0 on log scale allows 10x-fold
# variation in sensitivity before the prior strongly regularises the estimate.
_PRIOR_LOG_SENSITIVITY_MEAN: float = math.log(300.0)  # ~5.704
_PRIOR_LOG_SENSITIVITY_VAR: float = 1.0               # allows ~e^1 = 3x change
_PRIOR_INTERCEPT_MEAN: float = 0.0
_PRIOR_INTERCEPT_VAR: float = 0.25                    # ~0.5 probability units

# Learning rate for MAP gradient step (one step per observation)
_LEARNING_RATE: float = 0.05

# Minimum observations before posterior is used to override static parameters
_MIN_OBSERVATIONS_FOR_OVERRIDE: int = 30


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    exp_x = math.exp(x)
    return exp_x / (1.0 + exp_x)


def _log_sigmoid(x: float) -> float:
    """log(sigmoid(x)) — numerically stable."""
    if x >= 0:
        return -math.log(1.0 + math.exp(-x))
    return x - math.log(1.0 + math.exp(x))


class BayesianDriftModel:
    """
    Online MAP estimate of sigmoid parameters for the drift strategy.

    Parameters maintained:
        log_sensitivity: log of the sigmoid steepness (exponentiated for use)
        intercept:       bias term (positive = bullish bias, negative = bearish)

    The model tracks posterior mean and variance for each parameter, updated
    after each settled live drift bet via one gradient step on the log-posterior.
    """

    def __init__(
        self,
        log_sensitivity_mean: float = _PRIOR_LOG_SENSITIVITY_MEAN,
        log_sensitivity_var: float = _PRIOR_LOG_SENSITIVITY_VAR,
        intercept_mean: float = _PRIOR_INTERCEPT_MEAN,
        intercept_var: float = _PRIOR_INTERCEPT_VAR,
        n_observations: int = 0,
        n_wins: int = 0,
    ):
        self.log_sensitivity_mean = log_sensitivity_mean
        self.log_sensitivity_var = log_sensitivity_var
        self.intercept_mean = intercept_mean
        self.intercept_var = intercept_var
        self.n_observations = n_observations
        self.n_wins = n_wins

    @property
    def sensitivity(self) -> float:
        """Current MAP estimate of sensitivity (positive, e.g. 300)."""
        return math.exp(self.log_sensitivity_mean)

    @property
    def intercept(self) -> float:
        """Current MAP estimate of intercept."""
        return self.intercept_mean

    @property
    def win_rate(self) -> float:
        """Empirical win rate from all observations."""
        return self.n_wins / self.n_observations if self.n_observations > 0 else 0.0

    @property
    def posterior_uncertainty(self) -> float:
        """
        Combined posterior uncertainty (0=certain, 1=maximally uncertain).
        Used to scale fractional Kelly: bet less when uncertainty is high.
        """
        # Geometric mean of normalised variances relative to prior
        s_ratio = self.log_sensitivity_var / _PRIOR_LOG_SENSITIVITY_VAR
        i_ratio = self.intercept_var / _PRIOR_INTERCEPT_VAR
        return math.sqrt(s_ratio * i_ratio)

    @property
    def kelly_scale(self) -> float:
        """
        Fractional Kelly multiplier based on posterior uncertainty.
        Returns value in [0.25, 1.0].
        - At prior (0 observations): 1.0 (no reduction from Bayesian uncertainty alone)
        - As posterior narrows: approaches 1.0 (model is confident)
        - If posterior widens (bad data): approaches 0.25 (maximum conservatism)

        Note: this supplements, not replaces, the existing Kelly fraction from sizing.py.
        The existing sizing module already applies its own fraction — this is an additional
        multiplier for when the Bayesian model is actively disagreeing with live data.
        """
        uncertainty = self.posterior_uncertainty
        # Linearly map [0, 1] uncertainty to [1.0, 0.25] Kelly scale
        return max(0.25, 1.0 - 0.75 * uncertainty)

    def predict(self, drift_pct: float) -> float:
        """
        Predict P(YES wins | drift_pct) using current posterior mean.

        Args:
            drift_pct: BTC drift from open as decimal (e.g. 0.003 = 0.3% positive drift)

        Returns:
            float: P(YES) in [0.01, 0.99]
        """
        sensitivity = math.exp(self.log_sensitivity_mean)
        raw = _sigmoid(sensitivity * drift_pct + self.intercept_mean)
        return max(0.01, min(0.99, raw))

    def update(self, drift_pct: float, side: str, won: bool) -> None:
        """
        Update posterior after a settled drift bet.

        Args:
            drift_pct: BTC drift from open as decimal (positive = BTC up)
            side: "yes" or "no" (which side was bet)
            won: True if the bet won

        The observation is: we predicted P(YES=won) and the outcome was (side, won).
        Convert to: did the YES side win?
            yes_won = (side == "yes" and won) or (side == "no" and not won)
        Then update parameters toward maximising log P(yes_won | drift, params).
        """
        yes_won = (side == "yes" and won) or (side == "no" and not won)
        y = 1 if yes_won else 0  # target for logistic regression

        # Current parameter estimates
        s = math.exp(self.log_sensitivity_mean)
        b = self.intercept_mean

        # Forward pass
        logit = s * drift_pct + b
        p = _sigmoid(logit)

        # Gradient of log-likelihood w.r.t. logit
        # d/d_logit log P(y | logit) = y - sigmoid(logit)
        residual = y - p  # positive if we should move toward predicting y

        # Chain rule: d_logit/d_log_s = s * drift_pct (since s = exp(log_s))
        grad_log_s = residual * s * drift_pct
        grad_b = residual

        # Prior gradient (L2 regularisation toward prior mean)
        prior_grad_log_s = -(self.log_sensitivity_mean - _PRIOR_LOG_SENSITIVITY_MEAN) / _PRIOR_LOG_SENSITIVITY_VAR
        prior_grad_b = -(self.intercept_mean - _PRIOR_INTERCEPT_MEAN) / _PRIOR_INTERCEPT_VAR

        # MAP update: gradient of (log-likelihood + log-prior)
        total_grad_log_s = grad_log_s + prior_grad_log_s
        total_grad_b = grad_b + prior_grad_b

        # Gradient step
        self.log_sensitivity_mean += _LEARNING_RATE * total_grad_log_s
        self.intercept_mean += _LEARNING_RATE * total_grad_b

        # Variance update: decrease proportional to information gained
        # Hessian approximation: Fisher information for logistic = p*(1-p) per observation
        fisher = p * (1.0 - p)
        # Posterior precision update (variance = 1/precision)
        # new_precision = old_precision + fisher * effective_weight
        # Effective weight on log_sensitivity: (s * drift_pct)^2 (chain rule)
        eff_weight_s = (s * drift_pct) ** 2
        new_prec_s = 1.0 / self.log_sensitivity_var + fisher * eff_weight_s
        new_prec_b = 1.0 / self.intercept_var + fisher

        self.log_sensitivity_var = max(0.001, 1.0 / new_prec_s)
        self.intercept_var = max(0.001, 1.0 / new_prec_b)

        # Track empirical stats
        self.n_observations += 1
        if won:
            self.n_wins += 1

        logger.debug(
            "[bayesian_drift] Update: drift=%.3f%% side=%s won=%s y=%d "
            "p_predicted=%.3f residual=%.3f "
            "sensitivity=%.1f→%.1f intercept=%.4f→%.4f",
            drift_pct * 100, side, won, y, p, residual,
            s, math.exp(self.log_sensitivity_mean),
            b, self.intercept_mean,
        )

    def summary(self) -> str:
        """One-line summary for logging."""
        return (
            f"n={self.n_observations} WR={self.win_rate:.1%} "
            f"sensitivity={self.sensitivity:.1f} (prior={math.exp(_PRIOR_LOG_SENSITIVITY_MEAN):.0f}) "
            f"intercept={self.intercept:.4f} "
            f"uncertainty={self.posterior_uncertainty:.3f} "
            f"kelly_scale={self.kelly_scale:.2f}"
        )

    def should_override_static(self) -> bool:
        """True if we have enough observations to use posterior instead of static params."""
        return self.n_observations >= _MIN_OBSERVATIONS_FOR_OVERRIDE

    def to_dict(self) -> dict:
        return {
            "log_sensitivity_mean": self.log_sensitivity_mean,
            "log_sensitivity_var": self.log_sensitivity_var,
            "intercept_mean": self.intercept_mean,
            "intercept_var": self.intercept_var,
            "n_observations": self.n_observations,
            "n_wins": self.n_wins,
            # Derived fields for human readability
            "sensitivity": round(self.sensitivity, 2),
            "win_rate": round(self.win_rate, 4),
            "posterior_uncertainty": round(self.posterior_uncertainty, 4),
            "kelly_scale": round(self.kelly_scale, 4),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BayesianDriftModel":
        return cls(
            log_sensitivity_mean=d["log_sensitivity_mean"],
            log_sensitivity_var=d["log_sensitivity_var"],
            intercept_mean=d["intercept_mean"],
            intercept_var=d["intercept_var"],
            n_observations=d.get("n_observations", 0),
            n_wins=d.get("n_wins", 0),
        )

    def save(self, path: Path = DEFAULT_POSTERIOR_PATH) -> None:
        """Persist posterior to JSON. Called after each update."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.debug("[bayesian_drift] Saved posterior: %s", self.summary())

    @classmethod
    def load(cls, path: Path = DEFAULT_POSTERIOR_PATH) -> "BayesianDriftModel":
        """
        Load posterior from JSON. Returns flat prior if file not found.
        Safe to call at bot startup — never raises.
        """
        if not path.exists():
            logger.info(
                "[bayesian_drift] No posterior file at %s — using flat prior "
                "(sensitivity=%.0f, intercept=0.0)",
                path, math.exp(_PRIOR_LOG_SENSITIVITY_MEAN),
            )
            return cls()
        try:
            with open(path) as f:
                d = json.load(f)
            model = cls.from_dict(d)
            logger.info("[bayesian_drift] Loaded posterior: %s", model.summary())
            return model
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(
                "[bayesian_drift] Failed to load posterior from %s: %s — using flat prior",
                path, e,
            )
            return cls()
