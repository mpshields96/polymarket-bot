"""
FOMC Fed rate decision strategy.

JOB:    Compare yield-curve-implied Fed rate probabilities to Kalshi KXFEDDECISION
        market prices. Return a Signal when the model disagrees by > min_edge_pct.

SIGNAL MODEL (two independent signals combined):

    1. YIELD CURVE SIGNAL (primary)
       yield_spread = DGS2 - DFF (2yr treasury yield minus current fed funds rate)
       Negative spread → market pricing net cuts → cut-biased
       Near-zero spread → hold-biased
       Positive spread → hike-biased
       Theory: expectations hypothesis — 2yr yield embeds next ~8 FOMC decisions

    2. CPI TREND ADJUSTMENT (secondary, ±8% shift)
       CPI accelerating (MoM rising) → less likely to cut, more likely to hold
       CPI decelerating (MoM falling) → more likely to cut

    Combined → P(hold), P(cut_25), P(cut_large), P(hike_25), P(hike_large)
    Sum to 1.0 (softmax-normalized after adjustments)

KALSHI MARKET STRUCTURE:
    Series: KXFEDDECISION-{YYMM}-{ACTION}
    Action suffixes:
        H0  → Hold (0bps)
        C25 → Cut 25bps
        C26 → Cut >25bps (50bps+)
        H25 → Hike 25bps
        H26 → Hike >25bps

TIMING:
    Only runs within [days_before_meeting] days of next FOMC meeting.
    Strategy goes quiet between meetings (rare signal, ~8x/year).

Reference:
    Federal Reserve working paper (Jan 2026): FOMC prediction markets have near-
    perfect record on day before meeting. Edge window is 7-14 days before.
    Series KXFEDDECISION confirmed active with 5M+ contract volume (2026-02-27).
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market, OrderBook
from src.data.fred import FREDFeed, FREDSnapshot

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

# ── 2026 FOMC meeting decision dates (day 2 = announcement day) ────────
# Source: federalreserve.gov/monetarypolicy/fomccalendars.htm

FOMC_DECISION_DATES_2026: list[date] = [
    date(2026, 1, 29),
    date(2026, 3, 19),
    date(2026, 5, 7),
    date(2026, 6, 18),
    date(2026, 7, 30),
    date(2026, 9, 17),
    date(2026, 10, 29),
    date(2026, 12, 10),
]


class FedAction(str, Enum):
    HOLD = "hold"
    CUT_25 = "cut_25"
    CUT_LARGE = "cut_large"
    HIKE_25 = "hike_25"
    HIKE_LARGE = "hike_large"


# Action suffix → FedAction (from KXFEDDECISION ticker suffix)
_SUFFIX_TO_ACTION: dict[str, FedAction] = {
    "H0":  FedAction.HOLD,
    "C25": FedAction.CUT_25,
    "C26": FedAction.CUT_LARGE,
    "H25": FedAction.HIKE_25,
    "H26": FedAction.HIKE_LARGE,
}

# Defaults
_DEFAULT_MIN_EDGE_PCT = 0.05
_DEFAULT_MIN_MINUTES_REMAINING = 60.0
_DEFAULT_DAYS_BEFORE_MEETING = 14
_DEFAULT_SPREAD_HOLD_BAND = 0.25       # ±0.25% spread → hold-biased
_DEFAULT_CPI_ADJUSTMENT = 0.08         # shift 8% between hold/cut on CPI trend


def _kalshi_fee_pct(price_cents: int) -> float:
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


def next_fomc_date(today: Optional[date] = None) -> Optional[date]:
    """Return the next FOMC decision date on or after today, or None if none left."""
    today = today or date.today()
    upcoming = [d for d in FOMC_DECISION_DATES_2026 if d >= today]
    return min(upcoming) if upcoming else None


def days_until_fomc(today: Optional[date] = None) -> Optional[int]:
    """Days until the next FOMC decision date, or None if none scheduled."""
    nxt = next_fomc_date(today)
    if nxt is None:
        return None
    return (nxt - (today or date.today())).days


def parse_fomc_action(ticker: str) -> Optional[FedAction]:
    """
    Extract FedAction from a KXFEDDECISION ticker.

    Examples:
        KXFEDDECISION-26MAR-H0  → FedAction.HOLD
        KXFEDDECISION-26MAR-C25 → FedAction.CUT_25
        KXFEDDECISION-26MAR-H26 → FedAction.HIKE_LARGE
    """
    m = re.search(r"KXFEDDECISION-\w+-(\w+)$", ticker)
    if not m:
        return None
    return _SUFFIX_TO_ACTION.get(m.group(1).upper())


def compute_model_probs(
    snap: FREDSnapshot,
    spread_hold_band: float = _DEFAULT_SPREAD_HOLD_BAND,
    cpi_adjustment: float = _DEFAULT_CPI_ADJUSTMENT,
) -> dict[FedAction, float]:
    """
    Convert FRED snapshot into model probabilities for each Fed action.

    Returns dict mapping FedAction → probability (sums to 1.0).

    Yield spread regime:
        spread < -(2 * band)   → aggressive cut regime
        spread < -band         → mild cut regime
        |spread| <= band       → hold regime
        spread > +band         → hike regime (rare in 2026)
    """
    spread = snap.yield_spread

    # Base probs by yield spread regime
    if spread < -(2 * spread_hold_band):   # < -0.50%: aggressive cuts priced in
        probs = {
            FedAction.HOLD:       0.30,
            FedAction.CUT_25:     0.50,
            FedAction.CUT_LARGE:  0.15,
            FedAction.HIKE_25:    0.03,
            FedAction.HIKE_LARGE: 0.02,
        }
    elif spread < -spread_hold_band:       # -0.50% to -0.25%: mild cut bias
        probs = {
            FedAction.HOLD:       0.55,
            FedAction.CUT_25:     0.35,
            FedAction.CUT_LARGE:  0.06,
            FedAction.HIKE_25:    0.03,
            FedAction.HIKE_LARGE: 0.01,
        }
    elif spread <= spread_hold_band:       # -0.25% to +0.25%: hold regime
        probs = {
            FedAction.HOLD:       0.75,
            FedAction.CUT_25:     0.15,
            FedAction.CUT_LARGE:  0.03,
            FedAction.HIKE_25:    0.05,
            FedAction.HIKE_LARGE: 0.02,
        }
    else:                                  # > +0.25%: hike bias
        probs = {
            FedAction.HOLD:       0.45,
            FedAction.CUT_25:     0.05,
            FedAction.CUT_LARGE:  0.01,
            FedAction.HIKE_25:    0.40,
            FedAction.HIKE_LARGE: 0.09,
        }

    # CPI trend adjustment: shift between hold and cut_25
    adj = min(cpi_adjustment, probs[FedAction.CUT_25])
    if snap.cpi_accelerating:
        # Inflation re-accelerating → less likely to cut, more likely to hold
        probs[FedAction.CUT_25] = max(0.01, probs[FedAction.CUT_25] - adj)
        probs[FedAction.HOLD]   = min(0.97, probs[FedAction.HOLD]   + adj)
    else:
        # Inflation decelerating → more likely to cut, less likely to hold
        hold_transfer = min(adj, probs[FedAction.HOLD] - 0.05)
        if hold_transfer > 0:
            probs[FedAction.HOLD]   -= hold_transfer
            probs[FedAction.CUT_25] += hold_transfer

    # Normalize to sum = 1.0
    total = sum(probs.values())
    return {k: round(v / total, 6) for k, v in probs.items()}


# ── Strategy ──────────────────────────────────────────────────────────


class FOMCRateStrategy(BaseStrategy):
    """
    FOMC rate decision strategy.

    Compares yield-curve-derived model probabilities to Kalshi
    KXFEDDECISION market prices. Only active within days_before_meeting
    days of the next scheduled FOMC decision.

    Paper-only until edge is confirmed over multiple meetings.
    """

    def __init__(
        self,
        fred_feed: FREDFeed,
        min_edge_pct: float = _DEFAULT_MIN_EDGE_PCT,
        min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
        days_before_meeting: int = _DEFAULT_DAYS_BEFORE_MEETING,
        spread_hold_band: float = _DEFAULT_SPREAD_HOLD_BAND,
        cpi_adjustment: float = _DEFAULT_CPI_ADJUSTMENT,
    ):
        self._fred = fred_feed
        self._min_edge_pct = min_edge_pct
        self._min_minutes_remaining = min_minutes_remaining
        self._days_before_meeting = days_before_meeting
        self._spread_hold_band = spread_hold_band
        self._cpi_adjustment = cpi_adjustment

    @property
    def name(self) -> str:
        return "fomc_rate_v1"

    def generate_signal(
        self,
        market: Market,
        orderbook: OrderBook,
        btc_feed,   # not used — FOMC strategy needs no crypto feed
    ) -> Optional[Signal]:
        """Evaluate FOMC model vs Kalshi KXFEDDECISION market price."""

        # ── 1. FOMC timing gate ───────────────────────────────────────
        days_away = days_until_fomc()
        if days_away is None or days_away > self._days_before_meeting:
            logger.debug(
                "[fomc] Next meeting %d days away (window=%d) — skip %s",
                days_away or 9999, self._days_before_meeting, market.ticker,
            )
            return None

        # ── 2. FRED data check ────────────────────────────────────────
        if self._fred.is_stale:
            logger.debug("[fomc] FRED feed stale — skip %s", market.ticker)
            return None

        snap = self._fred.snapshot()
        if snap is None:
            logger.debug("[fomc] No FRED snapshot — skip %s", market.ticker)
            return None

        # ── 3. Parse market action from ticker ────────────────────────
        action = parse_fomc_action(market.ticker)
        if action is None:
            logger.debug("[fomc] Cannot parse action from ticker %s — skip", market.ticker)
            return None

        # ── 4. Time remaining check ───────────────────────────────────
        minutes_remaining = self._minutes_remaining(market)
        if minutes_remaining is None or minutes_remaining <= self._min_minutes_remaining:
            logger.debug(
                "[fomc] %.1f min remaining (need >%.1f) — skip %s",
                minutes_remaining or 0.0, self._min_minutes_remaining, market.ticker,
            )
            return None

        # ── 5. Compute model probabilities ────────────────────────────
        model_probs = compute_model_probs(
            snap,
            spread_hold_band=self._spread_hold_band,
            cpi_adjustment=self._cpi_adjustment,
        )
        model_prob_yes = model_probs.get(action, 0.0)

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
                "[fomc] %s %s: model=%.3f | YES=%d¢ NO=%d¢ | "
                "edge_yes=%.3f edge_no=%.3f | spread=%.2f%% CPI %s — skip",
                market.ticker, action.value, model_prob_yes,
                market.yes_price, market.no_price,
                edge_yes, edge_no,
                snap.yield_spread,
                "↑" if snap.cpi_accelerating else "↓",
            )
            return None

        if price_cents <= 0 or price_cents >= 100:
            return None

        win_prob = max(0.51, min(0.99, win_prob))
        confidence = min(1.0, abs(model_prob_yes - 0.5) * 2.0)

        reason = (
            f"FOMC {days_away}d away | action={action.value} | "
            f"model={model_prob_yes:.3f} mkt={market.yes_price / 100:.3f} | "
            f"spread={snap.yield_spread:+.2f}% CPI_accel={snap.cpi_accelerating} | "
            f"edge_{side}={edge_pct:.1%}"
        )

        logger.info("[fomc] Signal: BUY %s @ %d¢ | %s", side.upper(), price_cents, reason)

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


def load_from_config() -> FOMCRateStrategy:
    """Build FOMCRateStrategy from config.yaml strategy.fomc section."""
    import yaml
    from src.data.fred import load_from_config as fred_load

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return FOMCRateStrategy(fred_feed=fred_load())

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    f_cfg = cfg.get("strategy", {}).get("fomc", {})
    return FOMCRateStrategy(
        fred_feed=fred_load(),
        min_edge_pct=f_cfg.get("min_edge_pct", _DEFAULT_MIN_EDGE_PCT),
        min_minutes_remaining=f_cfg.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING),
        days_before_meeting=f_cfg.get("days_before_meeting", _DEFAULT_DAYS_BEFORE_MEETING),
        spread_hold_band=f_cfg.get("spread_hold_band", _DEFAULT_SPREAD_HOLD_BAND),
        cpi_adjustment=f_cfg.get("cpi_adjustment", _DEFAULT_CPI_ADJUSTMENT),
    )
