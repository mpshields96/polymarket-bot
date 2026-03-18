"""
Tests for scripts/guard_retirement_check.py

Covers:
- break-even WR computation
- binomial p-value computation
- retirement gate logic
- guard registry completeness
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

PROJ = Path(__file__).parent.parent
sys.path.insert(0, str(PROJ))

# Import after path fix
from scripts.guard_retirement_check import (
    _break_even_wr,
    _binomial_pvalue,
    _is_retirement_candidate,
    GUARD_REGISTRY,
    MIN_BETS_FOR_RETIREMENT,
    RETIREMENT_MARGIN,
)


class TestBreakEvenWR:
    """Break-even WR formula accounting for Kalshi taker fee."""

    def test_90c_yes(self):
        # payout = 100 - 90 = 10c per contract. Fee = 7% of gross.
        # break_even = price / (payout * (1 - fee_rate) + price)
        # But we use the simpler per-price formula from live.py
        wr = _break_even_wr(90)
        # At 90c: win pays 10c, break-even ~91% accounting for fees
        assert 0.89 < wr < 0.93

    def test_95c_yes(self):
        wr = _break_even_wr(95)
        # At 95c: win pays 5c, break-even ~95% accounting for fees
        assert 0.94 < wr < 0.97

    def test_91c_no(self):
        # NO@91c means YES@9c equivalent from fee perspective
        # win pays 91c, cost 9c — break-even is low (~9/100 = 9%)
        # But NO@91c means we bet 91c for a 9c payout → very high break-even
        wr = _break_even_wr(91, side="no")
        assert 0.90 < wr < 0.94

    def test_higher_price_higher_breakeven(self):
        # At higher prices, more win-rate needed to break even
        wr_90 = _break_even_wr(90)
        wr_95 = _break_even_wr(95)
        assert wr_95 > wr_90

    def test_breakeven_under_100pct(self):
        for price in range(90, 100):
            wr = _break_even_wr(price)
            assert 0.0 < wr < 1.0, f"break-even WR for {price}c must be (0, 1)"


class TestBinomialPValue:
    """One-sided binomial test: H0 = bucket is bad (WR = historical WR)."""

    def test_0_of_0_bets(self):
        # No data — p-value is 1.0 (can't reject H0)
        p = _binomial_pvalue(n=0, wins=0, p_null=0.80)
        assert p == 1.0

    def test_50_of_50_wins(self):
        # 50/50 wins when H0 is 80% → very strong evidence against H0
        p = _binomial_pvalue(n=50, wins=50, p_null=0.80)
        assert p < 0.001

    def test_40_of_50_wins_null_80pct(self):
        # 80% WR exactly matching H0 → p should be close to 1
        p = _binomial_pvalue(n=50, wins=40, p_null=0.80)
        assert p > 0.5

    def test_48_of_50_wins_null_80pct(self):
        # 96% WR when H0 is 80% → strong evidence of recovery
        p = _binomial_pvalue(n=50, wins=48, p_null=0.80)
        assert p < 0.05

    def test_p_value_between_0_and_1(self):
        for wins in range(0, 21):
            p = _binomial_pvalue(n=20, wins=wins, p_null=0.90)
            assert 0.0 <= p <= 1.0


class TestRetirementCandidate:
    """Gate logic for flagging a bucket as retirement candidate."""

    def test_not_ready_below_min_bets(self):
        ready, msg = _is_retirement_candidate(
            n=20, wins=20, break_even_wr=0.91, historical_wr=0.80
        )
        assert not ready
        assert "20" in msg.lower() or "n=" in msg.lower() or "bets" in msg.lower()

    def test_not_ready_wr_too_low(self):
        # 50 bets but WR = 94% when threshold requires 95% + 2pp = 97%
        ready, msg = _is_retirement_candidate(
            n=50, wins=47, break_even_wr=0.95, historical_wr=0.80
        )
        assert not ready

    def test_ready_when_all_gates_met(self):
        # 50 bets, 100% WR, break-even 91%, threshold = 93%
        ready, msg = _is_retirement_candidate(
            n=50, wins=50, break_even_wr=0.91, historical_wr=0.80
        )
        assert ready
        assert "READY" in msg.upper()

    def test_minimum_bets_threshold(self):
        assert MIN_BETS_FOR_RETIREMENT >= 50

    def test_retirement_margin_positive(self):
        assert RETIREMENT_MARGIN > 0.0


class TestGuardRegistry:
    """Guard registry completeness checks."""

    def test_all_il_guards_present(self):
        guard_ids = {g["guard_id"] for g in GUARD_REGISTRY}
        # Core IL guards that should always be tracked
        for expected in [
            "IL-10A", "IL-10B", "IL-10C", "IL-19", "IL-20",
            "IL-21", "IL-22", "IL-23", "IL-24", "IL-25",
            "IL-26", "IL-27", "IL-28", "IL-30", "IL-31", "IL-32",
        ]:
            assert expected in guard_ids, f"{expected} missing from GUARD_REGISTRY"

    def test_each_guard_has_required_fields(self):
        required = {"guard_id", "ticker_contains", "side", "price_cents",
                    "historical_wr", "break_even_wr", "n_at_guard"}
        for g in GUARD_REGISTRY:
            missing = required - set(g.keys())
            assert not missing, f"{g['guard_id']} missing fields: {missing}"

    def test_historical_wr_below_break_even(self):
        """All guards were added because historical WR < break-even WR."""
        for g in GUARD_REGISTRY:
            assert g["historical_wr"] < g["break_even_wr"], (
                f"{g['guard_id']}: historical WR {g['historical_wr']:.1%} "
                f">= break-even {g['break_even_wr']:.1%} — guard shouldn't exist"
            )

    def test_price_cents_in_valid_range(self):
        for g in GUARD_REGISTRY:
            assert 80 <= g["price_cents"] <= 99, (
                f"{g['guard_id']}: price_cents={g['price_cents']} outside expected range"
            )

    def test_side_is_yes_or_no(self):
        for g in GUARD_REGISTRY:
            assert g["side"] in ("yes", "no"), (
                f"{g['guard_id']}: side={g['side']} must be 'yes' or 'no'"
            )
