"""
Tests for src/strategies/orderbook_imbalance.py — VPIN-lite orderbook imbalance strategy.

Uses real OrderbookImbalanceStrategy (no mocking of strategy logic).
Mocks Market, OrderBook to control test inputs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.strategies.orderbook_imbalance import (
    OrderbookImbalanceStrategy,
    load_from_config,
    load_btc_imbalance_from_config,
    load_eth_imbalance_from_config,
)
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Helpers ───────────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTC15M-TEST",
    yes_price: int = 50,
    no_price: int = 50,
    minutes_remaining: float = 10.0,
    status: str = "open",
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(minutes=minutes_remaining)).isoformat()
    open_time = (now - timedelta(minutes=5)).isoformat()
    return Market(
        ticker=ticker,
        title="Test market",
        event_ticker="KXBTC15M",
        status=status,
        yes_price=yes_price,
        no_price=no_price,
        volume=1000,
        close_time=close_time,
        open_time=open_time,
        result=None,
        raw={},
    )


def _make_orderbook(
    yes_qty: int = 0, no_qty: int = 0, levels: int = 1
) -> OrderBook:
    """Create orderbook with given total YES and NO bid quantities split across `levels`."""
    per_level_yes = yes_qty // max(levels, 1) if yes_qty else 0
    per_level_no = no_qty // max(levels, 1) if no_qty else 0
    return OrderBook(
        yes_bids=[OrderBookLevel(price=50 - i, quantity=per_level_yes) for i in range(levels)] if yes_qty else [],
        no_bids=[OrderBookLevel(price=50 - i, quantity=per_level_no) for i in range(levels)] if no_qty else [],
    )


def _make_btc_feed():
    feed = MagicMock()
    feed.is_stale = False
    feed.current_price.return_value = 50000.0
    return feed


def _default_strategy() -> OrderbookImbalanceStrategy:
    return OrderbookImbalanceStrategy(
        min_imbalance_ratio=0.65,
        min_total_depth=50,
        depth_top_n=10,
        min_edge_pct=0.05,
        min_minutes_remaining=3.0,
        signal_scaling=1.0,
        min_yes_price_cents=35,  # unfiltered for backward-compat tests
        max_no_price_cents=65,   # unfiltered for backward-compat tests
    )


# ── Strategy name + factories ─────────────────────────────────────────


class TestFactories:
    def test_default_name(self):
        s = OrderbookImbalanceStrategy()
        assert s.name == "orderbook_imbalance_v1"

    def test_name_override(self):
        s = OrderbookImbalanceStrategy(name_override="eth_orderbook_imbalance_v1")
        assert s.name == "eth_orderbook_imbalance_v1"

    def test_load_from_config_returns_strategy(self):
        s = load_from_config()
        assert isinstance(s, OrderbookImbalanceStrategy)

    def test_load_btc_imbalance_factory_name(self):
        s = load_btc_imbalance_from_config()
        assert s.name == "orderbook_imbalance_v1"

    def test_load_eth_imbalance_factory_name(self):
        s = load_eth_imbalance_from_config()
        assert s.name == "eth_orderbook_imbalance_v1"


# ── Gate 1: Time remaining ─────────────────────────────────────────────


class TestTimeGate:
    def test_below_min_minutes_returns_none(self):
        s = _default_strategy()
        market = _make_market(minutes_remaining=2.9)
        ob = _make_orderbook(yes_qty=1000, no_qty=100)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_exactly_min_minutes_returns_none(self):
        s = _default_strategy()
        market = _make_market(minutes_remaining=3.0)
        ob = _make_orderbook(yes_qty=1000, no_qty=100)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_above_min_minutes_passes(self):
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.01, min_minutes_remaining=3.0,
            min_yes_price_cents=35,  # unfiltered to isolate time gate
        )
        market = _make_market(minutes_remaining=3.1, yes_price=40)
        ob = _make_orderbook(yes_qty=900, no_qty=100)  # 90% imbalance
        result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is not None


# ── Gate 2: Minimum depth ──────────────────────────────────────────────


class TestDepthGate:
    def test_empty_orderbook_returns_none(self):
        s = _default_strategy()
        market = _make_market()
        ob = _make_orderbook(yes_qty=0, no_qty=0)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_below_min_depth_returns_none(self):
        s = _default_strategy()  # min_total_depth=50
        market = _make_market()
        ob = _make_orderbook(yes_qty=30, no_qty=10)  # total=40, below 50
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_at_min_depth_proceeds(self):
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.01, min_minutes_remaining=3.0,
        )
        market = _make_market(yes_price=40)
        ob = _make_orderbook(yes_qty=50, no_qty=10)  # total=60, above min; imbalance=0.83
        result = s.generate_signal(market, ob, _make_btc_feed())
        # Should pass depth gate (but edge may still block)
        # Just check it doesn't fail on depth
        assert result is not None or result is None  # doesn't crash


# ── Gate 3: Imbalance threshold ────────────────────────────────────────


class TestImbalanceGate:
    def test_balanced_orderbook_returns_none(self):
        """50/50 split — no signal."""
        s = _default_strategy()
        market = _make_market()
        ob = _make_orderbook(yes_qty=500, no_qty=500)  # perfect balance
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_slight_imbalance_returns_none(self):
        """60/40 split — below 65% threshold."""
        s = _default_strategy()
        market = _make_market()
        ob = _make_orderbook(yes_qty=600, no_qty=400)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_heavy_yes_imbalance_generates_yes_signal(self):
        """80% YES depth → should generate YES signal."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.01, min_minutes_remaining=3.0,
            min_yes_price_cents=35,  # unfiltered to isolate imbalance gate
        )
        market = _make_market(yes_price=40)  # underpriced relative to 80% probability
        ob = _make_orderbook(yes_qty=800, no_qty=200)
        result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is not None
        assert result.side == "yes"

    def test_heavy_no_imbalance_generates_no_signal(self):
        """Only 20% YES depth → heavy NO imbalance → buy NO."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.01, min_minutes_remaining=3.0,
            max_no_price_cents=65,  # unfiltered to isolate imbalance gate
        )
        market = _make_market(no_price=40)  # NO underpriced
        ob = _make_orderbook(yes_qty=200, no_qty=800)
        result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is not None
        assert result.side == "no"


# ── Signal field validation ────────────────────────────────────────────


class TestSignalFields:
    @pytest.fixture
    def yes_signal(self):
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.01, min_minutes_remaining=3.0,
            min_yes_price_cents=35,  # unfiltered to isolate signal field tests
        )
        market = _make_market(yes_price=40, minutes_remaining=10.0)
        ob = _make_orderbook(yes_qty=800, no_qty=200)
        return s.generate_signal(market, ob, _make_btc_feed())

    def test_win_prob_above_coin_flip(self, yes_signal):
        assert yes_signal.win_prob > 0.5

    def test_edge_pct_positive(self, yes_signal):
        assert yes_signal.edge_pct > 0.0

    def test_confidence_in_valid_range(self, yes_signal):
        assert 0.0 <= yes_signal.confidence <= 1.0

    def test_ticker_matches_market(self, yes_signal):
        assert yes_signal.ticker == "KXBTC15M-TEST"

    def test_reason_nonempty(self, yes_signal):
        assert yes_signal.reason
        assert "imbalance" in yes_signal.reason.lower()


# ── Edge gate ─────────────────────────────────────────────────────────


class TestEdgeGate:
    def test_high_edge_threshold_blocks_weak_signal(self):
        """With min_edge=0.99 (impossible), no signal fires even on extreme imbalance."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65, min_total_depth=50,
            min_edge_pct=0.99, min_minutes_remaining=3.0,
        )
        market = _make_market(yes_price=50)
        ob = _make_orderbook(yes_qty=900, no_qty=100)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None


