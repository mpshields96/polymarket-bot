"""
scripts/check_kxbtcd_edge.py — KXBTCD threshold market feasibility check.

Purpose:
  1. Fetch all open KXBTCD markets from Kalshi (authenticated).
  2. Fetch current BTC spot from Binance.US.
  3. Fetch current DVOL from Deribit (fallback: use hardcoded sigma if geo-blocked).
  4. For each market, compute N(d2) fair probability.
  5. Compare to Kalshi YES price — log markets with |edge| > 7%.

RESEARCH/DIAGNOSTIC ONLY. No trading, no order placement, no bot interaction.
Run: source venv/bin/activate && python scripts/check_kxbtcd_edge.py
"""

from __future__ import annotations

import asyncio
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiohttp
import requests

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.strategies.crypto_daily_threshold import fair_prob_above_strike, edge_pct

KALSHI_BASE = "https://trading-api.kalshi.com/trade-api/v2"
DERIBIT_INDEX_URL = "https://www.deribit.com/api/v2/public/get_index_price"
BINANCE_US_SPOT_URL = "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT"

MIN_EDGE_PCT = 0.07   # 7% min edge threshold (from research file)
TIMEOUT_SEC = 10


def fetch_btc_spot() -> Optional[float]:
    """Fetch BTC spot from Binance.US."""
    try:
        r = requests.get(BINANCE_US_SPOT_URL, timeout=TIMEOUT_SEC)
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception as e:
        print(f"  [warn] BTC spot fetch failed: {e}")
        return None


DERIBIT_DVOL_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"


def fetch_dvol() -> Optional[float]:
    """Fetch Deribit BTC DVOL.

    Uses get_volatility_index_data (1-hour resolution), returns last close.
    NOTE: get_index_price with btc_usdv returns 400 — wrong endpoint per research file.
    """
    try:
        now_ms = int(time.time() * 1000)
        two_hours_ago_ms = now_ms - 7_200_000
        r = requests.get(
            DERIBIT_DVOL_URL,
            params={
                "currency": "BTC",
                "start_timestamp": two_hours_ago_ms,
                "end_timestamp": now_ms,
                "resolution": "3600",
            },
            timeout=TIMEOUT_SEC,
        )
        r.raise_for_status()
        data = r.json()
        rows = data.get("result", {}).get("data", [])
        if not rows:
            return None
        return float(rows[-1][4])  # last candle close
    except Exception as e:
        print(f"  [warn] Deribit DVOL fetch failed: {e}")
        return None


def parse_strike_from_ticker(ticker: str) -> Optional[float]:
    """Extract strike price from Kalshi ticker.

    Example: KXBTCD-26MAR1317-T70499.99 → 70499.99
             KXBTCD-26MAR2117-T84000.00 → 84000.00

    Format: SERIES-DATE-T{strike}
    """
    try:
        parts = ticker.split("-T")
        if len(parts) == 2:
            return float(parts[1])
    except (ValueError, IndexError):
        pass
    return None


def parse_settlement_hours(close_time: str) -> Optional[float]:
    """Compute hours_remaining from market close_time (ISO 8601 string).

    Returns None if parsing fails.
    """
    try:
        # close_time is typically "2026-03-12T21:00:00Z" or similar
        dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = dt - now
        hours = delta.total_seconds() / 3600.0
        return max(0.0, hours)
    except Exception:
        return None


def fetch_kxbtcd_markets(auth) -> list:
    """Fetch open KXBTCD markets from Kalshi API using synchronous requests.

    Uses requests (not aiohttp) to avoid competing with the running bot's
    aiohttp connection pool on the same API endpoint.
    """
    path = "/trade-api/v2/markets"
    url = f"{KALSHI_BASE}/markets"
    params = {
        "series_ticker": "KXBTCD",
        "status": "open",
        "limit": 200,
    }
    headers = auth.headers("GET", path)

    resp = requests.get(url, headers=headers, params=params, timeout=TIMEOUT_SEC)
    if resp.status_code != 200:
        raise RuntimeError(f"Kalshi markets fetch failed: HTTP {resp.status_code} — {resp.text[:200]}")
    return resp.json().get("markets", [])


