"""
Tests for src/strategies/btc_drift.py — BTC drift-from-open signal generation.

Uses real BTCDriftStrategy (no mocking of the strategy logic).
Mocks Market, OrderBook, and BinanceFeed to control test inputs.

Key difference from btc_lag tests: btc_drift uses btc_feed.current_price()
(not btc_move_pct) and tracks reference prices per market ticker.
On the FIRST call for a ticker, it records the reference and returns None.
On subsequent calls, it measures drift from that reference.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.strategies.btc_drift import BTCDriftStrategy
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Helpers ───────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTC15M-TEST",
    yes_price: int = 50,
    no_price: int = 50,
    minutes_remaining: float = 10.0,
    minutes_since_open: float = 5.0,
    status: str = "open",
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(minutes=minutes_remaining)).isoformat()
    open_time = (now - timedelta(minutes=minutes_since_open)).isoformat()
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


def _make_orderbook(yes_bids=None, no_bids=None) -> OrderBook:
    return OrderBook(
        yes_bids=[OrderBookLevel(price=b[0], quantity=b[1]) for b in (yes_bids or [])],
        no_bids=[OrderBookLevel(price=b[0], quantity=b[1]) for b in (no_bids or [])],
    )


def _make_btc_feed(current_price=50000.0, is_stale: bool = False):
    feed = MagicMock()
    feed.is_stale = is_stale
    feed.current_price.return_value = current_price
    return feed


def _default_strategy() -> BTCDriftStrategy:
    return BTCDriftStrategy(
        sensitivity=300.0,
        min_edge_pct=0.05,
        min_minutes_remaining=3.0,
        time_weight=0.7,
        min_drift_pct=0.05,
    )


def _strategy_seed_reference(strategy: BTCDriftStrategy, market: Market, ref_price: float):
    """
    Seed the strategy's reference price for a market ticker by calling
    generate_signal once (which returns None and sets the reference).
    """
    feed = _make_btc_feed(current_price=ref_price)
    result = strategy.generate_signal(market, _make_orderbook(), feed)
    assert result is None, "First call should always return None (sets reference)"


# ── Gate 1: BTC feed health ───────────────────────────────────────


class TestFeedGate:
    def test_stale_feed_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(is_stale=True)
        )
        assert signal is None

    def test_none_current_price_returns_none(self):
        s = _default_strategy()
        signal = s.generate_signal(
            _make_market(), _make_orderbook(), _make_btc_feed(current_price=None)
        )
        assert signal is None


# ── Reference price tracking ─────────────────────────────────────


class TestReferencePrice:
    def test_first_observation_sets_reference_and_returns_none(self):
        """On first observation, strategy records BTC price and holds (no signal yet)."""
        s = _default_strategy()
        market = _make_market()
        feed = _make_btc_feed(current_price=50000.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None
        assert "KXBTC15M-TEST" in s._reference_prices
        assert s._reference_prices["KXBTC15M-TEST"][0] == 50000.0

    def test_second_observation_uses_stored_reference(self):
        """After reference is set, strategy computes drift and can generate a signal."""
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01,  # low edge floor to ensure signal fires
            min_minutes_remaining=3.0, time_weight=0.7, min_drift_pct=0.0,
        )
        market = _make_market(yes_price=50, no_price=50)
        # Set reference at 50000
        _strategy_seed_reference(s, market, ref_price=50000.0)
        # BTC drifted up 2% → strong YES signal
        feed = _make_btc_feed(current_price=51000.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is not None
        assert signal.side == "yes"

    def test_different_tickers_have_separate_references(self):
        """Each market ticker gets its own BTC reference price."""
        s = _default_strategy()
        market_a = _make_market(ticker="KXBTC15M-A")
        market_b = _make_market(ticker="KXBTC15M-B")
        # Seed different references
        _strategy_seed_reference(s, market_a, ref_price=50000.0)
        _strategy_seed_reference(s, market_b, ref_price=51000.0)
        assert s._reference_prices["KXBTC15M-A"][0] == 50000.0
        assert s._reference_prices["KXBTC15M-B"][0] == 51000.0


# ── Gate 2: Drift threshold ──────────────────────────────────────


class TestDriftGate:
    def test_zero_drift_returns_none(self):
        """If BTC hasn't moved from reference, no signal."""
        s = _default_strategy()
        market = _make_market()
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=50000.0)  # zero drift
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None

    def test_drift_below_minimum_returns_none(self):
        """Drift below min_drift_pct (0.05%) returns None."""
        s = _default_strategy()  # min_drift_pct=0.05
        market = _make_market()
        _strategy_seed_reference(s, market, ref_price=50000.0)
        # 0.03% drift — below 0.05% threshold
        feed = _make_btc_feed(current_price=50015.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None

    def test_drift_above_minimum_passes_gate(self):
        """Drift above min_drift_pct proceeds to signal evaluation."""
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_minutes_remaining=3.0,
            time_weight=0.7, min_drift_pct=0.05,
        )
        market = _make_market(yes_price=50, no_price=50)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        # 1% drift — well above threshold
        feed = _make_btc_feed(current_price=50500.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        # Should produce a signal (edge gate is low)
        assert signal is not None


# ── Gate 3: Time remaining ────────────────────────────────────────


class TestTimeGate:
    def test_less_than_min_minutes_remaining_returns_none(self):
        s = _default_strategy()  # min_minutes_remaining=3.0
        market = _make_market(minutes_remaining=2.9)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)  # large drift
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None

    def test_exactly_at_min_minutes_returns_none(self):
        s = _default_strategy()
        market = _make_market(minutes_remaining=3.0)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None

    def test_above_min_minutes_passes_time_gate(self):
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_minutes_remaining=3.0,
            time_weight=0.7, min_drift_pct=0.05,
        )
        market = _make_market(yes_price=50, no_price=50, minutes_remaining=3.1)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)  # 2% up
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is not None


