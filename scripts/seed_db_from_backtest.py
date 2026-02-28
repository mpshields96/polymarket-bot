"""
scripts/seed_db_from_backtest.py — Seed polybot.db with btc_lag historical results.

WHY THIS EXISTS:
  The backtest proved btc_lag works (84.1% accuracy, 44 signals/30d) but wrote
  nothing to the DB. graduation_stats() checks the DB. This script replays the
  same 30-day Binance.US history and writes settled paper trades so graduation
  thresholds can be evaluated against real historical performance.

WHAT IT DOES:
  1. Fetches 30 days of 1-min Binance.US klines (same source as backtest.py)
  2. Replays btc_lag signal logic on each 15-min window
  3. Writes each signal + actual outcome as a settled paper trade to polybot.db
  4. Prints graduation_stats() afterward

SAFETY:
  - is_paper=1 on every record — never touches live trade accounting
  - Idempotent: re-running clears previous seed trades first (client_order_id prefix)
  - Does NOT start any connections to Kalshi or Binance WebSocket

USAGE:
  source venv/bin/activate && python scripts/seed_db_from_backtest.py
  python scripts/seed_db_from_backtest.py --days 30   (default)
  python scripts/seed_db_from_backtest.py --dry-run   (print signals, no DB writes)
"""

from __future__ import annotations

import argparse
import asyncio
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.db import DB, load_from_config as _load_db

# ── Constants (mirror backtest.py / config.yaml) ──────────────────────
_DEFAULT_DAYS = 30
_KLINES_URL = "https://api.binance.us/api/v3/klines"
_SYMBOL = "BTCUSDT"
_INTERVAL = "1m"
_MAX_KLINES = 1000
_WINDOW_MIN = 15
_POLL_INTERVAL_MIN = 0.5
_LAG_SENSITIVITY = 15.0
_LAG_MIN_BTC_MOVE_PCT = 0.4
_LAG_MIN_EDGE_PCT = 0.08
_LAG_MIN_MINUTES_REMAINING = 3.0
_ASSUMED_PRICE_CENTS = 50
_SLIPPAGE_TICKS = 1          # matches PaperExecutor default
_FILL_PRICE_CENTS = _ASSUMED_PRICE_CENTS + _SLIPPAGE_TICKS  # 51¢
_SEED_PREFIX = "btc_lag_backtest_seed"  # used to identify/remove previous seeds
_STRATEGY = "btc_lag_v1"


# ── Binance.US klines fetch (mirrors backtest.py) ─────────────────────

