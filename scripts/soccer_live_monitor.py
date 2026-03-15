"""
Soccer Live Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Generic in-play monitor for any Kalshi soccer game-winner series.
    Tests whether markets hit 90c+ during live games, logs price movement.

USAGE:
    # EPL (Brentford vs Wolves, March 16):
    python scripts/soccer_live_monitor.py --series KXEPLGAME --date 26MAR16

    # UCL (March 17):
    python scripts/soccer_live_monitor.py --series KXUCLGAME --date 26MAR17 --ws

    # La Liga:
    python scripts/soccer_live_monitor.py --series KXLALIGAGAME

SUPPORTED SERIES (all confirmed can_close_early=True, settlement_timer=30s):
    KXUCLGAME    — UEFA Champions League  (100K - 5M vol/game)
    KXEPLGAME    — English Premier League (500K - 1.2M vol/game)
    KXLALIGAGAME — La Liga                (100K - 728K vol/game)
    KXSERIEAGAME — Serie A                (100K - 512K vol/game)

RESEARCH QUESTIONS:
    1. Do market prices update live during games?
    2. At what score/game state does a team reach 90c+?
    3. How long does a market stay above 90c before early settlement?
    4. What is the false-positive rate (market reaches 90c but still loses)?

EVIDENCE SO FAR (as of 2026-03-15):
    UCL Feb 25: ATA 45c→99c, RMA 59c→99c (confirmed live movement first legs)
    UCL Mar 10: All settled at 99c (2nd legs already near-certain pre-game)
    EPL Mar 15: MUN 56c→99c (confirmed: Man Utd won TODAY, live price movement)
    EPL Mar 15: LFC 75c→lost (Liverpool was heavily favored but drew vs Tottenham)

DO NOT USE FOR LIVE TRADING. Research only.
Log file: /tmp/soccer_monitor_<series>.log
"""

import argparse
import asyncio
import base64
import csv
import json
import os
import sys
import time
import logging
import requests
import threading
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SNIPER_THRESHOLD = 0.90
DEFAULT_POLL_SEC = 60

# ── ESPN configurations per league ─────────────────────────────────────────

ESPN_CONFIGS = {
    'KXUCLGAME': {
        'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/UEFA.CHAMPIONS/scoreboard',
        'name': 'UEFA Champions League',
    },
    'KXEPLGAME': {
        'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard',
        'name': 'English Premier League',
    },
    'KXLALIGAGAME': {
        'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/scoreboard',
        'name': 'La Liga',
    },
    'KXSERIEAGAME': {
        'url': 'https://site.api.espn.com/apis/site/v2/sports/soccer/ita.1/scoreboard',
        'name': 'Serie A',
    },
}

