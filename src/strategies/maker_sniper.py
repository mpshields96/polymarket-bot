"""
Maker Sniper — Kalshi 15-min maker-side FLB variant.

JOB:    Same signal selection as expiry_sniper_v1 (FLB at 90-94c, last 14 min,
        coin drift in same direction), but executes as a POST-ONLY LIMIT ORDER
        placed 1c below the current ask price to capture taker fees as maker.

ACADEMIC BASIS:
    Becker (2026) — "Makers and Takers: Economics of the Kalshi Prediction Market"
    CESifo WP 12122 / CEPR DP20631
    Kalshi makers earn +1.12% structural excess return vs takers -1.12%.
    Post-2024 crypto contracts: maker edge widened to +2.5pp.
    Fee savings: ~5c/bet * 30 bets/day = ~45 USD/month pure fee capture.

KEY DIFFERENCES FROM expiry_sniper_v1:
    1. Ceiling: 94c max (vs expiry_sniper 100c). Spread is too narrow above 94c.
    2. Price: places at (ask - offset_cents), not at ask.
    3. Execution: post_only=True, 5-min auto-cancel (not immediate fill).
    4. Fill: ~40-60% estimated fill rate. Taker fallback if spread crosses.

PAPER PHASE:
    Paper-only during ramp-up (30 filled bets required before live evaluation).
    Paper simulates at maker_price (not taker price) for accurate fee calibration.
    Track fill_rate, time-to-fill, and WR vs expiry_sniper to validate edge.

LOOP PROTOCOL:
    Loop calls strategy.generate_signal(market, coin_drift_pct)
    → if signal: fetch orderbook
    → call strategy.compute_maker_adjustment(signal, orderbook)
    → if (maker_price, None): execute at maker_price with post_only=True
    → else: skip (spread too narrow or missing data)

CALIBRATION NOTE:
    Paper executor fills at maker_price (not ask). Real fill rates will be lower.
    30 paper fills needed to evaluate: fill_rate, WR, and time-to-fill distribution.
    Threshold for live promotion: fill_rate >= 40% AND WR matches expiry_sniper CI.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

from src.strategies.base import Signal
from src.strategies.expiry_sniper import ExpirySniperStrategy, _DEFAULT_TRIGGER_PRICE_CENTS
from src.platforms.kalshi import Market, OrderBook

logger = logging.getLogger(__name__)

# ── Maker-specific parameters ─────────────────────────────────────────────

# Ceiling: above 94c the bid-ask spread is typically 1c or less — not enough
# room to place a maker limit and still capture the FLB edge.
_DEFAULT_CEILING_PRICE_CENTS = 94

# Offset: place 1c below current ask. At 1c offset, estimated fill rate ~50%.
# At 2c offset, fill rate drops to ~25-35% — lower but more price improvement.
# Default 1c maximises fills during paper calibration.
_DEFAULT_OFFSET_CENTS = 1

# Auto-cancel unfilled maker orders after 5 minutes. Sniper window is 14 min,
# so 5-min expiry gives time for a second attempt if needed.
_DEFAULT_EXPIRY_SECONDS = 300

# Minimum spread required to place a maker order. Spread < 2c means our 1c offset
# would place the order at the same price as the best bid — effectively taker.
_DEFAULT_MIN_SPREAD_CENTS = 2

# Floor: same as expiry_sniper (90c). Bet placed at maker_price (ask - offset),
# so actual entry will be 90-1=89c minimum. Guard against going below 87c.
_MAKER_FLOOR_CENTS = 87


class MakerSniperStrategy(ExpirySniperStrategy):
    """
    Maker-side FLB sniper for Kalshi 15-min binary markets.

    Inherits expiry_sniper_v1's signal generation (FLB at 90-94c, last 14 min,
    coin drift filter). Adds ceiling check and maker-price computation.

    Paper-only during calibration. Main loop must use compute_maker_adjustment()
    to get the actual limit price before calling the executor.
    """

    # Paper calibration bet size (same as expiry_sniper)
    PAPER_CALIBRATION_USD: float = 0.50

    def __init__(
        self,
        ceiling_price_cents: int = _DEFAULT_CEILING_PRICE_CENTS,
        offset_cents: int = _DEFAULT_OFFSET_CENTS,
        expiry_seconds: int = _DEFAULT_EXPIRY_SECONDS,
        min_spread_cents: int = _DEFAULT_MIN_SPREAD_CENTS,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.ceiling_price_cents = ceiling_price_cents
        self.offset_cents = offset_cents
        self.expiry_seconds = expiry_seconds
        self.min_spread_cents = min_spread_cents

    @property
    def name(self) -> str:
        return "maker_sniper_v1"

    def generate_signal(
        self,
        market: Market,
        coin_drift_pct: float,
    ) -> Optional[Signal]:
        """
        Same FLB conditions as expiry_sniper_v1, plus ceiling check.

        Returns None if price > ceiling_price_cents (94c) — spread is too
        narrow at 95c+ for a maker offset to add value.
        """
        signal = super().generate_signal(market, coin_drift_pct)
        if signal is None:
            return None

        # ── Ceiling check: reject prices above 94c ────────────────────────
        # At 95c+ the bid-ask spread is typically 1c (95/5 book). There is no
        # room to place 1c below ask without crossing or landing at the bid.
        if signal.price_cents > self.ceiling_price_cents:
            logger.debug(
                "[maker_sniper] %s: price %dc > ceiling %dc — no maker room, skip",
                market.ticker, signal.price_cents, self.ceiling_price_cents,
            )
            return None

        return signal

    def compute_maker_adjustment(
        self,
        signal: Signal,
        orderbook: OrderBook,
    ) -> Tuple[Optional[int], Optional[str]]:
        """
        Compute maker limit price from current orderbook.

        Checks spread is wide enough (≥ min_spread_cents) and computes
        maker_price = ask - offset_cents.

        Args:
            signal:    FLB signal from generate_signal() (side, price_cents, etc.)
            orderbook: Current Kalshi order book (yes_bids, no_bids)

        Returns:
            (maker_price_cents, None)   — place maker order at this price
            (None, skip_reason)         — skip (spread too narrow, no data, etc.)
        """
        if signal.side == "yes":
            ask = orderbook.yes_ask()
            bid = orderbook.best_yes_bid()
        elif signal.side == "no":
            ask = orderbook.no_ask()
            bid = orderbook.best_no_bid()
        else:
            return None, f"unknown side: {signal.side}"

        # ── Data availability check ────────────────────────────────────────
        if ask is None or bid is None:
            logger.debug(
                "[maker_sniper] %s %s: orderbook missing (ask=%s bid=%s) — skip",
                signal.ticker, signal.side, ask, bid,
            )
            return None, "orderbook data missing"

        # ── Spread check ───────────────────────────────────────────────────
        spread_cents = ask - bid
        if spread_cents < self.min_spread_cents:
            logger.debug(
                "[maker_sniper] %s %s: spread=%dc < min=%dc — too narrow for maker, skip",
                signal.ticker, signal.side, spread_cents, self.min_spread_cents,
            )
            return None, f"spread {spread_cents}c < min {self.min_spread_cents}c"

        # ── Maker price calculation ────────────────────────────────────────
        maker_price = ask - self.offset_cents

        # ── Floor guard ────────────────────────────────────────────────────
        if maker_price < _MAKER_FLOOR_CENTS:
            logger.debug(
                "[maker_sniper] %s %s: maker_price=%dc < floor=%dc — skip",
                signal.ticker, signal.side, maker_price, _MAKER_FLOOR_CENTS,
            )
            return None, f"maker_price {maker_price}c below floor {_MAKER_FLOOR_CENTS}c"

        logger.debug(
            "[maker_sniper] %s %s: ask=%dc spread=%dc maker_price=%dc",
            signal.ticker, signal.side, ask, spread_cents, maker_price,
        )
        return maker_price, None
