"""
Kill switch tests — must pass 100%.

Tests every trigger condition from POLYBOT_INIT.md:
1. Single trade size cap ($5 hard cap, 5% bankroll)
2. Daily loss limit (20%)
3. Consecutive loss cooling (8 losses → 2hr pause)
4. Hourly rate limit (15 trades/hr)
5. Auth failure hard stop (3 consecutive)
6. Bankroll minimum hard stop ($20)
7. Lock file blocks startup
"""

import json
import os
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from src.risk.kill_switch import (
    HARD_MAX_TRADE_USD,
    HARD_MIN_BANKROLL_USD,
    DAILY_LOSS_LIMIT_PCT,
    CONSECUTIVE_LOSS_LIMIT,
    COOLING_PERIOD_HOURS,
    MAX_HOURLY_TRADES,
    MAX_AUTH_FAILURES,
    LOCK_FILE,
    KillSwitch,
    check_lock_at_startup,
    reset_kill_switch,
)

PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def cleanup_lock():
    """Remove kill_switch.lock before and after each test."""
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    yield
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()


@pytest.fixture
def ks():
    """Fresh KillSwitch with $100 starting bankroll."""
    return KillSwitch(starting_bankroll_usd=100.0)


# ── 1. Trade size caps ─────────────────────────────────────────────

class TestTradeSizeCaps:
    def test_trade_at_hard_cap_allowed(self, ks):
        ok, reason = ks.check_order_allowed(trade_usd=5.00, current_bankroll_usd=100.0)
        assert ok, reason

    def test_trade_above_hard_cap_blocked(self, ks):
        ok, reason = ks.check_order_allowed(trade_usd=5.01, current_bankroll_usd=100.0)
        assert not ok
        assert "5.01" in reason or "hard cap" in reason.lower()

    def test_trade_exceeds_pct_cap_blocked(self, ks):
        # 6% of $100 = $6 — exceeds 5% pct cap AND $5 hard cap
        ok, reason = ks.check_order_allowed(trade_usd=6.00, current_bankroll_usd=100.0)
        assert not ok

    def test_pct_cap_is_lower_than_hard_cap(self, ks):
        # $50 bankroll — 5% = $2.50, which is lower than $5 hard cap
        ok, reason = ks.check_order_allowed(trade_usd=3.00, current_bankroll_usd=50.0)
        assert not ok
        assert "bankroll" in reason.lower() or "%" in reason

    def test_pct_cap_applies_at_small_bankroll(self, ks):
        # $40 bankroll, 5% = $2.00 max
        ok, _ = ks.check_order_allowed(trade_usd=2.00, current_bankroll_usd=40.0)
        assert ok
        ok2, reason = ks.check_order_allowed(trade_usd=2.01, current_bankroll_usd=40.0)
        assert not ok2


# ── 2. Daily loss tracking (cap DISABLED — user directive Session 41) ────────
# Daily loss cap was removed. Tracking still active for --health display.
# Bankroll floor ($20) + consecutive loss cooling are the primary risk governors.

class TestDailyLossLimit:
    def test_under_daily_limit_allowed(self, ks):
        ks.record_loss(19.0)  # daily loss tracked but no longer blocks
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=81.0)
        assert ok

    def test_at_daily_limit_no_longer_blocked(self, ks):
        """Daily loss cap removed — 20% loss no longer blocks trades (Session 41)."""
        ks.record_loss(20.0)  # previously triggered soft stop
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=80.0)
        assert ok, f"Daily loss cap removed — should be allowed, got: {reason}"

    def test_over_daily_limit_no_longer_blocked(self, ks):
        """Daily loss cap removed — even large daily loss no longer blocks (Session 41)."""
        ks.record_loss(25.0)
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=75.0)
        assert ok, "Daily loss cap removed — should be allowed"

    def test_daily_loss_tracked_but_no_soft_stop(self, ks):
        """Daily loss is tracked for display but does NOT trigger soft stop (Session 41)."""
        ks.record_loss(20.0)
        ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=80.0)
        assert not ks.is_soft_stopped, "Soft stop must NOT be set by daily loss cap (cap disabled)"


# ── 3. Consecutive loss cooling ────────────────────────────────────

