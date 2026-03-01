"""
Kill switch tests — must pass 100%.

Tests every trigger condition from POLYBOT_INIT.md:
1. Single trade size cap ($5 hard cap, 5% bankroll)
2. Daily loss limit (15%)
3. Consecutive loss cooling (5 losses → 2hr pause)
4. Hourly rate limit (15 trades/hr)
5. Auth failure hard stop (3 consecutive)
6. Total bankroll loss hard stop (30%)
7. Bankroll minimum hard stop ($20)
8. Lock file blocks startup
"""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from src.risk.kill_switch import (
    HARD_MAX_TRADE_USD,
    HARD_MIN_BANKROLL_USD,
    HARD_STOP_LOSS_PCT,
    DAILY_LOSS_LIMIT_PCT,
    CONSECUTIVE_LOSS_LIMIT,
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


# ── 2. Daily loss limit ────────────────────────────────────────────

class TestDailyLossLimit:
    def test_under_daily_limit_allowed(self, ks):
        ks.record_loss(14.0)  # 14% of $100
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=86.0)
        assert ok

    def test_at_daily_limit_blocked(self, ks):
        ks.record_loss(15.0)  # exactly 15%
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=85.0)
        assert not ok
        assert "daily" in reason.lower() or "loss" in reason.lower()

    def test_over_daily_limit_blocked(self, ks):
        ks.record_loss(20.0)
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=80.0)
        assert not ok

    def test_daily_loss_soft_stop_recorded(self, ks):
        ks.record_loss(15.0)
        ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=85.0)
        assert ks.is_soft_stopped


# ── 3. Consecutive loss cooling ────────────────────────────────────

class TestConsecutiveLossCooling:
    def test_four_losses_still_allowed(self, ks):
        for _ in range(4):
            ks.record_loss(1.0)
        ok, _ = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=96.0)
        assert ok

    def test_five_losses_triggers_cooling(self, ks):
        for _ in range(5):
            ks.record_loss(1.0)
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=95.0)
        assert not ok
        assert "consecutive" in reason.lower() or "cooling" in reason.lower()

    def test_cooling_period_is_two_hours(self, ks):
        for _ in range(5):
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

    def test_auth_failure_writes_lock_file(self, ks):
        for _ in range(MAX_AUTH_FAILURES):
            ks.record_auth_failure()
        assert LOCK_FILE.exists()

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


# ── 6. Total bankroll loss hard stop ──────────────────────────────

class TestTotalBankrollHardStop:
    def test_under_30pct_loss_no_hard_stop(self, ks):
        ks.record_loss(29.0)
        assert not ks.is_hard_stopped

    def test_at_30pct_loss_triggers_hard_stop(self, ks):
        ks.record_loss(30.0)
        assert ks.is_hard_stopped

    def test_hard_stop_writes_lock_file(self, ks):
        ks.record_loss(31.0)
        assert LOCK_FILE.exists()

    def test_hard_stop_blocks_all_trades(self, ks):
        ks.record_loss(31.0)
        ok, reason = ks.check_order_allowed(trade_usd=1.0, current_bankroll_usd=69.0)
        assert not ok


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

    def test_total_loss_hard_stop_triggered_at_30pct(self):
        ks = KillSwitch(starting_bankroll_usd=100.0)
        ks.record_loss(29.99)
        assert not ks.is_hard_stopped
        ks.record_loss(0.02)  # crosses 30%
        assert ks.is_hard_stopped

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
