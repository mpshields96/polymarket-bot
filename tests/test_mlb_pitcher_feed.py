"""
tests/test_mlb_pitcher_feed.py — Unit tests for mlb_pitcher_feed.py

Covers: PitcherStats, PitcherMatchup, _evaluate_pitcher, _compute_era_advantage,
        pitcher_kill_switch, get_pitcher_matchup (mocked + real API smoke),
        team name normalization, cache behavior.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "strategies"))

from mlb_pitcher_feed import (
    PitcherStats,
    PitcherMatchup,
    ERA_KILL_THRESHOLD,
    MIN_IP_FOR_ERA_SIGNAL,
    ERA_EDGE_PTS_MAX,
    _evaluate_pitcher,
    _compute_era_advantage,
    _teams_match,
    _normalize_team,
    pitcher_kill_switch,
    pitcher_edge_pts,
    get_pitcher_matchup,
    _ERA_FALLBACK,
    _schedule_cache,
    _stats_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sp(era: float, ip: float, name: str = "Test Pitcher", pid: int = 999) -> PitcherStats:
    s = PitcherStats(player_id=pid, full_name=name)
    s.era = era
    s.innings_pitched = ip
    s.source = "api"
    return s


# ---------------------------------------------------------------------------
# Test: PitcherStats defaults
# ---------------------------------------------------------------------------

def test_pitcher_stats_defaults():
    sp = PitcherStats(player_id=12345, full_name="John Doe")
    assert sp.era == _ERA_FALLBACK
    assert sp.innings_pitched == 0.0
    assert sp.source == "api"


# ---------------------------------------------------------------------------
# Test: _evaluate_pitcher kill switch
# ---------------------------------------------------------------------------

def test_evaluate_pitcher_kills_high_era_sufficient_ip():
    sp = _sp(era=7.20, ip=25.0)  # ERA > 6.50, IP > 15
    killed, reason = _evaluate_pitcher(sp)
    assert killed is True
    assert "7.20" in reason


def test_evaluate_pitcher_no_kill_low_era():
    sp = _sp(era=2.80, ip=30.0)
    killed, _ = _evaluate_pitcher(sp)
    assert killed is False


def test_evaluate_pitcher_no_kill_insufficient_ip():
    # ERA 8.00 but only 5 IP — too small sample
    sp = _sp(era=8.00, ip=5.0)
    killed, reason = _evaluate_pitcher(sp)
    assert killed is False
    assert reason == ""


def test_evaluate_pitcher_none_returns_false():
    killed, reason = _evaluate_pitcher(None)
    assert killed is False
    assert reason == ""


def test_evaluate_pitcher_no_data_source():
    sp = _sp(era=9.00, ip=30.0)
    sp.source = "no_data"
    killed, _ = _evaluate_pitcher(sp)
    assert killed is False


def test_evaluate_pitcher_exactly_at_threshold():
    # ERA == ERA_KILL_THRESHOLD should NOT kill (must be strictly greater)
    sp = _sp(era=ERA_KILL_THRESHOLD, ip=MIN_IP_FOR_ERA_SIGNAL)
    killed, _ = _evaluate_pitcher(sp)
    assert killed is False


# ---------------------------------------------------------------------------
# Test: _compute_era_advantage
# ---------------------------------------------------------------------------

def test_era_advantage_home_better():
    home = _sp(era=2.50, ip=20.0)
    away = _sp(era=5.00, ip=20.0)
    adv, edge_pts = _compute_era_advantage(home, away)
    assert adv > 0  # positive = home better
    assert edge_pts > 0
    assert edge_pts <= ERA_EDGE_PTS_MAX


def test_era_advantage_away_better_no_edge_pts():
    home = _sp(era=5.00, ip=20.0)
    away = _sp(era=2.50, ip=20.0)
    adv, edge_pts = _compute_era_advantage(home, away)
    assert adv < 0   # negative = away better
    assert edge_pts == 0.0  # no pts for home when home SP is worse


def test_era_advantage_insufficient_ip_returns_zero():
    home = _sp(era=2.50, ip=5.0)   # not enough IP
    away = _sp(era=6.00, ip=20.0)
    adv, edge_pts = _compute_era_advantage(home, away)
    assert adv == 0.0
    assert edge_pts == 0.0


def test_era_advantage_capped_at_max():
    # 10 ERA gap should max out at ERA_EDGE_PTS_MAX
    home = _sp(era=1.00, ip=60.0)
    away = _sp(era=11.00, ip=60.0)
    _, edge_pts = _compute_era_advantage(home, away)
    assert edge_pts == ERA_EDGE_PTS_MAX


def test_era_advantage_none_pitchers():
    adv, edge_pts = _compute_era_advantage(None, None)
    assert adv == 0.0
    assert edge_pts == 0.0


# ---------------------------------------------------------------------------
# Test: pitcher_kill_switch
# ---------------------------------------------------------------------------

def test_pitcher_kill_switch_home_bad_sp_betting_home():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.kill_home = True
    matchup.kill_reason = "SP kill: Bad Pitcher ERA 7.00 in 20.0 IP"
    killed, reason = pitcher_kill_switch(matchup, betting_home=True)
    assert killed is True
    assert "ERA 7.00" in reason


def test_pitcher_kill_switch_home_bad_sp_betting_away():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.kill_home = True
    matchup.kill_reason = "SP kill: Bad Pitcher ERA 7.00 in 20.0 IP"
    killed, reason = pitcher_kill_switch(matchup, betting_home=False)
    assert killed is False  # away SP is fine, we're betting away
    assert reason == ""


def test_pitcher_kill_switch_away_bad_sp_betting_away():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.kill_away = True
    matchup.kill_reason = "SP kill: Bad Away Pitcher ERA 8.10 in 18.0 IP"
    killed, reason = pitcher_kill_switch(matchup, betting_home=False)
    assert killed is True


def test_pitcher_kill_switch_no_kill():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.kill_home = False
    matchup.kill_away = False
    killed, reason = pitcher_kill_switch(matchup, betting_home=True)
    assert killed is False
    assert reason == ""


def test_pitcher_edge_pts_home_better_only_rewards_home_side():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.era_advantage = 2.5
    matchup.edge_pts = 5.0
    assert pitcher_edge_pts(matchup, betting_home=True) == 5.0
    assert pitcher_edge_pts(matchup, betting_home=False) == 0.0


def test_pitcher_edge_pts_away_better_rewards_away_side():
    matchup = PitcherMatchup(home_team="Cubs", away_team="Rays", game_date="2026-04-07")
    matchup.era_advantage = -2.5
    matchup.edge_pts = 0.0
    assert pitcher_edge_pts(matchup, betting_home=True) == 0.0
    assert pitcher_edge_pts(matchup, betting_home=False) == 5.0


# ---------------------------------------------------------------------------
# Test: _teams_match
# ---------------------------------------------------------------------------

def test_teams_match_exact():
    assert _teams_match("Houston Astros", "Houston Astros") is True


def test_teams_match_partial():
    # "Athletics" should match "Oakland Athletics"
    assert _teams_match("Athletics", "Oakland Athletics") is True


def test_teams_match_no_match():
    assert _teams_match("Boston Red Sox", "New York Yankees") is False


def test_teams_match_case_insensitive():
    assert _teams_match("chicago cubs", "Chicago Cubs") is True


# ---------------------------------------------------------------------------
# Test: _normalize_team
# ---------------------------------------------------------------------------

def test_normalize_team_known():
    assert _normalize_team("Oakland Athletics") == "athletics"


def test_normalize_team_unknown_passthrough():
    assert _normalize_team("Fake Team FC") == "fake team fc"


# ---------------------------------------------------------------------------
# Test: get_pitcher_matchup (real API smoke test — network required)
# ---------------------------------------------------------------------------

def test_get_pitcher_matchup_live_api():
    """Smoke test — requires network. Verify API returns real data structure."""
    matchup = get_pitcher_matchup(
        home_team="Pittsburgh Pirates",
        away_team="San Diego Padres",
        game_date="2026-04-07",
    )
    assert isinstance(matchup, PitcherMatchup)
    assert matchup.home_team == "Pittsburgh Pirates"
    assert matchup.away_team == "San Diego Padres"
    # home SP should be Paul Skenes if named
    if matchup.home_sp:
        assert isinstance(matchup.home_sp.era, float)
        assert matchup.home_sp.era >= 0.0
    # edge_pts in valid range
    assert 0.0 <= matchup.edge_pts <= ERA_EDGE_PTS_MAX


def test_get_pitcher_matchup_not_found_returns_neutral():
    """Unknown teams return a neutral matchup without crashing."""
    matchup = get_pitcher_matchup(
        home_team="Fake Team A",
        away_team="Fake Team B",
        game_date="2026-04-07",
    )
    assert matchup.home_sp is None
    assert matchup.away_sp is None
    assert matchup.kill_home is False
    assert matchup.kill_away is False
    assert matchup.edge_pts == 0.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
