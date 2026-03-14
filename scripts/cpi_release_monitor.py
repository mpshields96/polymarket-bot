"""
CPI Release Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Monitor whether Kalshi KXFEDDECISION prices lag behind the market
    after a CPI release at 8:30 AM ET. If Kalshi takes 30-60+ seconds to
    adjust, there is a speed-play edge: detect CPI surprise, then buy the
    relevant KXFEDDECISION contract before Kalshi fully reprices.

USAGE:
    python scripts/cpi_release_monitor.py
    # Run this on CPI release day (next: 2026-04-10) starting at ~8:28 AM ET

OUTPUT:
    Logs to stdout and /tmp/cpi_monitor.log
    Tracks Kalshi prices every 10s for 5 minutes before and after release

RESEARCH QUESTIONS:
    1. How fast does Kalshi reprice KXFEDDECISION after a CPI surprise?
    2. Is the adjustment window > 30s? (our execution latency)
    3. In which direction does price move for a positive vs negative surprise?
    4. Is the repricing proportional to the magnitude of the surprise?

NEXT CPI RELEASE: 2026-04-10 at 08:30 ET (13:30 UTC)
DATA SOURCES:
    BLS API: api.bls.gov/publicAPI/v2/timeseries/data/ (free, no key needed for limited use)
    Kalshi: /trade-api/v2/markets?series_ticker=KXFEDDECISION

FINDINGS SO FAR:
    (none yet — run on April 10, 2026)
"""

import requests
import time
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional

# ── Setup ──────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S UTC',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/cpi_monitor.log'),
    ]
)
logger = logging.getLogger(__name__)

# ── Config ─────────────────────────────────────────────────────────────────
POLL_INTERVAL_SEC = 10          # poll every 10s (matches bot's polling rate)
PRE_RELEASE_POLLS = 18          # 3 min before release (baseline)
POST_RELEASE_POLLS = 30         # 5 min after release (watch adjustment)

BLS_CPI_SERIES = 'CUSR0000SA0'  # CPI All Items, Seasonally Adjusted (official headline)
BLS_API_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'

KALSHI_FEDMEETING_SERIES = 'KXFEDDECISION'


# ── BLS CPI fetcher ─────────────────────────────────────────────────────────

def fetch_latest_cpi() -> Optional[dict]:
    """
    Fetch the most recent CPI reading from BLS public API.
    Returns dict with 'value' (float), 'period' (e.g. 'M03'), 'year' (str).
    Returns None if API call fails or no data.

    BLS public API is free with no key for up to 25 series/day at 500 calls/day.
    """
    try:
        payload = {
            "seriesid": [BLS_CPI_SERIES],
            "startyear": str(datetime.now(timezone.utc).year),
            "endyear": str(datetime.now(timezone.utc).year),
        }
        r = requests.post(BLS_API_URL, json=payload, timeout=10)
        data = r.json()
        if data.get('status') != 'REQUEST_SUCCEEDED':
            logger.warning('BLS API error: %s', data.get('message', 'unknown'))
            return None
        series = data.get('Results', {}).get('series', [{}])[0]
        records = series.get('data', [])
        if not records:
            return None
        latest = records[0]  # most recent is first
        return {
            'value': float(latest.get('value', 0)),
            'period': latest.get('period', '?'),
            'year': latest.get('year', '?'),
            'footnotes': [f.get('text', '') for f in latest.get('footnotes', [])],
        }
    except Exception as e:
        logger.warning('BLS fetch error: %s', e)
        return None


# ── Kalshi KXFEDDECISION fetcher ────────────────────────────────────────────

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


def fetch_fomc_markets() -> list[dict]:
    """
    Fetch all open KXFEDDECISION markets with current prices.
    Returns list sorted by close_time (nearest meeting first).
    """
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    url = f'https://api.elections.kalshi.com{path}?series_ticker={KALSHI_FEDMEETING_SERIES}&status=open&limit=50'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        markets = r.json().get('markets', [])
        result = []
        for m in markets:
            yb = float(m.get('yes_bid_dollars') or 0)
            ya = float(m.get('yes_ask_dollars') or 0)
            vol = float(m.get('volume_fp') or 0)
            if yb <= 0 and ya <= 0:
                continue
            result.append({
                'ticker': m.get('ticker', ''),
                'subtitle': m.get('subtitle', m.get('title', ''))[:50],
                'yes_bid': yb,
                'yes_ask': ya,
                'volume': vol,
                'close_time': m.get('close_time', ''),
            })
        result.sort(key=lambda x: x.get('close_time', ''))
        return result
    except Exception as e:
        logger.warning('Kalshi fetch error: %s', e)
        return []


# ── Analysis helpers ────────────────────────────────────────────────────────

def summarize_markets(markets: list[dict]) -> str:
    """One-line summary of the 3 nearest KXFEDDECISION markets."""
    if not markets:
        return 'no markets'
    parts = []
    for m in markets[:3]:
        bid_pct = int(m['yes_bid'] * 100)
        ask_pct = int(m['yes_ask'] * 100)
        label = m['subtitle'][:20].strip()
        parts.append(f"{label}: {bid_pct}-{ask_pct}c")
    return ' | '.join(parts)


