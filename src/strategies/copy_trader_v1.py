"""
Whale copy trading strategy for Polymarket.

JOB:    Evaluate individual whale trades and return a copy-trade Signal when
        the trade passes all decoy filters. One file, one job.

DOES NOT: Fetch data (whale_watcher.py does that), execute orders, know about
          sizing, risk, or which wallets to watch (main loop's responsibility).

Decoy filter logic (documented "Copytrade Wars" research):
  Genuine signal = ALL of:
  1. BUY only (never copy sells — selling could be profit-take or reversal trap)
  2. size >= min_trade_size_usd ($200 default — real conviction threshold)
  3. entry price in [min_whale_price, max_whale_price] (5-95¢ — extreme prices = decoys)
  4. trade age in [min_position_age_sec, max_trade_age_sec] (15 min–1 hr window)
  5. outcome is "Yes" or "No" (skip exotic outcomes)
  6. whale still holds matching open position (position confirmation = decoy ruled out)

Edge assignment by smart_score tier (from predicting.top leaderboard):
  - smart_score >= 80 → 8% edge  (high conviction copy)
  - smart_score >= 60 → 5% edge  (medium conviction copy)
  - smart_score < 60  → 3% edge  (low conviction copy)

Signal.ticker = trade.condition_id  (Polymarket market identifier)
Signal.price_cents = current market price for our side (where we'll execute)
Signal.win_prob = trade.price for YES signals; 1.0 - trade.price for NO signals
                  (whale's entry is their implied fair value estimate)
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.data.whale_watcher import WhaleTrade, WhalePosition
from src.strategies.base import Signal

logger = logging.getLogger(__name__)

_HIGH_SMART_SCORE = 80.0
_MID_SMART_SCORE = 60.0
_EDGE_HIGH = 0.08
_EDGE_MID = 0.05
_EDGE_LOW = 0.03


class CopyTraderStrategy:
    """
    Evaluate a whale trade and emit a copy-trade Signal if genuine.

    Paper-only until POST /v1/orders protobuf format on Polymarket.us is confirmed.
    Currently supports season-winner futures (NBA/NHL/NCAA) on api.polymarket.us/v1.
    Will extend to game-by-game markets when .us platform expands.
    """

    def __init__(
        self,
        min_trade_size_usd: float = 200.0,
        min_position_age_sec: int = 900,    # 15 min — no flash/pump trades
        max_trade_age_sec: int = 3_600,     # 1 hour — don't chase stale signals
        min_whale_price: float = 0.05,      # 5¢ lower bound — below = decoy territory
        max_whale_price: float = 0.95,      # 95¢ upper bound — above = decoy territory
    ):
        self.min_trade_size_usd = min_trade_size_usd
        self._min_age = min_position_age_sec
        self._max_age = max_trade_age_sec
        self._min_price = min_whale_price
        self._max_price = max_whale_price

    @property
    def name(self) -> str:
        return "copy_trader_v1"

    # ── public API ────────────────────────────────────────────────

    def is_genuine_signal(
        self,
        trade: WhaleTrade,
        positions: List[WhalePosition],
        now_ts: int,
    ) -> bool:
        """
        Return True if the whale trade passes all decoy filters.

        Args:
            trade:     The whale trade to evaluate.
            positions: Whale's currently open positions (for position confirmation).
            now_ts:    Current unix timestamp (seconds).

        Returns:
            True if all 6 filters pass, False otherwise.
        """
        # 1. BUY only
        if trade.side.upper() != "BUY":
            logger.debug("[copy_trader] skip %s: not BUY (side=%s)", trade.slug, trade.side)
            return False

        # 2. Minimum size
        if trade.size < self.min_trade_size_usd:
            logger.debug("[copy_trader] skip %s: size %.0f < %.0f",
                         trade.slug, trade.size, self.min_trade_size_usd)
            return False

        # 3. Price not extreme
        if not (self._min_price <= trade.price <= self._max_price):
            logger.debug("[copy_trader] skip %s: price %.3f out of [%.2f, %.2f]",
                         trade.slug, trade.price, self._min_price, self._max_price)
            return False

        # 4. Trade age in window
        age_sec = now_ts - trade.timestamp
        if age_sec < self._min_age:
            logger.debug("[copy_trader] skip %s: trade only %ds old (min %ds)",
                         trade.slug, age_sec, self._min_age)
            return False
        if age_sec > self._max_age:
            logger.debug("[copy_trader] skip %s: trade %ds old (max %ds)",
                         trade.slug, age_sec, self._max_age)
            return False

        # 5. Known outcome
        if trade.outcome.lower() not in ("yes", "no"):
            logger.debug("[copy_trader] skip %s: unknown outcome %r", trade.slug, trade.outcome)
            return False

        # 6. Position confirmation — whale still holds it (decoy check)
        if not self._has_confirmed_position(trade, positions):
            logger.debug("[copy_trader] skip %s: no matching open position (likely decoy)",
                         trade.slug)
            return False

        return True

    def generate_signal(
        self,
        trade: WhaleTrade,
        positions: List[WhalePosition],
        now_ts: int,
        current_market_price: float,
        smart_score: float = 75.0,
    ) -> Optional[Signal]:
        """
        Generate a copy-trade Signal if the trade passes all decoy filters.

        Args:
            trade:                 The whale trade to evaluate.
            positions:             Whale's currently open positions.
            now_ts:                Current unix timestamp (seconds).
            current_market_price:  Current YES price on the market (0.0–1.0).
            smart_score:           Whale's predicting.top smart_score (0–100).

        Returns:
            Signal if trade is genuine, None otherwise.
        """
        if not self.is_genuine_signal(trade, positions, now_ts):
            return None

        outcome = trade.outcome.lower()
        if outcome == "yes":
            side = "yes"
            exec_price = current_market_price
            win_prob = trade.price          # whale's entry = their implied fair value
        else:
            side = "no"
            exec_price = 1.0 - current_market_price
            win_prob = trade.price          # whale's NO entry price

        price_cents = round(exec_price * 100)
        if not (1 <= price_cents <= 99):
            logger.debug("[copy_trader] skip %s: price_cents %d out of range",
                         trade.slug, price_cents)
            return None

        edge_pct = self._edge_from_smart_score(smart_score)

        try:
            return Signal(
                side=side,
                edge_pct=edge_pct,
                win_prob=win_prob,
                confidence=smart_score / 100.0,
                ticker=trade.condition_id,
                price_cents=price_cents,
                reason=(
                    f"copy {trade.proxy_wallet[:10]} {trade.title}: "
                    f"{outcome.upper()} ${trade.size:.0f}@{trade.price:.2f} "
                    f"(smart={smart_score:.0f}, edge={edge_pct:.0%})"
                ),
            )
        except ValueError as exc:
            logger.warning("[copy_trader] invalid signal for %s: %s", trade.slug, exc)
            return None

    # ── internal ──────────────────────────────────────────────────

    def _has_confirmed_position(
        self,
        trade: WhaleTrade,
        positions: List[WhalePosition],
    ) -> bool:
        """Return True if whale holds an open position matching this trade."""
        return any(
            p.condition_id == trade.condition_id
            and p.outcome.lower() == trade.outcome.lower()
            for p in positions
        )

    @staticmethod
    def _edge_from_smart_score(smart_score: float) -> float:
        """Map predicting.top smart_score to a copy-trade edge estimate."""
        if smart_score >= _HIGH_SMART_SCORE:
            return _EDGE_HIGH
        if smart_score >= _MID_SMART_SCORE:
            return _EDGE_MID
        return _EDGE_LOW
