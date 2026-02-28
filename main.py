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
    db,
    live_executor_enabled: bool,
    live_confirmed: bool,
    btc_series_ticker: str = "KXBTC15M",
    loop_name: str = "trading",
    initial_delay_sec: float = 0.0,
    max_daily_bets: int = 5,
):
    """Main async loop: poll markets, generate signals, execute trades."""
    from src.execution import paper as paper_mod
    import time

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

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
                logger.info("[%s] No open %s markets found", loop_name, btc_series_ticker)
                await asyncio.sleep(POLL_INTERVAL_SEC)
                continue

            logger.info("[%s] Evaluating %d market(s): %s",
                        loop_name, len(markets), [m.ticker for m in markets])

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

                # Position deduplication — skip if we already have an open bet on this market
                if db.has_open_position(market.ticker):
                    logger.info("[%s] Open position already exists on %s — skip",
                                loop_name, market.ticker)
                    continue

                # Daily bet cap (tax protection + quality gate)
                if max_daily_bets > 0:
                    today_count = db.count_trades_today(strategy.name)
                    if today_count >= max_daily_bets:
                        logger.info("[%s] Daily bet cap reached (%d/%d) for %s — skip",
                                    loop_name, today_count, max_daily_bets, strategy.name)
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
                    _slip = config.get("risk", {}).get("paper_slippage_ticks", 1)
                    paper_exec = paper_mod.PaperExecutor(
                        db=db,
                        strategy_name=strategy.name,
                        slippage_ticks=_slip,
                    )
                    result = paper_exec.execute(
                        ticker=signal.ticker,
                        side=signal.side,
                        price_cents=signal.price_cents,
                        size_usd=trade_usd,
                        reason=signal.reason,
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


# ── Weather forecast trading loop ─────────────────────────────────────

WEATHER_POLL_INTERVAL_SEC = 300   # 5 min — weather forecasts change slowly


async def weather_loop(
    kalshi,
    weather_strategy,
    weather_feed,
    kill_switch,
    db,
    series_ticker: str = "HIGHNY",
    loop_name: str = "weather",
    initial_delay_sec: float = 43.0,
    max_daily_bets: int = 5,
):
    """
    Weather forecast trading loop.

    Fetches HIGHNY (NYC daily high-temp) markets every 5 min.
    Refreshes Open-Meteo forecast when stale (every 30 min).
    Evaluates WeatherForecastStrategy on each open market.
    Paper-only — same signal/execution path as trading_loop.
    """
    from src.execution import paper as paper_mod

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.critical("[%s] Kill switch HARD STOPPED. Halting.", loop_name)
                break

            # Refresh weather feed if stale (blocking ~100ms HTTP call)
            if weather_feed.is_stale:
                ok = weather_feed.refresh()
                if not ok:
                    logger.warning("[%s] Weather feed refresh failed — skipping cycle", loop_name)
                    await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)
                    continue

            forecast_f = weather_feed.forecast_temp_f()
            if forecast_f is None:
                await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)
                continue

            # Fetch open weather markets
            try:
                markets = await kalshi.get_markets(series_ticker=series_ticker, status="open")
            except Exception as e:
                logger.warning("[%s] Failed to fetch markets: %s", loop_name, e)
                await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)
                continue

            if not markets:
                logger.info(
                    "[%s] No open %s markets found (forecast=%.1f°F)",
                    loop_name, series_ticker, forecast_f,
                )
                await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)
                continue

            logger.info(
                "[%s] Evaluating %d %s market(s) | forecast=%.1f°F",
                loop_name, len(markets), series_ticker, forecast_f,
            )

            for market in markets:
                if kill_switch.is_hard_stopped:
                    break

                try:
                    orderbook = await kalshi.get_orderbook(market.ticker)
                except Exception as e:
                    logger.warning("[%s] Orderbook fetch failed for %s: %s", loop_name, market.ticker, e)
                    continue

                # btc_feed=None — weather strategy ignores it
                signal = weather_strategy.generate_signal(market, orderbook, None)

                if signal is None:
                    continue

                # Position deduplication
                if db.has_open_position(market.ticker):
                    logger.info("[%s] Open position already on %s — skip", loop_name, market.ticker)
                    continue

                # Daily bet cap
                if max_daily_bets > 0 and db.count_trades_today(weather_strategy.name) >= max_daily_bets:
                    logger.info("[%s] Daily bet cap reached for %s — skip", loop_name, weather_strategy.name)
                    continue

                # ── Execute (paper only) ──────────────────────────────
                current_bankroll = db.latest_bankroll() or 50.0
                order_check = kill_switch.check_order_allowed(
                    proposed_usd=1.0,   # placeholder; sizing is paper-only
                    current_bankroll=current_bankroll,
                )
                if not order_check.get("allowed", False):
                    logger.info("[%s] Kill switch blocked trade: %s", loop_name, order_check.get("reason"))
                    continue

                from src.risk.sizing import calculate_size
                size = calculate_size(
                    edge_pct=signal.edge_pct,
                    win_prob=signal.win_prob,
                    price_cents=signal.price_cents,
                    bankroll_usd=current_bankroll,
                )
                if size is None:
                    continue

                import yaml as _yaml
                with open(PROJECT_ROOT / "config.yaml") as _f:
                    _wcfg = _yaml.safe_load(_f)
                _wslip = _wcfg.get("risk", {}).get("paper_slippage_ticks", 1)
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=weather_strategy.name,
                    slippage_ticks=_wslip,
                )
                result = paper_exec.execute(
                    ticker=signal.ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=size,
                    reason=signal.reason,
                )
                logger.info(
                    "[%s] Paper trade: %s %s @ %d¢ $%.2f",
                    loop_name,
                    result["side"].upper(),
                    result["ticker"],
                    result.get("fill_price_cents", result.get("price_cents", 0)),
                    result["cost_usd"],
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("[%s] Unexpected error: %s", loop_name, e, exc_info=True)

        await asyncio.sleep(WEATHER_POLL_INTERVAL_SEC)


# ── FOMC rate trading loop ─────────────────────────────────────────────

FOMC_POLL_INTERVAL_SEC = 1800   # 30 min — FOMC markets don't move every second


async def fomc_loop(
    kalshi,
    fomc_strategy,
    fred_feed,
    kill_switch,
    db,
    series_ticker: str = "KXFEDDECISION",
    loop_name: str = "fomc",
    initial_delay_sec: float = 51.0,
    max_daily_bets: int = 5,
):
    """
    FOMC rate decision trading loop.

    Fetches KXFEDDECISION markets every 30 min.
    Refreshes FRED feed (DFF, DGS2, CPI) if stale.
    Only active within days_before_meeting of next FOMC date.
    Paper-only — yield curve model needs calibration over multiple meetings.
    """
    from src.execution import paper as paper_mod

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.critical("[%s] Kill switch HARD STOPPED. Halting.", loop_name)
                break

            # Refresh FRED feed if stale (blocking ~600ms for 3 CSV fetches)
            if fred_feed.is_stale:
                ok = fred_feed.refresh()
                if not ok:
                    logger.warning("[%s] FRED refresh failed — skipping cycle", loop_name)
                    await asyncio.sleep(FOMC_POLL_INTERVAL_SEC)
                    continue

            snap = fred_feed.snapshot()
            if snap is None:
                await asyncio.sleep(FOMC_POLL_INTERVAL_SEC)
                continue

            # Fetch KXFEDDECISION markets
            try:
                markets = await kalshi.get_markets(series_ticker=series_ticker, status="open")
            except Exception as e:
                logger.warning("[%s] Failed to fetch markets: %s", loop_name, e)
                await asyncio.sleep(FOMC_POLL_INTERVAL_SEC)
                continue

            if not markets:
                logger.info(
                    "[%s] No open %s markets found (DFF=%.2f%% DGS2=%.2f%%)",
                    loop_name, series_ticker, snap.fed_funds_rate, snap.yield_2yr,
                )
                await asyncio.sleep(FOMC_POLL_INTERVAL_SEC)
                continue

            logger.info(
                "[%s] Evaluating %d %s market(s) | DFF=%.2f%% DGS2=%.2f%% spread=%+.2f%% CPI %s",
                loop_name, len(markets), series_ticker,
                snap.fed_funds_rate, snap.yield_2yr, snap.yield_spread,
                "↑accel" if snap.cpi_accelerating else "↓decel",
            )

            for market in markets:
                if kill_switch.is_hard_stopped:
                    break

                try:
                    orderbook = await kalshi.get_orderbook(market.ticker)
                except Exception as e:
                    logger.warning("[%s] Orderbook fetch failed for %s: %s", loop_name, market.ticker, e)
                    continue

                signal = fomc_strategy.generate_signal(market, orderbook, None)
                if signal is None:
                    continue

                # Position deduplication
                if db.has_open_position(market.ticker):
                    logger.info("[%s] Open position already on %s — skip", loop_name, market.ticker)
                    continue

                # Daily bet cap (FOMC fires rarely but guard anyway)
                if max_daily_bets > 0 and db.count_trades_today(fomc_strategy.name) >= max_daily_bets:
                    logger.info("[%s] Daily bet cap reached for %s — skip", loop_name, fomc_strategy.name)
                    continue

                current_bankroll = db.latest_bankroll() or 50.0
                order_check = kill_switch.check_order_allowed(
                    proposed_usd=1.0,
                    current_bankroll=current_bankroll,
                )
                if not order_check.get("allowed", False):
                    logger.info("[%s] Kill switch blocked: %s", loop_name, order_check.get("reason"))
                    continue

                from src.risk.sizing import calculate_size
                size = calculate_size(
                    edge_pct=signal.edge_pct,
                    win_prob=signal.win_prob,
                    price_cents=signal.price_cents,
                    bankroll_usd=current_bankroll,
                )
                if size is None:
                    continue

                import yaml as _yaml
                with open(PROJECT_ROOT / "config.yaml") as _f:
                    _fcfg = _yaml.safe_load(_f)
                _fslip = _fcfg.get("risk", {}).get("paper_slippage_ticks", 1)
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=fomc_strategy.name,
                    slippage_ticks=_fslip,
                )
                result = paper_exec.execute(
                    ticker=signal.ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=size,
                    reason=signal.reason,
                )
                logger.info(
                    "[%s] Paper trade: %s %s @ %d¢ $%.2f",
                    loop_name,
                    result["side"].upper(),
                    result["ticker"],
                    result.get("fill_price_cents", result.get("price_cents", 0)),
                    result["cost_usd"],
                )

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("[%s] Unexpected error: %s", loop_name, e, exc_info=True)

        await asyncio.sleep(FOMC_POLL_INTERVAL_SEC)


