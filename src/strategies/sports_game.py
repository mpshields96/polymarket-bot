"""
JOB:    Compare Kalshi NBA/NHL game-winner prices to bookmaker consensus odds.
        When Kalshi misprices a team vs the sharp-book consensus, bet the gap.

SIGNAL LOGIC:
    1. Fetch open Kalshi KXNBAGAME / KXNHLGAME markets
    2. Parse each market title → "Away at Home Winner?" → team names
    3. Match to Odds API game by team name similarity
    4. For each side (YES/NO): edge = consensus_prob - kalshi_price
    5. If edge > min_edge_pct: emit Signal

TICKER FORMAT:
    KXNBAGAME-26FEB28HOUMIA-HOU  →  "Houston at Miami Winner?" YES side = HOU wins
    KXNHLGAME-26FEB28EDMSJ-EDM   →  "Edmonton at San Jose Winner?" YES side = EDM wins

DATA SOURCE:
    The-Odds-API v4 (api.the-odds-api.com) — requires ODDS_API_KEY in .env
    Budget: 1,000 credits/month (5% of 20k subscription)
    Cache: 15 min (feed level) — so this strategy never burns quota itself

REFERENCE: nikhilnd/kalshi-market-making (Avellaneda-Stoikov)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

from src.platforms.kalshi import Market
from src.strategies.base import BaseStrategy, Signal

logger = logging.getLogger(__name__)


# ── Team name normalisation ──────────────────────────────────────────────────
# Kalshi titles use city/short names. Odds API uses full franchise names.
# Map common Kalshi city patterns → words that appear in Odds API team name.

_NBA_CITY_MAP = {
    "Atlanta": "Atlanta Hawks",
    "Boston": "Boston Celtics",
    "Brooklyn": "Brooklyn Nets",
    "Charlotte": "Charlotte Hornets",
    "Chicago": "Chicago Bulls",
    "Cleveland": "Cleveland Cavaliers",
    "Dallas": "Dallas Mavericks",
    "Denver": "Denver Nuggets",
    "Detroit": "Detroit Pistons",
    "Golden State": "Golden State Warriors",
    "Houston": "Houston Rockets",
    "Indiana": "Indiana Pacers",
    "Los Angeles C": "Los Angeles Clippers",
    "Los Angeles L": "Los Angeles Lakers",
    "Memphis": "Memphis Grizzlies",
    "Miami": "Miami Heat",
    "Milwaukee": "Milwaukee Bucks",
    "Minnesota": "Minnesota Timberwolves",
    "New Orleans": "New Orleans Pelicans",
    "New York": "New York Knicks",
    "Oklahoma City": "Oklahoma City Thunder",
    "Orlando": "Orlando Magic",
    "Philadelphia": "Philadelphia 76ers",
    "Phoenix": "Phoenix Suns",
    "Portland": "Portland Trail Blazers",
    "Sacramento": "Sacramento Kings",
    "San Antonio": "San Antonio Spurs",
    "Toronto": "Toronto Raptors",
    "Utah": "Utah Jazz",
    "Washington": "Washington Wizards",
}

_NHL_CITY_MAP = {
    "Anaheim": "Anaheim Ducks",
    "Boston": "Boston Bruins",
    "Buffalo": "Buffalo Sabres",
    "Calgary": "Calgary Flames",
    "Carolina": "Carolina Hurricanes",
    "Chicago": "Chicago Blackhawks",
    "Colorado": "Colorado Avalanche",
    "Columbus": "Columbus Blue Jackets",
    "Dallas": "Dallas Stars",
    "Detroit": "Detroit Red Wings",
    "Edmonton": "Edmonton Oilers",
    "Florida": "Florida Panthers",
    "Los Angeles": "Los Angeles Kings",
    "Minnesota": "Minnesota Wild",
    "Montreal": "Montreal Canadiens",
    "Nashville": "Nashville Predators",
    "New Jersey": "New Jersey Devils",
    "New York I": "New York Islanders",
    "New York R": "New York Rangers",
    "Ottawa": "Ottawa Senators",
    "Philadelphia": "Philadelphia Flyers",
    "Pittsburgh": "Pittsburgh Penguins",
    "San Jose": "San Jose Sharks",
    "Seattle": "Seattle Kraken",
    "St. Louis": "St. Louis Blues",
    "Tampa Bay": "Tampa Bay Lightning",
    "Toronto": "Toronto Maple Leafs",
    "Utah": "Utah Hockey Club",
    "Vancouver": "Vancouver Canucks",
    "Vegas": "Vegas Golden Knights",
    "Washington": "Washington Capitals",
    "Winnipeg": "Winnipeg Jets",
}


def _resolve_team(kalshi_name: str, sport: str) -> Optional[str]:
    """Map Kalshi city/short name → Odds API full team name."""
    mapping = _NBA_CITY_MAP if sport == "basketball_nba" else _NHL_CITY_MAP
    # Exact match first
    if kalshi_name in mapping:
        return mapping[kalshi_name]
    # Prefix match (handles "Los Angeles C" matching "Los Angeles C")
    for k, v in mapping.items():
        if kalshi_name.startswith(k) or k.startswith(kalshi_name):
            return v
    return None


def _parse_title(title: str) -> Optional[tuple[str, str]]:
    """
    'Houston at Miami Winner?' → ('Houston', 'Miami')   [away, home]
    'Los Angeles C at Golden State Winner?' → ('Los Angeles C', 'Golden State')
    Returns (away, home) or None.
    """
    m = re.match(r"^(.+?) at (.+?) Winner\?$", title.strip())
    if not m:
        return None
    return m.group(1).strip(), m.group(2).strip()


# ── Strategy ─────────────────────────────────────────────────────────────────

@dataclass
class SportsGameStrategy(BaseStrategy):
    """
    Compares Kalshi NBA/NHL game-winner markets to bookmaker consensus.
    Emits Signal when Kalshi price diverges from sharp-book implied probability.
    """
    name: str = "sports_game_v1"
    sport: str = "basketball_nba"       # "basketball_nba" or "icehockey_nhl"
    min_edge_pct: float = 0.05          # Minimum edge after Kalshi fee
    min_minutes_remaining: float = 15.0 # Don't enter with < 15 min to game start
    min_books: int = 2                  # Require at least N books in consensus
    min_volume: int = 100               # Skip Kalshi markets with low volume

    # Kalshi fee model (approximation)
    _KALSHI_FEE_PCT: float = 0.07       # ~7% of winnings on binary markets

    def generate_signal(
        self,
        market: Market,
        odds_games: list,               # list[OddsGame] from OddsAPIFeed
        yes_side_team: Optional[str] = None,  # parsed from ticker suffix
    ) -> Optional[Signal]:
        """
        market: a Kalshi KXNBAGAME or KXNHLGAME market
        odds_games: current odds from OddsAPIFeed.get_nba_games() or get_nhl_games()
        yes_side_team: Kalshi city name for the YES side (parsed from ticker)
        """
        if not odds_games or not yes_side_team:
            return None

        # Parse market title to get both team names
        parsed = _parse_title(market.title or "")
        if not parsed:
            logger.debug("[sports_game] Cannot parse title: %s", market.title)
            return None
        away_kalshi, home_kalshi = parsed

        # Resolve to Odds API names
        away_odds_name = _resolve_team(away_kalshi, self.sport)
        home_odds_name = _resolve_team(home_kalshi, self.sport)
        if not away_odds_name or not home_odds_name:
            logger.debug("[sports_game] No team mapping: away=%s home=%s", away_kalshi, home_kalshi)
            return None

        # YES side is the team in the ticker suffix
        yes_odds_name = _resolve_team(yes_side_team, self.sport)
        if not yes_odds_name:
            logger.debug("[sports_game] No mapping for YES team: %s", yes_side_team)
            return None

        # Find matching Odds API game
        game = _match_game(odds_games, home_odds_name, away_odds_name)
        if not game:
            logger.debug("[sports_game] No odds match for %s vs %s", away_odds_name, home_odds_name)
            return None

        if game.num_books < self.min_books:
            logger.debug("[sports_game] Only %d books (need %d)", game.num_books, self.min_books)
            return None

        # Volume gate
        if (market.volume or 0) < self.min_volume:
            logger.debug("[sports_game] Low volume %d on %s", market.volume or 0, market.ticker)
            return None

        # Determine consensus prob for the YES side
        if yes_odds_name == game.home_team:
            consensus_prob = game.home_prob
        elif yes_odds_name == game.away_team:
            consensus_prob = game.away_prob
        else:
            logger.debug("[sports_game] YES team %s not in game %s vs %s",
                         yes_odds_name, game.home_team, game.away_team)
            return None

        # Kalshi price (YES side)
        kalshi_yes = (market.yes_price or 0) / 100.0   # cents → fraction

        # Edge calculation: consensus_prob vs what Kalshi is offering
        # If consensus > kalshi_yes: YES is underpriced → BUY YES
        # After Kalshi fee: net_edge = (consensus - kalshi_yes) / consensus - fee
        if kalshi_yes <= 0.01 or kalshi_yes >= 0.99:
            return None  # Skip near-resolved markets

        edge_yes = consensus_prob - kalshi_yes
        # Approximate fee: Kalshi takes ~7% of gross profit on YES win
        fee = self._KALSHI_FEE_PCT * (1.0 - kalshi_yes)
        net_edge_yes = edge_yes - fee

        edge_no = (1.0 - consensus_prob) - (1.0 - kalshi_yes)
        fee_no = self._KALSHI_FEE_PCT * kalshi_yes
        net_edge_no = edge_no - fee_no

        logger.debug(
            "[sports_game] %s YES=%d¢ consensus=%.1f%% edge_yes=%.1f%% edge_no=%.1f%% books=%d",
            market.ticker, int(kalshi_yes * 100), consensus_prob * 100,
            net_edge_yes * 100, net_edge_no * 100, game.num_books,
        )

        if net_edge_yes >= self.min_edge_pct:
            return Signal(
                ticker=market.ticker,
                side="yes",
                win_prob=consensus_prob,
                edge_pct=net_edge_yes,
                confidence=min(0.9, game.num_books / 5.0),
                price_cents=market.yes_price or 50,
                reason=(
                    f"{yes_odds_name} consensus={consensus_prob:.0%} "
                    f"vs Kalshi={kalshi_yes:.0%} ({game.num_books} books)"
                ),
            )

        if net_edge_no >= self.min_edge_pct:
            return Signal(
                ticker=market.ticker,
                side="no",
                win_prob=1.0 - consensus_prob,
                edge_pct=net_edge_no,
                confidence=min(0.9, game.num_books / 5.0),
                price_cents=market.no_price or 50,
                reason=(
                    f"{yes_odds_name} overpriced: consensus={consensus_prob:.0%} "
                    f"vs Kalshi={kalshi_yes:.0%} ({game.num_books} books)"
                ),
            )

        return None


def _match_game(games: list, home: str, away: str) -> Optional[object]:
    """Find the Odds API game matching home+away team names (case-insensitive partial)."""
    home_l, away_l = home.lower(), away.lower()
    for g in games:
        if home_l in g.home_team.lower() and away_l in g.away_team.lower():
            return g
        # Kalshi sometimes flips home/away designation
        if home_l in g.away_team.lower() and away_l in g.home_team.lower():
            return g
    return None


# ── Factory ─────────────────────────────────────────────────────────────────

def load_nba_from_config(config: dict) -> SportsGameStrategy:
    sg = config.get("strategy", {}).get("sports_game", {})
    return SportsGameStrategy(
        name="sports_game_nba_v1",
        sport="basketball_nba",
        min_edge_pct=sg.get("min_edge_pct", 0.05),
        min_minutes_remaining=sg.get("min_minutes_remaining", 15.0),
        min_books=sg.get("min_books", 2),
        min_volume=sg.get("min_volume", 100),
    )


def load_nhl_from_config(config: dict) -> SportsGameStrategy:
    sg = config.get("strategy", {}).get("sports_game", {})
    return SportsGameStrategy(
        name="sports_game_nhl_v1",
        sport="icehockey_nhl",
        min_edge_pct=sg.get("min_edge_pct", 0.05),
        min_minutes_remaining=sg.get("min_minutes_remaining", 15.0),
        min_books=sg.get("min_books", 2),
        min_volume=sg.get("min_volume", 100),
    )
