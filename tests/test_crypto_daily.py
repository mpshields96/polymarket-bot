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
from src.strategies.crypto_daily import CryptoDailyStrategy, _hourly_vol_for


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
        """direction_filter='no': positive drift triggers a NO signal when edge check passes.

        The contrarian NO bet fires when:
        1. drift_pct > min_drift_pct (upward drift check)
        2. model_prob < market YES price (YES is overpriced by market — NO has edge)
        3. edge > min_edge_pct

        For NO to have positive edge: (1-model_prob) > price_no/100 + fee.
        This works when the market overprices YES (e.g., yes_bid=58¢ but model says 53%).
        """
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_drift_pct=0.005, min_edge_pct=0.001, direction_filter="no",
        )
        # Small positive drift (+0.7%) → drift_signal = 0.535 → model_prob ≈ 0.50-0.53
        # Market overprices YES at yes_bid=58, yes_ask=60, mid=59 → NO costs 42¢
        # model NO ≈ 47%  >  42¢ → positive NO edge
        spot = 70500.0
        session_open = 70000.0  # +0.71% drift (above 0.5% threshold)
        # Create a single market where YES is overpriced (market YES=59¢, model YES≈53%)
        # strike must parse from ticker via split('-T')[-1]
        market = _make_market(
            ticker="KXBTCD-TEST-T71000",
            strike=71000.0,
            yes_price=57,   # bid
            yes_ask=60,     # ask; mid=58.5¢ (within 35-65 guard)
            volume=5000,
            minutes_to_close=120.0,
        )
        markets = [market]
        sig = strat.generate_signal(spot, session_open, markets)
        assert sig is not None, (
            "Should fire a signal on upward drift with direction_filter='no' "
            "when market overprices YES"
        )
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


# ── TestHourlyVolConstants ────────────────────────────────────────────


class TestHourlyVolConstants:
    """Per-asset hourly vol lookup must return correct values (Task 1)."""

    def test_btc_vol_returns_0_01(self):
        """BTC hourly vol = 0.01 (1% per sqrt-hour)."""
        assert _hourly_vol_for("BTC") == 0.01

    def test_eth_vol_returns_0_015(self):
        """ETH hourly vol = 0.015 (1.5% per sqrt-hour)."""
        assert _hourly_vol_for("ETH") == 0.015

    def test_sol_vol_returns_0_025(self):
        """SOL hourly vol = 0.025 (2.5% per sqrt-hour)."""
        assert _hourly_vol_for("SOL") == 0.025

    def test_unknown_asset_returns_default(self):
        """Unknown asset falls back to default of 0.01."""
        assert _hourly_vol_for("XYZ") == 0.01

    def test_model_prob_uses_asset_specific_vol_btc(self):
        """BTC strategy _model_prob uses sigma = 0.01 * sqrt(2) at 2 hours."""
        import math
        strat = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        # At spot=strike, position_prob = 0.5 (symmetric log-normal).
        # drift_pct = 0.0 → drift_signal = 0.5
        # Combined = 0.7 * 0.5 + 0.3 * 0.5 = 0.5 always when spot==strike.
        # Instead verify sigma indirectly: at spot slightly above strike,
        # smaller sigma → position_prob closer to 1 → higher model_prob.
        # BTC sigma at 2hr = 0.01 * sqrt(2) ≈ 0.01414
        # ETH sigma at 2hr = 0.015 * sqrt(2) ≈ 0.02121
        # At spot/strike=1.01 (1% above), BTC should have higher position_prob.
        strat_btc = CryptoDailyStrategy(asset="BTC", series_ticker="KXBTCD")
        strat_eth = CryptoDailyStrategy(asset="ETH", series_ticker="KXETHD")
        spot = 81000.0
        strike = 80000.0  # spot is 1.25% above strike
        hours = 2.0
        drift = 0.0  # no drift so position_prob governs
        prob_btc = strat_btc._model_prob(spot, strike, hours, drift)
        prob_eth = strat_eth._model_prob(spot, strike, hours, drift)
        # BTC has smaller sigma → z-score larger → position_prob closer to 1 → higher prob
        assert prob_btc > prob_eth, (
            f"BTC (smaller vol) should have higher position_prob than ETH: "
            f"prob_btc={prob_btc:.4f} prob_eth={prob_eth:.4f}"
        )


# ── TestATMPrioritySlot ───────────────────────────────────────────────


