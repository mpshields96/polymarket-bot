"""
Unemployment rate strategy.

JOB:    Compare BLS Employment Situation forecast (linear trend on last 3 UNRATE
        readings + ±0.2pp normal uncertainty) to Kalshi KXUNRATE market prices.
        Return a Signal when the model disagrees by > min_edge_pct.

SIGNAL MODEL:
    1. LINEAR TREND (primary)
       Uses last 3 monthly UNRATE readings from FRED.
       trend = (latest - prior2) / 2   (slope over 2 monthly intervals)
       forecast = latest + trend        (one-step-ahead extrapolation)

    2. NORMAL CDF (probability)
       P(YES) = P(actual > threshold) = 1 - norm.cdf((threshold - forecast) / sigma)
       sigma = uncertainty_band (default 0.2pp — typical 1-month UNRATE MAE)
       Implemented via math.erfc (no scipy dependency):
         norm.cdf(x) = 0.5 * erfc(-x / sqrt(2))

KALSHI MARKET STRUCTURE:
    Series: KXUNRATE-{YYYYMM}-{threshold}
    Ticker examples:
        KXUNRATE-202503-4.0  → "UNRATE > 4.0% in March 2026?"
        KXUNRATE-202504-3.5  → "UNRATE > 3.5% in April 2026?"

TIMING:
    Only runs within [days_before_release] days of next BLS Employment Situation
    release. Goes quiet between releases (12 releases per year, monthly).

BLS 2026 RELEASE DATES (Employment Situation — first Friday of each month):
    Jan 9, Feb 7, Mar 7, Apr 3, May 1, Jun 5, Jul 3, Aug 7, Sep 4, Oct 2, Nov 6, Dec 4

Reference:
    BLS calendar: bls.gov/schedule/news_release/empsit.htm
    FRED UNRATE series: fred.stlouisfed.org/series/UNRATE
"""

from __future__ import annotations

import logging
import math
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market, OrderBook
from src.data.fred import FREDFeed, FREDSnapshot

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── 2026 BLS Employment Situation release dates ────────────────────────
# Source: bls.gov/schedule/news_release/empsit.htm

BLS_RELEASE_DATES_2026: list[date] = [
    date(2026, 1, 9),
    date(2026, 2, 7),
    date(2026, 3, 7),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 6, 5),
    date(2026, 7, 3),
    date(2026, 8, 7),
    date(2026, 9, 4),
    date(2026, 10, 2),
    date(2026, 11, 6),
    date(2026, 12, 4),
]

# Defaults
_DEFAULT_MIN_EDGE_PCT = 0.05
_DEFAULT_MIN_MINUTES_REMAINING = 60.0
_DEFAULT_DAYS_BEFORE_RELEASE = 7
_DEFAULT_UNCERTAINTY_BAND = 0.2   # ±0.2pp normal distribution width for forecast


# ── Normal CDF via math.erfc (no scipy dependency) ────────────────────