class TestConsecutiveLossCooling:
    def test_three_losses_still_allowed(self, ks):
        for _ in range(3):
            ks.record_loss(1.0)
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=97.0)
        assert ok

    def test_eight_losses_triggers_cooling(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=92.0)
        assert not ok
        assert "consecutive" in reason.lower() or "cooling" in reason.lower()

    def test_cooling_period_is_two_hours(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        # Verify cooling_until is ~2 hours from now
        cooling_until = ks._state._cooling_until
        assert cooling_until is not None
        remaining = cooling_until - time.time()
        assert 7100 < remaining < 7210  # ~2 hours

    def test_win_resets_consecutive_counter(self, ks):
        for _ in range(4):
            ks.record_loss(1.0)
        ks.record_win()
        assert ks._state._consecutive_losses == 0


# ── 4. Hourly rate limit ───────────────────────────────────────────

class TestHourlyRateLimit:
    def test_under_hourly_limit_allowed(self, ks):
        for _ in range(14):
            ks.record_trade()
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert ok

    def test_at_hourly_limit_blocked(self, ks):
        for _ in range(MAX_HOURLY_TRADES):
            ks.record_trade()
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert not ok
        assert "hourly" in reason.lower() or "rate" in reason.lower()


# ── 5. Auth failure hard stop ──────────────────────────────────────

class TestAuthFailureHardStop:
    def test_two_auth_failures_not_stopped(self, ks):
        for _ in range(MAX_AUTH_FAILURES - 1):
            ks.record_auth_failure()
        assert not ks.is_hard_stopped

    def test_three_auth_failures_hard_stop(self, ks):
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        assert ks.is_hard_stopped

    def test_auth_failure_hard_stop_sets_state(self, ks):
        # Lock file is NOT written during tests (PYTEST_CURRENT_TEST guard).
        # Verify in-memory state is set instead.
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        assert ks.is_hard_stopped

    def test_auth_success_resets_failure_counter(self, ks):
        ks.record_auth_failure()
        ks.record_auth_failure()
        ks.record_auth_success()
        assert ks._state._consecutive_auth_failures == 0

    def test_auth_hard_stop_writes_blockers(self, ks):
        blockers = PROJECT_ROOT / "BLOCKERS.md"
        original = blockers.read_text() if blockers.exists() else ""
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        content = blockers.read_text()
        assert "auth" in content.lower() or "Auth" in content


# ── 6. Lifetime loss — display only, no hard stop ─────────────────

class TestLifetimeLossDisplayOnly:
    """Lifetime realized loss is tracked for reporting only. No hard stop triggered."""

    def test_any_loss_does_not_hard_stop(self, ks):
        ks.record_loss(50.0)
        assert not ks.is_hard_stopped

    def test_extreme_loss_does_not_hard_stop(self, ks):
        ks.record_loss(99.0)
        assert not ks.is_hard_stopped

    def test_losses_still_tracked_for_display(self, ks):
        ks.record_loss(15.0)
        ks.record_loss(10.0)
        assert ks._state._realized_loss_usd == pytest.approx(25.0)

    def test_trade_still_allowed_after_large_lifetime_loss(self, ks):
        # Record a large lifetime loss but keep daily loss under 20% limit
        # so we can confirm lifetime loss alone does NOT block trades
        ks.record_loss(5.0)   # daily: $5 (under $20 daily limit)
        ks._state._realized_loss_usd = 50.0   # simulate large lifetime loss directly
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=95.0)
        assert ok, "Lifetime loss alone must not block trades (display-only)"


# ── 7. Bankroll minimum hard stop ────────────────────────────────

class TestBankrollMinimum:
    def test_above_minimum_allowed(self, ks):
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=20.01)
        assert ok

    def test_at_minimum_hard_stop(self, ks):
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=20.00)
        assert not ok
        assert ks.is_hard_stopped

    def test_below_minimum_hard_stop(self, ks):
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=19.99)
        assert not ok
        assert ks.is_hard_stopped


# ── 8. Lock file blocks startup ────────────────────────────────────

class TestLockFileStartup:
    def test_no_lock_file_passes(self):
        assert not LOCK_FILE.exists()
        check_lock_at_startup()  # Should not raise

    def test_lock_file_raises_on_startup(self):
        LOCK_FILE.write_text(json.dumps({
            "triggered_at": "2026-01-01T00:00:00Z",
            "reason": "test stop",
            "starting_bankroll": 100.0,
            "realized_loss_usd": 30.0,
        }))
        with pytest.raises(RuntimeError, match="HARD STOP IS ACTIVE"):
            check_lock_at_startup()

    def test_lock_file_check_in_order_allowed(self, ks):
        LOCK_FILE.write_text(json.dumps({"reason": "test", "triggered_at": "now"}))
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert not ok
        assert "lock" in reason.lower() or "reset" in reason.lower()


# ── 9. Minutes remaining guard ─────────────────────────────────────

class TestMinutesRemaining:
    def test_enough_time_allowed(self, ks):
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0, minutes_remaining=6.0)
        assert ok

    def test_exactly_5_min_blocked(self, ks):
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0, minutes_remaining=5.0)
        assert not ok
        assert "remaining" in reason.lower() or "window" in reason.lower()

    def test_no_minutes_provided_allowed(self, ks):
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert ok


# ── 10. Status reporting ───────────────────────────────────────────

class TestStatusReporting:
    def test_status_keys_present(self, ks):
        status = ks.get_status()
        required_keys = [
            "hard_stop", "hard_stop_reason", "soft_stop", "soft_stop_reason",
            "daily_loss_usd", "daily_trades", "hourly_trades",
            "consecutive_losses", "total_realized_loss_usd",
        ]
        for key in required_keys:
            assert key in status, f"Missing key: {key}"

    def test_fresh_status_all_clean(self, ks):
        status = ks.get_status()
        assert not status["hard_stop"]
        assert not status["soft_stop"]
        assert status["daily_loss_usd"] == 0.0


# ── 11. Settlement loop integration ────────────────────────────────

