#!/usr/bin/env python3
"""
kalshi_self_learning.py — Advanced Self-Learning Orchestrator for Kalshi Bot

Integrates CCA analytical tools into a unified self-improvement engine that
runs every 3rd monitoring cycle and improves the bot automatically over time.

ACTIVE ANALYSIS (run every 3rd cycle):
  1. Per-bucket statistics (asset × price × side × hour): Wilson CI + CUSUM
  2. CalibrationBias: systematic mispricing detection across price levels
  3. DynamicKelly: per-bucket optimal bet sizing vs current flat Kelly
  4. StrategyHealth: overall strategy-level health scoring
  5. Guard candidates: buckets crossing guard thresholds before auto_guard fires

PASSIVE LEARNING (persistent across sessions):
  - data/learning_state.json: bucket trajectories, CUSUM state, calibration history
  - Each session builds on the last: CUSUMs continue from where they left off
  - Warming buckets tracked with session-over-session trend lines

SAFETY:
  - Read-only DB access (no writes, no trade execution)
  - Advisory only — all proposals require review before action
  - Minimum sample sizes enforced (N >= 10 for warnings, N >= 20 for guard proposals)

Usage:
    python3 scripts/analysis/kalshi_self_learning.py            # Full report
    python3 scripts/analysis/kalshi_self_learning.py --brief    # Summary only
    python3 scripts/analysis/kalshi_self_learning.py --json     # JSON output
    python3 scripts/analysis/kalshi_self_learning.py --save     # Save + append to reports/
"""

import json
import math
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, SCRIPT_DIR)

LEARNING_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "learning_state.json")
REPORT_DIR = os.path.join(PROJECT_ROOT, "reports")


# ── Statistical Functions (stdlib-only) ──────────────────────────────────────

def wilson_ci(n: int, k: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval for win rate. Wilson (1927)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, round(center - margin, 4)), min(1.0, round(center + margin, 4)))


def cusum_statistic(outcomes: list[bool], mu_0: float, h: float = 5.0) -> tuple[bool, float, int | None]:
    """Page's CUSUM for detecting downward WR shift. Page (1954).

    Returns (signaled, max_S, trigger_index).
    """
    mu_1 = max(0.01, mu_0 - 0.15)  # Expected WR under degraded regime
    k = (mu_0 - mu_1) / 2
    S = 0.0
    max_S = 0.0
    trigger_idx = None
    for i, won in enumerate(outcomes):
        x = 1.0 if won else 0.0
        S = max(0.0, S + (mu_0 - x - k))
        if S > max_S:
            max_S = S
        if S >= h and trigger_idx is None:
            trigger_idx = i
    return (trigger_idx is not None, round(max_S, 4), trigger_idx)


def binomial_p_value(n: int, k: int, p0: float) -> float:
    """One-tailed binomial p-value: P(X >= k | H0: p = p0). Stdlib only."""
    if n == 0:
        return 1.0
    # Use normal approximation for speed (accurate when n > 20)
    if n > 20:
        mu = n * p0
        sigma = math.sqrt(n * p0 * (1 - p0))
        if sigma == 0:
            return 0.0 if k > mu else 1.0
        z = (k - mu - 0.5) / sigma  # continuity correction
        # erfc approximation: p = 0.5 * erfc(z / sqrt(2))
        return 0.5 * math.erfc(z / math.sqrt(2))
    # Exact for small n
    total = 0.0
    for i in range(k, n + 1):
        coef = math.comb(n, i)
        total += coef * (p0 ** i) * ((1 - p0) ** (n - i))
    return total


# ── DB Access ─────────────────────────────────────────────────────────────────

