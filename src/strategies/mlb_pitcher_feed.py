"""
src/strategies/mlb_pitcher_feed.py — MLB Starting Pitcher Signal Feed
======================================================================
Provides 2026 starting pitcher data for each scheduled MLB game.

Source: MLB Stats API (statsapi.mlb.com) — free, no auth required.
Cache: 6-hour TTL (starters confirmed by ~10 AM ET day-of-game).

Primary function:
  get_pitcher_matchup(home_team, away_team, game_date) -> PitcherMatchup

Signal used in sports_game.py:
  - pitcher_kill_switch(): fires if a clearly inferior SP is starting
    (ERA > 6.0 with < 4 IP average) against an elite lineup
  - pitcher_edge_pts(): 0-10 bonus pts toward sharp score when our
    team's SP has significantly better ERA than opponent

Wire-in: call get_pitcher_matchup() in sports_game generate_signal()
  after efficiency_gap is computed, before sharp_score_for_bet().

Zero external dependencies. All stdlib.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
    "?sportId=1&date={date}&hydrate=probablePitcher"
)
_PLAYER_STATS_URL = (
    "https://statsapi.mlb.com/api/v1/people/{pid}/stats"
    "?stats=season&season={season}&group=pitching"
)

_CACHE_TTL_SECONDS: int = 6 * 3600   # 6 hours — starters finalized by 10 AM ET
_REQUEST_TIMEOUT: int = 8             # seconds per HTTP call
_ERA_FALLBACK: float = 4.50           # league-average ERA when data unavailable
_IP_FALLBACK: float = 5.5             # typical starter IP/game when data unavailable

# ERA thresholds for kill switch
ERA_KILL_THRESHOLD: float = 6.50      # SP with ERA > 6.50 in 3+ starts = high-risk
MIN_IP_FOR_ERA_SIGNAL: float = 15.0   # need ≥ 15 IP before ERA is meaningful

# ERA advantage for edge pts (0-10 scale)
ERA_EDGE_PTS_MAX: float = 10.0
ERA_EDGE_SCALE: float = 2.0           # 2 pts per 1.0 ERA advantage (max 5-pt gap → 10 pts)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PitcherStats:
    """2026 season stats for one starting pitcher."""
    player_id: int
    full_name: str
    era: float = _ERA_FALLBACK
    innings_pitched: float = 0.0
    games_started: int = 0
    strikeouts: int = 0
    whip: float = 1.30
    source: str = "api"  # "api", "fallback", "no_data"


@dataclass
class PitcherMatchup:
    """
    Pitcher matchup for a single game.

    home_sp / away_sp: may be None if not yet announced.
    era_advantage: positive = home SP has better (lower) ERA.
    """
    home_team: str
    away_team: str
    game_date: str
    home_sp: Optional[PitcherStats] = None
    away_sp: Optional[PitcherStats] = None
    era_advantage: float = 0.0      # home_sp.era - away_sp.era (negative = home favored)
    edge_pts: float = 0.0           # 0-10 pts toward sharp score
    kill_home: bool = False         # True if home SP is flagged kill
    kill_away: bool = False         # True if away SP is flagged kill
    kill_reason: str = ""


# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_schedule_cache: dict[str, tuple[float, list[dict]]] = {}  # date -> (ts, games)
_stats_cache: dict[int, tuple[float, PitcherStats]] = {}    # pid -> (ts, stats)


# ---------------------------------------------------------------------------
# HTTP helpers (stdlib only)
# ---------------------------------------------------------------------------

def _fetch_json(url: str) -> Optional[dict]:
    """GET url, return parsed JSON or None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "polybot/1.0"})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _now_ts() -> float:
    return time.monotonic()


# ---------------------------------------------------------------------------
# Schedule loader
# ---------------------------------------------------------------------------

def _get_schedule(date_str: str) -> list[dict]:
    """
    Return list of game dicts from MLB Stats API for the given date (YYYY-MM-DD).
    Cached for _CACHE_TTL_SECONDS.

    Each game dict has structure:
      { "teams": { "home": { "team": {"name": ...}, "probablePitcher": {"id": ..., "fullName": ...} },
                   "away": { ... } },
        "gameDate": "2026-04-07T..." }
    """
    now = _now_ts()
    if date_str in _schedule_cache:
        ts, games = _schedule_cache[date_str]
        if now - ts < _CACHE_TTL_SECONDS:
            return games

    url = _SCHEDULE_URL.format(date=date_str)
    data = _fetch_json(url)
    if not data:
        return []

    games = []
    for date_entry in data.get("dates", []):
        games.extend(date_entry.get("games", []))

    _schedule_cache[date_str] = (now, games)
    return games


# ---------------------------------------------------------------------------
# Pitcher stats loader
# ---------------------------------------------------------------------------

