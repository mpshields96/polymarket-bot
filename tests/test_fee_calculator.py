"""
Tests for src/risk/fee_calculator.py

Reference: KALSHI_BOT_COMPLETE_REFERENCE.pdf Section 3.3
Formula: fee = ceil(0.07 * contracts * price * (1-price) * 100) cents
"""

import math
import pytest

from src.risk.fee_calculator import (
    kalshi_taker_fee_cents,
    fee_as_probability_points,
    edge_survives_fee,
)


class TestKalshiTakerFeeCents:
    """Verify the fee formula matches the reference doc exactly."""

    def test_50_cent_market_1_contract(self):
        """Reference: 'At price=0.50: fee = ceil(0.0175) = 2 cents per contract'"""
        # ceil(0.07 * 1 * 0.50 * 0.50 * 100) = ceil(1.75) = 2
        assert kalshi_taker_fee_cents(1, 50) == 2

    def test_85_cent_market_1_contract(self):
        """Reference: 'At price=0.85: fee = ceil(0.0089) = 1 cent per contract'"""
        # ceil(0.07 * 1 * 0.85 * 0.15 * 100) = ceil(0.8925) = 1
        assert kalshi_taker_fee_cents(1, 85) == 1

    def test_10_cent_market_1_contract(self):
        """Reference: 'At price=0.10: fee = ceil(0.0063) = 1 cent per contract'"""
        # ceil(0.07 * 1 * 0.10 * 0.90 * 100) = ceil(0.63) = 1
        assert kalshi_taker_fee_cents(1, 10) == 1

    def test_fee_is_symmetric(self):
        """Buying YES@35¢ costs same fee as buying YES@65¢ (same probability distance from 50¢)."""
        assert kalshi_taker_fee_cents(1, 35) == kalshi_taker_fee_cents(1, 65)

    def test_fee_scales_with_contracts(self):
        """Fee scales linearly with contract count."""
        fee_1 = kalshi_taker_fee_cents(1, 50)
        fee_7 = kalshi_taker_fee_cents(7, 50)
        # 7x contracts = 7x fee before ceiling effects
        # ceil(0.07 * 7 * 0.5 * 0.5 * 100) = ceil(12.25) = 13
        assert fee_7 == 13  # not exactly 7*2=14 due to ceiling on total not per-contract

    def test_fee_maximum_at_50_cents(self):
        """Fee is maximum at 50¢ (worst case for Kalshi, highest variance market)."""
        fee_50 = kalshi_taker_fee_cents(1, 50)
        for price in [10, 20, 30, 35, 40, 45, 55, 60, 65, 70, 80, 90]:
            assert kalshi_taker_fee_cents(1, price) <= fee_50

    def test_minimum_fee_enforced(self):
        """Fee is never 0 even for edge-of-range prices."""
        # At price=1 cent: ceil(0.07 * 1 * 0.01 * 0.99 * 100) = ceil(0.069) = 1
        assert kalshi_taker_fee_cents(1, 1) >= 1
        assert kalshi_taker_fee_cents(1, 99) >= 1

    def test_invalid_contracts(self):
        with pytest.raises(ValueError, match="contracts must be"):
            kalshi_taker_fee_cents(0, 50)

    def test_invalid_price_zero(self):
        with pytest.raises(ValueError, match="price_cents"):
            kalshi_taker_fee_cents(1, 0)

    def test_invalid_price_100(self):
        with pytest.raises(ValueError, match="price_cents"):
            kalshi_taker_fee_cents(1, 100)

    def test_btc_drift_typical_trade(self):
        """Typical btc_drift trade: 7 contracts at 48¢. Based on trade id=64 in live DB."""
        # ceil(0.07 * 7 * 0.48 * 0.52 * 100) = ceil(12.23) = 13
        fee = kalshi_taker_fee_cents(7, 48)
        assert fee == 13

    def test_large_contract_count_at_stage_1_cap(self):
        """At Stage 1 $5 cap and 35¢ price: 14 contracts. Fee should be < edge."""
        # ceil(0.07 * 14 * 0.35 * 0.65 * 100) = ceil(22.26) = 23
        fee = kalshi_taker_fee_cents(14, 35)
        assert fee == 23
        # 23 cents on a $4.90 stake = 0.47% fee — survivable vs 5% edge


