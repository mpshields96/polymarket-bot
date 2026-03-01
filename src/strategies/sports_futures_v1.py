"""
Sports futures mispricing strategy for Polymarket.us.

JOB:    Compare Polymarket.us season-winner futures prices to Odds API sharp
        consensus (Pinnacle / DraftKings) and signal when edge > min_edge_pct.

DOES NOT: Execute trades, know about sizing, risk decisions, or API calls.
          Signal generation only — all I/O done before calling scan_for_signals().

Supported markets (as of 2026-03):
  - NBA Championship Winner (basketball_nba_championship_winner)
  - NHL Stanley Cup Champion  (icehockey_nhl_championship_winner)
  - NCAA Tournament Winner    (basketball_ncaab_championship_winner)

Signal logic:
  BUY YES if pm_price < odds_prob - min_edge_pct  (market underpriced)
  BUY NO  if pm_price > odds_prob + min_edge_pct  (market overpriced)

Team name matching: normalize_team_name() strips city prefix to get canonical
short name ("Oklahoma City Thunder" → "thunder") for fuzzy cross-platform matching.

Paper-only until POST /v1/orders format is confirmed.
"""

from __future__ import annotations

import logging
from typing import List

from src.data.odds_api import ChampionshipOdds
from src.platforms.polymarket import PolymarketMarket
from src.strategies.base import Signal

logger = logging.getLogger(__name__)

# Known two-word city/metro prefixes in NBA, NHL, NCAAB
_MULTI_WORD_CITIES = {
    "golden state", "new orleans", "new york", "oklahoma city",
    "san antonio", "los angeles", "las vegas", "salt lake",
    "tampa bay", "kansas city", "san francisco", "san jose",
    "st. louis", "st louis", "new england", "new jersey",
}


def normalize_team_name(name: str) -> str:
    """
    Strip city/state prefix from a team name and return lowercase nickname.

    Examples:
      "Oklahoma City Thunder"  → "thunder"
      "Portland Trail Blazers" → "trail blazers"
      "Boston Celtics"         → "celtics"
      "Thunder"                → "thunder"
      "Philadelphia 76ers"     → "76ers"
      "76ers"                  → "76ers"
    """
    name_lower = name.strip().lower()

    # Check known two-word city prefixes first
    for prefix in _MULTI_WORD_CITIES:
        if name_lower.startswith(prefix + " "):
            return name_lower[len(prefix):].strip()

    # Strip single first word (single-word city like "Boston", "Denver", etc.)
    words = name_lower.split()
    if len(words) > 1:
        return " ".join(words[1:])

    return name_lower


class SportsFuturesStrategy:
    """
    Compare Polymarket.us futures prices to sharp bookmaker consensus.

    Signals when the gap between PM implied probability and Odds API
    consensus exceeds min_edge_pct (default 5%).

    Paper-only until POST /v1/orders protobuf format is confirmed.
    """

    def __init__(self, min_edge_pct: float = 0.05):
        self._min_edge_pct = min_edge_pct

    @property
    def name(self) -> str:
        return "sports_futures_v1"

    def scan_for_signals(
        self,
        pm_markets: List[PolymarketMarket],
        odds: List[ChampionshipOdds],
    ) -> List[Signal]:
        """
        Compare PM futures prices to Odds API consensus and emit signals.

        Args:
            pm_markets: Open Polymarket.us futures markets (from PolymarketClient.get_markets)
            odds:       Championship odds from OddsAPIFeed.get_nba/nhl/ncaab_championship

        Returns:
            List of Signal objects (may be empty). Never raises.
        """
        # Build lookup: normalized_name → ChampionshipOdds
        odds_by_name: dict[str, ChampionshipOdds] = {
            normalize_team_name(o.team_name): o for o in odds
        }

        signals: List[Signal] = []
        for market in pm_markets:
            if market.closed or not market.active:
                continue

            # Polymarket.us futures markets use "title" for the short team name (e.g. "Thunder")
            team_title = market.raw.get("title", "") or market.question
            normalized = normalize_team_name(team_title)

            o = odds_by_name.get(normalized)
            if o is None:
                logger.debug(
                    "[sports_futures] No odds match for PM market %r (normalized=%r)",
                    team_title, normalized,
                )
                continue

            pm_price = market.yes_price
            odds_prob = o.implied_prob
            edge = odds_prob - pm_price

            if edge >= self._min_edge_pct:
                # PM is underpriced → BUY YES
                try:
                    signals.append(Signal(
                        side="yes",
                        edge_pct=round(edge, 4),
                        win_prob=odds_prob,
                        confidence=min(o.num_books / 3.0, 1.0),
                        ticker=market.yes_identifier,
                        price_cents=market.yes_price_cents,
                        reason=(
                            f"{team_title}: PM {pm_price:.3f} vs odds {odds_prob:.3f} "
                            f"({edge:.1%} YES edge, {o.num_books} books)"
                        ),
                    ))
                    logger.info(
                        "[sports_futures] YES signal: %s PM=%.3f odds=%.3f edge=%.1%%",
                        team_title, pm_price, odds_prob, edge * 100,
                    )
                except ValueError as exc:
                    logger.warning("[sports_futures] Invalid YES signal for %s: %s", team_title, exc)

            elif (-edge) >= self._min_edge_pct:
                # PM is overpriced → BUY NO
                no_edge = pm_price - odds_prob
                try:
                    signals.append(Signal(
                        side="no",
                        edge_pct=round(no_edge, 4),
                        win_prob=1.0 - odds_prob,
                        confidence=min(o.num_books / 3.0, 1.0),
                        ticker=market.no_identifier,
                        price_cents=market.no_price_cents,
                        reason=(
                            f"{team_title}: PM {pm_price:.3f} vs odds {odds_prob:.3f} "
                            f"({no_edge:.1%} NO edge, {o.num_books} books)"
                        ),
                    ))
                    logger.info(
                        "[sports_futures] NO signal: %s PM=%.3f odds=%.3f edge=%.1%%",
                        team_title, pm_price, odds_prob, no_edge * 100,
                    )
                except ValueError as exc:
                    logger.warning("[sports_futures] Invalid NO signal for %s: %s", team_title, exc)

        return signals
