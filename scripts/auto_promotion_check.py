"""
Auto-promotion check for paper-only trading strategies.

JOB:    At session start, scan DB for paper strategies that have hit all
        graduation gate criteria. If any are ready, send a Reminders alert
        and append a recommendation to .planning/CHANGELOG.md.

RUNS:   python3 scripts/auto_promotion_check.py
        Exit code 0 = healthy (no action needed), 1 = promotion recommended

GATES (must ALL be met):
    1. n_settled_bets >= MIN_BETS (default 20, paper bets)
    2. brier_score < MAX_BRIER (default 0.30)
    3. win_rate > break_even_wr (strategy-specific)
    4. No structural YES/NO asymmetry (neither YES WR nor NO WR < 40%)

DOES NOT:
    - Modify main.py or config.yaml automatically
    - Promote without human sign-off (sends alert instead)
    - Block or pause the strategy being evaluated

WHY HUMAN SIGN-OFF:
    Promotion from paper to live involves real money. The script provides
    statistical evidence for a decision; the human confirms.
    Exception: when OOS auto-promotion is explicitly enabled (future Dim 4.1).
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"
CHANGELOG_PATH = PROJ / ".planning" / "CHANGELOG.md"

# Gate thresholds
MIN_BETS = 20               # minimum paper-settled bets
MAX_BRIER = 0.30            # maximum acceptable Brier score
MIN_DIRECTIONAL_WR = 0.40   # neither YES-only nor NO-only WR below this (detects asymmetry)

# Strategies that are already live — skip these
_ALREADY_LIVE = {
    "btc_drift_v1",
    "eth_drift_v1",
    "sol_drift_v1",
    "xrp_drift_v1",
    "expiry_sniper_v1",
}

# Strategies with known reasons NOT to promote (documented dead ends)
_SKIP_REASONS = {
    "btc_lag_v1": "Dead signal: HFTs price faster than our latency",
    "eth_lag_v1": "Returning to calibration — Brier was high",
    "weather_forecast_v1": "Weather (ALL weather) is a confirmed dead end",
}

# Break-even win rate by strategy name (overrides default 50%)
# For binary 50/50 markets the break-even is 50%, but for biased markets we compute.
# These are for the paper output Brier signals — use 50% as conservative default.
_STRATEGY_BREAK_EVEN_WR: dict[str, float] = {
    "orderbook_imbalance_v1": 0.50,
    "eth_orderbook_imbalance_v1": 0.50,
    "fomc_rate_v1": 0.50,
    "unemployment_rate_v1": 0.50,
}


def _brier_score(predictions: list[float], outcomes: list[int]) -> float:
    """Compute Brier score: mean(prediction - outcome)^2. Lower is better."""
    if not predictions:
        return float("nan")
    total = sum((p - o) ** 2 for p, o in zip(predictions, outcomes))
    return total / len(predictions)


def evaluate_strategies() -> list[dict]:
    """
    Query DB for paper strategy performance and evaluate graduation gates.
    Returns list of strategy dicts with 'ready' flag and gate details.
    """
    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))

    # Paper trades: WR, side distribution (win_prob is NULL for paper, so Brier from live only)
    rows = conn.execute("""
        SELECT strategy,
               COUNT(*) as n,
               SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
               SUM(CASE WHEN side='yes' AND result='yes' THEN 1 ELSE 0 END) as yes_wins,
               SUM(CASE WHEN side='no' AND result='no' THEN 1 ELSE 0 END) as no_wins,
               SUM(CASE WHEN side='yes' THEN 1 ELSE 0 END) as yes_bets,
               SUM(CASE WHEN side='no' THEN 1 ELSE 0 END) as no_bets
        FROM trades
        WHERE is_paper = 1
          AND result IS NOT NULL
          AND strategy NOT IN ('expiry_sniper_v1')
        GROUP BY strategy
        HAVING COUNT(*) >= 5
        ORDER BY strategy
    """).fetchall()

    # Live trades: Brier score (win_prob is stored for live bets)
    live_rows = conn.execute("""
        SELECT strategy,
               GROUP_CONCAT(win_prob, ',') as win_probs,
               GROUP_CONCAT(CASE WHEN side=result THEN 1 ELSE 0 END, ',') as outcomes,
               COUNT(*) as n_live
        FROM trades
        WHERE is_paper = 0
          AND result IS NOT NULL
          AND win_prob IS NOT NULL
          AND strategy NOT IN ('expiry_sniper_v1')
        GROUP BY strategy
    """).fetchall()
    live_brier: dict[str, float] = {}
    for strat, wp_str, out_str, n_live in live_rows:
        try:
            probs = [float(p) for p in wp_str.split(",") if p and p != "None"]
            outs = [int(o) for o in out_str.split(",") if o and o != "None"]
            if probs and outs and len(probs) == len(outs):
                live_brier[strat] = _brier_score(probs, outs)
        except (ValueError, AttributeError):
            pass
    conn.close()

    results = []
    for row in rows:
        strat, n, wins, yes_wins, no_wins, yes_bets, no_bets = row

        # Skip already-live strategies
        if strat in _ALREADY_LIVE:
            continue

        # Brier: use live bet history if available (paper trades have NULL win_prob)
        brier = live_brier.get(strat, float("nan"))

        wr = wins / n if n > 0 else 0.0
        yes_wr = yes_wins / yes_bets if yes_bets > 0 else None
        no_wr = no_wins / no_bets if no_bets > 0 else None

        # Evaluate gates
        skip_reason = _SKIP_REASONS.get(strat)
        if skip_reason:
            results.append({
                "strategy": strat, "n": n, "wins": wins, "wr": wr,
                "brier": brier, "ready": False,
                "skip_reason": skip_reason,
                "gate_summary": f"SKIPPED: {skip_reason}",
            })
            continue

        break_even = _STRATEGY_BREAK_EVEN_WR.get(strat, 0.50)
        gate_n = n >= MIN_BETS
        gate_brier = not math.isnan(brier) and brier < MAX_BRIER
        gate_wr = wr > break_even
        gate_asymmetry = True
        asymmetry_note = ""
        # Only check directional WR if the strategy has placed BOTH YES and NO bets.
        # One-sided strategies (e.g. imbalance always bets NO) skip this gate.
        if yes_bets >= 5 and no_bets >= 5:
            if yes_wr is not None and yes_wr < MIN_DIRECTIONAL_WR:
                gate_asymmetry = False
                asymmetry_note = f"YES WR={yes_wr:.1%} < {MIN_DIRECTIONAL_WR:.0%}"
            if no_wr is not None and no_wr < MIN_DIRECTIONAL_WR:
                gate_asymmetry = False
                asymmetry_note += f" NO WR={no_wr:.1%} < {MIN_DIRECTIONAL_WR:.0%}"

        all_gates = gate_n and gate_brier and gate_wr and gate_asymmetry

        failures = []
        if not gate_n:
            failures.append(f"n={n} < {MIN_BETS}")
        if not gate_brier:
            brier_str = f"{brier:.3f}" if not math.isnan(brier) else "n/a"
            failures.append(f"Brier={brier_str} >= {MAX_BRIER}")
        if not gate_wr:
            failures.append(f"WR={wr:.1%} <= {break_even:.1%} break-even")
        if not gate_asymmetry:
            failures.append(f"Directional asymmetry: {asymmetry_note.strip()}")

        gate_summary = "READY FOR PROMOTION" if all_gates else ("FAILING: " + " | ".join(failures))

        results.append({
            "strategy": strat, "n": n, "wins": wins, "wr": wr,
            "brier": brier, "yes_wr": yes_wr, "no_wr": no_wr,
            "ready": all_gates,
            "gate_n": gate_n, "gate_brier": gate_brier,
            "gate_wr": gate_wr, "gate_asymmetry": gate_asymmetry,
            "gate_summary": gate_summary,
            "break_even": break_even,
        })

    return results


def _send_reminders_alert(strategy: str, n: int, brier: float, wr: float) -> None:
    """Send macOS Reminders alert for promotion-ready strategy."""
    brier_str = f"{brier:.3f}" if not math.isnan(brier) else "n/a"
    message = (
        f"POLYBOT PROMOTION ALERT: {strategy} is ready for live promotion. "
        f"n={n}, Brier={brier_str}, WR={wr:.1%}. "
        f"Run --graduation-status and flip live_executor_enabled=True in main.py after pre-live audit."
    )
    try:
        subprocess.run([
            "osascript", "-e",
            f'tell application "Reminders" to make new reminder with properties '
            f'{{name:"{message}", due date:current date}}'
        ], check=True, capture_output=True, timeout=10)
    except Exception:
        pass  # Reminders alert is best-effort; don't fail the script


def _append_to_changelog(strategy: str, n: int, brier: float, wr: float) -> None:
    """Append promotion recommendation to CHANGELOG.md."""
    if not CHANGELOG_PATH.exists():
        return
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    brier_str = f"{brier:.3f}" if not math.isnan(brier) else "n/a"
    entry = (
        f"\n## AUTO-PROMOTION ALERT — {ts}\n"
        f"Strategy `{strategy}` has met ALL graduation gates.\n"
        f"  n={n}, Brier={brier_str}, WR={wr:.1%}\n"
        f"ACTION NEEDED: Run `--graduation-status` and flip `live_executor_enabled=True`\n"
        f"  in main.py ONLY after completing the pre-live audit checklist (CLAUDE.md Step 5).\n"
    )
    try:
        with open(CHANGELOG_PATH, "a") as f:
            f.write(entry)
    except OSError:
        pass


def main() -> int:
    print("=" * 60)
    print("  AUTO-PROMOTION CHECK")
    print("=" * 60)

    results = evaluate_strategies()

    if not results:
        print("  No paper strategies with 5+ settled bets found.")
        print("=" * 60)
        return 0

    ready = [r for r in results if r.get("ready")]
    not_ready = [r for r in results if not r.get("ready") and not r.get("skip_reason")]
    skipped = [r for r in results if r.get("skip_reason")]

    # Print all statuses
    for r in results:
        brier_str = f"{r['brier']:.3f}" if not math.isnan(r.get("brier", float("nan"))) else "  n/a"
        if r.get("skip_reason"):
            print(f"  SKIP  {r['strategy']:35s}  n={r['n']:4d}  Brier={brier_str}  WR={r['wr']:.1%}")
            print(f"        Reason: {r['skip_reason']}")
        else:
            status_icon = "READY" if r["ready"] else "-----"
            print(f"  {status_icon}  {r['strategy']:35s}  n={r['n']:4d}  Brier={brier_str}  WR={r['wr']:.1%}")
            if not r["ready"]:
                print(f"        {r['gate_summary']}")
            else:
                print(f"        *** {r['gate_summary']} ***")

    print()

    if ready:
        print(f"  {len(ready)} strategy/strategies ready for promotion:")
        for r in ready:
            print(f"    → {r['strategy']}")
        print()
        print("  ACTION REQUIRED (Claude does NOT auto-promote):")
        print("  1. Run python main.py --graduation-status  (verify manually)")
        print("  2. Complete CLAUDE.md Step 5 pre-live audit checklist")
        print("  3. Flip live_executor_enabled=True in main.py")
        print("  4. Restart bot and watch log for first live bet within 15 min")
        print()
        # Send alert and log
        for r in ready:
            _send_reminders_alert(r["strategy"], r["n"], r["brier"], r["wr"])
            _append_to_changelog(r["strategy"], r["n"], r["brier"], r["wr"])
            print(f"  Reminders alert sent + CHANGELOG.md updated for {r['strategy']}.")
        print("=" * 60)
        return 1

    print("  No strategies ready for promotion at this time.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
