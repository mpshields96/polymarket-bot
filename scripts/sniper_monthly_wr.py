"""
Sniper Monthly WR Tracker — scripts/sniper_monthly_wr.py

Motivation: CCA (Session 111) flagged that FLB may be weakening (Whelan VoxEU March 2026).
"Some evidence of weakening favourite-longshot bias in 2025 data vs earlier years."
This script tracks rolling and monthly WR to detect sustained degradation early.

Flag threshold:
  Rolling 30-day WR < 93% with n >= 30 bets → WARNING (potential FLB weakening signal)
  Action: monitor trend over 2+ sessions before changing any parameter.
  Do NOT change config based on a single flag (PRINCIPLES.md anti-trauma rule).

Usage:
  python3 scripts/sniper_monthly_wr.py
  python3 scripts/sniper_monthly_wr.py --db path/to/polybot.db
"""

from __future__ import annotations

import argparse
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"

# ── Thresholds (CCA Session 111 recommendation) ────────────────────────────────
WR_FLAG_THRESHOLD = 0.93   # flag if rolling WR drops below this
WR_FLAG_MIN_BETS = 30      # minimum bets in window to flag (avoid noise)
ROLLING_WINDOW_DAYS = 30   # lookback window in days


@dataclass
class MonthlyWRResult:
    month: str          # "YYYY-MM"
    n_bets: int
    wins: int
    win_rate: float
    pnl_usd: float


@dataclass
class RollingWRResult:
    window_days: int
    n_bets: int
    wins: int
    win_rate: float
    pnl_usd: float
    flagged: bool       # True if WR < threshold and n >= min_bets


def compute_monthly_wr(conn: sqlite3.Connection) -> list[MonthlyWRResult]:
    """
    Compute win rate per calendar month for expiry_sniper_v1 live settled bets.
    Returns list sorted chronologically by month.
    """
    rows = conn.execute("""
        SELECT
            strftime('%Y-%m', datetime(settled_at, 'unixepoch')) AS month,
            COUNT(*) AS n,
            SUM(CASE WHEN side = result THEN 1 ELSE 0 END) AS wins,
            SUM(pnl_cents) AS pnl_cents
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
        GROUP BY month
        ORDER BY month ASC
    """).fetchall()

    return [
        MonthlyWRResult(
            month=r[0],
            n_bets=r[1],
            wins=r[2],
            win_rate=r[2] / r[1] if r[1] > 0 else 0.0,
            pnl_usd=round((r[3] or 0) / 100.0, 2),
        )
        for r in rows
    ]


def compute_rolling_wr(
    conn: sqlite3.Connection,
    as_of_ts: float | None = None,
    window_days: int = ROLLING_WINDOW_DAYS,
) -> RollingWRResult:
    """
    Compute win rate over the last `window_days` days of settled bets.
    as_of_ts defaults to now (time.time()).
    """
    if as_of_ts is None:
        as_of_ts = time.time()
    cutoff_ts = as_of_ts - window_days * 86400

    row = conn.execute("""
        SELECT
            COUNT(*) AS n,
            SUM(CASE WHEN side = result THEN 1 ELSE 0 END) AS wins,
            SUM(pnl_cents) AS pnl_cents
        FROM trades
        WHERE strategy = 'expiry_sniper_v1'
          AND is_paper = 0
          AND result IS NOT NULL
          AND settled_at >= ?
    """, (cutoff_ts,)).fetchone()

    n = row[0] or 0
    wins = row[1] or 0
    pnl_usd = round((row[2] or 0) / 100.0, 2)
    win_rate = wins / n if n > 0 else 0.0
    flagged = (win_rate < WR_FLAG_THRESHOLD) and (n >= WR_FLAG_MIN_BETS)

    return RollingWRResult(
        window_days=window_days,
        n_bets=n,
        wins=wins,
        win_rate=win_rate,
        pnl_usd=pnl_usd,
        flagged=flagged,
    )


def _print_report(db_path: Path = DB_PATH) -> None:
    """Run monthly + rolling WR analysis and print report."""
    conn = sqlite3.connect(str(db_path))

    monthly = compute_monthly_wr(conn)
    rolling = compute_rolling_wr(conn)

    print("=" * 55)
    print("  SNIPER MONTHLY WR TRACKER")
    print("  FLB Weakening Monitor (Whelan VoxEU March 2026)")
    print("=" * 55)
    print()

    if not monthly:
        print("  No settled sniper bets found.")
        return

    print("  Monthly breakdown (expiry_sniper_v1, live only):")
    print()
    for r in monthly:
        flag = "  *** BELOW TARGET" if r.win_rate < WR_FLAG_THRESHOLD else ""
        wr_str = f"{r.win_rate * 100:.1f}%"
        print(
            f"  {r.month}:  n={r.n_bets:4d}  WR={wr_str:6s}  "
            f"P&L={r.pnl_usd:+8.2f} USD{flag}"
        )

    print()
    print(f"  Rolling {rolling.window_days}-day window:")
    flag_str = "  *** FLB WEAKENING SIGNAL — monitor trend" if rolling.flagged else ""
    if rolling.n_bets == 0:
        print("  No bets in rolling window.")
    else:
        print(
            f"  n={rolling.n_bets}  WR={rolling.win_rate * 100:.1f}%  "
            f"P&L={rolling.pnl_usd:+.2f} USD{flag_str}"
        )

    print()
    print(f"  Flag threshold: WR < {WR_FLAG_THRESHOLD * 100:.0f}% with n >= {WR_FLAG_MIN_BETS} bets")
    if rolling.flagged:
        print()
        print("  ACTION: Do NOT change config based on single flag. Monitor 2+ sessions.")
        print("  If WR stays below 93% for 100+ bets: escalate to Matthew.")
    print()
    print("  Source: Whelan (2026) VoxEU/CEPR — FLB weakening in 2025 Kalshi data")
    print("  Bot edge: structural FLB + liquidity premium (not calibration-based)")
    print("  Crypto b=1.03 (Le 2026 arXiv:2602.19520) — near-perfect calibration")
    print()

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sniper monthly WR tracker")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to polybot.db")
    args = parser.parse_args()
    _print_report(db_path=args.db)
