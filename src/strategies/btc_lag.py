"""
BTC 15-minute lag strategy — PRIMARY strategy.

JOB:    Detect when BTC price moves on Binance and Kalshi hasn't caught up yet.
        Return a Signal to trade the lag, or None to hold.

LOGIC (all 4 must be true to generate a signal):
    1. BTC moved > min_btc_move_pct in the last btc_window_seconds
    2. Kalshi YES/NO price hasn't moved to match (gap > min_kalshi_lag_cents)
    3. > min_minutes_remaining remain in the current 15-min window
    4. Net edge (lag_pct - fee) > min_edge_pct (default 8%)

EDGE CALCULATION:
    implied_lag_cents = abs(btc_move_pct) * LAG_SENSITIVITY
    edge_pct          = (implied_lag_cents / 100) - kalshi_fee(price)
    win_prob          = min(0.85, current_price_pct + (implied_lag_cents / 100) * 0.8)
    # 0.8 multiplier: conservative — assume we capture only 80% of the implied lag

DOES NOT: Know about sizing, risk, order placement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market, OrderBook
from src.data.binance import BinanceFeed

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── Defaults (overridden by config.yaml) ─────────────────────────────

_DEFAULT_MIN_BTC_MOVE_PCT = 0.4      # BTC must move at least this % in window
_DEFAULT_MIN_LAG_CENTS = 5           # Kalshi must lag by at least this many cents
_DEFAULT_MIN_MINUTES_REMAINING = 5   # Don't enter with <= 5 min left
_DEFAULT_MIN_EDGE_PCT = 0.08         # Minimum edge after fees (8%)
_DEFAULT_LAG_SENSITIVITY = 15.0      # Cents of YES price implied per 1% BTC move
                                      # 0.4% BTC → 6¢ implied lag (tunable)

# Kalshi fee formula: 0.07 × P × (1 - P), where P is price in [0, 1]
# Source: https://kalshi.com/blog/fees

def _kalshi_fee_pct(price_cents: int) -> float:
    """Return fee as a fraction (e.g. 0.017 = 1.7%) given price in cents."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


class BTCLagStrategy(BaseStrategy):
    """
    BTC 15-minute price lag strategy.

    Watches for BTC moves on Binance that Kalshi markets haven't priced in yet.
    When the lag exceeds the minimum and edge clears the floor, generates a signal.
    """

    def __init__(
        self,
        min_btc_move_pct: float = _DEFAULT_MIN_BTC_MOVE_PCT,
        min_kalshi_lag_cents: int = _DEFAULT_MIN_LAG_CENTS,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        lag_sensitivity: float = _DEFAULT_LAG_SENSITIVITY,
    ):
        self._min_btc_move_pct = min_btc_move_pct
        self._min_kalshi_lag_cents = min_kalshi_lag_cents
        self._min_minutes_remaining = min_minutes_remaining
        self._min_edge_pct = min_edge_pct
        self._lag_sensitivity = lag_sensitivity

    @property
    def name(self) -> str:
        return "btc_lag_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed: BinanceFeed,
    ) -> Optional[Signal]:
        """
        Check all 4 conditions and return a Signal or None.

        This is SYNCHRONOUS — no await here. All data is already fetched.
        """
        # ── 1. Check BTC feed health ───────────────────────────────
        if btc_feed.is_stale:
            logger.debug("[btc_lag] BTC feed is stale — skip")
            return None

        btc_move = btc_feed.btc_move_pct()
        if btc_move is None:
            logger.debug("[btc_lag] Insufficient BTC price history — skip")
            return None

        if abs(btc_move) < self._min_btc_move_pct:
            logger.info(
                "[btc_lag] BTC move %+.3f%% (need ±%.2f%%) — waiting for signal",
                btc_move, self._min_btc_move_pct,
            )
            return None

        # ── 2. Determine trade direction from BTC move ─────────────
        # BTC moved UP → we expect YES to be underpriced → buy YES
        # BTC moved DOWN → we expect NO to be underpriced → buy NO
        btc_up = btc_move > 0
        side = "yes" if btc_up else "no"
        price_cents = market.yes_price if btc_up else market.no_price

        if price_cents <= 0 or price_cents >= 100:
            logger.debug("[btc_lag] Invalid %s price %d¢ — skip", side, price_cents)
            return None

        # ── 3. Check Kalshi lag ────────────────────────────────────
        # Implied move = how much YES/NO price SHOULD have moved given BTC's move
        # lag_sensitivity = cents of YES/NO change per 1% BTC move (tunable)
        implied_lag_cents = abs(btc_move) * self._lag_sensitivity

        if implied_lag_cents < self._min_kalshi_lag_cents:
            logger.debug(
                "[btc_lag] Implied lag %.1f¢ < min %d¢ — skip",
                implied_lag_cents, self._min_kalshi_lag_cents,
            )
            return None

        # ── 4. Check time remaining in market window ────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None:
            logger.debug("[btc_lag] Cannot determine time remaining — skip")
            return None

        if minutes_remaining <= self._min_minutes_remaining:
            logger.debug(
                "[btc_lag] Only %.1f min remaining (need >%d) — skip",
                minutes_remaining, self._min_minutes_remaining,
            )
            return None

        # ── 5. Compute edge ────────────────────────────────────────
        lag_pct = implied_lag_cents / 100.0
        fee_pct = _kalshi_fee_pct(price_cents)
        edge_pct = lag_pct - fee_pct

        if edge_pct < self._min_edge_pct:
            logger.debug(
                "[btc_lag] Edge %.3f (lag %.3f - fee %.3f) < min %.3f — skip",
                edge_pct, lag_pct, fee_pct, self._min_edge_pct,
            )
            return None

        # ── 6. Estimate win probability ────────────────────────────
        # Rough estimate: current price + implied lag, capped at 85%
        win_prob = min(0.85, (price_cents / 100.0) + lag_pct * 0.8)
        win_prob = max(0.51, win_prob)  # must be above coin flip

        # Confidence scaled by how much BTC moved beyond threshold
        move_excess = abs(btc_move) - self._min_btc_move_pct
        confidence = min(1.0, move_excess / 0.5)  # saturates at 0.5% excess

        reason = (
            f"BTC {btc_move:+.3f}% in 60s, "
            f"{side.upper()} lag ~{implied_lag_cents:.1f}¢, "
            f"edge {edge_pct:.1%}, "
            f"{minutes_remaining:.1f}min remaining"
        )

        logger.info("[btc_lag] Signal: BUY %s @ %d¢ | %s", side.upper(), price_cents, reason)

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


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> BTCLagStrategy:
    """Build BTCLagStrategy from config.yaml strategy.btc_lag section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using BTCLagStrategy defaults")
        return BTCLagStrategy()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    s = cfg.get("strategy", {}).get("btc_lag", {})
    return BTCLagStrategy(
        min_btc_move_pct=s.get("min_btc_move_pct", _DEFAULT_MIN_BTC_MOVE_PCT),
        min_kalshi_lag_cents=s.get("min_kalshi_lag_cents", _DEFAULT_MIN_LAG_CENTS),
        min_minutes_remaining=s.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        min_edge_pct=s.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        lag_sensitivity=s.get("lag_sensitivity", _DEFAULT_LAG_SENSITIVITY),
    )
