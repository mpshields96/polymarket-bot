"""
src/strategies/sports_math.py — Pure Sports Betting Math
=========================================================
Ported from agentic-rd-sandbox/core/math_engine.py (S165, 2026-04-06).
Injury leverage added from agentic-rd-sandbox/core/injury_data.py (Chat 39).
Zero external dependencies. Zero I/O. Fully testable in isolation.

Provides:
  - implied_probability()              American odds → raw implied prob
  - no_vig_probability()               Remove vig from 2-way market
  - no_vig_probability_3way()          Remove vig from 3-way market (soccer)
  - passes_collar()                    Standard -180 to +150 collar
  - passes_collar_soccer()             Expanded -250 to +400 collar (soccer h2h)
  - assign_grade()                     A/B/C grade tiers by edge%
  - nba_kill_switch()                  NBA situational kill (rest disadvantage, B2B)
  - nhl_kill_switch()                  NHL goalie kill (backup goalie)
  - get_positional_leverage()          (sport, position) → (leverage_pts, is_pivotal)
  - evaluate_injury_impact()           Full injury report for a bet
  - injury_kill_switch()               Convenience wrapper → (should_kill, reason)
  - situational_score_from_injuries()  List[InjuryReport] → 0-15 SITUATIONAL pts
  - sharp_score_for_bet()              Full Sharp Score with SITUATIONAL component

Usage:
  from src.strategies.sports_math import (
      implied_probability, no_vig_probability, passes_collar,
      passes_collar_soccer, assign_grade, nba_kill_switch, nhl_kill_switch,
      evaluate_injury_impact, injury_kill_switch, situational_score_from_injuries,
      sharp_score_for_bet, InjuryReport,
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
    injury_reports: Optional[list] = None,
) -> float:
    """
    Compute Sharp Score (0-100) for a single bet candidate.

    Simplified wrapper used in the bot's signal path — no RLM detection yet,
    so rlm_confirmed defaults to False (RLM worth 25 pts when available).

    Components (from calculate_sharp_score):
        EDGE (40 pts):        (edge% / 10%) × 40, capped at 40
        RLM  (25 pts):        0 (disabled — not detected in current stack)
        EFFICIENCY (20 pts):  caller-provided 0-20 scaled gap
        SITUATIONAL (15 pts): from injury_reports if provided, else 0

    Without RLM + no injuries, maximum is 60 pts (edge=40 + efficiency=20).
    With opponent injuries (max situational=15), maximum is 75 pts.
    Threshold: SHARP_SCORE_MIN=35 — bets below this are skipped.

    At min_edge_pct=5%: edge_pts=20. Need efficiency_gap≥15 to pass 35.
    At 8% edge: edge_pts=32. Passes 35 with eff_gap≥3.

    >>> round(sharp_score_for_bet(0.08, efficiency_gap=12.0), 1)
    44.0
    >>> round(sharp_score_for_bet(0.06, efficiency_gap=10.0), 1)
    34.0
    >>> round(sharp_score_for_bet(0.05, efficiency_gap=15.0), 1)
    35.0
    >>> round(sharp_score_for_bet(0.05, efficiency_gap=10.0, injury_reports=[]), 1)
    30.0
    """
    edge_pts = min(40.0, (edge_pct / 0.10) * 40)
    rlm_pts = 25.0 if rlm_confirmed else 0.0
    eff_pts = max(0.0, min(20.0, efficiency_gap))
    sit_pts = situational_score_from_injuries(injury_reports) if injury_reports is not None else 0.0
    return round(edge_pts + rlm_pts + eff_pts + sit_pts, 1)


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


# ---------------------------------------------------------------------------
# Injury leverage (ported from agentic-rd-sandbox/core/injury_data.py, Chat 39)
# ---------------------------------------------------------------------------

LEVERAGE_KILL_THRESHOLD: float = 3.5   # flag and kill bet if starter absence shifts line >= this
LEVERAGE_FLAG_THRESHOLD: float = 2.0   # soft flag (advisory only) at this threshold

# Format: sport → {position_code: (leverage_pts, is_pivotal)}
# leverage_pts: expected point-spread shift on confirmed starter absence
# is_pivotal: True if position is franchise-level (e.g. QB in NFL, G in NHL)
_POSITIONAL_LEVERAGE: dict[str, dict[str, tuple[float, bool]]] = {
    "NBA": {
        "PG":  (3.0, True),
        "SG":  (2.0, False),
        "SF":  (2.5, True),
        "PF":  (2.0, False),
        "C":   (2.5, True),
        "G":   (2.0, False),
        "F":   (2.0, False),
        "F-G": (2.0, False),
        "G-F": (2.0, False),
        "C-F": (2.5, True),
    },
    "NFL": {
        "QB":  (4.5, True),
        "RB":  (1.5, False),
        "WR":  (1.5, False),
        "TE":  (1.5, False),
        "OL":  (0.5, False),
        "DL":  (1.0, False),
        "DE":  (1.0, False),
        "LB":  (1.0, False),
        "CB":  (1.5, False),
        "S":   (1.0, False),
        "K":   (0.5, False),
        "P":   (0.2, False),
    },
    "NHL": {
        "G":   (3.5, True),
        "C":   (2.0, True),
        "LW":  (1.5, False),
        "RW":  (1.5, False),
        "D":   (1.5, False),
        "F":   (1.5, False),
    },
    "MLB": {
        "SP":  (2.0, True),
        "RP":  (0.5, False),
        "CL":  (0.5, False),
        "C":   (0.5, False),
        "1B":  (0.5, False),
        "2B":  (0.5, False),
        "3B":  (0.7, False),
        "SS":  (0.8, False),
        "OF":  (0.7, False),
        "DH":  (0.7, False),
    },
    "SOCCER": {
        "GK":  (1.5, True),
        "CB":  (0.8, False),
        "LB":  (0.5, False),
        "RB":  (0.5, False),
        "CDM": (0.8, False),
        "CM":  (0.8, False),
        "CAM": (1.0, False),
        "LW":  (0.8, False),
        "RW":  (0.8, False),
        "ST":  (1.2, True),
        "CF":  (1.2, True),
        "FW":  (1.0, False),
        "MF":  (0.7, False),
        "DF":  (0.7, False),
    },
}

# Sport name aliases for normalisation
_SPORT_ALIASES: dict[str, str] = {
    "nba": "NBA",
    "nfl": "NFL",
    "nhl": "NHL",
    "mlb": "MLB",
    "soccer": "SOCCER",
    "ncaab": "NBA",   # use NBA leverage for college basketball
    "ncaaf": "NFL",   # use NFL leverage for college football
}

# Side multipliers: injury direction vs bet direction
_SIDE_MULTIPLIER: dict[str, float] = {
    "home_bet_home_injury": -1.0,  # betting home, home player out → hurts
    "home_bet_away_injury": +0.5,  # betting home, away player out → mild edge
    "away_bet_away_injury": -1.0,  # betting away, away player out → hurts
    "away_bet_home_injury": +0.5,  # betting away, home player out → mild edge
    "total_injury": -0.3,          # totals: absence reduces scoring
}


@dataclass
class InjuryReport:
    """Result of evaluate_injury_impact()."""
    leverage_pts: float
    signed_impact: float
    flag: bool
    kill: bool
    advisory: str
    position: str
    sport: str


def get_positional_leverage(sport: str, position: str) -> tuple[float, bool]:
    """
    Return (leverage_pts, is_pivotal) for a given sport + position.

    Returns (0.0, False) for unknown sport/position combinations.

    >>> get_positional_leverage("NBA", "PG")
    (3.0, True)
    >>> get_positional_leverage("NFL", "QB")
    (4.5, True)
    >>> get_positional_leverage("NHL", "G")
    (3.5, True)
    >>> get_positional_leverage("MLB", "SP")
    (2.0, True)
    >>> get_positional_leverage("NBA", "UNKNOWN")
    (0.0, False)
    """
    norm_sport = _SPORT_ALIASES.get(sport.lower(), sport.upper())
    table = _POSITIONAL_LEVERAGE.get(norm_sport, {})
    return table.get(position.upper(), (0.0, False))


def evaluate_injury_impact(
    sport: str,
    position: str,
    is_starter: bool,
    team_side: str,
    bet_market: str,
    bet_direction: str = "home",
) -> InjuryReport:
    """
    Evaluate the impact of a confirmed starter absence on a specific bet.

    Args:
        sport:          Sport identifier (NBA, NFL, NHL, MLB, SOCCER, or aliases).
        position:       Player position code (PG, QB, G, SP, etc.).
        is_starter:     True only for confirmed starters — reserves ignored.
        team_side:      "home" or "away" — which team is missing the player.
        bet_market:     "spreads", "h2h", or "totals".
        bet_direction:  "home" or "away" — which side the bet favours.

    Returns:
        InjuryReport with flag/kill status and advisory text.

    >>> r = evaluate_injury_impact("NBA", "PG", True, "home", "spreads", "home")
    >>> r.kill
    True
    >>> r.signed_impact < 0
    True
    >>> r2 = evaluate_injury_impact("NFL", "QB", True, "away", "spreads", "home")
    >>> r2.signed_impact > 0
    True
    >>> r3 = evaluate_injury_impact("NBA", "PG", False, "home", "spreads", "home")
    >>> r3.leverage_pts
    0.0
    """
    norm_sport = _SPORT_ALIASES.get(sport.lower(), sport.upper())
    pos_upper = position.upper()

    if not is_starter:
        return InjuryReport(
            leverage_pts=0.0, signed_impact=0.0,
            flag=False, kill=False,
            advisory="Non-starter — no impact expected.",
            position=pos_upper, sport=norm_sport,
        )

    leverage, is_pivotal = get_positional_leverage(norm_sport, pos_upper)

    if leverage == 0.0:
        return InjuryReport(
            leverage_pts=0.0, signed_impact=0.0,
            flag=False, kill=False,
            advisory=f"Unknown position '{pos_upper}' for {norm_sport} — no leverage data.",
            position=pos_upper, sport=norm_sport,
        )

    if bet_market == "totals":
        multiplier = _SIDE_MULTIPLIER["total_injury"]
    else:
        key = f"{bet_direction}_bet_{team_side}_injury"
        multiplier = _SIDE_MULTIPLIER.get(key, -1.0)

    signed_impact = leverage * multiplier
    flag = abs(signed_impact) >= LEVERAGE_FLAG_THRESHOLD
    kill = abs(signed_impact) >= LEVERAGE_KILL_THRESHOLD

    direction = "hurts" if signed_impact < 0 else "helps"
    severity = "KILL" if kill else ("FLAG" if flag else "INFO")
    pivotal_tag = " [PIVOTAL POSITION]" if is_pivotal else ""
    advisory = (
        f"{severity}: {norm_sport} {pos_upper} starter out — "
        f"expected {leverage:.1f}pt line shift, {direction} this bet{pivotal_tag}."
    )

    return InjuryReport(
        leverage_pts=leverage,
        signed_impact=round(signed_impact, 2),
        flag=flag,
        kill=kill,
        advisory=advisory,
        position=pos_upper,
        sport=norm_sport,
    )


def injury_kill_switch(
    sport: str,
    position: str,
    is_starter: bool,
    team_side: str,
    bet_market: str,
    bet_direction: str = "home",
) -> tuple[bool, str]:
    """
    Convenience wrapper — returns (should_kill, reason_string).

    Returns (False, "") when no injury impact meets kill threshold.

    >>> injury_kill_switch("NBA", "PG", True, "home", "spreads", "home")
    (False, '')
    >>> injury_kill_switch("NFL", "RB", True, "home", "spreads", "away")
    (False, '')
    >>> injury_kill_switch("NBA", "PG", False, "home", "spreads", "home")
    (False, '')
    """
    report = evaluate_injury_impact(sport, position, is_starter, team_side, bet_market, bet_direction)
    if report.kill:
        return True, report.advisory
    return False, ""


def situational_score_from_injuries(injury_reports: Optional[list]) -> float:
    """
    Compute SITUATIONAL component (0-15 pts) of Sharp Score from injury reports.

    Only opponent injuries (positive signed_impact) add points — they represent
    a structural edge. Own-team kill-level injuries should trigger injury_kill_switch()
    before reaching this function, so they are excluded here.

    Cap: 15 pts total (SITUATIONAL component ceiling).

    Args:
        injury_reports: List of InjuryReport objects, or None/empty → 0.0

    Returns:
        float in [0.0, 15.0]

    >>> situational_score_from_injuries(None)
    0.0
    >>> situational_score_from_injuries([])
    0.0
    """
    if not injury_reports:
        return 0.0

    total = 0.0
    for r in injury_reports:
        if isinstance(r, InjuryReport) and r.signed_impact > 0:
            total += r.signed_impact
    return round(min(15.0, total), 1)


# ---------------------------------------------------------------------------
# NBA PDO regression signal (Chat 40)
# Ported from agentic-rd-sandbox/core/nba_pdo.py — static snapshot only.
# nba_api live-fetch dependency is NOT ported. Static dict updated each season.
# ---------------------------------------------------------------------------

PDO_BASELINE: float = 100.0
PDO_REGRESS_THRESHOLD: float = 102.0   # overperforming luck -> expect regression
PDO_RECOVER_THRESHOLD: float = 98.0    # underperforming luck -> expect recovery
PDO_MIN_GAMES: int = 10                # sample size guard

# Static PDO snapshot -- 2024-25 NBA season (mid-season estimates).
# PDO = (team FG% + opponent save%) * 100. League average = 100.0 by identity.
# Values >102 -> regression expected; <98 -> recovery expected.
# UPDATE at season start (October) when full-season data available.
_PDO_SNAPSHOT: dict = {
    # Regression candidates (PDO > 102)
    "Oklahoma City Thunder":    103.5,
    "Cleveland Cavaliers":      102.8,
    "Boston Celtics":           102.4,
    "New York Knicks":          102.2,
    # Neutral zone (PDO 98-102)
    "Denver Nuggets":           101.5,
    "Minnesota Timberwolves":   101.2,
    "Memphis Grizzlies":        101.0,
    "Golden State Warriors":    100.8,
    "Milwaukee Bucks":          100.7,
    "Houston Rockets":          100.6,
    "Los Angeles Lakers":       100.4,
    "Indiana Pacers":           100.3,
    "Los Angeles Clippers":     100.1,
    "Miami Heat":               100.0,
    "Atlanta Hawks":             99.8,
    "Dallas Mavericks":          99.7,
    "Sacramento Kings":          99.6,
    "Phoenix Suns":              99.5,
    "New Orleans Pelicans":      99.4,
    "Orlando Magic":             99.2,
    "Toronto Raptors":           99.0,
    "Brooklyn Nets":             98.8,
    "Chicago Bulls":             98.5,
    "Detroit Pistons":           98.3,
    # Recovery candidates (PDO < 98)
    "Portland Trail Blazers":    97.8,
    "San Antonio Spurs":         97.5,
    "Philadelphia 76ers":        97.2,
    "Utah Jazz":                 97.0,
    "Charlotte Hornets":         96.8,
    "Washington Wizards":        96.5,
}

# Team name aliases -- avoids alias collisions with soccer (Spurs/Wolves namespaced here)
_PDO_TEAM_ALIASES: dict = {
    "thunder": "Oklahoma City Thunder",
    "cavaliers": "Cleveland Cavaliers",
    "cavs": "Cleveland Cavaliers",
    "celtics": "Boston Celtics",
    "knicks": "New York Knicks",
    "nuggets": "Denver Nuggets",
    "timberwolves": "Minnesota Timberwolves",
    "wolves": "Minnesota Timberwolves",
    "grizzlies": "Memphis Grizzlies",
    "warriors": "Golden State Warriors",
    "bucks": "Milwaukee Bucks",
    "rockets": "Houston Rockets",
    "lakers": "Los Angeles Lakers",
    "pacers": "Indiana Pacers",
    "clippers": "Los Angeles Clippers",
    "heat": "Miami Heat",
    "hawks": "Atlanta Hawks",
    "mavericks": "Dallas Mavericks",
    "mavs": "Dallas Mavericks",
    "kings": "Sacramento Kings",
    "suns": "Phoenix Suns",
    "pelicans": "New Orleans Pelicans",
    "magic": "Orlando Magic",
    "raptors": "Toronto Raptors",
    "nets": "Brooklyn Nets",
    "bulls": "Chicago Bulls",
    "pistons": "Detroit Pistons",
    "blazers": "Portland Trail Blazers",
    "nba_spurs": "San Antonio Spurs",
    "spurs": "San Antonio Spurs",
    "76ers": "Philadelphia 76ers",
    "sixers": "Philadelphia 76ers",
    "jazz": "Utah Jazz",
    "hornets": "Charlotte Hornets",
    "wizards": "Washington Wizards",
    "okc": "Oklahoma City Thunder",
}


def _resolve_nba_team(name: str) -> Optional[str]:
    """
    Resolve a team name string to the canonical key in _PDO_SNAPSHOT.

    Returns None for unknown teams (caller treats as NEUTRAL).

    >>> _resolve_nba_team("Oklahoma City Thunder")
    'Oklahoma City Thunder'
    >>> _resolve_nba_team("Thunder")
    'Oklahoma City Thunder'
    >>> _resolve_nba_team("OKC")
    'Oklahoma City Thunder'
    >>> _resolve_nba_team("Unknown Team FC") is None
    True
    """
    if not name:
        return None
    if name in _PDO_SNAPSHOT:
        return name
    lower = name.strip().lower()
    if lower in _PDO_TEAM_ALIASES:
        return _PDO_TEAM_ALIASES[lower]
    last = lower.split()[-1] if lower else ""
    if last in _PDO_TEAM_ALIASES:
        return _PDO_TEAM_ALIASES[last]
    return None


def get_pdo_signal(team: str) -> str:
    """
    Return PDO signal for an NBA team: "REGRESS", "RECOVER", or "NEUTRAL".

    Unknown teams return "NEUTRAL" (fail-safe).

    >>> get_pdo_signal("Oklahoma City Thunder")
    'REGRESS'
    >>> get_pdo_signal("Washington Wizards")
    'RECOVER'
    >>> get_pdo_signal("Miami Heat")
    'NEUTRAL'
    >>> get_pdo_signal("Unknown Team FC")
    'NEUTRAL'
    """
    canonical = _resolve_nba_team(team)
    if canonical is None:
        return "NEUTRAL"
    pdo = _PDO_SNAPSHOT[canonical]
    if pdo >= PDO_REGRESS_THRESHOLD:
        return "REGRESS"
    if pdo <= PDO_RECOVER_THRESHOLD:
        return "RECOVER"
    return "NEUTRAL"


def pdo_situational_pts(home_team: str, away_team: str) -> float:
    """
    Compute PDO-based SITUATIONAL bonus pts (0-10) for a matchup.

    Signal strength:
      REGRESS vs RECOVER (max mismatch) -> 10 pts
      One signal + NEUTRAL             ->  5 pts
      Both NEUTRAL or same signal      ->  0 pts

    >>> pdo_situational_pts("Oklahoma City Thunder", "Washington Wizards")
    10.0
    >>> pdo_situational_pts("Miami Heat", "Atlanta Hawks")
    0.0
    >>> pdo_situational_pts("Oklahoma City Thunder", "Miami Heat")
    5.0
    >>> pdo_situational_pts("Oklahoma City Thunder", "Cleveland Cavaliers")
    0.0
    """
    home_sig = get_pdo_signal(home_team)
    away_sig = get_pdo_signal(away_team)
    signals = {home_sig, away_sig}
    if "REGRESS" in signals and "RECOVER" in signals:
        return 10.0
    if home_sig != "NEUTRAL" and away_sig == "NEUTRAL":
        return 5.0
    if away_sig != "NEUTRAL" and home_sig == "NEUTRAL":
        return 5.0
    return 0.0


def pdo_kill_switch_from_snapshot(
    team: str,
    bet_direction: str,
) -> tuple:
    """
    PDO kill switch using static snapshot (no live API call).

    Args:
        team:          Canonical team name (or alias).
        bet_direction: "with" (backing this team) or "against" (fading them).

    Returns:
        (True,  "KILL: reason") -- remove from pipeline
        (False, "FLAG: reason") -- annotate but keep
        (False, "")             -- no PDO signal

    >>> pdo_kill_switch_from_snapshot("Oklahoma City Thunder", "with")
    (True, 'KILL: PDO regress -- Oklahoma City Thunder overperforming luck (PDO 103.5)')
    >>> pdo_kill_switch_from_snapshot("Washington Wizards", "with")
    (False, 'FLAG: PDO recovery candidate -- Washington Wizards underperforming luck (PDO 96.5)')
    >>> pdo_kill_switch_from_snapshot("Miami Heat", "with")
    (False, '')
    """
    canonical = _resolve_nba_team(team)
    if canonical is None:
        return (False, "")
    pdo = _PDO_SNAPSHOT[canonical]
    signal = get_pdo_signal(canonical)
    if signal == "NEUTRAL":
        return (False, "")
    direction = bet_direction.lower().strip()
    if signal == "REGRESS":
        if direction == "with":
            return (True, f"KILL: PDO regress -- {canonical} overperforming luck (PDO {pdo})")
        return (False, f"FLAG: PDO regress opponent -- {canonical} due for regression (PDO {pdo})")
    # signal == "RECOVER"
    if direction == "against":
        return (True, f"KILL: PDO recovery -- fading {canonical} but they're due positive regression (PDO {pdo})")
    return (False, f"FLAG: PDO recovery candidate -- {canonical} underperforming luck (PDO {pdo})")


# ---------------------------------------------------------------------------
# NHL goalie kill switch signal (Chat 40)
# Wraps existing nhl_kill_switch() for both-team context.
# ---------------------------------------------------------------------------

def nhl_kill_switch_signal(
    home_goalie_starter: bool,
    away_goalie_starter: bool,
    home_goalie_confirmed: bool = True,
    away_goalie_confirmed: bool = True,
) -> dict:
    """
    NHL kill switch given starter status for BOTH teams.

    Returns dict with keys: skip (bool), reason (str).

    Kill: either team has a confirmed backup -> skip immediately.
    Flag: either team's goalie unconfirmed -> advisory only, don't skip.
    Pass: both starters confirmed -> no action.

    >>> nhl_kill_switch_signal(False, True)
    {'skip': True, 'reason': 'KILL: Backup goalie confirmed -- skip NHL bet'}
    >>> nhl_kill_switch_signal(True, False)
    {'skip': True, 'reason': 'KILL: Backup goalie confirmed -- skip NHL bet'}
    >>> nhl_kill_switch_signal(True, True)
    {'skip': False, 'reason': ''}
    >>> nhl_kill_switch_signal(True, True, home_goalie_confirmed=False)
    {'skip': False, 'reason': 'FLAG: Goalie not yet confirmed -- require 8%+ edge'}
    """
    home_backup = not home_goalie_starter
    away_backup = not away_goalie_starter

    if home_backup or away_backup:
        kill, reason = nhl_kill_switch(backup_goalie=True)
        return {"skip": kill, "reason": reason}

    if not home_goalie_confirmed or not away_goalie_confirmed:
        _, reason = nhl_kill_switch(backup_goalie=False, goalie_confirmed=False)
        return {"skip": False, "reason": reason}

    return {"skip": False, "reason": ""}
