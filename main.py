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
    slippage_ticks: int = 1,
):
    """Main async loop: poll markets, generate signals, execute trades."""
    from src.execution import paper as paper_mod
    import time

    if initial_delay_sec > 0:
        logger.info("[%s] Startup delay %.0fs (stagger)", loop_name, initial_delay_sec)
        await asyncio.sleep(initial_delay_sec)

    last_bankroll_snapshot = 0.0
    # Paper/live mode for dedup and daily-cap filtering — computed once, never changes mid-run
    is_paper_mode = not (live_executor_enabled and live_confirmed)

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
                        strategy_name=strategy.name,
                    )
                else:
                    _slip = slippage_ticks
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
                    if live_executor_enabled and live_confirmed:
                        _announce_live_bet(result, strategy_name=strategy.name)

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
                ok, reason = kill_switch.check_order_allowed(
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
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=weather_strategy.name,
                    slippage_ticks=_wslip,
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
                ok, reason = kill_switch.check_order_allowed(
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
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=fomc_strategy.name,
                    slippage_ticks=_fslip,
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
                ok, reason = kill_switch.check_order_allowed(
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
                paper_exec = paper_mod.PaperExecutor(
                    db=db,
                    strategy_name=unemployment_strategy.name,
                    slippage_ticks=_uslip,
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
                    # Only count LIVE trades toward daily loss limit (paper losses are not real money)
                    if not trade["is_paper"]:
                        if won:
                            kill_switch.record_win()
                        else:
                            kill_switch.record_loss(abs(pnl_cents) / 100.0)

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
    Print graduation progress table for all 8 strategies.

    Imports _GRAD thresholds from setup/verify.py (single source of truth).
    Reads DB only — does NOT start Kalshi or Binance connections.
    """
    from setup.verify import _GRAD
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
        stats = db.graduation_stats(strategy)

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

    # Per-strategy breakdown
    strategies = sorted({t.get("strategy", "unknown") for t in today_trades if t.get("strategy")})
    if strategies:
        print(f"\n  {'Strategy':<28} {'Bets':>4} {'W/L':>5} {'P&L':>8}")
        print("  " + "-" * (width - 2))
        for strat in strategies:
            strat_settled = [t for t in settled if t.get("strategy") == strat]
            strat_wins = [t for t in strat_settled if t["result"] == t["side"]]
            strat_pnl = sum(t.get("pnl_cents", 0) or 0 for t in strat_settled) / 100
            strat_all_today = [t for t in today_trades if t.get("strategy") == strat]
            wl = f"{len(strat_wins)}/{len(strat_settled)}"
            mode = "📋" if all(t.get("is_paper") for t in strat_all_today) else "🔴"
            print(f"  {mode} {strat:<26} {len(strat_all_today):>4} {wl:>5} ${strat_pnl:>6.2f}")

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
    parser.add_argument("--graduation-status", action="store_true",
                        help="Print graduation progress for all 8 strategies and exit")
    parser.add_argument("--status", action="store_true",
                        help="Print bot status (bankroll, prices, pending bets, recent trades) and exit")
    parser.add_argument("--export-trades", action="store_true",
                        help="Export all trades to reports/trades.csv and exit")
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
    _read_only_mode = args.status or args.report or args.graduation_status or args.export_trades
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
    from src.strategies.unemployment_rate import load_from_config as unemployment_strategy_load
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
    logger.info("Strategy loaded: %s (LIVE BTC drift)", drift_strategy.name)
    eth_lag_strategy = eth_lag_load()
    logger.info("Strategy loaded: %s (LIVE ETH lag)", eth_lag_strategy.name)
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
    unemployment_strategy = unemployment_strategy_load()
    logger.info("Strategy loaded: %s (paper-only BLS unemployment, fires ~12x/year)", unemployment_strategy.name)

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
            max_daily_bets=max_daily_bets_live,
            slippage_ticks=paper_slippage_ticks,
        ),
        name="trading_loop",
    )
    # ETH lag: LIVE mode as of 2026-02-28 (same path as btc_lag), stagger 7s
    eth_lag_task = asyncio.create_task(
        trading_loop(
            kalshi=kalshi,
            btc_feed=eth_feed,
            strategy=eth_lag_strategy,
            kill_switch=kill_switch,
            db=db,
            live_executor_enabled=live_mode,
            live_confirmed=live_confirmed,
            btc_series_ticker=eth_series_ticker,
            loop_name="eth_trading",
            initial_delay_sec=7.0,
            max_daily_bets=max_daily_bets_live,
            slippage_ticks=paper_slippage_ticks,
        ),
        name="eth_lag_loop",
    )
    # BTC drift: LIVE (69.1% accuracy confirmed, Brier 0.22), stagger 15s
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
            max_daily_bets=max_daily_bets_live,
            slippage_ticks=paper_slippage_ticks,
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
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
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
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
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
            max_daily_bets=max_daily_bets_paper,
            slippage_ticks=paper_slippage_ticks,
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
        unemployment_task.cancel()
        settle_task.cancel()

    for _sig, _sname in ((_signal.SIGTERM, "SIGTERM"), (_signal.SIGHUP, "SIGHUP")):
        _loop.add_signal_handler(_sig, lambda n=_sname: _on_signal(n))

    try:
        await asyncio.gather(
            trade_task, eth_lag_task, drift_task, eth_drift_task,
            btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task,
            unemployment_task, settle_task,
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
        unemployment_task.cancel()
        settle_task.cancel()
        await asyncio.gather(
            trade_task, eth_lag_task, drift_task, eth_drift_task,
            btc_imbalance_task, eth_imbalance_task, weather_task, fomc_task,
            unemployment_task, settle_task,
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
