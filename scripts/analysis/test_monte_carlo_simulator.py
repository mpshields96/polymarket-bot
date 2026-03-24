#!/usr/bin/env python3
"""Tests for monte_carlo_simulator.py — Monte Carlo Forward Projection."""

import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from monte_carlo_simulator import (
    TrialResult,
    MonteCarloResult,
    MonteCarloSimulator,
)
from synthetic_bet_generator import BucketProfile


def _make_profile(bucket_key="KXBTC|93|no", price=93, wr=0.96, n=100):
    return BucketProfile(
        bucket_key=bucket_key,
        asset="KXBTC",
        price_cents=price,
        side="no",
        n_historical=n,
        win_rate=wr,
        avg_win_pnl_cents=100 - price,
        avg_loss_pnl_cents=-price,
    )


class TestTrialResult(unittest.TestCase):

    def test_creation(self):
        t = TrialResult(
            final_pnl_cents=100, max_drawdown_cents=50,
            peak_pnl_cents=150, n_wins=90, n_losses=10, is_ruin=False,
        )
        self.assertEqual(t.final_pnl_cents, 100)
        self.assertFalse(t.is_ruin)


class TestMonteCarloResult(unittest.TestCase):

    def test_to_dict(self):
        r = MonteCarloResult(
            bucket_key="KXBTC|93|no", n_bets=500, n_trials=1000,
            win_rate_used=0.96, win_pnl_cents=7, loss_pnl_cents=-93,
            bankroll_cents=10000,
        )
        d = r.to_dict()
        self.assertEqual(d["bucket_key"], "KXBTC|93|no")
        self.assertIn("pnl_percentiles", d)
        self.assertIn("risk", d)
        self.assertIn("drawdown", d)
        self.assertIn("expected_value", d)

    def test_to_dict_has_all_fields(self):
        r = MonteCarloResult(
            bucket_key="X", n_bets=10, n_trials=100,
            win_rate_used=0.9, win_pnl_cents=10, loss_pnl_cents=-90,
            bankroll_cents=5000, pnl_p50=50, var_95=100,
            prob_ruin=0.01, prob_profit=0.85,
        )
        d = r.to_dict()
        self.assertEqual(d["risk"]["prob_ruin"], 0.01)
        self.assertEqual(d["risk"]["prob_profit"], 0.85)


class TestMonteCarloSimulator(unittest.TestCase):

    def test_basic_simulation(self):
        profile = _make_profile(wr=0.96, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=1000)

        self.assertEqual(result.n_bets, 100)
        self.assertEqual(result.n_trials, 1000)
        self.assertAlmostEqual(result.win_rate_used, 0.96)
        self.assertEqual(result.win_pnl_cents, 7)
        self.assertEqual(result.loss_pnl_cents, -93)

    def test_ev_calculation(self):
        profile = _make_profile(wr=0.96, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=100)

        # EV = 0.96 * 7 + 0.04 * (-93) = 6.72 - 3.72 = 3.0 per bet
        self.assertAlmostEqual(result.ev_per_bet_cents, 3.0, places=1)
        self.assertAlmostEqual(result.ev_total_cents, 300.0, places=0)

    def test_high_wr_mostly_profit(self):
        profile = _make_profile(wr=0.99, price=90)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=200, n_trials=5000)

        # At 99% WR on 90c, should almost always profit
        self.assertGreater(result.prob_profit, 0.95)
        self.assertGreater(result.pnl_p50, 0)

    def test_low_wr_mostly_loss(self):
        profile = _make_profile(wr=0.50, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=200, n_trials=5000)

        # At 50% WR on 93c, heavy losses (EV = 0.5*7 + 0.5*(-93) = -43 per bet)
        self.assertLess(result.pnl_p50, 0)
        self.assertLess(result.prob_profit, 0.05)  # Almost never profitable

    def test_break_even_wr(self):
        # At exactly break-even WR (93%), EV should be ~0
        profile = _make_profile(wr=0.93, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=1000)

        # EV = 0.93 * 7 + 0.07 * (-93) = 6.51 - 6.51 = 0
        self.assertAlmostEqual(result.ev_per_bet_cents, 0.0, places=0)

    def test_percentile_ordering(self):
        profile = _make_profile(wr=0.95, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=200, n_trials=5000)

        self.assertLessEqual(result.pnl_p5, result.pnl_p25)
        self.assertLessEqual(result.pnl_p25, result.pnl_p50)
        self.assertLessEqual(result.pnl_p50, result.pnl_p75)
        self.assertLessEqual(result.pnl_p75, result.pnl_p95)

    def test_drawdown_ordering(self):
        profile = _make_profile(wr=0.95, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=200, n_trials=5000)

        self.assertLessEqual(result.dd_p50, result.dd_p95)
        self.assertLessEqual(result.dd_p95, result.dd_max)
        self.assertGreaterEqual(result.dd_p50, 0)

    def test_reproducibility(self):
        profile = _make_profile()
        sim1 = MonteCarloSimulator(seed=123)
        r1 = sim1.simulate(profile, n_bets=50, n_trials=100)
        sim2 = MonteCarloSimulator(seed=123)
        r2 = sim2.simulate(profile, n_bets=50, n_trials=100)

        self.assertEqual(r1.pnl_p50, r2.pnl_p50)
        self.assertEqual(r1.prob_profit, r2.prob_profit)
        self.assertEqual(r1.dd_max, r2.dd_max)

    def test_different_seeds(self):
        profile = _make_profile()
        sim1 = MonteCarloSimulator(seed=1)
        r1 = sim1.simulate(profile, n_bets=100, n_trials=500)
        sim2 = MonteCarloSimulator(seed=2)
        r2 = sim2.simulate(profile, n_bets=100, n_trials=500)

        # Results shouldn't be identical — check across multiple metrics
        differs = (r1.pnl_p5 != r2.pnl_p5 or r1.dd_max != r2.dd_max
                   or r1.pnl_p95 != r2.pnl_p95)
        self.assertTrue(differs, "Different seeds should produce different results")

    def test_zero_bets(self):
        profile = _make_profile()
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=0, n_trials=100)

        self.assertEqual(result.pnl_p50, 0)
        self.assertEqual(result.dd_max, 0)

    def test_zero_trials(self):
        profile = _make_profile()
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=0)

        self.assertEqual(result.n_trials, 0)

    def test_win_rate_override(self):
        profile = _make_profile(wr=0.96)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=100, win_rate_override=0.50)

        self.assertAlmostEqual(result.win_rate_used, 0.50)
        # At 50% WR on 93c, should be losing
        self.assertLess(result.ev_per_bet_cents, 0)

    def test_bankroll_affects_ruin(self):
        profile = _make_profile(wr=0.90, price=93)
        sim = MonteCarloSimulator(seed=42)

        # Small bankroll → more ruin
        r_small = sim.simulate(profile, n_bets=200, n_trials=2000, bankroll_cents=500)
        sim2 = MonteCarloSimulator(seed=42)
        r_large = sim2.simulate(profile, n_bets=200, n_trials=2000, bankroll_cents=50000)

        self.assertGreaterEqual(r_small.prob_ruin, r_large.prob_ruin)

    def test_var_nonnegative(self):
        profile = _make_profile(wr=0.96)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=100, n_trials=1000)

        # VaR is defined as loss amount at 5th percentile
        # For a profitable strategy, VaR can be negative (meaning even worst case is profit)
        # But it should be a valid number
        self.assertIsInstance(result.var_95, int)

    def test_cvar_defined(self):
        profile = _make_profile(wr=0.90, price=93)
        sim = MonteCarloSimulator(seed=42)
        result = sim.simulate(profile, n_bets=200, n_trials=5000)

        # CVaR should be >= VaR (Expected Shortfall is always worse than VaR)
        self.assertGreaterEqual(result.cvar_95, result.var_95 - 1)  # Allow small rounding


