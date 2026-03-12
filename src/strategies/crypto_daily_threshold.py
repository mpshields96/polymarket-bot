"""
crypto_daily_threshold.py — N(d2) fair-value calculator for KXBTCD threshold bets.

KXBTCD markets are digital cash-or-nothing call options:
  "Will BTC price be ABOVE $K at time T?"
  Fair probability = N(d2) from Black-Scholes digital call formula.

This module is RESEARCH/PROTOTYPE only. No trading loop. No execution path.
Expansion gate must clear before building a live loop.

Math reference:
  Digital call P(above K) = N(d2)
  d2 = (ln(S/K) - 0.5 * sigma^2 * T) / (sigma * sqrt(T))
  N(x) = standard normal CDF = 0.5 * erfc(-x / sqrt(2))

Volatility source: Deribit DVOL (annualized implied vol, e.g. 57.0 for 57%).
  daily_sigma = DVOL / 100 / sqrt(365)
  hourly_sigma = DVOL / 100 / sqrt(8760)

This module has zero external dependencies (no scipy, no pandas, no numpy).
"""

import math
from typing import Optional


# ── Normal CDF via math.erfc (no scipy) ─────────────────────────────────────
# Same pattern as src/strategies/unemployment_rate.py

def _norm_cdf(x: float) -> float:
    """Standard normal CDF: P(Z <= x). Implemented via math.erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


# ── Core fair-value function ─────────────────────────────────────────────────

def fair_prob_above_strike(
    spot: float,
    strike: float,
    hours_remaining: float,
    dvol: float,
) -> float:
    """Compute P(BTC > strike at expiry) using Black-Scholes digital call formula.

    Parameters:
        spot: current BTC price in USD
        strike: threshold strike price in USD
        hours_remaining: time to settlement in hours (e.g. 4.0 for 4 hours)
        dvol: Deribit DVOL — annualized implied volatility as a percentage
              (e.g. 57.0 means 57% annualized vol)

    Returns:
        float in [0, 1] — model probability that BTC finishes above strike

    Returns 0.5 (coin flip) for invalid or degenerate inputs to fail safe.

    Notes:
        - d2 uses the full Black-Scholes form: ln(S/K) - 0.5*sigma^2*T
        - The -0.5*sigma^2 drift term is important for same-day (hours 1-8);
          over short horizons it is small but not zero.
        - No risk-free rate or carry (r=q=0 appropriate for crypto).
        - This is a lognormal position model only. It does NOT include
          intraday drift signals. For daily/weekly KXBTCD bets, the
          intraday drift from btc_daily_v1 is irrelevant (different signal
          regime). See .planning/KXBTCD_FRIDAY_FEASIBILITY.md.
    """
    # Safe defaults for degenerate inputs
    if hours_remaining <= 0.0 or spot <= 0.0 or strike <= 0.0 or dvol <= 0.0:
        return 0.5

    # Convert to BS parameters
    T = hours_remaining / 8760.0        # years (8760 = 24 * 365)
    sigma = dvol / 100.0                # annualized vol as decimal (e.g. 0.57)

    try:
        ln_ratio = math.log(spot / strike)
    except (ValueError, ZeroDivisionError):
        return 0.5

    # d2 = (ln(S/K) - 0.5 * sigma^2 * T) / (sigma * sqrt(T))
    drift_correction = 0.5 * sigma * sigma * T
    sigma_sqrt_t = sigma * math.sqrt(T)

    if sigma_sqrt_t <= 0.0:
        return 0.5

    d2 = (ln_ratio - drift_correction) / sigma_sqrt_t

    return _norm_cdf(d2)


# ── Edge calculation ──────────────────────────────────────────────────────────

def edge_pct(fair_prob: float, market_yes_price_cents: int) -> float:
    """Compute signed edge: model probability minus market-implied probability.

    Parameters:
        fair_prob: model probability (0–1) that BTC finishes above strike
        market_yes_price_cents: Kalshi YES price in cents (e.g. 50 = 50c)

    Returns:
        float — positive means model thinks YES is underpriced (favorable)
                negative means model thinks YES is overpriced (unfavorable)

    Example:
        fair_prob=0.65, market=50c → edge=+0.15 (buy YES, 15% edge)
        fair_prob=0.40, market=55c → edge=-0.15 (do not buy YES)
    """
    market_prob = market_yes_price_cents / 100.0
    return fair_prob - market_prob


# ── Volatility helpers ────────────────────────────────────────────────────────

def dvol_to_daily_sigma(dvol: float) -> float:
    """Convert annualized DVOL to daily expected move (1-sigma).

    Example: DVOL=57 → daily sigma ≈ 2.98%
    """
    return (dvol / 100.0) / math.sqrt(365)


def dvol_to_hourly_sigma(dvol: float) -> float:
    """Convert annualized DVOL to hourly expected move (1-sigma).

    Example: DVOL=57 → hourly sigma ≈ 0.495%
    """
    return (dvol / 100.0) / math.sqrt(8760)
