#!/usr/bin/env python3
"""
synthetic_bet_generator.py — Synthetic Bet Sequence Generator for Hypothesis Testing

Creates synthetic bet sequences matching historical distributions for testing
new guards, Kelly sizing rules, or strategy changes before deploying to live.

Generation modes:
  1. Historical resampling: draw from actual bucket-level (WR, PnL) distributions
  2. Parametric: Bernoulli with calibrated p, time-of-day weighting
  3. Sensitivity sweep: vary p0 and calibration slope to test edge boundaries

Safety: Read-only DB access. Generates data files only. No trade execution.

Usage:
    python3 synthetic_bet_generator.py --bucket KXBTC|93|no --n 1000
    python3 synthetic_bet_generator.py --strategy expiry_sniper_v1 --n 500 --mode parametric
    python3 synthetic_bet_generator.py --sweep --bucket KXBTC|93|no --p-range 0.88,0.98 --steps 10
    python3 synthetic_bet_generator.py --all --n 200  # All buckets with sufficient data
"""

import json
import math
import os
import random
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

LEARNING_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "learning_state.json")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "polybot.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "synthetic")


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class SyntheticBet:
    """A single synthetic bet."""
    synthetic_id: int
    bucket_key: str
    timestamp_offset: float  # seconds from sequence start
    ticker: str
    side: str
    price_cents: int
    result: str  # "win" or "loss"
    pnl_cents: int
    hour_utc: int = 0

    def to_dict(self) -> dict:
        return {
            "synthetic_id": self.synthetic_id,
            "bucket_key": self.bucket_key,
            "timestamp_offset": round(self.timestamp_offset, 1),
            "ticker": self.ticker,
            "side": self.side,
            "price_cents": self.price_cents,
            "result": self.result,
            "pnl_cents": self.pnl_cents,
            "hour_utc": self.hour_utc,
        }


@dataclass
class BucketProfile:
    """Statistical profile of a bucket for synthetic generation."""
    bucket_key: str
    asset: str
    price_cents: int
    side: str
    n_historical: int
    win_rate: float
    avg_win_pnl_cents: float  # Average PnL on wins
    avg_loss_pnl_cents: float  # Average PnL on losses (negative)
    hour_weights: dict = field(default_factory=dict)  # hour -> relative frequency

    @property
    def break_even_wr(self) -> float:
        """Break-even win rate for this price level (accounting for fees)."""
        # At 93c: buy at 93, win pays 100-93=7c, lose pays -93c
        # BE = 93 / 100 = 0.93 (simplified, ignoring fees)
        return self.price_cents / 100.0

    def to_dict(self) -> dict:
        return {
            "bucket_key": self.bucket_key,
            "asset": self.asset,
            "price_cents": self.price_cents,
            "side": self.side,
            "n_historical": self.n_historical,
            "win_rate": round(self.win_rate, 4),
            "break_even_wr": round(self.break_even_wr, 4),
            "avg_win_pnl_cents": round(self.avg_win_pnl_cents, 1),
            "avg_loss_pnl_cents": round(self.avg_loss_pnl_cents, 1),
        }


@dataclass
class SyntheticSequence:
    """A complete synthetic bet sequence with metadata."""
    bucket_key: str
    mode: str  # "historical", "parametric", "sweep"
    n_bets: int
    win_rate_param: float  # The p used for generation
    bets: list[SyntheticBet] = field(default_factory=list)
    actual_wr: float = 0.0
    total_pnl_cents: int = 0
    seed: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "bucket_key": self.bucket_key,
            "mode": self.mode,
            "n_bets": self.n_bets,
            "win_rate_param": round(self.win_rate_param, 4),
            "actual_wr": round(self.actual_wr, 4),
            "total_pnl_cents": self.total_pnl_cents,
            "seed": self.seed,
            "bets": [b.to_dict() for b in self.bets],
        }


# ── Profile Builder ──────────────────────────────────────────────────────────