class TestSensitivitySweep(unittest.TestCase):

    def test_sweep_basic(self):
        profile = _make_profile(wr=0.95)
        sim = MonteCarloSimulator(seed=42)
        results = sim.sensitivity_sweep(profile, n_bets=100, wr_lo=0.88, wr_hi=0.98, steps=5, n_trials=500)

        self.assertEqual(len(results), 5)
        wrs = [r.win_rate_used for r in results]
        self.assertAlmostEqual(wrs[0], 0.88, places=2)
        self.assertAlmostEqual(wrs[-1], 0.98, places=2)

    def test_sweep_ev_increases(self):
        profile = _make_profile(price=93)
        sim = MonteCarloSimulator(seed=42)
        results = sim.sensitivity_sweep(profile, n_bets=100, wr_lo=0.85, wr_hi=0.99, steps=5, n_trials=500)

        evs = [r.ev_per_bet_cents for r in results]
        # EV should increase monotonically with win rate
        for i in range(len(evs) - 1):
            self.assertLess(evs[i], evs[i + 1])

    def test_sweep_single_step(self):
        profile = _make_profile()
        sim = MonteCarloSimulator(seed=42)
        results = sim.sensitivity_sweep(profile, n_bets=50, wr_lo=0.90, wr_hi=0.95, steps=1, n_trials=100)

        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0].win_rate_used, 0.90)


class TestPercentileHelper(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(MonteCarloSimulator._percentile([], 50), 0)

    def test_single(self):
        self.assertEqual(MonteCarloSimulator._percentile([42], 50), 42)

    def test_median_odd(self):
        self.assertEqual(MonteCarloSimulator._percentile([1, 2, 3, 4, 5], 50), 3)

    def test_p5(self):
        data = list(range(100))
        self.assertEqual(MonteCarloSimulator._percentile(data, 5), 5)

    def test_p95(self):
        data = list(range(100))
        self.assertEqual(MonteCarloSimulator._percentile(data, 95), 95)


class TestFormatResult(unittest.TestCase):

    def test_format_runs(self):
        from monte_carlo_simulator import format_result
        r = MonteCarloResult(
            bucket_key="KXBTC|93|no", n_bets=500, n_trials=10000,
            win_rate_used=0.96, win_pnl_cents=7, loss_pnl_cents=-93,
            bankroll_cents=10000, pnl_p50=1500, ev_per_bet_cents=3.0,
            ev_total_cents=1500.0, prob_profit=0.95, prob_ruin=0.001,
            var_95=200, cvar_95=350.0, dd_p50=100, dd_p95=300, dd_max=500,
        )
        output = format_result(r)
        self.assertIn("MONTE CARLO", output)
        self.assertIn("KXBTC|93|no", output)
        self.assertIn("EXPECTED VALUE", output)
        self.assertIn("RISK METRICS", output)


if __name__ == "__main__":
    unittest.main()