def _get_pitcher_stats(player_id: int, full_name: str, season: int = 2026) -> PitcherStats:
    """
    Fetch 2026 pitching stats for a player ID.
    Falls back to _ERA_FALLBACK if no stats yet this season.
    Cached for _CACHE_TTL_SECONDS.
    """
    now = _now_ts()
    if player_id in _stats_cache:
        ts, stats = _stats_cache[player_id]
        if now - ts < _CACHE_TTL_SECONDS:
            return stats

    url = _PLAYER_STATS_URL.format(pid=player_id, season=season)
    data = _fetch_json(url)

    stats_obj = PitcherStats(player_id=player_id, full_name=full_name)

    if data:
        for stat_group in data.get("stats", []):
            splits = stat_group.get("splits", [])
            if splits:
                s = splits[0].get("stat", {})
                try:
                    ip_str = s.get("inningsPitched", "0.0")
                    # IP stored as "9.2" (9 innings + 2 outs = 9.667 real innings)
                    ip_parts = str(ip_str).split(".")
                    ip_real = int(ip_parts[0]) + int(ip_parts[1] if len(ip_parts) > 1 else 0) / 3.0
                    stats_obj.innings_pitched = round(ip_real, 2)
                except (ValueError, IndexError):
                    pass

                era_raw = s.get("era", None)
                if era_raw is not None:
                    try:
                        stats_obj.era = float(era_raw)
                        stats_obj.source = "api"
                    except ValueError:
                        stats_obj.era = _ERA_FALLBACK
                        stats_obj.source = "fallback"
                else:
                    stats_obj.era = _ERA_FALLBACK
                    stats_obj.source = "no_data"

                try:
                    stats_obj.games_started = int(s.get("gamesStarted", 0))
                    stats_obj.strikeouts = int(s.get("strikeOuts", 0))
                    whip_raw = s.get("whip", None)
                    if whip_raw is not None:
                        stats_obj.whip = float(whip_raw)
                except (ValueError, TypeError):
                    pass
                break

    _stats_cache[player_id] = (now, stats_obj)
    return stats_obj


# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------

# Map Odds API full team names → MLB Stats API team names
# MLB Stats API uses official franchise names; Odds API uses common names
_ODDS_TO_MLB_STATS: dict[str, str] = {
    "Los Angeles Dodgers": "Los Angeles Dodgers",
    "New York Yankees": "New York Yankees",
    "Boston Red Sox": "Boston Red Sox",
    "Chicago Cubs": "Chicago Cubs",
    "Chicago White Sox": "Chicago White Sox",
    "Houston Astros": "Houston Astros",
    "San Diego Padres": "San Diego Padres",
    "Atlanta Braves": "Atlanta Braves",
    "Cleveland Guardians": "Cleveland Guardians",
    "Toronto Blue Jays": "Toronto Blue Jays",
    "Milwaukee Brewers": "Milwaukee Brewers",
    "Arizona Diamondbacks": "Arizona Diamondbacks",
    "New York Mets": "New York Mets",
    "Seattle Mariners": "Seattle Mariners",
    "Pittsburgh Pirates": "Pittsburgh Pirates",
    "Washington Nationals": "Washington Nationals",
    "St. Louis Cardinals": "St. Louis Cardinals",
    "Cincinnati Reds": "Cincinnati Reds",
    "Miami Marlins": "Miami Marlins",
    "Detroit Tigers": "Detroit Tigers",
    "Minnesota Twins": "Minnesota Twins",
    "Kansas City Royals": "Kansas City Royals",
    "Texas Rangers": "Texas Rangers",
    "Tampa Bay Rays": "Tampa Bay Rays",
    "Baltimore Orioles": "Baltimore Orioles",
    "Oakland Athletics": "Athletics",         # relocated
    "Los Angeles Angels": "Los Angeles Angels",
    "San Francisco Giants": "San Francisco Giants",
    "Colorado Rockies": "Colorado Rockies",
    "Philadelphia Phillies": "Philadelphia Phillies",
}


def _normalize_team(name: str) -> str:
    """Normalize team name for matching against MLB Stats API response."""
    return _ODDS_TO_MLB_STATS.get(name, name).lower().strip()


def _teams_match(api_name: str, lookup_name: str) -> bool:
    """Fuzzy team name match — handles 'Athletics' vs 'Oakland Athletics' etc."""
    a = api_name.lower().strip()
    b = _normalize_team(lookup_name)
    return a == b or a in b or b in a


# ---------------------------------------------------------------------------
# Kill switch + edge pts
# ---------------------------------------------------------------------------

