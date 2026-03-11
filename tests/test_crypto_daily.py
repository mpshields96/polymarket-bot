"""
Tests for src/strategies/crypto_daily.py — CryptoDailyStrategy.

Market structure: Kalshi KXBTCD/KXETHD/KXSOLD
- Each series has 24 hourly slots per day (midnight to 11pm EST)
- Each slot has ~40-75 price levels (strikes)
- YES = asset price above $strike at close time
- ATM = strike where yes_price ≈ 50¢
- Settlement via CF Benchmarks at fixed UTC close time

Strategy: Find ATM market 30min-6hr to settlement.
Apply drift signal to estimate direction.
Bet when model probability diverges from market price by > min_edge_pct.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from unittest.mock import patch

import pytest

from src.platforms.kalshi import Market
from src.strategies.crypto_daily import CryptoDailyStrategy


# ── Helpers ───────────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTCD-26MAR0921-T80000",
    strike: float = 80000.0,
    yes_price: int = 50,    # bid in cents
    yes_ask: int = 52,
    volume: int = 5000,
    minutes_to_close: float = 120.0,
    series: str = "KXBTCD",
) -> Market:
    """Create a fake Market for testing."""
    close_dt = datetime.now(timezone.utc) + timedelta(minutes=minutes_to_close)
    close_iso = close_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return Market(
        ticker=ticker,
        title=f"BTC above ${strike:,.2f}?",
        event_ticker=ticker,
        status="open",
        yes_price=yes_price,
        no_price=100 - yes_price,
        volume=volume,
        close_time=close_iso,
        open_time="",
        result=None,
        raw={"yes_ask": yes_ask, "yes_bid": yes_price, "series_ticker": series},
    )


def _make_markets_around_strike(
    center_strike: float,
    spot: float,
    n: int = 10,
    step: float = 250.0,
    minutes_to_close: float = 120.0,
    series: str = "KXBTCD",
) -> List[Market]:
    """Create a range of markets around center_strike, simulating a Kalshi slot."""
    markets = []
    for i in range(-n // 2, n // 2 + 1):
        strike = center_strike + i * step
        # Simulate probability: spot above strike = sigmoidal probability
        diff = (spot - strike) / spot
        prob = 50 + int(diff * 1500)
        prob = max(1, min(99, prob))
        ask = min(99, prob + 1)
        ticker = f"{series}-TEST-T{int(strike)}"
        markets.append(_make_market(
            ticker=ticker,
            strike=strike,
            yes_price=prob,
            yes_ask=ask,
            volume=max(100, 5000 - abs(i) * 300),
            minutes_to_close=minutes_to_close,
            series=series,
        ))
    return markets


# ── TestATMSelection ──────────────────────────────────────────────────


class TestATMSelection:
    """Strategy must pick the market closest to ATM (yes_price ≈ 50)."""

    def test_picks_market_closest_to_50(self):
        spot = 80000.0
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        markets = _make_markets_around_strike(spot, spot)
        atm = strat._find_atm_market(markets, spot)
        assert atm is not None
        # ATM market should have yes_price closest to 50
        mid = (atm.yes_price + atm.raw.get("yes_ask", atm.yes_price + 1)) / 2
        assert abs(mid - 50) < 15

    def test_returns_none_when_no_markets(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        assert strat._find_atm_market([], 80000.0) is None

    def test_skips_markets_outside_price_guard(self):
        """Markets with mid < 35 or > 65 are excluded (price guard)."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        # All markets outside 35-65¢ window
        extreme_markets = [
            _make_market(yes_price=10, yes_ask=12, volume=5000),  # too cheap
            _make_market(yes_price=88, yes_ask=90, volume=5000),  # too expensive
        ]
        result = strat._find_atm_market(extreme_markets, 80000.0)
        assert result is None

    def test_skips_markets_with_low_volume(self):
        """Markets with volume below min_volume are skipped."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD", min_volume=500)
        thin = _make_market(yes_price=50, yes_ask=51, volume=10)
        liquid = _make_market(ticker="KXBTCD-2", yes_price=49, yes_ask=51, volume=1000)
        result = strat._find_atm_market([thin, liquid], 80000.0)
        assert result is not None
        assert result.volume >= 500

    def test_skips_markets_too_close_to_settlement(self):
        """Markets with < min_minutes_remaining are excluded."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD",
                                    min_minutes_remaining=30.0)
        close_market = _make_market(yes_price=50, yes_ask=51, volume=5000,
                                    minutes_to_close=15.0)  # too close
        ok_market = _make_market(ticker="KXBTCD-2", yes_price=49, yes_ask=51,
                                  volume=5000, minutes_to_close=90.0)
        result = strat._find_atm_market([close_market, ok_market], 80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-2"

    def test_skips_markets_too_far_from_settlement(self):
        """Markets with > max_minutes_remaining are excluded (too early)."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD",
                                    max_minutes_remaining=360.0)
        far_market = _make_market(yes_price=50, yes_ask=51, volume=5000,
                                   minutes_to_close=600.0)  # 10hrs out
        ok_market = _make_market(ticker="KXBTCD-2", yes_price=49, yes_ask=51,
                                  volume=5000, minutes_to_close=120.0)
        result = strat._find_atm_market([far_market, ok_market], 80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-2"


# ── TestSignalDirection ───────────────────────────────────────────────


class TestSignalDirection:
    """When drift is up, signal should be YES (above); when down, NO."""

    def test_upward_drift_generates_yes_signal(self):
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.03,
        )
        spot = 81600.0
        session_open = 80000.0  # +2% drift up
        markets = _make_markets_around_strike(81000.0, spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert sig.side == "yes"

    def test_downward_drift_generates_no_signal(self):
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.03,
        )
        spot = 78400.0
        session_open = 80000.0  # -2% drift down
        markets = _make_markets_around_strike(79000.0, spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert sig.side == "no"

    def test_no_signal_when_drift_below_threshold(self):
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.01,  # 1% min drift
        )
        spot = 80040.0
        session_open = 80000.0  # only 0.05% drift — below threshold
        markets = _make_markets_around_strike(80000.0, spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is None

    def test_no_signal_when_edge_too_small(self):
        """If model probability doesn't differ enough from market, skip."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.001, min_edge_pct=0.20,  # Very high edge requirement
        )
        spot = 81600.0
        session_open = 80000.0
        # Market already prices the drift in — 65¢ YES
        markets = [_make_market(yes_price=63, yes_ask=65, volume=5000, minutes_to_close=120.0)]
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is None

    def test_no_signal_when_no_atm_market(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        sig = strat.generate_signal(80000.0, 79000.0, [])
        assert sig is None


# ── TestSignalContents ────────────────────────────────────────────────


class TestSignalContents:
    """Signal fields must be correct."""

    def test_signal_has_required_fields(self):
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.02,
        )
        spot = 81600.0
        session_open = 80000.0
        markets = _make_markets_around_strike(81000.0, spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert sig.ticker is not None and sig.ticker != ""
        assert sig.side in ("yes", "no")
        assert 1 <= sig.price_cents <= 99
        assert sig.edge_pct > 0
        assert sig.reason != ""

    def test_yes_signal_price_is_yes_ask(self):
        """When buying YES, we pay the YES ask price."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.02,
        )
        spot = 82000.0
        session_open = 80000.0
        market = _make_market(yes_price=48, yes_ask=51, volume=5000, minutes_to_close=120.0)
        sig = strat.generate_signal(spot, session_open, [market])
        if sig and sig.side == "yes":
            assert sig.price_cents == 51  # paid the ask

    def test_no_signal_price_is_no_ask(self):
        """When buying NO, price_cents = 100 - yes_bid (NO ask)."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.02,
        )
        spot = 78000.0
        session_open = 80000.0
        market = _make_market(yes_price=55, yes_ask=57, volume=5000, minutes_to_close=120.0)
        sig = strat.generate_signal(spot, session_open, [market])
        if sig and sig.side == "no":
            # NO ask = 100 - yes_bid
            assert sig.price_cents == 100 - 55


