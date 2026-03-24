#!/usr/bin/env python3
"""
monte_carlo_simulator.py — Forward-Looking Monte Carlo Simulator for Kalshi Strategies

Projects bucket-level performance under uncertainty using Monte Carlo trials.
Answers: "If the sniper maintains X% WR for N more bets, what's the range of outcomes?"

Outputs:
  - CDF of cumulative PnL (5th, 25th, 50th, 75th, 95th percentiles)
  - Value-at-Risk (VaR) and Conditional VaR (Expected Shortfall)
  - Probability of ruin (cumulative PnL < -bankroll)
  - Max drawdown distribution
  - Kelly-optimal vs flat sizing comparison

Safety: Read-only. Advisory only. No trade execution.

Usage:
    python3 monte_carlo_simulator.py --bucket KXBTC|93|no --n 500 --trials 10000
    python3 monte_carlo_simulator.py --bucket KXBTC|93|no --n 500 --trials 5000 --json
    python3 monte_carlo_simulator.py --bucket KXBTC|93|no --wr-range 0.90,0.98 --n 500
"""

import json
import math
import os
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))

LEARNING_STATE_PATH = os.path.join(PROJECT_ROOT, "data", "learning_state.json")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "polybot.db")

# Import profile builder from synthetic generator (same directory)
sys.path.insert(0, SCRIPT_DIR)
from synthetic_bet_generator import ProfileBuilder, BucketProfile


# ── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class TrialResult:
    """Result of a single Monte Carlo trial."""
    final_pnl_cents: int
    max_drawdown_cents: int
    peak_pnl_cents: int
    n_wins: int
    n_losses: int
    is_ruin: bool  # Final PnL < -bankroll


@dataclass
class MonteCarloResult:
    """Aggregated Monte Carlo simulation results."""
    bucket_key: str
    n_bets: int
    n_trials: int
    win_rate_used: float
    win_pnl_cents: int
    loss_pnl_cents: int
    bankroll_cents: int
    seed: Optional[int] = None

    # PnL percentiles (in cents)
    pnl_p5: int = 0
    pnl_p25: int = 0
    pnl_p50: int = 0  # Median
    pnl_p75: int = 0
    pnl_p95: int = 0
    pnl_mean: float = 0.0

    # Risk metrics
    var_95: int = 0  # 5th percentile loss (Value-at-Risk)
    cvar_95: float = 0.0  # Expected Shortfall below 5th percentile
    prob_ruin: float = 0.0  # P(final PnL < -bankroll)
    prob_profit: float = 0.0  # P(final PnL > 0)

    # Drawdown percentiles
    dd_p50: int = 0
    dd_p95: int = 0
    dd_max: int = 0

    # Expected value
    ev_per_bet_cents: float = 0.0
    ev_total_cents: float = 0.0

    def to_dict(self) -> dict:
        return {
            "bucket_key": self.bucket_key,
            "n_bets": self.n_bets,
            "n_trials": self.n_trials,
            "win_rate_used": round(self.win_rate_used, 4),
            "win_pnl_cents": self.win_pnl_cents,
            "loss_pnl_cents": self.loss_pnl_cents,
            "bankroll_cents": self.bankroll_cents,
            "seed": self.seed,
            "pnl_percentiles": {
                "p5": self.pnl_p5,
                "p25": self.pnl_p25,
                "p50": self.pnl_p50,
                "p75": self.pnl_p75,
                "p95": self.pnl_p95,
                "mean": round(self.pnl_mean, 1),
            },
            "risk": {
                "var_95": self.var_95,
                "cvar_95": round(self.cvar_95, 1),
                "prob_ruin": round(self.prob_ruin, 4),
                "prob_profit": round(self.prob_profit, 4),
            },
            "drawdown": {
                "p50": self.dd_p50,
                "p95": self.dd_p95,
                "max": self.dd_max,
            },
            "expected_value": {
                "per_bet_cents": round(self.ev_per_bet_cents, 2),
                "total_cents": round(self.ev_total_cents, 1),
            },
        }


# ── Monte Carlo Engine ───────────────────────────────────────────────────────


