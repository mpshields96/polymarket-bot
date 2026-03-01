"""
Tests for src/strategies/btc_lag.py — BTC lag signal generation.

Uses real BTCLagStrategy (no mocking of the strategy logic).
Mocks Market, OrderBook, and BinanceFeed to control test inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from src.strategies.btc_lag import BTCLagStrategy, _DEFAULT_LAG_SENSITIVITY
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Helpers ───────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTC15M-TEST",
    yes_price: int = 44,
    no_price: int = 56,
    minutes_remaining: float = 10.0,
    status: str = "open",
) -> Market:
    close_time = (datetime.now(timezone.utc) + timedelta(minutes=minutes_remaining)).isoformat()
    return Market(
        ticker=ticker,
        title="Test market",
        event_ticker="KXBTC15M",
        status=status,
        yes_price=yes_price,
        no_price=no_price,
        volume=1000,
        close_time=close_time,
        open_time=datetime.now(timezone.utc).isoformat(),
        result=None,
        raw={},
    )


def _make_orderbook(yes_bids=None, no_bids=None) -> OrderBook:
    return OrderBook(
        yes_bids=[OrderBookLevel(price=b[0], quantity=b[1]) for b in (yes_bids or [])],
        no_bids=[OrderBookLevel(price=b[0], quantity=b[1]) for b in (no_bids or [])],
    )


def _make_btc_feed(btc_move_pct: Optional[float] = 0.5, is_stale: bool = False):
    feed = MagicMock()
    feed.is_stale = is_stale
    feed.btc_move_pct.return_value = btc_move_pct
    return feed


def _default_strategy() -> BTCLagStrategy:
    return BTCLagStrategy(
        min_btc_move_pct=0.4,
        min_kalshi_lag_cents=5,
        min_minutes_remaining=5,
        min_edge_pct=0.08,
        lag_sensitivity=15.0,
    )


# ── Gate 1: BTC feed health ───────────────────────────────────────


class TestBTCFeedGate:
    def test_stale_feed_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(is_stale=True)
        )
        assert signal is None

    def test_none_btc_move_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(btc_move_pct=None)
        )
        assert signal is None

    def test_btc_move_below_threshold_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(btc_move_pct=0.3)  # < 0.4 threshold
        )
        assert signal is None

    def test_btc_move_exactly_at_threshold_returns_none(self):
        # Must EXCEED threshold (strictly greater than)
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(btc_move_pct=0.4)
        )
        # 0.4% * 15 = 6¢ lag — passes lag gate, but let's check edge:
        # edge = 0.06 - fee(44¢) = 0.06 - 0.0172 = 0.0428 < 0.08 threshold
        # So should return None due to thin edge
        assert signal is None


# ── Gate 2: Lag check ─────────────────────────────────────────────


class TestLagGate:
    def test_implied_lag_below_minimum_returns_none(self):
        # 0.4% move * 15 sensitivity = 6¢ implied lag (≥ 5¢ min) — should pass lag gate
        # but 0.3% * 15 = 4.5¢ < 5¢ min_lag → should block
        s = BTCLagStrategy(
            min_btc_move_pct=0.2,   # low threshold so BTC gate passes
            min_kalshi_lag_cents=5,
            min_minutes_remaining=5,
            min_edge_pct=0.01,      # low to isolate lag gate
            lag_sensitivity=15.0,
        )
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(btc_move_pct=0.3)
            # 0.3 * 15 = 4.5¢ < 5¢ min
        )
        assert signal is None

    def test_implied_lag_above_minimum_passes(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2,
            min_kalshi_lag_cents=5,
            min_minutes_remaining=5,
            min_edge_pct=0.01,
            lag_sensitivity=15.0,
        )
        signal = s.generate_signal(
            _make_market(yes_price=44), _make_orderbook(), _make_btc_feed(btc_move_pct=0.5)
            # 0.5 * 15 = 7.5¢ > 5¢ min
        )
        assert signal is not None


# ── Gate 3: Time remaining ────────────────────────────────────────


class TestTimeGate:
    def test_less_than_5_min_remaining_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(minutes_remaining=4.9),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),  # strong move to pass other gates
        )
        assert signal is None

    def test_exactly_5_min_remaining_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(minutes_remaining=5.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),
        )
        assert signal is None

    def test_just_above_5_min_passes_time_gate(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2,
            min_kalshi_lag_cents=5,
            min_minutes_remaining=5,
            min_edge_pct=0.01,
            lag_sensitivity=15.0,
        )
        signal = s.generate_signal(
            _make_market(minutes_remaining=5.1, yes_price=44),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=0.5),
        )
        assert signal is not None


# ── Gate 4: Edge check ────────────────────────────────────────────


class TestEdgeGate:
    def test_thin_edge_returns_none(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2,
            min_kalshi_lag_cents=1,
            min_minutes_remaining=5,
            min_edge_pct=0.50,      # very high edge requirement
            lag_sensitivity=15.0,
        )
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(btc_move_pct=0.5)
        )
        assert signal is None

    def test_sufficient_edge_generates_signal(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2,
            min_kalshi_lag_cents=5,
            min_minutes_remaining=5,
            min_edge_pct=0.01,      # low enough to always pass
            lag_sensitivity=15.0,
        )
        signal = s.generate_signal(
            _make_market(yes_price=44, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=0.5),
        )
        assert signal is not None
        assert signal.edge_pct > 0.01


# ── Signal correctness ────────────────────────────────────────────


class TestSignalFields:
    @pytest.fixture
    def signal_yes(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2, min_kalshi_lag_cents=5,
            min_minutes_remaining=5, min_edge_pct=0.01, lag_sensitivity=15.0,
        )
        return s.generate_signal(
            _make_market(yes_price=44, no_price=56, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=0.5),  # BTC UP → YES signal
        )

    @pytest.fixture
    def signal_no(self):
        s = BTCLagStrategy(
            min_btc_move_pct=0.2, min_kalshi_lag_cents=5,
            min_minutes_remaining=5, min_edge_pct=0.01, lag_sensitivity=15.0,
        )
        return s.generate_signal(
            _make_market(yes_price=44, no_price=56, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=-0.5),  # BTC DOWN → NO signal
        )

    def test_btc_up_generates_yes_signal(self, signal_yes):
        assert signal_yes is not None
        assert signal_yes.side == "yes"

    def test_btc_down_generates_no_signal(self, signal_no):
        assert signal_no is not None
        assert signal_no.side == "no"

    def test_yes_signal_uses_yes_price(self, signal_yes):
        assert signal_yes.price_cents == 44

    def test_no_signal_uses_no_price(self, signal_no):
        assert signal_no.price_cents == 56

    def test_win_prob_above_coin_flip(self, signal_yes):
        assert signal_yes.win_prob > 0.5

    def test_win_prob_capped_at_85_pct(self, signal_yes):
        assert signal_yes.win_prob <= 0.85

    def test_edge_pct_positive(self, signal_yes):
        assert signal_yes.edge_pct > 0

    def test_confidence_between_0_and_1(self, signal_yes):
        assert 0.0 <= signal_yes.confidence <= 1.0

    def test_ticker_matches_market(self, signal_yes):
        assert signal_yes.ticker == "KXBTC15M-TEST"

    def test_reason_string_nonempty(self, signal_yes):
        assert signal_yes.reason
        assert "BTC" in signal_yes.reason


# ── Invalid market prices ─────────────────────────────────────────


class TestEdgeCases:
    def test_zero_yes_price_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=0, no_price=100),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),
        )
        assert signal is None

    def test_100_cent_yes_price_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=100, no_price=0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),
        )
        assert signal is None


# ── Price extremes filter (35¢–65¢ calibrated range) ─────────────


class TestPriceExtremesFilter:
    """btc_lag should skip any signal where the selected price is outside 35–65¢.

    Only bet near even odds. Outside this range the market has strong conviction
    and we have no informational edge against HFTs. Tightened from 10–90 2026-03-01.
    """

    def test_no_signal_blocked_below_35_cents(self):
        """BTC down → BUY NO, but NO price 3¢ → outside 35¢ floor → skip."""
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=97, no_price=3, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=-1.0),
        )
        assert signal is None

    def test_yes_signal_blocked_above_65_cents(self):
        """BTC up → BUY YES, but YES price 97¢ → outside 65¢ ceiling → skip."""
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=97, no_price=3, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),
        )
        assert signal is None

    def test_signal_blocked_at_old_10_cent_boundary(self):
        """10¢ was previously the floor — now it is outside the 35¢ floor → skip."""
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=90, no_price=10, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=-1.0),  # BTC down → BUY NO at 10¢ — now blocked
        )
        assert signal is None, "10¢ NO is outside new 35¢ floor — must skip"

    def test_signal_blocked_at_old_90_cent_boundary(self):
        """90¢ was previously the ceiling — now it is outside the 65¢ ceiling → skip."""
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(yes_price=90, no_price=10, minutes_remaining=10.0),
            _make_orderbook(),
            _make_btc_feed(btc_move_pct=1.0),  # BTC up → BUY YES at 90¢ — now blocked
        )
        assert signal is None, "90¢ YES is outside new 65¢ ceiling — must skip"

    def test_signal_allowed_in_35_65_range(self):
        """Price at 50¢ is well within the 35–65¢ range → signal may fire."""
        from src.strategies.btc_lag import _MIN_SIGNAL_PRICE_CENTS, _MAX_SIGNAL_PRICE_CENTS
        assert _MIN_SIGNAL_PRICE_CENTS == 35
        assert _MAX_SIGNAL_PRICE_CENTS == 65
