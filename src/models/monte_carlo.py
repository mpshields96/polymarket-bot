"""
src/models/monte_carlo.py — Monte Carlo spread/total simulation + Poisson soccer model.

Ported from agentic-rd-sandbox/core/originator_engine.py (Matthew's R&D sandbox).
Addresses REQ-027 (simulation standing directive — S132).

This module provides:
  run_trinity_simulation()  — Trinity-weighted Monte Carlo for spread/total cover probability
  poisson_soccer()          — Poisson matrix for soccer 1X2 + over/under
  efficiency_gap_to_margin() — Convert efficiency gap to projected point margin

Trinity weighting (V36.1 spec):
  Ceiling scenario (20% weight): optimistic inputs
  Floor scenario   (20% weight): pessimistic inputs
  Median scenario  (60% weight): baseline inputs
  Simulates uncertainty in INPUTS, not just noise in outputs.

Usage:
    from src.models.monte_carlo import run_trinity_simulation, efficiency_gap_to_margin
    margin = efficiency_gap_to_margin(efficiency_gap=12.5)
    result = run_trinity_simulation(mean=margin, sport="NBA", line=-4.5)
    cover_prob = result.cover_probability

DO NOT import from src/risk/ — circular import risk.
DO NOT call from async hot path without seed= for reproducibility.
"""

import math
import random
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Base volatility by sport (std dev in points/goals)
# ---------------------------------------------------------------------------
BASE_VOLATILITY: dict[str, float] = {
    "NBA":    6.5,
    "NCAAB":  8.5,
    "NFL":   10.5,
    "NCAAF": 12.0,
    "NHL":    1.8,
    "MLB":    2.2,
    "SOCCER": 1.1,
}

_DEFAULT_VOLATILITY: float = 8.0

# Input variance constants (per V36.1 spec)
EFFICIENCY_VARIANCE: float = 2.5   # ± pts per 100 possessions
PACE_VARIANCE: float       = 3.0   # ± possessions
REST_VARIANCE: float       = 1.5   # pts from rest edge
TRAVEL_VARIANCE: float     = 1.0   # pts from travel
HOME_VARIANCE: float       = 2.5   # home court/field pts

# League-average totals for over/under simulation
LEAGUE_AVG_TOTALS: dict[str, float] = {
    "NBA": 228.0, "NCAAB": 148.0, "NFL": 45.0,
    "NHL":   6.0, "MLB":     9.0, "SOCCER": 2.65,
}

# Efficiency gap scale: gap of 10 = neutral, gap of 20 = max home advantage
# Each 1-unit gap beyond 10 = ~1 projected point advantage
EFFICIENCY_GAP_NEUTRAL: float = 10.0
EFFICIENCY_GAP_SCALE: float   = 1.0   # pts per gap unit


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------
@dataclass
class SimulationResult:
    cover_probability: float   # % sims where home covers the line (home perspective)
    over_probability: float    # % sims where total goes over total_line
    projected_margin: float    # median simulated margin (home - away)
    ci_10: float               # 10th percentile margin
    ci_90: float               # 90th percentile margin
    volatility: float          # std dev of simulated margins
    iterations: int


@dataclass
class PoissonResult:
    """
    Poisson matrix simulation result for soccer over/under and 1X2 probabilities.

    home_win / draw / away_win sum to ~1.0 (rounding from discrete grid).
    over_probability is P(total goals > total_line).
    """
    home_win: float
    draw: float
    away_win: float
    over_probability: float
    under_probability: float
    expected_home_goals: float
    expected_away_goals: float
    expected_total: float
    max_goals: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normal_sample(mu: float, sigma: float) -> float:
    """Box-Muller transform — normal sample without scipy/numpy dependency."""
    u1 = random.uniform(1e-10, 1.0)
    u2 = random.uniform(0.0, 1.0)
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return mu + sigma * z


def _poisson_pmf(k: int, lam: float) -> float:
    """
    Poisson probability mass function P(X=k | lambda).
    Pure Python — no scipy dependency.
    Returns 0.0 for lambda <= 0 or k < 0.
    """
    if lam <= 0 or k < 0:
        return 0.0
    log_p = -lam + k * math.log(lam) - sum(math.log(i) for i in range(1, k + 1))
    return math.exp(log_p)


