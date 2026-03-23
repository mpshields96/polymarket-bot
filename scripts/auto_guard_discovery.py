"""
Auto-guard discovery for expiry_sniper_v1.

JOB:    Scan live sniper bet history, identify negative-EV price/side/asset
        buckets, write new guards to data/auto_guards.json.

RUNS:   At session start (via polybot-init), or manually:
            python3 scripts/auto_guard_discovery.py
            python3 scripts/auto_guard_discovery.py --dry-run   # print only

OUTPUT: data/auto_guards.json — loaded by live.py at next restart.

CRITERIA for auto-guard:
    1. n_bets >= MIN_BETS (default 10, raised from 3 in S112 trauma audit)
    2. win_rate < break_even_wr (fee-adjusted)
    3. binomial p-value < P_VALUE_THRESHOLD (0.20) — one-sided test H1: WR < break-even
       Prevents trauma guards from firing on pure-noise samples (S112 audit found
       all 5 existing auto-guards had p=0.44-0.60, random-chance territory).
    4. total_loss_usd < -MIN_LOSS_USD (default 5 USD)
    5. Not already covered by a hardcoded IL guard in live.py

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
MIN_BETS = 10           # minimum sample size (raised S112: n=3 was trauma-level)
MIN_LOSS_USD = 5.0      # minimum total loss to trigger guard (USD)
KALSHI_FEE_RATE = 0.07  # 7% taker fee

# Statistical significance gate (S112 — trauma audit finding)
# One-sided binomial p-value threshold: P(X <= observed_wins | n, break_even_wr) < this.
# 0.20 = permissive early-warning (catches real patterns before n=30 SPRT threshold),
# but filters pure-noise activations (p=0.44-0.60 seen in all 5 existing guards).
P_VALUE_THRESHOLD = 0.20

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
    # IL-34: KXBTC NO@95c — 28 bets, 92.9% WR, needs 95.3% (S127)
    ("KXBTC", 95, "no"),
    # IL-35: KXSOL sniper at 05:xx UTC — handled via _EXISTING_HARDCODED_HOUR_GUARDS
    # IL-33: KXXRP global sniper block — individual KXXRP combos already listed above
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


def binomial_pvalue_below(k: int, n: int, p0: float) -> float:
    """
    One-sided binomial p-value: P(X <= k | n, p0).

    Used to test H0: true WR = break-even WR (p0).
    H1: true WR < p0 (bucket is unprofitable).

    Returns probability of observing k or fewer wins in n trials if true WR = p0.
    Low p-value (< P_VALUE_THRESHOLD) → statistically significant underperformance.

    Args:
        k:  observed wins
        n:  total bets
        p0: null hypothesis win rate (break-even WR for this price)

    Returns p-value in [0, 1]. Returns 1.0 if n=0.
    """
    if n == 0:
        return 1.0
    total = 0.0
    for i in range(k + 1):
        total += math.comb(n, i) * (p0 ** i) * ((1 - p0) ** (n - i))
    return min(1.0, total)


def meets_statistical_threshold(n: int, wins: int, break_even: float) -> bool:
    """
    Return True if bucket meets statistical guard criteria:
      1. n >= MIN_BETS
      2. WR < break-even (raw check)
      3. binomial p-value < P_VALUE_THRESHOLD (one-sided, H1: WR < break-even)

    All three must hold. This prevents trauma guards from activating on
    small samples with p-values in random-chance territory.
    """
    if n < MIN_BETS:
        return False
    wr = wins / n
    if wr >= break_even:
        return False
    p = binomial_pvalue_below(k=wins, n=n, p0=break_even)
    return p < P_VALUE_THRESHOLD


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


# Hardcoded hour guards already in live.py — skip these to avoid duplicates.
# Format: (ticker_contains_or_None, utc_hour)
_EXISTING_HARDCODED_HOUR_GUARDS: set[tuple] = {
    # IL-35: KXSOL sniper at 05:xx UTC (S127)
    ("KXSOL", 5),
    # Blanket 08:xx block is in main.py (not live.py execute) — not tracked here
}


def discover_hour_guards(db_path: Path = DB_PATH) -> list[dict]:
    """
    Scan sniper bet history grouped by (asset_prefix, utc_hour) for negative-EV time slots.

    Uses average price in each bucket to compute break-even WR.
    Same statistical criteria as price guards: n>=10, p<0.20, loss > MIN_LOSS_USD.
    Guards output with price_cents=null, utc_hour=N, side=null (blocks all bets for that
    asset × hour regardless of price or side).
    """
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ticker, side, price_cents, result, pnl_cents,
               CAST(strftime('%H', datetime(created_at, 'unixepoch')) AS INTEGER) as utc_hour
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
    """).fetchall()
    conn.close()

    # Bucket: (asset_prefix, utc_hour) → {n, wins, total_pnl, price_sum}
    buckets: dict[tuple, dict] = {}
    for ticker, side, price_cents, result, pnl_cents, utc_hour in rows:
        prefix = ticker_prefix(ticker)
        key = (prefix, utc_hour)
        if key not in buckets:
            buckets[key] = {"n": 0, "wins": 0, "pnl": 0, "price_sum": 0}
        buckets[key]["n"] += 1
        buckets[key]["wins"] += 1 if side == result else 0
        buckets[key]["pnl"] += pnl_cents or 0
        buckets[key]["price_sum"] += price_cents or 0

    guards = []
    now_ts = datetime.now(timezone.utc).timestamp()

    for (prefix, utc_hour), stats in buckets.items():
        n = stats["n"]
        wins = stats["wins"]
        total_pnl_usd = stats["pnl"] / 100.0
        avg_price = stats["price_sum"] / n if n > 0 else 92.0
        be_wr = break_even_wr(int(round(avg_price)))

        if (prefix, utc_hour) in _EXISTING_HARDCODED_HOUR_GUARDS:
            continue
        if not meets_statistical_threshold(n, wins, be_wr):
            continue
        if total_pnl_usd >= -MIN_LOSS_USD:
            continue

        guards.append({
            "ticker_contains": prefix,
            "price_cents": None,
            "utc_hour": utc_hour,
            "side": None,
            "n_bets": n,
            "win_rate": round(wins / n, 4),
            "break_even_wr": round(be_wr, 4),
            "avg_price_cents": round(avg_price, 1),
            "total_loss_usd": round(total_pnl_usd, 2),
            "discovered_ts": now_ts,
            "discovered_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        })

    guards.sort(key=lambda g: g["total_loss_usd"])
    return guards


def discover_hour_warming_buckets(db_path: Path = DB_PATH, min_n: int = 5, min_loss: float = 2.0) -> list[dict]:
    """Return hour buckets accumulating losses but not yet at formal guard threshold."""
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ticker, side, price_cents, result, pnl_cents,
               CAST(strftime('%H', datetime(created_at, 'unixepoch')) AS INTEGER) as utc_hour
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
    """).fetchall()
    conn.close()

    buckets: dict[tuple, dict] = {}
    for ticker, side, price_cents, result, pnl_cents, utc_hour in rows:
        prefix = ticker_prefix(ticker)
        key = (prefix, utc_hour)
        if key not in buckets:
            buckets[key] = {"n": 0, "wins": 0, "pnl": 0, "price_sum": 0}
        buckets[key]["n"] += 1
        buckets[key]["wins"] += 1 if side == result else 0
        buckets[key]["pnl"] += pnl_cents or 0
        buckets[key]["price_sum"] += price_cents or 0

    warming = []
    for (prefix, utc_hour), stats in buckets.items():
        n = stats["n"]
        wins = stats["wins"]
        total_pnl_usd = stats["pnl"] / 100.0
        avg_price = stats["price_sum"] / n if n > 0 else 92.0
        be_wr = break_even_wr(int(round(avg_price)))

        if (prefix, utc_hour) in _EXISTING_HARDCODED_HOUR_GUARDS:
            continue
        if n < min_n:
            continue
        if total_pnl_usd >= -min_loss:
            continue
        if wins / n >= be_wr:
            continue
        if meets_statistical_threshold(n, wins, be_wr):
            continue  # already qualifies as full guard

        p_val = binomial_pvalue_below(k=wins, n=n, p0=be_wr)
        warming.append({
            "ticker_contains": prefix,
            "utc_hour": utc_hour,
            "n_bets": n,
            "win_rate": round(wins / n, 4),
            "break_even_wr": round(be_wr, 4),
            "avg_price_cents": round(avg_price, 1),
            "total_loss_usd": round(total_pnl_usd, 2),
            "p_value": round(p_val, 3),
        })

    warming.sort(key=lambda w: w["total_loss_usd"])
    return warming


def discover_guards(db_path: Path = DB_PATH) -> list[dict]:
    """
    Query sniper bet history, return list of new auto-guard dicts.
    Each dict: ticker_contains, price_cents, side, n_bets, win_rate,
               break_even_wr, total_loss_usd, discovered_ts
    """
    conn = sqlite3.connect(str(db_path))

    # ticker_prefix column does not exist in DB — always use manual grouping
    conn.close()
    return _discover_guards_manual(db_path)


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
        if not meets_statistical_threshold(n, wins, be_wr):
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

        if not meets_statistical_threshold(n_bets, wins, be_wr):
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


def discover_warming_buckets(db_path: Path = DB_PATH, min_n: int = 5, min_loss: float = 2.0) -> list[dict]:
    """
    Return buckets that are accumulating losses but haven't crossed the formal guard threshold.
    These are early-warning signals — not yet actionable, but worth watching.

    Criteria:
    - n >= min_n (default 5 — enough to be meaningful)
    - total_pnl_usd < -min_loss USD
    - WR below break-even
    - NOT already guarded (checks both hardcoded IL guards AND auto_guards.json)
    - Does NOT meet statistical threshold (otherwise it would be a new guard)
    """
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("""
        SELECT ticker, side, price_cents, result, pnl_cents
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
    """).fetchall()
    conn.close()

    # Load auto-discovered guards to exclude already-guarded buckets
    auto_guarded: set[tuple] = {
        (g["ticker_contains"], g["price_cents"], g["side"])
        for g in load_existing_auto_guards()
    }

    buckets: dict[tuple, dict] = {}
    for ticker, side, price_cents, result, pnl_cents in rows:
        prefix = ticker_prefix(ticker)
        key = (prefix, price_cents, side)
        if key not in buckets:
            buckets[key] = {"n": 0, "wins": 0, "pnl": 0}
        buckets[key]["n"] += 1
        buckets[key]["wins"] += 1 if side == result else 0
        buckets[key]["pnl"] += pnl_cents or 0

    warming = []
    for (prefix, price_cents, side), stats in buckets.items():
        n = stats["n"]
        wins = stats["wins"]
        total_pnl_usd = stats["pnl"] / 100.0
        wr = wins / n if n > 0 else 0.0
        be_wr = break_even_wr(price_cents)

        if n < min_n:
            continue
        if total_pnl_usd >= -min_loss:
            continue
        if wr >= be_wr:
            continue
        if is_already_guarded(prefix, price_cents, side):
            continue
        if (prefix, price_cents, side) in auto_guarded:
            continue
        # Only show buckets that haven't yet crossed formal threshold
        if meets_statistical_threshold(n, wins, be_wr):
            continue

        p_val = binomial_pvalue_below(k=wins, n=n, p0=be_wr)
        warming.append({
            "ticker_contains": prefix,
            "price_cents": price_cents,
            "side": side,
            "n_bets": n,
            "win_rate": round(wr, 4),
            "break_even_wr": round(be_wr, 4),
            "total_loss_usd": round(total_pnl_usd, 2),
            "p_value": round(p_val, 3),
        })

    warming.sort(key=lambda w: w["total_loss_usd"])
    return warming


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
    else:
        print(f"\nFound {len(new_guards)} new guard(s):")
        for g in new_guards:
            be_pct = round(g['break_even_wr'] * 100, 1)
            wr_pct = round(g['win_rate'] * 100, 1)
            print(
                f"  AUTO: {g['ticker_contains']} {g['side'].upper()}@{g['price_cents']}c "
                f"— {g['n_bets']} bets, {wr_pct}% WR (need {be_pct}%), "
                f"{g['total_loss_usd']} USD"
            )

    # Hour-based guards (new dimension: asset × UTC hour)
    new_hour_guards = discover_hour_guards(db_path)
    if not new_hour_guards:
        print("No new hour guards — all negative-EV time slots already covered.")
    else:
        print(f"\nFound {len(new_hour_guards)} new HOUR guard(s):")
        for g in new_hour_guards:
            be_pct = round(g['break_even_wr'] * 100, 1)
            wr_pct = round(g['win_rate'] * 100, 1)
            print(
                f"  HOUR: {g['ticker_contains']} at {g['utc_hour']:02d}:xx UTC "
                f"— {g['n_bets']} bets, {wr_pct}% WR (need {be_pct}%, avg {g['avg_price_cents']}c), "
                f"{g['total_loss_usd']} USD"
            )

    # Always show warming buckets (early warning, not actionable yet)
    warming = discover_warming_buckets(db_path)
    hour_warming = discover_hour_warming_buckets(db_path)
    if warming:
        print(f"\nWarming price buckets (n>=5, below BE, not yet significant — watch only):")
        for w in warming:
            be_pct = round(w['break_even_wr'] * 100, 1)
            wr_pct = round(w['win_rate'] * 100, 1)
            print(
                f"  WATCH: {w['ticker_contains']} {w['side'].upper()}@{w['price_cents']}c "
                f"— n={w['n_bets']}, {wr_pct}% WR (need {be_pct}%), "
                f"{w['total_loss_usd']} USD, p={w['p_value']}"
            )
    else:
        print("No warming price buckets.")

    if hour_warming:
        print(f"\nWarming hour buckets (n>=5, below BE, not yet significant — watch only):")
        for w in hour_warming:
            be_pct = round(w['break_even_wr'] * 100, 1)
            wr_pct = round(w['win_rate'] * 100, 1)
            print(
                f"  WATCH HOUR: {w['ticker_contains']} at {w['utc_hour']:02d}:xx UTC "
                f"— n={w['n_bets']}, {wr_pct}% WR (need {be_pct}%, avg {w['avg_price_cents']}c), "
                f"{w['total_loss_usd']} USD, p={w['p_value']}"
            )

    all_new = new_guards + new_hour_guards
    if all_new and not args.dry_run:
        existing = load_existing_auto_guards()
        merged, added = merge_guards(existing, all_new)
        write_guards(merged)
        print(f"\nWrote {len(merged)} total guards ({added} new) to {OUTPUT_PATH}")
        print("Restart bot to activate new guards.")
    elif all_new and args.dry_run:
        print("\n[dry-run] Not writing to file.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
