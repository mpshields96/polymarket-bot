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
import contextlib
import logging
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

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

POLL_INTERVAL_SEC = 10      # How often to check markets and generate signals
                             # Reduced from 30s→10s (Session 44 overhaul) — 3x latency improvement.
                             # At 6 loops × 1 get_markets / 10s = 0.6 req/s (well within 20/s Basic limit).
                             # Phase 2 (Session 45): event-driven asyncio.Condition trigger implemented.
                             # Drift loops wake on BTC price move OR POLL_INTERVAL_SEC timeout.
BANKROLL_SNAPSHOT_SEC = 300  # How often to record bankroll to DB (5 min)
SETTLEMENT_POLL_SEC = 60    # How often to check for settled markets

# ── No-live-bets watchdog thresholds ───────────────────────────────────
# If btc_drift (the only live strategy) has been running with 0 new live bets
# for this long, something is wrong. Does NOT force bets — only surfaces the issue.
_NO_LIVE_BETS_WARN_HOURS = 24    # WARNING level: review kill switch + signal logs
_NO_LIVE_BETS_CRITICAL_HOURS = 72  # CRITICAL level: systematic debugging required
_NO_LIVE_BETS_WARN_INTERVAL_SEC = 3600  # Re-emit watchdog warning at most once/hr


# ── Event-driven price trigger ─────────────────────────────────────────
# Phase 2 latency improvement: instead of sleeping for POLL_INTERVAL_SEC every cycle,
# drift loops wait on an asyncio.Condition that fires when BTC price moves ≥ threshold.
# If no BTC move fires within POLL_INTERVAL_SEC, the loop wakes up anyway (fallback).
# This reduces average latency from 5s (half of 10s) to ~1-3s on active price moves.
# Benefits sol_drift and eth_drift most — less HFT saturation on those markets.
# btc_price_monitor() broadcasts to ALL waiting loops simultaneously (notify_all).


async def btc_price_monitor(
    btc_feed,
    condition: asyncio.Condition,
    min_move_pct: float = 0.05,
    check_interval_sec: float = 0.5,
) -> None:
    """
    Monitor BTC price for significant moves; broadcast to all waiting trading loops.

    Fires condition.notify_all() when BTC price moves >= min_move_pct from the
    last-notified price. Reference price updates after each notification so moves
    are measured from the new base (not from session start).

    Args:
        btc_feed: BinanceFeed (or DualPriceFeed). Uses current_price() — no stale check here
                  (loops handle stale themselves via strategy.generate_signal()).
        condition: asyncio.Condition shared with all trading_loop callers.
        min_move_pct: Minimum % price change to trigger a notification. Default 0.05% =
                      ~$33 move on $67k BTC — fires ~5-15x per hour in normal volatility.
        check_interval_sec: How often to poll btc_feed.current_price(). Default 0.5s.
    """
    last_price: Optional[float] = None

    while True:
        try:
            price = btc_feed.current_price()
            if price is None:
                pass
            elif last_price is None:
                last_price = price
            else:
                move_pct = abs(price - last_price) / last_price * 100
                if move_pct >= min_move_pct:
                    async with condition:
                        condition.notify_all()
                    last_price = price  # reset: next move measured from new base
                    logger.debug(
                        "[btc_monitor] BTC moved %.3f%% → notified loops (new ref: $%.2f)",
                        move_pct, price,
                    )
            await asyncio.sleep(check_interval_sec)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug("[btc_monitor] Error: %s", e)


async def _wait_for_btc_move(
    condition: Optional[asyncio.Condition],
    timeout: float,
) -> bool:
    """
    Wait for a BTC price move notification or timeout.

    Returns:
        True  — condition was notified (BTC moved) before timeout
        False — timeout expired, or condition is None (plain sleep fallback)

    When condition is None, falls back to asyncio.sleep(timeout) for backward
    compatibility with loops that don't receive the BTC condition (weather/fomc/others).
    """
    if condition is None:
        await asyncio.sleep(timeout)
        return False
    try:
        async with asyncio.timeout(timeout):
            async with condition:
                await condition.wait()
        return True
    except TimeoutError:
        return False


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
    slippage_ticks: int = 1,
    fill_probability: float = 1.0,
    trade_lock: Optional[asyncio.Lock] = None,
    calibration_max_usd: Optional[float] = None,
    direction_filter: Optional[str] = None,
    btc_move_condition: Optional[asyncio.Condition] = None,
    maker_mode: bool = False,
):
    """Main async loop: poll markets, generate signals, execute trades.

    trade_lock: shared asyncio.Lock passed to all live loops. Ensures that the
    check_order_allowed() → execute() → record_trade() sequence is atomic,
    preventing two loops from both passing the hourly rate check before either
    records a trade. Paper loops pass None (no lock needed).

    btc_move_condition: asyncio.Condition shared with btc_price_monitor(). When
    provided, the end-of-loop sleep is replaced by an event-driven wait that wakes
    early on a significant BTC price move OR after POLL_INTERVAL_SEC (whichever is
    sooner). Pass None to fall back to plain asyncio.sleep (weather/fomc/daily loops).
    """
    from src.execution import paper as paper_mod
    import time

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    last_bankroll_snapshot = 0.0
    # Paper/live mode for dedup and daily-cap filtering — computed once, never changes mid-run
    is_paper_mode = not (live_executor_enabled and live_confirmed)

    # ── No-live-bets watchdog state ────────────────────────────────────
    _last_no_bets_warn_ts: float = 0.0  # when we last emitted a watchdog warning

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

            # ── No-live-bets watchdog (live loops only) ───────────────
            # If the live strategy hasn't generated a bet in too long,
            # something is objectively wrong. Surfaces it — never forces bets.
            if (
                live_executor_enabled
                and live_confirmed
                and now - _last_no_bets_warn_ts > _NO_LIVE_BETS_WARN_INTERVAL_SEC
            ):
                _last_live_trades = db.get_trades(is_paper=False, limit=1)
                if _last_live_trades:
                    _last_live_ts = _last_live_trades[0].get("timestamp") or 0.0
                    _elapsed_hr = (now - _last_live_ts) / 3600
                    if _elapsed_hr >= _NO_LIVE_BETS_CRITICAL_HOURS:
                        logger.critical(
                            "[%s] NO LIVE BETS in %.0fhr (threshold: %dhr) — "
                            "something is wrong. Check: kill switch state, signal frequency, "
                            "strategy thresholds, log errors. "
                            "Run: python main.py --health",
                            loop_name, _elapsed_hr, _NO_LIVE_BETS_CRITICAL_HOURS,
                        )
                        _last_no_bets_warn_ts = now
                    elif _elapsed_hr >= _NO_LIVE_BETS_WARN_HOURS:
                        logger.warning(
                            "[%s] No live bets in %.0fhr (warn threshold: %dhr). "
                            "Possible causes: kill switch soft stop, low signal frequency, "
                            "strict thresholds. Run: python main.py --health",
                            loop_name, _elapsed_hr, _NO_LIVE_BETS_WARN_HOURS,
                        )
                        _last_no_bets_warn_ts = now

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

                # Direction filter: block signals on the filtered side.
                # Used to restrict btc_drift to NO-only after YES showed 30% win rate
                # across 20 live bets (vs 61% win rate for NO) — statistically significant
                # underperformance with mechanical explanation (upward BTC drift already
                # priced into Kalshi YES market by HFTs before our signal fires).
                if direction_filter is not None and signal.side != direction_filter:
                    logger.debug(
                        "[%s] Direction filter active: skipping %s signal (only %s allowed)",
                        loop_name, signal.side, direction_filter,
                    )
                    continue

                # Position deduplication — skip if we already have an open bet on this market
                # is_paper_mode ensures live bets don't dedup against paper positions and vice versa
                if db.has_open_position(market.ticker, is_paper=is_paper_mode):
                    logger.info("[%s] Open position already exists on %s — skip",
                                loop_name, market.ticker)
                    continue

                # Daily bet cap (tax protection + quality gate)
                # is_paper_mode ensures paper bets don't eat into the live daily quota
                if max_daily_bets > 0:
                    today_count = db.count_trades_today(strategy.name, is_paper=is_paper_mode)
                    if today_count >= max_daily_bets:
                        logger.info("[%s] Daily bet cap reached (%d/%d) for %s — skip",
                                    loop_name, today_count, max_daily_bets, strategy.name)
                        continue

                # Size the trade (synchronous)
                # kalshi_payout() takes YES price — convert NO price for NO-side signals
                from src.risk.sizing import calculate_size, kalshi_payout
                yes_price_cents_for_payout = (
                    signal.price_cents if signal.side == "yes"
                    else (100 - signal.price_cents)
                )
                payout = kalshi_payout(yes_price_cents_for_payout, signal.side)
                # Use strategy's own min_edge_pct so calculate_size doesn't silently drop
                # signals the strategy already cleared (btc_lag 4%, btc_drift 5% vs 8% default).
                # Signal reaching this point already passed the strategy's edge gate.
                _strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)
                size_result = calculate_size(
                    win_prob=signal.win_prob,
                    payout_per_dollar=payout,
                    edge_pct=signal.edge_pct,
                    bankroll_usd=current_bankroll,
                    min_edge_pct=_strat_min_edge,
                )

                if size_result is None:
                    logger.debug("[main] Sizing returned None for signal on %s", market.ticker)
                    continue

                # Clamp to hard cap — sizing uses stage caps ($5/$10/$15) but the kill switch
                # hard cap is always $5.00. Without this clamp, bankroll > $100 means
                # 5% pct_cap ($5.18) exceeds $5.00 and the kill switch blocks every trade.
                from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
                trade_usd = min(size_result.recommended_usd, _HARD_CAP)
                # Calibration cap: micro-live phase uses $1.00 max to collect real data
                # cheaply. Set calibration_max_usd on the loop call to activate.
                if calibration_max_usd is not None:
                    trade_usd = min(trade_usd, calibration_max_usd)

                # Dynamic scaling: reduce bet size during losing streaks, restore on wins.
                # S60: Addresses asymmetric win/loss problem — prevents large losses from
                # compounding during adverse market conditions. Kill switch consecutive
                # counter is shared across strategies and resets on ANY win.
                _consec = kill_switch._state._consecutive_losses
                if _consec >= 1 and live_executor_enabled and live_confirmed:
                    # Halve for each consecutive loss: 1→50%, 2→25%, 3→12.5%, etc.
                    # Floor at 10% of original size to keep collecting data.
                    _scale = max(0.10, 0.5 ** _consec)
                    _original = trade_usd
                    trade_usd = round(trade_usd * _scale, 2)
                    if trade_usd < _original:
                        logger.info(
                            "[%s] Dynamic scaling: %d consec losses → %.0f%% size (%.2f → %.2f USD)",
                            loop_name, _consec, _scale * 100, _original, trade_usd,
                        )

                # Kill switch pre-trade check (synchronous)
                from src.strategies.btc_lag import BTCLagStrategy
                minutes_remaining = BTCLagStrategy._minutes_remaining(market)

                if live_executor_enabled and live_confirmed:
                    # ── Live path: check → execute → record_trade is atomic ─────
                    # trade_lock serializes all live loops so two strategies can't
                    # both pass check_order_allowed() before either records a trade.
                    # Without the lock, the hourly rate limit can be exceeded by 1
                    # if two loops pass the check concurrently.
                    _lock_ctx = trade_lock if trade_lock is not None else contextlib.nullcontext()
                    async with _lock_ctx:
                        ok, reason = kill_switch.check_order_allowed(
                            trade_usd=trade_usd,
                            current_bankroll_usd=current_bankroll,
                            minutes_remaining=minutes_remaining,
                        )
                        if not ok:
                            logger.info("[main] Kill switch blocked trade: %s", reason)
                            continue

                        from src.execution import live as live_mod
                        # Maker mode: post_only=True with 30s expiration
                        _post_only = maker_mode
                        _expiration_ts = None
                        if maker_mode:
                            import time as _time_mod
                            _expiration_ts = int(_time_mod.time()) + 30
                        result = await live_mod.execute(
                            signal=signal,
                            market=market,
                            orderbook=orderbook,
                            trade_usd=trade_usd,
                            kalshi=kalshi,
                            db=db,
                            live_confirmed=live_confirmed,
                            strategy_name=strategy.name,
                            post_only=_post_only,
                            expiration_ts=_expiration_ts,
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
                            _announce_live_bet(result, strategy_name=strategy.name)
                else:
                    # ── Paper path: only hard stops block, no locking needed ────
                    ok, reason = kill_switch.check_paper_order_allowed(
                        trade_usd=trade_usd,
                        current_bankroll_usd=current_bankroll,
                    )
                    if not ok:
                        logger.info("[main] Kill switch blocked paper trade: %s", reason)
                        continue

                    _slip = slippage_ticks
                    paper_exec = paper_mod.PaperExecutor(
                        db=db,
                        strategy_name=strategy.name,
                        slippage_ticks=_slip,
                        fill_probability=fill_probability,
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

        # Event-driven: wake early on BTC move, or fall back to full timeout.
        # btc_move_condition=None uses plain sleep (weather/fomc/daily loops).
        await _wait_for_btc_move(btc_move_condition, POLL_INTERVAL_SEC)


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

                # Position deduplication (weather is always paper)
                if db.has_open_position(market.ticker, is_paper=True):
                    logger.info("[%s] Open position already on %s — skip", loop_name, market.ticker)
                    continue

                # Daily bet cap (paper only — never counts live bets)
                if max_daily_bets > 0 and db.count_trades_today(weather_strategy.name, is_paper=True) >= max_daily_bets:
                    logger.info("[%s] Daily bet cap reached for %s — skip", loop_name, weather_strategy.name)
                    continue

                # ── Execute (paper only) ──────────────────────────────
                current_bankroll = db.latest_bankroll() or 50.0
                # Paper-only loop: soft stops do not halt calibration data collection
                ok, reason = kill_switch.check_paper_order_allowed(
                    trade_usd=1.0,   # placeholder; sizing is paper-only
                    current_bankroll_usd=current_bankroll,
                )
                if not ok:
                    logger.info("[%s] Kill switch blocked trade: %s", loop_name, reason)
                    continue

                from src.risk.sizing import calculate_size, kalshi_payout as _kp
                from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
                _yes_p = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
                _size_result = calculate_size(
                    win_prob=signal.win_prob,
                    payout_per_dollar=_kp(_yes_p, signal.side),
                    edge_pct=signal.edge_pct,
                    bankroll_usd=current_bankroll,
                )
                if _size_result is None:
                    continue
                _trade_usd = min(_size_result.recommended_usd, _HARD_CAP)

                import yaml as _yaml
                with open(PROJECT_ROOT / "config.yaml") as _f:
                    _wcfg = _yaml.safe_load(_f)
                _wslip = _wcfg.get("risk", {}).get("paper_slippage_ticks", 1)
                _wfill = _wcfg.get("risk", {}).get("paper_fill_probability", 1.0)
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=weather_strategy.name,
                    slippage_ticks=_wslip,
                    fill_probability=_wfill,
                )
                result = paper_exec.execute(
                    ticker=signal.ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=_trade_usd,
                    reason=signal.reason,
                )
                if result is None:
                    continue
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
UNEMPLOYMENT_POLL_INTERVAL_SEC = 1800   # 30 min — KXUNRATE markets don't move every second


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

                # Position deduplication (fomc is always paper)
                if db.has_open_position(market.ticker, is_paper=True):
                    logger.info("[%s] Open position already on %s — skip", loop_name, market.ticker)
                    continue

                # Daily bet cap (paper only — never counts live bets)
                if max_daily_bets > 0 and db.count_trades_today(fomc_strategy.name, is_paper=True) >= max_daily_bets:
                    logger.info("[%s] Daily bet cap reached for %s — skip", loop_name, fomc_strategy.name)
                    continue

                current_bankroll = db.latest_bankroll() or 50.0
                # Paper-only loop: soft stops do not halt calibration data collection
                ok, reason = kill_switch.check_paper_order_allowed(
                    trade_usd=1.0,
                    current_bankroll_usd=current_bankroll,
                )
                if not ok:
                    logger.info("[%s] Kill switch blocked: %s", loop_name, reason)
                    continue

                from src.risk.sizing import calculate_size, kalshi_payout as _kp
                from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
                _yes_p = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
                _size_result = calculate_size(
                    win_prob=signal.win_prob,
                    payout_per_dollar=_kp(_yes_p, signal.side),
                    edge_pct=signal.edge_pct,
                    bankroll_usd=current_bankroll,
                )
                if _size_result is None:
                    continue
                _trade_usd = min(_size_result.recommended_usd, _HARD_CAP)

                import yaml as _yaml
                with open(PROJECT_ROOT / "config.yaml") as _f:
                    _fcfg = _yaml.safe_load(_f)
                _fslip = _fcfg.get("risk", {}).get("paper_slippage_ticks", 1)
                _ffill = _fcfg.get("risk", {}).get("paper_fill_probability", 1.0)
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=fomc_strategy.name,
                    slippage_ticks=_fslip,
                    fill_probability=_ffill,
                )
                result = paper_exec.execute(
                    ticker=signal.ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=_trade_usd,
                    reason=signal.reason,
                )
                if result is None:
                    continue
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


# ── Unemployment rate trading loop ─────────────────────────────────────


