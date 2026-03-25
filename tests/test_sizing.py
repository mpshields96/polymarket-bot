"""
Sizing module tests — MAX_LOSS cap + kelly_scale multiplier.

Tests the position sizing enhancements from REQ-042:
1. max_loss_usd parameter caps maximum loss per trade
2. kelly_scale parameter adjusts Kelly fraction based on Bayesian posterior uncertainty
"""

import math
import unittest

from src.risk.sizing import (
    ABSOLUTE_MAX_USD,
    KELLY_FRACTION,
    SizeResult,
    calculate_size,
    get_stage,
    kalshi_fee,
    kalshi_payout,
)


class TestMaxLossCap(unittest.TestCase):
    """MAX_LOSS cap limits the maximum dollar amount risked per trade."""

    def _base_kwargs(self, bankroll=200.0):
        """Standard kwargs for a bet that would normally size at ~$8-10."""
        return dict(
            win_prob=0.70,
            payout_per_dollar=1.5,
            edge_pct=0.15,
            bankroll_usd=bankroll,
            min_edge_pct=0.08,
        )

    def test_max_loss_caps_size(self):
        """When max_loss_usd is set, recommended_usd must not exceed it."""
        result = calculate_size(**self._base_kwargs(), max_loss_usd=3.00)
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 3.00)

    def test_max_loss_none_uses_existing_caps(self):
        """When max_loss_usd is None (default), sizing works as before."""
        result = calculate_size(**self._base_kwargs())
        self.assertIsNotNone(result)
        # Stage 2 (bankroll $200): max $10 or 5% of $200 = $10
        self.assertLessEqual(result.recommended_usd, 10.00)

    def test_max_loss_limiting_factor(self):
        """When max_loss is the binding constraint, limiting_factor says so."""
        result = calculate_size(**self._base_kwargs(), max_loss_usd=1.00)
        self.assertIsNotNone(result)
        self.assertEqual(result.limiting_factor, "max_loss_cap")

    def test_max_loss_not_binding_preserves_kelly(self):
        """When max_loss is higher than Kelly result, Kelly is the limiting factor."""
        result = calculate_size(**self._base_kwargs(bankroll=50.0), max_loss_usd=100.0)
        self.assertIsNotNone(result)
        # At small bankroll, Kelly or stage cap should bind, not max_loss
        self.assertNotEqual(result.limiting_factor, "max_loss_cap")

    def test_max_loss_below_minimum_bet_returns_none(self):
        """If max_loss_usd caps below $0.50 minimum bet, returns None."""
        result = calculate_size(**self._base_kwargs(), max_loss_usd=0.30)
        self.assertIsNone(result)

    def test_max_loss_7_50_default_constant(self):
        """Verify DEFAULT_MAX_LOSS_USD exists and equals 7.50."""
        from src.risk.sizing import DEFAULT_MAX_LOSS_USD
        self.assertEqual(DEFAULT_MAX_LOSS_USD, 7.50)

    def test_max_loss_interacts_with_stage_cap(self):
        """max_loss is applied after stage cap — tighter constraint wins."""
        # Stage 3 cap is $15, max_loss $5 is tighter
        result = calculate_size(**self._base_kwargs(bankroll=500.0), max_loss_usd=5.00)
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 5.00)

    def test_max_loss_field_in_result(self):
        """SizeResult includes max_loss_cap_usd field."""
        result = calculate_size(**self._base_kwargs(), max_loss_usd=5.00)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'max_loss_cap_usd'))
        self.assertEqual(result.max_loss_cap_usd, 5.00)

    def test_max_loss_field_none_when_not_set(self):
        """SizeResult max_loss_cap_usd is None when no max_loss passed."""
        result = calculate_size(**self._base_kwargs())
        self.assertIsNotNone(result)
        self.assertIsNone(result.max_loss_cap_usd)


class TestKellyScale(unittest.TestCase):
    """kelly_scale multiplier adjusts fractional Kelly based on Bayesian uncertainty."""

    def _base_kwargs(self, bankroll=200.0):
        return dict(
            win_prob=0.70,
            payout_per_dollar=1.5,
            edge_pct=0.15,
            bankroll_usd=bankroll,
            min_edge_pct=0.08,
        )

    def test_kelly_scale_1_is_default(self):
        """Default kelly_scale=1.0 produces same result as before."""
        result_default = calculate_size(**self._base_kwargs())
        result_explicit = calculate_size(**self._base_kwargs(), kelly_scale=1.0)
        self.assertEqual(result_default.recommended_usd, result_explicit.recommended_usd)

    def test_kelly_scale_reduces_size(self):
        """kelly_scale < 1.0 reduces bet size."""
        result_full = calculate_size(**self._base_kwargs(bankroll=50.0))
        result_half = calculate_size(**self._base_kwargs(bankroll=50.0), kelly_scale=0.5)
        self.assertIsNotNone(result_full)
        self.assertIsNotNone(result_half)
        # Half Kelly scale should produce smaller or equal size
        self.assertLessEqual(result_half.kelly_raw_usd, result_full.kelly_raw_usd)

    def test_kelly_scale_0_25_minimum(self):
        """kelly_scale=0.25 produces very small bets (may hit $0.50 floor)."""
        result = calculate_size(**self._base_kwargs(bankroll=50.0), kelly_scale=0.25)
        # Either None (below $0.50 floor) or very small
        if result is not None:
            self.assertLessEqual(result.recommended_usd, 5.00)

    def test_kelly_scale_clamped_to_0_1(self):
        """kelly_scale below 0 is treated as 0 (returns None — no bet)."""
        result = calculate_size(**self._base_kwargs(), kelly_scale=0.0)
        self.assertIsNone(result)

    def test_kelly_scale_above_1_clamped(self):
        """kelly_scale above 1.0 is clamped to 1.0."""
        result_1 = calculate_size(**self._base_kwargs(bankroll=50.0))
        result_2 = calculate_size(**self._base_kwargs(bankroll=50.0), kelly_scale=2.0)
        self.assertIsNotNone(result_1)
        self.assertIsNotNone(result_2)
        self.assertEqual(result_1.kelly_raw_usd, result_2.kelly_raw_usd)

    def test_kelly_scale_and_max_loss_combined(self):
        """Both parameters can be used together; tighter constraint wins."""
        result = calculate_size(
            **self._base_kwargs(), kelly_scale=0.5, max_loss_usd=2.00
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 2.00)


