"""
NCAAB Live Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Monitor ESPN live NCAAB scores and corresponding Kalshi market prices.
    Identify when any team reaches 90c+ on Kalshi during a live game.
    Log all observations to build empirical evidence for NCAAB sniper feasibility.

USAGE:
    python scripts/ncaab_live_monitor.py

OUTPUT:
    Logs to stdout and /tmp/ncaab_monitor.log
    Only shows price changes and threshold crossings (90c+)

RESEARCH QUESTIONS:
    1. How often does a game reach 90c+ on Kalshi before the final buzzer?
    2. What lead size / game time triggers 90c+?
    3. How long does the 90c+ window last before settlement?
    4. What's the WR if we enter at 90c+?

DO NOT USE FOR LIVE TRADING. Research only.

FINDINGS SO FAR (S68):
    - ESPN API works: site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard
    - Kalshi prices DO move in real-time (MICH dropped 80c → 76c when down 5 pts in Q1)
    - Capital efficiency: ~75x worse than crypto sniper (120 min vs 2.5 min)
    - Settlement timing: same-day (within ~60 min of game end, S66 confirmed)
"""

import requests
import time
import os
import sys
import logging
from datetime import datetime, timezone

# ── Setup ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S UTC',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/ncaab_monitor.log'),
    ]
)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 120  # poll every 2 minutes
SNIPER_THRESHOLD = 0.90  # flag when market hits 90c+

ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard'


# ── ESPN ───────────────────────────────────────────────────────────────────

def get_live_games() -> list[dict]:
    """Return all in-progress NCAAB games from ESPN."""
    try:
        r = requests.get(ESPN_URL, timeout=10)
        events = r.json().get('events', [])
        games = []
        for e in events:
            comp = e.get('competitions', [{}])[0]
            teams = comp.get('competitors', [])
            status = comp.get('status', {})
            state = status.get('type', {}).get('name', '')

            if state != 'STATUS_IN_PROGRESS':
                continue

            if len(teams) < 2:
                continue

            t1, t2 = teams[0], teams[1]
            games.append({
                'event_id': e.get('id', ''),
                'name': e.get('name', ''),
                'team1_abbrev': t1.get('team', {}).get('abbreviation', '?'),
                'team1_score': int(t1.get('score', 0) or 0),
                'team1_home': t1.get('homeAway', '?'),
                'team2_abbrev': t2.get('team', {}).get('abbreviation', '?'),
                'team2_score': int(t2.get('score', 0) or 0),
                'period': status.get('period', 0),
                'clock': status.get('displayClock', '?'),
            })
        return games
    except Exception as e:
        logger.warning(f'ESPN fetch error: {e}')
        return []


# ── Kalshi ─────────────────────────────────────────────────────────────────

_auth = None

def _get_auth():
    global _auth
    if _auth is None:
        from dotenv import load_dotenv
        load_dotenv()
        from src.auth.kalshi_auth import KalshiAuth
        _auth = KalshiAuth(
            os.getenv('KALSHI_API_KEY_ID'),
            os.getenv('KALSHI_PRIVATE_KEY_PATH'),
        )
    return _auth


def get_open_ncaab_markets() -> list[dict]:
    """Return all open KXNCAAMBGAME markets with prices."""
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    url = f'https://api.elections.kalshi.com{path}?series_ticker=KXNCAAMBGAME&status=open&limit=200'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        markets = r.json().get('markets', [])
        result = []
        for m in markets:
            yb = float(m.get('yes_bid_dollars') or 0)
            ya = float(m.get('yes_ask_dollars') or 0)
            if yb <= 0 and ya <= 0:
                continue
            result.append({
                'ticker': m.get('ticker', ''),
                'title': m.get('title', '')[:60],
                'yes_bid': yb,
                'yes_ask': ya,
                'volume': float(m.get('volume_fp') or 0),
                'close_time': m.get('close_time', ''),
            })
        return result
    except Exception as e:
        logger.warning(f'Kalshi fetch error: {e}')
        return []


# ── Matching ───────────────────────────────────────────────────────────────

def find_kalshi_market(team_abbrev: str, markets: list[dict]) -> dict | None:
    """Find Kalshi market for a team abbreviation (fuzzy match)."""
    abbrev_upper = team_abbrev.upper()
    for m in markets:
        ticker = m.get('ticker', '').upper()
        # Ticker format: KXNCAAMBGAME-26MAR14WISMICH-MICH
        # Last part after final - is the team abbreviation
        parts = ticker.split('-')
        if len(parts) >= 3:
            kalshi_team = parts[-1]
            if kalshi_team == abbrev_upper or kalshi_team[:3] == abbrev_upper[:3]:
                return m
    return None


# ── Main loop ──────────────────────────────────────────────────────────────

def main():
    logger.info('=== NCAAB Live Monitor (Research Only) ===')
    logger.info(f'Poll interval: {POLL_INTERVAL_SEC}s | Sniper threshold: {int(SNIPER_THRESHOLD*100)}c')
    logger.info('NOT a trading bot — data collection only')

    seen_crossings: dict[str, float] = {}  # ticker → price when crossed 90c

    while True:
        now_utc = datetime.now(timezone.utc).strftime('%H:%M UTC')
        games = get_live_games()
        markets = get_open_ncaab_markets()

        if not games:
            logger.info(f'[{now_utc}] No live games')
        else:
            for g in games:
                lead1 = g['team1_score'] - g['team2_score']
                lead2 = -lead1
                logger.info(
                    f"[{now_utc}] {g['team1_abbrev']} {g['team1_score']} vs {g['team2_abbrev']} {g['team2_score']}"
                    f" | Q{g['period']} {g['clock']} | lead={lead1:+d}"
                )

                for team, lead in [(g['team1_abbrev'], lead1), (g['team2_abbrev'], lead2)]:
                    m = find_kalshi_market(team, markets)
                    if not m:
                        continue

                    price = max(m['yes_bid'], m['yes_ask'])
                    price_pct = int(price * 100)

                    if price >= SNIPER_THRESHOLD:
                        ticker = m['ticker']
                        if ticker not in seen_crossings:
                            seen_crossings[ticker] = price
                            logger.warning(
                                f'*** 90c+ CROSSING: {team} at {price_pct}c '
                                f'(lead={lead:+d} Q{g["period"]} {g["clock"]}) '
                                f'| ticker={ticker} ***'
                            )
                        else:
                            logger.info(f'  [{team}] STILL AT {price_pct}c (lead={lead:+d})')
                    else:
                        # Remove from seen if dropped below threshold
                        if m['ticker'] in seen_crossings:
                            del seen_crossings[m['ticker']]
                        logger.info(f'  [{team}] {price_pct}c (lead={lead:+d})')

        time.sleep(POLL_INTERVAL_SEC)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Monitor stopped')
