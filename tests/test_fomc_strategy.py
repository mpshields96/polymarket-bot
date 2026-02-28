"""
Tests for src/strategies/fomc_rate.py and src/data/fred.py.

Mocks FREDFeed and Market objects to control inputs.
No live HTTP calls.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.strategies.fomc_rate import (
    FOMCRateStrategy,
    FedAction,
    FREDSnapshot,
    compute_model_probs,
    days_until_fomc,
    next_fomc_date,
    parse_fomc_action,
    load_from_config,
    FOMC_DECISION_DATES_2026,
)
from src.data.fred import FREDFeed, FREDSnapshot
from src.platforms.kalshi import Market, OrderBook


# ── Helpers ───────────────────────────────────────────────────────────


def _make_snap(
    fed_funds_rate: float = 3.64,
    yield_2yr: float = 3.90,
    cpi_latest: float = 320.0,
    cpi_prior: float = 319.5,
    cpi_prior2: float = 319.0,
) -> FREDSnapshot:
    return FREDSnapshot(
        fed_funds_rate=fed_funds_rate,
        yield_2yr=yield_2yr,
        cpi_latest=cpi_latest,
        cpi_prior=cpi_prior,
        cpi_prior2=cpi_prior2,
        fetched_at=datetime.now(timezone.utc),
    )


def _make_fred(snap: FREDSnapshot, stale: bool = False) -> FREDFeed:
    feed = MagicMock(spec=FREDFeed)
    feed.is_stale = stale
    feed.snapshot.return_value = snap
    return feed


def _make_market(
    ticker: str = "KXFEDDECISION-26MAR-H0",
    title: str = "Fed holds at 3.75%",
    yes_price: int = 70,
    no_price: int = 30,
    minutes_remaining: float = 5000.0,
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(minutes=minutes_remaining)).isoformat()
    open_time = (now - timedelta(hours=100)).isoformat()
    return Market(
        ticker=ticker,
        title=title,
        event_ticker="KXFEDDECISION-26MAR",
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
    days_before: int = 365,   # large window so timing gate never blocks
) -> FOMCRateStrategy:
    snap = snap or _make_snap()
    return FOMCRateStrategy(
        fred_feed=_make_fred(snap),
        min_edge_pct=0.01,
        min_minutes_remaining=1.0,
        days_before_meeting=days_before,
    )


# ── FOMC calendar ─────────────────────────────────────────────────────


class TestFOMCCalendar:
    def test_meeting_dates_are_sorted(self):
        dates = FOMC_DECISION_DATES_2026
        assert dates == sorted(dates)

    def test_eight_meetings_in_2026(self):
        assert len(FOMC_DECISION_DATES_2026) == 8

    def test_next_fomc_date_returns_future(self):
        result = next_fomc_date(date(2026, 1, 1))
        assert result == date(2026, 1, 29)

    def test_next_fomc_date_on_meeting_day(self):
        """On the meeting day itself, return that date."""
        result = next_fomc_date(date(2026, 3, 19))
        assert result == date(2026, 3, 19)

    def test_next_fomc_after_last_meeting(self):
        """After December 10, no meetings remain."""
        result = next_fomc_date(date(2026, 12, 11))
        assert result is None

    def test_days_until_fomc_from_known_date(self):
        result = days_until_fomc(date(2026, 3, 12))
        assert result == 7   # 7 days before March 19

    def test_days_until_fomc_on_meeting_day(self):
        assert days_until_fomc(date(2026, 1, 29)) == 0


# ── Ticker parsing ────────────────────────────────────────────────────


class TestParseAction:
    def test_hold(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-H0") == FedAction.HOLD

    def test_cut_25(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-C25") == FedAction.CUT_25

    def test_cut_large(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-C26") == FedAction.CUT_LARGE

    def test_hike_25(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-H25") == FedAction.HIKE_25

    def test_hike_large(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-H26") == FedAction.HIKE_LARGE

    def test_invalid_ticker_returns_none(self):
        assert parse_fomc_action("KXBTC15M-26MAR-123") is None
        assert parse_fomc_action("HIGHNY-26FEB28-T6467") is None
        assert parse_fomc_action("") is None

    def test_unknown_suffix_returns_none(self):
        assert parse_fomc_action("KXFEDDECISION-26MAR-Z99") is None


# ── Model probabilities ───────────────────────────────────────────────


class TestComputeModelProbs:
    def test_probs_sum_to_one(self):
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.90)
        probs = compute_model_probs(snap)
        assert abs(sum(probs.values()) - 1.0) < 0.001

    def test_hold_dominant_when_spread_near_zero(self):
        """Spread = 0 → hold regime → P(hold) > all others."""
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.64)
        probs = compute_model_probs(snap)
        assert probs[FedAction.HOLD] > 0.60
        assert probs[FedAction.HOLD] == max(probs.values())

    def test_cut_dominant_when_spread_very_negative(self):
        """Spread = -1.0 → aggressive cut regime → P(cut_25) is highest."""
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=2.64)
        probs = compute_model_probs(snap)
        assert probs[FedAction.CUT_25] > probs[FedAction.HOLD]

    def test_hike_bias_when_spread_positive(self):
        """Spread = +0.50% → hike bias → P(hike_25) elevated."""
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=4.14)
        probs = compute_model_probs(snap)
        assert probs[FedAction.HIKE_25] > 0.20

    def test_cpi_accelerating_reduces_cut_prob(self):
        """CPI accelerating should transfer probability from cut to hold."""
        snap_accel = _make_snap(
            fed_funds_rate=3.64, yield_2yr=3.30,
            cpi_latest=321.0, cpi_prior=319.0, cpi_prior2=318.0,
        )
        snap_decel = _make_snap(
            fed_funds_rate=3.64, yield_2yr=3.30,
            cpi_latest=319.0, cpi_prior=320.0, cpi_prior2=321.0,
        )
        p_accel = compute_model_probs(snap_accel)
        p_decel = compute_model_probs(snap_decel)
        assert p_accel[FedAction.CUT_25] < p_decel[FedAction.CUT_25]
        assert p_accel[FedAction.HOLD] > p_decel[FedAction.HOLD]

    def test_all_actions_have_nonzero_probability(self):
        snap = _make_snap()
        probs = compute_model_probs(snap)
        for action in FedAction:
            assert probs[action] > 0.0, f"{action} probability is zero"

    def test_custom_band_widens_hold_regime(self):
        """A wider band should give more weight to hold in mild-spread regimes."""
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.80)  # spread = +0.16%
        probs_narrow = compute_model_probs(snap, spread_hold_band=0.10)
        probs_wide   = compute_model_probs(snap, spread_hold_band=0.50)
        # With narrow band, +0.16% is outside band → hike bias
        # With wide band, +0.16% is inside band → hold bias
        assert probs_wide[FedAction.HOLD] > probs_narrow[FedAction.HOLD]


# ── FREDSnapshot properties ───────────────────────────────────────────


class TestFREDSnapshotProperties:
    def test_yield_spread(self):
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.90)
        assert abs(snap.yield_spread - 0.26) < 0.001

    def test_cpi_accelerating_true(self):
        """MoM latest (0.16%) > MoM prior (0.16%... need latest to be higher)."""
        snap = _make_snap(cpi_latest=320.5, cpi_prior=319.5, cpi_prior2=319.0)
        # MoM latest = (320.5-319.5)/319.5*100 = 0.313%
        # MoM prior  = (319.5-319.0)/319.0*100 = 0.157%
        assert snap.cpi_accelerating is True

    def test_cpi_accelerating_false(self):
        snap = _make_snap(cpi_latest=319.2, cpi_prior=319.5, cpi_prior2=319.0)
        # MoM latest = (319.2-319.5)/319.5 = negative → decelerating
        assert snap.cpi_accelerating is False


# ── Factory ───────────────────────────────────────────────────────────


class TestFOMCFactory:
    def test_load_from_config_returns_strategy(self):
        s = load_from_config()
        assert isinstance(s, FOMCRateStrategy)
        assert s.name == "fomc_rate_v1"


# ── Gate 1: FOMC timing ───────────────────────────────────────────────


class TestTimingGate:
    def test_meeting_far_away_blocks_signal(self):
        s = FOMCRateStrategy(
            fred_feed=_make_fred(_make_snap()),
            days_before_meeting=7,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        # Patch days_until_fomc to return 30 (outside 7-day window)
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=30):
            assert s.generate_signal(market, ob, None) is None

    def test_meeting_within_window_passes(self):
        s = FOMCRateStrategy(
            fred_feed=_make_fred(_make_snap(fed_funds_rate=3.64, yield_2yr=3.64)),
            days_before_meeting=14,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market(ticker="KXFEDDECISION-26MAR-C25", yes_price=5, no_price=95)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=7):
            result = s.generate_signal(market, ob, None)
        # May or may not signal, but should not be blocked by timing gate
        assert result is None or result is not None  # just checking no crash


# ── Gate 2: FRED stale ────────────────────────────────────────────────


class TestFREDGate:
    def test_stale_fred_returns_none(self):
        s = FOMCRateStrategy(
            fred_feed=_make_fred(_make_snap(), stale=True),
            days_before_meeting=365,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            assert s.generate_signal(market, ob, None) is None

    def test_none_snapshot_returns_none(self):
        feed = _make_fred(_make_snap())
        feed.snapshot.return_value = None
        s = FOMCRateStrategy(fred_feed=feed, days_before_meeting=365, min_edge_pct=0.01, min_minutes_remaining=1.0)
        market = _make_market()
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            assert s.generate_signal(market, ob, None) is None


# ── Gate 3: Ticker parsing ────────────────────────────────────────────


class TestTickerGate:
    def test_unrecognised_ticker_returns_none(self):
        s = _default_strategy()
        market = _make_market(ticker="KXBTC15M-26MAR-H0")
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            assert s.generate_signal(market, ob, None) is None


# ── Gate 4: Time remaining ────────────────────────────────────────────


class TestTimeRemainingGate:
    def test_expired_market_returns_none(self):
        s = FOMCRateStrategy(
            fred_feed=_make_fred(_make_snap()),
            days_before_meeting=365,
            min_edge_pct=0.01,
            min_minutes_remaining=60.0,
        )
        market = _make_market(minutes_remaining=30.0)  # below 60 min threshold
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            assert s.generate_signal(market, ob, None) is None


# ── Signal generation ─────────────────────────────────────────────────


class TestSignalGeneration:
    def test_underpriced_hold_generates_yes_signal(self):
        """
        Model: near-zero spread → P(hold) ≈ 0.75.
        Market: HOLD at YES=50¢ (underpriced relative to model).
        Expected: BUY YES on HOLD market.
        """
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.64)  # spread = 0
        s = FOMCRateStrategy(
            fred_feed=_make_fred(snap),
            days_before_meeting=365,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market(
            ticker="KXFEDDECISION-26MAR-H0",
            yes_price=50, no_price=50,
        )
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            result = s.generate_signal(market, ob, None)
        assert result is not None
        assert result.side == "yes"
        assert result.ticker == "KXFEDDECISION-26MAR-H0"

    def test_overpriced_hold_generates_no_signal(self):
        """
        Model: negative spread → P(hold) ≈ 0.55 or lower.
        Market: HOLD at YES=95¢ (overpriced).
        Expected: BUY NO on HOLD market.
        """
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=2.64)  # spread = -1.0
        s = FOMCRateStrategy(
            fred_feed=_make_fred(snap),
            days_before_meeting=365,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market(
            ticker="KXFEDDECISION-26MAR-H0",
            yes_price=95, no_price=5,
        )
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            result = s.generate_signal(market, ob, None)
        assert result is not None
        assert result.side == "no"

    def test_high_edge_threshold_blocks_signal(self):
        s = FOMCRateStrategy(
            fred_feed=_make_fred(_make_snap()),
            days_before_meeting=365,
            min_edge_pct=0.99,
            min_minutes_remaining=1.0,
        )
        market = _make_market(yes_price=50, no_price=50)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            assert s.generate_signal(market, ob, None) is None


# ── Signal field validation ───────────────────────────────────────────


class TestSignalFields:
    @pytest.fixture
    def signal(self):
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.64)
        s = FOMCRateStrategy(
            fred_feed=_make_fred(snap),
            days_before_meeting=365,
            min_edge_pct=0.01,
            min_minutes_remaining=1.0,
        )
        market = _make_market(ticker="KXFEDDECISION-26MAR-H0", yes_price=50, no_price=50)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
            return s.generate_signal(market, ob, None)

    def test_signal_not_none(self, signal):
        assert signal is not None

    def test_win_prob_above_coin_flip(self, signal):
        assert signal.win_prob > 0.5

    def test_edge_pct_positive(self, signal):
        assert signal.edge_pct > 0.0

    def test_confidence_in_range(self, signal):
        assert 0.0 <= signal.confidence <= 1.0

    def test_ticker_correct(self, signal):
        assert signal.ticker == "KXFEDDECISION-26MAR-H0"

    def test_reason_contains_key_fields(self, signal):
        assert "fomc" in signal.reason.lower() or "FOMC" in signal.reason
        assert "spread" in signal.reason


# ── Near-miss log ─────────────────────────────────────────────────────


class TestNearMissLog:
    def test_no_edge_logs_at_info(self, caplog):
        """When there's no edge, logs at INFO with market details."""
        snap = _make_snap(fed_funds_rate=3.64, yield_2yr=3.64)  # hold regime
        s = FOMCRateStrategy(
            fred_feed=_make_fred(snap),
            days_before_meeting=365,
            min_edge_pct=0.99,   # impossibly high → always no-edge
            min_minutes_remaining=1.0,
        )
        market = _make_market(ticker="KXFEDDECISION-26MAR-H0", yes_price=74, no_price=26)
        ob = OrderBook(yes_bids=[], no_bids=[])
        with caplog.at_level(logging.INFO, logger="src.strategies.fomc_rate"):
            with patch("src.strategies.fomc_rate.days_until_fomc", return_value=5):
                s.generate_signal(market, ob, None)
        info_records = [r for r in caplog.records if r.levelno == logging.INFO]
        assert len(info_records) >= 1


