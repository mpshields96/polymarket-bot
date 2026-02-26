"""
main.py — CLI entry point and main trading loop.

JOB:    Parse CLI args, wire all components, run the loop.
DOES NOT: Business logic, math, API calls, risk decisions.

Usage:
    python main.py                  # Paper mode (default)
    python main.py --live           # Live mode (also requires LIVE_TRADING=true in .env)
    python main.py --verify         # Run connection verification and exit
    python main.py --reset-killswitch  # Reset a triggered hard stop
    python main.py --report         # Print today's P&L summary and exit

Architecture:
    Async I/O for API + WebSocket.
    Synchronous risk checks (kill switch, sizing).
    SQLite for persistence.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
load_dotenv(PROJECT_ROOT / ".env")

# ── Logging setup (before importing src modules) ───────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(PROJECT_ROOT / "logs" / "errors" / "bot.log", delay=True),
    ],
)
logger = logging.getLogger("main")


# ── Main trading loop ─────────────────────────────────────────────────

POLL_INTERVAL_SEC = 30      # How often to check markets and generate signals
BANKROLL_SNAPSHOT_SEC = 300  # How often to record bankroll to DB (5 min)
SETTLEMENT_POLL_SEC = 60    # How often to check for settled markets


async def trading_loop(
    kalshi,
    btc_feed,
    strategy,
    kill_switch,
    sizing,
    db,
    paper_executor,
    live_executor_enabled: bool,
    live_confirmed: bool,
    btc_series_ticker: str = "KXBTC15M",
):
    """Main async loop: poll markets, generate signals, execute trades."""
    from src.execution import paper as paper_mod
    import time

    last_bankroll_snapshot = 0.0

    while True:
        try:
            # ── Bankroll snapshot ─────────────────────────────────────
            now = time.time()
            if now - last_bankroll_snapshot > BANKROLL_SNAPSHOT_SEC:
                try:
                    balance = await kalshi.get_balance()
                    db.save_bankroll(balance.available_usd, source="api")
                    last_bankroll_snapshot = now
                except Exception as e:
                    logger.warning("Balance fetch failed: %s", e)
                    # Use DB's last known value
                    balance_usd = db.latest_bankroll() or 50.0
                    db.save_bankroll(balance_usd, source="paper_simulation")
                    last_bankroll_snapshot = now

            # ── Current bankroll for risk checks ─────────────────────
            current_bankroll = db.latest_bankroll() or 50.0

            # ── Kill switch status check ──────────────────────────────
            if kill_switch.is_hard_stopped:
                logger.critical("Kill switch is HARD STOPPED. Halting loop.")
                break

            # ── Get open BTC markets ──────────────────────────────────
            try:
                markets = await kalshi.get_markets(
                    series_ticker=btc_series_ticker, status="open"
                )
            except Exception as e:
                logger.warning("Failed to fetch markets: %s", e)
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            if not markets:
                logger.debug("No open BTC markets found")
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            # ── Evaluate each market ──────────────────────────────────
            for market in markets:
                if kill_switch.is_hard_stopped:
                    break

                # Get orderbook
                try:
                    orderbook = await kalshi.get_orderbook(market.ticker)
                except Exception as e:
                    logger.warning("Failed to fetch orderbook for %s: %s", market.ticker, e)
                    continue

                # Generate signal (synchronous)
                signal = strategy.generate_signal(market, orderbook, btc_feed)
                if signal is None:
                    continue

                # Size the trade (synchronous)
                from src.risk.sizing import calculate_size, kalshi_payout
                payout = kalshi_payout(signal.price_cents, signal.side)
                size_result = calculate_size(
                    win_prob=signal.win_prob,
                    payout_per_dollar=payout,
                    edge_pct=signal.edge_pct,
                    bankroll_usd=current_bankroll,
                )

                if size_result is None:
                    logger.debug("[main] Sizing returned None for signal on %s", market.ticker)
                    continue

                trade_usd = size_result.recommended_usd

                # Kill switch pre-trade check (synchronous)
                from src.strategies.btc_lag import BTCLagStrategy
                minutes_remaining = BTCLagStrategy._minutes_remaining(market)
                ok, reason = kill_switch.check_order_allowed(
                    trade_usd=trade_usd,
                    current_bankroll_usd=current_bankroll,
                    minutes_remaining=minutes_remaining,
                )

                if not ok:
                    logger.info("[main] Kill switch blocked trade: %s", reason)
                    continue

                # Execute (paper or live)
                if live_executor_enabled and live_confirmed:
                    from src.execution import live as live_mod
                    result = await live_mod.execute(
                        signal=signal,
                        market=market,
                        orderbook=orderbook,
                        trade_usd=trade_usd,
                        kalshi=kalshi,
                        db=db,
                        live_confirmed=live_confirmed,
                    )
                else:
                    paper_exec = paper_mod.PaperExecutor(db)
                    result = paper_exec.execute(
                        signal=signal,
                        market=market,
                        orderbook=orderbook,
                        bankroll_usd=current_bankroll,
                        trade_usd=trade_usd,
                    )

                if result:
                    kill_switch.record_trade()
                    logger.info(
                        "[main] Trade executed: %s %s @ %d¢ $%.2f | trade_id=%s",
                        result["side"].upper(),
                        result["ticker"],
                        result["fill_price_cents"] if "fill_price_cents" in result else result.get("price_cents", 0),
                        result["cost_usd"],
                        result.get("trade_id"),
                    )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Unexpected error in trading loop: %s", e, exc_info=True)

        await asyncio.sleep(POLL_INTERVAL_SEC)


# ── Settlement polling loop ────────────────────────────────────────────

async def settlement_loop(kalshi, db):
    """
    Background loop: detect settled markets and record outcomes in DB.

    Polls every SETTLEMENT_POLL_SEC seconds. For each open trade, fetches the
    market from Kalshi. When a market status is 'finalized', settles the trade
    and records P&L (same formula for paper + live: win/loss based on result).
    """
    from src.execution.paper import PaperExecutor
    paper_exec = PaperExecutor(db)

    while True:
        try:
            await asyncio.sleep(SETTLEMENT_POLL_SEC)

            open_trades = db.get_open_trades()
            if not open_trades:
                continue

            # Deduplicate tickers to minimise API calls
            tickers = list({t["ticker"] for t in open_trades})

            for ticker in tickers:
                try:
                    market = await kalshi.get_market(ticker)
                except Exception as e:
                    logger.warning("[settle] Failed to fetch market %s: %s", ticker, e)
                    continue

                # Kalshi marks settled markets as "finalized"
                if market.status not in ("finalized", "settled") or not market.result:
                    continue

                result = market.result  # "yes" | "no"
                ticker_trades = [t for t in open_trades if t["ticker"] == ticker]

                for trade in ticker_trades:
                    pnl_cents = paper_exec.settle(
                        trade_id=trade["id"],
                        result=result,
                        fill_price_cents=trade["price_cents"],
                        side=trade["side"],
                        count=trade["count"],
                    )
                    mode = "PAPER" if trade["is_paper"] else "LIVE"
                    logger.info(
                        "[settle] %s trade %d (%s %s @ %d¢ ×%d): result=%s P&L=$%.2f",
                        mode, trade["id"], trade["side"].upper(), ticker,
                        trade["price_cents"], trade["count"],
                        result.upper(), pnl_cents / 100.0,
                    )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Unexpected error in settlement loop: %s", e, exc_info=True)


# ── Startup banner ─────────────────────────────────────────────────────

def print_banner(mode: str, bankroll: float, stage: int, kill_switch_active: bool):
    width = 60
    print()
    print("=" * width)
    print(f"  POLYMARKET-BOT  {'[LIVE]' if mode == 'live' else '[PAPER]'}")
    print(f"  Mode:      {mode.upper()}")
    print(f"  Bankroll:  ${bankroll:.2f}")
    print(f"  Stage:     {stage}")
    print(f"  Kill SW:   {'🔴 ACTIVE' if kill_switch_active else '✅ Clear'}")
    print(f"  Started:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * width)
    print()


# ── Report command ─────────────────────────────────────────────────────

def print_report(db):
    """Print today's P&L summary."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trades = db.get_trades(limit=50)
    today_trades = [t for t in trades if t["timestamp"] and
                    datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%Y-%m-%d") == today]
    settled = [t for t in today_trades if t.get("result")]
    wins = [t for t in settled if t["result"] == t["side"]]
    total_pnl_cents = sum(t.get("pnl_cents", 0) or 0 for t in settled)

    print(f"\n{'='*50}")
    print(f"  P&L REPORT — {today}")
    print(f"  Trades today:  {len(today_trades)}")
    print(f"  Settled:       {len(settled)}")
    print(f"  Wins:          {len(wins)}")
    print(f"  Win rate:      {len(wins)/max(1,len(settled)):.0%}")
    print(f"  P&L:           ${total_pnl_cents/100:.2f}")
    wr = db.win_rate()
    if wr is not None:
        print(f"  All-time win:  {wr:.0%}")
    print(f"  All-time P&L:  ${db.total_realized_pnl_usd():.2f}")
    print(f"{'='*50}\n")


# ── Main ──────────────────────────────────────────────────────────────


async def main():
    parser = argparse.ArgumentParser(description="polymarket-bot — Kalshi BTC lag trader")
    parser.add_argument("--live", action="store_true",
                        help="Enable live trading (also requires LIVE_TRADING=true in .env)")
    parser.add_argument("--verify", action="store_true",
                        help="Run connection verification and exit")
    parser.add_argument("--reset-killswitch", action="store_true",
                        help="Reset a triggered hard stop (requires manual confirmation)")
    parser.add_argument("--report", action="store_true",
                        help="Print today's P&L summary and exit")
    args = parser.parse_args()

    # ── --reset-killswitch ────────────────────────────────────────────
    if args.reset_killswitch:
        from src.risk.kill_switch import reset_kill_switch
        reset_kill_switch()
        return

    # ── --verify ──────────────────────────────────────────────────────
    if args.verify:
        import subprocess
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "setup" / "verify.py")]
        )
        sys.exit(result.returncode)

    # ── Kill switch startup check ─────────────────────────────────────
    from src.risk.kill_switch import check_lock_at_startup, KillSwitch
    try:
        check_lock_at_startup()
    except RuntimeError as e:
        print(str(e))
        sys.exit(1)

    # ── Load config ───────────────────────────────────────────────────
    import yaml
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        print("ERROR: config.yaml not found. Run: cp .env.example .env && fill it in.")
        sys.exit(1)
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # ── Live mode gate ────────────────────────────────────────────────
    live_env = os.getenv("LIVE_TRADING", "false").lower() == "true"
    live_mode = args.live and live_env

    if args.live and not live_env:
        print("ERROR: --live passed but LIVE_TRADING is not 'true' in .env.")
        print("Set LIVE_TRADING=true in .env and try again.")
        sys.exit(1)

    # ── Initialize DB ─────────────────────────────────────────────────
    from src.db import load_from_config as db_load
    db = db_load()
    db.init()

    # ── --report ──────────────────────────────────────────────────────
    if args.report:
        print_report(db)
        db.close()
        return

    # ── Initialize components ─────────────────────────────────────────
    from src.platforms.kalshi import load_from_env as kalshi_load
    from src.data.binance import load_from_config as binance_load
    from src.strategies.btc_lag import load_from_config as strategy_load
    from src.risk.sizing import get_stage

    starting_bankroll = config.get("risk", {}).get("starting_bankroll_usd", 50.0)
    kill_switch = KillSwitch(starting_bankroll_usd=starting_bankroll)

    current_bankroll = db.latest_bankroll() or starting_bankroll
    stage = get_stage(current_bankroll)

    mode = "live" if live_mode else "paper"
    print_banner(mode, current_bankroll, stage, kill_switch.is_hard_stopped)

    # ── Connect to Kalshi ─────────────────────────────────────────────
    logger.info("Initializing Kalshi client...")
    kalshi = kalshi_load()
    await kalshi.start()

    # ── Start Binance feed ────────────────────────────────────────────
    logger.info("Starting Binance BTC feed...")
    btc_feed = binance_load()
    await btc_feed.start()

    # ── Load strategy ─────────────────────────────────────────────────
    strategy = strategy_load()
    logger.info("Strategy loaded: %s", strategy.name)

    # ── Run ───────────────────────────────────────────────────────────
    trade_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            strategy=strategy,
            kill_switch=kill_switch,
            sizing=None,
            db=db,
            paper_executor=None,
            live_executor_enabled=live_mode,
            live_confirmed=False,
            btc_series_ticker=config.get("strategy", {}).get("markets", ["KXBTC15M"])[0],
        ),
        name="trading_loop",
    )
    settle_task = asyncio.create_task(
        settlement_loop(kalshi=kalshi, db=db),
        name="settlement_loop",
    )

    try:
        await asyncio.gather(trade_task, settle_task)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt — shutting down")
    finally:
        trade_task.cancel()
        settle_task.cancel()
        await asyncio.gather(trade_task, settle_task, return_exceptions=True)
        logger.info("Stopping feeds and connections...")
        await btc_feed.stop()
        await kalshi.close()
        db.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Ensure log directories exist
    (PROJECT_ROOT / "logs" / "errors").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs" / "trades").mkdir(parents=True, exist_ok=True)
    asyncio.run(main())