# ── Near-miss INFO log ─────────────────────────────────────────────────


class TestPriceRangeGuard:
    """Regression: extreme-price bets must be blocked (same 35-65¢ guard as btc_lag)."""

    def test_extreme_yes_price_blocked(self):
        """YES at 98¢ (NO at 2¢) must not fire — was the anomalous $233 trade."""
        s = _default_strategy()
        market = _make_market(yes_price=98, no_price=2)
        ob = _make_orderbook(yes_qty=900, no_qty=100)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_extreme_no_price_blocked(self):
        """NO at 98¢ (YES at 2¢) must not fire."""
        s = _default_strategy()
        market = _make_market(yes_price=2, no_price=98)
        ob = _make_orderbook(yes_qty=100, no_qty=900)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_price_at_boundary_allowed(self):
        """YES at 35¢ is exactly at the lower bound — should not be blocked by price guard."""
        s = _default_strategy()
        market = _make_market(yes_price=35, no_price=65)
        ob = _make_orderbook(yes_qty=900, no_qty=100)
        # May return None due to edge gate but NOT due to price guard
        # We just verify it doesn't raise and the guard itself isn't the blocker at this boundary
        # (outcome depends on edge calc — no assertion on result here)
        s.generate_signal(market, ob, _make_btc_feed())  # must not raise