def _evaluate_pitcher(sp: Optional[PitcherStats]) -> tuple[bool, str]:
    """
    Return (should_kill, reason) for a starting pitcher.

    Kills when:
    - ERA > ERA_KILL_THRESHOLD AND IP >= MIN_IP_FOR_ERA_SIGNAL
      (avoid killing on tiny sample: ERA 9.0 in 1 start = noise)
    """
    if sp is None:
        return False, ""
    if sp.source == "no_data":
        return False, ""
    if sp.innings_pitched >= MIN_IP_FOR_ERA_SIGNAL and sp.era > ERA_KILL_THRESHOLD:
        return True, f"SP kill: {sp.full_name} ERA {sp.era:.2f} in {sp.innings_pitched:.1f} IP"
    return False, ""


def _compute_era_advantage(home_sp: Optional[PitcherStats], away_sp: Optional[PitcherStats]) -> tuple[float, float]:
    """
    ERA advantage (home perspective) and edge pts.

    era_advantage = away_sp.era - home_sp.era
      positive → home SP better (lower ERA)
      negative → away SP better

    edge_pts = min(ERA_EDGE_PTS_MAX, ERA_EDGE_SCALE × max(0, era_advantage))
      Only award points when home SP is clearly better.
    """
    home_era = home_sp.era if home_sp else _ERA_FALLBACK
    away_era = away_sp.era if away_sp else _ERA_FALLBACK

    # Only use ERA signal when we have meaningful sample size
    home_ip = home_sp.innings_pitched if home_sp else 0.0
    away_ip = away_sp.innings_pitched if away_sp else 0.0

    if home_ip < MIN_IP_FOR_ERA_SIGNAL or away_ip < MIN_IP_FOR_ERA_SIGNAL:
        return 0.0, 0.0

    era_adv = away_era - home_era  # positive = home better
    edge = min(ERA_EDGE_PTS_MAX, ERA_EDGE_SCALE * max(0.0, era_adv))
    return round(era_adv, 3), round(edge, 1)


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def get_pitcher_matchup(
    home_team: str,
    away_team: str,
    game_date: Optional[str] = None,
) -> PitcherMatchup:
    """
    Fetch starting pitcher matchup for a given game.

    Args:
        home_team:  Home team name (Odds API format, e.g. "Houston Astros")
        away_team:  Away team name
        game_date:  ISO date string YYYY-MM-DD (defaults to today UTC)

    Returns:
        PitcherMatchup with home_sp, away_sp, era_advantage, edge_pts,
        kill_home, kill_away, kill_reason.
        Falls back gracefully — returns neutral matchup on any API failure.
    """
    if game_date is None:
        game_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    matchup = PitcherMatchup(home_team=home_team, away_team=away_team, game_date=game_date)

    games = _get_schedule(game_date)
    target_game = None
    for g in games:
        api_home = g.get("teams", {}).get("home", {}).get("team", {}).get("name", "")
        api_away = g.get("teams", {}).get("away", {}).get("team", {}).get("name", "")
        if _teams_match(api_home, home_team) and _teams_match(api_away, away_team):
            target_game = g
            break

    if not target_game:
        return matchup  # no game found — neutral

    teams = target_game.get("teams", {})

    for side, attr in [("home", "home_sp"), ("away", "away_sp")]:
        pitcher_data = teams.get(side, {}).get("probablePitcher", {})
        pid = pitcher_data.get("id")
        name = pitcher_data.get("fullName", "TBD")
        if pid:
            setattr(matchup, attr, _get_pitcher_stats(int(pid), name))

    # Kill switches
    kill_home, reason_home = _evaluate_pitcher(matchup.home_sp)
    kill_away, reason_away = _evaluate_pitcher(matchup.away_sp)
    matchup.kill_home = kill_home
    matchup.kill_away = kill_away
    matchup.kill_reason = reason_home or reason_away

    # ERA advantage (home perspective)
    matchup.era_advantage, matchup.edge_pts = _compute_era_advantage(matchup.home_sp, matchup.away_sp)

    return matchup


def pitcher_kill_switch(matchup: PitcherMatchup, betting_home: bool) -> tuple[bool, str]:
    """
    Return (should_kill, reason) for a specific bet direction.

    betting_home=True → we're betting on the home team → kill if home SP is bad.
    betting_home=False → we're betting on the away team → kill if away SP is bad.
    """
    if betting_home and matchup.kill_home:
        return True, matchup.kill_reason
    if not betting_home and matchup.kill_away:
        return True, matchup.kill_reason
    return False, ""


def pitcher_edge_pts(matchup: PitcherMatchup, betting_home: bool) -> float:
    """
    Return pitcher edge points for the side we are actually betting.

    matchup.edge_pts is stored from the home-team perspective. Convert that
    into the selected side so away-team bets can receive the same ERA bonus.
    """
    if betting_home:
        return round(max(0.0, matchup.edge_pts), 1)
    if matchup.era_advantage >= 0.0:
        return 0.0
    return round(min(ERA_EDGE_PTS_MAX, ERA_EDGE_SCALE * abs(matchup.era_advantage)), 1)
