"""
Kalshi async REST client.

JOB:    All Kalshi API calls (markets, orders, fills, positions, balance).
        Rate limiting (read: 10/s, write: 5/s), retry with exponential backoff.
        Raises KalshiAPIError on any 4xx/5xx response.

DOES NOT: Auth logic (delegates to kalshi_auth.py), strategy, risk decisions.

Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot (kalshi_client.py)
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# DNS override: if DNS_SERVERS env var is set (comma-separated IPs, e.g. "8.8.8.8,8.8.4.4"),
# use aiodns with those servers instead of the system resolver. Useful when the local network
# performs Cisco Umbrella TLS inspection that redirects API traffic through a proxy.
_DNS_SERVERS_RAW = os.environ.get("DNS_SERVERS", "").strip()
_DNS_SERVERS: Optional[list] = [s.strip() for s in _DNS_SERVERS_RAW.split(",") if s.strip()] or None

PROJECT_ROOT = Path(__file__).parent.parent.parent
_API_PATH_PREFIX = "/trade-api/v2"


# ── API field migration helpers (March 12, 2026 breaking change) ──────
# Kalshi removed integer cents price fields and integer count fields.
# New fields: *_dollars (string "0.5900") and *_fp (string "100.00").
# These helpers read new format first, fall back to legacy for test mocks.


def _dollars_to_cents(
    d: Dict,
    dollars_key: str,
    fallback_key: str = "",
    fallback_key2: str = "",
) -> int:
    """Convert a dollars-string field ("0.5900") to integer cents (59).

    Falls back to legacy integer cents fields for backward compat with tests.
    Returns 0 for any value outside [0, 100] — NaN, Inf, negative, overflow.
    SEC-1: bounds check added Session 74 to make downstream price guards explicit.
    """
    val = d.get(dollars_key)
    if val is not None:
        try:
            result = round(float(val) * 100)
            if 0 <= result <= 100:
                return result
        except (ValueError, TypeError, OverflowError):
            pass
    # Legacy fallback: integer cents
    if fallback_key and fallback_key in d:
        try:
            result = int(d[fallback_key])
            if 0 <= result <= 100:
                return result
        except (ValueError, TypeError):
            pass
    if fallback_key2 and fallback_key2 in d:
        try:
            result = int(d[fallback_key2])
            if 0 <= result <= 100:
                return result
        except (ValueError, TypeError):
            pass
    return 0


def _fp_to_int(d: Dict, fp_key: str, fallback_key: str = "") -> int:
    """Convert an _fp string field ("100.00") to integer (100).

    Falls back to legacy integer field for backward compat with tests.
    Returns 0 for NaN, Inf, negative, or absurdly large values (> 1e9).
    SEC-1: bounds check added Session 74 alongside _dollars_to_cents fix.
    """
    _MAX_REASONABLE = 1_000_000_000  # 1 billion contracts is not a valid count
    val = d.get(fp_key)
    if val is not None:
        try:
            result = round(float(val))
            if 0 <= result <= _MAX_REASONABLE:
                return result
        except (ValueError, TypeError, OverflowError):
            pass
    if fallback_key and fallback_key in d:
        try:
            result = int(d[fallback_key])
            if 0 <= result <= _MAX_REASONABLE:
                return result
        except (ValueError, TypeError):
            pass
    return 0


# ── Data classes ──────────────────────────────────────────────────────


@dataclass
class Market:
    ticker: str
    title: str
    event_ticker: str
    status: str
    yes_price: int      # cents 0-100
    no_price: int       # cents 0-100
    volume: int
    close_time: str     # ISO-8601
    open_time: str      # ISO-8601
    result: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class OrderBookLevel:
    price: int      # cents
    quantity: int


@dataclass
class OrderBook:
    yes_bids: List[OrderBookLevel]
    no_bids: List[OrderBookLevel]

    def best_yes_bid(self) -> Optional[int]:
        return max((l.price for l in self.yes_bids), default=None)

    def best_no_bid(self) -> Optional[int]:
        return max((l.price for l in self.no_bids), default=None)

    def yes_ask(self) -> Optional[int]:
        """YES ask implied from best NO bid: 100 - best_no_bid."""
        no_bid = self.best_no_bid()
        return (100 - no_bid) if no_bid is not None else None

    def no_ask(self) -> Optional[int]:
        """NO ask implied from best YES bid: 100 - best_yes_bid."""
        yes_bid = self.best_yes_bid()
        return (100 - yes_bid) if yes_bid is not None else None


@dataclass
class Order:
    order_id: str
    client_order_id: str
    ticker: str
    side: str           # "yes" | "no"
    action: str         # "buy" | "sell"
    type: str           # "limit" | "market"
    status: str         # "resting" | "canceled" | "executed" | "pending"
    yes_price: int
    no_price: int
    initial_count: int
    remaining_count: int
    fill_count: int
    created_time: str
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class Fill:
    trade_id: str
    order_id: str
    ticker: str
    side: str
    action: str
    yes_price: int
    no_price: int
    count: int
    created_time: str
    is_taker: bool = False
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class Position:
    ticker: str
    market_exposure: int    # net contracts (positive=YES, negative=NO)
    realized_pnl: int       # cents
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass
class Balance:
    available_balance: int  # cents
    portfolio_value: int    # cents

    @property
    def available_usd(self) -> float:
        return self.available_balance / 100.0

    @property
    def portfolio_usd(self) -> float:
        return self.portfolio_value / 100.0


# ── Rate limiter ──────────────────────────────────────────────────────


class _AsyncRateLimiter:
    """Token-bucket rate limiter for async contexts.
    Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot
    """

    def __init__(self, calls_per_second: int):
        self._rate = calls_per_second
        self._sem = asyncio.Semaphore(calls_per_second)
        self._refill_task: Optional[asyncio.Task] = None

    async def start(self):
        self._refill_task = asyncio.create_task(self._refill())

    async def _refill(self):
        while True:
            await asyncio.sleep(1.0)
            for _ in range(self._rate - self._sem._value):
                try:
                    self._sem.release()
                except ValueError:
                    break  # already at max

    async def acquire(self):
        await self._sem.acquire()

    def stop(self):
        if self._refill_task:
            self._refill_task.cancel()


# ── Main client ───────────────────────────────────────────────────────


class KalshiClient:
    """
    Async Kalshi REST API client.

    All network I/O is async. Auth is delegated to KalshiAuth.
    Rate limiters enforce Kalshi's API limits.
    Auto-retries on 429 and 5xx with exponential backoff.
    """

    def __init__(
        self,
        auth,               # KalshiAuth instance (avoid circular import)
        base_url: str,
        read_rate_limit: int = 10,
        write_rate_limit: int = 5,
        timeout: int = 10,
        max_retries: int = 3,
    ):
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._session: Optional[aiohttp.ClientSession] = None
        self._read_limiter = _AsyncRateLimiter(read_rate_limit)
        self._write_limiter = _AsyncRateLimiter(write_rate_limit)

    # ── Session lifecycle ─────────────────────────────────────────────

    async def start(self):
        if _DNS_SERVERS:
            try:
                resolver = aiohttp.AsyncResolver(nameservers=_DNS_SERVERS)
                connector = aiohttp.TCPConnector(resolver=resolver)
                self._session = aiohttp.ClientSession(connector=connector)
                logger.info("KalshiClient using custom DNS resolver: %s", _DNS_SERVERS)
            except Exception as e:
                logger.warning("Custom DNS resolver failed (%s), falling back to default", e)
                self._session = aiohttp.ClientSession()
        else:
            self._session = aiohttp.ClientSession()
        await self._read_limiter.start()
        await self._write_limiter.start()
        logger.info("KalshiClient started (base_url=%s)", self._base_url)

    async def close(self):
        self._read_limiter.stop()
        self._write_limiter.stop()
        if self._session:
            await self._session.close()
        logger.info("KalshiClient closed")

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *_):
        await self.close()

    # ── Auth ──────────────────────────────────────────────────────────

    def _auth_headers(self, method: str, path: str) -> Dict[str, str]:
        """Build auth headers. path is the relative path like '/markets'."""
        full_path = f"{_API_PATH_PREFIX}{path}"
        headers = self._auth.headers(method, full_path)
        headers["Content-Type"] = "application/json"
        headers["User-Agent"] = "polymarket-bot/1.0 (automated-trader; paper-mode)"
        return headers

    # ── Generic HTTP ──────────────────────────────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: Optional[Dict] = None,
        params: Optional[Dict] = None,
        is_write: bool = False,
    ) -> Dict[str, Any]:
        limiter = self._write_limiter if is_write else self._read_limiter
        url = f"{self._base_url}{path}"
        headers = self._auth_headers(method.upper(), path.split("?")[0])

        for attempt in range(1, self._max_retries + 1):
            await limiter.acquire()
            try:
                async with self._session.request(
                    method, url,
                    headers=headers,
                    json=json_body,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    if resp.status == 429:
                        wait = min(2 ** attempt, 16)
                        logger.warning("Rate limited on %s %s, retry in %ss", method, path, wait)
                        await asyncio.sleep(wait)
                        continue

                    if resp.status >= 500:
                        wait = min(2 ** attempt, 16)
                        logger.warning(
                            "Server error %s on %s %s, retry in %ss",
                            resp.status, method, path, wait,
                        )
                        await asyncio.sleep(wait)
                        continue

                    try:
                        body = await resp.json()
                    except Exception:
                        body = {"_raw": await resp.text()}

                    if resp.status >= 400:
                        logger.error(
                            "API error %s on %s %s: %s",
                            resp.status, method, path, body,
                        )
                        raise KalshiAPIError(resp.status, body)

                    return body

            except KalshiAPIError:
                raise  # never retry 4xx
            except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
                if attempt == self._max_retries:
                    raise
                wait = min(2 ** attempt, 16)
                logger.warning(
                    "Network error on %s %s (%s), retry in %ss",
                    method, path, exc, wait,
                )
                await asyncio.sleep(wait)

        raise KalshiAPIError(0, {"error": "Max retries exceeded"})

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, body: Dict) -> Dict:
        return await self._request("POST", path, json_body=body, is_write=True)

    async def _delete(self, path: str) -> Dict:
        return await self._request("DELETE", path, is_write=True)

    # ── Exchange status (no auth required) ────────────────────────────

    async def get_exchange_status(self) -> Dict[str, Any]:
        return await self._get("/exchange/status")

    # ── Market data ───────────────────────────────────────────────────

    async def get_markets(
        self,
        series_ticker: Optional[str] = None,
        status: str = "open",
        limit: int = 100,
        cursor: Optional[str] = None,
    ) -> List[Market]:
        """Fetch open markets, optionally filtered by series ticker."""
        params: Dict[str, Any] = {"status": status, "limit": limit}
        if series_ticker:
            params["series_ticker"] = series_ticker
        if cursor:
            params["cursor"] = cursor
        data = await self._get("/markets", params=params)
        return [self._parse_market(m) for m in data.get("markets", [])]

    async def get_market(self, ticker: str) -> Market:
        data = await self._get(f"/markets/{ticker}")
        return self._parse_market(data["market"])

    async def get_orderbook(self, ticker: str) -> OrderBook:
        """
        Fetch order book for a market.

        Kalshi returns bids for both YES and NO sides.
        YES bid at X cents → NO ask at (100-X) cents.
        """
        data = await self._get(f"/markets/{ticker}/orderbook")
        # March 12, 2026: orderbook → orderbook_fp with string dollar prices
        ob = data.get("orderbook_fp", data.get("orderbook", {}))
        # New format: yes_dollars/no_dollars with string pairs ["0.5900", "100.00"]
        # Legacy format: yes/no with int pairs [59, 100]
        yes_key = "yes_dollars" if "yes_dollars" in ob else "yes"
        no_key = "no_dollars" if "no_dollars" in ob else "no"
        is_dollars = yes_key == "yes_dollars"
        yes_bids = [
            OrderBookLevel(
                price=round(float(level[0]) * 100) if is_dollars else int(level[0]),
                quantity=round(float(level[1])) if is_dollars else int(level[1]),
            )
            for level in ob.get(yes_key, [])
            if len(level) >= 2
        ]
        no_bids = [
            OrderBookLevel(
                price=round(float(level[0]) * 100) if is_dollars else int(level[0]),
                quantity=round(float(level[1])) if is_dollars else int(level[1]),
            )
            for level in ob.get(no_key, [])
            if len(level) >= 2
        ]
        return OrderBook(yes_bids=yes_bids, no_bids=no_bids)

    # ── Order management ──────────────────────────────────────────────

    async def create_order(
        self,
        ticker: str,
        side: str,
        action: str,
        count: int,
        *,
        order_type: str = "limit",
        yes_price: Optional[int] = None,
        no_price: Optional[int] = None,
        client_order_id: Optional[str] = None,
        time_in_force: Optional[str] = None,
        post_only: bool = False,
        expiration_ts: Optional[int] = None,
    ) -> Order:
        """
        Place an order on Kalshi.

        Args:
            ticker: Market ticker (e.g. "KXBTC15M-26FEB071500")
            side: "yes" or "no"
            action: "buy" or "sell"
            count: Number of contracts (1 contract = 1 cent cost at P=1¢)
            order_type: "limit" or "market"
            yes_price: Limit price in cents (1-99) for YES side
            no_price: Limit price in cents (1-99) for NO side
            client_order_id: Idempotency key — generated if not provided
            time_in_force: "fill_or_kill" or None (GTC default)
            post_only: If True, order is maker-only (rejected if it would
                cross the spread and fill as taker). Saves ~75% on fees.
            expiration_ts: Unix timestamp (int64) when the order expires.
                Useful with post_only to auto-cancel unfilled maker orders.
        """
        if client_order_id is None:
            client_order_id = str(uuid.uuid4())

        if yes_price is not None and not (1 <= yes_price <= 99):
            raise ValueError(f"yes_price must be 1–99, got {yes_price}")
        if no_price is not None and not (1 <= no_price <= 99):
            raise ValueError(f"no_price must be 1–99, got {no_price}")

        body: Dict[str, Any] = {
            "ticker": ticker,
            "side": side,
            "action": action,
            "count": count,
            "type": order_type,
            "client_order_id": client_order_id,
        }
        if yes_price is not None:
            body["yes_price"] = yes_price
        if no_price is not None:
            body["no_price"] = no_price
        if time_in_force:
            body["time_in_force"] = time_in_force
        if post_only:
            body["post_only"] = True
        if expiration_ts is not None:
            body["expiration_ts"] = expiration_ts

        data = await self._post("/portfolio/orders", body)
        return self._parse_order(data["order"])

    async def get_order(self, order_id: str) -> Order:
        data = await self._get(f"/portfolio/orders/{order_id}")
        return self._parse_order(data["order"])

    async def cancel_order(self, order_id: str) -> Order:
        data = await self._delete(f"/portfolio/orders/{order_id}")
        return self._parse_order(data["order"])

    async def get_orders(
        self,
        ticker: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Order]:
        params: Dict[str, Any] = {}
        if ticker:
            params["ticker"] = ticker
        if status:
            params["status"] = status
        data = await self._get("/portfolio/orders", params=params)
        return [self._parse_order(o) for o in data.get("orders", [])]

    async def cancel_all_orders(self, ticker: Optional[str] = None) -> List[Order]:
        """Cancel all open orders. Used by kill switch emergency path."""
        orders = await self.get_orders(ticker=ticker, status="resting")
        cancelled = []
        for order in orders:
            try:
                cancelled.append(await self.cancel_order(order.order_id))
                logger.info("Cancelled order %s", order.order_id)
            except KalshiAPIError as e:
                logger.warning("Failed to cancel order %s: %s", order.order_id, e)
        return cancelled

    # ── Fills / Positions / Balance ───────────────────────────────────

    async def get_fills(
        self,
        ticker: Optional[str] = None,
        limit: int = 100,
    ) -> List[Fill]:
        params: Dict[str, Any] = {"limit": limit}
        if ticker:
            params["ticker"] = ticker
        data = await self._get("/portfolio/fills", params=params)
        fills = []
        for f in data.get("fills", []):
            fills.append(Fill(
                trade_id=f.get("trade_id", ""),
                order_id=f.get("order_id", ""),
                ticker=f.get("ticker", f.get("market_ticker", "")),
                side=f.get("side", ""),
                action=f.get("action", ""),
                yes_price=_dollars_to_cents(f, "yes_price_dollars", fallback_key="yes_price"),
                no_price=_dollars_to_cents(f, "no_price_dollars", fallback_key="no_price"),
                count=_fp_to_int(f, "count_fp", fallback_key="count"),
                created_time=f.get("created_time", ""),
                is_taker=f.get("is_taker", False),
                raw=f,
            ))
        return fills

    async def get_positions(
        self,
        ticker: Optional[str] = None,
        settlement_status: str = "unsettled",
    ) -> List[Position]:
        params: Dict[str, Any] = {"settlement_status": settlement_status}
        if ticker:
            params["ticker"] = ticker
        data = await self._get("/portfolio/positions", params=params)
        return [
            Position(
                ticker=p.get("ticker", ""),
                market_exposure=p.get("market_exposure", 0),
                realized_pnl=p.get("realized_pnl", 0),
                raw=p,
            )
            for p in data.get("market_positions", [])
        ]

    async def get_balance(self) -> Balance:
        data = await self._get("/portfolio/balance")
        return Balance(
            available_balance=data.get("balance", data.get("available_balance", 0)),
            portfolio_value=data.get("portfolio_value", 0),
        )

    # ── Parsers ───────────────────────────────────────────────────────

    @staticmethod
    def _parse_market(m: Dict) -> Market:
        # March 12, 2026: Kalshi API v2 removed integer cents fields.
        # New fields: yes_bid_dollars/no_bid_dollars (string "0.5900" = 59c)
        # Fall back to legacy integer cents fields for test mocks.
        yes_price = _dollars_to_cents(m, "yes_bid_dollars", fallback_key="yes_bid", fallback_key2="yes_price")
        no_price = _dollars_to_cents(m, "no_bid_dollars", fallback_key="no_bid", fallback_key2="no_price")
        volume = _fp_to_int(m, "volume_fp", fallback_key="volume")
        return Market(
            ticker=m.get("ticker", ""),
            title=m.get("title", ""),
            event_ticker=m.get("event_ticker", ""),
            status=m.get("status", ""),
            yes_price=yes_price,
            no_price=no_price,
            volume=volume,
            close_time=m.get("close_time", ""),
            open_time=m.get("open_time", ""),
            result=(m.get("result") or "").lower() or None,
            raw=m,
        )

    @staticmethod
    def _parse_order(o: Dict) -> Order:
        return Order(
            order_id=o.get("order_id", ""),
            client_order_id=o.get("client_order_id", ""),
            ticker=o.get("ticker", ""),
            side=o.get("side", ""),
            action=o.get("action", ""),
            type=o.get("type", ""),
            status=o.get("status", ""),
            yes_price=_dollars_to_cents(o, "yes_price_dollars", fallback_key="yes_price"),
            no_price=_dollars_to_cents(o, "no_price_dollars", fallback_key="no_price"),
            initial_count=_fp_to_int(o, "initial_count_fp", fallback_key="initial_count"),
            remaining_count=_fp_to_int(o, "remaining_count_fp", fallback_key="remaining_count"),
            fill_count=_fp_to_int(o, "fill_count_fp", fallback_key="fill_count"),
            created_time=o.get("created_time", ""),
            raw=o,
        )


# ── Error ─────────────────────────────────────────────────────────────


class KalshiAPIError(Exception):
    def __init__(self, status: int, body: Any):
        self.status = status
        self.body = body  # preserved in full for programmatic inspection
        # SEC-2: truncate body in the string representation so full API error
        # responses (which may contain account/order details) don't flood logs.
        body_str = str(body)
        if len(body_str) > 300:
            body_str = body_str[:300] + "...[truncated]"
        super().__init__(f"Kalshi API {status}: {body_str}")


# ── Factory ───────────────────────────────────────────────────────────


def load_from_env() -> KalshiClient:
    """
    Build a KalshiClient from environment variables and config.yaml.

    Reads:
        LIVE_TRADING env var → selects demo vs live base URL
        config.yaml → rate limits, timeout, retries
        Delegates auth setup to kalshi_auth.load_from_env()
    """
    import yaml
    from src.auth.kalshi_auth import load_from_env as auth_load

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        raise RuntimeError(f"config.yaml not found at {config_path}")

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    k = cfg.get("kalshi", {})
    live_trading = os.getenv("LIVE_TRADING", "false").lower() == "true"

    if live_trading:
        base_url = k.get("live_url", "https://trading-api.kalshi.com/trade-api/v2")
        logger.warning("KalshiClient initialized in LIVE mode")
    else:
        base_url = k.get("demo_url", "https://demo-api.kalshi.co/trade-api/v2")
        logger.info("KalshiClient initialized in DEMO mode")

    auth = auth_load()

    return KalshiClient(
        auth=auth,
        base_url=base_url,
        read_rate_limit=k.get("read_rate_limit", 10),
        write_rate_limit=k.get("write_rate_limit", 5),
        timeout=k.get("request_timeout", 10),
        max_retries=k.get("max_retries", 3),
    )
