"""
Live trade executor.

JOB:    Real order placement via kalshi.py.
        All orders go to Kalshi's actual API (demo or production).

GUARDS (both must be active):
    1. LIVE_TRADING=true in .env
    2. --live flag passed at CLI

GUARD (first live run):
    Prints giant warning banner, requires interactive "CONFIRM" input.

DOES NOT:
    - Bypass kill switch under any circumstance
    - Call live.py from paper mode
    - Know about strategy or sizing logic
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.platforms.kalshi import KalshiClient, KalshiAPIError, Market, OrderBook
from src.strategies.base import Signal
from src.db import DB

logger = logging.getLogger(__name__)

_FIRST_RUN_CONFIRMED = False  # module-level flag, reset on restart
# NOTE: This is an ADDITIONAL guard to the main.py CONFIRM prompt.
# main.py prompts at startup; this prompts at first actual order placement.
# Both are intentional — defense-in-depth for real money operations.


async def execute(
    signal: Signal,
    market: Market,
    orderbook: OrderBook,
    trade_usd: float,
    kalshi: KalshiClient,
    db: DB,
    *,
    live_confirmed: bool = False,
) -> Optional[dict]:
    """
    Place a real order on Kalshi.

    Args:
        signal:         The trading signal from the strategy
        market:         Current market snapshot
        orderbook:      Current order book
        trade_usd:      Dollar amount to spend (from sizing module)
        kalshi:         Authenticated KalshiClient
        db:             Database for recording the trade
        live_confirmed: Must be True — set by main.py after first-run confirmation

    Returns:
        Trade record dict on success, None on failure.
    """
    global _FIRST_RUN_CONFIRMED

    # ── Guard 1: env var ─────────────────────────────────────────────
    if os.getenv("LIVE_TRADING", "false").lower() != "true":
        raise RuntimeError(
            "LIVE_TRADING env var is not 'true'. "
            "Set it in .env and restart with --live flag."
        )

    # ── Guard 2: CLI flag ─────────────────────────────────────────────
    if not live_confirmed:
        raise RuntimeError(
            "live_confirmed=False. Pass --live at CLI and confirm the warning prompt."
        )

    # ── Guard 3: First-run confirmation ──────────────────────────────
    if not _FIRST_RUN_CONFIRMED:
        _print_live_warning()
        confirmation = input("Type CONFIRM to proceed with live trading: ").strip()
        if confirmation != "CONFIRM":
            logger.warning("Live trading not confirmed — aborting")
            return None
        _FIRST_RUN_CONFIRMED = True
        logger.info("Live trading confirmed by operator")

    # ── Determine fill price ──────────────────────────────────────────
    price_cents = _determine_limit_price(signal.side, market, orderbook)
    if price_cents is None:
        logger.warning("[live] Cannot determine limit price for %s — skip", signal.ticker)
        return None

    if not (1 <= price_cents <= 99):
        logger.warning("[live] Unreasonable limit price %d¢ — skip", price_cents)
        return None

    # ── Calculate contracts ────────────────────────────────────────────
    cost_per_contract = price_cents / 100.0
    count = max(1, int(trade_usd / cost_per_contract))
    expected_cost = count * cost_per_contract

    client_order_id = str(uuid.uuid4())

    logger.info(
        "[LIVE] Placing order: BUY %s %d contracts @ %d¢ = $%.2f | %s",
        signal.side.upper(), count, price_cents, expected_cost, signal.ticker,
    )

    # ── Place order ────────────────────────────────────────────────────
    try:
        order = await kalshi.create_order(
            ticker=signal.ticker,
            side=signal.side,
            action="buy",
            count=count,
            order_type="limit",
            yes_price=price_cents if signal.side == "yes" else None,
            no_price=price_cents if signal.side == "no" else None,
            client_order_id=client_order_id,
        )
    except KalshiAPIError as e:
        logger.error("[live] Order placement failed: %s", e)
        return None
    except Exception as e:
        logger.error("[live] Unexpected error placing order: %s", e, exc_info=True)
        return None

    now_utc = datetime.now(timezone.utc).isoformat()
    logger.info(
        "[LIVE] Order placed: server_id=%s status=%s",
        order.order_id, order.status,
    )

    # ── Record to DB ──────────────────────────────────────────────────
    trade_id = db.save_trade(
        ticker=signal.ticker,
        side=signal.side,
        action="buy",
        price_cents=price_cents,
        count=count,
        cost_usd=expected_cost,
        strategy="btc_lag",
        edge_pct=signal.edge_pct,
        win_prob=signal.win_prob,
        is_paper=False,
        client_order_id=client_order_id,
        server_order_id=order.order_id,
    )

    return {
        "trade_id": trade_id,
        "client_order_id": client_order_id,
        "server_order_id": order.order_id,
        "ticker": signal.ticker,
        "side": signal.side,
        "action": "buy",
        "price_cents": price_cents,
        "count": count,
        "cost_usd": expected_cost,
        "status": order.status,
        "is_paper": False,
        "timestamp": now_utc,
    }


def _determine_limit_price(
    side: str,
    market: Market,
    orderbook: OrderBook,
) -> Optional[int]:
    """
    Choose a limit price for live order placement.

    Uses orderbook ask price (the real cost to buy).
    Falls back to market snapshot price.
    """
    if side == "yes":
        yes_ask = orderbook.yes_ask()
        if yes_ask and 1 <= yes_ask <= 99:
            return yes_ask
        if 1 <= market.yes_price <= 99:
            return market.yes_price
    elif side == "no":
        no_ask = orderbook.no_ask()
        if no_ask and 1 <= no_ask <= 99:
            return no_ask
        if 1 <= market.no_price <= 99:
            return market.no_price
    return None


def _print_live_warning():
    print()
    print("=" * 64)
    print("  ⚠️   LIVE TRADING MODE — REAL MONEY AT RISK   ⚠️")
    print()
    print("  You are about to place orders on Kalshi's production API.")
    print("  This uses real funds from your Kalshi account.")
    print()
    print("  Kill switch is active — trades are capped at $5/trade.")
    print("  Starting bankroll: see config.yaml (risk.starting_bankroll_usd)")
    print()
    print("  If you see unexpected behavior:")
    print("  1. Let the kill switch trigger (it will halt automatically)")
    print("  2. Or: Ctrl+C → python main.py --reset-killswitch")
    print()
    print("=" * 64)
    print()