# ── Settlement polling loop ────────────────────────────────────────────

async def settlement_loop(kalshi, db, kill_switch):
    """
    Background loop: detect settled markets and record outcomes in DB.

    Polls every SETTLEMENT_POLL_SEC seconds. For each open trade, fetches the
    market from Kalshi. When a market status is 'finalized', settles the trade
    and records P&L (same formula for paper + live: win/loss based on result).

    Also notifies kill_switch of each outcome so consecutive-loss and
    total-bankroll-loss hard stops are properly tracked.
    """
    from src.execution.paper import PaperExecutor
    paper_exec = PaperExecutor(db=db, strategy_name="settlement")

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
                    won = result == trade["side"]
                    logger.info(
                        "[settle] %s trade %d (%s %s @ %d¢ ×%d): result=%s P&L=$%.2f",
                        mode, trade["id"], trade["side"].upper(), ticker,
                        trade["price_cents"], trade["count"],
                        result.upper(), pnl_cents / 100.0,
                    )

                    # Notify kill switch — drives consecutive-loss and total-loss hard stops
                    if won:
                        kill_switch.record_win()
                    else:
                        kill_switch.record_loss(abs(pnl_cents) / 100.0)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Unexpected error in settlement loop: %s", e, exc_info=True)


# ── PID lock — prevent two bot instances running at the same time ─────

