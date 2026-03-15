"""
NCAA Tournament Scanner — one-shot edge finder.

JOB:    Find KXNCAAMBGAME markets where Kalshi prices a heavy favorite
        (90c+) meaningfully below what sharp books show.

WHEN:   Run March 17-21 once Kalshi opens Round 1 markets.
        Kalshi typically opens game markets 1-3 days before tip-off.

USAGE:
    python scripts/ncaa_tournament_scanner.py            # scan all open NCAAB
    python scripts/ncaa_tournament_scanner.py --min-edge 0.03

COST:   ~1 odds-api credit per run. Run sparingly (once/day March 17-21).

FINDINGS SO FAR:
    - Bracket dropped 2026-03-15 evening ET
    - As of 2026-03-15 ~07:00 UTC: Kalshi has 0 KXNCAAMBGAME open markets
    - the-odds-api has 0 Round 1 lines yet (check March 17-18)
    - First Four: March 19-20. Round 1: March 20-21.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

MIN_EDGE_DEFAULT = 0.03
MIN_FAV_PRICE_CENTS = 90  # only care about heavy favorites


def _parse_args():
    import argparse
    p = argparse.ArgumentParser(description='NCAA Tournament edge scanner')
    p.add_argument('--min-edge', type=float, default=MIN_EDGE_DEFAULT)
    p.add_argument('--min-price', type=int, default=MIN_FAV_PRICE_CENTS)
    return p.parse_args()


def _notify(message: str):
    """Send macOS Reminders notification."""
    try:
        import subprocess
        escaped = message.replace('"', '\\"')
        subprocess.run([
            'osascript', '-e',
            f'tell application "Reminders" to make new reminder with properties {{name:"{escaped}"}}'
        ], timeout=5, capture_output=True)
    except Exception:
        pass


async def scan_ncaab(min_edge: float, min_price_cents: int) -> list[dict]:
    """Scan Kalshi NCAAB markets vs sharp book odds. Returns edge opportunities."""
    # Import edge scanner comparison logic
    from scripts.edge_scanner import (
        fetch_kalshi_sports_markets,
        fetch_odds_api_games,
        parse_odds_games,
        compare_market,
    )

    odds_key = os.getenv("SDATA_KEY", "")
    kalshi_url = os.getenv("KALSHI_API_URL", "https://api.elections.kalshi.com/trade-api/v2")

    from src.auth.kalshi_auth import load_from_env as load_auth
    from src.platforms.kalshi import KalshiClient

    auth = load_auth()
    kalshi = KalshiClient(auth=auth, base_url=kalshi_url)
    await kalshi.__aenter__()

    try:
        # Get open Kalshi NCAAB markets
        kalshi_markets = await fetch_kalshi_sports_markets(kalshi, ["KXNCAAMBGAME"])
        logger.info(f"Kalshi NCAAB open markets: {len(kalshi_markets)}")

        if not kalshi_markets:
            logger.info("No KXNCAAMBGAME markets open yet. Check again March 17-18.")
            return []

        # Get sharp book odds
        raw_games = await fetch_odds_api_games("basketball_ncaab", odds_key)
        odds_lookup = parse_odds_games(raw_games)
        logger.info(f"Odds API NCAAB games: {len(raw_games)}")

        if not raw_games:
            logger.info("No NCAAB odds from sharp books yet. Lines typically appear March 17-19.")
            return []

        # Compare each Kalshi market
        opportunities = []
        for market in kalshi_markets:
            # Only care about heavy favorites
            fav_price = max(market.yes_price, market.no_price)
            if fav_price < min_price_cents:
                continue

            comparison = compare_market(market, odds_lookup, "KXNCAAMBGAME")
            if comparison is None:
                continue

            # Edge = sharp_book_prob - kalshi_price
            # Positive = Kalshi underprices the favorite
            sharp_prob = comparison.sharp_prob  # type: ignore
            kalshi_price = fav_price / 100.0
            edge = sharp_prob - kalshi_price

            if edge >= min_edge:
                opp = {
                    "ticker": market.ticker,
                    "title": market.title,
                    "kalshi_cents": fav_price,
                    "sharp_prob": round(sharp_prob, 4),
                    "edge": round(edge, 4),
                    "edge_pct": round(edge * 100, 1),
                }
                opportunities.append(opp)

        return opportunities

    finally:
        await kalshi.__aexit__(None, None, None)


def main():
    args = _parse_args()
    logger.info("=" * 60)
    logger.info(f"NCAA Tournament Scanner — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"Min edge: {args.min_edge:.1%} | Min fav price: {args.min_price}c")
    logger.info("=" * 60)

    opportunities = asyncio.run(scan_ncaab(args.min_edge, args.min_price))

    if not opportunities:
        logger.info("No opportunities found above threshold.")
        logger.info("Remember: Kalshi typically opens Round 1 markets March 17-18.")
        logger.info("Run again then. Round 1 tip-offs: March 20-21.")
    else:
        logger.info(f"\n*** {len(opportunities)} OPPORTUNITY/IES FOUND ***\n")
        for opp in sorted(opportunities, key=lambda x: -x['edge']):
            logger.info(
                f"  EDGE {opp['edge_pct']}% | {opp['ticker']}"
                f"\n    {opp['title']}"
                f"\n    Kalshi: {opp['kalshi_cents']}c | Sharp: {int(opp['sharp_prob']*100)}c"
            )

        # Send notification
        best = opportunities[0]
        _notify(
            f"NCAA Edge Found: {best['edge_pct']}% | "
            f"{best['ticker']} Kalshi={best['kalshi_cents']}c Sharp={int(best['sharp_prob']*100)}c"
        )

        # Save to file
        out = Path("data/ncaa_tournament_scan.json")
        out.write_text(json.dumps({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "opportunities": opportunities,
        }, indent=2))
        logger.info(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
