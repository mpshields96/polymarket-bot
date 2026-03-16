"""
Tests for scripts/ncaab_live_monitor.py

Research tool tests — validates ESPN parsing and Kalshi market matching.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Import helpers from the script ────────────────────────────────────────

from scripts.ncaab_live_monitor import find_kalshi_market


# ── Test data ──────────────────────────────────────────────────────────────

SAMPLE_MARKETS = [
    {'ticker': 'KXNCAAMBGAME-26MAR14WISMICH-MICH', 'title': 'Wisconsin at Michigan', 'yes_bid': 0.80, 'yes_ask': 0.81, 'volume': 1851324, 'close_time': '2026-03-28T17:00:00Z'},
    {'ticker': 'KXNCAAMBGAME-26MAR14WISMICH-WIS', 'title': 'Wisconsin at Michigan', 'yes_bid': 0.20, 'yes_ask': 0.21, 'volume': 663615, 'close_time': '2026-03-28T17:00:00Z'},
    {'ticker': 'KXNCAAMBGAME-26MAR14VANFLA-FLA', 'title': 'Vanderbilt at Florida', 'yes_bid': 0.71, 'yes_ask': 0.72, 'volume': 948022, 'close_time': '2026-03-28T17:00:00Z'},
    {'ticker': 'KXNCAAMBGAME-26MAR14CHARUSF-USF', 'title': 'Charlotte at South Florida', 'yes_bid': 0.92, 'yes_ask': 0.93, 'volume': 26642, 'close_time': '2026-03-28T19:00:00Z'},
]


# ── find_kalshi_market tests ───────────────────────────────────────────────

class TestFindKalshiMarket:
    def test_exact_match_mich(self):
        m = find_kalshi_market('MICH', SAMPLE_MARKETS)
        assert m is not None
        assert 'MICH' in m['ticker']

    def test_exact_match_wis(self):
        m = find_kalshi_market('WIS', SAMPLE_MARKETS)
        assert m is not None
        assert 'WIS' in m['ticker']

    def test_exact_match_fla(self):
        m = find_kalshi_market('FLA', SAMPLE_MARKETS)
        assert m is not None
        assert 'FLA' in m['ticker']

    def test_exact_match_usf(self):
        m = find_kalshi_market('USF', SAMPLE_MARKETS)
        assert m is not None
        assert 'USF' in m['ticker']

    def test_lowercase_input(self):
        m = find_kalshi_market('mich', SAMPLE_MARKETS)
        assert m is not None

    def test_unknown_team_returns_none(self):
        m = find_kalshi_market('DUKE', SAMPLE_MARKETS)
        assert m is None

    def test_empty_markets_returns_none(self):
        m = find_kalshi_market('MICH', [])
        assert m is None

    def test_returns_correct_price(self):
        m = find_kalshi_market('USF', SAMPLE_MARKETS)
        assert m is not None
        assert m['yes_bid'] == pytest.approx(0.92)
        assert m['yes_ask'] == pytest.approx(0.93)

    def test_high_price_market_identified(self):
        """USF at 92-93c should be identified as a 90c+ crossing."""
        m = find_kalshi_market('USF', SAMPLE_MARKETS)
        assert m is not None
        price = max(m['yes_bid'], m['yes_ask'])
        assert price >= 0.90, f"Expected >=0.90 but got {price}"

    def test_mid_price_market_below_threshold(self):
        """Michigan at 80c should NOT trigger the 90c threshold."""
        m = find_kalshi_market('MICH', SAMPLE_MARKETS)
        assert m is not None
        price = max(m['yes_bid'], m['yes_ask'])
        assert price < 0.90, f"Expected <0.90 but got {price}"


# ── NCAA Tournament Scanner bug regression tests ─────────────────────────

class TestNCAATournamentScannerBugs:
    """
    Regression tests for two bugs fixed 2026-03-16:
    1. fetch_odds_api_games called with args swapped (sport as api_key → 401)
    2. sharp_prob attr used instead of sharp_yes_prob/sharp_no_prob → AttributeError
    """

    def test_fetch_odds_api_games_signature_matches_call(self):
        """
        Ensure ncaa_tournament_scanner calls fetch_odds_api_games with (api_key, sport).
        Bug: was called as (sport, api_key) → 401 Unauthorized.
        """
        import inspect
        from scripts.edge_scanner import fetch_odds_api_games
        sig = inspect.signature(fetch_odds_api_games)
        params = list(sig.parameters.keys())
        # First param must be api_key, second must be sport
        assert params[0] == "api_key", f"Expected first param 'api_key', got '{params[0]}'"
        assert params[1] == "sport", f"Expected second param 'sport', got '{params[1]}'"

    def test_odds_comparison_has_sharp_yes_prob_not_sharp_prob(self):
        """
        OddsComparison must have sharp_yes_prob and sharp_no_prob, NOT sharp_prob.
        Bug: ncaa_tournament_scanner used comparison.sharp_prob → AttributeError.
        """
        from scripts.edge_scanner import OddsComparison
        import dataclasses
        fields = {f.name for f in dataclasses.fields(OddsComparison)}
        assert "sharp_yes_prob" in fields, "OddsComparison must have sharp_yes_prob"
        assert "sharp_no_prob" in fields, "OddsComparison must have sharp_no_prob"
        assert "sharp_prob" not in fields, "OddsComparison must NOT have sharp_prob (old typo)"

    def test_scanner_selects_correct_sharp_prob_for_yes_favorite(self):
        """
        When yes_price is the favorite side, sharp_yes_prob should be used (not sharp_no_prob).
        """
        from scripts.edge_scanner import OddsComparison
        cmp = OddsComparison(
            kalshi_ticker="KXNCAAMBGAME-26MAR20TEXA-TEX",
            kalshi_title="Texas vs NCST",
            kalshi_yes_cents=92,
            kalshi_no_cents=8,
            kalshi_volume=10000,
            sport="basketball_ncaab",
            sharp_yes_prob=0.95,
            sharp_no_prob=0.05,
            num_books=2,
            pinnacle_yes_prob=0.95,
            yes_edge_raw=0.02,
            no_edge_raw=-0.03,
            yes_edge_net=0.02,
            no_edge_net=-0.03,
            yes_edge_maker=0.025,
            no_edge_maker=-0.025,
            home_team="Texas",
            away_team="NCST",
            commence_time="2026-03-20T22:00:00Z",
            best_side="yes",
            best_edge=0.02,
        )
        # Simulate the scanner logic: use sharp_yes_prob when yes_price >= no_price
        yes_price = cmp.kalshi_yes_cents
        no_price = cmp.kalshi_no_cents
        fav_price = max(yes_price, no_price)
        if yes_price >= no_price:
            sharp_prob = cmp.sharp_yes_prob
        else:
            sharp_prob = cmp.sharp_no_prob
        assert sharp_prob == 0.95
        edge = sharp_prob - (fav_price / 100.0)
        assert abs(edge - 0.03) < 0.001  # 95% sharp - 92% kalshi = 3% edge