# Comprehensive team name → Kalshi ticker code mapping
# Covers UCL, EPL, La Liga, Serie A, Bundesliga
TEAM_MAP: dict[str, str] = {
    # UCL / EPL
    'MANCHESTER CITY': 'MCI', 'MAN CITY': 'MCI', 'MAN. CITY': 'MCI',
    'MANCHESTER UNITED': 'MUN', 'MAN UNITED': 'MUN', 'MAN UTD': 'MUN',
    'ARSENAL': 'ARS',
    'BAYER LEVERKUSEN': 'LEV', 'LEVERKUSEN': 'LEV',
    'CHELSEA': 'CFC',
    'PARIS SAINT-GERMAIN': 'PSG', 'PARIS SG': 'PSG',
    'REAL MADRID': 'RMA',
    'BARCELONA': 'BAR', 'FC BARCELONA': 'BAR',
    'ATLETICO DE MADRID': 'ATM', 'ATLETICO MADRID': 'ATM', 'ATL. MADRID': 'ATM',
    'LIVERPOOL': 'LFC', 'LIVERPOOL FC': 'LFC',
    'TOTTENHAM HOTSPUR': 'TOT', 'TOTTENHAM': 'TOT',
    'NEWCASTLE UNITED': 'NEW', 'NEWCASTLE': 'NEW',
    'ASTON VILLA': 'AVL',
    'BRENTFORD': 'BRE',
    'WOLVERHAMPTON WANDERERS': 'WOL', 'WOLVERHAMPTON': 'WOL', 'WOLVES': 'WOL',
    'BRIGHTON & HOVE ALBION': 'BHA', 'BRIGHTON': 'BHA',
    'WEST HAM UNITED': 'WHU', 'WEST HAM': 'WHU',
    'FULHAM': 'FUL',
    'EVERTON': 'EVE',
    'NOTTINGHAM FOREST': 'NFO', 'NOTTM FOREST': 'NFO',
    'CRYSTAL PALACE': 'CRY',
    'BOURNEMOUTH': 'BOU', 'AFC BOURNEMOUTH': 'BOU',
    'IPSWICH TOWN': 'IPS', 'IPSWICH': 'IPS',
    'LEICESTER CITY': 'LEI', 'LEICESTER': 'LEI',
    'SOUTHAMPTON': 'SOU',
    'SUNDERLAND': 'SUN',
    'LEEDS UNITED': 'LEE', 'LEEDS': 'LEE',
    'BURNLEY': 'BUR',
    # UCL
    'SPORTING CP': 'SPO', 'SPORTING': 'SPO',
    'BODO/GLIMT': 'BOG', 'FK BODO': 'BOG',
    'BAYERN MUNICH': 'BMU', 'FC BAYERN MÜNCHEN': 'BMU', 'BAYERN': 'BMU',
    'ATALANTA': 'ATA', 'ATALANTA BC': 'ATA',
    'GALATASARAY': 'GAL',
    'BORUSSIA DORTMUND': 'DOR',
    'AC MILAN': 'MIL',
    'INTERNAZIONALE': 'INT', 'INTER MILAN': 'INT',
    'BENFICA': 'BEN', 'SL BENFICA': 'BEN',
    'JUVENTUS': 'JUV',
    # La Liga
    'SEVILLA': 'SEV', 'SEVILLA FC': 'SEV',
    'VILLARREAL': 'VIL', 'VILLARREAL CF': 'VIL',
    'BETIS': 'BET', 'REAL BETIS': 'BET',
    'ATHLETIC BILBAO': 'ATH',
    'OSASUNA': 'OSA', 'CA OSASUNA': 'OSA',
    'GIRONA': 'GIR', 'GIRONA FC': 'GIR',
    'GETAFE': 'GET', 'GETAFE CF': 'GET',
    'RAYO VALLECANO': 'RAY',
    'CELTA VIGO': 'CEL',
    'ALAVES': 'ALA',
    'MALLORCA': 'MLL',
    'LAS PALMAS': 'LPM',
    'ESPANOL': 'ESP',
    'REAL SOCIEDAD': 'RSO',
    'VALENCIA': 'VAL', 'VALENCIA CF': 'VAL',
    'REAL VALLADOLID': 'VLD',
    'LEGANES': 'LEG',
    # Serie A
    'NAPOLI': 'NAP', 'SSC NAPOLI': 'NAP',
    'LAZIO': 'LAZ', 'SS LAZIO': 'LAZ',
    'ROMA': 'ROM', 'AS ROMA': 'ROM',
    'FIORENTINA': 'FIO', 'ACF FIORENTINA': 'FIO',
    'TORINO': 'TOR', 'TORINO FC': 'TOR',
    'UDINESE': 'UDI',
    'CAGLIARI': 'CAG',
    'LECCE': 'LEC', 'US LECCE': 'LEC',
    'VERONA': 'VER', 'HELLAS VERONA': 'VER',
    'PARMA': 'PAR', 'PARMA CALCIO': 'PAR',
    'COMO': 'COM', 'COMO 1907': 'COM',
    'VENEZIA': 'VEN', 'VENEZIA FC': 'VEN',
    'EMPOLI': 'EMP', 'EMPOLI FC': 'EMP',
    'MONZA': 'MNZ', 'AC MONZA': 'MNZ',
    'BOLOGNA': 'BOL', 'BOLOGNA FC': 'BOL',
    'GENOA': 'GEN', 'GENOA CFC': 'GEN',
}


# ── Auth ───────────────────────────────────────────────────────────────────

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


def _lookup_team(name_upper: str) -> str | None:
    if name_upper in TEAM_MAP:
        return TEAM_MAP[name_upper]
    for key, code in TEAM_MAP.items():
        if key in name_upper or name_upper in key:
            return code
    return None


# ── ESPN ───────────────────────────────────────────────────────────────────

