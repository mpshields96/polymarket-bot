#!/usr/bin/env python3
"""
edge_stability.py — Bucket-Level Edge Degradation Early Warning System

Detects when per-bucket edges are degrading before CUSUM alerts trigger.
Runs as part of the monitoring loop (every 3rd cycle) alongside kalshi_self_learning.py.

Analyses:
  1. Win rate slope (Theil-Sen robust regression over session history)
  2. CUSUM proximity (S / h ratio — how close to alert threshold)
  3. Cross-bucket correlation (asset-wide vs bucket-specific degradation)
  4. Time-of-day seasonality shifts (week-over-week hour-level WR changes)
  5. Days-until-alert projection (extrapolate CUSUM trajectory)

Safety: Read-only. Advisory only. No trade execution.

Usage:
    python3 scripts/analysis/edge_stability.py              # Full report
    python3 scripts/analysis/edge_stability.py --json       # JSON output
    python3 scripts/analysis/edge_stability.py --brief      # Summary only
    python3 scripts/analysis/edge_stability.py --bucket KXBTC|93|no  # Single bucket
"""

import json
import math
import os
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

LEARNING_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "learning_state.json")
AUTO_GUARDS_PATH = os.path.join(PROJECT_ROOT, "data", "auto_guards.json")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "polybot.db")


# ── Statistical Functions (stdlib-only) ──────────────────────────────────────


def theil_sen_slope(x: list[float], y: list[float]) -> float:
    """Theil-Sen estimator: median of all pairwise slopes. Robust to outliers.

    Theil (1950), Sen (1968). Breakdown point: 29.3% (vs 0% for OLS).
    Returns 0.0 if fewer than 2 points.
    """
    n = len(x)
    if n < 2 or len(y) < 2:
        return 0.0
    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            if dx != 0:
                slopes.append((y[j] - y[i]) / dx)
    if not slopes:
        return 0.0
    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 0:
        return (slopes[mid - 1] + slopes[mid]) / 2
    return slopes[mid]


def wilson_ci(n: int, k: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval. Wilson (1927)."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, round(center - margin, 4)), min(1.0, round(center + margin, 4)))


def cusum_proximity(cusum_s: float, threshold: float = 5.0) -> float:
    """How close CUSUM S is to the alert threshold h. Returns S/h ratio (0..1+)."""
    if threshold <= 0:
        return 1.0
    return cusum_s / threshold


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class BucketStability:
    """Stability assessment for a single (asset, price, side) bucket."""
    bucket_key: str  # "KXBTC|93|no"
    status: str = "UNKNOWN"  # DEGRADING, STABLE, IMPROVING, INSUFFICIENT_DATA
    n_total: int = 0
    current_wr: float = 0.0
    wr_slope: float = 0.0  # Theil-Sen slope per session
    cusum_s: float = 0.0
    cusum_proximity: float = 0.0  # S/h ratio
    days_until_alert: Optional[float] = None  # Projected days until CUSUM >= h
    wilson_lo: float = 0.0
    wilson_hi: float = 1.0
    is_guarded: bool = False
    recommendation: str = ""

    def to_dict(self) -> dict:
        d = {
            "bucket": self.bucket_key,
            "status": self.status,
            "n_total": self.n_total,
            "current_wr": round(self.current_wr, 4),
            "win_rate_slope": round(self.wr_slope, 6),
            "cusum_s": round(self.cusum_s, 3),
            "cusum_proximity": round(self.cusum_proximity, 3),
            "wilson_ci": [self.wilson_lo, self.wilson_hi],
            "is_guarded": self.is_guarded,
            "recommendation": self.recommendation,
        }
        if self.days_until_alert is not None:
            d["days_until_alert"] = round(self.days_until_alert, 1)
        return d


@dataclass
class AssetCorrelation:
    """Cross-bucket degradation correlation for an asset."""
    asset: str
    n_buckets: int = 0
    n_degrading: int = 0
    degradation_ratio: float = 0.0
    is_asset_wide: bool = False  # True if >50% of buckets are degrading

    def to_dict(self) -> dict:
        return {
            "asset": self.asset,
            "n_buckets": self.n_buckets,
            "n_degrading": self.n_degrading,
            "degradation_ratio": round(self.degradation_ratio, 3),
            "is_asset_wide": self.is_asset_wide,
        }


@dataclass
class StabilityReport:
    """Complete edge stability report."""
    timestamp: str = ""
    buckets: list[BucketStability] = field(default_factory=list)
    asset_correlations: list[AssetCorrelation] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "summary": self.summary,
            "buckets": [b.to_dict() for b in self.buckets],
            "asset_correlations": [a.to_dict() for a in self.asset_correlations],
        }


# ── Core Analysis Engine ─────────────────────────────────────────────────────