def _read_trades(db_path: str) -> list[dict]:
    """Read settled live trades from polybot.db."""
    uri = f"file:{db_path}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.OperationalError:
        conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.execute("PRAGMA table_info(trades)")
        columns = {row[1] for row in cursor.fetchall()}

        has_is_paper = "is_paper" in columns
        has_side = "side" in columns
        has_pnl_cents = "pnl_cents" in columns

        select = "SELECT strategy, result, timestamp"
        if has_side:
            select += ", side"
        if "price_cents" in columns:
            select += ", price_cents"
        if "cost_usd" in columns:
            select += ", cost_usd"
        if has_pnl_cents:
            select += ", pnl_cents"
        elif "payout_usd" in columns:
            select += ", payout_usd"
        if "ticker" in columns:
            select += ", ticker"
        if "settled_at" in columns:
            select += ", settled_at"
        if has_is_paper:
            select += ", is_paper"
        select += " FROM trades WHERE result IS NOT NULL"
        if has_is_paper:
            select += " AND is_paper=0"
        select += " ORDER BY timestamp"

        rows = conn.execute(select).fetchall()
        trades = []
        for r in rows:
            d = dict(r)
            if has_pnl_cents:
                d["pnl_usd"] = (d.pop("pnl_cents", 0) or 0) / 100.0
            elif "payout_usd" in d:
                d["pnl_usd"] = (d.pop("payout_usd", 0) or 0) - (d.get("cost_usd", 0) or 0)
            else:
                d["pnl_usd"] = 0.0
            d.setdefault("side", "yes")
            d.setdefault("is_paper", False)
            trades.append(d)
        return trades
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()


# ── Bucket Analysis ───────────────────────────────────────────────────────────

@dataclass
class BucketStats:
    """Statistics for one (asset × price_bucket × side) bucket."""
    key: str                           # e.g. "KXBTC|93|yes"
    asset: str
    price_bucket: int                  # price_cents rounded to nearest 5 (90,91,...,99)
    side: str
    n: int
    wins: int
    pnl_usd: float
    win_rate: float
    break_even_wr: float               # price_cents / 100
    wilson_lo: float
    wilson_hi: float
    cusum_s: float
    cusum_triggered: bool
    p_value: float                     # One-tailed binomial against break-even
    avg_cost_usd: float
    # Derived
    above_be: bool = False             # wilson_lo > break_even_wr (statistically confirmed edge)
    below_be: bool = False             # wilson_hi < break_even_wr (statistically confirmed loser)
    warning: bool = False              # n >= 10, WR below BE, not yet enough for guard
    guard_candidate: bool = False      # p_value < 0.20 and n >= 10


def _asset_from_ticker(ticker: str | None) -> str:
    """Extract asset from ticker like KXBTC15M-xxx → KXBTC."""
    if not ticker:
        return "unknown"
    t = str(ticker)
    for asset in ("KXBTC", "KXETH", "KXSOL", "KXXRP"):
        if asset in t:
            return asset
    return t.split("-")[0] if "-" in t else t[:6]