class ProfileBuilder:
    """Builds bucket profiles from historical trade data."""

    ASSETS = ("KXBTC", "KXETH", "KXSOL", "KXXRP")

    def __init__(self, db_path: str = DB_PATH, learning_state_path: str = LEARNING_STATE_PATH):
        self.db_path = db_path
        self.learning_state_path = learning_state_path

    @staticmethod
    def _asset_from_ticker(ticker: str) -> str:
        for asset in ("KXBTC", "KXETH", "KXSOL", "KXXRP"):
            if asset in ticker:
                return asset
        return "unknown"

    def build_from_db(self, bucket_key: str) -> Optional[BucketProfile]:
        """Build profile from trade DB. Read-only access."""
        parts = bucket_key.split("|")
        if len(parts) < 3:
            return None
        asset, price_str, side = parts[0], parts[1], parts[2]

        if not os.path.exists(self.db_path):
            return None

        try:
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as n,
                    SUM(CASE WHEN (result = side) THEN 1 ELSE 0 END) as wins,
                    AVG(CASE WHEN (result = side) THEN pnl_cents END) as avg_win_pnl,
                    AVG(CASE WHEN (result != side) THEN pnl_cents END) as avg_loss_pnl
                FROM trades
                WHERE ticker LIKE ? || '%'
                    AND price_cents = ?
                    AND side = ?
                    AND is_paper = 0
                    AND result IS NOT NULL
            """, (asset, int(price_str), side))

            row = cursor.fetchone()
            if not row or row["n"] == 0:
                conn.close()
                return None

            # Hour distribution
            cursor.execute("""
                SELECT
                    CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as hour,
                    COUNT(*) as cnt
                FROM trades
                WHERE ticker LIKE ? || '%'
                    AND price_cents = ?
                    AND side = ?
                    AND is_paper = 0
                    AND result IS NOT NULL
                GROUP BY hour
            """, (asset, int(price_str), side))

            hour_rows = cursor.fetchall()
            total = sum(r["cnt"] for r in hour_rows)
            hour_weights = {
                r["hour"]: r["cnt"] / total if total > 0 else 0.0
                for r in hour_rows
            }
            conn.close()

            return BucketProfile(
                bucket_key=bucket_key,
                asset=asset,
                price_cents=int(price_str),
                side=side,
                n_historical=row["n"],
                win_rate=row["wins"] / row["n"] if row["n"] > 0 else 0.0,
                avg_win_pnl_cents=row["avg_win_pnl"] or (100 - int(price_str)),
                avg_loss_pnl_cents=row["avg_loss_pnl"] or (-int(price_str)),
                hour_weights=hour_weights,
            )
        except (sqlite3.Error, ValueError):
            return None

    def build_from_learning_state(self, bucket_key: str) -> Optional[BucketProfile]:
        """Build profile from learning state JSON (no DB needed)."""
        try:
            with open(self.learning_state_path, "r") as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

        buckets = state.get("buckets", {})
        bucket_data = buckets.get(bucket_key, {})
        history = bucket_data.get("history", [])
        if not history:
            return None

        latest = history[-1]
        parts = bucket_key.split("|")
        if len(parts) < 3:
            return None

        price = int(parts[1])
        return BucketProfile(
            bucket_key=bucket_key,
            asset=parts[0],
            price_cents=price,
            side=parts[2],
            n_historical=latest.get("n", 0),
            win_rate=latest.get("win_rate", 0.0),
            avg_win_pnl_cents=100 - price,  # Simplified: no fee data in learning state
            avg_loss_pnl_cents=-price,
            hour_weights={},
        )


# ── Synthetic Generator ─────────────────────────────────────────────────────


class SyntheticBetGenerator:
    """Generates synthetic bet sequences for hypothesis testing."""

    MIN_HISTORICAL = 10  # Minimum bets to build a profile

    def __init__(self, profile_builder: ProfileBuilder = None, seed: int = None):
        self.profile_builder = profile_builder or ProfileBuilder()
        self.seed = seed
        self._rng = random.Random(seed)

    def generate_parametric(
        self,
        profile: BucketProfile,
        n_bets: int,
        win_rate_override: float = None,
    ) -> SyntheticSequence:
        """Generate synthetic bets using Bernoulli draws with calibrated probability."""
        p = win_rate_override if win_rate_override is not None else profile.win_rate
        seq = SyntheticSequence(
            bucket_key=profile.bucket_key,
            mode="parametric",
            n_bets=n_bets,
            win_rate_param=p,
            seed=self.seed,
        )

        wins = 0
        total_pnl = 0
        hours = list(range(24))
        # Use 0.0 default for missing hours when profile has specific weights
        default_w = 1.0 / 24 if not profile.hour_weights else 0.0
        hour_weights = [profile.hour_weights.get(h, default_w) for h in hours]
        # Normalize weights
        weight_sum = sum(hour_weights)
        if weight_sum > 0:
            hour_weights = [w / weight_sum for w in hour_weights]

        for i in range(n_bets):
            is_win = self._rng.random() < p
            if is_win:
                pnl = int(profile.avg_win_pnl_cents)
                wins += 1
            else:
                pnl = int(profile.avg_loss_pnl_cents)
            total_pnl += pnl

            # Weighted hour selection
            hour = self._weighted_choice(hours, hour_weights)

            bet = SyntheticBet(
                synthetic_id=i,
                bucket_key=profile.bucket_key,
                timestamp_offset=i * 900.0,  # 15-min spacing
                ticker=f"{profile.asset}15M-SYN-{i:04d}",
                side=profile.side,
                price_cents=profile.price_cents,
                result="win" if is_win else "loss",
                pnl_cents=pnl,
                hour_utc=hour,
            )
            seq.bets.append(bet)

        seq.actual_wr = wins / n_bets if n_bets > 0 else 0.0
        seq.total_pnl_cents = total_pnl
        return seq

    def generate_sweep(
        self,
        profile: BucketProfile,
        n_bets: int,
        p_lo: float,
        p_hi: float,
        steps: int,
    ) -> list[SyntheticSequence]:
        """Generate multiple sequences at different win rates for sensitivity analysis."""
        sequences = []
        for i in range(steps):
            p = p_lo + (p_hi - p_lo) * i / max(steps - 1, 1)
            seq = self.generate_parametric(profile, n_bets, win_rate_override=p)
            seq.mode = "sweep"
            sequences.append(seq)
        return sequences

    def _weighted_choice(self, items: list, weights: list) -> any:
        """Weighted random selection (stdlib-only, no numpy)."""
        if not items:
            return 0
        r = self._rng.random()
        cumulative = 0.0
        for item, weight in zip(items, weights):
            cumulative += weight
            if r <= cumulative:
                return item
        return items[-1]

    def save_sequence(self, seq: SyntheticSequence, output_dir: str = OUTPUT_DIR) -> str:
        """Save sequence to JSONL file. Returns path."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_key = seq.bucket_key.replace("|", "_")
        filename = f"synthetic_{safe_key}_{seq.mode}_{timestamp}.jsonl"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w") as f:
            # Metadata line
            meta = {
                "type": "metadata",
                "bucket_key": seq.bucket_key,
                "mode": seq.mode,
                "n_bets": seq.n_bets,
                "win_rate_param": seq.win_rate_param,
                "actual_wr": seq.actual_wr,
                "total_pnl_cents": seq.total_pnl_cents,
                "seed": seq.seed,
            }
            f.write(json.dumps(meta) + "\n")
            # Bet lines
            for bet in seq.bets:
                f.write(json.dumps(bet.to_dict()) + "\n")

        return filepath

    def load_sequence(self, filepath: str) -> SyntheticSequence:
        """Load a previously saved sequence."""
        bets = []
        meta = {}
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "metadata":
                    meta = obj
                else:
                    bets.append(SyntheticBet(**{
                        k: v for k, v in obj.items()
                        if k in SyntheticBet.__dataclass_fields__
                    }))

        return SyntheticSequence(
            bucket_key=meta.get("bucket_key", "unknown"),
            mode=meta.get("mode", "unknown"),
            n_bets=meta.get("n_bets", len(bets)),
            win_rate_param=meta.get("win_rate_param", 0.0),
            actual_wr=meta.get("actual_wr", 0.0),
            total_pnl_cents=meta.get("total_pnl_cents", 0),
            seed=meta.get("seed"),
            bets=bets,
        )


