#!/usr/bin/env python3
"""
Full Kalshi market audit — pull EVERY event and market, analyze:
- Category breakdown (what exists)
- Volume by category
- Open market count by category
- Spread analysis (wide spreads = potential inefficiency)
- Price clustering (how many near 50c = uncertain = opportunity)

Usage: source venv/bin/activate && python scripts/audit_all_kalshi_markets.py
"""

import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.platforms.kalshi import KalshiClient, load_from_env as kalshi_load_from_env


async def fetch_all_events(client: KalshiClient) -> list:
    """Fetch ALL events with pagination."""
    all_events = []
    cursor = None
    page = 0
    while True:
        page += 1
        params = {"limit": 200}  # events endpoint may not support status filter
        if cursor:
            params["cursor"] = cursor
        try:
            data = await client._get("/events", params=params)
        except Exception as e:
            print(f"  Events fetch error on page {page}: {e}")
            break
        events = data.get("events", [])
        all_events.extend(events)
        cursor = data.get("cursor", "")
        print(f"  Events page {page}: {len(events)} events (total: {len(all_events)})")
        if not events or not cursor:
            break
        if page >= 50:  # safety limit
            print("  Hit 50-page safety limit for events")
            break
    return all_events


async def fetch_all_series(client: KalshiClient) -> list:
    """Fetch ALL series."""
    all_series = []
    cursor = None
    page = 0
    while True:
        page += 1
        params = {"limit": 1000}
        if cursor:
            params["cursor"] = cursor
        data = await client._get("/series", params=params)
        series = data.get("series", [])
        all_series.extend(series)
        cursor = data.get("cursor", "")
        print(f"  Series page {page}: {len(series)} series (total: {len(all_series)})")
        if not series or not cursor:
            break
    return all_series


async def fetch_all_markets(client: KalshiClient) -> list:
    """Fetch ALL open markets with pagination."""
    all_markets = []
    cursor = None
    page = 0
    while True:
        page += 1
        params = {"limit": 1000, "status": "open"}
        if cursor:
            params["cursor"] = cursor
        data = await client._get("/markets", params=params)
        markets = data.get("markets", [])
        all_markets.extend(markets)
        cursor = data.get("cursor", "")
        print(f"  Markets page {page}: {len(markets)} markets (total: {len(all_markets)})")
        if not markets or not cursor:
            break
    return all_markets


async def fetch_categories(client: KalshiClient) -> dict:
    """Fetch series categories/tags."""
    try:
        data = await client._get("/search/tags/series-categories")
        return data
    except Exception as e:
        print(f"  Categories endpoint failed: {e}")
        return {}


def extract_volume(market: dict) -> int:
    """Extract volume from market dict, handling both old and new API formats."""
    # Try volume_fp (new string format) first, then volume (old int format)
    vol_fp = market.get("volume_fp")
    if vol_fp:
        try:
            return int(float(vol_fp))
        except (ValueError, TypeError):
            pass
    vol = market.get("volume")
    if vol is not None:
        try:
            return int(vol)
        except (ValueError, TypeError):
            pass
    # Try volume_24h or similar
    vol24 = market.get("volume_24h")
    if vol24 is not None:
        try:
            return int(float(vol24)) if isinstance(vol24, str) else int(vol24)
        except (ValueError, TypeError):
            pass
    return 0


def extract_yes_price(market: dict) -> int:
    """Extract YES price in cents."""
    # Try yes_dollars (new format) first
    yes_d = market.get("last_price_dollars") or market.get("yes_price_dollars")
    if yes_d:
        try:
            return round(float(yes_d) * 100)
        except (ValueError, TypeError):
            pass
    # Legacy int cents
    yp = market.get("last_price") or market.get("yes_price")
    if yp is not None:
        try:
            return int(yp)
        except (ValueError, TypeError):
            pass
    return 50  # default


def analyze_spread(market: dict) -> float:
    """Estimate spread from bid/ask if available."""
    yes_bid = market.get("yes_bid_dollars") or market.get("yes_bid")
    yes_ask = market.get("yes_ask_dollars") or market.get("yes_ask")
    if yes_bid and yes_ask:
        try:
            bid = float(yes_bid) * 100 if "dollars" in str(type(yes_bid)) or "." in str(yes_bid) else float(yes_bid)
            ask = float(yes_ask) * 100 if "dollars" in str(type(yes_ask)) or "." in str(yes_ask) else float(yes_ask)
            return ask - bid
        except (ValueError, TypeError):
            pass
    return -1  # unknown