class TestFeeAsProbabilityPoints:
    """Verify fee expressed in same units as edge_pct."""

    def test_fee_as_probability_at_50_cents_14_contracts(self):
        """14 contracts at 50¢: fee=25¢. Payout=1400¢. fee_prob=25/1400≈0.018."""
        fee_pp = fee_as_probability_points(14, 50, 1400)
        # ceil(0.07*14*0.5*0.5*100) = ceil(24.5) = 25
        expected = 25 / 1400
        assert abs(fee_pp - expected) < 0.001

    def test_fee_probability_zero_payout(self):
        """Zero payout returns 0 (division guard)."""
        assert fee_as_probability_points(1, 50, 0) == 0.0

    def test_fee_probability_is_small_relative_to_5pct_edge(self):
        """
        At our min_edge_pct=0.05 and typical trade, fee should be < edge.
        Verifies we have positive expected value after fees.
        """
        # 10 contracts at 50¢: fee = ceil(0.07*10*0.5*0.5*100) = ceil(17.5) = 18 cents
        # payout = 1000 cents
        # fee_pp = 18/1000 = 0.018
        fee_pp = fee_as_probability_points(10, 50, 1000)
        assert fee_pp < 0.05  # fee < min_edge_pct, so edge survives


class TestEdgeSurvivesFee:
    """Verify the edge survival check correctly accepts/rejects signals."""

    def test_strong_edge_survives(self):
        """A 10% edge clearly survives fees."""
        survives, net_edge = edge_survives_fee(
            edge_pct=0.10, contracts=10, price_cents=50
        )
        assert survives
        assert net_edge > 0.05  # net edge still substantial

    def test_borderline_edge_may_not_survive(self):
        """
        Edge just at min_edge_pct=0.05 may be wiped by fees at high contract counts.
        fee_pp at 14 contracts, 50¢ = ~0.018. net_edge = 0.05 - 0.018 = 0.032 > 0.01 default.
        Should still survive with default min_net_edge_pct=0.01.
        """
        survives, net_edge = edge_survives_fee(
            edge_pct=0.05, contracts=14, price_cents=50
        )
        assert survives  # 0.032 > 0.01
        assert net_edge > 0.0

    def test_tiny_edge_does_not_survive_with_strict_threshold(self):
        """A 2% edge at high fee threshold does not survive with 2% min."""
        survives, net_edge = edge_survives_fee(
            edge_pct=0.02, contracts=14, price_cents=50, min_net_edge_pct=0.02
        )
        # fee_pp ≈ 0.018. net_edge = 0.02 - 0.018 = 0.002 < 0.02
        assert not survives

    def test_returns_tuple(self):
        """Function returns (bool, float) tuple."""
        result = edge_survives_fee(0.05, 1, 50)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], float)

    def test_fee_formula_matches_reference_doc(self):
        """
        End-to-end: reference doc says edge > 4 cents after fee for 1 contract.
        4 cents on 100 cent payout = 0.04 probability points edge.
        At 50¢, fee = 2 cents = 0.02 prob points. Net edge = 0.04 - 0.02 = 0.02 > 0.01.
        """
        # Reference: "edge > 0.04 (4 cents) after subtracting estimated fee"
        survives, net = edge_survives_fee(
            edge_pct=0.04, contracts=1, price_cents=50, min_net_edge_pct=0.01
        )
        # fee_pp = 2/100 = 0.02. net = 0.04 - 0.02 = 0.02 > 0.01
        assert survives
        assert abs(net - 0.02) < 0.005