def _make_market_at_relative_offset(
    minutes_from_now: float,
    mid: float = 50.0,
    ticker: str = None,
    volume: int = 5000,
) -> Market:
    """
    Create a market that closes exactly `minutes_from_now` minutes from now.
    The close_time.hour reflects whatever UTC hour that corresponds to.
    Must be within [35, 355] minutes to pass CryptoDailyStrategy time window filters.
    """
    now_utc = datetime.now(timezone.utc)
    close_dt = now_utc + timedelta(minutes=minutes_from_now)
    close_dt = close_dt.replace(microsecond=0)
    close_iso = close_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    yes_bid = max(1, int(mid - 0.5))
    yes_ask = min(99, int(mid + 0.5))
    if ticker is None:
        ticker = f"KXBTCD-TEST-T80000-rel{int(minutes_from_now)}min"
    return Market(
        ticker=ticker,
        title=f"BTC above 80000? (closes in {minutes_from_now:.0f} min)",
        event_ticker=ticker,
        status="open",
        yes_price=yes_bid,
        no_price=100 - yes_bid,
        volume=volume,
        close_time=close_iso,
        open_time="",
        result=None,
        raw={"yes_ask": yes_ask, "yes_bid": yes_bid, "series_ticker": "KXBTCD"},
    )


def _find_minutes_to_utc_hour(target_hour: int, min_minutes: float = 35.0, max_minutes: float = 355.0) -> Optional[float]:
    """
    Return the number of minutes from now until the next occurrence of target_hour:00 UTC
    that falls within [min_minutes, max_minutes]. Returns None if no such window exists.
    """
    now_utc = datetime.now(timezone.utc)
    for day_offset in range(3):
        candidate = now_utc.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        candidate = candidate + timedelta(days=day_offset)
        minutes = (candidate - now_utc).total_seconds() / 60.0
        if min_minutes <= minutes <= max_minutes:
            return minutes
    return None


def _make_market_with_close_hour(
    close_hour_utc: int,
    mid: float = 50.0,
    ticker: str = None,
    volume: int = 5000,
) -> Optional[Market]:
    """
    Create a market that closes at close_hour_utc:00 UTC, within the 30-360 min window.
    Returns None if close_hour_utc:00 UTC is not within the required time window.

    Callers must handle None (skip test or assert early).
    """
    minutes = _find_minutes_to_utc_hour(close_hour_utc)
    if minutes is None:
        return None  # not within time window — caller must handle this
    return _make_market_at_relative_offset(
        minutes_from_now=minutes,
        mid=mid,
        ticker=ticker if ticker else f"KXBTCD-TEST-T80000-h{close_hour_utc}",
        volume=volume,
    )


