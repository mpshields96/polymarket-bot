"""
JOB:    Fetch NBA + NHL moneyline odds AND championship futures from the sports data feed (v4).
        Returns consensus implied probability per team per game (h2h) and
        per team per championship season (outrights/futures).

USAGE:
    feed = SportsFeed.load_from_env()
    games = await feed.get_nba_games()           # list[OddsGame]  — h2h moneylines
    games = await feed.get_nhl_games()
    champ = await feed.get_nba_championship()    # list[ChampionshipOdds] — season winners
    champ = await feed.get_nhl_championship()
    champ = await feed.get_ncaab_championship()

RATE:   h2h games: ~1 credit/call.
        Championship outrights: ~1 credit per bookmaker per event.
        Budget: hard cap 4000 credits/month for this bot (sub limit 20K/month).
        Cache TTL: 900s (15 min) for games, 21,600s (6 hr) for championships.

KEYS:   SDATA_KEY in .env
        Quota persisted to data/sdata_quota.json — hard block at 4000 credits/month.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_BASE = "https://api.the-odds-api.com/v4/sports"
_MONTHLY_CREDIT_CAP = 4000         # raised S123 — Matthew directive (sub limit 20K/month)
_QUOTA_FILE = "data/sdata_quota.json"

# Preferred bookmakers in priority order (sharpest lines first)
_PREFERRED_BOOKS = ["pinnacle", "draftkings", "fanduel", "betmgm", "caesars", "pointsbet"]


# ── Quota guard ──────────────────────────────────────────────────────────────

class _QuotaGuard:
    """
    Tracks monthly credits used against a hard cap.
    Persists state to a local JSON file so restarts don't reset the counter.
    """

    def __init__(self, path: str = _QUOTA_FILE, cap: int = _MONTHLY_CREDIT_CAP) -> None:
        self._path = path
        self._cap = cap

    def _load(self) -> dict:
        try:
            with open(self._path) as f:
                return json.load(f)
        except Exception:
            return {"year": 0, "month": 0, "used": 0}

    def _save(self, data: dict) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning("[sdata] Could not write quota file: %s", e)

    def check(self) -> bool:
        """Returns True if a call is allowed (credits remaining)."""
        now = datetime.now(timezone.utc)
        data = self._load()
        if data["year"] != now.year or data["month"] != now.month:
            return True  # new month — reset
        used = data.get("used", 0)
        if used >= self._cap:
            logger.error(
                "[sdata] Monthly credit cap reached (%d/%d) — feed disabled until next month",
                used, self._cap,
            )
            return False
        return True

    def update(self, used_header: str) -> None:
        """Update from x-requests-used response header value."""
        try:
            used = int(used_header)
        except (ValueError, TypeError):
            return
        now = datetime.now(timezone.utc)
        data = self._load()
        if data["year"] != now.year or data["month"] != now.month:
            data = {"year": now.year, "month": now.month, "used": 0}
        # use max in case of concurrent calls — never decrease the counter
        data["used"] = max(data.get("used", 0), used)
        if data["used"] >= self._cap:
            logger.warning(
                "[sdata] Monthly credit cap hit (%d/%d) — no further calls this month",
                data["used"], self._cap,
            )
        self._save(data)

    def status(self) -> str:
        now = datetime.now(timezone.utc)
        data = self._load()
        if data["year"] != now.year or data["month"] != now.month:
            return f"0/{self._cap} (new month)"
        return f"{data.get('used', 0)}/{self._cap}"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class OddsGame:
    """A single game with consensus moneyline odds."""
    sport: str                  # "basketball_nba" or "icehockey_nhl"
    game_id: str                # event ID from feed
    home_team: str              # Full name, e.g. "Miami Heat"
    away_team: str              # Full name, e.g. "Houston Rockets"
    commence_time: str          # ISO8601 UTC — when the game starts (market closes)
    home_prob: float            # Consensus implied prob, vig-removed
    away_prob: float            # Consensus implied prob, vig-removed
    num_books: int = 0          # How many books contributed to consensus
    raw_home_odds: float = 0.0  # Decimal odds (best available)
    raw_away_odds: float = 0.0


@dataclass
class ChampionshipOdds:
    """
    Consensus championship odds for one team (outrights/futures market).

    implied_prob is vig-removed consensus across all available sharp bookmakers.
    decimal_odds is the best available (Pinnacle-preferred) decimal price.
    """

    team_name: str      # raw team name from feed, e.g. "Oklahoma City Thunder"
    decimal_odds: float # best available decimal odds (Pinnacle preferred)
    implied_prob: float # vig-removed consensus probability (0.0-1.0)
    num_books: int      # how many books contributed to consensus

    @classmethod
    def from_event(cls, event: dict) -> list["ChampionshipOdds"]:
        """
        Parse all teams from one outright event.

        Returns a list of ChampionshipOdds (one per team found in bookmakers).
        Returns [] if no bookmakers or no outrights market found.
        """
        bookmakers = event.get("bookmakers") or []
        if not bookmakers:
            return []

        team_decimals: dict[str, list[float]] = {}
        best_decimal: dict[str, float] = {}

        def _book_rank(b: dict) -> int:
            key = b.get("key", "")
            try:
                return _PREFERRED_BOOKS.index(key)
            except ValueError:
                return 999

        for bm in sorted(bookmakers, key=_book_rank):
            for mkt in bm.get("markets", []):
                if mkt.get("key") != "outrights":
                    continue
                for outcome in mkt.get("outcomes", []):
                    name = outcome.get("name", "")
                    price = float(outcome.get("price", 0.0))
                    if price <= 1.0 or not name:
                        continue
                    if name not in team_decimals:
                        team_decimals[name] = []
                        best_decimal[name] = price
                    team_decimals[name].append(price)

        if not team_decimals:
            return []

        result = []
        for team, decimals in team_decimals.items():
            raw_probs = [1.0 / d for d in decimals if d > 1.0]
            if not raw_probs:
                continue
            avg_prob = sum(raw_probs) / len(raw_probs)
            result.append(cls(
                team_name=team,
                decimal_odds=best_decimal[team],
                implied_prob=round(avg_prob, 4),
                num_books=len(raw_probs),
            ))

        return result


# ── Main feed class ──────────────────────────────────────────────────────────

@dataclass
class SportsFeed:
    """
    Sports data feed client with monthly quota enforcement.

    Loads API key from SDATA_KEY in .env.
    Hard blocks at _MONTHLY_CREDIT_CAP credits/month — no calls after cap is hit.
    """
    api_key: str
    cache_ttl_sec: int = 900    # 15 min cache

    _cache: Dict[str, tuple] = field(default_factory=dict, repr=False)
    _quota: _QuotaGuard = field(default_factory=_QuotaGuard, repr=False)

    # ── Public API ──────────────────────────────────────────────────

    async def get_nba_games(self) -> List[OddsGame]:
        return await self._fetch("basketball_nba")

    async def get_nhl_games(self) -> List[OddsGame]:
        return await self._fetch("icehockey_nhl")

    # ── Championship futures ─────────────────────────────────────────

    async def get_nba_championship(self) -> List[ChampionshipOdds]:
        """NBA Championship Winner — season-long futures odds."""
        return await self._fetch_outrights("basketball_nba_championship_winner")

    async def get_nhl_championship(self) -> List[ChampionshipOdds]:
        """NHL Stanley Cup Champion — season-long futures odds."""
        return await self._fetch_outrights("icehockey_nhl_championship_winner")

    async def get_ncaab_championship(self) -> List[ChampionshipOdds]:
        """NCAAB Tournament Winner — March Madness futures odds."""
        return await self._fetch_outrights("basketball_ncaab_championship_winner")

    def quota_status(self) -> str:
        """Returns current monthly credit usage, e.g. '12/4000'."""
        return self._quota.status()

    # ── Internal ────────────────────────────────────────────────────

    async def _fetch_outrights(self, sport: str) -> List[ChampionshipOdds]:
        """Fetch championship/outright odds with a 6-hour cache. Returns [] on any error."""
        if not self._quota.check():
            return []

        cache_key = f"outrights_{sport}"
        cached = self._cache.get(cache_key)
        _CHAMPIONSHIP_CACHE_TTL = 21_600  # 6 hours
        if cached and (time.monotonic() - cached[1]) < _CHAMPIONSHIP_CACHE_TTL:
            logger.debug("[sdata] Cache hit for outrights %s", sport)
            return cached[0]

        url = f"{_BASE}/{sport}/odds/"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "outrights",
            "oddsFormat": "decimal",
            "bookmakers": ",".join(_PREFERRED_BOOKS[:3]),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    remaining = resp.headers.get("x-requests-remaining", "?")
                    used = resp.headers.get("x-requests-used", "?")
                    self._quota.update(str(used))
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning("[sdata] HTTP %d for outrights %s: %s",
                                       resp.status, sport, body[:200])
                        return []
                    data = await resp.json()
                    logger.info("[sdata] outrights %s: %d events (used=%s remaining=%s)",
                                sport, len(data), used, remaining)
        except Exception as exc:
            logger.warning("[sdata] Outrights fetch error for %s: %s", sport, exc)
            return []

        all_odds: List[ChampionshipOdds] = []
        for event in data:
            all_odds.extend(ChampionshipOdds.from_event(event))

        self._cache[cache_key] = (all_odds, time.monotonic())
        return all_odds

    async def _fetch(self, sport: str) -> List[OddsGame]:
        """Fetch odds with cache. Returns [] on API error or quota exhaustion."""
        if not self._quota.check():
            return []

        cached = self._cache.get(sport)
        if cached and (time.monotonic() - cached[1]) < self.cache_ttl_sec:
            logger.debug("[sdata] Cache hit for %s (%ds old)", sport,
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
                async with session.get(url, params=params,
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    remaining = resp.headers.get("x-requests-remaining", "?")
                    used = resp.headers.get("x-requests-used", "?")
                    self._quota.update(str(used))
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning("[sdata] HTTP %d for %s: %s", resp.status, sport, body[:200])
                        return []
                    data = await resp.json()
                    logger.info("[sdata] %s: %d games fetched (used=%s remaining=%s)",
                                sport, len(data), used, remaining)
        except Exception as exc:
            logger.warning("[sdata] Fetch error for %s: %s", sport, exc)
            return []

        games = [g for g in (_parse_game(sport, raw) for raw in data) if g is not None]
        self._cache[sport] = (games, time.monotonic())
        return games

    # ── Factory ─────────────────────────────────────────────────────

    @classmethod
    def load_from_env(cls) -> "SportsFeed":
        api_key = os.getenv("SDATA_KEY", "")
        if not api_key:
            raise RuntimeError(
                "SDATA_KEY not set in .env — sports data feed disabled"
            )
        return cls(api_key=api_key)


# Backwards-compatible alias — existing imports of OddsAPIFeed still work
OddsAPIFeed = SportsFeed


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

    home_probs, away_probs = [], []
    home_decimal, away_decimal = 0.0, 0.0

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
            if home_decimal == 0.0:
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
