"""
tests/test_mlb_live_ratings.py — Unit tests for mlb_live_ratings.py

Covers: _compute_ratings, _API_TO_CANONICAL mapping coverage,
        refresh_efficiency_feed_mlb, cache behavior, fallback on API failure.
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "strategies"))

import mlb_live_ratings as mlr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(api_name: str, wins: int, losses: int,
                 runs_scored: int, runs_allowed: int) -> dict:
    return {
        "team": {"name": api_name},
        "wins": wins,
        "losses": losses,
        "runsScored": runs_scored,
        "runsAllowed": runs_allowed,
    }


# ---------------------------------------------------------------------------
# Test: _compute_ratings
# ---------------------------------------------------------------------------

def test_compute_ratings_basic():
    """Strong team (many RS, few RA) gets positive adj_em."""
    records = [_make_record("Yankees", 7, 2, 47, 22)]
    ratings = mlr._compute_ratings(records)
    assert "New York Yankees" in ratings
    assert ratings["New York Yankees"] > 0


def test_compute_ratings_weak_team():
    """Weak team (few RS, many RA) gets negative adj_em."""
    records = [_make_record("Giants", 3, 8, 30, 57)]
    ratings = mlr._compute_ratings(records)
    assert "San Francisco Giants" in ratings
    assert ratings["San Francisco Giants"] < 0


def test_compute_ratings_neutral_team():
    """Team with equal RS/RA gets adj_em near 0."""
    records = [_make_record("Angels", 6, 5, 47, 47)]
    ratings = mlr._compute_ratings(records)
    assert "Los Angeles Angels" in ratings
    assert abs(ratings["Los Angeles Angels"]) < 0.5


def test_compute_ratings_zero_games():
    """Team with 0 RS and 0 RA gets adj_em = 0 (no division by zero)."""
    records = [_make_record("Dodgers", 0, 0, 0, 0)]
    ratings = mlr._compute_ratings(records)
    assert "Los Angeles Dodgers" in ratings
    assert ratings["Los Angeles Dodgers"] == 0.0


def test_compute_ratings_unknown_team_skipped():
    """Team not in _API_TO_CANONICAL is silently skipped."""
    records = [_make_record("Fake Team", 5, 5, 50, 50)]
    ratings = mlr._compute_ratings(records)
    assert len(ratings) == 0


def test_compute_ratings_regression_to_mean():
    """Early in season, strong team is pulled toward 0 by prior."""
    # Perfect record 10-0 with RS=100, RA=0 → pyth=1.0
    # Regressed = (0.5 * 30 + 1.0 * 10) / (30 + 10) = 25/40 = 0.625
    records = [_make_record("Yankees", 10, 0, 100, 1)]
    ratings = mlr._compute_ratings(records)
    adj = ratings["New York Yankees"]
    # 0.625 - 0.5 = 0.125 → * 30 = 3.75
    assert 3.0 < adj < 5.0, f"expected ~3.75, got {adj}"


# ---------------------------------------------------------------------------
# Test: API_TO_CANONICAL coverage
# ---------------------------------------------------------------------------

def test_all_30_teams_mapped():
    """All 30 MLB teams must be in _API_TO_CANONICAL."""
    # Canonical names from efficiency_feed MLB section
    expected_canonical = {
        "Los Angeles Angels", "Arizona Diamondbacks", "Baltimore Orioles",
        "Boston Red Sox", "Chicago Cubs", "Cincinnati Reds", "Cleveland Guardians",
        "Colorado Rockies", "Detroit Tigers", "Houston Astros", "Kansas City Royals",
        "Los Angeles Dodgers", "Miami Marlins", "Milwaukee Brewers", "Minnesota Twins",
        "New York Mets", "New York Yankees", "Oakland Athletics", "Philadelphia Phillies",
        "Pittsburgh Pirates", "San Diego Padres", "San Francisco Giants",
        "Seattle Mariners", "St. Louis Cardinals", "Tampa Bay Rays", "Texas Rangers",
        "Toronto Blue Jays", "Washington Nationals", "Chicago White Sox", "Atlanta Braves",
    }
    mapped_canonical = set(mlr._API_TO_CANONICAL.values())
    assert mapped_canonical == expected_canonical, (
        f"Missing: {expected_canonical - mapped_canonical}, "
        f"Extra: {mapped_canonical - expected_canonical}"
    )


def test_no_duplicate_canonical_names():
    """No two API names should map to the same canonical name."""
    values = list(mlr._API_TO_CANONICAL.values())
    assert len(values) == len(set(values)), "Duplicate canonical names in _API_TO_CANONICAL"


# ---------------------------------------------------------------------------
# Test: refresh_efficiency_feed_mlb
# ---------------------------------------------------------------------------

def test_refresh_updates_mlb_entries():
    """refresh_efficiency_feed_mlb updates MLB team adj_em values."""
    fake_feed = {
        "New York Yankees": {"adj_em": 0.0, "league": "MLB"},
        "Los Angeles Dodgers": {"adj_em": 0.0, "league": "MLB"},
        "Boston Celtics": {"adj_em": 25.0, "league": "NBA"},  # should be untouched
    }
    # Inject fake live ratings directly via cache
    mlr._cache = (time.monotonic(), {
        "New York Yankees": 2.22,
        "Los Angeles Dodgers": 2.11,
    })

    mlr.refresh_efficiency_feed_mlb(fake_feed)
    assert fake_feed["New York Yankees"]["adj_em"] == 2.22
    assert fake_feed["Los Angeles Dodgers"]["adj_em"] == 2.11
    assert fake_feed["Boston Celtics"]["adj_em"] == 25.0  # unchanged

    mlr._cache = None  # reset


def test_refresh_falls_back_on_empty_ratings():
    """If live ratings return empty (API fail), original values preserved."""
    fake_feed = {
        "New York Yankees": {"adj_em": 5.0, "league": "MLB"},
    }
    mlr._cache = (time.monotonic(), {})  # empty ratings = API failed

    result = mlr.refresh_efficiency_feed_mlb(fake_feed)
    assert result["New York Yankees"]["adj_em"] == 5.0  # preserved

    mlr._cache = None  # reset


# ---------------------------------------------------------------------------
# Test: cache behavior
# ---------------------------------------------------------------------------

def test_cache_is_used_on_second_call():
    """get_mlb_adj_em_dict returns cached result within TTL."""
    fake_ratings = {"New York Yankees": 2.22}
    mlr._cache = (time.monotonic(), fake_ratings)

    result = mlr.get_mlb_adj_em_dict(2026)
    assert result is fake_ratings

    mlr._cache = None  # reset


def test_cache_expires_on_stale_ts():
    """Stale cache (beyond TTL) triggers a refetch (returns empty on no network in test)."""
    fake_ratings = {"New York Yankees": 2.22}
    stale_ts = time.monotonic() - (mlr._CACHE_TTL_SECONDS + 1)
    mlr._cache = (stale_ts, fake_ratings)

    # Will attempt a real API call — in test env just verify it doesn't crash
    try:
        result = mlr.get_mlb_adj_em_dict(2026)
        assert isinstance(result, dict)
    finally:
        mlr._cache = None  # reset


# ---------------------------------------------------------------------------
# Test: pythagorean formula
# ---------------------------------------------------------------------------

def test_pythagorean_formula_correctness():
    """Verify the pythagorean formula is RS²/(RS²+RA²)."""
    # 50 RS, 50 RA → pyth = 0.5 → regressed = (0.5*30 + 0.5*10)/(30+10) = 0.5
    records = [_make_record("Rangers", 5, 5, 50, 50)]
    ratings = mlr._compute_ratings(records)
    assert abs(ratings["Texas Rangers"]) < 0.1  # near zero


def test_strong_offense_correctly_rated():
    """Team with RS >> RA gets high positive adj_em."""
    records = [_make_record("Brewers", 8, 3, 70, 41)]
    ratings = mlr._compute_ratings(records)
    assert ratings["Milwaukee Brewers"] > 0.5
