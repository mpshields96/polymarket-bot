"""
Paper trade executor.

JOB:    Simulate trade execution without touching Kalshi order endpoints.
        Records trades to DB as paper trades with realistic fill simulation.

DOES NOT: Call any Kalshi order API endpoint. Zero real money at risk.
          Does not know about strategy or risk decisions — those happen upstream.
          Does NOT read config — caller passes slippage_ticks at construction time.

Fill simulation:
    Uses price_cents from the signal as the base fill price.
    Slippage is applied adversely: buyer always pays more.
    slippage_ticks=1 (default): fill_price = price_cents + 1 tick (adverse).
    slippage_ticks=0: exact fill at price_cents.

Caller (main.py) reads paper_slippage_ticks from config.yaml and passes it as:
    PaperExecutor(db=db, strategy_name=..., slippage_ticks=config["risk"]["paper_slippage_ticks"])
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.db import DB

logger = logging.getLogger(__name__)


class PaperExecutor:
    """
    Simulates trade execution in paper mode.

    All operations are synchronous. DB writes are the only side effect.

    Slippage model:
        Buyer always pays more. fill_price = price_cents + slippage_ticks.
        Clamped to 99 (never fills above 99 cents).
        Default slippage_ticks=1 matches realistic paper mode.
        Set slippage_ticks=0 for exact-price backtesting.
    """

    def __init__(self, db: DB, strategy_name: str = "btc_lag", slippage_ticks: int = 1):
        """
        Args:
            db:              SQLite persistence layer.
            strategy_name:   Name of the strategy placing the trade (stored in DB).
            slippage_ticks:  Adverse fill shift in cents. Default 1 (realistic paper mode).
                             Caller reads this from config.yaml risk.paper_slippage_ticks.
        """
        self._db = db
        self._strategy_name = strategy_name
        self._slippage_ticks = slippage_ticks

    def execute(
        self,
        ticker: str,
        side: str,
        price_cents: int,
        size_usd: float,
        reason: str = "",
    ) -> Optional[dict]:
        """
        Record a simulated trade.

        Args:
            ticker:       Kalshi market ticker.
            side:         "yes" | "no"
            price_cents:  Signal price (base fill price before slippage).
            size_usd:     Dollar amount to spend (from sizing module).
            reason:       Human-readable reason string from signal.

        Returns:
            Trade record dict, or None if execution failed.
        """
        # Apply slippage adversely (buyer pays more)
        fill_price_cents = self._apply_slippage(price_cents, self._slippage_ticks)

        if fill_price_cents <= 0 or fill_price_cents >= 100:
            logger.warning("[paper] Unreasonable fill price %d¢ — skip", fill_price_cents)
            return None

        # Calculate number of contracts
        # Each contract costs fill_price_cents / 100 dollars
        cost_per_contract = fill_price_cents / 100.0
        if cost_per_contract <= 0:
            return None

        count = max(1, int(size_usd / cost_per_contract))
        actual_cost = count * cost_per_contract

        client_order_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        slip_note = f" (+{self._slippage_ticks} slip)" if self._slippage_ticks > 0 else ""
        logger.info(
            "[PAPER] BUY %s %d contracts @ %d¢%s = $%.2f | %s | %s",
            side.upper(),
            count,
            fill_price_cents,
            slip_note,
            actual_cost,
            ticker,
            reason[:60] if reason else "",
        )

        # Record to DB
        trade_id = self._db.save_trade(
            ticker=ticker,
            side=side,
            action="buy",
            price_cents=fill_price_cents,
            count=count,
            cost_usd=actual_cost,
            strategy=self._strategy_name,
            edge_pct=None,
            win_prob=None,
            is_paper=True,
            client_order_id=client_order_id,
        )

        return {
            "trade_id": trade_id,
            "client_order_id": client_order_id,
            "ticker": ticker,
            "side": side,
            "action": "buy",
            "fill_price_cents": fill_price_cents,
            "count": count,
            "cost_usd": actual_cost,
            "is_paper": True,
            "timestamp": now_utc,
            "reason": reason,
        }

    def settle(
        self,
        trade_id: int,
        result: str,             # "yes" | "no" — how the market settled
        fill_price_cents: int,   # price we paid (side's buy price)
        side: str,               # "yes" | "no" — our position
        count: int,
    ) -> int:
        """
        Record settlement for a paper trade.

        result and side are both lowercase: "yes" | "no". Kalshi API returns lowercase.
        WIN condition: result == side (NO-side bets win when result=="no").

        Returns:
            P&L in cents.
        """
        # Kalshi pays $1 per contract if you win, $0 if you lose
        # pnl = (payout - cost) * count - fees
        if side == result:
            # WIN: each contract pays 100¢
            gross_pnl_cents = (100 - fill_price_cents) * count
        else:
            # LOSS: contract expires worthless
            gross_pnl_cents = -fill_price_cents * count

        # Kalshi fee: 0.07 × P × (1-P) per contract, charged on win only
        p = fill_price_cents / 100.0
        fee_per_contract_cents = round(0.07 * p * (1 - p) * 100)
        fees_cents = fee_per_contract_cents * count if side == result else 0

        pnl_cents = gross_pnl_cents - fees_cents

        self._db.settle_trade(trade_id, result, pnl_cents)
        logger.info(
            "[paper] Settled trade %d: result=%s, P&L=$%.2f",
            trade_id, result, pnl_cents / 100.0,
        )
        return pnl_cents

    @staticmethod
    def _apply_slippage(fill_price_cents: int, ticks: int) -> int:
        """
        Shift fill price adversely by ticks. Buyer always pays more. Clamped to 99.

        Args:
            fill_price_cents: Raw fill price before slippage.
            ticks:            Number of ticks to shift adversely.

        Returns:
            Slippage-adjusted fill price, clamped to 99.
        """
        return min(99, fill_price_cents + ticks)