def get_live_games(espn_url: str) -> list[dict]:
    try:
        r = requests.get(espn_url, timeout=10)
        r.raise_for_status()
        events = r.json().get('events', [])
        games = []
        for e in events:
            comp = e.get('competitions', [{}])[0]
            teams = comp.get('competitors', [])
            status = comp.get('status', {})
            home_name = away_name = 'UNK'
            home_score = away_score = 0
            home_k = away_k = None
            for t in teams:
                name = t.get('team', {}).get('displayName', '') or ''
                score = int(t.get('score', 0) or 0)
                k = _lookup_team(name.upper())
                if t.get('homeAway') == 'home':
                    home_name, home_score, home_k = name, score, k
                else:
                    away_name, away_score, away_k = name, score, k
            games.append({
                'home_name': home_name, 'home_score': home_score, 'home_k': home_k,
                'away_name': away_name, 'away_score': away_score, 'away_k': away_k,
                'state': status.get('type', {}).get('name', ''),
                'detail': status.get('type', {}).get('detail', ''),
            })
        return games
    except Exception as e:
        logger.warning(f'ESPN error: {e}')
        return []


# ── Kalshi ─────────────────────────────────────────────────────────────────

def get_markets(series_ticker: str, date_filter: str | None) -> dict[str, dict]:
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    url = f'https://api.elections.kalshi.com{path}?series_ticker={series_ticker}&status=open&limit=100'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        r.raise_for_status()
        result = {}
        for m in r.json().get('markets', []):
            ticker = m.get('ticker', '')
            if date_filter and date_filter.upper() not in ticker.upper():
                continue
            parts = ticker.split('-')
            if len(parts) < 3:
                continue
            code = parts[-1].upper()
            yb = float(m.get('yes_bid_dollars') or 0)
            ya = float(m.get('yes_ask_dollars') or 0)
            last = float(m.get('last_price_dollars') or 0)
            result[code] = {
                'ticker': ticker, 'yes_bid': yb, 'yes_ask': ya, 'last': last,
                'mid': round((yb + ya) / 2, 3) if (yb + ya) > 0 else last,
                'volume': float(m.get('volume_fp') or 0),
            }
        return result
    except Exception as e:
        logger.warning(f'Kalshi fetch error: {e}')
        return {}


# ── Price tracker ──────────────────────────────────────────────────────────

class PriceTracker:
    def __init__(self, label: str, csv_path: str | None = None):
        self.label = label
        self._last: dict[str, float] = {}
        self._crossings: dict[str, tuple[str, float, float]] = {}  # ticker → (iso_time, price, epoch)
        self._ever_moved: dict[str, bool] = {}
        self._lock = threading.Lock()
        self._csv_path = csv_path
        self._csv_file = None
        self._csv_writer = None
        if csv_path:
            self._csv_file = open(csv_path, 'w', newline='', buffering=1)
            self._csv_writer = csv.writer(self._csv_file)
            self._csv_writer.writerow([
                'timestamp_utc', 'ticker', 'mid_cents', 'change_cents',
                'above_90c', 'seconds_above_90c', 'game_state',
            ])

    def _write_csv(self, ticker: str, mid: float, change: float, game_state: str):
        if not self._csv_writer:
            return
        now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        above = mid >= SNIPER_THRESHOLD
        secs_above = 0.0
        if above and ticker in self._crossings:
            secs_above = round(time.time() - self._crossings[ticker][2], 1)
        self._csv_writer.writerow([
            now_iso,
            ticker,
            round(mid * 100, 1),
            round(change * 100, 1),
            1 if above else 0,
            secs_above,
            game_state,
        ])

    def observe(self, ticker: str, mid: float, state: str):
        with self._lock:
            now = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
            prev = self._last.get(ticker)
            if ticker not in self._ever_moved:
                self._ever_moved[ticker] = False
                logger.info(f'  [INIT] {ticker} | {int(mid*100)}c')
            change = (mid - prev) if prev is not None else 0
            moved = abs(change) >= 0.01
            if moved:
                self._ever_moved[ticker] = True
                d = '▲' if change > 0 else '▼'
                logger.info(f'  [MOVE] {ticker} | {int(mid*100)}c {d}{int(abs(change)*100)}c | {state}')
            if mid >= SNIPER_THRESHOLD:
                if ticker not in self._crossings:
                    self._crossings[ticker] = (now, mid, time.time())
                    logger.warning(f'  *** 90c+ CROSSING: {ticker} {int(mid*100)}c @ {now} | {state} ***')
                elif moved:
                    logger.warning(f'  *** STILL 90c+: {ticker} {int(mid*100)}c | {state} ***')
            elif ticker in self._crossings:
                crossed_at, crossed_price, crossed_epoch = self._crossings.pop(ticker)
                duration = round(time.time() - crossed_epoch, 0)
                logger.info(f'  [DROPPED] {ticker} → {int(mid*100)}c | was 90c+ for {int(duration)}s since {crossed_at} | {state}')
            self._write_csv(ticker, mid, change, state)
            self._last[ticker] = mid

    def summary(self) -> str:
        movers = sum(1 for v in self._ever_moved.values() if v)
        active = list(self._crossings.keys())
        return f'[{self.label}] Movers: {movers} | Active 90c+: {len(active)}' + (f' → {", ".join(active)}' if active else '')


