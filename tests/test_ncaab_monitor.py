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