async def unemployment_loop(
    kalshi,
    unemployment_strategy,
    fred_feed,
    kill_switch,
    db,
    series_ticker: str = "KXUNRATE",
    loop_name: str = "unemployment",
    initial_delay_sec: float = 58.0,
    max_daily_bets: int = 5,
):
    """
    Unemployment rate trading loop.

    Fetches KXUNRATE markets every 30 min.
    Refreshes FRED feed (UNRATE data) if stale.
    Only active within days_before_release of next BLS Employment Situation date.
    Paper-only — BLS linear trend model needs calibration over multiple releases.
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

            # Refresh FRED feed if stale (blocking ~800ms for 4 CSV fetches incl. UNRATE)
            if fred_feed.is_stale:
                ok = fred_feed.refresh()
                if not ok:
                    logger.warning("[%s] FRED refresh failed — skipping cycle", loop_name)
                    await asyncio.sleep(UNEMPLOYMENT_POLL_INTERVAL_SEC)
                    continue

            snap = fred_feed.snapshot()
            if snap is None:
                await asyncio.sleep(UNEMPLOYMENT_POLL_INTERVAL_SEC)
                continue

            # Fetch KXUNRATE markets
            try:
                markets = await kalshi.get_markets(series_ticker=series_ticker, status="open")
            except Exception as e:
                logger.warning("[%s] Failed to fetch markets: %s", loop_name, e)
                await asyncio.sleep(UNEMPLOYMENT_POLL_INTERVAL_SEC)
                continue

            if not markets:
                forecast_str = (
                    f"forecast={snap.unrate_forecast:.2f}%"
                    if snap.unrate_latest != 0.0 else "no UNRATE data"
                )
                logger.info(
                    "[%s] No open %s markets found (%s)",
                    loop_name, series_ticker, forecast_str,
                )
                await asyncio.sleep(UNEMPLOYMENT_POLL_INTERVAL_SEC)
                continue

            forecast_str = (
                f"{snap.unrate_forecast:.2f}%"
                if snap.unrate_latest != 0.0 else "n/a"
            )
            logger.info(
                "[%s] Evaluating %d KXUNRATE market(s) | forecast=%s",
                loop_name, len(markets), forecast_str,
            )

            for market in markets:
                if kill_switch.is_hard_stopped:
                    break

                try:
                    orderbook = await kalshi.get_orderbook(market.ticker)
                except Exception as e:
                    logger.warning("[%s] Orderbook fetch failed for %s: %s", loop_name, market.ticker, e)
                    continue

                signal = unemployment_strategy.generate_signal(market, orderbook, None)
                if signal is None:
                    continue

                # Position deduplication (unemployment is always paper)
                if db.has_open_position(market.ticker, is_paper=True):
                    logger.info("[%s] Open position already on %s — skip", loop_name, market.ticker)
                    continue

                # Daily bet cap (paper only — never counts live bets)
                if max_daily_bets > 0 and db.count_trades_today(unemployment_strategy.name, is_paper=True) >= max_daily_bets:
                    logger.info("[%s] Daily bet cap reached for %s — skip", loop_name, unemployment_strategy.name)
                    continue

                current_bankroll = db.latest_bankroll() or 50.0
                # Paper-only loop: soft stops do not halt calibration data collection
                ok, reason = kill_switch.check_paper_order_allowed(
                    trade_usd=1.0,
                    current_bankroll_usd=current_bankroll,
                )
                if not ok:
                    logger.info("[%s] Kill switch blocked: %s", loop_name, reason)
                    continue

                from src.risk.sizing import calculate_size, kalshi_payout as _kp
                from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
                _yes_p = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
                _size_result = calculate_size(
                    win_prob=signal.win_prob,
                    payout_per_dollar=_kp(_yes_p, signal.side),
                    edge_pct=signal.edge_pct,
                    bankroll_usd=current_bankroll,
                )
                if _size_result is None:
                    continue
                _trade_usd = min(_size_result.recommended_usd, _HARD_CAP)

                import yaml as _yaml
                with open(PROJECT_ROOT / "config.yaml") as _f:
                    _ucfg = _yaml.safe_load(_f)
                _uslip = _ucfg.get("risk", {}).get("paper_slippage_ticks", 1)
                _ufill = _ucfg.get("risk", {}).get("paper_fill_probability", 1.0)
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=unemployment_strategy.name,
                    slippage_ticks=_uslip,
                    fill_probability=_ufill,
                )
                result = paper_exec.execute(
                    ticker=signal.ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=_trade_usd,
                    reason=signal.reason,
                )
                if result is None:
                    continue
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

        await asyncio.sleep(UNEMPLOYMENT_POLL_INTERVAL_SEC)


# ── Crypto daily (KXBTCD/KXETHD/KXSOLD) trading loop ─────────────────

CRYPTO_DAILY_POLL_INTERVAL_SEC = 300   # 5 min — hourly markets move slowly


async def crypto_daily_loop(
    kalshi,
    asset_feed,
    strategy,
    kill_switch,
    db,
    loop_name: str = "btc_daily",
    initial_delay_sec: float = 0.0,
    max_daily_bets: int = 5,
    direction_filter: Optional[str] = None,
):
    """
    Kalshi daily crypto market loop (KXBTCD / KXETHD / KXSOLD).

    Each series has 24 hourly settlement slots per day. This loop:
    1. Tracks session_open (asset price at midnight UTC — resets each day)
    2. Fetches all open markets for the series (up to 500 per poll)
    3. Passes ALL markets to CryptoDailyStrategy.generate_signal()
       — the strategy picks the ATM market and applies drift signal internally
    4. Paper-executes any signal that passes edge + price guard filters

    Paper-only — collecting calibration data for future live evaluation.
    """
    from src.execution import paper as paper_mod
    from datetime import date as _date
    import yaml as _yaml

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    session_open: Optional[float] = None
    session_open_date: Optional[_date] = None

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.critical("[%s] Kill switch HARD STOPPED. Halting.", loop_name)
                break

            # ── Current spot price ────────────────────────────────────
            spot = asset_feed.current_price()
            if spot is None or spot <= 0:
                logger.debug("[%s] No spot price yet — waiting", loop_name)
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Session open tracking (reset at midnight UTC) ─────────
            today_utc = datetime.now(timezone.utc).date()
            if session_open is None or session_open_date != today_utc:
                session_open = spot
                session_open_date = today_utc
                logger.info(
                    "[%s] Session open reset: $%.2f (UTC date %s)",
                    loop_name, session_open, today_utc,
                )

            # ── Fetch all open markets for this series ────────────────
            try:
                markets = await kalshi.get_markets(
                    series_ticker=strategy.series_ticker,
                    status="open",
                    limit=500,
                )
            except Exception as e:
                logger.warning("[%s] Failed to fetch markets: %s", loop_name, e)
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            if not markets:
                logger.debug(
                    "[%s] No open %s markets found", loop_name, strategy.series_ticker
                )
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            logger.debug(
                "[%s] Evaluating %d %s market(s) | spot=$%.2f session_open=$%.2f drift=%.3f%%",
                loop_name, len(markets), strategy.series_ticker,
                spot, session_open, 100 * (spot - session_open) / session_open,
            )

            # ── Generate signal (strategy picks ATM internally) ───────
            signal = strategy.generate_signal(
                spot=spot,
                session_open=session_open,
                markets=markets,
            )

            if signal is None:
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Loop-level direction filter (defense-in-depth) ────────
            # Mirrors the guard in trading_loop. Strategy already filters, but
            # this protects against future misconfiguration where strategy is
            # constructed without direction_filter.
            if direction_filter is not None and signal.side != direction_filter:
                logger.debug(
                    "[%s] Direction filter active: skipping %s signal (only %s allowed)",
                    loop_name, signal.side, direction_filter,
                )
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Position deduplication ────────────────────────────────
            if db.has_open_position(signal.ticker, is_paper=True):
                logger.info(
                    "[%s] Open position already on %s — skip",
                    loop_name, signal.ticker,
                )
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Daily bet cap ─────────────────────────────────────────
            if max_daily_bets > 0 and db.count_trades_today(strategy.name, is_paper=True) >= max_daily_bets:
                logger.info(
                    "[%s] Daily paper bet cap (%d) reached — skip",
                    loop_name, max_daily_bets,
                )
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Kill switch (paper path) ──────────────────────────────
            current_bankroll = db.latest_bankroll() or 50.0
            ok, block_reason = kill_switch.check_paper_order_allowed(
                trade_usd=1.0,
                current_bankroll_usd=current_bankroll,
            )
            if not ok:
                logger.info("[%s] Kill switch blocked paper trade: %s", loop_name, block_reason)
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue

            # ── Size + execute (paper) ────────────────────────────────
            from src.risk.sizing import calculate_size, kalshi_payout as _kp
            from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP

            _yes_p = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
            _size_result = calculate_size(
                win_prob=signal.win_prob,
                payout_per_dollar=_kp(_yes_p, signal.side),
                edge_pct=signal.edge_pct,
                bankroll_usd=current_bankroll,
                min_edge_pct=strategy._min_edge_pct,
            )
            if _size_result is None:
                await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
                continue
            _trade_usd = min(_size_result.recommended_usd, _HARD_CAP)

            with open(PROJECT_ROOT / "config.yaml") as _f:
                _cfg = _yaml.safe_load(_f)
            _slip = _cfg.get("risk", {}).get("paper_slippage_ticks", 3)
            _fill = _cfg.get("risk", {}).get("paper_fill_probability", 1.0)

            paper_exec = paper_mod.PaperExecutor(
                db=db,
                strategy_name=strategy.name,
                slippage_ticks=_slip,
                fill_probability=_fill,
            )
            result = paper_exec.execute(
                ticker=signal.ticker,
                side=signal.side,
                price_cents=signal.price_cents,
                size_usd=_trade_usd,
                reason=signal.reason,
            )
            if result is not None:
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

        await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)


# ── Daily sniper loop (KXBTCD near-expiry paper sniping) ──────────────

_DAILY_SNIPER_POLL_SEC = 60   # 60s poll — needs to catch entry in 30-90min window
_DAILY_SNIPER_LIVE_CAP_USD = 1.0  # Conservative live cap for initial ramp-up (CCA REQ-035)
_ECONOMICS_SNIPER_POLL_SEC = 300  # 5-min poll — 48h window, no urgency


async def daily_sniper_loop(
    kalshi,
    btc_feed,
    db,
    kill_switch,
    initial_delay_sec: float = 60.0,
    max_daily_bets: int = 10,
    live_executor_enabled: bool = False,
    live_confirmed: bool = False,
    trade_lock: Optional[asyncio.Lock] = None,
):
    """
    KXBTCD near-expiry sniping loop.

    Targets KXBTCD daily threshold markets when YES or NO price is 90-94c
    AND settlement is within 90 minutes AND coin direction is consistent.

    Academic basis: same favorite-longshot bias (FLB) as expiry_sniper_v1.
    CCA REQ-026: academic validation. 10/30 paper bets settled. Now live with 1 USD cap.

    Series: KXBTCD only (BTC daily threshold). KXETHD/KXSOLD can be added
    after KXBTCD validates (same code, different series_ticker + feed).

    Price ceiling: 94c (consistent with live sniper ceiling, S130).
    Drift reference: session_open = BTC price at midnight UTC (same as crypto_daily_loop).
    Live sizing: _DAILY_SNIPER_LIVE_CAP_USD (1 USD hard cap, conservative ramp-up).
    """
    from src.strategies.daily_sniper import make_daily_sniper, DAILY_SNIPER_MAX_PRICE_CENTS
    from src.execution.paper import PaperExecutor
    from datetime import date as _date
    import yaml as _yaml
    import contextlib

    strategy = make_daily_sniper()
    paper_exec = PaperExecutor(
        db=db,
        strategy_name=strategy.name,
        slippage_ticks=1,
        fill_probability=1.0,
    )

    if initial_delay_sec > 0:
        logger.info("[daily_sniper] Startup delay %.0fs (stagger)", initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    is_paper_mode = not (live_executor_enabled and live_confirmed)
    _mode_label = "paper" if is_paper_mode else "LIVE"
    logger.info(
        "[daily_sniper] Started — %s KXBTCD 90-94c near-expiry sniping (cap=%.2f USD)",
        _mode_label, _DAILY_SNIPER_LIVE_CAP_USD if not is_paper_mode else strategy.PAPER_CALIBRATION_USD,
    )

    session_open: Optional[float] = None
    session_open_date: Optional[_date] = None

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.debug("[daily_sniper] Hard stop active — skipping poll")
                await asyncio.sleep(60)
                continue

            # ── Current BTC spot price ────────────────────────────────
            spot = btc_feed.current_price() if not btc_feed.is_stale else None
            if spot is None or spot <= 0:
                logger.debug("[daily_sniper] BTC feed stale — waiting")
                await asyncio.sleep(_DAILY_SNIPER_POLL_SEC)
                continue

            # ── Session open tracking (reset at midnight UTC) ─────────
            today_utc = datetime.now(timezone.utc).date()
            if session_open is None or session_open_date != today_utc:
                session_open = spot
                session_open_date = today_utc
                logger.info(
                    "[daily_sniper] Session open reset: $%.2f (UTC date %s)",
                    session_open, today_utc,
                )

            coin_drift_pct = (spot - session_open) / session_open if session_open > 0 else 0.0

            # ── Fetch KXBTCD markets ──────────────────────────────────
            try:
                markets = await kalshi.get_markets(
                    series_ticker="KXBTCD",
                    status="open",
                    limit=500,
                )
            except Exception as e:
                logger.warning("[daily_sniper] Market fetch failed: %s", e)
                await asyncio.sleep(_DAILY_SNIPER_POLL_SEC)
                continue

            if not markets:
                logger.debug("[daily_sniper] No open KXBTCD markets found")
                await asyncio.sleep(_DAILY_SNIPER_POLL_SEC)
                continue

            # ── Evaluate each market ──────────────────────────────────
            for market in markets:
                ticker = market.ticker

                # Ceiling check: skip markets where the favored side is AT or above 94c.
                # Uses >= (not >) to account for 1-tick paper slippage:
                #   bid=94c → execution=95c (above ceiling) → must block.
                #   bid=93c → execution=94c (at ceiling) → allowed.
                # Bug history: S131 fix: AND→max(). S132 fix: >→>= for slippage.
                if max(market.yes_price, market.no_price) >= DAILY_SNIPER_MAX_PRICE_CENTS:
                    continue

                # Generate signal (strategy handles time gate + floor + direction)
                signal = strategy.generate_signal(
                    market=market,
                    coin_drift_pct=coin_drift_pct,
                )
                if signal is None:
                    continue

                # Dedup: skip if already have open position
                if db.has_open_position(ticker=ticker, is_paper=is_paper_mode):
                    logger.debug("[daily_sniper] Already have open position for %s — skip", ticker)
                    continue

                # Daily bet cap
                if max_daily_bets > 0:
                    today_count = db.count_trades_today(
                        strategy=strategy.name, is_paper=is_paper_mode
                    )
                    if today_count >= max_daily_bets:
                        logger.info(
                            "[daily_sniper] Daily %s cap (%d/%d) reached",
                            _mode_label, today_count, max_daily_bets,
                        )
                        break

                current_bankroll = db.latest_bankroll() or 50.0

                if not is_paper_mode:
                    # ═══ LIVE PATH ═══════════════════════════════════════
                    # Price slippage guard — skip if price drifted 3c+ from signal
                    _live_price = market.yes_price if signal.side == "yes" else market.no_price
                    _MAX_SLIPPAGE_CENTS = 3
                    if _live_price < signal.price_cents - _MAX_SLIPPAGE_CENTS:
                        logger.warning(
                            "[daily_sniper] %s %s: price slipped %dc (signal=%dc, now=%dc) — skip",
                            ticker, signal.side.upper(),
                            signal.price_cents - _live_price, signal.price_cents, _live_price,
                        )
                        continue

                    # Fee floor: skip if execution price ≥ 99c (0 net per contract)
                    if _live_price >= 99:
                        logger.info(
                            "[daily_sniper] %s %s: price at %dc — skip (99c+ = 0 net)",
                            ticker, signal.side.upper(), _live_price,
                        )
                        continue

                    # Fetch orderbook
                    try:
                        orderbook = await kalshi.get_orderbook(ticker)
                    except Exception as ob_exc:
                        logger.warning("[daily_sniper] Orderbook fetch failed for %s: %s", ticker, ob_exc)
                        continue

                    # Sizing: conservative 1 USD cap for daily sniper ramp-up
                    from src.risk.kill_switch import MAX_TRADE_PCT as _MAX_PCT
                    _pct_max = round(current_bankroll * _MAX_PCT, 2) - 0.01
                    trade_usd = min(_DAILY_SNIPER_LIVE_CAP_USD, max(0.01, _pct_max))

                    # Atomic: lock → kill_switch → execute → record_trade
                    _lock_ctx = trade_lock if trade_lock is not None else contextlib.nullcontext()
                    async with _lock_ctx:
                        ok, block_reason = kill_switch.check_order_allowed(
                            trade_usd=trade_usd,
                            current_bankroll_usd=current_bankroll,
                            minutes_remaining=None,
                        )
                        if not ok:
                            logger.info("[daily_sniper] Kill switch blocked live order: %s", block_reason)
                            continue

                        from src.execution import live as live_mod
                        result = await live_mod.execute(
                            signal=signal,
                            market=market,
                            orderbook=orderbook,
                            trade_usd=trade_usd,
                            kalshi=kalshi,
                            db=db,
                            live_confirmed=live_confirmed,
                            strategy_name=strategy.name,
                            price_guard_min=1,
                            price_guard_max=99,
                            max_slippage_cents=3,
                        )
                        if result:
                            kill_switch.record_trade()
                            secs_left = strategy._seconds_remaining(market) or 0
                            logger.info(
                                "[daily_sniper] [LIVE] BUY %s %s @ %d¢ %.2f USD"
                                " | drift=%+.3f%% | %ds left | trade_id=%s",
                                ticker, signal.side.upper(),
                                result.get("price_cents", 0),
                                result["cost_usd"],
                                coin_drift_pct * 100,
                                secs_left,
                                result.get("trade_id", "?"),
                            )
                            _announce_live_bet(result, strategy_name=strategy.name)
                else:
                    # ═══ PAPER PATH ══════════════════════════════════════
                    ok, block_reason = kill_switch.check_paper_order_allowed(
                        trade_usd=strategy.PAPER_CALIBRATION_USD,
                        current_bankroll_usd=current_bankroll,
                    )
                    if not ok:
                        logger.info("[daily_sniper] Kill switch blocked paper order: %s", block_reason)
                        continue

                    result = paper_exec.execute(
                        ticker=ticker,
                        side=signal.side,
                        price_cents=signal.price_cents,
                        size_usd=strategy.PAPER_CALIBRATION_USD,
                        reason=signal.reason,
                    )
                    if result:
                        secs_left = strategy._seconds_remaining(market) or 0
                        logger.info(
                            "[daily_sniper] [paper] BUY %s %s @ %d¢ USD %.2f"
                            " | drift=%+.3f%% | %ds left | trade_id=%s",
                            ticker, signal.side.upper(), signal.price_cents,
                            strategy.PAPER_CALIBRATION_USD,
                            coin_drift_pct * 100,
                            secs_left,
                            result.get("trade_id", "?"),
                        )

        except asyncio.CancelledError:
            logger.info("[daily_sniper] Loop cancelled — exiting")
            break
        except Exception as exc:
            logger.warning("[daily_sniper] Unexpected error: %s", exc, exc_info=True)

        await asyncio.sleep(_DAILY_SNIPER_POLL_SEC)


async def economics_sniper_loop(
    kalshi,
    db,
    kill_switch,
    initial_delay_sec: float = 180.0,
    max_daily_bets: int = 5,
):
    """
    KXCPI/KXGDP near-settlement paper sniping loop (K2 expansion).

    Paper-only. Targets KXCPI-* and KXGDP-* markets when YES or NO price
    is 88-93c AND settlement is within 48h.

    Academic basis: Burgi et al. (2026) [SSRN 5502658] — FLB in economics
    prediction markets is strongest 24-48h before settlement.

    No coin_drift_pct required — pure FLB signal (price + time proximity).
    CCA REQ-032: entry YES>=88c, 24-48h window, 0.5x Kelly. Paper phase.
    Entry window: April 8 for KXCPI-26MAR-T0.6 (closes April 10).

    Poll interval: 5 min (48h window, no urgency vs 14-min crypto window).
    """
    from src.strategies.economics_sniper import make_economics_sniper
    from src.execution.paper import PaperExecutor

    strategy = make_economics_sniper()
    paper_exec = PaperExecutor(
        db=db,
        strategy_name=strategy.name,
        slippage_ticks=1,
        fill_probability=1.0,
    )

    if initial_delay_sec > 0:
        logger.info("[economics_sniper] Startup delay %.0fs (stagger)", initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    logger.info("[economics_sniper] Started — paper-only KXCPI/KXGDP 88-93c FLB sniping")

    _SERIES = ("KXCPI", "KXGDP")

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.debug("[economics_sniper] Hard stop active — skipping poll")
                await asyncio.sleep(_ECONOMICS_SNIPER_POLL_SEC)
                continue

            # ── Fetch KXCPI + KXGDP markets ──────────────────────────
            markets = []
            for series in _SERIES:
                try:
                    batch = await kalshi.get_markets(
                        series_ticker=series,
                        status="open",
                        limit=100,
                    )
                    markets.extend(batch or [])
                except Exception as e:
                    logger.debug("[economics_sniper] Fetch %s failed: %s", series, e)

            if not markets:
                logger.debug("[economics_sniper] No open KXCPI/KXGDP markets found")
                await asyncio.sleep(_ECONOMICS_SNIPER_POLL_SEC)
                continue

            # ── Evaluate each market ──────────────────────────────────
            for market in markets:
                ticker = market.ticker

                # Generate signal (strategy handles time gate + floor + ceiling)
                signal = strategy.generate_signal(market=market)
                if signal is None:
                    continue

                # Dedup: skip if already have open position
                if db.has_open_position(ticker=ticker, is_paper=True):
                    logger.debug("[economics_sniper] Already have open position for %s — skip", ticker)
                    continue

                # Daily bet cap
                if max_daily_bets > 0:
                    today_count = db.count_trades_today(strategy=strategy.name, is_paper=True)
                    if today_count >= max_daily_bets:
                        logger.info(
                            "[economics_sniper] Daily paper cap (%d/%d) reached",
                            today_count, max_daily_bets,
                        )
                        break

                # Kill switch (paper path)
                current_bankroll = db.latest_bankroll() or 50.0
                ok, block_reason = kill_switch.check_paper_order_allowed(
                    trade_usd=strategy.PAPER_CALIBRATION_USD,
                    current_bankroll_usd=current_bankroll,
                )
                if not ok:
                    logger.info("[economics_sniper] Kill switch blocked paper order: %s", block_reason)
                    continue

                # Execute paper bet
                result = paper_exec.execute(
                    ticker=ticker,
                    side=signal.side,
                    price_cents=signal.price_cents,
                    size_usd=strategy.PAPER_CALIBRATION_USD,
                    reason=signal.reason,
                )
                if result:
                    secs_left = strategy._seconds_remaining(market) or 0
                    logger.info(
                        "[economics_sniper] [paper] BUY %s %s @ %d¢ USD %.2f"
                        " | %ds to settlement | trade_id=%s",
                        ticker, signal.side.upper(), signal.price_cents,
                        strategy.PAPER_CALIBRATION_USD,
                        secs_left,
                        result.get("trade_id", "?"),
                    )

        except asyncio.CancelledError:
            logger.info("[economics_sniper] Loop cancelled — exiting")
            break
        except Exception as exc:
            logger.warning("[economics_sniper] Unexpected error: %s", exc, exc_info=True)

        await asyncio.sleep(_ECONOMICS_SNIPER_POLL_SEC)


async def maker_sniper_loop(
    kalshi,
    btc_feed,
    eth_feed,
    sol_feed,
    xrp_feed,
    db,
    kill_switch,
    initial_delay_sec: float = 135.0,
    max_daily_bets: int = 5,
):
    """
    Maker-side FLB sniping loop — paper-only calibration phase.

    Same signal selection as expiry_sniper_v1 (FLB at 90-94c, last 14 min,
    coin drift confirmed), but places orders at (ask - 1c) as POST-ONLY limit.

    Academic basis: Becker (2026) — Kalshi makers earn +1.12% structural vs
    takers -1.12%. At 30 sniper bets/day, 1c maker improvement = ~45 USD/month
    pure fee capture even before spread improvement.

    Paper-only (30 fills required before live gate evaluation).
    Orderbook is fetched for EVERY signal to compute maker price and spread check.
    Paper executor fills at maker_price (not ask) to simulate realistic entry.

    CCA REQ-039 implementation: MakerSniperStrategy spec from 2026-03-26.
    Live promotion gate: 30 fills + fill_rate >= 40% + WR within expiry_sniper CI.
    """
    from src.strategies.maker_sniper import MakerSniperStrategy
    from src.execution.paper import PaperExecutor

    strategy = MakerSniperStrategy()
    paper_exec = PaperExecutor(
        db=db,
        strategy_name=strategy.name,
        slippage_ticks=0,          # Paper fills AT maker_price (no additional slippage)
        fill_probability=1.0,      # Paper always fills — real fill rate tracked separately
    )

    _POLL_SEC = 10
    _series_feeds = {
        "KXBTC15M": btc_feed,
        "KXETH15M": eth_feed,
        "KXSOL15M": sol_feed,
        "KXXRP15M": xrp_feed,
    }
    _window_open_price: dict = {}

    logger.info("[maker_sniper] Startup — waiting %.0fs before first poll", initial_delay_sec)
    await asyncio.sleep(initial_delay_sec)
    logger.info(
        "[maker_sniper] Started — paper-only BTC/ETH/SOL/XRP 15M 90-94c maker sniping "
        "(offset=1c, min_spread=2c, expiry=300s)"
    )

    # Same hour block as expiry_sniper — structural weakness at 08:xx UTC
    _BLOCKED_HOURS_UTC = frozenset({8})

    while True:
        try:
            _now_utc_hour = __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).hour
            if _now_utc_hour in _BLOCKED_HOURS_UTC:
                logger.debug(
                    "[maker_sniper] Hour block: %02d:xx UTC — skipping poll",
                    _now_utc_hour,
                )
                await asyncio.sleep(_POLL_SEC)
                continue

            today_paper_count = db.count_trades_today(strategy.name, is_paper=True)
            if today_paper_count >= max_daily_bets:
                logger.debug(
                    "[maker_sniper] Daily paper cap (%d/%d) — skipping until midnight UTC",
                    today_paper_count, max_daily_bets,
                )
                await asyncio.sleep(_POLL_SEC)
                continue

            for series_ticker, feed in _series_feeds.items():
                if feed.is_stale:
                    logger.debug("[maker_sniper] %s feed stale — skip series", series_ticker)
                    continue

                try:
                    markets = await kalshi.get_markets(series_ticker=series_ticker, status="open")
                except Exception as exc:
                    logger.warning("[maker_sniper] Market fetch failed for %s: %s", series_ticker, exc)
                    continue

                if not markets:
                    continue

                current_price = feed.current_price()
                for market in markets:
                    ticker = market.ticker

                    # Track window open price for drift calculation
                    if ticker not in _window_open_price:
                        _window_open_price[ticker] = current_price
                    window_open = _window_open_price[ticker]
                    if window_open and window_open > 0:
                        coin_drift_pct = (current_price - window_open) / window_open
                    else:
                        continue

                    # Generate signal (FLB + ceiling + time + drift checks)
                    signal = strategy.generate_signal(market, coin_drift_pct)
                    if signal is None:
                        continue

                    # Skip if we already have an open paper position in this window
                    if db.has_open_position(ticker, is_paper=True):
                        logger.debug("[maker_sniper] Already have open paper position for %s — skip", ticker)
                        continue

                    # Fetch orderbook to compute maker price
                    try:
                        orderbook = await kalshi.get_orderbook(ticker)
                    except Exception as ob_exc:
                        logger.warning("[maker_sniper] Orderbook fetch failed for %s: %s", ticker, ob_exc)
                        continue

                    # Compute maker price from orderbook
                    maker_price, skip_reason = strategy.compute_maker_adjustment(signal, orderbook)
                    if maker_price is None:
                        logger.debug(
                            "[maker_sniper] %s %s: maker adjustment skipped — %s",
                            ticker, signal.side, skip_reason,
                        )
                        continue

                    # Paper execute at maker_price (simulates 1c price improvement)
                    _current_bankroll = db.latest_bankroll() or 50.0
                    ok, block_reason = kill_switch.check_paper_order_allowed(
                        trade_usd=strategy.PAPER_CALIBRATION_USD,
                        current_bankroll_usd=_current_bankroll,
                    )
                    if not ok:
                        logger.info("[maker_sniper] Kill switch blocked paper order: %s", block_reason)
                        continue

                    result = paper_exec.execute(
                        ticker=ticker,
                        side=signal.side,
                        price_cents=maker_price,     # maker price (ask - 1c), NOT ask
                        size_usd=strategy.PAPER_CALIBRATION_USD,
                        reason=signal.reason + f" | maker_price={maker_price}c",
                    )
                    if result:
                        logger.info(
                            "[maker_sniper] [paper] BUY %s %s @ %dc (maker, ask=%dc) "
                            "USD %.2f | drift=%+.3f%% | trade_id=%s",
                            series_ticker, signal.side.upper(),
                            maker_price, signal.price_cents,
                            strategy.PAPER_CALIBRATION_USD,
                            coin_drift_pct * 100,
                            result.get("trade_id", "?"),
                        )

            # Prune stale window tracking entries
            _window_open_price = {
                k: v for k, v in _window_open_price.items()
                if k in {m.ticker for series_ticker in _series_feeds for m in []}
            }

        except asyncio.CancelledError:
            logger.info("[maker_sniper] Loop cancelled — exiting")
            break
        except Exception as exc:
            logger.warning("[maker_sniper] Unexpected error: %s", exc, exc_info=True)

        await asyncio.sleep(_POLL_SEC)


# ── Bayesian drift model update helper ────────────────────────────────
# Logic lives in src/models/bayesian_settlement.py for clean testability.
from src.models.bayesian_settlement import (
    apply_bayesian_update as _apply_bayesian_update,
    _DRIFT_STRATEGY_NAMES,
)
from src.models.temperature_calibration import StrategyCalibrator as _StrategyCalibrator


# ── Settlement polling loop ────────────────────────────────────────────

async def settlement_loop(kalshi, db, kill_switch, drift_model=None, calibrator=None):
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

            # Only settle Kalshi trades here — Polymarket trades (tec-*, nba-*, etc.)
            # are NOT Kalshi markets and will 404. Kalshi tickers always start with "KX".
            kalshi_trades = [t for t in open_trades if t["ticker"].upper().startswith("KX")]

            # Deduplicate tickers to minimise API calls
            tickers = list({t["ticker"] for t in kalshi_trades})

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
                ticker_trades = [t for t in kalshi_trades if t["ticker"] == ticker]

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
                    # Only count LIVE trades toward daily loss limit (paper losses are not real money)
                    if not trade["is_paper"]:
                        if won:
                            kill_switch.record_win()
                        else:
                            kill_switch.record_loss(abs(pnl_cents) / 100.0)

                        # ── Bayesian posterior + temperature calibration update ────────
                        # Bayesian: updates sigmoid parameter estimates after each settled live drift bet.
                        # Calibrator: updates per-strategy T_s for post-hoc confidence correction.
                        # Sniper / lag bets are excluded — different signal model.
                        _apply_bayesian_update(drift_model, trade, won, calibrator=calibrator)

            # Auto-export CSV after each settlement poll that found settled trades
            if open_trades:
                try:
                    db.export_trades_csv()
                except Exception as e:
                    logger.warning("[settle] CSV export failed: %s", e)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Unexpected error in settlement loop: %s", e, exc_info=True)


# ── Live bet announcement ─────────────────────────────────────────────


def _announce_live_bet(result: dict, strategy_name: str) -> None:
    """
    Fire a prominent log banner and macOS Reminders notification when a live bet is placed.

    Called immediately after live_mod.execute() returns a confirmed result.
    Exceptions from the notification subprocess are always swallowed — never crashes the loop.
    """
    import subprocess

    side = result["side"].upper()
    ticker = result["ticker"]
    cost = result["cost_usd"]
    fill = result.get("fill_price_cents", result.get("price_cents", 0))
    trade_id = result.get("trade_id", "?")

    sep = "=" * 62
    logger.info(sep)
    logger.info(
        "💰 LIVE BET PLACED  ·  %s  ·  %s %s @ %d¢ = $%.2f  ·  trade_id=%s",
        strategy_name, side, ticker, fill, cost, trade_id,
    )
    logger.info(sep)

    msg = f"LIVE BET: {side} {ticker} @ {fill}¢ = ${cost:.2f}"
    body = f"trade_id={trade_id} — {strategy_name}"
    script = (
        f'tell application "Reminders" to make new reminder '
        f'with properties {{name:"{msg}", body:"{body}"}}'
    )
    try:
        subprocess.run(["osascript", "-e", script], timeout=3, capture_output=True)
    except Exception:
        pass  # notification is best-effort; never block the trading loop


# ── Polymarket sports-futures mispricing loop ─────────────────────────

async def sports_futures_loop(
    pm_client,
    db,
    kill_switch,
    initial_delay_sec: float = 95.0,
    poll_interval_sec: int = 1_800,   # 30 min — championship prices move slowly
    paper_slippage_ticks: int = 1,
    paper_fill_probability: float = 1.0,
):
    """
    Compares Polymarket.us championship futures prices to sharp bookmaker consensus
    (Pinnacle / DraftKings) and paper-executes signals when edge > 5%.

    Paper-only. Will NOT flip to live until 30+ settled paper trades + Brier < 0.25.

    Sports feed (SDATA_KEY): 6-hour cache on championship data → ~1 API credit per
    sport per cache cycle.  Monthly credit usage: ~30-90 credits out of 500 cap.

    Markets: NBA Championship, NHL Stanley Cup, NCAAB Tournament winner.
    Signal: BUY YES if PM underprice by >5pp vs sharp consensus.
            BUY NO  if PM overprice by >5pp.

    kill_switch.check_paper_order_allowed() called before every paper order.
    Hard stop blocks paper orders; soft stops (daily loss, consecutive) do NOT.
    """
    from src.data.odds_api import SportsFeed
    from src.strategies.sports_futures_v1 import SportsFuturesStrategy
    from src.execution.paper import PaperExecutor

    try:
        feed = SportsFeed.load_from_env()
    except RuntimeError as exc:
        logger.warning("[sports_futures] %s — loop disabled for this session", exc)
        return

    strategy = SportsFuturesStrategy(min_edge_pct=0.05)
    paper_exec = PaperExecutor(
        db=db,
        strategy_name=strategy.name,
        slippage_ticks=paper_slippage_ticks,
        fill_probability=paper_fill_probability,
    )

    _PAPER_SIZE_USD = 5.0

    logger.info("[sports_futures] Startup — waiting %.0fs before first poll", initial_delay_sec)
    await asyncio.sleep(initial_delay_sec)

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.debug("[sports_futures] Hard stop active — skipping poll")
                await asyncio.sleep(poll_interval_sec)
                continue

            # ── Fetch open Polymarket futures markets ─────────────────────
            try:
                all_pm = await pm_client.get_markets(closed=False, limit=500)
            except Exception as exc:
                logger.warning("[sports_futures] PM market fetch failed: %s", exc)
                await asyncio.sleep(poll_interval_sec)
                continue

            futures_markets = [
                m for m in all_pm
                if (
                    m.market_type == "futures"
                    or m.raw.get("sportsMarketType") == "futures"
                    or m.raw.get("sportsMarketTypeV2") == "SPORTS_MARKET_TYPE_FUTURE"
                )
            ]

            if not futures_markets:
                logger.debug("[sports_futures] No futures markets open — sleeping")
                await asyncio.sleep(poll_interval_sec)
                continue

            # ── Fetch championship odds (6-hour cache — low credit burn) ──
            nba_odds = await feed.get_nba_championship()
            nhl_odds = await feed.get_nhl_championship()
            ncaab_odds = await feed.get_ncaab_championship()
            all_odds = nba_odds + nhl_odds + ncaab_odds

            logger.debug(
                "[sports_futures] %d futures markets | %d odds (%d NBA, %d NHL, %d NCAAB) | quota: %s",
                len(futures_markets), len(all_odds),
                len(nba_odds), len(nhl_odds), len(ncaab_odds),
                feed.quota_status(),
            )

            if not all_odds:
                logger.debug("[sports_futures] No championship odds available — sleeping")
                await asyncio.sleep(poll_interval_sec)
                continue

            # ── Scan for mispricing signals ───────────────────────────────
            signals = strategy.scan_for_signals(futures_markets, all_odds)
            logger.info(
                "[sports_futures] Poll: %d PM futures, %d odds → %d signals | quota: %s",
                len(futures_markets), len(all_odds), len(signals), feed.quota_status(),
            )

            # ── Paper-execute signals ─────────────────────────────────────
            _current_bankroll = db.latest_bankroll() or 50.0
            for sig in signals:
                ok, block_reason = kill_switch.check_paper_order_allowed(
                    trade_usd=_PAPER_SIZE_USD,
                    current_bankroll_usd=_current_bankroll,
                )
                if not ok:
                    logger.info(
                        "[sports_futures] Kill switch blocked paper order: %s", block_reason
                    )
                    continue

                result = paper_exec.execute(
                    ticker=sig.ticker,
                    side=sig.side,
                    price_cents=sig.price_cents,
                    size_usd=_PAPER_SIZE_USD,
                    reason=sig.reason,
                )
                if result:
                    logger.info(
                        "[sports_futures] [paper] %s@%d¢ $%.2f trade_id=%s | %s",
                        sig.side.upper(), sig.price_cents,
                        result.get("cost_usd", 0), result.get("trade_id", "?"),
                        sig.reason,
                    )

        except asyncio.CancelledError:
            logger.info("[sports_futures] Loop cancelled — shutting down")
            raise
        except Exception as exc:
            logger.error("[sports_futures] Unexpected loop error: %s", exc, exc_info=True)

        await asyncio.sleep(poll_interval_sec)


# ── Expiry Sniper loop — Kalshi 15-min paper-only sniping ─────────────

async def expiry_sniper_loop(
    kalshi,
    btc_feed,
    eth_feed,
    sol_feed,
    xrp_feed,
    db,
    kill_switch,
    initial_delay_sec: float = 110.0,
    live_executor_enabled: bool = False,
    live_confirmed: bool = False,
    trade_lock: Optional[asyncio.Lock] = None,
    max_daily_bets: int = 10,
):
    """
    Expiry sniping loop for KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M.

    Enters when YES or NO price >= 90c in the final 14 minutes of a 15-min window
    AND the underlying coin has moved >= 0.1% from window open in the SAME direction.

    Covers all 4 coin series. Each series uses its own coin feed for drift calculation.
    During extreme bearish sessions (YES < 35c → NO > 65c), these NO=90c+ signals
    fire exactly when the drift strategies are blocked by the 35-65c price guard.
    These two strategies complement each other across market regimes.

    Academic basis: Favorite-longshot bias — heavy favorites close >90% of the time.
    Source strategy: processoverprofit.blog V7 (reconstructed clean — NOT using
    their NightShark/JavaScript code, see EXPIRY_SNIPER_SPEC.md security analysis).

    Live/paper mode controlled by live_executor_enabled + live_confirmed params.
    Live path uses price_guard_min=1, price_guard_max=99 (sniper operates at 87-99c).
    Live sizing: HARD_MAX_TRADE_USD directly (Kelly not used — full Kelly at 93c/93% WR
    = 2.88% of bankroll = ~4 USD at 138 USD bankroll; using ~7.5% = 2.6x Kelly for income target).
    S130: HARD_MAX_TRADE_USD = 10.00, MAX_TRADE_PCT = 8%. At 138 USD bankroll: ~9.99 USD/bet.

    kill_switch.check_paper_order_allowed() for paper; check_order_allowed() for live.
    minutes_remaining=None passed to kill switch (sniper has own 5s hard skip).

    Timing: Use market.close_time directly — NOT clock modulo arithmetic.
    Sizing: Paper = fixed PAPER_CALIBRATION_USD = 0.50.
            Live = HARD_MAX_TRADE_USD ($10.00), no Kelly.
    """
    from src.strategies.expiry_sniper import ExpirySniperStrategy
    from src.execution.paper import PaperExecutor
    from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
    import contextlib

    strategy = ExpirySniperStrategy()
    paper_exec = PaperExecutor(
        db=db,
        strategy_name=strategy.name,
        slippage_ticks=1,
        fill_probability=1.0,
    )

    # Paper/live mode — computed once, never changes mid-run
    is_paper_mode = not (live_executor_enabled and live_confirmed)
    _mode_label = "paper-only" if is_paper_mode else "LIVE"

    # Map series prefix → feed for drift calculation
    _series_feeds = {
        "KXBTC15M": btc_feed,
        "KXETH15M": eth_feed,
        "KXSOL15M": sol_feed,
        "KXXRP15M": xrp_feed,
    }

    # Per-window price tracking: ticker → coin price at first observation of window
    _window_open_price: dict = {}

    logger.info("[expiry_sniper] Startup — waiting %.0fs before first poll", initial_delay_sec)
    await asyncio.sleep(initial_delay_sec)
    logger.info("[expiry_sniper] Started — %s BTC/ETH/SOL/XRP 15M 90c+ sniping", _mode_label)

    # S123 analysis: 08:xx reinstated — all-time n=39, WR=82.1%, -106.63 USD, p=0.012 (sig at 5%).
    # Non-XRP 08:xx: n=32, WR=87.5%, -52.70 USD. SOL=100% but only n=9 (too small to exclude).
    # S119 "non-XRP clean" conclusion was based on crash-stripped short window — all-time data
    # contradicts it. This is the #1 worst hour all-time. Reinstating unconditionally.
    # 13:xx not reinstated — all-time data needed (S119 claim post-guards WR=100% may still hold).
    _BLOCKED_HOURS_UTC = frozenset({8})

    while True:
        try:
            if kill_switch.is_hard_stopped:
                logger.debug("[expiry_sniper] Hard stop active — skipping poll")
                await asyncio.sleep(10)
                continue

            _utc_hour = datetime.now(timezone.utc).hour
            if _utc_hour in _BLOCKED_HOURS_UTC:
                logger.info(
                    "[expiry_sniper] Hour block: %02d:xx UTC — skipping poll (WR<91%% historically)",
                    _utc_hour,
                )
                await asyncio.sleep(60)
                continue

            current_bankroll = db.latest_bankroll() or 50.0

            # ── Evaluate all 4 series each cycle ──────────────────────
            for series_ticker, coin_feed in _series_feeds.items():

                # ── Get current coin price ─────────────────────────────
                current_price = coin_feed.current_price() if not coin_feed.is_stale else None
                if current_price is None:
                    logger.debug("[expiry_sniper] %s feed stale — skip series", series_ticker)
                    continue

                # ── Fetch open markets for this series ─────────────────
                try:
                    markets = await kalshi.get_markets(series_ticker=series_ticker, status="open")
                except Exception as exc:
                    logger.warning("[expiry_sniper] Market fetch failed for %s: %s", series_ticker, exc)
                    continue

                if not markets:
                    logger.debug("[expiry_sniper] No open %s markets", series_ticker)
                    continue

                # ── Evaluate each market in this series ────────────────
                for market in markets:
                    ticker = market.ticker

                    # Track coin price at first observation of each window
                    if ticker not in _window_open_price:
                        _window_open_price[ticker] = current_price
                        logger.debug(
                            "[expiry_sniper] Window open reference %s: price=%.4f",
                            ticker, current_price,
                        )

                    window_open_price = _window_open_price[ticker]
                    coin_drift_pct = (
                        (current_price - window_open_price) / window_open_price
                        if window_open_price > 0 else 0.0
                    )

                    # ── Generate signal ────────────────────────────────
                    signal = strategy.generate_signal(
                        market=market,
                        coin_drift_pct=coin_drift_pct,
                    )
                    if signal is None:
                        continue

                    # ── Dedup: skip if already have open position ──────
                    if db.has_open_position(ticker=ticker, is_paper=is_paper_mode):
                        logger.debug("[expiry_sniper] Already have open position for %s — skip", ticker)
                        continue

                    if live_executor_enabled and live_confirmed:
                        # ═══ LIVE PATH ═══════════════════════════════════
                        # Daily bet cap for sniper (0 = unlimited)
                        if max_daily_bets > 0:
                            today_count = db.count_trades_today(
                                strategy=strategy.name, is_paper=False
                            )
                            if today_count >= max_daily_bets:
                                logger.info(
                                    "[expiry_sniper] Daily bet cap reached (%d/%d) — skip",
                                    today_count, max_daily_bets,
                                )
                                continue

                        # Fee-floor check: at 99c, gross profit (1c) = min fee (1c) → 0 net.
                        # generate_signal() already blocks 99c signals (negative edge), but
                        # execution price can drift from signal price in the 0.1-1s between
                        # signal generation and orderbook fetch. Re-check current market price.
                        # S70: confirmed 17 live 99c bets = -14.85 USD (one loss vs 16 zero wins).
                        _live_price = market.yes_price if signal.side == "yes" else market.no_price
                        if _live_price >= 99:
                            logger.info(
                                "[expiry_sniper] %s %s: price drifted to %dc — skip (99c+ = 0 net per contract)",
                                ticker, signal.side.upper(), _live_price,
                            )
                            continue

                        # S81: Slippage guard — skip if price has moved down 3c+ from signal price.
                        # Trade 2786 example: signal at 90c, fill at 86c (-4c slippage), edge evaporated.
                        # Model confidence = 0 below 87c, so any fill <88c is out-of-model territory.
                        _MAX_SLIPPAGE_CENTS = 3
                        if _live_price < signal.price_cents - _MAX_SLIPPAGE_CENTS:
                            logger.warning(
                                "[expiry_sniper] %s %s: price slipped %dc (signal=%dc, now=%dc) — skip (slippage risk)",
                                ticker, signal.side.upper(),
                                signal.price_cents - _live_price, signal.price_cents, _live_price,
                            )
                            continue

                        # Fetch orderbook for this specific market
                        try:
                            orderbook = await kalshi.get_orderbook(ticker)
                        except Exception as ob_exc:
                            logger.warning(
                                "[expiry_sniper] Orderbook fetch failed for %s: %s",
                                ticker, ob_exc,
                            )
                            continue

                        # Sizing: HARD_MAX clamped to pct_cap to avoid kill switch blocking.
                        # S60 fix: at ~98 USD bankroll, 5.00 = 5.1% > 5% cap → blocked.
                        # S61 fix: floating-point precision — 4.72/94.4 = 0.05000000003 > 0.05.
                        # Subtract 0.01 to guarantee strictly under the cap.
                        from src.risk.kill_switch import MAX_TRADE_PCT as _MAX_PCT
                        _pct_max = round(current_bankroll * _MAX_PCT, 2) - 0.01
                        trade_usd = min(_HARD_CAP, max(0.01, _pct_max))

                        # Atomic: lock → kill_switch → execute → record_trade
                        _lock_ctx = trade_lock if trade_lock is not None else contextlib.nullcontext()
                        async with _lock_ctx:
                            ok, block_reason = kill_switch.check_order_allowed(
                                trade_usd=trade_usd,
                                current_bankroll_usd=current_bankroll,
                                minutes_remaining=None,  # sniper has own 5s hard skip
                            )
                            if not ok:
                                logger.info("[expiry_sniper] Kill switch blocked live order: %s", block_reason)
                                continue

                            from src.execution import live as live_mod
                            result = await live_mod.execute(
                                signal=signal,
                                market=market,
                                orderbook=orderbook,
                                trade_usd=trade_usd,
                                kalshi=kalshi,
                                db=db,
                                live_confirmed=live_confirmed,
                                strategy_name=strategy.name,
                                price_guard_min=1,
                                price_guard_max=99,
                                max_slippage_cents=3,  # S85: sniper-specific tight guard
                            )
                            if result:
                                kill_switch.record_trade()
                                logger.info(
                                    "[expiry_sniper] [LIVE] BUY %s %s @ %d¢ $%.2f | drift=%+.3f%% | %ds left | trade_id=%s",
                                    series_ticker, signal.side.upper(),
                                    result.get("price_cents", 0),
                                    result["cost_usd"],
                                    coin_drift_pct * 100,
                                    strategy._seconds_remaining(market) or 0,
                                    result.get("trade_id", "?"),
                                )
                                _announce_live_bet(result, strategy_name=strategy.name)
                    else:
                        # ═══ PAPER PATH ══════════════════════════════════
                        ok, block_reason = kill_switch.check_paper_order_allowed(
                            trade_usd=strategy.PAPER_CALIBRATION_USD,
                            current_bankroll_usd=current_bankroll,
                        )
                        if not ok:
                            logger.info("[expiry_sniper] Kill switch blocked paper order: %s", block_reason)
                            continue

                        result = paper_exec.execute(
                            ticker=ticker,
                            side=signal.side,
                            price_cents=signal.price_cents,
                            size_usd=strategy.PAPER_CALIBRATION_USD,
                            reason=signal.reason,
                        )
                        if result:
                            logger.info(
                                "[expiry_sniper] [paper] BUY %s %s @ %d¢ USD %.2f | drift=%+.3f%% | %ds left | trade_id=%s",
                                series_ticker, signal.side.upper(), signal.price_cents,
                                strategy.PAPER_CALIBRATION_USD,
                                coin_drift_pct * 100,
                                strategy._seconds_remaining(market) or 0,
                                result.get("trade_id", "?"),
                            )

        except asyncio.CancelledError:
            logger.info("[expiry_sniper] Loop cancelled — exiting")
            break
        except Exception as exc:
            logger.warning("[expiry_sniper] Unexpected error: %s", exc, exc_info=True)

        await asyncio.sleep(10)   # poll every 10s (sniper needs fast polling near expiry)


# ── Polymarket copy-trade polling loop ────────────────────────────────

async def copy_trade_loop(
    pm_client,
    db,
    kill_switch,
    initial_delay_sec: float = 72.0,
    poll_interval_sec: int = 300,
    whale_refresh_sec: int = 21_600,
    paper_slippage_ticks: int = 1,
    paper_fill_probability: float = 1.0,
    live_executor_enabled: bool = False,   # flip True after 30 paper trades + schema confirmed
):
    """
    Polls top whale wallets, applies decoy filters, and executes
    copy-trade signals on Polymarket.us.

    live_executor_enabled=False (default): paper-only. Flip to True after:
      - 30 paper copy trades completed
      - POST /v1/orders schema confirmed (DONE: 2026-03-08)
    Execution targets: season-winner futures currently on api.polymarket.us.
    Game-by-game whale trades are logged but not executed (no .us venue yet).

    Whale list refreshed every 6 hours from predicting.top (public API).
    Trade poll interval: 5 min. Window: last 2 hours per wallet.
    Seen trades deduped by transaction_hash to prevent double copies.
    """
    import time
    from src.data.predicting_top import PredictingTopClient
    from src.data.whale_watcher import WhaleDataClient
    from src.strategies.copy_trader_v1 import CopyTraderStrategy, find_market_for_trade
    from src.execution.paper import PaperExecutor
    from src.platforms.polymarket import OrderIntent, TimeInForce, PolymarketAPIError

    _PAPER_SIZE_USD = 5.0          # fixed $5 paper bets
    _LIVE_SIZE_USD  = 5.0          # max $5 live copy trades (HARD_MAX_TRADE_USD enforced separately)
    _TRADE_LOOKBACK_SEC = 7_200    # look at last 2 hours of whale trades per poll
    _MAX_WHALES_PER_POLL = 30      # cap to control API load per poll cycle

    predicting_top = PredictingTopClient()
    whale_data = WhaleDataClient()
    strategy = CopyTraderStrategy()
    paper_exec = PaperExecutor(db=db, strategy_name=strategy.name,
                               slippage_ticks=paper_slippage_ticks,
                               fill_probability=paper_fill_probability)

    whales: list = []
    last_whale_refresh: float = 0.0
    seen_trade_ids: set = set()     # transaction_hash — dedup across polls

    logger.info("[copy_trade] Startup — waiting %.0fs before first poll", initial_delay_sec)
    await asyncio.sleep(initial_delay_sec)

    while True:
        try:
            now_ts = int(time.time())

            # ── Refresh whale list every 6 hours ─────────────────────
            if now_ts - last_whale_refresh > whale_refresh_sec:
                new_whales = await predicting_top.get_leaderboard(limit=50)
                if new_whales:
                    whales = new_whales
                    last_whale_refresh = now_ts
                    logger.info("[copy_trade] Whale list refreshed: %d wallets (top %d polled)",
                                len(whales), min(len(whales), _MAX_WHALES_PER_POLL))
                else:
                    logger.warning("[copy_trade] predicting.top returned empty list — retrying next cycle")

            if not whales:
                logger.warning("[copy_trade] No whale list yet — sleeping 60s")
                await asyncio.sleep(60)
                continue

            # ── Fetch open .us markets for matching ──────────────────
            try:
                pm_markets = await pm_client.get_markets(closed=False, limit=200)
            except Exception as exc:
                logger.warning("[copy_trade] Failed to fetch PM markets: %s", exc)
                pm_markets = []

            # ── Poll each whale ───────────────────────────────────────
            logger.info("[copy_trade] Poll cycle — %d whales | %d seen trades | %d .us markets",
                        min(len(whales), _MAX_WHALES_PER_POLL), len(seen_trade_ids), len(pm_markets))
            for whale in whales[:_MAX_WHALES_PER_POLL]:
                try:
                    trades = await whale_data.get_trades(
                        whale.proxy_wallet,
                        limit=20,
                        since_ts=now_ts - _TRADE_LOOKBACK_SEC,
                    )
                    if not trades:
                        continue

                    positions = await whale_data.get_positions(whale.proxy_wallet)

                    for trade in trades:
                        # Dedup — skip already-seen transaction hashes
                        trade_key = trade.transaction_hash or (
                            f"{trade.condition_id}_{trade.outcome}_{trade.timestamp}"
                        )
                        if trade_key in seen_trade_ids:
                            continue

                        # Find matching .us market (semantic title match)
                        pm_market = find_market_for_trade(trade, pm_markets)
                        current_price = pm_market.yes_price if pm_market else trade.price

                        sig = strategy.generate_signal(
                            trade, positions, now_ts,
                            current_market_price=current_price,
                            smart_score=whale.smart_score,
                        )

                        if sig is None:
                            continue

                        # Mark seen whether or not we execute (avoid re-evaluating)
                        seen_trade_ids.add(trade_key)
                        # Prune seen set to avoid unbounded growth (keep last 10k)
                        if len(seen_trade_ids) > 10_000:
                            seen_trade_ids = set(list(seen_trade_ids)[-5_000:])

                        if pm_market:
                            logger.info(
                                "[copy_trade] %s %s %s@%d¢ | whale=%s smart=%.0f edge=%.0f%%",
                                sig.side.upper(), trade.title, trade.outcome,
                                sig.price_cents, whale.name, whale.smart_score,
                                sig.edge_pct * 100,
                            )
                            _current_bankroll = db.latest_bankroll() or 50.0

                            if live_executor_enabled:
                                # ── Live execution path ─────────────────────────────
                                trade_price = sig.price_cents / 100.0
                                contracts = max(1, int(_LIVE_SIZE_USD / trade_price))
                                actual_cost = round(contracts * trade_price, 2)

                                ok, block_reason = kill_switch.check_order_allowed(
                                    trade_usd=actual_cost,
                                    current_bankroll_usd=_current_bankroll,
                                )
                                if not ok:
                                    logger.info("[copy_trade] [live] Kill switch blocked: %s", block_reason)
                                else:
                                    identifier = (
                                        pm_market.yes_identifier if sig.side == "yes"
                                        else pm_market.no_identifier
                                    )
                                    intent = (
                                        OrderIntent.BUY_LONG if sig.side == "yes"
                                        else OrderIntent.BUY_SHORT
                                    )
                                    try:
                                        order_result = await pm_client.place_order(
                                            market_slug=identifier,
                                            intent=intent,
                                            price=trade_price,
                                            quantity=contracts,
                                            tif=TimeInForce.FOK,
                                        )
                                        if order_result.is_filled:
                                            db.save_trade(
                                                ticker=sig.ticker,
                                                side=sig.side,
                                                action="buy",
                                                price_cents=sig.price_cents,
                                                count=contracts,
                                                cost_usd=actual_cost,
                                                strategy=strategy.name,
                                                edge_pct=sig.edge_pct,
                                                win_prob=sig.win_prob,
                                                is_paper=False,
                                                server_order_id=order_result.order_id,
                                                signal_price_cents=sig.price_cents,
                                            )
                                            kill_switch.record_trade()
                                            logger.info(
                                                "[copy_trade] [LIVE] Executed: %s %s@%d¢ "
                                                "$%.2f %dc order=%s",
                                                sig.side.upper(), trade.title, sig.price_cents,
                                                actual_cost, contracts, order_result.order_id,
                                            )
                                        else:
                                            logger.info(
                                                "[copy_trade] [live] FOK no fill: %s %s@%d¢ "
                                                "(order=%s)",
                                                sig.side.upper(), trade.title, sig.price_cents,
                                                order_result.order_id,
                                            )
                                    except PolymarketAPIError as exc:
                                        logger.warning("[copy_trade] [live] Order failed: %s", exc)

                            else:
                                # ── Paper execution path ────────────────────────────
                                ok, block_reason = kill_switch.check_paper_order_allowed(
                                    trade_usd=_PAPER_SIZE_USD,
                                    current_bankroll_usd=_current_bankroll,
                                )
                                if not ok:
                                    logger.info("[copy_trade] Kill switch blocked paper order: %s",
                                                block_reason)
                                else:
                                    result = paper_exec.execute(
                                        ticker=sig.ticker,
                                        side=sig.side,
                                        price_cents=sig.price_cents,
                                        size_usd=_PAPER_SIZE_USD,
                                        reason=sig.reason,
                                    )
                                    if result:
                                        logger.info(
                                            "[copy_trade] [paper] Executed: %s %s@%d¢ "
                                            "$%.2f trade_id=%s",
                                            sig.side.upper(), trade.title, sig.price_cents,
                                            result.get("cost_usd", 0), result.get("trade_id", "?"),
                                        )
                        else:
                            # No matching .us market — log signal for intelligence only
                            logger.info(
                                "[copy_trade] Signal (no .us venue, log only): %s %s %s",
                                sig.side.upper(), trade.title, trade.outcome,
                            )

                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("[copy_trade] Error processing whale %s: %s",
                                   whale.name, exc)
                    continue

        except asyncio.CancelledError:
            logger.info("[copy_trade] Loop cancelled — shutting down")
            raise
        except Exception as exc:
            logger.error("[copy_trade] Unexpected loop error: %s", exc, exc_info=True)

        await asyncio.sleep(poll_interval_sec)


# ── PID lock — prevent two bot instances running at the same time ─────

_PID_FILE = PROJECT_ROOT / "bot.pid"


def _scan_for_duplicate_main_processes() -> list:
    """
    Scan all running processes for other instances of 'python main.py'.

    Returns a list of PIDs that are NOT our own process. Empty list = no duplicates.
    This catches orphaned instances that survived previous kill $(cat bot.pid) calls,
    which only kills the most recent bot.pid entry not all older instances.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["pgrep", "-f", "main.py"],
            capture_output=True,
            text=True,
        )
        pids = []
        for line in result.stdout.strip().splitlines():
            try:
                pid = int(line.strip())
                if pid != os.getpid():
                    pids.append(pid)
            except ValueError:
                pass  # skip non-integer lines
        return pids
    except FileNotFoundError:
        return []  # pgrep not available — fall back to bot.pid check only


