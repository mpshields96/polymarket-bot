"""
Tests for crypto_daily_threshold.py — N(d2) fair-value calculator for KXBTCD threshold bets.
Written TDD-first before implementation.
"""
import math
import pytest

from src.strategies.crypto_daily_threshold import (
    fair_prob_above_strike,
    edge_pct,
    _norm_cdf,
)


# ── _norm_cdf sanity checks ──────────────────────────────────────────────────

class TestNormCdf:
    def test_zero_is_half(self):
        assert abs(_norm_cdf(0.0) - 0.5) < 1e-9

    def test_positive_z_above_half(self):
        assert _norm_cdf(1.96) > 0.975

    def test_negative_z_below_half(self):
        assert _norm_cdf(-1.96) < 0.025

    def test_symmetry(self):
        assert abs(_norm_cdf(1.0) + _norm_cdf(-1.0) - 1.0) < 1e-9

    def test_large_positive_near_one(self):
        assert _norm_cdf(5.0) > 0.9999

    def test_large_negative_near_zero(self):
        assert _norm_cdf(-5.0) < 0.0001


# ── fair_prob_above_strike ───────────────────────────────────────────────────

class TestFairProbAboveStrike:
    def test_atm_prob_near_half(self):
        """Spot == strike → probability close to 0.5."""
        p = fair_prob_above_strike(spot=80000, strike=80000, hours_remaining=4.0, dvol=60.0)
        assert 0.48 < p < 0.52

    def test_itm_prob_above_half(self):
        """BTC 5% above strike → high probability."""
        p = fair_prob_above_strike(spot=84000, strike=80000, hours_remaining=6.0, dvol=60.0)
        assert p > 0.90

    def test_otm_prob_below_half(self):
        """BTC 5% below strike → low probability."""
        p = fair_prob_above_strike(spot=76000, strike=80000, hours_remaining=6.0, dvol=60.0)
        assert p < 0.10

    def test_monotonic_in_spot(self):
        """Higher spot → higher probability (all else equal)."""
        kwargs = dict(strike=80000, hours_remaining=4.0, dvol=60.0)
        p_low = fair_prob_above_strike(spot=77000, **kwargs)
        p_mid = fair_prob_above_strike(spot=80000, **kwargs)
        p_high = fair_prob_above_strike(spot=83000, **kwargs)
        assert p_low < p_mid < p_high

    def test_more_time_increases_uncertainty(self):
        """ATM: more hours → prob moves TOWARD 0.5 (more uncertainty, not less).
        Actually for ATM: more time → d2 becomes more negative (drift term dominates) → prob drops slightly.
        But the spread around ATM widens. Test: OTM becomes less certain over longer horizons."""
        # BTC 3% above strike: short horizon → high confidence; long horizon → less certain
        p_short = fair_prob_above_strike(spot=82400, strike=80000, hours_remaining=1.0, dvol=60.0)
        p_long = fair_prob_above_strike(spot=82400, strike=80000, hours_remaining=48.0, dvol=60.0)
        # Shorter horizon → BTC still 3% above, nearly certain → p_short > p_long
        assert p_short > p_long

    def test_zero_hours_returns_safe_default(self):
        """hours_remaining=0 → safe default (0.5), no division by zero."""
        p = fair_prob_above_strike(spot=80000, strike=80000, hours_remaining=0.0, dvol=60.0)
        assert p == 0.5

    def test_invalid_spot_returns_safe_default(self):
        p = fair_prob_above_strike(spot=0, strike=80000, hours_remaining=4.0, dvol=60.0)
        assert p == 0.5

    def test_invalid_strike_returns_safe_default(self):
        p = fair_prob_above_strike(spot=80000, strike=0, hours_remaining=4.0, dvol=60.0)
        assert p == 0.5

    def test_invalid_dvol_returns_safe_default(self):
        p = fair_prob_above_strike(spot=80000, strike=80000, hours_remaining=4.0, dvol=0.0)
        assert p == 0.5

    def test_known_value_itm(self):
        """Verify specific calculation against hand-computed d2.

        spot=84000, strike=80000, hours=6, dvol=60
        T = 6/8760 = 0.000685 years
        sigma = 0.60
        ln(84000/80000) = ln(1.05) ≈ 0.04879
        d2 = (0.04879 - 0.5*0.36*0.000685) / (0.60*sqrt(0.000685))
           = (0.04879 - 0.0001233) / (0.60*0.02617)
           = 0.04867 / 0.01570
           ≈ 3.10
        N(3.10) ≈ 0.9990
        """
        p = fair_prob_above_strike(spot=84000, strike=80000, hours_remaining=6.0, dvol=60.0)
        assert p > 0.997

    def test_known_value_otm(self):
        """Verify specific calculation for OTM case.

        spot=78000, strike=80000, hours=8, dvol=57
        T = 8/8760 = 0.000913 years
        sigma = 0.57
        ln(78000/80000) = ln(0.975) ≈ -0.02532
        d2 = (-0.02532 - 0.5*0.3249*0.000913) / (0.57*sqrt(0.000913))
           = (-0.02532 - 0.0001483) / (0.57*0.03022)
           = -0.02547 / 0.01723
           ≈ -1.478
        N(-1.478) ≈ 0.070
        """
        p = fair_prob_above_strike(spot=78000, strike=80000, hours_remaining=8.0, dvol=57.0)
        assert 0.04 < p < 0.12

    def test_weekly_horizon_high_uncertainty(self):
        """72-hour horizon: even 2% OTM shouldn't be highly confident."""
        p = fair_prob_above_strike(spot=78400, strike=80000, hours_remaining=72.0, dvol=60.0)
        assert 0.2 < p < 0.5

    def test_probability_in_unit_interval(self):
        """All results must be in [0, 1]."""
        test_cases = [
            (80000, 80000, 4.0, 60.0),
            (90000, 80000, 1.0, 40.0),
            (70000, 80000, 72.0, 80.0),
            (100000, 50000, 0.1, 100.0),
        ]
        for spot, strike, hours, dvol in test_cases:
            p = fair_prob_above_strike(spot, strike, hours, dvol)
            assert 0.0 <= p <= 1.0, f"Out of range for {spot},{strike},{hours},{dvol}: {p}"


# ── edge_pct ─────────────────────────────────────────────────────────────────

class TestEdgePct:
    def test_positive_edge_when_model_above_market(self):
        """Model says 65% probability, market prices YES at 50c → edge = +15%."""
        e = edge_pct(fair_prob=0.65, market_yes_price_cents=50)
        assert abs(e - 0.15) < 1e-9

    def test_negative_edge_when_model_below_market(self):
        """Model says 40%, market prices YES at 55c → edge = -15%."""
        e = edge_pct(fair_prob=0.40, market_yes_price_cents=55)
        assert abs(e - (-0.15)) < 1e-9

    def test_zero_edge_when_model_matches_market(self):
        e = edge_pct(fair_prob=0.50, market_yes_price_cents=50)
        assert abs(e) < 1e-9

    def test_large_positive_edge(self):
        """Model says 90%, market at 70c → 20% edge."""
        e = edge_pct(fair_prob=0.90, market_yes_price_cents=70)
        assert abs(e - 0.20) < 1e-9

    def test_edge_is_signed_float(self):
        e = edge_pct(fair_prob=0.60, market_yes_price_cents=50)
        assert isinstance(e, float)
        assert e > 0