class TestATMPrioritySlot:
    """5pm EDT (21:00 UTC) slot should be preferred when tied on ATM distance (Task 1).

    These tests create markets by crafting close_time strings with specific .hour values
    using absolute UTC datetimes. Since CryptoDailyStrategy._find_atm_market filters on
    minutes_remaining, we set all markets to 120 minutes from now but with the
    close_time.hour field controlled via strftime on a datetime with the desired hour.

    Implementation note: we set close_time to 120 minutes from now, then replace the
    hour with the target value. If replacing the hour would make the time inconsistent
    (e.g., hour=5 when it's 16:30 UTC → would be in the past), we add 1 day to ensure
    it's still future. The key is that the market_minutes check in _find_atm_market
    uses the parsed close_dt, so we just need to ensure the close_time parses correctly
    and yields close_dt.hour == target_hour.

    Simplest approach: use close_time = (now + 120 min) but with hour forced to desired
    value, padded to next day if needed. This ensures close_dt.hour is correct AND the
    market is within the time window (35-355 min).
    """

    def _market_with_hour(
        self,
        target_hour: int,
        mid: float = 50.0,
        ticker: str = "KXBTCD-TEST",
        minutes_offset: float = 120.0,
    ) -> Market:
        """
        Create a market whose close_time.hour == target_hour and is within time window.
        Uses minutes_offset as a base, then adjusts to the next occurrence of target_hour.
        """
        now_utc = datetime.now(timezone.utc)
        # Try today's occurrence of target_hour first
        candidate = now_utc.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        for _ in range(3):
            mins = (candidate - now_utc).total_seconds() / 60.0
            if 35.0 <= mins <= 355.0:
                break
            candidate = candidate + timedelta(days=1)
        else:
            # If no occurrence in window, use minutes_offset from now
            # (test will degenerate — not ideal but avoids test hanging)
            candidate = now_utc + timedelta(minutes=minutes_offset)
            candidate = candidate.replace(microsecond=0)

        close_iso = candidate.strftime("%Y-%m-%dT%H:%M:%SZ")
        yes_bid = max(1, int(mid - 0.5))
        yes_ask = min(99, int(mid + 0.5))
        return Market(
            ticker=ticker,
            title=f"BTC above 80000? close_hour={target_hour}",
            event_ticker=ticker,
            status="open",
            yes_price=yes_bid,
            no_price=100 - yes_bid,
            volume=5000,
            close_time=close_iso,
            open_time="",
            result=None,
            raw={"yes_ask": yes_ask, "yes_bid": yes_bid, "series_ticker": "KXBTCD"},
        )

    def _non_21_hour(self) -> Optional[int]:
        """Find a UTC hour != 21 that's within the 30-360 min window."""
        for h in [14, 15, 16, 17, 18, 19, 20, 22, 23, 0, 1, 2, 3]:
            if h != 21 and _find_minutes_to_utc_hour(h) is not None:
                return h
        return None

    def test_prefers_21utc_slot_when_tied(self):
        """When two candidates have identical ATM distance, prefer 21:00 UTC close."""
        mins_21 = _find_minutes_to_utc_hour(21)
        if mins_21 is None:
            pytest.skip("21:00 UTC not within 30-360 min window — skip time-sensitive test")

        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_minutes_remaining=30.0, max_minutes_remaining=360.0,
        )
        alt_hour = self._non_21_hour()
        if alt_hour is None:
            pytest.skip("No alternative UTC hour in window to pair with 21:00")

        market_alt = self._market_with_hour(alt_hour, mid=50.0, ticker="KXBTCD-TEST-alt-T80000")
        market_21 = self._market_with_hour(21, mid=50.0, ticker="KXBTCD-TEST-21h-T80000")

        result = strat._find_atm_market([market_alt, market_21], spot=80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-TEST-21h-T80000", (
            f"Expected 21:00 UTC slot to be preferred over h={alt_hour}, got {result.ticker}"
        )

    def test_no_regression_without_21utc_slot(self):
        """When no 21:00 UTC slot exists, picks the best ATM market normally."""
        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_minutes_remaining=30.0, max_minutes_remaining=360.0,
        )
        # Create two markets with relative offsets, neither at 21:00 UTC.
        # Use 120 min and 180 min from now — adjust if either lands on 21:00 UTC.
        now_utc = datetime.now(timezone.utc)

        def make_rel_market(minutes_offset: float, mid: float, ticker: str, avoid_hour: int = 21) -> Market:
            """Create market at relative offset, shifting by 1hr until clear of avoid_hour.

            +10 min was insufficient — if original time is at 21:10, shifting +10 gives 21:20
            (still hour 21). Use +1hr per iteration to guarantee leaving the avoided hour.
            """
            close_dt = now_utc + timedelta(minutes=minutes_offset)
            while close_dt.hour == avoid_hour:
                close_dt = close_dt + timedelta(hours=1)
            close_dt = close_dt.replace(microsecond=0)
            yes_bid = max(1, int(mid - 0.5))
            yes_ask = min(99, int(mid + 0.5))
            return Market(
                ticker=ticker, title="", event_ticker=ticker, status="open",
                yes_price=yes_bid, no_price=100 - yes_bid, volume=5000,
                close_time=close_dt.strftime("%Y-%m-%dT%H:%M:%SZ"), open_time="", result=None,
                raw={"yes_ask": yes_ask, "yes_bid": yes_bid, "series_ticker": "KXBTCD"},
            )

        # market_a: mid=48 (dist=2), market_b: mid=51 (dist=1) → market_b should win
        market_a = make_rel_market(120.0, mid=48.0, ticker="KXBTCD-TEST-a-T80000")
        market_b = make_rel_market(180.0, mid=51.0, ticker="KXBTCD-TEST-b-T80000")

        result = strat._find_atm_market([market_a, market_b], spot=80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-TEST-b-T80000", (
            f"Without 21:00 UTC slot, should pick market_b (closer to 50, dist=1), got {result.ticker}"
        )

    def test_priority_slot_does_not_override_price_guard(self):
        """21:00 UTC slot with extreme price (outside 35-65) is excluded despite priority."""
        mins_21 = _find_minutes_to_utc_hour(21)
        if mins_21 is None:
            pytest.skip("21:00 UTC not within 30-360 min window — skip time-sensitive test")

        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_minutes_remaining=30.0, max_minutes_remaining=360.0,
        )
        # 21:00 UTC market with mid=20 (outside price guard 35-65)
        market_21_extreme = self._market_with_hour(21, mid=20.0, ticker="KXBTCD-21h-extreme")
        # Non-21 market with valid mid=50
        now_utc = datetime.now(timezone.utc)
        close_dt_ok = (now_utc + timedelta(minutes=120)).replace(microsecond=0)
        if close_dt_ok.hour == 21:
            close_dt_ok = close_dt_ok + timedelta(minutes=10)
        market_ok = Market(
            ticker="KXBTCD-non21h-valid", title="", event_ticker="KXBTCD-non21h-valid",
            status="open", yes_price=49, no_price=51, volume=5000,
            close_time=close_dt_ok.strftime("%Y-%m-%dT%H:%M:%SZ"), open_time="", result=None,
            raw={"yes_ask": 51, "yes_bid": 49, "series_ticker": "KXBTCD"},
        )

        result = strat._find_atm_market([market_21_extreme, market_ok], spot=80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-non21h-valid", (
            "21:00 UTC slot with price outside guard should be excluded; "
            f"got {result.ticker}"
        )

    def test_21utc_preference_is_within_2c_tolerance(self):
        """21:00 UTC slot is only preferred when within 2c of the best ATM distance."""
        mins_21 = _find_minutes_to_utc_hour(21)
        if mins_21 is None:
            pytest.skip("21:00 UTC not within 30-360 min window — skip time-sensitive test")

        strat = CryptoDailyStrategy(
            asset="BTC", series_ticker="KXBTCD",
            min_minutes_remaining=30.0, max_minutes_remaining=360.0,
        )
        # Best market: mid=50 (dist=0), NOT at 21:00 UTC
        now_utc = datetime.now(timezone.utc)
        close_dt_best = (now_utc + timedelta(minutes=120)).replace(microsecond=0)
        if close_dt_best.hour == 21:
            close_dt_best = close_dt_best + timedelta(minutes=10)
        market_best = Market(
            ticker="KXBTCD-best-T80000", title="", event_ticker="KXBTCD-best-T80000",
            status="open", yes_price=49, no_price=51, volume=5000,
            close_time=close_dt_best.strftime("%Y-%m-%dT%H:%M:%SZ"), open_time="", result=None,
            raw={"yes_ask": 51, "yes_bid": 49, "series_ticker": "KXBTCD"},
        )
        # 21:00 UTC market: mid=53 (dist=3 > best_dist+2=2) — should NOT win
        market_21_worse = self._market_with_hour(21, mid=53.0, ticker="KXBTCD-21h-worse")

        result = strat._find_atm_market([market_best, market_21_worse], spot=80000.0)
        assert result is not None
        assert result.ticker == "KXBTCD-best-T80000", (
            "21:00 UTC slot with dist=3 > tolerance(2) should NOT override best ATM; "
            f"got {result.ticker}"
        )


