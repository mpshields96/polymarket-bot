"""Tests for sports sniper strategy — ESPN API + Kalshi game-winner markets."""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone


class TestESPNFeed(unittest.TestCase):
    """ESPN scoreboard API parsing."""

    def _make_event(self, away_abbr, home_abbr, away_score, home_score, period, clock, status_name):
        return {
            "competitions": [{
                "competitors": [
                    {"homeAway": "home", "score": str(home_score), "team": {"abbreviation": home_abbr}},
                    {"homeAway": "away", "score": str(away_score), "team": {"abbreviation": away_abbr}},
                ],
                "status": {
                    "period": period,
                    "displayClock": clock,
                    "type": {"name": status_name},
                },
            }]
        }

    def test_parse_mlb_game_in_progress(self):
        from src.data.espn import ESPNFeed
        ev = self._make_event("PIT", "NYM", 2, 5, 7, "0:00", "STATUS_IN_PROGRESS")
        game = ESPNFeed._parse_game(ev, sport="mlb")
        self.assertEqual(game["away"], "PIT")
        self.assertEqual(game["home"], "NYM")
        self.assertEqual(game["away_score"], 2)
        self.assertEqual(game["home_score"], 5)
        self.assertEqual(game["period"], 7)
        self.assertEqual(game["status"], "in_progress")

    def test_parse_nba_game_in_progress(self):
        from src.data.espn import ESPNFeed
        ev = self._make_event("CHI", "OKC", 85, 112, 4, "2:30", "STATUS_IN_PROGRESS")
        game = ESPNFeed._parse_game(ev, sport="nba")
        self.assertEqual(game["period"], 4)
        self.assertEqual(game["home_score"], 112)
        self.assertEqual(game["lead"], 27)  # OKC leads by 27

    def test_parse_final_game_skipped(self):
        from src.data.espn import ESPNFeed
        ev = self._make_event("PIT", "NYM", 2, 7, 9, "0:00", "STATUS_FINAL")
        game = ESPNFeed._parse_game(ev, sport="mlb")
        self.assertIsNone(game)  # Final games not returned

    def test_parse_pre_game_skipped(self):
        from src.data.espn import ESPNFeed
        ev = self._make_event("WSH", "CHC", 0, 0, 0, "0:00", "STATUS_SCHEDULED")
        game = ESPNFeed._parse_game(ev, sport="mlb")
        self.assertIsNone(game)

    def test_lead_computed_correctly(self):
        from src.data.espn import ESPNFeed
        ev = self._make_event("LAL", "GSW", 100, 95, 4, "1:00", "STATUS_IN_PROGRESS")
        game = ESPNFeed._parse_game(ev, sport="nba")
        self.assertEqual(game["leading_team"], "LAL")  # away team leads
        self.assertEqual(game["lead"], 5)


class TestSportsSniperSignal(unittest.TestCase):
    """Signal generation logic."""

    def _game(self, sport, period, lead, leading_team, home, away, price_cents):
        return {
            "sport": sport,
            "home": home,
            "away": away,
            "period": period,
            "lead": lead,
            "leading_team": leading_team,
            "home_score": 5 + lead if leading_team == home else 5,
            "away_score": 5 if leading_team == home else 5 + lead,
            "status": "in_progress",
        }, price_cents

    def test_mlb_late_inning_large_lead_fires(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("mlb", 8, 5, "NYM", "NYM", "PIT", 93)
        sig = s.evaluate(game, price)
        self.assertIsNotNone(sig)
        self.assertEqual(sig["side"], "yes")
        self.assertEqual(sig["team"], "NYM")

    def test_mlb_early_inning_no_signal(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("mlb", 2, 5, "NYM", "NYM", "PIT", 93)
        sig = s.evaluate(game, price)
        self.assertIsNone(sig)  # Only 2nd inning — too early

    def test_mlb_small_lead_no_signal(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("mlb", 8, 2, "NYM", "NYM", "PIT", 93)
        sig = s.evaluate(game, price)
        self.assertIsNone(sig)  # Lead < 5 runs

    def test_nba_q4_large_lead_fires(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("nba", 4, 20, "OKC", "OKC", "CHI", 91)
        sig = s.evaluate(game, price)
        self.assertIsNotNone(sig)

    def test_nba_q3_no_signal(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("nba", 3, 20, "OKC", "OKC", "CHI", 93)
        sig = s.evaluate(game, price)
        self.assertIsNone(sig)  # Not Q4 yet

    def test_nhl_3rd_period_3goal_lead_fires(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("nhl", 3, 3, "COL", "COL", "WPG", 92)
        sig = s.evaluate(game, price)
        self.assertIsNotNone(sig)

    def test_price_below_floor_no_signal(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("mlb", 8, 5, "NYM", "NYM", "PIT", 88)
        sig = s.evaluate(game, price)
        self.assertIsNone(sig)  # Below 90c floor

    def test_price_above_ceiling_no_signal(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("mlb", 8, 5, "NYM", "NYM", "PIT", 96)
        sig = s.evaluate(game, price)
        self.assertIsNone(sig)  # Above 95c ceiling

    def test_away_team_leading_resolved_correctly(self):
        from src.strategies.sports_sniper import SportsSniper
        s = SportsSniper()
        game, price = self._game("nba", 4, 18, "LAL", "GSW", "LAL", 90)
        sig = s.evaluate(game, price)
        self.assertIsNotNone(sig)
        self.assertEqual(sig["team"], "LAL")  # Away team leading


class TestKalshiTickerMatching(unittest.TestCase):
    """Kalshi game-winner ticker → ESPN team matching."""

    def test_nba_ticker_parsed(self):
        from src.strategies.sports_sniper import parse_kalshi_game_ticker
        result = parse_kalshi_game_ticker("KXNBAGAME-26MAR27CHIOKC-CHI")
        self.assertEqual(result["series"], "KXNBAGAME")
        self.assertEqual(result["sport"], "nba")
        self.assertEqual(result["team"], "CHI")
        self.assertIn("CHI", result["teams"])
        self.assertIn("OKC", result["teams"])

    def test_mlb_ticker_parsed(self):
        from src.strategies.sports_sniper import parse_kalshi_game_ticker
        result = parse_kalshi_game_ticker("KXMLBGAME-26MAR261315PITNYM-NYM")
        self.assertEqual(result["sport"], "mlb")
        self.assertEqual(result["team"], "NYM")

    def test_nhl_ticker_parsed(self):
        from src.strategies.sports_sniper import parse_kalshi_game_ticker
        result = parse_kalshi_game_ticker("KXNHLGAME-26MAR26COLWPG-COL")
        self.assertEqual(result["sport"], "nhl")
        self.assertEqual(result["team"], "COL")

    def test_unknown_ticker_returns_none(self):
        from src.strategies.sports_sniper import parse_kalshi_game_ticker
        result = parse_kalshi_game_ticker("KXBTC15M-26MAR261830-30")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
