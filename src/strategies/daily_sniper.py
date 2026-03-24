"""
DailySniper — KXBTCD near-expiry paper sniping strategy (factory).

JOB:    Wrap ExpirySniperStrategy with parameters tuned for KXBTCD daily
        threshold markets: 90-minute entry window, same FLB logic as 15M sniper.

ACADEMIC BASIS:
    Favorite-longshot bias (same as expiry_sniper_v1 / Snowberg & Wolfers):
    Near-certain binary outcomes are systematically underpriced near settlement.
    KXBTCD YES@92c near expiry = "8% chance BTC falls significantly in 90min".
    FLB predicts actual win rate > 92c market price.

PAPER ONLY:
    CCA REQ-026 validation pending (academic basis for 90-min threshold markets).
    Paper data collection starts immediately. WR gate = 30+ bets before live eval.

KEY DIFFERENCES FROM expiry_sniper_v1:
    - max_seconds_remaining: 5400s (90 min) vs 840s (14 min for 15M)
    - hard_skip_seconds: 30s vs 5s (CF Benchmarks settlement timing less precise)
    - series: KXBTCD only (daily threshold). 15M sniper covers KXBTC15M/KXETH15M/KXSOL15M.
    - ceiling: 94c max price enforced in loop (same as live sniper ceiling).

DRIFT REFERENCE:
    Uses session_open (asset price at midnight UTC) as the drift reference point.
    Same approach as crypto_daily_loop. "Coin moved up today" → YES at 92c is valid.
"""
from __future__ import annotations

from src.strategies.expiry_sniper import ExpirySniperStrategy

# ── Parameters ──────────────────────────────────────────────────────────────

_DAILY_SNIPER_MAX_SECONDS = 5400        # 90-minute entry window
_DAILY_SNIPER_HARD_SKIP_SECONDS = 30   # 30s hard skip (CF Benchmarks settlement imprecision)
_DAILY_SNIPER_MAX_PRICE_CENTS = 94      # ceiling matches live sniper ceiling (S130)


def make_daily_sniper() -> ExpirySniperStrategy:
    """
    Return ExpirySniperStrategy configured for KXBTCD daily threshold markets.

    NOTE: Price ceiling at 94c is NOT enforced here — it is enforced in the
    daily_sniper_loop before calling generate_signal(). This keeps the strategy
    class stateless and reusable with different ceiling values if needed later.
    """
    return ExpirySniperStrategy(
        max_seconds_remaining=_DAILY_SNIPER_MAX_SECONDS,
        hard_skip_seconds=_DAILY_SNIPER_HARD_SKIP_SECONDS,
        name_override="daily_sniper_v1",
    )


# Exported constant so the loop can import it without magic numbers
DAILY_SNIPER_MAX_PRICE_CENTS: int = _DAILY_SNIPER_MAX_PRICE_CENTS
