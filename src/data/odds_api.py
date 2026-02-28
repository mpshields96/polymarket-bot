"""
JOB:    Fetch NBA + NHL moneyline odds from The-Odds-API (v4).
        Returns consensus implied probability per team per game.

USAGE:
    feed = OddsAPIFeed.load_from_env()
    games = await feed.get_nba_games()   # list[OddsGame]
    games = await feed.get_nhl_games()

RATE:   1 request per call (1 request costs 1 credit per region×market).
        At 1 call per 15 min: ~96 calls/day × 31 days = ~3,000/month.
        Budget: 5% of 20,000 = 1,000 credits/month → limit to 1 call/30min max.
        Cache TTL: 900s (15 min). Shared between NBA + NHL to minimise calls.

KEYS:   ODDS_API_KEY in .env
        Endpoint: https://api.the-odds-api.com/v4/sports/{sport}/odds/
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_BASE = "https://api.the-odds-api.com/v4/sports"

# Preferred bookmakers in priority order (sharpest lines first)
_PREFERRED_BOOKS = ["pinnacle", "draftkings", "fanduel", "betmgm", "caesars", "pointsbet"]


@dataclass
class OddsGame:
    """A single game with consensus moneyline odds."""
    sport: str                  # "basketball_nba" or "icehockey_nhl"
    game_id: str                # Odds API event ID
    home_team: str              # Full name, e.g. "Miami Heat"
    away_team: str              # Full name, e.g. "Houston Rockets"
    commence_time: str          # ISO8601 UTC — when the game starts (market closes)
    home_prob: float            # Consensus implied prob, vig-removed
    away_prob: float            # Consensus implied prob, vig-removed
    num_books: int = 0          # How many books contributed to consensus
    raw_home_odds: float = 0.0  # Decimal odds (best available)
    raw_away_odds: float = 0.0


@dataclass
class OddsAPIFeed:
    api_key: str
    cache_ttl_sec: int = 900    # 15 min cache

    _cache: Dict[str, tuple] = field(default_factory=dict, repr=False)  # sport → (games, ts)

    # ── Public API ──────────────────────────────────────────────────

    async def get_nba_games(self) -> List[OddsGame]:
        return await self._fetch("basketball_nba")

    async def get_nhl_games(self) -> List[OddsGame]:
        return await self._fetch("icehockey_nhl")

    # ── Internal ────────────────────────────────────────────────────

    async def _fetch(self, sport: str) -> List[OddsGame]:
        """Fetch odds with cache. Returns [] on API error."""
        cached = self._cache.get(sport)
        if cached and (time.monotonic() - cached[1]) < self.cache_ttl_sec:
            logger.debug("[odds_api] Cache hit for %s (%ds old)", sport,
                         int(time.monotonic() - cached[1]))
            return cached[0]

        url = f"{_BASE}/{sport}/odds/"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "decimal",
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    remaining = resp.headers.get("x-requests-remaining", "?")
                    used = resp.headers.get("x-requests-used", "?")
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning("[odds_api] HTTP %d for %s: %s", resp.status, sport, body[:200])
                        return []
                    data = await resp.json()
                    logger.info("[odds_api] %s: %d games fetched (quota used=%s remaining=%s)",
                                sport, len(data), used, remaining)
        except Exception as exc:
            logger.warning("[odds_api] Fetch error for %s: %s", sport, exc)
            return []

        games = [g for g in (_parse_game(sport, raw) for raw in data) if g is not None]
        self._cache[sport] = (games, time.monotonic())
        return games

    # ── Factory ─────────────────────────────────────────────────────

    @classmethod
    def load_from_env(cls) -> "OddsAPIFeed":
        api_key = os.getenv("ODDS_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                "ODDS_API_KEY not set in .env. "
                "Get one at https://the-odds-api.com — add ODDS_API_KEY=<key> to .env"
            )
        return cls(api_key=api_key)


# ── Parsing helpers ──────────────────────────────────────────────────────────

def _american_to_decimal(american: float) -> float:
    if american > 0:
        return 1.0 + american / 100.0
    return 1.0 + 100.0 / abs(american)


def _decimal_to_implied(decimal: float) -> float:
    """Raw implied probability (includes vig)."""
    if decimal <= 1.0:
        return 0.0
    return 1.0 / decimal


def _remove_vig(home_raw: float, away_raw: float) -> tuple[float, float]:
    """Normalise two implied probs so they sum to 1.0."""
    total = home_raw + away_raw
    if total <= 0:
        return 0.5, 0.5
    return home_raw / total, away_raw / total


def _parse_game(sport: str, raw: dict) -> Optional[OddsGame]:
    home = raw.get("home_team", "")
    away = raw.get("away_team", "")
    if not home or not away:
        return None

    bookmakers = raw.get("bookmakers", [])
    if not bookmakers:
        return None

    # Collect h2h outcomes from as many books as possible
    home_probs, away_probs = [], []
    home_decimal, away_decimal = 0.0, 0.0

    # Sort books by preference
    def _book_rank(b: dict) -> int:
        key = b.get("key", "")
        try:
            return _PREFERRED_BOOKS.index(key)
        except ValueError:
            return 999

    for bm in sorted(bookmakers, key=_book_rank):
        for mkt in bm.get("markets", []):
            if mkt.get("key") != "h2h":
                continue
            outcomes = {o["name"]: o["price"] for o in mkt.get("outcomes", [])}
            h_dec = outcomes.get(home, 0.0)
            a_dec = outcomes.get(away, 0.0)
            if h_dec <= 1.0 or a_dec <= 1.0:
                continue
            h_imp = _decimal_to_implied(h_dec)
            a_imp = _decimal_to_implied(a_dec)
            h_norm, a_norm = _remove_vig(h_imp, a_imp)
            home_probs.append(h_norm)
            away_probs.append(a_norm)
            if home_decimal == 0.0:   # take best book's decimal for reference
                home_decimal = h_dec
                away_decimal = a_dec

    if not home_probs:
        return None

    consensus_home = sum(home_probs) / len(home_probs)
    consensus_away = sum(away_probs) / len(away_probs)

    return OddsGame(
        sport=sport,
        game_id=raw.get("id", ""),
        home_team=home,
        away_team=away,
        commence_time=raw.get("commence_time", ""),
        home_prob=round(consensus_home, 4),
        away_prob=round(consensus_away, 4),
        num_books=len(home_probs),
        raw_home_odds=home_decimal,
        raw_away_odds=away_decimal,
    )
