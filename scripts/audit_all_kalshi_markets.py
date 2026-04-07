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


def build_audit_report(all_series: list, all_events: list, all_markets: list) -> dict:
    """Build the structured audit report used by the CLI and visibility layer."""
    series_lookup = {}
    for series in all_series:
        ticker = series.get("ticker", "")
        series_lookup[ticker] = {
            "title": series.get("title", ""),
            "category": series.get("category", "unknown"),
            "tags": series.get("tags", []),
            "frequency": series.get("frequency", ""),
            "settlement_sources": series.get("settlement_sources", []),
        }

    series_stats = defaultdict(lambda: {
        "count": 0,
        "total_volume": 0,
        "prices": [],
        "spreads": [],
        "titles": set(),
        "event_tickers": set(),
    })
    for market in all_markets:
        series_ticker = market.get("series_ticker", "") or "UNKNOWN"
        event_ticker = market.get("event_ticker", "") or ""
        volume = extract_volume(market)
        price = extract_yes_price(market)
        spread = analyze_spread(market)
        title = market.get("title", "") or market.get("subtitle", "") or ""

        series_stats[series_ticker]["count"] += 1
        series_stats[series_ticker]["total_volume"] += volume
        series_stats[series_ticker]["prices"].append(price)
        if spread >= 0:
            series_stats[series_ticker]["spreads"].append(spread)
        series_stats[series_ticker]["titles"].add(title[:80])
        series_stats[series_ticker]["event_tickers"].add(event_ticker)

    event_categories = {}
    for event in all_events:
        event_ticker = event.get("event_ticker", "")
        event_categories[event_ticker] = {
            "category": event.get("category", "") or event.get("series_ticker", ""),
            "title": event.get("title", ""),
        }

    sorted_series = sorted(
        series_stats.items(),
        key=lambda item: item[1]["total_volume"],
        reverse=True,
    )

    series_breakdown = []
    for series_ticker, stats in sorted_series:
        prices = stats["prices"]
        avg_price = sum(prices) / len(prices) if prices else 0
        near_50_count = sum(1 for price in prices if 35 <= price <= 65)
        near_50_pct = round(100 * near_50_count / len(prices)) if prices else 0

        category = series_lookup.get(series_ticker, {}).get("category", "")
        if not category:
            for event_ticker in stats["event_tickers"]:
                if event_ticker in event_categories:
                    category = event_categories[event_ticker].get("category", "")
                    break

        sample_title = list(stats["titles"])[0][:50] if stats["titles"] else ""
        series_breakdown.append({
            "series": series_ticker,
            "market_count": stats["count"],
            "total_volume": stats["total_volume"],
            "avg_price_cents": round(avg_price, 1),
            "near_50c_count": near_50_count,
            "near_50c_pct": near_50_pct,
            "category": category,
            "sample_title": sample_title,
            "avg_spread": round(sum(stats["spreads"]) / len(stats["spreads"]), 1) if stats["spreads"] else -1,
        })

    category_rollup = defaultdict(
        lambda: {"series_count": 0, "market_count": 0, "total_volume": 0, "near_50c": 0, "total_mkts": 0}
    )
    for row in series_breakdown:
        category = row["category"] or "uncategorized"
        category_rollup[category]["series_count"] += 1
        category_rollup[category]["market_count"] += row["market_count"]
        category_rollup[category]["total_volume"] += row["total_volume"]
        category_rollup[category]["near_50c"] += row["near_50c_count"]
        category_rollup[category]["total_mkts"] += row["market_count"]

    sorted_categories = sorted(
        category_rollup.items(),
        key=lambda item: item[1]["total_volume"],
        reverse=True,
    )
    category_rollup_dict = {category: stats for category, stats in sorted_categories}

    opportunities = [
        row for row in series_breakdown
        if row["total_volume"] > 1000 and row["near_50c_pct"] > 20
    ]
    opportunities.sort(key=lambda row: row["total_volume"], reverse=True)

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_series": len(all_series),
        "total_open_events": len(all_events),
        "total_open_markets": len(all_markets),
        "series_breakdown": series_breakdown,
        "category_rollup": category_rollup_dict,
        "opportunities": opportunities,
    }


def print_audit_report(report: dict) -> None:
    """Print the human-readable audit summary."""
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    print(f"\n{'SERIES':<20} {'MKTS':>5} {'VOLUME':>12} {'AVG_PRICE':>10} {'NEAR_50c':>8} {'CATEGORY':<30} SAMPLE_TITLE")
    print("-" * 130)
    for row in report["series_breakdown"]:
        line = (
            f"{row['series']:<20} {row['market_count']:>5} {row['total_volume']:>12,} "
            f"{row['avg_price_cents']:>9.1f}c {row['near_50c_count']:>4}({row['near_50c_pct']:>2}%) "
            f"{row['category']:<30} {row['sample_title']}"
        )
        print(line)

    print(f"\n\n{'='*70}")
    print("CATEGORY ROLLUP")
    print(f"{'='*70}")
    print(f"\n{'CATEGORY':<30} {'SERIES':>7} {'MARKETS':>8} {'VOLUME':>14} {'NEAR_50c':>10}")
    print("-" * 80)
    for category, stats in report["category_rollup"].items():
        near_50_pct = round(100 * stats["near_50c"] / stats["total_mkts"]) if stats["total_mkts"] else 0
        print(
            f"{category:<30} {stats['series_count']:>7} {stats['market_count']:>8} "
            f"{stats['total_volume']:>14,} {stats['near_50c']:>6}({near_50_pct:>2}%)"
        )

    print(f"\n\n{'='*70}")
    print("OPPORTUNITY ANALYSIS — series with volume + near-50c pricing")
    print("(High near-50c% = uncertain outcomes = potential edge)")
    print(f"{'='*70}")
    print(f"\n{'SERIES':<20} {'VOLUME':>12} {'NEAR_50c%':>10} {'AVG_SPREAD':>10} {'CATEGORY':<25} TITLE")
    print("-" * 110)
    for row in report["opportunities"]:
        spread_str = f"{row['avg_spread']:.1f}c" if row["avg_spread"] >= 0 else "n/a"
        print(
            f"{row['series']:<20} {row['total_volume']:>12,} {row['near_50c_pct']:>8}% "
            f"{spread_str:>10} {row['category']:<25} {row['sample_title']}"
        )


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

        audit_report = build_audit_report(all_series, all_events, all_markets)
        print_audit_report(audit_report)

        with open("data/kalshi_audit_report.json", "w") as f:
            json.dump(audit_report, f, indent=2, default=str)
        print(f"\n\nFull report saved to data/kalshi_audit_report.json")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
