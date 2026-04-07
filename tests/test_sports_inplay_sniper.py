"""
Tests for SportsInPlaySniperStrategy (KXNBAGAME/KXNHLGAME/KXMLBGAME in-play FLB sniper).

Covers:
1. Signal fires during live game at 90-92c (YES and NO sides)
2. No signal before game starts
3. No signal after game ends
4. No signal when price below trigger (90c)
5. No signal at or above ceiling (93c)
6. Hard skip near game end (<= 120s remaining)
7. Time gate: no signal before last 45 min
8. expected_expiration_time extraction from raw field
9. Fallback to close_time when expected_expiration_time missing
10. Per-sport game duration (NBA/NHL/MLB)
11. _series_from_ticker helper
12. make_sports_inplay_sniper factory
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from src.strategies.sports_inplay_sniper import (
    SportsInPlaySniperStrategy,
    make_sports_inplay_sniper,
    _get_expected_expiration,
    _series_from_ticker,
    _GAME_DURATION_NBA_SECS,
    _GAME_DURATION_NHL_SECS,
    _GAME_DURATION_MLB_SECS,
)
from src.platforms.kalshi import Market


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_market(
    yes_price: int = 55,
    no_price: int = 43,
    yes_bid: int | None = None,
    no_bid: int | None = None,
    close_time: str = "2026-05-10T04:00:00Z",   # Safety buffer weeks away
    expected_expiration: str = "2026-04-07T02:00:00Z",   # Actual game end
    ticker: str = "KXNBAGAME-26APR06BOSBKN-BOS",
    series: str = "KXNBAGAME",
) -> Market:
    """Create a test Market with KXNBAGAME structure."""
    raw: dict = {
        "expected_expiration_time": expected_expiration,
    }
    m = Market(
        ticker=ticker,
        title="Boston Celtics vs Brooklyn Nets Winner?",
        event_ticker=f"{series}-26APR06BOSBKN",
        status="active",
        yes_price=yes_price,
        no_price=no_price,
        volume=120000,
        close_time=close_time,
        open_time="2026-04-01T12:00:00Z",
        result=None,
        raw=raw,
    )
    if yes_bid is not None:
        m.yes_bid = yes_bid
    if no_bid is not None:
        m.no_bid = no_bid
    return m


def _make_strategy() -> SportsInPlaySniperStrategy:
    return SportsInPlaySniperStrategy()


# ── _series_from_ticker ──────────────────────────────────────────────────────

class TestSeriesFromTicker:
    def test_nba(self):
        assert _series_from_ticker("KXNBAGAME-26APR06BOSBKN-BOS") == "KXNBAGAME"

    def test_nhl(self):
        assert _series_from_ticker("KXNHLGAME-26APR07BOSCOL-BOS") == "KXNHLGAME"

    def test_mlb(self):
        assert _series_from_ticker("KXMLBGAME-26APR07MILBOS-MIL") == "KXMLBGAME"

    def test_no_hyphen(self):
        """Ticker with no hyphen returns whole string."""
        assert _series_from_ticker("KXNBAGAME") == "KXNBAGAME"


# ── _get_expected_expiration ─────────────────────────────────────────────────

class TestGetExpectedExpiration:
    def test_extracts_from_raw_field(self):
        market = _make_market(expected_expiration="2026-04-07T02:00:00Z")
        exp = _get_expected_expiration(market)
        assert exp is not None
        assert exp.year == 2026
        assert exp.month == 4
        assert exp.day == 7
        assert exp.hour == 2
        assert exp.tzinfo == timezone.utc

    def test_falls_back_to_close_time_when_raw_missing(self):
        market = _make_market()
        market.raw = {}
        exp = _get_expected_expiration(market)
        # Falls back to close_time = 2026-05-10T04:00:00Z
        assert exp is not None
        assert exp.month == 5
        assert exp.day == 10

    def test_returns_none_when_both_missing(self):
        market = _make_market(expected_expiration="")
        market.raw = {}
        market.close_time = ""
        exp = _get_expected_expiration(market)
        assert exp is None

    def test_handles_z_suffix(self):
        market = _make_market(expected_expiration="2026-04-07T02:00:00Z")
        exp = _get_expected_expiration(market)
        assert exp is not None
        assert exp.tzinfo == timezone.utc


# ── Signal generation ────────────────────────────────────────────────────────

class TestSportsInPlaySniperSignal:
    """Core signal generation tests — NBA series."""

    def test_fires_yes_when_in_range(self):
        """YES at 91c during final 45 min → fire YES."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        # expected_exp = 02:00 UTC. game_start_est = 02:00 - 2.5hr = 23:30 UTC prev day.
        # now = 01:20 UTC (40 min before end) — inside 45-min gate.
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.side == "yes"
        assert signal.price_cents == 91
        assert signal.edge_pct > 0.005

    def test_fires_no_when_in_range(self):
        """NO at 90c during final 45 min → fire NO."""
        strategy = _make_strategy()
        market = _make_market(yes_price=8, no_price=90)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.side == "no"
        assert signal.price_cents == 90

    def test_strategy_name_default(self):
        strategy = _make_strategy()
        assert strategy.name == "sports_inplay_sniper_v1"

    def test_strategy_name_override(self):
        strategy = SportsInPlaySniperStrategy(name_override="sports_inplay_sniper_nba_v1")
        assert strategy.name == "sports_inplay_sniper_nba_v1"

    def test_yes_bid_used_over_yes_price(self):
        """yes_bid takes priority over yes_price for price check."""
        strategy = _make_strategy()
        # yes_price=50 (below trigger), yes_bid=91 (above trigger)
        market = _make_market(yes_price=50, no_price=48, yes_bid=91, no_bid=7)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.price_cents == 91