# ── Summary Statistics ───────────────────────────────────────────────────────


def sequence_summary(seq: SyntheticSequence) -> dict:
    """Compute summary statistics for a synthetic sequence."""
    if not seq.bets:
        return {"n": 0}

    pnls = [b.pnl_cents for b in seq.bets]
    wins = sum(1 for b in seq.bets if b.result == "win")
    cumulative = []
    running = 0
    max_drawdown = 0
    peak = 0
    for p in pnls:
        running += p
        cumulative.append(running)
        peak = max(peak, running)
        drawdown = peak - running
        max_drawdown = max(max_drawdown, drawdown)

    return {
        "n": len(seq.bets),
        "wins": wins,
        "losses": len(seq.bets) - wins,
        "actual_wr": round(wins / len(seq.bets), 4),
        "total_pnl_cents": sum(pnls),
        "avg_pnl_cents": round(sum(pnls) / len(pnls), 1),
        "max_drawdown_cents": max_drawdown,
        "peak_pnl_cents": peak,
        "final_pnl_cents": cumulative[-1] if cumulative else 0,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Synthetic Bet Generator")
    parser.add_argument("--bucket", type=str, help="Bucket key (e.g. KXBTC|93|no)")
    parser.add_argument("--n", type=int, default=1000, help="Number of bets to generate")
    parser.add_argument("--mode", choices=["parametric", "sweep"], default="parametric")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--p-range", type=str, help="Win rate range for sweep (e.g. 0.88,0.98)")
    parser.add_argument("--steps", type=int, default=10, help="Number of sweep steps")
    parser.add_argument("--save", action="store_true", help="Save to JSONL")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    if not args.bucket:
        print("Error: --bucket required (e.g. KXBTC|93|no)")
        sys.exit(1)

    builder = ProfileBuilder()
    profile = builder.build_from_db(args.bucket)
    if profile is None:
        profile = builder.build_from_learning_state(args.bucket)
    if profile is None:
        print(f"Error: No data found for bucket {args.bucket}")
        sys.exit(1)

    gen = SyntheticBetGenerator(seed=args.seed)

    if args.mode == "sweep":
        if not args.p_range:
            print("Error: --p-range required for sweep mode (e.g. 0.88,0.98)")
            sys.exit(1)
        p_lo, p_hi = [float(x) for x in args.p_range.split(",")]
        sequences = gen.generate_sweep(profile, args.n, p_lo, p_hi, args.steps)
        for seq in sequences:
            summary = sequence_summary(seq)
            if args.json:
                print(json.dumps({"p": seq.win_rate_param, **summary}))
            else:
                print(f"p={seq.win_rate_param:.3f}: WR={summary['actual_wr']:.3f} PnL={summary['total_pnl_cents']}c DD={summary['max_drawdown_cents']}c")
            if args.save:
                path = gen.save_sequence(seq)
                print(f"  Saved: {path}")
    else:
        seq = gen.generate_parametric(profile, args.n)
        summary = sequence_summary(seq)
        if args.json:
            print(json.dumps(summary, indent=2))
        else:
            print(f"Bucket: {profile.bucket_key}")
            print(f"Historical: {profile.n_historical} bets, WR={profile.win_rate:.3f}")
            print(f"Generated: {summary['n']} bets, WR={summary['actual_wr']:.3f}")
            print(f"PnL: {summary['total_pnl_cents']}c (peak: {summary['peak_pnl_cents']}c, DD: {summary['max_drawdown_cents']}c)")
        if args.save:
            path = gen.save_sequence(seq)
            print(f"Saved: {path}")


if __name__ == "__main__":
    main()
