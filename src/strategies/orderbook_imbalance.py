"""
Orderbook imbalance strategy — detects informed trading via bid depth asymmetry.

JOB:    When YES bid depth significantly exceeds NO bid depth (or vice versa),
        this signals informed traders betting on one side. Generate a signal
        in that direction if edge clears the floor.

LOGIC (VPIN-lite — simplified Probability of Informed Trading):
    1. Compute depth-weighted imbalance = yes_depth / (yes_depth + no_depth)
       where depth = sum of quantities across the top N price levels.
    2. If imbalance > min_imbalance_ratio  (default 0.65) → buy YES
    3. If imbalance < 1 - min_imbalance_ratio (default 0.35) → buy NO
    4. Edge = abs(imbalance - 0.5) * 2 * scaling_factor - fee

KEY INSIGHT (from PIN model, Easley et al. 1996):
    In financial markets, large bid imbalance signals informed traders who
    know the outcome. For Kalshi binary contracts, a YES bid depth > NO bid
    depth means the crowd (or informed traders) is expecting YES to win.
    The more extreme the imbalance, the stronger the signal.

DOES NOT: Use BTC price feed (pure market microstructure signal).
          This works on ANY Kalshi market — BTC, ETH, weather, economic data.

PAPER-ONLY: Runs as calibration data collection. Not live until validated.

Adapted from:
  - vortexpixelz/Kalshi-smart-money (VPIN/PIN implementation)
  - refs/kalshi-btc/strategy.py (ModelFeatures yes_bid_depth / no_bid_depth)
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

# ── Defaults (overridden by config.yaml strategy.orderbook_imbalance) ─

_DEFAULT_MIN_IMBALANCE_RATIO = 0.65  # >65% YES depth → buy YES signal
_DEFAULT_MIN_TOTAL_DEPTH = 50        # Skip if total bid depth < 50 contracts
_DEFAULT_DEPTH_TOP_N = 10            # Consider top N price levels only
_DEFAULT_MIN_EDGE_PCT = 0.05         # 5% edge required after fees
_DEFAULT_MIN_MINUTES_REMAINING = 3.0
_DEFAULT_SIGNAL_SCALING = 1.0        # Scale imbalance→prob mapping (1.0 = linear)


def _kalshi_fee_pct(price_cents: int) -> float:
    """Return fee as a fraction (e.g. 0.017 = 1.7%) given price in cents."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


