"""
scripts/kalshi_real_backtest.py — Real Kalshi price backtest for btc_lag_v1.

Uses actual Kalshi candlestick data (1-min resolution, free API) and Binance BTC
klines to simulate the btc_lag signal with REAL Kalshi YES prices instead of the
50c assumption used in backtest.py.

DATA SOURCES:
  Kalshi REST API (no auth for reads):
    - Settled KXBTC15M markets (last 30 days)
    - 1-min YES candlesticks per market window
  Binance.US REST API (no auth):
    - 1-min BTCUSDT klines for settlement determination and BTC move calc

KEY QUESTION ANSWERED:
  "Is Kalshi already priced in when btc_lag fires?"
  i.e., is YES already at 60-70c instead of 50c when BTC makes a big move?

CANDLESTICK API NOTES (confirmed via probing):
  GET /series/KXBTC15M/markets/{ticker}/candlesticks
    ?start_ts={unix_seconds}&end_ts={unix_seconds}&period_interval=1
  Response: candlesticks[].end_period_ts  (unix seconds)
           candlesticks[].yes_bid.close   (cents)
           candlesticks[].yes_ask.close   (cents)
  Markets API: open_time / close_time fields used for window boundaries
               (NOT parsed from ticker — ticker uses local timezone suffix)

USAGE:
  source venv/bin/activate && python scripts/kalshi_real_backtest.py
  python scripts/kalshi_real_backtest.py --days 30
  python scripts/kalshi_real_backtest.py --days 60
"""

from __future__ import annotations

import argparse
import asyncio
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

# ── Constants ─────────────────────────────────────────────────────────

_KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
_SERIES_TICKER = "KXBTC15M"

_KLINES_URL = "https://api.binance.us/api/v3/klines"
_SYMBOL = "BTCUSDT"
_INTERVAL = "1m"
_MAX_KLINES_PER_REQUEST = 1000

_THRESHOLDS = [0.20, 0.30, 0.40, 0.50]       # BTC move % thresholds to sweep
_MIN_SIGNAL_PRICE_CENTS = 35                   # Price range guard (match live btc_lag.py)
_MAX_SIGNAL_PRICE_CENTS = 65                   # Price range guard (match live btc_lag.py)
_MIN_MINUTES_REMAINING = 3.0                   # Skip signals with < 3 min left
_LAG_SENSITIVITY = 15.0                        # Cents implied per 1% BTC move (from config)
_MIN_EDGE_PCT = 0.04                           # 4% edge minimum (btc_lag live)
_WINDOW_MIN = 15                               # 15-min Kalshi windows
_LAG_WINDOW_SECONDS = 60                       # 60s rolling BTC move window
_POLL_INTERVAL_MIN = 0.5                       # Simulate 30s polling

_RESULTS_PATH = Path(__file__).parent / "real_backtest_results.md"

_KALSHI_RATE_LIMIT_SLEEP = 2.0                 # Sleep on 429 (longer back-off)
_KALSHI_MARKETS_LIMIT = 200                    # Markets per page
_DEFAULT_DAYS = 30
_MAX_MARKETS = 300                             # Cap for candlestick calls; sampled across full date range
_CANDLE_REQUEST_INTERVAL = 0.15               # 150ms between candle requests = ~6.5/sec (well under 20/sec limit)


# ── Data structures ────────────────────────────────────────────────────

@dataclass
class KalshiCandle:
    """1-minute Kalshi candlestick for YES prices."""
    end_ts_ms: int          # unix ms (end of the 1-min period)
    start_ts_ms: int        # unix ms (end_ts_ms - 60_000)
    yes_bid_close: int      # cents
    yes_ask_close: int      # cents
    yes_mid_close: int      # cents (computed: (bid+ask)//2)
    volume: int


@dataclass
class MarketWindow:
    """A settled KXBTC15M market window with its data."""
    ticker: str
    window_open_ms: int     # unix ms (UTC) — from Kalshi API open_time
    window_close_ms: int    # unix ms (UTC) — from Kalshi API close_time
    yes_candles: List[KalshiCandle] = field(default_factory=list)
    btc_candles: Dict[int, float] = field(default_factory=dict)   # {open_ts_ms: close_price}
    settlement: Optional[int] = None  # 1=YES won, 0=NO won (from BTC direction)
    kalshi_result: Optional[str] = None  # "yes" or "no" from Kalshi API