def _norm_cdf(x: float) -> float:
    """Standard normal CDF: P(Z <= x). Implemented via math.erfc."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def _kalshi_fee_pct(price_cents: int) -> float:
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


# ── BLS calendar helpers ──────────────────────────────────────────────


def next_bls_date(today: Optional[date] = None) -> Optional[date]:
    """Return the next BLS release date on or after today, or None if none left in 2026."""
    today = today or date.today()
    upcoming = [d for d in BLS_RELEASE_DATES_2026 if d >= today]
    return min(upcoming) if upcoming else None


def days_until_bls(today: Optional[date] = None) -> Optional[int]:
    """Days until the next BLS release date, or None if none scheduled in 2026."""
    nxt = next_bls_date(today)
    if nxt is None:
        return None
    return (nxt - (today or date.today())).days


# ── Ticker parser ──────────────────────────────────────────────────────


def parse_unrate_ticker(ticker: str) -> Optional[float]:
    """
    Extract the rate threshold from a KXUNRATE ticker.

    Examples:
        KXUNRATE-202503-4.0 → 4.0
        KXUNRATE-202504-3.5 → 3.5

    Returns None if the ticker does not match the KXUNRATE pattern.
    """
    m = re.search(r"KXUNRATE-\d{6}-(\d+(?:\.\d+)?)$", ticker)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


# ── Probability model ─────────────────────────────────────────────────


def compute_unrate_model_prob(
    snap: FREDSnapshot,
    threshold: float,
    uncertainty_band: float = _DEFAULT_UNCERTAINTY_BAND,
) -> float:
    """
    Compute model P(YES) = P(actual UNRATE > threshold).

    Uses the linear trend from snap.unrate_forecast as the mean of a normal
    distribution with std_dev = uncertainty_band. Returns float in [0, 1].

    Formula:
        P(YES) = 1 - norm.cdf((threshold - forecast) / uncertainty_band)
    """
    forecast = snap.unrate_forecast
    if uncertainty_band <= 0.0:
        uncertainty_band = _DEFAULT_UNCERTAINTY_BAND
    z = (threshold - forecast) / uncertainty_band
    return 1.0 - _norm_cdf(z)


# ── Strategy ──────────────────────────────────────────────────────────


class UnemploymentRateStrategy(BaseStrategy):
    """
    Unemployment rate strategy.

    Compares BLS Employment Situation forecast (linear trend on last 3 UNRATE
    readings) to Kalshi KXUNRATE market prices. Only active within
    days_before_release days of the next scheduled BLS release.

    Paper-only until edge is confirmed over multiple BLS releases.
    """

    def __init__(
        self,
        fred_feed: FREDFeed,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        days_before_release: int = _DEFAULT_DAYS_BEFORE_RELEASE,
        uncertainty_band: float = _DEFAULT_UNCERTAINTY_BAND,
    ):
        self._fred = fred_feed
        self._min_edge_pct = min_edge_pct
        self._min_minutes_remaining = min_minutes_remaining
        self._days_before_release = days_before_release
        self._uncertainty_band = uncertainty_band

    @property
    def name(self) -> str:
        return "unemployment_rate_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed,   # not used — unemployment strategy needs no crypto feed
    ) -> Optional[Signal]:
        """Evaluate BLS unemployment model vs Kalshi KXUNRATE market price."""

        # ── 1. BLS timing gate ────────────────────────────────────────
        days_away = days_until_bls()
        if days_away is None or days_away > self._days_before_release:
            logger.debug(
                "[unemployment] Next BLS %s days away (window=%d) — skip %s",
                days_away if days_away is not None else "N/A",
                self._days_before_release,
                market.ticker,
            )
            return None

        # ── 2. FRED data check ────────────────────────────────────────
        if self._fred.is_stale:
            logger.debug("[unemployment] FRED feed stale — skip %s", market.ticker)
            return None

        snap = self._fred.snapshot()
        if snap is None:
            logger.debug("[unemployment] No FRED snapshot — skip %s", market.ticker)
            return None

        # ── 3. Parse threshold from ticker ────────────────────────────
        threshold = parse_unrate_ticker(market.ticker)
        if threshold is None:
            logger.debug(
                "[unemployment] Cannot parse KXUNRATE threshold from %s — skip",
                market.ticker,
            )
            return None

        # ── 4. Time remaining check ───────────────────────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None or minutes_remaining <= self._min_minutes_remaining:
            logger.debug(
                "[unemployment] %.1f min remaining (need >%.1f) — skip %s",
                minutes_remaining or 0.0, self._min_minutes_remaining, market.ticker,
            )
            return None

        # ── 5. Compute model probability ──────────────────────────────
        model_prob_yes = compute_unrate_model_prob(
            snap, threshold, uncertainty_band=self._uncertainty_band
        )

        # ── 6. Edge calculation ───────────────────────────────────────
        fee_yes = _kalshi_fee_pct(market.yes_price)
        fee_no  = _kalshi_fee_pct(market.no_price)
        edge_yes = model_prob_yes - (market.yes_price / 100.0) - fee_yes
        edge_no  = (1.0 - model_prob_yes) - (market.no_price / 100.0) - fee_no

        if edge_yes >= edge_no and edge_yes >= self._min_edge_pct:
            side, edge_pct, price_cents = "yes", edge_yes, market.yes_price
            win_prob = model_prob_yes
        elif edge_no > edge_yes and edge_no >= self._min_edge_pct:
            side, edge_pct, price_cents = "no", edge_no, market.no_price
            win_prob = 1.0 - model_prob_yes
        else:
            logger.info(
                "[unemployment] %s threshold=%.1f: model=%.3f | YES=%d¢ NO=%d¢ | "
                "edge_yes=%.3f edge_no=%.3f | forecast=%.2f%% %s — skip",
                market.ticker, threshold, model_prob_yes,
                market.yes_price, market.no_price,
                edge_yes, edge_no,
                snap.unrate_forecast,
                f"BLS {days_away}d away",
            )
            return None

        if price_cents <= 0 or price_cents >= 100:
            return None

        win_prob = max(0.51, min(0.99, win_prob))
        confidence = min(1.0, abs(model_prob_yes - 0.5) * 2.0)

        reason = (
            f"BLS {days_away}d away | threshold={threshold:.1f}% | "
            f"unrate_forecast={snap.unrate_forecast:.2f}% (trend={snap.unrate_trend:+.2f}pp/mo) | "
            f"model_yes={model_prob_yes:.3f} mkt_yes={market.yes_price / 100:.3f} | "
            f"edge_{side}={edge_pct:.1%}"
        )

        logger.info(
            "[unemployment] Signal: BUY %s @ %d¢ | %s",
            side.upper(), price_cents, reason,
        )

        return Signal(
            side=side,
            edge_pct=round(edge_pct, 4),
            win_prob=round(win_prob, 4),
            confidence=round(confidence, 4),
            ticker=market.ticker,
            price_cents=price_cents,
            reason=reason,
        )

    @staticmethod
    def _minutes_remaining(market: Market) -> Optional[float]:
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            return max(0.0, (close_dt - now_dt).total_seconds() / 60.0)
        except Exception:
            return None


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> UnemploymentRateStrategy:
    """Build UnemploymentRateStrategy from config.yaml strategy.unemployment section."""
    import yaml
    from src.data.fred import load_from_config as fred_load

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return UnemploymentRateStrategy(fred_feed=fred_load())

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    u_cfg = cfg.get("strategy", {}).get("unemployment", {})
    return UnemploymentRateStrategy(
        fred_feed=fred_load(),
        min_edge_pct=u_cfg.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=u_cfg.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        days_before_release=u_cfg.get("days_before_release", _DEFAULT_DAYS_BEFORE_RELEASE),
        uncertainty_band=u_cfg.get("uncertainty_band", _DEFAULT_UNCERTAINTY_BAND),
    )