# ---------------------------------------------------------------------------
# Poisson Soccer Simulation
# ---------------------------------------------------------------------------
SOCCER_HOME_GOAL_BOOST: float = 0.20
SOCCER_LEAGUE_AVG_GOALS_HOME: float = 1.54
SOCCER_LEAGUE_AVG_GOALS_AWAY: float = 1.11
_POISSON_MAX_GOALS: int = 10


def poisson_soccer(
    home_attack: float = 1.0,
    away_attack: float = 1.0,
    home_defense: float = 1.0,
    away_defense: float = 1.0,
    total_line: float = 2.5,
    apply_home_advantage: bool = True,
) -> PoissonResult:
    """
    Poisson matrix model for soccer 1X2 and over/under probabilities.

    Models goals as independent Poisson processes for home and away teams.

    Args:
        home_attack:    Home team's attacking strength relative to league avg (1.0 = neutral).
        away_attack:    Away team attacking strength.
        home_defense:   Home team's defensive strength (lower = better).
        away_defense:   Away defensive strength.
        total_line:     Over/under total goals line (e.g. 2.5).
        apply_home_advantage: If True, adds SOCCER_HOME_GOAL_BOOST to home lambda.

    Returns:
        PoissonResult with home_win, draw, away_win, over/under probabilities.
    """
    lam_home = SOCCER_LEAGUE_AVG_GOALS_HOME * home_attack * away_defense
    lam_away = SOCCER_LEAGUE_AVG_GOALS_AWAY * away_attack * home_defense

    if apply_home_advantage:
        lam_home *= (1.0 + SOCCER_HOME_GOAL_BOOST)

    lam_home = max(0.1, min(lam_home, 6.0))
    lam_away = max(0.1, min(lam_away, 6.0))

    home_pmf = [_poisson_pmf(k, lam_home) for k in range(_POISSON_MAX_GOALS + 1)]
    away_pmf = [_poisson_pmf(k, lam_away) for k in range(_POISSON_MAX_GOALS + 1)]

    home_win = 0.0
    draw = 0.0
    away_win = 0.0
    over = 0.0
    under = 0.0

    for h in range(_POISSON_MAX_GOALS + 1):
        for a in range(_POISSON_MAX_GOALS + 1):
            p = home_pmf[h] * away_pmf[a]
            total_goals = h + a

            if h > a:
                home_win += p
            elif h == a:
                draw += p
            else:
                away_win += p

            if total_goals > total_line:
                over += p
            else:
                under += p

    return PoissonResult(
        home_win=home_win,
        draw=draw,
        away_win=away_win,
        over_probability=over,
        under_probability=under,
        expected_home_goals=lam_home,
        expected_away_goals=lam_away,
        expected_total=lam_home + lam_away,
        max_goals=_POISSON_MAX_GOALS,
    )


def efficiency_gap_to_soccer_strength(efficiency_gap: float) -> tuple[float, float, float, float]:
    """
    Convert efficiency_gap (0-20 scale) to Poisson attack/defense strength factors.

    Gap = 10 → neutral (all factors = 1.0)
    Gap > 10 → home stronger: home_attack ↑, away_defense ↓

    Returns:
        (home_attack, away_attack, home_defense, away_defense)
    """
    delta = (efficiency_gap - EFFICIENCY_GAP_NEUTRAL) / 10.0 * 0.30
    home_attack = max(0.5, 1.0 + delta)
    away_attack = max(0.5, 1.0 - delta)
    home_defense = max(0.5, 1.0 - delta * 0.5)
    away_defense = max(0.5, 1.0 + delta * 0.5)
    return home_attack, away_attack, home_defense, away_defense


def efficiency_gap_to_margin(
    efficiency_gap: float,
    home_advantage_pts: float = 0.0,
) -> float:
    """
    Convert efficiency_gap (0-20 scale from efficiency_feed) to projected margin.

    efficiency_gap=10 → perfectly matched → projected margin = 0
    efficiency_gap=15 → home is 5 units better → projected margin = +5.0 pts
    efficiency_gap=5  → away is 5 units better → projected margin = -5.0 pts

    Args:
        efficiency_gap: Float 0-20.
        home_advantage_pts: Additional home court/field advantage in pts.

    Returns:
        Projected margin in sport-appropriate units (pts, goals, runs).
    """
    return (efficiency_gap - EFFICIENCY_GAP_NEUTRAL) * EFFICIENCY_GAP_SCALE + home_advantage_pts


