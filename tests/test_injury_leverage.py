"""
Tests for src/data/injury_leverage.py — positional injury kill switch.

Covers:
1. get_positional_leverage: known positions, unknown positions, sport aliases
2. evaluate_injury_impact: kill/flag thresholds, non-starter returns zero, totals market
3. injury_kill_switch: wrapper returns (True, str) on kill, (False, "") when below threshold
4. list_high_leverage_positions: sorted results, min_leverage filter
5. SportsSniper.evaluate: injury guard kills signal when kill threshold met
"""

import unittest

from src.data.injury_leverage import (
    get_positional_leverage,
    evaluate_injury_impact,
    injury_kill_switch,
    list_high_leverage_positions,
    LEVERAGE_KILL_THRESHOLD,
    LEVERAGE_FLAG_THRESHOLD,
)


class TestGetPositionalLeverage(unittest.TestCase):

    def test_nba_pg_is_pivotal(self):
        lev, pivotal = get_positional_leverage("NBA", "PG")
        self.assertAlmostEqual(lev, 3.0)
        self.assertTrue(pivotal)

    def test_nfl_qb_pivotal(self):
        lev, pivotal = get_positional_leverage("NFL", "QB")
        self.assertAlmostEqual(lev, 4.5)
        self.assertTrue(pivotal)

    def test_nhl_goalie_is_pivotal(self):
        lev, pivotal = get_positional_leverage("NHL", "G")
        self.assertAlmostEqual(lev, 3.5)
        self.assertTrue(pivotal)

    def test_mlb_sp_pivotal(self):
        lev, pivotal = get_positional_leverage("MLB", "SP")
        self.assertAlmostEqual(lev, 2.0)
        self.assertTrue(pivotal)

    def test_unknown_position_returns_zero(self):
        lev, pivotal = get_positional_leverage("NBA", "UNKNOWN")
        self.assertEqual(lev, 0.0)
        self.assertFalse(pivotal)

    def test_unknown_sport_returns_zero(self):
        lev, pivotal = get_positional_leverage("TENNIS", "anything")
        self.assertEqual(lev, 0.0)
        self.assertFalse(pivotal)

    def test_lowercase_sport_alias(self):
        # "nba" → "NBA"
        lev_lower, _ = get_positional_leverage("nba", "PG")
        lev_upper, _ = get_positional_leverage("NBA", "PG")
        self.assertEqual(lev_lower, lev_upper)

    def test_nfl_rb_not_pivotal(self):
        _, pivotal = get_positional_leverage("NFL", "RB")
        self.assertFalse(pivotal)


class TestEvaluateInjuryImpact(unittest.TestCase):

    def test_nba_pg_starter_home_bet_home_injury_flags_not_kills(self):
        # NBA PG leverage=3.0, multiplier=-1.0, signed=-3.0. Flag (>=2.0) but NOT kill (>=3.5).
        r = evaluate_injury_impact("NBA", "PG", True, "home", "h2h", "home")
        self.assertTrue(r.flag)
        self.assertFalse(r.kill)  # 3.0 < 3.5 kill threshold
        self.assertLess(r.signed_impact, 0)

    def test_nhl_goalie_starter_home_bet_home_injury_kills(self):
        # NHL G leverage=3.5, multiplier=-1.0, signed=-3.5 >= kill threshold
        r = evaluate_injury_impact("NHL", "G", True, "home", "h2h", "home")
        self.assertTrue(r.kill)
        self.assertLess(r.signed_impact, 0)

    def test_non_starter_no_impact(self):
        r = evaluate_injury_impact("NBA", "PG", False, "home", "h2h", "home")
        self.assertEqual(r.leverage_pts, 0.0)
        self.assertFalse(r.flag)
        self.assertFalse(r.kill)

    def test_away_injury_helps_home_bet(self):
        r = evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
        self.assertGreater(r.signed_impact, 0)

    def test_nfl_qb_injury_on_bet_team_kills(self):
        r = evaluate_injury_impact("NFL", "QB", True, "home", "spreads", "home")
        self.assertTrue(r.kill)

    def test_totals_market_uses_total_multiplier(self):
        r = evaluate_injury_impact("NBA", "PG", True, "home", "totals", "home")
        # totals multiplier = -0.3 → signed_impact = 3.0 * -0.3 = -0.9 → no kill
        self.assertFalse(r.kill)
        self.assertAlmostEqual(r.signed_impact, -0.9, places=2)

    def test_unknown_position_no_flag(self):
        r = evaluate_injury_impact("NBA", "XYZ", True, "home", "h2h", "home")
        self.assertFalse(r.flag)
        self.assertFalse(r.kill)

    def test_advisory_contains_severity(self):
        r = evaluate_injury_impact("NFL", "QB", True, "home", "h2h", "home")
        self.assertIn("KILL", r.advisory)

    def test_flag_threshold(self):
        # NFL RB leverage=1.5, multiplier=-1.0, signed=-1.5 → flag (>=2.0? no)
        # SG leverage=2.0, multiplier=-1.0, signed=-2.0 → flag (>=2.0)
        r = evaluate_injury_impact("NBA", "SG", True, "home", "h2h", "home")
        self.assertTrue(r.flag)
        self.assertFalse(r.kill)


