"""
UCL Live Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Monitor ESPN live UEFA Champions League scores and corresponding Kalshi
    KXUCLGAME market prices in real-time. Identify if/when markets hit 90c+
    during a live game, log all price observations, and build empirical evidence
    for UCL in-play sniper feasibility.

USAGE:
    python scripts/ucl_live_monitor.py
    python scripts/ucl_live_monitor.py --date 26MAR17   # filter to specific match-day
    python scripts/ucl_live_monitor.py --interval 30    # poll every 30s (default 60)

OUTPUT:
    Logs to stdout and /tmp/ucl_monitor.log
    Only shows price changes ≥1c and 90c+ threshold crossings

RESEARCH QUESTIONS:
    1. Do KXUCLGAME markets update in real-time during a live UCL game?
    2. How often does any outcome hit 90c+ before 90 minutes?
    3. What game state (lead, minute) triggers 90c+?
    4. How long does the 90c+ window last before early settlement?
    5. Is capital efficiency competitive with crypto 15-min sniper (~2.5 min hold)?

KEY HYPOTHESIS:
    UCL favorite-longshot bias same as crypto sniper, but:
    - Volume is 10-100x larger (745K contracts vs 5-10K for NCAAB)
    - 90-min game + can_close_early = settlement within 30s of result
    - Large leads in 60+ min = near-certainty, market may reach 90c+

DO NOT USE FOR LIVE TRADING. Research only.

MATCH SCHEDULE (March 2026):
    March 17: Sporting vs Bodo (17:45 UTC), Man City vs Real Madrid (20:00 UTC),
              Chelsea vs PSG (20:00 UTC), Arsenal vs Leverkusen (20:00 UTC)
    March 18: Barcelona vs Newcastle (17:45 UTC), Bayern vs Atalanta (20:00 UTC),
              Tottenham vs Atletico (20:00 UTC), Liverpool vs Galatasaray (20:00 UTC)
"""

import argparse
import os
import sys
import time
import logging
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S UTC',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/ucl_monitor.log'),
    ],
)
logger = logging.getLogger(__name__)

DEFAULT_POLL_SEC = 60
SNIPER_THRESHOLD = 0.90

ESPN_URL = 'https://site.api.espn.com/apis/site/v2/sports/soccer/UEFA.CHAMPIONS/scoreboard'

# ESPN team abbreviation → Kalshi KXUCLGAME team code
# Manually built from known March 17-18 matchups + common UCL teams
TEAM_MAP: dict[str, str] = {
    # Real Madrid
    'REAL MADRID': 'RMA',
    'REAL': 'RMA',
    # Manchester City
    'MANCHESTER CITY': 'MCI',
    'MAN CITY': 'MCI',
    # Arsenal
    'ARSENAL': 'ARS',
    # Bayer Leverkusen
    'BAYER LEVERKUSEN': 'LEV',
    'LEVERKUSEN': 'LEV',
    # Chelsea
    'CHELSEA': 'CFC',
    # Paris Saint-Germain
    'PARIS SAINT-GERMAIN': 'PSG',
    'PARIS SG': 'PSG',
    'PSG': 'PSG',
    # Sporting CP
    'SPORTING CP': 'SPO',
    'SPORTING': 'SPO',
    # FK Bodo/Glimt
    'BODO/GLIMT': 'BOG',
    'BODO': 'BOG',
    "FK BODO": 'BOG',
    # Bayern Munich
    'BAYERN MUNICH': 'BMU',
    'BAYERN': 'BMU',
    # Atalanta
    'ATALANTA': 'ATA',
    # Tottenham
    'TOTTENHAM HOTSPUR': 'TOT',
    'TOTTENHAM': 'TOT',
    # Atletico Madrid
    'ATLETICO DE MADRID': 'ATM',
    'ATLETICO MADRID': 'ATM',
    'ATL. MADRID': 'ATM',
    # Liverpool
    'LIVERPOOL': 'LFC',
    # Galatasaray
    'GALATASARAY': 'GAL',
    # Barcelona
    'FC BARCELONA': 'BAR',
    'BARCELONA': 'BAR',
    # Newcastle
    'NEWCASTLE UNITED': 'NEW',
    'NEWCASTLE': 'NEW',
    # Borussia Dortmund (potential future)
    'BORUSSIA DORTMUND': 'DOR',
    # AC Milan
    'AC MILAN': 'MIL',
    # Inter Milan
    'INTER MILAN': 'INT',
    'INTERNAZIONALE': 'INT',
    # Benfica
    'BENFICA': 'BEN',
    # Club Brugge
    'CLUB BRUGGE': 'CLB',
    # Juventus
    'JUVENTUS': 'JUV',
    # Celtic
    'CELTIC': 'CEL',
    # Feyenoord
    'FEYENOORD': 'FEY',
    # Lazio
    'LAZIO': 'LAZ',
    # Porto
    'FC PORTO': 'POR',
    'PORTO': 'POR',
}


