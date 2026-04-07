"""
src/strategies/efficiency_feed.py — Kalshi Bot
===============================================
Team efficiency data layer. Ported from agentic-rd-sandbox/core/efficiency_feed.py.
Zero external dependencies — stdlib only.

The efficiency component contributes 0-20 points to Sharp Score:
    eff_pts = max(0.0, min(20.0, efficiency_gap))

Gap output is pre-scaled 0-20 — pass directly to calculate_sharp_score().

Scaling formula (same across all sports):
    differential = home_adj_em - away_adj_em
    gap = (differential + 30) / 60 * 20
    Gap 10.0 = evenly matched. >10 = home advantage. <10 = away advantage.
    Clamped to [0.0, 20.0].

Data sources (static snapshots, not live):
    NBA:   Net Rating * 2.2 → adj_em scale. ~2024-25 season.
    NHL:   Goal differential/game * 12.0 → adj_em scale. ~2024-25 season.
    NCAAB: KenPom/Barttorvik AdjEM. ~2024-25 season.
    NFL:   EPA/play * 80.0 → adj_em scale. ~2024 season.
    MLB:   (4.30 - ERA) * 8.0 → adj_em scale. ~2024 season.
    MLS:   xGD/90 * 15.0 → adj_em scale. ~2024 season.
    Soccer (EPL/Bund/Ligue1/SerieA/LaLiga): xG-based adj_em. ~2024-25 season.

Unknown teams fall back to gap=8.0 (below neutral — doesn't inflate scores).
"""

from __future__ import annotations
from typing import Optional


# ---------------------------------------------------------------------------
# Unknown team fallback
# ---------------------------------------------------------------------------
_UNKNOWN_GAP: float = 8.0


# ---------------------------------------------------------------------------
# Team efficiency data — adj_em is the single number that matters.
# ---------------------------------------------------------------------------

