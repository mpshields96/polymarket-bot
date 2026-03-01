"""
Tests for SOL 15-min lag strategy and Binance SOL feed.

Verifies:
- load_sol_from_config() returns BinanceFeed with Binance.US SOL URL
- load_sol_lag_from_config() returns BTCLagStrategy named sol_lag_v1
- SOL strategy parameters differ from BTC (higher move threshold for volatility)
- generate_signal() works with SOL feed and KXSOL15M markets
- SOL feed URL constant is correct
"""

from __future__ import annotations

import time
from collections import deque
from unittest.mock import MagicMock

import pytest

from src.data.binance import BinanceFeed, load_sol_from_config, _BINANCE_SOL_WS_URL
from src.strategies.btc_lag import BTCLagStrategy, load_sol_lag_from_config
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── SOL feed factory ──────────────────────────────────────────────────


class TestSolFeed:
    def test_load_sol_from_config_returns_binance_feed(self):
        feed = load_sol_from_config()
        assert isinstance(feed, BinanceFeed)

    def test_sol_feed_uses_sol_url(self):
        feed = load_sol_from_config()
        assert "solusdt" in feed._ws_url.lower()
        assert "binance.us" in feed._ws_url

    def test_sol_feed_url_constant_is_sol(self):
        assert "solusdt" in _BINANCE_SOL_WS_URL.lower()
        assert "binance.us" in _BINANCE_SOL_WS_URL
        assert "btcusdt" not in _BINANCE_SOL_WS_URL
        assert "ethusdt" not in _BINANCE_SOL_WS_URL

    def test_sol_feed_uses_60s_window(self):
        feed = load_sol_from_config()
        assert feed._window_sec == 60


# ── SOL strategy factory ──────────────────────────────────────────────


class TestSolLagFactory:
    def test_load_sol_lag_from_config_returns_strategy(self):
        strategy = load_sol_lag_from_config()
        assert isinstance(strategy, BTCLagStrategy)

    def test_sol_lag_name_is_sol_lag_v1(self):
        strategy = load_sol_lag_from_config()
        assert strategy.name == "sol_lag_v1"

    def test_sol_lag_name_override_is_set(self):
        strategy = load_sol_lag_from_config()
        assert strategy._name_override == "sol_lag_v1"

    def test_sol_lag_has_higher_move_threshold_than_btc(self):
        """SOL is more volatile than BTC — threshold should be >= BTC's 0.4%."""
        strategy = load_sol_lag_from_config()
        assert strategy._min_btc_move_pct >= 0.4

    def test_sol_lag_min_edge_pct_is_reasonable(self):
        """Should be at or below 0.08 (8%) — otherwise no signals will fire."""
        strategy = load_sol_lag_from_config()
        assert 0.02 <= strategy._min_edge_pct <= 0.08

    def test_sol_lag_lag_sensitivity_is_positive(self):
        strategy = load_sol_lag_from_config()
        assert strategy._lag_sensitivity > 0

    def test_sol_lag_min_minutes_remaining_is_positive(self):
        strategy = load_sol_lag_from_config()
        assert strategy._min_minutes_remaining > 0


# ── SOL signal generation ─────────────────────────────────────────────


def _make_sol_market(
    yes_price: int = 50,
    no_price: int = 50,
    ticker: str = "KXSOL15M-26MAR011500-00",
    close_minutes_from_now: float = 10.0,
) -> Market:
    """Helper: build a KXSOL15M market with given prices."""
    import datetime
    close_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=close_minutes_from_now)
    return Market(
        ticker=ticker,
        title="SOL price up in next 15 mins?",
        event_ticker="KXSOL15M-26MAR011500",
        status="active",
        yes_price=yes_price,
        no_price=no_price,
        volume=5000,
        close_time=close_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        open_time=close_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _make_sol_orderbook(yes_bid: int = 48, no_bid: int = 48) -> OrderBook:
    return OrderBook(
        yes_bids=[OrderBookLevel(price=yes_bid, quantity=50)],
        no_bids=[OrderBookLevel(price=no_bid, quantity=50)],
    )


def _make_sol_feed_with_move(move_pct: float, base_price: float = 85.0) -> BinanceFeed:
    """
    Build a BinanceFeed with a synthetic price history producing the given move_pct.
    Uses the SOL URL but never connects (no live test).
    """
    feed = BinanceFeed(ws_url=_BINANCE_SOL_WS_URL)
    now = time.time()
    old_price = base_price
    new_price = base_price * (1 + move_pct / 100.0)
    # Two data points spanning the 60-second window
    feed._history = deque([
        (now - 59, old_price),
        (now - 1, new_price),
    ])
    feed._last_price = new_price
    feed._last_update = now - 1  # fresh, not stale
    return feed


class TestSolSignalGeneration:
    def setup_method(self):
        self.strategy = BTCLagStrategy(
            min_btc_move_pct=0.8,
            min_kalshi_lag_cents=5,
            min_minutes_remaining=5,
            min_edge_pct=0.04,
            lag_sensitivity=15.0,
            name_override="sol_lag_v1",
        )

    def test_signal_fires_on_large_sol_up_move(self):
        """SOL +1.5% move should generate a YES signal."""
        market = _make_sol_market(yes_price=35, no_price=65)
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(+1.5)

        signal = self.strategy.generate_signal(market, ob, feed)
        assert signal is not None
        assert signal.side == "yes"
        assert signal.edge_pct > 0.04

    def test_signal_fires_on_large_sol_down_move(self):
        """SOL -1.5% move should generate a NO signal."""
        market = _make_sol_market(yes_price=65, no_price=35)
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(-1.5)

        signal = self.strategy.generate_signal(market, ob, feed)
        assert signal is not None
        assert signal.side == "no"

    def test_no_signal_on_small_sol_move(self):
        """SOL +0.3% move (below 0.8% threshold) should return None."""
        market = _make_sol_market()
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(+0.3)

        signal = self.strategy.generate_signal(market, ob, feed)
        assert signal is None

    def test_no_signal_when_feed_stale(self):
        """Stale feed should block signal."""
        market = _make_sol_market()
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(+2.0)
        feed._last_update = time.time() - 100  # make stale

        signal = self.strategy.generate_signal(market, ob, feed)
        assert signal is None

    def test_no_signal_when_time_almost_up(self):
        """< 5 minutes remaining should block signal."""
        market = _make_sol_market(close_minutes_from_now=3.0)
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(+2.0)

        signal = self.strategy.generate_signal(market, ob, feed)
        assert signal is None

    def test_signal_ticker_matches_sol_market(self):
        """Signal ticker should come from the SOL market, not BTC."""
        ticker = "KXSOL15M-26MAR011500-15"
        market = _make_sol_market(ticker=ticker, yes_price=30)
        ob = _make_sol_orderbook()
        feed = _make_sol_feed_with_move(+2.0)

        signal = self.strategy.generate_signal(market, ob, feed)
        if signal:
            assert signal.ticker == ticker

    def test_strategy_name_is_sol_lag_v1(self):
        assert self.strategy.name == "sol_lag_v1"