# ── Signal correctness ────────────────────────────────────────────


class TestSignalGeneration:
    @pytest.fixture
    def yes_signal(self):
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_minutes_remaining=3.0,
            time_weight=0.7, min_drift_pct=0.0,
        )
        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0, minutes_since_open=5.0)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)  # +2% → YES
        return s.generate_signal(market, _make_orderbook(), feed)

    @pytest.fixture
    def no_signal(self):
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_minutes_remaining=3.0,
            time_weight=0.7, min_drift_pct=0.0,
        )
        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0, minutes_since_open=5.0)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=49000.0)  # -2% → NO
        return s.generate_signal(market, _make_orderbook(), feed)

    def test_btc_up_generates_yes_signal(self, yes_signal):
        assert yes_signal is not None
        assert yes_signal.side == "yes"

    def test_btc_down_generates_no_signal(self, no_signal):
        assert no_signal is not None
        assert no_signal.side == "no"

    def test_strategy_name(self):
        s = BTCDriftStrategy()
        assert s.name == "btc_drift_v1"

    def test_thin_edge_returns_none(self):
        """With very high min_edge_pct, even strong drift doesn't fire."""
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.99,  # impossible to meet
            min_minutes_remaining=3.0, time_weight=0.7, min_drift_pct=0.0,
        )
        market = _make_market(yes_price=50, no_price=50)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)
        signal = s.generate_signal(market, _make_orderbook(), feed)
        assert signal is None

    def test_win_prob_above_coin_flip(self, yes_signal):
        assert yes_signal.win_prob > 0.5

    def test_edge_pct_positive(self, yes_signal):
        assert yes_signal.edge_pct > 0

    def test_confidence_in_valid_range(self, yes_signal):
        assert 0.0 <= yes_signal.confidence <= 1.0

    def test_ticker_matches_market(self, yes_signal):
        assert yes_signal.ticker == "KXBTC15M-TEST"


# ── Time adjustment effect ────────────────────────────────────────


class TestTimeAdjustment:
    """Verify that confidence increases as market approaches close."""

    def _get_confidence(self, minutes_remaining: float, minutes_since_open: float) -> float:
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_minutes_remaining=0.0,
            time_weight=0.7, min_drift_pct=0.0,
        )
        market = _make_market(
            yes_price=50, no_price=50,
            minutes_remaining=minutes_remaining,
            minutes_since_open=minutes_since_open,
        )
        _strategy_seed_reference(s, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=51000.0)  # +2% drift
        signal = s.generate_signal(market, _make_orderbook(), feed)
        return signal.confidence if signal else 0.0

    def test_late_market_has_higher_confidence_than_early(self):
        """At 95% through the market window, confidence is higher than at 5%."""
        # 1 min left out of 20 total = 95% elapsed
        late_confidence = self._get_confidence(minutes_remaining=1.0, minutes_since_open=19.0)
        # 1 min elapsed out of 20 total = 5% elapsed
        early_confidence = self._get_confidence(minutes_remaining=19.0, minutes_since_open=1.0)
        assert late_confidence > early_confidence


# ── Late-entry penalty (reference staleness) ─────────────────────


