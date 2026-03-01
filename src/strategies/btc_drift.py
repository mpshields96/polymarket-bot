"""
BTC 15-minute drift strategy — SECONDARY (paper-data collection only).

JOB:    Compare current BTC price to the BTC price when we first observed
        the market (the "reference"). A drift from the open implies an
        expected YES/NO price shift on Kalshi.  Return a Signal if edge
        clears the floor, or None to hold.

LOGIC:
    1. BTC feed is live and has a current price.
    2. Reference price is recorded on first observation of each market ticker.
    3. BTC has drifted > min_drift_pct from the reference.
    4. > min_minutes_remaining remain in the current 15-min window.
    5. Probability model (sigmoid + time-adjustment) gives edge > min_edge_pct.

PROBABILITY MODEL (adapted from refs/kalshi-btc/strategy.py BaselineHeuristicModel):
    pct_from_open = (btc_now - btc_ref) / btc_ref   (decimal, not %)
    raw_prob      = 1 / (1 + exp(-sensitivity * pct_from_open))
    time_factor   = 1.0 - time_remaining_frac        (0 at open, 1 at close)
    prob_yes      = 0.5 + (raw_prob - 0.5) * (1 - time_weight + time_weight * time_factor)

    Interpretation:
    - Positive drift → raw_prob > 0.5 → expect YES to be underpriced.
    - As market closes, time_factor → 1 and the probability anchors to raw_prob.
    - Early in the window, the model hedges toward 0.5 (uncertainty about direction).

WHY SEPARATE FROM BTC_LAG:
    btc_lag  fires on 60s MOMENTUM (rare in calm markets, needs ~0.65% BTC in 60s).
    btc_drift fires on DRIFT FROM OPEN (fires whenever BTC trends away from where
    it started, even gently). At min_drift_pct=0.05% and min_edge=5%, this fires
    roughly 10-20x more often than btc_lag on a typical BTC session.

Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot (strategy.py)
"""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market, OrderBook
from src.data.binance import BinanceFeed

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── Defaults (overridden by config.yaml strategy.btc_drift) ──────────

_DEFAULT_SENSITIVITY = 300.0        # Sigmoid steepness. At 300, 1% drift → P≈0.95
_DEFAULT_MIN_EDGE_PCT = 0.05        # Minimum net edge after fees (5%)
_DEFAULT_MIN_MINUTES_REMAINING = 3.0  # Don't enter with ≤ 3 min left
_DEFAULT_TIME_WEIGHT = 0.7          # How much time remaining adjusts confidence
_DEFAULT_MIN_DRIFT_PCT = 0.05       # BTC must have drifted ≥ 0.05% from open

# Price range guard — model was calibrated on near-50¢ markets.
# Outside 35–65¢, the market has priced in significant conviction; our edge shrinks
# and we're fighting HFT certainty. Tightened from 10–90 per Matthew 2026-03-01.
_MIN_SIGNAL_PRICE_CENTS = 35
_MAX_SIGNAL_PRICE_CENTS = 65

# Kalshi fee formula: 0.07 × P × (1 - P), where P is price in [0, 1]
# Source: https://kalshi.com/blog/fees


