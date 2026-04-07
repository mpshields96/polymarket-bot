"""
sports_analytics.py — Kalshi Sports Bet Performance Analytics
==============================================================
Ported from agentic-rd-sandbox/core/analytics.py (457 LOC)
         and agentic-rd-sandbox/core/calibration.py (401 LOC)

Design principles (same as sandbox):
  - All analytics functions accept list[dict] — source-agnostic.
  - Calibration reads from polymarket-bot's trades DB.
  - Zero external dependencies beyond stdlib.

DB adaptation notes (vs sandbox):
  - Sandbox: bet_log table, result='W'/'L', pnl float, sharp_score col present.
  - Kalshi:  trades table, result='yes'/'no', side='yes'/'no',
             pnl_cents int, no sharp_score col.
  - Win determination: side == result → win.
  - Callers normalise to {result:'win'/'loss', profit:float, stake:float}
    before passing bets list. Calibration does its own normalisation from DB.

Functions:
  get_bet_counts                  — resolved/pending/total (sample-size guard)
  compute_sharp_roi_correlation   — sharp score bins vs ROI + Pearson r
  compute_equity_curve            — cumulative P&L series + max drawdown
  compute_rolling_metrics         — 7/30/90-day win rate + ROI
  compute_strategy_breakdown      — per-strategy ROI and volume (replaces book breakdown)
  CalibrationReport               — dataclass for calibration pipeline output
  get_calibration_report          — loads from trades DB, computes Brier/AUC/bins
  calibration_is_ready            — fast gate check
  generate_sports_performance_report — full text summary for /polybot-wrap

Sample-size guard:
  MIN_RESOLVED = 10 — returned in every result as "min_required".
  status="inactive" and analytics values omitted when n_resolved < MIN_RESOLVED.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MIN_RESOLVED: int = 10
MIN_BETS_FOR_CALIBRATION: int = 10
N_CALIBRATION_BINS: int = 10
DEFAULT_DB_PATH: str = "data/polybot.db"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolved(bets: list[dict]) -> list[dict]:
    """Return only win/loss rows (not pending/void)."""
    return [b for b in bets if b.get("result") in ("win", "loss")]


def _pearson_r(xs: list[float], ys: list[float]) -> Optional[float]:
    """Pearson correlation coefficient. Returns None if <3 pairs or zero variance."""
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return num / (denom_x * denom_y)


def _roi(bets: list[dict]) -> float:
    """ROI% for a list of resolved bets. Returns 0.0 for empty/unstaked."""
    resolved = _resolved(bets)
    if not resolved:
        return 0.0
    total_profit = sum(b.get("profit", 0.0) for b in resolved)
    total_stake = sum(b.get("stake", 0.0) for b in resolved)
    if total_stake <= 0:
        return 0.0
    return round(total_profit / total_stake * 100, 2)


def _win_rate(bets: list[dict]) -> float:
    """Win rate% for resolved bets."""
    resolved = _resolved(bets)
    if not resolved:
        return 0.0
    wins = sum(1 for b in resolved if b.get("result") == "win")
    return round(wins / len(resolved) * 100, 1)


# ---------------------------------------------------------------------------
# Sample-size guard
# ---------------------------------------------------------------------------

def get_bet_counts(bets: list[dict]) -> dict:
    """
    Return counts by status — used by callers to render sample-size guards.

    Returns:
        {
          "total": int,
          "resolved": int,
          "pending": int,
          "wins": int,
          "losses": int,
          "min_required": int
        }
    """
    resolved = _resolved(bets)
    return {
        "total": len(bets),
        "resolved": len(resolved),
        "pending": sum(1 for b in bets if b.get("result") not in ("win", "loss")),
        "wins": sum(1 for b in resolved if b.get("result") == "win"),
        "losses": sum(1 for b in resolved if b.get("result") == "loss"),
        "min_required": MIN_RESOLVED,
    }


# ---------------------------------------------------------------------------
# Core analytics functions
# ---------------------------------------------------------------------------

def compute_sharp_roi_correlation(bets: list[dict]) -> dict:
    """
    Bin resolved bets by sharp_score and compute ROI per bin.

    Bins: [0-20), [20-40), [40-60), [60-80), [80-100]
    Each bet dict must have: sharp_score (int/float), result, profit, stake.

    Returns:
        {
          "status": "active" | "inactive",
          "n_resolved": int,
          "min_required": int,
          "bins": [{"label": str, "n": int, "roi_pct": float, "win_rate": float}, ...],
          "correlation_r": float | None,
          "correlation_label": str,
          "mean_score_winners": float,
          "mean_score_losers": float,
        }
    """
    resolved = _resolved(bets)
    n_resolved = len(resolved)

    base = {
        "status": "inactive",
        "n_resolved": n_resolved,
        "min_required": MIN_RESOLVED,
        "bins": [],
        "correlation_r": None,
        "correlation_label": "insufficient data",
        "mean_score_winners": 0.0,
        "mean_score_losers": 0.0,
    }

    if n_resolved < MIN_RESOLVED:
        return base

    bin_edges = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
    bin_labels = ["0-20", "20-40", "40-60", "60-80", "80-100"]
    bins = []

    for (lo, hi), label in zip(bin_edges, bin_labels):
        bucket = [b for b in resolved if lo <= b.get("sharp_score", 0) < hi]
        bins.append({
            "label": label,
            "n": len(bucket),
            "roi_pct": _roi(bucket) if bucket else 0.0,
            "win_rate": _win_rate(bucket) if bucket else 0.0,
        })

    xs = [float(b.get("sharp_score", 0)) for b in resolved]
    ys = [1.0 if b.get("result") == "win" else 0.0 for b in resolved]
    r = _pearson_r(xs, ys)

    def _label(r_val: Optional[float]) -> str:
        if r_val is None:
            return "insufficient data"
        if r_val >= 0.5:
            return "strong positive"
        if r_val >= 0.3:
            return "moderate positive"
        if r_val >= 0.1:
            return "weak positive"
        if r_val >= -0.1:
            return "no correlation"
        if r_val >= -0.3:
            return "weak negative"
        if r_val >= -0.5:
            return "moderate negative"
        return "strong negative"

    winners = [b for b in resolved if b.get("result") == "win"]
    losers = [b for b in resolved if b.get("result") == "loss"]
    mean_w = sum(b.get("sharp_score", 0) for b in winners) / len(winners) if winners else 0.0
    mean_l = sum(b.get("sharp_score", 0) for b in losers) / len(losers) if losers else 0.0

    return {
        "status": "active",
        "n_resolved": n_resolved,
        "min_required": MIN_RESOLVED,
        "bins": bins,
        "correlation_r": round(r, 4) if r is not None else None,
        "correlation_label": _label(r),
        "mean_score_winners": round(mean_w, 1),
        "mean_score_losers": round(mean_l, 1),
    }


def compute_equity_curve(bets: list[dict]) -> dict:
    """
    Cumulative P&L series sorted by logged_at.

    Each bet dict must have: logged_at (str), result, profit.

    Returns:
        {
          "dates": list[str],
          "cumulative_pnl": list[float],
          "max_drawdown": float,
          "final_pnl": float,
          "n": int,
        }
    """
    resolved = sorted(_resolved(bets), key=lambda b: b.get("logged_at", ""))
    if not resolved:
        return {"dates": [], "cumulative_pnl": [], "max_drawdown": 0.0, "final_pnl": 0.0, "n": 0}

    cumulative = []
    running = 0.0
    peak = 0.0
    max_dd = 0.0

    for b in resolved:
        running += b.get("profit", 0.0)
        cumulative.append(round(running, 3))
        if running > peak:
            peak = running
        drawdown = peak - running
        if drawdown > max_dd:
            max_dd = drawdown

    return {
        "dates": [b.get("logged_at", "") for b in resolved],
        "cumulative_pnl": cumulative,
        "max_drawdown": round(max_dd, 3),
        "final_pnl": round(running, 3),
        "n": len(resolved),
    }


def compute_rolling_metrics(bets: list[dict], windows: tuple = (7, 30, 90)) -> dict:
    """
    Rolling win rate and ROI for given day windows.

    Each bet dict must have: logged_at (ISO str), result, profit, stake.

    Returns dict keyed by window size:
        {7: {"n": int, "win_rate": float, "roi_pct": float}, 30: {...}, 90: {...}}
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    result = {}

    for days in windows:
        cutoff = (now - timedelta(days=days)).isoformat()
        window_bets = [b for b in bets if b.get("logged_at", "") >= cutoff]
        result[days] = {
            "n": len(_resolved(window_bets)),
            "win_rate": _win_rate(window_bets),
            "roi_pct": _roi(window_bets),
        }

    return result