_PID_FILE = PROJECT_ROOT / "bot.pid"


def _acquire_bot_lock() -> Path:
    """
    Write current PID to bot.pid. If another instance is already running,
    print an error and exit. Protects against accidental duplicate runs
    that could double-execute trades and burn API quota.

    Returns the PID file Path so the caller can release it on shutdown.
    """
    if _PID_FILE.exists():
        try:
            existing_pid = int(_PID_FILE.read_text().strip())
            os.kill(existing_pid, 0)  # signal 0 = existence check, no actual signal
            print(f"\nERROR: Bot is already running (PID {existing_pid}).")
            print(f"  If that process crashed, delete {_PID_FILE} and retry.")
            print(f"  To stop a running bot: kill {existing_pid}\n")
            sys.exit(1)
        except ProcessLookupError:
            pass  # Stale PID — process no longer exists, safe to overwrite
        except PermissionError:
            # Process exists but is owned by a different user — it IS running
            print(f"\nERROR: Bot appears to be running under a different user (PID {existing_pid}).")
            print(f"  Cannot verify ownership. Check: ps aux | grep main.py\n")
            sys.exit(1)
        except ValueError:
            pass  # Corrupt PID file — safe to overwrite
    _PID_FILE.write_text(str(os.getpid()))
    logger.info("Bot lock acquired (PID %d)", os.getpid())
    return _PID_FILE


