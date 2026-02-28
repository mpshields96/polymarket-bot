"""
Weather forecast vs Kalshi temperature market strategy.

JOB:    Compare Open-Meteo GFS forecast with Kalshi daily temperature market prices.
        Return a Signal when the model probability diverges from the market price
        by more than min_edge_pct (after fees). Return None to hold.

LOGIC (all 4 must be true):
    1. Weather feed is fresh (not stale).
    2. Market title encodes a temperature bracket we can parse.
    3. > min_minutes_remaining remain in the market window.
    4. |model_prob - market_yes_price| - kalshi_fee > min_edge_pct.

PROBABILITY MODEL:
    - Open-Meteo gives: forecast_temp_f (daily max, °F), forecast_std_f (uncertainty, °F).
    - Model assumes daily high ~ N(forecast_temp_f, forecast_std_f).
    - P(daily high in bracket) = Φ((upper - mu)/sigma) - Φ((lower - mu)/sigma).
    - Normal CDF computed via math.erf (no scipy needed).

MARKET TITLE PARSING:
    Kalshi NYC daily high markets have subtitles like:
      "63° or lower"   →  bracket = (-inf, 63]
      "64° to 67°"     →  bracket = [64, 67]
      "68° or higher"  →  bracket = [68, +inf)

    Parsing is attempted on market.title; if that fails, skipped (returns None).

Reference:  jazzmine-p/weather-forecast-automated-trading (LSTM + NCEI approach)
            Kalshi NYC high-temp series: HIGHNY-YYMONDD-* markets
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market, OrderBook
from src.data.weather import WeatherFeed

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── Defaults ─────────────────────────────────────────────────────────

_DEFAULT_MIN_EDGE_PCT = 0.05          # 5% net edge required after fees
_DEFAULT_MIN_MINUTES_REMAINING = 30.0 # Don't enter with < 30 min left
_DEFAULT_MIN_CONFIDENCE = 0.60        # Model must assign < 40% or > 60% to YES side

# Kalshi fee formula: 0.07 × P × (1 - P), where P is price in [0, 1]


def _kalshi_fee_pct(price_cents: int) -> float:
    """Return fee as fraction (e.g. 0.017 = 1.7%) given price in cents."""
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


def _normal_cdf(x: float) -> float:
    """Standard normal CDF Φ(x) via math.erf. No scipy needed."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _prob_in_bracket(lower: float, upper: float, mu: float, sigma: float) -> float:
    """
    P(X in [lower, upper]) where X ~ N(mu, sigma).
    lower and upper may be -inf/+inf for open-ended brackets.
    """
    sigma = max(sigma, 0.01)   # guard against zero sigma
    p_above_lower = 1.0 - _normal_cdf((lower - mu) / sigma) if math.isfinite(lower) else 1.0
    p_below_upper = _normal_cdf((upper - mu) / sigma) if math.isfinite(upper) else 1.0
    prob = p_below_upper - (1.0 - p_above_lower)
    return max(0.001, min(0.999, prob))


# ── Title parser ──────────────────────────────────────────────────────


def parse_temp_bracket(title: str) -> Optional[Tuple[float, float]]:
    """
    Parse temperature bracket from Kalshi market title.

    Supports:
      "63° or lower"  →  (-inf, 63)
      "64° to 67°"    →  (64, 67)
      "68° or higher" →  (68, +inf)

    Returns (lower_f, upper_f) inclusive bounds, or None on parse failure.
    """
    # "X° or lower" / "X degrees or lower"
    m = re.search(r'(\d+)\s*[°°]?\s*(?:degrees?)?\s+or\s+lower', title, re.IGNORECASE)
    if m:
        return (float('-inf'), float(m.group(1)))

    # "X° or higher"
    m = re.search(r'(\d+)\s*[°°]?\s*(?:degrees?)?\s+or\s+higher', title, re.IGNORECASE)
    if m:
        return (float(m.group(1)), float('inf'))

    # "X° to Y°" / "X-Y°"
    m = re.search(r'(\d+)\s*[°°]?\s*(?:degrees?)?\s+(?:to|-)\s+(\d+)', title, re.IGNORECASE)
    if m:
        return (float(m.group(1)), float(m.group(2)))

    # Also try subtitle-like: "≥68°" or "≤63°"
    m = re.search(r'[≥>=]+\s*(\d+)', title)
    if m:
        return (float(m.group(1)), float('inf'))
    m = re.search(r'[≤<=]+\s*(\d+)', title)
    if m:
        return (float('-inf'), float(m.group(1)))

    return None


# ── Strategy ──────────────────────────────────────────────────────────