class EdgeStabilityAnalyzer:
    """Analyzes bucket-level edge degradation from learning state and trade DB."""

    # Thresholds for classification
    SLOPE_DEGRADING = -0.005  # Losing >0.5% WR per session → DEGRADING
    SLOPE_IMPROVING = 0.005   # Gaining >0.5% WR per session → IMPROVING
    CUSUM_WARNING = 0.6       # S/h >= 0.6 → approaching alert
    CUSUM_CRITICAL = 0.8      # S/h >= 0.8 → imminent alert
    MIN_HISTORY = 3           # Minimum session snapshots for slope analysis
    MIN_BETS = 10             # Minimum bets for any analysis

    def __init__(
        self,
        learning_state_path: str = LEARNING_STATE_PATH,
        auto_guards_path: str = AUTO_GUARDS_PATH,
        db_path: str = DB_PATH,
        cusum_threshold: float = 5.0,
    ):
        self.learning_state_path = learning_state_path
        self.auto_guards_path = auto_guards_path
        self.db_path = db_path
        self.cusum_threshold = cusum_threshold
        self._learning_state = None
        self._guards = None

    def load_learning_state(self) -> dict:
        """Load persisted learning state."""
        if self._learning_state is not None:
            return self._learning_state
        try:
            with open(self.learning_state_path, "r") as f:
                self._learning_state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._learning_state = {}
        return self._learning_state

    def load_guards(self) -> list[dict]:
        """Load active auto-guards."""
        if self._guards is not None:
            return self._guards
        try:
            with open(self.auto_guards_path, "r") as f:
                self._guards = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self._guards = []
        return self._guards

    def _is_guarded(self, bucket_key: str) -> bool:
        """Check if a bucket is currently guarded."""
        guards = self.load_guards()
        # Guards can be stored in various formats — check common patterns
        for g in guards:
            if isinstance(g, dict):
                gkey = g.get("bucket", g.get("key", ""))
                if gkey == bucket_key:
                    return True
        return False

    def _extract_bucket_history(self, bucket_key: str) -> list[dict]:
        """Extract session-over-session history for a bucket from learning state."""
        state = self.load_learning_state()
        buckets = state.get("buckets", {})
        bucket_data = buckets.get(bucket_key, {})
        history = bucket_data.get("history", [])
        return history

    def analyze_bucket(self, bucket_key: str, history: list[dict] = None) -> BucketStability:
        """Analyze stability of a single bucket."""
        if history is None:
            history = self._extract_bucket_history(bucket_key)

        result = BucketStability(bucket_key=bucket_key)
        result.is_guarded = self._is_guarded(bucket_key)

        if not history or len(history) < 1:
            result.status = "INSUFFICIENT_DATA"
            result.recommendation = "Not enough data for analysis"
            return result

        # Latest snapshot
        latest = history[-1]
        result.n_total = latest.get("n", 0)
        result.current_wr = latest.get("win_rate", 0.0)
        result.cusum_s = latest.get("cusum_s", 0.0)
        result.wilson_lo = latest.get("wilson_lo", 0.0)
        result.wilson_hi = latest.get("wilson_hi", 1.0)

        if result.n_total < self.MIN_BETS:
            result.status = "INSUFFICIENT_DATA"
            result.recommendation = f"Only {result.n_total} bets — need {self.MIN_BETS}+"
            return result

        # CUSUM proximity
        result.cusum_proximity = cusum_proximity(result.cusum_s, self.cusum_threshold)

        # Win rate slope (Theil-Sen over session history)
        if len(history) >= self.MIN_HISTORY:
            timestamps = [h.get("ts", i) for i, h in enumerate(history)]
            win_rates = [h.get("win_rate", 0.0) for h in history]
            # Normalize timestamps to session indices for interpretability
            indices = list(range(len(history)))
            result.wr_slope = theil_sen_slope(indices, win_rates)
        else:
            result.wr_slope = 0.0

        # Days until CUSUM alert (extrapolate from CUSUM trajectory)
        if len(history) >= 2:
            cusum_values = [h.get("cusum_s", 0.0) for h in history]
            cusum_indices = list(range(len(cusum_values)))
            cusum_slope = theil_sen_slope(cusum_indices, cusum_values)
            if cusum_slope > 0:
                remaining = self.cusum_threshold - result.cusum_s
                sessions_until = remaining / cusum_slope if cusum_slope > 0 else None
                # Assume ~8 sessions/day (rough average)
                if sessions_until is not None and sessions_until > 0:
                    result.days_until_alert = sessions_until / 8
            # Negative or zero slope means CUSUM is stable/decreasing

        # Classify status
        result.status = self._classify_status(result)
        result.recommendation = self._generate_recommendation(result)

        return result

    def _classify_status(self, bucket: BucketStability) -> str:
        """Classify bucket as DEGRADING, STABLE, or IMPROVING."""
        # CUSUM critical overrides everything
        if bucket.cusum_proximity >= self.CUSUM_CRITICAL:
            return "DEGRADING"

        # Win rate slope
        if bucket.wr_slope <= self.SLOPE_DEGRADING:
            return "DEGRADING"
        if bucket.wr_slope >= self.SLOPE_IMPROVING:
            return "IMPROVING"

        # CUSUM warning with flat/negative slope
        if bucket.cusum_proximity >= self.CUSUM_WARNING:
            return "DEGRADING"

        return "STABLE"

    def _generate_recommendation(self, bucket: BucketStability) -> str:
        """Generate human-readable recommendation."""
        if bucket.status == "INSUFFICIENT_DATA":
            return f"Only {bucket.n_total} bets — need {self.MIN_BETS}+"

        if bucket.is_guarded:
            return "Already guarded — monitor for removal candidacy"

        if bucket.status == "DEGRADING":
            if bucket.cusum_proximity >= self.CUSUM_CRITICAL:
                return "CUSUM near threshold — guard activation imminent"
            if bucket.days_until_alert is not None and bucket.days_until_alert < 2:
                return f"Alert projected in {bucket.days_until_alert:.1f} days — consider preemptive guard"
            return "Win rate declining — monitor closely, consider guard if next cycle confirms"

        if bucket.status == "IMPROVING":
            return "Edge strengthening — maintain current approach"

        return "Stable — no action needed"

    def analyze_asset_correlation(self, buckets: list[BucketStability]) -> list[AssetCorrelation]:
        """Detect asset-wide degradation patterns."""
        asset_buckets: dict[str, list[BucketStability]] = {}
        for b in buckets:
            if b.status == "INSUFFICIENT_DATA":
                continue
            parts = b.bucket_key.split("|")
            if len(parts) >= 1:
                asset = parts[0]
                asset_buckets.setdefault(asset, []).append(b)

        correlations = []
        for asset, blist in sorted(asset_buckets.items()):
            n_degrading = sum(1 for b in blist if b.status == "DEGRADING")
            n_total = len(blist)
            ratio = n_degrading / n_total if n_total > 0 else 0.0
            correlations.append(AssetCorrelation(
                asset=asset,
                n_buckets=n_total,
                n_degrading=n_degrading,
                degradation_ratio=ratio,
                is_asset_wide=ratio > 0.5 and n_total >= 2,
            ))
        return correlations

    def run(self, bucket_filter: str = None) -> StabilityReport:
        """Run full edge stability analysis."""
        state = self.load_learning_state()
        # Support both schema variants:
        # - "bucket_history" (current polybot schema): dict of bucket_key → list of session dicts
        # - "buckets" (original CCA schema): dict of bucket_key → {"history": [...]}
        raw = state.get("bucket_history") or state.get("buckets", {})

        report = StabilityReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Analyze each bucket
        for bucket_key in sorted(raw.keys()):
            if bucket_filter and bucket_key != bucket_filter:
                continue
            bucket_val = raw[bucket_key]
            if isinstance(bucket_val, list):
                history = bucket_val  # polybot schema: value IS the history list
            else:
                history = bucket_val.get("history", [])  # CCA schema
            stability = self.analyze_bucket(bucket_key, history)
            report.buckets.append(stability)

        # Cross-bucket correlations
        report.asset_correlations = self.analyze_asset_correlation(report.buckets)

        # Summary
        n_degrading = sum(1 for b in report.buckets if b.status == "DEGRADING")
        n_stable = sum(1 for b in report.buckets if b.status == "STABLE")
        n_improving = sum(1 for b in report.buckets if b.status == "IMPROVING")
        n_insufficient = sum(1 for b in report.buckets if b.status == "INSUFFICIENT_DATA")
        asset_wide = [a for a in report.asset_correlations if a.is_asset_wide]

        report.summary = {
            "total_buckets": len(report.buckets),
            "degrading": n_degrading,
            "stable": n_stable,
            "improving": n_improving,
            "insufficient_data": n_insufficient,
            "asset_wide_degradation": [a.asset for a in asset_wide],
            "critical_buckets": [
                b.bucket_key for b in report.buckets
                if b.status == "DEGRADING" and b.cusum_proximity >= self.CUSUM_CRITICAL
            ],
        }

        return report

    def load_trades_by_hour(self, bucket_key: str, days_back: int = 14) -> dict:
        """Load time-of-day breakdown from DB for a bucket. Read-only."""
        if not os.path.exists(self.db_path):
            return {}

        parts = bucket_key.split("|")
        if len(parts) < 3:
            return {}
        asset, price_str, side = parts[0], parts[1], parts[2]

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get trades for this bucket in the last N days
            cursor.execute("""
                SELECT
                    CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as hour,
                    COUNT(*) as n,
                    SUM(CASE WHEN result = side THEN 1 ELSE 0 END) as wins,
                    SUM(pnl_cents) as pnl_cents
                FROM trades
                WHERE ticker LIKE ? || '%'
                    AND price_cents = ?
                    AND side = ?
                    AND is_paper = 0
                    AND result IS NOT NULL
                    AND timestamp >= strftime('%s', 'now') - ? * 86400
                GROUP BY hour
                ORDER BY hour
            """, (asset, int(price_str), side, days_back))

            rows = cursor.fetchall()
            conn.close()

            return {
                row["hour"]: {
                    "n": row["n"],
                    "wins": row["wins"],
                    "wr": row["wins"] / row["n"] if row["n"] > 0 else 0.0,
                    "pnl_cents": row["pnl_cents"] or 0,
                }
                for row in rows
            }
        except (sqlite3.Error, ValueError):
            return {}