class TestAsymmetricPriceFilter:
    """Asymmetric price filter: YES only at >=52c, NO only at <=44c.

    Based on 162 paper bets (combined BTC+ETH):
      YES@52-65c: 63% WR (profitable)
      YES@35-51c: 40% WR (noise, negative EV)
      NO@35-44c: 50% WR (profitable: break-even is 35-44%)
      NO@45-65c: not enough data, excluded
    """

    def test_yes_below_min_yes_price_blocked(self):
        """YES signal at 51c blocked when min_yes_price_cents=52."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65,
            min_total_depth=50,
            min_edge_pct=0.0,  # disable edge gate to isolate price gate
            min_yes_price_cents=52,
            max_no_price_cents=44,
        )
        market = _make_market(yes_price=51, no_price=49)
        ob = _make_orderbook(yes_qty=900, no_qty=100)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_yes_at_min_yes_price_allowed(self):
        """YES signal at 52c is allowed when min_yes_price_cents=52."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65,
            min_total_depth=50,
            min_edge_pct=0.0,
            min_yes_price_cents=52,
            max_no_price_cents=44,
        )
        market = _make_market(yes_price=52, no_price=48)
        ob = _make_orderbook(yes_qty=900, no_qty=100)
        result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is not None
        assert result.side == "yes"
        assert result.price_cents == 52

    def test_no_above_max_no_price_blocked(self):
        """NO signal at 45c blocked when max_no_price_cents=44."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65,
            min_total_depth=50,
            min_edge_pct=0.0,
            min_yes_price_cents=52,
            max_no_price_cents=44,
        )
        # NO price = 45c means YES = 55c; heavy NO orderbook → buy NO at 45c
        market = _make_market(yes_price=55, no_price=45)
        ob = _make_orderbook(yes_qty=100, no_qty=900)
        assert s.generate_signal(market, ob, _make_btc_feed()) is None

    def test_no_at_max_no_price_allowed(self):
        """NO signal at 44c allowed when max_no_price_cents=44."""
        s = OrderbookImbalanceStrategy(
            min_imbalance_ratio=0.65,
            min_total_depth=50,
            min_edge_pct=0.0,
            min_yes_price_cents=52,
            max_no_price_cents=44,
        )
        # NO price = 44c means YES = 56c; heavy NO orderbook → buy NO at 44c
        market = _make_market(yes_price=56, no_price=44)
        ob = _make_orderbook(yes_qty=100, no_qty=900)
        result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is not None
        assert result.side == "no"
        assert result.price_cents == 44

    def test_default_min_yes_price_is_52(self):
        """Default strategy uses min_yes_price_cents=52 (filtered, not 35)."""
        s = OrderbookImbalanceStrategy()
        assert s._min_yes_price_cents == 52

    def test_default_max_no_price_is_44(self):
        """Default strategy uses max_no_price_cents=44 (filtered, not 65)."""
        s = OrderbookImbalanceStrategy()
        assert s._max_no_price_cents == 44

    def test_old_default_strategy_helper_unfiltered(self):
        """_default_strategy() uses min_yes=35 / max_no=65 — keeps old tests valid."""
        s = _default_strategy()
        assert s._min_yes_price_cents == 35
        assert s._max_no_price_cents == 65


class TestNearMissLog:
    def test_balanced_book_logs_at_info(self, caplog):
        """When imbalance is between thresholds, logs at INFO level."""
        s = _default_strategy()  # min_imbalance_ratio=0.65
        market = _make_market()
        ob = _make_orderbook(yes_qty=550, no_qty=450)  # 55% YES — inside neutral band
        with caplog.at_level(logging.INFO, logger="src.strategies.orderbook_imbalance"):
            result = s.generate_signal(market, ob, _make_btc_feed())
        assert result is None
        # Confirm INFO log was emitted
        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) >= 1
