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
    sharp_score_for_bet,
    SHARP_SCORE_MIN,
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


class TestSharpScoreForBet:
    def test_high_edge_passes_threshold(self):
        # 8% edge + eff_gap=12 → 32+12=44 → above SHARP_SCORE_MIN=35
        score = sharp_score_for_bet(0.08, efficiency_gap=12.0)
        assert score == pytest.approx(44.0)
        assert score >= SHARP_SCORE_MIN

    def test_low_edge_below_threshold(self):
        # 6% edge + eff_gap=10 → 24+10=34 → below SHARP_SCORE_MIN=35
        score = sharp_score_for_bet(0.06, efficiency_gap=10.0)
        assert score == pytest.approx(34.0)
        assert score < SHARP_SCORE_MIN

    def test_min_edge_high_gap_passes(self):
        # 5% edge + eff_gap=15 → 20+15=35 → exactly at threshold
        score = sharp_score_for_bet(0.05, efficiency_gap=15.0)
        assert score == pytest.approx(35.0)
        assert score >= SHARP_SCORE_MIN

    def test_edge_capped_at_40(self):
        # 15% edge: (0.15/0.10)*40=60 → capped at 40
        score = sharp_score_for_bet(0.15, efficiency_gap=0.0)
        assert score == pytest.approx(40.0)

    def test_default_eff_gap_fallback(self):
        # No efficiency_gap arg → defaults to 8.0
        score = sharp_score_for_bet(0.10)
        assert score == pytest.approx(40.0 + 8.0)

    def test_rlm_adds_25_pts(self):
        score = sharp_score_for_bet(0.05, efficiency_gap=0.0, rlm_confirmed=True)
        assert score == pytest.approx(20.0 + 25.0)


# ---------------------------------------------------------------------------
# Injury leverage tests (Chat 39)
# ---------------------------------------------------------------------------

from src.strategies.sports_math import (
    get_positional_leverage,
    evaluate_injury_impact,
    injury_kill_switch,
    situational_score_from_injuries,
    InjuryReport,
    LEVERAGE_KILL_THRESHOLD,
    LEVERAGE_FLAG_THRESHOLD,
)


class TestGetPositionalLeverage:
    def test_nba_pg_pivotal(self):
        pts, pivotal = get_positional_leverage("NBA", "PG")
        assert pts == 3.0
        assert pivotal is True

    def test_nfl_qb_highest(self):
        pts, pivotal = get_positional_leverage("NFL", "QB")
        assert pts == 4.5
        assert pivotal is True

    def test_nhl_goalie_pivotal(self):
        pts, pivotal = get_positional_leverage("NHL", "G")
        assert pts == 3.5
        assert pivotal is True

    def test_mlb_sp_pivotal(self):
        pts, pivotal = get_positional_leverage("MLB", "SP")
        assert pts == 2.0
        assert pivotal is True

    def test_unknown_position_returns_zero(self):
        pts, pivotal = get_positional_leverage("NBA", "UNKNOWN")
        assert pts == 0.0
        assert pivotal is False

    def test_unknown_sport_returns_zero(self):
        pts, pivotal = get_positional_leverage("TENNIS", "anything")
        assert pts == 0.0
        assert pivotal is False

    def test_case_insensitive_sport(self):
        pts_upper, _ = get_positional_leverage("NBA", "PG")
        pts_lower, _ = get_positional_leverage("nba", "PG")
        assert pts_upper == pts_lower

    def test_ncaab_alias_uses_nba_table(self):
        pts, _ = get_positional_leverage("ncaab", "PG")
        assert pts == 3.0


