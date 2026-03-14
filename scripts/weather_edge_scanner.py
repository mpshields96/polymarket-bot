"""
Weather Edge Scanner — GEFS ensemble vs Kalshi KXHIGH* price comparison.

JOB:    Fetch GEFS 31-member ensemble forecasts for all 5 cities,
        compare to live Kalshi KXHIGH* market prices,
        and flag discrepancies > min_edge_pct.

USAGE:
    source venv/bin/activate
    python scripts/weather_edge_scanner.py
    python scripts/weather_edge_scanner.py --min-edge 0.10   # 10% threshold
    python scripts/weather_edge_scanner.py --city nyc         # NYC only

WHY THIS WORKS:
    Kalshi weather participants price markets based on historical seasonal averages.
    GEFS 31-member ensemble reflects current forecast far better.
    On unusual weather days (warm fronts, cold snaps), edges of 20-80% emerge.
    Markets open daily. Settlement = same day.

CITIES COVERED:
    NYC (KXHIGHNY) — NY daily high temp
    LAX (KXHIGHLAX) — LA daily high temp
    CHI (KXHIGHCHI) — Chicago daily high temp
    DEN (KXHIGHDEN) — Denver daily high temp
    MIA (KXHIGHMIA) — Miami daily high temp

API COST: Zero — GEFS via Open-Meteo (free), Kalshi API (no quota on reads)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Bootstrap project path ────────────────────────────────────────────────
_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

for line in (_PROJ / ".env").read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from src.data.weather import GEFSEnsembleFeed
from src.platforms.kalshi import load_from_env as kalshi_load, Market

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("weather_edge_scanner")

# ── City definitions ──────────────────────────────────────────────────────
CITIES = {
    "nyc": {"latitude": 40.71, "longitude": -74.01, "timezone": "America/New_York",
            "city_name": "NYC", "series": "KXHIGHNY"},
    "lax": {"latitude": 34.05, "longitude": -118.24, "timezone": "America/Los_Angeles",
            "city_name": "LAX", "series": "KXHIGHLAX"},
    "chi": {"latitude": 41.88, "longitude": -87.63, "timezone": "America/Chicago",
            "city_name": "CHI", "series": "KXHIGHCHI"},
    "den": {"latitude": 39.74, "longitude": -104.98, "timezone": "America/Denver",
            "city_name": "DEN", "series": "KXHIGHDEN"},
    "mia": {"latitude": 25.76, "longitude": -80.19, "timezone": "America/New_York",
            "city_name": "MIA", "series": "KXHIGHMIA"},
}

# ── Bracket parsing ───────────────────────────────────────────────────────

def parse_weather_bracket(title: str) -> Optional[tuple[float, float, str]]:
    """
    Parse temperature bracket from Kalshi weather market title.

    Returns (lower_f, upper_f, direction) where direction is 'above', 'below', or 'between'.
    lower_f or upper_f may be float('inf') / float('-inf').
    Returns None on parse failure.

    Handles formats:
      "be >79°"   → (79, inf,  'above')
      "be <72°"   → (-inf, 72, 'below')
      "be 78-79°" → (78, 79,   'between')
      "be 68° or higher" → (68, inf, 'above')
      "be 63° or lower"  → (-inf, 63, 'below')
    """
    # ">79°" format (strict above threshold)
    m = re.search(r">\s*(\d+(?:\.\d+)?)\s*[°F°]", title)
    if m:
        return (float(m.group(1)), float("inf"), "above")

    # "<72°" format (strict below threshold)
    m = re.search(r"<\s*(\d+(?:\.\d+)?)\s*[°F°]", title)
    if m:
        return (float("-inf"), float(m.group(1)), "below")

    # "78-79°" or "78° to 79°" range format
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:[°F°]?\s*(?:-|to)\s*)(\d+(?:\.\d+)?)\s*[°F°]", title)
    if m:
        return (float(m.group(1)), float(m.group(2)), "between")

    # "X° or higher"
    m = re.search(r"(\d+(?:\.\d+)?)\s*[°F°]?\s*or\s+higher", title, re.IGNORECASE)
    if m:
        return (float(m.group(1)), float("inf"), "above")

    # "X° or lower"
    m = re.search(r"(\d+(?:\.\d+)?)\s*[°F°]?\s*or\s+lower", title, re.IGNORECASE)
    if m:
        return (float("-inf"), float(m.group(1)), "below")

    return None


def gefs_prob_yes(temps: list[float], lower: float, upper: float, direction: str) -> float:
    """
    Compute GEFS probability that the YES condition is met.

    For 'above' markets: YES = high > lower. Uses strict >.
    For 'below' markets: YES = high < upper. Uses strict <.
    For 'between' markets: YES = lower <= high <= upper.
    """
    if not temps:
        return 0.5

    if direction == "above":
        count = sum(1 for t in temps if t > lower)
    elif direction == "below":
        count = sum(1 for t in temps if t < upper)
    else:  # between
        count = sum(1 for t in temps if lower <= t <= upper)

    n = len(temps)
    raw = count / n
    # Clamp to avoid 0% or 100% (Laplace smoothing)
    return max(1.0 / (n + 1), min(n / (n + 1), raw))


def kalshi_taker_fee(price_cents: int) -> float:
    """Kalshi taker fee as fraction: 7% * P * (1-P)."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