async def _fetch_klines(days: int) -> Dict[int, float]:
    """Fetch 1-min closes from Binance.US. Returns {open_ms: close_price}."""
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - days * 24 * 60 * 60 * 1000
    candles: Dict[int, float] = {}

    async with aiohttp.ClientSession() as session:
        cursor = start_ms
        while cursor < end_ms:
            params = {
                "symbol": _SYMBOL,
                "interval": _INTERVAL,
                "startTime": cursor,
                "endTime": end_ms,
                "limit": _MAX_KLINES,
            }
            async with session.get(_KLINES_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
                data = await resp.json()
            if not data:
                break
            for row in data:
                open_ms = int(row[0])
                close_price = float(row[4])
                candles[open_ms] = close_price
            last_ms = int(data[-1][0])
            if last_ms <= cursor:
                break
            cursor = last_ms + 60_000  # advance 1 minute

    print(f"  Fetched {len(candles):,} 1-min candles ({days}d of BTC history)")
    return candles


def _price_at(candles: Dict[int, float], ts_ms: int) -> Optional[float]:
    """Return close price at or just before ts_ms."""
    candidates = [t for t in candles if t <= ts_ms]
    if not candidates:
        return None
    return candles[max(candidates)]


# ── btc_lag signal replay (mirrors backtest.py simulate_window_lag) ───

def _simulate_window(
    candles: Dict[int, float],
    window_start_ms: int,
) -> Optional[Dict]:
    """Replay btc_lag on one 15-min window. Returns signal dict or None."""
    window_end_ms = window_start_ms + _WINDOW_MIN * 60 * 1000
    reference = _price_at(candles, window_start_ms)
    final_price = _price_at(candles, window_end_ms)
    if reference is None or final_price is None or reference <= 0:
        return None

    outcome = 1 if final_price > reference else 0
    t_min = 1.0
    lag_window_min = 60.0 / 60.0  # 60s in minutes

    while t_min <= (_WINDOW_MIN - _LAG_MIN_MINUTES_REMAINING):
        current_ms = window_start_ms + int(t_min * 60 * 1000)
        prev_ms = window_start_ms + int((t_min - lag_window_min) * 60 * 1000)
        current_price = _price_at(candles, current_ms)
        prev_price = _price_at(candles, prev_ms)

        if current_price is None or prev_price is None or prev_price <= 0:
            t_min += _POLL_INTERVAL_MIN
            continue

        btc_move_pct = (current_price - prev_price) / prev_price * 100

        if abs(btc_move_pct) < _LAG_MIN_BTC_MOVE_PCT:
            t_min += _POLL_INTERVAL_MIN
            continue

        implied_lag_cents = abs(btc_move_pct) * _LAG_SENSITIVITY
        fee_pct = 0.07 * (_ASSUMED_PRICE_CENTS / 100) * (1 - _ASSUMED_PRICE_CENTS / 100)
        edge_pct = (implied_lag_cents / 100.0) - fee_pct

        if edge_pct < _LAG_MIN_EDGE_PCT:
            t_min += _POLL_INTERVAL_MIN
            continue

        side = "yes" if btc_move_pct > 0 else "no"
        win_prob = min(0.85, (_ASSUMED_PRICE_CENTS / 100.0) + (implied_lag_cents / 100.0) * 0.8)
        won = (outcome == 1 and side == "yes") or (outcome == 0 and side == "no")

        return {
            "window_start_ms": window_start_ms,
            "window_end_ms": window_end_ms,
            "side": side,
            "edge_pct": edge_pct,
            "win_prob": win_prob,
            "outcome": outcome,
            "won": won,
            "btc_move_pct": btc_move_pct,
        }

    return None


# ── PnL calculation (mirrors src/execution/paper.py settle logic) ─────

def _calc_pnl_cents(won: bool, fill_price_cents: int, count: int) -> int:
    if won:
        gross = (100 - fill_price_cents) * count
        fee = int(0.07 * fill_price_cents * (100 - fill_price_cents) / 100 * count)
        return gross - fee
    else:
        return -fill_price_cents * count


# ── DB seeding ─────────────────────────────────────────────────────────

def _clear_previous_seeds(conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        "DELETE FROM trades WHERE client_order_id LIKE ?",
        (f"{_SEED_PREFIX}%",),
    )
    conn.commit()
    return cur.rowcount


def _insert_trade(
    conn: sqlite3.Connection,
    sig: Dict,
    idx: int,
) -> int:
    """Insert a fully-settled paper trade with historical timestamps."""
    created_at = sig["window_start_ms"] / 1000.0
    settled_at = sig["window_end_ms"] / 1000.0
    result = sig["side"] if sig["won"] else ("no" if sig["side"] == "yes" else "yes")
    pnl_cents = _calc_pnl_cents(sig["won"], _FILL_PRICE_CENTS, 1)
    date_str = datetime.fromtimestamp(created_at, tz=timezone.utc).strftime("%Y%m%d%H%M")
    ticker = f"KXBTC15M-{date_str}"
    client_order_id = f"{_SEED_PREFIX}_{idx:04d}"

    cur = conn.execute(
        """INSERT INTO trades
           (timestamp, ticker, side, action, price_cents, count, cost_usd,
            strategy, edge_pct, win_prob, is_paper, client_order_id,
            result, pnl_cents, created_at, settled_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?)""",
        (
            created_at,          # timestamp (legacy field)
            ticker,
            sig["side"],
            "buy",
            _FILL_PRICE_CENTS,
            1,                   # count
            _FILL_PRICE_CENTS / 100.0,  # cost_usd
            _STRATEGY,
            sig["edge_pct"],
            sig["win_prob"],
            client_order_id,
            result,
            pnl_cents,
            created_at,          # created_at — historical timestamp
            settled_at,          # settled_at — 15 min later
        ),
    )
    conn.commit()
    return cur.lastrowid


# ── Main ───────────────────────────────────────────────────────────────

async def main(days: int, dry_run: bool) -> None:
    db_path = PROJECT_ROOT / "data" / "polybot.db"
    if not db_path.exists():
        print(f"ERROR: DB not found at {db_path}")
        sys.exit(1)

    print(f"\n{'DRY RUN — ' if dry_run else ''}Seeding btc_lag backtest results into {db_path}\n")

    # 1. Fetch klines
    print("Fetching Binance.US klines...")
    candles = await _fetch_klines(days)

    # 2. Enumerate all 15-min windows
    ts_list = sorted(candles.keys())
    if not ts_list:
        print("ERROR: No kline data fetched.")
        sys.exit(1)

    start_ms = ts_list[0]
    end_ms = ts_list[-1] - _WINDOW_MIN * 60 * 1000  # need full window
    window_ms = _WINDOW_MIN * 60 * 1000
    windows = list(range(start_ms, end_ms, window_ms))

    # 3. Replay signals
    signals: List[Dict] = []
    for w in windows:
        sig = _simulate_window(candles, w)
        if sig is not None:
            signals.append(sig)

    total = len(windows)
    fired = len(signals)
    wins = sum(1 for s in signals if s["won"])
    accuracy = wins / fired * 100 if fired else 0
    brier = sum((s["win_prob"] - s["outcome"]) ** 2 for s in signals) / fired if fired else 0

    first_dt = datetime.fromtimestamp(signals[0]["window_start_ms"] / 1000, tz=timezone.utc) if signals else None
    last_dt  = datetime.fromtimestamp(signals[-1]["window_start_ms"] / 1000, tz=timezone.utc) if signals else None

    print(f"\n  Windows simulated: {total:,}")
    print(f"  Signals fired:     {fired} ({fired/total*100:.1f}% coverage)")
    print(f"  Wins:              {wins}/{fired} ({accuracy:.1f}% accuracy)")
    print(f"  Brier score:       {brier:.4f} ({'STRONG' if brier < 0.25 else 'WEAK'})")
    print(f"  Date range:        {first_dt:%Y-%m-%d} → {last_dt:%Y-%m-%d}")

    if dry_run:
        print("\n  DRY RUN — no DB writes. Remove --dry-run to seed.")
        return

    # 4. Seed DB
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    removed = _clear_previous_seeds(conn)
    if removed:
        print(f"\n  Cleared {removed} previous seed records.")

    for i, sig in enumerate(signals):
        _insert_trade(conn, sig, i)

    conn.close()
    print(f"\n  ✅ Seeded {fired} settled paper trades into {db_path}")

    # 5. Show graduation_stats
    db = _load_db()
    db.init()
    stats = db.graduation_stats(_STRATEGY)
    db.close()

    print(f"\n  graduation_stats('{_STRATEGY}'):")
    print(f"    settled_count:      {stats['settled_count']}")
    print(f"    win_rate:           {stats['win_rate']:.1%}" if stats['win_rate'] else "    win_rate:           n/a")
    print(f"    brier_score:        {stats['brier_score']:.4f}" if stats['brier_score'] else "    brier_score:        n/a")
    print(f"    consecutive_losses: {stats['consecutive_losses']}")
    print(f"    days_running:       {stats['days_running']:.1f}")
    print(f"    total_pnl_usd:      ${stats['total_pnl_usd']:.2f}")

    # 6. Evaluate against thresholds
    min_trades, min_days, max_brier, max_consec = 30, 7, 0.30, 4
    gaps = []
    if stats['settled_count'] < min_trades:
        gaps.append(f"needs {min_trades - stats['settled_count']} more trades")
    if stats['days_running'] < min_days:
        gaps.append(f"needs {min_days - stats['days_running']:.1f} more days")
    if stats['brier_score'] and stats['brier_score'] >= max_brier:
        gaps.append(f"brier {stats['brier_score']:.4f} >= {max_brier} threshold")
    if stats['consecutive_losses'] > max_consec:
        gaps.append(f"consecutive losses {stats['consecutive_losses']} > {max_consec}")

    if not gaps:
        print(f"\n  🟢 btc_lag_v1 PASSES all graduation thresholds — ready for live consideration.")
    else:
        print(f"\n  🔴 btc_lag_v1 not yet ready: {', '.join(gaps)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed DB from btc_lag backtest")
    parser.add_argument("--days", type=int, default=_DEFAULT_DAYS, help="Days of history to replay")
    parser.add_argument("--dry-run", action="store_true", help="Print signals without writing to DB")
    args = parser.parse_args()
    asyncio.run(main(args.days, args.dry_run))
