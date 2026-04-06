"""
JOB:    Compare Kalshi NBA/NHL game-winner prices to bookmaker consensus odds.
        When Kalshi misprices a team vs the sharp-book consensus, bet the gap.

SIGNAL LOGIC:
    1. Fetch open Kalshi KXNBAGAME / KXNHLGAME markets
    2. Parse each market title → "Away at Home Winner?" → team names
    3. Match to sports feed game by team name similarity
    4. For each side (YES/NO): edge = consensus_prob - kalshi_price
    5. If edge > min_edge_pct: emit Signal

TICKER FORMAT:
    KXNBAGAME-26FEB28HOUMIA-HOU  →  "Houston at Miami Winner?" YES side = HOU wins
    KXNHLGAME-26FEB28EDMSJ-EDM   →  "Edmonton at San Jose Winner?" YES side = EDM wins

DATA SOURCE:
    External sports feed v4 — requires SDATA_KEY in .env
    Budget: 500 credits/month hard cap (enforced by _QuotaGuard)
    Cache: 15 min (feed level) — so this strategy never burns quota itself

REFERENCE: nikhilnd/kalshi-market-making (Avellaneda-Stoikov)
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING, List, Optional

from src.strategies.base import BaseStrategy, Signal

if TYPE_CHECKING:
    from src.platforms.kalshi import Market

logger = logging.getLogger(__name__)


# ── Team name normalisation ──────────────────────────────────────────────────
# Kalshi titles use city/short names. Sports feed uses full franchise names.
# Map common Kalshi city patterns → words that appear in sports feed team name.

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


_MLB_CITY_MAP = {
    "Arizona": "Arizona Diamondbacks",
    "Atlanta": "Atlanta Braves",
    "Baltimore": "Baltimore Orioles",
    "Boston": "Boston Red Sox",
    "Chicago C": "Chicago Cubs",
    "Chicago S": "Chicago White Sox",
    "Cincinnati": "Cincinnati Reds",
    "Cleveland": "Cleveland Guardians",
    "Colorado": "Colorado Rockies",
    "Detroit": "Detroit Tigers",
    "Houston": "Houston Astros",
    "Kansas City": "Kansas City Royals",
    "Los Angeles D": "Los Angeles Dodgers",
    "Los Angeles A": "Los Angeles Angels",
    "Miami": "Miami Marlins",
    "Milwaukee": "Milwaukee Brewers",
    "Minnesota": "Minnesota Twins",
    "New York M": "New York Mets",
    "New York Y": "New York Yankees",
    "Oakland": "Oakland Athletics",
    "Philadelphia": "Philadelphia Phillies",
    "Pittsburgh": "Pittsburgh Pirates",
    "San Diego": "San Diego Padres",
    "San Francisco": "San Francisco Giants",
    "Seattle": "Seattle Mariners",
    "St. Louis": "St. Louis Cardinals",
    "Tampa Bay": "Tampa Bay Rays",
    "Texas": "Texas Rangers",
    "Toronto": "Toronto Blue Jays",
    "Washington": "Washington Nationals",
}

# Reverse maps: Kalshi ticker codes (e.g. "HOU") → city key in the city maps above
_NBA_CODE_TO_CITY = {
    "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn",
    "CHA": "Charlotte", "CHI": "Chicago", "CLE": "Cleveland",
    "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit",
    "GSW": "Golden State", "HOU": "Houston", "IND": "Indiana",
    "LAC": "Los Angeles C", "LAL": "Los Angeles L",
    "MEM": "Memphis", "MIA": "Miami", "MIL": "Milwaukee",
    "MIN": "Minnesota", "NOP": "New Orleans", "NYK": "New York",
    "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia",
    "PHX": "Phoenix", "POR": "Portland", "SAC": "Sacramento",
    "SAS": "San Antonio", "TOR": "Toronto", "UTA": "Utah",
    "WAS": "Washington",
}

_NHL_CODE_TO_CITY = {
    "ANA": "Anaheim", "BOS": "Boston", "BUF": "Buffalo",
    "CGY": "Calgary", "CAR": "Carolina", "CHI": "Chicago",
    "COL": "Colorado", "CBJ": "Columbus", "DAL": "Dallas",
    "DET": "Detroit", "EDM": "Edmonton", "FLA": "Florida",
    "LAK": "Los Angeles", "MIN": "Minnesota", "MTL": "Montreal",
    "NSH": "Nashville", "NJD": "New Jersey", "NYI": "New York I",
    "NYR": "New York R", "OTT": "Ottawa", "PHI": "Philadelphia",
    "PIT": "Pittsburgh", "SJS": "San Jose", "SEA": "Seattle",
    "STL": "St. Louis", "TBL": "Tampa Bay", "TOR": "Toronto",
    "UTA": "Utah", "VAN": "Vancouver", "VGK": "Vegas",
    "WSH": "Washington", "WPG": "Winnipeg",
}

_MLB_CODE_TO_CITY = {
    "ARI": "Arizona", "ATL": "Atlanta", "BAL": "Baltimore",
    "BOS": "Boston", "CHC": "Chicago C", "CWS": "Chicago S",
    "CIN": "Cincinnati", "CLE": "Cleveland", "COL": "Colorado",
    "DET": "Detroit", "HOU": "Houston", "KCR": "Kansas City",
    "LAD": "Los Angeles D", "LAA": "Los Angeles A",
    "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota",
    "NYM": "New York M", "NYY": "New York Y", "OAK": "Oakland",
    "PHI": "Philadelphia", "PIT": "Pittsburgh", "SDP": "San Diego",
    "SFG": "San Francisco", "SEA": "Seattle", "STL": "St. Louis",
    "TBR": "Tampa Bay", "TEX": "Texas", "TOR": "Toronto",
    "WSN": "Washington",
}


# ── Soccer team mappings ────────────────────────────────────────────────────
# Kalshi 3-letter ticker code → name that fuzzy-matches Odds API team names.
# UCL/EPL/Bundesliga/La Liga/Serie A/Ligue 1 — expand as new tickers are observed.

_SOCCER_CODE_TO_TEAM: dict[str, str] = {
    # UCL 2025-26 QF teams — use Kalshi subtitle names for consistency
    "ARS": "Arsenal",
    "SPO": "Sporting CP",
    "BAY": "Bayern Munich",
    "BMU": "Bayern Munich",   # BMU = Bayern MUnich (NOT Borussia Dortmund)
    "PSG": "PSG",             # Kalshi subtitle uses "PSG", not "Paris Saint Germain"
    "BAR": "Barcelona",
    "LIV": "Liverpool",
    "BVB": "Borussia Dortmund",
    "ATM": "Atletico",        # Kalshi subtitle uses "Atletico" (no "Madrid")
    "MCI": "Manchester City",
    "CFC": "Chelsea",
    "INT": "Internazionale",
    "REA": "Real Madrid",
    "RMA": "Real Madrid",
    "BEN": "Benfica",
    "SLB": "Benfica",
    "PSV": "PSV Eindhoven",
    "AJA": "Ajax",
    "JUV": "Juventus",
    "ACM": "Milan",           # Kalshi subtitle uses "Milan" (not "AC Milan")
    "MIL": "Milan",
    "NAP": "Napoli",
    "SEV": "Sevilla",
    "VIL": "Villarreal",
    "RBL": "RB Leipzig",
    "LEV": "Bayer Leverkusen",
    "BDO": "Borussia Dortmund",
    "DOR": "Borussia Dortmund",
    "FEY": "Feyenoord",
    "CLU": "Club Brugge",
    "CEL": "Celtic",
    "GIR": "Girona",
    "AST": "Aston Villa",
    "STU": "Stuttgart",
    "SHA": "Shakhtar Donetsk",
    # EPL 2024-25
    "MUN": "Manchester United",
    "TOT": "Tottenham Hotspur",
    "NEW": "Newcastle United",
    "AVL": "Aston Villa",
    "WHU": "West Ham United",
    "BRI": "Brighton",
    "BOU": "Bournemouth",
    "FUL": "Fulham",
    "WOL": "Wolverhampton Wanderers",
    "EVE": "Everton",
    "NOT": "Nottingham Forest",
    "CRY": "Crystal Palace",
    "BRE": "Brentford",
    "IPS": "Ipswich Town",
    "LEE": "Leeds United",
    "SOU": "Southampton",
    "LEI": "Leicester City",
    # Bundesliga
    "BAM": "Bayern Munich",
    "BLE": "Bayer Leverkusen",
    "MAI": "Mainz 05",
    "AUG": "Augsburg",
    "FRE": "Freiburg",
    # La Liga
    "ATC": "Atletico",
    "BET": "Real Betis",
    "SOC": "Real Sociedad",
    "OSA": "Osasuna",
    # Serie A
    "ITA": "Internazionale",
    "ROM": "Roma",
    "LAZ": "Lazio",
    "FIO": "Fiorentina",
    "TOR": "Torino",
    "BOL": "Bologna",
    "GEN": "Genoa",
    # Ligue 1
    "MON": "Monaco",
    "NIC": "Nice",
    "LYO": "Lyon",
    "MAR": "Marseille",
    "REN": "Rennes",
    "LIL": "Lille",
    "LEN": "Lens",
    "STR": "Strasbourg",
}

# Normalise Kalshi subtitle short names → Odds API full names (for team matching).
# Kalshi uses abbreviations; Odds API uses full international names.
_SOCCER_NAME_TO_ODDS: dict[str, str] = {
    "PSG": "Paris Saint Germain",
    "Atletico": "Atletico Madrid",   # Odds API: "Atlético Madrid" — accent stripped in _match_game
    "Atletico Madrid": "Atletico Madrid",
    "Milan": "AC Milan",
    "Inter": "Internazionale",
    "Sporting CP": "Sporting CP",
    "Man City": "Manchester City",
    "Man United": "Manchester United",
}

_SOCCER_SPORTS: frozenset = frozenset({
    "soccer_epl",
    "soccer_uefa_champs_league",
    "soccer_germany_bundesliga",
    "soccer_italy_serie_a",
    "soccer_spain_la_liga",
    "soccer_france_ligue_one",
})


def _code_to_city(code: str, sport: str) -> Optional[str]:
    """Convert a Kalshi ticker team code (e.g. 'HOU') to city name (e.g. 'Houston')."""
    if sport in _SOCCER_SPORTS:
        return _SOCCER_CODE_TO_TEAM.get(code)
    elif sport == "basketball_nba":
        return _NBA_CODE_TO_CITY.get(code)
    elif sport == "icehockey_nhl":
        return _NHL_CODE_TO_CITY.get(code)
    else:  # baseball_mlb
        return _MLB_CODE_TO_CITY.get(code)


def _resolve_team(kalshi_name: str, sport: str) -> Optional[str]:
    """Map Kalshi city/short name → sports feed full team name."""
    if sport in _SOCCER_SPORTS:
        if not kalshi_name:
            return None
        # Normalise Kalshi subtitle short names to Odds API full names.
        # e.g. "PSG" → "Paris Saint Germain", "Atletico" → "Atletico Madrid", "Milan" → "AC Milan"
        return _SOCCER_NAME_TO_ODDS.get(kalshi_name, kalshi_name)
    if sport == "basketball_nba":
        mapping = _NBA_CITY_MAP
    elif sport == "icehockey_nhl":
        mapping = _NHL_CITY_MAP
    else:  # baseball_mlb
        mapping = _MLB_CITY_MAP
    # Exact match first
    if kalshi_name in mapping:
        return mapping[kalshi_name]
    # Prefix match (handles "Los Angeles C" matching "Los Angeles C")
    for k, v in mapping.items():
        if kalshi_name.startswith(k) or k.startswith(kalshi_name):
            return v
    return None


def _resolve_market_subtitles(market: "Market", sport: str) -> tuple[Optional[str], Optional[str]]:
    """Resolve full yes/no team names from Kalshi market subtitles when present."""
    raw = getattr(market, "raw", {}) or {}
    yes_label = raw.get("yes_sub_title") or raw.get("yes_subtitle") or ""
    no_label = raw.get("no_sub_title") or raw.get("no_subtitle") or ""
    yes_team = _resolve_team(yes_label, sport) if yes_label else None
    no_team = _resolve_team(no_label, sport) if no_label else None
    return yes_team, no_team


def _parse_title(title: str) -> Optional[tuple[str, str]]:
    """
    'Houston at Miami Winner?' → ('Houston', 'Miami')   [away, home]
    'Los Angeles C at Golden State Winner?' → ('Los Angeles C', 'Golden State')
    'Sporting CP vs Arsenal Winner?' → ('Sporting CP', 'Arsenal')  [soccer "vs"]
    Returns (away, home) or None.
    """
    t = title.strip()
    # Standard US sports: "Away at Home Winner?"
    m = re.match(r"^(.+?) at (.+?) Winner\?$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Soccer: "Team A vs Team B Winner?"
    m = re.match(r"^(.+?) vs (.+?) Winner\?$", t)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


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
        market: "Market",
        odds_games: list,               # list[OddsGame] from SportsFeed
        yes_side_team: Optional[str] = None,  # parsed from ticker suffix
    ) -> Optional[Signal]:
        """
        market: a Kalshi KXNBAGAME or KXNHLGAME market
        odds_games: current odds from SportsFeed.get_nba_games() or get_nhl_games()
        yes_side_team: Kalshi city name for the YES side (parsed from ticker)
        """
        if not odds_games:
            return None

        # Parse market title to get both team names
        parsed = _parse_title(market.title or "")
        if not parsed:
            logger.debug("[sports_game] Cannot parse title: %s", market.title)
            return None
        away_kalshi, home_kalshi = parsed

        # Resolve to sports feed names
        away_odds_name = _resolve_team(away_kalshi, self.sport)
        home_odds_name = _resolve_team(home_kalshi, self.sport)
        if not away_odds_name or not home_odds_name:
            logger.debug("[sports_game] No team mapping: away=%s home=%s", away_kalshi, home_kalshi)
            return None

        subtitle_yes_team, subtitle_no_team = _resolve_market_subtitles(market, self.sport)

        # YES side is ideally sourced from Kalshi's subtitle metadata.
        # Fall back to the ticker suffix mapping when the API response lacks subtitles.
        yes_odds_name = subtitle_yes_team
        if yes_odds_name and yes_side_team:
            ticker_yes_team = _resolve_team(yes_side_team, self.sport)
            if ticker_yes_team and ticker_yes_team != yes_odds_name:
                logger.warning(
                    "[sports_game] YES-side mismatch for %s: ticker=%s subtitle=%s — skip",
                    market.ticker, ticker_yes_team, yes_odds_name,
                )
                return None
        elif not yes_odds_name and yes_side_team:
            yes_odds_name = _resolve_team(yes_side_team, self.sport)

        if not yes_odds_name:
            logger.debug("[sports_game] No mapping for YES team: %s", yes_side_team or "(missing)")
            return None

        expected_teams = {away_odds_name, home_odds_name}
        if yes_odds_name not in expected_teams:
            logger.warning(
                "[sports_game] YES team %s not in parsed matchup %s vs %s — skip",
                yes_odds_name, away_odds_name, home_odds_name,
            )
            return None
        if subtitle_no_team and subtitle_no_team not in expected_teams:
            logger.warning(
                "[sports_game] NO team %s not in parsed matchup %s vs %s — skip",
                subtitle_no_team, away_odds_name, home_odds_name,
            )
            return None

        # Find matching sports feed game — pass ticker date so same-team multi-day
        # series don't accidentally match the wrong game's odds.
        kalshi_date = _parse_ticker_date(market.ticker)
        game = _match_game(odds_games, home_odds_name, away_odds_name, kalshi_date)
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
        kalshi_no = 1.0 - kalshi_yes

        # Edge calculation: consensus_prob vs what Kalshi is offering
        # If consensus > kalshi_yes: YES is underpriced → BUY YES
        # After Kalshi fee: net_edge = (consensus - kalshi_yes) / consensus - fee
        if kalshi_yes <= 0.01 or kalshi_yes >= 0.99:
            return None  # Skip near-resolved markets

        edge_yes = consensus_prob - kalshi_yes
        # Approximate fee: Kalshi takes ~7% of gross profit on YES win
        fee = self._KALSHI_FEE_PCT * (1.0 - kalshi_yes)
        net_edge_yes = edge_yes - fee

        consensus_no = 1.0 - consensus_prob
        edge_no = consensus_no - kalshi_no
        fee_no = self._KALSHI_FEE_PCT * kalshi_yes
        net_edge_no = edge_no - fee_no

        logger.debug(
            "[sports_game] %s match=%s @ %s | yes_team=%s | YES=%d¢ vs fair=%.1f%% | NO=%d¢ vs fair=%.1f%% | edge_yes=%.1f%% edge_no=%.1f%% books=%d",
            market.ticker, game.away_team, game.home_team, yes_odds_name,
            int(kalshi_yes * 100), consensus_prob * 100,
            int(kalshi_no * 100), consensus_no * 100,
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
                    f"{yes_odds_name} YES consensus={consensus_prob:.0%} "
                    f"vs Kalshi YES={kalshi_yes:.0%} ({game.num_books} books)"
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
                    f"{yes_odds_name} YES overpriced: consensus={consensus_prob:.0%} "
                    f"vs Kalshi YES={kalshi_yes:.0%}; "
                    f"NO fair={consensus_no:.0%} vs Kalshi NO={kalshi_no:.0%} "
                    f"({game.num_books} books)"
                ),
            )

        return None


def _strip_accents(s: str) -> str:
    """Remove Unicode accents for fuzzy matching (e.g. 'Atlético' → 'atletico')."""
    return unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()


_TICKER_DATE_RE = re.compile(r"\d{2}([A-Z]{3})(\d{2})(\d{2})(\d{2})")
_MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}
# Kalshi sports game tickers embed game date+time: KXMLBGAME-26APR071845MILBOS
# The pattern is YY MONTH DAY HH MM (all digits, no separators).
# Non-game tickers (KXBTCD-26APR0617-T69999) don't follow this convention.
# We require the series to contain "GAME" or the ticker to match a sports series.
_SPORTS_TICKER_RE = re.compile(
    r"KXMLBGAME|KXNBAGAME|KXNHLGAME|KXUCLGAME|KXEPLGAME|KXBUNGAME|KXSERGAME|KXLALGAME|KXL1GAME",
    re.IGNORECASE,
)


def _parse_ticker_date(ticker: str) -> Optional[datetime]:
    """Extract game start time from a Kalshi sports-game ticker.

    KXMLBGAME-26APR071845MILBOS → 2026-04-07 18:45 UTC
    Returns timezone-aware UTC datetime, or None for non-sports/unparseable tickers.
    """
    if not _SPORTS_TICKER_RE.search(ticker):
        return None
    m = _TICKER_DATE_RE.search(ticker)
    if not m:
        return None
    month_str, day_str, hour_str, min_str = m.group(1), m.group(2), m.group(3), m.group(4)
    month = _MONTH_MAP.get(month_str)
    if not month:
        return None
    year = datetime.now(timezone.utc).year
    try:
        return datetime(year, month, int(day_str), int(hour_str), int(min_str),
                        tzinfo=timezone.utc)
    except ValueError:
        return None


def _match_game(games: list, home: str, away: str,
                kalshi_date: Optional[datetime] = None) -> Optional[object]:
    """Find the sports feed game matching home+away team names (case-insensitive partial).

    Accent-strips both sides so "Atletico Madrid" matches "Atlético Madrid" from Odds API.
    When kalshi_date is provided, prefers games whose commence_time falls within ±1 day;
    this prevents same-team games on adjacent days from producing false edge signals.
    """
    home_l, away_l = _strip_accents(home), _strip_accents(away)
    candidates = []
    for g in games:
        gh, ga = _strip_accents(g.home_team), _strip_accents(g.away_team)
        if (home_l in gh and away_l in ga) or (home_l in ga and away_l in gh):
            candidates.append(g)
    if not candidates:
        return None
    if kalshi_date is None or len(candidates) == 1:
        return candidates[0]
    # With multiple candidates (e.g. same teams play 2 days in a row), pick the
    # one whose commence_time is closest to kalshi_date.
    def _date_diff(g: object) -> float:
        ct = getattr(g, "commence_time", None)
        if not ct:
            return float("inf")
        try:
            game_dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            return abs((game_dt - kalshi_date).total_seconds())
        except (ValueError, AttributeError):
            return float("inf")
    return min(candidates, key=_date_diff)


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
