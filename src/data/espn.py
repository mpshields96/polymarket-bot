"""ESPN scoreboard feed — no auth, no API key required.

Polls the undocumented ESPN scoreboard API for live game state.
Used by sports_sniper to verify game phase before executing a bet.

WARNING: This API is undocumented and can change without notice.
If parsing breaks, check the raw JSON at:
  https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/scoreboard
"""
import json
import logging
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

_ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports"
_SPORT_PATHS = {
    "mlb": "baseball/mlb",
    "nba": "basketball/nba",
    "nhl": "hockey/nhl",
    "nfl": "football/nfl",
}
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; polybot/1.0)"}
_TIMEOUT = 8  # seconds


class ESPNFeed:
    """Fetches and parses live game state from ESPN scoreboard API."""

    @staticmethod
    def _parse_game(event: dict, sport: str) -> Optional[dict]:
        """Parse one ESPN event into a normalized game dict.

        Returns None for games that are not STATUS_IN_PROGRESS.
        """
        try:
            comp = event["competitions"][0]
            status = comp.get("status", {})
            status_name = status.get("type", {}).get("name", "")

            if status_name != "STATUS_IN_PROGRESS":
                return None

            competitors = comp["competitors"]
            home = next(c for c in competitors if c["homeAway"] == "home")
            away = next(c for c in competitors if c["homeAway"] == "away")

            home_abbr = home["team"]["abbreviation"].upper()
            away_abbr = away["team"]["abbreviation"].upper()
            home_score = int(home.get("score") or 0)
            away_score = int(away.get("score") or 0)
            period = int(status.get("period") or 0)
            clock = status.get("displayClock", "")

            lead = abs(home_score - away_score)
            if home_score > away_score:
                leading_team = home_abbr
            elif away_score > home_score:
                leading_team = away_abbr
            else:
                leading_team = None  # tied

            return {
                "sport": sport,
                "home": home_abbr,
                "away": away_abbr,
                "home_score": home_score,
                "away_score": away_score,
                "period": period,
                "clock": clock,
                "lead": lead,
                "leading_team": leading_team,
                "status": "in_progress",
            }
        except (KeyError, StopIteration, ValueError, TypeError) as e:
            logger.debug("[espn] Parse error: %s", e)
            return None

    @staticmethod
    def get_live_games(sport: str) -> list[dict]:
        """Fetch all in-progress games for the given sport.

        Args:
            sport: One of 'mlb', 'nba', 'nhl', 'nfl'

        Returns:
            List of normalized game dicts (only in-progress games).
        """
        path = _SPORT_PATHS.get(sport)
        if not path:
            raise ValueError(f"Unknown sport: {sport}")

        url = f"{_ESPN_BASE}/{path}/scoreboard"
        try:
            req = urllib.request.Request(url, headers=_HEADERS)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                data = json.load(resp)
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
            logger.warning("[espn] Failed to fetch %s scoreboard: %s", sport, e)
            return []

        games = []
        for event in data.get("events", []):
            game = ESPNFeed._parse_game(event, sport)
            if game:
                games.append(game)

        logger.debug("[espn] %s: %d in-progress games", sport, len(games))
        return games
