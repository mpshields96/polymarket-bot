"""
Tests for statistical rigor improvements to auto_guard_discovery.py.

Addresses trauma-guard problem: MIN_BETS=3 with no p-value test was activating
guards with insufficient statistical evidence. All 5 existing auto-guards had
p-values of 0.44-0.60 (random-chance territory).

Improvements tested here:
  - binomial_pvalue_below(): one-sided binomial test
  - MIN_BETS raised to 10
  - P_VALUE_THRESHOLD = 0.20 gates guard activation
  - meets_statistical_threshold() combines all criteria

Source: S112 trauma audit found all 5 guards non-significant (p=0.44-0.60).
Fix: add p-value gate so future guards require stronger evidence.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.auto_guard_discovery import (
    binomial_pvalue_below,
    meets_statistical_threshold,
    MIN_BETS,
    P_VALUE_THRESHOLD,
    break_even_wr,
)


# ── Constants ─────────────────────────────────────────────────────────────────

class TestConstants:
    def test_min_bets_at_least_10(self):
        """MIN_BETS must be >= 10 to prevent trauma guards on tiny samples."""
        assert MIN_BETS >= 10

    def test_p_value_threshold_is_permissive_but_not_trivial(self):
        """P_VALUE_THRESHOLD = 0.20 is permissive (early warning) but > pure noise."""
        assert 0.05 <= P_VALUE_THRESHOLD <= 0.25


# ── binomial_pvalue_below() ───────────────────────────────────────────────────

class TestBinomialPvalueBelow:
    def test_all_wins_high_pvalue(self):
        """100% WR when expected 93.4% → high p-value (WR is above, not below)."""
        # P(X <= 10 | n=10, p=0.934) = 1.0
        p = binomial_pvalue_below(k=10, n=10, p0=0.934)
        assert p > 0.90

    def test_severe_underperformance_low_pvalue(self):
        """70% WR when expected 93% across 30 bets → very low p-value."""
        # 21/30 wins when expected 28/30 — statistically significant
        p = binomial_pvalue_below(k=21, n=30, p0=0.934)
        assert p < 0.01

    def test_borderline_performance_mid_pvalue(self):
        """91.7% WR on n=24 when break-even is 93.4% → p ≈ 0.47 (not significant)."""
        p = binomial_pvalue_below(k=22, n=24, p0=0.934)
        assert 0.3 < p < 0.6  # should be near 0.476 from S112 audit

    def test_current_guard_pvalues_all_above_threshold(self):
        """
        S112 audit: all 5 existing auto-guards have p > 0.20.
        This confirms they would NOT have triggered under the new threshold.
        Tests serve as regression: verify new code doesn't introduce
        guardrails that are MORE permissive than the old raw-WR check.
        """
        # (n, k_wins, break_even) for each guard
        guards = [
            (19, 18, 0.953),  # KXXRP NO@95c
            (12, 11, 0.934),  # KXSOL NO@93c
            (13, 12, 0.944),  # KXBTC YES@94c
            (24, 22, 0.934),  # KXXRP NO@93c
            (10,  9, 0.944),  # KXBTC NO@94c
        ]
        for n, k, be in guards:
            p = binomial_pvalue_below(k=k, n=n, p0=be)
            assert p > P_VALUE_THRESHOLD, (
                f"Guard (n={n}, k={k}, be={be:.3f}) has p={p:.3f} < threshold {P_VALUE_THRESHOLD} — "
                "would have been blocked under new rules (unexpected, re-audit)"
            )

    def test_n0_returns_one(self):
        """Edge case: n=0 returns p=1.0 (no data, cannot reject null)."""
        assert binomial_pvalue_below(k=0, n=0, p0=0.93) == 1.0

    def test_symmetry_at_50pct(self):
        """At exactly break-even WR, p should be near 0.5."""
        # 15 wins / 30 bets at p0=0.5
        p = binomial_pvalue_below(k=15, n=30, p0=0.5)
        assert 0.4 < p < 0.7

    def test_clear_significant_result(self):
        """40 wins / 50 bets when break-even is 93.4% → p < 0.01 (significant)."""
        p = binomial_pvalue_below(k=40, n=50, p0=0.934)
        assert p < 0.01


# ── meets_statistical_threshold() ────────────────────────────────────────────

class TestMeetsStatisticalThreshold:
    def test_insufficient_n_fails(self):
        """Below MIN_BETS (n=5) should not qualify even with bad WR."""
        assert not meets_statistical_threshold(n=5, wins=3, break_even=0.934)

    def test_marginal_pvalue_fails(self):
        """n=24, WR=91.7%, p=0.476 — should NOT meet threshold."""
        assert not meets_statistical_threshold(n=24, wins=22, break_even=0.934)

    def test_strong_underperformance_passes(self):
        """n=40, 28 wins (70% WR) vs 93.4% break-even — should pass."""
        assert meets_statistical_threshold(n=40, wins=28, break_even=0.934)

    def test_above_break_even_fails(self):
        """WR above break-even should never qualify as a guard."""
        # 39/40 = 97.5% WR, break-even = 93.4%
        assert not meets_statistical_threshold(n=40, wins=39, break_even=0.934)

    def test_exact_min_bets_boundary(self):
        """At exactly MIN_BETS with bad WR: should respect threshold."""
        n = MIN_BETS
        # All losses — should fail on p-value test (WR=0 is extreme but n=MIN_BETS)
        # p-value of 0 wins / MIN_BETS when expected 93.4%
        p = binomial_pvalue_below(k=0, n=n, p0=0.934)
        result = meets_statistical_threshold(n=n, wins=0, break_even=0.934)
        if p < P_VALUE_THRESHOLD:
            assert result  # should pass if p qualifies
        else:
            assert not result  # should fail if p doesn't qualify

    def test_large_sample_moderate_underperformance_passes(self):
        """n=100, 88 wins (88% WR) vs 93.4% break-even — statistically significant."""
        assert meets_statistical_threshold(n=100, wins=88, break_even=0.934)