# ── Main scan ─────────────────────────────────────────────────────────────

async def scan_city(
    client,
    city_key: str,
    city_cfg: dict,
    min_edge: float,
    now_ts: float,
) -> list[dict]:
    """Scan one city's weather markets. Returns list of opportunity dicts."""
    series = city_cfg["series"]
    city_name = city_cfg["city_name"]

    # Fetch GEFS forecast
    gefs_cfg = {k: v for k, v in city_cfg.items() if k != "series"}
    feed = GEFSEnsembleFeed(**gefs_cfg)
    try:
        feed.refresh()
    except Exception as e:
        logger.warning("%s GEFS fetch failed: %s", city_name, e)
        return []

    temps = feed.member_temps_f()
    if not temps:
        logger.warning("%s: no GEFS data", city_name)
        return []

    forecast_date = feed.forecast_date()

    # Fetch open Kalshi markets
    try:
        markets = await client.get_markets(series_ticker=series, status="open", limit=30)
    except Exception as e:
        logger.warning("%s market fetch failed: %s", city_name, e)
        return []

    opportunities = []
    for m in markets:
        # Parse bracket
        bracket = parse_weather_bracket(m.title)
        if bracket is None:
            logger.debug("%s: could not parse title %r", city_name, m.title)
            continue

        lower_f, upper_f, direction = bracket

        # Skip markets not for the GEFS forecast date (date mismatch guard)
        # Extract date from ticker: KXHIGHNY-26MAR15-T54 → "26MAR15"
        ticker_parts = m.ticker.split("-")
        if len(ticker_parts) >= 2:
            market_date_str = ticker_parts[1]  # e.g. "26MAR15"
            if forecast_date and forecast_date[-5:].replace("-", "") not in market_date_str.upper():
                # Simple check: if the forecast date month+day doesn't match ticker date, skip
                # forecast_date like "2026-03-15", last 5 = "03-15", strip "-" = "0315"
                # market_date_str like "26MAR15"
                # This is a rough check — skip only if obviously mismatched
                import datetime
                try:
                    fd = datetime.datetime.fromisoformat(forecast_date)
                    fd_key = f"{fd.month:02d}{fd.day:02d}"  # "0315"
                    # market_date_str "26MAR15" → month=MAR=3, day=15 → key "0315"
                    months = {"JAN":"01","FEB":"02","MAR":"03","APR":"04","MAY":"05","JUN":"06",
                              "JUL":"07","AUG":"08","SEP":"09","OCT":"10","NOV":"11","DEC":"12"}
                    md_month = market_date_str[2:5].upper()
                    md_day = market_date_str[5:7]
                    mk_key = months.get(md_month, "00") + md_day
                    if mk_key != fd_key:
                        logger.debug("Skipping %s — market date %s != GEFS date %s",
                                     m.ticker, mk_key, fd_key)
                        continue
                except Exception:
                    pass  # If date check fails, proceed anyway

        # Skip markets with no liquidity
        yes_p = m.yes_price or 0
        no_p = m.no_price or 0
        if yes_p < 2 or no_p < 2:
            continue  # Too one-sided, no margin

        # Skip markets closing in < 15 min (too late to trade)
        try:
            close_ts = datetime.fromisoformat(m.close_time.rstrip("Z")).replace(
                tzinfo=timezone.utc
            ).timestamp()
            mins_to_close = (close_ts - now_ts) / 60
            if mins_to_close < 15:
                continue
        except Exception:
            pass

        # Compute GEFS probability and edge
        gefs_p = gefs_prob_yes(temps, lower_f, upper_f, direction)
        fee_yes = kalshi_taker_fee(yes_p)
        fee_no = kalshi_taker_fee(no_p)

        edge_yes = gefs_p - (yes_p / 100.0) - fee_yes
        edge_no = (1.0 - gefs_p) - (no_p / 100.0) - fee_no

        best_edge = max(edge_yes, edge_no)
        if best_edge < min_edge:
            continue

        if edge_yes >= edge_no:
            side = "YES"
            price = yes_p
            win_prob = gefs_p
        else:
            side = "NO"
            price = no_p
            win_prob = 1.0 - gefs_p

        win_cents = 100 - price
        ev_usd_per_5 = win_prob * win_cents * 5 / price - (1 - win_prob) * 5

        opportunities.append({
            "city": city_name,
            "ticker": m.ticker,
            "title": m.title,
            "side": side,
            "price_cents": price,
            "gefs_pct": round(gefs_p * 100, 1),
            "kalshi_yes_pct": yes_p,
            "edge_pct": round(best_edge * 100, 1),
            "ev_usd_per_5": round(ev_usd_per_5, 2),
            "volume": m.volume,
            "gefs_mean_f": round(sum(temps) / len(temps), 1),
            "gefs_range_f": [round(min(temps), 1), round(max(temps), 1)],
            "bracket": f"{lower_f}–{upper_f}F ({direction})",
        })

    return opportunities


