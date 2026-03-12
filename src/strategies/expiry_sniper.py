"""
Expiry Sniper — Kalshi 15-min binary expiry sniping strategy.

JOB:    Enter a 15-min Kalshi binary in the LAST 14 minutes when YES or NO
        price reaches 90c+ and the underlying coin has moved >= 0.1% from
        window open in the SAME DIRECTION as the 90c side.

ACADEMIC BASIS:
    Favorite-longshot bias (Snowberg & Wolfers, CEPR):
    Humans systematically undervalue heavy favorites in binary outcomes.
    A 90c YES market closes at YES MORE than 90% of the time.
    Edge = the underpricing of near-certain outcomes.

SOURCE STRATEGY (V7 — processoverprofit.blog):
    triggerPoint   = 90c  — enter when YES or NO >= 90c
    triggerMinute  = 14   — only enter when <= 14 min remaining
    HARD_SKIP      = 5s   — skip final 5 seconds
    stop-loss      = None — start without (empirical data needed first)

OUR ENHANCEMENT (from Reddit commenter analysis):
    Require underlying coin moved >= 0.1% from window open IN SAME DIRECTION.
    Filters "stuck at 90c with no momentum" (market maker resting at 90c = noise).
    Maps to: min_drift_pct = 0.001 (0.1%)
    Direction consistency: positive drift → YES at 90c; negative drift → NO at 90c

KEY DIFFERENCE FROM btc_drift:
    btc_drift: price zone 35-65c (neutral), momentum signals
    expiry_sniper: price zone 87-100c (near-certain), harvest premium
    These two strategies almost NEVER conflict — opposite price zones.
    When btc_drift is blocked by price guard (bearish/bullish), expiry_sniper FIRES.

TIMING NOTE (Session 53/54 gotcha):
    Use close_time from Kalshi market object directly.
    seconds_remaining = (close_time_dt - now_utc).total_seconds()
    Do NOT use clock modulo arithmetic — it's unreliable at window boundaries.

KELLY NOTE (Session 53/54 gotcha):
    At exactly 90c with 90% win rate, Kelly fraction = 0 (breakeven).
    Until real win rate data exists from 30+ paper bets, do NOT use Kelly for sizing.
    Paper phase uses fixed PAPER_CALIBRATION_USD = 0.50 per bet.
    Once win rate data confirms >90%, Kelly will yield small positive fractions.

PAPER PHASE:
    live_executor_enabled = False (enforced in main.py)
    calibration_max_usd = 0.01 (micro-live cap when going live initially)
    Goal: 30 paper bets + Brier < 0.30 → live gate evaluation
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market

logger = logging.getLogger(__name__)

# ── V7 Parameters (processoverprofit.blog) ────────────────────────────────

_DEFAULT_TRIGGER_PRICE_CENTS = 90.0  # enter when YES or NO price >= this
_DEFAULT_MAX_SECONDS_REMAINING = 840  # 14 * 60 — only enter in last 14 min
_DEFAULT_HARD_SKIP_SECONDS = 5       # don't enter in final 5 seconds
_DEFAULT_MIN_DRIFT_PCT = 0.001       # 0.1% underlying coin move (commenter enhancement)

# Favorite-longshot bias premium: heavy favorites are systematically UNDERPRICED.
# At 90c, actual win rate is ~91% (1pp over price). At 95c, ~96%. At 97c, ~98%.
# Model: win_prob = min(0.99, entry_price_cents / 100.0 + WIN_PROB_PREMIUM)
# This scales naturally — at any trigger price, we assume 1pp underpricing.
# Actual data from paper trades will calibrate this over time.
# This is NOT used for sizing in paper phase — sizing uses PAPER_CALIBRATION_USD.
_WIN_PROB_PREMIUM = 0.01   # 1pp premium above market price (favorite-longshot bias estimate)


def _kalshi_fee_pct(price_cents: int) -> float:
    """Return Kalshi taker fee as fraction. Fee = 0.07 * P * (1-P)."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


