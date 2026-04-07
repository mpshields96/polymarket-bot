#!/usr/bin/env python3
"""
Kalshi Series Scout — Weekly Intelligence Scanner
Chat 48 (S269) | CCA design

Scans ALL Kalshi series, filters for high-volume non-covered markets,
outputs ranked list of expansion candidates.

Usage:
    python3 scripts/kalshi_series_scout.py [--output .planning/SERIES_SCOUT_YYYY-MM-DD.md]
    python3 scripts/kalshi_series_scout.py --dry-run  # print to stdout only

This is INTELLIGENCE, not automation. Matthew reviews output and decides what to add.

Schedule: weekly, Monday 06:00 ET
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Known covered series (already in strategy map) ──────────────────────
COVERED_SERIES = {
    # Crypto (live)
    "KXBTCD",     # BTC daily sniper
    "KXETHD",     # ETH daily sniper (disabled live, paper)
    # Sports (live or paper)
    "KXNBAGAME",
    "KXNHLGAME",
    "KXMLBGAME",
    "KXNCAABGAME",
    "KXUCLGAME",
    "KXEPLGAME",
    "KXBUNDESLIGAGAME",
    "KXSERIEAGAME",
    "KXLALIGAGAME",
    "KXLIGUE1GAME",
    "KXUFCFIGHT",  # paper validation planned
    # Economics (live or paper)
    "KXCPI",
    "KXFED",
    "KXUNRATE",
    "KXGDP",
    # Confirmed dead ends
    "KXBTC15M",
    "KXETH15M",
    "KXSOL15M",
    "KXXRP15M",
}

# ── Category classifier ──────────────────────────────────────────────────
CATEGORY_PREFIXES = {
    "KXB": "crypto",
    "KXE": "crypto_or_economics",
    "KXN": "sports",
    "KXM": "sports",
    "KXS": "sports",
    "KXL": "sports",
    "KXU": "sports_or_other",
    "KXC": "economics",
    "KXF": "economics",
    "KXG": "economics",
}

def classify_series(ticker: str) -> str:
    """Guess category from ticker prefix."""
    for prefix, cat in CATEGORY_PREFIXES.items():
        if ticker.upper().startswith(prefix):
            return cat
    return "unknown"

def is_dead_end(ticker: str) -> bool:
    """Quick filter for known waste categories."""
    dead_patterns = ["15M", "COPYTRADING", "VANITY", "MICRO"]
    return any(p in ticker.upper() for p in dead_patterns)

def scout(api_key: str, min_volume: int = 50_000, horizon_days: int = 7) -> list[dict]:
    """
    Fetch all Kalshi series, filter for viable expansion candidates.
    Returns list of dicts sorted by volume descending.
    """
    try:
        import requests
    except ImportError:
        print("ERROR: requests not available. Install via: pip install requests")
        sys.exit(1)

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(days=horizon_days)

    headers = {"Authorization": f"Bearer {api_key}"}
    base_url = "https://api.elections.kalshi.com/trade-api/v2"

    candidates = []
    cursor = None
    page = 0

    while True:
        params = {"limit": 1000, "status": "open"}
        if cursor:
            params["cursor"] = cursor

        try:
            resp = requests.get(f"{base_url}/markets", headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"API error on page {page}: {e}")
            break

        markets = data.get("markets", [])
        if not markets:
            break

        for m in markets:
            ticker = m.get("ticker", "")
            series = m.get("series_ticker", ticker.split("-")[0] if "-" in ticker else ticker)
            volume = m.get("volume", 0) or 0
            close_time = m.get("close_time", "")

            # Filter 1: volume threshold
            if volume < min_volume:
                continue

            # Filter 2: not already covered
            if any(series.startswith(c) or ticker.startswith(c) for c in COVERED_SERIES):
                continue

            # Filter 3: not a confirmed dead end
            if is_dead_end(series):
                continue

            # Filter 4: must close within horizon (or long-dated futures)
            try:
                close_dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
                if close_dt < now:  # already expired
                    continue
            except (ValueError, AttributeError):
                pass  # no close_time → include (futures style)

            category = classify_series(series)
            candidates.append({
                "series": series,
                "ticker": ticker,
                "volume": volume,
                "category": category,
                "close_time": close_time,
                "title": m.get("title", ""),
            })

        cursor = data.get("cursor")
        if not cursor:
            break
        page += 1
        if page > 100:  # safety cap
            break

    # Deduplicate by series (keep highest volume representative)
    by_series: dict[str, dict] = {}
    for c in candidates:
        s = c["series"]
        if s not in by_series or c["volume"] > by_series[s]["volume"]:
            by_series[s] = c

    return sorted(by_series.values(), key=lambda x: x["volume"], reverse=True)

def format_report(candidates: list[dict], run_date: str) -> str:
    lines = [
        f"# Kalshi Series Scout Report — {run_date}",
        f"# Min volume: 50,000 | Horizon: 7+ days remaining",
        f"# Found {len(candidates)} viable expansion candidates",
        "",
        "## Ranked by Volume",
        "",
    ]

    for i, c in enumerate(candidates[:50], 1):  # top 50 only
        vol_k = c["volume"] // 1000
        lines.append(f"### {i}. {c['series']} — {vol_k}K volume — [{c['category']}]")
        lines.append(f"   Title: {c['title'][:80]}")
        lines.append(f"   Ticker: {c['ticker']}")
        lines.append(f"   Close: {c['close_time'][:10] if c['close_time'] else 'N/A'}")
        lines.append(f"   Action: [ ] Review for FLB structure | [ ] Check bookmaker consensus available")
        lines.append("")

    lines += [
        "## Decision Framework",
        "",
        "For each candidate: answer YES to ALL before adding to strategy map:",
        "1. Is bookmaker consensus available via OddsAPI for this event type?",
        "2. Is volume > 50K (enough for clean fills at $3-5/bet)?",
        "3. Is there academic or empirical basis for FLB/bookmaker-consensus gap?",
        "4. Does this market open 7+ days before expiry (time to scan)?",
        "5. Can we paper-validate for 5+ events before live?",
        "",
        "If all YES: add to sports_game sport map. Paper first. 5-event validation gate.",
    ]

    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="Kalshi series scout — weekly expansion intelligence")
    parser.add_argument("--output", default=None, help="Output file path (default: stdout)")
    parser.add_argument("--dry-run", action="store_true", help="Print to stdout without writing file")
    parser.add_argument("--min-volume", type=int, default=50_000, help="Minimum volume threshold")
    args = parser.parse_args()

    api_key = os.environ.get("KALSHI_API_KEY") or os.environ.get("KALSHI_TOKEN")
    if not api_key:
        # Try reading from config
        config_path = Path(__file__).parent.parent / ".planning" / "config.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
                api_key = config.get("api_key") or config.get("kalshi_api_key")

    if not api_key:
        print("ERROR: No Kalshi API key found. Set KALSHI_API_KEY env var.")
        sys.exit(1)

    run_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Scouting Kalshi series (min volume: {args.min_volume:,})...")

    candidates = scout(api_key, min_volume=args.min_volume)
    report = format_report(candidates, run_date)

    if args.dry_run or not args.output:
        print(report)
    else:
        output_path = args.output or f".planning/SERIES_SCOUT_{run_date}.md"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(report)
        print(f"Report written to: {output_path}")
        print(f"Top 5 candidates:")
        for c in candidates[:5]:
            print(f"  {c['series']:30s} {c['volume']//1000:6d}K  [{c['category']}]  {c['title'][:50]}")

if __name__ == "__main__":
    main()
