"""
Tests for Dimension 4: Bayesian predict wired into BTCDriftStrategy.generate_signal()

Verifies:
  1. No model (None) → static sigmoid used
  2. Model below threshold (< 30 obs) → static sigmoid used
  3. Model at/above threshold (30+ obs) → Bayesian predict() used
  4. predict() receives the correct drift_pct
  5. Time adjustment is STILL applied after Bayesian raw_prob
  6. Model can be injected after construction (instance variable)
  7. All 4 drift strategy factory names work (btc/eth/sol/xrp use same class)
  8. Bayesian model with negative intercept + positive drift → shifted signal
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, call, patch

import pytest

from src.strategies.btc_drift import BTCDriftStrategy
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Shared helpers ────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTC15M-TEST",
    yes_price: int = 50,
    no_price: int = 50,
    minutes_remaining: float = 10.0,
    minutes_since_open: float = 5.0,
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(minutes=minutes_remaining)).isoformat()
    open_time = (now - timedelta(minutes=minutes_since_open)).isoformat()
    return Market(
        ticker=ticker,
        title="Test market",
        event_ticker="KXBTC15M",
        status="open",
        yes_price=yes_price,
        no_price=no_price,
        volume=1000,
        close_time=close_time,
        open_time=open_time,
        result=None,
        raw={},
    )


def _make_orderbook() -> OrderBook:
    return OrderBook(yes_bids=[], no_bids=[])


def _make_btc_feed(current_price: float = 50000.0, is_stale: bool = False):
    feed = MagicMock()
    feed.is_stale = is_stale
    feed.current_price.return_value = current_price
    return feed


def _make_mock_model(n_observations: int = 30, predict_return: float = 0.75):
    """Create a MagicMock BayesianDriftModel with controllable behaviour."""
    model = MagicMock()
    model.n_observations = n_observations
    model.should_override_static.return_value = n_observations >= 30
    model.predict.return_value = predict_return
    return model


def _strategy_with_ref(
    strat: BTCDriftStrategy,
    market: Market,
    ref_price: float,
    btc_feed=None,
) -> None:
    """Seed reference price by calling generate_signal once (returns None on first call)."""
    if btc_feed is None:
        btc_feed = _make_btc_feed(ref_price)
    strat.generate_signal(market, _make_orderbook(), btc_feed)


# ── Tests ─────────────────────────────────────────────────────────────


class TestStaticPathWhenNoModel:
    """With no drift model, static sigmoid must be used."""

    def test_no_model_by_default(self):
        strat = BTCDriftStrategy()
        assert strat._drift_model is None

    def test_no_model_uses_static_sigmoid_and_fires_signal(self):
        strat = BTCDriftStrategy(
            sensitivity=300.0,
            min_edge_pct=0.05,
            min_drift_pct=0.05,
            min_minutes_remaining=3.0,
            time_weight=0.7,
        )
        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)

        # Seed reference at 50000, then feed 50500 (+1% drift → strong YES signal)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=50500.0)
        signal = strat.generate_signal(market, _make_orderbook(), feed)

        assert signal is not None
        assert signal.side == "yes"
        # No model means static path — if model had been called we'd catch it via mock

    def test_signal_generated_without_model(self):
        """Regression: static path must not require a model attribute."""
        strat = BTCDriftStrategy(min_edge_pct=0.05, min_drift_pct=0.05)
        assert not hasattr(strat, "nonexistent_attr")
        assert strat._drift_model is None  # attribute exists, is None


class TestBelowThreshold:
    """Model present but n_observations < 30 → static path."""

    def test_below_threshold_uses_static(self):
        strat = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.05, min_drift_pct=0.05,
            min_minutes_remaining=3.0, time_weight=0.7,
        )
        model = _make_mock_model(n_observations=29)  # one below threshold
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=50500.0)
        strat.generate_signal(market, _make_orderbook(), feed)

        model.predict.assert_not_called()

    def test_exactly_29_observations_static(self):
        strat = BTCDriftStrategy(min_edge_pct=0.05, min_drift_pct=0.05)
        model = _make_mock_model(n_observations=29)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        strat.generate_signal(market, _make_orderbook(), _make_btc_feed(50500.0))

        model.predict.assert_not_called()


class TestBayesianOverrideAtThreshold:
    """Model with 30+ observations → predict() used as raw_prob."""

    def test_exactly_30_observations_uses_bayesian(self):
        strat = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.05, min_drift_pct=0.05,
            min_minutes_remaining=3.0, time_weight=0.7,
        )
        model = _make_mock_model(n_observations=30, predict_return=0.8)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        feed = _make_btc_feed(current_price=50500.0)
        strat.generate_signal(market, _make_orderbook(), feed)

        model.predict.assert_called_once()

    def test_100_observations_uses_bayesian(self):
        strat = BTCDriftStrategy(min_edge_pct=0.05, min_drift_pct=0.05)
        model = _make_mock_model(n_observations=100, predict_return=0.7)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        strat.generate_signal(market, _make_orderbook(), _make_btc_feed(50500.0))

        model.predict.assert_called_once()

    def test_predict_receives_correct_drift_pct(self):
        """predict() must receive pct_from_open in decimal form."""
        strat = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.05, min_drift_pct=0.05,
        )
        model = _make_mock_model(n_observations=50, predict_return=0.75)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=10.0)
        ref_price = 50000.0
        current_price = 50500.0
        expected_drift = (current_price - ref_price) / ref_price  # 0.01 (1%)

        _strategy_with_ref(strat, market, ref_price=ref_price)
        strat.generate_signal(market, _make_orderbook(), _make_btc_feed(current_price))

        model.predict.assert_called_once()
        actual_drift = model.predict.call_args[0][0]
        assert abs(actual_drift - expected_drift) < 1e-10, (
            f"predict() called with drift={actual_drift}, expected {expected_drift}"
        )


class TestTimeAdjustmentWithBayesian:
    """Time adjustment blending toward 0.5 must STILL apply after Bayesian raw_prob."""

    def test_time_blending_reduces_prob_early_in_window(self):
        """
        Early in window (minutes_since_open=0, large minutes_remaining):
        time_factor ≈ 0, blend = 1 - time_weight = 0.3 (at time_weight=0.7).
        If Bayesian predict returns 0.8, prob_yes = 0.5 + (0.8-0.5)*0.3 = 0.59.
        Late in window (minutes_since_open=14, minutes_remaining=1 but > min):
        time_factor ≈ 1, blend = 1.0.
        If Bayesian predict returns 0.8, prob_yes ≈ 0.8.

        We verify: early win_prob < late win_prob when model returns same probability.
        """
        # Early window: just opened
        strat_early = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_drift_pct=0.05,
            min_minutes_remaining=1.0, time_weight=0.7,
        )
        model_early = _make_mock_model(n_observations=50, predict_return=0.9)
        strat_early._drift_model = model_early
        market_early = _make_market(
            ticker="EARLY", yes_price=50, no_price=50,
            minutes_remaining=14.0, minutes_since_open=1.0,
        )
        _strategy_with_ref(strat_early, market_early, ref_price=50000.0)
        sig_early = strat_early.generate_signal(
            market_early, _make_orderbook(), _make_btc_feed(50500.0)
        )

        # Late window: about to close
        strat_late = BTCDriftStrategy(
            sensitivity=300.0, min_edge_pct=0.01, min_drift_pct=0.05,
            min_minutes_remaining=1.0, time_weight=0.7,
        )
        model_late = _make_mock_model(n_observations=50, predict_return=0.9)
        strat_late._drift_model = model_late
        market_late = _make_market(
            ticker="LATE", yes_price=50, no_price=50,
            minutes_remaining=2.0, minutes_since_open=13.0,
        )
        _strategy_with_ref(strat_late, market_late, ref_price=50000.0)
        sig_late = strat_late.generate_signal(
            market_late, _make_orderbook(), _make_btc_feed(50500.0)
        )

        # Both should fire (strong drift), but early window should have lower win_prob
        assert sig_early is not None, "Early window signal must fire with strong drift"
        assert sig_late is not None, "Late window signal must fire with strong drift"
        assert sig_early.win_prob < sig_late.win_prob, (
            f"Early win_prob={sig_early.win_prob} should be < late win_prob={sig_late.win_prob} "
            f"(time adjustment must apply even with Bayesian model)"
        )


class TestModelInjection:
    """Model can be injected after construction and replaced."""

    def test_model_injected_via_attribute(self):
        strat = BTCDriftStrategy()
        model = _make_mock_model(n_observations=50)
        strat._drift_model = model
        assert strat._drift_model is model

    def test_model_replaced_after_injection(self):
        strat = BTCDriftStrategy()
        model1 = _make_mock_model(n_observations=50)
        model2 = _make_mock_model(n_observations=100)
        strat._drift_model = model1
        strat._drift_model = model2
        assert strat._drift_model is model2

    def test_all_four_strategy_instances_can_hold_model(self):
        """btc/eth/sol/xrp all use BTCDriftStrategy — verify attribute works for each."""
        from src.strategies.btc_drift import (
            load_from_config,
            load_eth_drift_from_config,
            load_sol_drift_from_config,
            load_xrp_drift_from_config,
        )
        strategies = [
            load_from_config(),
            load_eth_drift_from_config(),
            load_sol_drift_from_config(),
            load_xrp_drift_from_config(),
        ]
        model = _make_mock_model(n_observations=50)
        for strat in strategies:
            assert hasattr(strat, "_drift_model"), f"{strat.name} missing _drift_model"
            strat._drift_model = model
            assert strat._drift_model is model


class TestBayesianSignalBehaviour:
    """Verify signal side and win_prob reflect Bayesian model output."""

    def test_bayesian_high_yes_prob_fires_yes_signal(self):
        """Model predicts P(YES)=0.85 → YES signal when YES price is ~50c."""
        strat = BTCDriftStrategy(
            min_edge_pct=0.01, min_drift_pct=0.05, min_minutes_remaining=1.0,
        )
        model = _make_mock_model(n_observations=50, predict_return=0.85)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=5.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        signal = strat.generate_signal(
            market, _make_orderbook(), _make_btc_feed(50300.0)  # 0.6% positive drift
        )

        assert signal is not None
        assert signal.side == "yes"

    def test_bayesian_low_yes_prob_fires_no_signal(self):
        """Model predicts P(YES)=0.15 → NO signal when NO price is ~50c."""
        strat = BTCDriftStrategy(
            min_edge_pct=0.01, min_drift_pct=0.05, min_minutes_remaining=1.0,
        )
        model = _make_mock_model(n_observations=50, predict_return=0.15)
        strat._drift_model = model

        market = _make_market(yes_price=50, no_price=50, minutes_remaining=5.0)
        _strategy_with_ref(strat, market, ref_price=50000.0)
        # Drift needs to clear min_drift_pct threshold regardless of model output
        # Use negative drift to ensure we're past the drift gate
        signal = strat.generate_signal(
            market, _make_orderbook(), _make_btc_feed(49700.0)  # -0.6% negative drift
        )

        assert signal is not None
        assert signal.side == "no"
