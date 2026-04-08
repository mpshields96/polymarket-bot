"""
src/strategies/mlb_live_ratings.py — 2026 MLB Team Quality Ratings
===================================================================
Fetches live 2026 MLB standings from the MLB Stats API and computes
regressed pythagorean win% for each team.

Used by efficiency_feed.py to replace stale 2024 ERA data with current
2026 run-differential-based team quality ratings.

Primary function:
    get_mlb_adj_em_dict() -> dict[str, float]

Returns adj_em values in the same scale as efficiency_feed.py:
    positive = strong team, negative = weak team
    Regressed toward 0 (neutral) early in season when sample is small.

Update cadence: call weekly. Values stabilize by June (60+ games).

Zero external dependencies. Stdlib only.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_STANDINGS_URL = (
    "https://statsapi.mlb.com/api/v1/standings"
    "?leagueId=103,104&season={season}&standingsTypes=regularSeason"
)
_REQUEST_TIMEOUT: int = 8
_CACHE_TTL_SECONDS: int = 6 * 3600  # 6 hours — enough for daily use

# Regression prior: treat each team as having 30 "ghost games" at .500 before
# the season. At 10 real games: 25% weight on observed; at 60 games: 67% weight.
_PRIOR_GAMES: int = 30

# Scale factor for adj_em: 1 point of pythagorean deviation from .500 → this many adj_em points.
# Set to 30 to keep MLB on a similar scale to other sports in get_efficiency_gap().
_ADJ_EM_SCALE: float = 30.0

# Map from MLB Stats API team short names → efficiency_feed.py canonical names.
# The API returns franchise short names ("Yankees", "Dodgers"), not full names.
_API_TO_CANONICAL: dict[str, str] = {
    "Angels":       "Los Angeles Angels",
    "D-backs":      "Arizona Diamondbacks",
    "Orioles":      "Baltimore Orioles",
    "Red Sox":      "Boston Red Sox",
    "Cubs":         "Chicago Cubs",
    "Reds":         "Cincinnati Reds",
    "Guardians":    "Cleveland Guardians",
    "Rockies":      "Colorado Rockies",
    "Tigers":       "Detroit Tigers",
    "Astros":       "Houston Astros",
    "Royals":       "Kansas City Royals",
    "Dodgers":      "Los Angeles Dodgers",
    "Marlins":      "Miami Marlins",
    "Brewers":      "Milwaukee Brewers",
    "Twins":        "Minnesota Twins",
    "Mets":         "New York Mets",
    "Yankees":      "New York Yankees",
    "Athletics":    "Oakland Athletics",
    "Phillies":     "Philadelphia Phillies",
    "Pirates":      "Pittsburgh Pirates",
    "Padres":       "San Diego Padres",
    "Giants":       "San Francisco Giants",
    "Mariners":     "Seattle Mariners",
    "Cardinals":    "St. Louis Cardinals",
    "Rays":         "Tampa Bay Rays",
    "Rangers":      "Texas Rangers",
    "Blue Jays":    "Toronto Blue Jays",
    "Nationals":    "Washington Nationals",
    "White Sox":    "Chicago White Sox",
    "Braves":       "Atlanta Braves",
}


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: Optional[tuple[float, dict[str, float]]] = None   # (ts, ratings)


def _now_ts() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_standings(season: int) -> list[dict]:
    """Fetch raw team record dicts from MLB Stats API. Returns [] on failure."""
    url = _STANDINGS_URL.format(season=season)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "polybot/1.0"})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return []

    records = []
    for division_rec in data.get("records", []):
        records.extend(division_rec.get("teamRecords", []))
    return records


def _compute_ratings(team_records: list[dict]) -> dict[str, float]:
    """
    Convert raw team records to adj_em dict keyed by canonical name.

    Formula:
        pyth = RS² / (RS² + RA²)                      # pythagorean win%
        regressed = (0.5 * PRIOR + pyth * n) / (PRIOR + n)
        adj_em = (regressed - 0.5) * ADJ_EM_SCALE
    """
    ratings: dict[str, float] = {}

    for tr in team_records:
        api_name = tr.get("team", {}).get("name", "")
        canonical = _API_TO_CANONICAL.get(api_name)
        if not canonical:
            continue

        w = tr.get("wins", 0)
        l = tr.get("losses", 0)
        n = w + l
        rs = tr.get("runsScored", 0)
        ra = tr.get("runsAllowed", 0)

        if rs + ra > 0:
            pyth = rs * rs / (rs * rs + ra * ra)
        else:
            pyth = 0.5

        # Bayesian shrinkage: regress toward .500 with prior of _PRIOR_GAMES
        regressed = (0.5 * _PRIOR_GAMES + pyth * n) / (_PRIOR_GAMES + n)
        adj_em = (regressed - 0.5) * _ADJ_EM_SCALE
        ratings[canonical] = round(adj_em, 2)

    return ratings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_mlb_adj_em_dict(season: Optional[int] = None) -> dict[str, float]:
    """
    Return adj_em ratings for all 30 MLB teams for the given season.

    Cached for 6 hours. Returns empty dict on API failure (callers fall back
    to static efficiency_feed values).

    Args:
        season: MLB season year. Defaults to current UTC year.

    Returns:
        dict mapping canonical team name → adj_em float
        e.g. {"New York Yankees": 2.22, "San Francisco Giants": -2.28, ...}

    >>> ratings = get_mlb_adj_em_dict(2026)
    >>> isinstance(ratings, dict)
    True
    >>> len(ratings) > 0
    True
    """
    global _cache

    if season is None:
        season = datetime.now(timezone.utc).year

    now = _now_ts()
    if _cache is not None:
        ts, cached_ratings = _cache
        if now - ts < _CACHE_TTL_SECONDS:
            return cached_ratings

    records = _fetch_standings(season)
    if not records:
        return _cache[1] if _cache is not None else {}

    ratings = _compute_ratings(records)
    _cache = (now, ratings)
    return ratings


def refresh_efficiency_feed_mlb(efficiency_data: dict) -> dict:
    """
    Update the MLB section of an efficiency_feed data dict in-place.

    Called at bot startup to replace stale static MLB ratings with live 2026 values.
    Falls back gracefully — if API fails, existing static values are preserved.

    Args:
        efficiency_data: the _TEAM_EFFICIENCY dict from efficiency_feed.py

    Returns:
        The same dict, with MLB entries updated (others untouched).

    Example:
        from mlb_live_ratings import refresh_efficiency_feed_mlb
        from efficiency_feed import _TEAM_EFFICIENCY
        refresh_efficiency_feed_mlb(_TEAM_EFFICIENCY)
    """
    live = get_mlb_adj_em_dict()
    if not live:
        return efficiency_data  # API failed — preserve existing values

    updated = 0
    for team_name, adj_em in live.items():
        if team_name in efficiency_data:
            efficiency_data[team_name]["adj_em"] = adj_em
            updated += 1

    return efficiency_data


if __name__ == "__main__":
    import sys

    season_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    ratings = get_mlb_adj_em_dict(season_arg)
    if not ratings:
        print("ERROR: Could not fetch 2026 MLB standings.")
        sys.exit(1)

    print(f"MLB adj_em ratings ({len(ratings)} teams):")
    for name, adj_em in sorted(ratings.items(), key=lambda x: -x[1]):
        bar = "+" * int(abs(adj_em)) if adj_em > 0 else "-" * int(abs(adj_em))
        print(f"  {adj_em:+6.2f}  {bar:20s}  {name}")
