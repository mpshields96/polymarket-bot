"""
Tests for SoccerSniperStrategy (KXUCLGAME in-play FLB sniper).

Covers:
1. Signal fires during live game at 88-93c (YES and NO sides)
2. No signal before game starts
3. No signal after game ends
4. No signal when price below trigger (88c)
5. No signal at or above ceiling (93c)
6. Hard skip near game end
7. Time gate: no signal before last 90 min
8. expected_expiration_time extraction from raw field
9. Fallback to close_time when expected_expiration_time missing
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.strategies.soccer_sniper import SoccerSniperStrategy, make_soccer_sniper, _get_expected_expiration
from src.platforms.kalshi import Market


def _make_market(
    yes_price: int = 55,
    no_price: int = 43,
    close_time: str = "2026-04-21T19:00:00Z",  # Safety buffer (weeks away)
    expected_expiration: str = "2026-04-07T22:00:00Z",  # Actual game end
    ticker: str = "KXUCLGAME-26APR07SPOARS-ARS",
) -> Market:
    """Create a test Market with KXUCLGAME structure."""
    return Market(
        ticker=ticker,
        title="Sporting CP vs Arsenal Winner?",
        event_ticker="KXUCLGAME-26APR07SPOARS",
        status="active",
        yes_price=yes_price,
        no_price=no_price,
        volume=468594,
        close_time=close_time,
        open_time="2026-03-23T17:22:00Z",
        result=None,
        raw={
            "expected_expiration_time": expected_expiration,
            "early_close_condition": "This market will close and expire after a winner is declared.",
        },
    )


def _make_strategy() -> SoccerSniperStrategy:
    return make_soccer_sniper()


# ─── _get_expected_expiration ───────────────────────────────────────────────

class TestGetExpectedExpiration:
    def test_extracts_from_raw_field(self):
        market = _make_market(expected_expiration="2026-04-07T22:00:00Z")
        exp = _get_expected_expiration(market)
        assert exp is not None
        assert exp.year == 2026
        assert exp.month == 4
        assert exp.day == 7
        assert exp.hour == 22
        assert exp.tzinfo == timezone.utc

    def test_falls_back_to_close_time_when_raw_missing(self):
        market = _make_market()
        market.raw = {}  # No expected_expiration_time
        exp = _get_expected_expiration(market)
        # Falls back to close_time = 2026-04-21T19:00:00Z
        assert exp is not None
        assert exp.month == 4
        assert exp.day == 21

    def test_returns_none_when_both_missing(self):
        market = _make_market(close_time="", expected_expiration="")
        market.raw = {}
        exp = _get_expected_expiration(market)
        assert exp is None


# ─── Signal generation ──────────────────────────────────────────────────────

class TestSoccerSniperSignal:
    """Core signal generation tests."""

    def test_fires_yes_when_in_range(self):
        """YES at 90c during live game → fire YES."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)

        # Simulate: now = 21:00 UTC (60 min before expected expiry at 22:00)
        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.side == "yes"
        assert signal.price_cents == 90
        assert signal.edge_pct > 0.005  # At least 0.5% FLB premium

    def test_fires_no_when_in_range(self):
        """NO at 91c during live game → fire NO."""
        strategy = _make_strategy()
        market = _make_market(yes_price=7, no_price=91)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.side == "no"
        assert signal.price_cents == 91

    def test_strategy_name_is_soccer_sniper_v1(self):
        strategy = _make_strategy()
        assert strategy.name == "soccer_sniper_v1"


class TestNegativeCases:
    """Cases where no signal should fire."""

    def test_no_signal_before_game_starts(self):
        """Game hasn't started yet (pre-game) → no signal even if price is high."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)

        # Now = 3 hours before expected_expiration = BEFORE game_start_est
        # game_start_est = 22:00 - 3 hours = 19:00. now = 18:00 → before game
        now = datetime(2026, 4, 7, 18, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_after_game_ends(self):
        """Game already ended (past expected_expiration) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)

        # now = after expected_expiration
        now = datetime(2026, 4, 7, 22, 30, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_price_below_trigger(self):
        """Price at 80c (below 88c trigger) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=80, no_price=18)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_at_ceiling(self):
        """YES at 93c (AT ceiling) → no signal (too close to fee floor)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=93, no_price=5)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_above_ceiling(self):
        """YES at 95c (above 93c ceiling) → no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=95, no_price=3)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_too_early_in_game(self):
        """Game started but still > 90 min remaining → no signal (too early in game)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)

        # now = 19:30 UTC, game ends at 22:00. Remaining = 150 min > 90 min gate
        now = datetime(2026, 4, 7, 19, 30, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_hard_skip_near_end(self):
        """< 60s remaining → hard skip, no signal."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)

        # 30 seconds before expected_expiration
        now = datetime(2026, 4, 7, 21, 59, 30, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is None

    def test_no_signal_when_expected_expiration_missing(self):
        """Raw field missing → falls back to close_time (weeks away) → no signal due to timing."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)
        market.raw = {}  # No expected_expiration_time, falls back to close_time

        # close_time is 2026-04-21 — weeks away, seconds_remaining >> 5400
        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        # With close_time weeks away → game_start_est also in future or past,
        # seconds_remaining >> 5400 → no signal
        assert signal is None


class TestBoundaryValues:
    """Edge cases and boundary values."""

    def test_fires_at_exactly_88c(self):
        """YES at exactly 88c (trigger threshold) → should fire."""
        strategy = _make_strategy()
        market = _make_market(yes_price=88, no_price=10)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.price_cents == 88

    def test_fires_at_92c(self):
        """YES at 92c (one below ceiling) → should fire."""
        strategy = _make_strategy()
        market = _make_market(yes_price=92, no_price=6)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert signal.price_cents == 92

    def test_exactly_at_max_seconds_remaining(self):
        """Exactly at 5400s remaining → should fire (boundary inclusive)."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)

        # Exactly 5400s before expected_expiration
        exp = datetime(2026, 4, 7, 22, 0, 0, tzinfo=timezone.utc)
        now = exp - timedelta(seconds=5400)  # = 20:30 UTC
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None

    def test_signal_contains_reason_with_timing(self):
        """Signal reason contains timing info for logs."""
        strategy = _make_strategy()
        market = _make_market(yes_price=90, no_price=8)

        now = datetime(2026, 4, 7, 21, 0, 0, tzinfo=timezone.utc)
        with patch("src.strategies.soccer_sniper.datetime") as mock_dt:
            mock_dt.now.return_value = now
            mock_dt.fromisoformat = datetime.fromisoformat
            mock_dt.utcfromtimestamp = datetime.utcfromtimestamp
            signal = strategy.generate_signal(market)

        assert signal is not None
        assert "soccer_sniper" in signal.reason
        assert signal.win_prob > 0.90
        assert signal.ticker == market.ticker

    def test_make_soccer_sniper_factory(self):
        """Factory function returns properly configured strategy."""
        s = make_soccer_sniper()
        assert isinstance(s, SoccerSniperStrategy)
        assert s.name == "soccer_sniper_v1"
        assert s._trigger_price_cents == 88.0
        assert s._max_price_cents == 93