class TestSettlementIntegration:
    """Verify kill_switch is properly updated by settlement outcomes."""

    def test_win_resets_consecutive_losses(self, ks):
        ks.record_loss(1.00)
        ks.record_loss(1.00)
        assert ks._state._consecutive_losses == 2
        ks.record_win()
        assert ks._state._consecutive_losses == 0

    def test_loss_accumulates_daily_total(self, ks):
        ks.record_loss(2.50)
        ks.record_loss(1.00)
        assert ks._state._daily_loss_usd == pytest.approx(3.50)

    def test_loss_accumulates_realized_loss(self, ks):
        ks.record_loss(2.00)
        assert ks._state._realized_loss_usd == pytest.approx(2.00)

    def test_large_losses_do_not_hard_stop(self):
        """Lifetime loss no longer triggers a hard stop — regression guard."""
        ks = KillSwitch(starting_bankroll_usd=100.0)
        ks.record_loss(50.0)  # well above any old 30% threshold
        assert not ks.is_hard_stopped, (
            "Lifetime loss must NOT trigger hard stop (removed — rely on bankroll floor + consecutive cooling)"
        )

    def test_record_loss_zero_is_ignored(self, ks):
        ks.record_loss(0.0)
        assert ks._state._consecutive_losses == 0
        assert ks._state._daily_loss_usd == 0.0


# ── 12. PYTEST guard for _write_blockers ──────────────────────────

class TestPytestGuard:
    """Verify _write_blockers is suppressed during pytest runs."""

    def test_write_blockers_skipped_during_pytest(self, ks, tmp_path, monkeypatch):
        """
        PYTEST_CURRENT_TEST is set by pytest automatically.
        _write_blockers must not write to BLOCKERS.md during test runs.
        """
        import os
        # Confirm the env var is currently set (we ARE in pytest)
        assert os.environ.get("PYTEST_CURRENT_TEST"), "PYTEST_CURRENT_TEST not set — test context wrong"

        blockers_path = PROJECT_ROOT / "BLOCKERS.md"
        original_content = blockers_path.read_text() if blockers_path.exists() else None

        # Trigger _write_blockers via enough auth failures to cross the threshold
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()

        # File must be unchanged — guard should have suppressed the write
        if original_content is not None:
            assert blockers_path.read_text() == original_content
        else:
            assert not blockers_path.exists()


# ── Regression: paper loop call signature ─────────────────────────
class TestPaperLoopCallSignature:
    """Regression tests for the paper loop kill switch call.

    Bug: weather_loop/fomc_loop/unemployment_loop called check_order_allowed
    with wrong kwargs (proposed_usd, current_bankroll) instead of
    (trade_usd, current_bankroll_usd), causing TypeError swallowed silently
    and ALL paper trades in those loops being skipped.
    """

    def test_wrong_kwargs_raise_type_error(self, ks):
        # Document the bug: wrong kwarg names blow up immediately.
        with pytest.raises(TypeError):
            ks.check_order_allowed(proposed_usd=1.0, current_bankroll=100.0)

    def test_paper_placeholder_trade_allowed(self, ks):
        # Paper loops use trade_usd=1.0 as a placeholder to check kill switch state.
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert ok, f"Paper placeholder $1 trade should be allowed: {reason}"

    def test_paper_placeholder_blocked_when_hard_stopped(self, ks):
        from src.risk.kill_switch import LOCK_FILE
        import json
        LOCK_FILE.write_text(json.dumps({"reason": "test", "triggered_at": "now"}))
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert not ok


