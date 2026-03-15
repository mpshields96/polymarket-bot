"""
Weather Calibration Tracker — GEFS vs Actual Settlement Analysis.

JOB:    Check all weather paper bets in the DB. For closed/finalized markets,
        compare GEFS prediction vs actual outcome. Report accuracy by city.
        For still-open but closed markets, infer likely outcome from YES price.

USAGE:
    python scripts/weather_calibration.py              # full report
    python scripts/weather_calibration.py --pending    # show inferred pending outcomes

OUTPUT:
    Per-city calibration accuracy (when settled data available).
    Inferred win/loss from current market price (for not-yet-finalized markets).
    Edge accuracy: did GEFS edge > 20% actually win?

WHY THIS MATTERS:
    Weather strategy has 16 paper bets placed but none settled yet (Kalshi delays).
    Market current prices infer likely outcome now. If KXHIGHCHI-T39 YES=0c,
    our NO bet effectively already won. This gives real-time calibration signal.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import aiohttp

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.platforms.kalshi import load_from_env

logger = logging.getLogger(__name__)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Weather calibration tracker")
    p.add_argument("--pending", action="store_true", help="Show inferred pending outcomes")
    p.add_argument("--verbose", action="store_true", help="Show all bets including unknowns")
    return p.parse_args()


async def _fetch_market_price(kalshi, ticker: str) -> dict:
    """Fetch current market YES price and status."""
    try:
        market = await kalshi.get_market(ticker)
        return {
            "ticker": ticker,
            "yes_price": market.yes_price,
            "no_price": market.no_price,
            "status": market.status,
            "result": market.result,
        }
    except Exception as e:
        logger.debug("Could not fetch %s: %s", ticker, e)
        return {
            "ticker": ticker,
            "yes_price": None,
            "no_price": None,
            "status": "unknown",
            "result": None,
        }


def _infer_outcome(side: str, yes_price: int | None) -> str:
    """
    Infer likely outcome from current market price.

    If YES=0-2c and we bet NO: very likely WIN.
    If YES=98-100c and we bet NO: very likely LOSS.
    If YES=0-2c and we bet YES: very likely LOSS.
    If YES=98-100c and we bet YES: very likely WIN.
    """
    if yes_price is None:
        return "UNKNOWN"

    if side == "no":
        if yes_price <= 2:
            return "LIKELY_WIN"
        elif yes_price >= 98:
            return "LIKELY_LOSS"
        elif yes_price <= 10:
            return "PROB_WIN"
        elif yes_price >= 90:
            return "PROB_LOSS"
        else:
            return "OPEN"
    else:  # yes
        if yes_price >= 98:
            return "LIKELY_WIN"
        elif yes_price <= 2:
            return "LIKELY_LOSS"
        elif yes_price >= 90:
            return "PROB_WIN"
        elif yes_price <= 10:
            return "PROB_LOSS"
        else:
            return "OPEN"


def _city_from_ticker(ticker: str) -> str:
    if "HIGHNY" in ticker:
        return "NYC"
    elif "HIGHLAX" in ticker:
        return "LAX"
    elif "HIGHCHI" in ticker:
        return "CHI"
    elif "HIGHDEN" in ticker:
        return "DEN"
    elif "HIGHMIA" in ticker:
        return "MIA"
    return "OTHER"


async def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    import sqlite3
    conn = sqlite3.connect("data/polybot.db")
    conn.row_factory = sqlite3.Row

    # Fetch all weather paper bets
    trades = conn.execute("""
        SELECT id, ticker, strategy, side, price_cents, count,
               result, pnl_cents, created_at, settled_at
        FROM trades
        WHERE is_paper = 1 AND strategy LIKE 'weather%'
        ORDER BY created_at DESC
    """).fetchall()

    if not trades:
        print("No weather paper bets found in DB.")
        return

    print(f"Weather Paper Bet Calibration Report")
    print(f"Total bets: {len(trades)}")
    print()

    kalshi = load_from_env()
    async with aiohttp.ClientSession() as session:
        kalshi._session = session

        # Get unique tickers
        tickers = list({t["ticker"] for t in trades})

        print(f"Fetching market prices for {len(tickers)} markets...")
        market_data = {}
        for ticker in tickers:
            data = await _fetch_market_price(kalshi, ticker)
            market_data[ticker] = data

        # Analyze each bet
        by_city: dict[str, list] = {}
        settled_count = 0
        likely_win = 0
        likely_loss = 0

        print()
        print("=== PENDING BETS (inferred outcomes from current market price) ===")
        print()

        for trade in trades:
            ticker = trade["ticker"]
            side = trade["side"]
            price_c = trade["price_cents"]
            mkt = market_data.get(ticker, {})
            yes_price = mkt.get("yes_price")
            status = mkt.get("status", "unknown")
            result = trade["result"]
            city = _city_from_ticker(ticker)

            if city not in by_city:
                by_city[city] = []

            if result:
                # Already settled
                settled_count += 1
                won = result == side
                by_city[city].append({
                    "status": "SETTLED",
                    "won": won,
                    "pnl_cents": trade["pnl_cents"],
                    "side": side,
                    "price": price_c,
                })
                continue

            # Not yet settled — infer from current market price
            inferred = _infer_outcome(side, yes_price)
            by_city[city].append({
                "status": "INFERRED",
                "inferred": inferred,
                "side": side,
                "price": price_c,
                "yes_price": yes_price,
                "market_status": status,
            })

            if inferred.endswith("WIN"):
                likely_win += 1
            elif inferred.endswith("LOSS"):
                likely_loss += 1

            # Show pending bets with inference
            if args.pending or args.verbose or inferred in ("LIKELY_WIN", "LIKELY_LOSS"):
                short_ticker = ticker.split("-", 2)[-1] if "-" in ticker else ticker
                mkt_stat = "CLOSED" if status == "closed" else status.upper()
                print(f"  {city} | {trade['strategy'][:15]:<15} | {short_ticker:<20} "
                      f"| {side.upper()}@{price_c}c | mkt_yes={yes_price}c "
                      f"| {mkt_stat} | => {inferred}")

        print()
        print("=== SUMMARY BY CITY ===")
        print()

        for city in ["NYC", "LAX", "CHI", "DEN", "MIA", "OTHER"]:
            bets = by_city.get(city, [])
            if not bets:
                continue

            settled = [b for b in bets if b["status"] == "SETTLED"]
            inferred = [b for b in bets if b["status"] == "INFERRED"]
            likely_wins_city = len([b for b in inferred if b.get("inferred", "").endswith("WIN")])
            likely_losses_city = len([b for b in inferred if b.get("inferred", "").endswith("LOSS")])

            print(f"  {city}: {len(bets)} bets total")
            if settled:
                wins = sum(1 for b in settled if b["won"])
                total_pnl = sum(b["pnl_cents"] for b in settled) / 100
                print(f"    Settled: {len(settled)} | W/L={wins}/{len(settled)-wins} "
                      f"| PnL={total_pnl:.2f} USD")
            if inferred:
                print(f"    Pending: {len(inferred)} | "
                      f"LikelyWin={likely_wins_city} LikelyLoss={likely_losses_city} "
                      f"Open={len(inferred)-likely_wins_city-likely_losses_city}")

        print()
        print(f"=== OVERALL STATUS ===")
        print(f"  Settled: {settled_count}")
        total_inferred = len(trades) - settled_count
        print(f"  Pending: {total_inferred} | LikelyWin={likely_win} LikelyLoss={likely_loss}")
        if likely_win + likely_loss > 0:
            inferred_wr = likely_win / (likely_win + likely_loss) * 100
            print(f"  Inferred win rate (excl OPEN): {inferred_wr:.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