class OrderbookImbalanceStrategy(BaseStrategy):
    """
    VPIN-lite orderbook imbalance strategy.

    Measures the ratio of YES bid depth to total bid depth. A high ratio
    means the market is heavily skewed toward YES — smart money signal.
    Works on any Kalshi market; does not require a price feed.

    Imbalance = yes_depth / (yes_depth + no_depth)
    - imbalance > min_imbalance_ratio  → BUY YES
    - imbalance < 1 - min_imbalance_ratio → BUY NO
    - otherwise → HOLD

    Probability estimate: scaled from [0.5 to 1.0] based on imbalance.
    Edge = estimated_prob - market_price - fee.
    """

    def __init__(
        self,
        min_imbalance_ratio: float = _DEFAULT_MIN_IMBALANCE_RATIO,
        min_total_depth: int = _DEFAULT_MIN_TOTAL_DEPTH,
        depth_top_n: int = _DEFAULT_DEPTH_TOP_N,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        signal_scaling: float = _DEFAULT_SIGNAL_SCALING,
        name_override: Optional[str] = None,
    ):
        self._min_imbalance_ratio = min_imbalance_ratio
        self._min_total_depth = min_total_depth
        self._depth_top_n = depth_top_n
        self._min_edge_pct = min_edge_pct
        self._min_minutes_remaining = min_minutes_remaining
        self._signal_scaling = signal_scaling
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "orderbook_imbalance_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed: BinanceFeed,  # accepted but NOT used — pure microstructure signal
    ) -> Optional[Signal]:
        """
        Evaluate orderbook imbalance and return a Signal or None.

        SYNCHRONOUS — no await. All data is already fetched.
        """
        # ── 1. Check time remaining ────────────────────────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None:
            logger.debug("[%s] Cannot determine time remaining for %s — skip",
                         self.name, market.ticker)
            return None

        if minutes_remaining <= self._min_minutes_remaining:
            logger.debug("[%s] Only %.1f min left (need >%.1f) — skip",
                         self.name, minutes_remaining, self._min_minutes_remaining)
            return None

        # ── 2. Compute depth imbalance ─────────────────────────────────
        yes_depth = sum(
            level.quantity
            for level in orderbook.yes_bids[: self._depth_top_n]
        )
        no_depth = sum(
            level.quantity
            for level in orderbook.no_bids[: self._depth_top_n]
        )
        total_depth = yes_depth + no_depth

        if total_depth < self._min_total_depth:
            logger.debug(
                "[%s] %s: total depth %d < min %d — skip",
                self.name, market.ticker, total_depth, self._min_total_depth,
            )
            return None

        imbalance = yes_depth / total_depth  # [0, 1]: 1.0 = all YES bids

        # ── 3. Near-miss INFO log ──────────────────────────────────────
        reverse_threshold = 1.0 - self._min_imbalance_ratio
        if reverse_threshold <= imbalance <= self._min_imbalance_ratio:
            time_str = f"{minutes_remaining:.1f}min left"
            logger.info(
                "[%s] %s: imbalance %.2f (need >%.2f or <%.2f) | YES=%d¢ NO=%d¢ depth=%d | %s",
                self.name, market.ticker, imbalance,
                self._min_imbalance_ratio, reverse_threshold,
                market.yes_price, market.no_price, total_depth, time_str,
            )
            return None

        # ── 4. Determine direction ─────────────────────────────────────
        if imbalance >= self._min_imbalance_ratio:
            side = "yes"
            price_cents = market.yes_price
            # Scale imbalance→probability: 0.65→~0.57, 0.80→~0.70, 1.0→1.0
            # Uses linear scale from imbalance_threshold (= 0.5 prob) to 1.0 (= 1.0 prob)
            prob_yes = 0.5 + (imbalance - self._min_imbalance_ratio) / (
                1.0 - self._min_imbalance_ratio
            ) * 0.5 * self._signal_scaling
        else:
            # imbalance < reverse_threshold → heavy NO bidding → buy NO
            side = "no"
            price_cents = market.no_price
            no_imbalance = 1.0 - imbalance  # flip to make it analogous
            prob_yes = 1.0 - (0.5 + (no_imbalance - self._min_imbalance_ratio) / (
                1.0 - self._min_imbalance_ratio
            ) * 0.5 * self._signal_scaling)

        prob_yes = max(0.51, min(0.99, prob_yes))

        if price_cents <= 0 or price_cents >= 100:
            logger.debug("[%s] Invalid %s price %d¢ for %s — skip",
                         self.name, side, price_cents, market.ticker)
            return None

        # ── 5. Compute edge ────────────────────────────────────────────
        fee = _kalshi_fee_pct(price_cents)
        if side == "yes":
            edge_pct = prob_yes - (price_cents / 100.0) - fee
            win_prob = prob_yes
        else:
            edge_pct = (1.0 - prob_yes) - (price_cents / 100.0) - fee
            win_prob = 1.0 - prob_yes

        if edge_pct < self._min_edge_pct:
            logger.debug(
                "[%s] %s: edge %.3f < min %.3f (imb=%.3f) — skip",
                self.name, market.ticker, edge_pct, self._min_edge_pct, imbalance,
            )
            return None

        win_prob = max(0.51, min(0.99, win_prob))
        confidence = min(1.0, abs(imbalance - 0.5) * 2)  # 0 at neutral, 1 at extreme

        reason = (
            f"Orderbook imbalance {imbalance:.3f} "
            f"(YES depth {yes_depth} vs NO depth {no_depth}), "
            f"edge_{side}={edge_pct:.1%}, "
            f"{minutes_remaining:.1f}min remaining"
        )

        logger.info(
            "[%s] Signal: BUY %s @ %d¢ | %s",
            self.name, side.upper(), price_cents, reason,
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


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config(name_override: Optional[str] = None) -> OrderbookImbalanceStrategy:
    """Build OrderbookImbalanceStrategy from config.yaml strategy.orderbook_imbalance section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using OrderbookImbalanceStrategy defaults")
        return OrderbookImbalanceStrategy(name_override=name_override)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    s = cfg.get("strategy", {}).get("orderbook_imbalance", {})
    return OrderbookImbalanceStrategy(
        min_imbalance_ratio=s.get("min_imbalance_ratio", _DEFAULT_MIN_IMBALANCE_RATIO),
        min_total_depth=s.get("min_total_depth", _DEFAULT_MIN_TOTAL_DEPTH),
        depth_top_n=s.get("depth_top_n", _DEFAULT_DEPTH_TOP_N),
        min_edge_pct=s.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=s.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        signal_scaling=s.get("signal_scaling", _DEFAULT_SIGNAL_SCALING),
        name_override=name_override,
    )


def load_btc_imbalance_from_config() -> OrderbookImbalanceStrategy:
    """Convenience factory for BTC market imbalance strategy."""
    return load_from_config(name_override=None)  # uses default "orderbook_imbalance_v1"


def load_eth_imbalance_from_config() -> OrderbookImbalanceStrategy:
    """Convenience factory for ETH market imbalance strategy."""
    return load_from_config(name_override="eth_orderbook_imbalance_v1")