# ---------------------------------------------------------------------------
# Trinity simulation
# ---------------------------------------------------------------------------
def run_trinity_simulation(
    mean: float,
    sport: str = "NBA",
    line: float = 0.0,
    total_line: Optional[float] = None,
    rest_edge: float = 0.0,
    travel_penalty: float = 0.0,
    home_advantage: float = 0.0,
    iterations: int = 10_000,
    seed: Optional[int] = None,
) -> SimulationResult:
    """
    Trinity Monte Carlo simulation for spread and total cover probability.

    IMPORTANT — mean must be model-derived projected margin, NOT the market line.
    Use efficiency_gap_to_margin() to convert efficiency_gap before calling.

    Args:
        mean:           Model-derived projected margin (home minus away, pts).
        sport:          Sport key for base volatility lookup (e.g. "NBA", "NCAAB").
        line:           Market spread line (e.g. -4.5 = home favoured by 4.5).
                        Home covers if simulated_margin > -line.
        total_line:     Over/under market line. Pass None to skip total simulation.
        rest_edge:      Rest advantage in pts (positive = home better rested).
        travel_penalty: Travel fatigue in pts (positive = away penalized).
        home_advantage: Home court/field advantage in pts (separate from mean).
        iterations:     Monte Carlo iterations. Default 10,000.
        seed:           Random seed for reproducibility.

    Returns:
        SimulationResult with cover_probability, over_probability, projected_margin,
        confidence interval (ci_10/ci_90), volatility, and iteration count.

    Trinity weighting:
        Ceiling (20%): mean + optimistic noise, tighter vol (×0.85)
        Floor   (20%): mean + pessimistic noise, wider vol (×1.15)
        Median  (60%): mean + small baseline noise, standard vol
    """
    if seed is not None:
        random.seed(seed)

    base_vol = BASE_VOLATILITY.get(sport.upper(), _DEFAULT_VOLATILITY)
    situational = rest_edge + travel_penalty + home_advantage
    adjusted_mean = mean + situational

    margins = []
    covers = 0
    overs = 0

    for _ in range(iterations):
        roll = random.random()

        if roll < 0.20:
            # CEILING — optimistic inputs (20% of sims)
            eff_noise = abs(_normal_sample(0.0, EFFICIENCY_VARIANCE))
            pace_noise = abs(_normal_sample(0.0, PACE_VARIANCE)) * 0.3
            scenario_mean = adjusted_mean + eff_noise + pace_noise
            vol = base_vol * 0.85

        elif roll < 0.40:
            # FLOOR — pessimistic inputs (20% of sims)
            eff_noise = -abs(_normal_sample(0.0, EFFICIENCY_VARIANCE))
            pace_noise = -abs(_normal_sample(0.0, PACE_VARIANCE)) * 0.3
            scenario_mean = adjusted_mean + eff_noise + pace_noise
            vol = base_vol * 1.15

        else:
            # MEDIAN — baseline (60% of sims)
            eff_noise = _normal_sample(0.0, EFFICIENCY_VARIANCE * 0.5)
            scenario_mean = adjusted_mean + eff_noise
            vol = base_vol

        simulated_margin = _normal_sample(scenario_mean, vol)
        margins.append(simulated_margin)

        if simulated_margin > -line:
            covers += 1

        if total_line is not None:
            league_avg = LEAGUE_AVG_TOTALS.get(sport.upper(), 200.0)
            simulated_total = league_avg + _normal_sample(0.0, base_vol * 0.6)
            if simulated_total > total_line:
                overs += 1

    margins.sort()
    n = len(margins)
    ci_10 = margins[int(0.10 * n)]
    ci_90 = margins[int(0.90 * n)]
    median_margin = margins[n // 2]

    variance = sum((m - adjusted_mean) ** 2 for m in margins) / n
    volatility = math.sqrt(variance)

    return SimulationResult(
        cover_probability=covers / iterations,
        over_probability=overs / iterations if total_line is not None else 0.0,
        projected_margin=median_margin,
        ci_10=ci_10,
        ci_90=ci_90,
        volatility=volatility,
        iterations=iterations,
    )