# ── Negative cases ───────────────────────────────────────────────────────────

class TestNegativeCases:
    def test_no_signal_before_game_starts(self):
        """Pre-game (before game_start_est) → no signal even if price at trigger."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        # NBA duration = 2.5hr. game_start_est = 02:00 - 9000s = 23:30 UTC.
        # now = 22:00 UTC — before game_start_est.
        now = datetime(2026, 4, 6, 22, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_after_game_ends(self):
        """Game already ended (past expected_expiration) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        # now = after expected_expiration (02:00 UTC)
        now = datetime(2026, 4, 7, 2, 30, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_price_below_trigger(self):
        """Price at 85c (below 90c trigger) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=85, no_price=13)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_at_ceiling(self):
        """YES at exactly 93c (AT ceiling) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=93, no_price=5)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_above_ceiling(self):
        """YES at 96c (above ceiling) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=96, no_price=3)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_too_early_in_game(self):
        """Game started but >45 min remaining → no signal (outside gate)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        # expected_exp = 02:00 UTC. now = 00:00 UTC → 120 min remaining > 45 min gate
        now = datetime(2026, 4, 7, 0, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_hard_skip_at_120s_remaining(self):
        """Exactly 120s remaining → hard skip, no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)
        # 120 seconds before expected_expiration
        exp = datetime(2026, 4, 7, 2, 0, 0, tzinfo=timezone.utc)
        now = exp - timedelta(seconds=120)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_hard_skip_below_120s(self):
        """< 120s remaining → hard skip."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)
        exp = datetime(2026, 4, 7, 2, 0, 0, tzinfo=timezone.utc)
        now = exp - timedelta(seconds=60)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_when_expiration_missing(self):
        """Cannot parse any expiration → no signal (returns None)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        market.raw = {}
        market.close_time = "INVALID"
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None


# ── Boundary values ──────────────────────────────────────────────────────────

class TestBoundaryValues:
    def test_fires_at_exactly_90c(self):
        """YES at exactly 90c (trigger threshold) → should fire."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.price_cents == 90

    def test_fires_at_92c(self):
        """YES at 92c (one below ceiling) → should fire."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.price_cents == 92

    def test_exactly_at_max_seconds_remaining(self):
        """Exactly at 2700s remaining → should fire (boundary inclusive)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)
        exp = datetime(2026, 4, 7, 2, 0, 0, tzinfo=timezone.utc)
        now = exp - timedelta(seconds=2700)   # = 01:15 UTC
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None

    def test_just_past_max_seconds_remaining(self):
        """2701s remaining → too early, no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)
        exp = datetime(2026, 4, 7, 2, 0, 0, tzinfo=timezone.utc)
        now = exp - timedelta(seconds=2701)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_signal_reason_contains_inplay_sniper(self):
        """Signal reason contains 'inplay_sniper' for log identification."""
        strategy = _make_strategy()
        market = _make_market(yes_price=91, no_price=7)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert "inplay_sniper" in signal.reason
        assert signal.ticker == market.ticker
        assert signal.win_prob >= 0.90

    def test_no_side_at_89c_does_not_trigger(self):
        """NO at 89c (below 90c trigger) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=9, no_price=89)
        now = datetime(2026, 4, 7, 1, 20, 0, tzinfo=timezone.utc)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)

        assert signal is None


