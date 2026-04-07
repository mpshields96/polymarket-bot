"""
src/data/kalshi_series_discovery.py — Dynamic Kalshi Series Discovery
======================================================================
JOB:    Replace hardcoded series dicts across the bot with a single module
        that can discover, classify, and map ALL Kalshi series.

PRIMARY INTERFACE:
    discovery = KalshiSeriesDiscovery(client)
    all_open  = await discovery.get_all_open_markets(min_volume=100)
    # {series_prefix: [Market, ...]} — ready for strategy loops

    cat       = discovery.classify_series("KXNBAGAME", "NBA Game")
    # SeriesCategory.SPORTS

    key       = discovery.get_odds_api_key("KXNBAGAME")
    # "basketball_nba"

DESIGN NOTES:
    - Wraps existing client._get("/series") pagination (same as audit_all_kalshi_markets.py)
    - No new API dependencies; no Odds API credits consumed
    - All mapping tables are pure-Python dicts — zero I/O
    - Async: use await for any method that hits the Kalshi API
    - Classifiers and mappers are sync (pure computation)

ODDS API MAPPING:
    Confirmed (from edge_scanner.py + kalshi_series_scout.py):
      KXNBAGAME          → basketball_nba
      KXNHLGAME          → icehockey_nhl
      KXMLBGAME          → baseball_mlb
      KXNCAABGAME        → basketball_ncaab
      KXNCAAMBGAME       → basketball_ncaab   (alias — same sport)
      KXUCLGAME          → soccer_uefa_champions_league
      KXEPLGAME          → soccer_epl
      KXBUNDESLIGAGAME   → soccer_germany_bundesliga
      KXSERIEAGAME       → soccer_italy_serie_a
      KXLALIGAGAME       → soccer_spain_la_liga
      KXLIGUE1GAME       → soccer_france_ligue_one

    Unverified (series existence not confirmed on Kalshi):
      KXNFLGAME          → americanfootball_nfl      (not confirmed)
      KXNCAAFGAME        → americanfootball_ncaaf    (not confirmed)
      KXMLSGAME          → soccer_usa_mls            (not confirmed)
      KXATPGAME          → tennis_atp                (not confirmed)
      KXWTAGAME          → tennis_wta                (not confirmed)

    No Odds API equivalent (non-game markets):
      KXCPI / KXGDP / KXFED / KXUNRATE / KXSENATE* / KXGOV* → None

SERIES CATEGORIES:
    SPORTS      — game-outcome markets (NBA/NHL/MLB/UCL/etc.)
    ECONOMICS   — macro data releases (CPI/GDP/FOMC/unemployment)
    POLITICS    — elections, legislation, polls
    CULTURE     — entertainment, awards, pop culture
    CRYPTO      — BTC/ETH/SOL/XRP price markets
    OTHER       — anything else
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from src.platforms.kalshi import KalshiClient, Market

logger = logging.getLogger(__name__)


# ── Series category enum ─────────────────────────────────────────────────────

class SeriesCategory(str, Enum):
    SPORTS    = "sports"
    ECONOMICS = "economics"
    POLITICS  = "politics"
    CULTURE   = "culture"
    CRYPTO    = "crypto"
    OTHER     = "other"


# ── SeriesInfo dataclass ─────────────────────────────────────────────────────

@dataclass
class SeriesInfo:
    ticker: str
    title: str
    category: SeriesCategory
    volume: int = 0
    tags: list = field(default_factory=list)
    frequency: str = ""
    odds_api_key: Optional[str] = None     # set if mappable to Odds API

    @property
    def is_game_market(self) -> bool:
        return self.category == SeriesCategory.SPORTS

    @property
    def has_odds_api_coverage(self) -> bool:
        return self.odds_api_key is not None


# ── Odds API sport key mapping ────────────────────────────────────────────────
# Maps Kalshi series prefix → the-odds-api sport key.
# None = no Odds API equivalent (use alternative signal or skip).
# "UNVERIFIED" entries: mapping is plausible but series existence not confirmed.

_ODDS_API_MAP: dict[str, Optional[str]] = {
    # ── Sports (confirmed) ──────────────────────────────────────────────────
    "KXNBAGAME":          "basketball_nba",
    "KXNHLGAME":          "icehockey_nhl",
    "KXMLBGAME":          "baseball_mlb",
    "KXNCAABGAME":        "basketball_ncaab",
    "KXNCAAMBGAME":       "basketball_ncaab",    # alternate ticker (same sport)
    "KXUCLGAME":          "soccer_uefa_champions_league",
    "KXEPLGAME":          "soccer_epl",
    "KXBUNDESLIGAGAME":   "soccer_germany_bundesliga",
    "KXSERIEAGAME":       "soccer_italy_serie_a",
    "KXLALIGAGAME":       "soccer_spain_la_liga",
    "KXLIGUE1GAME":       "soccer_france_ligue_one",
    "KXUFCFIGHT":         "mma_mixed_martial_arts",

    # ── Sports (unverified — series may not exist on Kalshi yet) ───────────
    "KXNFLGAME":          "americanfootball_nfl",      # not confirmed
    "KXNCAAFGAME":        "americanfootball_ncaaf",    # not confirmed
    "KXMLSGAME":          "soccer_usa_mls",            # not confirmed
    "KXATPGAME":          "tennis_atp",                # not confirmed
    "KXWTAGAME":          "tennis_wta",                # not confirmed

    # ── Economics / politics / crypto — no Odds API equivalent ───────────
    "KXBTCD":             None,
    "KXETHD":             None,
    "KXBTC15M":           None,
    "KXETH15M":           None,
    "KXSOL15M":           None,
    "KXXRP15M":           None,
    "KXCPI":              None,
    "KXGDP":              None,
    "KXFED":              None,
    "KXUNRATE":           None,
}

# Suffixes that indicate game-outcome sports markets
_GAME_SUFFIXES = ("GAME", "FIGHT", "MATCH", "BOUT")

# Known economics series prefixes
_ECONOMICS_PREFIXES = ("KXCPI", "KXGDP", "KXFED", "KXFOMC", "KXUNRATE",
                       "KXPCE", "KXPPI", "KXNFP", "KXHOUSING")

# Known crypto series prefixes
_CRYPTO_PREFIXES = ("KXBTC", "KXETH", "KXSOL", "KXXRP", "KXDOGE",
                    "KXBNB", "KXADA", "KXAVAX", "KXLINK")

# Known politics keywords (case-insensitive match against title)
_POLITICS_KEYWORDS = ("election", "senate", "house", "congress", "president",
                      "governor", "ballot", "vote", "poll", "party", "democrat",
                      "republican", "legislation", "bill", "supreme court")

# Known culture keywords
_CULTURE_KEYWORDS = ("oscar", "emmy", "grammy", "golden globe", "award",
                     "box office", "album", "movie", "tv show", "celebrity",
                     "super bowl halftime", "reality", "entertainment")


def classify_series(ticker: str, title: str = "") -> SeriesCategory:
    """
    Classify a Kalshi series into a category based on ticker + title.

    Args:
        ticker: Kalshi series ticker (e.g. "KXNBAGAME", "KXCPI").
        title: Series title string (used for culture/politics disambiguation).

    Returns:
        SeriesCategory enum value.
    """
    t = ticker.upper()
    tl = title.lower()

    # Crypto: known prefixes
    for prefix in _CRYPTO_PREFIXES:
        if t.startswith(prefix):
            return SeriesCategory.CRYPTO

    # Economics: known prefixes
    for prefix in _ECONOMICS_PREFIXES:
        if t.startswith(prefix):
            return SeriesCategory.ECONOMICS

    # Sports: game suffix
    for suffix in _GAME_SUFFIXES:
        if t.endswith(suffix) or (f"{suffix}-" in t) or (f"{suffix}_" in t):
            return SeriesCategory.SPORTS

    # Sports: common sport prefixes
    sport_prefixes = ("KXNBA", "KXNHL", "KXMLB", "KXNFL", "KXNCAA",
                      "KXUCL", "KXEPL", "KXMLS", "KXATP", "KXWTA",
                      "KXUFC", "KXBUNDESLIGA", "KXSERIEA", "KXLALIGA",
                      "KXLIGUE", "KXCONF")
    for prefix in sport_prefixes:
        if t.startswith(prefix):
            return SeriesCategory.SPORTS

    # Politics: title keyword scan
    for kw in _POLITICS_KEYWORDS:
        if kw in tl:
            return SeriesCategory.POLITICS

    # Culture: title keyword scan
    for kw in _CULTURE_KEYWORDS:
        if kw in tl:
            return SeriesCategory.CULTURE

    # KXSENATE, KXGOV, KXHOUSE, KXPRES pattern
    if any(t.startswith(p) for p in ("KXSENATE", "KXGOV", "KXHOUSE", "KXPRES",
                                      "KXCONGRESS", "KXELECT")):
        return SeriesCategory.POLITICS

    return SeriesCategory.OTHER


def get_odds_api_key(kalshi_series: str) -> Optional[str]:
    """
    Return the the-odds-api sport key for a Kalshi series prefix, or None.

    Performs exact match first, then tries stripping trailing date/variant
    suffixes to match canonical series prefix.

    Args:
        kalshi_series: Kalshi series prefix (e.g. "KXNBAGAME", "KXUCLGAME").

    Returns:
        Odds API sport key string, or None if no mapping exists.
    """
    # Exact match
    key = _ODDS_API_MAP.get(kalshi_series.upper())
    if key is not None or kalshi_series.upper() in _ODDS_API_MAP:
        return key

    # Try stripping trailing digits/year suffix: KXNBAGAME26 → KXNBAGAME
    stripped = kalshi_series.upper().rstrip("0123456789")
    return _ODDS_API_MAP.get(stripped)


def get_all_odds_api_mappings() -> dict[str, str]:
    """
    Return the full dict of Kalshi series prefix → Odds API sport key,
    filtered to only confirmed (non-None) mappings.
    """
    return {k: v for k, v in _ODDS_API_MAP.items() if v is not None}


# ── KalshiSeriesDiscovery ─────────────────────────────────────────────────────

class KalshiSeriesDiscovery:
    """
    Dynamic Kalshi series discovery and classification.

    Wraps the Kalshi /series endpoint to replace hardcoded series dicts
    across the bot. Classification and Odds API mapping are sync; API
    calls are async.

    Usage:
        discovery = KalshiSeriesDiscovery(client)
        all_series = await discovery.get_all_series(min_volume=1000)
        open_markets = await discovery.get_all_open_markets(min_volume=100)
        sports = [s for s in all_series if s.is_game_market]
    """

    def __init__(self, client: "KalshiClient", page_size: int = 200):
        self._client = client
        self._page_size = page_size

    # ── Public async methods ──────────────────────────────────────────────

    async def get_all_series(self, min_volume: int = 0) -> list[SeriesInfo]:
        """
        Fetch all Kalshi series via paginated /series endpoint.

        Args:
            min_volume: Skip series with volume below this threshold.

        Returns:
            List of SeriesInfo objects, sorted by volume descending.
        """
        raw_series = await self._fetch_all_series_raw()
        result = []
        for raw in raw_series:
            ticker = raw.get("ticker", "").upper()
            if not ticker:
                continue
            title = raw.get("title", "")
            vol = int(raw.get("volume", 0) or 0)
            if vol < min_volume:
                continue
            cat = classify_series(ticker, title)
            odds_key = get_odds_api_key(ticker)
            result.append(SeriesInfo(
                ticker=ticker,
                title=title,
                category=cat,
                volume=vol,
                tags=raw.get("tags", []),
                frequency=raw.get("frequency", ""),
                odds_api_key=odds_key,
            ))
        result.sort(key=lambda s: s.volume, reverse=True)
        logger.info(
            "[series_discovery] Fetched %d series (min_volume=%d)",
            len(result), min_volume,
        )
        return result

    async def get_all_open_markets(
        self,
        min_volume: int = 100,
        exclude_crypto: bool = True,
        exclude_banned: bool = True,
    ) -> dict[str, list["Market"]]:
        """
        Fetch open markets for all discovered series, grouped by series prefix.

        Args:
            min_volume: Skip series with total volume below this.
            exclude_crypto: Skip 15-min crypto series (banned per Matthew directive).
            exclude_banned: Skip permanently banned series (KXBTC15M etc.).

        Returns:
            Dict mapping series_prefix → list of open Market objects.
        """
        _BANNED = {"KXBTC15M", "KXETH15M", "KXSOL15M", "KXXRP15M"}
        _CRYPTO_DAILY = {"KXBTCD", "KXETHD"}  # handled by dedicated sniper loops

        all_series = await self.get_all_series(min_volume=min_volume)
        grouped: dict[str, list["Market"]] = {}

        for series in all_series:
            ticker = series.ticker
            if exclude_banned and ticker in _BANNED:
                logger.debug("[series_discovery] Skipping banned series %s", ticker)
                continue
            if exclude_crypto and series.category == SeriesCategory.CRYPTO:
                if ticker not in _CRYPTO_DAILY:  # allow daily crypto (has dedicated loops)
                    logger.debug("[series_discovery] Skipping crypto series %s", ticker)
                    continue

            try:
                markets = await self._client.get_markets(
                    series_ticker=ticker, status="open"
                )
                if markets:
                    grouped[ticker] = markets
                    logger.debug(
                        "[series_discovery] %s: %d open markets", ticker, len(markets)
                    )
            except Exception as exc:
                logger.warning(
                    "[series_discovery] Failed to fetch markets for %s: %s", ticker, exc
                )
                continue

        logger.info(
            "[series_discovery] %d series with open markets (total)",
            len(grouped),
        )
        return grouped

    async def get_sports_markets(
        self,
        min_volume: int = 500,
    ) -> dict[str, list["Market"]]:
        """
        Convenience: return open markets only for SPORTS category series.

        Args:
            min_volume: Volume threshold for including a series.

        Returns:
            Dict mapping sports series prefix → open Market list.
        """
        all_open = await self.get_all_open_markets(min_volume=min_volume)
        return {
            prefix: markets
            for prefix, markets in all_open.items()
            if classify_series(prefix) == SeriesCategory.SPORTS
        }

    async def get_expansion_candidates(
        self,
        min_volume: int = 10_000,
    ) -> list[SeriesInfo]:
        """
        Return series with high volume that are NOT yet covered by any strategy.

        Used for weekly market intelligence scan. Uncovered = no Odds API key
        AND not in the known economics/politics tracking list.

        Args:
            min_volume: Minimum volume to appear as an expansion candidate.

        Returns:
            List of SeriesInfo sorted by volume descending.
        """
        _TRACKED_ECONOMICS = {
            "KXCPI", "KXGDP", "KXFED", "KXUNRATE", "KXFOMC",
        }
        all_series = await self.get_all_series(min_volume=min_volume)
        candidates = []
        for s in all_series:
            if s.has_odds_api_coverage:
                continue  # already covered by sports_game loop
            if s.ticker in _TRACKED_ECONOMICS:
                continue  # already covered by economics sniper
            if s.category == SeriesCategory.CRYPTO:
                continue  # crypto handled separately
            candidates.append(s)
        candidates.sort(key=lambda s: s.volume, reverse=True)
        return candidates

    # ── Private helpers ───────────────────────────────────────────────────

    async def _fetch_all_series_raw(self) -> list[dict]:
        """Paginate /series endpoint and return raw dicts."""
        all_series: list[dict] = []
        cursor: Optional[str] = None
        page = 0
        while True:
            page += 1
            params: dict = {"limit": self._page_size}
            if cursor:
                params["cursor"] = cursor
            try:
                data = await self._client._get("/series", params=params)
            except Exception as exc:
                logger.error(
                    "[series_discovery] /series page %d failed: %s", page, exc
                )
                break
            batch = data.get("series", [])
            all_series.extend(batch)
            cursor = data.get("cursor")
            logger.debug(
                "[series_discovery] /series page %d: %d series (total: %d)",
                page, len(batch), len(all_series),
            )
            if not batch or not cursor:
                break
        return all_series
