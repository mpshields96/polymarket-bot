"""
Tests for src/strategies/unemployment_rate.py and UNRATE extension to src/data/fred.py.

Mocks FREDFeed and Market objects to control inputs.
No live HTTP calls.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.data.fred import FREDFeed, FREDSnapshot
from src.platforms.kalshi import Market, OrderBook
from src.strategies.unemployment_rate import (
    BLS_RELEASE_DATES_2026,
    UnemploymentRateStrategy,
    compute_unrate_model_prob,
    days_until_bls,
    load_from_config,
    next_bls_date,
    parse_unrate_ticker,
)


# ── Helpers ───────────────────────────────────────────────────────────


def _make_snap(
    fed_funds_rate: float = 3.64,
    yield_2yr: float = 3.90,
    cpi_latest: float = 320.0,
    cpi_prior: float = 319.5,
    cpi_prior2: float = 319.0,
    unrate_latest: float = 4.3,
    unrate_prior: float = 4.4,
    unrate_prior2: float = 4.5,
) -> FREDSnapshot:
    return FREDSnapshot(
        fed_funds_rate=fed_funds_rate,
        yield_2yr=yield_2yr,
        cpi_latest=cpi_latest,
        cpi_prior=cpi_prior,
        cpi_prior2=cpi_prior2,
        fetched_at=datetime.now(timezone.utc),
        unrate_latest=unrate_latest,
        unrate_prior=unrate_prior,
        unrate_prior2=unrate_prior2,
    )


def _make_fred(snap: FREDSnapshot, stale: bool = False) -> FREDFeed:
    feed = MagicMock(spec=FREDFeed)
    feed.is_stale = stale
    feed.snapshot.return_value = snap
    return feed


def _make_market(
    ticker: str = "KXUNRATE-202503-4.0",
    title: str = "Unemployment rate above 4.0%",
    yes_price: int = 40,
    no_price: int = 60,
    minutes_remaining: float = 5000.0,
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(minutes=minutes_remaining)).isoformat()
    open_time = (now - timedelta(hours=100)).isoformat()
    return Market(
        ticker=ticker,
        title=title,
        event_ticker="KXUNRATE-202503",
        status="open",
        yes_price=yes_price,
        no_price=no_price,
        volume=1000,
        close_time=close_time,
        open_time=open_time,
        result=None,
        raw={},
    )


def _default_strategy(
    snap: FREDSnapshot = None,
    days_before: int = 365,
) -> UnemploymentRateStrategy:
    snap = snap or _make_snap()
    return UnemploymentRateStrategy(
        fred_feed=_make_fred(snap),
        min_edge_pct=0.01,
        min_minutes_remaining=1.0,
        days_before_release=days_before,
    )


# ── Group A: FREDSnapshot backward compatibility ───────────────────────


class TestFREDSnapshotBackwardCompat:
    def test_existing_fields_still_construct_without_unrate(self):
        """Existing callers that don't pass unrate_* should not break."""
        snap = FREDSnapshot(
            fed_funds_rate=3.64,
            yield_2yr=3.90,
            cpi_latest=320.0,
            cpi_prior=319.5,
            cpi_prior2=319.0,
            fetched_at=datetime.now(timezone.utc),
        )
        assert snap.fed_funds_rate == 3.64
        assert snap.yield_2yr == 3.90

    def test_unrate_latest_defaults_to_zero(self):
        snap = FREDSnapshot(
            fed_funds_rate=3.64,
            yield_2yr=3.90,
            cpi_latest=320.0,
            cpi_prior=319.5,
            cpi_prior2=319.0,
            fetched_at=datetime.now(timezone.utc),
        )
        assert snap.unrate_latest == 0.0

    def test_unrate_prior_defaults_to_zero(self):
        snap = FREDSnapshot(
            fed_funds_rate=3.64,
            yield_2yr=3.90,
            cpi_latest=320.0,
            cpi_prior=319.5,
            cpi_prior2=319.0,
            fetched_at=datetime.now(timezone.utc),
        )
        assert snap.unrate_prior == 0.0

    def test_unrate_prior2_defaults_to_zero(self):
        snap = FREDSnapshot(
            fed_funds_rate=3.64,
            yield_2yr=3.90,
            cpi_latest=320.0,
            cpi_prior=319.5,
            cpi_prior2=319.0,
            fetched_at=datetime.now(timezone.utc),
        )
        assert snap.unrate_prior2 == 0.0


# ── Group B: FREDSnapshot UNRATE fields ───────────────────────────────