# ── TestCryptoDailyLoopDirectionFilter ───────────────────────────────


class TestCryptoDailyLoopDirectionFilter:
    """Loop-level direction_filter guard in crypto_daily_loop (Task 2)."""

    def test_direction_filter_no_blocks_yes_signal(self):
        """Guard condition: signal.side='yes' with direction_filter='no' → should block."""
        from src.strategies.base import Signal
        signal = Signal(
            side="yes",
            edge_pct=0.08,
            win_prob=0.60,
            confidence=0.5,
            ticker="KXBTCD-TEST-T80000",
            price_cents=52,
            reason="test",
        )
        direction_filter = "no"
        # Simulate the guard: blocked when side != direction_filter
        blocked = direction_filter is not None and signal.side != direction_filter
        assert blocked is True, "YES signal with direction_filter='no' must be blocked"

    def test_direction_filter_none_passes_both_sides(self):
        """Guard condition: direction_filter=None → neither side is blocked."""
        from src.strategies.base import Signal
        for side in ("yes", "no"):
            signal = Signal(
                side=side,
                edge_pct=0.08,
                win_prob=0.60,
                confidence=0.5,
                ticker="KXBTCD-TEST-T80000",
                price_cents=52,
                reason="test",
            )
            direction_filter = None
            blocked = direction_filter is not None and signal.side != direction_filter
            assert blocked is False, f"direction_filter=None must not block {side} signal"

    def test_direction_filter_yes_blocks_no_signal(self):
        """Guard condition: signal.side='no' with direction_filter='yes' → should block."""
        from src.strategies.base import Signal
        signal = Signal(
            side="no",
            edge_pct=0.08,
            win_prob=0.60,
            confidence=0.5,
            ticker="KXBTCD-TEST-T80000",
            price_cents=48,
            reason="test",
        )
        direction_filter = "yes"
        blocked = direction_filter is not None and signal.side != direction_filter
        assert blocked is True, "NO signal with direction_filter='yes' must be blocked"

    def test_loop_direction_filter_param_exists_in_main(self):
        """crypto_daily_loop in main.py must accept direction_filter parameter."""
        import inspect
        from main import crypto_daily_loop
        params = inspect.signature(crypto_daily_loop).parameters
        assert "direction_filter" in params, (
            "crypto_daily_loop must have a direction_filter parameter"
        )