# ── ESPN ───────────────────────────────────────────────────────────────────

def get_live_ucl_games() -> list[dict]:
    """Return all in-progress UCL games from ESPN."""
    try:
        r = requests.get(ESPN_URL, timeout=10)
        r.raise_for_status()
        events = r.json().get('events', [])
        games = []
        for e in events:
            comp = e.get('competitions', [{}])[0]
            teams = comp.get('competitors', [])
            status = comp.get('status', {})
            state = status.get('type', {}).get('name', '')

            home_score = away_score = 0
            home_name = away_name = 'UNK'
            home_kalshi = away_kalshi = None

            for t in teams:
                name = t.get('team', {}).get('displayName', '') or ''
                name_upper = name.upper()
                score = int(t.get('score', 0) or 0)
                kalshi_code = _lookup_team(name_upper)

                if t.get('homeAway') == 'home':
                    home_name = name
                    home_score = score
                    home_kalshi = kalshi_code
                else:
                    away_name = name
                    away_score = score
                    away_kalshi = kalshi_code

            games.append({
                'event_id': e.get('id', ''),
                'name': e.get('name', ''),
                'home_name': home_name,
                'home_score': home_score,
                'home_kalshi': home_kalshi,
                'away_name': away_name,
                'away_score': away_score,
                'away_kalshi': away_kalshi,
                'state': state,
                'period': status.get('period', 0),
                'clock': status.get('displayClock', '?'),
                'detail': status.get('type', {}).get('detail', ''),
            })
        return games
    except Exception as e:
        logger.warning(f'ESPN fetch error: {e}')
        return []


def _lookup_team(name_upper: str) -> str | None:
    """Try exact then partial match in TEAM_MAP."""
    if name_upper in TEAM_MAP:
        return TEAM_MAP[name_upper]
    for key, code in TEAM_MAP.items():
        if key in name_upper or name_upper in key:
            return code
    return None


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


def get_ucl_markets(date_filter: str | None = None) -> dict[str, dict]:
    """
    Return dict of {kalshi_team_code: market_dict} for open KXUCLGAME markets.
    If date_filter provided (e.g. '26MAR17'), only return markets with that date.
    """
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    params = 'series_ticker=KXUCLGAME&status=open&limit=100'
    url = f'https://api.elections.kalshi.com{path}?{params}'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        r.raise_for_status()
        markets = r.json().get('markets', [])
        result = {}
        for m in markets:
            ticker = m.get('ticker', '')

            if date_filter and date_filter.upper() not in ticker.upper():
                continue

            # Last segment after final hyphen is team code (RMA, MCI, TIE, etc.)
            parts = ticker.split('-')
            if len(parts) < 3:
                continue
            team_code = parts[-1].upper()

            yb = float(m.get('yes_bid_dollars') or 0)
            ya = float(m.get('yes_ask_dollars') or 0)
            last = float(m.get('last_price_dollars') or 0)

            result[team_code] = {
                'ticker': ticker,
                'title': m.get('title', '')[:60],
                'yes_bid': yb,
                'yes_ask': ya,
                'last': last,
                'mid': round((yb + ya) / 2, 3) if (yb + ya) > 0 else last,
                'volume': float(m.get('volume_fp') or 0),
                'close_time': m.get('close_time', ''),
                'status': m.get('status', ''),
            }
        return result
    except Exception as e:
        logger.warning(f'Kalshi UCL fetch error: {e}')
        return {}


# ── Observation log ────────────────────────────────────────────────────────