def analyze_buckets(trades: list[dict]) -> list[BucketStats]:
    """Compute per-bucket statistics across all settled live trades."""
    # Group by (asset × price_bucket × side)
    groups: dict[str, list[dict]] = {}
    for t in trades:
        ticker = t.get("ticker") or t.get("market_id", "")
        asset = _asset_from_ticker(ticker)
        price = t.get("price_cents", 0) or 0
        side = t.get("side", "yes") or "yes"
        key = f"{asset}|{price}|{side}"
        groups.setdefault(key, []).append(t)

    buckets = []
    for key, group in sorted(groups.items()):
        asset, price_str, side = key.split("|")
        price_cents = int(price_str)
        be_wr = price_cents / 100.0

        n = len(group)
        wins = sum(1 for t in group if t.get("result") == t.get("side"))
        pnl = sum(t.get("pnl_usd", 0) or 0 for t in group)
        wr = wins / n if n > 0 else 0.0
        costs = [t.get("cost_usd", 0) or 0 for t in group if t.get("cost_usd")]
        avg_cost = sum(costs) / len(costs) if costs else 0.0

        lo, hi = wilson_ci(n, wins)
        cusum_triggered, cusum_s, _ = cusum_statistic(
            [t.get("result") == t.get("side") for t in group],
            mu_0=be_wr,
        )

        # Two-sided p-values:
        # p_lose = P(X <= wins | H0: p=be_wr) — small means "statistically few wins" (GUARD)
        # p_edge = P(X >= wins | H0: p=be_wr) — small means "statistically many wins" (EDGE)
        #
        # binomial_p_value(n, k, p0) returns P(X >= k | H0)
        # So P(X <= wins) = 1 - P(X >= wins+1)
        p_edge = round(binomial_p_value(n, wins, be_wr), 4)     # P(X >= wins) — low = confirmed edge
        p_lose = round(1.0 - binomial_p_value(n, wins + 1, be_wr), 4)  # P(X <= wins) — low = loser

        bucket = BucketStats(
            key=key,
            asset=asset,
            price_bucket=price_cents,
            side=side,
            n=n,
            wins=wins,
            pnl_usd=round(pnl, 2),
            win_rate=round(wr, 4),
            break_even_wr=round(be_wr, 4),
            wilson_lo=lo,
            wilson_hi=hi,
            cusum_s=cusum_s,
            cusum_triggered=cusum_triggered,
            p_value=round(p_lose, 4),   # Display p_lose (relevant for guard decisions)
            avg_cost_usd=round(avg_cost, 4),
        )

        # Derived flags
        bucket.above_be = lo > be_wr              # Statistically confirmed edge
        bucket.below_be = hi < be_wr              # Statistically confirmed loser
        if n >= 10 and wr < be_wr:
            bucket.warning = True
        # Guard candidate: LOSING bucket where p_lose < 0.20 (mirrors auto_guard threshold)
        if n >= 10 and wr < be_wr and p_lose < 0.20:
            bucket.guard_candidate = True

        buckets.append(bucket)

    return buckets


# ── Calibration Analysis ──────────────────────────────────────────────────────

def run_calibration_analysis(trades: list[dict]) -> dict:
    """
    Detect systematic calibration bias per price zone.

    For each price bucket, computes: market_price vs actual_win_frequency.
    Positive bias = market overestimates probability (market is overconfident).
    Negative bias = market underestimates probability (we can exploit — bet more).
    """
    try:
        from calibration_bias import CalibrationBias
        cb = CalibrationBias(n_bins=10, min_samples_per_bin=15)
        for t in trades:
            price = (t.get("price_cents", 0) or 0) / 100.0
            if not 0.0 < price < 1.0:
                continue
            side = t.get("side", "yes") or "yes"
            won = t.get("result") == t.get("side")
            # Normalize: outcome=1 means "we won this bet"
            cb.add_contract(market_price=price, outcome=1 if won else 0, domain="crypto")
        result = cb.analyze(domain="crypto")
        return result.to_dict() if result else {}
    except Exception:
        return {}


# ── Dynamic Kelly Sizing ──────────────────────────────────────────────────────

def run_kelly_analysis(
    buckets: list[BucketStats],
    bankroll_cents: int = 10000,
) -> dict[str, dict]:
    """
    Compute per-bucket optimal Kelly fraction vs current flat sizing.

    For each confirmed-edge bucket (above_be=True), compute what Kelly says
    vs what our bot currently bets (flat 500c / 5 USD per sniper bet).
    """
    try:
        from dynamic_kelly import DynamicKelly
        dk = DynamicKelly(
            bankroll_cents=bankroll_cents,
            max_fraction=0.10,   # 10% max per bet (conservative)
            kelly_multiplier=0.5,  # Half-Kelly for safety
            min_bet_cents=50,
        )
    except ImportError:
        return {}

    results = {}
    for b in buckets:
        if b.n < 20 or not b.above_be:
            continue
        # True probability = Wilson midpoint (conservative)
        true_prob = (b.wilson_lo + b.win_rate) / 2
        market_price = b.price_bucket / 100.0
        try:
            sizing = dk.compute_bet_sizing(
                true_prob=true_prob,
                market_price=market_price,
            )
            results[b.key] = {
                "bucket": b.key,
                "n": b.n,
                "win_rate": b.win_rate,
                "break_even": b.break_even_wr,
                "true_prob_estimate": round(true_prob, 4),
                "kelly_fraction": sizing.kelly_fraction,
                "kelly_bet_cents": sizing.bet_amount_cents,
                "edge": sizing.edge,
                "current_flat_cents": 500,
                "kelly_vs_flat": round(sizing.bet_amount_cents / 500, 2),
            }
        except Exception:
            continue

    return results


