"""
Polymarket.us async REST client.

JOB:    All Polymarket.us API calls (markets, orderbook, positions, activities).
        Auth delegation to polymarket_auth.py. Raises PolymarketAPIError on 4xx/5xx.

DOES NOT: Auth logic (delegates to polymarket_auth.py), strategy, risk decisions.

API facts confirmed via live exploration 2026-03-01:
  Base URL:     https://api.polymarket.us
  Version:      /v1
  Auth:         X-PM-Access-Key / X-PM-Timestamp / X-PM-Signature (Ed25519)
  Rate limit:   60 req/min

  Confirmed endpoints:
    GET /v1/markets                          — list markets (sports only as of 2026-03)
    GET /v1/markets?closed=false             — open markets only
    GET /v1/markets/{identifier}/book        — orderbook (bids/asks, 0-1 price scale)
    GET /v1/portfolio/positions              — current holdings
    GET /v1/portfolio/activities             — deposit/trade history
    POST /v1/orders                          — create order (format TBD — no crypto markets yet)

  Price scale: 0.0 – 1.0  (NOT cents like Kalshi — multiply by 100 for Kalshi comparison)
  Market sides: long=True = YES, long=False = NO
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

from src.auth.polymarket_auth import PolymarketAuth, load_from_env as _auth_from_env

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.polymarket.us"
_API_PREFIX = "/v1"


# ── Exceptions ────────────────────────────────────────────────────


class PolymarketAPIError(Exception):
    """Raised when the Polymarket API returns a non-2xx status."""

    def __init__(self, status: int, message: str):
        self.status = status
        super().__init__(f"Polymarket API error {status}: {message}")


# ── Data models ───────────────────────────────────────────────────


@dataclass
class PolymarketMarket:
    """
    A single Polymarket.us market (binary YES/NO).

    Prices are 0.0-1.0 (probability). Use yes_price_cents for Kalshi-style comparison.
    """

    market_id: str
    question: str
    slug: str
    end_date: str
    start_date: str
    category: str
    active: bool
    closed: bool
    market_type: str          # "futures", "binary", etc.
    yes_price: float          # 0.0 – 1.0
    no_price: float           # 0.0 – 1.0
    yes_identifier: str       # slug for the YES side — used in /book endpoint
    no_identifier: str        # slug for the NO side
    tick_size: float          # minimum price increment
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def yes_price_cents(self) -> int:
        """YES price in cents (0-100), for Kalshi-style comparisons."""
        return round(self.yes_price * 100)

    @property
    def no_price_cents(self) -> int:
        """NO price in cents (0-100)."""
        return round(self.no_price * 100)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PolymarketMarket":
        """Parse API response dict into a PolymarketMarket."""
        # Extract YES/NO prices from marketSides if available (most reliable source)
        yes_price = 0.0
        no_price = 0.0
        yes_ident = ""
        no_ident = ""

        sides = d.get("marketSides") or []
        for side in sides:
            price = float(side.get("price", 0))
            ident = side.get("identifier", "")
            if side.get("long", False):
                yes_price = price
                yes_ident = ident
            else:
                no_price = price
                no_ident = ident

        # Fallback to outcomePrices if marketSides was empty
        if not sides:
            outcomes = d.get("outcomes", [])
            prices = d.get("outcomePrices", [])
            if outcomes and prices and len(outcomes) == len(prices):
                for outcome, price_str in zip(outcomes, prices):
                    if outcome.upper() == "YES":
                        yes_price = float(price_str)
                    elif outcome.upper() == "NO":
                        no_price = float(price_str)

        return cls(
            market_id=str(d.get("id", "")),
            question=d.get("question", ""),
            slug=d.get("slug", ""),
            end_date=d.get("endDate", ""),
            start_date=d.get("startDate", ""),
            category=d.get("category", ""),
            active=bool(d.get("active", False)),
            closed=bool(d.get("closed", True)),
            market_type=d.get("marketType", ""),
            yes_price=yes_price,
            no_price=no_price,
            yes_identifier=yes_ident,
            no_identifier=no_ident,
            tick_size=float(d.get("orderPriceMinTickSize", 0.001)),
            raw=d,
        )


@dataclass
class PolymarketOrderBook:
    """
    Orderbook snapshot for one market side (YES or NO).

    Prices are 0.0-1.0. Bids are sorted descending (best bid first).
    Asks are sorted ascending (best ask first).
    """

    slug: str
    bids: List[Dict[str, float]]   # [{"price": 0.728, "qty": 68.0}, ...]
    asks: List[Dict[str, float]]   # [{"price": 0.750, "qty": 50.0}, ...]

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0]["price"] if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0]["price"] if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        """(best_bid + best_ask) / 2 — None if either side is empty."""
        bid = self.best_bid
        ask = self.best_ask
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PolymarketOrderBook":
        """Parse marketData dict from /v1/markets/{identifier}/book response."""

        def _parse_levels(levels: list) -> List[Dict[str, float]]:
            result = []
            for lvl in levels:
                px = lvl.get("px", {})
                price_val = px.get("value", px) if isinstance(px, dict) else px
                result.append({
                    "price": float(price_val),
                    "qty": float(lvl.get("qty", 0)),
                })
            return result

        bids = _parse_levels(d.get("bids", []))
        asks = _parse_levels(d.get("asks", []))

        # Ensure sorted: bids descending, asks ascending
        bids.sort(key=lambda x: x["price"], reverse=True)
        asks.sort(key=lambda x: x["price"])

        return cls(
            slug=d.get("marketSlug", ""),
            bids=bids,
            asks=asks,
        )


# ── REST client ───────────────────────────────────────────────────


class PolymarketClient:
    """
    Async HTTP client for Polymarket.us.

    One instance per bot lifecycle. Not thread-safe — runs inside asyncio event loop.
    All methods create a fresh aiohttp.ClientSession per call (matches Kalshi pattern).
    """

    def __init__(self, auth: PolymarketAuth, timeout_sec: float = 10.0):
        self._auth = auth
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    # ── internal ──────────────────────────────────────────────────

    def _url(self, path: str) -> str:
        return f"{_BASE_URL}{_API_PREFIX}{path}"

    async def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Authenticated GET. Raises PolymarketAPIError on 4xx/5xx.
        Returns parsed JSON body on success.
        """
        query = ""
        if params:
            query = "?" + "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        full_path = f"{_API_PREFIX}{path}"
        headers = self._auth.headers("GET", full_path)
        url = self._url(path) + query

        async with aiohttp.ClientSession(timeout=self._timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    return None  # caller decides: 404 often means "not found" not error
                if resp.status >= 400:
                    body = await resp.text()
                    raise PolymarketAPIError(resp.status, body[:200])
                return await resp.json()

    # ── public API ────────────────────────────────────────────────

    async def get_markets(
        self,
        closed: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[PolymarketMarket]:
        """
        List Polymarket.us markets.

        Args:
            closed:  None = all, False = open only, True = closed only
            limit:   max results per page (default 100)
            offset:  pagination offset

        Returns:
            List of PolymarketMarket objects.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if closed is not None:
            params["closed"] = "true" if closed else "false"

        data = await self._get("/markets", params)
        if data is None:
            return []
        return [PolymarketMarket.from_dict(m) for m in data.get("markets", [])]

    async def get_orderbook(self, identifier: str) -> Optional[PolymarketOrderBook]:
        """
        Get orderbook (bids + asks) for a specific market side.

        Args:
            identifier:  The market side identifier from PolymarketMarket.yes_identifier
                         or .no_identifier (e.g. "tec-nba-mvp-2026-shagil")

        Returns:
            PolymarketOrderBook, or None if market not found.
        """
        data = await self._get(f"/markets/{identifier}/book")
        if data is None:
            return None
        market_data = data.get("marketData")
        if not market_data:
            return None
        return PolymarketOrderBook.from_dict(market_data)

    async def get_positions(self) -> Dict[str, Any]:
        """
        Get current account positions.

        Returns:
            Raw API response dict with 'positions' and 'availablePositions' keys.
        """
        data = await self._get("/portfolio/positions")
        return data or {}

    async def get_activities(
        self,
        limit: int = 50,
        cursor: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Get account activity history (deposits, trades, withdrawals).

        Args:
            limit:   max results per page
            cursor:  pagination cursor from previous response's nextCursor

        Returns:
            List of raw activity dicts.
        """
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        data = await self._get("/portfolio/activities", params)
        if data is None:
            return []
        return data.get("activities", [])

    async def connectivity_check(self) -> bool:
        """
        Quick authenticated connectivity check. Returns True if API responds.
        Does NOT raise on failure — suitable for verify.py.
        """
        try:
            data = await self._get("/markets", {"limit": 1})
            return data is not None
        except Exception as exc:
            logger.warning("Polymarket connectivity check failed: %s", exc)
            return False


def load_from_env() -> PolymarketClient:
    """
    Create PolymarketClient from environment variables.
    Delegates credential loading to polymarket_auth.load_from_env().
    """
    auth = _auth_from_env()
    return PolymarketClient(auth=auth)