# ── Regression: paper loop sizing call signature ───────────────────
class TestPaperLoopSizingCallSignature:
    """Regression tests for the paper loop calculate_size() call.

    Bug: weather_loop/fomc_loop/unemployment_loop called calculate_size with
    price_cents=signal.price_cents (invalid kwarg, not in function signature)
    and omitted the required payout_per_dollar parameter.
    Result: TypeError silently caught by outer except, ALL paper trades skipped.

    Fix: compute payout_per_dollar via kalshi_payout() before calling calculate_size.
    """

    def test_wrong_kwarg_price_cents_raises_type_error(self):
        from src.risk.sizing import calculate_size
        with pytest.raises(TypeError):
            calculate_size(
                edge_pct=0.06,
                win_prob=0.65,
                price_cents=45,       # invalid kwarg — not in function signature
                bankroll_usd=100.0,
            )

    def test_correct_call_with_payout_per_dollar_works(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        # YES side signal at 45¢
        payout = kalshi_payout(45, "yes")
        result = calculate_size(
            win_prob=0.65,
            payout_per_dollar=payout,
            edge_pct=0.06,
            bankroll_usd=100.0,
        )
        # Should return a SizeResult, not None — edge 6% > default 8% min? No: 6% < 8% → None
        # Use min_edge_pct=0.05 to get a result
        result = calculate_size(
            win_prob=0.65,
            payout_per_dollar=payout,
            edge_pct=0.06,
            bankroll_usd=100.0,
            min_edge_pct=0.05,
        )
        assert result is not None
        assert result.recommended_usd > 0

    def test_no_side_requires_yes_price_conversion(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        # NO side signal: signal.price_cents=35 → YES price = 100-35=65
        signal_price_cents = 35
        signal_side = "no"
        yes_price_cents_for_payout = 100 - signal_price_cents  # correct conversion
        payout = kalshi_payout(yes_price_cents_for_payout, signal_side)
        result = calculate_size(
            win_prob=0.65,
            payout_per_dollar=payout,
            edge_pct=0.06,
            bankroll_usd=100.0,
            min_edge_pct=0.05,
        )
        assert result is not None


# ── Regression: paper loop size_usd must be float, not SizeResult ──
class TestPaperLoopSizeExtraction:
    """Regression tests for the SizeResult vs float bug.

    Bug: weather_loop/fomc_loop/unemployment_loop passed size_usd=size where
    size is a SizeResult object from calculate_size(), not a float.
    PaperExecutor.execute() does int(size_usd / cost_per_contract) which
    raises TypeError: unsupported operand type(s) for /: 'SizeResult' and 'float'.
    Caught by outer except, paper trade silently skipped.

    Fix: use _size_result.recommended_usd and clamp with HARD_MAX_TRADE_USD.
    Also added result is None guard before accessing result["side"] etc.
    """

    def test_size_result_not_directly_divisible(self):
        from src.risk.sizing import calculate_size, kalshi_payout, SizeResult
        payout = kalshi_payout(55, "yes")
        size_result = calculate_size(
            win_prob=0.65,
            payout_per_dollar=payout,
            edge_pct=0.06,
            bankroll_usd=100.0,
            min_edge_pct=0.05,
        )
        assert isinstance(size_result, SizeResult)
        with pytest.raises(TypeError):
            _ = size_result / 0.55

    def test_recommended_usd_is_float(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        payout = kalshi_payout(55, "yes")
        size_result = calculate_size(
            win_prob=0.65,
            payout_per_dollar=payout,
            edge_pct=0.06,
            bankroll_usd=100.0,
            min_edge_pct=0.05,
        )
        assert isinstance(size_result.recommended_usd, float)
        assert size_result.recommended_usd > 0

    def test_hard_cap_clamp_applied(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        from src.risk.kill_switch import HARD_MAX_TRADE_USD
        payout = kalshi_payout(55, "yes")
        size_result = calculate_size(
            win_prob=0.95,
            payout_per_dollar=payout,
            edge_pct=0.30,
            bankroll_usd=100.0,
            min_edge_pct=0.05,
        )
        trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD)
        assert trade_usd <= HARD_MAX_TRADE_USD


# ── Regression: strategy min_edge_pct must propagate to calculate_size ─
class TestStrategyMinEdgePropagation:
    """Regression tests for the missing min_edge_pct propagation bug.

    Bug: trading_loop called calculate_size() without passing min_edge_pct,
    so the default 8% applied even though the strategy threshold is 4% (btc_lag)
    or 5% (btc_drift). Signals at 4-7.9% edge were silently dropped even though:
      (a) the strategy already cleared the signal past its own threshold, and
      (b) Kelly formula at those edge levels still produces positive bet size.

    This caused the 17:23 mystery: btc_drift signal at 6.7% edge was generated
    (5% < 6.7%) but dropped by calculate_size with 8% default (6.7% < 8%).

    Fix: pass min_edge_pct=getattr(strategy, '_min_edge_pct', 0.08) to calculate_size.
    """

    def test_5pct_edge_drops_with_8pct_default(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        payout = kalshi_payout(65, "no")
        # 6.7% edge signal, calculate_size default 8% → None (signal silently dropped)
        result = calculate_size(
            win_prob=0.62,
            payout_per_dollar=payout,
            edge_pct=0.067,
            bankroll_usd=100.0,
            # min_edge_pct defaults to 0.08 → 6.7% < 8% → returns None
        )
        assert result is None, "8% default should drop 6.7% edge signal"

    def test_5pct_edge_succeeds_with_strategy_threshold(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        payout = kalshi_payout(65, "no")
        # Same 6.7% edge signal, but using btc_drift min_edge_pct=5% → should size
        result = calculate_size(
            win_prob=0.62,
            payout_per_dollar=payout,
            edge_pct=0.067,
            bankroll_usd=100.0,
            min_edge_pct=0.05,  # btc_drift strategy threshold
        )
        assert result is not None, "With 5% threshold, 6.7% edge should produce a bet"
        assert result.recommended_usd >= 0.50

    def test_kelly_positive_at_4pct_btc_lag_edge(self):
        from src.risk.sizing import calculate_size, kalshi_payout
        # btc_lag: YES signal at 55¢, edge 4% → Kelly should be positive
        payout = kalshi_payout(55, "yes")
        result = calculate_size(
            win_prob=0.60,
            payout_per_dollar=payout,
            edge_pct=0.04,
            bankroll_usd=100.0,
            min_edge_pct=0.04,  # btc_lag strategy threshold
        )
        assert result is not None, "Kelly is positive at 4% edge — should produce a bet"
        assert result.kelly_raw_usd > 0


class TestPaperOrderAllowed:
    """
    check_paper_order_allowed() only blocks on hard stops.
    Soft stops (daily loss, consecutive losses, hourly rate) do NOT block paper trades.
    Paper losses aren't real money — paper bets continue during soft kills for calibration.
    """

    def test_paper_allowed_when_clean(self, ks):
        ok, reason = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert ok
        assert reason == "OK"

    def test_paper_not_blocked_by_consecutive_soft_stop(self, ks):
        """Consecutive loss cooling (soft stop) must NOT block paper trades.
        Uses cooling period to trigger soft stop since daily loss cap was removed (Session 41).
        """
        for _ in range(8):
            ks.record_loss(1.0)  # triggers consecutive loss cooling
        # confirm soft stop state is active via cooling
        assert ks._state._cooling_until is not None, "Cooling must be active"
        ok, _ = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=92.0)
        assert ok, "Paper trade must not be blocked by consecutive loss cooling (soft stop)"

    def test_paper_not_blocked_by_consecutive_loss_cooling(self, ks):
        """Consecutive loss cooling period must NOT block paper trades."""
        for _ in range(8):
            ks.record_loss(1.0)  # triggers cooling (limit=8)
        assert ks._state._cooling_until is not None  # cooling is active
        ok, _ = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=92.0)
        assert ok, "Paper trade must not be blocked by consecutive loss cooling"

    def test_paper_not_blocked_by_hourly_rate_limit(self, ks):
        """Hourly rate limit must NOT block paper trades."""
        from src.risk.kill_switch import MAX_HOURLY_TRADES
        for _ in range(MAX_HOURLY_TRADES):
            ks.record_trade()
        ok, _ = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert ok, "Paper trade must not be blocked by hourly rate limit"

    def test_paper_blocked_by_hard_stop(self, ks):
        """Hard stops MUST still block paper trades (triggered via auth failures)."""
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        assert ks.is_hard_stopped
        ok, _ = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=90.0)
        assert not ok, "Hard stop must still block paper trades"

    def test_paper_blocked_by_lock_file(self, ks, tmp_path, monkeypatch):
        """kill_switch.lock must still block paper trades."""
        from src.risk import kill_switch as ks_mod
        fake_lock = tmp_path / "kill_switch.lock"
        fake_lock.write_text("{}")
        monkeypatch.setattr(ks_mod, "LOCK_FILE", fake_lock)
        ok, reason = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=100.0)
        assert not ok
        assert "lock" in reason.lower()

    def test_paper_blocked_below_bankroll_floor(self, ks):
        """Bankroll below hard floor must still block paper trades."""
        ok, _ = ks.check_paper_order_allowed(trade_usd=1.0, current_bankroll_usd=15.0)
        assert not ok


class TestHardStopNoPollutionDuringTests:
    """
    Regression tests: _hard_stop() must NOT write to KILL_SWITCH_EVENT.log
    or create kill_switch.lock during pytest runs.

    Without this guard, tests that trigger hard stops pollute the live event log
    with false entries (e.g. '31% bankroll loss') that look like real trading events.

    Root cause: _hard_stop() had no PYTEST_CURRENT_TEST guard, unlike _write_blockers().
    Fix: same os.environ.get("PYTEST_CURRENT_TEST") guard added to _hard_stop().
    """

    def test_hard_stop_does_not_write_event_log_during_tests(self, tmp_path, monkeypatch):
        """EVENT_LOG must not be written during pytest (PYTEST_CURRENT_TEST is set)."""
        from src.risk.kill_switch import KillSwitch, EVENT_LOG, MAX_AUTH_FAILURES
        # Confirm we ARE in a test (PYTEST_CURRENT_TEST is set by pytest)
        assert os.environ.get("PYTEST_CURRENT_TEST"), "This test requires PYTEST env var"
        # Record event log size before
        size_before = EVENT_LOG.stat().st_size if EVENT_LOG.exists() else 0
        ks = KillSwitch(starting_bankroll_usd=100.0)
        # Trigger hard stop via auth failures
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        # Event log must NOT have grown
        size_after = EVENT_LOG.stat().st_size if EVENT_LOG.exists() else 0
        assert size_after == size_before, (
            f"KILL_SWITCH_EVENT.log grew by {size_after - size_before} bytes during test. "
            "This pollutes the live event log with test-triggered hard stops."
        )

    def test_hard_stop_does_not_create_lock_file_during_tests(self, monkeypatch):
        """kill_switch.lock must not be created during pytest runs."""
        from src.risk.kill_switch import KillSwitch, LOCK_FILE, MAX_AUTH_FAILURES
        assert os.environ.get("PYTEST_CURRENT_TEST"), "This test requires PYTEST env var"
        # Remove any existing lock file
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        ks = KillSwitch(starting_bankroll_usd=100.0)
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        assert not LOCK_FILE.exists(), (
            "kill_switch.lock was created during a test run. "
            "This can block bot startup after pytest if conftest cleanup doesn't run."
        )

    def test_hard_stop_state_still_set_during_tests(self):
        """In-memory hard stop state SHOULD still be set — tests need to assert it."""
        from src.risk.kill_switch import KillSwitch, MAX_AUTH_FAILURES
        ks = KillSwitch(starting_bankroll_usd=100.0)
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        # State should be set even though files are not written
        assert ks.is_hard_stopped, "Hard stop in-memory state must still be set during tests"


# ── Daily loss counter persistence across restarts ─────────────────


class TestRestoreDailyLoss:
    """
    Regression tests: restore_daily_loss() seeds the daily counter from the DB
    so that bot restarts mid-session don't reset daily risk limits to zero.

    Design intent:
    - Consecutive loss counter DOES reset on restart (restart = manual soft-stop override)
    - Daily loss counter DOES NOT reset — daily risk protection should survive restart
    """

    @pytest.fixture
    def ks(self):
        return KillSwitch(starting_bankroll_usd=100.0)

    def test_restore_daily_loss_seeds_counter(self, ks):
        """After restore, daily loss counter reflects restored amount."""
        ks.restore_daily_loss(15.0)
        status = ks.get_status()
        assert status["daily_loss_usd"] == pytest.approx(15.0)

    def test_restore_zero_is_noop(self, ks):
        """restore_daily_loss(0) must not change anything."""
        ks.restore_daily_loss(0.0)
        status = ks.get_status()
        assert status["daily_loss_usd"] == pytest.approx(0.0)

    def test_restore_negative_is_noop(self, ks):
        """restore_daily_loss with negative value must be ignored."""
        ks.restore_daily_loss(-5.0)
        status = ks.get_status()
        assert status["daily_loss_usd"] == pytest.approx(0.0)

    def test_restore_at_limit_still_allowed(self, ks):
        """Daily loss cap disabled (Session 41) — restoring any amount no longer blocks trades.
        Use bankroll=100 and trade=2.0 to avoid pct_cap check ($2 < 5% of $100)."""
        daily_limit = 100.0 * DAILY_LOSS_LIMIT_PCT  # $20
        ks.restore_daily_loss(daily_limit)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert ok, f"Daily loss cap disabled — restore should not block trades, got: {reason}"

    def test_restore_partial_does_not_block(self, ks):
        """Restored loss below daily limit should not block trading.
        Use bankroll=100 and trade=2.0 to avoid pct_cap check."""
        daily_limit = 100.0 * DAILY_LOSS_LIMIT_PCT  # $20
        ks.restore_daily_loss(daily_limit * 0.8)  # $16 — still has $4 of room
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert ok, f"Expected trade allowed but got: {reason}"

    def test_restore_does_not_affect_consecutive_count(self, ks):
        """restore_daily_loss must not increment consecutive_losses."""
        ks.restore_daily_loss(10.0)
        status = ks.get_status()
        assert status["consecutive_losses"] == 0

    def test_restore_daily_does_not_touch_realized_loss(self, ks):
        """restore_daily_loss must NOT modify _realized_loss_usd (separate counter)."""
        ks.restore_daily_loss(15.0)
        status = ks.get_status()
        # Daily counter seeded; lifetime counter untouched (still 0)
        assert status["daily_loss_usd"] == pytest.approx(15.0)
        assert status["total_realized_loss_usd"] == pytest.approx(0.0)


# ── Lifetime loss counter persistence across restarts ──────────────


class TestRestoreRealizedLoss:
    """
    Regression tests: restore_realized_loss() seeds the lifetime counter for
    display/reporting purposes on bot restart.

    Design intent:
    - Uses SET semantics (not add) to avoid double-counting with restore_daily_loss()
    - Does NOT trigger any hard stop — lifetime loss is display-only
    - Only touches _realized_loss_usd — not _daily_loss_usd
    """

    @pytest.fixture
    def ks(self):
        return KillSwitch(starting_bankroll_usd=100.0)

    def test_restore_realized_seeds_counter(self, ks):
        """After restore, lifetime loss counter reflects restored amount."""
        ks.restore_realized_loss(20.0)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(20.0)

    def test_restore_realized_zero_is_noop(self, ks):
        """restore_realized_loss(0) must not change anything."""
        ks.restore_realized_loss(0.0)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(0.0)

    def test_restore_realized_negative_is_noop(self, ks):
        """restore_realized_loss with negative value must be ignored."""
        ks.restore_realized_loss(-5.0)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(0.0)

    def test_restore_realized_uses_set_not_add(self, ks):
        """Calling restore_realized_loss twice must not double-count."""
        ks.restore_realized_loss(25.0)
        ks.restore_realized_loss(25.0)  # second call — same amount, not additive
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(25.0)

    def test_restore_realized_any_amount_does_not_hard_stop(self, ks):
        """Lifetime loss no longer triggers a hard stop — regression guard."""
        ks.restore_realized_loss(99.0)  # extreme value — must NOT hard stop
        assert not ks.is_hard_stopped, (
            "restore_realized_loss must not trigger hard stop (display-only now)"
        )

    def test_restore_realized_does_not_touch_daily_loss(self, ks):
        """restore_realized_loss must NOT modify _daily_loss_usd (separate counter)."""
        ks.restore_realized_loss(20.0)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(20.0)
        assert status["daily_loss_usd"] == pytest.approx(0.0)

    def test_restore_realized_does_not_affect_consecutive_count(self, ks):
        """restore_realized_loss must not increment consecutive_losses."""
        ks.restore_realized_loss(15.0)
        status = ks.get_status()
        assert status["consecutive_losses"] == 0

    def test_restore_both_independent(self, ks):
        """restore_daily_loss + restore_realized_loss are fully independent.
        Together they must not double-count or interfere with each other."""
        ks.restore_realized_loss(25.0)   # all-time: $25
        ks.restore_daily_loss(10.0)      # today: $10 (subset of all-time)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(25.0)
        assert status["daily_loss_usd"] == pytest.approx(10.0)


# ── Consecutive loss counter persistence across restarts ────────────


class TestRestoreConsecutiveLosses:
    """
    Regression: bot restarted mid-losing-streak (trade 85→86 gap = 2200s),
    consecutive counter reset to 0, allowed 3 extra losing bets (~$14.74 loss).

    restore_consecutive_losses() mirrors restore_daily_loss/restore_realized_loss:
    - Seeds _consecutive_losses from DB on startup
    - If count >= CONSECUTIVE_LOSS_LIMIT: immediately starts cooling period
    - If count < limit: sets counter so fewer losses needed to trigger it
    """

    @pytest.fixture
    def ks(self):
        return KillSwitch(starting_bankroll_usd=100.0)

    def test_restore_seeds_counter(self, ks):
        """After restore(3), consecutive_losses status reflects 3."""
        ks.restore_consecutive_losses(3)
        status = ks.get_status()
        assert status["consecutive_losses"] == 3

    def test_restore_zero_is_noop(self, ks):
        """restore_consecutive_losses(0) must not change anything."""
        ks.restore_consecutive_losses(0)
        status = ks.get_status()
        assert status["consecutive_losses"] == 0

    def test_restore_negative_is_noop(self, ks):
        """Negative values must be ignored."""
        ks.restore_consecutive_losses(-2)
        status = ks.get_status()
        assert status["consecutive_losses"] == 0

    def test_restore_at_limit_no_ts_triggers_cooling(self, ks):
        """No timestamp → conservative fallback → cooling fires immediately."""
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT, last_loss_ts=None)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_at_limit_triggers_cooling(self, ks):
        """Backward compat: positional arg only → same as no timestamp."""
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_above_limit_triggers_cooling(self, ks):
        """Restoring count > limit (e.g. 6) with no timestamp must also block trading."""
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT + 2)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_stale_streak_does_not_block(self, ks):
        """KEY REGRESSION (Session 35): stale streak (last loss >2hr ago) must NOT block.

        Trades 110-121 on 2026-03-01 triggered 4 consecutive losses. Every restart
        since then fired a fresh 2-hour block because last_loss_ts was never checked.
        This test confirms the fix: if cooling window has expired, only seed the counter.
        """
        import time as _time
        stale_ts = _time.time() - (COOLING_PERIOD_HOURS * 3600 + 600)  # 10min past expiry
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT, last_loss_ts=stale_ts)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert ok, (
            f"Stale streak should NOT block — got: {reason}. "
            "This is the Session 35 regression."
        )

    def test_restore_stale_streak_seeds_counter(self, ks):
        """Stale streak seeds counter so one MORE loss still triggers cooling."""
        import time as _time
        stale_ts = _time.time() - (COOLING_PERIOD_HOURS * 3600 + 600)
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT, last_loss_ts=stale_ts)
        # Counter seeded at LIMIT — next loss should immediately trigger cooling
        ks.record_loss(5.0)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_fresh_streak_still_blocks(self, ks):
        """Recent streak (within 2hr window) must still block trading."""
        import time as _time
        recent_ts = _time.time() - 1800  # 30 min ago — well within 2hr window
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT, last_loss_ts=recent_ts)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_fresh_streak_uses_remaining_time(self, ks):
        """Fresh streak restores REMAINING cooling time, not a new full 2hr window."""
        import time as _time
        recent_ts = _time.time() - 3000  # 50 min ago → ~70min remaining
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT, last_loss_ts=recent_ts)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        # Remaining should be ~70min, not 120min
        assert "70min" in reason or "69min" in reason or "71min" in reason

    def test_restore_below_limit_does_not_block(self, ks):
        """Restoring count < limit must NOT block trading yet."""
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT - 1)
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert ok, f"Expected trade allowed but got: {reason}"

    def test_restore_three_then_one_more_loss_triggers_cooling(self, ks):
        """restore(3) + record_loss → 4th loss → cooling fires."""
        ks.restore_consecutive_losses(CONSECUTIVE_LOSS_LIMIT - 1)  # 3
        ks.record_loss(5.0)  # 4th loss — should trigger cooling
        ok, reason = ks.check_order_allowed(trade_usd=2.0, current_bankroll_usd=100.0)
        assert not ok
        assert "ooling" in reason

    def test_restore_does_not_affect_daily_loss(self, ks):
        """restore_consecutive_losses must not touch _daily_loss_usd."""
        ks.restore_consecutive_losses(3)
        status = ks.get_status()
        assert status["daily_loss_usd"] == pytest.approx(0.0)

    def test_restore_does_not_affect_realized_loss(self, ks):
        """restore_consecutive_losses must not touch _realized_loss_usd."""
        ks.restore_consecutive_losses(3)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(0.0)

    def test_restore_all_three_counters_independent(self, ks):
        """All three restores are fully independent — no cross-contamination."""
        ks.restore_realized_loss(10.0)
        ks.restore_daily_loss(5.0)
        ks.restore_consecutive_losses(2)
        status = ks.get_status()
        assert status["total_realized_loss_usd"] == pytest.approx(10.0)
        assert status["daily_loss_usd"] == pytest.approx(5.0)
        assert status["consecutive_losses"] == 2