class TestInjuryKillSwitch(unittest.TestCase):

    def test_returns_true_on_kill(self):
        # NHL G leverage=3.5 >= kill threshold 3.5
        kill, reason = injury_kill_switch("NHL", "G", True, "home", "h2h", "home")
        self.assertTrue(kill)
        self.assertIn("KILL", reason)

    def test_returns_false_below_kill_threshold(self):
        # NFL RB leverage=1.5, below 3.5 kill threshold
        kill, reason = injury_kill_switch("NFL", "RB", True, "home", "h2h", "home")
        self.assertFalse(kill)

    def test_returns_empty_string_when_no_impact(self):
        kill, reason = injury_kill_switch("NHL", "LW", False, "home", "h2h", "home")
        self.assertFalse(kill)
        self.assertEqual(reason, "")

    def test_nhl_goalie_kills(self):
        # NHL G leverage=3.5 >= kill threshold
        kill, reason = injury_kill_switch("NHL", "G", True, "home", "h2h", "home")
        self.assertTrue(kill)


class TestListHighLeveragePositions(unittest.TestCase):

    def test_nfl_qb_is_first(self):
        positions = list_high_leverage_positions("NFL", min_leverage=2.0)
        self.assertEqual(positions[0][0], "QB")
        self.assertAlmostEqual(positions[0][1], 4.5)

    def test_sorted_descending(self):
        positions = list_high_leverage_positions("NBA", min_leverage=0.0)
        leverages = [lev for _, lev, _ in positions]
        self.assertEqual(leverages, sorted(leverages, reverse=True))

    def test_min_leverage_filter(self):
        positions = list_high_leverage_positions("MLB", min_leverage=1.0)
        for _, lev, _ in positions:
            self.assertGreaterEqual(lev, 1.0)

    def test_unknown_sport_returns_empty(self):
        positions = list_high_leverage_positions("TENNIS")
        self.assertEqual(positions, [])


class TestSportsSniperInjuryGuard(unittest.TestCase):
    """Integration: SportsSniper.evaluate() blocks signal when injury kill threshold met."""

    def _make_game(self, sport="nba", leading_team="CHI", period=4, lead=16):
        return {
            "sport": sport,
            "home": "CHI",
            "away": "OKC",
            "home_score": 100,
            "away_score": 84,
            "period": period,
            "clock": "2:00",
            "lead": lead,
            "leading_team": leading_team,
            "status": "in_progress",
        }

    def test_signal_fires_without_injuries(self):
        from src.strategies.sports_sniper import SportsSniper
        sniper = SportsSniper()
        signal = sniper.evaluate(self._make_game(), price_cents=92)
        self.assertIsNotNone(signal)

    def test_signal_blocked_by_injury_kill(self):
        from src.strategies.sports_sniper import SportsSniper
        sniper = SportsSniper()
        # NHL game: G leverage=3.5 >= kill threshold when betting home team that lost goalie
        nhl_game = self._make_game(sport="nhl", period=3, lead=3)
        injuries = [{"position": "G", "is_starter": True, "team_side": "home"}]
        signal = sniper.evaluate(nhl_game, price_cents=92, injuries=injuries)
        self.assertIsNone(signal)

    def test_signal_not_blocked_by_non_starter(self):
        from src.strategies.sports_sniper import SportsSniper
        sniper = SportsSniper()
        injuries = [{"position": "PG", "is_starter": False, "team_side": "home"}]
        signal = sniper.evaluate(self._make_game(), price_cents=92, injuries=injuries)
        self.assertIsNotNone(signal)

    def test_signal_not_blocked_by_low_leverage_injury(self):
        from src.strategies.sports_sniper import SportsSniper
        sniper = SportsSniper()
        # NFL RB leverage=1.5, below kill threshold
        injuries = [{"position": "RB", "is_starter": True, "team_side": "home"}]
        signal = sniper.evaluate(self._make_game(), price_cents=92, injuries=injuries)
        # Sport is NBA so RB not in table → (0.0, False) → no kill
        self.assertIsNotNone(signal)

    def test_empty_injuries_list_no_kill(self):
        from src.strategies.sports_sniper import SportsSniper
        sniper = SportsSniper()
        signal = sniper.evaluate(self._make_game(), price_cents=92, injuries=[])
        self.assertIsNotNone(signal)


if __name__ == "__main__":
    unittest.main()