class MonteCarloSimulator:
    """Forward-projects bucket performance with uncertainty quantification."""

    DEFAULT_TRIALS = 10000
    DEFAULT_BANKROLL_CENTS = 10000  # $100

    def __init__(self, seed: int = None):
        self.seed = seed
        self._rng = random.Random(seed)

    def simulate(
        self,
        profile: BucketProfile,
        n_bets: int,
        n_trials: int = None,
        bankroll_cents: int = None,
        win_rate_override: float = None,
    ) -> MonteCarloResult:
        """Run Monte Carlo simulation for a bucket.

        Args:
            profile: Bucket statistical profile
            n_bets: Number of forward bets per trial
            n_trials: Number of Monte Carlo trials (default 10000)
            bankroll_cents: Bankroll for ruin calculation (default 10000 = $100)
            win_rate_override: Override the historical win rate
        """
        if n_trials is None:
            n_trials = self.DEFAULT_TRIALS
        if bankroll_cents is None:
            bankroll_cents = self.DEFAULT_BANKROLL_CENTS

        p = win_rate_override if win_rate_override is not None else profile.win_rate
        win_pnl = int(profile.avg_win_pnl_cents)
        loss_pnl = int(profile.avg_loss_pnl_cents)

        # Run trials
        trials: list[TrialResult] = []
        for _ in range(n_trials):
            trial = self._run_trial(p, win_pnl, loss_pnl, n_bets, bankroll_cents)
            trials.append(trial)

        # Aggregate results
        return self._aggregate(
            trials, profile.bucket_key, n_bets, n_trials,
            p, win_pnl, loss_pnl, bankroll_cents,
        )

    def _run_trial(
        self, p: float, win_pnl: int, loss_pnl: int,
        n_bets: int, bankroll_cents: int,
    ) -> TrialResult:
        """Execute a single trial: n_bets sequential Bernoulli draws."""
        cumulative = 0
        peak = 0
        max_dd = 0
        wins = 0

        for _ in range(n_bets):
            if self._rng.random() < p:
                cumulative += win_pnl
                wins += 1
            else:
                cumulative += loss_pnl

            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        return TrialResult(
            final_pnl_cents=cumulative,
            max_drawdown_cents=max_dd,
            peak_pnl_cents=peak,
            n_wins=wins,
            n_losses=n_bets - wins,
            is_ruin=cumulative < -bankroll_cents,
        )

    def _aggregate(
        self, trials: list[TrialResult],
        bucket_key: str, n_bets: int, n_trials: int,
        p: float, win_pnl: int, loss_pnl: int, bankroll_cents: int,
    ) -> MonteCarloResult:
        """Aggregate trial results into percentiles and risk metrics."""
        if not trials:
            return MonteCarloResult(
                bucket_key=bucket_key, n_bets=n_bets, n_trials=0,
                win_rate_used=p, win_pnl_cents=win_pnl,
                loss_pnl_cents=loss_pnl, bankroll_cents=bankroll_cents,
            )

        pnls = sorted([t.final_pnl_cents for t in trials])
        drawdowns = sorted([t.max_drawdown_cents for t in trials])

        result = MonteCarloResult(
            bucket_key=bucket_key,
            n_bets=n_bets,
            n_trials=n_trials,
            win_rate_used=p,
            win_pnl_cents=win_pnl,
            loss_pnl_cents=loss_pnl,
            bankroll_cents=bankroll_cents,
            seed=self.seed,
        )

        # PnL percentiles
        result.pnl_p5 = self._percentile(pnls, 5)
        result.pnl_p25 = self._percentile(pnls, 25)
        result.pnl_p50 = self._percentile(pnls, 50)
        result.pnl_p75 = self._percentile(pnls, 75)
        result.pnl_p95 = self._percentile(pnls, 95)
        result.pnl_mean = sum(pnls) / len(pnls)

        # VaR and CVaR at 95% confidence
        result.var_95 = -result.pnl_p5  # Loss at 5th percentile
        cutoff_idx = max(1, len(pnls) * 5 // 100)
        tail = pnls[:cutoff_idx]
        result.cvar_95 = -sum(tail) / len(tail) if tail else 0.0

        # Probabilities
        result.prob_ruin = sum(1 for t in trials if t.is_ruin) / len(trials)
        result.prob_profit = sum(1 for t in trials if t.final_pnl_cents > 0) / len(trials)

        # Drawdown percentiles
        result.dd_p50 = self._percentile(drawdowns, 50)
        result.dd_p95 = self._percentile(drawdowns, 95)
        result.dd_max = drawdowns[-1] if drawdowns else 0

        # Expected value (analytical, not simulated)
        result.ev_per_bet_cents = p * win_pnl + (1 - p) * loss_pnl
        result.ev_total_cents = result.ev_per_bet_cents * n_bets

        return result

    @staticmethod
    def _percentile(sorted_data: list, pct: int) -> int:
        """Compute percentile from sorted list. Returns int."""
        if not sorted_data:
            return 0
        idx = max(0, min(len(sorted_data) - 1, int(len(sorted_data) * pct / 100)))
        return sorted_data[idx]

    def sensitivity_sweep(
        self,
        profile: BucketProfile,
        n_bets: int,
        wr_lo: float,
        wr_hi: float,
        steps: int = 10,
        n_trials: int = 1000,
    ) -> list[MonteCarloResult]:
        """Run simulations across a range of win rates."""
        results = []
        for i in range(steps):
            wr = wr_lo + (wr_hi - wr_lo) * i / max(steps - 1, 1)
            r = self.simulate(profile, n_bets, n_trials=n_trials, win_rate_override=wr)
            results.append(r)
        return results


# ── CLI ──────────────────────────────────────────────────────────────────────


def format_result(r: MonteCarloResult) -> str:
    """Format simulation result for console."""
    lines = []
    lines.append("=" * 70)
    lines.append(f"MONTE CARLO SIMULATION: {r.bucket_key}")
    lines.append(f"  {r.n_trials:,} trials x {r.n_bets} bets @ WR={r.win_rate_used:.1%}")
    lines.append(f"  Win: +{r.win_pnl_cents}c / Loss: {r.loss_pnl_cents}c")
    lines.append("=" * 70)

    lines.append(f"\nEXPECTED VALUE:")
    lines.append(f"  Per bet: {r.ev_per_bet_cents:+.2f}c")
    lines.append(f"  Total ({r.n_bets} bets): {r.ev_total_cents:+.1f}c (${r.ev_total_cents/100:+.2f})")

    lines.append(f"\nPnL DISTRIBUTION (cents):")
    lines.append(f"  5th:  {r.pnl_p5:+,}c (${r.pnl_p5/100:+.2f})")
    lines.append(f"  25th: {r.pnl_p25:+,}c (${r.pnl_p25/100:+.2f})")
    lines.append(f"  50th: {r.pnl_p50:+,}c (${r.pnl_p50/100:+.2f})")
    lines.append(f"  75th: {r.pnl_p75:+,}c (${r.pnl_p75/100:+.2f})")
    lines.append(f"  95th: {r.pnl_p95:+,}c (${r.pnl_p95/100:+.2f})")
    lines.append(f"  Mean: {r.pnl_mean:+,.1f}c (${r.pnl_mean/100:+.2f})")

    lines.append(f"\nRISK METRICS:")
    lines.append(f"  VaR (95%):  {r.var_95:,}c (${r.var_95/100:.2f})")
    lines.append(f"  CVaR (95%): {r.cvar_95:,.1f}c (${r.cvar_95/100:.2f})")
    lines.append(f"  P(ruin):    {r.prob_ruin:.2%}")
    lines.append(f"  P(profit):  {r.prob_profit:.2%}")

    lines.append(f"\nDRAWDOWN:")
    lines.append(f"  Median: {r.dd_p50:,}c")
    lines.append(f"  95th:   {r.dd_p95:,}c")
    lines.append(f"  Max:    {r.dd_max:,}c")

    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monte Carlo Simulator")
    parser.add_argument("--bucket", type=str, required=True, help="Bucket key (e.g. KXBTC|93|no)")
    parser.add_argument("--n", type=int, default=500, help="Forward bets per trial")
    parser.add_argument("--trials", type=int, default=10000, help="Number of MC trials")
    parser.add_argument("--bankroll", type=int, default=10000, help="Bankroll in cents")
    parser.add_argument("--wr-override", type=float, help="Override win rate")
    parser.add_argument("--wr-range", type=str, help="Win rate sweep range (e.g. 0.90,0.98)")
    parser.add_argument("--steps", type=int, default=10, help="Sweep steps")
    parser.add_argument("--seed", type=int, help="Random seed")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    builder = ProfileBuilder()
    profile = builder.build_from_db(args.bucket)
    if profile is None:
        profile = builder.build_from_learning_state(args.bucket)
    if profile is None:
        print(f"Error: No data found for bucket {args.bucket}")
        sys.exit(1)

    sim = MonteCarloSimulator(seed=args.seed)

    if args.wr_range:
        lo, hi = [float(x) for x in args.wr_range.split(",")]
        results = sim.sensitivity_sweep(profile, args.n, lo, hi, args.steps, n_trials=args.trials)
        for r in results:
            if args.json:
                print(json.dumps({"wr": r.win_rate_used, **r.to_dict()}))
            else:
                print(f"WR={r.win_rate_used:.3f}: EV={r.ev_total_cents:+.0f}c P(profit)={r.prob_profit:.1%} VaR={r.var_95}c DD95={r.dd_p95}c")
    else:
        result = sim.simulate(
            profile, args.n, n_trials=args.trials,
            bankroll_cents=args.bankroll,
            win_rate_override=args.wr_override,
        )
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(format_result(result))


if __name__ == "__main__":
    main()
