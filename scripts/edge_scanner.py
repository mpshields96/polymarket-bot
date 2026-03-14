"""
Edge Scanner — Kalshi vs Pinnacle price comparison tool.

JOB:    Pull live Kalshi sports markets, compare to Pinnacle/sharp book odds,
        and flag discrepancies that represent exploitable edge.

USAGE:
    source venv/bin/activate
    python scripts/edge_scanner.py                    # scan all sports
    python scripts/edge_scanner.py --sport nba        # NBA only
    python scripts/edge_scanner.py --sport ncaab      # March Madness only
    python scripts/edge_scanner.py --min-edge 0.03    # 3% minimum edge
    python scripts/edge_scanner.py --dry-run          # don't call APIs, use cached data

OUTPUT:
    Prints discrepancies sorted by edge size.
    Saves results to data/edge_scan_results.json for later analysis.

API BUDGET:
    Kalshi: free (no quota)
    the-odds-api: ~1 credit per sport per call (500/month cap)
    Total per full scan: ~3-5 credits
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from src.auth.kalshi_auth import load_from_env as load_kalshi_auth
from src.platforms.kalshi import KalshiClient, Market

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────

# Kalshi series → the-odds-api sport key mapping
SPORT_MAP = {
    "KXNBAGAME": "basketball_nba",
    "KXNHLGAME": "icehockey_nhl",
    "KXNCAAMBGAME": "basketball_ncaab",
    "KXMLBGAME": "baseball_mlb",
}

# the-odds-api base
ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"

# Kalshi taker fee formula: 0.07 * P * (1-P) per contract
KALSHI_FEE_RATE = 0.07

# Preferred bookmakers (sharpest first)
SHARP_BOOKS = ["pinnacle", "draftkings", "fanduel", "betmgm"]


# ── Data classes ──────────────────────────────────────────────────────────

@dataclass
class OddsComparison:
    """One Kalshi market compared to sharp book odds."""
    kalshi_ticker: str
    kalshi_title: str
    kalshi_yes_cents: int
    kalshi_no_cents: int
    kalshi_volume: int
    sport: str
    # Sharp book data
    sharp_yes_prob: float       # devigged probability for YES side
    sharp_no_prob: float        # devigged probability for NO side
    num_books: int
    pinnacle_yes_prob: Optional[float]  # Pinnacle specifically (if available)
    # Edge calculations
    yes_edge_raw: float         # sharp_yes_prob - kalshi_yes_price
    no_edge_raw: float          # sharp_no_prob - kalshi_no_price
    yes_edge_net: float         # after Kalshi taker fee
    no_edge_net: float          # after Kalshi taker fee
    # Limit order edge (maker = ~0 fee)
    yes_edge_maker: float       # edge if using limit order
    no_edge_maker: float
    # Match info
    home_team: str
    away_team: str
    commence_time: str
    best_side: str              # "yes", "no", or "none"
    best_edge: float            # max(yes_edge_net, no_edge_net)


@dataclass
class ScanResult:
    """Full scan output."""
    timestamp: str
    sports_scanned: List[str]
    total_kalshi_markets: int
    total_matched: int
    total_with_edge: int
    min_edge_threshold: float
    opportunities: List[OddsComparison]
    credits_used: int


# ── Team name matching ───────────────────────────────────────────────────

# Common abbreviations/city names used by Kalshi in tickers and titles
_TEAM_ALIASES: Dict[str, List[str]] = {
    # NBA
    "Atlanta Hawks": ["ATL", "Atlanta", "Hawks"],
    "Boston Celtics": ["BOS", "Boston", "Celtics"],
    "Brooklyn Nets": ["BKN", "Brooklyn", "Nets"],
    "Charlotte Hornets": ["CHA", "Charlotte", "Hornets"],
    "Chicago Bulls": ["CHI", "Chicago", "Bulls"],
    "Cleveland Cavaliers": ["CLE", "Cleveland", "Cavaliers", "Cavs"],
    "Dallas Mavericks": ["DAL", "Dallas", "Mavericks", "Mavs"],
    "Denver Nuggets": ["DEN", "Denver", "Nuggets"],
    "Detroit Pistons": ["DET", "Detroit", "Pistons"],
    "Golden State Warriors": ["GSW", "Golden State", "Warriors"],
    "Houston Rockets": ["HOU", "Houston", "Rockets"],
    "Indiana Pacers": ["IND", "Indiana", "Pacers"],
    "Los Angeles Clippers": ["LAC", "LA Clippers", "Clippers"],
    "Los Angeles Lakers": ["LAL", "LA Lakers", "Lakers"],
    "Memphis Grizzlies": ["MEM", "Memphis", "Grizzlies"],
    "Miami Heat": ["MIA", "Miami", "Heat"],
    "Milwaukee Bucks": ["MIL", "Milwaukee", "Bucks"],
    "Minnesota Timberwolves": ["MIN", "Minnesota", "Timberwolves", "Wolves"],
    "New Orleans Pelicans": ["NOP", "New Orleans", "Pelicans"],
    "New York Knicks": ["NYK", "New York", "Knicks"],
    "Oklahoma City Thunder": ["OKC", "Oklahoma City", "Thunder"],
    "Orlando Magic": ["ORL", "Orlando", "Magic"],
    "Philadelphia 76ers": ["PHI", "Philadelphia", "76ers", "Sixers"],
    "Phoenix Suns": ["PHX", "Phoenix", "Suns"],
    "Portland Trail Blazers": ["POR", "Portland", "Trail Blazers", "Blazers"],
    "Sacramento Kings": ["SAC", "Sacramento", "Kings"],
    "San Antonio Spurs": ["SAS", "San Antonio", "Spurs"],
    "Toronto Raptors": ["TOR", "Toronto", "Raptors"],
    "Utah Jazz": ["UTA", "Utah", "Jazz"],
    "Washington Wizards": ["WAS", "Washington", "Wizards"],
    # NHL
    "Anaheim Ducks": ["ANA", "Anaheim", "Ducks"],
    "Boston Bruins": ["BOS", "Boston", "Bruins"],
    "Buffalo Sabres": ["BUF", "Buffalo", "Sabres"],
    "Calgary Flames": ["CGY", "Calgary", "Flames"],
    "Carolina Hurricanes": ["CAR", "Carolina", "Hurricanes", "Canes"],
    "Chicago Blackhawks": ["CHI", "Chicago", "Blackhawks"],
    "Colorado Avalanche": ["COL", "Colorado", "Avalanche", "Avs"],
    "Columbus Blue Jackets": ["CBJ", "Columbus", "Blue Jackets"],
    "Dallas Stars": ["DAL", "Dallas", "Stars"],
    "Detroit Red Wings": ["DET", "Detroit", "Red Wings"],
    "Edmonton Oilers": ["EDM", "Edmonton", "Oilers"],
    "Florida Panthers": ["FLA", "Florida", "Panthers"],
    "Los Angeles Kings": ["LAK", "Los Angeles", "Kings"],
    "Minnesota Wild": ["MIN", "Minnesota", "Wild"],
    "Montreal Canadiens": ["MTL", "Montreal", "Canadiens", "Habs"],
    "Nashville Predators": ["NSH", "Nashville", "Predators", "Preds"],
    "New Jersey Devils": ["NJD", "New Jersey", "Devils"],
    "New York Islanders": ["NYI", "NY Islanders", "Islanders"],
    "New York Rangers": ["NYR", "NY Rangers", "Rangers"],
    "Ottawa Senators": ["OTT", "Ottawa", "Senators", "Sens"],
    "Philadelphia Flyers": ["PHI", "Philadelphia", "Flyers"],
    "Pittsburgh Penguins": ["PIT", "Pittsburgh", "Penguins", "Pens"],
    "San Jose Sharks": ["SJS", "San Jose", "Sharks"],
    "Seattle Kraken": ["SEA", "Seattle", "Kraken"],
    "St Louis Blues": ["STL", "St. Louis", "Blues"],
    "Tampa Bay Lightning": ["TBL", "Tampa Bay", "Lightning", "Bolts"],
    "Toronto Maple Leafs": ["TOR", "Toronto", "Maple Leafs", "Leafs"],
    "Utah Hockey Club": ["UTA", "Utah HC", "Utah Hockey"],
    "Vancouver Canucks": ["VAN", "Vancouver", "Canucks"],
    "Vegas Golden Knights": ["VGK", "Vegas", "Golden Knights", "Knights"],
    "Washington Capitals": ["WSH", "Washington", "Capitals", "Caps"],
    "Winnipeg Jets": ["WPG", "Winnipeg", "Jets"],
}


def _normalize(name: str) -> str:
    """Lowercase, strip punctuation for fuzzy matching."""
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _match_team(kalshi_name: str, odds_teams: List[str]) -> Optional[str]:
    """Match a Kalshi team name/abbrev to a the-odds-api team name."""
    kn = _normalize(kalshi_name)
    if len(kn) < 2:
        return None

    # 1. Exact match
    for team in odds_teams:
        tn = _normalize(team)
        if kn == tn:
            return team

    # 2. Alias match (most reliable for short abbreviations like "LA", "NY")
    for full_name, aliases in _TEAM_ALIASES.items():
        fn = _normalize(full_name)
        for alias in aliases:
            an = _normalize(alias)
            if an == kn or (len(kn) >= 3 and (kn.startswith(an) or an.startswith(kn))):
                # Found alias match — now find this team in odds_teams
                for team in odds_teams:
                    tn = _normalize(team)
                    if fn == tn or fn in tn or tn in fn:
                        return team

    # 3. Substring match — only for longer names (>= 4 chars) to avoid
    #    false positives like "la" matching "islanders"
    if len(kn) >= 4:
        # Prefer team where kalshi name appears at START of a word
        best_match = None
        for team in odds_teams:
            tn = _normalize(team)
            # Check if kn appears at start of any word in tn
            words = tn.split()
            for word in words:
                if word.startswith(kn) or kn.startswith(word):
                    return team
            # Fallback: substring match
            if kn in tn:
                best_match = team
        if best_match:
            return best_match

    # 4. For very short names (2-3 chars), only match if it's a word boundary
    if len(kn) <= 3:
        for team in odds_teams:
            tn = _normalize(team)
            words = tn.split()
            for word in words:
                if word == kn or word.startswith(kn):
                    return team

    return None


def _parse_kalshi_game_title(title: str) -> Optional[Tuple[str, str]]:
    """Parse 'Away at Home Winner?' → (away, home)."""
    m = re.match(r"^(.+?)\s+at\s+(.+?)\s+Winner\??$", title.strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    # Also try "Team A vs Team B" pattern
    m = re.match(r"^(.+?)\s+vs\.?\s+(.+?)(?:\s+Winner)?\??$", title.strip(), re.IGNORECASE)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return None


def _kalshi_taker_fee(price_frac: float) -> float:
    """Kalshi taker fee per contract given price as fraction (0-1)."""
    return KALSHI_FEE_RATE * price_frac * (1.0 - price_frac)


# ── API calls ─────────────────────────────────────────────────────────────

async def fetch_kalshi_sports_markets(
    client: KalshiClient,
    series_ticker: str,
) -> List[Market]:
    """Fetch all open markets for a Kalshi sports series."""
    all_markets = []
    cursor = None
    for _ in range(20):  # safety limit
        markets = await client.get_markets(
            series_ticker=series_ticker,
            status="open",
            limit=100,
            cursor=cursor,
        )
        if not markets:
            break
        all_markets.extend(markets)
        if len(markets) < 100:
            break
        # Get cursor from last market for pagination
        cursor = markets[-1].raw.get("cursor")
        if not cursor:
            break
    return all_markets


async def fetch_odds_api_games(
    api_key: str,
    sport: str,
    bookmakers: str = "pinnacle,draftkings,fanduel",
) -> Tuple[List[dict], int]:
    """
    Fetch game odds from the-odds-api.
    Returns (list of game dicts, credits used).
    """
    import aiohttp

    url = f"{ODDS_API_BASE}/{sport}/odds/"
    params = {
        "apiKey": api_key,
        "regions": "us,eu",  # Include EU for Pinnacle
        "markets": "h2h",
        "oddsFormat": "decimal",
        "bookmakers": bookmakers,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params,
                               timeout=aiohttp.ClientTimeout(total=15)) as resp:
            used = resp.headers.get("x-requests-used", "0")
            remaining = resp.headers.get("x-requests-remaining", "?")
            if resp.status != 200:
                body = await resp.text()
                logger.error("Odds API HTTP %d: %s", resp.status, body[:200])
                return [], 0
            data = await resp.json()
            logger.info("Odds API %s: %d games (used=%s remaining=%s)",
                        sport, len(data), used, remaining)
            return data, int(used) if used.isdigit() else 0


def _devig_h2h(outcomes: List[dict], home: str, away: str) -> Optional[Tuple[float, float]]:
    """Devig h2h odds → (home_prob, away_prob) summing to 1.0."""
    home_dec = None
    away_dec = None
    for o in outcomes:
        if o.get("name") == home:
            home_dec = float(o.get("price", 0))
        elif o.get("name") == away:
            away_dec = float(o.get("price", 0))
    if not home_dec or not away_dec or home_dec <= 1.0 or away_dec <= 1.0:
        return None
    h_raw = 1.0 / home_dec
    a_raw = 1.0 / away_dec
    total = h_raw + a_raw
    if total <= 0:
        return None
    return h_raw / total, a_raw / total


def parse_odds_games(raw_games: List[dict]) -> Dict[str, dict]:
    """
    Parse the-odds-api response into a dict keyed by normalized matchup.
    Each value has: home, away, home_prob, away_prob, pinnacle_home, pinnacle_away, num_books.
    """
    result = {}
    for game in raw_games:
        home = game.get("home_team", "")
        away = game.get("away_team", "")
        if not home or not away:
            continue

        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            continue

        all_home_probs = []
        all_away_probs = []
        pinnacle_home = None
        pinnacle_away = None

        for bm in bookmakers:
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "h2h":
                    continue
                devigged = _devig_h2h(mkt.get("outcomes", []), home, away)
                if not devigged:
                    continue
                all_home_probs.append(devigged[0])
                all_away_probs.append(devigged[1])
                if bm.get("key") == "pinnacle":
                    pinnacle_home = devigged[0]
                    pinnacle_away = devigged[1]

        if not all_home_probs:
            continue

        consensus_home = sum(all_home_probs) / len(all_home_probs)
        consensus_away = sum(all_away_probs) / len(all_away_probs)

        key = f"{_normalize(away)}_at_{_normalize(home)}"
        result[key] = {
            "home": home,
            "away": away,
            "home_prob": consensus_home,
            "away_prob": consensus_away,
            "pinnacle_home": pinnacle_home,
            "pinnacle_away": pinnacle_away,
            "num_books": len(all_home_probs),
            "commence_time": game.get("commence_time", ""),
        }

    return result


def compare_market(
    market: Market,
    odds_lookup: Dict[str, dict],
    sport: str,
) -> Optional[OddsComparison]:
    """Compare one Kalshi market to sharp book odds."""
    parsed = _parse_kalshi_game_title(market.title or "")
    if not parsed:
        return None

    away_kalshi, home_kalshi = parsed
    all_teams = []
    for g in odds_lookup.values():
        all_teams.extend([g["home"], g["away"]])
    all_teams = list(set(all_teams))

    home_matched = _match_team(home_kalshi, all_teams)
    away_matched = _match_team(away_kalshi, all_teams)

    if not home_matched or not away_matched:
        logger.debug("No match for %s vs %s", away_kalshi, home_kalshi)
        return None

    # Find the game in odds lookup
    game_data = None
    for g in odds_lookup.values():
        if ((g["home"] == home_matched and g["away"] == away_matched) or
                (g["home"] == away_matched and g["away"] == home_matched)):
            game_data = g
            break

    if not game_data:
        return None

    # Determine which team is YES side on Kalshi
    # Ticker format: KXNCAAMBGAME-26MAR13HALLSJU-SJU  → suffix "SJU" = YES team
    # Title: "Seton Hall Pirates at St. John's Red Storm Winner?"
    # We need to figure out: does "SJU" refer to the home or away team?
    ticker_parts = market.ticker.split("-")
    yes_team_abbrev = ticker_parts[-1] if len(ticker_parts) >= 3 else ""

    # Strategy: try to match ticker suffix to one of the title teams
    # First, try direct alias-based matching
    yes_matched = _match_team(yes_team_abbrev, [game_data["home"], game_data["away"]])

    if not yes_matched:
        # Fuzzy: check if abbrev appears in the team name (case-insensitive)
        # e.g., "SJU" in "St. John's" won't work, but "MSU" in "Michigan St Spartans"
        # Also try: the Kalshi title teams → which one shares more letters with the odds team?
        # Best approach: match title teams to odds teams, then map ticker suffix to title position
        home_odds_match = _match_team(home_kalshi, [game_data["home"], game_data["away"]])
        away_odds_match = _match_team(away_kalshi, [game_data["home"], game_data["away"]])

        if home_odds_match and away_odds_match:
            # Both title teams matched — now figure out which title team the ticker refers to
            # The ticker middle section often has both abbrevs: "HALLSJU" = HALL + SJU
            # SJU is likely the home team (second in title = "at HOME")
            # HALL is likely the away team (first in title = "AWAY at")
            middle = ticker_parts[1] if len(ticker_parts) >= 3 else ""
            # Check if suffix matches start or end of the middle part's team abbreviations
            if middle.endswith(yes_team_abbrev):
                # Suffix = second team = home in title
                yes_matched = home_odds_match
            elif middle.startswith(yes_team_abbrev):
                # Suffix = first team = away in title
                yes_matched = away_odds_match
            else:
                # Can't determine — skip this market
                logger.debug("Cannot determine YES team for %s (suffix=%s mid=%s)",
                             market.ticker, yes_team_abbrev, middle)
                return None
        else:
            return None

    if not yes_matched:
        return None

    if yes_matched == game_data["home"]:
        sharp_yes = game_data["home_prob"]
        sharp_no = game_data["away_prob"]
        pinnacle_yes = game_data.get("pinnacle_home")
    else:
        sharp_yes = game_data["away_prob"]
        sharp_no = game_data["home_prob"]
        pinnacle_yes = game_data.get("pinnacle_away")

    # Kalshi prices: yes_price=yes_bid, no_price=no_bid
    # To BUY YES: pay the ask = 100 - no_bid
    # To BUY NO: pay the ask = 100 - yes_bid
    yes_bid = market.yes_price or 0
    no_bid = market.no_price or 0
    yes_ask = 100 - no_bid if no_bid > 0 else 100
    no_ask = 100 - yes_bid if yes_bid > 0 else 100

    # Mid-prices for display (what the market "thinks")
    yes_mid = (yes_bid + yes_ask) / 2.0
    no_mid = (no_bid + no_ask) / 2.0

    # Edge = sharp_prob - price_to_buy (ask, not bid)
    yes_ask_frac = yes_ask / 100.0
    no_ask_frac = no_ask / 100.0
    kalshi_yes_frac = yes_mid / 100.0  # for OddsComparison fields
    kalshi_no_frac = no_mid / 100.0

    # Raw edge (vs ask price — what you'd actually pay)
    yes_edge_raw = sharp_yes - yes_ask_frac
    no_edge_raw = sharp_no - no_ask_frac

    # Net edge (after taker fee on the ask price)
    yes_fee = _kalshi_taker_fee(yes_ask_frac)
    no_fee = _kalshi_taker_fee(no_ask_frac)
    yes_edge_net = yes_edge_raw - yes_fee
    no_edge_net = no_edge_raw - no_fee

    # Maker edge: place limit at mid or slightly better — saves taker fee
    # Approximate: buy at mid instead of ask
    yes_edge_maker = sharp_yes - (yes_mid / 100.0)
    no_edge_maker = sharp_no - (no_mid / 100.0)

    best_side = "none"
    best_edge = 0.0
    if yes_edge_net > no_edge_net and yes_edge_net > 0:
        best_side = "yes"
        best_edge = yes_edge_net
    elif no_edge_net > 0:
        best_side = "no"
        best_edge = no_edge_net

    return OddsComparison(
        kalshi_ticker=market.ticker,
        kalshi_title=market.title or "",
        kalshi_yes_cents=market.yes_price or 50,
        kalshi_no_cents=market.no_price or 50,
        kalshi_volume=market.volume or 0,
        sport=sport,
        sharp_yes_prob=round(sharp_yes, 4),
        sharp_no_prob=round(sharp_no, 4),
        num_books=game_data["num_books"],
        pinnacle_yes_prob=round(pinnacle_yes, 4) if pinnacle_yes else None,
        yes_edge_raw=round(yes_edge_raw, 4),
        no_edge_raw=round(no_edge_raw, 4),
        yes_edge_net=round(yes_edge_net, 4),
        no_edge_net=round(no_edge_net, 4),
        yes_edge_maker=round(yes_edge_maker, 4),
        no_edge_maker=round(no_edge_maker, 4),
        home_team=game_data["home"],
        away_team=game_data["away"],
        commence_time=game_data.get("commence_time", ""),
        best_side=best_side,
        best_edge=round(best_edge, 4),
    )


# ── Game-in-progress filter ───────────────────────────────────────────────

def _game_started(commence_time: str) -> bool:
    """Return True if the game has already started (commence_time is in the past)."""
    if not commence_time:
        return False
    try:
        game_start = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        return game_start < datetime.now(timezone.utc)
    except (ValueError, TypeError):
        return False  # unparseable — don't filter


# ── Main scan ─────────────────────────────────────────────────────────────

async def run_scan(
    sports: List[str],
    min_edge: float = 0.02,
    save_path: str = "data/edge_scan_results.json",
) -> ScanResult:
    """Run the full edge scan."""
    # Init Kalshi client
    auth = load_kalshi_auth()
    base_url = os.getenv("KALSHI_API_URL", "https://api.elections.kalshi.com/trade-api/v2")
    kalshi = KalshiClient(auth=auth, base_url=base_url)
    odds_key = os.getenv("SDATA_KEY", "")
    if not odds_key:
        logger.error("SDATA_KEY not set — cannot fetch odds")
        return ScanResult(
            timestamp=datetime.now(timezone.utc).isoformat(),
            sports_scanned=sports,
            total_kalshi_markets=0,
            total_matched=0,
            total_with_edge=0,
            min_edge_threshold=min_edge,
            opportunities=[],
            credits_used=0,
        )

    all_opportunities: List[OddsComparison] = []
    total_kalshi = 0
    total_matched = 0
    total_credits = 0

    for series_ticker, odds_sport in SPORT_MAP.items():
        if sports and odds_sport not in sports:
            continue

        logger.info("Scanning %s (%s)...", series_ticker, odds_sport)

        # Fetch Kalshi markets
        try:
            if not kalshi._session:
                await kalshi.start()
            markets = await fetch_kalshi_sports_markets(kalshi, series_ticker)
        except Exception as e:
            logger.warning("Kalshi fetch failed for %s: %s", series_ticker, e)
            markets = []

        total_kalshi += len(markets)
        if not markets:
            logger.info("  No open Kalshi markets for %s", series_ticker)
            continue

        logger.info("  %d open Kalshi markets", len(markets))

        # Fetch odds
        try:
            raw_games, credits = await fetch_odds_api_games(
                odds_key, odds_sport,
                bookmakers=",".join(SHARP_BOOKS),
            )
            total_credits = max(total_credits, credits)
        except Exception as e:
            logger.warning("Odds API fetch failed for %s: %s", odds_sport, e)
            continue

        if not raw_games:
            logger.info("  No odds data for %s", odds_sport)
            continue

        odds_lookup = parse_odds_games(raw_games)
        logger.info("  %d games with odds data", len(odds_lookup))

        # Compare each Kalshi market
        for market in markets:
            comp = compare_market(market, odds_lookup, odds_sport)
            if comp:
                total_matched += 1
                # Skip in-progress/settled games (commence_time already passed)
                if _game_started(comp.commence_time):
                    logger.debug(
                        "Skip %s — game started %s",
                        comp.kalshi_ticker, comp.commence_time,
                    )
                    continue
                if comp.best_edge >= min_edge:
                    all_opportunities.append(comp)

    # Cleanup
    try:
        await kalshi.close()
    except Exception:
        pass

    # Sort by edge (descending)
    all_opportunities.sort(key=lambda x: x.best_edge, reverse=True)

    result = ScanResult(
        timestamp=datetime.now(timezone.utc).isoformat(),
        sports_scanned=sports or list(SPORT_MAP.values()),
        total_kalshi_markets=total_kalshi,
        total_matched=total_matched,
        total_with_edge=len(all_opportunities),
        min_edge_threshold=min_edge,
        opportunities=all_opportunities,
        credits_used=total_credits,
    )

    # Save results
    try:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "w") as f:
            json.dump(asdict(result), f, indent=2, default=str)
        logger.info("Results saved to %s", save_path)
    except Exception as e:
        logger.warning("Could not save results: %s", e)

    return result


def print_results(result: ScanResult) -> None:
    """Print scan results in a readable format."""
    print(f"\n{'='*70}")
    print(f"EDGE SCANNER — {result.timestamp}")
    print(f"{'='*70}")
    print(f"Sports scanned: {', '.join(result.sports_scanned)}")
    print(f"Kalshi markets found: {result.total_kalshi_markets}")
    print(f"Matched to odds: {result.total_matched}")
    print(f"With edge >= {result.min_edge_threshold:.1%}: {result.total_with_edge}")
    print(f"API credits used: {result.credits_used}")

    if not result.opportunities:
        print("\nNo opportunities found above threshold.")
        print("Try lowering --min-edge or scanning during game hours.")
        return

    print(f"\n{'='*70}")
    print("OPPORTUNITIES (sorted by edge)")
    print(f"{'='*70}\n")

    for i, opp in enumerate(result.opportunities, 1):
        side_label = opp.best_side.upper()
        sharp_prob = opp.sharp_yes_prob if opp.best_side == "yes" else opp.sharp_no_prob
        maker_edge = opp.yes_edge_maker if opp.best_side == "yes" else opp.no_edge_maker

        # Show bid/ask for the relevant side
        yes_bid = opp.kalshi_yes_cents
        no_bid = opp.kalshi_no_cents
        if opp.best_side == "yes":
            ask_price = 100 - no_bid
            bid_price = yes_bid
        else:
            ask_price = 100 - yes_bid
            bid_price = no_bid
        mid_price = (bid_price + ask_price) / 2
        spread = ask_price - bid_price

        print(f"  #{i} {opp.kalshi_ticker}")
        print(f"     {opp.away_team} at {opp.home_team}")
        print(f"     Side: {side_label} | Bid={bid_price}c Ask={ask_price}c Mid={mid_price:.0f}c Spread={spread}c")
        print(f"     Sharp: {sharp_prob:.1%} | Books: {opp.num_books}")
        print(f"     Edge vs ask (taker): {opp.best_edge:.1%} | Edge vs mid (maker): {maker_edge:.1%}")
        if opp.pinnacle_yes_prob:
            pin_prob = opp.pinnacle_yes_prob if opp.best_side == "yes" else (1 - opp.pinnacle_yes_prob)
            print(f"     Pinnacle: {pin_prob:.1%}")
        print(f"     Volume: {opp.kalshi_volume:,} | Game: {opp.commence_time}")
        print()


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Kalshi vs Pinnacle Edge Scanner")
    parser.add_argument("--sport", type=str, default="",
                        help="Filter: nba, nhl, ncaab, mlb (comma-separated)")
    parser.add_argument("--min-edge", type=float, default=0.02,
                        help="Minimum net edge to display (default: 2%%)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
    )

    # Parse sport filter
    sport_filter = []
    if args.sport:
        for s in args.sport.split(","):
            s = s.strip().lower()
            mapping = {
                "nba": "basketball_nba",
                "nhl": "icehockey_nhl",
                "ncaab": "basketball_ncaab",
                "mlb": "baseball_mlb",
            }
            if s in mapping:
                sport_filter.append(mapping[s])
            else:
                print(f"Unknown sport: {s}. Options: nba, nhl, ncaab, mlb")
                sys.exit(1)

    result = asyncio.run(run_scan(
        sports=sport_filter,
        min_edge=args.min_edge,
    ))
    print_results(result)


if __name__ == "__main__":
    main()