async def main():
    print("=" * 70)
    print("FULL KALSHI MARKET AUDIT")
    print(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    client = kalshi_load_from_env()
    await client.start()

    try:
        # 1. Fetch categories
        print("\n--- Fetching categories ---")
        categories = await fetch_categories(client)
        if categories:
            print(f"  Raw categories response keys: {list(categories.keys())}")
            # Save raw for inspection
            with open("data/kalshi_categories_raw.json", "w") as f:
                json.dump(categories, f, indent=2, default=str)
            print("  Saved to data/kalshi_categories_raw.json")

        # 2. Fetch all series
        print("\n--- Fetching all series ---")
        all_series = await fetch_all_series(client)
        print(f"  Total series: {len(all_series)}")

        # Build series lookup
        series_lookup = {}
        for s in all_series:
            ticker = s.get("ticker", "")
            series_lookup[ticker] = {
                "title": s.get("title", ""),
                "category": s.get("category", "unknown"),
                "tags": s.get("tags", []),
                "frequency": s.get("frequency", ""),
                "settlement_sources": s.get("settlement_sources", []),
            }

        # 3. Fetch all open events
        print("\n--- Fetching all open events ---")
        all_events = await fetch_all_events(client)
        print(f"  Total open events: {len(all_events)}")

        # 4. Fetch all open markets
        print("\n--- Fetching all open markets ---")
        all_markets = await fetch_all_markets(client)
        print(f"  Total open markets: {len(all_markets)}")

        # Save raw market data for deep analysis
        with open("data/kalshi_all_markets_raw.json", "w") as f:
            json.dump(all_markets, f, indent=2, default=str)
        print("  Saved raw market data to data/kalshi_all_markets_raw.json")

        # Save raw event data
        with open("data/kalshi_all_events_raw.json", "w") as f:
            json.dump(all_events, f, indent=2, default=str)
        print("  Saved raw event data to data/kalshi_all_events_raw.json")

        # Save raw series data
        with open("data/kalshi_all_series_raw.json", "w") as f:
            json.dump(all_series, f, indent=2, default=str)
        print("  Saved raw series data to data/kalshi_all_series_raw.json")

        # ── ANALYSIS ─────────────────────────────────────────────────

        print("\n" + "=" * 70)
        print("ANALYSIS")
        print("=" * 70)

        # Group by series ticker prefix (e.g., KXBTC15M -> crypto, HIGHNY -> weather)
        series_stats = defaultdict(lambda: {
            "count": 0,
            "total_volume": 0,
            "prices": [],
            "spreads": [],
            "titles": set(),
            "event_tickers": set(),
        })

        for m in all_markets:
            series_ticker = m.get("series_ticker", "") or "UNKNOWN"
            event_ticker = m.get("event_ticker", "") or ""
            vol = extract_volume(m)
            price = extract_yes_price(m)
            spread = analyze_spread(m)
            title = m.get("title", "") or m.get("subtitle", "") or ""

            series_stats[series_ticker]["count"] += 1
            series_stats[series_ticker]["total_volume"] += vol
            series_stats[series_ticker]["prices"].append(price)
            if spread >= 0:
                series_stats[series_ticker]["spreads"].append(spread)
            series_stats[series_ticker]["titles"].add(title[:80])
            series_stats[series_ticker]["event_tickers"].add(event_ticker)

        # Also try to extract category from events
        event_categories = {}
        for e in all_events:
            eticker = e.get("event_ticker", "")
            cat = e.get("category", "") or e.get("series_ticker", "")
            title = e.get("title", "")
            event_categories[eticker] = {"category": cat, "title": title}

        # Sort by volume descending
        sorted_series = sorted(
            series_stats.items(),
            key=lambda x: x[1]["total_volume"],
            reverse=True,
        )

        print(f"\n{'SERIES':<20} {'MKTS':>5} {'VOLUME':>12} {'AVG_PRICE':>10} {'NEAR_50c':>8} {'CATEGORY':<30} SAMPLE_TITLE")
        print("-" * 130)

        report_lines = []
        for series, stats in sorted_series:
            count = stats["count"]
            vol = stats["total_volume"]
            prices = stats["prices"]
            avg_price = sum(prices) / len(prices) if prices else 0
            near_50 = sum(1 for p in prices if 35 <= p <= 65)  # in our sweet spot
            near_50_pct = round(100 * near_50 / len(prices)) if prices else 0

            # Look up category from series_lookup
            cat = series_lookup.get(series, {}).get("category", "")
            if not cat:
                # Try from first event
                for et in stats["event_tickers"]:
                    if et in event_categories:
                        cat = event_categories[et].get("category", "")
                        break

            sample_title = list(stats["titles"])[0][:50] if stats["titles"] else ""

            line = f"{series:<20} {count:>5} {vol:>12,} {avg_price:>9.1f}c {near_50:>4}({near_50_pct:>2}%) {cat:<30} {sample_title}"
            print(line)
            report_lines.append({
                "series": series,
                "market_count": count,
                "total_volume": vol,
                "avg_price_cents": round(avg_price, 1),
                "near_50c_count": near_50,
                "near_50c_pct": near_50_pct,
                "category": cat,
                "sample_title": sample_title,
                "avg_spread": round(sum(stats["spreads"]) / len(stats["spreads"]), 1) if stats["spreads"] else -1,
            })

        # Category rollup
        print(f"\n\n{'='*70}")
        print("CATEGORY ROLLUP")
        print(f"{'='*70}")
        cat_stats = defaultdict(lambda: {"series_count": 0, "market_count": 0, "total_volume": 0, "near_50c": 0, "total_mkts": 0})
        for r in report_lines:
            cat = r["category"] or "uncategorized"
            cat_stats[cat]["series_count"] += 1
            cat_stats[cat]["market_count"] += r["market_count"]
            cat_stats[cat]["total_volume"] += r["total_volume"]
            cat_stats[cat]["near_50c"] += r["near_50c_count"]
            cat_stats[cat]["total_mkts"] += r["market_count"]

        sorted_cats = sorted(cat_stats.items(), key=lambda x: x[1]["total_volume"], reverse=True)
        print(f"\n{'CATEGORY':<30} {'SERIES':>7} {'MARKETS':>8} {'VOLUME':>14} {'NEAR_50c':>10}")
        print("-" * 80)
        for cat, cs in sorted_cats:
            n50_pct = round(100 * cs["near_50c"] / cs["total_mkts"]) if cs["total_mkts"] else 0
            print(f"{cat:<30} {cs['series_count']:>7} {cs['market_count']:>8} {cs['total_volume']:>14,} {cs['near_50c']:>6}({n50_pct:>2}%)")

        # OPPORTUNITY ANALYSIS — wide spreads + high volume = tradeable inefficiency
        print(f"\n\n{'='*70}")
        print("OPPORTUNITY ANALYSIS — series with volume + near-50c pricing")
        print("(High near-50c% = uncertain outcomes = potential edge)")
        print(f"{'='*70}")
        opportunities = [r for r in report_lines if r["total_volume"] > 1000 and r["near_50c_pct"] > 20]
        opportunities.sort(key=lambda x: x["total_volume"], reverse=True)
        print(f"\n{'SERIES':<20} {'VOLUME':>12} {'NEAR_50c%':>10} {'AVG_SPREAD':>10} {'CATEGORY':<25} TITLE")
        print("-" * 110)
        for r in opportunities:
            spread_str = f"{r['avg_spread']:.1f}c" if r["avg_spread"] >= 0 else "n/a"
            print(f"{r['series']:<20} {r['total_volume']:>12,} {r['near_50c_pct']:>8}% {spread_str:>10} {r['category']:<25} {r['sample_title']}")

        # Save full report
        with open("data/kalshi_audit_report.json", "w") as f:
            json.dump({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_series": len(all_series),
                "total_open_events": len(all_events),
                "total_open_markets": len(all_markets),
                "series_breakdown": report_lines,
                "category_rollup": {cat: stats for cat, stats in sorted_cats},
            }, f, indent=2, default=str)
        print(f"\n\nFull report saved to data/kalshi_audit_report.json")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
