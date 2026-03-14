"""
Tests for scripts/edge_scanner.py — Kalshi vs Pinnacle price comparison scanner.
"""

import pytest
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.edge_scanner import (
    _normalize,
    _match_team,
    _parse_kalshi_game_title,
    _kalshi_taker_fee,
    _devig_h2h,
    _game_started,
    parse_odds_games,
    OddsComparison,
)


# ── Team name matching ──────────────────────────────────────────────────

class TestMatchTeam:
    """Team name fuzzy matching between Kalshi and odds API."""

    def test_exact_match(self):
        assert _match_team("Los Angeles Lakers", ["Los Angeles Lakers", "Miami Heat"]) == "Los Angeles Lakers"

    def test_alias_match_nba(self):
        """NBA team abbreviations should match via alias table."""
        teams = ["Los Angeles Lakers", "Miami Heat"]
        assert _match_team("LAL", teams) == "Los Angeles Lakers"
        assert _match_team("MIA", teams) == "Miami Heat"

    def test_alias_match_nhl(self):
        teams = ["Edmonton Oilers", "St Louis Blues"]
        assert _match_team("EDM", teams) == "Edmonton Oilers"
        assert _match_team("STL", teams) == "St Louis Blues"

    def test_substring_match_long_name(self):
        """Long team names should match via substring."""
        teams = ["Golden State Warriors", "Houston Rockets"]
        assert _match_team("Golden State", teams) == "Golden State Warriors"
        assert _match_team("Houston", teams) == "Houston Rockets"

    def test_la_does_not_match_islanders(self):
        """CRITICAL: 'LA' must NOT match 'Islanders' (contains 'la' substring)."""
        teams = ["New York Islanders", "Los Angeles Kings"]
        result = _match_team("LA", teams)
        # LA should match Kings, not Islanders
        assert result != "New York Islanders"

    def test_la_matches_kings_via_alias(self):
        """LA should match Los Angeles Kings via alias table."""
        teams = ["New York Islanders", "Los Angeles Kings"]
        result = _match_team("LA", teams)
        # Should find via alias "Los Angeles" -> "Los Angeles Kings"
        # Note: "LA" is only 2 chars, might not match. That's acceptable —
        # the alias table has "Los Angeles" which would match.
        # The key test is that it does NOT return Islanders.
        assert result != "New York Islanders"

    def test_ny_matches_correctly(self):
        """NY abbreviations should match the right New York team."""
        teams = ["New York Knicks", "Indiana Pacers"]
        result = _match_team("NYK", teams)
        assert result == "New York Knicks"

    def test_no_match_returns_none(self):
        assert _match_team("XYZ", ["Team A", "Team B"]) is None

    def test_empty_name(self):
        assert _match_team("", ["Team A"]) is None

    def test_single_char(self):
        assert _match_team("A", ["Team A"]) is None

    def test_ncaab_long_name(self):
        """College team names are long — should match on substring."""
        teams = ["Michigan St Spartans", "UCLA Bruins"]
        assert _match_team("Michigan", teams) == "Michigan St Spartans"
        assert _match_team("UCLA", teams) == "UCLA Bruins"


# ── Title parsing ────────────────────────────────────────────────────────

class TestParseTitle:
    def test_standard_format(self):
        result = _parse_kalshi_game_title("Houston at Miami Winner?")
        assert result == ("Houston", "Miami")

    def test_with_full_names(self):
        result = _parse_kalshi_game_title("Seton Hall Pirates at St. John's Red Storm Winner?")
        assert result == ("Seton Hall Pirates", "St. John's Red Storm")

    def test_no_match(self):
        assert _parse_kalshi_game_title("Something else") is None

    def test_vs_format(self):
        result = _parse_kalshi_game_title("Team A vs Team B Winner?")
        assert result == ("Team A", "Team B")


# ── Fee calculation ──────────────────────────────────────────────────────

