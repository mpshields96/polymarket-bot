"""
Tests for ETH feed + strategy support.

Verifies:
- load_eth_from_config() produces a BinanceFeed with ETH URL
- load_eth_lag_from_config() returns BTCLagStrategy named eth_lag_v1
- load_eth_drift_from_config() returns BTCDriftStrategy named eth_drift_v1
- name_override is respected on both strategy classes
- Near-miss INFO log for btc_drift fires at INFO level
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

from src.data.binance import BinanceFeed, load_eth_from_config, _BINANCE_ETH_WS_URL
from src.strategies.btc_lag import BTCLagStrategy, load_eth_lag_from_config
from src.strategies.btc_drift import BTCDriftStrategy, load_eth_drift_from_config


# ── Feed factory ──────────────────────────────────────────────────────


class TestEthFeed:
    def test_load_eth_from_config_returns_binance_feed(self):
        feed = load_eth_from_config()
        assert isinstance(feed, BinanceFeed)

    def test_eth_feed_uses_eth_url(self):
        feed = load_eth_from_config()
        assert "ethusdt" in feed._ws_url
        assert "binance.us" in feed._ws_url

    def test_eth_feed_url_constant_is_eth(self):
        assert "ethusdt" in _BINANCE_ETH_WS_URL
        assert "btcusdt" not in _BINANCE_ETH_WS_URL


# ── BTCLagStrategy name override ──────────────────────────────────────


class TestLagNameOverride:
    def test_default_name_is_btc_lag_v1(self):
        s = BTCLagStrategy()
        assert s.name == "btc_lag_v1"

    def test_name_override_sets_name(self):
        s = BTCLagStrategy(name_override="eth_lag_v1")
        assert s.name == "eth_lag_v1"

    def test_eth_lag_factory_name(self):
        s = load_eth_lag_from_config()
        assert s.name == "eth_lag_v1"

    def test_eth_lag_factory_returns_strategy_instance(self):
        s = load_eth_lag_from_config()
        assert isinstance(s, BTCLagStrategy)


# ── BTCDriftStrategy name override ───────────────────────────────────


class TestDriftNameOverride:
    def test_default_name_is_btc_drift_v1(self):
        s = BTCDriftStrategy()
        assert s.name == "btc_drift_v1"

    def test_name_override_sets_name(self):
        s = BTCDriftStrategy(name_override="eth_drift_v1")
        assert s.name == "eth_drift_v1"

    def test_eth_drift_factory_name(self):
        s = load_eth_drift_from_config()
        assert s.name == "eth_drift_v1"

    def test_eth_drift_factory_returns_strategy_instance(self):
        s = load_eth_drift_from_config()
        assert isinstance(s, BTCDriftStrategy)


# ── Near-miss INFO log for btc_drift ─────────────────────────────────


class TestDriftNearMissLog:
    """When BTC drift is below min_drift_pct, btc_drift logs at INFO (not just DEBUG)."""

    def _make_market(self, yes_price=50, no_price=50):
        from datetime import datetime, timedelta, timezone
        from src.platforms.kalshi import Market
        now = datetime.now(timezone.utc)
        return Market(
            ticker="KXETH15M-TEST",
            title="Test market",
            event_ticker="KXETH15M",
            status="open",
            yes_price=yes_price,
            no_price=no_price,
            volume=1000,
            close_time=(now + timedelta(minutes=10)).isoformat(),
            open_time=(now - timedelta(minutes=5)).isoformat(),
            result=None,
            raw={},
        )

    def _make_orderbook(self):
        from src.platforms.kalshi import OrderBook
        return OrderBook(yes_bids=[], no_bids=[])

    def _make_feed(self, current_price=1000.0):
        feed = MagicMock()
        feed.is_stale = False
        feed.current_price.return_value = current_price
        return feed

    def test_near_miss_logs_at_info_level(self, caplog):
        """When drift < min_drift_pct, an INFO log is emitted."""
        s = BTCDriftStrategy(min_drift_pct=0.5)  # need 0.5% drift
        market = self._make_market()
        ob = self._make_orderbook()

        # Seed reference at 1000
        feed = self._make_feed(current_price=1000.0)
        s.generate_signal(market, ob, feed)

        # Very tiny drift — below 0.5% threshold
        feed2 = self._make_feed(current_price=1001.0)  # only 0.1% drift
        with caplog.at_level(logging.INFO, logger="src.strategies.btc_drift"):
            result = s.generate_signal(market, ob, feed2)

        assert result is None
        info_msgs = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_msgs) >= 1
        assert "drift" in info_msgs[0].message.lower()