class TestFREDSnapshotUnrateFields:
    def test_unrate_fields_accepted(self):
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        assert snap.unrate_latest == 4.3
        assert snap.unrate_prior == 4.4
        assert snap.unrate_prior2 == 4.5

    def test_unrate_trend_declining(self):
        """trend = (latest - prior2) / 2 = (4.3 - 4.5) / 2 = -0.1"""
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        assert abs(snap.unrate_trend - (-0.1)) < 1e-6

    def test_unrate_forecast_extrapolates_one_step(self):
        """forecast = latest + trend = 4.3 + (-0.1) = 4.2"""
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        assert abs(snap.unrate_forecast - 4.2) < 1e-6

    def test_unrate_trend_rising(self):
        """Increasing unemployment: 4.0 → 4.2 → 4.4, trend = (4.4-4.0)/2 = +0.2"""
        snap = _make_snap(unrate_latest=4.4, unrate_prior=4.2, unrate_prior2=4.0)
        assert abs(snap.unrate_trend - 0.2) < 1e-6

    def test_unrate_flat_trend(self):
        """Flat: all same. trend = 0, forecast = latest."""
        snap = _make_snap(unrate_latest=4.2, unrate_prior=4.2, unrate_prior2=4.2)
        assert abs(snap.unrate_trend) < 1e-6
        assert abs(snap.unrate_forecast - 4.2) < 1e-6


# ── Group C: BLS window helpers ───────────────────────────────────────


class TestBLSWindowHelpers:
    def test_bls_dates_list_has_12_entries(self):
        assert len(BLS_RELEASE_DATES_2026) == 12

    def test_bls_dates_are_sorted(self):
        assert BLS_RELEASE_DATES_2026 == sorted(BLS_RELEASE_DATES_2026)

    def test_next_bls_date_before_march(self):
        """Feb 28 → next is Mar 7."""
        result = next_bls_date(today=date(2026, 2, 28))
        assert result == date(2026, 3, 7)

    def test_next_bls_date_on_release_day(self):
        """On release day itself, return that day."""
        result = next_bls_date(today=date(2026, 3, 7))
        assert result == date(2026, 3, 7)

    def test_next_bls_date_day_after_release(self):
        """Day after March 7 → next is April 3."""
        result = next_bls_date(today=date(2026, 3, 8))
        assert result == date(2026, 4, 3)

    def test_next_bls_date_after_all_2026(self):
        """After Dec 4, no dates left → None."""
        result = next_bls_date(today=date(2026, 12, 5))
        assert result is None

    def test_days_until_bls_seven_days_before(self):
        """Feb 28 is 7 days before Mar 7."""
        result = days_until_bls(today=date(2026, 2, 28))
        assert result == 7

    def test_days_until_bls_on_release_day(self):
        result = days_until_bls(today=date(2026, 3, 7))
        assert result == 0

    def test_days_until_bls_after_all_2026(self):
        result = days_until_bls(today=date(2026, 12, 31))
        assert result is None


# ── Group D: compute_unrate_model_prob ────────────────────────────────


class TestComputeUnrateModelProb:
    def test_prob_above_threshold_below_forecast(self):
        """
        forecast=4.2, threshold=4.0, uncertainty=0.2
        P(YES) = 1 - norm.cdf((4.0 - 4.2) / 0.2) = 1 - norm.cdf(-1) ≈ 0.841
        """
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        # snap.unrate_forecast = 4.2
        prob = compute_unrate_model_prob(snap, threshold=4.0, uncertainty_band=0.2)
        assert abs(prob - 0.8413) < 0.002

    def test_prob_at_threshold_equals_forecast(self):
        """
        When threshold == forecast, P(YES) = 0.5 exactly.
        """
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        # forecast = 4.2
        prob = compute_unrate_model_prob(snap, threshold=4.2, uncertainty_band=0.2)
        assert abs(prob - 0.5) < 0.002

    def test_prob_above_threshold_far_above_forecast(self):
        """
        threshold=5.0 >> forecast=4.2: P(YES) ≈ 0 (very unlikely to be above 5.0 when forecast is 4.2)
        """
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        prob = compute_unrate_model_prob(snap, threshold=5.0, uncertainty_band=0.2)
        assert prob < 0.01

    def test_prob_returns_float_in_0_1(self):
        snap = _make_snap()
        prob = compute_unrate_model_prob(snap, threshold=4.0)
        assert 0.0 <= prob <= 1.0

    def test_flat_trend_uses_latest_as_forecast(self):
        """Flat trend: forecast = latest = 4.3. threshold=4.3 → prob ≈ 0.5"""
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.3, unrate_prior2=4.3)
        prob = compute_unrate_model_prob(snap, threshold=4.3, uncertainty_band=0.2)
        assert abs(prob - 0.5) < 0.002


# ── Group E: UnemploymentRateStrategy.generate_signal ─────────────────