def _synthetic_kxbtcd_markets(spot: float) -> list:
    """Generate representative KXBTCD-style market dicts for synthetic edge analysis.

    Uses typical Kalshi strike distribution (multiples of 500/1000 USD around ATM)
    and market YES prices that follow a rough lognormal pricing convention.
    Hours_remaining = 5.0 (represents ~5pm EDT same-day slot).

    This is for diagnostic/demonstration purposes only. Real market YES prices
    will differ due to order flow, spreads, and maker/taker dynamics.
    """
    import math
    from datetime import datetime, timedelta, timezone

    # Settlement in 5 hours from now (approximate 5pm EDT slot)
    settlement = datetime.now(timezone.utc) + timedelta(hours=5)
    close_time = settlement.isoformat().replace("+00:00", "Z")

    # Strikes: ±5% around ATM in ~1% increments
    strikes = []
    base = round(spot / 1000) * 1000  # round to nearest 1000
    for offset_pct in [-5, -4, -3, -2, -1, 0, 1, 2, 3, 4, 5]:
        s = base * (1 + offset_pct / 100)
        s = round(s / 500) * 500  # round to 500 USD increments
        strikes.append(s)
    strikes = sorted(set(strikes))

    # For each strike, generate a synthetic YES price (lognormal with NO drift adjustment)
    # Use slightly mispriced quotes to test edge detection
    from src.strategies.crypto_daily_threshold import fair_prob_above_strike
    markets = []
    for strike in strikes:
        fair_p = fair_prob_above_strike(spot=spot, strike=strike, hours_remaining=5.0, dvol=55.0)
        # Market maker adds ~2c spread, slight bias toward 50c (over-pricing OTM)
        mispriced_cents = int(fair_p * 100 + 2 * (0.5 - fair_p))  # nudge toward 50
        mispriced_cents = max(2, min(98, mispriced_cents))

        ticker = f"KXBTCD-26MAR2117-T{strike:.2f}"
        markets.append({
            "ticker": ticker,
            "yes_ask": mispriced_cents,
            "close_time": close_time,
            "volume": 50000 + int(abs(fair_p - 0.5) * -100000),  # ATM has most volume
            "_synthetic": True,
        })
    return markets


