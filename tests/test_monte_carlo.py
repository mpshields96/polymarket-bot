"""
Tests for src/models/monte_carlo.py — Trinity simulation + Poisson soccer.

Covers:
1. efficiency_gap_to_margin: neutral, home-favoured, away-favoured
2. run_trinity_simulation: probability bounds, seed reproducibility, iterations
3. poisson_soccer: sum-to-1 invariant, over/under bounds, home advantage effect
4. efficiency_gap_to_soccer_strength: neutral gap → all 1.0
"""

import unittest

from src.models.monte_carlo import (
    SimulationResult,
    PoissonResult,
    efficiency_gap_to_margin,
    efficiency_gap_to_soccer_strength,
    run_trinity_simulation,
    poisson_soccer,
    EFFICIENCY_GAP_NEUTRAL,
)


class TestEfficiencyGapToMargin(unittest.TestCase):

    def test_neutral_gap_is_zero(self):
        self.assertAlmostEqual(efficiency_gap_to_margin(10.0), 0.0)

    def test_home_favoured(self):
        self.assertAlmostEqual(efficiency_gap_to_margin(15.0), 5.0)

    def test_away_favoured(self):
        self.assertAlmostEqual(efficiency_gap_to_margin(5.0), -5.0)

    def test_home_advantage_pts_added(self):
        # gap=10 (neutral) + 2.5 home pts = 2.5
        self.assertAlmostEqual(efficiency_gap_to_margin(10.0, home_advantage_pts=2.5), 2.5)

    def test_combined(self):
        # gap=12.5 (+2.5 gap pts) + 2.5 home = 5.0
        self.assertAlmostEqual(efficiency_gap_to_margin(12.5, home_advantage_pts=2.5), 5.0)


class TestTrinitySim(unittest.TestCase):

    def test_returns_simulation_result(self):
        result = run_trinity_simulation(0.0, "NBA", line=0.0, seed=42)
        self.assertIsInstance(result, SimulationResult)

    def test_cover_prob_near_50_for_even_match(self):
        result = run_trinity_simulation(0.0, "NBA", line=0.0, seed=99)
        self.assertGreater(result.cover_probability, 0.35)
        self.assertLess(result.cover_probability, 0.65)

    def test_cover_prob_higher_with_positive_mean(self):
        result_adv = run_trinity_simulation(10.0, "NBA", line=0.0, seed=42)
        result_even = run_trinity_simulation(0.0, "NBA", line=0.0, seed=42)
        self.assertGreater(result_adv.cover_probability, result_even.cover_probability)

    def test_iterations_count(self):
        result = run_trinity_simulation(0.0, "NBA", seed=1)
        self.assertEqual(result.iterations, 10_000)

    def test_custom_iterations(self):
        result = run_trinity_simulation(0.0, "NBA", iterations=1000, seed=1)
        self.assertEqual(result.iterations, 1000)

    def test_seed_reproducibility(self):
        r1 = run_trinity_simulation(5.0, "NFL", line=-3.0, seed=123)
        r2 = run_trinity_simulation(5.0, "NFL", line=-3.0, seed=123)
        self.assertAlmostEqual(r1.cover_probability, r2.cover_probability)

    def test_ci_10_lt_ci_90(self):
        result = run_trinity_simulation(0.0, "NBA", seed=7)
        self.assertLess(result.ci_10, result.ci_90)

    def test_volatility_positive(self):
        result = run_trinity_simulation(0.0, "NBA", seed=3)
        self.assertGreater(result.volatility, 0.0)

    def test_over_prob_zero_when_no_total_line(self):
        result = run_trinity_simulation(0.0, "NBA", total_line=None, seed=42)
        self.assertEqual(result.over_probability, 0.0)

    def test_over_prob_nonzero_with_total_line(self):
        result = run_trinity_simulation(0.0, "NBA", total_line=220.0, seed=42)
        self.assertGreater(result.over_probability, 0.0)
        self.assertLess(result.over_probability, 1.0)

    def test_unknown_sport_uses_default_volatility(self):
        # Should not raise — uses _DEFAULT_VOLATILITY
        result = run_trinity_simulation(0.0, "CRICKET", seed=1)
        self.assertIsInstance(result, SimulationResult)
        self.assertGreater(result.volatility, 0.0)

    def test_nhl_volatility_lower_than_nfl(self):
        # NHL base_vol=1.8, NFL=10.5 → NHL results should have lower spread
        r_nhl = run_trinity_simulation(0.0, "NHL", seed=5, iterations=5000)
        r_nfl = run_trinity_simulation(0.0, "NFL", seed=5, iterations=5000)
        self.assertLess(r_nhl.volatility, r_nfl.volatility)


class TestPoissonSoccer(unittest.TestCase):

    def test_returns_poisson_result(self):
        result = poisson_soccer()
        self.assertIsInstance(result, PoissonResult)

    def test_probabilities_sum_to_one(self):
        result = poisson_soccer()
        total = result.home_win + result.draw + result.away_win
        self.assertAlmostEqual(total, 1.0, places=2)

    def test_over_prob_in_bounds(self):
        result = poisson_soccer(total_line=2.5)
        self.assertGreater(result.over_probability, 0.0)
        self.assertLess(result.over_probability, 1.0)

    def test_home_advantage_increases_home_win(self):
        with_adv = poisson_soccer(apply_home_advantage=True)
        without_adv = poisson_soccer(apply_home_advantage=False)
        self.assertGreater(with_adv.home_win, without_adv.home_win)

    def test_strong_home_attack_increases_home_win(self):
        strong = poisson_soccer(home_attack=1.5)
        neutral = poisson_soccer(home_attack=1.0)
        self.assertGreater(strong.home_win, neutral.home_win)

    def test_expected_total_positive(self):
        result = poisson_soccer()
        self.assertGreater(result.expected_total, 0.0)

    def test_max_goals_is_10(self):
        result = poisson_soccer()
        self.assertEqual(result.max_goals, 10)


class TestEfficiencyGapToSoccerStrength(unittest.TestCase):

    def test_neutral_gap_returns_ones(self):
        h_att, a_att, h_def, a_def = efficiency_gap_to_soccer_strength(10.0)
        self.assertAlmostEqual(h_att, 1.0, places=3)
        self.assertAlmostEqual(a_att, 1.0, places=3)

    def test_home_stronger_when_gap_above_neutral(self):
        h_att, a_att, _, _ = efficiency_gap_to_soccer_strength(15.0)
        self.assertGreater(h_att, 1.0)
        self.assertLess(a_att, 1.0)

    def test_away_stronger_when_gap_below_neutral(self):
        h_att, a_att, _, _ = efficiency_gap_to_soccer_strength(5.0)
        self.assertLess(h_att, 1.0)
        self.assertGreater(a_att, 1.0)

    def test_values_clamped_above_0_5(self):
        # Extreme gap should not go below 0.5
        h_att, a_att, h_def, a_def = efficiency_gap_to_soccer_strength(0.0)
        self.assertGreaterEqual(min(h_att, a_att, h_def, a_def), 0.5)


if __name__ == "__main__":
    unittest.main()
