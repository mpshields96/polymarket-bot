"""
Economics Sniper — Kalshi KXCPI/KXGDP FLB sniping strategy.

JOB:    Enter Kalshi economics contracts (KXCPI-*/KXGDP-*) in the 24-48h window
        before settlement when YES or NO price reaches 88c+.

ACADEMIC BASIS:
    Favorite-longshot bias in Kalshi economics prediction markets.
    Burgi et al. (2026) [SSRN 5502658]: FLB strongest in 24-48h window pre-settlement.
    Economics markets have WEAKER FLB than crypto 15-min contracts — trigger=88c (vs 90c).
    CCA REQ-032 (2026-03-24): entry YES>=88c, 24-48h window, 0.5x Kelly.

KEY DIFFERENCE FROM ExpirySniperStrategy:
    expiry_sniper: 15-min crypto contracts, requires coin_drift_pct param, 14-min window
    economics_sniper: multi-day economics contracts, NO underlying asset, 24-48h window
    No coin_drift_pct needed — FLB is the only signal (price + time proximity to settlement).

TIMING (CCA REQ-032 clarification):
    Entry window: 24-48h before settlement close_time.
    Do NOT enter at 16+ days out — pre-release drift is a different mechanism (not FLB).
    Hard skip: 5 min (<300s) before close — settlement imminent, liquidity may be gone.

PAPER PHASE:
    live_executor_enabled = False
    calibration = 0.5x Kelly sizing (CCA recommendation for first 20 economics bets)
    PAPER_CALIBRATION_USD = 0.50 per bet during calibration
    Goal: 30 paper bets → evaluate before live promotion

GUARD:
    Ceiling = 94c (slippage to 95c at 94c entry; 95c+ historically negative, IL-blocked)
    Floor = 88c (FLB weaker for economics vs crypto, use conservative threshold)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market

logger = logging.getLogger(__name__)

# ── Parameters ────────────────────────────────────────────────────────

_DEFAULT_TRIGGER_PRICE_CENTS = 88.0   # FLB weaker for economics → lower threshold than 90c
_DEFAULT_MAX_SECONDS_REMAINING = 172800  # 48h — only enter in 48h window before close
_DEFAULT_HARD_SKIP_SECONDS = 300      # 5 min — economics settlement less time-sensitive

# Ceiling: 94c triggers slippage to 95c; 95c+ historically negative EV (IL-blocked)
_CEILING_PRICE_CENTS = 94

# FLB premium: 1pp above market price (same as expiry_sniper).
# Economics FLB uses lower 88c floor (vs 90c) to account for weaker bias,
# but the win_prob model still uses 1pp premium — validated by fee structure
# (at 88c, fee=0.007, 1pp premium leaves edge=0.003; 0.5pp would be negative).
_WIN_PROB_PREMIUM = 0.01   # 1pp premium above market price


def _kalshi_fee_pct(price_cents: int) -> float:
    """Return Kalshi taker fee as fraction. Fee = 0.07 * P * (1-P)."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