# ── REST mode ──────────────────────────────────────────────────────────────

def run_rest(series: str, espn_url: str, date_filter: str | None, poll_sec: int, csv_path: str | None = None):
    tracker = PriceTracker(series, csv_path=csv_path)
    cycle = 0
    while True:
        cycle += 1
        now = datetime.now(timezone.utc).strftime('%H:%M UTC')
        games = get_live_games(espn_url)
        markets = get_markets(series, date_filter)
        live = [g for g in games if g['state'] == 'STATUS_IN_PROGRESS']
        if not live:
            if cycle % 5 == 1:
                logger.info(f'[{now}] No live games | markets={len(markets)}')
                for code, m in sorted(markets.items(), key=lambda x: -x[1]['volume']):
                    if m['mid'] > 0:
                        tracker.observe(m['ticker'], m['mid'], f'PRE-GAME vol={int(m["volume"])}')
        for g in live:
            lead = g['home_score'] - g['away_score']
            state = f'{g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]} | {g["detail"]}'
            logger.info(f'[{now}] LIVE: {state}')
            for code, side_lead in [(g['home_k'], lead), (g['away_k'], -lead), ('TIE', 0)]:
                if not code or code not in markets:
                    continue
                m = markets[code]
                if m['mid'] > 0:
                    tracker.observe(m['ticker'], m['mid'], f'{state} | lead={side_lead:+d}')
        if cycle % 10 == 0:
            logger.info(tracker.summary())
        time.sleep(poll_sec)


# ── WebSocket mode ─────────────────────────────────────────────────────────

