"""
Tests for src/strategies/sports_math.py — ported math from agentic-rd-sandbox.
"""

import pytest
from src.strategies.sports_math import (
    implied_probability,
    no_vig_probability,
    no_vig_probability_3way,
    passes_collar,
    passes_collar_soccer,
    assign_grade,
    nba_kill_switch,
    nhl_kill_switch,
    american_odds_from_prob,
)


# ---------------------------------------------------------------------------
# implied_probability
# ---------------------------------------------------------------------------

class TestImpliedProbability:
    def test_favourite(self):
        assert round(implied_probability(-110), 4) == 0.5238

    def test_underdog(self):
        assert round(implied_probability(110), 4) == 0.4762

    def test_heavy_favourite(self):
        assert round(implied_probability(-180), 4) == 0.6429

    def test_even_money(self):
        assert round(implied_probability(100), 4) == 0.5000

    def test_sum_exceeds_one(self):
        # Both sides of a juiced market sum to > 1.0 (the vig)
        total = implied_probability(-110) + implied_probability(-110)
        assert total > 1.0


# ---------------------------------------------------------------------------
# no_vig_probability
# ---------------------------------------------------------------------------

class TestNoVigProbability:
    def test_even_market(self):
        a, b = no_vig_probability(-110, -110)
        assert round(a, 4) == 0.5
        assert round(b, 4) == 0.5
        assert round(a + b, 6) == 1.0

    def test_asymmetric_market(self):
        a, b = no_vig_probability(-180, 150)
        assert round(a + b, 6) == 1.0
        assert a > b  # favourite has higher fair prob

    def test_returns_tuple(self):
        result = no_vig_probability(-110, 100)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# no_vig_probability_3way
# ---------------------------------------------------------------------------

class TestNoVigProbability3Way:
    def test_sums_to_one(self):
        a, b, c = no_vig_probability_3way(-105, 290, 250)
        assert round(a + b + c, 4) == 1.0

    def test_favourite_highest_prob(self):
        a, b, c = no_vig_probability_3way(-105, 290, 250)
        assert a > b  # home favourite

    def test_returns_tuple_of_three(self):
        result = no_vig_probability_3way(-105, 290, 250)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# passes_collar
# ---------------------------------------------------------------------------

class TestPassesCollar:
    def test_inside_collar(self):
        assert passes_collar(-110) is True
        assert passes_collar(100) is True
        assert passes_collar(-180) is True
        assert passes_collar(150) is True

    def test_outside_collar_heavy_fav(self):
        assert passes_collar(-200) is False
        assert passes_collar(-181) is False

    def test_outside_collar_big_dog(self):
        assert passes_collar(151) is False
        assert passes_collar(200) is False

    def test_at_boundaries(self):
        # Boundary values are inclusive
        assert passes_collar(-180) is True
        assert passes_collar(150) is True


# ---------------------------------------------------------------------------
# passes_collar_soccer
# ---------------------------------------------------------------------------

class TestPassesCollarSoccer:
    def test_standard_odds_pass(self):
        assert passes_collar_soccer(-110) is True
        assert passes_collar_soccer(100) is True

    def test_expanded_range(self):
        # Soccer allows heavier favourites and bigger dogs/draws
        assert passes_collar_soccer(-250) is True
        assert passes_collar_soccer(400) is True

    def test_beyond_expanded_range(self):
        assert passes_collar_soccer(-260) is False
        assert passes_collar_soccer(401) is False

    def test_soccer_rejects_where_standard_would_too(self):
        # Standard collar would reject these, soccer too
        assert passes_collar_soccer(-300) is False


# ---------------------------------------------------------------------------
# assign_grade
# ---------------------------------------------------------------------------

class TestAssignGrade:
    def test_grade_a(self):
        assert assign_grade(0.05) == "A"    # 5% edge = Grade A
        assert assign_grade(0.035) == "A"   # exactly at threshold

    def test_grade_b(self):
        assert assign_grade(0.02) == "B"
        assert assign_grade(0.015) == "B"   # exactly at threshold

    def test_grade_c(self):
        assert assign_grade(0.008) == "C"
        assert assign_grade(0.005) == "C"   # exactly at threshold

    def test_near_miss(self):
        assert assign_grade(0.001) == "NEAR_MISS"
        assert assign_grade(0.0) == "NEAR_MISS"

    def test_large_edge_still_a(self):
        assert assign_grade(0.20) == "A"


# ---------------------------------------------------------------------------
# nba_kill_switch
# ---------------------------------------------------------------------------

class TestNbaKillSwitch:
    def test_rest_disadvantage_tight_spread_kills(self):
        killed, reason = nba_kill_switch(True, -3.5)
        assert killed is True
        assert "Rest disadvantage" in reason

    def test_rest_disadvantage_large_spread_ok(self):
        killed, reason = nba_kill_switch(True, -8.5)
        assert killed is False
        assert reason == ""

    def test_no_disadvantage_no_kill(self):
        killed, reason = nba_kill_switch(False, -3.5)
        assert killed is False

    def test_road_b2b_flags(self):
        killed, reason = nba_kill_switch(False, 0.0, b2b=True, is_road_b2b=True)
        assert killed is False
        assert "Road B2B" in reason

    def test_home_b2b_flags(self):
        killed, reason = nba_kill_switch(False, 0.0, b2b=True)
        assert killed is False
        assert "Home B2B" in reason

    def test_clean_situation_no_kill(self):
        killed, reason = nba_kill_switch(False, -5.0)
        assert killed is False
        assert reason == ""

    def test_spread_at_boundary_kills(self):
        # abs(spread) < 4 → kills on rest disadvantage
        killed, reason = nba_kill_switch(True, -3.9)
        assert killed is True

    def test_spread_at_boundary_ok(self):
        # abs(spread) = 4 → does NOT kill
        killed, reason = nba_kill_switch(True, -4.0)
        assert killed is False


# ---------------------------------------------------------------------------
# nhl_kill_switch
# ---------------------------------------------------------------------------

class TestNhlKillSwitch:
    def test_backup_goalie_kills(self):
        killed, reason = nhl_kill_switch(True)
        assert killed is True
        assert "Backup goalie" in reason

    def test_b2b_flags_not_kills(self):
        killed, reason = nhl_kill_switch(False, b2b=True)
        assert killed is False
        assert "B2B" in reason

    def test_goalie_unconfirmed_flags(self):
        killed, reason = nhl_kill_switch(False, goalie_confirmed=False)
        assert killed is False
        assert "not yet confirmed" in reason

    def test_clean_situation(self):
        killed, reason = nhl_kill_switch(False)
        assert killed is False
        assert reason == ""


# ---------------------------------------------------------------------------
# american_odds_from_prob
# ---------------------------------------------------------------------------

class TestAmericanOddsFromProb:
    def test_favourite(self):
        # 55% win prob → negative American odds
        odds = american_odds_from_prob(0.55)
        assert odds < 0

    def test_underdog(self):
        # 45% win prob → positive American odds
        odds = american_odds_from_prob(0.45)
        assert odds > 0

    def test_even_money(self):
        # 50% → ±100
        assert american_odds_from_prob(0.50) in (-100, 100)

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            american_odds_from_prob(0.0)
        with pytest.raises(ValueError):
            american_odds_from_prob(1.0)