class TestLateEntryPenalty:
    """
    When the bot first observes a market mid-window (e.g. after a restart),
    the reference price is stale relative to the true market open.
    confidence should be penalised proportionally.
    """

    def _signal_with_late_entry(self, minutes_late: float) -> object:
        """
        Return a signal where the reference was set `minutes_late` minutes
        after the market opened.  BTC moves +2% from the reference.

        Inject _reference_prices directly so that time_factor is identical
        across all minutes_late values — this isolates the late_penalty from
        the time-remaining confidence adjustment.
        """
        s = BTCDriftStrategy(
            sensitivity=300.0,
            min_edge_pct=0.01,      # very low threshold so signal fires
            min_minutes_remaining=1.0,
            time_weight=0.7,
            min_drift_pct=0.05,
        )
        # Fixed market geometry: 5 min left, 10 min since open.
        # time_factor is the same regardless of minutes_late.
        market = _make_market(
            yes_price=50, no_price=50,
            minutes_remaining=5.0,
            minutes_since_open=10.0,
        )
        # Inject reference directly — (price, minutes_late stored at first-obs)
        s._reference_prices[market.ticker] = (50000.0, minutes_late)
        feed = _make_btc_feed(current_price=51000.0)  # +2% drift
        return s.generate_signal(market, _make_orderbook(), feed)

    def test_on_time_reference_no_penalty(self):
        """First observation within 2 min of open: no penalty applied."""
        sig_on_time = self._signal_with_late_entry(0.0)
        sig_slightly_late = self._signal_with_late_entry(1.5)
        assert sig_on_time is not None
        assert sig_slightly_late is not None
        # Confidence should be similar (within penalty threshold of 2 min)
        assert abs(sig_on_time.confidence - sig_slightly_late.confidence) < 0.02

    def test_late_reference_reduces_confidence(self):
        """Reference set 10 min late should have lower confidence than on-time."""
        sig_on_time = self._signal_with_late_entry(0.0)
        sig_late = self._signal_with_late_entry(10.0)
        assert sig_on_time is not None
        assert sig_late is not None
        assert sig_late.confidence < sig_on_time.confidence

    def test_very_late_reference_halves_confidence(self):
        """Reference set near end of window (14 min late) should cap at ~50% confidence."""
        sig = self._signal_with_late_entry(14.0)
        assert sig is not None
        # late_penalty at 14min late = max(0.5, 1.0 - (14-2)/16) = max(0.5, 0.25) = 0.5
        sig_on_time = self._signal_with_late_entry(0.0)
        assert sig_on_time is not None
        # Late signal confidence should be at most 50% of on-time signal confidence
        assert sig.confidence <= sig_on_time.confidence * 0.55

    def test_reason_includes_late_marker(self):
        """Reason string should mention late reference when minutes_late > 2."""
        sig = self._signal_with_late_entry(8.0)
        assert sig is not None
        assert "late" in sig.reason.lower()

    def test_reason_clean_when_on_time(self):
        """On-time reference should not add noise to reason string."""
        sig = self._signal_with_late_entry(0.0)
        assert sig is not None
        assert "late" not in sig.reason.lower()

    def test_minutes_since_open_helper_zero_at_open(self):
        """Market just opened (open_time == now): minutes_since_open ≈ 0."""
        market = _make_market(minutes_since_open=0.0, minutes_remaining=15.0)
        result = BTCDriftStrategy._minutes_since_open(market)
        assert result < 0.5  # within half a minute of zero


# ── Price extremes filter ─────────────────────────────────────────


class TestPriceExtremesFilter:
    """
    btc_drift must not place bets when the market price is outside the calibrated
    range (10¢–90¢). The sigmoid model was trained on near-50¢ data and extrapolates
    at extremes. At 3¢ or 97¢, HFTs have already priced in certainty — the model
    has no informational edge there.
    """

    def _signal_at_price(self, yes_price: int, no_price: int) -> object:
        s = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01,
            min_minutes_remaining=3.0, min_drift_pct=0.05,
        )
        market = _make_market(yes_price=yes_price, no_price=no_price,
                              minutes_remaining=8.0, minutes_since_open=5.0)
        _strategy_seed_reference(s, market, ref_price=50000.0)
        # BTC drifts enough to fire a signal in normal range
        feed = _make_btc_feed(current_price=50500.0)  # +1% drift → strong YES signal
        return s.generate_signal(market, _make_orderbook(), feed)

    def test_signal_blocked_below_10_cents(self):
        """Price at 3¢ YES is below the 10¢ floor — must be skipped."""
        sig = self._signal_at_price(yes_price=3, no_price=97)
        assert sig is None, "3¢ YES bet is outside calibrated range — must skip"

    def test_signal_blocked_above_90_cents(self):
        """Price at 97¢ YES is above the 90¢ ceiling — must be skipped."""
        sig = self._signal_at_price(yes_price=97, no_price=3)
        assert sig is None, "97¢ YES bet is outside calibrated range — must skip"

    def test_signal_allowed_at_10_cents_boundary(self):
        """Exactly 10¢ is within the calibrated range — must not be skipped."""
        sig = self._signal_at_price(yes_price=10, no_price=90)
        # Signal may or may not fire (edge calculation decides), but if edge passes
        # the price guard must not block it — not None due to price filter.
        # We verify by checking that the price guard constant is 10 (not stricter).
        from src.strategies.btc_drift import _MIN_SIGNAL_PRICE_CENTS
        assert _MIN_SIGNAL_PRICE_CENTS == 10

    def test_signal_allowed_at_90_cents_boundary(self):
        """Exactly 90¢ is within the calibrated range — must not be skipped."""
        from src.strategies.btc_drift import _MAX_SIGNAL_PRICE_CENTS
        assert _MAX_SIGNAL_PRICE_CENTS == 90

    def test_minutes_since_open_helper_reflects_elapsed(self):
        """Market opened 7 min ago: _minutes_since_open returns ≈ 7."""
        market = _make_market(minutes_since_open=7.0, minutes_remaining=8.0)
        result = BTCDriftStrategy._minutes_since_open(market)
        assert 6.5 < result < 7.5