async def run_ws(series: str, espn_url: str, date_filter: str | None, csv_path: str | None = None):
    import websockets
    tracker = PriceTracker(series, csv_path=csv_path)
    ws_path = '/trade-api/ws/v2'
    ws_url = f'wss://api.elections.kalshi.com{ws_path}'
    markets = get_markets(series, date_filter)
    if not markets:
        logger.warning(f'No open {series} markets')
        return
    tickers = [m['ticker'] for m in markets.values()]
    t2c: dict[str, str] = {m['ticker']: code for code, m in markets.items()}
    orderbook: dict[str, dict] = {t: {'yes': {}, 'no': {}} for t in tickers}
    last_games: list[dict] = []

    def espn_bg():
        nonlocal last_games
        while True:
            last_games = get_live_games(espn_url)
            live = [g for g in last_games if g['state'] == 'STATUS_IN_PROGRESS']
            for g in live:
                lead = g['home_score'] - g['away_score']
                logger.info(f'  [ESPN] {g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]} | {g["detail"]}')
            time.sleep(30)

    threading.Thread(target=espn_bg, daemon=True).start()

    def get_state(code: str) -> str:
        for g in last_games:
            if g['state'] != 'STATUS_IN_PROGRESS':
                continue
            if g.get('home_k') == code or g.get('away_k') == code:
                lead = g['home_score'] - g['away_score']
                if g.get('away_k') == code:
                    lead = -lead
                return f'{g["home_name"]} {g["home_score"]}-{g["away_score"]} {g["away_name"]} | {g["detail"]} | lead={lead:+d}'
        return 'PRE-GAME'

    def compute_mid(ob: dict) -> float:
        yes_bids = sorted([float(p) for p, q in ob['yes'].items() if float(q) > 0], reverse=True)
        no_bids = sorted([float(p) for p, q in ob['no'].items() if float(q) > 0], reverse=True)
        best_bid = yes_bids[0] if yes_bids else 0.0
        best_ask = (1.0 - no_bids[0]) if no_bids else 1.0
        if best_bid > 0 and best_ask < 1.0:
            return round((best_bid + best_ask) / 2, 3)
        return best_bid or (best_ask if best_ask < 1.0 else 0.0)

    delay = 5
    while True:
        try:
            hdrs = _make_ws_headers(ws_path)
            async with websockets.connect(ws_url, additional_headers=hdrs, open_timeout=15) as ws:
                logger.info(f'WS connected: {series}')
                delay = 5
                for i in range(0, len(tickers), 10):
                    await ws.send(json.dumps({'id': i+1, 'cmd': 'subscribe', 'params': {
                        'channels': ['orderbook_delta'], 'market_tickers': tickers[i:i+10]
                    }}))
                async for raw in ws:
                    msg = json.loads(raw)
                    mtype = msg.get('type', '')
                    if mtype == 'orderbook_snapshot':
                        body = msg['msg']
                        ticker = body.get('market_ticker', '')
                        if ticker not in orderbook:
                            continue
                        ob = orderbook[ticker]
                        for p, q in body.get('yes_dollars_fp', []):
                            ob['yes'][p] = q if float(q) > 0 else ob['yes'].pop(p, None) or '0'
                        for p, q in body.get('no_dollars_fp', []):
                            ob['no'][p] = q if float(q) > 0 else ob['no'].pop(p, None) or '0'
                        mid = compute_mid(ob)
                        code = t2c.get(ticker, ticker.split('-')[-1])
                        tracker.observe(ticker, mid, f'SNAPSHOT | {get_state(code)}')
                    elif mtype == 'orderbook_delta':
                        body = msg['msg']
                        ticker = body.get('market_ticker', '')
                        if ticker not in orderbook:
                            continue
                        p = body.get('price_dollars', '0')
                        delta = float(body.get('delta_fp', 0))
                        side = body.get('side', 'yes')
                        ob = orderbook[ticker]
                        existing = float(ob[side].get(p, '0')) + delta
                        if existing > 0:
                            ob[side][p] = str(existing)
                        else:
                            ob[side].pop(p, None)
                        mid = compute_mid(ob)
                        if mid > 0:
                            code = t2c.get(ticker, ticker.split('-')[-1])
                            tracker.observe(ticker, mid, f'DELTA | {get_state(code)}')
        except Exception as e:
            logger.warning(f'WS error: {e} — reconnect in {delay}s')
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)


# ── Main ───────────────────────────────────────────────────────────────────

def setup_logging(series: str):
    log_file = f'/tmp/soccer_monitor_{series}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(message)s',
        datefmt='%H:%M:%S UTC',
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file)],
    )
    return log_file


def main():
    parser = argparse.ArgumentParser(description='Soccer Live Monitor (Research Only)')
    parser.add_argument('--series', default='KXUCLGAME', choices=list(ESPN_CONFIGS.keys()),
                        help='Kalshi series ticker (default: KXUCLGAME)')
    parser.add_argument('--date', default=None, help='Date filter e.g. 26MAR16')
    parser.add_argument('--interval', type=int, default=DEFAULT_POLL_SEC)
    parser.add_argument('--ws', action='store_true', help='WebSocket mode (real-time)')
    args = parser.parse_args()

    log_file = setup_logging(args.series)
    global logger
    logger = logging.getLogger(__name__)

    cfg = ESPN_CONFIGS[args.series]
    date_tag = args.date or 'nodate'
    csv_path = f'/tmp/soccer_sniper_data_{args.series}_{date_tag}.csv'

    logger.info(f'=== Soccer Monitor: {cfg["name"]} ({args.series}) — Research Only ===')
    logger.info(f'Mode: {"WebSocket" if args.ws else f"REST poll {args.interval}s"} | date={args.date}')
    logger.info(f'Log: {log_file}')
    logger.info(f'CSV: {csv_path}')
    logger.info('')

    if args.ws:
        asyncio.run(run_ws(args.series, cfg['url'], args.date, csv_path=csv_path))
    else:
        run_rest(args.series, cfg['url'], args.date, args.interval, csv_path=csv_path)


logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Monitor stopped')
