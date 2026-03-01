"""
Polymarket data-api client for whale trade tracking.

JOB:    Read whale trades and positions from data-api.polymarket.com.
        Used by copy_trader strategy to detect genuine whale signals.

DOES NOT: Execute trades, know about strategies, touch kill switch, require auth.

API facts confirmed via live probing 2026-03-01:
  Base URL:   https://data-api.polymarket.com
  Auth:       NONE — fully public, zero auth required
  Rate limit: Effectively none at reasonable polling cadence

  Confirmed endpoints:
    GET /trades?user={proxy_wallet}&limit=N       — trades for one wallet
    GET /trades?limit=N                           — most recent N global trades
    GET /positions?user={proxy_wallet}&limit=N    — open positions for one wallet

  Trade fields: proxyWallet, side, asset, conditionId, size, price, timestamp,
    title, slug, outcome, outcomeIndex, transactionHash, name, pseudonym
  Position fields: proxyWallet, asset, conditionId, size, avgPrice, currentValue,
    cashPnl, percentPnl, curPrice, title, slug, outcome, endDate, negativeRisk

  Price scale: 0.0–1.0 (probability). Multiply by 100 for Kalshi-style cents.
  Timestamps: Unix seconds (int).

Decoy filtering note: This module is pure data. Decoy detection (position age,
  minimum size, liquidity checks) lives in src/strategies/copy_trader_v1.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_BASE_URL = "https://data-api.polymarket.com"
_DEFAULT_TIMEOUT_SEC = 10.0


@dataclass
class WhaleTrade:
    """
    A single trade by a tracked whale on polymarket.com.

    price is 0.0-1.0 (probability scale). size is USD notional.
    outcome is the specific outcome they traded (e.g. "Yes", "No", "Up", "Down").
    side is "BUY" (opening/adding) or "SELL" (reducing/closing).
    """

    proxy_wallet: str
    side: str           # "BUY" or "SELL"
    outcome: str        # "Yes", "No", "Up", "Down", etc.
    price: float        # 0.0–1.0
    size: float         # USD notional
    timestamp: int      # unix seconds
    title: str          # human-readable market title
    slug: str           # market slug
    condition_id: str   # Polymarket condition ID (hex)
    transaction_hash: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WhaleTrade":
        """Parse one trade entry from the data-api response."""
        return cls(
            proxy_wallet=str(d.get("proxyWallet", "")),
            side=str(d.get("side", "")),
            outcome=str(d.get("outcome", "")),
            price=float(d.get("price", 0.0)),
            size=float(d.get("size", 0.0)),
            timestamp=int(d.get("timestamp", 0)),
            title=str(d.get("title", "")),
            slug=str(d.get("slug", "")),
            condition_id=str(d.get("conditionId", "")),
            transaction_hash=str(d.get("transactionHash", "")),
        )


@dataclass
class WhalePosition:
    """
    A currently open position held by a tracked whale.

    avg_price is the whale's average entry price (0.0-1.0).
    cur_price is the current market price (0.0-1.0).
    cash_pnl is unrealised USD P&L.
    end_date is the market resolution date (ISO8601 UTC or None).
    """

    proxy_wallet: str
    outcome: str        # "Yes", "No", etc.
    avg_price: float    # 0.0–1.0 — whale's average entry price
    cur_price: float    # 0.0–1.0 — current market price
    size: float         # shares held (roughly == USD at $1 par value)
    cash_pnl: float     # unrealised USD P&L
    title: str
    slug: str
    end_date: Optional[str]   # ISO8601 UTC or None
    condition_id: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WhalePosition":
        """Parse one position entry from the data-api response."""
        return cls(
            proxy_wallet=str(d.get("proxyWallet", "")),
            outcome=str(d.get("outcome", "")),
            avg_price=float(d.get("avgPrice", 0.0)),
            cur_price=float(d.get("curPrice", 0.0)),
            size=float(d.get("size", 0.0)),
            cash_pnl=float(d.get("cashPnl", 0.0)),
            title=str(d.get("title", "")),
            slug=str(d.get("slug", "")),
            end_date=d.get("endDate") or None,
            condition_id=str(d.get("conditionId", "")),
        )


class WhaleDataClient:
    """
    Async HTTP client for data-api.polymarket.com.

    No auth required. Returns [] on any error so callers degrade gracefully.
    since_ts filtering is done client-side (API does not expose a since= param).
    """

    def __init__(self, timeout_sec: float = _DEFAULT_TIMEOUT_SEC):
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    # ── internal ──────────────────────────────────────────────────

    async def _get_json(self, url: str) -> Optional[list]:
        """
        GET the URL and return parsed JSON list. Returns None on any error.
        """
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning("[whale_watcher] HTTP %d: %s", resp.status, url)
                        return None
                    return await resp.json()
        except Exception as exc:
            logger.warning("[whale_watcher] Fetch error for %s: %s", url, exc)
            return None

    # ── public API ────────────────────────────────────────────────

    async def get_trades(
        self,
        proxy_wallet: str,
        limit: int = 20,
        since_ts: Optional[int] = None,
    ) -> List[WhaleTrade]:
        """
        Fetch recent trades for one whale wallet.

        Args:
            proxy_wallet:  The trader's proxy address (from predicting.top or leaderboard)
            limit:         Max trades to fetch per call (default 20)
            since_ts:      If set, filter to trades with timestamp > since_ts (client-side)

        Returns:
            List of WhaleTrade objects, newest first. Empty list on error.
        """
        url = f"{_BASE_URL}/trades?user={proxy_wallet}&limit={limit}"
        data = await self._get_json(url)
        if data is None:
            return []

        trades = []
        for raw in data:
            try:
                t = WhaleTrade.from_dict(raw)
                if since_ts is not None and t.timestamp <= since_ts:
                    continue
                trades.append(t)
            except Exception as exc:
                logger.debug("[whale_watcher] Skipping malformed trade: %s", exc)

        return trades

    async def get_positions(
        self,
        proxy_wallet: str,
        limit: int = 50,
    ) -> List[WhalePosition]:
        """
        Fetch currently open positions for one whale wallet.

        Args:
            proxy_wallet:  The trader's proxy address
            limit:         Max positions to fetch (default 50)

        Returns:
            List of WhalePosition objects. Empty list on error.
        """
        url = f"{_BASE_URL}/positions?user={proxy_wallet}&limit={limit}"
        data = await self._get_json(url)
        if data is None:
            return []

        positions = []
        for raw in data:
            try:
                positions.append(WhalePosition.from_dict(raw))
            except Exception as exc:
                logger.debug("[whale_watcher] Skipping malformed position: %s", exc)

        return positions

    async def get_global_trades(self, limit: int = 20) -> List[WhaleTrade]:
        """
        Fetch the most recent trades globally (all wallets, all markets).

        Useful for monitoring market activity without a specific wallet target.
        Does NOT include a user= parameter in the request.

        Args:
            limit:  Max trades to return (default 20)

        Returns:
            List of WhaleTrade objects. Empty list on error.
        """
        url = f"{_BASE_URL}/trades?limit={limit}"
        data = await self._get_json(url)
        if data is None:
            return []

        trades = []
        for raw in data:
            try:
                trades.append(WhaleTrade.from_dict(raw))
            except Exception as exc:
                logger.debug("[whale_watcher] Skipping malformed global trade: %s", exc)

        return trades


def load_from_env() -> WhaleDataClient:
    """
    Create WhaleDataClient. No credentials required — public API.
    Factory follows project convention.
    """
    return WhaleDataClient()
