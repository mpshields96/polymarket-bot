"""
Tests for CoinbasePriceFeed and DualPriceFeed.

TDD — these tests were written BEFORE the implementation.
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCoinbasePriceFeed:
    """Tests for CoinbasePriceFeed (REST polling backup feed)."""

    def test_initial_state_is_stale(self):
        """Feed starts with no price — must be stale until first poll."""
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="BTC")
        assert feed.is_stale is True
        assert feed.current_price() is None

    def test_symbol_builds_correct_url(self):
        """URL uses symbol correctly."""
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="ETH")
        assert "ETH-USD" in feed._url

    def test_btc_symbol_url(self):
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="BTC")
        assert "BTC-USD" in feed._url

    def test_sol_symbol_url(self):
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="SOL")
        assert "SOL-USD" in feed._url

    def test_xrp_symbol_url(self):
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="XRP")
        assert "XRP-USD" in feed._url

    async def test_poll_updates_price(self):
        """A successful poll sets _price and _last_update."""
        from src.data.coinbase import CoinbasePriceFeed

        feed = CoinbasePriceFeed(symbol="BTC")
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "data": {"base": "BTC", "currency": "USD", "amount": "67500.00"}
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.data.coinbase.aiohttp.ClientSession", return_value=mock_session):
            await feed._poll_once()

        assert feed.current_price() == pytest.approx(67500.00)
        assert not feed.is_stale

    async def test_poll_handles_http_error_gracefully(self):
        """Non-200 response: price stays None, no exception raised."""
        from src.data.coinbase import CoinbasePriceFeed

        feed = CoinbasePriceFeed(symbol="BTC")
        mock_response = AsyncMock()
        mock_response.status = 429  # rate limited
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.data.coinbase.aiohttp.ClientSession", return_value=mock_session):
            await feed._poll_once()  # must not raise

        assert feed.current_price() is None
        assert feed.is_stale

    async def test_poll_handles_network_exception(self):
        """Network exception: price stays None, no exception raised."""
        from src.data.coinbase import CoinbasePriceFeed

        feed = CoinbasePriceFeed(symbol="BTC")
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=Exception("Connection refused"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("src.data.coinbase.aiohttp.ClientSession", return_value=mock_session):
            await feed._poll_once()  # must not raise

        assert feed.current_price() is None

    def test_is_stale_after_threshold(self):
        """is_stale returns True once STALE_THRESHOLD_SEC passes since last update."""
        from src.data.coinbase import CoinbasePriceFeed, _STALE_THRESHOLD_SEC
        feed = CoinbasePriceFeed(symbol="BTC")
        feed._price = 67000.0
        feed._last_update = time.time() - _STALE_THRESHOLD_SEC - 1  # just past threshold
        assert feed.is_stale is True

    def test_is_not_stale_within_threshold(self):
        from src.data.coinbase import CoinbasePriceFeed
        feed = CoinbasePriceFeed(symbol="BTC")
        feed._price = 67000.0
        feed._last_update = time.time() - 5  # 5s ago — well within threshold
        assert feed.is_stale is False


class TestDualPriceFeed:
    """Tests for DualPriceFeed — returns primary (Binance) or backup (Coinbase)."""

    def _make_binance_feed(self, price: float, stale: bool) -> MagicMock:
        feed = MagicMock()
        feed.is_stale = stale
        feed.current_price.return_value = None if stale else price
        return feed

    def _make_coinbase_feed(self, price: float, stale: bool) -> MagicMock:
        feed = MagicMock()
        feed.is_stale = stale
        feed.current_price.return_value = None if stale else price
        return feed

    def test_returns_primary_when_not_stale(self):
        """Returns Binance price when Binance is fresh."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(67000.0, stale=False)
        backup = self._make_coinbase_feed(67001.0, stale=False)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.current_price() == pytest.approx(67000.0)

    def test_falls_back_to_coinbase_when_binance_stale(self):
        """Falls back to Coinbase when Binance is stale."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(0.0, stale=True)
        backup = self._make_coinbase_feed(67001.0, stale=False)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.current_price() == pytest.approx(67001.0)

    def test_is_stale_only_when_both_stale(self):
        """is_stale True only when both feeds are stale."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(0.0, stale=True)
        backup = self._make_coinbase_feed(0.0, stale=True)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.is_stale is True

    def test_not_stale_when_primary_fresh(self):
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(67000.0, stale=False)
        backup = self._make_coinbase_feed(0.0, stale=True)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.is_stale is False

    def test_not_stale_when_backup_fresh(self):
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(0.0, stale=True)
        backup = self._make_coinbase_feed(67001.0, stale=False)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.is_stale is False

    def test_returns_none_when_both_stale(self):
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(0.0, stale=True)
        backup = self._make_coinbase_feed(0.0, stale=True)
        dual = DualPriceFeed(primary=primary, backup=backup)
        assert dual.current_price() is None

    def test_logs_warning_on_fallback(self, caplog):
        """Logs a WARNING when falling back to Coinbase."""
        import logging
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(0.0, stale=True)
        backup = self._make_coinbase_feed(67001.0, stale=False)
        dual = DualPriceFeed(primary=primary, backup=backup)
        with caplog.at_level(logging.WARNING):
            dual.current_price()
        assert any("fallback" in r.message.lower() or "coinbase" in r.message.lower()
                   for r in caplog.records)

    def test_btc_move_pct_delegates_to_primary(self):
        """btc_move_pct() always uses the primary (Binance) feed's history."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(67000.0, stale=False)
        primary.btc_move_pct = MagicMock(return_value=0.15)
        backup = self._make_coinbase_feed(67001.0, stale=False)
        dual = DualPriceFeed(primary=primary, backup=backup)
        result = dual.btc_move_pct()
        assert result == pytest.approx(0.15)
        primary.btc_move_pct.assert_called_once()

    async def test_stop_calls_both_feeds(self):
        """stop() stops both primary and backup feeds."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(67000.0, stale=False)
        primary.stop = AsyncMock()
        backup = self._make_coinbase_feed(67001.0, stale=False)
        backup.stop = AsyncMock()
        dual = DualPriceFeed(primary=primary, backup=backup)
        await dual.stop()
        primary.stop.assert_called_once()
        backup.stop.assert_called_once()

    async def test_stop_tolerates_primary_without_stop(self):
        """stop() works even if primary lacks a stop() method."""
        from src.data.coinbase import DualPriceFeed
        primary = self._make_binance_feed(67000.0, stale=False)
        # MagicMock has no stop attr by default unless set explicitly
        del primary.stop  # ensure no stop method
        backup = self._make_coinbase_feed(67001.0, stale=False)
        backup.stop = AsyncMock()
        dual = DualPriceFeed(primary=primary, backup=backup)
        await dual.stop()  # must not raise
        backup.stop.assert_called_once()