# ── TestEdgeCalculation ───────────────────────────────────────────────


class TestEdgeCalculation:
    """Edge must account for Kalshi fee."""

    def test_edge_is_positive_when_model_above_market(self):
        """If model says 65% YES and market asks 50¢, edge should be positive."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.001, min_edge_pct=0.001,
        )
        spot = 82000.0
        session_open = 80000.0
        # Market priced at 50 even though BTC is up 2.5%
        market = _make_market(yes_price=48, yes_ask=51, volume=5000, minutes_to_close=120.0)
        sig = strat.generate_signal(spot, session_open, [market])
        if sig is not None:
            assert sig.edge_pct > 0

    def test_edge_reflects_fee_deduction(self):
        """Net edge = gross edge minus Kalshi fee."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.001, min_edge_pct=0.001,
        )
        # Test the edge calculation directly
        gross = strat._compute_edge(model_prob=0.65, price_cents=50, side="yes")
        # gross = 0.65 - 0.50 = 0.15
        # fee = 0.07 * p * (1-p) = 0.07 * 0.50 * 0.50 = 0.0175
        # net = 0.15 - 0.0175 = 0.1325
        assert gross > 0
        assert gross < 0.15  # fee deducted

    def test_negative_edge_returns_zero(self):
        """When model_prob < market price, edge is 0 or negative."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        edge = strat._compute_edge(model_prob=0.40, price_cents=55, side="yes")
        assert edge <= 0


# ── TestModelProbability ──────────────────────────────────────────────


class TestModelProbability:
    """Model probability must respond correctly to drift and time."""

    def test_probability_above_50_when_spot_above_strike(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        # Spot above strike → prob > 50%
        prob = strat._model_prob(
            spot=82000.0, strike=80000.0,
            hours_to_settle=2.0, drift_pct=0.025,
        )
        assert prob > 0.5

    def test_probability_below_50_when_spot_below_strike(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        prob = strat._model_prob(
            spot=78000.0, strike=80000.0,
            hours_to_settle=2.0, drift_pct=-0.025,
        )
        assert prob < 0.5

    def test_probability_is_0_to_1(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        for spot, strike in [(80000, 80000), (100000, 80000), (50000, 80000)]:
            prob = strat._model_prob(spot=spot, strike=strike,
                                      hours_to_settle=2.0, drift_pct=0.0)
            assert 0.0 <= prob <= 1.0

    def test_probability_approaches_certainty_far_in_money(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        # Spot far above strike, only 0.1h to settle → nearly certain YES
        prob = strat._model_prob(
            spot=90000.0, strike=70000.0,
            hours_to_settle=0.1, drift_pct=0.1,
        )
        assert prob > 0.9

    def test_probability_decreases_with_more_time_remaining(self):
        """More time = more uncertainty = probability closer to 0.5."""
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        p_near = strat._model_prob(spot=82000.0, strike=80000.0,
                                    hours_to_settle=0.1, drift_pct=0.025)
        p_far = strat._model_prob(spot=82000.0, strike=80000.0,
                                   hours_to_settle=6.0, drift_pct=0.025)
        # Near settlement, in-money position should be more certain
        assert p_near > p_far


# ── TestPriceGuard ────────────────────────────────────────────────────


class TestPriceGuard:
    """Price range guard: 35-65¢ for ATM selection."""

    def test_rejects_market_below_35(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        mkt = _make_market(yes_price=20, yes_ask=22, volume=5000)
        result = strat._find_atm_market([mkt], 80000.0)
        assert result is None

    def test_rejects_market_above_65(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        mkt = _make_market(yes_price=70, yes_ask=72, volume=5000)
        result = strat._find_atm_market([mkt], 80000.0)
        assert result is None

    def test_accepts_market_at_50(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        mkt = _make_market(yes_price=49, yes_ask=51, volume=5000)
        result = strat._find_atm_market([mkt], 80000.0)
        assert result is not None

    def test_accepts_market_at_boundary_35(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        mkt = _make_market(yes_price=34, yes_ask=36, volume=5000)  # mid=35
        result = strat._find_atm_market([mkt], 80000.0)
        assert result is not None

    def test_accepts_market_at_boundary_65(self):
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        mkt = _make_market(yes_price=64, yes_ask=66, volume=5000)  # mid=65
        result = strat._find_atm_market([mkt], 80000.0)
        assert result is not None


# ── TestAssetCoverage ─────────────────────────────────────────────────


class TestAssetCoverage:
    """Strategy works for ETH and SOL as well as BTC."""

    def test_eth_strategy_generates_signal(self):
        strat = CryptoDailyStrategy(
            asset="ETH", series_ticker="KXETHD",
            min_drift_pct=0.005, min_edge_pct=0.03,
        )
        spot = 2550.0
        session_open = 2500.0  # +2%
        markets = _make_markets_around_strike(2520.0, spot, step=10.0, series="KXETHD")
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert "KXETHD" in sig.ticker

    def test_sol_strategy_generates_signal(self):
        strat = CryptoDailyStrategy(
            asset="SOL", series_ticker="KXSOLD",
            min_drift_pct=0.005, min_edge_pct=0.03,
        )
        spot = 102.0
        session_open = 100.0  # +2%
        markets = _make_markets_around_strike(101.0, spot, step=0.5, series="KXSOLD")
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert "KXSOLD" in sig.ticker

    def test_strategy_name_reflects_asset(self):
        btc_strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        eth_strat = CryptoDailyStrategy(asset="ETH", series_ticker="KXETHD")
        sol_strat = CryptoDailyStrategy(asset="SOL", series_ticker="KXSOLD")
        assert "btc" in btc_strat.name.lower() or "btc" in btc_strat.series_ticker.lower()
        assert "eth" in eth_strat.name.lower() or "eth" in eth_strat.series_ticker.lower()
        assert "sol" in sol_strat.name.lower() or "sol" in sol_strat.series_ticker.lower()


class TestDirectionFilter:
    """Tests for direction_filter='no' — contrarian NO-only mode (S47)."""

    def _make_markets_atm(self, spot: float, series: str = "KXBTCD") -> list:
        """Create ATM markets around spot price with good liquidity."""
        import math
        strike = round(spot / 500) * 500  # nearest $500
        markets = []
        for offset in [-1000, -500, 0, 500, 1000]:
            s = strike + offset
            # Price based on distance from ATM
            dist_pct = (spot - s) / spot
            yes_price = int(50 + dist_pct * 100)
            yes_price = max(10, min(90, yes_price))
            markets.append(_make_market(
                ticker=f"{series}-26MAR1021-T{s:.2f}",
                strike=s,
                yes_price=yes_price,
                yes_ask=yes_price + 2,
                volume=5000,
                minutes_to_close=120.0,
                series=series,
            ))
        return markets

    def test_direction_filter_no_fires_no_on_upward_drift(self):
        """direction_filter='no': positive drift triggers a NO signal."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.02, direction_filter="no",
        )
        spot = 71000.0
        session_open = 70000.0  # +1.4% drift
        markets = self._make_markets_atm(spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None, "Should fire a signal on upward drift with direction_filter='no'"
        assert sig.side == "no", f"direction_filter='no' must always bet NO, got {sig.side}"

    def test_direction_filter_no_ignores_downward_drift(self):
        """direction_filter='no': negative drift produces no signal."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, direction_filter="no",
        )
        spot = 69000.0
        session_open = 70000.0  # -1.4% drift (downward)
        markets = self._make_markets_atm(spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is None, "direction_filter='no' should NOT fire on downward drift"

    def test_direction_filter_no_ignores_flat_drift(self):
        """direction_filter='no': drift below threshold produces no signal."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, direction_filter="no",
        )
        spot = 70020.0
        session_open = 70000.0  # +0.03% drift (below 0.5% threshold)
        markets = self._make_markets_atm(spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is None, "direction_filter='no' should not fire on drift below threshold"

    def test_original_mode_fires_yes_on_upward_drift(self):
        """Original mode (no filter): positive drift → YES signal."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.02, direction_filter=None,
        )
        spot = 71000.0
        session_open = 70000.0
        # ATM markets centered at spot — YES is underpriced vs model (drift pushes model >50%)
        markets = _make_markets_around_strike(spot, spot, step=500.0)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert sig.side == "yes"

    def test_original_mode_fires_no_on_downward_drift(self):
        """Original mode (no filter): negative drift → NO signal."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, direction_filter=None,
        )
        spot = 69000.0
        session_open = 70000.0  # -1.4% drift
        markets = self._make_markets_atm(spot)
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None
        assert sig.side == "no"
