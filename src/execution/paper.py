"""
Paper trade executor.

JOB:    Simulate trade execution without touching Kalshi order endpoints.
        Records trades to DB as paper trades with realistic fill simulation.

DOES NOT: Call any Kalshi order API endpoint. Zero real money at risk.
          Does not know about strategy or risk decisions — those happen upstream.

Fill simulation:
    Uses current orderbook spread to simulate realistic fills.
    YES buy: fills at current YES ask (implied from NO best bid)
    NO buy:  fills at current NO ask (implied from YES best bid)
    Falls back to market.yes_price / market.no_price if orderbook is empty.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.platforms.kalshi import Market, OrderBook
from src.strategies.base import Signal
from src.db import DB

logger = logging.getLogger(__name__)


class PaperExecutor:
    """
    Simulates trade execution in paper mode.

    All operations are synchronous. DB writes are the only side effect.
    """

    def __init__(self, db: DB):
        self._db = db

    def execute(
        self,
        signal: Signal,
        market: Market,
        orderbook: OrderBook,
        bankroll_usd: float,
        trade_usd: float,
    ) -> Optional[dict]:
        """
        Record a simulated trade.

        Args:
            signal:      The signal from the strategy (side, edge_pct, etc.)
            market:      Current market snapshot
            orderbook:   Current order book (used for fill price simulation)
            bankroll_usd: Current paper bankroll (for context only — not modified here)
            trade_usd:   Dollar amount to spend (from sizing module)

        Returns:
            Trade record dict, or None if execution failed.
        """
        # Determine fill price (simulate realistic fill from orderbook)
        fill_price_cents = self._simulate_fill_price(signal.side, market, orderbook)
        if fill_price_cents is None:
            logger.warning("[paper] Cannot determine fill price for %s — skip", signal.ticker)
            return None

        if fill_price_cents <= 0 or fill_price_cents >= 100:
            logger.warning("[paper] Unreasonable fill price %d¢ — skip", fill_price_cents)
            return None

        # Calculate number of contracts
        # Each contract costs fill_price_cents / 100 dollars
        cost_per_contract = fill_price_cents / 100.0
        if cost_per_contract <= 0:
            return None

        count = max(1, int(trade_usd / cost_per_contract))
        actual_cost = count * cost_per_contract

        client_order_id = str(uuid.uuid4())
        now_utc = datetime.now(timezone.utc).isoformat()

        logger.info(
            "[PAPER] BUY %s %d contracts @ %d¢ = $%.2f | %s | %s",
            signal.side.upper(),
            count,
            fill_price_cents,
            actual_cost,
            signal.ticker,
            signal.reason[:60] if signal.reason else "",
        )

        # Record to DB
        trade_id = self._db.save_trade(
            ticker=signal.ticker,
            side=signal.side,
            action="buy",
            price_cents=fill_price_cents,
            count=count,
            cost_usd=actual_cost,
            strategy="btc_lag",
            edge_pct=signal.edge_pct,
            win_prob=signal.win_prob,
            is_paper=True,
            client_order_id=client_order_id,
        )

        return {
            "trade_id": trade_id,
            "client_order_id": client_order_id,
            "ticker": signal.ticker,
            "side": signal.side,
            "action": "buy",
            "fill_price_cents": fill_price_cents,
            "count": count,
            "cost_usd": actual_cost,
            "is_paper": True,
            "timestamp": now_utc,
            "reason": signal.reason,
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
    def _simulate_fill_price(
        side: str,
        market: Market,
        orderbook: OrderBook,
    ) -> Optional[int]:
        """
        Estimate the fill price using orderbook data.

        For a buy:
            YES buy → we pay the YES ask = 100 - best_no_bid
            NO buy  → we pay the NO ask = 100 - best_yes_bid

        Falls back to market.yes_price / market.no_price.
        """
        if side == "yes":
            # Try orderbook-implied ask first
            yes_ask = orderbook.yes_ask()
            if yes_ask and 1 <= yes_ask <= 99:
                return yes_ask
            # Fallback to market snapshot
            if 1 <= market.yes_price <= 99:
                return market.yes_price

        elif side == "no":
            no_ask = orderbook.no_ask()
            if no_ask and 1 <= no_ask <= 99:
                return no_ask
            if 1 <= market.no_price <= 99:
                return market.no_price

        return None
