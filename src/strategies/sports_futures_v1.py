"""
Sports futures mispricing strategy for Polymarket.us.

JOB:    Compare Polymarket.us season-winner futures prices to sports feed sharp
        consensus (Pinnacle / DraftKings) and signal when edge > min_edge_pct.

DOES NOT: Execute trades, know about sizing, risk decisions, or API calls.
          Signal generation only — all I/O done before calling scan_for_signals().

Supported markets (as of 2026-03):
  - NBA Championship Winner (basketball_nba_championship_winner)
  - NHL Stanley Cup Champion  (icehockey_nhl_championship_winner)
  - NCAA Tournament Winner    (basketball_ncaab_championship_winner)

Signal logic:
  BUY YES if pm_price < odds_prob - min_edge_pct  (market underpriced)
  BUY NO  if pm_price > odds_prob + min_edge_pct  (market overpriced)

Team name matching: normalize_team_name() strips city prefix to get canonical
short name ("Oklahoma City Thunder" → "thunder") for fuzzy cross-platform matching.

Paper-only until POST /v1/orders format is confirmed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.data.odds_api import ChampionshipOdds
from src.platforms.polymarket import PolymarketMarket
from src.strategies.base import Signal

logger = logging.getLogger(__name__)

# Known two-word city/metro prefixes in NBA, NHL, NCAAB
_MULTI_WORD_CITIES = {
    "golden state", "new orleans", "new york", "oklahoma city",
    "san antonio", "los angeles", "las vegas", "salt lake",
    "tampa bay", "kansas city", "san francisco", "san jose",
    "st. louis", "st louis", "new england", "new jersey",
}

# ── City → nickname mapping ───────────────────────────────────────────────────
# Polymarket.us title field is city-only ("Memphis", "Golden State", "Los Angeles C").
# Maps lowercase PM title → list of possible team nicknames (priority order).
# Sport context disambiguates: caller tries each candidate against the odds lookup
# dict and uses the first match, so "Boston" picks Celtics in NBA context, Bruins
# in NHL context.
_CITY_TO_NICKNAMES: Dict[str, List[str]] = {
    # ── NBA ──────────────────────────────────────────────────────────────────
    "atlanta": ["hawks"],
    "boston": ["celtics", "bruins"],       # NBA: Celtics | NHL: Bruins
    "brooklyn": ["nets"],
    "charlotte": ["hornets"],
    "chicago": ["bulls", "blackhawks"],    # NBA: Bulls | NHL: Blackhawks
    "cleveland": ["cavaliers"],
    "dallas": ["mavericks", "stars"],      # NBA: Mavs | NHL: Stars
    "denver": ["nuggets", "avalanche"],    # NBA: Nuggets | NHL: Avalanche
    "detroit": ["pistons", "red wings"],
    "golden state": ["warriors"],
    "houston": ["rockets"],
    "indiana": ["pacers"],
    "la lakers": ["lakers"],               # PM abbreviation form
    "la clippers": ["clippers"],
    "los angeles l": ["lakers"],           # PM truncated form ("Los Angeles L")
    "los angeles c": ["clippers"],         # PM truncated form ("Los Angeles C")
    "los angeles": ["lakers", "clippers", "kings"],  # ambiguous — resolved via odds lookup
    "memphis": ["grizzlies"],
    "miami": ["heat"],
    "milwaukee": ["bucks"],
    "minnesota": ["timberwolves", "wild"],
    "new orleans": ["pelicans"],
    "new york": ["knicks", "rangers", "islanders"],
    "oklahoma city": ["thunder"],
    "orlando": ["magic"],
    "philadelphia": ["76ers", "sixers", "flyers"],
    "phoenix": ["suns", "coyotes"],
    "portland": ["trail blazers"],
    "sacramento": ["kings"],
    "san antonio": ["spurs"],
    "toronto": ["raptors", "maple leafs"],
    "utah": ["jazz", "hockey club"],
    "washington": ["wizards", "capitals"],
    # ── NHL (not already covered above) ──────────────────────────────────────
    "anaheim": ["ducks"],
    "buffalo": ["sabres"],
    "calgary": ["flames"],
    "carolina": ["hurricanes"],
    "colorado": ["avalanche", "nuggets"],
    "columbus": ["blue jackets"],
    "edmonton": ["oilers"],
    "florida": ["panthers"],
    "las vegas": ["golden knights"],
    "vegas": ["golden knights"],
    "montreal": ["canadiens"],
    "nashville": ["predators"],
    "new jersey": ["devils"],
    "ottawa": ["senators"],
    "pittsburgh": ["penguins"],
    "san jose": ["sharks"],
    "seattle": ["kraken"],
    "st. louis": ["blues"],
    "st louis": ["blues"],
    "tampa bay": ["lightning"],
    "vancouver": ["canucks"],
    "winnipeg": ["jets"],
    # ── NCAAB common tournament teams ────────────────────────────────────────
    "connecticut": ["huskies"],
    "uconn": ["huskies"],
    "gonzaga": ["bulldogs"],
    "kansas": ["jayhawks"],
    "kentucky": ["wildcats"],
    "duke": ["blue devils"],
    "north carolina": ["tar heels"],
    "michigan": ["wolverines"],
    "michigan state": ["spartans"],
    "villanova": ["wildcats"],
    "arizona": ["wildcats"],
    "iowa": ["hawkeyes"],
    "iowa state": ["cyclones"],
    "purdue": ["boilermakers"],
    "tennessee": ["volunteers"],
    "alabama": ["crimson tide"],
    "baylor": ["bears"],
    "arkansas": ["razorbacks"],
    "creighton": ["bluejays"],
    "san diego state": ["aztecs"],
    "florida state": ["seminoles"],
    "auburn": ["tigers"],
    "south carolina": ["gamecocks"],
    "ohio state": ["buckeyes"],
    "virginia": ["cavaliers"],
    "oregon": ["ducks"],
}

# Standard sport abbreviations (ESPN/Polymarket) → nickname
_ABBREV_TO_NICKNAME: Dict[str, str] = {
    # NBA
    "atl": "hawks",    "bos": "celtics",   "bkn": "nets",     "cha": "hornets",
    "chi": "bulls",    "cle": "cavaliers", "dal": "mavericks", "den": "nuggets",
    "det": "pistons",  "gsw": "warriors",  "hou": "rockets",   "ind": "pacers",
    "lac": "clippers", "lal": "lakers",    "mem": "grizzlies", "mia": "heat",
    "mil": "bucks",    "min": "timberwolves", "nop": "pelicans", "nyk": "knicks",
    "okc": "thunder",  "orl": "magic",     "phi": "76ers",     "phx": "suns",
    "por": "trail blazers", "sac": "kings", "sas": "spurs",   "tor": "raptors",
    "uta": "jazz",     "was": "wizards",
    # NHL
    "ana": "ducks",    "buf": "sabres",    "cgy": "flames",    "car": "hurricanes",
    "cbj": "blue jackets", "col": "avalanche", "dal": "stars", "det": "red wings",
    "edm": "oilers",   "fla": "panthers",  "lak": "kings",     "mtl": "canadiens",
    "nsh": "predators", "njd": "devils",   "nyi": "islanders", "nyr": "rangers",
    "ott": "senators", "pit": "penguins",  "sjs": "sharks",    "sea": "kraken",
    "stl": "blues",    "tbl": "lightning", "tor": "maple leafs", "van": "canucks",
    "vgk": "golden knights", "wpg": "jets", "wsh": "capitals",
}


def _extract_identifier_abbrev(identifier: str) -> str:
    """
    Extract the team abbreviation/slug from a Polymarket side identifier.

    Example: "nba-champion-2026-mem-yes" → "mem"
             "nba-champion-2026-thunder-yes" → "thunder"
    Pattern: strip "-yes" / "-no" suffix, return last hyphen segment.
    """
    ident = identifier.lower().strip()
    for suffix in ("-yes", "-no"):
        if ident.endswith(suffix):
            ident = ident[: -len(suffix)]
            break
    parts = ident.split("-")
    return parts[-1] if parts else ""


def _get_pm_team_nickname(
    title: str, identifier: str, odds_by_name: Dict[str, Any]
) -> str:
    """
    Resolve a Polymarket team title to a matchable nickname key.

    PM market titles are often city-only ("Memphis") instead of full names
    ("Memphis Grizzlies").  Uses a multi-stage fallback:

      Stage 1: normalize_team_name(title) — works for full names and bare nicknames
               ("Thunder", "Oklahoma City Thunder" → "thunder")
      Stage 2: City → nickname map — for city-only titles ("Memphis" → "grizzlies").
               Tries every candidate in priority order; returns first found in odds.
               Sport context disambiguates: "Boston" picks "celtics" in NBA context
               (where odds has "celtics" but not "bruins") and vice-versa for NHL.
      Stage 3: Abbreviation from identifier slug — "mem" → "grizzlies" as last resort.

    Returns the best matching key, or normalized title if nothing found (signal
    will be silently skipped by the caller's odds lookup).
    """
    # Stage 1: direct normalize — works for nickname titles and full names
    normalized = normalize_team_name(title)
    if normalized in odds_by_name:
        return normalized

    # Stage 2: city map lookup
    title_lower = title.strip().lower()
    candidates = _CITY_TO_NICKNAMES.get(title_lower, [])
    for candidate in candidates:
        if candidate in odds_by_name:
            return candidate

    # Stage 3: abbreviation extracted from identifier slug
    abbrev = _extract_identifier_abbrev(identifier)
    if abbrev:
        nickname = _ABBREV_TO_NICKNAME.get(abbrev)
        if nickname and nickname in odds_by_name:
            return nickname

    # Fall through — return normalized; caller's odds.get() will miss, logged as debug
    return normalized


def normalize_team_name(name: str) -> str:
    """
    Strip city/state prefix from a team name and return lowercase nickname.

    Examples:
      "Oklahoma City Thunder"  → "thunder"
      "Portland Trail Blazers" → "trail blazers"
      "Boston Celtics"         → "celtics"
      "Thunder"                → "thunder"
      "Philadelphia 76ers"     → "76ers"
      "76ers"                  → "76ers"
    """
    name_lower = name.strip().lower()

    # Check known two-word city prefixes first
    for prefix in _MULTI_WORD_CITIES:
        if name_lower.startswith(prefix + " "):
            return name_lower[len(prefix):].strip()

    # Strip single first word (single-word city like "Boston", "Denver", etc.)
    words = name_lower.split()
    if len(words) > 1:
        return " ".join(words[1:])

    return name_lower


class SportsFuturesStrategy:
    """
    Compare Polymarket.us futures prices to sharp bookmaker consensus.

    Signals when the gap between PM implied probability and sports feed
    consensus exceeds min_edge_pct (default 5%).

    Paper-only until POST /v1/orders protobuf format is confirmed.
    """

    def __init__(self, min_edge_pct: float = 0.05, min_books: int = 2):
        self._min_edge_pct = min_edge_pct
        self._min_books = min_books

    @property
    def name(self) -> str:
        return "sports_futures_v1"

    def scan_for_signals(
        self,
        pm_markets: List[PolymarketMarket],
        odds: List[ChampionshipOdds],
    ) -> List[Signal]:
        """
        Compare PM futures prices to sports feed consensus and emit signals.

        Args:
            pm_markets: Open Polymarket.us futures markets (from PolymarketClient.get_markets)
            odds:       Championship odds from SportsFeed.get_nba/nhl/ncaab_championship

        Returns:
            List of Signal objects (may be empty). Never raises.
        """
        # Build lookup: normalized_name → ChampionshipOdds
        odds_by_name: dict[str, ChampionshipOdds] = {
            normalize_team_name(o.team_name): o for o in odds
        }

        signals: List[Signal] = []
        for market in pm_markets:
            if market.closed or not market.active:
                continue

            # PM .us title field is often city-only ("Memphis", "Golden State").
            # _get_pm_team_nickname resolves it to the canonical nickname via a
            # multi-stage fallback (normalize → city map → identifier abbreviation).
            team_title = market.raw.get("title", "") or market.question
            normalized = _get_pm_team_nickname(
                team_title, market.yes_identifier, odds_by_name
            )

            o = odds_by_name.get(normalized)
            if o is None:
                logger.debug(
                    "[sports_futures] No odds match for PM market %r (normalized=%r)",
                    team_title, normalized,
                )
                continue

            if o.num_books < self._min_books:
                logger.debug(
                    "[sports_futures] Skipping %r — only %d book(s), min_books=%d",
                    team_title, o.num_books, self._min_books,
                )
                continue

            pm_price = market.yes_price
            odds_prob = o.implied_prob
            edge = odds_prob - pm_price

            if edge >= self._min_edge_pct:
                # PM is underpriced → BUY YES
                try:
                    signals.append(Signal(
                        side="yes",
                        edge_pct=round(edge, 4),
                        win_prob=odds_prob,
                        confidence=min(o.num_books / 3.0, 1.0),
                        ticker=market.yes_identifier,
                        price_cents=market.yes_price_cents,
                        reason=(
                            f"{team_title}: PM {pm_price:.3f} vs odds {odds_prob:.3f} "
                            f"({edge:.1%} YES edge, {o.num_books} books)"
                        ),
                    ))
                    logger.info(
                        "[sports_futures] YES signal: %s PM=%.3f odds=%.3f edge=%.1f%%",
                        team_title, pm_price, odds_prob, edge * 100,
                    )
                except ValueError as exc:
                    logger.warning("[sports_futures] Invalid YES signal for %s: %s", team_title, exc)

            elif (-edge) >= self._min_edge_pct:
                # PM is overpriced → BUY NO
                no_edge = pm_price - odds_prob
                try:
                    signals.append(Signal(
                        side="no",
                        edge_pct=round(no_edge, 4),
                        win_prob=1.0 - odds_prob,
                        confidence=min(o.num_books / 3.0, 1.0),
                        ticker=market.no_identifier,
                        price_cents=market.no_price_cents,
                        reason=(
                            f"{team_title}: PM {pm_price:.3f} vs odds {odds_prob:.3f} "
                            f"({no_edge:.1%} NO edge, {o.num_books} books)"
                        ),
                    ))
                    logger.info(
                        "[sports_futures] NO signal: %s PM=%.3f odds=%.3f edge=%.1f%%",
                        team_title, pm_price, odds_prob, no_edge * 100,
                    )
                except ValueError as exc:
                    logger.warning("[sports_futures] Invalid NO signal for %s: %s", team_title, exc)

        return signals
