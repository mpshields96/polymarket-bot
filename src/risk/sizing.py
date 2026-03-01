"""
Position sizing — Kelly criterion + stage-based caps.

This module ONLY calculates size. It does NOT place orders or check kill switch.
The kill switch is always checked separately before this result is used.

Kelly formula: f* = (p*b - q) / b
  p = win probability
  b = net odds (payout per $1 risked)
  q = 1 - p

We use 0.25x fractional Kelly (conservative) capped by the stage system.

Stage system:
  Stage 1: bankroll $0–$100   → max $5/bet, 5% bankroll
  Stage 2: bankroll $100–$250 → max $10/bet, 5% bankroll
  Stage 3: bankroll $250+     → max $15/bet, 4% bankroll

Adapted from: https://github.com/djienne/Polymarket-bot (core/kelly.py)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Hard caps — cannot be overridden by config ────────────────────
KELLY_FRACTION = 0.25           # Conservative 1/4 Kelly
ABSOLUTE_MAX_USD = 15.00        # No bet ever exceeds this (Stage 3 cap)

STAGES = {
    1: {"range": (0.0,   100.0),  "max_usd": 5.00,  "max_pct": 0.05},
    2: {"range": (100.0, 250.0),  "max_usd": 10.00, "max_pct": 0.05},
    3: {"range": (250.0, 9999.0), "max_usd": 15.00, "max_pct": 0.04},
}


@dataclass
class SizeResult:
    recommended_usd: float      # What we recommend betting
    kelly_raw_usd: float        # Raw Kelly before caps
    stage: int                  # Current bankroll stage (1, 2, or 3)
    stage_cap_usd: float        # Stage max_usd that applied
    pct_cap_usd: float          # Pct-of-bankroll cap that applied
    limiting_factor: str        # "kelly" | "stage_cap" | "pct_cap" | "absolute_cap"
    edge_pct: float             # Edge percentage from strategy signal


def get_stage(bankroll_usd: float) -> int:
    """Return the bankroll stage (1, 2, or 3)."""
    for stage_num, config in STAGES.items():
        lo, hi = config["range"]
        if lo <= bankroll_usd < hi:
            return stage_num
    return 3  # Default to Stage 3 if above all ranges


def calculate_size(
    win_prob: float,
    payout_per_dollar: float,
    edge_pct: float,
    bankroll_usd: float,
    min_edge_pct: float = 0.08,
) -> Optional[SizeResult]:
    """
    Calculate recommended bet size.

    Args:
        win_prob:           Probability of winning (0.0–1.0)
        payout_per_dollar:  Net payout per $1 risked (e.g., 1.27 for a 44¢ YES contract)
        edge_pct:           Edge from strategy signal (must exceed min_edge_pct)
        bankroll_usd:       Current bankroll in USD
        min_edge_pct:       Minimum edge to bet at all (default 8%)

    Returns:
        SizeResult if we should bet, None if edge is too thin or bankroll too low.
    """
    # Edge check
    if edge_pct < min_edge_pct:
        logger.debug("Edge %.1f%% below minimum %.1f%% — no bet", edge_pct * 100, min_edge_pct * 100)
        return None

    # Bankroll check
    if bankroll_usd <= 0:
        logger.warning("Bankroll is zero or negative — no bet")
        return None

    # ── Kelly calculation ─────────────────────────────────────────
    p = win_prob
    q = 1.0 - p
    b = payout_per_dollar  # net odds (b to 1)

    # Kelly fraction (fraction of bankroll to bet)
    if b <= 0:
        logger.warning("Invalid payout_per_dollar: %.4f — no bet", b)
        return None

    kelly_raw = (p * b - q) / b
    if kelly_raw <= 0:
        logger.debug("Kelly is negative (%.4f) — no edge, no bet", kelly_raw)
        return None

    kelly_fractional = kelly_raw * KELLY_FRACTION
    kelly_usd = kelly_fractional * bankroll_usd

    # ── Stage caps ────────────────────────────────────────────────
    stage = get_stage(bankroll_usd)
    stage_cfg = STAGES[stage]
    stage_cap_usd = stage_cfg["max_usd"]
    pct_cap_usd = bankroll_usd * stage_cfg["max_pct"]

    # ── Apply caps in order ───────────────────────────────────────
    size = kelly_usd
    limiting_factor = "kelly"

    if size > stage_cap_usd:
        size = stage_cap_usd
        limiting_factor = "stage_cap"

    if size > pct_cap_usd:
        size = pct_cap_usd
        limiting_factor = "pct_cap"

    if size > ABSOLUTE_MAX_USD:
        size = ABSOLUTE_MAX_USD
        limiting_factor = "absolute_cap"

    # Floor to nearest cent (truncate, never round up).
    # Using round() would round $4.7685 → $4.77, which then fails the kill switch
    # pct_cap check ($4.77 / $95.37 = 5.0016% > 5.0%).  Floor ensures the sized
    # bet never exceeds the pct cap when the kill switch re-checks the same bankroll.
    size = math.floor(size * 100) / 100

    # Minimum viable bet ($0.50 — below this isn't worth the fee)
    if size < 0.50:
        logger.debug("Size $%.2f below minimum $0.50 — no bet", size)
        return None

    result = SizeResult(
        recommended_usd=size,
        kelly_raw_usd=round(kelly_usd, 2),
        stage=stage,
        stage_cap_usd=stage_cap_usd,
        pct_cap_usd=round(pct_cap_usd, 2),
        limiting_factor=limiting_factor,
        edge_pct=edge_pct,
    )

    logger.info(
        "SIZE: $%.2f (Kelly raw: $%.2f, Stage %d cap: $%.2f, "
        "pct cap: $%.2f, edge: %.1f%%, limited by: %s)",
        size, kelly_usd, stage, stage_cap_usd, pct_cap_usd,
        edge_pct * 100, limiting_factor,
    )

    return result


def kalshi_fee(yes_price_cents: int) -> float:
    """
    Kalshi taker fee: 0.07 * P * (1 - P), where P = yes_price / 100.

    Adapted from: https://github.com/sswadkar/kalshi-interface
    """
    p = yes_price_cents / 100.0
    return 0.07 * p * (1.0 - p)


def kalshi_payout(yes_price_cents: int, side: str) -> float:
    """
    Net payout per $1 risked on Kalshi, after fee.

    For a YES contract at 44¢:
      - Pay 44¢ to potentially win 100¢ (56¢ profit)
      - Net odds b = 56/44 = 1.27
      - After fee: slightly lower

    Args:
        yes_price_cents: YES price in cents (1–99)
        side: "yes" or "no"

    Returns:
        Net payout per $1 risked (b in Kelly formula)
    """
    p_yes = yes_price_cents / 100.0
    p_no = 1.0 - p_yes
    fee = kalshi_fee(yes_price_cents)

    if side == "yes":
        # Pay p_yes, win 1.0, net profit = (1 - p_yes) = p_no
        gross_payout = p_no / p_yes  # odds b
    else:
        # Pay p_no, win 1.0, net profit = (1 - p_no) = p_yes
        gross_payout = p_yes / p_no  # odds b

    # Fee is deducted from winnings
    net_payout = gross_payout - (fee / (p_yes if side == "yes" else p_no))
    return max(net_payout, 0.0)
