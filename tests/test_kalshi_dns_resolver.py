"""
test_kalshi_dns_resolver.py

Tests that KalshiClient uses a custom DNS resolver when DNS_SERVERS env var is set.
This feature bypasses Cisco Umbrella TLS inspection on hospital/corporate networks.
"""
import os
from unittest import mock
import pytest
import aiohttp


class TestKalshiClientDNSResolver:
    """Verify DNS resolver wiring in KalshiClient.start()."""

    def test_dns_servers_parsed_from_env(self, monkeypatch):
        """_DNS_SERVERS is populated when DNS_SERVERS env var is set."""
        monkeypatch.setenv("DNS_SERVERS", "8.8.8.8,8.8.4.4")
        import importlib
        import src.platforms.kalshi as kalshi_mod
        importlib.reload(kalshi_mod)
        assert kalshi_mod._DNS_SERVERS == ["8.8.8.8", "8.8.4.4"]

    def test_dns_servers_none_when_env_unset(self, monkeypatch):
        """_DNS_SERVERS is None when DNS_SERVERS env var is not set."""
        monkeypatch.delenv("DNS_SERVERS", raising=False)
        import importlib
        import src.platforms.kalshi as kalshi_mod
        importlib.reload(kalshi_mod)
        assert kalshi_mod._DNS_SERVERS is None

    def test_dns_servers_ignores_empty_entries(self, monkeypatch):
        """Comma entries that are blank are ignored."""
        monkeypatch.setenv("DNS_SERVERS", "8.8.8.8,,  ,8.8.4.4")
        import importlib
        import src.platforms.kalshi as kalshi_mod
        importlib.reload(kalshi_mod)
        assert kalshi_mod._DNS_SERVERS == ["8.8.8.8", "8.8.4.4"]

    @pytest.mark.asyncio
    async def test_start_uses_custom_resolver_when_dns_servers_set(self, monkeypatch):
        """KalshiClient.start() creates AsyncResolver when _DNS_SERVERS is set."""
        monkeypatch.setenv("DNS_SERVERS", "8.8.8.8")
        import importlib
        import src.platforms.kalshi as kalshi_mod
        importlib.reload(kalshi_mod)

        created_resolvers = []
        original_async_resolver = aiohttp.AsyncResolver

        class MockResolver:
            def __init__(self, nameservers=None):
                created_resolvers.append(nameservers)

        with mock.patch.object(aiohttp, "AsyncResolver", MockResolver):
            with mock.patch.object(aiohttp, "TCPConnector", return_value=mock.MagicMock()):
                with mock.patch.object(aiohttp, "ClientSession", return_value=mock.MagicMock()):
                    from src.auth.kalshi_auth import KalshiAuth
                    auth = mock.MagicMock(spec=KalshiAuth)
                    client = kalshi_mod.KalshiClient(
                        auth=auth, base_url="https://trading-api.kalshi.com/trade-api/v2"
                    )
                    # Mock rate limiters to avoid asyncio complications
                    client._read_limiter = mock.MagicMock()
                    client._read_limiter.start = mock.AsyncMock()
                    client._write_limiter = mock.MagicMock()
                    client._write_limiter.start = mock.AsyncMock()
                    await client.start()

        assert len(created_resolvers) == 1
        assert created_resolvers[0] == ["8.8.8.8"]

    @pytest.mark.asyncio
    async def test_start_no_custom_resolver_when_dns_servers_unset(self, monkeypatch):
        """KalshiClient.start() does NOT use AsyncResolver when _DNS_SERVERS is None."""
        monkeypatch.delenv("DNS_SERVERS", raising=False)
        import importlib
        import src.platforms.kalshi as kalshi_mod
        importlib.reload(kalshi_mod)

        async_resolver_called = []

        class MockResolver:
            def __init__(self, **kwargs):
                async_resolver_called.append(True)

        with mock.patch.object(aiohttp, "AsyncResolver", MockResolver):
            with mock.patch.object(aiohttp, "ClientSession", return_value=mock.MagicMock()):
                from src.auth.kalshi_auth import KalshiAuth
                auth = mock.MagicMock(spec=KalshiAuth)
                client = kalshi_mod.KalshiClient(
                    auth=auth, base_url="https://trading-api.kalshi.com/trade-api/v2"
                )
                client._read_limiter = mock.MagicMock()
                client._read_limiter.start = mock.AsyncMock()
                client._write_limiter = mock.MagicMock()
                client._write_limiter.start = mock.AsyncMock()
                await client.start()

        assert len(async_resolver_called) == 0