class PriceTracker:
    """Track price history per market ticker for change detection."""

    def __init__(self):
        self._last: dict[str, float] = {}  # ticker → last logged mid price
        self._crossings: dict[str, float] = {}  # ticker → price at 90c crossing
        self._price_moved: dict[str, bool] = {}  # ticker → ever moved from start?
        self._initial: dict[str, float] = {}  # ticker → price at first observation

    def observe(self, ticker: str, mid: float, game_state: str) -> None:
        """Log price observation, highlighting changes and threshold crossings."""
        prev = self._last.get(ticker)

        if ticker not in self._initial:
            self._initial[ticker] = mid
            self._price_moved[ticker] = False
            logger.info(f'  [INIT] {ticker} | {int(mid*100)}c')

        change = mid - prev if prev is not None else 0
        moved = abs(change) >= 0.01  # ≥1c change

        if moved:
            self._price_moved[ticker] = True
            direction = '▲' if change > 0 else '▼'
            logger.info(
                f'  [MOVE] {ticker} | {int(mid*100)}c {direction}{int(abs(change)*100)}c | {game_state}'
            )

        if mid >= SNIPER_THRESHOLD:
            if ticker not in self._crossings:
                self._crossings[ticker] = mid
                logger.warning(
                    f'  *** 90c+ CROSSING: {ticker} at {int(mid*100)}c | {game_state} ***'
                )
            elif moved:
                logger.warning(
                    f'  *** STILL 90c+: {ticker} at {int(mid*100)}c | {game_state} ***'
                )
        else:
            if ticker in self._crossings:
                del self._crossings[ticker]
                logger.info(f'  [DROPPED] {ticker} fell below 90c → {int(mid*100)}c | {game_state}')

        self._last[ticker] = mid

    def has_ever_moved(self, ticker: str) -> bool:
        return self._price_moved.get(ticker, False)

    def summary(self) -> str:
        movers = [t for t, v in self._price_moved.items() if v]
        crossings = list(self._crossings.keys())
        return (
            f'Movers (ever): {len(movers)} | Active 90c+: {len(crossings)}'
            + (f' ACTIVE: {", ".join(crossings)}' if crossings else '')
        )


# ── Main loop ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='UCL Live Monitor (Research Only)')
    parser.add_argument('--date', default=None, help='Match date filter e.g. 26MAR17')
    parser.add_argument('--interval', type=int, default=DEFAULT_POLL_SEC,
                        help=f'Poll interval seconds (default {DEFAULT_POLL_SEC})')
    args = parser.parse_args()

    logger.info('=== UCL Live Monitor (Research Only — NOT a trading bot) ===')
    logger.info(f'Poll interval: {args.interval}s | Threshold: {int(SNIPER_THRESHOLD*100)}c')
    if args.date:
        logger.info(f'Date filter: {args.date}')
    logger.info('Watching: KXUCLGAME markets for live in-play price movement')
    logger.info('')

    tracker = PriceTracker()
    cycle = 0

    while True:
        cycle += 1
        now_utc = datetime.now(timezone.utc).strftime('%H:%M UTC')

        all_games = get_live_ucl_games()
        live_games = [g for g in all_games if g['state'] == 'STATUS_IN_PROGRESS']
        scheduled = [g for g in all_games if g['state'] in ('STATUS_SCHEDULED',)]
        markets = get_ucl_markets(args.date)

        # ── No live games ──
        if not live_games:
            game_count = len(all_games)
            sched_count = len(scheduled)
            mkt_count = len(markets)

            if cycle % 5 == 1:  # Log only every 5th cycle when no live games
                logger.info(
                    f'[{now_utc}] No live UCL games | ESPN events={game_count} scheduled={sched_count}'
                    f' | Kalshi markets={mkt_count}'
                )
                # Still probe market prices when no live game — detect pre-game movement
                if markets:
                    for team_code, m in sorted(markets.items(), key=lambda x: -x[1]['volume']):
                        if m['mid'] > 0:
                            game_state = f'PRE-GAME | vol={int(m["volume"])}'
                            tracker.observe(m['ticker'], m['mid'], game_state)

        # ── Live games ──
        for g in live_games:
            lead_home = g['home_score'] - g['away_score']
            game_state = (
                f'{g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]}'
                f' | {g["detail"]} | lead={lead_home:+d}'
            )
            logger.info(f'[{now_utc}] LIVE: {game_state}')

            # Check each outcome's market price
            for team_code, lead in [
                (g['home_kalshi'], lead_home),
                (g['away_kalshi'], -lead_home),
                ('TIE', 0),  # Check TIE market too
            ]:
                if not team_code or team_code not in markets:
                    if team_code and team_code not in markets:
                        logger.debug(f'  No Kalshi market found for team_code={team_code}')
                    continue

                m = markets[team_code]
                if m['mid'] <= 0:
                    continue

                detail = f'{game_state} | team={team_code} lead={lead:+d}'
                tracker.observe(m['ticker'], m['mid'], detail)

        # ── Periodic summary ──
        if cycle % 10 == 0:
            logger.info(f'[SUMMARY at {now_utc}] {tracker.summary()}')

        time.sleep(args.interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Monitor stopped')
