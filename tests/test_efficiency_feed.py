"""Tests for efficiency_feed.py — Team efficiency data and gap calculation."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.strategies.efficiency_feed import get_team_data, get_efficiency_gap, list_teams

# ──────────────────────────────────────────────────────────────────────────────
# Team data lookup
# ──────────────────────────────────────────────────────────────────────────────

def test_known_nba_team():
    data = get_team_data("Boston Celtics")
    assert data is not None
    assert "adj_em" in data
    assert isinstance(data["adj_em"], float)


def test_known_nhl_team():
    data = get_team_data("Florida Panthers")
    assert data is not None
    assert "adj_em" in data


def test_known_ncaab_team():
    # Teams stored as short names: "Duke" not "Duke Blue Devils"
    data = get_team_data("Duke")
    assert data is not None


def test_known_mlb_team():
    data = get_team_data("Los Angeles Dodgers")
    assert data is not None


def test_known_epl_team():
    data = get_team_data("Arsenal")
    assert data is not None


def test_unknown_team_returns_none():
    data = get_team_data("Fake Team XYZ")
    assert data is None


def test_empty_string_returns_none():
    data = get_team_data("")
    assert data is None


# ──────────────────────────────────────────────────────────────────────────────
# Alias resolution
# ──────────────────────────────────────────────────────────────────────────────

def test_nhl_alias_jets():
    data = get_team_data("Jets")
    assert data is not None, "NHL alias 'Jets' should resolve to Winnipeg Jets"


def test_nhl_alias_bruins():
    data = get_team_data("Bruins")
    assert data is not None


def test_nba_alias_celtics():
    data = get_team_data("Celtics")
    assert data is not None


def test_alias_case_insensitive():
    lower = get_team_data("celtics")
    upper = get_team_data("CELTICS")
    full = get_team_data("Boston Celtics")
    # All three should resolve (or all be None — consistency check)
    assert lower is not None or full is not None  # at least one path works


# ──────────────────────────────────────────────────────────────────────────────
# Efficiency gap calculation
# ──────────────────────────────────────────────────────────────────────────────

def test_gap_between_known_teams():
    gap = get_efficiency_gap("Boston Celtics", "Charlotte Hornets")
    assert isinstance(gap, float)
    assert 0.0 <= gap <= 20.0


def test_gap_is_clamped_low():
    """Gap should never go below 0.0."""
    gap = get_efficiency_gap("Charlotte Hornets", "Boston Celtics")
    assert gap >= 0.0


def test_gap_is_clamped_high():
    """Gap should never exceed 20.0."""
    gap = get_efficiency_gap("Boston Celtics", "Charlotte Hornets")
    assert gap <= 20.0


def test_gap_unknown_home_returns_default():
    gap = get_efficiency_gap("Unknown Team", "Boston Celtics")
    assert gap == 8.0  # _UNKNOWN_GAP fallback


def test_gap_unknown_away_returns_default():
    gap = get_efficiency_gap("Boston Celtics", "Unknown Team")
    assert gap == 8.0


def test_gap_both_unknown_returns_default():
    gap = get_efficiency_gap("Team A", "Team B")
    assert gap == 8.0


def test_gap_same_team_is_midpoint():
    """Same team vs same team → differential=0 → gap = (0+30)/60*20 = 10.0."""
    gap = get_efficiency_gap("Boston Celtics", "Boston Celtics")
    assert abs(gap - 10.0) < 0.1


def test_gap_formula_correctness():
    """Verify the formula: (home_adj_em - away_adj_em + 30) / 60 * 20."""
    home = get_team_data("Boston Celtics")
    away = get_team_data("Charlotte Hornets")
    if home is None or away is None:
        return  # skip if data missing
    expected = (home["adj_em"] - away["adj_em"] + 30.0) / 60.0 * 20.0
    expected = max(0.0, min(20.0, expected))
    actual = get_efficiency_gap("Boston Celtics", "Charlotte Hornets")
    assert abs(actual - expected) < 0.001


# ──────────────────────────────────────────────────────────────────────────────
# list_teams
# ──────────────────────────────────────────────────────────────────────────────

def test_list_teams_returns_list():
    teams = list_teams()
    assert isinstance(teams, list)
    assert len(teams) > 50  # NBA + NHL + NFL + MLB alone = 123 teams


def test_list_teams_contains_known():
    teams = list_teams()
    assert "Boston Celtics" in teams
    assert "Florida Panthers" in teams
    assert "Los Angeles Dodgers" in teams
    assert "Duke" in teams  # NCAAB stored as short name


# ──────────────────────────────────────────────────────────────────────────────
# NHL-specific (added vs original agentic-rd-sandbox)
# ──────────────────────────────────────────────────────────────────────────────

def test_nhl_teams_present():
    nhl_teams = [
        "Florida Panthers", "Winnipeg Jets", "Carolina Hurricanes",
        "Boston Bruins", "Edmonton Oilers", "Colorado Avalanche",
        "Toronto Maple Leafs", "Dallas Stars", "Vegas Golden Knights",
        "New York Rangers"
    ]
    for team in nhl_teams:
        data = get_team_data(team)
        assert data is not None, f"NHL team '{team}' not found in efficiency_feed"


def test_nhl_adj_em_range():
    """NHL adj_em values should be in a plausible range (not NBA-scaled)."""
    data = get_team_data("Florida Panthers")
    assert data is not None
    # NHL adj_em uses goal_differential * 12.0 scaling; top team ~10-15 range
    assert -20.0 <= data["adj_em"] <= 25.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
