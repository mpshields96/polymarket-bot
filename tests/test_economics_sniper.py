"""Tests for EconomicsSniper strategy — paper-only KXCPI/KXGDP FLB sniping.

TDD: tests written before implementation.
Academic basis: Burgi et al. (2026) [SSRN 5502658] FLB in economics contracts.
CCA REQ-032: entry YES>=88c, 24-48h window, 0.5x Kelly.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


def _make_market(yes_price: int, no_price: int, hours_to_close: float):
    """Helper: build a mock Market object with given prices and close_time."""
    close_time = datetime.now(timezone.utc) + timedelta(hours=hours_to_close)
    m = MagicMock()
    m.ticker = f"KXCPI-TEST-T0.6"
    m.yes_price = yes_price
    m.no_price = no_price
    m.close_time = close_time.isoformat().replace("+00:00", "Z")
    return m


class TestEconomicsSniperFactory:
    def test_make_economics_sniper_returns_strategy(self):
        from src.strategies.economics_sniper import make_economics_sniper, EconomicsSniperStrategy
        strat = make_economics_sniper()
        assert isinstance(strat, EconomicsSniperStrategy)

    def test_economics_sniper_name(self):
        from src.strategies.economics_sniper import make_economics_sniper
        strat = make_economics_sniper()
        assert strat.name == "economics_sniper_v1"

    def test_paper_calibration_usd(self):
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        assert strat.PAPER_CALIBRATION_USD == 0.50


class TestEconomicsSniperTimeGate:
    def test_too_early_returns_none(self):
        """Market >48h away → skip."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=72)
        assert strat.generate_signal(market) is None

    def test_exactly_at_boundary_returns_none(self):
        """Market at exactly 48h → skip (strictly less than)."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=48.01)
        assert strat.generate_signal(market) is None

    def test_inside_window_returns_signal(self):
        """Market 24h away + price in zone → should return signal."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None

    def test_hard_skip_near_settlement(self):
        """Market <5 min to close → skip (settlement imminent)."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=0.06)  # ~3.6 min
        assert strat.generate_signal(market) is None

    def test_no_close_time_returns_none(self):
        """Market with unparseable close_time → skip."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        m = MagicMock()
        m.ticker = "KXGDP-TEST"
        m.yes_price = 91
        m.no_price = 8
        m.close_time = "not-a-date"
        assert strat.generate_signal(m) is None


class TestEconomicsSniperPriceFilter:
    def test_yes_below_floor_returns_none(self):
        """YES=87c is below 88c floor → skip."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=87, no_price=12, hours_to_close=24)
        assert strat.generate_signal(market) is None

    def test_yes_at_floor_returns_signal(self):
        """YES=88c is at floor → should fire."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=88, no_price=11, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert result.side == "yes"
        assert result.price_cents == 88

    def test_no_at_floor_returns_signal(self):
        """NO=88c is at floor → should fire."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=11, no_price=88, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert result.side == "no"
        assert result.price_cents == 88

    def test_ceiling_blocks_yes_94c(self):
        """YES=94c hits ceiling (slippage → 95c) → skip."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=94, no_price=5, hours_to_close=24)
        assert strat.generate_signal(market) is None

    def test_yes_93c_allowed(self):
        """YES=93c is below ceiling → allowed."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=93, no_price=6, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None

    def test_neither_side_in_range_returns_none(self):
        """YES=50c, NO=48c — neither side in zone → skip."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=50, no_price=48, hours_to_close=24)
        assert strat.generate_signal(market) is None


class TestEconomicsSniperNoDriftRequired:
    def test_no_coin_drift_param(self):
        """generate_signal takes only market, no coin_drift_pct — unlike ExpirySniperStrategy."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        import inspect
        strat = EconomicsSniperStrategy()
        sig = inspect.signature(strat.generate_signal)
        assert "coin_drift_pct" not in sig.parameters

    def test_fires_without_drift_context(self):
        """Strategy fires purely on price + time — no underlying asset needed."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert result.side == "yes"


class TestEconomicsSniperSignalFields:
    def test_signal_has_positive_edge(self):
        """Signal edge should be positive (FLB gives slight edge)."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert result.edge_pct > 0

    def test_signal_win_prob_above_price(self):
        """win_prob should be slightly above entry price (FLB premium)."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert result.win_prob > 0.91  # > entry price

    def test_signal_reason_contains_settlement_context(self):
        """Signal reason should mention settlement timeframe."""
        from src.strategies.economics_sniper import EconomicsSniperStrategy
        strat = EconomicsSniperStrategy()
        market = _make_market(yes_price=91, no_price=8, hours_to_close=24)
        result = strat.generate_signal(market)
        assert result is not None
        assert "settlement" in result.reason.lower() or "FLB" in result.reason
