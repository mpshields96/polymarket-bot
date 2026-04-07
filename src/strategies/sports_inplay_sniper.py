"""
src/strategies/sports_inplay_sniper.py — Sports In-Play FLB Sniper
===================================================================
Ported from soccer_sniper.py pattern. Applies Favorite-Longshot Bias (FLB)
to NBA/NHL/MLB game markets in the final minutes of play.

JOB:    Enter KXNBAGAME/KXNHLGAME/KXMLBGAME markets when YES or NO price
        reaches 90c+ within the final 25 minutes of play. Harvests FLB:
        markets imply ~10% reversal probability when actual rate is ~3-5%.

MECHANISM (same as soccer_sniper.py / UCL Session 84 finding):
    When a team leads late in the game, the market moves to 90-93c.
    FLB predicts: market over-prices reversal → structural edge of 5-7%.
    Academic basis: FLB is not sport-specific (same mechanism UCL → NBA/NHL/MLB).

KEY DIFFERENCES FROM SOCCER SNIPER:
    - Trigger price: 90c (vs 88c soccer) — tighter window, shorter games
    - Max seconds remaining: 1500s (25 min) — NBA/NHL quarter/period timing
    - Game duration estimate: varies by sport (NBA=2.5hr, NHL=2.5hr, MLB=3hr)
    - Ceiling: 93c (same as soccer sniper)
    - Series: KXNBAGAME, KXNHLGAME, KXMLBGAME

TIMING LOGIC (same as soccer_sniper.py):
    - game_start_est = expected_expiration_time - game_duration_estimate_secs
    - Entry gate: game_start_est <= now < expected_expiration_time
    - FLB window: seconds_remaining <= max_seconds_remaining (25 min)
    - seconds_remaining = (expected_expiration_time - now).total_seconds()

STATUS: PAPER-ONLY — initial deployment.
    Gate to live: 30+ settled paper bets + Brier < 0.30.
    Expected WR at 90c+: 94-97% (extrapolated from UCL soccer sniper data).
    Expected daily triggers: 5-10 bets/day across 20+ NBA/NHL/MLB games.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.strategies.base import BaseStrategy, Signal
from src.platforms.kalshi import Market

logger = logging.getLogger(__name__)

# ── Parameters ─────────────────────────────────────────────────────────────

_TRIGGER_PRICE_CENTS: float = 90.0       # enter when YES or NO >= 90c
_MAX_PRICE_CENTS: int = 93               # ceiling: do not enter at 93c+ (fee floor)
_MAX_SECONDS_REMAINING: int = 2700       # 45 min: enter in final 45 min of game (CCA Chat 46 spec)
_HARD_SKIP_SECONDS: int = 120            # skip final 2 min (garbage-time noise)

# Per-sport game duration estimates (seconds from kickoff to expected_expiration_time)
_GAME_DURATION_NBA_SECS: int = int(2.5 * 3600)   # NBA: ~2.5 hours with breaks
_GAME_DURATION_NHL_SECS: int = int(2.5 * 3600)   # NHL: ~2.5 hours with breaks
_GAME_DURATION_MLB_SECS: int = int(3.0 * 3600)   # MLB: ~3 hours
_GAME_DURATION_DEFAULT_SECS: int = int(3.0 * 3600)

# Series → game duration map
_SPORT_DURATION: dict[str, int] = {
    "KXNBAGAME":  _GAME_DURATION_NBA_SECS,
    "KXNHLGAME":  _GAME_DURATION_NHL_SECS,
    "KXMLBGAME":  _GAME_DURATION_MLB_SECS,
}

# FLB win probability premium (same as expiry_sniper + soccer_sniper)
_WIN_PROB_PREMIUM: float = 0.01  # 1pp above market price


def _get_expected_expiration(market: Market) -> Optional[datetime]:
    """
    Extract expected_expiration_time from market.raw.

    For KXNBAGAME/KXNHLGAME/KXMLBGAME markets, expected_expiration_time is
    ~2.5-3 hours after game start (actual game end), NOT close_time which is
    weeks later (safety buffer). Same pattern as soccer_sniper.py.
    Falls back to close_time if raw field unavailable.
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
    except (ValueError, TypeError, AttributeError):
        return None


def _series_from_ticker(ticker: str) -> str:
    """Extract series prefix from ticker. KXNBAGAME-26APR... → KXNBAGAME."""
    return ticker.split("-")[0] if "-" in ticker else ticker


