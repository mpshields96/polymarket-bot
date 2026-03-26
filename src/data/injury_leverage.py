"""
src/data/injury_leverage.py — Static Injury Leverage Table for sports sniper guard.

Ported from agentic-rd-sandbox/core/injury_data.py (Matthew's R&D sandbox).

Provides a static positional impact model: given a player's position and sport,
return the expected point-spread impact (leverage) of their absence, and whether
to flag or kill the bet.

Design philosophy:
- Zero external API calls. Zero unofficial endpoints.
- Conservative: if player status unknown → no flag (safe default for sniper).
- Caller provides the player name + status from whatever data source is available.
  Currently ESPN feed does not expose injury data — this module is wired but dormant
  until an injury feed is connected.

Usage:
    from src.data.injury_leverage import injury_kill_switch, LEVERAGE_KILL_THRESHOLD
    should_kill, reason = injury_kill_switch(
        sport="NBA", position="PG", is_starter=True,
        team_side="home", bet_market="h2h", bet_direction="home",
    )
"""

from __future__ import annotations

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
LEVERAGE_KILL_THRESHOLD: float = 3.5  # pts: kill bet if starter absence shifts line >= this
LEVERAGE_FLAG_THRESHOLD: float = 2.0  # pts: soft flag (advisory only)


# ---------------------------------------------------------------------------
# Positional leverage tables
# ---------------------------------------------------------------------------
# Format: sport → {position_code: (leverage_pts, is_pivotal)}
# leverage_pts: expected point-spread shift on confirmed absence
# is_pivotal:   True if position is franchise-level (e.g. QB in NFL)

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

_SPORT_ALIASES: dict[str, str] = {
    "nba": "NBA",
    "nfl": "NFL",
    "nhl": "NHL",
    "mlb": "MLB",
    "soccer": "SOCCER",
    "ncaab": "NBA",
    "ncaaf": "NFL",
}

_SIDE_MULTIPLIER: dict[str, float] = {
    "home_bet_home_injury": -1.0,
    "home_bet_away_injury": +0.5,
    "away_bet_away_injury": -1.0,
    "away_bet_home_injury": +0.5,
    "total_injury": -0.3,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------
@dataclass
class InjuryReport:
    leverage_pts: float
    signed_impact: float
    flag: bool
    kill: bool
    advisory: str
    position: str
    sport: str


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
def get_positional_leverage(sport: str, position: str) -> tuple[float, bool]:
    """
    Return (leverage_pts, is_pivotal) for a given sport + position.

    Returns (0.0, False) for unknown sport/position combinations.
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
        sport:          Sport identifier (NBA, NFL, NHL, MLB, or aliases).
        position:       Player position code (PG, QB, G, SP, etc.).
        is_starter:     True only for confirmed starters — reserves ignored.
        team_side:      "home" or "away" — which team is missing the player.
        bet_market:     "spreads", "h2h", or "totals".
        bet_direction:  "home" or "away" — which side the bet favours.

    Returns:
        InjuryReport with flag/kill status and advisory text.
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

    Returns (False, "") when no injury impact is above kill threshold.
    Used by sports_sniper as an optional guard layer when injury data is available.
    """
    report = evaluate_injury_impact(sport, position, is_starter, team_side, bet_market, bet_direction)
    if report.kill:
        return True, report.advisory
    if report.flag:
        return False, report.advisory
    return False, ""


def list_high_leverage_positions(sport: str, min_leverage: float = 2.0) -> list[tuple[str, float, bool]]:
    """
    Return all positions in a sport above a leverage threshold.

    Returns list of (position, leverage_pts, is_pivotal) sorted by leverage desc.
    """
    norm_sport = _SPORT_ALIASES.get(sport.lower(), sport.upper())
    table = _POSITIONAL_LEVERAGE.get(norm_sport, {})
    result = [
        (pos, lev, piv)
        for pos, (lev, piv) in table.items()
        if lev >= min_leverage
    ]
    result.sort(key=lambda x: x[1], reverse=True)
    return result