async def run_scan(args):
    client = kalshi_load()
    now_ts = time.time()

    if args.city:
        cities_to_scan = {args.city: CITIES[args.city]}
    else:
        cities_to_scan = CITIES

    async with client:
        all_ops = []
        for city_key, city_cfg in cities_to_scan.items():
            ops = await scan_city(client, city_key, city_cfg, args.min_edge, now_ts)
            all_ops.extend(ops)

    all_ops.sort(key=lambda x: abs(x["ev_usd_per_5"]), reverse=True)
    return all_ops


def main():
    parser = argparse.ArgumentParser(description="GEFS weather edge scanner for Kalshi KXHIGH* markets")
    parser.add_argument("--min-edge", type=float, default=0.10,
                        help="Minimum edge fraction to report (default 0.10 = 10%%)")
    parser.add_argument("--city", choices=list(CITIES.keys()), default=None,
                        help="Only scan one city (default: all 5)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    ops = asyncio.run(run_scan(args))

    if args.json:
        print(json.dumps(ops, indent=2))
        return

    print(f"Weather Edge Scanner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Min edge: {args.min_edge*100:.0f}% | Found: {len(ops)} opportunities")
    print()

    if not ops:
        print("No opportunities above threshold.")
        print()
        print("GEFS forecasts:")
        for city_key, city_cfg in CITIES.items():
            if args.city and city_key != args.city:
                continue
            gefs_cfg = {k: v for k, v in city_cfg.items() if k != "series"}
            feed = GEFSEnsembleFeed(**gefs_cfg)
            feed.refresh()
            temps = feed.member_temps_f()
            if temps:
                print(f"  {city_cfg['city_name']}: mean={sum(temps)/len(temps):.1f}F "
                      f"range=[{min(temps):.1f},{max(temps):.1f}F] date={feed.forecast_date()}")
        return

    for op in ops:
        edge_flag = "*** STRONG EDGE ***" if abs(op["edge_pct"]) > 30 else ""
        print(f"{op['city']} | {op['side']}@{op['price_cents']}c {edge_flag}")
        print(f"  {op['ticker']}")
        print(f"  Title: {op['title']}")
        print(f"  GEFS: {op['gefs_pct']}% (mean={op['gefs_mean_f']}F, range={op['gefs_range_f']}) | "
              f"Kalshi YES: {op['kalshi_yes_pct']}c")
        print(f"  Edge: {op['edge_pct']:+.1f}% | EV per 5 USD bet: {op['ev_usd_per_5']:+.2f} USD | "
              f"vol={op['volume']:,}")
        print()

    if ops:
        print(f"Note: GEFS may overestimate by 3-5F on extreme warm days.")
        print(f"Best practice: trade only when GEFS std_dev < 2F and edge > 20%.")

    # Save to file
    out_path = _PROJ / "data" / "weather_edge_scan_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "results": ops}, f, indent=2)
    print(f"Results saved to {out_path}")


if __name__ == "__main__":
    main()