class TestEvaluateInjuryImpact:
    def test_nba_pg_own_team_flags_not_kills(self):
        # PG leverage=3.0 < KILL_THRESHOLD(3.5) → flag only
        r = evaluate_injury_impact("NBA", "PG", True, "home", "spreads", "home")
        assert r.flag is True
        assert r.kill is False
        assert r.signed_impact < 0
        assert r.leverage_pts == 3.0

    def test_nhl_goalie_own_team_kills(self):
        # NHL G leverage=3.5 == KILL_THRESHOLD → kill
        r = evaluate_injury_impact("NHL", "G", True, "home", "spreads", "home")
        assert r.kill is True
        assert r.signed_impact < 0

    def test_opponent_injury_helps(self):
        r = evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
        assert r.signed_impact > 0
        assert r.flag is False or r.signed_impact > 0  # positive = helps

    def test_non_starter_no_impact(self):
        r = evaluate_injury_impact("NBA", "PG", False, "home", "spreads", "home")
        assert r.leverage_pts == 0.0
        assert r.flag is False
        assert r.kill is False

    def test_unknown_position_no_impact(self):
        r = evaluate_injury_impact("NBA", "BENCHWARMER", True, "home", "spreads", "home")
        assert r.leverage_pts == 0.0
        assert r.kill is False

    def test_totals_market_multiplier(self):
        r = evaluate_injury_impact("NBA", "PG", True, "home", "totals", "home")
        # totals multiplier is -0.3 → signed_impact = 3.0 * -0.3 = -0.9
        assert r.signed_impact == pytest.approx(-0.9)
        assert r.kill is False  # -0.9 < 3.5 threshold

    def test_advisory_contains_severity(self):
        r = evaluate_injury_impact("NHL", "G", True, "home", "spreads", "home")
        assert "KILL" in r.advisory


class TestInjuryKillSwitch:
    def test_nhl_goalie_own_team_kills(self):
        # NHL G leverage=3.5 meets KILL_THRESHOLD
        killed, reason = injury_kill_switch("NHL", "G", True, "home", "spreads", "home")
        assert killed is True
        assert "KILL" in reason

    def test_nba_pg_own_team_does_not_kill(self):
        # PG leverage=3.0 < KILL_THRESHOLD — flags but kill_switch returns False
        killed, reason = injury_kill_switch("NBA", "PG", True, "home", "spreads", "home")
        assert killed is False

    def test_backup_position_no_kill(self):
        killed, reason = injury_kill_switch("NFL", "RB", True, "home", "spreads", "away")
        assert killed is False
        assert reason == ""

    def test_non_starter_no_kill(self):
        killed, reason = injury_kill_switch("NBA", "PG", False, "home", "spreads", "home")
        assert killed is False
        assert reason == ""


class TestSituationalScoreFromInjuries:
    def test_none_returns_zero(self):
        assert situational_score_from_injuries(None) == 0.0

    def test_empty_list_returns_zero(self):
        assert situational_score_from_injuries([]) == 0.0

    def test_opponent_injury_adds_points(self):
        # away QB out, betting home → positive signed_impact = 4.5 * 0.5 = 2.25
        r = evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
        score = situational_score_from_injuries([r])
        assert score > 0.0

    def test_own_team_injury_adds_no_points(self):
        # home QB out, betting home → negative signed_impact
        r = evaluate_injury_impact("NFL", "QB", True, "home", "spreads", "home")
        score = situational_score_from_injuries([r])
        assert score == 0.0

    def test_cap_at_15(self):
        # Create 10 reports all with max positive impact
        reports = [
            evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
            for _ in range(10)
        ]
        score = situational_score_from_injuries(reports)
        assert score <= 15.0


class TestSharpScoreWithInjuries:
    def test_injury_reports_none_same_as_before(self):
        # No injury_reports → same as old behaviour
        score_old = sharp_score_for_bet(0.08, efficiency_gap=12.0)
        score_new = sharp_score_for_bet(0.08, efficiency_gap=12.0, injury_reports=None)
        assert score_old == score_new

    def test_empty_injury_list_no_change(self):
        score_no_inj = sharp_score_for_bet(0.08, efficiency_gap=12.0)
        score_empty = sharp_score_for_bet(0.08, efficiency_gap=12.0, injury_reports=[])
        assert score_no_inj == score_empty

    def test_opponent_injury_boosts_score(self):
        r = evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
        score_base = sharp_score_for_bet(0.08, efficiency_gap=12.0)
        score_with = sharp_score_for_bet(0.08, efficiency_gap=12.0, injury_reports=[r])
        assert score_with > score_base