def _acquire_bot_lock() -> Path:
    """
    Write current PID to bot.pid. If another instance is already running,
    print an error and exit. Protects against accidental duplicate runs
    that could double-execute trades and burn API quota.

    Checks two ways:
      1. bot.pid file — catches the most recent instance
      2. pgrep scan — catches orphaned instances from prior restarts

    Returns the PID file Path so the caller can release it on shutdown.
    """
    # ── Check 1: pgrep scan for all running main.py processes ────────────
    duplicate_pids = _scan_for_duplicate_main_processes()
    if duplicate_pids:
        print(f"\nERROR: Other bot instance(s) already running: PIDs {duplicate_pids}")
        print(f"  Kill all of them: pkill -f 'python main.py'")
        print(f"  Then retry. (Never use 'kill $(cat bot.pid)' — it misses orphans.)\n")
        sys.exit(1)

    # ── Check 2: bot.pid file check ───────────────────────────────────────
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


def print_graduation_status(db):
    """
    Print graduation progress table for all tracked strategies.

    Imports _GRAD thresholds from setup/verify.py (single source of truth).
    Live strategies (in _LIVE_STRATEGIES) are checked against live trades only.
    Reads DB only — does NOT start Kalshi or Binance connections.
    """
    from setup.verify import _GRAD, _LIVE_STRATEGIES
    from datetime import datetime, timezone

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    width = 64

    print()
    print("=" * width)
    print(f"  GRADUATION STATUS — {now_str}")
    print("=" * width)
    print(
        f"  {'Strategy':<34} {'Trades':>6}  {'Days':>5}  {'Brier':>5}  "
        f"{'Streak':>6}  {'P&L':>7}  Status"
    )
    print("  " + "-" * (width - 2))

    ready_count = 0
    for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
        is_paper = False if strategy in _LIVE_STRATEGIES else True
        stats = db.graduation_stats(strategy, is_paper=is_paper)

        settled = stats["settled_count"]
        days = stats["days_running"]
        brier = stats["brier_score"]
        streak = stats["consecutive_losses"]
        pnl = stats["total_pnl_usd"]

        trades_str = f"{settled}/{min_trades}"
        days_str = f"{days:.1f}"
        brier_str = f"{brier:.3f}" if brier is not None else "n/a"
        streak_str = str(streak)
        pnl_str = f"${pnl:.2f}"

        # Determine status
        if streak >= max_consec:
            status = f"BLOCKED ({streak} consec losses)"
        else:
            gaps = []
            if settled < min_trades:
                gaps.append(f"needs {min_trades - settled} more trades")
            if min_days > 0 and days < min_days:
                gaps.append(f"{min_days - days:.1f} more days")
            if brier is not None and brier > max_brier:
                gaps.append(f"brier {brier:.3f}>={max_brier}")
            if not gaps:
                status = "READY FOR LIVE"
                ready_count += 1
            else:
                status = ", ".join(gaps)

        print(
            f"  {strategy:<34} {trades_str:>6}  {days_str:>5}  {brier_str:>5}  "
            f"{streak_str:>6}  {pnl_str:>7}  {status}"
        )

    print("=" * width)
    print(f"  {ready_count} / {len(_GRAD)} strategies ready for live trading.")
    print("=" * width)
    print()


