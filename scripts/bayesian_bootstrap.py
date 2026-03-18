"""
Bayesian posterior bootstrap from historical drift bets.

JOB:    Re-seed the Bayesian drift model's posterior using ALL historical live
        settled drift bets (btc/eth/sol/xrp_drift_v1) in chronological order.
        This jump-starts the posterior from n=15 (post-S99 wiring) to n=298+,
        immediately enabling the Bayesian override (requires n>=30).

WHEN TO RUN:
    Once, after Session 103 (n=15). After that, the settlement loop keeps the
    posterior current automatically (Dim 3 wiring). No need to re-run.

    Re-run only if posterior is corrupted or you want to reset and rebuild from DB.

HOW IT WORKS:
    1. Start from a flat prior (paper-calibrated values, same as startup default).
    2. Load all live settled drift bets from DB, oldest-first.
    3. For each bet, reconstruct drift_pct from win_prob via sigmoid inversion:
           logit = log(win_prob / (1 - win_prob))
           drift_pct ≈ logit / current_sensitivity
    4. Update the MAP estimate (same gradient step as settlement_loop).
    5. Save to data/drift_posterior.json — bot picks up on next restart.

MATH NOTE — why this is valid:
    The historical bets were placed by the same sigmoid signal (sensitivity≈300,
    intercept≈0). win_prob encodes the drift_pct at bet time. Inversion gives
    the same drift_pct used to generate the signal. Sequential MAP updates are
    order-dependent but converge to the true posterior regardless of starting n.

    Selection bias: we only have bets above min_drift_pct (threshold). Same bias
    applies to the online updates (n=15) — this is not worse.

USAGE:
    python scripts/bayesian_bootstrap.py              # uses default DB + posterior paths
    python scripts/bayesian_bootstrap.py --dry-run    # show what would happen, no write
    python scripts/bayesian_bootstrap.py --reset      # force reset even if n > 30

EXIT:
    0 = success
    1 = error (DB not found, etc.)
"""

from __future__ import annotations

import argparse
import logging
import math
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).parent.parent
sys.path.insert(0, str(PROJ))

from src.models.bayesian_drift import BayesianDriftModel

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_DB_PATH = PROJ / "data" / "polybot.db"
_POSTERIOR_PATH = PROJ / "data" / "drift_posterior.json"

_DRIFT_STRATEGY_NAMES = frozenset([
    "btc_drift_v1",
    "eth_drift_v1",
    "sol_drift_v1",
    "xrp_drift_v1",
])


def _load_historical_bets(db_path: Path) -> list[dict]:
    """
    Load all live settled drift bets from DB, ordered oldest-first.

    Returns list of dicts with keys: id, strategy, side, win_prob, result.
    Only bets where win_prob is in (0, 1) exclusive are returned — logit
    is undefined at 0 and 1.
    """
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT id, strategy, side, win_prob, result, settled_at
            FROM trades
            WHERE strategy IN (
                'btc_drift_v1', 'eth_drift_v1',
                'sol_drift_v1', 'xrp_drift_v1'
            )
              AND is_paper = 0
              AND result IS NOT NULL
              AND win_prob IS NOT NULL
              AND win_prob > 0.0
              AND win_prob < 1.0
            ORDER BY settled_at ASC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def run_bootstrap(
    db_path: Path = _DB_PATH,
    posterior_path: Path = _POSTERIOR_PATH,
    dry_run: bool = False,
) -> int:
    """
    Core bootstrap logic. Returns number of bets processed.

    Args:
        db_path:        Path to polybot.db.
        posterior_path: Where to write the updated posterior JSON.
        dry_run:        If True, compute but do not write.

    Returns:
        int: Number of bets processed (excluding skipped invalid rows).
    """
    if not db_path.exists():
        logger.error("DB not found: %s", db_path)
        return 0

    bets = _load_historical_bets(db_path)
    logger.info("Loaded %d historical live drift bets from DB.", len(bets))

    if not bets:
        logger.info("No bets to process. Posterior unchanged.")
        return 0

    # Start from flat prior — full reset
    model = BayesianDriftModel()
    logger.info("Starting from flat prior: sensitivity=%.0f, intercept=%.4f",
                model.sensitivity, model.intercept)

    strategy_counts: dict[str, int] = {}
    skipped = 0

    for bet in bets:
        win_prob = bet.get("win_prob") or 0.0
        if win_prob <= 0.0 or win_prob >= 1.0:
            skipped += 1
            continue

        side = bet["side"]
        result = bet["result"]
        strategy = bet["strategy"]

        won = (side == result)  # True if our side matched market result

        # Reconstruct drift_pct via sigmoid inversion
        logit = math.log(win_prob / (1.0 - win_prob))
        drift_pct = logit / model.sensitivity  # uses current MAP estimate

        model.update(drift_pct=drift_pct, side=side, won=won)
        strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

    logger.info(
        "Bootstrap complete: %d observations | WR=%.1f%% | sensitivity=%.1f | "
        "intercept=%.4f | uncertainty=%.3f | kelly_scale=%.2f",
        model.n_observations,
        100 * model.win_rate,
        model.sensitivity,
        model.intercept,
        model.posterior_uncertainty,
        model.kelly_scale,
    )
    if skipped:
        logger.info("Skipped %d bets (invalid win_prob).", skipped)

    for strat, cnt in sorted(strategy_counts.items()):
        logger.info("  %s: %d bets", strat, cnt)

    if model.should_override_static():
        logger.info(
            "Bayesian override NOW ACTIVE (n=%d >= 30). "
            "Bot will use posterior on next restart.",
            model.n_observations,
        )
    else:
        remaining = 30 - model.n_observations
        logger.info(
            "Override not yet active (n=%d, need %d more).",
            model.n_observations, remaining,
        )

    if not dry_run:
        model.save(path=posterior_path)
        logger.info("Posterior saved to: %s", posterior_path)

    return model.n_observations


def _parse_args():
    p = argparse.ArgumentParser(description="Bootstrap Bayesian posterior from DB history.")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute but do not write posterior file.")
    p.add_argument("--reset", action="store_true",
                   help="Force reset even if current posterior has many observations.")
    p.add_argument("--db", type=Path, default=_DB_PATH,
                   help=f"Path to polybot.db (default: {_DB_PATH})")
    p.add_argument("--posterior", type=Path, default=_POSTERIOR_PATH,
                   help=f"Path to drift_posterior.json (default: {_POSTERIOR_PATH})")
    return p.parse_args()


def main() -> int:
    args = _parse_args()

    # Safety check: warn if current posterior already has many observations
    if not args.reset and _POSTERIOR_PATH.exists():
        try:
            import json
            with open(_POSTERIOR_PATH) as f:
                current = json.load(f)
            current_n = current.get("n_observations", 0)
            if current_n >= 30:
                logger.warning(
                    "Current posterior already has n=%d (override active). "
                    "Run with --reset to force re-bootstrap.",
                    current_n,
                )
                return 0
        except Exception:
            pass

    n = run_bootstrap(
        db_path=args.db,
        posterior_path=args.posterior,
        dry_run=args.dry_run,
    )
    return 0 if n >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