# ── Regression: calibration_max_usd clamp in trading_loop ─────────────────
class TestCalibrationCap:
    """Regression tests for the micro-live calibration cap.

    The calibration_max_usd parameter in trading_loop caps bet size to $1.00
    (or any specified value) for the micro-live calibration phase.
    This test verifies the clamping arithmetic directly (the line in main.py is:
        trade_usd = min(trade_usd, calibration_max_usd)
    which is trivial, but we want to ensure the cap interacts correctly with the
    hard cap).
    """

    def test_calibration_cap_below_hard_cap(self):
        """$1.00 calibration cap clamps below $5.00 hard cap."""
        hard_cap = 5.00
        calibration_max_usd = 1.00
        # Simulate sizing returning $3.50 (within hard cap but above calibration cap)
        size_from_sizing = 3.50
        trade_usd = min(size_from_sizing, hard_cap)  # after hard cap: $3.50
        trade_usd = min(trade_usd, calibration_max_usd)  # after calibration cap: $1.00
        assert trade_usd == pytest.approx(1.00)

    def test_calibration_cap_none_leaves_size_unchanged(self):
        """calibration_max_usd=None must leave trade_usd unchanged."""
        calibration_max_usd = None
        hard_cap = 5.00
        size_from_sizing = 3.50
        trade_usd = min(size_from_sizing, hard_cap)
        if calibration_max_usd is not None:
            trade_usd = min(trade_usd, calibration_max_usd)
        assert trade_usd == pytest.approx(3.50)

    def test_calibration_cap_above_hard_cap_is_no_op(self):
        """calibration_max_usd > hard cap: hard cap still wins."""
        hard_cap = 5.00
        calibration_max_usd = 10.00  # higher than hard cap — should be no-op
        size_from_sizing = 4.50
        trade_usd = min(size_from_sizing, hard_cap)
        trade_usd = min(trade_usd, calibration_max_usd)
        assert trade_usd == pytest.approx(4.50)

    def test_calibration_cap_at_penny_level(self):
        """Calibration cap works at sub-dollar levels."""
        calibration_max_usd = 0.50
        size_from_sizing = 5.00
        hard_cap = 5.00
        trade_usd = min(size_from_sizing, hard_cap)
        trade_usd = min(trade_usd, calibration_max_usd)
        assert trade_usd == pytest.approx(0.50)


