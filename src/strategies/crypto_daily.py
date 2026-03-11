"""
CryptoDailyStrategy — Kalshi hourly crypto daily markets (KXBTCD/KXETHD/KXSOLD).

JOB:    Find the ATM market in a daily crypto series 30min-6hr before settlement.
        Apply intraday drift signal to estimate direction.
        Bet when model probability diverges from market price by > min_edge_pct.

Market structure (KXBTCD example):
  - 24 hourly settlement slots per day (midnight to 11pm EST)
  - ~40-75 strike levels per slot
  - YES = asset above $strike at close time
  - Settlement via CF Benchmarks at fixed UTC time

DOES NOT: Make API calls, size trades, manage risk.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import List, Optional

from src.platforms.kalshi import Market
from src.strategies.base import Signal

logger = logging.getLogger(__name__)

_MIN_SIGNAL_PRICE_CENTS = 35
_MAX_SIGNAL_PRICE_CENTS = 65
_KALSHI_FEE_COEFF = 0.07   # Kalshi charges 7% × p × (1-p) of winnings

# Per-asset hourly vol lookup (% per sqrt-hour, reflects intraday realized volatility).
# BTC annualized ~85% → 0.01/sqrt-hr. ETH ~50% more volatile. SOL ~2-3x more volatile.
# Old single constant _HOURLY_VOL = 0.005 was too low and asset-agnostic.
_HOURLY_VOL_BY_ASSET: dict[str, float] = {
    "BTC": 0.01,   # 1% per sqrt-hour (annualized ~85%)
    "ETH": 0.015,  # 1.5% per sqrt-hour (ETH ~50% more volatile than BTC)
    "SOL": 0.025,  # 2.5% per sqrt-hour (SOL ~2-3x BTC volatility)
}
_HOURLY_VOL_DEFAULT = 0.01  # fallback for unknown assets

_DRIFT_WEIGHT = 0.7        # blend: 70% drift signal, 30% lognormal position
_DRIFT_SCALE = 5.0         # 1% drift → +5pp probability premium


def _hourly_vol_for(asset: str) -> float:
    """Return per-asset hourly vol (% per sqrt-hour). Defaults to BTC if unknown."""
    return _HOURLY_VOL_BY_ASSET.get(asset.upper(), _HOURLY_VOL_DEFAULT)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erfc — no scipy dependency."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


class CryptoDailyStrategy:
    """
    Strategy for Kalshi daily crypto fixed-time markets (KXBTCD, KXETHD, KXSOLD).

    Each series has 24 hourly settlement slots per day. For each slot, Kalshi
    lists ~40-75 strike prices. This strategy finds the ATM strike and bets on
    direction when the intraday drift provides sufficient edge.

    Parameters
    ----------
    asset                 : "BTC", "ETH", or "SOL"
    series_ticker         : "KXBTCD", "KXETHD", or "KXSOLD"
    min_drift_pct         : minimum intraday drift to fire (0.005 = 0.5%)
    min_edge_pct          : minimum net edge after Kalshi fee (0.04 = 4%)
    min_minutes_remaining : skip markets settling too soon (default 30 min)
    max_minutes_remaining : skip markets settling too far out (default 360 min)
    min_volume            : minimum market volume for liquidity filter
    """

    def __init__(
        self,
        asset: str,
        series_ticker: str,
        min_drift_pct: float = 0.005,
        min_edge_pct: float = 0.04,
        min_minutes_remaining: float = 30.0,
        max_minutes_remaining: float = 360.0,
        min_volume: int = 100,
        direction_filter: Optional[str] = None,
    ) -> None:
        """
        direction_filter: if "no", only fire on upward drift and always bet NO.
        Rationale: same HFT front-running pattern seen in btc_drift (48 live bets,
        p≈3.7%): YES side overpriced when BTC trends up, NO side offers better value.
        Default None = original YES/NO based on drift direction.
        """
        self.asset = asset.upper()
        self.series_ticker = series_ticker
        self._min_drift_pct = min_drift_pct
        self._min_edge_pct = min_edge_pct
        self._direction_filter = direction_filter
        self._min_minutes_remaining = min_minutes_remaining
        self._max_minutes_remaining = max_minutes_remaining
        self._min_volume = min_volume

    @property
    def name(self) -> str:
        return f"{self.asset.lower()}_daily_v1"

    # ── Public interface ──────────────────────────────────────────────────

    def generate_signal(
        self,
        spot: float,
        session_open: float,
        markets: List[Market],
    ) -> Optional[Signal]:
        """
        Evaluate current intraday drift and return a Signal or None.

        Args:
            spot         : current mid-price of the asset (USD)
            session_open : asset price at the start of today's session (USD)
            markets      : all open markets for this series (all hourly slots)

        Returns:
            Signal if there's a trade opportunity, None to hold.
        """
        if session_open <= 0:
            return None

        drift_pct = (spot - session_open) / session_open

        # direction_filter="no": only fire on upward drift, always bet NO (contrarian).
        # Original mode: fire on both directions, side follows drift direction.
        if self._direction_filter == "no":
            if drift_pct < self._min_drift_pct:
                logger.debug(
                    "[%s] direction_filter=no: drift %.4f below +%.4f threshold — no signal",
                    self.name, drift_pct, self._min_drift_pct,
                )
                return None
        else:
            if abs(drift_pct) < self._min_drift_pct:
                logger.debug(
                    "[%s] drift %.4f below threshold %.4f — no signal",
                    self.name, drift_pct, self._min_drift_pct,
                )
                return None

        atm = self._find_atm_market(markets, spot)
        if atm is None:
            logger.debug("[%s] no ATM market found — no signal", self.name)
            return None

        if self._direction_filter == "no":
            side = "no"  # always bet NO when filter active (contrarian on upward momentum)
        else:
            side = "yes" if drift_pct > 0 else "no"

        try:
            close_dt = datetime.fromisoformat(atm.close_time.replace("Z", "+00:00"))
        except (ValueError, AttributeError) as e:
            logger.warning(
                "[%s] failed to parse close_time %r: %s", self.name, atm.close_time, e
            )
            return None

        now = datetime.now(timezone.utc)
        hours_to_settle = (close_dt - now).total_seconds() / 3600.0
        if hours_to_settle <= 0:
            return None

        try:
            strike = float(atm.ticker.split("-T")[-1])
        except (ValueError, IndexError):
            logger.warning(
                "[%s] cannot parse strike from ticker %r", self.name, atm.ticker
            )
            return None

        model_prob = self._model_prob(
            spot=spot,
            strike=strike,
            hours_to_settle=hours_to_settle,
            drift_pct=drift_pct,
        )

        yes_bid: int = atm.yes_price
        yes_ask: int = atm.raw.get("yes_ask", yes_bid + 1)

        if side == "yes":
            price_cents = yes_ask
        else:
            price_cents = 100 - yes_bid

        price_cents = max(1, min(99, price_cents))

        edge = self._compute_edge(
            model_prob=model_prob,
            price_cents=price_cents,
            side=side,
        )

        if edge < self._min_edge_pct:
            logger.debug(
                "[%s] edge %.4f below min %.4f — no signal",
                self.name, edge, self._min_edge_pct,
            )
            return None

        win_prob = model_prob if side == "yes" else (1.0 - model_prob)
        win_prob = max(0.001, min(0.999, win_prob))
        edge_pct = max(0.001, min(0.999, round(edge, 6)))

        reason = (
            f"{self.asset} {side.upper()} {atm.ticker} | "
            f"drift={drift_pct:+.3%} spot={spot:.0f} strike={strike:.0f} "
            f"edge={edge:.3%} model={model_prob:.3f}"
        )

        logger.info("[%s] Signal: %s", self.name, reason)

        return Signal(
            side=side,
            edge_pct=edge_pct,
            win_prob=round(win_prob, 6),
            confidence=min(1.0, abs(drift_pct) / 0.05),
            ticker=atm.ticker,
            price_cents=price_cents,
            reason=reason,
        )

    def _find_atm_market(
        self,
        markets: List[Market],
        spot: float,
    ) -> Optional[Market]:
        """
        Find the market closest to at-the-money (yes_mid ≈ 50¢).

        Filters:
        - Time window: [min_minutes_remaining, max_minutes_remaining] to settlement
        - Volume >= min_volume
        - Price guard: mid in [35, 65]

        Priority: When multiple candidates are within 2¢ of the best ATM distance,
        prefer the one closing at 21:00 UTC (5pm EDT) — highest volume and tightest
        spreads on KXBTCD due to US equities close. Only within 2¢ tolerance so
        we don't sacrifice ATM quality for slot preference.
        """
        now = datetime.now(timezone.utc)
        # Store (dist, close_dt, mkt) so we parse close_dt only once per market
        candidates: list[tuple[float, datetime, Market]] = []

        for mkt in markets:
            try:
                close_dt = datetime.fromisoformat(
                    mkt.close_time.replace("Z", "+00:00")
                )
            except (ValueError, AttributeError):
                continue

            minutes_remaining = (close_dt - now).total_seconds() / 60.0
            if minutes_remaining < self._min_minutes_remaining:
                continue
            if minutes_remaining > self._max_minutes_remaining:
                continue

            if mkt.volume < self._min_volume:
                continue

            yes_bid: int = mkt.yes_price
            yes_ask: int = mkt.raw.get("yes_ask", yes_bid + 1)
            mid = (yes_bid + yes_ask) / 2.0

            if mid < _MIN_SIGNAL_PRICE_CENTS or mid > _MAX_SIGNAL_PRICE_CENTS:
                continue

            candidates.append((abs(mid - 50.0), close_dt, mkt))

        if not candidates:
            return None

        candidates.sort(key=lambda t: t[0])

        # 5pm EDT priority: prefer 21:00 UTC close slot when within 2¢ of best ATM distance.
        # Rationale: KXBTCD 21:00 UTC slot has 676K volume vs ~40-100K for other slots —
        # tighter spreads and lower fill risk.
        best_dist = candidates[0][0]
        top_tier = [(dist, close_dt, mkt) for dist, close_dt, mkt in candidates
                    if dist <= best_dist + 2.0]
        priority_21 = [mkt for _, close_dt, mkt in top_tier if close_dt.hour == 21]
        if priority_21:
            return priority_21[0]

        return candidates[0][2]

    def _model_prob(
        self,
        spot: float,
        strike: float,
        hours_to_settle: float,
        drift_pct: float,
    ) -> float:
        """
        Estimate P(asset > strike at settlement).

        Blends two signals:
        1. Drift signal: session momentum (drift_pct) scaled to a probability
        2. Lognormal position: how far spot is from strike with time-scaled uncertainty

        Returns a probability in [0, 1].
        """
        if strike <= 0 or spot <= 0 or hours_to_settle <= 0:
            return 0.5

        # Drift momentum signal: 1% drift → +5pp probability premium
        drift_signal = max(0.0, min(1.0, 0.5 + drift_pct * _DRIFT_SCALE))

        # Lognormal position signal: spot vs strike, uncertainty scales with sqrt(T)
        sigma = _hourly_vol_for(self.asset) * math.sqrt(hours_to_settle)
        if sigma < 1e-9:
            if spot > strike:
                position_prob = 1.0
            elif spot < strike:
                position_prob = 0.0
            else:
                position_prob = 0.5
        else:
            z = (math.log(spot) - math.log(strike)) / sigma
            position_prob = _norm_cdf(z)

        return _DRIFT_WEIGHT * drift_signal + (1.0 - _DRIFT_WEIGHT) * position_prob

    def _compute_edge(
        self,
        model_prob: float,
        price_cents: int,
        side: str,
    ) -> float:
        """
        Net edge = gross edge minus Kalshi fee.

        fee = 0.07 × p × (1-p) where p = price_cents / 100.
        Can return negative values (no edge).
        """
        p = price_cents / 100.0

        if side == "yes":
            gross = model_prob - p
        else:
            gross = (1.0 - model_prob) - p

        fee = _KALSHI_FEE_COEFF * p * (1.0 - p)
        return gross - fee