def compute_strategy_breakdown(bets: list[dict]) -> list[dict]:
    """
    Per-strategy ROI, volume, and win rate for resolved bets.
    Replaces book_breakdown from sandbox (Kalshi has no book field, uses strategy).

    Each bet dict must have: strategy (str), result, profit, stake.

    Returns list sorted by roi_pct descending:
        [{"strategy": str, "n": int, "win_rate": float, "roi_pct": float}, ...]
    """
    resolved = _resolved(bets)
    strategies: dict[str, list] = {}

    for b in resolved:
        strat = b.get("strategy", "").strip() or "Unknown"
        strategies.setdefault(strat, []).append(b)

    rows = []
    for strat, strat_bets in strategies.items():
        rows.append({
            "strategy": strat,
            "n": len(strat_bets),
            "win_rate": _win_rate(strat_bets),
            "roi_pct": _roi(strat_bets),
        })

    rows.sort(key=lambda r: r["roi_pct"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Calibration dataclasses
# ---------------------------------------------------------------------------

@dataclass
class CalibrationBin:
    """One bin of the calibration curve."""
    prob_low: float
    prob_high: float
    predicted: float
    actual: float
    count: int

    @property
    def calibration_error(self) -> float:
        """Absolute gap between predicted and actual."""
        return abs(self.predicted - self.actual)


@dataclass
class CalibrationReport:
    """
    Full calibration report.

    is_active:      False if not enough graded bets yet.
    bets_total:     Total graded bets in DB.
    bets_wins:      Confirmed wins.
    bets_needed_for_activation: 0 when active.
    brier_score:    Mean squared error (lower = better; perfect = 0.0).
    roc_auc:        Area under ROC curve (0.5 = random; 1.0 = perfect).
    mean_edge_accuracy: Mean |predicted_edge - realized_edge| in pct points.
    calibration_bins: List of CalibrationBin.
    sharp_score_vs_wr: Dict of {sharp_tier: win_rate}.
    notes:          Human-readable diagnostics.
    """
    is_active: bool
    bets_total: int
    bets_wins: int
    bets_needed_for_activation: int
    brier_score: float = 0.0
    roc_auc: float = 0.0
    mean_edge_accuracy: float = 0.0
    calibration_bins: list = field(default_factory=list)
    sharp_score_vs_wr: dict = field(default_factory=dict)
    notes: str = ""


# ---------------------------------------------------------------------------
# Calibration math helpers (stdlib only)
# ---------------------------------------------------------------------------

def _brier_score(win_probs: list[float], outcomes: list[int]) -> float:
    """Mean squared error of predicted prob vs binary outcome. Lower = better."""
    if not win_probs:
        return 0.0
    total = sum((p - o) ** 2 for p, o in zip(win_probs, outcomes))
    return total / len(win_probs)


def _roc_auc(win_probs: list[float], outcomes: list[int]) -> float:
    """
    ROC AUC via Wilcoxon-Mann-Whitney statistic (no sklearn).
    Returns 0.5 for random classifier, 1.0 for perfect.
    """
    if not win_probs or sum(outcomes) == 0 or sum(outcomes) == len(outcomes):
        return 0.5

    positives = [p for p, o in zip(win_probs, outcomes) if o == 1]
    negatives = [p for p, o in zip(win_probs, outcomes) if o == 0]

    if not positives or not negatives:
        return 0.5

    concordant = 0.0
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                concordant += 1.0
            elif pos == neg:
                concordant += 0.5

    auc = concordant / (len(positives) * len(negatives))
    return round(min(1.0, max(0.0, auc)), 4)


def _calibration_bins_compute(
    win_probs: list[float],
    outcomes: list[int],
    n_bins: int = N_CALIBRATION_BINS,
) -> list[CalibrationBin]:
    """Bin predictions into n_bins equal-width probability buckets."""
    bins: dict[int, list] = {i: [] for i in range(n_bins)}
    bin_width = 1.0 / n_bins

    for prob, outcome in zip(win_probs, outcomes):
        bin_idx = min(n_bins - 1, int(prob / bin_width))
        bins[bin_idx].append((prob, outcome))

    result = []
    for i in range(n_bins):
        entries = bins[i]
        if not entries:
            continue
        prob_low = i * bin_width
        prob_high = (i + 1) * bin_width
        predicted = sum(p for p, _ in entries) / len(entries)
        actual = sum(o for _, o in entries) / len(entries)
        result.append(CalibrationBin(
            prob_low=round(prob_low, 2),
            prob_high=round(prob_high, 2),
            predicted=round(predicted, 4),
            actual=round(actual, 4),
            count=len(entries),
        ))
    return result


def _sharp_score_win_rates(
    sharp_scores: list[float],
    outcomes: list[int],
) -> dict[str, float]:
    """Win rates by sharp score tier: <45, 45-55, 55-65, 65-75, 75+. Min 3 bets per tier."""
    tiers: dict[str, list[int]] = {"<45": [], "45-55": [], "55-65": [], "65-75": [], "75+": []}
    for score, outcome in zip(sharp_scores, outcomes):
        if score < 45:
            tiers["<45"].append(outcome)
        elif score < 55:
            tiers["45-55"].append(outcome)
        elif score < 65:
            tiers["55-65"].append(outcome)
        elif score < 75:
            tiers["65-75"].append(outcome)
        else:
            tiers["75+"].append(outcome)

    result = {}
    for label, outcomes_list in tiers.items():
        if len(outcomes_list) >= 3:
            result[label] = round(sum(outcomes_list) / len(outcomes_list), 4)
    return result


def _mean_edge_accuracy(predicted_edges: list[float], outcomes: list[int]) -> float:
    """Mean |predicted_edge - realized_edge| in pct points."""
    if not predicted_edges:
        return 0.0
    total_error = 0.0
    for pred_edge, outcome in zip(predicted_edges, outcomes):
        market_implied = 1.0 - pred_edge
        realized_edge = outcome - market_implied
        total_error += abs(pred_edge - realized_edge)
    return round(total_error / len(predicted_edges), 4)


# ---------------------------------------------------------------------------
# Calibration DB loader — adapted for polymarket-bot trades table
# ---------------------------------------------------------------------------

def _load_graded_trades(db_path: str) -> list[dict]:
    """
    Load settled trades from polybot.db trades table.

    A trade is graded when result is 'yes' or 'no' (settled, not None).
    Win = (side == result). Normalises to {win_prob, edge_pct, result:'W'/'L',
    stake_usd, pnl_usd, sharp_score:0.0 (not stored in trades)}.

    Returns [] if DB doesn't exist or query fails.
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT side, result, win_prob, edge_pct, cost_usd, pnl_cents
            FROM trades
            WHERE result IN ('yes', 'no')
              AND win_prob IS NOT NULL
              AND edge_pct IS NOT NULL
        """)
        rows = []
        for r in cur.fetchall():
            outcome = "W" if r["side"] == r["result"] else "L"
            rows.append({
                "result": outcome,
                "win_prob": float(r["win_prob"]),
                "edge_pct": float(r["edge_pct"]),
                "stake": float(r["cost_usd"] or 0.0),
                "pnl": float((r["pnl_cents"] or 0) / 100.0),
                "sharp_score": 0.0,  # not stored in trades table
            })
        conn.close()
        return rows
    except Exception:
        return []


def _count_graded_trades(db_path: str) -> int:
    """Count settled trades without loading full dataset."""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM trades WHERE result IN ('yes', 'no')")
        count = cur.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Calibration main entry point
# ---------------------------------------------------------------------------

def get_calibration_report(db_path: str = DEFAULT_DB_PATH) -> CalibrationReport:
    """
    Load settled trades from DB and compute calibration metrics.

    Returns CalibrationReport with is_active=False when fewer than
    MIN_BETS_FOR_CALIBRATION settled trades exist.
    """
    rows = _load_graded_trades(db_path)
    n = len(rows)

    if n < MIN_BETS_FOR_CALIBRATION:
        return CalibrationReport(
            is_active=False,
            bets_total=n,
            bets_wins=sum(1 for r in rows if r["result"] == "W"),
            bets_needed_for_activation=max(0, MIN_BETS_FOR_CALIBRATION - n),
            notes=(
                f"Calibration inactive: {n}/{MIN_BETS_FOR_CALIBRATION} settled trades. "
                f"Need {MIN_BETS_FOR_CALIBRATION - n} more resolved bets."
            ),
        )

    win_probs = [r["win_prob"] for r in rows]
    outcomes = [1 if r["result"] == "W" else 0 for r in rows]
    edge_pcts = [r["edge_pct"] for r in rows]
    sharp_scores = [r.get("sharp_score", 0.0) for r in rows]
    n_wins = sum(outcomes)

    brier = _brier_score(win_probs, outcomes)
    auc = _roc_auc(win_probs, outcomes)
    bins = _calibration_bins_compute(win_probs, outcomes)
    tier_rates = _sharp_score_win_rates(sharp_scores, outcomes)
    edge_acc = _mean_edge_accuracy(edge_pcts, outcomes)

    ece = sum(b.calibration_error * b.count for b in bins) / n if bins else 0.0

    notes = (
        f"Calibration active: {n} settled trades ({n_wins} wins, {n - n_wins} losses). "
        f"Brier={brier:.4f} | AUC={auc:.3f} | ECE={ece:.4f}. "
    )
    if auc >= 0.65:
        notes += "Model shows good discrimination."
    elif auc >= 0.55:
        notes += "Model shows moderate discrimination."
    else:
        notes += "Low AUC — model edge detection needs review."

    return CalibrationReport(
        is_active=True,
        bets_total=n,
        bets_wins=n_wins,
        bets_needed_for_activation=0,
        brier_score=round(brier, 6),
        roc_auc=round(auc, 4),
        mean_edge_accuracy=round(edge_acc, 4),
        calibration_bins=bins,
        sharp_score_vs_wr=tier_rates,
        notes=notes,
    )


def calibration_is_ready(db_path: str = DEFAULT_DB_PATH) -> bool:
    """Fast check: does the DB have enough settled trades to activate calibration?"""
    return _count_graded_trades(db_path) >= MIN_BETS_FOR_CALIBRATION


# ---------------------------------------------------------------------------
# generate_sports_performance_report — /polybot-wrap entry point
# ---------------------------------------------------------------------------

def generate_sports_performance_report(
    bets: list[dict],
    db_path: str = DEFAULT_DB_PATH,
    include_calibration: bool = True,
) -> str:
    """
    Full text performance report for sports bets. Wire into /polybot-wrap output.

    Args:
        bets: list of bet dicts with keys:
              result ('win'/'loss'), profit (float), stake (float),
              logged_at (ISO str), sharp_score (float, optional),
              strategy (str, optional).
        db_path: path to polybot.db for calibration.
        include_calibration: if False, skip DB query (faster, offline mode).

    Returns:
        Multi-line string report suitable for terminal output.
    """
    lines = ["=== SPORTS PERFORMANCE REPORT ==="]

    counts = get_bet_counts(bets)
    lines.append(
        f"Bets: {counts['total']} total | {counts['resolved']} resolved "
        f"({counts['wins']}W/{counts['losses']}L) | {counts['pending']} pending"
    )

    if counts["resolved"] < MIN_RESOLVED:
        lines.append(
            f"[Insufficient data — need {MIN_RESOLVED - counts['resolved']} more resolved bets]"
        )
        if include_calibration:
            cal = get_calibration_report(db_path)
            if not cal.is_active:
                lines.append(f"Calibration: {cal.notes}")
        return "\n".join(lines)

    # Rolling metrics
    rolling = compute_rolling_metrics(bets)
    lines.append("")
    lines.append("ROLLING PERFORMANCE:")
    for days, m in rolling.items():
        if m["n"] > 0:
            lines.append(f"  {days:>2}d: {m['n']} bets | WR {m['win_rate']:.1f}% | ROI {m['roi_pct']:+.2f}%")
        else:
            lines.append(f"  {days:>2}d: no resolved bets")

    # Equity curve
    curve = compute_equity_curve(bets)
    if curve["n"] > 0:
        lines.append("")
        lines.append("EQUITY CURVE:")
        lines.append(f"  Final P&L: {curve['final_pnl']:+.2f} USD")
        lines.append(f"  Max drawdown: {curve['max_drawdown']:.2f} USD")

    # Sharp score correlation
    sharp_corr = compute_sharp_roi_correlation(bets)
    if sharp_corr["status"] == "active" and sharp_corr["correlation_r"] is not None:
        lines.append("")
        lines.append("SHARP SCORE CORRELATION:")
        lines.append(
            f"  r={sharp_corr['correlation_r']:.3f} ({sharp_corr['correlation_label']}) | "
            f"Avg score winners={sharp_corr['mean_score_winners']:.0f} losers={sharp_corr['mean_score_losers']:.0f}"
        )
        for b in sharp_corr["bins"]:
            if b["n"] > 0:
                lines.append(f"  [{b['label']}]: {b['n']} bets | WR {b['win_rate']:.0f}% | ROI {b['roi_pct']:+.1f}%")

    # Strategy breakdown
    strat_rows = compute_strategy_breakdown(bets)
    if strat_rows:
        lines.append("")
        lines.append("STRATEGY BREAKDOWN:")
        for row in strat_rows:
            lines.append(
                f"  {row['strategy']}: {row['n']} bets | WR {row['win_rate']:.1f}% | ROI {row['roi_pct']:+.2f}%"
            )

    # Calibration
    if include_calibration:
        lines.append("")
        lines.append("CALIBRATION:")
        cal = get_calibration_report(db_path)
        if cal.is_active:
            lines.append(
                f"  Brier={cal.brier_score:.4f} | AUC={cal.roc_auc:.3f} | "
                f"EdgeAcc={cal.mean_edge_accuracy:.4f}"
            )
            lines.append(f"  {cal.notes}")
            if cal.sharp_score_vs_wr:
                tier_str = " | ".join(
                    f"{t}: {wr:.0%}" for t, wr in cal.sharp_score_vs_wr.items()
                )
                lines.append(f"  WR by tier: {tier_str}")
        else:
            lines.append(f"  {cal.notes}")

    lines.append("")
    lines.append("=== END REPORT ===")
    return "\n".join(lines)
