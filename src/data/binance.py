"""
Binance BTC price feed.

JOB:    BTC spot price via Binance public WebSocket bookTicker stream.
        Maintains rolling price history for move detection.
        Provides: current_price(), btc_move_pct(), is_stale.

DOES NOT: Strategy logic, know about Kalshi, place orders.

URL (only allowed): wss://stream.binance.us:9443/ws/btcusdt@bookTicker

NOTE: Using bookTicker (best bid/ask, ~40 updates/min) instead of @trade.
      Binance.US BTCUSDT has near-zero individual trade volume.
      bookTicker fires on any order book change — far more reliable for price.
      Price recorded = mid-price: (best_bid + best_ask) / 2.

Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot (price_feed.py — BinanceFeed class)
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Optional, Tuple

import websockets
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

_BINANCE_WS_URL = "wss://stream.binance.us:9443/ws/btcusdt@bookTicker"
_BINANCE_ETH_WS_URL = "wss://stream.binance.us:9443/ws/ethusdt@bookTicker"
_STALE_THRESHOLD_SEC = 35.0     # price older than this = stale feed
                                 # (Binance.US @bookTicker can be silent 10-30s — use 35s to avoid false stale)
_WINDOW_SEC = 60                 # default rolling window for move detection
_RECONNECT_DELAY_SEC = 5         # wait before reconnecting on disconnect


class BinanceFeed:
    """
    Binance BTCUSDT live bookTicker stream.

    Connects to the Binance.US WebSocket bookTicker stream (~40 updates/min).
    Maintains a rolling price history for move detection.
    Auto-reconnects on disconnect.

    Uses bookTicker (not @trade) because Binance.US BTCUSDT has near-zero
    individual trade volume — the @trade stream produces 0 messages.

    Usage:
        feed = BinanceFeed()
        await feed.start()
        move = feed.btc_move_pct()   # % change over last 60s, or None
        await feed.stop()
    """

    def __init__(
        self,
        ws_url: str = _BINANCE_WS_URL,
        window_sec: int = _WINDOW_SEC,
        reconnect_delay: float = _RECONNECT_DELAY_SEC,
        on_tick: Optional[Callable[[float], None]] = None,
    ):
        self._ws_url = ws_url
        self._window_sec = window_sec
        self._reconnect_delay = reconnect_delay
        self._on_tick = on_tick  # optional external callback

        # Rolling price history: deque of (timestamp, price) tuples
        self._history: Deque[Tuple[float, float]] = deque()
        self._last_price: Optional[float] = None
        self._last_update: float = 0.0
        self._running = False
        self._task: Optional[asyncio.Task] = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def start(self):
        """Start the WebSocket connection in a background task."""
        if self._task is not None and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run())
        logger.info("BinanceFeed started (url=%s)", self._ws_url)

    async def stop(self):
        """Stop the WebSocket connection."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("BinanceFeed stopped")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.stop()

    # ── Data access ───────────────────────────────────────────────────

    @property
    def is_stale(self) -> bool:
        """True if no price received in the last _STALE_THRESHOLD_SEC seconds."""
        if self._last_price is None:
            return True
        return (time.time() - self._last_update) > _STALE_THRESHOLD_SEC

    def current_price(self) -> Optional[float]:
        """Return current BTC price, or None if feed is stale."""
        if self.is_stale:
            return None
        return self._last_price

    def btc_move_pct(self, window_sec: Optional[int] = None) -> Optional[float]:
        """
        Return % price change over the last window_sec seconds.

        Positive = price went up. Negative = price went down.
        Returns None if insufficient data.

        Args:
            window_sec: window in seconds (default: self._window_sec from config)
        """
        w = window_sec or self._window_sec
        if not self._history:
            return None

        now_ts = time.time()
        cutoff_ts = now_ts - w

        # Trim expired entries
        while self._history and self._history[0][0] < cutoff_ts:
            self._history.popleft()

        if len(self._history) < 2:
            return None

        oldest_price = self._history[0][1]
        newest_price = self._history[-1][1]

        if oldest_price == 0:
            return None

        return (newest_price - oldest_price) / oldest_price * 100.0

    def price_history(self, window_sec: Optional[int] = None) -> list[Tuple[float, float]]:
        """Return list of (timestamp, price) within window_sec."""
        w = window_sec or self._window_sec
        cutoff = time.time() - w
        return [(ts, p) for ts, p in self._history if ts >= cutoff]

    def age_sec(self) -> Optional[float]:
        """Seconds since last price update, or None if never received."""
        if self._last_update == 0:
            return None
        return time.time() - self._last_update

    # ── Internal WebSocket loop ───────────────────────────────────────

    async def _run(self):
        """Main WebSocket loop with auto-reconnect."""
        while self._running:
            try:
                async with websockets.connect(
                    self._ws_url,
                    open_timeout=10,
                    ping_interval=30,
                    ping_timeout=10,
                ) as ws:
                    logger.info("BinanceFeed connected")
                    async for raw_msg in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw_msg)
                            # bookTicker stream: {"u":id,"s":"BTCUSDT","b":"67435.49","B":"0.1","a":"67436.00","A":"0.05"}
                            # Use mid-price (best_bid + best_ask) / 2 for price tracking.
                            if "b" in msg and "a" in msg:
                                price = (float(msg["b"]) + float(msg["a"])) / 2.0
                                self._record_price(price)
                        except (KeyError, ValueError) as e:
                            logger.debug("BinanceFeed parse error: %s", e)

            except (ConnectionClosed, OSError, asyncio.TimeoutError) as e:
                if self._running:
                    logger.warning(
                        "BinanceFeed disconnected (%s), reconnecting in %ss",
                        e, self._reconnect_delay,
                    )
                    await asyncio.sleep(self._reconnect_delay)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("BinanceFeed unexpected error: %s", e, exc_info=True)
                if self._running:
                    await asyncio.sleep(self._reconnect_delay)

    def _record_price(self, price: float):
        """Record a price tick into the rolling history."""
        now = time.time()
        self._last_price = price
        self._last_update = now
        self._history.append((now, price))

        # Trim history older than 2x the window (keep a buffer)
        cutoff = now - self._window_sec * 2
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()

        if self._on_tick:
            try:
                self._on_tick(price)
            except Exception as e:
                logger.debug("BinanceFeed tick callback error: %s", e)


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> BinanceFeed:
    """Build BinanceFeed for BTC from config.yaml."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using defaults")
        return BinanceFeed()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    feeds = cfg.get("feeds", {})
    return BinanceFeed(
        ws_url=feeds.get("binance_ws_url", _BINANCE_WS_URL),
        window_sec=feeds.get("btc_window_seconds", _WINDOW_SEC),
        reconnect_delay=feeds.get("reconnect_delay", _RECONNECT_DELAY_SEC),
    )


def load_eth_from_config() -> BinanceFeed:
    """Build BinanceFeed for ETH from config.yaml."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using ETH defaults")
        return BinanceFeed(ws_url=_BINANCE_ETH_WS_URL)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    feeds = cfg.get("feeds", {})
    return BinanceFeed(
        ws_url=feeds.get("eth_ws_url", _BINANCE_ETH_WS_URL),
        window_sec=feeds.get("eth_window_seconds", _WINDOW_SEC),
        reconnect_delay=feeds.get("reconnect_delay", _RECONNECT_DELAY_SEC),
    )
