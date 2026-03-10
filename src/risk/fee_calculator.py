"""
Kalshi taker fee calculator.

JOB:    Compute the Kalshi taker fee for a given order before placing it.
        Verify that a signal's edge survives fees before returning a trade.

FORMULA (from Kalshi official fee schedule + reference doc Section 3.3):
    fee_cents = ceil(0.07 * contracts * (price_cents / 100) * (1 - price_cents / 100) * 100)

Examples at 1 contract:
    price=50¢: fee = ceil(0.07 * 1 * 0.50 * 0.50 * 100) = ceil(1.75) = 2 cents
    price=35¢: fee = ceil(0.07 * 1 * 0.35 * 0.65 * 100) = ceil(1.59) = 2 cents
    price=65¢: fee = ceil(0.07 * 1 * 0.65 * 0.35 * 100) = ceil(1.59) = 2 cents

Notes:
- Fees are charged at ORDER PLACEMENT (not settlement)
- Fee is symmetric: buying YES at 35¢ costs same as buying NO at 65¢ (they're the same odds)
- Fee is per-trade, not per-contract for small positions (but scales with contract count)
- Maximum fee per $5 bet: ~37 cents at 50¢ price (14 contracts × 2.6¢/contract)
- This is 0.74% of the $5 stake — significant vs a 5% edge but survivable

DOES NOT: Place orders, check kill switch, access DB.
"""

from __future__ import annotations

import math
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
_KALSHI_FEE_RATE = 0.07     # 7% fee rate (Kalshi official)
_MIN_FEE_CENTS = 1          # Minimum 1 cent per trade (our assumption — official may vary)


def kalshi_taker_fee_cents(contracts: int, price_cents: int) -> int:
    """
    Compute the Kalshi taker fee in cents.

    Formula: ceil(0.07 * contracts * (price_cents/100) * (1 - price_cents/100) * 100)

    Args:
        contracts:   Number of contracts (integer, >= 1)
        price_cents: YES price in cents (1-99)

    Returns:
        Fee in cents (always >= 1).

    Raises:
        ValueError: If inputs are out of range.
    """
    if contracts < 1:
        raise ValueError(f"contracts must be >= 1, got {contracts}")
    if not 1 <= price_cents <= 99:
        raise ValueError(f"price_cents must be 1-99, got {price_cents}")

    price_frac = price_cents / 100.0
    fee_raw = _KALSHI_FEE_RATE * contracts * price_frac * (1.0 - price_frac) * 100
    fee_cents = math.ceil(fee_raw)
    return max(fee_cents, _MIN_FEE_CENTS)


def fee_as_probability_points(contracts: int, price_cents: int, payout_cents: int) -> float:
    """
    Express the taker fee as a probability-point reduction to the edge.

    This allows comparing fee cost to edge_pct in the same units.

    fee_prob_points = fee_cents / payout_cents

    Where payout_cents = contracts * 100 (full $1 payout per contract at resolution).

    Example:
        14 contracts at 50¢: fee = 25 cents. payout = 1400 cents.
        fee_prob = 25 / 1400 = 0.018 = 1.8 probability points.
        If edge_pct = 0.05, net edge = 0.05 - 0.018 = 0.032 (3.2 probability points).

    Args:
        contracts:    Number of contracts
        price_cents:  YES price in cents
        payout_cents: Full payout in cents (= contracts * 100 for binary YES/NO)

    Returns:
        Fee as a fraction of payout (same units as edge_pct).
    """
    if payout_cents <= 0:
        return 0.0
    fee_c = kalshi_taker_fee_cents(contracts, price_cents)
    return fee_c / payout_cents


def edge_survives_fee(
    edge_pct: float,
    contracts: int,
    price_cents: int,
    min_net_edge_pct: float = 0.01,
) -> tuple[bool, float]:
    """
    Check if a signal's edge survives Kalshi taker fees.

    Args:
        edge_pct:         Raw edge from strategy model (|model_prob - market_prob|)
        contracts:        Number of contracts to trade
        price_cents:      YES price in cents
        min_net_edge_pct: Minimum acceptable net edge after fees (default: 1%)

    Returns:
        (survives: bool, net_edge_pct: float)
        survives = True if net_edge_pct >= min_net_edge_pct
        net_edge_pct = edge_pct minus fee expressed as probability points
    """
    payout_cents = contracts * 100
    fee_pp = fee_as_probability_points(contracts, price_cents, payout_cents)
    net_edge = edge_pct - fee_pp

    survives = net_edge >= min_net_edge_pct

    if not survives:
        logger.debug(
            "[fee_check] Edge %.3f - fee_pp %.3f = net %.3f < min %.3f — signal filtered",
            edge_pct, fee_pp, net_edge, min_net_edge_pct,
        )
    return survives, net_edge