def detect_price_change(before: list[dict], after: list[dict]) -> list[str]:
    """
    Compare two snapshots of FOMC markets, return list of meaningful changes.
    'Meaningful' = bid or ask moved by >= 2c.
    """
    changes = []
    before_by_ticker = {m['ticker']: m for m in before}
    for m in after:
        ticker = m['ticker']
        if ticker not in before_by_ticker:
            continue
        prev = before_by_ticker[ticker]
        bid_delta = round(m['yes_bid'] - prev['yes_bid'], 4)
        ask_delta = round(m['yes_ask'] - prev['yes_ask'], 4)
        if abs(bid_delta) >= 0.02 or abs(ask_delta) >= 0.02:
            changes.append(
                f"{m['subtitle'][:25]}: bid {prev['yes_bid']:.2f}->{m['yes_bid']:.2f} "
                f"ask {prev['yes_ask']:.2f}->{m['yes_ask']:.2f}"
            )
    return changes


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    logger.info('=== CPI Release Monitor (Research Only) ===')
    logger.info('CPI series: %s | Poll interval: %ds', BLS_CPI_SERIES, POLL_INTERVAL_SEC)
    logger.info('NOT a trading bot — price monitoring only')
    logger.info('')

    # ── Phase 1: Pre-release baseline ──────────────────────────────────────
    logger.info('PHASE 1: Establishing baseline (3 min pre-release polls)')

    cpi_baseline: Optional[dict] = None
    price_baseline: Optional[list[dict]] = None
    price_history: list[tuple[str, list[dict]]] = []

    for i in range(PRE_RELEASE_POLLS):
        now_utc = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')

        cpi = fetch_latest_cpi()
        markets = fetch_fomc_markets()

        if cpi and cpi_baseline is None:
            cpi_baseline = cpi
            logger.info('[BASELINE CPI] %s %s: %.3f', cpi['year'], cpi['period'], cpi['value'])

        if markets and price_baseline is None:
            price_baseline = markets
            logger.info('[BASELINE FOMC] %s', summarize_markets(markets))

        price_history.append((now_utc, markets))
        logger.info('[%s] pre-release check %d/%d | FOMC: %s',
                    now_utc, i + 1, PRE_RELEASE_POLLS, summarize_markets(markets))

        time.sleep(POLL_INTERVAL_SEC)

    # ── Phase 2: Post-release monitoring ───────────────────────────────────
    logger.info('')
    logger.info('PHASE 2: Post-release monitoring (5 min)')
    logger.info('Watching for CPI data update AND Kalshi price movement...')

    release_detected = False
    new_cpi: Optional[dict] = None
    first_change_elapsed: Optional[float] = None
    release_time: Optional[float] = None

    for i in range(POST_RELEASE_POLLS):
        now_utc = datetime.now(timezone.utc).strftime('%H:%M:%S UTC')
        now_ts = time.time()

        cpi = fetch_latest_cpi()
        markets = fetch_fomc_markets()

        # Detect CPI release: new data appeared (period changed or value changed)
        if cpi and cpi_baseline and not release_detected:
            if cpi['period'] != cpi_baseline['period'] or cpi['value'] != cpi_baseline['value']:
                release_detected = True
                release_time = now_ts
                new_cpi = cpi
                surprise = cpi['value'] - cpi_baseline['value']
                logger.warning(
                    '*** CPI RELEASED at %s: %s %s = %.3f (prev=%.3f, surprise=%+.3f) ***',
                    now_utc, cpi['year'], cpi['period'], cpi['value'],
                    cpi_baseline['value'], surprise,
                )

        # Detect Kalshi price changes
        if price_baseline and markets:
            changes = detect_price_change(price_baseline, markets)
            if changes:
                if not release_detected:
                    logger.warning('[%s] FOMC prices moved BEFORE CPI detected: %s',
                                   now_utc, ' | '.join(changes))
                else:
                    elapsed = now_ts - release_time if release_time else 0
                    if first_change_elapsed is None:
                        first_change_elapsed = elapsed
                        logger.warning(
                            '*** KALSHI REPRICED at %s (+%.0fs after release) ***',
                            now_utc, elapsed,
                        )
                    logger.info('[+%.0fs] Price changes: %s', elapsed, ' | '.join(changes))
                price_baseline = markets  # update baseline to catch incremental moves
            else:
                elapsed_str = ''
                if release_detected and release_time:
                    elapsed_str = f' +{now_ts - release_time:.0f}s'
                logger.info('[%s]%s check %d/%d | FOMC: %s',
                            now_utc, elapsed_str, i + 1, POST_RELEASE_POLLS,
                            summarize_markets(markets))

        time.sleep(POLL_INTERVAL_SEC)

    # ── Summary ────────────────────────────────────────────────────────────
    logger.info('')
    logger.info('=== SUMMARY ===')
    if not release_detected:
        logger.warning('CPI release NOT detected during monitoring window.')
        logger.warning('Possible: BLS API delay, or run script closer to 8:30 AM ET.')
    else:
        logger.info('CPI: %s %s = %.3f (prev=%.3f)',
                    new_cpi['year'], new_cpi['period'],
                    new_cpi['value'], cpi_baseline['value'])
        if first_change_elapsed is not None:
            logger.info('Kalshi repriced +%.0f seconds after CPI release', first_change_elapsed)
            if first_change_elapsed > 30:
                logger.warning('*** EDGE WINDOW: %.0fs > 30s execution threshold ***',
                               first_change_elapsed)
                logger.warning('*** This suggests a tradeable speed-play edge exists. ***')
            else:
                logger.info('No edge window: Kalshi repriced in < 30s (too fast for us)')
        else:
            logger.info('Kalshi prices did NOT move during monitoring window.')
            logger.info('Possible: CPI was in-line with expectations (no surprise).')

    logger.info('=== MONITOR COMPLETE ===')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Monitor stopped')