_TEAM_DATA: dict[str, dict] = {

    # =========================================================================
    # NBA — Net Rating * 2.2 → adj_em scale (~2024-25)
    # Elite: adj_em 18-30 | Strong: 8-18 | Mid: -2 to 8 | Lower: < -5
    # =========================================================================
    "Oklahoma City Thunder":  {"adj_em": 28.0,  "league": "NBA"},
    "Boston Celtics":         {"adj_em": 27.5,  "league": "NBA"},
    "Cleveland Cavaliers":    {"adj_em": 24.6,  "league": "NBA"},
    "Minnesota Timberwolves": {"adj_em": 21.6,  "league": "NBA"},
    "Denver Nuggets":         {"adj_em": 19.0,  "league": "NBA"},
    "Houston Rockets":        {"adj_em": 14.3,  "league": "NBA"},
    "Golden State Warriors":  {"adj_em": 14.1,  "league": "NBA"},
    "Los Angeles Lakers":     {"adj_em": 12.5,  "league": "NBA"},
    "Dallas Mavericks":       {"adj_em": 12.5,  "league": "NBA"},
    "Memphis Grizzlies":      {"adj_em": 11.4,  "league": "NBA"},
    "Indiana Pacers":         {"adj_em": 10.6,  "league": "NBA"},
    "Milwaukee Bucks":        {"adj_em":  9.0,  "league": "NBA"},
    "New York Knicks":        {"adj_em":  7.9,  "league": "NBA"},
    "Los Angeles Clippers":   {"adj_em":  7.3,  "league": "NBA"},
    "Sacramento Kings":       {"adj_em":  6.6,  "league": "NBA"},
    "San Antonio Spurs":      {"adj_em":  5.5,  "league": "NBA"},
    "Miami Heat":             {"adj_em":  4.2,  "league": "NBA"},
    "Philadelphia 76ers":     {"adj_em":  3.5,  "league": "NBA"},
    "Phoenix Suns":           {"adj_em":  2.6,  "league": "NBA"},
    "New Orleans Pelicans":   {"adj_em":  1.5,  "league": "NBA"},
    "Orlando Magic":          {"adj_em":  1.1,  "league": "NBA"},
    "Chicago Bulls":          {"adj_em": -0.4,  "league": "NBA"},
    "Atlanta Hawks":          {"adj_em": -2.0,  "league": "NBA"},
    "Toronto Raptors":        {"adj_em": -5.1,  "league": "NBA"},
    "Brooklyn Nets":          {"adj_em":-14.3,  "league": "NBA"},
    "Detroit Pistons":        {"adj_em":-13.6,  "league": "NBA"},
    "Utah Jazz":              {"adj_em":-13.0,  "league": "NBA"},
    "Portland Trail Blazers": {"adj_em":-14.3,  "league": "NBA"},
    "Charlotte Hornets":      {"adj_em":-14.9,  "league": "NBA"},
    "Washington Wizards":     {"adj_em":-21.6,  "league": "NBA"},

    # =========================================================================
    # NHL — Goal differential/game * 12.0 → adj_em scale (~2024-25)
    # Elite: adj_em 8-14 | Strong: 3-8 | Average: -2 to 3 | Poor: < -4
    # Scaling: +1 GD/game = adj_em 12. Average team = 0.
    # =========================================================================
    # Elite
    "Florida Panthers":       {"adj_em": 10.8,  "league": "NHL"},  # +0.9 GD/g
    "Winnipeg Jets":          {"adj_em":  9.6,  "league": "NHL"},  # +0.8 GD/g
    "Washington Capitals":    {"adj_em":  8.4,  "league": "NHL"},  # +0.7 GD/g
    "Vegas Golden Knights":   {"adj_em":  7.2,  "league": "NHL"},  # +0.6 GD/g
    "Carolina Hurricanes":    {"adj_em":  7.2,  "league": "NHL"},  # +0.6 GD/g
    "Dallas Stars":           {"adj_em":  6.0,  "league": "NHL"},  # +0.5 GD/g
    "Colorado Avalanche":     {"adj_em":  6.0,  "league": "NHL"},  # +0.5 GD/g

    # Strong
    "New Jersey Devils":      {"adj_em":  4.8,  "league": "NHL"},
    "Toronto Maple Leafs":    {"adj_em":  4.8,  "league": "NHL"},
    "Boston Bruins":          {"adj_em":  4.8,  "league": "NHL"},
    "Tampa Bay Lightning":    {"adj_em":  4.8,  "league": "NHL"},
    "Edmonton Oilers":        {"adj_em":  3.6,  "league": "NHL"},
    "Nashville Predators":    {"adj_em":  3.6,  "league": "NHL"},
    "Los Angeles Kings":      {"adj_em":  3.6,  "league": "NHL"},
    "Minnesota Wild":         {"adj_em":  2.4,  "league": "NHL"},

    # Mid
    "New York Rangers":       {"adj_em":  2.4,  "league": "NHL"},
    "Ottawa Senators":        {"adj_em":  1.2,  "league": "NHL"},
    "Calgary Flames":         {"adj_em":  1.2,  "league": "NHL"},
    "Pittsburgh Penguins":    {"adj_em":  0.0,  "league": "NHL"},
    "Seattle Kraken":         {"adj_em":  0.0,  "league": "NHL"},
    "New York Islanders":     {"adj_em": -1.2,  "league": "NHL"},
    "Vancouver Canucks":      {"adj_em": -1.2,  "league": "NHL"},
    "Arizona Coyotes":        {"adj_em": -2.4,  "league": "NHL"},  # Utah relocation
    "Utah Hockey Club":       {"adj_em": -2.4,  "league": "NHL"},

    # Lower
    "Detroit Red Wings":      {"adj_em": -3.6,  "league": "NHL"},
    "Philadelphia Flyers":    {"adj_em": -4.8,  "league": "NHL"},
    "St. Louis Blues":        {"adj_em": -4.8,  "league": "NHL"},
    "Anaheim Ducks":          {"adj_em": -7.2,  "league": "NHL"},
    "Buffalo Sabres":         {"adj_em": -6.0,  "league": "NHL"},
    "Chicago Blackhawks":     {"adj_em": -9.6,  "league": "NHL"},
    "Columbus Blue Jackets":  {"adj_em": -7.2,  "league": "NHL"},
    "San Jose Sharks":        {"adj_em":-10.8,  "league": "NHL"},
    "Montreal Canadiens":     {"adj_em": -3.6,  "league": "NHL"},

    # =========================================================================
    # NCAAB — KenPom/Barttorvik AdjEM (~2024-25)
    # =========================================================================
    "Duke":            {"adj_em": 32.8, "league": "NCAAB"},
    "UConn":           {"adj_em": 26.7, "league": "NCAAB"},
    "Marquette":       {"adj_em": 19.4, "league": "NCAAB"},
    "Creighton":       {"adj_em": 15.9, "league": "NCAAB"},
    "NC State":        {"adj_em": 12.3, "league": "NCAAB"},
    "Kansas":          {"adj_em": 29.7, "league": "NCAAB"},
    "Houston":         {"adj_em": 26.4, "league": "NCAAB"},
    "Texas":           {"adj_em": 17.7, "league": "NCAAB"},
    "Kentucky":        {"adj_em": 27.2, "league": "NCAAB"},
    "Auburn":          {"adj_em": 25.7, "league": "NCAAB"},
    "Alabama":         {"adj_em": 18.9, "league": "NCAAB"},
    "Tennessee":       {"adj_em": 18.4, "league": "NCAAB"},
    "Michigan St":     {"adj_em": 20.2, "league": "NCAAB"},
    "Purdue":          {"adj_em": 18.9, "league": "NCAAB"},
    "Gonzaga":         {"adj_em": 17.2, "league": "NCAAB"},
    "St. John's":      {"adj_em": 15.6, "league": "NCAAB"},

    # =========================================================================
    # MLB — (4.30 - ERA) * 8.0 → adj_em scale (~2024 season)
    # =========================================================================
    "Seattle Mariners":        {"adj_em": (4.30 - 3.52) * 8.0, "league": "MLB"},
    "Cleveland Guardians":     {"adj_em": (4.30 - 3.54) * 8.0, "league": "MLB"},
    "Los Angeles Dodgers":     {"adj_em": (4.30 - 3.63) * 8.0, "league": "MLB"},
    "Milwaukee Brewers":       {"adj_em": (4.30 - 3.69) * 8.0, "league": "MLB"},
    "Philadelphia Phillies":   {"adj_em": (4.30 - 3.80) * 8.0, "league": "MLB"},
    "Baltimore Orioles":       {"adj_em": (4.30 - 3.86) * 8.0, "league": "MLB"},
    "Kansas City Royals":      {"adj_em": (4.30 - 3.89) * 8.0, "league": "MLB"},
    "New York Mets":           {"adj_em": (4.30 - 3.93) * 8.0, "league": "MLB"},
    "San Diego Padres":        {"adj_em": (4.30 - 3.97) * 8.0, "league": "MLB"},
    "New York Yankees":        {"adj_em": (4.30 - 3.99) * 8.0, "league": "MLB"},
    "Atlanta Braves":          {"adj_em": (4.30 - 4.01) * 8.0, "league": "MLB"},
    "Pittsburgh Pirates":      {"adj_em": (4.30 - 4.04) * 8.0, "league": "MLB"},
    "Houston Astros":          {"adj_em": (4.30 - 4.12) * 8.0, "league": "MLB"},
    "Minnesota Twins":         {"adj_em": (4.30 - 4.18) * 8.0, "league": "MLB"},
    "Detroit Tigers":          {"adj_em": (4.30 - 4.23) * 8.0, "league": "MLB"},
    "San Francisco Giants":    {"adj_em": (4.30 - 4.28) * 8.0, "league": "MLB"},
    "Arizona Diamondbacks":    {"adj_em": (4.30 - 4.31) * 8.0, "league": "MLB"},
    "Tampa Bay Rays":          {"adj_em": (4.30 - 4.35) * 8.0, "league": "MLB"},
    "Cincinnati Reds":         {"adj_em": (4.30 - 4.38) * 8.0, "league": "MLB"},
    "Boston Red Sox":          {"adj_em": (4.30 - 4.44) * 8.0, "league": "MLB"},
    "Chicago Cubs":            {"adj_em": (4.30 - 4.48) * 8.0, "league": "MLB"},
    "St. Louis Cardinals":     {"adj_em": (4.30 - 4.51) * 8.0, "league": "MLB"},
    "Texas Rangers":           {"adj_em": (4.30 - 4.55) * 8.0, "league": "MLB"},
    "Miami Marlins":           {"adj_em": (4.30 - 4.58) * 8.0, "league": "MLB"},
    "Los Angeles Angels":      {"adj_em": (4.30 - 4.62) * 8.0, "league": "MLB"},
    "Toronto Blue Jays":       {"adj_em": (4.30 - 4.65) * 8.0, "league": "MLB"},
    "Chicago White Sox":       {"adj_em": (4.30 - 5.14) * 8.0, "league": "MLB"},
    "Oakland Athletics":       {"adj_em": (4.30 - 5.02) * 8.0, "league": "MLB"},
    "Washington Nationals":    {"adj_em": (4.30 - 4.88) * 8.0, "league": "MLB"},
    "Colorado Rockies":        {"adj_em": (4.30 - 5.22) * 8.0, "league": "MLB"},

    # =========================================================================
    # EPL — xG-differential based adj_em (~2024-25)
    # =========================================================================
    "Manchester City":    {"adj_em": 22.0, "league": "EPL"},
    "Arsenal":            {"adj_em": 20.5, "league": "EPL"},
    "Liverpool":          {"adj_em": 24.0, "league": "EPL"},
    "Chelsea":            {"adj_em": 14.0, "league": "EPL"},
    "Aston Villa":        {"adj_em": 16.0, "league": "EPL"},
    "Tottenham Hotspur":  {"adj_em": 12.0, "league": "EPL"},
    "Manchester United":  {"adj_em":  8.0, "league": "EPL"},
    "Newcastle United":   {"adj_em": 13.5, "league": "EPL"},
    "Brighton":           {"adj_em": 11.0, "league": "EPL"},
    "West Ham United":    {"adj_em":  6.0, "league": "EPL"},
    "Fulham":             {"adj_em":  5.0, "league": "EPL"},
    "Crystal Palace":     {"adj_em":  3.5, "league": "EPL"},
    "Brentford":          {"adj_em":  4.0, "league": "EPL"},
    "Wolverhampton":      {"adj_em":  2.0, "league": "EPL"},
    "Everton":            {"adj_em": -2.0, "league": "EPL"},
    "Nottingham Forest":  {"adj_em":  9.0, "league": "EPL"},
    "Bournemouth":        {"adj_em":  6.5, "league": "EPL"},
    "Leicester City":     {"adj_em": -4.0, "league": "EPL"},
    "Ipswich Town":       {"adj_em": -8.0, "league": "EPL"},
    "Southampton":        {"adj_em":-14.0, "league": "EPL"},

    # =========================================================================
    # Bundesliga (~2024-25)
    # =========================================================================
    "Bayern Munich":              {"adj_em": 24.0, "league": "BUNDESLIGA"},
    "Bayer Leverkusen":           {"adj_em": 22.5, "league": "BUNDESLIGA"},
    "Borussia Dortmund":          {"adj_em": 15.0, "league": "BUNDESLIGA"},
    "RB Leipzig":                 {"adj_em": 14.5, "league": "BUNDESLIGA"},
    "VfB Stuttgart":              {"adj_em": 11.0, "league": "BUNDESLIGA"},
    "Eintracht Frankfurt":        {"adj_em":  9.0, "league": "BUNDESLIGA"},
    "Freiburg":                   {"adj_em":  6.0, "league": "BUNDESLIGA"},
    "Borussia Mönchengladbach":   {"adj_em":  5.0, "league": "BUNDESLIGA"},
    "Wolfsburg":                  {"adj_em":  2.0, "league": "BUNDESLIGA"},
    "Werder Bremen":              {"adj_em":  3.0, "league": "BUNDESLIGA"},
    "Hoffenheim":                 {"adj_em":  1.0, "league": "BUNDESLIGA"},
    "Augsburg":                   {"adj_em": -1.0, "league": "BUNDESLIGA"},
    "Mainz":                      {"adj_em": -3.0, "league": "BUNDESLIGA"},
    "Union Berlin":               {"adj_em": -4.0, "league": "BUNDESLIGA"},
    "Heidenheim":                 {"adj_em": -6.0, "league": "BUNDESLIGA"},
    "St. Pauli":                  {"adj_em": -8.0, "league": "BUNDESLIGA"},
    "Bochum":                     {"adj_em":-10.0, "league": "BUNDESLIGA"},
    "Holstein Kiel":              {"adj_em":-12.0, "league": "BUNDESLIGA"},

    # =========================================================================
    # Ligue 1 (~2024-25)
    # =========================================================================
    "Paris Saint-Germain": {"adj_em": 28.0, "league": "LIGUE1"},
    "Monaco":              {"adj_em": 18.0, "league": "LIGUE1"},
    "Marseille":           {"adj_em": 14.0, "league": "LIGUE1"},
    "Lyon":                {"adj_em": 12.0, "league": "LIGUE1"},
    "Lille":               {"adj_em": 13.5, "league": "LIGUE1"},
    "Nice":                {"adj_em": 10.0, "league": "LIGUE1"},
    "Brest":               {"adj_em":  9.0, "league": "LIGUE1"},
    "Lens":                {"adj_em":  8.0, "league": "LIGUE1"},
    "Rennes":              {"adj_em":  7.0, "league": "LIGUE1"},
    "Toulouse":            {"adj_em":  3.0, "league": "LIGUE1"},
    "Stade de Reims":      {"adj_em":  4.0, "league": "LIGUE1"},
    "Nantes":              {"adj_em":  1.0, "league": "LIGUE1"},
    "Strasbourg":          {"adj_em": -2.0, "league": "LIGUE1"},
    "Auxerre":             {"adj_em": -5.0, "league": "LIGUE1"},
    "Angers":              {"adj_em": -6.0, "league": "LIGUE1"},
    "Le Havre":            {"adj_em": -4.0, "league": "LIGUE1"},
    "Montpellier":         {"adj_em": -8.0, "league": "LIGUE1"},
    "Saint-Etienne":       {"adj_em":-12.0, "league": "LIGUE1"},

    # =========================================================================
    # Serie A (~2024-25)
    # =========================================================================
    "Inter Milan":    {"adj_em": 22.0, "league": "SERIE_A"},
    "Napoli":         {"adj_em": 20.0, "league": "SERIE_A"},
    "Atalanta":       {"adj_em": 18.0, "league": "SERIE_A"},
    "Juventus":       {"adj_em": 15.0, "league": "SERIE_A"},
    "AC Milan":       {"adj_em": 14.0, "league": "SERIE_A"},
    "Bologna":        {"adj_em": 11.0, "league": "SERIE_A"},
    "Lazio":          {"adj_em": 10.0, "league": "SERIE_A"},
    "Fiorentina":     {"adj_em":  9.0, "league": "SERIE_A"},
    "Roma":           {"adj_em":  8.0, "league": "SERIE_A"},
    "Torino":         {"adj_em":  4.0, "league": "SERIE_A"},
    "Udinese":        {"adj_em":  2.0, "league": "SERIE_A"},
    "Empoli":         {"adj_em": -2.0, "league": "SERIE_A"},
    "Genoa":          {"adj_em": -1.0, "league": "SERIE_A"},
    "Cagliari":       {"adj_em": -3.0, "league": "SERIE_A"},
    "Verona":         {"adj_em": -4.0, "league": "SERIE_A"},
    "Lecce":          {"adj_em": -5.0, "league": "SERIE_A"},
    "Parma":          {"adj_em": -6.0, "league": "SERIE_A"},
    "Monza":          {"adj_em": -7.0, "league": "SERIE_A"},
    "Como":           {"adj_em": -8.0, "league": "SERIE_A"},
    "Venezia":        {"adj_em":-10.0, "league": "SERIE_A"},

    # =========================================================================
    # La Liga (~2024-25)
    # =========================================================================
    "Real Madrid":      {"adj_em": 26.0, "league": "LA_LIGA"},
    "FC Barcelona":     {"adj_em": 24.0, "league": "LA_LIGA"},
    "Atletico Madrid":  {"adj_em": 18.0, "league": "LA_LIGA"},
    "Girona":           {"adj_em": 15.0, "league": "LA_LIGA"},
    "Athletic Club":    {"adj_em": 14.0, "league": "LA_LIGA"},
    "Villarreal":       {"adj_em": 12.0, "league": "LA_LIGA"},
    "Real Sociedad":    {"adj_em": 11.0, "league": "LA_LIGA"},
    "Real Betis":       {"adj_em": 10.0, "league": "LA_LIGA"},
    "Sevilla":          {"adj_em":  8.0, "league": "LA_LIGA"},
    "Osasuna":          {"adj_em":  6.0, "league": "LA_LIGA"},
    "Celta Vigo":       {"adj_em":  3.0, "league": "LA_LIGA"},
    "Getafe":           {"adj_em":  2.0, "league": "LA_LIGA"},
    "Rayo Vallecano":   {"adj_em":  1.0, "league": "LA_LIGA"},
    "Alaves":           {"adj_em": -2.0, "league": "LA_LIGA"},
    "Valencia":         {"adj_em": -4.0, "league": "LA_LIGA"},
    "Las Palmas":       {"adj_em": -5.0, "league": "LA_LIGA"},
    "Leganes":          {"adj_em": -6.0, "league": "LA_LIGA"},
    "Espanyol":         {"adj_em": -7.0, "league": "LA_LIGA"},
    "Real Valladolid":  {"adj_em":-10.0, "league": "LA_LIGA"},
}


