"""
Tests for predicting_top.py — whale leaderboard client.

API facts confirmed via live probing 2026-03-01:
  GET https://predicting.top/api/leaderboard?limit=N
  Returns JSON array of trader objects, no auth required.
  144/179 traders have wallet addresses (proxy wallets matching data-api.polymarket.com format).

Uses unittest.mock to avoid real network calls.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── shared fixtures ──────────────────────────────────────────────────


SAMPLE_TRADER_FULL = {
    "name": "aenews",
    "wallet": "0xabc123def456abc123def456abc123def456abc1",
    "additional_wallets": ["0xdef456abc123def456abc123def456abc123def4"],
    "wallet_count": 2,
    "smart_score": 87.5,
    "twitter": "@aenews",
    "pfp": "https://example.com/pfp.jpg",
    "stats": {"wins": 42, "losses": 8},
    "join_date": "2024-01-15",
    "polymarket_profile": "https://polymarket.com/profile/0xabc123...",
    "kalshi_profile": None,
}

SAMPLE_TRADER_NO_TWITTER = {
    "name": "silenttrader",
    "wallet": "0x111222333444555666777888999000aaabbbccc1",
    "additional_wallets": [],
    "wallet_count": 1,
    "smart_score": 72.0,
    "twitter": None,
    "pfp": "",
    "stats": {},
    "join_date": "2025-03-01",
    "polymarket_profile": None,
    "kalshi_profile": None,
}

SAMPLE_TRADER_NO_WALLET = {
    "name": "nowallet",
    "wallet": None,
    "additional_wallets": [],
    "wallet_count": 0,
    "smart_score": 55.0,
    "twitter": "@nowallet",
}

SAMPLE_TRADER_EMPTY_WALLET = {
    "name": "emptywallet",
    "wallet": "",
    "additional_wallets": [],
    "wallet_count": 0,
    "smart_score": 61.0,
    "twitter": None,
}


# ── mock helpers ─────────────────────────────────────────────────────


def _make_mock_response(status: int, body):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=body)
    resp.text = AsyncMock(return_value=json.dumps(body))
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


# ── WhaleAccount dataclass tests ─────────────────────────────────────


class TestWhaleAccount:
    def test_from_dict_parses_name(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert acct.name == "aenews"

    def test_from_dict_parses_proxy_wallet(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert acct.proxy_wallet == "0xabc123def456abc123def456abc123def456abc1"

    def test_from_dict_all_wallets_includes_primary(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert "0xabc123def456abc123def456abc123def456abc1" in acct.all_wallets

    def test_from_dict_all_wallets_includes_additional(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert "0xdef456abc123def456abc123def456abc123def4" in acct.all_wallets
        assert len(acct.all_wallets) == 2

    def test_from_dict_no_additional_wallets(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_NO_TWITTER)
        assert acct.all_wallets == ["0x111222333444555666777888999000aaabbbccc1"]

    def test_from_dict_smart_score_float(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert isinstance(acct.smart_score, float)
        assert abs(acct.smart_score - 87.5) < 1e-6

    def test_from_dict_smart_score_nested_dict(self):
        """API changed smart_score from float to nested dict — extract .score."""
        from src.data.predicting_top import WhaleAccount
        trader = dict(SAMPLE_TRADER_FULL)
        trader["smart_score"] = {"tier": "Great", "score": 79.2, "winRate": 0.606}
        acct = WhaleAccount.from_dict(trader)
        assert isinstance(acct.smart_score, float)
        assert abs(acct.smart_score - 79.2) < 1e-6

    def test_from_dict_twitter_present(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_FULL)
        assert acct.twitter == "@aenews"

    def test_from_dict_twitter_none(self):
        from src.data.predicting_top import WhaleAccount
        acct = WhaleAccount.from_dict(SAMPLE_TRADER_NO_TWITTER)
        assert acct.twitter is None


# ── PredictingTopClient tests ─────────────────────────────────────────


class TestPredictingTopClient:
    def _make_client(self):
        from src.data.predicting_top import PredictingTopClient
        return PredictingTopClient(timeout_sec=5.0)

    @pytest.mark.asyncio
    async def test_get_leaderboard_returns_accounts(self):
        client = self._make_client()
        body = [SAMPLE_TRADER_FULL, SAMPLE_TRADER_NO_TWITTER]
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_leaderboard(limit=10)
        assert len(result) == 2
        assert result[0].name == "aenews"
        assert result[1].name == "silenttrader"

    @pytest.mark.asyncio
    async def test_get_leaderboard_skips_null_wallet(self):
        client = self._make_client()
        body = [SAMPLE_TRADER_FULL, SAMPLE_TRADER_NO_WALLET]
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_leaderboard(limit=10)
        assert len(result) == 1
        assert result[0].name == "aenews"

    @pytest.mark.asyncio
    async def test_get_leaderboard_skips_empty_wallet(self):
        client = self._make_client()
        body = [SAMPLE_TRADER_FULL, SAMPLE_TRADER_EMPTY_WALLET]
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_leaderboard(limit=10)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_leaderboard_returns_empty_on_http_error(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(500, {"error": "internal"})]
            )
            result = await client.get_leaderboard(limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_leaderboard_returns_empty_on_exception(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            session = MagicMock()
            session.__aenter__ = AsyncMock(return_value=session)
            session.__aexit__ = AsyncMock(return_value=None)
            session.get = MagicMock(side_effect=Exception("network error"))
            mock_cls.return_value = session
            result = await client.get_leaderboard(limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_leaderboard_limit_in_url(self):
        client = self._make_client()
        body = [SAMPLE_TRADER_FULL]
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, body)])
            mock_cls.return_value = sess
            await client.get_leaderboard(limit=25)
        call_url = sess.get.call_args[0][0]
        assert "limit=25" in call_url

    @pytest.mark.asyncio
    async def test_get_leaderboard_empty_array_response(self):
        client = self._make_client()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [])]
            )
            result = await client.get_leaderboard(limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_leaderboard_wrapped_traders_key(self):
        """API now returns {"traders": [...]} instead of bare list — must unwrap."""
        client = self._make_client()
        body = {"traders": [SAMPLE_TRADER_FULL, SAMPLE_TRADER_NO_TWITTER]}
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_leaderboard(limit=10)
        assert len(result) == 2
        assert result[0].name == "aenews"

    @pytest.mark.asyncio
    async def test_get_leaderboard_unexpected_dict_no_traders_key(self):
        """Dict without 'traders' key → empty list, no crash."""
        client = self._make_client()
        body = {"error": "rate limited"}
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, body)]
            )
            result = await client.get_leaderboard(limit=10)
        assert result == []
