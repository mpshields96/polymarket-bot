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

# ── Execution-time price guard constants ──────────────────────────────────
# Guard fires AFTER fetching the live orderbook price, immediately before
# placing the order. Protects against HFT repricing in the 0.1-1s asyncio gap
# between signal generation and order placement (observed: fill at 84¢ session 37).
_EXECUTION_MIN_PRICE_CENTS: int = 35
_EXECUTION_MAX_PRICE_CENTS: int = 65
_EXECUTION_MAX_SLIPPAGE_CENTS: int = 10


async def execute(
    signal: Signal,
    market: Market,
    orderbook: OrderBook,
    trade_usd: float,
    kalshi: KalshiClient,
    db: DB,
    *,
    live_confirmed: bool = False,
    strategy_name: str = "unknown",
    price_guard_min: int = _EXECUTION_MIN_PRICE_CENTS,
    price_guard_max: int = _EXECUTION_MAX_PRICE_CENTS,
    post_only: bool = False,
    expiration_ts: Optional[int] = None,
    max_slippage_cents: Optional[int] = None,
) -> Optional[dict]:
    """
    Place a real order on Kalshi.

    Args:
        signal:          The trading signal from the strategy
        market:          Current market snapshot
        orderbook:       Current order book
        trade_usd:       Dollar amount to spend (from sizing module)
        kalshi:          Authenticated KalshiClient
        db:              Database for recording the trade
        live_confirmed:  Must be True — set by main.py after first-run confirmation
        strategy_name:   Strategy name saved to DB (e.g. "btc_lag_v1", "btc_drift_v1")
        price_guard_min: Lower bound for YES-equivalent execution price guard (default 35).
                         Override with 1 for expiry_sniper, which operates at 87-99¢.
        price_guard_max: Upper bound for YES-equivalent execution price guard (default 65).
                         Override with 99 for expiry_sniper, which operates at 87-99¢.
        post_only:       If True, order is maker-only. Rejected if it would cross
                         the spread and fill as taker. Saves ~75% on fees for drift.
        expiration_ts:   Unix timestamp when maker order auto-cancels if unfilled.

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

    # ── Fee-floor guard: block 99c/1c raw prices ──────────────────────────
    # At 99c (either YES or NO side), gross margin = 1c/contract = near-zero net.
    # S72 incident: NO@99c slips through YES-equiv guard because 100-99=1c ∈ [1,99].
    # Explicitly block raw price at boundary to prevent execution at fee-floor prices.
    if price_cents >= 99 or price_cents <= 1:
        logger.info(
            "[live] Execution price %d¢ at fee-floor boundary — skip (no net margin)",
            price_cents,
        )
        return None

    # ── Negative-EV bucket guard: 96c, 97c-NO, 98c-NO ───────────────────────
    # These buckets are structurally unprofitable based on live bet history:
    #   96c both sides: 31 bets, 93.5% WR, -22.44 USD (needs 96%+ to break even)
    #   97c NO-side:    13 bets, 92.3% WR, -15.03 USD (needs 97%+ to break even)
    #   97c YES-side:   11 bets, 100% WR,   +2.90 USD -- profitable, NOT blocked
    #   98c NO-side:    28 bets, 92.9% WR, -25.54 USD (needs 98%+ to break even)
    #   98c YES-side:   20 bets, 100% WR,   +3.02 USD -- profitable, NOT blocked
    # Validated S74/S75/S78. Revisit at 200+ bets per price level per side.
    if price_cents == 96:
        logger.info(
            "[live] Execution price 96c -- both sides historically negative EV "
            "(93.5%% WR at 31 bets, needs >=96%% to break even) -- skip",
        )
        return None
    if price_cents == 97 and signal.side == "no":
        logger.info(
            "[live] Execution price 97c NO-side -- historically negative EV "
            "(92.3%% WR at 13 bets, needs >=97%% to break even) -- skip",
        )
        return None
    if price_cents == 98 and signal.side == "no":
        logger.info(
            "[live] Execution price 98c NO-side -- historically negative EV "
            "(92.9%% WR at 28 bets, needs >=98%% to break even) -- skip",
        )
        return None

    # ── Per-asset structural loss guards (S81) ────────────────────────────
    # XRP and SOL have higher intra-window volatility than BTC/ETH, causing
    # specific price buckets to fall structurally below break-even WR.
    # IL-10A: XRP YES@94c — 15 bets, 93.3% WR, need 94.9% break-even, -9.09 USD
    if "KXXRP" in signal.ticker and price_cents == 94 and signal.side == "yes":
        logger.info(
            "[live] KXXRP YES@94c -- structurally negative EV "
            "(93.3%% WR at 15 bets, needs 94.9%% to break even) -- skip",
        )
        return None
    # IL-20: XRP YES@95c — 10 bets, 90.0% WR, need 95.0% break-even, -14.27 USD
    # SOL/BTC/ETH YES@95c remain profitable (100% WR). XRP only.
    # Confirmed S88 2026-03-16: loss at KXXRP15M-26MAR160415-15 triggered analysis.
    if "KXXRP" in signal.ticker and price_cents == 95 and signal.side == "yes":
        logger.info(
            "[live] KXXRP YES@95c -- structurally negative EV "
            "(90.0%% WR at 10 bets, needs 95.0%% to break even) -- skip",
        )
        return None

    # IL-10B: XRP YES@97c — 6 bets, 83.3% WR, need 98.0% break-even, -18.04 USD
    if "KXXRP" in signal.ticker and price_cents == 97 and signal.side == "yes":
        logger.info(
            "[live] KXXRP YES@97c -- structurally negative EV "
            "(83.3%% WR at 6 bets, needs 98.0%% to break even, terrible R/R) -- skip",
        )
        return None
    # IL-10C: SOL YES@94c — 12 bets, 91.7% WR, need 94.9% break-even, -7.28 USD
    if "KXSOL" in signal.ticker and price_cents == 94 and signal.side == "yes":
        logger.info(
            "[live] KXSOL YES@94c -- structurally negative EV "
            "(91.7%% WR at 12 bets, needs 94.9%% to break even) -- skip",
        )
        return None
    # IL-19: SOL YES@97c — 8 bets, 87.5% WR, need 97.0% break-even, -17.18 USD
    # BTC/ETH YES@97c remain profitable (100% WR). SOL only.
    # Confirmed S88 2026-03-16: loss at KXSOL15M-26MAR160200-00 triggered analysis.
    if "KXSOL" in signal.ticker and price_cents == 97 and signal.side == "yes":
        logger.info(
            "[live] KXSOL YES@97c -- structurally negative EV "
            "(87.5%% WR at 8 bets, needs 97.0%% to break even) -- skip",
        )
        return None

    # ── Execution-time price guard ────────────────────────────────────────
    # Convert execution price to YES-equivalent for range + slippage checks.
    # Protects against HFT repricing in the asyncio gap after signal generation.
    execution_yes_price = price_cents if signal.side == "yes" else (100 - price_cents)
    signal_yes_price = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)

    if not (price_guard_min <= execution_yes_price <= price_guard_max):
        logger.warning(
            "[live] Execution price %d¢ (YES-equiv) outside guard %d-%d¢ — rejecting "
            "(signal was %d¢, ticker=%s)",
            execution_yes_price, price_guard_min, price_guard_max,
            signal_yes_price, signal.ticker,
        )
        return None

    slippage_cents = abs(execution_yes_price - signal_yes_price)
    _slip_limit = max_slippage_cents if max_slippage_cents is not None else _EXECUTION_MAX_SLIPPAGE_CENTS
    if slippage_cents > _slip_limit:
        logger.warning(
            "[live] Slippage %d¢ exceeds max %d¢ — rejecting (signal=%d¢, exec=%d¢, ticker=%s)",
            slippage_cents, _slip_limit,
            signal_yes_price, execution_yes_price, signal.ticker,
        )
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
            post_only=post_only,
            expiration_ts=expiration_ts,
        )
    except KalshiAPIError as e:
        # ── post_only taker fallback ──────────────────────────────────────
        # If post_only=True and Kalshi rejects with "post only cross", the limit
        # price crossed the spread (market moved). The signal is still valid.
        # Retry immediately as taker (post_only=False) to capture the edge.
        # Taker fees (~1.4%) are covered by drift edge (typically 5-15%).
        # S88 2026-03-16: drift strategies generated 50+ missed trades/session
        # from this pattern without fallback.
        _is_post_only_cross = (
            post_only
            and isinstance(e.body, dict)
            and e.body.get("error", {}).get("details") == "post only cross"
        )
        if _is_post_only_cross:
            logger.info(
                "[live] post_only rejected (spread crossed) — retrying as taker for %s",
                signal.ticker,
            )
            try:
                order = await kalshi.create_order(
                    ticker=signal.ticker,
                    side=signal.side,
                    action="buy",
                    count=count,
                    order_type="limit",
                    yes_price=price_cents if signal.side == "yes" else None,
                    no_price=price_cents if signal.side == "no" else None,
                    client_order_id=str(uuid.uuid4()),
                    post_only=False,
                    expiration_ts=expiration_ts,
                )
            except Exception as e2:
                logger.error("[live] Taker retry failed: %s", e2)
                return None
        else:
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

    # ── Canceled order guard ──────────────────────────────────────────────
    # Kalshi cancels orders that cannot be matched (no liquidity, market closing,
    # risk limit). A canceled order must NOT be recorded as a live bet — doing so
    # corrupts calibration data, inflates trade counters, and poisons Brier scores.
    if order.status == "canceled":
        logger.warning(
            "[live] Order canceled by Kalshi — NOT recording as trade: "
            "server_id=%s ticker=%s",
            order.order_id, signal.ticker,
        )
        return None

    # ── Record to DB ──────────────────────────────────────────────────
    trade_id = db.save_trade(
        ticker=signal.ticker,
        side=signal.side,
        action="buy",
        price_cents=price_cents,
        count=count,
        cost_usd=expected_cost,
        strategy=strategy_name,
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
