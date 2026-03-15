"""
Strategy baseline checker — used by scripts/verify_change.sh.

JOB:    Query settled live trades from the DB and check if a strategy's
        win rate meets the baseline threshold. Used by the verify-revert
        loop to gate parameter changes mechanically.

USAGE:
    python scripts/check_strategy_baseline.py --strategy expiry_sniper --min-win-rate 0.95
    python scripts/check_strategy_baseline.py --strategy btc_drift_v1 --min-win-rate 0.55 --last-n 30

EXIT CODES:
    0 = baseline met (safe to keep change)
    1 = baseline not met (verify_change.sh will revert)
    2 = error (missing DB, bad args)
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Optional


_DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "polybot.db"
_DEFAULT_LAST_N = 30
_DEFAULT_MIN_BETS = 5


def query_strategy_baseline(
    db_path: str,
    strategy: str,
    last_n: int = _DEFAULT_LAST_N,
) -> dict:
    """
    Query DB for the most recent `last_n` settled live trades for `strategy`.

    Win: result == side (works for both YES and NO side bets).
    Only counts is_paper=0 trades with a non-NULL result.

    Returns:
        dict with keys: bets (int), win_rate (float|None), total_pnl_usd (float)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Subquery: most recent last_n settled live trades for this strategy
    rows = conn.execute(
        """
        SELECT side, result, pnl_cents
        FROM (
            SELECT side, result, pnl_cents, settled_at
            FROM trades
            WHERE is_paper = 0
              AND strategy = ?
              AND result IS NOT NULL
            ORDER BY settled_at DESC
            LIMIT ?
        )
        """,
        (strategy, last_n),
    ).fetchall()
    conn.close()

    bets = len(rows)
    if bets == 0:
        return {"bets": 0, "win_rate": None, "total_pnl_usd": 0.0}

    wins = sum(1 for r in rows if r["result"] == r["side"])
    total_pnl = sum(r["pnl_cents"] for r in rows) / 100.0
    win_rate = wins / bets

    return {
        "bets": bets,
        "win_rate": win_rate,
        "total_pnl_usd": total_pnl,
    }


def check_passes(
    result: dict,
    min_win_rate: float,
    min_bets: int = _DEFAULT_MIN_BETS,
) -> tuple[bool, str]:
    """
    Evaluate whether a query_strategy_baseline result passes the threshold.

    Args:
        result:       Output of query_strategy_baseline()
        min_win_rate: Minimum acceptable win rate (e.g. 0.90 for 90%)
        min_bets:     Minimum settled bets required to make a judgment

    Returns:
        (passed: bool, reason: str)
    """
    bets = result["bets"]
    win_rate = result["win_rate"]
    pnl = result["total_pnl_usd"]

    if win_rate is None or bets == 0:
        return False, f"FAIL — no data: 0 settled live trades found"

    if bets < min_bets:
        return False, (
            f"FAIL — insufficient bets: {bets} settled live trades "
            f"(need >= {min_bets} to make a judgment)"
        )

    win_pct = win_rate * 100
    threshold_pct = min_win_rate * 100

    if win_rate < min_win_rate:
        return False, (
            f"FAIL — win rate {win_pct:.1f}% < threshold {threshold_pct:.1f}% "
            f"over last {bets} bets | P&L: {pnl:+.2f} USD"
        )

    return True, (
        f"PASS — win rate {win_pct:.1f}% >= threshold {threshold_pct:.1f}% "
        f"over last {bets} bets | P&L: {pnl:+.2f} USD"
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Check strategy win-rate baseline")
    p.add_argument("--strategy", required=True, help="Strategy name (e.g. expiry_sniper)")
    p.add_argument("--min-win-rate", type=float, required=True,
                   help="Minimum acceptable win rate (0.0–1.0, e.g. 0.90)")
    p.add_argument("--last-n", type=int, default=_DEFAULT_LAST_N,
                   help=f"Use last N settled live trades (default {_DEFAULT_LAST_N})")
    p.add_argument("--min-bets", type=int, default=_DEFAULT_MIN_BETS,
                   help=f"Minimum bets required (default {_DEFAULT_MIN_BETS})")
    p.add_argument("--db", default=str(_DEFAULT_DB_PATH),
                   help="Path to polybot.db")
    args = p.parse_args()

    if not Path(args.db).exists():
        print(f"ERROR: DB not found at {args.db}", file=sys.stderr)
        return 2

    if not 0.0 <= args.min_win_rate <= 1.0:
        print(f"ERROR: --min-win-rate must be between 0.0 and 1.0", file=sys.stderr)
        return 2

    result = query_strategy_baseline(args.db, args.strategy, last_n=args.last_n)
    passed, reason = check_passes(result, args.min_win_rate, min_bets=args.min_bets)

    print(f"Strategy:  {args.strategy}")
    print(f"Threshold: {args.min_win_rate * 100:.1f}% win rate over last {args.last_n} bets")
    print(f"Result:    {reason}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
