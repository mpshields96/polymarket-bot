"""
GDP Advance Release Monitor — Research Tool (NOT a trading bot)

PURPOSE:
    Monitor Kalshi KXGDP prices around the Q1 GDP advance release at 8:30 AM ET.
    Measure how fast Kalshi reprices after a GDP surprise.
    If Kalshi takes 30-60+ seconds to adjust, there is a speed-play edge:
    detect GDP surprise, then buy the relevant KXGDP contract before repricing.

USAGE:
    python scripts/gdp_release_monitor.py
    # Run on GDP release day (Q1 2026 advance: 2026-04-30) starting at ~8:25 AM ET

OUTPUT:
    Logs to stdout and /tmp/gdp_monitor.log
    Tracks KXGDP prices every 10s for 5 minutes before and after release

RESEARCH QUESTIONS:
    1. How fast does Kalshi reprice KXGDP after a GDP surprise?
    2. Is the adjustment window > 30s? (our execution latency)
    3. In which direction does price move for positive vs negative surprise?
    4. Is the repricing proportional to magnitude of the surprise?

NEXT GDP ADVANCE RELEASE: 2026-04-30 at 08:30 ET (13:30 UTC)
DATA SOURCES:
    BEA: Manual observation at bea.gov (free, no API needed for speed-play research)
    Kalshi: /trade-api/v2/markets?series_ticker=KXGDP

MARKET STRUCTURE (as of 2026-03-17):
    8 KXGDP-26APR30-TN.N markets, T1.0-T4.5
    Most liquid/interesting: T3.0 (yes=44c) and T2.5 (yes=60c)
    Strategy: if GDP > consensus → buy T3.0 YES (44c → near 100c)
               if GDP < consensus → buy T3.0 NO (51c → near 100c)
    Speed-play window: seconds to minutes after 08:30 ET
"""

import requests
import time
import os
import sys
import logging
from datetime import datetime, timezone
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/gdp_monitor.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)

POLL_INTERVAL_SEC = 10
PRE_RELEASE_POLLS = 18   # 3 min before release
POST_RELEASE_POLLS = 30  # 5 min after release

KALSHI_GDP_SERIES = 'KXGDP'

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


def fetch_gdp_markets() -> list[dict]:
    """Fetch all open KXGDP markets with current prices."""
    auth = _get_auth()
    path = '/trade-api/v2/markets'
    url = f'https://api.elections.kalshi.com{path}?series_ticker={KALSHI_GDP_SERIES}&status=open&limit=20'
    try:
        r = requests.get(url, headers=auth.headers('GET', path), timeout=10)
        markets = r.json().get('markets', [])
        result = []
        for m in markets:
            yb = float(m.get('yes_bid_dollars') or 0)
            ya = float(m.get('yes_ask_dollars') or 0)
            mid_yes = round((yb + ya) / 2 * 100) if yb > 0 and ya > 0 else int(round(float(m.get('yes_ask_dollars', 0) or 0) * 100))
            result.append({
                'ticker': m.get('ticker', ''),
                'yes_price': mid_yes,
                'subtitle': m.get('subtitle', ''),
            })
        # Sort by threshold (T-value ascending: T1.0, T1.5, T2.0...)
        result.sort(key=lambda x: x['ticker'])
        return result
    except Exception as e:
        logger.warning('Kalshi fetch error: %s', e)
        return []


def summarize_markets(markets: list[dict]) -> str:
    """Compact price summary of all KXGDP markets."""
    if not markets:
        return 'no markets'
    parts = []
    for m in markets:
        thresh = m['ticker'].split('-T')[-1] if '-T' in m['ticker'] else '?'
        parts.append(f"T{thresh}={m['yes_price']}c")
    return ' | '.join(parts)


def main():
    logger.info('=== GDP ADVANCE RELEASE MONITOR ===')
    logger.info('Series: %s | Next release: 2026-04-30 08:30 ET (13:30 UTC)', KALSHI_GDP_SERIES)
    logger.info('Polling every %ds | %d pre-release + %d post-release polls',
                POLL_INTERVAL_SEC, PRE_RELEASE_POLLS, POST_RELEASE_POLLS)
    logger.info('')

    # Phase 1: Pre-release baseline
    logger.info('--- PHASE 1: PRE-RELEASE BASELINE ---')
    baseline_markets = None
    for i in range(PRE_RELEASE_POLLS):
        markets = fetch_gdp_markets()
        summary = summarize_markets(markets)
        logger.info('[PRE %2d/%d] %s', i + 1, PRE_RELEASE_POLLS, summary)
        if i == 0:
            baseline_markets = {m['ticker']: m['yes_price'] for m in markets}
        time.sleep(POLL_INTERVAL_SEC)

    # Phase 2: Post-release monitoring
    logger.info('')
    logger.info('--- PHASE 2: POST-RELEASE MONITORING ---')
    logger.info('GDP number should have been released. Watching for repricing...')
    first_move_detected = False
    for i in range(POST_RELEASE_POLLS):
        markets = fetch_gdp_markets()
        summary = summarize_markets(markets)

        # Detect price movements
        moves = []
        if baseline_markets:
            for m in markets:
                baseline = baseline_markets.get(m['ticker'], m['yes_price'])
                delta = m['yes_price'] - baseline
                if abs(delta) >= 3:  # 3c+ move is significant
                    moves.append(f"{m['ticker'].split('-T')[-1]}: {'+' if delta >= 0 else ''}{delta}c")

        move_str = f" | MOVES: {', '.join(moves)}" if moves else ''
        if moves and not first_move_detected:
            logger.info('[POST %2d/%d] %s%s  ← FIRST PRICE MOVEMENT DETECTED', i + 1, POST_RELEASE_POLLS, summary, move_str)
            first_move_detected = True
        else:
            logger.info('[POST %2d/%d] %s%s', i + 1, POST_RELEASE_POLLS, summary, move_str)
        time.sleep(POLL_INTERVAL_SEC)

    logger.info('')
    logger.info('=== MONITORING COMPLETE ===')
    if baseline_markets:
        final_markets = fetch_gdp_markets()
        logger.info('Final deltas from baseline:')
        for m in final_markets:
            baseline = baseline_markets.get(m['ticker'], m['yes_price'])
            delta = m['yes_price'] - baseline
            thresh = m['ticker'].split('-T')[-1] if '-T' in m['ticker'] else '?'
            logger.info('  T%s: baseline=%dc → final=%dc | delta=%s%dc',
                       thresh, baseline, m['yes_price'], '+' if delta >= 0 else '', delta)
    logger.info('')
    logger.info('NEXT STEPS:')
    logger.info('  1. Note the actual GDP print vs consensus (check Bloomberg/CNBC)')
    logger.info('  2. Compare repricing speed to CPI monitor results')
    logger.info('  3. If window > 30s: GDP speed-play is viable')
    logger.info('  4. Best entry point: T3.0 if consensus ~ 2.5-3.0%%')


if __name__ == '__main__':
    main()
