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
"""
import logging
import re
from typing import Optional

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
}

# Regex to parse Kalshi game-winner tickers
# Format: KXNBAGAME-26MAR27CHIOKC-CHI  (series-date+teams-team)
# Teams are concatenated without separator; we derive the pair from the target team.
_TICKER_RE = re.compile(
    r"^(KXNBAGAME|KXNHLGAME|KXMLBGAME|KXNFLGAME)"  # series
    r"-\d{2}[A-Z]{3}\d{2}"                           # date (e.g. 26MAR26)
    r"(?:\d{4})?"                                     # optional time (e.g. 1315)
    r"([A-Z]{4,8})"                                   # combined teams (e.g. CHIOKC)
    r"-([A-Z]{2,4})$"                                 # target team (e.g. CHI)
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

    def evaluate(self, game: dict, price_cents: int) -> Optional[dict]:
        """Evaluate a live game and Kalshi market price for a sniper signal.

        Args:
            game: Normalized game dict from ESPNFeed._parse_game()
            price_cents: Current Kalshi YES price in cents for the leading team

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