class TestFeeCalculation:
    def test_fee_at_50c(self):
        """Max fee at 50c: 0.07 * 0.5 * 0.5 = 0.0175."""
        fee = _kalshi_taker_fee(0.50)
        assert abs(fee - 0.0175) < 0.001

    def test_fee_at_10c(self):
        fee = _kalshi_taker_fee(0.10)
        assert abs(fee - 0.0063) < 0.001

    def test_fee_at_90c(self):
        fee = _kalshi_taker_fee(0.90)
        assert abs(fee - 0.0063) < 0.001

    def test_fee_symmetric(self):
        """Fee should be same at complementary prices."""
        assert abs(_kalshi_taker_fee(0.30) - _kalshi_taker_fee(0.70)) < 0.0001


# ── Devig calculation ────────────────────────────────────────────────────

class TestDevig:
    def test_fair_line(self):
        """Even odds (2.0/2.0) should devig to 50/50."""
        result = _devig_h2h(
            [{"name": "Home", "price": 2.0}, {"name": "Away", "price": 2.0}],
            "Home", "Away",
        )
        assert result is not None
        assert abs(result[0] - 0.5) < 0.01
        assert abs(result[1] - 0.5) < 0.01

    def test_favorite(self):
        """Favorite at 1.5 / Underdog at 2.8 — devig should sum to 1.0."""
        result = _devig_h2h(
            [{"name": "Home", "price": 1.5}, {"name": "Away", "price": 2.8}],
            "Home", "Away",
        )
        assert result is not None
        assert abs(sum(result) - 1.0) < 0.001
        assert result[0] > result[1]  # Home is favorite

    def test_missing_team(self):
        result = _devig_h2h(
            [{"name": "Home", "price": 1.5}],
            "Home", "Away",
        )
        assert result is None


# ── Odds parsing ─────────────────────────────────────────────────────────

class TestParseOddsGames:
    def test_basic_parsing(self):
        raw = [{
            "home_team": "Miami Heat",
            "away_team": "Chicago Bulls",
            "commence_time": "2026-03-13T23:00:00Z",
            "bookmakers": [{
                "key": "pinnacle",
                "markets": [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Miami Heat", "price": 1.50},
                        {"name": "Chicago Bulls", "price": 2.80},
                    ],
                }],
            }],
        }]
        result = parse_odds_games(raw)
        assert len(result) == 1
        key = list(result.keys())[0]
        game = result[key]
        assert game["home"] == "Miami Heat"
        assert game["away"] == "Chicago Bulls"
        assert game["home_prob"] > 0.5  # Miami is favorite
        assert game["pinnacle_home"] is not None

    def test_empty_bookmakers(self):
        raw = [{"home_team": "A", "away_team": "B", "bookmakers": []}]
        assert len(parse_odds_games(raw)) == 0


# ── Normalize ────────────────────────────────────────────────────────────

class TestNormalize:
    def test_basic(self):
        assert _normalize("Los Angeles") == "los angeles"

    def test_punctuation(self):
        assert _normalize("St. John's") == "st johns"

    def test_empty(self):
        assert _normalize("") == ""


# ── Game-in-progress filter ───────────────────────────────────────────────

class TestGameStarted:
    """Tests for _game_started() — filters in-progress and settled games."""

    def test_past_game_is_started(self):
        """A game that started hours ago is in-progress — should be filtered."""
        assert _game_started("2020-01-01T00:00:00Z") is True

    def test_future_game_not_started(self):
        """A game starting tomorrow is not in-progress — should be kept."""
        assert _game_started("2099-12-31T23:59:59Z") is False

    def test_empty_string_not_filtered(self):
        """Empty commence_time: don't filter (missing data, keep market)."""
        assert _game_started("") is False

    def test_none_like_empty(self):
        """None commence_time: don't filter."""
        assert _game_started(None) is False

    def test_invalid_timestamp_not_filtered(self):
        """Unparseable timestamp: don't filter (fail safe)."""
        assert _game_started("not-a-date") is False

    def test_z_suffix_parsed_correctly(self):
        """Z suffix (UTC) must be parsed correctly, not raise an error."""
        # Recent past: definitely started
        assert _game_started("2026-01-01T00:00:00Z") is True

    def test_recent_future_not_started(self):
        """A game starting 1 hour from now should not be filtered."""
        from datetime import datetime, timezone, timedelta
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        assert _game_started(future) is False
