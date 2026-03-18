"""
Strategy Drift Check — Dimension 7 of SELF_IMPROVEMENT_ROADMAP.md

JOB:    Detect when a live strategy's win rate is declining using the
        Page-Hinkley sequential test. Runs at session start to give early
        warning of strategy deterioration — before losses accumulate.

        Self-improving: no human needed. Alerts are written to a report file
        and output to stdout. Bot continues running; this is a monitoring tool,
        not an automatic kill switch.

RUNS:   python3 scripts/strategy_drift_check.py
        Exit code 0 = no drift detected, 1 = drift alert on >= 1 strategy

ALGORITHM (Page-Hinkley CUSUM):
    For a sequence of binary outcomes X_1, X_2, ... (1=win, 0=loss):
    - Reference value: k = target_wr - delta/2
      (midpoint between "OK" and "declining" — minimises detection lag)
    - CUSUM: C_n = max(0, C_{n-1} - (X_n - k))
      (floored at 0 for one-sided downward detection)
    - Alert when C_n > h (threshold)

    Interpretation of h:
    - h=4 ≈ ARL (average run length) ~200 bets under H0 (no drift)
    - At 5 bets/day, h=4 → ~40 false alarm days (low noise)
    - Detect ~10pp WR drop within 20-30 bets (acceptable lag)

ACADEMIC BASIS:
    - Page (1954) "Continuous inspection schemes" — original CUSUM algorithm
    - Hinkley (1971) — one-sided sequential test for detecting mean shift
    - Basseville & Nikiforov (1993) "Detection of Abrupt Changes" — textbook
    - Optimal in the sense of Lorden (1971): minimises worst-case detection lag
      for a given false alarm rate

WHY NOT FIXED-SAMPLE TEST:
    A rolling-20-bet WR is noisy and has no formal stopping rule. The PH test
    uses ALL historical data efficiently: it accumulates evidence of drift and
    resets automatically if WR recovers. Fixed-sample tests waste data; CUSUM
    uses every observation.
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"
REPORT_PATH = Path("/tmp/strategy_drift_report.txt")

# Minimum bets before PH test runs (avoids false alarms on tiny samples)
MIN_BETS_DEFAULT = 15


# ── Strategy registry ─────────────────────────────────────────────────────
# target_wr: expected WR under H0 (historical average)
# delta: minimum detectable shift (half-width of reference interval)
# h: alert threshold — higher = fewer false alarms but slower detection
# min_bets: don't run PH until at least this many live settled bets

STRATEGY_REGISTRY: list[dict] = [
    {
        "name": "sol_drift_v1",
        "target_wr": 0.68,   # historical 70.7%, conservative target
        "delta": 0.10,        # detect ~10pp decline (68% → 58%)
        "h": 4.0,             # ~ARL 200 under H0
        "min_bets": 15,
    },
    {
        "name": "btc_drift_v1",
        "target_wr": 0.50,   # direction_filter="no", approximately 50% WR
        "delta": 0.10,        # detect ~10pp decline (50% → 40%)
        "h": 4.0,
        "min_bets": 20,
    },
    {
        "name": "eth_drift_v1",
        "target_wr": 0.50,   # approximately 50% WR
        "delta": 0.10,        # detect ~10pp decline (50% → 40%)
        "h": 4.0,
        "min_bets": 20,
    },
    {
        "name": "xrp_drift_v1",
        "target_wr": 0.50,   # approximately 51% WR
        "delta": 0.10,        # detect ~10pp decline
        "h": 4.0,
        "min_bets": 15,
    },
]


# ── Core PH algorithm ─────────────────────────────────────────────────────

def _page_hinkley_stat(
    outcomes: list[int],
    target_wr: float,
    delta: float,
    h: float,
) -> tuple[float, float, bool]:
    """
    Compute Page-Hinkley CUSUM statistic for downward drift detection.

    Args:
        outcomes:   Ordered list of 1 (win) or 0 (loss)
        target_wr:  Expected WR under H0 (no drift)
        delta:      Minimum shift to detect (e.g. 0.10 = 10pp decline)
        h:          Alert threshold (4.0 recommended)

    Returns:
        (current_stat, peak_stat, alert_triggered)
        current_stat: CUSUM at end of sequence (may have declined after alert)
        peak_stat: maximum CUSUM seen (what triggered the alert if alert=True)
        alert_triggered: True if peak_stat > h at any point in the sequence
    """
    if not outcomes:
        return 0.0, 0.0, False

    # Reference value: midpoint between H0 and H1
    # H0: WR = target_wr, H1: WR = target_wr - delta
    # k = (target_wr + (target_wr - delta)) / 2 = target_wr - delta/2
    k = target_wr - delta / 2.0

    cusum = 0.0
    peak = 0.0
    alert = False

    for x in outcomes:
        # Increment: positive when loss exceeds expected rate
        # Win (x=1): cusum decreases by (1 - k)
        # Loss (x=0): cusum increases by k
        cusum = max(0.0, cusum - (x - k))
        if cusum > peak:
            peak = cusum
        if cusum > h:
            alert = True
            # Don't break — continue to track final state

    return cusum, peak, alert


# ── Rolling WR helper ─────────────────────────────────────────────────────

def _rolling_wr(outcomes: list[int], window: int) -> Optional[float]:
    """Win rate over the last `window` bets (or all bets if fewer)."""
    if not outcomes:
        return None
    tail = outcomes[-window:]
    return sum(tail) / len(tail)


# ── Assessment dataclass ──────────────────────────────────────────────────

@dataclass
class StrategyDriftResult:
    strategy_name: str
    n_bets: int
    overall_wr: float
    rolling_20_wr: float
    rolling_10_wr: float
    ph_stat: float
    alert: bool
    status: str


def _assess_strategy(
    name: str,
    outcomes: list[int],
    target_wr: float,
    delta: float = 0.10,
    h: float = 4.0,
    min_bets: int = MIN_BETS_DEFAULT,
) -> StrategyDriftResult:
    """Assess a strategy for drift given its ordered outcomes."""
    n = len(outcomes)
    overall_wr = sum(outcomes) / n if n > 0 else 0.0
    rolling_20 = _rolling_wr(outcomes, 20) or 0.0
    rolling_10 = _rolling_wr(outcomes, 10) or 0.0

    if n < min_bets:
        status = f"INSUFFICIENT DATA — {n} bets (need {min_bets}+)"
        return StrategyDriftResult(
            strategy_name=name, n_bets=n, overall_wr=overall_wr,
            rolling_20_wr=rolling_20, rolling_10_wr=rolling_10,
            ph_stat=0.0, alert=False, status=status,
        )

    current_stat, peak_stat, alert = _page_hinkley_stat(
        outcomes, target_wr=target_wr, delta=delta, h=h
    )
    # Report peak stat (what triggered the alert) alongside current stat
    ph_stat = current_stat

    if alert:
        status = (
            f"DRIFT ALERT — peak PH={peak_stat:.2f} exceeded h={h} | "
            f"current PH={current_stat:.2f} | "
            f"WR last20={rolling_20:.1%} last10={rolling_10:.1%} (target={target_wr:.1%})"
        )
    elif current_stat > h * 0.7:
        status = (
            f"APPROACHING THRESHOLD — PH={current_stat:.2f} (threshold={h}) | "
            f"WR last20={rolling_20:.1%} last10={rolling_10:.1%}"
        )
    else:
        status = (
            f"Normal — PH={current_stat:.2f} (threshold={h}) | "
            f"WR last20={rolling_20:.1%} last10={rolling_10:.1%}"
        )

    return StrategyDriftResult(
        strategy_name=name, n_bets=n, overall_wr=overall_wr,
        rolling_20_wr=rolling_20, rolling_10_wr=rolling_10,
        ph_stat=ph_stat, alert=alert, status=status,
    )


# ── Database query ────────────────────────────────────────────────────────

def _query_outcomes(strategy_name: str) -> list[int]:
    """Query ordered win/loss outcomes for a strategy (oldest first)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute(
            """
            SELECT side, result
            FROM trades
            WHERE strategy = ?
              AND is_paper = 0
              AND result IS NOT NULL
            ORDER BY settled_at ASC
            """,
            (strategy_name,),
        ).fetchall()
        conn.close()
        return [1 if row[0] == row[1] else 0 for row in rows]
    except Exception:
        return []


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("  STRATEGY DRIFT CHECK — Page-Hinkley Sequential Test")
    print("=" * 60)

    alerts = []
    lines = []

    for config in STRATEGY_REGISTRY:
        outcomes = _query_outcomes(config["name"])
        result = _assess_strategy(
            name=config["name"],
            outcomes=outcomes,
            target_wr=config["target_wr"],
            delta=config["delta"],
            h=config["h"],
            min_bets=config["min_bets"],
        )

        alert_marker = "  *** ALERT ***" if result.alert else ""
        approach_marker = (
            "  (approaching)" if not result.alert and result.ph_stat > result.ph_stat
            else ""
        )

        print(
            f"\n  {result.strategy_name}  n={result.n_bets}"
            f"  overall={result.overall_wr:.1%}  last20={result.rolling_20_wr:.1%}"
            f"  last10={result.rolling_10_wr:.1%}"
        )
        print(f"  {result.status}{alert_marker}")

        lines.append(
            f"{result.strategy_name}: {result.status} (n={result.n_bets})"
        )
        if result.alert:
            alerts.append(result)

    print()
    if alerts:
        print(f"  DRIFT DETECTED ON {len(alerts)} STRATEGY/STRATEGIES:")
        for a in alerts:
            print(f"    - {a.strategy_name}: WR={a.overall_wr:.1%}, "
                  f"last20={a.rolling_20_wr:.1%}, PH={a.ph_stat:.2f}")
        print()
        print("  ACTION REQUIRED:")
        print("  1. Review recent bet history (last 20 bets)")
        print("  2. Check if losing buckets are unguarded (run auto_guard_discovery.py)")
        print("  3. Consider reducing bet size or pausing strategy if decline persists")
        print("  4. Do NOT change direction_filter without 30+ bets post-change")
        print("  5. Document decision in .planning/CHANGELOG.md")
        exit_code = 1
    else:
        print("  All strategies within normal drift bounds.")
        exit_code = 0

    # Write report for monitoring loop
    try:
        with open(REPORT_PATH, "w") as f:
            f.write("STRATEGY DRIFT REPORT\n")
            for line in lines:
                f.write(line + "\n")
            if alerts:
                f.write(f"\nALERT: {len(alerts)} strategy/strategies drifting\n")
            else:
                f.write("\nStatus: All normal\n")
    except Exception:
        pass

    print("=" * 60)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
