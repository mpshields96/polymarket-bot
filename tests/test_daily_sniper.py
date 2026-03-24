"""
Tests for src/strategies/daily_sniper.py — KXBTCD near-expiry paper sniping.

Tests the make_daily_sniper() factory function and verify the resulting
ExpirySniperStrategy is correctly configured for 90-minute KXBTCD markets.

Key behaviors tested:
  - 90-minute time gate (5400s max, not 840s as in 15M sniper)
  - 30-second hard skip (CF Benchmarks settlement timing)
  - Direction consistency: YES@90c+ requires positive drift, NO@90c+ requires negative
  - Price floor at 90c (same as 15M sniper)
  - Strategy name is "daily_sniper_v1"
  - 94c ceiling is NOT enforced in the strategy (loop responsibility)

Note: KXBTCD ticker format (KXBTCD-26MAR0818-T66749.99) means coin extraction
produces "UNK" for the meta-labeling features field — this is expected and harmless.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.platforms.kalshi import Market
from src.strategies.daily_sniper import (
    DAILY_SNIPER_MAX_PRICE_CENTS,
    make_daily_sniper,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_daily_market(
    ticker: str = "KXBTCD-26MAR0500-T67000.00",
    yes_price: int = 92,
    no_price: int = 8,
    seconds_remaining: float = 1800.0,  # 30 min default
) -> Market:
    """Construct a KXBTCD market for testing."""
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(seconds=seconds_remaining)).isoformat()
    open_time = (now - timedelta(hours=12)).isoformat()
    return Market(
        ticker=ticker,
        title="Will BTC be above $67,000 at 5 AM UTC?",
        event_ticker="KXBTCD",
        status="open",
        yes_price=yes_price,
        no_price=no_price,
        volume=12000,
        close_time=close_time,
        open_time=open_time,
    )


# ── Strategy name ─────────────────────────────────────────────────────────────


class TestDailySniperName:
    def test_strategy_name_is_daily_sniper_v1(self):
        strat = make_daily_sniper()
        assert strat.name == "daily_sniper_v1"

    def test_max_price_cents_exported_constant(self):
        assert DAILY_SNIPER_MAX_PRICE_CENTS == 94


# ── Time gate ─────────────────────────────────────────────────────────────────


class TestDailySniperTimeGate:
    def test_signal_at_30min_remaining(self):
        """Should fire at 30 minutes remaining — well within 90-min window."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.side == "yes"

    def test_signal_at_exactly_90min_remaining(self):
        """Should fire at exactly 90 minutes (5400s) — the boundary."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=5400)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None

    def test_rejected_just_beyond_90min(self):
        """Should NOT fire at 91 minutes (5460s) — too early."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=5460)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is None

    def test_rejected_at_hard_skip(self):
        """Should NOT fire at 30 seconds remaining — CF Benchmarks hard skip."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=30)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is None

    def test_rejected_at_15s_remaining(self):
        """Confirm hard skip also covers well below 30s."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=15)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is None

    def test_signal_just_above_hard_skip(self):
        """Should fire at 31 seconds remaining (just above 30s hard skip)."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=31)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None


# ── Price gate ────────────────────────────────────────────────────────────────


class TestDailySniperPriceGate:
    def test_signal_at_90c_trigger(self):
        """Should fire at exactly 90c YES — the trigger price floor."""
        mkt = _make_daily_market(yes_price=90, no_price=10, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.side == "yes"

    def test_signal_at_94c(self):
        """Should fire at 94c — strategy itself has no ceiling (loop enforces 94c max)."""
        mkt = _make_daily_market(yes_price=94, no_price=6, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.side == "yes"

    def test_strategy_allows_95c_ceiling_enforced_in_loop(self):
        """Strategy allows 95c+ — ceiling enforcement is loop responsibility.

        This test documents the architecture: loop filters YES>94c or NO>94c
        before calling generate_signal(). The strategy itself has no ceiling.
        """
        mkt = _make_daily_market(yes_price=95, no_price=5, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        # Strategy allows it — loop would reject (not tested here, tested in loop tests)
        assert sig is not None

    def test_rejected_at_89c_below_floor(self):
        """Should NOT fire at 89c — below trigger floor of 90c."""
        mkt = _make_daily_market(yes_price=89, no_price=11, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is None

    def test_rejected_at_neutral_zone(self):
        """Should NOT fire when both sides are 50c (neutral)."""
        mkt = _make_daily_market(yes_price=50, no_price=50, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is None


# ── Direction consistency ─────────────────────────────────────────────────────


class TestDailySniperDirection:
    def test_yes_side_requires_positive_drift(self):
        """YES@90c+ is invalid if coin moved DOWN — inconsistent direction."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=-0.005)  # DOWN
        assert sig is None

    def test_yes_side_fires_with_positive_drift(self):
        """YES@92c fires when coin moved UP — consistent direction."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)  # UP
        assert sig is not None
        assert sig.side == "yes"

    def test_no_side_requires_negative_drift(self):
        """NO@90c+ is invalid if coin moved UP — inconsistent direction."""
        mkt = _make_daily_market(yes_price=8, no_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)  # UP
        assert sig is None

    def test_no_side_fires_with_negative_drift(self):
        """NO@92c fires when coin moved DOWN — consistent direction."""
        mkt = _make_daily_market(yes_price=8, no_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=-0.005)  # DOWN
        assert sig is not None
        assert sig.side == "no"

    def test_rejected_below_min_drift(self):
        """Should NOT fire if coin drift is too small (< 0.1% = 0.001)."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.0005)  # only 0.05%
        assert sig is None


# ── Signal properties ─────────────────────────────────────────────────────────


class TestDailySniperSignalProperties:
    def test_signal_ticker_matches_market(self):
        mkt = _make_daily_market(
            ticker="KXBTCD-26MAR0500-T67000.00",
            yes_price=92,
            seconds_remaining=1800,
        )
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.ticker == "KXBTCD-26MAR0500-T67000.00"

    def test_signal_price_matches_entry_price(self):
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.price_cents == 92

    def test_signal_edge_is_positive(self):
        """Edge must be positive for signal to fire."""
        mkt = _make_daily_market(yes_price=92, seconds_remaining=1800)
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.edge_pct > 0

    def test_kxbtcd_ticker_produces_unk_coin_in_features(self):
        """KXBTCD ticker doesn't contain '15M' so coin extraction gives 'UNK'.

        This is expected and harmless — meta-labeling features are informational only.
        """
        mkt = _make_daily_market(
            ticker="KXBTCD-26MAR0500-T67000.00",
            yes_price=92,
            seconds_remaining=1800,
        )
        strat = make_daily_sniper()
        sig = strat.generate_signal(mkt, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.features is not None
        assert sig.features.get("coin") == "UNK"
