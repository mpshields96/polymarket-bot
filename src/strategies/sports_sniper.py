"""Sports game sniper strategy — FLB-based near-certain bet capture.

Monitors Kalshi KXNBAGAME / KXNHLGAME / KXMLBGAME markets. When:
  - A game is in a late period AND
  - The leading team has a statistically commanding lead AND
  - The Kalshi market price is 90–95c for the leading team

...we buy YES. This is the same FLB mechanism as the crypto 15M sniper.
CCA REQ-56 confirms FLB applies structurally to live sports game markets.

Late-game thresholds (conservative — calibrate with DB data after 30+ bets):
  MLB: inning 7+, lead 5+ runs (comeback rate ~1.5%)
  NBA: period 4 (Q4), lead 15+ points (comeback rate ~2%)
  NHL: period 3, lead 3+ goals (comeback rate ~1%)

Floor: 90c  Ceiling: 95c  (same as crypto sniper ceiling)
Paper-only until 20 settled bets with WR >= 90%.

Injury guard layer (src/data/injury_leverage.py — currently dormant):
  If injury data becomes available, pass injuries=[{position, is_starter, team_side}]
  to SportsSniper.evaluate(). Kill threshold: 3.5pt expected line shift on the bet team.
  Until an injury feed is wired, the guard is a no-op (safe default = allow).
"""
import logging
import re
from typing import Optional

from src.data.injury_leverage import injury_kill_switch

logger = logging.getLogger(__name__)

# Price bounds — same logic as crypto sniper
_FLOOR_CENTS = 90
_CEILING_CENTS = 95

# Late-game thresholds (period, min_lead)
_THRESHOLDS = {
    "mlb": {"min_period": 7, "min_lead": 5},
    "nba": {"min_period": 4, "min_lead": 15},
    "nhl": {"min_period": 3, "min_lead": 3},
    "nfl": {"min_period": 4, "min_lead": 17},
}

# Kalshi series → sport
_SERIES_SPORT = {
    "KXNBAGAME": "nba",
    "KXNHLGAME": "nhl",
    "KXMLBGAME": "mlb",
    "KXNFLGAME": "nfl",
    "KXUCLGAME": "soccer_uefa_champs_league",
    "KXEPLGAME": "soccer_epl",
    "KXSERIEAGAME": "soccer_italy_serie_a",
    "KXBUNDESLIGAGAME": "soccer_germany_bundesliga",
    "KXLALIGAGAME": "soccer_spain_la_liga",
    "KXLIGUE1GAME": "soccer_france_ligue_one",
}

# Regex to parse Kalshi game-winner tickers
# US sports: KXNBAGAME-26MAR27CHIOKC-CHI  (series-date+teams-team, 3-char codes)
# Soccer:    KXUCLGAME-26APR07SPOARS-ARS  (same format, 3-char codes)
_TICKER_RE = re.compile(
    r"^(KXNBAGAME|KXNHLGAME|KXMLBGAME|KXNFLGAME"     # US sports series
    r"|KXUCLGAME|KXEPLGAME|KXSERIEAGAME"              # soccer series
    r"|KXBUNDESLIGAGAME|KXLALIGAGAME|KXLIGUE1GAME)"   # soccer series (cont.)
    r"-\d{2}[A-Z]{3}\d{2}"                            # date (e.g. 26APR07)
    r"(?:\d{4})?"                                      # optional time (e.g. 1315)
    r"([A-Z]{4,8})"                                    # combined teams (e.g. SPOARS)
    r"-([A-Z]{2,4})$"                                  # target team (e.g. ARS)
)


def parse_kalshi_game_ticker(ticker: str) -> Optional[dict]:
    """Parse a Kalshi game-winner ticker into its components.

    Returns dict with keys: series, sport, team, teams (frozenset).
    Returns None if the ticker is not a recognized game-winner format.
    """
    m = _TICKER_RE.match(ticker)
    if not m:
        return None
    series, combined, target_team = m.groups()
    sport = _SERIES_SPORT.get(series)
    if not sport:
        return None

    # Derive the other team: target is prefix or suffix of combined string
    # e.g. combined="CHIOKC", target="CHI" → other="OKC"
    # e.g. combined="PITNYM", target="NYM" → other="PIT"
    if combined.startswith(target_team):
        other_team = combined[len(target_team):]
    elif combined.endswith(target_team):
        other_team = combined[:-len(target_team)]
    else:
        return None  # malformed

    return {
        "series": series,
        "sport": sport,
        "team": target_team,
        "teams": frozenset([target_team, other_team]),
    }


class SportsSniper:
    """Generates YES signals for near-certain late-game sports outcomes."""

    def evaluate(
        self,
        game: dict,
        price_cents: int,
        injuries: Optional[list] = None,
    ) -> Optional[dict]:
        """Evaluate a live game and Kalshi market price for a sniper signal.

        Args:
            game: Normalized game dict from ESPNFeed._parse_game()
            price_cents: Current Kalshi YES price in cents for the leading team
            injuries: Optional list of injury dicts, each with keys:
                        position (str), is_starter (bool), team_side ("home"/"away")
                      Currently unused (ESPN feed has no injury data).
                      Pass when an injury feed is connected.

        Returns:
            Signal dict with keys (team, side, price_cents, sport, period, lead)
            or None if no bet should be placed.
        """
        sport = game.get("sport")
        thresholds = _THRESHOLDS.get(sport)
        if not thresholds:
            logger.debug("[sports_sniper] Unknown sport: %s", sport)
            return None

        period = game.get("period", 0)
        lead = game.get("lead", 0)
        leading_team = game.get("leading_team")

        # Must have a leading team
        if not leading_team:
            return None

        # Late-game gate
        if period < thresholds["min_period"]:
            logger.debug(
                "[sports_sniper] %s period %d < %d — too early",
                sport, period, thresholds["min_period"],
            )
            return None

        # Lead gate
        if lead < thresholds["min_lead"]:
            logger.debug(
                "[sports_sniper] %s lead %d < %d — insufficient lead",
                sport, lead, thresholds["min_lead"],
            )
            return None

        # Price gate
        if price_cents < _FLOOR_CENTS or price_cents > _CEILING_CENTS:
            logger.debug(
                "[sports_sniper] price %dc outside [%d, %d]",
                price_cents, _FLOOR_CENTS, _CEILING_CENTS,
            )
            return None

        # Injury guard: if injury data is available, check for kill-threshold absences
        if injuries:
            bet_direction = "home" if leading_team == game.get("home") else "away"
            for inj in injuries:
                kill, reason = injury_kill_switch(
                    sport=sport,
                    position=inj.get("position", ""),
                    is_starter=inj.get("is_starter", False),
                    team_side=inj.get("team_side", "home"),
                    bet_market="h2h",
                    bet_direction=bet_direction,
                )
                if kill:
                    logger.info(
                        "[sports_sniper] INJURY KILL %s %s: %s",
                        sport.upper(), leading_team, reason,
                    )
                    return None

        logger.info(
            "[sports_sniper] SIGNAL %s %s: period=%d lead=%d price=%dc",
            sport.upper(), leading_team, period, lead, price_cents,
        )
        return {
            "team": leading_team,
            "side": "yes",
            "price_cents": price_cents,
            "sport": sport,
            "period": period,
            "lead": lead,
        }