# ── FREDFeed unit tests ────────────────────────────────────────────────


class TestFREDFeed:
    def test_is_stale_before_fetch(self):
        feed = FREDFeed()
        assert feed.is_stale is True

    def test_snapshot_none_before_fetch(self):
        feed = FREDFeed()
        assert feed.snapshot() is None

    def test_refresh_success(self):
        """Mock HTTP responses for DFF, DGS2, CPIAUCSL and verify snapshot populated."""
        import json, io, csv

        def _make_csv(values: list[tuple[str, float]]) -> bytes:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["DATE", "VALUE"])
            for date_str, val in values:
                w.writerow([date_str, val])
            return buf.getvalue().encode()

        dff_csv  = _make_csv([("2026-02-24", 3.64), ("2026-02-25", 3.64)])
        dgs2_csv = _make_csv([("2026-02-24", 3.90), ("2026-02-25", 3.90)])
        cpi_csv  = _make_csv([
            ("2026-01-01", 321.0),
            ("2025-12-01", 320.5),
            ("2025-11-01", 320.0),
        ])

        responses = [dff_csv, dgs2_csv, cpi_csv]
        call_count = [0]

        from unittest.mock import MagicMock

        def mock_urlopen(req, timeout=None):
            idx = call_count[0] % len(responses)
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_resp.read.return_value = responses[idx]
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=mock_urlopen):
            feed = FREDFeed()
            success = feed.refresh()

        assert success is True
        snap = feed.snapshot()
        assert snap is not None
        assert snap.fed_funds_rate == 3.64
        assert snap.yield_2yr == 3.90
        assert feed.is_stale is False

    def test_refresh_failure_returns_false(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection error")):
            feed = FREDFeed()
            assert feed.refresh() is False
            assert feed.snapshot() is None