def _kalshi_fee_pct(price_cents: int) -> float:
    """Return fee as a fraction (e.g. 0.017 = 1.7%) given price in cents."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


class BTCDriftStrategy(BaseStrategy):
    """
    BTC drift-from-open strategy.

    Records the BTC price on first observation of each Kalshi market ticker.
    On subsequent evaluations, measures the drift from that reference and
    applies a sigmoid probability model adjusted for time remaining.

    This strategy is always paper-only (main.py enforces live_executor_enabled=False
    for the drift task). It exists to collect calibration data.
    """

    def __init__(
        self,
        sensitivity: float = _DEFAULT_SENSITIVITY,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        time_weight: float = _DEFAULT_TIME_WEIGHT,
        min_drift_pct: float = _DEFAULT_MIN_DRIFT_PCT,
        name_override: Optional[str] = None,
    ):
        self._sensitivity = sensitivity
        self._min_edge_pct = min_edge_pct
        self._min_minutes_remaining = min_minutes_remaining
        self._time_weight = time_weight
        self._min_drift_pct = min_drift_pct
        self._name_override = name_override
        # ticker → (ref_btc_price, minutes_into_window_when_observed)
        # minutes_into_window tells us how stale our reference is relative to market open.
        # 0 = observed right at open (ideal), 15 = observed at end of window (worthless).
        self._reference_prices: Dict[str, Tuple[float, float]] = {}

    @property
    def name(self) -> str:
        return self._name_override or "btc_drift_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed: BinanceFeed,
    ) -> Optional[Signal]:
        """
        Evaluate drift-from-open and return a Signal or None.

        This method is SYNCHRONOUS — no await here. All data is already fetched.
        """
        # ── 1. Check BTC feed health ───────────────────────────────────
        if btc_feed.is_stale:
            logger.debug("[btc_drift] BTC feed is stale — skip")
            return None

        current_btc = btc_feed.current_price()
        if current_btc is None:
            logger.debug("[btc_drift] No current BTC price — skip")
            return None

        # ── 2. Record reference price on first observation ────────────
        # Record the BTC price the first time we see each market ticker, plus
        # how many minutes into the 15-min window we observed it.
        # Minutes-into-window = 0 at market open (ideal), 15 at market close (useless).
        # When the bot restarts mid-window, minutes_late > 0 and we apply a
        # late-entry confidence penalty later so stale references don't look like
        # clean signals.
        if market.ticker not in self._reference_prices:
            minutes_late = self._minutes_since_open(market)
            self._reference_prices[market.ticker] = (current_btc, minutes_late)
            logger.debug(
                "[btc_drift] Reference set for %s: BTC=%.2f (%.1f min into window)",
                market.ticker, current_btc, minutes_late,
            )
            return None  # No reference yet → can't compute drift → hold

        ref_btc, minutes_late = self._reference_prices[market.ticker]
        if ref_btc <= 0:
            logger.debug("[btc_drift] Invalid reference price %.2f for %s — skip",
                         ref_btc, market.ticker)
            return None

        # ── 3. Compute drift from reference ────────────────────────────
        pct_from_open = (current_btc - ref_btc) / ref_btc  # decimal, e.g. 0.003 = 0.3%

        if abs(pct_from_open) < (self._min_drift_pct / 100.0):
            mins = self._minutes_remaining(market)
            time_str = f"{mins:.1f}min left" if mins is not None else "?min"
            logger.info(
                "[%s] %s: drift %+.3f%% from open (need ±%.3f%%) | YES=%d¢ NO=%d¢ | %s",
                self.name, market.ticker, pct_from_open * 100, self._min_drift_pct,
                market.yes_price, market.no_price, time_str,
            )
            return None

        # ── 4. Check time remaining ────────────────────────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None:
            logger.debug("[btc_drift] Cannot determine time remaining for %s — skip",
                         market.ticker)
            return None

        if minutes_remaining <= self._min_minutes_remaining:
            logger.debug(
                "[btc_drift] Only %.1f min remaining (need >%.1f) for %s — skip",
                minutes_remaining, self._min_minutes_remaining, market.ticker,
            )
            return None

        # ── 5. Compute time remaining fraction ────────────────────────
        time_remaining_frac = self._time_remaining_frac(market)
        # time_remaining_frac: 1.0 at market open, 0.0 at market close
        # time_factor: 0.0 at open, 1.0 at close
        time_factor = max(0.0, min(1.0, 1.0 - time_remaining_frac))

        # ── 6. Probabilistic model (sigmoid + time adjustment) ─────────
        # raw_prob is P(YES settles at 100) based solely on price drift direction
        raw_prob = 1.0 / (1.0 + math.exp(-self._sensitivity * pct_from_open))
        raw_prob = max(0.01, min(0.99, raw_prob))

        # Time-adjust: early in market → hedge toward 0.5 (uncertain outcome).
        # Late in market → anchor to raw_prob (drift is more likely final).
        blend = 1.0 - self._time_weight + self._time_weight * time_factor
        prob_yes = 0.5 + (raw_prob - 0.5) * blend
        prob_yes = max(0.01, min(0.99, prob_yes))

        # ── 7. Determine best side ────────────────────────────────────
        # Compare edge on both sides; take the better one
        fee_yes = _kalshi_fee_pct(market.yes_price)
        fee_no = _kalshi_fee_pct(market.no_price)
        edge_yes = prob_yes - (market.yes_price / 100.0) - fee_yes
        edge_no = (1.0 - prob_yes) - (market.no_price / 100.0) - fee_no

        if edge_yes >= edge_no and edge_yes >= self._min_edge_pct:
            side = "yes"
            price_cents = market.yes_price
            edge_pct = edge_yes
            win_prob = prob_yes
        elif edge_no > edge_yes and edge_no >= self._min_edge_pct:
            side = "no"
            price_cents = market.no_price
            edge_pct = edge_no
            win_prob = 1.0 - prob_yes
        else:
            logger.debug(
                "[btc_drift] %s: edge_yes=%.3f edge_no=%.3f both < min %.3f — skip",
                market.ticker, edge_yes, edge_no, self._min_edge_pct,
            )
            return None

        if price_cents <= 0 or price_cents >= 100:
            logger.debug("[btc_drift] Invalid %s price %d¢ for %s — skip",
                         side, price_cents, market.ticker)
            return None

        if price_cents < _MIN_SIGNAL_PRICE_CENTS or price_cents > _MAX_SIGNAL_PRICE_CENTS:
            logger.info("[btc_drift] Price %d¢ outside calibrated range (%d–%d¢) — skip %s",
                        price_cents, _MIN_SIGNAL_PRICE_CENTS, _MAX_SIGNAL_PRICE_CENTS, market.ticker)
            return None

        # win_prob must be above coin flip for a valid signal
        win_prob = max(0.51, min(0.99, win_prob))

        # Late-entry confidence penalty: if we first observed the market >2 min into
        # the 15-min window, our "drift" reference may not reflect the true market open.
        # Penalty linearly reduces confidence from 1.0 (on time) to 0.5 (very late).
        # No effect in the first 2 minutes; full penalty if we joined at minute 10+.
        late_penalty = max(0.5, 1.0 - max(0.0, minutes_late - 2.0) / 16.0)

        # Confidence: how far prob is from 0.5, scaled by time_factor and late_penalty
        confidence = min(1.0, abs(prob_yes - 0.5) * 2 * (0.3 + 0.7 * time_factor) * late_penalty)

        late_str = f" [ref +{minutes_late:.1f}min late]" if minutes_late > 2.0 else ""
        reason = (
            f"BTC drift {pct_from_open:+.3%} from ref {ref_btc:.2f}{late_str}, "
            f"P(YES)={prob_yes:.3f}, "
            f"edge_{side}={edge_pct:.1%}, "
            f"{minutes_remaining:.1f}min remaining"
        )

        logger.info(
            "[btc_drift] Signal: BUY %s @ %d¢ | %s",
            side.upper(), price_cents, reason,
        )

        return Signal(
            side=side,
            edge_pct=round(edge_pct, 4),
            win_prob=round(win_prob, 4),
            confidence=round(confidence, 4),
            ticker=market.ticker,
            price_cents=price_cents,
            reason=reason,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _minutes_remaining(market: Market) -> Optional[float]:
        """Return minutes remaining until market close, or None on parse error."""
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            remaining_sec = (close_dt - now_dt).total_seconds()
            return max(0.0, remaining_sec / 60.0)
        except Exception:
            return None

    @staticmethod
    def _minutes_since_open(market: Market) -> float:
        """
        Return minutes elapsed since the Kalshi market opened.

        This tells us how "late" we are in observing a market for the first time.
        If the bot restarts mid-window, this will be > 0 and we penalise confidence.
        Falls back to 0.0 (assume on-time) on parse error.
        """
        try:
            open_dt = datetime.fromisoformat(market.open_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            elapsed_sec = max(0.0, (now_dt - open_dt).total_seconds())
            return elapsed_sec / 60.0
        except Exception:
            return 0.0

    @staticmethod
    def _time_remaining_frac(market: Market) -> float:
        """
        Return fraction of market time remaining (1.0 at open, 0.0 at close).
        Falls back to 0.5 on parse error.
        """
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            open_dt = datetime.fromisoformat(market.open_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            total_sec = max(1.0, (close_dt - open_dt).total_seconds())
            remaining_sec = max(0.0, (close_dt - now_dt).total_seconds())
            return remaining_sec / total_sec
        except Exception:
            return 0.5


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> BTCDriftStrategy:
    """Build BTCDriftStrategy from config.yaml strategy.btc_drift section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using BTCDriftStrategy defaults")
        return BTCDriftStrategy()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    s = cfg.get("strategy", {}).get("btc_drift", {})
    return BTCDriftStrategy(
        sensitivity=s.get("sensitivity", _DEFAULT_SENSITIVITY),
        min_edge_pct=s.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=s.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        time_weight=s.get("time_weight", _DEFAULT_TIME_WEIGHT),
        min_drift_pct=s.get("min_drift_pct", _DEFAULT_MIN_DRIFT_PCT),
    )


def load_eth_drift_from_config() -> BTCDriftStrategy:
    """Build BTCDriftStrategy for ETH markets from config.yaml strategy.eth_drift section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using ETH drift defaults")
        return BTCDriftStrategy(name_override="eth_drift_v1")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # Fall back to btc_drift params if eth_drift section is absent
    s = cfg.get("strategy", {}).get("eth_drift") or cfg.get("strategy", {}).get("btc_drift", {})
    return BTCDriftStrategy(
        sensitivity=s.get("sensitivity", _DEFAULT_SENSITIVITY),
        min_edge_pct=s.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=s.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        time_weight=s.get("time_weight", _DEFAULT_TIME_WEIGHT),
        min_drift_pct=s.get("min_drift_pct", _DEFAULT_MIN_DRIFT_PCT),
        name_override="eth_drift_v1",
    )