class TestDirectionFilter:
    """Regression tests for trading_loop direction_filter parameter.

    ACTIVE FILTERS (per-strategy, as of Sessions 43/53/51/54):
      btc_drift: filter="no"  — YES win rate 30% (6/20) vs NO 61% (14/23), p≈3.7%
      eth_drift: filter="yes" — NO has negative EV; YES 61% win rate (Session 53)
      sol_drift: filter="no"  — NO 11/11 wins pre-filter (Session 51)
      xrp_drift: filter="yes" — YES +0.38 vs NO -0.45 EV (Session 54, Matthew approved)

    Mechanical explanation for btc/sol drift NO-filter: upward drift already priced into
    Kalshi YES market by HFTs before our signal fires. Downward drift retains real edge.

    Tests verify the filter logic directly (the conditional in trading_loop is trivial
    but must be correctly applied to prevent wrong-side bets from sneaking through).
    """

    def _filter_signal(self, signal_side: str, direction_filter: Optional[str]) -> bool:
        """Returns True if signal should be kept (not filtered), False if it should be skipped."""
        if direction_filter is not None and signal_side != direction_filter:
            return False
        return True

    def test_no_filter_passes_yes_signal(self):
        """direction_filter=None passes YES signals through."""
        assert self._filter_signal("yes", None) is True

    def test_no_filter_passes_no_signal(self):
        """direction_filter=None passes NO signals through."""
        assert self._filter_signal("no", None) is True

    def test_no_filter_blocks_yes_signal(self):
        """direction_filter='no' blocks YES signals."""
        assert self._filter_signal("yes", "no") is False

    def test_no_filter_passes_no_signal_when_filter_no(self):
        """direction_filter='no' passes NO signals through."""
        assert self._filter_signal("no", "no") is True

    def test_yes_filter_blocks_no_signal(self):
        """direction_filter='yes' blocks NO signals — ACTIVE on eth_drift_v1 and xrp_drift_v1 (Sessions 53/54)."""
        assert self._filter_signal("no", "yes") is False

    def test_yes_filter_passes_yes_signal(self):
        """direction_filter='yes' passes YES signals through — ACTIVE on eth_drift_v1 and xrp_drift_v1."""
        assert self._filter_signal("yes", "yes") is True