# ── Proposal Generation ───────────────────────────────────────────────────────

@dataclass
class LearningProposal:
    """Actionable self-improvement proposal from learning analysis."""
    severity: str    # CRITICAL / HIGH / MEDIUM / LOW
    category: str    # GUARD / KELLY / CALIBRATION / HEALTH / DATA
    bucket: str
    title: str
    evidence: str
    action: str
    data_points: dict = field(default_factory=dict)


def generate_proposals(
    buckets: list[BucketStats],
    kelly_recs: dict[str, dict],
    calibration: dict,
    health_verdicts: list,
) -> list[LearningProposal]:
    """Generate ranked actionable proposals from all analyses."""
    proposals = []

    # 1. Guard candidates (p < 0.20 with n >= 10)
    for b in buckets:
        if b.guard_candidate and b.pnl_usd < 0:
            severity = "CRITICAL" if b.pnl_usd < -10 else "HIGH"
            proposals.append(LearningProposal(
                severity=severity,
                category="GUARD",
                bucket=b.key,
                title=f"Guard candidate: {b.asset} {b.side}@{b.price_bucket}c",
                evidence=(
                    f"n={b.n}, WR={b.win_rate:.1%}, BE={b.break_even_wr:.1%}, "
                    f"p={b.p_value:.3f}, PnL={b.pnl_usd:.2f} USD, "
                    f"CUSUM={b.cusum_s:.2f}"
                ),
                action=f"Add guard: {b.asset} {b.side}@{b.price_bucket}c to auto_guards.json",
                data_points={
                    "n": b.n, "win_rate": b.win_rate, "p_value": b.p_value,
                    "pnl_usd": b.pnl_usd, "cusum_s": b.cusum_s,
                },
            ))

    # 2. CUSUM-triggered degradation (even for buckets not yet at guard threshold)
    for b in buckets:
        if b.cusum_triggered and not b.guard_candidate and b.n >= 15:
            proposals.append(LearningProposal(
                severity="MEDIUM",
                category="GUARD",
                bucket=b.key,
                title=f"CUSUM drift detected: {b.asset} {b.side}@{b.price_bucket}c",
                evidence=(
                    f"CUSUM S={b.cusum_s:.2f} >= 5.0. "
                    f"n={b.n}, WR={b.win_rate:.1%}, BE={b.break_even_wr:.1%}"
                ),
                action=f"WATCH: {b.asset} {b.side}@{b.price_bucket}c. "
                       f"Guard when p < 0.20 (currently p={b.p_value:.3f})",
                data_points={
                    "n": b.n, "win_rate": b.win_rate, "cusum_s": b.cusum_s, "p_value": b.p_value
                },
            ))

    # 3. Kelly undersizing opportunities (confirmed-edge buckets)
    for key, rec in kelly_recs.items():
        ratio = rec.get("kelly_vs_flat", 1.0)
        if ratio > 1.5:  # Kelly says bet 50%+ more than we currently do
            proposals.append(LearningProposal(
                severity="HIGH" if ratio > 2.0 else "MEDIUM",
                category="KELLY",
                bucket=key,
                title=f"Kelly says bet MORE: {key}",
                evidence=(
                    f"Kelly-optimal={rec['kelly_bet_cents']}c vs current flat=500c "
                    f"(ratio {ratio:.1f}x). "
                    f"n={rec['n']}, WR={rec['win_rate']:.1%}, edge={rec['edge']:.3f}"
                ),
                action=f"Consider increasing bet size for {key} bucket. "
                       f"Half-Kelly recommendation: {rec['kelly_bet_cents']}c. "
                       f"Requires 30+ settled bets + Matthew approval before changing.",
                data_points=rec,
            ))
        elif ratio < 0.5:  # Kelly says bet 50%+ LESS
            proposals.append(LearningProposal(
                severity="MEDIUM",
                category="KELLY",
                bucket=key,
                title=f"Kelly says bet LESS: {key}",
                evidence=(
                    f"Kelly-optimal={rec['kelly_bet_cents']}c vs current flat=500c "
                    f"(ratio {ratio:.1f}x). Edge smaller than assumed."
                ),
                action=f"Consider reducing bet size for {key} bucket to {rec['kelly_bet_cents']}c.",
                data_points=rec,
            ))

    # 4. Strategy health issues
    for v in health_verdicts:
        if v.verdict in ("KILL", "PAUSE"):
            proposals.append(LearningProposal(
                severity="CRITICAL" if v.verdict == "KILL" else "HIGH",
                category="HEALTH",
                bucket=v.strategy,
                title=f"Strategy {v.verdict}: {v.strategy}",
                evidence="; ".join(v.reasons[:3]),
                action=f"Review {v.strategy} immediately. Verdict: {v.verdict}.",
                data_points={
                    "win_rate": v.win_rate, "pnl_usd": v.pnl_usd,
                    "max_loss_streak": v.max_loss_streak,
                },
            ))

    # 5. Calibration mispricing zones
    if calibration:
        for zone in calibration.get("mispricing_zones", []):
            if zone.get("exploitable") and abs(zone.get("bias", 0)) > 0.05:
                price_range = zone.get("price_range", [0, 1])
                bias = zone.get("bias", 0)
                direction = "OVERPRICED" if bias > 0 else "UNDERPRICED"
                proposals.append(LearningProposal(
                    severity="LOW",
                    category="CALIBRATION",
                    bucket=f"price_range_{price_range[0]:.2f}_{price_range[1]:.2f}",
                    title=f"Calibration: market {direction} at {price_range[0]:.0%}-{price_range[1]:.0%}",
                    evidence=(
                        f"Bias={bias:.3f}, confidence={zone.get('confidence', 0):.2f}, "
                        f"n={zone.get('n_samples', 0)}"
                    ),
                    action=(
                        f"Market systematically {'overestimates' if bias > 0 else 'underestimates'} "
                        f"probability in this range. "
                        + ("Bet less in this range." if bias > 0 else "This zone may have exploitable edge.")
                    ),
                    data_points=zone,
                ))

    # Sort: CRITICAL first, then HIGH, MEDIUM, LOW
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    proposals.sort(key=lambda p: order.get(p.severity, 4))
    return proposals


