"""
src/strategies/sports_math.py — Pure Sports Betting Math
=========================================================
Ported from agentic-rd-sandbox/core/math_engine.py (S165, 2026-04-06).
Zero external dependencies. Zero I/O. Fully testable in isolation.

Provides:
  - implied_probability()        American odds → raw implied prob
  - no_vig_probability()         Remove vig from 2-way market
  - no_vig_probability_3way()    Remove vig from 3-way market (soccer)
  - passes_collar()              Standard -180 to +150 collar
  - passes_collar_soccer()       Expanded -250 to +400 collar (soccer h2h)
  - assign_grade()               A/B/C grade tiers by edge%
  - nba_kill_switch()            NBA situational kill (rest disadvantage, B2B)
  - nhl_kill_switch()            NHL goalie kill (backup goalie)

Usage:
  from src.strategies.sports_math import (
      implied_probability, no_vig_probability, passes_collar,
      passes_collar_soccer, assign_grade, nba_kill_switch, nhl_kill_switch,
  )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Constants (ported from math_engine.py)
# ---------------------------------------------------------------------------

COLLAR_MIN: int = -180          # Maximum favourite odds allowed (standard)
COLLAR_MAX: int = 150           # Maximum underdog odds allowed (standard)
COLLAR_MIN_SOCCER: int = -250   # Expanded for soccer h2h (heavy favourites)
COLLAR_MAX_SOCCER: int = 400    # Expanded for soccer h2h (heavy dogs/draws)

MIN_EDGE: float = 0.035         # Grade A threshold (≥3.5% edge)
GRADE_B_MIN_EDGE: float = 0.015 # Grade B threshold (≥1.5% edge)
GRADE_C_MIN_EDGE: float = 0.005 # Grade C threshold (≥0.5% edge)

KELLY_FRACTION: float = 0.25    # Full Kelly fraction
KELLY_FRACTION_B: float = 0.12  # Grade B Kelly fraction
KELLY_FRACTION_C: float = 0.05  # Grade C Kelly fraction

SHARP_SCORE_MIN: float = 35.0   # Minimum sharp score to place any bet (Chat 45)


# ---------------------------------------------------------------------------
# Implied probability
# ---------------------------------------------------------------------------

def implied_probability(american_odds: int) -> float:
    """
    Convert American odds to raw (vig-inclusive) implied probability.

    >>> round(implied_probability(-110), 4)
    0.5238
    >>> round(implied_probability(110), 4)
    0.4762
    >>> round(implied_probability(-180), 4)
    0.6429
    """
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        return 100 / (american_odds + 100)


# ---------------------------------------------------------------------------
# No-vig probability
# ---------------------------------------------------------------------------

def no_vig_probability(odds_a: int, odds_b: int) -> tuple[float, float]:
    """
    Remove vig from a two-outcome market. Returns (fair_a, fair_b).

    >>> a, b = no_vig_probability(-110, -110)
    >>> round(a, 4), round(b, 4)
    (0.5, 0.5)
    >>> round(a + b, 6)
    1.0
    """
    raw_a = implied_probability(odds_a)
    raw_b = implied_probability(odds_b)
    overround = raw_a + raw_b
    if overround == 0:
        raise ZeroDivisionError("Overround is zero — invalid odds pair")
    return raw_a / overround, raw_b / overround


def no_vig_probability_3way(
    odds_a: int,
    odds_b: int,
    odds_c: int,
) -> tuple[float, float, float]:
    """
    Remove vig from a 3-outcome market (soccer home/away/draw).

    >>> a, b, c = no_vig_probability_3way(-105, 290, 250)
    >>> round(a + b + c, 4)
    1.0
    >>> a > b
    True
    """
    p_a = implied_probability(odds_a)
    p_b = implied_probability(odds_b)
    p_c = implied_probability(odds_c)
    total = p_a + p_b + p_c
    if total <= 0:
        raise ValueError(f"Total implied probability non-positive: {total}")
    return p_a / total, p_b / total, p_c / total


# ---------------------------------------------------------------------------
# Collar checks
# ---------------------------------------------------------------------------

def passes_collar(american_odds: int) -> bool:
    """
    Return True if odds are within the standard -180 to +150 collar.
    Rejects heavy favourites and extreme underdogs.

    >>> passes_collar(-110)
    True
    >>> passes_collar(-200)
    False
    >>> passes_collar(150)
    True
    >>> passes_collar(155)
    False
    """
    return COLLAR_MIN <= american_odds <= COLLAR_MAX


def passes_collar_soccer(american_odds: int) -> bool:
    """
    Expanded collar for soccer 3-way h2h markets (-250 to +400).
    Soccer dogs and draws commonly price at +200 to +400.

    >>> passes_collar_soccer(-110)
    True
    >>> passes_collar_soccer(-250)
    True
    >>> passes_collar_soccer(-260)
    False
    >>> passes_collar_soccer(400)
    True
    >>> passes_collar_soccer(401)
    False
    """
    return COLLAR_MIN_SOCCER <= american_odds <= COLLAR_MAX_SOCCER


# ---------------------------------------------------------------------------
# Grade assignment
# ---------------------------------------------------------------------------

def assign_grade(edge_pct: float) -> str:
    """
    Return confidence grade string based on edge percentage.

    Grade thresholds:
        A  (≥3.5%)  → Full Kelly. Standard production bet.
        B  (≥1.5%)  → Half Kelly. Reduced stake.
        C  (≥0.5%)  → Minimal stake. Data collection only.
        NEAR_MISS   → Never stake (display only).

    >>> assign_grade(0.05)
    'A'
    >>> assign_grade(0.02)
    'B'
    >>> assign_grade(0.008)
    'C'
    >>> assign_grade(0.001)
    'NEAR_MISS'
    """
    if edge_pct >= MIN_EDGE:
        return "A"
    elif edge_pct >= GRADE_B_MIN_EDGE:
        return "B"
    elif edge_pct >= GRADE_C_MIN_EDGE:
        return "C"
    else:
        return "NEAR_MISS"


def sharp_score_for_bet(
    edge_pct: float,
    efficiency_gap: float = 8.0,
    rlm_confirmed: bool = False,
) -> float:
    """
    Compute Sharp Score (0-100) for a single bet candidate.

    Simplified wrapper used in the bot's signal path — no RLM detection yet,
    so rlm_confirmed defaults to False (RLM worth 25 pts when available).

    Components (from calculate_sharp_score):
        EDGE (40 pts):        (edge% / 10%) × 40, capped at 40
        RLM  (25 pts):        0 (disabled — not detected in current stack)
        EFFICIENCY (20 pts):  caller-provided 0-20 scaled gap
        SITUATIONAL (15 pts): 0 (rest/injury not yet wired)

    Without RLM, maximum is 60 pts (edge=40 + efficiency=20).
    Threshold: SHARP_SCORE_MIN=35 — bets below this are skipped.

    At min_edge_pct=5%: edge_pts=20. Need efficiency_gap≥15 to pass 35.
    At 8% edge: edge_pts=32. Passes 35 with eff_gap≥3.

    >>> round(sharp_score_for_bet(0.08, efficiency_gap=12.0), 1)
    44.0
    >>> round(sharp_score_for_bet(0.06, efficiency_gap=10.0), 1)
    34.0
    >>> round(sharp_score_for_bet(0.05, efficiency_gap=15.0), 1)
    35.0
    """
    edge_pts = min(40.0, (edge_pct / 0.10) * 40)
    rlm_pts = 25.0 if rlm_confirmed else 0.0
    eff_pts = max(0.0, min(20.0, efficiency_gap))
    return round(edge_pts + rlm_pts + eff_pts, 1)


# ---------------------------------------------------------------------------
# Kill switches
# ---------------------------------------------------------------------------

def nba_kill_switch(
    rest_disadvantage: bool,
    spread: float,
    b2b: bool = False,
    is_road_b2b: bool = False,
) -> tuple[bool, str]:
    """
    NBA kill switch for situational risk factors.

    Fires (killed=True) when:
    - rest_disadvantage AND spread inside ±4 pts

    Flags (killed=False, non-empty reason) when:
    - is_road_b2b: road team on B2B — advisory, still requires 8%+ edge
    - b2b (home): reduce sizing

    >>> nba_kill_switch(True, -3.5)
    (True, 'KILL: Rest disadvantage with spread inside -4 — skip spread bet')
    >>> nba_kill_switch(False, -8.5)
    (False, '')
    >>> nba_kill_switch(False, 0.0, b2b=True, is_road_b2b=True)
    (False, 'FLAG: Road B2B — require 8%+ edge (travel + fatigue compound)')
    >>> nba_kill_switch(False, 0.0, b2b=True)
    (False, 'FLAG: Home B2B — reduce sizing')
    """
    if rest_disadvantage and abs(spread) < 4:
        return True, "KILL: Rest disadvantage with spread inside -4 — skip spread bet"
    if b2b:
        if is_road_b2b:
            return False, "FLAG: Road B2B — require 8%+ edge (travel + fatigue compound)"
        return False, "FLAG: Home B2B — reduce sizing"
    return False, ""


def nhl_kill_switch(
    backup_goalie: bool,
    b2b: bool = False,
    goalie_confirmed: bool = True,
) -> tuple[bool, str]:
    """
    NHL kill switch. Primary trigger: backup goalie.

    >>> nhl_kill_switch(True)
    (True, 'KILL: Backup goalie confirmed — skip NHL bet')
    >>> nhl_kill_switch(False, b2b=True)
    (False, 'FLAG: B2B — reduce sizing')
    >>> nhl_kill_switch(False, goalie_confirmed=False)
    (False, 'FLAG: Goalie not yet confirmed — require 8%+ edge')
    >>> nhl_kill_switch(False)
    (False, '')
    """
    if backup_goalie:
        return True, "KILL: Backup goalie confirmed — skip NHL bet"
    if b2b:
        return False, "FLAG: B2B — reduce sizing"
    if not goalie_confirmed:
        return False, "FLAG: Goalie not yet confirmed — require 8%+ edge"
    return False, ""


# ---------------------------------------------------------------------------
# American odds conversion helper
# ---------------------------------------------------------------------------

def american_odds_from_prob(prob: float) -> int:
    """
    Convert win probability to American odds (approximate).

    >>> american_odds_from_prob(0.55)
    -122
    >>> american_odds_from_prob(0.45)
    122
    """
    if prob <= 0 or prob >= 1:
        raise ValueError(f"Probability must be between 0 and 1, got {prob}")
    if prob >= 0.5:
        return round(-prob / (1 - prob) * 100)
    else:
        return round((1 - prob) / prob * 100)