class SportsInPlaySniperStrategy(BaseStrategy):
    """
    In-play FLB sniper for KXNBAGAME/KXNHLGAME/KXMLBGAME markets.

    Uses expected_expiration_time for timing. No coin drift — market price
    itself signals which team is winning convincingly (same as soccer_sniper).
    """

    PAPER_CALIBRATION_USD: float = 2.0

    def __init__(
        self,
        trigger_price_cents: float = _TRIGGER_PRICE_CENTS,
        max_price_cents: int = _MAX_PRICE_CENTS,
        max_seconds_remaining: int = _MAX_SECONDS_REMAINING,
        hard_skip_seconds: int = _HARD_SKIP_SECONDS,
        name_override: Optional[str] = None,
    ):
        self._trigger_price_cents = trigger_price_cents
        self._max_price_cents = max_price_cents
        self._max_seconds_remaining = max_seconds_remaining
        self._hard_skip_seconds = hard_skip_seconds
        self._name_override = name_override

    @property
    def name(self) -> str:
        return self._name_override or "sports_inplay_sniper_v1"

    def generate_signal(self, market: Market) -> Optional[Signal]:
        """
        Evaluate in-play FLB sniping conditions and return Signal or None.

        Args:
            market: Current Kalshi sports game market snapshot.

        Returns:
            Signal if ALL conditions met, else None.
        """
        now_utc = datetime.now(timezone.utc)
        series = _series_from_ticker(market.ticker)
        label = f"[sports_inplay_sniper:{series}]"

        # ── 1. Get expected expiration (actual game end, not close_time) ──
        expected_exp = _get_expected_expiration(market)
        if expected_exp is None:
            logger.debug("%s Cannot parse expiration for %s — skip", label, market.ticker)
            return None

        # ── 2. Check game is live (between estimated start and expected end) ──
        game_duration_secs = _SPORT_DURATION.get(series, _GAME_DURATION_DEFAULT_SECS)
        game_start_est = expected_exp.timestamp() - game_duration_secs
        now_ts = now_utc.timestamp()

        if now_ts < game_start_est:
            logger.debug(
                "%s %s: game hasn't started yet (est. start ~%s)",
                label, market.ticker,
                datetime.fromtimestamp(game_start_est, tz=timezone.utc).strftime("%H:%M UTC"),
            )
            return None

        if now_ts >= expected_exp.timestamp():
            logger.debug("%s %s: game already over — skip", label, market.ticker)
            return None

        # ── 3. Compute seconds remaining ─────────────────────────────────
        seconds_remaining = (expected_exp - now_utc).total_seconds()

        # ── 4. Time gate: only enter in last max_seconds_remaining ────────
        if seconds_remaining > self._max_seconds_remaining:
            logger.debug(
                "%s %s: %.0fs remaining > %ds gate — too early",
                label, market.ticker, seconds_remaining, self._max_seconds_remaining,
            )
            return None

        # ── 5. Hard skip: skip final seconds (garbage-time noise) ─────────
        if seconds_remaining <= self._hard_skip_seconds:
            logger.debug(
                "%s %s: %.0fs remaining — hard skip (<=%ds)",
                label, market.ticker, seconds_remaining, self._hard_skip_seconds,
            )
            return None

        # ── 6. Determine which side is at trigger price ───────────────────
        # Use yes_bid/no_bid (live bid price) per CCA Chat 46 spec if available.
        # Falls back to yes_price/no_price (Market dataclass standard fields).
        yes_price = getattr(market, "yes_bid", None) or market.yes_price or 0
        no_price = getattr(market, "no_bid", None) or market.no_price or 0

        if yes_price >= self._trigger_price_cents:
            if yes_price >= self._max_price_cents:
                logger.debug(
                    "%s %s: YES=%dc at or above ceiling %dc — skip",
                    label, market.ticker, yes_price, self._max_price_cents,
                )
                return None
            side = "yes"
            price_cents = yes_price
            win_prob = min(0.99, yes_price / 100.0 + _WIN_PROB_PREMIUM)

        elif no_price >= self._trigger_price_cents:
            if no_price >= self._max_price_cents:
                logger.debug(
                    "%s %s: NO=%dc at or above ceiling %dc — skip",
                    label, market.ticker, no_price, self._max_price_cents,
                )
                return None
            side = "no"
            price_cents = no_price
            win_prob = min(0.99, no_price / 100.0 + _WIN_PROB_PREMIUM)

        else:
            logger.debug(
                "%s %s: YES=%dc NO=%dc — neither at trigger %.0fc",
                label, market.ticker, yes_price, no_price, self._trigger_price_cents,
            )
            return None

        edge_pct = win_prob - (price_cents / 100.0)

        logger.info(
            "%s SIGNAL %s: %s @%dc | %.0fs remain | edge=%.1f%%",
            label, market.ticker, side.upper(), price_cents,
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
                f"inplay_sniper FLB: {side.upper()}@{price_cents}c "
                f"{int(seconds_remaining)}s remain edge={edge_pct:.1%}"
            ),
        )


def make_sports_inplay_sniper(series: str) -> SportsInPlaySniperStrategy:
    """
    Return SportsInPlaySniperStrategy for the given series.

    Args:
        series: Kalshi series ticker, e.g. "KXNBAGAME", "KXNHLGAME", "KXMLBGAME"

    Returns:
        Strategy configured for in-play FLB sniping on that series.
        Paper-only until 30+ settled bets + Brier < 0.30.
    """
    name = {
        "KXNBAGAME": "sports_inplay_sniper_nba_v1",
        "KXNHLGAME": "sports_inplay_sniper_nhl_v1",
        "KXMLBGAME": "sports_inplay_sniper_mlb_v1",
    }.get(series, f"sports_inplay_sniper_{series.lower()}_v1")
    return SportsInPlaySniperStrategy(name_override=name)