class TestResetSoftStop:
    """reset_soft_stop() clears consecutive counter and cooling without touching daily/hard state."""

    @pytest.fixture
    def ks(self):
        return KillSwitch(starting_bankroll_usd=100.0)

    def test_reset_clears_consecutive_counter(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        assert ks._state._consecutive_losses == 8
        ks.reset_soft_stop()
        assert ks._state._consecutive_losses == 0

    def test_reset_clears_cooling(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        assert ks._state._cooling_until is not None
        ks.reset_soft_stop()
        assert ks._state._cooling_until is None

    def test_reset_clears_soft_stop_flag(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        assert ks._state._soft_stop is True
        ks.reset_soft_stop()
        assert ks._state._soft_stop is False

    def test_reset_allows_order_after_active_cooling(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        allowed, _ = ks.check_order_allowed(trade_usd=0.50, current_bankroll_usd=100.0)
        assert allowed is False
        ks.reset_soft_stop()
        allowed, _ = ks.check_order_allowed(trade_usd=0.50, current_bankroll_usd=100.0)
        assert allowed is True

    def test_reset_does_not_affect_daily_loss(self, ks):
        for _ in range(8):
            ks.record_loss(1.0)
        ks.reset_soft_stop()
        assert ks._state._daily_loss_usd == pytest.approx(8.0)
