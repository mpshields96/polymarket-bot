"""
Soccer Sniper Paper Execution — Calibration Mode

PURPOSE:
    Extends soccer_live_monitor with paper bet execution.
    Places paper bets when a mid-game 90c+ crossing is detected and
    the pre-game price was >= 0.60 (structural edge filter).

    Paper mode only. Live activation requires 3+ paper wins first.

USAGE:
    # EPL game on March 21:
    python scripts/soccer_sniper_paper.py --series KXEPLGAME --date 26MAR21

    # UCL QF 1st legs March 31:
    python scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR31

    # La Liga:
    python scripts/soccer_sniper_paper.py --series KXLALIGAGAME

ENTRY CRITERIA (all required):
    1. Pre-game price >= 0.60 for the team (structural edge filter)
    2. Price crosses 90c+ during the game (NOT pre-game certainty)
    3. Price must be <= 98c (99c fee-floor blocks profit)
    4. One bet per market per session

ACADEMIC BASIS:
    Favorite-longshot bias (Whelan 2025, Snowberg-Wolfers 2010).
    Teams leading 2-0+ at minute 60-70 are at 90c+ = market implies 10%
    reversal probability vs true ~3-5% reversal rate.
    La Liga: 7/16 = 44% MID_GAME rate. Teams at 46c+ pre-game: 6/7 = 86%.
    UCL: 4/10 = 40% MID_GAME rate.
    False positive (90c+ but team lost): 0/3 tested at UCL.

STRATEGY NAME: soccer_sniper_v1
CALIBRATION BET: 5.0 USD flat (same as drift calibration approach)
VALIDATION GATE: Live activation only after 3+ paper wins.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.db import DB, load_from_config
from src.execution.paper import PaperExecutor
from scripts.soccer_live_monitor import (
    PriceTracker,
    SNIPER_THRESHOLD,
    get_markets,
    get_live_games,
    ESPN_CONFIGS,
    setup_logging,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

SOCCER_SNIPER_BET_USD: float = 5.0      # Calibration bet size (USD)
PRE_GAME_THRESHOLD: float = 0.60        # Min pre-game YES price to qualify
STRATEGY_NAME: str = "soccer_sniper_v1"


# ── Paper execution logic ────────────────────────────────────────────────────

class SoccerSniperExec:
    """
    Receives crossing notifications from SoccerPaperTracker and executes
    paper bets when structural edge conditions are met.

    State:
        _bet_placed: set of tickers that have already received a paper bet
                     this session (prevents duplicate bets).
    """

    def __init__(
        self,
        paper_executor: PaperExecutor | None = None,
        strategy_name: str = STRATEGY_NAME,
        bet_usd: float = SOCCER_SNIPER_BET_USD,
        pregame_min: float = PRE_GAME_THRESHOLD,
    ) -> None:
        self._paper_exec = paper_executor
        self._strategy_name = strategy_name
        self._bet_usd = bet_usd
        self._pregame_min = pregame_min
        self._bet_placed: set[str] = set()
        self._lock = threading.Lock()

    def on_crossing(
        self,
        ticker: str,
        price_cents: int,
        state: str,
        pregame_price: float,
    ) -> None:
        """
        Called when a market first crosses 90c+.

        Args:
            ticker:       Kalshi market ticker.
            price_cents:  Execution price in cents (int, e.g. 92).
            state:        Game state string (e.g. 'Arsenal 2-0 Lev | 67:00 | lead=+2').
            pregame_price: The tracked pre-game YES bid price (0.0-1.0).
        """
        with self._lock:
            # Guard: skip pre-game crossings (market was already at 90c before kickoff)
            if "PRE-GAME" in state:
                logger.debug(f"[soccer_sniper] {ticker} — skip (PRE-GAME crossing)")
                return

            # Guard: fee-floor (99c gives 1c gross profit = near-zero net)
            if price_cents >= 99 or price_cents <= 1:
                logger.debug(f"[soccer_sniper] {ticker} — skip (fee-floor {price_cents}c)")
                return

            # Guard: pre-game structural edge filter
            if pregame_price < self._pregame_min:
                logger.info(
                    f"[soccer_sniper] {ticker} — skip "
                    f"(pre-game {pregame_price:.0%} < threshold {self._pregame_min:.0%})"
                )
                return

            # Guard: one bet per market per session
            if ticker in self._bet_placed:
                logger.debug(f"[soccer_sniper] {ticker} — skip (already bet this session)")
                return

            # All guards passed — place paper bet
            self._bet_placed.add(ticker)
            logger.warning(
                f"[soccer_sniper] *** PAPER BET: {ticker} YES@{price_cents}c "
                f"| pre-game {pregame_price:.0%} | {state[:60]} ***"
            )

            if self._paper_exec is not None:
                try:
                    self._paper_exec.execute(
                        ticker=ticker,
                        side="yes",
                        price_cents=price_cents,
                        size_usd=self._bet_usd,
                    )
                    logger.info(f"[soccer_sniper] Paper bet placed: {ticker} YES@{price_cents}c {self._bet_usd} USD")
                except Exception as e:
                    logger.error(f"[soccer_sniper] Paper bet FAILED for {ticker}: {e}")
                    # Remove from bet_placed so it can retry
                    self._bet_placed.discard(ticker)
            else:
                logger.info(f"[soccer_sniper] [DRY RUN] Would bet {ticker} YES@{price_cents}c {self._bet_usd} USD")

    def session_reset(self) -> None:
        """Clear bet history for a new monitoring session."""
        with self._lock:
            self._bet_placed.clear()
        logger.info("[soccer_sniper] Session reset — bet history cleared")


# ── Extended tracker with paper execution ────────────────────────────────────

class SoccerPaperTracker(PriceTracker):
    """
    Extends PriceTracker with:
    1. Pre-game price tracking (needed for threshold filter)
    2. First-crossing detection that calls SoccerSniperExec
    """

    def __init__(
        self,
        label: str,
        sniper_exec: SoccerSniperExec | None = None,
        csv_path: str | None = None,
    ) -> None:
        super().__init__(label=label, csv_path=csv_path)
        self._sniper_exec = sniper_exec
        self._pregame_prices: dict[str, float] = {}   # ticker → last pre-game price
        self._crossing_fired: set[str] = set()        # tickers where we've fired exec

    def get_pregame_price(self, ticker: str) -> float:
        """Return the tracked pre-game price for a ticker (0.0 if unknown)."""
        return self._pregame_prices.get(ticker, 0.0)

    def observe(self, ticker: str, mid: float, state: str) -> None:
        """
        Override parent observe() to:
        1. Track pre-game prices
        2. Fire sniper_exec on first mid-game 90c+ crossing
        """
        # Track pre-game prices (before any crossing fires)
        if "PRE-GAME" in state and mid > 0:
            self._pregame_prices[ticker] = mid

        # Check if this is a new 90c+ crossing (ticker NOT already in parent _crossings)
        was_above = ticker in self._crossings  # parent tracks this
        is_above = mid >= SNIPER_THRESHOLD

        # Call parent's observe() for all logging/CSV/crossing tracking
        super().observe(ticker, mid, state)

        # After parent updates, detect first crossing
        now_in_crossings = ticker in self._crossings
        is_new_crossing = (not was_above) and is_above and now_in_crossings

        is_ingame_crossing = is_new_crossing and "PRE-GAME" not in state

        if is_ingame_crossing and ticker not in self._crossing_fired:
            self._crossing_fired.add(ticker)
            if self._sniper_exec is not None:
                self._sniper_exec.on_crossing(
                    ticker=ticker,
                    price_cents=int(round(mid * 100)),
                    state=state,
                    pregame_price=self._pregame_prices.get(ticker, 0.0),
                )

        # Reset crossing_fired if price drops back below threshold (market recovered)
        if not is_above and ticker in self._crossing_fired:
            self._crossing_fired.discard(ticker)


# ── Main runner ──────────────────────────────────────────────────────────────

def run_paper(series: str, date_filter: str | None, poll_sec: int) -> None:
    """Run soccer sniper paper monitoring for a given series."""
    import time as time_module
    from datetime import datetime, timezone

    espn_url = ESPN_CONFIGS.get(series, {}).get("url", "")
    csv_path = f"/tmp/soccer_sniper_paper_{series}.csv"

    # Set up paper executor
    db = load_from_config()
    paper_exec = PaperExecutor(db=db, strategy_name=STRATEGY_NAME)
    sniper_exec = SoccerSniperExec(paper_executor=paper_exec)
    tracker = SoccerPaperTracker(label=series, sniper_exec=sniper_exec, csv_path=csv_path)

    logger.info(
        f"[soccer_sniper] Starting paper monitor: {series} "
        f"| pre-game threshold={PRE_GAME_THRESHOLD:.0%} "
        f"| bet size={SOCCER_SNIPER_BET_USD} USD"
    )

    cycle = 0
    while True:
        cycle += 1
        now = datetime.now(timezone.utc).strftime("%H:%M UTC")

        games = get_live_games(espn_url) if espn_url else []
        markets = get_markets(series, date_filter)
        live = [g for g in games if g["state"] == "STATUS_IN_PROGRESS"]

        if not live:
            if cycle % 5 == 1:
                logger.info(f"[{now}] No live games | {series} markets={len(markets)}")
                for code, m in sorted(markets.items(), key=lambda x: -x[1]["volume"]):
                    if m["mid"] > 0:
                        tracker.observe(m["ticker"], m["mid"], f"PRE-GAME vol={int(m['volume'])}")
        else:
            for g in live:
                lead = g["home_score"] - g["away_score"]
                state = (
                    f"{g['home_name']} {g['home_score']}-{g['away_score']} "
                    f"{g['away_name']} | {g['detail']}"
                )
                logger.info(f"[{now}] LIVE: {state}")
                for code, side_lead in [
                    (g["home_k"], lead), (g["away_k"], -lead), ("TIE", 0)
                ]:
                    if not code or code not in markets:
                        continue
                    m = markets[code]
                    if m["mid"] > 0:
                        tracker.observe(m["ticker"], m["mid"], f"{state} | lead={side_lead:+d}")

        if cycle % 10 == 0:
            logger.info(tracker.summary())
        time_module.sleep(poll_sec)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Soccer Sniper Paper Monitor — calibration mode"
    )
    parser.add_argument(
        "--series",
        default="KXUCLGAME",
        choices=["KXUCLGAME", "KXEPLGAME", "KXLALIGAGAME", "KXSERIEAGAME"],
        help="Kalshi soccer series ticker",
    )
    parser.add_argument(
        "--date",
        help="Filter markets by date code (e.g. 26MAR31)",
    )
    parser.add_argument(
        "--poll",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)",
    )
    args = parser.parse_args()

    setup_logging(f"soccer_sniper_{args.series}")
    run_paper(series=args.series, date_filter=args.date, poll_sec=args.poll)


if __name__ == "__main__":
    main()