class WeatherForecastStrategy(BaseStrategy):
    """
    Weather forecast vs Kalshi temperature market strategy.

    Compares Open-Meteo GFS forecast with daily temperature market prices.
    Fires when our normal-distribution model says the market is mispriced.

    This strategy is paper-only (market prices in Kalshi weather markets are
    relatively efficient; paper mode collects calibration data first).
    """

    def __init__(
        self,
        weather_feed: WeatherFeed,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
        name_override: Optional[str] = None,
    ):
        self._weather_feed = weather_feed
        self._min_edge_pct = min_edge_pct
        self._min_minutes_remaining = min_minutes_remaining
        self._min_confidence = min_confidence
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "weather_forecast_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed,   # accepted but not used — weather strategy needs no crypto feed
    ) -> Optional[Signal]:
        """
        Evaluate weather forecast vs Kalshi market price.
        Returns Signal or None.
        """
        # ── 1. Weather feed check ─────────────────────────────────────
        if self._weather_feed.is_stale:
            logger.debug("[weather] Weather feed is stale — skip %s", market.ticker)
            return None

        forecast_f = self._weather_feed.forecast_temp_f()
        if forecast_f is None:
            logger.debug("[weather] No forecast available — skip %s", market.ticker)
            return None

        std_f = self._weather_feed.forecast_std_f()

        # ── 2. Parse temperature bracket from market title ────────────
        bracket = parse_temp_bracket(market.title)
        if bracket is None:
            logger.debug(
                "[weather] Cannot parse bracket from title %r — skip %s",
                market.title, market.ticker,
            )
            return None

        lower_f, upper_f = bracket

        # ── 3. Check time remaining ────────────────────────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None:
            logger.debug("[weather] Cannot determine time remaining for %s — skip", market.ticker)
            return None

        if minutes_remaining <= self._min_minutes_remaining:
            logger.debug(
                "[weather] Only %.1f min remaining (need >%.1f) for %s — skip",
                minutes_remaining, self._min_minutes_remaining, market.ticker,
            )
            return None

        # ── 4. Compute model probability ──────────────────────────────
        model_prob_yes = _prob_in_bracket(lower_f, upper_f, forecast_f, std_f)

        if abs(model_prob_yes - 0.5) < (self._min_confidence - 0.5):
            # Model is close to 50/50 — not confident enough to trade
            bracket_str = (
                f"≤{upper_f:.0f}°F" if not math.isfinite(lower_f)
                else f"≥{lower_f:.0f}°F" if not math.isfinite(upper_f)
                else f"{lower_f:.0f}–{upper_f:.0f}°F"
            )
            logger.info(
                "[weather] %s: forecast=%.1f°F bracket=%s P(YES)=%.3f — confidence too low",
                market.ticker, forecast_f, bracket_str, model_prob_yes,
            )
            return None

        # ── 5. Edge calculation ────────────────────────────────────────
        fee_yes = _kalshi_fee_pct(market.yes_price)
        fee_no = _kalshi_fee_pct(market.no_price)
        edge_yes = model_prob_yes - (market.yes_price / 100.0) - fee_yes
        edge_no = (1.0 - model_prob_yes) - (market.no_price / 100.0) - fee_no

        bracket_str = (
            f"≤{upper_f:.0f}°F" if not math.isfinite(lower_f)
            else f"≥{lower_f:.0f}°F" if not math.isfinite(upper_f)
            else f"{lower_f:.0f}–{upper_f:.0f}°F"
        )

        if edge_yes >= edge_no and edge_yes >= self._min_edge_pct:
            side = "yes"
            price_cents = market.yes_price
            edge_pct = edge_yes
            win_prob = model_prob_yes
        elif edge_no > edge_yes and edge_no >= self._min_edge_pct:
            side = "no"
            price_cents = market.no_price
            edge_pct = edge_no
            win_prob = 1.0 - model_prob_yes
        else:
            logger.info(
                "[weather] %s: forecast=%.1f°F bracket=%s P(YES)=%.3f | "
                "edge_yes=%.3f edge_no=%.3f both < min %.3f — skip",
                market.ticker, forecast_f, bracket_str, model_prob_yes,
                edge_yes, edge_no, self._min_edge_pct,
            )
            return None

        if price_cents <= 0 or price_cents >= 100:
            logger.debug(
                "[weather] Invalid %s price %d¢ for %s — skip", side, price_cents, market.ticker
            )
            return None

        win_prob = max(0.51, min(0.99, win_prob))
        confidence = min(1.0, abs(model_prob_yes - 0.5) * 2.0)

        reason = (
            f"forecast {forecast_f:.1f}°F (±{std_f:.1f}°F), "
            f"bracket {bracket_str}, P(YES)={model_prob_yes:.3f}, "
            f"edge_{side}={edge_pct:.1%}, {minutes_remaining:.0f}min remaining"
        )

        logger.info(
            "[weather] Signal: BUY %s @ %d¢ | %s",
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

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _minutes_remaining(market: Market) -> Optional[float]:
        """Return minutes remaining until market close, or None on parse error."""
        try:
            close_dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            remaining_sec = (close_dt - now_dt).total_seconds()
            return max(0.0, remaining_sec / 60.0)
        except Exception:
            return None


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> WeatherForecastStrategy:
    """Build WeatherForecastStrategy from config.yaml strategy.weather section."""
    import yaml
    from src.data.weather import load_nyc_weather_from_config

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using WeatherForecastStrategy defaults")
        from src.data.weather import WeatherFeed, CITY_NYC
        return WeatherForecastStrategy(weather_feed=WeatherFeed(**CITY_NYC))

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    w = cfg.get("strategy", {}).get("weather", {})
    weather_feed = load_nyc_weather_from_config()

    return WeatherForecastStrategy(
        weather_feed=weather_feed,
        min_edge_pct=w.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=w.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        min_confidence=w.get("min_confidence", _DEFAULT_MIN_CONFIDENCE),
    )