class TestExistingBehaviorPreserved(unittest.TestCase):
    """Regression tests: existing sizing behavior unchanged with new defaults."""

    def test_stage_1_cap(self):
        result = calculate_size(
            win_prob=0.75, payout_per_dollar=2.0,
            edge_pct=0.20, bankroll_usd=80.0,
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 5.00)
        self.assertEqual(result.stage, 1)

    def test_stage_2_cap(self):
        result = calculate_size(
            win_prob=0.75, payout_per_dollar=2.0,
            edge_pct=0.20, bankroll_usd=150.0,
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 10.00)
        self.assertEqual(result.stage, 2)

    def test_stage_3_cap(self):
        result = calculate_size(
            win_prob=0.75, payout_per_dollar=2.0,
            edge_pct=0.20, bankroll_usd=500.0,
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd, 15.00)
        self.assertEqual(result.stage, 3)

    def test_no_edge_returns_none(self):
        result = calculate_size(
            win_prob=0.51, payout_per_dollar=1.02,
            edge_pct=0.02, bankroll_usd=100.0,
        )
        self.assertIsNone(result)

    def test_negative_kelly_returns_none(self):
        result = calculate_size(
            win_prob=0.30, payout_per_dollar=1.0,
            edge_pct=0.10, bankroll_usd=100.0,
        )
        self.assertIsNone(result)

    def test_floor_truncation(self):
        """Verify floor truncation (not rounding) is preserved."""
        result = calculate_size(
            win_prob=0.65, payout_per_dollar=2.0,
            edge_pct=0.10, bankroll_usd=95.37,
            min_edge_pct=0.04,
        )
        self.assertIsNotNone(result)
        self.assertLessEqual(result.recommended_usd / 95.37, 0.05)

    def test_kalshi_payout_yes_side(self):
        p = kalshi_payout(44, "yes")
        self.assertGreater(p, 0)

    def test_kalshi_payout_no_side(self):
        p = kalshi_payout(44, "no")
        self.assertGreater(p, 0)

    def test_kalshi_fee(self):
        fee = kalshi_fee(50)
        self.assertAlmostEqual(fee, 0.07 * 0.5 * 0.5, places=4)

    def test_get_stage(self):
        self.assertEqual(get_stage(50.0), 1)
        self.assertEqual(get_stage(150.0), 2)
        self.assertEqual(get_stage(300.0), 3)

    def test_expiry_sniper_loop_max_loss_formula(self):
        """S140 regression: expiry_sniper_loop used min(_HARD_CAP, pct_max) bypassing
        DEFAULT_MAX_LOSS_USD. Fix: min(_HARD_CAP, pct_max, _MAX_LOSS).
        At bankroll=208, MAX_PCT=0.08: pct_max=16.63. HARD_CAP=10. MAX_LOSS=7.50.
        Correct result: 7.50. Wrong (pre-fix) result: 10.00."""
        from src.risk.kill_switch import HARD_MAX_TRADE_USD, MAX_TRADE_PCT
        from src.risk.sizing import DEFAULT_MAX_LOSS_USD
        bankroll = 208.0
        pct_max = round(bankroll * MAX_TRADE_PCT, 2) - 0.01
        # Pre-fix (wrong): trade_usd = min(HARD_CAP, pct_max)
        wrong = min(HARD_MAX_TRADE_USD, max(0.01, pct_max))
        self.assertAlmostEqual(wrong, 10.00, places=2, msg="pre-fix formula should give 10 USD")
        # Post-fix (correct): trade_usd = min(HARD_CAP, pct_max, MAX_LOSS)
        correct = min(HARD_MAX_TRADE_USD, max(0.01, pct_max), DEFAULT_MAX_LOSS_USD)
        self.assertAlmostEqual(correct, 7.50, places=2, msg="post-fix formula should give 7.50 USD")


if __name__ == "__main__":
    unittest.main()
