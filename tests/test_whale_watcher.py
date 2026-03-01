"""
Tests for whale_watcher.py — Polymarket data-api client.

API facts confirmed via live probing 2026-03-01:
  GET https://data-api.polymarket.com/trades?user={proxy_wallet}&limit=N  → 200 []
  GET https://data-api.polymarket.com/positions?user={proxy_wallet}&limit=N → 200 []
  GET https://data-api.polymarket.com/trades?limit=N  → 200 [{...recent trades...}]
  No auth required. Returns JSON array directly.

Trade fields confirmed: proxyWallet, side, asset, conditionId, size, price, timestamp,
  title, slug, outcome, outcomeIndex, transactionHash, name, pseudonym
Position fields confirmed (from docs): proxyWallet, asset, conditionId, size, avgPrice,
  currentValue, cashPnl, curPrice, title, slug, outcome, endDate, negativeRisk

Uses unittest.mock to avoid real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── shared fixtures ──────────────────────────────────────────────────


SAMPLE_TRADE_BUY = {
    "proxyWallet": "0xabc123def456abc123def456abc123def456abc1",
    "side": "BUY",
    "asset": "67261475250596079602273947215993075255055754768178515338779528591099114938883",
    "conditionId": "0xe109491cebba2d28cc8ffdb2de3463131601597f5a177fa66b12b9d7b79d38ad",
    "size": 122.13,
    "price": 0.28,
    "timestamp": 1772401117,
    "title": "Bitcoin Up or Down - March 1, 4:35PM-4:40PM ET",
    "slug": "btc-updown-5m-1772400900",
    "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/BTC+fullsize.png",
    "eventSlug": "btc-updown-5m-1772400900",
    "outcome": "Down",
    "outcomeIndex": 1,
    "name": "sala588",
    "pseudonym": "Masculine-Bafflement",
    "bio": "",
    "profileImage": "",
    "transactionHash": "0x875127da7c8acd81f79b28e9cb9504980b7f07fb8322afad031148b077568c54",
}

SAMPLE_TRADE_SELL = {
    "proxyWallet": "0xabc123def456abc123def456abc123def456abc1",
    "side": "SELL",
    "asset": "9876543210987654321",
    "conditionId": "0xaaaaabbbbbbcccccdddddeeeeeffffff00000001",
    "size": 50.0,
    "price": 0.65,
    "timestamp": 1772400000,
    "title": "Will Iran close the Strait of Hormuz before 2027?",
    "slug": "iran-hormuz-2027",
    "eventSlug": "iran-hormuz-2027",
    "outcome": "Yes",
    "outcomeIndex": 0,
    "name": "",
    "pseudonym": "",
    "bio": "",
    "profileImage": "",
    "transactionHash": "0xdeadbeef",
}

SAMPLE_POSITION = {
    "proxyWallet": "0xabc123def456abc123def456abc123def456abc1",
    "asset": "9876543210987654321",
    "conditionId": "0xaaaaabbbbbbcccccdddddeeeeeffffff00000001",
    "size": 607.0,
    "avgPrice": 0.41,
    "initialValue": 248.87,
    "currentValue": 261.01,
    "cashPnl": 12.14,
    "percentPnl": 0.0488,
    "totalBought": 248.87,
    "realizedPnl": 0.0,
    "percentRealizedPnl": 0.0,
    "curPrice": 0.43,
    "redeemable": False,
    "mergeable": False,
    "title": "Will Iran close the Strait of Hormuz before 2027?",
    "slug": "iran-hormuz-2027",
    "eventId": "42",
    "outcome": "Yes",
    "outcomeIndex": 0,
    "oppositeOutcome": "No",
    "endDate": "2027-01-01T00:00:00Z",
    "negativeRisk": False,
}


# ── mock helpers (same pattern as test_polymarket_client.py) ─────────


def _make_mock_response(status: int, body):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=body)
    resp.text = AsyncMock(return_value=json.dumps(body) if not isinstance(body, str) else body)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _make_mock_session(responses: list):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    call_count = [0]

    def get_side_effect(url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(responses):
            return responses[idx]
        return _make_mock_response(404, [])

    session.get = MagicMock(side_effect=get_side_effect)
    return session


# ── WhaleTrade dataclass tests ────────────────────────────────────────


class TestWhaleTrade:
    def test_from_dict_proxy_wallet(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert t.proxy_wallet == "0xabc123def456abc123def456abc123def456abc1"

    def test_from_dict_side_buy(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert t.side == "BUY"

    def test_from_dict_side_sell(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_SELL)
        assert t.side == "SELL"

    def test_from_dict_price_is_float(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert isinstance(t.price, float)
        assert abs(t.price - 0.28) < 1e-6

    def test_from_dict_size_is_float(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert isinstance(t.size, float)
        assert abs(t.size - 122.13) < 1e-3

    def test_from_dict_timestamp(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert t.timestamp == 1772401117

    def test_from_dict_title(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert "Bitcoin" in t.title

    def test_from_dict_outcome(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert t.outcome == "Down"

    def test_from_dict_condition_id(self):
        from src.data.whale_watcher import WhaleTrade
        t = WhaleTrade.from_dict(SAMPLE_TRADE_BUY)
        assert t.condition_id.startswith("0x")


# ── WhalePosition dataclass tests ────────────────────────────────────


class TestWhalePosition:
    def test_from_dict_proxy_wallet(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert p.proxy_wallet == "0xabc123def456abc123def456abc123def456abc1"

    def test_from_dict_avg_price(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert abs(p.avg_price - 0.41) < 1e-6

    def test_from_dict_cur_price(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert abs(p.cur_price - 0.43) < 1e-6

    def test_from_dict_cash_pnl(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert abs(p.cash_pnl - 12.14) < 1e-3

    def test_from_dict_outcome(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert p.outcome == "Yes"

    def test_from_dict_end_date(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert p.end_date == "2027-01-01T00:00:00Z"

    def test_from_dict_end_date_none_when_missing(self):
        from src.data.whale_watcher import WhalePosition
        data = dict(SAMPLE_POSITION)
        del data["endDate"]
        p = WhalePosition.from_dict(data)
        assert p.end_date is None

    def test_from_dict_size(self):
        from src.data.whale_watcher import WhalePosition
        p = WhalePosition.from_dict(SAMPLE_POSITION)
        assert abs(p.size - 607.0) < 1e-3


# ── WhaleDataClient tests ─────────────────────────────────────────────


class TestWhaleDataClient:
    def _make_client(self):
        from src.data.whale_watcher import WhaleDataClient
        return WhaleDataClient(timeout_sec=5.0)

    @pytest.mark.asyncio
    async def test_get_trades_returns_list(self):
        client = self._make_client()
        body = [SAMPLE_TRADE_BUY, SAMPLE_TRADE_SELL]
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_trades("0xabc123", limit=10)
        assert len(result) == 2
        assert result[0].side == "BUY"
        assert result[1].side == "SELL"

    @pytest.mark.asyncio
    async def test_get_trades_returns_empty_on_http_error(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(500, [])]
            )
            result = await client.get_trades("0xabc123", limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_trades_returns_empty_on_exception(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            session.get = MagicMock(side_effect=Exception("timeout"))
            mock_cls.return_value = session
            result = await client.get_trades("0xabc123", limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_trades_user_param_in_url(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, [])])
            mock_cls.return_value = sess
            await client.get_trades("0xabc123def", limit=5)
        call_url = sess.get.call_args[0][0]
        assert "0xabc123def" in call_url

    @pytest.mark.asyncio
    async def test_get_trades_limit_param_in_url(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, [])])
            mock_cls.return_value = sess
            await client.get_trades("0xabc123", limit=7)
        call_url = sess.get.call_args[0][0]
        assert "limit=7" in call_url

    @pytest.mark.asyncio
    async def test_get_trades_since_ts_filters_old_trades(self):
        """Trades with timestamp <= since_ts are filtered out client-side."""
        client = self._make_client()
        old_trade = dict(SAMPLE_TRADE_SELL, timestamp=1000000)
        new_trade = dict(SAMPLE_TRADE_BUY, timestamp=2000000)
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [old_trade, new_trade])]
            )
            result = await client.get_trades("0xabc123", limit=10, since_ts=1500000)
        assert len(result) == 1
        assert result[0].timestamp == 2000000

    @pytest.mark.asyncio
    async def test_get_global_trades_no_user_param(self):
        """get_global_trades() must NOT include a user= param in the URL."""
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, [SAMPLE_TRADE_BUY])])
            mock_cls.return_value = sess
            await client.get_global_trades(limit=5)
        call_url = sess.get.call_args[0][0]
        assert "user=" not in call_url

    @pytest.mark.asyncio
    async def test_get_global_trades_returns_list(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [SAMPLE_TRADE_BUY])]
            )
            result = await client.get_global_trades(limit=5)
        assert len(result) == 1
        assert result[0].title == "Bitcoin Up or Down - March 1, 4:35PM-4:40PM ET"

    @pytest.mark.asyncio
    async def test_get_positions_returns_list(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [SAMPLE_POSITION])]
            )
            result = await client.get_positions("0xabc123", limit=10)
        assert len(result) == 1
        assert result[0].outcome == "Yes"
        assert abs(result[0].avg_price - 0.41) < 1e-6

    @pytest.mark.asyncio
    async def test_get_positions_returns_empty_on_http_error(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(503, [])]
            )
            result = await client.get_positions("0xabc123", limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_positions_user_param_in_url(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, [])])
            mock_cls.return_value = sess
            await client.get_positions("0xdeadbeef99", limit=5)
        call_url = sess.get.call_args[0][0]
        assert "0xdeadbeef99" in call_url