class EconomicsSniperStrategy(BaseStrategy):
    """
    FLB sniping strategy for Kalshi economics contracts (KXCPI-*, KXGDP-*).

    Fires in the 24-48h window before settlement when YES or NO price >= 88c.
    No underlying asset required — FLB is the sole signal.

    Paper-only during calibration. Ceiling at 94c (slippage guard).
    """

    PAPER_CALIBRATION_USD: float = 0.50

    def __init__(
        self,
        trigger_price_cents: float = _DEFAULT_TRIGGER_PRICE_CENTS,
        max_seconds_remaining: int = _DEFAULT_MAX_SECONDS_REMAINING,
        hard_skip_seconds: int = _DEFAULT_HARD_SKIP_SECONDS,
        name_override: Optional[str] = None,
    ):
        self._trigger_price_cents = trigger_price_cents
        self._max_seconds_remaining = max_seconds_remaining
        self._hard_skip_seconds = hard_skip_seconds
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "economics_sniper_v1"

    def generate_signal(self, market: Market) -> Optional[Signal]:
        """
        Evaluate economics FLB sniping conditions and return a Signal or None.

        Args:
            market: Current Kalshi market snapshot (yes_price, no_price, close_time, ticker)

        Returns:
            Signal if ALL conditions are met, else None.
        """
        # ── 1. Compute time remaining ──────────────────────────────────
        seconds_remaining = self._seconds_remaining(market)
        if seconds_remaining is None:
            logger.debug("[economics_sniper] Cannot parse close_time for %s — skip", market.ticker)
            return None

        # ── 2. Time gate: only enter in last 48h (172800s) ────────────
        if seconds_remaining > self._max_seconds_remaining:
            logger.debug(
                "[economics_sniper] %s: %.0fs remaining > %ds gate (48h) — too early",
                market.ticker, seconds_remaining, self._max_seconds_remaining,
            )
            return None

        # ── 3. Hard skip: avoid final 5 min (settlement imminent) ─────
        if seconds_remaining <= self._hard_skip_seconds:
            logger.debug(
                "[economics_sniper] %s: %.0fs remaining — hard skip (<=300s)", market.ticker, seconds_remaining,
            )
            return None

        # ── 4. Determine which side is at trigger price ────────────────
        yes_price = market.yes_price
        no_price = market.no_price

        if yes_price >= self._trigger_price_cents and yes_price < _CEILING_PRICE_CENTS:
            side = "yes"
            price_cents = yes_price
            win_prob = min(0.99, yes_price / 100.0 + _WIN_PROB_PREMIUM)

        elif no_price >= self._trigger_price_cents and no_price < _CEILING_PRICE_CENTS:
            side = "no"
            price_cents = no_price
            win_prob = min(0.99, no_price / 100.0 + _WIN_PROB_PREMIUM)

        else:
            # Neither side in range (below floor or above ceiling)
            logger.debug(
                "[economics_sniper] %s: YES=%dc NO=%dc, neither in [%.0fc, %dc) — skip",
                market.ticker, yes_price, no_price, self._trigger_price_cents, _CEILING_PRICE_CENTS,
            )
            return None

        # ── 5. Compute edge ────────────────────────────────────────────
        fee = _kalshi_fee_pct(int(price_cents))
        edge_pct = win_prob - (price_cents / 100.0) - fee

        if edge_pct <= 0:
            logger.debug(
                "[economics_sniper] %s: edge %.4f <= 0 at %dc — not profitable, skip",
                market.ticker, edge_pct, price_cents,
            )
            return None

        # ── 6. Build reason ────────────────────────────────────────────
        hours_remaining = seconds_remaining / 3600.0
        reason = (
            f"FLB economics snipe: {side.upper()} @ {price_cents}c "
            f"| {hours_remaining:.1f}h to settlement "
            f"| est. win_prob={win_prob:.3f} edge={edge_pct:.4f}"
        )

        logger.info(
            "[economics_sniper] Signal: BUY %s @ %dc | %s",
            side.upper(), price_cents, reason,
        )

        # ── 7. Confidence (price proximity + time proximity) ──────────
        price_confidence = min(1.0, (price_cents - 87.0) / 7.0)  # 0 at 87c, 1 at 94c
        time_confidence = max(0.0, 1.0 - seconds_remaining / self._max_seconds_remaining)
        confidence = min(1.0, 0.5 * price_confidence + 0.5 * time_confidence)

        return Signal(
            side=side,
            edge_pct=round(edge_pct, 4),
            win_prob=round(win_prob, 4),
            confidence=round(confidence, 4),
            ticker=market.ticker,
            price_cents=int(price_cents),
            reason=reason,
            features={
                "utc_hour": datetime.now(timezone.utc).hour,
                "seconds_remaining": round(seconds_remaining, 1),
                "hours_remaining": round(hours_remaining, 2),
            },
        )

    @staticmethod
    def _seconds_remaining(market: Market) -> Optional[float]:
        """Return seconds until market close, derived from market.close_time."""
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            return max(0.0, (close_dt - now_dt).total_seconds())
        except Exception:
            return None


# ── Factory ───────────────────────────────────────────────────────────

def make_economics_sniper(
    trigger_price_cents: float = _DEFAULT_TRIGGER_PRICE_CENTS,
    max_seconds_remaining: int = _DEFAULT_MAX_SECONDS_REMAINING,
    hard_skip_seconds: int = _DEFAULT_HARD_SKIP_SECONDS,
) -> EconomicsSniperStrategy:
    """Create a default EconomicsSniperStrategy instance."""
    return EconomicsSniperStrategy(
        trigger_price_cents=trigger_price_cents,
        max_seconds_remaining=max_seconds_remaining,
        hard_skip_seconds=hard_skip_seconds,
    )