class ExpirySniperStrategy(BaseStrategy):
    """
    Expiry sniping strategy for Kalshi 15-min binary markets.

    Targets near-expiry contracts where one side has reached 90c+ (near certainty),
    with underlying coin momentum confirming the direction.

    This is a PAPER-ONLY strategy during calibration phase.
    main.py enforces live_executor_enabled=False.
    """

    # Fixed paper bet size: Kelly is near-zero at 90c until win rate data exists.
    # Use 0.50 USD for all paper bets to build calibration data.
    PAPER_CALIBRATION_USD: float = 0.50

    def __init__(
        self,
        trigger_price_cents: float = _DEFAULT_TRIGGER_PRICE_CENTS,
        max_seconds_remaining: int = _DEFAULT_MAX_SECONDS_REMAINING,
        hard_skip_seconds: int = _DEFAULT_HARD_SKIP_SECONDS,
        min_drift_pct: float = _DEFAULT_MIN_DRIFT_PCT,
        name_override: Optional[str] = None,
    ):
        self._trigger_price_cents = trigger_price_cents
        self._max_seconds_remaining = max_seconds_remaining
        self._hard_skip_seconds = hard_skip_seconds
        self._min_drift_pct = min_drift_pct
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "expiry_sniper_v1"

    def generate_signal(
        self,
        market: Market,
        coin_drift_pct: float,
    ) -> Optional[Signal]:
        """
        Evaluate expiry sniping conditions and return a Signal or None.

        Args:
            market:         Current Kalshi market snapshot (yes_price, close_time, ...)
            coin_drift_pct: % move of underlying crypto since window open.
                            Positive = coin went UP. Negative = coin went DOWN.
                            Example: 0.002 = +0.2%, -0.003 = -0.3%

        Returns:
            Signal if ALL conditions are met, else None.
        """
        # ── 1. Compute time remaining from close_time ──────────────────
        # Use close_time directly — NOT clock modulo arithmetic (Session 53/54 gotcha).
        seconds_remaining = self._seconds_remaining(market)
        if seconds_remaining is None:
            logger.debug("[expiry_sniper] Cannot parse close_time for %s — skip", market.ticker)
            return None

        # ── 2. Time guard: only enter in last 14 min (840s) ───────────
        if seconds_remaining > self._max_seconds_remaining:
            logger.debug(
                "[expiry_sniper] %s: %.0fs remaining > %ds gate — too early",
                market.ticker, seconds_remaining, self._max_seconds_remaining,
            )
            return None

        # ── 3. Hard skip: skip final 5 seconds (settlement imminent) ──
        if seconds_remaining <= self._hard_skip_seconds:
            logger.debug(
                "[expiry_sniper] %s: %.0fs remaining — hard skip (<=5s)", market.ticker, seconds_remaining,
            )
            return None

        # ── 4. Coin drift magnitude check ─────────────────────────────
        if abs(coin_drift_pct) < self._min_drift_pct:
            logger.debug(
                "[expiry_sniper] %s: coin drift %.4f%% < min %.4f%% — skip (no momentum)",
                market.ticker, coin_drift_pct * 100, self._min_drift_pct * 100,
            )
            return None

        # ── 5. Determine which side is at trigger price ────────────────
        yes_price = market.yes_price
        no_price = market.no_price

        if yes_price >= self._trigger_price_cents:
            # YES side at 90c+: only valid if coin drifted UP (consistent direction)
            if coin_drift_pct <= 0:
                logger.debug(
                    "[expiry_sniper] %s: YES at %dc but coin DOWN (%.4f%%) — inconsistent, skip",
                    market.ticker, yes_price, coin_drift_pct * 100,
                )
                return None
            side = "yes"
            price_cents = yes_price
            # Favorite-longshot bias: win_prob = price + 1pp premium
            win_prob = min(0.99, yes_price / 100.0 + _WIN_PROB_PREMIUM)

        elif no_price >= self._trigger_price_cents:
            # NO side at 90c+: only valid if coin drifted DOWN (consistent direction)
            if coin_drift_pct >= 0:
                logger.debug(
                    "[expiry_sniper] %s: NO at %dc but coin UP (%.4f%%) — inconsistent, skip",
                    market.ticker, no_price, coin_drift_pct * 100,
                )
                return None
            side = "no"
            price_cents = no_price  # Store actual NO price (consistent with all strategies)
            # Favorite-longshot bias: win_prob = no_price + 1pp premium
            win_prob = min(0.99, no_price / 100.0 + _WIN_PROB_PREMIUM)

        else:
            # Neither side at trigger — neutral zone, skip
            logger.debug(
                "[expiry_sniper] %s: YES=%dc NO=%dc, neither >= %.0fc — skip",
                market.ticker, yes_price, no_price, self._trigger_price_cents,
            )
            return None

        # ── 6. Compute edge ────────────────────────────────────────────
        # Edge = win_prob - (entry_price/100) - fee
        # At 90c YES: fee = 0.07 * 0.90 * 0.10 = 0.0063
        # Edge at win_prob=0.91: 0.91 - 0.90 - 0.0063 = 0.0037 (small but positive)
        entry_price_cents = yes_price if side == "yes" else no_price
        fee = _kalshi_fee_pct(int(entry_price_cents))
        edge_pct = win_prob - (entry_price_cents / 100.0) - fee

        if edge_pct <= 0:
            logger.debug(
                "[expiry_sniper] %s: edge %.4f <= 0 at %dc — not profitable, skip",
                market.ticker, edge_pct, entry_price_cents,
            )
            return None

        # ── 7. Confidence based on price and time ─────────────────────
        # Higher price = more certainty. Less time = more certainty about outcome.
        price_confidence = min(1.0, (entry_price_cents - 87.0) / 13.0)  # 0 at 87c, 1 at 100c
        time_confidence = max(0.0, 1.0 - seconds_remaining / self._max_seconds_remaining)
        confidence = min(1.0, 0.5 * price_confidence + 0.5 * time_confidence)

        reason = (
            f"Expiry snipe: {side.upper()} @ {entry_price_cents}c "
            f"({coin_drift_pct:+.3%} coin drift) "
            f"| {seconds_remaining:.0f}s remaining "
            f"| est. win_prob={win_prob:.2f} edge={edge_pct:.4f}"
        )

        logger.info(
            "[expiry_sniper] Signal: BUY %s @ %dc | %s",
            side.upper(), entry_price_cents, reason,
        )

        return Signal(
            side=side,
            edge_pct=round(edge_pct, 4),
            win_prob=round(win_prob, 4),
            confidence=round(confidence, 4),
            ticker=market.ticker,
            price_cents=int(price_cents),
            reason=reason,
        )

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _seconds_remaining(market: Market) -> Optional[float]:
        """
        Return seconds until market close, derived from market.close_time.

        Uses close_time directly — NOT clock modulo arithmetic. More reliable at
        window boundaries and when bot restarts mid-window. (Session 53/54 gotcha)
        """
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            return max(0.0, (close_dt - now_dt).total_seconds())
        except Exception:
            return None


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> ExpirySniperStrategy:
    """Build ExpirySniperStrategy from config.yaml strategy.expiry_sniper section."""
    from pathlib import Path
    import yaml

    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using ExpirySniperStrategy defaults")
        return ExpirySniperStrategy()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    s = cfg.get("strategy", {}).get("expiry_sniper", {})
    return ExpirySniperStrategy(
        trigger_price_cents=s.get("trigger_price_cents", _DEFAULT_TRIGGER_PRICE_CENTS),
        max_seconds_remaining=s.get("max_seconds_remaining", _DEFAULT_MAX_SECONDS_REMAINING),
        hard_skip_seconds=s.get("hard_skip_seconds", _DEFAULT_HARD_SKIP_SECONDS),
        min_drift_pct=s.get("min_drift_pct", _DEFAULT_MIN_DRIFT_PCT),
    )