# ── Per-sport game duration ──────────────────────────────────────────────────

class TestPerSportDuration:
    """Verify each sport's game duration constant is used for pre-game detection."""

    def _test_sport(self, series: str, ticker: str, duration_secs: int):
        """
        Simulate: expected_exp at T. game_start_est = T - duration_secs.
        Now = T - duration_secs - 300 (5 min before game start) → should return None.
        Now = T - duration_secs + 300 (5 min after game start, BUT > 2700s from end)
        → also None (outside 45-min gate).
        Now = T - 1500 (25 min from end) → should fire if price triggers.
        """
        strategy = _make_strategy()
        expected_exp = datetime(2026, 4, 10, 3, 0, 0, tzinfo=timezone.utc)
        market = _make_market(
            yes_price=91,
            no_price=7,
            expected_expiration=expected_exp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            ticker=ticker,
        )

        # Pre-game (5 min before game_start_est) → no signal
        now_pregame = expected_exp - timedelta(seconds=duration_secs + 300)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now_pregame
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)
        assert signal is None, f"{series}: expected None (pre-game), got signal"

        # Late game (25 min from end) → should fire
        now_late = expected_exp - timedelta(seconds=1500)
        with patch("src.strategies.sports_inplay_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now_late
            mock_dt.fromisoformat = datetime.fromisoformat
            signal = strategy.generate_signal(market)
        assert signal is not None, f"{series}: expected signal (late game), got None"

    def test_nba_duration(self):
        self._test_sport("KXNBAGAME", "KXNBAGAME-26APR10BOSBKN-BOS", _GAME_DURATION_NBA_SECS)

    def test_nhl_duration(self):
        self._test_sport("KXNHLGAME", "KXNHLGAME-26APR10BOSCOL-BOS", _GAME_DURATION_NHL_SECS)

    def test_mlb_duration(self):
        self._test_sport("KXMLBGAME", "KXMLBGAME-26APR10MILBOS-MIL", _GAME_DURATION_MLB_SECS)


# ── make_sports_inplay_sniper factory ────────────────────────────────────────

class TestFactory:
    def test_nba_name(self):
        s = make_sports_inplay_sniper("KXNBAGAME")
        assert isinstance(s, SportsInPlaySniperStrategy)
        assert s.name == "sports_inplay_sniper_nba_v1"

    def test_nhl_name(self):
        s = make_sports_inplay_sniper("KXNHLGAME")
        assert s.name == "sports_inplay_sniper_nhl_v1"

    def test_mlb_name(self):
        s = make_sports_inplay_sniper("KXMLBGAME")
        assert s.name == "sports_inplay_sniper_mlb_v1"

    def test_unknown_series_name(self):
        s = make_sports_inplay_sniper("KXSOCCER")
        assert s.name == "sports_inplay_sniper_kxsoccer_v1"

    def test_params_match_defaults(self):
        s = make_sports_inplay_sniper("KXNBAGAME")
        assert s._trigger_price_cents == 90.0
        assert s._max_price_cents == 93
        assert s._max_seconds_remaining == 2700
        assert s._hard_skip_seconds == 120