class TestUnemploymentRateStrategyGates:
    def test_outside_bls_window_returns_none(self):
        """If next BLS is 30 days away and window is 7 days, skip."""
        s = _default_strategy(days_before=7)
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=30):
            assert s.generate_signal(market, ob, None) is None

    def test_days_until_bls_none_returns_none(self):
        """If no BLS date remaining, skip."""
        s = _default_strategy(days_before=7)
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=None):
            assert s.generate_signal(market, ob, None) is None

    def test_stale_fred_returns_none(self):
        snap = _make_snap()
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap, stale=True),
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            assert s.generate_signal(market, ob, None) is None

    def test_none_snapshot_returns_none(self):
        feed = _make_fred(_make_snap())
        feed.snapshot.return_value = None
        s = UnemploymentRateStrategy(
            fred_feed=feed,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            assert s.generate_signal(market, ob, None) is None

    def test_non_kxunrate_ticker_returns_none(self):
        """Ticker that doesn't match KXUNRATE pattern → skip."""
        s = _default_strategy(days_before=365)
        market = _make_market(ticker="KXBTC15M-26MAR-H0")
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            assert s.generate_signal(market, ob, None) is None

    def test_insufficient_time_remaining_returns_none(self):
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(_make_snap()),
            min_edge_pct=0.01,
            min_minutes_remaining=60.0,
            days_before_release=365,
        )
        market = _make_market(minutes_remaining=30.0)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            assert s.generate_signal(market, ob, None) is None

    def test_insufficient_edge_returns_none(self):
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(_make_snap()),
            min_edge_pct=0.99,   # impossibly high
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(yes_price=50, no_price=50)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            assert s.generate_signal(market, ob, None) is None


class TestUnemploymentRateSignalGeneration:
    def test_underpriced_yes_generates_yes_signal(self):
        """
        forecast=4.2, threshold=4.0 → model P(YES) ≈ 0.84.
        Market: YES=40¢ → strong buy YES signal.
        """
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-4.0", yes_price=40, no_price=60)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        assert result is not None
        assert result.side == "yes"
        assert result.ticker == "KXUNRATE-202503-4.0"

    def test_overpriced_yes_generates_no_signal(self):
        """
        forecast=4.2, threshold=5.0 → model P(YES) ≈ 0.
        Market: YES=95¢ → strong buy NO signal.
        """
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-5.0", yes_price=95, no_price=5)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        assert result is not None
        assert result.side == "no"

    def test_signal_ticker_matches_market(self):
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-4.0", yes_price=40, no_price=60)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        if result is not None:
            assert result.ticker == "KXUNRATE-202503-4.0"

    def test_signal_reason_contains_bls(self):
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-4.0", yes_price=40, no_price=60)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        if result is not None:
            assert "BLS" in result.reason

    def test_signal_win_prob_above_coinflip(self):
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-4.0", yes_price=40, no_price=60)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        if result is not None:
            assert result.win_prob >= 0.51

    def test_signal_edge_pct_positive(self):
        snap = _make_snap(unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
        s = UnemploymentRateStrategy(
            fred_feed=_make_fred(snap),
            min_edge_pct=0.05,
            min_minutes_remaining=1.0,
            days_before_release=365,
        )
        market = _make_market(ticker="KXUNRATE-202503-4.0", yes_price=40, no_price=60)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.unemployment_rate.days_until_bls", return_value=5):
            result = s.generate_signal(market, ob, None)
        if result is not None:
            assert result.edge_pct > 0.0


class TestUnemploymentStrategyName:
    def test_strategy_name(self):
        s = _default_strategy()
        assert s.name == "unemployment_rate_v1"


# ── Group F: parse_unrate_ticker ──────────────────────────────────────


class TestParseUnrateTicker:
    def test_standard_format_4_0(self):
        assert parse_unrate_ticker("KXUNRATE-202503-4.0") == pytest.approx(4.0)

    def test_standard_format_3_5(self):
        assert parse_unrate_ticker("KXUNRATE-202504-3.5") == pytest.approx(3.5)

    def test_standard_format_4_2(self):
        assert parse_unrate_ticker("KXUNRATE-202501-4.2") == pytest.approx(4.2)

    def test_non_unrate_ticker_returns_none(self):
        assert parse_unrate_ticker("KXBTC15M-26MAR-H0") is None

    def test_empty_string_returns_none(self):
        assert parse_unrate_ticker("") is None

    def test_fomc_ticker_returns_none(self):
        assert parse_unrate_ticker("KXFEDDECISION-26MAR-H0") is None

    def test_partial_match_returns_none(self):
        assert parse_unrate_ticker("KXUNRATE") is None


# ── Group G: load_from_config ─────────────────────────────────────────


class TestUnemploymentFactory:
    def test_load_from_config_returns_strategy(self):
        s = load_from_config()
        assert isinstance(s, UnemploymentRateStrategy)

    def test_load_from_config_name_correct(self):
        s = load_from_config()
        assert s.name == "unemployment_rate_v1"
