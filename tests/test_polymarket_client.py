"""
Tests for Polymarket.us REST client.

Uses unittest.mock to avoid real network calls.
Tests: data parsing, model construction, error handling, rate limiting.

API facts (confirmed via live exploration 2026-03-01):
  - Base URL: https://api.polymarket.us
  - Version prefix: /v1
  - All current markets are SPORTS (NBA/NFL/NHL/NCAA)
  - Prices are 0.0-1.0 scale (not cents)
  - Orderbook: GET /v1/markets/{identifier}/book
  - Positions: GET /v1/portfolio/positions
  - Activities: GET /v1/portfolio/activities
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ── shared fixtures ────────────────────────────────────────────────

SAMPLE_MARKET = {
    "id": "4983",
    "question": "NBA MVP",
    "slug": "tec-nba-mvp-2026",
    "endDate": "2026-06-30T00:00:00Z",
    "startDate": "2026-01-01T00:00:00Z",
    "category": "sports",
    "active": True,
    "closed": False,
    "marketType": "futures",
    "outcomes": ["No", "Yes"],
    "outcomePrices": ["0.272", "0.728"],
    "orderPriceMinTickSize": 0.001,
    "marketSides": [
        {
            "id": "9965",
            "identifier": "tec-nba-mvp-2026-shagil",
            "description": "Yes",
            "price": "0.728",
            "long": True,
            "marketId": 4983,
        },
        {
            "id": "9966",
            "identifier": "tec-nba-mvp-2026-shagil",
            "description": "No",
            "price": "0.272",
            "long": False,
            "marketId": 4983,
        },
    ],
}

SAMPLE_ORDERBOOK = {
    "marketData": {
        "marketSlug": "tec-nba-mvp-2026-shagil",
        "bids": [
            {"px": {"value": "0.728", "currency": "USD"}, "qty": "68.000"},
            {"px": {"value": "0.700", "currency": "USD"}, "qty": "100.000"},
        ],
        "asks": [
            {"px": {"value": "0.750", "currency": "USD"}, "qty": "50.000"},
            {"px": {"value": "0.780", "currency": "USD"}, "qty": "200.000"},
        ],
    }
}

SAMPLE_POSITIONS = {
    "positions": {},
    "nextCursor": "",
    "eof": True,
    "availablePositions": [],
}

SAMPLE_ACTIVITIES = {
    "activities": [
        {
            "type": "ACTIVITY_TYPE_ACCOUNT_ADVANCED_DEPOSIT",
            "accountBalanceChange": {
                "transactionId": "TXN123",
                "status": "ACCOUNT_BALANCE_CHANGE_STATUS_COMPLETED",
                "amount": {"value": "50", "currency": "USD"},
            },
        }
    ],
    "nextCursor": "",
    "eof": True,
}


# ── Market dataclass tests ─────────────────────────────────────────


class TestPolymarketModels:
    def test_market_from_dict_basic_fields(self):
        from src.platforms.polymarket import PolymarketMarket
        m = PolymarketMarket.from_dict(SAMPLE_MARKET)
        assert m.market_id == "4983"
        assert m.question == "NBA MVP"
        assert m.closed is False
        assert m.market_type == "futures"
        assert m.category == "sports"

    def test_market_yes_price_from_market_sides(self):
        from src.platforms.polymarket import PolymarketMarket
        m = PolymarketMarket.from_dict(SAMPLE_MARKET)
        # YES price = long=True side
        assert abs(m.yes_price - 0.728) < 1e-6

    def test_market_no_price_from_market_sides(self):
        from src.platforms.polymarket import PolymarketMarket
        m = PolymarketMarket.from_dict(SAMPLE_MARKET)
        # NO price = long=False side
        assert abs(m.no_price - 0.272) < 1e-6

    def test_market_yes_price_cents(self):
        from src.platforms.polymarket import PolymarketMarket
        m = PolymarketMarket.from_dict(SAMPLE_MARKET)
        assert m.yes_price_cents == 73  # round(0.728 * 100)

    def test_market_identifier_yes(self):
        from src.platforms.polymarket import PolymarketMarket
        m = PolymarketMarket.from_dict(SAMPLE_MARKET)
        assert m.yes_identifier == "tec-nba-mvp-2026-shagil"

    def test_market_handles_no_market_sides(self):
        """Falls back to outcomePrices when marketSides is empty."""
        from src.platforms.polymarket import PolymarketMarket
        data = dict(SAMPLE_MARKET, marketSides=[])
        m = PolymarketMarket.from_dict(data)
        # outcomePrices: ["0.272", "0.728"] → outcomes: ["No", "Yes"] → YES=0.728
        assert abs(m.yes_price - 0.728) < 1e-6

    def test_orderbook_best_bid(self):
        from src.platforms.polymarket import PolymarketOrderBook
        ob = PolymarketOrderBook.from_dict(SAMPLE_ORDERBOOK["marketData"])
        assert abs(ob.best_bid - 0.728) < 1e-6

    def test_orderbook_best_ask(self):
        from src.platforms.polymarket import PolymarketOrderBook
        ob = PolymarketOrderBook.from_dict(SAMPLE_ORDERBOOK["marketData"])
        assert abs(ob.best_ask - 0.750) < 1e-6

    def test_orderbook_mid_price(self):
        from src.platforms.polymarket import PolymarketOrderBook
        ob = PolymarketOrderBook.from_dict(SAMPLE_ORDERBOOK["marketData"])
        mid = ob.mid_price
        assert mid is not None
        assert abs(mid - (0.728 + 0.750) / 2) < 1e-6

    def test_orderbook_mid_price_none_when_no_bids(self):
        from src.platforms.polymarket import PolymarketOrderBook
        data = {"marketSlug": "x", "bids": [], "asks": []}
        ob = PolymarketOrderBook.from_dict(data)
        assert ob.mid_price is None

    def test_orderbook_mid_price_none_when_no_asks(self):
        from src.platforms.polymarket import PolymarketOrderBook
        data = {"marketSlug": "x", "bids": [{"px": {"value": "0.5"}, "qty": "10"}], "asks": []}
        ob = PolymarketOrderBook.from_dict(data)
        assert ob.mid_price is None


# ── PolymarketClient tests (mocked aiohttp) ────────────────────────


def _make_mock_response(status: int, body: dict):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=body)
    resp.text = AsyncMock(return_value=json.dumps(body))
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _make_mock_session(responses: list):
    """Create mock aiohttp session that returns responses in sequence."""
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    call_count = [0]

    def get_side_effect(url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(responses):
            return responses[idx]
        return _make_mock_response(404, {"code": 5, "message": "Not Found"})

    session.get = MagicMock(side_effect=get_side_effect)
    session.post = MagicMock(side_effect=get_side_effect)
    return session


class TestPolymarketClient:
    def _make_client(self):
        from src.platforms.polymarket import PolymarketClient
        from src.auth.polymarket_auth import PolymarketAuth
        import base64
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        pk = Ed25519PrivateKey.generate()
        seed = pk.private_bytes_raw()
        pub = pk.public_key().public_bytes_raw()
        auth = PolymarketAuth(
            key_id="test-key-id",
            secret_key_b64=base64.b64encode(seed + pub).decode(),
        )
        return PolymarketClient(auth=auth)

    @pytest.mark.asyncio
    async def test_get_markets_returns_list(self):
        client = self._make_client()
        body = {"markets": [SAMPLE_MARKET]}
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_markets(limit=1)
        assert len(result) == 1
        assert result[0].question == "NBA MVP"

    @pytest.mark.asyncio
    async def test_get_markets_open_only(self):
        client = self._make_client()
        body = {"markets": [SAMPLE_MARKET]}
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, body)])
            mock_cls.return_value = sess
            await client.get_markets(closed=False, limit=10)
        # Verify closed=false was in the request URL
        call_args = sess.get.call_args
        assert "closed=false" in call_args[0][0] or "closed=false" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_markets_empty_returns_empty_list(self):
        client = self._make_client()
        body = {"markets": []}
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_markets()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_markets_raises_on_4xx(self):
        from src.platforms.polymarket import PolymarketAPIError
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(401, {"code": 16, "message": "Unauthorized"})]
            )
            with pytest.raises(PolymarketAPIError):
                await client.get_markets()

    @pytest.mark.asyncio
    async def test_get_orderbook_returns_orderbook(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, SAMPLE_ORDERBOOK)]
            )
            ob = await client.get_orderbook("tec-nba-mvp-2026-shagil")
        assert ob is not None
        assert abs(ob.best_bid - 0.728) < 1e-6

    @pytest.mark.asyncio
    async def test_get_orderbook_404_returns_none(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(404, {"code": 5, "message": "Not Found"})]
            )
            ob = await client.get_orderbook("nonexistent")
        assert ob is None

    @pytest.mark.asyncio
    async def test_get_positions_returns_dict(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, SAMPLE_POSITIONS)]
            )
            result = await client.get_positions()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_activities_returns_list(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, SAMPLE_ACTIVITIES)]
            )
            acts = await client.get_activities(limit=5)
        assert len(acts) == 1
        assert acts[0]["type"] == "ACTIVITY_TYPE_ACCOUNT_ADVANCED_DEPOSIT"

    @pytest.mark.asyncio
    async def test_client_uses_correct_base_url(self):
        client = self._make_client()
        body = {"markets": []}
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, body)])
            mock_cls.return_value = sess
            await client.get_markets()
        url = sess.get.call_args[0][0]
        assert url.startswith("https://api.polymarket.us/v1/")

    @pytest.mark.asyncio
    async def test_client_sends_auth_headers(self):
        client = self._make_client()
        body = {"markets": []}
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, body)])
            mock_cls.return_value = sess
            await client.get_markets()
        call_kwargs = sess.get.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "X-PM-Access-Key" in headers
        assert "X-PM-Signature" in headers
        assert "X-PM-Timestamp" in headers


# ── load_from_env tests ───────────────────────────────────────────


class TestPolymarketPlaceOrder:
    """Tests for POST /v1/orders — place_order()."""

    # Real API response (confirmed 2026-03-08): uses "id" + "executions" list
    SAMPLE_ORDER_UNFILLED = {
        "id": "ord-abc123",
        "executions": [],
    }
    SAMPLE_ORDER_FILLED = {
        "id": "ord-abc123",
        "executions": [{"quantity": 1, "price": {"value": "0.55", "currency": "USD"}}],
    }

    def _make_client(self):
        from src.platforms.polymarket import PolymarketClient
        from src.auth.polymarket_auth import PolymarketAuth
        import base64
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        pk = Ed25519PrivateKey.generate()
        seed = pk.private_bytes_raw()
        pub = pk.public_key().public_bytes_raw()
        auth = PolymarketAuth(
            key_id="test-key-id",
            secret_key_b64=base64.b64encode(seed + pub).decode(),
        )
        return PolymarketClient(auth=auth)

    # ── PolymarketOrderResult dataclass tests ───────────────────────

    def test_order_result_is_filled_true(self):
        """is_filled = True when executions list is non-empty."""
        from src.platforms.polymarket import PolymarketOrderResult
        result = PolymarketOrderResult(
            order_id="abc",
            executions=[{"quantity": 1}],
        )
        assert result.is_filled

    def test_order_result_is_filled_false(self):
        """is_filled = False when executions list is empty (FOK no-fill)."""
        from src.platforms.polymarket import PolymarketOrderResult
        result = PolymarketOrderResult(order_id="abc", executions=[])
        assert not result.is_filled

    def test_order_result_from_dict_real_response(self):
        """Parse the real API response shape confirmed 2026-03-08."""
        from src.platforms.polymarket import PolymarketOrderResult
        r = PolymarketOrderResult.from_dict({"id": "8P08FD200KVQ", "executions": []})
        assert r.order_id == "8P08FD200KVQ"
        assert not r.is_filled

    def test_order_result_from_dict_filled(self):
        from src.platforms.polymarket import PolymarketOrderResult
        r = PolymarketOrderResult.from_dict({
            "id": "xyz-789",
            "executions": [{"quantity": 1, "price": {"value": "0.55"}}],
        })
        assert r.order_id == "xyz-789"
        assert r.is_filled

    def test_order_result_from_dict_fallback_order_id(self):
        """Falls back to 'orderId' field when 'id' is absent."""
        from src.platforms.polymarket import PolymarketOrderResult
        r = PolymarketOrderResult.from_dict({"orderId": "fallback-id", "executions": []})
        assert r.order_id == "fallback-id"

    def test_order_result_from_dict_empty_dict(self):
        from src.platforms.polymarket import PolymarketOrderResult
        r = PolymarketOrderResult.from_dict({})
        assert r.order_id == ""
        assert not r.is_filled

    # ── OrderIntent / TimeInForce constants ─────────────────────────

    def test_order_intent_constants_exist(self):
        from src.platforms.polymarket import OrderIntent
        assert OrderIntent.BUY_LONG == "ORDER_INTENT_BUY_LONG"
        assert OrderIntent.BUY_SHORT == "ORDER_INTENT_BUY_SHORT"

    def test_time_in_force_constants_exist(self):
        from src.platforms.polymarket import TimeInForce
        assert TimeInForce.FOK == "TIME_IN_FORCE_FILL_OR_KILL"
        assert TimeInForce.IOC == "TIME_IN_FORCE_IMMEDIATE_OR_CANCEL"
        assert TimeInForce.GTC == "TIME_IN_FORCE_GOOD_TILL_CANCEL"

    # ── place_order() HTTP tests ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_place_order_returns_result(self):
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, self.SAMPLE_ORDER_FILLED)]
            )
            result = await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        assert result.order_id == "ord-abc123"
        assert result.is_filled

    @pytest.mark.asyncio
    async def test_place_order_uses_post_not_get(self):
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        assert sess.post.called, "Expected POST to be called"
        assert not sess.get.called, "Expected GET NOT to be called"

    @pytest.mark.asyncio
    async def test_place_order_url_is_correct(self):
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        url = sess.post.call_args[0][0]
        assert url == "https://api.polymarket.us/v1/orders"

    @pytest.mark.asyncio
    async def test_place_order_sends_correct_body(self):
        from src.platforms.polymarket import OrderIntent, TimeInForce
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        sent_body = sess.post.call_args[1].get("json", {})
        assert sent_body["marketSlug"] == "tec-nba-mvp-2026-shagil"
        assert sent_body["intent"] == "ORDER_INTENT_BUY_LONG"
        assert sent_body["type"] == "ORDER_TYPE_LIMIT"
        assert sent_body["price"]["value"] == "0.55"
        assert sent_body["price"]["currency"] == "USD"
        assert sent_body["quantity"] == 1
        assert sent_body["tif"] == TimeInForce.FOK  # default

    @pytest.mark.asyncio
    async def test_place_order_defaults_to_fok(self):
        from src.platforms.polymarket import OrderIntent, TimeInForce
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        sent_body = sess.post.call_args[1].get("json", {})
        assert sent_body["tif"] == TimeInForce.FOK

    @pytest.mark.asyncio
    async def test_place_order_buy_short_no_side(self):
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_SHORT,
                price=0.45,
                quantity=2,
            )
        sent_body = sess.post.call_args[1].get("json", {})
        assert sent_body["intent"] == "ORDER_INTENT_BUY_SHORT"
        assert sent_body["quantity"] == 2

    @pytest.mark.asyncio
    async def test_place_order_sends_auth_headers(self):
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.55,
                quantity=1,
            )
        headers = sess.post.call_args[1].get("headers", {})
        assert "X-PM-Access-Key" in headers
        assert "X-PM-Signature" in headers
        assert "X-PM-Timestamp" in headers

    @pytest.mark.asyncio
    async def test_place_order_raises_on_400(self):
        from src.platforms.polymarket import OrderIntent, PolymarketAPIError
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(400, {"code": 2, "message": "market metadata is required"})]
            )
            with pytest.raises(PolymarketAPIError) as exc_info:
                await client.place_order(
                    market_slug="nonexistent",
                    intent=OrderIntent.BUY_LONG,
                    price=0.55,
                    quantity=1,
                )
        assert exc_info.value.status == 400

    @pytest.mark.asyncio
    async def test_place_order_raises_on_500(self):
        from src.platforms.polymarket import OrderIntent, PolymarketAPIError
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(500, {"code": 2, "message": "internal error"})]
            )
            with pytest.raises(PolymarketAPIError) as exc_info:
                await client.place_order(
                    market_slug="bad-market",
                    intent=OrderIntent.BUY_LONG,
                    price=0.55,
                    quantity=1,
                )
        assert exc_info.value.status == 500

    @pytest.mark.asyncio
    async def test_place_order_price_formatted_as_string(self):
        """Price dict value must be a string, not a float."""
        from src.platforms.polymarket import OrderIntent
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, self.SAMPLE_ORDER_FILLED)])
            mock_cls.return_value = sess
            await client.place_order(
                market_slug="tec-nba-mvp-2026-shagil",
                intent=OrderIntent.BUY_LONG,
                price=0.7280,  # should round to 4dp
                quantity=1,
            )
        sent_body = sess.post.call_args[1].get("json", {})
        assert isinstance(sent_body["price"]["value"], str)
        assert sent_body["price"]["value"] == "0.728"


class TestPolymarketClientLoadFromEnv:
    def test_load_from_env_returns_client(self, monkeypatch):
        import base64
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        pk = Ed25519PrivateKey.generate()
        seed = pk.private_bytes_raw()
        pub = pk.public_key().public_bytes_raw()
        monkeypatch.setenv("POLYMARKET_KEY_ID", "test-id")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", base64.b64encode(seed + pub).decode())
        from src.platforms.polymarket import load_from_env
        client = load_from_env()
        assert client is not None

    def test_load_from_env_fails_without_credentials(self, monkeypatch):
        monkeypatch.delenv("POLYMARKET_KEY_ID", raising=False)
        monkeypatch.delenv("POLYMARKET_SECRET_KEY", raising=False)
        from src.platforms.polymarket import load_from_env
        with pytest.raises(RuntimeError):
            load_from_env()