# ---------------------------------------------------------------------------
# Aliases — short names / alternate spellings → canonical _TEAM_DATA key
# ---------------------------------------------------------------------------
_ALIASES: dict[str, str] = {
    # NBA
    "Warriors":              "Golden State Warriors",
    "Mavs":                  "Dallas Mavericks",
    "Thunder":               "Oklahoma City Thunder",
    "Celtics":               "Boston Celtics",
    "Cavs":                  "Cleveland Cavaliers",
    "Wolves":                "Minnesota Timberwolves",
    "Nuggets":               "Denver Nuggets",
    "Rockets":               "Houston Rockets",
    "Lakers":                "Los Angeles Lakers",
    "Mavericks":             "Dallas Mavericks",
    "Grizzlies":             "Memphis Grizzlies",
    "Pacers":                "Indiana Pacers",
    "Bucks":                 "Milwaukee Bucks",
    "Knicks":                "New York Knicks",
    "Clippers":              "Los Angeles Clippers",
    "Kings":                 "Sacramento Kings",
    "Spurs":                 "San Antonio Spurs",
    "Heat":                  "Miami Heat",
    "76ers":                 "Philadelphia 76ers",
    "Sixers":                "Philadelphia 76ers",
    "Suns":                  "Phoenix Suns",
    "Pelicans":              "New Orleans Pelicans",
    "Magic":                 "Orlando Magic",
    "Bulls":                 "Chicago Bulls",
    "Hawks":                 "Atlanta Hawks",
    "Raptors":               "Toronto Raptors",
    "Nets":                  "Brooklyn Nets",
    "Pistons":               "Detroit Pistons",
    "Jazz":                  "Utah Jazz",
    "Blazers":               "Portland Trail Blazers",
    "Trail Blazers":         "Portland Trail Blazers",
    "Hornets":               "Charlotte Hornets",
    "Wizards":               "Washington Wizards",
    "Timberwolves":          "Minnesota Timberwolves",
    # NHL
    "Panthers":              "Florida Panthers",
    "Jets":                  "Winnipeg Jets",
    "Caps":                  "Washington Capitals",
    "Capitals":              "Washington Capitals",
    "Golden Knights":        "Vegas Golden Knights",
    "Hurricanes":            "Carolina Hurricanes",
    "Canes":                 "Carolina Hurricanes",
    "Stars":                 "Dallas Stars",
    "Avs":                   "Colorado Avalanche",
    "Avalanche":             "Colorado Avalanche",
    "Devils":                "New Jersey Devils",
    "Leafs":                 "Toronto Maple Leafs",
    "Maple Leafs":           "Toronto Maple Leafs",
    "Bruins":                "Boston Bruins",
    "Lightning":             "Tampa Bay Lightning",
    "Bolts":                 "Tampa Bay Lightning",
    "Oilers":                "Edmonton Oilers",
    "Predators":             "Nashville Predators",
    "Preds":                 "Nashville Predators",
    "Kings":                 "Los Angeles Kings",
    "Wild":                  "Minnesota Wild",
    "Rangers":               "New York Rangers",
    "Senators":              "Ottawa Senators",
    "Sens":                  "Ottawa Senators",
    "Flames":                "Calgary Flames",
    "Penguins":              "Pittsburgh Penguins",
    "Pens":                  "Pittsburgh Penguins",
    "Kraken":                "Seattle Kraken",
    "Islanders":             "New York Islanders",
    "Canucks":               "Vancouver Canucks",
    "Red Wings":             "Detroit Red Wings",
    "Flyers":                "Philadelphia Flyers",
    "Blues":                 "St. Louis Blues",
    "Ducks":                 "Anaheim Ducks",
    "Sabres":                "Buffalo Sabres",
    "Blackhawks":            "Chicago Blackhawks",
    "Blue Jackets":          "Columbus Blue Jackets",
    "Sharks":                "San Jose Sharks",
    "Habs":                  "Montreal Canadiens",
    "Canadiens":             "Montreal Canadiens",
    # Soccer
    "PSG":                   "Paris Saint-Germain",
    "Man City":              "Manchester City",
    "Man Utd":               "Manchester United",
    "Man United":            "Manchester United",
    "Spurs":                 "Tottenham Hotspur",
    "Wolves":                "Wolverhampton",
    "BVB":                   "Borussia Dortmund",
    "Dortmund":              "Borussia Dortmund",
    "Leverkusen":            "Bayer Leverkusen",
    "Leipzig":               "RB Leipzig",
    "Bayern":                "Bayern Munich",
    "Frankfurt":             "Eintracht Frankfurt",
    "Stuttgart":             "VfB Stuttgart",
    "Gladbach":              "Borussia Mönchengladbach",
    "Barca":                 "FC Barcelona",
    "Barcelona":             "FC Barcelona",
    "Real":                  "Real Madrid",
    "Atletico":              "Atletico Madrid",
    "Betis":                 "Real Betis",
    "Sociedad":              "Real Sociedad",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_team_data(team_name: str) -> Optional[dict]:
    """Return raw efficiency dict for a team, or None if not in database."""
    name = team_name.strip()
    if name in _TEAM_DATA:
        return _TEAM_DATA[name]
    canonical = _ALIASES.get(name)
    if canonical and canonical in _TEAM_DATA:
        return _TEAM_DATA[canonical]
    lower = name.lower()
    for k in _TEAM_DATA:
        if k.lower() == lower:
            return _TEAM_DATA[k]
    return None


def get_efficiency_gap(home_team: str, away_team: str) -> float:
    """
    Return a 0-20 scaled efficiency gap for a matchup.

    Gap = (home_adj_em - away_adj_em + 30) / 60 * 20
    Clamped to [0.0, 20.0]. Gap 10.0 = evenly matched.

    Returns _UNKNOWN_GAP (8.0) if either team not in database.
    """
    home_data = get_team_data(home_team)
    away_data = get_team_data(away_team)
    if home_data is None or away_data is None:
        return _UNKNOWN_GAP
    differential = home_data["adj_em"] - away_data["adj_em"]
    gap = (differential + 30.0) / 60.0 * 20.0
    return max(0.0, min(20.0, gap))


def list_teams(league: Optional[str] = None) -> list[str]:
    """Return list of canonical team names, optionally filtered by league."""
    if league is None:
        return list(_TEAM_DATA.keys())
    upper = league.upper()
    return [name for name, data in _TEAM_DATA.items() if data.get("league") == upper]
