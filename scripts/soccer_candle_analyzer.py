"""
Soccer Candlestick Analyzer — Research Tool

PURPOSE:
    Analyzes historical soccer game candlestick data to find:
    1. Which games had mid-game 90c+ windows (not just post-game)
    2. How pre-game price correlates with mid-game 90c+ opportunity
    3. Average hold time and capital efficiency at different thresholds

USAGE:
    python scripts/soccer_candle_analyzer.py --series KXEPLGAME
    python scripts/soccer_candle_analyzer.py --series KXLALIGAGAME --threshold 0.80
    python scripts/soccer_candle_analyzer.py --all  # All 4 leagues

DATA SOURCE:
    Kalshi candlestick API — 1-minute resolution, no auth required for settled markets

OUTPUTS:
    Console summary + CSV to /tmp/soccer_candle_<series>.csv
"""

import argparse
import csv
import json
import os
import sys
import time
import requests
from datetime import datetime, timezone
from typing import Optional

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

SERIES_CONFIG = {
    "KXEPLGAME": {"label": "EPL", "kickoff_duration_h": 2.5},
    "KXLALIGAGAME": {"label": "La Liga", "kickoff_duration_h": 2.5},
    "KXUCLGAME": {"label": "UCL", "kickoff_duration_h": 2.5},
    "KXSERIEAGAME": {"label": "Serie A", "kickoff_duration_h": 2.5},
}


