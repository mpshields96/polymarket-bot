"""
UCL Live Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Monitor ESPN live UEFA Champions League scores and corresponding Kalshi
    KXUCLGAME market prices in real-time. Identify if/when markets hit 90c+
    during a live game, log all price observations, and build empirical evidence
    for UCL in-play sniper feasibility.

USAGE:
    python scripts/ucl_live_monitor.py                   # REST polling mode (default)
    python scripts/ucl_live_monitor.py --date 26MAR17    # filter to specific match-day
    python scripts/ucl_live_monitor.py --ws              # WebSocket mode (real-time)
    python scripts/ucl_live_monitor.py --ws --date 26MAR17

MODES:
    REST (default): polls Kalshi every 60s, ESPN every 60s. Suitable for pre-game monitoring.
    WebSocket (--ws): subscribes to Kalshi orderbook_delta channel for tick-by-tick prices.
                      Use during live games for precise 90c+ crossing detection.

OUTPUT:
    Logs to stdout and /tmp/ucl_monitor.log
    Only shows price changes and 90c+ threshold crossings

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

EVIDENCE FROM SETTLED GAMES (March 10, 2026):
    - ATM won vs Tottenham: ATM last_price=0.99 (CONFIRMED live price movement)
    - GAL won vs Liverpool: GAL last_price=0.99 (Galatasaray ~8c pre-game, massive upset)
    - RMA won vs MCI: RMA last_price=0.99, vol=2.8M
    - BMU won vs Atalanta: BMU last_price=0.99
    - TIE in LEV vs ARS: TIE last_price=0.99 (note: Leverkusen vs Arsenal ended in tie)
    All winners at 99c = markets DO update live and were actively traded to near-certainty

DO NOT USE FOR LIVE TRADING. Research only.

MATCH SCHEDULE (March 2026):
    March 17: Sporting vs Bodo (17:45 UTC), Man City vs Real Madrid (20:00 UTC),
              Chelsea vs PSG (20:00 UTC), Arsenal vs Leverkusen (20:00 UTC)
    March 18: Barcelona vs Newcastle (17:45 UTC), Bayern vs Atalanta (20:00 UTC),
              Tottenham vs Atletico (20:00 UTC), Liverpool vs Galatasaray (20:00 UTC)
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import time
import logging
import requests
import threading
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

# ESPN team display name → Kalshi KXUCLGAME team code
TEAM_MAP: dict[str, str] = {
    'REAL MADRID': 'RMA', 'REAL': 'RMA',
    'MANCHESTER CITY': 'MCI', 'MAN CITY': 'MCI', 'MAN. CITY': 'MCI',
    'ARSENAL': 'ARS',
    'BAYER LEVERKUSEN': 'LEV', 'LEVERKUSEN': 'LEV',
    'CHELSEA': 'CFC',
    'PARIS SAINT-GERMAIN': 'PSG', 'PARIS SG': 'PSG', 'PSG': 'PSG',
    'SPORTING CP': 'SPO', 'SPORTING': 'SPO',
    'BODO/GLIMT': 'BOG', 'BODO': 'BOG', 'FK BODO': 'BOG',
    'BAYERN MUNICH': 'BMU', 'BAYERN': 'BMU', 'FC BAYERN MÜNCHEN': 'BMU',
    'ATALANTA': 'ATA', 'ATALANTA BC': 'ATA',
    'TOTTENHAM HOTSPUR': 'TOT', 'TOTTENHAM': 'TOT',
    'ATLETICO DE MADRID': 'ATM', 'ATLETICO MADRID': 'ATM', 'ATL. MADRID': 'ATM',
    'LIVERPOOL': 'LFC', 'LIVERPOOL FC': 'LFC',
    'GALATASARAY': 'GAL',
    'FC BARCELONA': 'BAR', 'BARCELONA': 'BAR',
    'NEWCASTLE UNITED': 'NEW', 'NEWCASTLE': 'NEW',
    'BORUSSIA DORTMUND': 'DOR',
    'AC MILAN': 'MIL',
    'INTERNAZIONALE': 'INT', 'INTER MILAN': 'INT',
    'BENFICA': 'BEN', 'SL BENFICA': 'BEN',
    'CLUB BRUGGE': 'CLB',
    'JUVENTUS': 'JUV',
    'CELTIC': 'CEL',
    'FEYENOORD': 'FEY',
    'FC PORTO': 'POR', 'PORTO': 'POR',
}


# ── ESPN ───────────────────────────────────────────────────────────────────

def get_live_ucl_games() -> list[dict]:
    """Return all UCL games from ESPN (any status)."""
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

            home_name = away_name = 'UNK'
            home_score = away_score = 0
            home_kalshi = away_kalshi = None

            for t in teams:
                name = t.get('team', {}).get('displayName', '') or ''
                name_upper = name.upper()
                score = int(t.get('score', 0) or 0)
                kalshi_code = _lookup_team(name_upper)
                if t.get('homeAway') == 'home':
                    home_name, home_score, home_kalshi = name, score, kalshi_code
                else:
                    away_name, away_score, away_kalshi = name, score, kalshi_code

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
    if name_upper in TEAM_MAP:
        return TEAM_MAP[name_upper]
    for key, code in TEAM_MAP.items():
        if key in name_upper or name_upper in key:
            return code
    return None


# ── Kalshi auth ─────────────────────────────────────────────────────────────

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


def _make_ws_headers(path: str) -> list[tuple[str, str]]:
    """Build signed WebSocket headers for Kalshi."""
    from dotenv import load_dotenv
    load_dotenv()
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.backends import default_backend

    ts = str(int(time.time() * 1000))
    msg = ts + 'GET' + path
    with open(os.getenv('KALSHI_PRIVATE_KEY_PATH'), 'rb') as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    sig = private_key.sign(
        msg.encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return [
        ('KALSHI-ACCESS-KEY', os.getenv('KALSHI_API_KEY_ID')),
        ('KALSHI-ACCESS-TIMESTAMP', ts),
        ('KALSHI-ACCESS-SIGNATURE', base64.b64encode(sig).decode()),
    ]


# ── Kalshi REST ─────────────────────────────────────────────────────────────

def get_ucl_markets(date_filter: str | None = None) -> dict[str, dict]:
    """Return dict of {kalshi_team_code: market_dict} for open KXUCLGAME markets."""
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    url = f'https://api.elections.kalshi.com{path}?series_ticker=KXUCLGAME&status=open&limit=100'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        r.raise_for_status()
        markets = r.json().get('markets', [])
        result = {}
        for m in markets:
            ticker = m.get('ticker', '')
            if date_filter and date_filter.upper() not in ticker.upper():
                continue
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
            }
        return result
    except Exception as e:
        logger.warning(f'Kalshi REST fetch error: {e}')
        return {}


# ── Price tracker ──────────────────────────────────────────────────────────

class PriceTracker:
    """Track price history per market ticker for change detection."""

    def __init__(self):
        self._last: dict[str, float] = {}
        self._crossings: dict[str, float] = {}
        self._ever_moved: dict[str, bool] = {}
        self._initial: dict[str, float] = {}
        self._crossing_times: dict[str, str] = {}  # ticker → UTC time of first 90c crossing
        self._lock = threading.Lock()

    def observe(self, ticker: str, mid: float, game_state: str) -> None:
        with self._lock:
            now = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
            prev = self._last.get(ticker)

            if ticker not in self._initial:
                self._initial[ticker] = mid
                self._ever_moved[ticker] = False
                logger.info(f'  [INIT] {ticker} | {int(mid*100)}c @ {now}')

            change = (mid - prev) if prev is not None else 0
            moved = abs(change) >= 0.01

            if moved:
                self._ever_moved[ticker] = True
                direction = '▲' if change > 0 else '▼'
                logger.info(
                    f'  [MOVE] {ticker} | {int(mid*100)}c {direction}{int(abs(change)*100)}c | {game_state}'
                )

            if mid >= SNIPER_THRESHOLD:
                if ticker not in self._crossings:
                    self._crossings[ticker] = mid
                    self._crossing_times[ticker] = now
                    logger.warning(
                        f'  *** 90c+ CROSSING: {ticker} at {int(mid*100)}c | {game_state} | time={now} ***'
                    )
                elif moved:
                    logger.warning(
                        f'  *** STILL 90c+: {ticker} at {int(mid*100)}c {direction}{int(abs(change)*100)}c '
                        f'| {game_state} ***'
                    )
            else:
                if ticker in self._crossings:
                    first_time = self._crossing_times.pop(ticker, '?')
                    del self._crossings[ticker]
                    logger.info(
                        f'  [DROPPED] {ticker} fell below 90c → {int(mid*100)}c '
                        f'| was above since {first_time} | {game_state}'
                    )

            self._last[ticker] = mid

    def summary(self) -> str:
        movers = sum(1 for v in self._ever_moved.values() if v)
        crossings = list(self._crossings.keys())
        return (
            f'Movers (ever): {movers} | Active 90c+: {len(crossings)}'
            + (f' → {", ".join(crossings)}' if crossings else '')
        )


# ── REST polling mode ──────────────────────────────────────────────────────

def run_rest_mode(date_filter: str | None, poll_sec: int):
    tracker = PriceTracker()
    cycle = 0

    logger.info(f'REST mode: poll every {poll_sec}s')

    while True:
        cycle += 1
        now_utc = datetime.now(timezone.utc).strftime('%H:%M UTC')

        all_games = get_live_ucl_games()
        live_games = [g for g in all_games if g['state'] == 'STATUS_IN_PROGRESS']
        markets = get_ucl_markets(date_filter)

        if not live_games:
            if cycle % 5 == 1:
                sched = sum(1 for g in all_games if g['state'] == 'STATUS_SCHEDULED')
                logger.info(
                    f'[{now_utc}] No live games | ESPN events={len(all_games)} scheduled={sched}'
                    f' | Kalshi markets={len(markets)}'
                )
                for team_code, m in sorted(markets.items(), key=lambda x: -x[1]['volume']):
                    if m['mid'] > 0:
                        tracker.observe(m['ticker'], m['mid'], f'PRE-GAME vol={int(m["volume"])}')
        else:
            for g in live_games:
                lead = g['home_score'] - g['away_score']
                state = (
                    f'{g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]}'
                    f' | {g["detail"]}'
                )
                logger.info(f'[{now_utc}] LIVE: {state}')

                for team_code, side_lead in [
                    (g['home_kalshi'], lead),
                    (g['away_kalshi'], -lead),
                    ('TIE', 0),
                ]:
                    if not team_code or team_code not in markets:
                        continue
                    m = markets[team_code]
                    if m['mid'] <= 0:
                        continue
                    tracker.observe(m['ticker'], m['mid'], f'{state} | lead={side_lead:+d}')

        if cycle % 10 == 0:
            logger.info(f'[SUMMARY @ {now_utc}] {tracker.summary()}')

        time.sleep(poll_sec)


# ── WebSocket mode ─────────────────────────────────────────────────────────

async def run_ws_mode(date_filter: str | None):
    """Subscribe to Kalshi orderbook_delta via WebSocket for real-time price ticks."""
    import websockets

    tracker = PriceTracker()
    ws_path = '/trade-api/ws/v2'
    ws_url = f'wss://api.elections.kalshi.com{ws_path}'

    # Get target market tickers
    markets = get_ucl_markets(date_filter)
    if not markets:
        logger.warning('No open UCL markets found for WebSocket subscription')
        return

    tickers = [m['ticker'] for m in markets.values()]
    # Map ticker → team_code for later lookups
    ticker_to_code: dict[str, str] = {m['ticker']: code for code, m in markets.items()}
    # Track best bid/ask per market (reconstructed from deltas)
    orderbook: dict[str, dict] = {t: {'yes': {}, 'no': {}} for t in tickers}

    logger.info(f'WS mode: subscribing to {len(tickers)} markets')
    for t in tickers:
        logger.info(f'  {t}')

    # ESPN polling runs in background thread
    last_games: list[dict] = []

    def espn_thread():
        nonlocal last_games
        while True:
            games = get_live_ucl_games()
            last_games = games
            live = [g for g in games if g['state'] == 'STATUS_IN_PROGRESS']
            if live:
                for g in live:
                    lead = g['home_score'] - g['away_score']
                    logger.info(
                        f'  [ESPN] LIVE: {g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]}'
                        f' | {g["detail"]} | lead={lead:+d}'
                    )
            time.sleep(30)  # ESPN every 30s during WS mode

    t = threading.Thread(target=espn_thread, daemon=True)
    t.start()

    def get_game_state(team_code: str) -> str:
        for g in last_games:
            if g['state'] != 'STATUS_IN_PROGRESS':
                continue
            if g.get('home_kalshi') == team_code or g.get('away_kalshi') == team_code:
                lead = g['home_score'] - g['away_score']
                if g.get('away_kalshi') == team_code:
                    lead = -lead
                return (
                    f'{g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]}'
                    f' | {g["detail"]} | lead={lead:+d}'
                )
        return 'PRE-GAME or no live match found'

    def compute_mid(ob: dict) -> float:
        """Compute mid price from orderbook dict."""
        # yes side: prices where buyers want to buy YES
        yes_bids = sorted([float(p) for p in ob['yes'].keys() if float(ob['yes'][p]) > 0], reverse=True)
        # no side: prices where buyers want to buy NO (= equivalent YES sellers)
        no_bids = sorted([float(p) for p in ob['no'].keys() if float(ob['no'][p]) > 0], reverse=True)
        if not yes_bids and not no_bids:
            return 0.0
        best_yes_bid = yes_bids[0] if yes_bids else 0.0
        # best NO bid at price X = someone will sell YES at (1-X)
        best_yes_ask = (1.0 - no_bids[0]) if no_bids else 1.0
        if best_yes_bid > 0 and best_yes_ask < 1.0:
            return round((best_yes_bid + best_yes_ask) / 2, 3)
        elif best_yes_bid > 0:
            return best_yes_bid
        elif best_yes_ask < 1.0:
            return best_yes_ask
        return 0.0

    reconnect_delay = 5
    while True:
        try:
            headers = _make_ws_headers(ws_path)
            async with websockets.connect(ws_url, additional_headers=headers, open_timeout=15) as ws:
                logger.info(f'WS connected to {ws_url}')
                reconnect_delay = 5  # reset on success

                # Subscribe in batches of 10 (Kalshi limit)
                for i in range(0, len(tickers), 10):
                    batch = tickers[i:i+10]
                    sub = json.dumps({
                        'id': i + 1,
                        'cmd': 'subscribe',
                        'params': {
                            'channels': ['orderbook_delta'],
                            'market_tickers': batch,
                        }
                    })
                    await ws.send(sub)

                async for raw in ws:
                    msg = json.loads(raw)
                    msg_type = msg.get('type', '')

                    if msg_type == 'subscribed':
                        logger.info(f'  WS subscribed: channel={msg.get("msg", {}).get("channel")}')

                    elif msg_type == 'orderbook_snapshot':
                        body = msg.get('msg', {})
                        ticker = body.get('market_ticker', '')
                        if ticker not in orderbook:
                            continue
                        ob = orderbook[ticker]
                        for p, qty in body.get('yes_dollars_fp', []):
                            if float(qty) > 0:
                                ob['yes'][p] = qty
                            else:
                                ob['yes'].pop(p, None)
                        for p, qty in body.get('no_dollars_fp', []):
                            if float(qty) > 0:
                                ob['no'][p] = qty
                            else:
                                ob['no'].pop(p, None)
                        mid = compute_mid(ob)
                        team_code = ticker_to_code.get(ticker, ticker.split('-')[-1])
                        game_state = get_game_state(team_code)
                        tracker.observe(ticker, mid, f'WS_SNAPSHOT | {game_state}')

                    elif msg_type == 'orderbook_delta':
                        body = msg.get('msg', {})
                        ticker = body.get('market_ticker', '')
                        if ticker not in orderbook:
                            continue
                        price = body.get('price_dollars', '0')
                        delta = float(body.get('delta_fp', 0))
                        side = body.get('side', 'yes')
                        ob = orderbook[ticker]

                        if delta > 0:
                            ob[side][price] = str(float(ob[side].get(price, '0')) + delta)
                        else:
                            existing = float(ob[side].get(price, '0')) + delta
                            if existing <= 0:
                                ob[side].pop(price, None)
                            else:
                                ob[side][price] = str(existing)

                        mid = compute_mid(ob)
                        if mid > 0:
                            team_code = ticker_to_code.get(ticker, ticker.split('-')[-1])
                            game_state = get_game_state(team_code)
                            tracker.observe(ticker, mid, f'WS_DELTA | {game_state}')

        except Exception as e:
            logger.warning(f'WS error: {type(e).__name__}: {e} — reconnecting in {reconnect_delay}s')
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, 60)


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='UCL Live Monitor (Research Only)')
    parser.add_argument('--date', default=None, help='Match date filter e.g. 26MAR17')
    parser.add_argument('--interval', type=int, default=DEFAULT_POLL_SEC)
    parser.add_argument('--ws', action='store_true', help='Use WebSocket mode for real-time ticks')
    args = parser.parse_args()

    logger.info('=== UCL Live Monitor (Research Only — NOT a trading bot) ===')
    logger.info(f'Mode: {"WebSocket (real-time)" if args.ws else f"REST poll every {args.interval}s"}')
    if args.date:
        logger.info(f'Date filter: {args.date}')
    logger.info('Watching KXUCLGAME markets for live in-play price movement')
    logger.info('')

    if args.ws:
        asyncio.run(run_ws_mode(args.date))
    else:
        run_rest_mode(args.date, args.interval)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Monitor stopped')
