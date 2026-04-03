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
    make_eth_daily_sniper,
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


# ── Loop ceiling filter (tests the condition used in daily_sniper_loop) ────────
#
# The loop must enforce: max(yes_price, no_price) >= DAILY_SNIPER_MAX_PRICE_CENTS → skip.
#
# Slippage rationale: paper executor adds 1 tick slippage (fill = signal + 1).
# Signal at 94c → execution at 95c (above 94c ceiling). Must block at bid=94c.
# Signal at 93c → execution at 94c (at ceiling). Correct.
# So the check is >= (not >) to account for 1-tick slippage.
#
# Bug history: S131 introduced AND logic bug (yes > 94 AND no > 94) — never fired.
# S131 fix: max() logic (> ceiling). S132 fix: >= to account for slippage.


def _ceiling_filter(market: Market, ceiling: int = DAILY_SNIPER_MAX_PRICE_CENTS) -> bool:
    """Mirror of the ceiling check in daily_sniper_loop — returns True if market should be SKIPPED.

    Uses >= (not >) because paper slippage adds 1 tick:
    bid=94c → execution=95c (above ceiling). Must be blocked.
    bid=93c → execution=94c (at ceiling). Allowed.
    """
    return max(market.yes_price, market.no_price) >= ceiling


class TestDailySniperLoopCeilingFilter:
    """Tests for the ceiling filter logic used in daily_sniper_loop.

    The loop must skip markets where the favored side (90c+) is at or above 94c.
    Slippage bug fixed S132: >= instead of > to prevent 94c bid → 95c execution.
    """

    def test_yes_96c_is_skipped(self):
        """YES@96c market must be skipped — above 94c ceiling."""
        mkt = _make_daily_market(yes_price=96, no_price=4, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_97c_is_skipped(self):
        mkt = _make_daily_market(yes_price=97, no_price=3, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_98c_is_skipped(self):
        mkt = _make_daily_market(yes_price=98, no_price=2, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_99c_is_skipped(self):
        mkt = _make_daily_market(yes_price=99, no_price=1, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_no_96c_is_skipped(self):
        """NO@96c market must be skipped — above 94c ceiling."""
        mkt = _make_daily_market(yes_price=4, no_price=96, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_95c_is_skipped(self):
        """YES@95c bid skipped — would execute at 96c (slippage +1). Above ceiling."""
        mkt = _make_daily_market(yes_price=95, no_price=5, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_94c_is_skipped(self):
        """YES@94c bid skipped — would execute at 95c (slippage +1). Above ceiling."""
        mkt = _make_daily_market(yes_price=94, no_price=6, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_no_94c_is_skipped(self):
        """NO@94c bid skipped — would execute at 95c (slippage +1). Above ceiling."""
        mkt = _make_daily_market(yes_price=6, no_price=94, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True

    def test_yes_93c_is_allowed(self):
        """YES@93c bid allowed — executes at 94c (slippage +1). At ceiling. OK."""
        mkt = _make_daily_market(yes_price=93, no_price=7, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is False

    def test_yes_92c_is_allowed(self):
        """YES@92c is in clean zone — must be allowed."""
        mkt = _make_daily_market(yes_price=92, no_price=8, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is False

    def test_yes_90c_is_allowed(self):
        """YES@90c is at floor — must be allowed."""
        mkt = _make_daily_market(yes_price=90, no_price=10, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is False

    def test_neutral_50_50_is_allowed(self):
        """50/50 neutral market is allowed (strategy will return None anyway)."""
        mkt = _make_daily_market(yes_price=50, no_price=50, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is False

    def test_and_logic_bug_would_miss_yes_96c(self):
        """Document the AND bug: wrong logic passes YES@96c/NO@4c incorrectly."""
        mkt = _make_daily_market(yes_price=96, no_price=4, seconds_remaining=1800)
        # The old AND logic incorrectly passes this market
        old_broken_logic = (
            mkt.yes_price > DAILY_SNIPER_MAX_PRICE_CENTS
            and mkt.no_price > DAILY_SNIPER_MAX_PRICE_CENTS
        )
        assert old_broken_logic is False  # Bug: should be True (skip), not False (allow)
        # The new max() logic correctly skips it
        assert _ceiling_filter(mkt) is True  # Fixed: correctly skips


# ── Live path: function signature and constants ──────────────────────────────

import inspect


class TestDailySniperLiveSignature:
    """Verify daily_sniper_loop accepts live params (TDD — pre-implementation tests)."""

    def test_loop_accepts_live_executor_enabled(self):
        """daily_sniper_loop must accept live_executor_enabled param."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert "live_executor_enabled" in sig.parameters

    def test_loop_accepts_live_confirmed(self):
        """daily_sniper_loop must accept live_confirmed param."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert "live_confirmed" in sig.parameters

    def test_loop_accepts_trade_lock(self):
        """daily_sniper_loop must accept trade_lock param."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert "trade_lock" in sig.parameters

    def test_live_executor_defaults_to_false(self):
        """live_executor_enabled must default to False (safe default = paper)."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert sig.parameters["live_executor_enabled"].default is False

    def test_live_confirmed_defaults_to_false(self):
        """live_confirmed must default to False."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert sig.parameters["live_confirmed"].default is False

    def test_trade_lock_defaults_to_none(self):
        """trade_lock must default to None."""
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert sig.parameters["trade_lock"].default is None

    def test_live_cap_constant_is_ten_dollars(self):
        """_DAILY_SNIPER_LIVE_CAP_USD must be 10.0 USD (S156 ABSOLUTE FREEDOM — SPRT lambda=+5.317 at 38 bets, mandate 15-25 USD/day)."""
        import main as _main
        assert _main._DAILY_SNIPER_LIVE_CAP_USD == 10.0

    def test_is_paper_mode_both_false(self):
        """is_paper_mode = not (False and False) = True."""
        live_executor_enabled = False
        live_confirmed = False
        is_paper_mode = not (live_executor_enabled and live_confirmed)
        assert is_paper_mode is True

    def test_is_paper_mode_executor_only(self):
        """is_paper_mode = not (True and False) = True."""
        live_executor_enabled = True
        live_confirmed = False
        is_paper_mode = not (live_executor_enabled and live_confirmed)
        assert is_paper_mode is True

    def test_is_paper_mode_confirmed_only(self):
        """is_paper_mode = not (False and True) = True."""
        live_executor_enabled = False
        live_confirmed = True
        is_paper_mode = not (live_executor_enabled and live_confirmed)
        assert is_paper_mode is True

    def test_is_paper_mode_both_true(self):
        """is_paper_mode = not (True and True) = False → live mode."""
        live_executor_enabled = True
        live_confirmed = True
        is_paper_mode = not (live_executor_enabled and live_confirmed)
        assert is_paper_mode is False


# ── ETH daily sniper factory ──────────────────────────────────────────────────


class TestEthDailySniperFactory:
    def test_eth_strategy_name_is_eth_daily_sniper_v1(self):
        strat = make_eth_daily_sniper()
        assert strat.name == "eth_daily_sniper_v1"

    def test_eth_sniper_has_same_time_gate_as_btc(self):
        """ETH uses same 90-minute window as BTC daily sniper."""
        btc = make_daily_sniper()
        eth = make_eth_daily_sniper()
        assert eth._max_seconds_remaining == btc._max_seconds_remaining

    def test_eth_sniper_has_same_hard_skip_as_btc(self):
        """ETH uses same 30s hard skip as BTC daily sniper."""
        btc = make_daily_sniper()
        eth = make_eth_daily_sniper()
        assert eth._hard_skip_seconds == btc._hard_skip_seconds

    def test_eth_sniper_fires_on_kxethd_market(self):
        """ETH sniper generates signals on KXETHD-style markets."""
        from datetime import datetime, timedelta, timezone
        strat = make_eth_daily_sniper()
        now = datetime.now(timezone.utc)
        close_time = (now + timedelta(seconds=1800)).isoformat()
        from src.platforms.kalshi import Market
        market = Market(
            ticker="KXETHD-26MAR2817-T2050.00",
            title="Will ETH be above $2,050 at 5 PM UTC?",
            event_ticker="KXETHD",
            status="open",
            yes_price=8,
            no_price=92,  # NO at 92c = ETH expected below threshold
            volume=5000,
            close_time=close_time,
            open_time=(now - timedelta(hours=12)).isoformat(),
        )
        # Negative drift (ETH moved down) + NO@92c = consistent FLB signal
        signal = strat.generate_signal(market=market, coin_drift_pct=-0.01)
        assert signal is not None
        assert signal.side == "no"

    def test_eth_and_btc_snipers_have_different_names(self):
        btc = make_daily_sniper()
        eth = make_eth_daily_sniper()
        assert btc.name != eth.name


# ── max_price_cents parameter (CCA REQ-62 — ETH uses 92c ceiling, not 94c) ──────


class TestDailySniperMaxPriceCentsParam:
    """Verify daily_sniper_loop accepts max_price_cents param for per-series ceiling control.

    CCA REQ-62: ETH daily sniper uses 92c ceiling (not 94c).
    Default=None resolves to DAILY_SNIPER_MAX_PRICE_CENTS (94c) preserving BTC behavior.
    """

    def test_loop_accepts_max_price_cents_param(self):
        """daily_sniper_loop must accept max_price_cents param."""
        import inspect
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert "max_price_cents" in sig.parameters

    def test_max_price_cents_defaults_to_none(self):
        """max_price_cents must default to None (resolves to DAILY_SNIPER_MAX_PRICE_CENTS in loop)."""
        import inspect
        import main as _main
        sig = inspect.signature(_main.daily_sniper_loop)
        assert sig.parameters["max_price_cents"].default is None

    def test_ceiling_filter_respects_92c_override(self):
        """Ceiling filter helper must block YES@92c when ceiling=92 (ETH REQ-62 config)."""
        mkt = _make_daily_market(yes_price=92, no_price=8, seconds_remaining=1800)
        assert _ceiling_filter(mkt, ceiling=92) is True

    def test_ceiling_filter_allows_91c_with_92c_ceiling(self):
        """YES@91c must be allowed when ceiling=92 (one below ceiling)."""
        mkt = _make_daily_market(yes_price=91, no_price=9, seconds_remaining=1800)
        assert _ceiling_filter(mkt, ceiling=92) is False

    def test_ceiling_filter_btc_default_allows_93c(self):
        """Default 94c ceiling must still allow YES@93c (BTC behavior unchanged)."""
        mkt = _make_daily_market(yes_price=93, no_price=7, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is False  # default ceiling=94

    def test_ceiling_filter_btc_default_blocks_94c(self):
        """Default 94c ceiling must still block YES@94c (BTC behavior unchanged)."""
        mkt = _make_daily_market(yes_price=94, no_price=6, seconds_remaining=1800)
        assert _ceiling_filter(mkt) is True  # default ceiling=94