def get_settled_markets(series_ticker: str, limit: int = 100) -> list:
    """Get settled markets for a series — YES-side winners only."""
    resp = requests.get(
        f"{BASE_URL}/markets",
        params={"series_ticker": series_ticker, "status": "settled", "limit": limit},
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    markets = resp.json().get("markets", [])
    # Filter to YES-side winners with meaningful volume
    return [
        m for m in markets
        if m.get("result") == "yes" and float(m.get("volume_fp", 0) or 0) > 50_000
    ]


def get_candlesticks(series_ticker: str, market_ticker: str, close_time_iso: str) -> list:
    """
    Get 1-minute candlesticks around game time.
    close_time_iso is the market close time — use ±4 hours as window.
    """
    try:
        close_dt = datetime.fromisoformat(close_time_iso.replace("Z", "+00:00"))
    except Exception:
        return []

    end_ts = int(close_dt.timestamp()) + 3600  # 1h after close
    start_ts = int(close_dt.timestamp()) - 14400  # 4h before close

    resp = requests.get(
        f"{BASE_URL}/series/{series_ticker}/markets/{market_ticker}/candlesticks",
        params={"start_ts": start_ts, "end_ts": end_ts, "period_interval": 1},
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    return resp.json().get("candlesticks", [])


def analyze_candles(candles: list, threshold: float = 0.90) -> dict:
    """
    Analyze price movement to find threshold crossings.
    Returns dict with timing and duration info.
    """
    if not candles:
        return {}

    # Sort by time
    candles = sorted(candles, key=lambda c: c["end_period_ts"])

    first_ts = candles[0]["end_period_ts"]
    last_ts = candles[-1]["end_period_ts"]

    # Pre-game price: average of first 30 min (before volume spike)
    pre_game_bids = []
    for c in candles[:30]:
        vol = float(c.get("volume_fp", 0) or 0)
        if vol > 0:
            bid = float(c.get("yes_bid", {}).get("close_dollars", 0) or 0)
            if bid > 0:
                pre_game_bids.append(bid)
    pre_game_price = sum(pre_game_bids) / len(pre_game_bids) if pre_game_bids else 0.0

    # Find first crossing of threshold
    first_crossing_ts = None
    first_crossing_price = None
    minutes_at_threshold = 0
    max_bid = 0

    for c in candles:
        ts = c["end_period_ts"]
        bid_high = float(c.get("yes_bid", {}).get("high_dollars", 0) or 0)
        bid_close = float(c.get("yes_bid", {}).get("close_dollars", 0) or 0)
        max_bid = max(max_bid, bid_high)

        if bid_high >= threshold and first_crossing_ts is None:
            first_crossing_ts = ts
            first_crossing_price = bid_close

        if first_crossing_ts and bid_close >= threshold:
            minutes_at_threshold += 1

    # Minutes elapsed from first candle to first crossing
    minutes_to_crossing = None
    if first_crossing_ts is not None:
        minutes_to_crossing = (first_crossing_ts - first_ts) / 60

    return {
        "pre_game_price": round(pre_game_price, 2),
        "max_bid": round(max_bid, 2),
        "first_crossing_ts": first_crossing_ts,
        "first_crossing_price": first_crossing_price,
        "minutes_to_crossing": round(minutes_to_crossing, 0) if minutes_to_crossing is not None else None,
        "minutes_at_threshold": minutes_at_threshold,
        "total_candles": len(candles),
    }


def run_analysis(series: str, threshold: float = 0.90, limit: int = 50) -> None:
    """Run full analysis for a series."""
    cfg = SERIES_CONFIG.get(series, {"label": series, "kickoff_duration_h": 2.5})
    label = cfg["label"]

    print(f"\n{'='*60}")
    print(f"Soccer Sniper Analysis: {label} ({series})")
    print(f"Threshold: {threshold:.0%} | Min volume: 50K | Max games: {limit}")
    print(f"{'='*60}")

    markets = get_settled_markets(series, limit=limit)
    print(f"Found {len(markets)} high-volume YES-side winners\n")

    rows = []
    had_mid_game_90c = 0
    had_post_game_only = 0
    no_90c = 0

    for m in markets:
        ticker = m.get("ticker", "")
        close_time = m.get("close_time") or m.get("expiration_time", "")
        vol = float(m.get("volume_fp", 0) or 0)

        candles = get_candlesticks(series, ticker, close_time)
        if not candles:
            continue

        result = analyze_candles(candles, threshold)
        if not result:
            continue

        # Classify: mid-game vs post-game vs no crossing
        minutes_to = result.get("minutes_to_crossing")
        minutes_at = result.get("minutes_at_threshold", 0)
        pre_game = result.get("pre_game_price", 0)

        # Mid-game = crossed threshold while there was still meaningful time left
        # Proxy: if there are 30+ candles (min) after the crossing, it was mid-game
        if minutes_to is None:
            category = "NO_CROSS"
            no_90c += 1
        elif minutes_at >= 30:  # at least 30 min above threshold before settlement
            category = "MID_GAME"
            had_mid_game_90c += 1
        else:
            category = "POST_GAME"
            had_post_game_only += 1

        short_ticker = ticker[-22:]
        print(
            f"  {short_ticker:22s} | pre={pre_game:.2f} | "
            f"first_{threshold:.0%}={minutes_to}min | "
            f"duration={minutes_at}min | {category}"
        )

        rows.append({
            "ticker": ticker,
            "series": series,
            "pre_game_price": pre_game,
            "max_bid": result.get("max_bid", 0),
            "minutes_to_crossing": minutes_to,
            "minutes_at_threshold": minutes_at,
            "category": category,
            "volume_fp": int(vol),
        })

        time.sleep(0.2)  # rate limit

    print(f"\n--- SUMMARY ---")
    total = had_mid_game_90c + had_post_game_only + no_90c
    if total:
        print(f"MID_GAME (30+ min at {threshold:.0%}): {had_mid_game_90c}/{total} = {100*had_mid_game_90c/total:.0f}%")
        print(f"POST_GAME only:                        {had_post_game_only}/{total} = {100*had_post_game_only/total:.0f}%")
        print(f"NEVER crossed {threshold:.0%}:              {no_90c}/{total} = {100*no_90c/total:.0f}%")

    # Pre-game price correlation with mid-game opportunity
    mid_games = [r for r in rows if r["category"] == "MID_GAME"]
    post_games = [r for r in rows if r["category"] == "POST_GAME"]
    if mid_games:
        avg_pre = sum(r["pre_game_price"] for r in mid_games) / len(mid_games)
        avg_wait = sum(r["minutes_to_crossing"] or 0 for r in mid_games) / len(mid_games)
        avg_hold = sum(r["minutes_at_threshold"] for r in mid_games) / len(mid_games)
        print(f"\nMID_GAME stats:")
        print(f"  Avg pre-game price: {avg_pre:.2f}")
        print(f"  Avg min to 90c+:    {avg_wait:.0f} min")
        print(f"  Avg hold time:      {avg_hold:.0f} min")
    if post_games:
        avg_pre2 = sum(r["pre_game_price"] for r in post_games) / len(post_games)
        print(f"\nPOST_GAME stats:")
        print(f"  Avg pre-game price: {avg_pre2:.2f}")

    # Save CSV
    csv_path = f"/tmp/soccer_candle_{series}.csv"
    with open(csv_path, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
    print(f"\nCSV saved: {csv_path}")


def main():
    parser = argparse.ArgumentParser(description="Soccer Candle Analyzer")
    parser.add_argument("--series", default="KXEPLGAME", choices=list(SERIES_CONFIG.keys()))
    parser.add_argument("--all", action="store_true", help="Run all 4 leagues")
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument("--limit", type=int, default=50, help="Max settled games to analyze")
    args = parser.parse_args()

    if args.all:
        for series in SERIES_CONFIG:
            run_analysis(series, args.threshold, args.limit)
    else:
        run_analysis(args.series, args.threshold, args.limit)


if __name__ == "__main__":
    main()
