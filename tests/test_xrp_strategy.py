"""
Tests for XRP 15-min drift strategy and Binance XRP feed.

Verifies:
- _BINANCE_XRP_WS_URL constant points to Binance.US xrpusdt@bookTicker
- load_xrp_from_config() returns BinanceFeed with correct XRP URL
- load_xrp_drift_from_config() returns BTCDriftStrategy named xrp_drift_v1
- XRP drift min_drift_pct >= 0.10 (XRP ~2x more volatile than BTC)
- XRP drift min_edge_pct is set
- XRP feed window is 60s
- Strategy does NOT fire on sub-threshold drift
"""

from __future__ import annotations

import time
from collections import deque
from unittest.mock import MagicMock

import pytest

from src.data.binance import BinanceFeed, load_xrp_from_config, _BINANCE_XRP_WS_URL
from src.strategies.btc_drift import BTCDriftStrategy, load_xrp_drift_from_config
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── XRP feed factory ──────────────────────────────────────────────────


class TestXrpFeed:
    def test_load_xrp_from_config_returns_binance_feed(self):
        feed = load_xrp_from_config()
        assert isinstance(feed, BinanceFeed)

    def test_xrp_feed_uses_xrp_url(self):
        feed = load_xrp_from_config()
        assert "xrpusdt" in feed._ws_url.lower()
        assert "binance.us" in feed._ws_url

    def test_xrp_feed_url_constant_is_xrp(self):
        assert "xrpusdt" in _BINANCE_XRP_WS_URL.lower()
        assert "binance.us" in _BINANCE_XRP_WS_URL
        assert "btcusdt" not in _BINANCE_XRP_WS_URL
        assert "ethusdt" not in _BINANCE_XRP_WS_URL
        assert "solusdt" not in _BINANCE_XRP_WS_URL

    def test_xrp_feed_uses_60s_window(self):
        feed = load_xrp_from_config()
        assert feed._window_sec == 60


# ── XRP drift strategy factory ────────────────────────────────────────


class TestXrpDriftStrategy:
    def test_load_xrp_drift_from_config_returns_strategy(self):
        strategy = load_xrp_drift_from_config()
        assert isinstance(strategy, BTCDriftStrategy)

    def test_xrp_drift_strategy_name(self):
        strategy = load_xrp_drift_from_config()
        assert strategy.name == "xrp_drift_v1"

    def test_xrp_drift_min_drift_pct_scaled_for_volatility(self):
        """XRP ~2x more volatile than BTC → min_drift_pct must be >= 0.10."""
        strategy = load_xrp_drift_from_config()
        assert strategy._min_drift_pct >= 0.10, (
            f"XRP drift min_drift_pct={strategy._min_drift_pct:.3f} is too low. "
            "XRP is ~2x more volatile than BTC; threshold must be >= 0.10 to maintain signal quality."
        )

    def test_xrp_drift_min_edge_pct_set(self):
        strategy = load_xrp_drift_from_config()
        assert strategy._min_edge_pct > 0.0
        assert strategy._min_edge_pct <= 0.15  # reasonable upper bound

    def test_xrp_drift_not_btc_strategy_name(self):
        """XRP strategy must have xrp_drift name, not btc/eth/sol."""
        strategy = load_xrp_drift_from_config()
        assert "btc" not in strategy.name.lower()
        assert "eth" not in strategy.name.lower()
        assert "sol" not in strategy.name.lower()


# ── XRP drift signal generation ───────────────────────────────────────


def _make_xrp_feed_with_move(move_pct: float, base_price: float = 0.55) -> BinanceFeed:
    """Build a BinanceFeed with a synthetic price history producing the given move_pct.
    Uses the XRP URL but never connects (no live test).
    """
    from collections import deque
    feed = BinanceFeed(ws_url=_BINANCE_XRP_WS_URL)
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


def _make_near50_market(price_cents: int = 50) -> Market:
    import datetime
    close_dt = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=10)
    return Market(
        ticker="KXXRP15M-25Mar0907-T2.3",
        event_ticker="KXXRP15M-25Mar0907",
        title="Will XRP be above $2.30 at 9:07am on March 25?",
        status="active",
        yes_price=price_cents,
        no_price=100 - price_cents,
        volume=5000,
        close_time=close_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        open_time=close_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


def _make_empty_book() -> OrderBook:
    return OrderBook(yes_bids=[], no_bids=[])


def _seed_xrp_reference(strategy: BTCDriftStrategy, market: Market, ref_price: float) -> None:
    """Seed the strategy's reference price by calling generate_signal once (returns None)."""
    from collections import deque
    feed = BinanceFeed(ws_url=_BINANCE_XRP_WS_URL)
    now = time.time()
    feed._history = deque([(now - 1, ref_price)])
    feed._last_price = ref_price
    feed._last_update = now - 1
    result = strategy.generate_signal(market, _make_empty_book(), feed)
    assert result is None, "First call should return None (sets reference)"


class TestXrpDriftSignals:
    def test_xrp_drift_first_call_returns_none(self):
        """First generate_signal call must return None (sets reference, no drift yet)."""
        strategy = load_xrp_drift_from_config()
        feed = _make_xrp_feed_with_move(+0.25)
        market = _make_near50_market(price_cents=50)
        book = _make_empty_book()
        signal = strategy.generate_signal(market, book, feed)
        assert signal is None, "First call must return None (reference-setting phase)"

    def test_xrp_drift_fires_above_threshold(self):
        """With +0.25% XRP drift from reference, strategy should fire (2.5x threshold)."""
        strategy = load_xrp_drift_from_config()
        market = _make_near50_market(price_cents=50)
        # Seed reference at base price
        _seed_xrp_reference(strategy, market, ref_price=0.55)
        # Now create feed showing +0.25% drift from 0.55
        feed = _make_xrp_feed_with_move(+0.25)
        book = _make_empty_book()
        signal = strategy.generate_signal(market, book, feed)
        assert signal is not None, (
            "Expected a signal with +0.25% XRP drift from reference at near-50¢ market"
        )

    def test_xrp_drift_no_signal_below_threshold(self):
        """With tiny XRP drift, strategy should NOT fire."""
        strategy = load_xrp_drift_from_config()
        market = _make_near50_market(price_cents=50)
        # Seed reference at same price as the move (so drift is tiny)
        _seed_xrp_reference(strategy, market, ref_price=0.55)
        feed = _make_xrp_feed_with_move(+0.01)  # only 0.01% drift
        book = _make_empty_book()
        signal = strategy.generate_signal(market, book, feed)
        assert signal is None, (
            "Expected no signal on 0.01% XRP drift (below min_drift_pct=0.10 threshold)"
        )

    def test_xrp_drift_respects_price_range_guard(self):
        """Market at extreme price (e.g. 20¢) should not fire."""
        strategy = load_xrp_drift_from_config()
        market = _make_near50_market(price_cents=20)  # outside 35-65¢ guard
        _seed_xrp_reference(strategy, market, ref_price=0.55)
        feed = _make_xrp_feed_with_move(+0.25)
        book = _make_empty_book()
        signal = strategy.generate_signal(market, book, feed)
        assert signal is None, (
            "Expected no signal when market price is outside 35-65¢ guard"
        )