def print_report(db):
    """Print today's P&L summary with per-strategy breakdown."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    trades = db.get_trades(limit=500)  # wide window — up to 500 trades today
    today_trades = [t for t in trades if t["timestamp"] and
                    datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%Y-%m-%d") == today]
    settled = [t for t in today_trades if t.get("result")]
    wins = [t for t in settled if t["result"] == t["side"]]
    total_pnl_cents = sum(t.get("pnl_cents", 0) or 0 for t in settled)
    live_settled = [t for t in settled if not t.get("is_paper")]
    paper_settled = [t for t in settled if t.get("is_paper")]
    live_pnl = sum(t.get("pnl_cents", 0) or 0 for t in live_settled) / 100
    paper_pnl = sum(t.get("pnl_cents", 0) or 0 for t in paper_settled) / 100

    width = 56
    print(f"\n{'='*width}")
    print(f"  P&L REPORT — {today}")
    print(f"{'='*width}")
    print(f"  Trades today:      {len(today_trades):>4}  (settled: {len(settled)})")
    print(f"  Wins:              {len(wins):>4}  (rate: {len(wins)/max(1,len(settled)):.0%})")
    print(f"  P&L live:        ${live_pnl:>6.2f}  ({len(live_settled)} settled)")
    print(f"  P&L paper:       ${paper_pnl:>6.2f}  ({len(paper_settled)} settled)")
    print(f"  P&L total:       ${total_pnl_cents/100:>6.2f}")

    # Per-strategy breakdown — split paper vs live using is_paper on each trade
    # Prevents mixing pre-restart paper bets with post-restart live bets for same strategy
    strat_mode_keys = sorted({
        (t.get("strategy", "unknown"), bool(t.get("is_paper", True)))
        for t in today_trades if t.get("strategy")
    })
    if strat_mode_keys:
        print(f"\n  {'Strategy':<28} {'Bets':>4} {'W/L':>5} {'P&L':>8}")
        print("  " + "-" * (width - 2))
        for strat, is_paper in strat_mode_keys:
            strat_all = [t for t in today_trades
                         if t.get("strategy") == strat and bool(t.get("is_paper", True)) == is_paper]
            strat_settled = [t for t in strat_all if t.get("result")]
            strat_wins = [t for t in strat_settled if t["result"] == t["side"]]
            strat_pnl = sum(t.get("pnl_cents", 0) or 0 for t in strat_settled) / 100
            wl = f"{len(strat_wins)}/{len(strat_settled)}"
            mode = "📋" if is_paper else "🔴"
            print(f"  {mode} {strat:<26} {len(strat_all):>4} {wl:>5} ${strat_pnl:>6.2f}")

    print(f"\n  All-time P&L (live):   ${db.total_realized_pnl_usd(is_paper=False):>7.2f}")
    print(f"  All-time P&L (paper):  ${db.total_realized_pnl_usd(is_paper=True):>7.2f}")
    wr = db.win_rate()
    if wr is not None:
        print(f"  All-time win rate:     {wr:>6.0%}")
    print(f"{'='*width}\n")


# ── Status command ─────────────────────────────────────────────────────


def get_binance_mid_price(symbol: str) -> Optional[float]:
    """
    Fetch a single mid-price snapshot from Binance.US REST API.

    Uses /api/v3/ticker/bookTicker (same data as the WebSocket bookTicker stream).
    Returns mid = (bidPrice + askPrice) / 2.
    Returns None on any network error or malformed response — never raises.

    Always uses api.binance.us — binance.com is geo-blocked in the US (HTTP 451).
    """
    url = f"https://api.binance.us/api/v3/ticker/bookTicker?symbol={symbol}"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        bid = float(data["bidPrice"])
        ask = float(data["askPrice"])
        return (bid + ask) / 2
    except requests.RequestException:
        return None
    except (KeyError, ValueError, TypeError):
        return None


def print_status(db) -> None:
    """
    Print a rich bot status snapshot to stdout.

    Reads from:
    - DB: last 10 trades, open trades, latest bankroll, today's P&L, all-time P&L
    - Binance.US REST: BTC and ETH mid-prices (synchronous, no WebSocket)

    Exits in under 2 seconds. Safe to run while bot is running (read-only DB + short REST call).
    """
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    width = 64

    # ── Fetch prices (fast REST snapshot) ─────────────────────────────
    btc_mid = get_binance_mid_price("BTCUSDT")
    eth_mid = get_binance_mid_price("ETHUSDT")

    btc_str = f"${btc_mid:,.2f}" if btc_mid is not None else "n/a"
    eth_str = f"${eth_mid:,.2f}" if eth_mid is not None else "n/a"

    # ── DB reads ──────────────────────────────────────────────────────
    bankroll = db.latest_bankroll()
    bankroll_str = f"${bankroll:.2f}" if bankroll is not None else "n/a"

    open_trades = db.get_open_trades()
    open_paper = [t for t in open_trades if t.get("is_paper")]
    open_live = [t for t in open_trades if not t.get("is_paper")]
    pending_total = len(open_trades)

    # Today's trades (paper + live split)
    all_trades_today_window = db.get_trades(limit=200)
    today_trades = [
        t for t in all_trades_today_window
        if t.get("timestamp") and
        datetime.fromtimestamp(t["timestamp"], timezone.utc).strftime("%Y-%m-%d") == today
    ]
    today_paper_settled = [
        t for t in today_trades if t.get("result") and t.get("is_paper")
    ]
    today_live_settled = [
        t for t in today_trades if t.get("result") and not t.get("is_paper")
    ]
    today_paper_pnl = sum(t.get("pnl_cents", 0) or 0 for t in today_paper_settled) / 100
    today_live_pnl = sum(t.get("pnl_cents", 0) or 0 for t in today_live_settled) / 100

    alltime_paper_pnl = db.total_realized_pnl_usd(is_paper=True)
    alltime_live_pnl = db.total_realized_pnl_usd(is_paper=False)

    # Recent 10 trades (newest first)
    recent = db.get_trades(limit=10)

    # ── Print block ───────────────────────────────────────────────────
    print()
    print("=" * width)
    print(f"  BOT STATUS — {now_str}")
    print("=" * width)
    print(f"  Bankroll (DB):   {bankroll_str}")
    print(f"  BTC mid:         {btc_str}")
    print(f"  ETH mid:         {eth_str}")
    print(
        f"  Pending bets:    {pending_total} "
        f"(paper: {len(open_paper)}, live: {len(open_live)})"
    )
    print()
    today_live_display = (
        f"${today_live_pnl:.2f}   ({len(today_live_settled)} settled)"
        if today_live_settled else
        "n/a     (0 settled)"
    )
    print(f"  Today's P&L (paper):   ${today_paper_pnl:.2f}   ({len(today_paper_settled)} settled)")
    print(f"  Today's P&L (live):    {today_live_display}")
    print(f"  All-time P&L (paper):  ${alltime_paper_pnl:.2f}")
    print(f"  All-time P&L (live):   ${alltime_live_pnl:.2f}")
    print()
    print(f"  Recent Trades (last {len(recent)}):")
    print("  " + "-" * (width - 2))
    if not recent:
        print("  (no trades yet)")
    else:
        for t in recent:
            ts = t.get("timestamp")
            ts_str = (
                datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M")
                if ts else "          ?"
            )
            ticker = t.get("ticker", "?")
            side = t.get("side", "?")
            price = t.get("price_cents", 0) or 0
            label = "[PAPER]" if t.get("is_paper") else "[LIVE] "
            result = t.get("result", "")
            result_str = f"  [{result}]" if result else "  [open]"
            print(
                f"  {ts_str}  {ticker:<36} {side:<4} {price:>3}c  {label}{result_str}"
            )
    print("=" * width)
    print()


# ── Health diagnostic command ──────────────────────────────────────────


def print_health(db) -> None:
    """
    Comprehensive bot health diagnostic. Run via: python main.py --health

    Surfaces ALL known silent failure modes:
      - Kill switch state (hard stop, daily loss, consecutive streak + staleness)
      - Last live bet + elapsed time (warns at 24hr, critical at 72hr)
      - Open trades including any non-Kalshi tickers (settlement orphans)
      - SDATA quota consumption
      - Bot PID and whether process is running
      - Recent KILL_SWITCH_EVENT.log entries
    """
    import time as _time
    import json as _json
    import os as _os
    from src.risk.kill_switch import (
        COOLING_PERIOD_HOURS,
        CONSECUTIVE_LOSS_LIMIT,
        DAILY_LOSS_LIMIT_PCT,
    )

    now = _time.time()
    width = 70
    warnings: list[str] = []  # actionable but non-critical
    issues: list[str] = []    # critical / blocking

    print()
    print("=" * width)
    print("  BOT HEALTH DIAGNOSTIC")
    print(f"  Run at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * width)

    # ── 1. Kill switch state ──────────────────────────────────────────
    print()
    print("  [1] KILL SWITCH STATE")
    print("  " + "-" * (width - 2))

    # Hard stop — check lock file
    lock_path = PROJECT_ROOT / "kill_switch.lock"
    if lock_path.exists():
        try:
            lock_content = lock_path.read_text().strip()
            print(f"  Hard stopped:      ACTIVE - {lock_content[:55]}")
            issues.append("HARD STOP active — review KILL_SWITCH_EVENT.log, then --reset-killswitch")
        except Exception:
            print(f"  Hard stopped:      ACTIVE (lock file unreadable)")
            issues.append("Hard stop lock file exists but unreadable")
    else:
        print(f"  Hard stopped:      OK (no lock file)")

    # Daily loss
    daily_loss = db.daily_live_loss_usd()
    bankroll = db.latest_bankroll() or 50.0
    daily_limit = bankroll * DAILY_LOSS_LIMIT_PCT
    daily_pct = (daily_loss / daily_limit * 100) if daily_limit > 0 else 0
    daily_flag = " -- SOFT STOP ACTIVE" if daily_loss >= daily_limit else ""
    print(f"  Daily loss (live): ${daily_loss:.2f} / ${daily_limit:.2f} ({daily_pct:.0f}%){daily_flag}")
    if daily_loss >= daily_limit:
        warnings.append(f"Daily loss soft stop active: ${daily_loss:.2f} >= ${daily_limit:.2f}")

    # Consecutive losses + staleness
    streak, last_loss_ts = db.current_live_consecutive_losses()
    if streak == 0:
        print(f"  Consecutive:       {streak}/{CONSECUTIVE_LOSS_LIMIT} -- OK")
    elif last_loss_ts is None:
        print(f"  Consecutive:       {streak}/{CONSECUTIVE_LOSS_LIMIT} -- AT LIMIT (no timestamp -- conservative block may be active)")
        warnings.append(f"Consecutive streak {streak} at limit, no timestamp — verify cooling state")
    else:
        cooling_window_sec = COOLING_PERIOD_HOURS * 3600
        elapsed_hr = (now - last_loss_ts) / 3600
        if streak >= CONSECUTIVE_LOSS_LIMIT and elapsed_hr < COOLING_PERIOD_HOURS:
            remaining_min = (cooling_window_sec - (now - last_loss_ts)) / 60
            print(f"  Consecutive:       {streak}/{CONSECUTIVE_LOSS_LIMIT} -- COOLING {remaining_min:.0f}min remaining (last loss {elapsed_hr:.1f}hr ago)")
            warnings.append(f"Consecutive loss cooling: {remaining_min:.0f}min remaining — live bets blocked")
        elif streak >= CONSECUTIVE_LOSS_LIMIT:
            print(f"  Consecutive:       {streak}/{CONSECUTIVE_LOSS_LIMIT} -- stale, last loss {elapsed_hr:.1f}hr ago (cooling already served)")
        else:
            print(f"  Consecutive:       {streak}/{CONSECUTIVE_LOSS_LIMIT} -- last loss {elapsed_hr:.1f}hr ago")

    # ── 2. Live trading activity ───────────────────────────────────────
    print()
    print("  [2] LIVE TRADING ACTIVITY")
    print("  " + "-" * (width - 2))

    live_trades_recent = db.get_trades(is_paper=False, limit=1)
    if not live_trades_recent:
        print("  Last live bet:     (none -- no live trades ever placed)")
        warnings.append("No live bets ever placed — bot has never executed a live trade")
    else:
        last_live = live_trades_recent[0]
        last_ts = last_live.get("timestamp") or 0.0
        elapsed_hr = (now - last_ts) / 3600
        ts_str = datetime.fromtimestamp(last_ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        ticker = last_live.get("ticker", "?")
        strategy_name = last_live.get("strategy", "?")
        result = last_live.get("result") or "open"
        print(f"  Last live bet:     {ts_str}  [{ticker}]  strategy={strategy_name}  result={result}")
        if elapsed_hr >= _NO_LIVE_BETS_CRITICAL_HOURS:
            print(f"  Elapsed:           {elapsed_hr:.0f}hr -- CRITICAL: something is wrong (threshold {_NO_LIVE_BETS_CRITICAL_HOURS}hr)")
            issues.append(
                f"NO LIVE BETS in {elapsed_hr:.0f}hr (threshold {_NO_LIVE_BETS_CRITICAL_HOURS}hr). "
                f"Causes to check: kill switch soft stop | signal too rare | thresholds too strict | loop error. "
                f"Run: grep 'kill switch blocked\\|SOFT STOP\\|No open' /tmp/polybot_*.log | tail -30"
            )
        elif elapsed_hr >= _NO_LIVE_BETS_WARN_HOURS:
            print(f"  Elapsed:           {elapsed_hr:.0f}hr -- WARNING: no live bet in {_NO_LIVE_BETS_WARN_HOURS}hr+")
            warnings.append(
                f"No live bets in {elapsed_hr:.0f}hr. Check: kill switch state above | signal conditions | loop errors"
            )
        else:
            print(f"  Elapsed:           {elapsed_hr:.1f}hr -- OK")

    all_live = db.get_trades(is_paper=False, limit=2000)
    settled_live = [t for t in all_live if t.get("result")]
    print(f"  Total live bets:   {len(all_live)} placed, {len(settled_live)} settled")

    # ── 3. Open trades / settlement orphans ───────────────────────────
    print()
    print("  [3] OPEN TRADES")
    print("  " + "-" * (width - 2))

    open_trades = db.get_open_trades()
    open_live = [t for t in open_trades if not t.get("is_paper")]
    open_paper = [t for t in open_trades if t.get("is_paper")]
    non_kx = [t for t in open_trades if not t.get("ticker", "").upper().startswith("KX")]

    print(f"  Open live bets:    {len(open_live)}")
    print(f"  Open paper bets:   {len(open_paper)}")

    non_kx_live = [t for t in non_kx if not t.get("is_paper")]
    non_kx_paper = [t for t in non_kx if t.get("is_paper")]
    if non_kx_live:
        print(f"  Non-Kalshi LIVE ({len(non_kx_live)} -- these will cause 404 in settlement loop):")
        for t in non_kx_live[:5]:
            print(f"    ticker={t.get('ticker', '?')}  strategy={t.get('strategy', '?')}")
        issues.append(
            f"{len(non_kx_live)} non-KX LIVE tickers in open trades — settlement loop KX filter may be missing"
        )
    elif non_kx_paper:
        print(f"  Non-Kalshi paper: {len(non_kx_paper)} (all is_paper=1, e.g. sports_futures_v1 -- OK, settlement loop ignores them)")
    else:
        print(f"  Non-Kalshi tickers: none (OK)")

    stale_hr = 48
    stale_open = [
        t for t in open_trades
        if not t.get("is_paper")  # paper trades excluded — settlement loop ignores them intentionally
        and (t.get("timestamp") or 0) and (now - (t.get("timestamp") or 0)) / 3600 > stale_hr
    ]
    stale_paper = [
        t for t in open_trades
        if t.get("is_paper")
        and (t.get("timestamp") or 0) and (now - (t.get("timestamp") or 0)) / 3600 > stale_hr
    ]
    if stale_open:
        print(f"  Stale open live (>{stale_hr}hr): {len(stale_open)} -- may be missed settlements")
        warnings.append(f"{len(stale_open)} open live trades older than {stale_hr}hr — settlement loop may have missed them")
    else:
        print(f"  Stale open live (>{stale_hr}hr): none (OK)")
    if stale_paper:
        print(f"  Stale open paper (>{stale_hr}hr): {len(stale_paper)} -- expected for long-duration paper strategies (sports_futures, fomc, weather)")

    # ── 4. Bot process ─────────────────────────────────────────────────
    print()
    print("  [4] BOT PROCESS")
    print("  " + "-" * (width - 2))

    pid_path = PROJECT_ROOT / "bot.pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            try:
                _os.kill(pid, 0)
                print(f"  Bot PID:           {pid} (running)")
            except ProcessLookupError:
                print(f"  Bot PID:           {pid} -- NOT running (stale pid file?)")
                warnings.append(f"bot.pid has PID {pid} but process not found — stale pid or bot crashed")
            except PermissionError:
                print(f"  Bot PID:           {pid} (running, different user)")
        except (ValueError, OSError) as e:
            print(f"  Bot PID:           unreadable -- {e}")
    else:
        print(f"  Bot PID:           not found (bot not running or clean exit)")

    # ── 5. SDATA quota ─────────────────────────────────────────────────
    print()
    print("  [5] SDATA QUOTA")
    print("  " + "-" * (width - 2))

    sdata_path = PROJECT_ROOT / "data" / "sdata_quota.json"
    if sdata_path.exists():
        try:
            quota_data = _json.loads(sdata_path.read_text())
            used = quota_data.get("used", 0)
            qlimit = quota_data.get("limit", 500)
            year = quota_data.get("year", "?")
            month = quota_data.get("month", "?")
            reset_str = f"{year}-{int(month)+1:02d}-01" if year != "?" and month != "?" else "next month"
            pct = (used / qlimit * 100) if qlimit > 0 else 0
            flag = " -- HIGH" if pct > 80 else (" -- NEAR CAP" if pct > 95 else "")
            print(f"  SDATA used:        {used}/{qlimit} ({pct:.0f}%) resets {reset_str}{flag}")
            if pct > 80:
                warnings.append(f"SDATA quota at {pct:.0f}% ({used}/{qlimit}) — approaching monthly cap")
        except Exception as e:
            print(f"  SDATA quota:       error reading -- {e}")
    else:
        print(f"  SDATA quota:       (no quota file -- sports_futures_v1 not yet run this month)")

    # ── 6. Recent kill switch events ──────────────────────────────────
    print()
    print("  [6] RECENT KILL SWITCH EVENTS")
    print("  " + "-" * (width - 2))

    event_log_path = PROJECT_ROOT / "KILL_SWITCH_EVENT.log"
    if event_log_path.exists():
        try:
            lines = event_log_path.read_text().splitlines()
            real_events = [ln for ln in lines if ln.strip()]
            recent_events = real_events[-6:]
            if recent_events:
                for line in recent_events:
                    print(f"  {line[:width - 4]}")
            else:
                print("  (log exists but empty)")
        except Exception as e:
            print(f"  Error reading event log: {e}")
    else:
        print(f"  (no event log -- no kill switch hard stops ever fired)")

    # ── 7. Summary ────────────────────────────────────────────────────
    print()
    print("=" * width)
    if issues:
        print("  CRITICAL:")
        for issue in issues:
            print(f"    * {issue}")
    if warnings:
        print("  WARNINGS:")
        for w in warnings:
            print(f"    * {w}")
    if not issues and not warnings:
        print("  All systems healthy -- no active blocks or anomalies detected.")
    print()
    print("  Useful commands:")
    print("  python main.py --status           # recent trades + P&L")
    print("  python main.py --report           # today's strategy breakdown")
    print("  python main.py --graduation-status  # live bet progress toward graduation")
    if issues or warnings:
        print()
        print("  If no live bets for 24hr+:")
        print("    grep 'kill switch blocked\\|SOFT STOP\\|No open' /tmp/polybot_*.log | tail -30")
        print("    grep 'WARNING\\|ERROR\\|CRITICAL' /tmp/polybot_*.log | tail -20")
    print("=" * width)
    print()


# ── Main ──────────────────────────────────────────────────────────────


async def main():
    parser = argparse.ArgumentParser(description="polymarket-bot — Kalshi BTC lag trader")
    parser.add_argument("--live", action="store_true",
                        help="Enable live trading (also requires LIVE_TRADING=true in .env)")
    parser.add_argument("--verify", action="store_true",
                        help="Run connection verification and exit")
    parser.add_argument("--reset-killswitch", action="store_true",
                        help="Reset a triggered hard stop (requires manual confirmation)")
    parser.add_argument("--reset-soft-stop", action="store_true",
                        help="Clear consecutive loss counter and cooling period at startup "
                             "(use after a bug fix that caused the loss streak)")
    parser.add_argument("--report", action="store_true",
                        help="Print today's P&L summary and exit")
    parser.add_argument("--graduation-status", action="store_true",
                        help="Print graduation progress for all 8 strategies and exit")
    parser.add_argument("--status", action="store_true",
                        help="Print bot status (bankroll, prices, pending bets, recent trades) and exit")
    parser.add_argument("--export-trades", action="store_true",
                        help="Export all trades to reports/trades.csv and exit")
    parser.add_argument("--export-tax", action="store_true",
                        help="Export resolved live trades to reports/tax_trades.csv (Section 4.4 fields) and exit")
    parser.add_argument("--health", action="store_true",
                        help="Comprehensive health diagnostic: surfaces kill switch state, "
                             "no-live-bets warnings, open trade anomalies, SDATA quota, PID")
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

    # ── Read-only commands (bypass bot lock — safe while bot is live) ──
    _read_only_mode = args.status or args.report or args.graduation_status or args.export_trades or args.export_tax or args.health
    if _read_only_mode:
        from src.db import load_from_config as db_load
        db = db_load()
        db.init()
        if args.status:
            print_status(db)
        elif args.report:
            print_report(db)
        elif args.graduation_status:
            print_graduation_status(db)
        elif args.export_trades:
            path = db.export_trades_csv()
            print(f"Exported {path}")
        elif args.export_tax:
            path = db.export_tax_csv()
            print(f"Tax CSV exported to {path}")
        elif args.health:
            print_health(db)
        db.close()
        return

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

        # ── Auto-guard discovery at startup (Dim 1 — runs before live.py import) ──
        # live.py loads auto_guards.json at MODULE IMPORT TIME (line 64).
        # By running discovery here, any new guards are written before that import,
        # making them active immediately in this session — no restart needed.
        try:
            import importlib.util as _ilu
            _ag_spec = _ilu.spec_from_file_location(
                "auto_guard_discovery",
                str(Path(__file__).parent / "scripts" / "auto_guard_discovery.py"),
            )
            _ag_mod = _ilu.module_from_spec(_ag_spec)
            _ag_spec.loader.exec_module(_ag_mod)
            _new_guards = _ag_mod.discover_guards()
            _existing_guards = _ag_mod.load_existing_auto_guards()
            _merged_guards, _n_added = _ag_mod.merge_guards(_existing_guards, _new_guards)
            if _n_added > 0:
                _ag_mod.write_guards(_merged_guards)
                _new_guard_labels = [
                    f"{g['ticker_contains']} {g['side'].upper()}@{g['price_cents']}c"
                    for g in _new_guards
                ]
                logger.critical(
                    "[startup] AUTO-GUARD: %d NEW guard(s) written to auto_guards.json "
                    "— activated in this session (no restart needed). "
                    "New guards: %s",
                    _n_added,
                    _new_guard_labels,
                )
                # Alert Matthew via macOS Reminders (best-effort)
                try:
                    import subprocess as _sp
                    _msg = f"POLYBOT AUTO-GUARD: {_n_added} new guard(s) activated"
                    _body = ", ".join(_new_guard_labels)
                    _script = (
                        f'tell application "Reminders" to make new reminder '
                        f'with properties {{name:"{_msg}", body:"{_body}"}}'
                    )
                    _sp.run(["osascript", "-e", _script], timeout=3, capture_output=True)
                except Exception:
                    pass
            else:
                logger.info(
                    "[startup] AUTO-GUARD: 0 new guards (all %d known buckets covered).",
                    len(_merged_guards),
                )
        except Exception as _ag_err:
            logger.warning("[startup] AUTO-GUARD discovery failed (non-fatal): %s", _ag_err)

        # Propagate confirmation to live executor so its internal guard doesn't
        # re-prompt via input() (which hangs when stdin is piped/non-interactive)
        import src.execution.live as _live_exec_mod
        _live_exec_mod._FIRST_RUN_CONFIRMED = True
        print("  ✅ Live trading confirmed.")
        print("=" * 60 + "\n")

    # ── Initialize DB ─────────────────────────────────────────────────
    from src.db import load_from_config as db_load
    db = db_load()
    db.init()


    # ── Initialize components ─────────────────────────────────────────
    from src.platforms.kalshi import load_from_env as kalshi_load
    from src.data.binance import load_from_config as binance_load
    from src.data.binance import load_eth_from_config as eth_binance_load
    from src.data.binance import load_sol_from_config as sol_binance_load
    from src.data.binance import load_xrp_from_config as xrp_binance_load
    from src.data.coinbase import CoinbasePriceFeed, DualPriceFeed
    from src.strategies.btc_lag import load_from_config as strategy_load
    from src.strategies.btc_lag import load_eth_lag_from_config as eth_lag_load
    from src.strategies.btc_lag import load_sol_lag_from_config as sol_lag_load
    from src.strategies.btc_drift import load_from_config as drift_strategy_load
    from src.strategies.btc_drift import load_eth_drift_from_config as eth_drift_load
    from src.strategies.btc_drift import load_sol_drift_from_config as sol_drift_load
    from src.strategies.btc_drift import load_xrp_drift_from_config as xrp_drift_load
    from src.strategies.orderbook_imbalance import (
        load_btc_imbalance_from_config,
        load_eth_imbalance_from_config,
    )
    from src.strategies.weather_forecast import load_from_config as weather_strategy_load
    from src.data.weather import load_gefs_from_config as weather_feed_load
    from src.strategies.fomc_rate import load_from_config as fomc_strategy_load
    from src.data.fred import load_from_config as fred_feed_load
    from src.strategies.unemployment_rate import load_from_config as unemployment_strategy_load
    from src.risk.sizing import get_stage

    starting_bankroll = config.get("risk", {}).get("starting_bankroll_usd", 50.0)
    kill_switch = KillSwitch(starting_bankroll_usd=starting_bankroll)

    # Restore loss counters from DB so restarts never reset financial risk limits.
    # _realized_loss_usd (30% hard stop): ALL-TIME live losses — restored first, set not add.
    # _daily_loss_usd (daily soft stop): TODAY's live losses only.
    # _consecutive_losses (cooling period): streak from end of live trade history.
    #   Restoring prevents a restart mid-streak from bypassing the 4-loss cool-down.
    #   If streak >= 4 at startup, a fresh 2hr cooling period fires immediately.
    _all_time_live_loss = db.all_time_live_loss_usd()
    if _all_time_live_loss > 0:
        kill_switch.restore_realized_loss(_all_time_live_loss)
    _today_live_loss = db.daily_live_loss_usd()
    if _today_live_loss > 0:
        kill_switch.restore_daily_loss(_today_live_loss)
    _consecutive_streak, _last_loss_ts = db.current_live_consecutive_losses()
    if _consecutive_streak > 0:
        kill_switch.restore_consecutive_losses(_consecutive_streak, _last_loss_ts)
    if args.reset_soft_stop:
        kill_switch.reset_soft_stop()
        logger.warning("[startup] --reset-soft-stop: consecutive loss counter cleared")
    # Log kill switch health AFTER all restores — surfaces any active blocks immediately
    kill_switch.log_startup_status()

    # ── Load Bayesian drift posterior ─────────────────────────────────
    # Safe at startup — returns flat prior if file is missing or corrupt.
    # Updated after each settled live drift bet in settlement_loop.
    from src.models.bayesian_drift import BayesianDriftModel as _BDM
    _drift_model = _BDM.load()
    logger.info("[startup] Bayesian drift model: %s", _drift_model.summary())

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

    logger.info("Starting Binance SOL feed...")
    sol_feed = sol_binance_load()
    await sol_feed.start()

    logger.info("Starting Binance XRP feed...")
    xrp_feed = xrp_binance_load()
    await xrp_feed.start()

    # ── Start Coinbase backup feeds (DualPriceFeed = Binance primary + Coinbase backup) ──
    # If Binance WebSocket goes stale (>35s no tick), DualPriceFeed falls back to Coinbase
    # REST API (free, no auth, 30s poll). If both stale → current_price() returns None.
    logger.info("Starting Coinbase backup feeds (BTC/ETH/SOL/XRP)...")
    btc_coinbase = CoinbasePriceFeed(symbol="BTC")
    eth_coinbase = CoinbasePriceFeed(symbol="ETH")
    sol_coinbase = CoinbasePriceFeed(symbol="SOL")
    xrp_coinbase = CoinbasePriceFeed(symbol="XRP")
    await btc_coinbase.start()
    await eth_coinbase.start()
    await sol_coinbase.start()
    await xrp_coinbase.start()
    btc_feed = DualPriceFeed(primary=btc_feed, backup=btc_coinbase)
    eth_feed = DualPriceFeed(primary=eth_feed, backup=eth_coinbase)
    sol_feed = DualPriceFeed(primary=sol_feed, backup=sol_coinbase)
    xrp_feed = DualPriceFeed(primary=xrp_feed, backup=xrp_coinbase)
    logger.info("DualPriceFeed active: Binance primary + Coinbase backup for BTC/ETH/SOL/XRP")

    # ── Event-driven BTC move trigger (Phase 2 latency reduction) ─────
    # btc_price_monitor fires asyncio.Condition.notify_all() when BTC moves ≥ 0.05%.
    # All crypto trading_loop calls wait on this condition instead of sleeping.
    # Result: loop wakes within 1-3s of a BTC move vs up to 10s (POLL_INTERVAL_SEC) before.
    _btc_move_condition = asyncio.Condition()
    btc_monitor_task = asyncio.create_task(
        btc_price_monitor(
            btc_feed=btc_feed,
            condition=_btc_move_condition,
            min_move_pct=0.05,
            check_interval_sec=0.5,
        ),
        name="btc_price_monitor",
    )
    logger.info("BTC price monitor started (event-driven trigger, 0.05%% move threshold)")

    # ── Load strategies ───────────────────────────────────────────────
    strategy = strategy_load()
    logger.info("Strategy loaded: %s", strategy.name)
    drift_strategy = drift_strategy_load()
    logger.info("Strategy loaded: %s (LIVE BTC drift)", drift_strategy.name)
    eth_lag_strategy = eth_lag_load()
    logger.info("Strategy loaded: %s (paper-only ETH lag — returning to calibration)", eth_lag_strategy.name)
    eth_drift_strategy = eth_drift_load()
    logger.info("Strategy loaded: %s (STAGE 1 ETH drift — Kelly + $5 cap, graduated Session 44)", eth_drift_strategy.name)
    sol_drift_strategy = sol_drift_load()
    logger.info("Strategy loaded: %s (STAGE 1 SOL drift — Kelly + $5 cap, promoted S48 per Matthew)", sol_drift_strategy.name)
    xrp_drift_strategy = xrp_drift_load()
    logger.info("Strategy loaded: %s (micro-live XRP drift, 1 contract/bet)", xrp_drift_strategy.name)

    # ── Inject Bayesian posterior into all 4 drift strategies (Dim 4) ─────
    # Each strategy holds a reference to the shared model loaded at startup.
    # When model.should_override_static() (30+ live obs), generate_signal() uses
    # model.predict(drift_pct) instead of the static sigmoid. Both paths still
    # apply the time-blending adjustment toward 0.5 early in the window.
    for _drift_strat in [drift_strategy, eth_drift_strategy, sol_drift_strategy, xrp_drift_strategy]:
        _drift_strat._drift_model = _drift_model
    logger.info(
        "[startup] Bayesian model injected into 4 drift strategies "
        "(n=%d obs, override_active=%s)",
        _drift_model.n_observations,
        _drift_model.should_override_static(),
    )

    # ── Temperature calibrator — per-strategy post-hoc confidence correction ──
    # Session 107: ETH (p=0.015) and XRP (p=0.033) have statistically significant
    # calibration overconfidence. T_s shrinks overconfident win_probs toward 50%,
    # reducing Kelly bet size on strategies with no real edge.
    _calibrator = _StrategyCalibrator()
    for _drift_strat in [drift_strategy, eth_drift_strategy, sol_drift_strategy, xrp_drift_strategy]:
        _drift_strat._calibrator = _calibrator
    logger.info(
        "[startup] Temperature calibrator loaded — ETH T=%.3f  BTC T=%.3f  SOL T=%.3f  XRP T=%.3f",
        _calibrator.temperature("eth_drift_v1"),
        _calibrator.temperature("btc_drift_v1"),
        _calibrator.temperature("sol_drift_v1"),
        _calibrator.temperature("xrp_drift_v1"),
    )

    btc_imbalance_strategy = load_btc_imbalance_from_config()
    logger.info("Strategy loaded: %s (paper-only BTC orderbook imbalance)", btc_imbalance_strategy.name)
    eth_imbalance_strategy = load_eth_imbalance_from_config()
    logger.info("Strategy loaded: %s (PAPER-ONLY — ETH orderbook imbalance, Brier 0.340 disabled live S47)", eth_imbalance_strategy.name)
    from src.data.weather import KALSHI_WEATHER_CITIES, build_gefs_feed
    from src.strategies.weather_forecast import WeatherForecastStrategy as _WeatherStrategy
    # NYC weather feed + strategy (loaded from config as before)
    weather_feed = weather_feed_load()
    weather_strategy = weather_strategy_load()
    logger.info("Strategy loaded: %s (paper-only NYC weather forecast)", weather_strategy.name)
    # Additional city feeds + strategies (LAX, CHI, DEN, MIA)
    _weather_other_cities = {}  # city_key → (feed, strategy, series_ticker)
    for _city_key, (_series, _city_params) in KALSHI_WEATHER_CITIES.items():
        if _city_key == "nyc":
            continue  # NYC already handled above
        _feed = build_gefs_feed(_city_params)
        _strat = _WeatherStrategy(weather_feed=_feed, name_override=f"weather_{_city_key}_v1")
        _weather_other_cities[_city_key] = (_feed, _strat, _series)
        logger.info("Strategy loaded: weather_%s_v1 (paper-only %s weather, %s)", _city_key, _city_params["city_name"], _series)
    fred_feed = fred_feed_load()
    fomc_strategy = fomc_strategy_load(fred_feed=fred_feed)
    logger.info("Strategy loaded: %s (paper-only FOMC yield curve, fires ~8x/year)", fomc_strategy.name)
    unemployment_strategy = unemployment_strategy_load(fred_feed=fred_feed)
    logger.info("Strategy loaded: %s (paper-only BLS unemployment, fires ~12x/year)", unemployment_strategy.name)
    sol_lag_strategy = sol_lag_load()
    logger.info("Strategy loaded: %s (paper-only SOL 15-min lag, KXSOL15M)", sol_lag_strategy.name)

    from src.strategies.crypto_daily import CryptoDailyStrategy
    _cdcfg = config.get("crypto_daily", {})
    btc_daily_strategy = CryptoDailyStrategy(
        asset="BTC",
        series_ticker="KXBTCD",
        min_drift_pct=_cdcfg.get("min_drift_pct", 0.005),
        min_edge_pct=_cdcfg.get("min_edge_pct", 0.04),
        min_minutes_remaining=_cdcfg.get("min_minutes_remaining", 30.0),
        max_minutes_remaining=_cdcfg.get("max_minutes_remaining", 360.0),
        min_volume=_cdcfg.get("min_volume", 100),
        direction_filter="no",  # contrarian: only bet NO on upward drift (S47 hypothesis)
    )
    logger.info("Strategy loaded: %s (paper-only KXBTCD, direction_filter=no contrarian)", btc_daily_strategy.name)
    eth_daily_strategy = CryptoDailyStrategy(
        asset="ETH",
        series_ticker="KXETHD",
        min_drift_pct=_cdcfg.get("min_drift_pct", 0.005),
        min_edge_pct=_cdcfg.get("min_edge_pct", 0.04),
        min_minutes_remaining=_cdcfg.get("min_minutes_remaining", 30.0),
        max_minutes_remaining=_cdcfg.get("max_minutes_remaining", 360.0),
        min_volume=_cdcfg.get("min_volume", 100),
    )
    logger.info("Strategy loaded: %s (paper-only ETH hourly daily markets KXETHD)", eth_daily_strategy.name)
    sol_daily_strategy = CryptoDailyStrategy(
        asset="SOL",
        series_ticker="KXSOLD",
        min_drift_pct=_cdcfg.get("min_drift_pct", 0.005),
        min_edge_pct=_cdcfg.get("min_edge_pct", 0.04),
        min_minutes_remaining=_cdcfg.get("min_minutes_remaining", 30.0),
        max_minutes_remaining=_cdcfg.get("max_minutes_remaining", 360.0),
        min_volume=_cdcfg.get("min_volume", 100),
    )
    logger.info("Strategy loaded: %s (paper-only SOL hourly daily markets KXSOLD)", sol_daily_strategy.name)

    # ── Polymarket copy-trade client ──────────────────────────────────
    # Ed25519 auth, api.polymarket.us/v1, sports-only US iOS beta platform
    try:
        from src.platforms.polymarket import load_from_env as polymarket_load
        pm_client = polymarket_load()
        logger.info("Polymarket client loaded (api.polymarket.us, Ed25519 auth)")
    except Exception as _pm_err:
        pm_client = None
        logger.warning("Polymarket client unavailable — copy_trade_loop will be skipped: %s", _pm_err)

    # ── Run ───────────────────────────────────────────────────────────
    _configured_markets = config.get("strategy", {}).get("markets", ["KXBTC15M"])
    if not _configured_markets:
        print("ERROR: config.yaml strategy.markets is empty. Add at least one ticker (e.g., KXBTC15M).")
        sys.exit(1)
    btc_series_ticker = _configured_markets[0]
    eth_series_ticker = config.get("strategy", {}).get("eth_markets", ["KXETH15M"])[0]
    max_daily_bets_live = config.get("risk", {}).get("max_daily_bets_live", 10)
    max_daily_bets_paper = config.get("risk", {}).get("max_daily_bets_paper", 0)
    paper_slippage_ticks = config.get("risk", {}).get("paper_slippage_ticks", 1)
    paper_fill_probability = config.get("risk", {}).get("paper_fill_probability", 1.0)

    # Shared lock for live trading loops — serializes check→execute→record_trade so
    # two loops can't both pass check_order_allowed() before either increments the
    # hourly counter. Paper loops don't need the lock (no hourly soft stop).
    _live_trade_lock = asyncio.Lock()

    # Stagger the 4 loops by 7-8s each to spread Kalshi API calls evenly:
    #   btc_lag=0s, eth_lag=7s, btc_drift=15s, eth_drift=22s
    # BTC lag: STAGE 1 LIVE — re-promoted Session 41 (45/30 bets, Brier 0.191 — graduated).
    # Signal frequency is low (~0 signals/week — HFTs price KXBTC15M same minute as BTC move)
    # but statistical edge is valid (66.7% accuracy, 13.5% edge). Bets fire when signal clears
    # threshold; daily loss limit is the primary risk governor.
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
            max_daily_bets=max_daily_bets_live,
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            btc_move_condition=_btc_move_condition,
        ),
        name="trading_loop",
    )
    # ETH lag: PAPER-ONLY — returned to paper 2026-03-01 (graduation criteria not met:
    # 0/30 paper trades completed before live promotion — process violation).
    # Re-promote to live only after: 30+ settled paper trades + Brier < 0.25.
    # See .planning/PRINCIPLES.md — graduation criteria are mandatory, not suggestions.
    eth_lag_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_lag_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=live_confirmed,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_trading",
            initial_delay_sec=7.0,
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=None,
            btc_move_condition=_btc_move_condition,
        ),
        name="eth_lag_loop",
    )
    # BTC drift: STAGE 1 LIVE (promoted Session 41: 42/30 bets, Brier 0.249 — graduated).
    # calibration_max_usd removed: Kelly + HARD_MAX_TRADE_USD ($5) now governs bet size.
    # Daily loss limit is the primary risk governor.
    _DRIFT_CALIBRATION_CAP_USD = 0.01   # still used by XRP drift (still in calibration phase). SOL promoted to Stage 1 (S48).
    drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            strategy=drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker=btc_series_ticker,
            loop_name="drift",
            initial_delay_sec=15.0,
            max_daily_bets=0,  # unlimited — daily loss limit governs
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            calibration_max_usd=_DRIFT_CALIBRATION_CAP_USD,  # S60: demoted to micro-live. 54 bets, 48% win rate, -11.12 USD. Losing real money.
            # direction_filter: YES signals have 30% win rate (6/20, p=3.7%) vs NO at 61%
            # (14/23). Upward BTC drift is already priced into Kalshi YES market by HFTs
            # before our signal fires — the edge is illusory. Downward drift is slower to
            # price in and retains real edge. Restrict to NO-only until YES edge recovers.
            direction_filter="no",
            btc_move_condition=_btc_move_condition,
            maker_mode=True,  # S65: post_only=True, 30s expiration. Saves ~75% on fees (~5c/trade).
        ),
        name="drift_loop",
    )
    # ETH drift: STAGE 1 (graduated Session 44 — 30/30 live bets, Brier 0.255 < 0.30 threshold).
    # Kelly + $5 HARD_MAX governs bet size. calibration_max_usd removed.
    # Session 36 original: micro-live, 1 contract/bet (~$0.35-0.65) for data collection.
    # Stage 1 promotion: 30 live bets + Brier 0.255 confirmed by --graduation-status 2026-03-10.
    eth_drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_drift",
            initial_delay_sec=22.0,
            max_daily_bets=0,  # unlimited — daily loss limit governs
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            calibration_max_usd=_DRIFT_CALIBRATION_CAP_USD,  # S60: demoted to micro-live. 87 bets, 49% win rate, -16.24 USD. Biggest P&L drag.
            btc_move_condition=_btc_move_condition,
            # S53: direction_filter="yes" — YES side: 36 bets 61.1% wins +0.711 USD/bet EV
            # NO side: 31 bets 48.4% wins -0.212 USD/bet EV. Z=1.04, p=0.148. 67 bets total
            # (≥30 per side — meets PRINCIPLES.md threshold). Same pattern as btc/sol reversed.
            # Estimated +2.54 USD/day. Re-evaluate at 30+ YES-only settled bets.
            direction_filter="yes",
            maker_mode=True,  # S65: post_only=True, 30s expiration. Saves ~75% on fees (~5c/trade).
        ),
        name="eth_drift_loop",
    )
    # SOL drift: STAGE 1 — promoted S48 per Matthew explicit instruction.
    # Brier 0.181 (best signal across all strategies, well below 0.25 gate).
    # 16/30 live bets at promotion — Matthew explicitly authorized Stage 1 before 30-bet gate.
    # calibration_max_usd removed: Kelly + HARD_MAX_TRADE_USD ($5) now governs bet size.
    # KXSOL15M series, stagger 29s.
    sol_drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=sol_feed,
            strategy=sol_drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker="KXSOL15M",
            loop_name="sol_drift",
            initial_delay_sec=29.0,
            max_daily_bets=0,  # unlimited — daily loss limit governs
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            calibration_max_usd=None,  # S81: graduated Stage 2 — 30 settled bets, Brier 0.184, +6.07 USD. Kelly + HARD_MAX governs.
            btc_move_condition=_btc_move_condition,
            direction_filter="no",  # S51: NO wins 11/11 (100%), YES only 63.6% — filter YES bets
            maker_mode=True,  # S98: post_only=True, 30s expiration. Same as btc/eth drift. Saves ~75% on fees.
        ),
        name="sol_drift_loop",
    )
    # XRP drift: micro-live, stagger 33s (offset from sol_drift at 29s)
    # Enabled Session 41: XRP ~2x more volatile than BTC → more frequent signals.
    # Same 1-contract/bet cap as btc_drift/eth_drift/sol_drift. KXXRP15M series.
    # Do NOT raise cap until: 30+ xrp live trades + Brier < 0.30.
    xrp_drift_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=xrp_feed,
            strategy=xrp_drift_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker="KXXRP15M",
            loop_name="xrp_drift",
            initial_delay_sec=33.0,
            max_daily_bets=0,  # unlimited — daily loss limit governs
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            calibration_max_usd=_DRIFT_CALIBRATION_CAP_USD,
            btc_move_condition=_btc_move_condition,
            direction_filter="yes",  # YES 83% (5/6) vs NO 36% (4/11) — applied Session 54
            maker_mode=True,  # S98: post_only=True, 30s expiration. Same as btc/eth drift. Saves ~75% on fees.
        ),
        name="xrp_drift_loop",
    )
    # BTC orderbook imbalance: paper-only, stagger 36s (was 29s — shifted for sol_drift)
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
            initial_delay_sec=36.0,
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            btc_move_condition=_btc_move_condition,
        ),
        name="btc_imbalance_loop",
    )
    # ETH orderbook imbalance: STAGE 1 LIVE — promoted Session 41 (41/30 bets — graduated).
    # Signal: orderbook depth ratio >0.65 (YES-heavy) or <0.35 (NO-heavy) = directional edge.
    # Brier n/a — imbalance doesn't produce win_prob, but 41 paper bets at 35-65¢ guard.
    # trade_lock: serializes with all live loops to prevent hourly rate limit bypass.
    # Daily loss limit is the primary risk governor.
    # eth_imbalance: PAPER-ONLY as of 2026-03-11 (Session 47)
    # Brier 0.340 at 15 live bets — 27% systematic calibration error confirmed.
    # Model predicts 67% win, actual is ~40%. Disabled live until model is recalibrated.
    # Watchdog originally set for bet 22 but evidence conclusive at bet 15.
    eth_imbalance_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_imbalance_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,  # DISABLED — Brier 0.340 (Session 47)
            live_confirmed=live_confirmed,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_imbalance",
            initial_delay_sec=36.0,
            max_daily_bets=max_daily_bets_live,
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
            trade_lock=_live_trade_lock,
            btc_move_condition=_btc_move_condition,
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
            max_daily_bets=max_daily_bets_paper,
        ),
        name="weather_loop",
    )
    # Additional city weather loops: LAX, CHI, DEN, MIA (paper-only, staggered 2s apart)
    _weather_other_tasks = []
    for _i, (_ck, (_wfeed, _wstrat, _wseries)) in enumerate(_weather_other_cities.items()):
        _delay = 45.0 + _i * 2.0  # 45, 47, 49, 51s (stagger from NYC at 43s)
        _t = asyncio.create_task(
            weather_loop(
                kalshi=kalshi,
                weather_strategy=_wstrat,
                weather_feed=_wfeed,
                kill_switch=kill_switch,
                db=db,
                series_ticker=_wseries,
                loop_name=f"weather_{_ck}",
                initial_delay_sec=_delay,
                max_daily_bets=max_daily_bets_paper,
            ),
            name=f"weather_{_ck}_loop",
        )
        _weather_other_tasks.append(_t)
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
            max_daily_bets=max_daily_bets_paper,
        ),
        name="fomc_loop",
    )
    # Unemployment rate: paper-only, polls every 30 min, stagger 58s
    unrate_series = config.get("strategy", {}).get("unemployment", {}).get("series_ticker", "KXUNRATE")
    unemployment_task = asyncio.create_task(
        unemployment_loop(
            kalshi=kalshi,
            unemployment_strategy=unemployment_strategy,
            fred_feed=fred_feed,
            kill_switch=kill_switch,
            db=db,
            series_ticker=unrate_series,
            loop_name="unemployment",
            initial_delay_sec=58.0,
            max_daily_bets=max_daily_bets_paper,
        ),
        name="unemployment_loop",
    )
    # SOL lag: paper-only, KXSOL15M series, stagger 65s
    sol_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=sol_feed,
            strategy=sol_lag_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=False,
            live_confirmed=False,
            btc_series_ticker="KXSOL15M",
            loop_name="sol_lag",
            initial_delay_sec=65.0,
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
            fill_probability=paper_fill_probability,
        ),
        name="sol_lag_loop",
    )
    settle_task = asyncio.create_task(
        settlement_loop(kalshi=kalshi, db=db, kill_switch=kill_switch,
                        drift_model=_drift_model, calibrator=_calibrator),
        name="settlement_loop",
    )

    # ── Crypto daily loops (KXBTCD / KXETHD / KXSOLD) ────────────────
    # Paper-only — all 24 hourly slots per day, ATM drift strategy.
    # Stagger 90s / 100s / 110s to spread Kalshi API calls.
    btc_daily_task = asyncio.create_task(
        crypto_daily_loop(
            kalshi=kalshi,
            asset_feed=btc_feed,
            strategy=btc_daily_strategy,
            kill_switch=kill_switch,
            db=db,
            loop_name="btc_daily",
            initial_delay_sec=90.0,
            max_daily_bets=5,
            direction_filter="no",  # defense-in-depth (strategy also filters; guards misconfiguration)
        ),
        name="btc_daily_loop",
    )
    eth_daily_task = asyncio.create_task(
        crypto_daily_loop(
            kalshi=kalshi,
            asset_feed=eth_feed,
            strategy=eth_daily_strategy,
            kill_switch=kill_switch,
            db=db,
            loop_name="eth_daily",
            initial_delay_sec=100.0,
            max_daily_bets=5,
        ),
        name="eth_daily_loop",
    )
    sol_daily_task = asyncio.create_task(
        crypto_daily_loop(
            kalshi=kalshi,
            asset_feed=sol_feed,
            strategy=sol_daily_strategy,
            kill_switch=kill_switch,
            db=db,
            loop_name="sol_daily",
            initial_delay_sec=110.0,
            max_daily_bets=5,
        ),
        name="sol_daily_loop",
    )

    # ── Daily sniper loop (KXBTCD near-expiry paper sniping) ──────────
    # Paper-only. Targets KXBTCD YES/NO at 90-94c within 90min of settlement.
    # Same FLB mechanism as expiry_sniper_v1. CCA REQ-026 validation pending.
    # Stagger 120s to spread from daily loops. Data collection starts immediately.
    daily_sniper_task = asyncio.create_task(
        daily_sniper_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            db=db,
            kill_switch=kill_switch,
            initial_delay_sec=120.0,
            max_daily_bets=10,
            live_executor_enabled=True,
            live_confirmed=live_confirmed,
            trade_lock=_live_trade_lock,
        ),
        name="daily_sniper_loop",
    )

    # ── Economics sniper loop (KXCPI/KXGDP FLB — paper-only K2) ─────────
    # Paper-only. Targets KXCPI-*/KXGDP-* at 88-93c within 48h of settlement.
    # Academic basis: Burgi et al. (2026) [SSRN 5502658] — FLB strongest 24-48h pre-settlement.
    # CCA REQ-032: April 8 entry window for KXCPI-26MAR-T0.6. 0.5x Kelly paper phase.
    economics_sniper_task = asyncio.create_task(
        economics_sniper_loop(
            kalshi=kalshi,
            db=db,
            kill_switch=kill_switch,
            initial_delay_sec=180.0,   # stagger: after daily_sniper (120s) + buffer
            max_daily_bets=5,
        ),
        name="economics_sniper_loop",
    )
    logger.info("Economics sniper loop started (paper-only, KXCPI/KXGDP, 88-93c, 48h window)")

    # ── Maker sniper loop (paper-only — 30 fills before live gate) ────────
    # Same FLB signal as expiry_sniper_v1, but places maker limit orders 1c below ask.
    # Academic basis: Becker (2026) — makers earn +1.12% structural vs takers -1.12%.
    # Paper phase: 30 fills needed. Fill rate, WR, and time-to-fill tracked vs expiry_sniper.
    # CCA REQ-039 implementation. Live gate: fill_rate >= 40% AND WR within expiry_sniper CI.
    maker_sniper_task = asyncio.create_task(
        maker_sniper_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            eth_feed=eth_feed,
            sol_feed=sol_feed,
            xrp_feed=xrp_feed,
            db=db,
            kill_switch=kill_switch,
            initial_delay_sec=135.0,   # stagger: between daily_sniper (120s) and economics_sniper (180s)
            max_daily_bets=5,
        ),
        name="maker_sniper_loop",
    )
    logger.info("Maker sniper loop started (paper-only, 90-94c FLB, 1c offset, 30-fill gate)")

    # ── Copy-trade loop (Polymarket PRIMARY strategy) ─────────────────
    # Paper-only. Polls top whale wallets every 5 min, applies decoy filters,
    # paper-executes genuine signals on api.polymarket.us markets.
    # Skipped gracefully if PM client failed to load.
    if pm_client is not None:
        copy_task = asyncio.create_task(
            copy_trade_loop(
                pm_client=pm_client,
                db=db,
                kill_switch=kill_switch,
                initial_delay_sec=80.0,     # stagger after Kalshi loops
                poll_interval_sec=300,       # 5-min poll cadence
                whale_refresh_sec=21_600,    # refresh whale list every 6 hours
                paper_slippage_ticks=paper_slippage_ticks,
                paper_fill_probability=paper_fill_probability,
            ),
            name="copy_trade_loop",
        )
        logger.info("Copy-trade loop started (paper, 5-min poll, 50 whale wallets)")
    else:
        copy_task = asyncio.create_task(asyncio.sleep(0), name="copy_trade_noop")
        logger.warning("Copy-trade loop SKIPPED — PM client unavailable")

    # ── Expiry sniper loop (Kalshi KXBTC15M) ─────────────────────────
    # Enter when YES/NO >= 90c in final 14 min of window + coin drift confirms.
    # Academic basis: favorite-longshot bias — heavy favorites close >90% of time.
    # Source: processoverprofit.blog V7 (clean rebuild — NOT their NightShark/JS code).
    # Live path uses price_guard_min=1, price_guard_max=99 (operates at 87-99c).
    expiry_sniper_task = asyncio.create_task(
        expiry_sniper_loop(
            kalshi=kalshi,
            btc_feed=btc_feed,
            eth_feed=eth_feed,
            sol_feed=sol_feed,
            xrp_feed=xrp_feed,
            db=db,
            kill_switch=kill_switch,
            initial_delay_sec=110.0,   # stagger after copy_trade (80s) + sports_futures (95s)
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            trade_lock=_live_trade_lock,
            max_daily_bets=0,  # S60: UNLIMITED — 97% win rate across 85 data points, every signal is +EV. Matthew directive.
            # Previously: 10 (S59), 20 (S60 early). Removed entirely to capture every favorable-longshot window.
        ),
        name="expiry_sniper_loop",
    )
    _sniper_mode = "LIVE" if (live_mode and live_confirmed) else "paper-only"
    logger.info("Expiry sniper loop started (%s BTC/ETH/SOL/XRP 15M, 90c+ threshold, 10s poll, NO daily cap)", _sniper_mode)

    # ── Sports-futures mispricing loop (Polymarket supplemental) ─────
    # Paper-only. Compares PM championship futures to bookmaker consensus.
    # 30-min poll; 6-hr feed cache keeps credit usage ~30-90/month.
    # Disabled gracefully if PM client or SDATA_KEY unavailable.
    if pm_client is not None:
        sports_futures_task = asyncio.create_task(
            sports_futures_loop(
                pm_client=pm_client,
                db=db,
                kill_switch=kill_switch,
                initial_delay_sec=95.0,        # stagger after copy_trade (80s)
                poll_interval_sec=1_800,        # 30-min cadence
                paper_slippage_ticks=paper_slippage_ticks,
                paper_fill_probability=paper_fill_probability,
            ),
            name="sports_futures_loop",
        )
        logger.info("Sports-futures loop started (paper, 30-min poll, NBA/NHL/NCAAB)")
    else:
        sports_futures_task = asyncio.create_task(
            asyncio.sleep(0), name="sports_futures_noop"
        )
        logger.warning("Sports-futures loop SKIPPED — PM client unavailable")

    # ── Signal handlers (clean shutdown on SIGTERM/SIGHUP) ───────────
    import signal as _signal
    _loop = asyncio.get_running_loop()

    def _on_signal(signame: str) -> None:
        logger.info("Received %s — requesting clean shutdown", signame)
        btc_monitor_task.cancel()
        trade_task.cancel()
        eth_lag_task.cancel()
        drift_task.cancel()
        eth_drift_task.cancel()
        sol_drift_task.cancel()
        xrp_drift_task.cancel()
        btc_imbalance_task.cancel()
        eth_imbalance_task.cancel()
        weather_task.cancel()
        for _wt in _weather_other_tasks:
            _wt.cancel()
        fomc_task.cancel()
        unemployment_task.cancel()
        sol_task.cancel()
        settle_task.cancel()
        btc_daily_task.cancel()
        eth_daily_task.cancel()
        sol_daily_task.cancel()
        copy_task.cancel()
        sports_futures_task.cancel()
        expiry_sniper_task.cancel()
        daily_sniper_task.cancel()
        economics_sniper_task.cancel()
        maker_sniper_task.cancel()

    for _sig, _sname in ((_signal.SIGTERM, "SIGTERM"), (_signal.SIGHUP, "SIGHUP")):
        _loop.add_signal_handler(_sig, lambda n=_sname: _on_signal(n))

    try:
        results = await asyncio.gather(
            btc_monitor_task,
            trade_task, eth_lag_task, drift_task, eth_drift_task, sol_drift_task,
            xrp_drift_task, btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task,
            unemployment_task, sol_task, settle_task,
            btc_daily_task, eth_daily_task, sol_daily_task, copy_task,
            sports_futures_task,
            expiry_sniper_task,
            daily_sniper_task,
            economics_sniper_task,
            maker_sniper_task,
            return_exceptions=True,  # S90: prevent one task's exception from killing all others
        )
        # Log any tasks that died with unexpected exceptions (not CancelledError)
        _task_names = [
            "btc_monitor", "trade", "eth_lag", "drift", "eth_drift", "sol_drift",
            "xrp_drift", "btc_imbalance", "eth_imbalance", "weather", "fomc",
            "unemployment", "sol_lag", "settle",
            "btc_daily", "eth_daily", "sol_daily", "copy_trade",
            "sports_futures", "expiry_sniper", "daily_sniper", "economics_sniper",
            "maker_sniper",
        ]
        for _tname, _result in zip(_task_names, results):
            if isinstance(_result, Exception) and not isinstance(_result, asyncio.CancelledError):
                logger.critical("[main] Task '%s' died unexpectedly: %s", _tname, _result, exc_info=_result)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass  # Normal shutdown — SIGTERM or Ctrl+C; finally block handles cleanup
    finally:
        btc_monitor_task.cancel()
        trade_task.cancel()
        eth_lag_task.cancel()
        drift_task.cancel()
        eth_drift_task.cancel()
        sol_drift_task.cancel()
        xrp_drift_task.cancel()
        btc_imbalance_task.cancel()
        eth_imbalance_task.cancel()
        weather_task.cancel()
        for _wt in _weather_other_tasks:
            _wt.cancel()
        fomc_task.cancel()
        unemployment_task.cancel()
        sol_task.cancel()
        settle_task.cancel()
        btc_daily_task.cancel()
        eth_daily_task.cancel()
        sol_daily_task.cancel()
        copy_task.cancel()
        sports_futures_task.cancel()
        expiry_sniper_task.cancel()
        daily_sniper_task.cancel()
        economics_sniper_task.cancel()
        maker_sniper_task.cancel()
        await asyncio.gather(
            btc_monitor_task,
            trade_task, eth_lag_task, drift_task, eth_drift_task, sol_drift_task,
            xrp_drift_task, btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task,
            unemployment_task, sol_task, settle_task,
            btc_daily_task, eth_daily_task, sol_daily_task, copy_task,
            sports_futures_task,
            expiry_sniper_task,
            daily_sniper_task,
            economics_sniper_task,
            maker_sniper_task,
            return_exceptions=True,
        )
        logger.info("Stopping feeds and connections...")
        await btc_feed.stop()
        await eth_feed.stop()
        await sol_feed.stop()
        await xrp_feed.stop()
        await kalshi.close()
        db.close()
        _release_bot_lock()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    # Ensure required directories exist (safe on fresh clone)
    (PROJECT_ROOT / "logs" / "errors").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "logs" / "trades").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    # S90: wrap asyncio.run in try/except to ensure crash traceback is always logged
    # Previously: uncaught exceptions printed to stderr only (lost if nohup redirects stderr)
    _crash_log = PROJECT_ROOT / "data" / "polybot_crash.log"
    try:
        asyncio.run(main())
    except Exception as _crash_exc:
        import traceback as _tb
        _ts = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(_crash_log, "a") as _f:
            _f.write(f"\n=== CRASH {_ts} ===\n")
            _tb.print_exc(file=_f)
        raise  # re-raise so the exit code is non-zero
