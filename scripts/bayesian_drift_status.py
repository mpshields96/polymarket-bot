"""
Bayesian drift model status report.

JOB:    Show current posterior state for the BayesianDriftModel — observations,
        sensitivity estimate, posterior uncertainty, kelly_scale.
        Used at session start to verify self-improvement is accumulating.

RUNS:   python3 scripts/bayesian_drift_status.py
        (or as part of session start checklist)

OUTPUT: One-page human-readable status to stdout.
        Exit code 0 = healthy, 1 = warning (file missing or not enough obs).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PROJ = Path(__file__).parent.parent
POSTERIOR_PATH = PROJ / "data" / "drift_posterior.json"
DB_PATH = PROJ / "data" / "polybot.db"

# Minimum observations before posterior meaningfully diverges from prior
MIN_OBS_FOR_OVERRIDE = 30


def _load_posterior() -> dict | None:
    if not POSTERIOR_PATH.exists():
        return None
    try:
        with open(POSTERIOR_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        return None


def _count_live_drift_bets() -> dict:
    """Count live settled drift bets per strategy from DB."""
    try:
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        rows = conn.execute("""
            SELECT strategy, COUNT(*) as n,
                   SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins
            FROM trades
            WHERE strategy IN ('btc_drift_v1', 'eth_drift_v1', 'sol_drift_v1', 'xrp_drift_v1')
              AND is_paper = 0
              AND result IS NOT NULL
            GROUP BY strategy
            ORDER BY strategy
        """).fetchall()
        conn.close()
        return {r[0]: {"n": r[1], "wins": r[2]} for r in rows}
    except Exception:
        return {}


def main() -> int:
    print("=" * 60)
    print("  BAYESIAN DRIFT MODEL STATUS")
    print("=" * 60)

    # ── Posterior file ────────────────────────────────────────────
    posterior = _load_posterior()
    if posterior is None:
        print("  STATUS: NO POSTERIOR FILE — using flat prior")
        print(f"  Expected at: {POSTERIOR_PATH}")
        print()
        print("  The model has not yet accumulated any live drift bets.")
        print("  Posterior will be created automatically after the first")
        print("  settled live drift bet.")
        print()
        print("  Static sigmoid (sensitivity=300, intercept=0) active.")
        print("=" * 60)
        return 1

    n_obs = posterior.get("n_observations", 0)
    n_wins = posterior.get("n_wins", 0)
    sensitivity = posterior.get("sensitivity", math.exp(posterior.get("log_sensitivity_mean", math.log(300))))
    intercept = posterior.get("intercept_mean", 0.0)
    uncertainty = posterior.get("posterior_uncertainty", 1.0)
    kelly_scale = posterior.get("kelly_scale", 1.0)
    win_rate = posterior.get("win_rate", 0.0)
    log_s_var = posterior.get("log_sensitivity_var", 1.0)
    intercept_var = posterior.get("intercept_var", 0.25)

    override_active = n_obs >= MIN_OBS_FOR_OVERRIDE

    # Status banner
    if override_active:
        status = "ACTIVE — Bayesian predictions overriding static sigmoid"
    else:
        remaining = MIN_OBS_FOR_OVERRIDE - n_obs
        status = f"WARMING UP — {remaining} more live drift bets needed to activate"

    print(f"  STATUS: {status}")
    print()

    # Core posterior stats
    print(f"  Observations:    {n_obs:4d}  (wins: {n_wins}, WR: {win_rate:.1%})")
    print(f"  Sensitivity:     {sensitivity:.1f}  (prior: 300.0)")
    delta_s = sensitivity - 300.0
    direction_s = "↑ market more responsive to drift" if delta_s > 5 else ("↓ market less responsive" if delta_s < -5 else "≈ matches prior")
    print(f"    Shift:         {delta_s:+.1f}  ({direction_s})")
    print()
    print(f"  Intercept:       {intercept:+.4f}  (prior: 0.0)")
    if intercept > 0.02:
        print(f"    Bias:          Bullish — model has learnt upward drift edge")
    elif intercept < -0.02:
        print(f"    Bias:          Bearish — model has learnt downward drift edge")
    else:
        print(f"    Bias:          Neutral — no systematic directional bias")
    print()

    # Uncertainty / posterior width
    prior_uncertainty = 1.0  # by definition at prior
    uncertainty_reduction = max(0.0, 1.0 - uncertainty / prior_uncertainty)
    print(f"  Uncertainty:     {uncertainty:.4f}  (prior: 1.0)")
    print(f"    Reduction:     {uncertainty_reduction:.1%}  {'← posterior narrowing' if uncertainty_reduction > 0.05 else '← still at prior'}")
    print(f"    Log-S var:     {log_s_var:.4f}  (prior: 1.000)")
    print(f"    Intercept var: {intercept_var:.4f}  (prior: 0.250)")
    print()

    # Kelly scale
    print(f"  Kelly scale:     {kelly_scale:.3f}  (1.0 = full Kelly, 0.25 = max conservative)")
    if kelly_scale < 0.5:
        print(f"    WARNING: Low kelly_scale — posterior uncertainty is high.")
        print(f"    This reduces bet sizes automatically until model stabilises.")
    elif kelly_scale > 0.9:
        print(f"    Healthy: model has strong conviction.")
    print()

    # DB cross-check
    db_counts = _count_live_drift_bets()
    if db_counts:
        print("  Live drift bets by strategy (DB):")
        total_db = 0
        for strat, stats in sorted(db_counts.items()):
            wr_str = f"{stats['wins']/stats['n']:.1%}" if stats['n'] > 0 else "n/a"
            print(f"    {strat:20s}  {stats['n']:4d} settled  WR={wr_str}")
            total_db += stats['n']
        print(f"    {'TOTAL':20s}  {total_db:4d} settled")
        if n_obs != total_db:
            diff = total_db - n_obs
            print(f"    NOTE: posterior n={n_obs} != DB total={total_db} (diff={diff:+d})")
            print(f"    This is expected if some bets pre-date the Bayesian wiring (Dim 3, S99).")
    print()

    # Interpretation
    print("  Interpretation:")
    if override_active:
        print(f"    Bayesian model IS active — generate_signal() uses predict() for drift strategies.")
        print(f"    Static sigmoid was sensitivity=300; model is now {sensitivity:.0f}.")
        if abs(delta_s) > 20:
            print(f"    The {abs(delta_s):.0f}-point sensitivity shift suggests live markets behave")
            print(f"    {'more' if delta_s > 0 else 'less'} strongly than paper data predicted.")
    else:
        print(f"    Static sigmoid still active. Bayesian model will activate at {MIN_OBS_FOR_OVERRIDE} observations.")
        print(f"    {n_obs} observations accumulated so far — {MIN_OBS_FOR_OVERRIDE - n_obs} more needed.")
    print("=" * 60)

    return 0 if override_active else 1


if __name__ == "__main__":
    sys.exit(main())