def _release_bot_lock() -> None:
    """Remove the PID file on clean shutdown."""
    try:
        _PID_FILE.unlink(missing_ok=True)
    except Exception as e:
        logger.warning("Could not remove bot.pid: %s", e)


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

    # ── Bot process lock (prevents dual instances) ────────────────────
    _acquire_bot_lock()

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

    # ── Live mode confirmation prompt ─────────────────────────────
    live_confirmed = False
    if live_mode:
        print("\n" + "=" * 60)
        print("  ⚠️  LIVE TRADING MODE — REAL MONEY AT RISK")
        print()
        print("  Both gates are set:")
        print("    ✓ LIVE_TRADING=true in .env")
        print("    ✓ --live flag passed")
        print()
        print("  This will place REAL orders on Kalshi.")
        print("  Review KILL_SWITCH_EVENT.log and verify bankroll before proceeding.")
        confirm = input("  Type 'CONFIRM' to enable live trading: ").strip()
        if confirm != "CONFIRM":
            print("  Live trading not confirmed — exiting.")
            sys.exit(0)
        live_confirmed = True
        print("  ✅ Live trading confirmed.")
        print("=" * 60 + "\n")

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
    from src.data.binance import load_eth_from_config as eth_binance_load
    from src.strategies.btc_lag import load_from_config as strategy_load
    from src.strategies.btc_lag import load_eth_lag_from_config as eth_lag_load
    from src.strategies.btc_drift import load_from_config as drift_strategy_load
    from src.strategies.btc_drift import load_eth_drift_from_config as eth_drift_load
    from src.strategies.orderbook_imbalance import (
        load_btc_imbalance_from_config,
        load_eth_imbalance_from_config,
    )
    from src.strategies.weather_forecast import load_from_config as weather_strategy_load
    from src.data.weather import load_nyc_weather_from_config as weather_feed_load
    from src.strategies.fomc_rate import load_from_config as fomc_strategy_load
    from src.data.fred import load_from_config as fred_feed_load
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

    # ── Start Binance feeds ───────────────────────────────────────────
    logger.info("Starting Binance BTC feed...")
    btc_feed = binance_load()
    await btc_feed.start()

    logger.info("Starting Binance ETH feed...")
    eth_feed = eth_binance_load()
    await eth_feed.start()

    # ── Load strategies ───────────────────────────────────────────────
    strategy = strategy_load()
    logger.info("Strategy loaded: %s", strategy.name)
    drift_strategy = drift_strategy_load()
    logger.info("Strategy loaded: %s (paper-only data collection)", drift_strategy.name)
    eth_lag_strategy = eth_lag_load()
    logger.info("Strategy loaded: %s (paper-only ETH lag)", eth_lag_strategy.name)
    eth_drift_strategy = eth_drift_load()
    logger.info("Strategy loaded: %s (paper-only ETH drift)", eth_drift_strategy.name)
    btc_imbalance_strategy = load_btc_imbalance_from_config()
    logger.info("Strategy loaded: %s (paper-only BTC orderbook imbalance)", btc_imbalance_strategy.name)
    eth_imbalance_strategy = load_eth_imbalance_from_config()
    logger.info("Strategy loaded: %s (paper-only ETH orderbook imbalance)", eth_imbalance_strategy.name)
    weather_feed = weather_feed_load()
    weather_strategy = weather_strategy_load()
    logger.info("Strategy loaded: %s (paper-only NYC weather forecast)", weather_strategy.name)
    fred_feed = fred_feed_load()
    fomc_strategy = fomc_strategy_load()
    logger.info("Strategy loaded: %s (paper-only FOMC yield curve, fires ~8x/year)", fomc_strategy.name)

    # ── Run ───────────────────────────────────────────────────────────
    _configured_markets = config.get("strategy", {}).get("markets", ["KXBTC15M"])
    if not _configured_markets:
        print("ERROR: config.yaml strategy.markets is empty. Add at least one ticker (e.g., KXBTC15M).")
        sys.exit(1)
    btc_series_ticker = _configured_markets[0]
    eth_series_ticker = config.get("strategy", {}).get("eth_markets", ["KXETH15M"])[0]
    max_daily_bets = config.get("risk", {}).get("max_daily_bets_per_strategy", 5)

    # Stagger the 4 loops by 7-8s each to spread Kalshi API calls evenly:
    #   btc_lag=0s, eth_lag=7s, btc_drift=15s, eth_drift=22s
    trade_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            strategy=strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker=btc_series_ticker,
            loop_name="trading",
            initial_delay_sec=0.0,
            max_daily_bets=max_daily_bets,
        ),
        name="trading_loop",
    )
    # ETH lag: paper-only, stagger 7s
    eth_lag_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_lag_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_trading",
            initial_delay_sec=7.0,
            max_daily_bets=max_daily_bets,
        ),
        name="eth_lag_loop",
    )
    # BTC drift: paper-only, stagger 15s
    drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            strategy=drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker=btc_series_ticker,
            loop_name="drift",
            initial_delay_sec=15.0,
            max_daily_bets=max_daily_bets,
        ),
        name="drift_loop",
    )
    # ETH drift: paper-only, stagger 22s
    eth_drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_drift",
            initial_delay_sec=22.0,
            max_daily_bets=max_daily_bets,
        ),
        name="eth_drift_loop",
    )
    # BTC orderbook imbalance: paper-only, stagger 29s
    btc_imbalance_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            strategy=btc_imbalance_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker=btc_series_ticker,
            loop_name="btc_imbalance",
            initial_delay_sec=29.0,
            max_daily_bets=max_daily_bets,
        ),
        name="btc_imbalance_loop",
    )
    # ETH orderbook imbalance: paper-only, stagger 36s (offset from ETH drift)
    eth_imbalance_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_imbalance_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_imbalance",
            initial_delay_sec=36.0,
            max_daily_bets=max_daily_bets,
        ),
        name="eth_imbalance_loop",
    )
    # Weather forecast: paper-only, polls every 5 min, stagger 43s
    weather_series = config.get("strategy", {}).get("weather", {}).get("series_ticker", "HIGHNY")
    weather_task = asyncio.create_task(
        weather_loop(
            kalshi=kalshi,
            weather_strategy=weather_strategy,
            weather_feed=weather_feed,
            kill_switch=kill_switch,
            db=db,
            series_ticker=weather_series,
            loop_name="weather",
            initial_delay_sec=43.0,
            max_daily_bets=max_daily_bets,
        ),
        name="weather_loop",
    )
    # FOMC rate: paper-only, polls every 30 min, stagger 51s
    fomc_task = asyncio.create_task(
        fomc_loop(
            kalshi=kalshi,
            fomc_strategy=fomc_strategy,
            fred_feed=fred_feed,
            kill_switch=kill_switch,
            db=db,
            series_ticker="KXFEDDECISION",
            loop_name="fomc",
            initial_delay_sec=51.0,
            max_daily_bets=max_daily_bets,
        ),
        name="fomc_loop",
    )
    settle_task = asyncio.create_task(
        settlement_loop(kalshi=kalshi, db=db, kill_switch=kill_switch),
        name="settlement_loop",
    )

    # ── Signal handlers (clean shutdown on SIGTERM/SIGHUP) ───────────
    import signal as _signal
    _loop = asyncio.get_running_loop()

    def _on_signal(signame: str) -> None:
        logger.info("Received %s — requesting clean shutdown", signame)
        trade_task.cancel()
        eth_lag_task.cancel()
        drift_task.cancel()
        eth_drift_task.cancel()
        btc_imbalance_task.cancel()
        eth_imbalance_task.cancel()
        weather_task.cancel()
        fomc_task.cancel()
        settle_task.cancel()

    for _sig, _sname in ((_signal.SIGTERM, "SIGTERM"), (_signal.SIGHUP, "SIGHUP")):
        _loop.add_signal_handler(_sig, lambda n=_sname: _on_signal(n))

    try:
        await asyncio.gather(
            trade_task, eth_lag_task, drift_task, eth_drift_task,
            btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task, settle_task,
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass  # Normal shutdown — SIGTERM or Ctrl+C; finally block handles cleanup
    finally:
        trade_task.cancel()
        eth_lag_task.cancel()
        drift_task.cancel()
        eth_drift_task.cancel()
        btc_imbalance_task.cancel()
        eth_imbalance_task.cancel()
        weather_task.cancel()
        fomc_task.cancel()
        settle_task.cancel()
        await asyncio.gather(
            trade_task, eth_lag_task, drift_task, eth_drift_task,
            btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task, settle_task,
            return_exceptions=True,
        )
        logger.info("Stopping feeds and connections...")
        await btc_feed.stop()
        await eth_feed.stop()
        await kalshi.close()
        db.close()
        _release_bot_lock()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Ensure required directories exist (safe on fresh clone)
    (PROJECT_ROOT / "logs" / "errors").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs" / "trades").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    asyncio.run(main())
