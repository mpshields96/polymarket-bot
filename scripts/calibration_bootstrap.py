"""
Bootstrap temperature calibration from historical DB.

Seeds data/calibration.json with per-strategy running sums computed from
all settled live drift bets. Run once after installing the temperature
calibration feature (Session 107), or to re-seed after clearing the file.

Usage:
    ./venv/bin/python3 scripts/calibration_bootstrap.py [--dry-run]

Output:
    Writes data/calibration.json with n, sum_pred, sum_actual per strategy.
    Prints summary of T_s values and expected calibration impact.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.models.temperature_calibration import StrategyCalibrator, MIN_OBSERVATIONS

DB_PATH = PROJECT_ROOT / "data" / "polybot.db"
CAL_PATH = PROJECT_ROOT / "data" / "calibration.json"

_DRIFT_STRATEGIES = frozenset([
    "btc_drift_v1",
    "eth_drift_v1",
    "sol_drift_v1",
    "xrp_drift_v1",
])


def bootstrap(dry_run: bool = False) -> None:
    conn = sqlite3.connect(DB_PATH)

    print("Calibration Bootstrap — seeding from historical DB")
    print(f"  DB: {DB_PATH}")
    print(f"  OUT: {CAL_PATH}")
    print()

    # Create a fresh calibrator (or load existing to see what's there)
    cal = StrategyCalibrator(CAL_PATH if not dry_run else Path("/tmp/cal_dry.json"))

    total_seeded = 0
    for strat in sorted(_DRIFT_STRATEGIES):
        rows = conn.execute(
            """
            SELECT win_prob, side, result
            FROM trades
            WHERE strategy = ?
              AND is_paper = 0
              AND result IS NOT NULL
              AND win_prob IS NOT NULL
              AND win_prob > 0.0 AND win_prob < 1.0
            ORDER BY settled_at ASC
            """,
            (strat,),
        ).fetchall()

        if not rows:
            print(f"  {strat}: 0 settled bets — skip")
            continue

        n = 0
        sum_pred = 0.0
        sum_actual = 0.0
        for win_prob, side, result in rows:
            won = (side == result)
            pred_excess = win_prob - 0.5
            actual_excess = (1.0 if won else 0.0) - 0.5
            n += 1
            sum_pred += pred_excess
            sum_actual += actual_excess

        if not dry_run:
            cal._data[strat] = {
                "n": float(n),
                "sum_pred": sum_pred,
                "sum_actual": sum_actual,
            }

        # Compute T for display
        T = 1.0
        if n >= MIN_OBSERVATIONS and abs(sum_pred) > 1e-6:
            from src.models.temperature_calibration import _T_MIN, _T_MAX
            T = max(_T_MIN, min(_T_MAX, sum_actual / sum_pred))

        wins = sum(1 for _, side, result in rows if side == result)
        avg_pred = (sum_pred / n) + 0.5
        actual_wr = wins / n

        impact_str = ""
        if T < 0.99:
            # Show corrected win_prob at avg_pred
            corrected = 0.5 + (avg_pred - 0.5) * T
            impact_str = f"  [avg_pred={avg_pred*100:.1f}% → {corrected*100:.1f}% after correction]"
        elif T > 1.01:
            corrected = 0.5 + (avg_pred - 0.5) * T
            impact_str = f"  [avg_pred={avg_pred*100:.1f}% → {corrected*100:.1f}% after correction]"

        status = "ACTIVE" if n >= MIN_OBSERVATIONS else f"inactive (need {MIN_OBSERVATIONS - n} more bets)"
        print(f"  {strat}: n={n}  predicted={avg_pred*100:.1f}%  actual={actual_wr*100:.1f}%  T={T:.3f}  [{status}]{impact_str}")
        total_seeded += n

    if not dry_run:
        cal._save()
        print()
        print(f"Wrote {CAL_PATH}")

    print(f"Total bets processed: {total_seeded}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap temperature calibration from DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()
    bootstrap(dry_run=args.dry_run)