def main() -> None:
    print("=" * 70)
    print("KXBTCD Threshold Edge Feasibility Check")
    print(f"Run time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # 1. Load Kalshi auth
    print("\n[1] Loading Kalshi auth...")
    try:
        from src.auth.kalshi_auth import load_from_env
        auth = load_from_env()
        print("    Auth loaded OK")
    except Exception as e:
        print(f"    FAILED: {e}")
        return

    # 2. Fetch BTC spot
    print("\n[2] Fetching BTC spot (Binance.US)...")
    spot = fetch_btc_spot()
    if spot:
        print(f"    BTC spot: {spot:,.0f} USD")
    else:
        print("    FAILED — cannot compute fair values without spot")
        return

    # 3. Fetch Deribit DVOL
    print("\n[3] Fetching Deribit DVOL...")
    dvol = fetch_dvol()
    if dvol:
        print(f"    DVOL: {dvol:.1f} (annualized implied vol)")
        daily_sigma = dvol / math.sqrt(365)
        print(f"    Daily 1-sigma: {daily_sigma:.2f}%")
    else:
        # Fallback: use historical average DVOL for BTC (~55-65%)
        dvol = 60.0
        print(f"    Deribit unavailable — using fallback DVOL = {dvol:.1f}")

    # 4. Fetch KXBTCD markets
    print("\n[4] Fetching open KXBTCD markets from Kalshi...")
    markets = []
    try:
        markets = fetch_kxbtcd_markets(auth)
        print(f"    Found {len(markets)} open KXBTCD markets")
    except Exception as e:
        print(f"    FAILED: {e}")
        print(f"    NOTE: This script cannot run while the trading bot holds an active")
        print(f"    connection to Kalshi (SSL session conflict). Stop the bot first, then retry.")
        print(f"    Falling back to SYNTHETIC mode with representative strikes.")
        markets = _synthetic_kxbtcd_markets(spot)

    if not markets:
        print("    No open KXBTCD markets found.")
        return

    if not markets:
        print("    No open KXBTCD markets found.")
        return

    # 5. Analyze each market
    print(f"\n[5] Edge analysis (threshold: {MIN_EDGE_PCT * 100:.0f}%)")
    print("-" * 70)

    high_edge_count = 0
    analyzed = 0

    is_synthetic = any(m.get("_synthetic") for m in markets)
    if is_synthetic:
        print("  (SYNTHETIC MODE — showing all markets for model validation)")
        print()

    for mkt in markets:
        ticker = mkt.get("ticker", "")
        yes_price = mkt.get("yes_ask", mkt.get("yes_bid", None))  # use ask for fair comparison
        if yes_price is None:
            yes_price = mkt.get("last_price", None)
        no_price = mkt.get("no_ask", None)
        close_time = mkt.get("close_time", "")
        volume = mkt.get("volume", 0)

        # Parse strike
        strike = parse_strike_from_ticker(ticker)
        if strike is None:
            continue

        # Parse hours remaining
        hours = parse_settlement_hours(close_time)
        if hours is None or hours <= 0:
            continue

        # Only analyze markets settling within 7 days (168 hours)
        if hours > 168:
            continue

        if yes_price is None:
            continue

        yes_price_cents = int(yes_price) if yes_price >= 1 else int(yes_price * 100)

        # Compute fair probability
        p_fair = fair_prob_above_strike(
            spot=spot,
            strike=strike,
            hours_remaining=hours,
            dvol=dvol,
        )

        e = edge_pct(fair_prob=p_fair, market_yes_price_cents=yes_price_cents)

        analyzed += 1

        if is_synthetic:
            # In synthetic mode show all markets to validate model
            direction = "BUY YES" if e > 0 else "BUY NO "
            flag = " ***" if abs(e) >= MIN_EDGE_PCT else "    "
            print(f"  {flag} {ticker}")
            print(f"       Strike={strike:,.0f} | Hours={hours:.1f} | Market={yes_price_cents}c | Fair={p_fair*100:.1f}c | Edge={e*100:+.1f}%")
            if abs(e) >= MIN_EDGE_PCT:
                high_edge_count += 1
                print(f"       Action: {direction}")
            print()
        elif abs(e) >= MIN_EDGE_PCT:
            high_edge_count += 1
            direction = "BUY YES" if e > 0 else "BUY NO "
            print(f"  *** HIGH EDGE: {ticker}")
            print(f"      Strike={strike:,.0f} | Spot={spot:,.0f} | Hours={hours:.1f}")
            print(f"      Market YES={yes_price_cents}c | Fair={p_fair*100:.1f}c | Edge={e*100:+.1f}%")
            print(f"      Action: {direction} | Volume={volume:,}")
            print()

    # 6. Summary
    print("-" * 70)
    print(f"\n[6] Summary:")
    print(f"    Markets analyzed: {analyzed}")
    print(f"    High-edge markets (>={MIN_EDGE_PCT*100:.0f}%): {high_edge_count}")
    if high_edge_count == 0:
        print(f"    No high-edge opportunities found at current BTC={spot:,.0f}, DVOL={dvol:.1f}")
        print(f"    This is expected when BTC is near ATM on all strikes.")
    else:
        print(f"    Found {high_edge_count} potential trading opportunities.")
        print(f"    NOTE: These are model estimates only. Do not trade without:")
        print(f"    (1) expansion gate clearing, (2) live path built, (3) Matthew approval.")

    print("\nDone.")


if __name__ == "__main__":
    main()
