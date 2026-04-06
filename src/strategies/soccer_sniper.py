"""
SoccerSniper — KXUCLGAME in-play FLB sniping strategy.

JOB:    Enter UCL game markets when YES or NO price reaches 88-93c
        DURING a live game. Harvests the Favorite-Longshot Bias (FLB)
        that causes markets to undervalue near-certain wins.

MECHANISM:
    When a team is winning convincingly (e.g., Arsenal 2-0 at 75 min),
    the KXUCLGAME market moves to 90-93c YES. The FLB predicts:
    - Market implies ~10% reversal probability
    - Historical UCL data: actual reversal rate ~3-5%
    - Edge: 5-7% above market price

MARKET STRUCTURE (confirmed Session 164):
    - KXUCLGAME-26APR07SPOARS-ARS resolves on 90-min FIRST LEG result
    - close_time field = latest possible expiry (safety buffer, weeks away)
    - expected_expiration_time in raw = ~3 hours after kick-off (actual game end)
    - Market closes EARLY when winner is declared (early_close_condition)
    - FLB applies: time gate from expected_expiration_time, NOT close_time

TIMING LOGIC:
    - Game starts ~3 hours before expected_expiration_time (UCL kickoff 19:00 UTC)
    - game_start_est = expected_expiration_time - 3 * 3600
    - Entry gate: game_start_est <= now < expected_expiration_time
    - FLB window: seconds_remaining <= max_seconds_remaining (90 min)
    - seconds_remaining = (expected_expiration_time - now).total_seconds()

DIRECTION (no coin drift — soccer is score-based):
    - YES >= 88c: team is winning convincingly → buy YES
    - NO >= 88c: other team is winning convincingly → buy NO
    - No underlying asset drift check (score IS the signal)

PAPER ONLY:
    Initial deployment paper-only. Gate: 30+ paper bets + Brier < 0.30.
    First live test: April 7-8 UCL QF 1st legs (Arsenal/Bayern/PSG/BAR).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market

logger = logging.getLogger(__name__)

# ── Parameters ─────────────────────────────────────────────────────────────

_TRIGGER_PRICE_CENTS: float = 88.0        # enter when YES or NO >= 88c
_MAX_PRICE_CENTS: int = 93                 # ceiling: do not enter at 93c+ (fee floor + slippage)
_MAX_SECONDS_REMAINING: int = 5400        # 90 min: enter in last 90 min of game
_HARD_SKIP_SECONDS: int = 60             # skip final 60s (score can change in injury time)
_GAME_DURATION_ESTIMATE_SECS: int = 3 * 3600  # 3 hours from kickoff to expected_expiration

# FLB win probability premium (same as expiry_sniper)
_WIN_PROB_PREMIUM: float = 0.01  # 1pp above market price


def _get_expected_expiration(market: Market) -> Optional[datetime]:
    """
    Extract expected_expiration_time from market.raw.

    For KXUCLGAME markets, this is ~3 hours after kickoff (actual game end),
    NOT the close_time which is weeks later (safety buffer).
    Falls back to parsing close_time if raw field is unavailable.
    """
    raw_exp = market.raw.get("expected_expiration_time", "")
    if raw_exp:
        try:
            dt = datetime.fromisoformat(raw_exp.replace("Z", "+00:00"))
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass

    # Fallback: try close_time
    try:
        dt = datetime.fromisoformat(market.close_time.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


class SoccerSniperStrategy(BaseStrategy):
    """
    In-play FLB sniper for KXUCLGAME markets.

    Uses expected_expiration_time (actual game end) rather than close_time
    (safety buffer weeks away) for timing. No coin drift required — the
    market price itself signals which team is winning.
    """

    PAPER_CALIBRATION_USD: float = 0.50

    def __init__(
        self,
        trigger_price_cents: float = _TRIGGER_PRICE_CENTS,
        max_price_cents: int = _MAX_PRICE_CENTS,
        max_seconds_remaining: int = _MAX_SECONDS_REMAINING,
        hard_skip_seconds: int = _HARD_SKIP_SECONDS,
        game_duration_estimate_secs: int = _GAME_DURATION_ESTIMATE_SECS,
        name_override: Optional[str] = None,
    ):
        self._trigger_price_cents = trigger_price_cents
        self._max_price_cents = max_price_cents
        self._max_seconds_remaining = max_seconds_remaining
        self._hard_skip_seconds = hard_skip_seconds
        self._game_duration_estimate_secs = game_duration_estimate_secs
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "soccer_sniper_v1"

    def generate_signal(self, market: Market) -> Optional[Signal]:
        """
        Evaluate in-play FLB sniping conditions and return a Signal or None.

        Args:
            market: Current Kalshi KXUCLGAME market snapshot.

        Returns:
            Signal if ALL conditions are met, else None.
        """
        now_utc = datetime.now(timezone.utc)

        # ── 1. Get expected expiration (actual game end, not close_time) ──
        expected_exp = _get_expected_expiration(market)
        if expected_exp is None:
            logger.debug("[soccer_sniper] Cannot parse expiration for %s — skip", market.ticker)
            return None

        # ── 2. Check game is live (between estimated start and expected end) ──
        game_start_est = expected_exp.timestamp() - self._game_duration_estimate_secs
        now_ts = now_utc.timestamp()

        if now_ts < game_start_est:
            logger.debug(
                "[soccer_sniper] %s: game hasn't started yet (start ~%s)",
                market.ticker,
                datetime.fromtimestamp(game_start_est, tz=timezone.utc).strftime("%H:%M UTC"),
            )
            return None

        if now_ts >= expected_exp.timestamp():
            logger.debug("[soccer_sniper] %s: game already over — skip", market.ticker)
            return None

        # ── 3. Compute seconds remaining in game ──────────────────────────
        seconds_remaining = (expected_exp - now_utc).total_seconds()

        # ── 4. Time gate: only enter in last max_seconds_remaining ─────────
        if seconds_remaining > self._max_seconds_remaining:
            logger.debug(
                "[soccer_sniper] %s: %.0fs remaining > %ds gate — too early",
                market.ticker, seconds_remaining, self._max_seconds_remaining,
            )
            return None

        # ── 5. Hard skip: skip final seconds (score can change in injury time) ──
        if seconds_remaining <= self._hard_skip_seconds:
            logger.debug(
                "[soccer_sniper] %s: %.0fs remaining — hard skip (<=%ds)",
                market.ticker, seconds_remaining, self._hard_skip_seconds,
            )
            return None

        # ── 6. Determine which side is at trigger price ────────────────────
        yes_price = market.yes_price
        no_price = market.no_price

        if yes_price >= self._trigger_price_cents:
            # YES side at 88c+: team A is winning convincingly
            if yes_price >= self._max_price_cents:
                logger.debug(
                    "[soccer_sniper] %s: YES=%dc at or above ceiling %dc — skip",
                    market.ticker, yes_price, self._max_price_cents,
                )
                return None
            side = "yes"
            price_cents = yes_price
            win_prob = min(0.99, yes_price / 100.0 + _WIN_PROB_PREMIUM)

        elif no_price >= self._trigger_price_cents:
            # NO side at 88c+: team B is winning convincingly
            if no_price >= self._max_price_cents:
                logger.debug(
                    "[soccer_sniper] %s: NO=%dc at or above ceiling %dc — skip",
                    market.ticker, no_price, self._max_price_cents,
                )
                return None
            side = "no"
            price_cents = no_price
            win_prob = min(0.99, no_price / 100.0 + _WIN_PROB_PREMIUM)

        else:
            # Neither side at trigger — neutral zone
            logger.debug(
                "[soccer_sniper] %s: YES=%dc NO=%dc — neither at trigger %.0fc",
                market.ticker, yes_price, no_price, self._trigger_price_cents,
            )
            return None

        edge_pct = win_prob - (price_cents / 100.0)

        logger.info(
            "[soccer_sniper] SIGNAL %s: %s @%dc | %.0fs remain | edge=%.1f%%",
            market.ticker, side.upper(), price_cents,
            seconds_remaining, edge_pct * 100,
        )

        return Signal(
            side=side,
            price_cents=price_cents,
            edge_pct=edge_pct,
            win_prob=win_prob,
            confidence=win_prob,
            ticker=market.ticker,
            reason=(
                f"soccer_sniper FLB: {side.upper()}@{price_cents}c "
                f"{int(seconds_remaining)}s remain edge={edge_pct:.1%}"
            ),
        )


def make_soccer_sniper() -> SoccerSniperStrategy:
    """
    Return SoccerSniperStrategy configured for KXUCLGAME in-play FLB sniping.

    Paper-only until 30+ settled bets + Brier < 0.30.
    First test: UCL QF April 7-8, 2026.
    """
    return SoccerSniperStrategy(name_override="soccer_sniper_v1")
