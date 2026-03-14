"""
Tests for scripts/cpi_release_monitor.py

Research tool tests — validates BLS CPI parsing and Kalshi price change detection.
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.cpi_release_monitor import detect_price_change, summarize_markets


# ── Test data ───────────────────────────────────────────────────────────────

SAMPLE_MARKETS = [
    {'ticker': 'KXFEDDECISION-26MAR19-HOLD', 'subtitle': 'Hold rates',
     'yes_bid': 0.92, 'yes_ask': 0.93, 'volume': 11000000, 'close_time': '2026-03-19T18:00:00Z'},
    {'ticker': 'KXFEDDECISION-26MAR19-CUT25', 'subtitle': 'Cut 25bp',
     'yes_bid': 0.06, 'yes_ask': 0.07, 'volume': 500000, 'close_time': '2026-03-19T18:00:00Z'},
    {'ticker': 'KXFEDDECISION-26APR30-HOLD', 'subtitle': 'Hold April',
     'yes_bid': 0.88, 'yes_ask': 0.89, 'volume': 200000, 'close_time': '2026-04-30T18:00:00Z'},
]


# ── detect_price_change tests ───────────────────────────────────────────────

class TestDetectPriceChange:

    def test_no_change_returns_empty(self):
        """Same prices before and after: no changes detected."""
        result = detect_price_change(SAMPLE_MARKETS, SAMPLE_MARKETS)
        assert result == []

    def test_large_bid_move_detected(self):
        """A 7c drop in YES bid (Hold repricing after CPI) should be detected."""
        after = [
            {'ticker': 'KXFEDDECISION-26MAR19-HOLD', 'subtitle': 'Hold rates',
             'yes_bid': 0.85, 'yes_ask': 0.86},
            {'ticker': 'KXFEDDECISION-26MAR19-CUT25', 'subtitle': 'Cut 25bp',
             'yes_bid': 0.13, 'yes_ask': 0.14},
            {'ticker': 'KXFEDDECISION-26APR30-HOLD', 'subtitle': 'Hold April',
             'yes_bid': 0.88, 'yes_ask': 0.89},
        ]
        result = detect_price_change(SAMPLE_MARKETS, after)
        assert len(result) == 2  # both March markets repriced

    def test_small_1c_change_not_detected(self):
        """A 1c move is noise — below the 2c threshold."""
        after = [
            {'ticker': 'KXFEDDECISION-26MAR19-HOLD', 'subtitle': 'Hold rates',
             'yes_bid': 0.93, 'yes_ask': 0.94},  # +1c each — below threshold
            {'ticker': 'KXFEDDECISION-26MAR19-CUT25', 'subtitle': 'Cut 25bp',
             'yes_bid': 0.06, 'yes_ask': 0.07},
            {'ticker': 'KXFEDDECISION-26APR30-HOLD', 'subtitle': 'Hold April',
             'yes_bid': 0.88, 'yes_ask': 0.89},
        ]
        result = detect_price_change(SAMPLE_MARKETS, after)
        assert result == []

    def test_exactly_2c_change_detected(self):
        """2c is the threshold — should be detected."""
        after = [
            {'ticker': 'KXFEDDECISION-26MAR19-HOLD', 'subtitle': 'Hold rates',
             'yes_bid': 0.94, 'yes_ask': 0.95},  # +2c — exactly at threshold
            {'ticker': 'KXFEDDECISION-26MAR19-CUT25', 'subtitle': 'Cut 25bp',
             'yes_bid': 0.06, 'yes_ask': 0.07},
            {'ticker': 'KXFEDDECISION-26APR30-HOLD', 'subtitle': 'Hold April',
             'yes_bid': 0.88, 'yes_ask': 0.89},
        ]
        result = detect_price_change(SAMPLE_MARKETS, after)
        assert len(result) == 1

    def test_new_ticker_in_after_ignored(self):
        """A ticker present in 'after' but not 'before' should be ignored."""
        after = SAMPLE_MARKETS + [
            {'ticker': 'KXFEDDECISION-26JUN11-HOLD', 'subtitle': 'Hold June',
             'yes_bid': 0.70, 'yes_ask': 0.71},
        ]
        result = detect_price_change(SAMPLE_MARKETS, after)
        assert result == []

    def test_empty_before_returns_empty(self):
        """Empty baseline: no changes to detect."""
        result = detect_price_change([], SAMPLE_MARKETS)
        assert result == []

    def test_empty_after_returns_empty(self):
        """Empty after-snapshot: no changes detected."""
        result = detect_price_change(SAMPLE_MARKETS, [])
        assert result == []

    def test_ask_change_also_detected(self):
        """A move in ask alone (bid unchanged) should be detected if >= 2c."""
        after = [
            {'ticker': 'KXFEDDECISION-26MAR19-HOLD', 'subtitle': 'Hold rates',
             'yes_bid': 0.92, 'yes_ask': 0.95},  # ask +2c, bid unchanged
            {'ticker': 'KXFEDDECISION-26MAR19-CUT25', 'subtitle': 'Cut 25bp',
             'yes_bid': 0.06, 'yes_ask': 0.07},
            {'ticker': 'KXFEDDECISION-26APR30-HOLD', 'subtitle': 'Hold April',
             'yes_bid': 0.88, 'yes_ask': 0.89},
        ]
        result = detect_price_change(SAMPLE_MARKETS, after)
        assert len(result) == 1


# ── summarize_markets tests ─────────────────────────────────────────────────

class TestSummarizeMarkets:

    def test_empty_markets(self):
        assert summarize_markets([]) == 'no markets'

    def test_single_market(self):
        summary = summarize_markets(SAMPLE_MARKETS[:1])
        assert 'Hold rates' in summary
        assert 'c' in summary  # should show bid-ask in cents

    def test_shows_first_three_only(self):
        """Should show at most 3 markets even if more exist."""
        result = summarize_markets(SAMPLE_MARKETS)
        # Three markets separated by ' | '
        assert result.count('|') == 2  # 3 markets = 2 separators

    def test_bid_ask_format(self):
        """Should show bid and ask as integers (in cents)."""
        summary = summarize_markets(SAMPLE_MARKETS[:1])
        assert '92-93c' in summary  # 0.92 bid, 0.93 ask