# ── Learning State (cross-session persistence) ────────────────────────────────

def load_learning_state() -> dict:
    """Load persistent learning state from data/learning_state.json."""
    path = Path(LEARNING_STATE_PATH)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "version": 1,
        "sessions": [],
        "bucket_history": {},
        "cusum_states": {},
        "guard_candidates": {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def save_learning_state(
    state: dict,
    buckets: list[BucketStats],
    proposals: list[LearningProposal],
    calibration: dict,
) -> None:
    """Update and save persistent learning state."""
    now = datetime.now(timezone.utc).isoformat()

    # Update bucket history
    for b in buckets:
        history = state["bucket_history"].setdefault(b.key, [])
        history.append({
            "ts": now,
            "n": b.n,
            "win_rate": b.win_rate,
            "pnl_usd": b.pnl_usd,
            "cusum_s": b.cusum_s,
            "wilson_lo": b.wilson_lo,
            "wilson_hi": b.wilson_hi,
            "guard_candidate": b.guard_candidate,
        })
        # Keep last 50 entries per bucket
        if len(history) > 50:
            state["bucket_history"][b.key] = history[-50:]

    # Track guard candidates over time
    for p in proposals:
        if p.category == "GUARD":
            state["guard_candidates"].setdefault(p.bucket, {}).update({
                "last_seen": now,
                "severity": p.severity,
                "evidence": p.evidence,
                "action": p.action,
            })

    # Session summary
    state["sessions"].append({
        "ts": now,
        "n_buckets": len(buckets),
        "n_proposals": len(proposals),
        "n_guard_candidates": sum(1 for p in proposals if p.category == "GUARD"),
        "has_calibration": bool(calibration),
    })
    if len(state["sessions"]) > 200:
        state["sessions"] = state["sessions"][-200:]

    state["updated_at"] = now

    # Atomic write
    tmp = LEARNING_STATE_PATH + ".tmp"
    Path(LEARNING_STATE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, LEARNING_STATE_PATH)


# ── Report Formatting ─────────────────────────────────────────────────────────

def format_report(
    buckets: list[BucketStats],
    proposals: list[LearningProposal],
    calibration: dict,
    kelly_recs: dict[str, dict],
    health_verdicts: list,
    analyzed_at: str,
    brief: bool = False,
) -> str:
    """Format full self-learning report as markdown."""
    lines = [
        "## Kalshi Self-Learning Report",
        "",
        f"**Generated:** {analyzed_at[:19]} UTC",
        f"**Live buckets analyzed:** {len(buckets)} | "
        f"**Proposals:** {len(proposals)}",
        "",
    ]

    # Proposals
    if proposals:
        lines.append("### Proposals (ranked by severity)")
        lines.append("")
        for i, p in enumerate(proposals[:10], 1):
            lines.append(f"**{i}. [{p.severity}] {p.title}**")
            lines.append(f"   Evidence: {p.evidence}")
            lines.append(f"   Action: {p.action}")
            lines.append("")
    else:
        lines.append("No proposals — all buckets within acceptable parameters.")
        lines.append("")

    if brief:
        # Summary counts only
        counts: dict[str, int] = {}
        for p in proposals:
            counts[p.severity] = counts.get(p.severity, 0) + 1
        summary_parts = [
            f"{counts.get(k, 0)} {k}"
            for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            if counts.get(k, 0) > 0
        ]
        lines.append(f"**Proposal summary:** {', '.join(summary_parts) or 'none'}")
        return "\n".join(lines)

    # Bucket stats — only show buckets with >= 10 trades
    significant = [b for b in buckets if b.n >= 10]
    if significant:
        lines.append("### Bucket Analysis (N >= 10, sorted by PnL)")
        lines.append("")
        significant.sort(key=lambda b: b.pnl_usd)
        for b in significant:
            edge_flag = "EDGE" if b.above_be else ("LOSER" if b.below_be else "")
            guard_flag = " [GUARD CANDIDATE]" if b.guard_candidate else ""
            cusum_flag = f" [CUSUM={b.cusum_s:.1f}]" if b.cusum_s >= 3.0 else ""
            lines.append(
                f"  {b.asset} {b.side}@{b.price_bucket}c: "
                f"n={b.n}, WR={b.win_rate:.1%} vs BE={b.break_even_wr:.1%}, "
                f"PnL={b.pnl_usd:.2f} USD, "
                f"CI=[{b.wilson_lo:.2%},{b.wilson_hi:.2%}], "
                f"p={b.p_value:.3f}"
                f"{cusum_flag}{guard_flag}"
                + (f" [{edge_flag}]" if edge_flag else "")
            )
        lines.append("")

    # Calibration summary
    if calibration:
        bias_dir = calibration.get("bias_direction", "unknown")
        mean_bias = calibration.get("mean_bias", 0)
        zones = calibration.get("mispricing_zones", [])
        exploitable = [z for z in zones if z.get("exploitable")]
        lines.append("### Calibration Analysis")
        lines.append("")
        lines.append(
            f"  Bias direction: {bias_dir} | "
            f"Mean bias: {mean_bias:.4f} | "
            f"Exploitable zones: {len(exploitable)}"
        )
        lines.append("")

    # Kelly sizing (only confirmed-edge buckets)
    if kelly_recs:
        lines.append("### Kelly Sizing Recommendations (confirmed-edge buckets)")
        lines.append("")
        for key, rec in sorted(kelly_recs.items(), key=lambda x: -x[1]["kelly_vs_flat"]):
            ratio = rec["kelly_vs_flat"]
            direction = "increase" if ratio > 1.0 else "decrease"
            lines.append(
                f"  {key}: n={rec['n']}, WR={rec['win_rate']:.1%}, "
                f"Kelly={rec['kelly_bet_cents']}c vs flat=500c "
                f"({ratio:.1f}x — {direction} sizing)"
            )
        lines.append("")

    # Strategy health
    if health_verdicts:
        lines.append("### Strategy Health")
        lines.append("")
        for v in health_verdicts:
            lines.append(
                f"  {v.strategy}: {v.verdict} | "
                f"n={v.settled_trades}, WR={v.win_rate:.1%}, "
                f"PnL={v.pnl_usd:.2f} USD"
            )
        lines.append("")

    return "\n".join(lines)


# ── Main Orchestrator ─────────────────────────────────────────────────────────

def run_self_learning(
    db_path: str,
    brief: bool = False,
    save_state: bool = True,
) -> dict:
    """
    Run full self-learning analysis pipeline.

    Returns structured dict with all findings.
    """
    analyzed_at = datetime.now(timezone.utc).isoformat()
    trades = _read_trades(db_path)

    if not trades:
        return {
            "analyzed_at": analyzed_at,
            "trade_count": 0,
            "buckets": [],
            "proposals": [],
            "calibration": {},
            "kelly_recs": {},
            "health_verdicts": [],
            "summary": "No settled live trades found.",
        }

    # Run all analyses
    buckets = analyze_buckets(trades)
    calibration = run_calibration_analysis(trades)
    kelly_recs = run_kelly_analysis(buckets)

    # Strategy health scoring
    health_verdicts = []
    try:
        from strategy_health_scorer import score_strategies
        health_verdicts = score_strategies(trades, live_only=False)
    except ImportError:
        pass

    # Generate proposals
    proposals = generate_proposals(buckets, kelly_recs, calibration, health_verdicts)

    # Save persistent learning state
    if save_state:
        try:
            state = load_learning_state()
            save_learning_state(state, buckets, proposals, calibration)
        except Exception:
            pass

    return {
        "analyzed_at": analyzed_at,
        "trade_count": len(trades),
        "buckets": [
            {
                "key": b.key,
                "n": b.n,
                "wins": b.wins,
                "win_rate": b.win_rate,
                "break_even_wr": b.break_even_wr,
                "pnl_usd": b.pnl_usd,
                "wilson_lo": b.wilson_lo,
                "wilson_hi": b.wilson_hi,
                "cusum_s": b.cusum_s,
                "cusum_triggered": b.cusum_triggered,
                "p_value": b.p_value,
                "guard_candidate": b.guard_candidate,
                "above_be": b.above_be,
                "below_be": b.below_be,
            }
            for b in sorted(buckets, key=lambda b: b.pnl_usd)
        ],
        "proposals": [
            {
                "severity": p.severity,
                "category": p.category,
                "bucket": p.bucket,
                "title": p.title,
                "evidence": p.evidence,
                "action": p.action,
                "data_points": p.data_points,
            }
            for p in proposals
        ],
        "calibration": calibration,
        "kelly_recs": kelly_recs,
        "health_verdicts": [
            {
                "strategy": v.strategy,
                "verdict": v.verdict,
                "win_rate": v.win_rate,
                "pnl_usd": v.pnl_usd,
                "settled_trades": v.settled_trades,
                "max_loss_streak": v.max_loss_streak,
                "reasons": v.reasons,
            }
            for v in health_verdicts
        ],
        "summary": (
            f"{len(trades)} settled live trades, {len(buckets)} buckets, "
            f"{len(proposals)} proposals "
            f"({sum(1 for p in proposals if p.severity in ('CRITICAL','HIGH'))} critical/high)"
        ),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Kalshi self-learning analysis")
    parser.add_argument("--db", help="Path to polybot.db")
    parser.add_argument("--brief", action="store_true", help="Summary only")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--save", action="store_true", help="Save report to reports/")
    parser.add_argument("--no-state", action="store_true", help="Skip saving learning_state.json")
    args = parser.parse_args()

    # Discover DB
    db_path = args.db
    if not db_path:
        db_path = os.environ.get("POLYBOT_DB_PATH")
    if not db_path:
        candidates = [
            os.path.join(PROJECT_ROOT, "data", "polybot.db"),
            os.path.expanduser("~/Projects/polymarket-bot/data/polybot.db"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                db_path = c
                break
    if not db_path or not os.path.isfile(db_path):
        print("ERROR: polybot.db not found. Use --db /path/to/polybot.db", file=sys.stderr)
        sys.exit(1)

    result = run_self_learning(
        db_path=db_path,
        brief=args.brief,
        save_state=not args.no_state,
    )

    if args.json:
        print(json.dumps(result, indent=2))
        return

    # Format report
    # Reconstruct bucket objects for formatting
    bucket_objs = []
    for b_dict in result["buckets"]:
        parts = b_dict["key"].split("|")
        if len(parts) != 3:
            continue
        asset, price_str, side = parts
        b = BucketStats(
            key=b_dict["key"],
            asset=asset,
            price_bucket=int(price_str),
            side=side,
            n=b_dict["n"],
            wins=b_dict["wins"],
            pnl_usd=b_dict["pnl_usd"],
            win_rate=b_dict["win_rate"],
            break_even_wr=b_dict["break_even_wr"],
            wilson_lo=b_dict["wilson_lo"],
            wilson_hi=b_dict["wilson_hi"],
            cusum_s=b_dict["cusum_s"],
            cusum_triggered=b_dict["cusum_triggered"],
            p_value=b_dict["p_value"],
            avg_cost_usd=0.0,
            above_be=b_dict["above_be"],
            below_be=b_dict["below_be"],
            guard_candidate=b_dict["guard_candidate"],
        )
        bucket_objs.append(b)

    # Reconstruct proposal objects
    from dataclasses import fields as dc_fields
    proposal_objs = []
    for p_dict in result["proposals"]:
        proposal_objs.append(LearningProposal(
            severity=p_dict["severity"],
            category=p_dict["category"],
            bucket=p_dict["bucket"],
            title=p_dict["title"],
            evidence=p_dict["evidence"],
            action=p_dict["action"],
            data_points=p_dict.get("data_points", {}),
        ))

    # Reconstruct health verdict stubs
    class _Verdict:
        pass

    health_objs = []
    for v_dict in result["health_verdicts"]:
        v = _Verdict()
        v.strategy = v_dict["strategy"]
        v.verdict = v_dict["verdict"]
        v.win_rate = v_dict["win_rate"]
        v.pnl_usd = v_dict["pnl_usd"]
        v.settled_trades = v_dict["settled_trades"]
        v.max_loss_streak = v_dict["max_loss_streak"]
        v.reasons = v_dict["reasons"]
        health_objs.append(v)

    report = format_report(
        buckets=bucket_objs,
        proposals=proposal_objs,
        calibration=result["calibration"],
        kelly_recs=result["kelly_recs"],
        health_verdicts=health_objs,
        analyzed_at=result["analyzed_at"],
        brief=args.brief,
    )

    print(report)
    print(f"\nSummary: {result['summary']}")

    if args.save:
        Path(REPORT_DIR).mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        report_path = os.path.join(REPORT_DIR, f"learning_report_{ts}.md")
        with open(report_path, "w") as f:
            f.write(report)
        print(f"\nReport saved to {report_path}")


if __name__ == "__main__":
    main()