# ── CLI ──────────────────────────────────────────────────────────────────────


def format_report(report: StabilityReport, brief: bool = False) -> str:
    """Format report for console output."""
    lines = []
    lines.append("=" * 70)
    lines.append("EDGE STABILITY REPORT")
    lines.append(f"  Generated: {report.timestamp}")
    lines.append("=" * 70)

    s = report.summary
    lines.append(f"\nSUMMARY: {s.get('total_buckets', 0)} buckets analyzed")
    lines.append(f"  DEGRADING: {s.get('degrading', 0)}")
    lines.append(f"  STABLE:    {s.get('stable', 0)}")
    lines.append(f"  IMPROVING: {s.get('improving', 0)}")
    lines.append(f"  INSUFFICIENT: {s.get('insufficient_data', 0)}")

    if s.get("asset_wide_degradation"):
        lines.append(f"\n  ASSET-WIDE DEGRADATION: {', '.join(s['asset_wide_degradation'])}")
    if s.get("critical_buckets"):
        lines.append(f"  CRITICAL BUCKETS: {', '.join(s['critical_buckets'])}")

    if brief:
        return "\n".join(lines)

    # Detailed per-bucket
    degrading = [b for b in report.buckets if b.status == "DEGRADING"]
    if degrading:
        lines.append(f"\n{'─' * 70}")
        lines.append("DEGRADING BUCKETS (action needed)")
        lines.append(f"{'─' * 70}")
        for b in sorted(degrading, key=lambda x: x.cusum_proximity, reverse=True):
            lines.append(f"\n  {b.bucket_key}")
            lines.append(f"    WR: {b.current_wr:.1%} (slope: {b.wr_slope:+.4f}/session)")
            lines.append(f"    CUSUM: {b.cusum_s:.2f}/{self_threshold(b)} (proximity: {b.cusum_proximity:.1%})")
            lines.append(f"    Wilson CI: [{b.wilson_lo:.3f}, {b.wilson_hi:.3f}]")
            if b.days_until_alert is not None:
                lines.append(f"    Days until alert: {b.days_until_alert:.1f}")
            lines.append(f"    Guarded: {'YES' if b.is_guarded else 'no'}")
            lines.append(f"    >> {b.recommendation}")

    improving = [b for b in report.buckets if b.status == "IMPROVING"]
    if improving:
        lines.append(f"\n{'─' * 70}")
        lines.append("IMPROVING BUCKETS")
        lines.append(f"{'─' * 70}")
        for b in improving:
            lines.append(f"  {b.bucket_key}: WR {b.current_wr:.1%} (slope: {b.wr_slope:+.4f})")

    # Asset correlations
    asset_wide = [a for a in report.asset_correlations if a.is_asset_wide]
    if asset_wide:
        lines.append(f"\n{'─' * 70}")
        lines.append("ASSET-WIDE DEGRADATION")
        lines.append(f"{'─' * 70}")
        for a in asset_wide:
            lines.append(f"  {a.asset}: {a.n_degrading}/{a.n_buckets} buckets degrading ({a.degradation_ratio:.0%})")

    return "\n".join(lines)


def self_threshold(b):
    """Helper for formatting."""
    return "5.0"


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Edge Stability Analyzer")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--brief", action="store_true", help="Summary only")
    parser.add_argument("--bucket", type=str, help="Analyze single bucket (e.g. KXBTC|93|no)")
    args = parser.parse_args()

    analyzer = EdgeStabilityAnalyzer()
    report = analyzer.run(bucket_filter=args.bucket)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(format_report(report, brief=args.brief))


if __name__ == "__main__":
    main()