@dataclass
class SignalRecord:
    """A simulated btc_lag evaluation that would have fired at a given minute."""
    ticker: str
    window_open_ms: int
    eval_minute: float          # minutes elapsed in window when evaluated
    btc_move_pct: float         # signed BTC move in 60s
    yes_cents: int              # ACTUAL Kalshi YES price at eval time
    no_cents: int               # estimated NO price (100 - yes_cents - spread)
    minutes_remaining: float
    edge_pct: float             # computed edge at actual price
    side: str                   # "yes" or "no"
    settlement: int             # 1=YES won, 0=NO won


# ── Fee helper (mirrors backtest.py exactly) ────────────────────────────

def _lag_fee_pct(price_cents: int) -> float:
    """Kalshi fee: 7% of p*(1-p) where p = price_cents/100."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


# ── Kalshi API helpers ─────────────────────────────────────────────────

async def _kalshi_get(
    session: aiohttp.ClientSession,
    path: str,
    params: dict,
    retries: int = 3,
) -> Optional[dict]:
    """GET from Kalshi API with rate-limit retry."""
    url = f"{_KALSHI_BASE}{path}"
    for attempt in range(retries):
        try:
            async with session.get(
                url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 429:
                    print(f"  [kalshi] 429 rate limit — sleeping {_KALSHI_RATE_LIMIT_SLEEP}s", flush=True)
                    await asyncio.sleep(_KALSHI_RATE_LIMIT_SLEEP)
                    continue
                if resp.status != 200:
                    text = await resp.text()
                    print(f"  [kalshi] HTTP {resp.status} on {path}: {text[:120]}")
                    return None
                return await resp.json()
        except asyncio.TimeoutError:
            if attempt < retries - 1:
                await asyncio.sleep(1.0)
            else:
                print(f"  [kalshi] Timeout on {path}")
                return None
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(1.0)
            else:
                print(f"  [kalshi] Error on {path}: {e}")
                return None
    return None


def _iso_to_ms(iso_str: Optional[str]) -> Optional[int]:
    """Convert ISO datetime string to unix ms."""
    if not iso_str:
        return None
    try:
        ts = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


async def fetch_settled_markets(
    session: aiohttp.ClientSession,
    days: int,
) -> List[MarketWindow]:
    """
    Pull settled KXBTC15M markets from the last `days` days.

    Uses open_time / close_time from the Kalshi API directly
    (NOT parsed from ticker — ticker uses local timezone).
    Returns list of MarketWindow objects (no candlestick data yet).
    """
    cutoff_ms = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    markets: List[MarketWindow] = []
    cursor = None
    pages_fetched = 0

    while True:
        params: dict = {
            "series_ticker": _SERIES_TICKER,
            "status": "settled",   # Confirmed valid: returns finalized markets
            "limit": _KALSHI_MARKETS_LIMIT,
        }
        if cursor:
            params["cursor"] = cursor

        data = await _kalshi_get(session, "/markets", params)
        if data is None:
            break

        batch = data.get("markets", [])
        if not batch:
            break

        pages_fetched += 1
        hit_cutoff = False

        for m in batch:
            ticker = m.get("ticker", "")
            open_time_str = m.get("open_time")
            close_time_str = m.get("close_time")

            window_open_ms = _iso_to_ms(open_time_str)
            window_close_ms = _iso_to_ms(close_time_str)

            if window_open_ms is None or window_close_ms is None:
                continue

            # Skip markets that are not yet fully closed
            if window_close_ms + 60_000 > now_ms:
                continue

            # Stop if we've gone past our cutoff window
            if window_open_ms < cutoff_ms:
                hit_cutoff = True
                continue

            markets.append(MarketWindow(
                ticker=ticker,
                window_open_ms=window_open_ms,
                window_close_ms=window_close_ms,
                kalshi_result=m.get("result"),
            ))

        if hit_cutoff:
            break

        cursor = data.get("cursor")
        if not cursor:
            break

        # Rate limit: stay at ~7 req/sec (well under 20/sec cap)
        await asyncio.sleep(0.15)

    return markets


# ── Kalshi candlestick fetching ────────────────────────────────────────

async def fetch_kalshi_candles(
    session: aiohttp.ClientSession,
    ticker: str,
    start_ts_s: int,
    end_ts_s: int,
) -> List[KalshiCandle]:
    """
    Fetch 1-minute Kalshi YES candlesticks for a market.

    Confirmed API structure:
      candlestick.end_period_ts  — unix seconds (end of the 1-min period)
      candlestick.yes_bid.close  — YES bid price in cents
      candlestick.yes_ask.close  — YES ask price in cents
    """
    data = await _kalshi_get(
        session,
        f"/series/{_SERIES_TICKER}/markets/{ticker}/candlesticks",
        {
            "start_ts": start_ts_s,
            "end_ts": end_ts_s,
            "period_interval": 1,
        },
    )
    if data is None:
        return []

    raw_candles = data.get("candlesticks", [])
    if not raw_candles:
        return []

    result: List[KalshiCandle] = []
    for c in raw_candles:
        try:
            # end_period_ts is in seconds
            end_ts_s_val = c.get("end_period_ts")
            if not end_ts_s_val:
                continue
            end_ts_ms = int(end_ts_s_val) * 1000
            start_ts_ms = end_ts_ms - 60_000

            # YES bid and ask
            yes_bid_data = c.get("yes_bid", {})
            yes_ask_data = c.get("yes_ask", {})

            yes_bid_close = int(yes_bid_data.get("close", 0) or 0)
            yes_ask_close = int(yes_ask_data.get("close", 0) or 0)

            # Mid price — use whichever is available
            if yes_bid_close > 0 and yes_ask_close > 0:
                yes_mid = (yes_bid_close + yes_ask_close) // 2
            elif yes_bid_close > 0:
                yes_mid = yes_bid_close
            elif yes_ask_close > 0:
                yes_mid = yes_ask_close
            else:
                # Try the generic price.close field
                price_data = c.get("price", {})
                yes_mid = int(price_data.get("close", 0) or 0)

            volume = int(c.get("volume", 0) or 0)

            if yes_mid > 0:
                result.append(KalshiCandle(
                    end_ts_ms=end_ts_ms,
                    start_ts_ms=start_ts_ms,
                    yes_bid_close=yes_bid_close,
                    yes_ask_close=yes_ask_close,
                    yes_mid_close=yes_mid,
                    volume=volume,
                ))
        except Exception:
            continue

    result.sort(key=lambda c: c.end_ts_ms)
    return result


def _yes_price_at(candles: List[KalshiCandle], target_ms: int, tolerance_ms: int = 90_000) -> Optional[int]:
    """
    Find the YES mid price at or near target_ms.

    Matches the candle whose 1-min period contains target_ms
    (i.e., start_ts_ms <= target_ms < end_ts_ms), with tolerance fallback.
    """
    if not candles:
        return None

    # First: try to find a candle that contains target_ms
    for c in candles:
        if c.start_ts_ms <= target_ms < c.end_ts_ms:
            return c.yes_mid_close if c.yes_mid_close > 0 else None

    # Fallback: nearest candle within tolerance
    best_diff = tolerance_ms + 1
    best_price: Optional[int] = None
    for c in candles:
        # Use the midpoint of the candle period
        candle_mid_ms = (c.start_ts_ms + c.end_ts_ms) // 2
        diff = abs(candle_mid_ms - target_ms)
        if diff < best_diff:
            best_diff = diff
            best_price = c.yes_mid_close if c.yes_mid_close > 0 else None

    return best_price if best_diff <= tolerance_ms else None


# ── Binance klines (same pattern as backtest.py) ────────────────────────

async def _fetch_klines_chunk(
    session: aiohttp.ClientSession,
    start_ms: int,
    end_ms: int,
) -> List[Tuple[int, float]]:
    """Fetch up to 1000 1-min BTCUSDT candles from Binance.US."""
    params = {
        "symbol": _SYMBOL,
        "interval": _INTERVAL,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": _MAX_KLINES_PER_REQUEST,
    }
    async with session.get(
        _KLINES_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
    ) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Binance.US klines error {resp.status}: {text[:200]}")
        data = await resp.json()
    # data = [[open_time_ms, open, high, low, close, volume, ...], ...]
    return [(int(row[0]), float(row[4])) for row in data]


async def fetch_btc_candles_range(
    session: aiohttp.ClientSession,
    start_ms: int,
    end_ms: int,
) -> Dict[int, float]:
    """
    Fetch all 1-min BTC candles from start_ms to end_ms.
    Returns {open_time_ms: close_price}.
    Batches into chunks of 1000 candles per Binance.US limit.
    """
    all_candles: Dict[int, float] = {}
    current_ms = start_ms
    batch_ms = _MAX_KLINES_PER_REQUEST * 60 * 1000
    total_batches = math.ceil((end_ms - start_ms) / batch_ms)
    fetched = 0

    while current_ms < end_ms:
        chunk_end = min(current_ms + batch_ms - 1, end_ms)
        try:
            chunk = await _fetch_klines_chunk(session, current_ms, chunk_end)
        except Exception as e:
            print(f"\n  [binance] Error fetching klines: {e}")
            break
        for ts, price in chunk:
            all_candles[ts] = price
        fetched += 1
        pct = fetched / max(1, total_batches) * 100
        print(f"\r        Fetching BTC history: {pct:.0f}% ({fetched}/{total_batches} batches)", end="", flush=True)
        if chunk:
            current_ms = chunk[-1][0] + 60_000
        else:
            break

    print()  # newline after progress bar
    return all_candles


def _price_at(candles: Dict[int, float], target_ms: int, tolerance_ms: int = 90_000) -> Optional[float]:
    """Return BTC close price at or near target_ms."""
    if target_ms in candles:
        return candles[target_ms]
    best_diff = tolerance_ms + 1
    best_price: Optional[float] = None
    for ts, price in candles.items():
        diff = abs(ts - target_ms)
        if diff < best_diff:
            best_diff = diff
            best_price = price
    return best_price if best_diff <= tolerance_ms else None


# ── Signal simulation ──────────────────────────────────────────────────

def simulate_btc_lag_window(
    window: MarketWindow,
    threshold: float,
) -> Optional[SignalRecord]:
    """
    Simulate btc_lag signal on one window using REAL Kalshi YES prices.

    For each 30s poll interval from T+1min to T+12min:
      - BTC move in prior 60s >= threshold (Gate 1)
      - Actual Kalshi YES price in 35-65c range (Gate 2 — price range guard)
      - Edge > 4% at actual price (Gate 3)

    Returns the first SignalRecord that fires, or None.
    """
    if not window.yes_candles or not window.btc_candles or window.settlement is None:
        return None

    lag_window_min = _LAG_WINDOW_SECONDS / 60.0
    t_min = 1.0  # Start 1 min in (need 60s of BTC history)

    while t_min <= (_WINDOW_MIN - _MIN_MINUTES_REMAINING):
        current_ms = window.window_open_ms + int(t_min * 60 * 1000)
        prev_ms = window.window_open_ms + int((t_min - lag_window_min) * 60 * 1000)

        current_btc = _price_at(window.btc_candles, current_ms)
        prev_btc = _price_at(window.btc_candles, prev_ms)

        if current_btc is None or prev_btc is None or prev_btc <= 0:
            t_min += _POLL_INTERVAL_MIN
            continue

        btc_move_pct = (current_btc - prev_btc) / prev_btc * 100

        # Gate 1: BTC move threshold
        if abs(btc_move_pct) < threshold:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Gate 2: Real Kalshi YES price in range
        yes_cents = _yes_price_at(window.yes_candles, current_ms)
        if yes_cents is None:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Price range guard (matches live btc_lag.py: _MIN_SIGNAL_PRICE_CENTS=35, _MAX=65)
        if yes_cents < _MIN_SIGNAL_PRICE_CENTS or yes_cents > _MAX_SIGNAL_PRICE_CENTS:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Gate 3: Edge at actual price
        implied_lag_cents = abs(btc_move_pct) * _LAG_SENSITIVITY
        side = "yes" if btc_move_pct > 0 else "no"

        if side == "yes":
            signal_price_cents = yes_cents
        else:
            # NO price ≈ 100 - yes_cents - spread; estimate 2c spread
            signal_price_cents = max(1, 100 - yes_cents - 2)

        fee = _lag_fee_pct(signal_price_cents)
        edge_pct = (implied_lag_cents / 100.0) - fee

        if edge_pct < _MIN_EDGE_PCT:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Signal fires
        minutes_remaining = _WINDOW_MIN - t_min
        no_cents_est = max(1, 100 - yes_cents - 2)

        return SignalRecord(
            ticker=window.ticker,
            window_open_ms=window.window_open_ms,
            eval_minute=t_min,
            btc_move_pct=btc_move_pct,
            yes_cents=yes_cents,
            no_cents=no_cents_est,
            minutes_remaining=minutes_remaining,
            edge_pct=edge_pct,
            side=side,
            settlement=window.settlement,
        )

    return None


# ── Threshold sweep analysis ───────────────────────────────────────────

def analyze_threshold(
    records: List[SignalRecord],
    threshold: float,
    all_windows_with_settlement: int,
) -> dict:
    """Compute metrics for one threshold level."""
    fired = [r for r in records if abs(r.btc_move_pct) >= threshold]

    if not fired:
        return {
            "threshold": threshold,
            "fired": 0,
            "correct": 0,
            "accuracy": 0.0,
            "yes_prices": [],
            "mean_yes": 0.0,
            "median_yes": 0.0,
            "p25_yes": 0.0,
            "p75_yes": 0.0,
            "mean_actual_edge": 0.0,
            "mean_50c_edge": 0.0,
            "coverage_pct": 0.0,
        }

    correct = sum(
        1 for r in fired
        if (r.side == "yes" and r.settlement == 1) or (r.side == "no" and r.settlement == 0)
    )
    accuracy = correct / len(fired)

    yes_prices = [r.yes_cents for r in fired]
    mean_yes = statistics.mean(yes_prices)
    median_yes = statistics.median(yes_prices)
    if len(yes_prices) >= 4:
        quants = statistics.quantiles(yes_prices, n=4)
        p25 = quants[0]
        p75 = quants[2]
    else:
        p25 = float(min(yes_prices))
        p75 = float(max(yes_prices))

    # Actual edge per signal at real prices, using observed accuracy as P(win)
    actual_edges = []
    for r in fired:
        if r.side == "yes":
            payout = (100 - r.yes_cents) / 100.0
            stake = r.yes_cents / 100.0
            fee = _lag_fee_pct(r.yes_cents)
        else:
            payout = (100 - r.no_cents) / 100.0
            stake = r.no_cents / 100.0
            fee = _lag_fee_pct(r.no_cents)
        # Expected edge = P(win)*net_payout - P(loss)*stake - fee
        edge = accuracy * payout - (1 - accuracy) * stake - fee
        actual_edges.append(edge)

    mean_actual_edge = statistics.mean(actual_edges) if actual_edges else 0.0

    # 50c-assumed edge (what backtest.py shows)
    fee_50c = _lag_fee_pct(50)
    payout_50c = 0.50
    stake_50c = 0.50
    mean_50c_edge = accuracy * payout_50c - (1 - accuracy) * stake_50c - fee_50c

    coverage_pct = len(fired) / max(1, all_windows_with_settlement) * 100

    return {
        "threshold": threshold,
        "fired": len(fired),
        "correct": correct,
        "accuracy": accuracy,
        "yes_prices": yes_prices,
        "mean_yes": mean_yes,
        "median_yes": median_yes,
        "p25_yes": p25,
        "p75_yes": p75,
        "mean_actual_edge": mean_actual_edge,
        "mean_50c_edge": mean_50c_edge,
        "coverage_pct": coverage_pct,
    }


# ── Report ─────────────────────────────────────────────────────────────

def build_key_finding(results: List[dict]) -> str:
    """Generate KEY FINDING section based on actual YES prices at 0.40% threshold."""
    r040 = next((r for r in results if abs(r["threshold"] - 0.40) < 0.001), None)
    if r040 is None or r040["fired"] == 0:
        return "  Insufficient signals at 0.40% threshold to draw conclusions."

    mean_yes = r040["mean_yes"]
    accuracy = r040["accuracy"]
    actual_edge = r040["mean_actual_edge"]
    assumed_edge = r040["mean_50c_edge"]
    delta_pp = (actual_edge - assumed_edge) * 100

    lines = []

    if mean_yes > 52:
        price_finding = (
            f"  At >=0.40% threshold, actual Kalshi YES price was {mean_yes:.1f}c avg "
            f"(p25={r040['p25_yes']:.0f}c, p75={r040['p75_yes']:.0f}c).\n"
            f"  HFTs had already priced in ~{mean_yes - 50:.1f}c of the BTC move before btc_lag fires.\n"
            f"  This REDUCES effective edge by ~{abs(delta_pp):.1f}pp vs the 50c backtest assumption."
        )
    elif mean_yes < 48:
        price_finding = (
            f"  At >=0.40% threshold, actual Kalshi YES price was {mean_yes:.1f}c avg "
            f"(p25={r040['p25_yes']:.0f}c, p75={r040['p75_yes']:.0f}c).\n"
            f"  Kalshi lagged: YES was BELOW 50c on positive BTC moves. Suggests opportunity.\n"
            f"  This INCREASES effective edge by ~{abs(delta_pp):.1f}pp vs the 50c assumption."
        )
    else:
        price_finding = (
            f"  At >=0.40% threshold, actual Kalshi YES price was {mean_yes:.1f}c avg "
            f"(p25={r040['p25_yes']:.0f}c, p75={r040['p75_yes']:.0f}c).\n"
            f"  Kalshi price was near-neutral at signal time. 50c assumption is largely valid.\n"
            f"  Edge delta: {delta_pp:+.1f}pp vs 50c assumption."
        )
    lines.append(price_finding)

    if accuracy >= 0.60:
        lines.append(
            f"\n  Directional accuracy at 0.40%: {accuracy:.1%} — strong momentum continuation."
        )
    elif accuracy >= 0.54:
        lines.append(
            f"\n  Directional accuracy at 0.40%: {accuracy:.1%} — modest edge above coin flip."
        )
    elif accuracy >= 0.50:
        lines.append(
            f"\n  Directional accuracy at 0.40%: {accuracy:.1%} — marginal edge."
        )
    else:
        lines.append(
            f"\n  Directional accuracy at 0.40%: {accuracy:.1%} — below coin flip on real data."
        )

    if actual_edge > 0.02:
        lines.append(
            f"\n  Mean actual edge at real prices: {actual_edge:.1%} — positive after fees."
        )
    elif actual_edge > 0:
        lines.append(
            f"\n  Mean actual edge at real prices: {actual_edge:.1%} — barely positive; tight margin."
        )
    else:
        lines.append(
            f"\n  Mean actual edge at real prices: {actual_edge:.1%} — NEGATIVE after fees."
        )

    return "\n".join(lines)


def format_report(
    total_markets: int,
    markets_with_candles: int,
    markets_with_settlement: int,
    all_records: List[SignalRecord],
    threshold_results: List[dict],
    days: int,
    date_range: Tuple[str, str],
    max_markets: int = _MAX_MARKETS,
) -> str:
    """Format the full report as a string."""
    width = 64
    sep = "=" * width

    lines = [
        "",
        sep,
        "  KALSHI REAL-PRICE BACKTEST — btc_lag_v1",
        f"  Source: Kalshi API ({_SERIES_TICKER}) + Binance.US 1-min klines",
        f"  Period: last {days} days | Date range: {date_range[0]} to {date_range[1]}",
        f"  Price range guard: {_MIN_SIGNAL_PRICE_CENTS}-{_MAX_SIGNAL_PRICE_CENTS}c | Min remaining: {_MIN_MINUTES_REMAINING}min",
        f"  lag_sensitivity={_LAG_SENSITIVITY:.0f}c/1% | min_edge={_MIN_EDGE_PCT:.0%} | 50c assumed in backtest.py",
        sep,
        "",
        f"  Settled markets pulled:              {total_markets}",
        f"  Markets with Kalshi candle data:     {markets_with_candles}",
        f"  Markets with full settlement data:   {markets_with_settlement}",
        "",
        "  THRESHOLD SWEEP:",
        "",
    ]

    for r in threshold_results:
        thr = r["threshold"]
        marker = "  <-- current live threshold" if abs(thr - 0.40) < 0.001 else ""
        lines.append(f"  BTC move threshold: >={thr:.2f}% (60s){marker}")

        if r["fired"] == 0:
            lines.append("    No signals fired at this threshold.")
            lines.append("")
            continue

        lines.extend([
            f"    Signals fired:                   {r['fired']}  ({r['coverage_pct']:.1f}% of windows)",
            f"    Directional accuracy:            {r['accuracy']:.1%}",
            f"    Actual Kalshi YES price — mean:  {r['mean_yes']:.1f}c | median: {r['median_yes']:.1f}c | p25: {r['p25_yes']:.0f}c | p75: {r['p75_yes']:.0f}c",
            f"    Mean actual edge (real prices):  {r['mean_actual_edge']:.1%}",
            f"    50c-assumed edge would show:     {r['mean_50c_edge']:.1%}  (delta: {(r['mean_actual_edge'] - r['mean_50c_edge'])*100:+.1f}pp)",
            "",
        ])

    key_finding = build_key_finding(threshold_results)
    lines.extend([
        "  KEY FINDING:",
        key_finding,
        "",
        sep,
    ])

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Backtest btc_lag with real Kalshi YES prices from the API"
    )
    parser.add_argument("--days", type=int, default=_DEFAULT_DAYS,
                        help=f"Days of settled markets to analyze (default: {_DEFAULT_DAYS})")
    parser.add_argument("--max-markets", type=int, default=_MAX_MARKETS,
                        help=f"Max markets to pull candlesticks for (default: {_MAX_MARKETS})")
    args = parser.parse_args()

    print()
    print("  Kalshi Real-Price Backtest — btc_lag_v1")
    print(f"  Fetching last {args.days} days of settled {_SERIES_TICKER} markets...")
    print("  Using REAL Kalshi YES prices (not the 50c assumption in backtest.py)")
    print()

    start_wall = time.time()

    async with aiohttp.ClientSession() as session:

        # ── Step 1: Fetch settled markets ─────────────────────────────
        print("  [1/4] Pulling settled markets from Kalshi API...", flush=True)
        markets = await fetch_settled_markets(session, days=args.days)
        print(f"        Found {len(markets)} finalized markets in last {args.days} days")

        # Sample evenly across the date range (not just the most recent N)
        # Kalshi API returns newest first; naive [:N] gives only the most recent N markets
        # which may be a calm period. Even sampling across 30 days gives better coverage.
        max_mkt = args.max_markets
        if len(markets) > max_mkt:
            import random
            random.seed(42)  # Reproducible
            markets = random.sample(markets, max_mkt)
            markets.sort(key=lambda m: m.window_open_ms)  # Sort by time after sampling
            print(f"        Sampled {max_mkt} markets evenly across date range (use --max-markets N for more)")

        if not markets:
            print()
            print("  ERROR: No settled markets found.")
            print("  Check connectivity: curl 'https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXBTC15M&status=settled&limit=5'")
            sys.exit(1)

        # Date range from markets
        all_open_ms = [m.window_open_ms for m in markets]
        earliest_dt = datetime.fromtimestamp(min(all_open_ms) / 1000, tz=timezone.utc)
        latest_dt = datetime.fromtimestamp(max(all_open_ms) / 1000, tz=timezone.utc)
        date_range = (earliest_dt.strftime("%Y-%m-%d"), latest_dt.strftime("%Y-%m-%d"))

        # ── Step 2: Fetch Kalshi candlesticks ─────────────────────────
        print(f"  [2/4] Fetching Kalshi 1-min candlesticks for {len(markets)} markets...", flush=True)
        markets_with_candles = 0
        for i, mkt in enumerate(markets):
            start_s = mkt.window_open_ms // 1000
            end_s = mkt.window_close_ms // 1000

            candles = await fetch_kalshi_candles(session, mkt.ticker, start_s, end_s)
            mkt.yes_candles = candles
            if candles:
                markets_with_candles += 1

            if (i + 1) % 20 == 0 or (i + 1) == len(markets):
                pct = (i + 1) / len(markets) * 100
                print(
                    f"\r        {pct:.0f}% ({i+1}/{len(markets)}) — {markets_with_candles} with candle data",
                    end="", flush=True
                )

            # Rate limit: stay at ~6.5 req/sec (well under 20/sec cap)
            await asyncio.sleep(_CANDLE_REQUEST_INTERVAL)

        print()
        print(f"        {markets_with_candles}/{len(markets)} markets have Kalshi candlestick data")

        # ── Step 3: Fetch BTC klines for all windows ──────────────────
        print("  [3/4] Fetching Binance BTC klines for all windows...", flush=True)
        btc_start_ms = min(m.window_open_ms for m in markets) - 180_000  # 3min buffer
        btc_end_ms = max(m.window_close_ms for m in markets) + 180_000
        try:
            btc_all = await fetch_btc_candles_range(session, btc_start_ms, btc_end_ms)
            print(f"        Fetched {len(btc_all):,} BTC 1-min candles")
        except Exception as e:
            print(f"  ERROR: Binance fetch failed: {e}")
            sys.exit(1)

        # Assign BTC data and compute settlement for each window
        markets_with_settlement = 0
        for mkt in markets:
            buf_ms = 180_000
            mkt.btc_candles = {
                ts: price for ts, price in btc_all.items()
                if (mkt.window_open_ms - buf_ms) <= ts <= (mkt.window_close_ms + buf_ms)
            }

            ref_price = _price_at(mkt.btc_candles, mkt.window_open_ms)
            final_price = _price_at(mkt.btc_candles, mkt.window_close_ms)
            if ref_price and final_price and ref_price > 0:
                mkt.settlement = 1 if final_price > ref_price else 0
                markets_with_settlement += 1

        print(f"        {markets_with_settlement}/{len(markets)} markets have settlement data")

        # ── Step 4: Simulate btc_lag signal ───────────────────────────
        print(f"  [4/4] Simulating btc_lag across {len(_THRESHOLDS)} thresholds...", flush=True)

        windows_with_settlement = [m for m in markets if m.settlement is not None]
        min_threshold = min(_THRESHOLDS)

        # Collect all signal opportunities at the lowest threshold
        # (higher thresholds are subsets — filter by |btc_move_pct| in analyze_threshold)
        all_records: List[SignalRecord] = []
        for mkt in windows_with_settlement:
            record = simulate_btc_lag_window(mkt, threshold=min_threshold)
            if record is not None:
                all_records.append(record)

        print(f"        Total signal opportunities (>={min_threshold:.2f}%): {len(all_records)}")

        # Analyze each threshold
        threshold_results = []
        for thr in _THRESHOLDS:
            result = analyze_threshold(all_records, thr, len(windows_with_settlement))
            threshold_results.append(result)

    # ── Build and print report ─────────────────────────────────────────
    report = format_report(
        total_markets=len(markets),
        markets_with_candles=markets_with_candles,
        markets_with_settlement=markets_with_settlement,
        all_records=all_records,
        threshold_results=threshold_results,
        days=args.days,
        date_range=date_range,
        max_markets=args.max_markets,
    )

    print(report)

    # ── Write results file ─────────────────────────────────────────────
    elapsed = time.time() - start_wall
    ts_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    md_content = f"""# Kalshi Real-Price Backtest — btc_lag_v1

Generated: {ts_str}
Elapsed: {elapsed:.1f}s

```
{report}
```

## Methodology Notes

- Settlement determined from Binance BTC direction (same proxy as backtest.py)
- YES prices from Kalshi 1-min candlestick API (actual bid/ask mid prices)
- Price range guard: {_MIN_SIGNAL_PRICE_CENTS}-{_MAX_SIGNAL_PRICE_CENTS}c (matches live btc_lag.py constants)
- Edge formula: implied_lag_pct - kalshi_fee_pct (0.07 * p * (1-p))
- lag_sensitivity = {_LAG_SENSITIVITY} cents per 1% BTC move (from config.yaml)
- min_edge_pct = {_MIN_EDGE_PCT:.0%} (current live btc_lag threshold)
- Each window simulated at 30s poll intervals (matches live bot behavior)
- First signal per window taken (matches live behavior — one bet per window)
"""
    _RESULTS_PATH.write_text(md_content)
    print(f"\n  Results written to: {_RESULTS_PATH}")
    print(f"  Total runtime: {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())
