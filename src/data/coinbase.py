"""
Coinbase BTC/ETH/SOL/XRP price feed — backup to Binance.US.

JOB:    BTC/ETH/SOL/XRP spot price via Coinbase public REST API.
        Used as fallback when Binance.US WebSocket goes stale.

DOES NOT: Strategy logic, know about Kalshi, place orders.

URL: https://api.coinbase.com/v2/prices/{SYMBOL}-USD/spot (free, no auth)

Architecture: DualPriceFeed wraps BinanceFeed + CoinbasePriceFeed.
  - Returns Binance price when not stale (primary)
  - Falls back to Coinbase price when Binance is stale (backup)
  - is_stale = True only when both feeds are stale → PriceFeedError upstream

Reference: CODEBASE_AUDIT.md REBUILD priority 5 (Session 44):
  "Add CoinbaseFeed class. Run as backup. If Binance stale: fall back to Coinbase.
   If both stale: PriceFeedError."
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

_COINBASE_BASE_URL = "https://api.coinbase.com/v2/prices"
_POLL_INTERVAL_SEC = 30        # poll every 30s (REST not WebSocket)
_STALE_THRESHOLD_SEC = 120.0   # stale if no update in 2 minutes
_REQUEST_TIMEOUT_SEC = 10      # per-request timeout


class CoinbasePriceFeed:
    """
    Polls Coinbase public REST API for spot prices.

    Provides the same interface as BinanceFeed: current_price(), is_stale,
    and btc_move_pct() (always None — no history tracking).

    Usage:
        feed = CoinbasePriceFeed(symbol="BTC")
        await feed.start()
        price = feed.current_price()
        await feed.stop()
    """

    def __init__(self, symbol: str = "BTC", poll_interval: float = _POLL_INTERVAL_SEC):
        self._symbol = symbol.upper()
        self._poll_interval = poll_interval
        self._url = f"{_COINBASE_BASE_URL}/{self._symbol}-USD/spot"
        self._price: Optional[float] = None
        self._last_update: float = 0.0
        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self) -> None:
        """Start background polling task."""
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name=f"coinbase_{self._symbol}")
        logger.info("CoinbasePriceFeed started (%s, poll=%ds)", self._symbol, self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.stop()

    # ── Data access ───────────────────────────────────────────────────

    @property
    def is_stale(self) -> bool:
        if self._price is None:
            return True
        return (time.time() - self._last_update) > _STALE_THRESHOLD_SEC

    def current_price(self) -> Optional[float]:
        if self.is_stale:
            return None
        return self._price

    def btc_move_pct(self, window_sec: Optional[int] = None) -> Optional[float]:
        """Always None — Coinbase feed has no rolling history (REST, not WebSocket)."""
        return None

    # ── Internal ──────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            await self._poll_once()
            await asyncio.sleep(self._poll_interval)

    async def _poll_once(self) -> None:
        """Fetch price from Coinbase. Updates _price/_last_update on success."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self._url,
                    timeout=aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SEC),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = float(data["data"]["amount"])
                        self._price = price
                        self._last_update = time.time()
                        logger.debug(
                            "[coinbase] %s price updated: $%.2f", self._symbol, price
                        )
                    else:
                        logger.warning(
                            "[coinbase] HTTP %d fetching %s price", resp.status, self._symbol
                        )
        except Exception as e:
            logger.debug("[coinbase] Poll error for %s: %s", self._symbol, e)


class DualPriceFeed:
    """
    Wraps a primary BinanceFeed and a backup CoinbasePriceFeed.

    Returns Binance price when Binance is fresh.
    Falls back to Coinbase price when Binance is stale.
    is_stale = True only when BOTH feeds are stale.

    Drop-in replacement for BinanceFeed anywhere the feed is used.
    btc_move_pct() always delegates to primary (Binance has rolling history).
    """

    def __init__(self, primary, backup: CoinbasePriceFeed):
        """
        Args:
            primary: BinanceFeed instance (or any feed with .is_stale + .current_price())
            backup: CoinbasePriceFeed instance
        """
        self._primary = primary
        self._backup = backup

    @property
    def is_stale(self) -> bool:
        return self._primary.is_stale and self._backup.is_stale

    def current_price(self) -> Optional[float]:
        if not self._primary.is_stale:
            return self._primary.current_price()
        # Primary stale — fall back to Coinbase
        backup_price = self._backup.current_price()
        if backup_price is not None:
            logger.warning(
                "[dual_feed] Binance.US stale — using Coinbase %s fallback ($%.2f)",
                getattr(self._backup, "_symbol", "?"),
                backup_price,
            )
        return backup_price

    def btc_move_pct(self, window_sec: Optional[int] = None) -> Optional[float]:
        """Always delegates to primary (Binance) — it has the rolling price history."""
        return self._primary.btc_move_pct(window_sec=window_sec)

    async def stop(self) -> None:
        """Stop both primary and backup feeds. Tolerates missing stop() on primary."""
        if hasattr(self._primary, "stop"):
            await self._primary.stop()
        await self._backup.stop()
