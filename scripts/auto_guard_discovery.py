"""
Auto-guard discovery for expiry_sniper_v1.

JOB:    Scan live sniper bet history, identify negative-EV price/side/asset
        buckets, write new guards to data/auto_guards.json.

RUNS:   At session start (via polybot-init), or manually:
            python3 scripts/auto_guard_discovery.py
            python3 scripts/auto_guard_discovery.py --dry-run   # print only

OUTPUT: data/auto_guards.json — loaded by live.py at next restart.

CRITERIA for auto-guard:
    1. n_bets >= MIN_BETS (default 3) in the bucket
    2. win_rate < break_even_wr (fee-adjusted)
    3. total_loss_usd < -MIN_LOSS_USD (default 5 USD)
    4. Not already covered by a hardcoded IL guard in live.py

BREAK-EVEN FORMULA (Kalshi taker fee = 7%):
    For a YES bet at P cents:
        gross_win  = (100 - P) cents
        fee        = 0.07 * P/100 * (100-P)/100 * 100 cents  (per contract)
        net_win    = gross_win - fee_per_contract (approx, using 10-contract baseline)
        break_even = loss / (loss + net_win)  per contract

    Simplified conservative formula used here:
        break_even_wr = P / (P + (100 - P) * (1 - 0.07 * P / 100))
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"
OUTPUT_PATH = PROJ / "data" / "auto_guards.json"

# Thresholds for auto-guard trigger
MIN_BETS = 3            # minimum sample size
MIN_LOSS_USD = 5.0      # minimum total loss to trigger guard (USD)
KALSHI_FEE_RATE = 0.07  # 7% taker fee

# Ticker prefix map — maps DB ticker prefix to guard pattern
# e.g. "KXBTC15M-26MAR..." → prefix "KXBTC"
_TICKER_PREFIXES = ["KXBTC", "KXETH", "KXSOL", "KXXRP"]

# Hardcoded guards already in live.py — skip these to avoid duplicates.
# Format: (ticker_contains_or_None, price_cents, side)
# None ticker = global (any asset)
_EXISTING_HARDCODED_GUARDS: set[tuple] = {
    # IL-5: 99c/1c global
    (None, 99, "yes"), (None, 99, "no"), (None, 1, "yes"), (None, 1, "no"),
    # IL-10: 96c global
    (None, 96, "yes"), (None, 96, "no"),
    # IL-11: 98c NO global
    (None, 98, "no"),
    # IL-10A
    ("KXXRP", 94, "yes"),
    # IL-20
    ("KXXRP", 95, "yes"),
    # IL-10B
    ("KXXRP", 97, "yes"),
    # IL-10C
    ("KXSOL", 94, "yes"),
    # IL-19
    ("KXSOL", 97, "yes"),
    # IL-21
    ("KXXRP", 92, "no"),
    # IL-22
    ("KXSOL", 92, "no"),
    # IL-23
    ("KXXRP", 98, "yes"),
    # IL-24
    ("KXSOL", 95, "no"),
    # IL-25
    ("KXXRP", 97, "no"),
    # IL-26
    ("KXXRP", 98, "no"),
    # IL-27
    ("KXSOL", 96, "yes"),
    # IL-28
    ("KXXRP", 94, "no"),
    # IL-29
    ("KXBTC", 88, "yes"),
    # IL-30
    ("KXETH", 93, "yes"),
    # IL-31
    ("KXXRP", 91, "no"),
    # IL-32
    ("KXBTC", 91, "no"),
}


def break_even_wr(price_cents: int) -> float:
    """
    Fee-adjusted break-even win rate for a sniper bet at price_cents.

    Uses conservative per-contract fee approximation:
        fee_per_contract = 0.07 * (price_cents/100) * ((100-price_cents)/100) * 100
        net_win = (100 - price_cents) - fee_per_contract
        break_even = price_cents / (price_cents + net_win)
    """
    p = price_cents
    fee = KALSHI_FEE_RATE * (p / 100) * ((100 - p) / 100) * 100
    net_win = (100 - p) - fee
    if net_win <= 0:
        return 1.0  # impossible to profit
    return p / (p + net_win)


def ticker_prefix(ticker: str) -> str:
    """Extract asset prefix from full ticker. e.g. 'KXBTC15M-26MAR...' → 'KXBTC'."""
    for prefix in _TICKER_PREFIXES:
        if ticker.startswith(prefix):
            return prefix
    return ticker[:5]  # fallback


def is_already_guarded(asset_prefix: str, price_cents: int, side: str) -> bool:
    """Return True if this bucket is already covered by a hardcoded IL guard."""
    # Global guards (None ticker)
    if (None, price_cents, side) in _EXISTING_HARDCODED_GUARDS:
        return True
    # Asset-specific guards
    if (asset_prefix, price_cents, side) in _EXISTING_HARDCODED_GUARDS:
        return True
    return False


def discover_guards(db_path: Path = DB_PATH) -> list[dict]:
    """
    Query sniper bet history, return list of new auto-guard dicts.
    Each dict: ticker_contains, price_cents, side, n_bets, win_rate,
               break_even_wr, total_loss_usd, discovered_ts
    """
    conn = sqlite3.connect(str(db_path))

    rows = conn.execute("""
        SELECT ticker, side, price_cents,
               COUNT(*) as n_bets,
               SUM(CASE WHEN side = result THEN 1 ELSE 0 END) as wins,
               SUM(pnl_cents) as total_pnl_cents
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
        GROUP BY ticker_prefix, side, price_cents
    """).fetchall()

    # Fallback: group by computed prefix since ticker_prefix column may not exist
    if not rows:
        rows = conn.execute("""
            SELECT ticker, side, price_cents,
                   COUNT(*) as n_bets,
                   SUM(CASE WHEN side = result THEN 1 ELSE 0 END) as wins,
                   SUM(pnl_cents) as total_pnl_cents
            FROM trades
            WHERE strategy = 'expiry_sniper_v1'
              AND is_paper = 0
              AND result IS NOT NULL
            GROUP BY side, price_cents
        """).fetchall()
        # Flatten: these rows have full ticker, need to group by prefix manually
        conn.close()
        return _discover_guards_manual(db_path)

    conn.close()
    return _process_rows(rows)


def _discover_guards_manual(db_path: Path) -> list[dict]:
    """Group by (asset_prefix, price_cents, side) manually in Python."""
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ticker, side, price_cents, result, pnl_cents
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
    """).fetchall()
    conn.close()

    # Bucket: (asset_prefix, price_cents, side) → {n, wins, total_pnl}
    buckets: dict[tuple, dict] = {}
    for ticker, side, price_cents, result, pnl_cents in rows:
        prefix = ticker_prefix(ticker)
        key = (prefix, price_cents, side)
        if key not in buckets:
            buckets[key] = {"n": 0, "wins": 0, "pnl": 0}
        buckets[key]["n"] += 1
        buckets[key]["wins"] += 1 if side == result else 0
        buckets[key]["pnl"] += pnl_cents or 0

    guards = []
    now_ts = datetime.now(timezone.utc).timestamp()

    for (prefix, price_cents, side), stats in buckets.items():
        n = stats["n"]
        wins = stats["wins"]
        total_pnl_usd = stats["pnl"] / 100.0
        wr = wins / n if n > 0 else 0.0
        be_wr = break_even_wr(price_cents)

        # Skip if doesn't meet guard criteria
        if n < MIN_BETS:
            continue
        if wr >= be_wr:
            continue
        if total_pnl_usd >= -MIN_LOSS_USD:
            continue
        if is_already_guarded(prefix, price_cents, side):
            continue

        guards.append({
            "ticker_contains": prefix,
            "price_cents": price_cents,
            "side": side,
            "n_bets": n,
            "win_rate": round(wr, 4),
            "break_even_wr": round(be_wr, 4),
            "total_loss_usd": round(total_pnl_usd, 2),
            "discovered_ts": now_ts,
            "discovered_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        })

    # Sort by total_loss_usd ascending (worst first)
    guards.sort(key=lambda g: g["total_loss_usd"])
    return guards


def _process_rows(rows: list) -> list[dict]:
    """Process SQL rows that already have prefix grouping."""
    guards = []
    now_ts = datetime.now(timezone.utc).timestamp()

    for ticker, side, price_cents, n_bets, wins, total_pnl_cents in rows:
        prefix = ticker_prefix(ticker)
        wr = wins / n_bets if n_bets > 0 else 0.0
        be_wr = break_even_wr(price_cents)
        total_pnl_usd = (total_pnl_cents or 0) / 100.0

        if n_bets < MIN_BETS:
            continue
        if wr >= be_wr:
            continue
        if total_pnl_usd >= -MIN_LOSS_USD:
            continue
        if is_already_guarded(prefix, price_cents, side):
            continue

        guards.append({
            "ticker_contains": prefix,
            "price_cents": price_cents,
            "side": side,
            "n_bets": n_bets,
            "win_rate": round(wr, 4),
            "break_even_wr": round(be_wr, 4),
            "total_loss_usd": round(total_pnl_usd, 2),
            "discovered_ts": now_ts,
            "discovered_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        })

    guards.sort(key=lambda g: g["total_loss_usd"])
    return guards


def load_existing_auto_guards(output_path: Path = OUTPUT_PATH) -> list[dict]:
    """Load existing auto_guards.json, return empty list if not found."""
    if not output_path.exists():
        return []
    try:
        with open(output_path) as f:
            data = json.load(f)
        return data.get("guards", [])
    except (json.JSONDecodeError, KeyError):
        return []


def merge_guards(existing: list[dict], new_guards: list[dict]) -> list[dict]:
    """
    Merge new guards into existing, deduplicating by (ticker_contains, price_cents, side).
    New guards take precedence (fresher stats).
    """
    existing_keys = {
        (g["ticker_contains"], g["price_cents"], g["side"])
        for g in existing
    }
    merged = list(existing)
    added = 0
    for g in new_guards:
        key = (g["ticker_contains"], g["price_cents"], g["side"])
        if key not in existing_keys:
            merged.append(g)
            existing_keys.add(key)
            added += 1
    return merged, added


def write_guards(guards: list[dict], output_path: Path = OUTPUT_PATH) -> None:
    """Write guards to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updated_ts": datetime.now(timezone.utc).timestamp(),
        "updated_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "guards": guards,
    }
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Auto-discover sniper guards from live bet history")
    parser.add_argument("--dry-run", action="store_true", help="Print guards without writing file")
    parser.add_argument("--db", default=str(DB_PATH), help="Path to polybot.db")
    parser.add_argument("--min-bets", type=int, default=MIN_BETS)
    parser.add_argument("--min-loss", type=float, default=MIN_LOSS_USD)
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        return 1

    print(f"Scanning {db_path} for negative-EV sniper buckets...")
    print(f"  Criteria: n>={args.min_bets}, loss>{args.min_loss} USD, WR < break-even")

    new_guards = discover_guards(db_path)

    if not new_guards:
        print("No new guards found — all negative-EV buckets already covered.")
        return 0

    print(f"\nFound {len(new_guards)} new guard(s):")
    for g in new_guards:
        be_pct = round(g['break_even_wr'] * 100, 1)
        wr_pct = round(g['win_rate'] * 100, 1)
        print(
            f"  AUTO: {g['ticker_contains']} {g['side'].upper()}@{g['price_cents']}c "
            f"— {g['n_bets']} bets, {wr_pct}% WR (need {be_pct}%), "
            f"{g['total_loss_usd']} USD"
        )

    if args.dry_run:
        print("\n[dry-run] Not writing to file.")
        return 0

    existing = load_existing_auto_guards()
    merged, added = merge_guards(existing, new_guards)
    write_guards(merged)
    print(f"\nWrote {len(merged)} total guards ({added} new) to {OUTPUT_PATH}")
    print("Restart bot to activate new guards.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
