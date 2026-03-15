"""Tests for soccer_candle_analyzer.py — Research script."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scripts.soccer_candle_analyzer import analyze_candles


def _make_candle(ts: int, bid_close: float, bid_high: float, vol: float = 100):
    return {
        "end_period_ts": ts,
        "yes_bid": {
            "close_dollars": str(bid_close),
            "high_dollars": str(bid_high),
            "open_dollars": str(bid_close),
            "low_dollars": str(bid_close),
        },
        "volume_fp": str(vol),
    }


class TestAnalyzeCandles:
    def test_empty_returns_empty(self):
        assert analyze_candles([]) == {}

    def test_no_threshold_crossing(self):
        candles = [_make_candle(1000 + i * 60, 0.75, 0.79) for i in range(30)]
        result = analyze_candles(candles, threshold=0.90)
        assert result["first_crossing_ts"] is None
        assert result["minutes_at_threshold"] == 0
        assert result["max_bid"] == 0.79

    def test_first_crossing_detected(self):
        candles = [_make_candle(1000 + i * 60, 0.75, 0.79) for i in range(10)]
        candles.append(_make_candle(1000 + 600, 0.92, 0.95))  # 10th candle crosses
        result = analyze_candles(candles, threshold=0.90)
        assert result["first_crossing_ts"] == 1000 + 600
        assert result["first_crossing_price"] == 0.92

    def test_minutes_at_threshold(self):
        candles = [_make_candle(1000 + i * 60, 0.75, 0.79) for i in range(5)]
        for i in range(5, 15):
            candles.append(_make_candle(1000 + i * 60, 0.93, 0.95))
        result = analyze_candles(candles, threshold=0.90)
        assert result["minutes_at_threshold"] == 10

    def test_minutes_to_crossing_calculated(self):
        # First candle at ts=0, crossing at ts=1800 (30 min later)
        candles = [_make_candle(i * 60, 0.75, 0.79) for i in range(30)]
        candles.append(_make_candle(1800, 0.92, 0.95))
        result = analyze_candles(candles)
        assert result["minutes_to_crossing"] == 30.0

    def test_pre_game_price_from_first_candles(self):
        candles = [_make_candle(i * 60, 0.72, 0.74, vol=50) for i in range(10)]
        candles += [_make_candle(600 + i * 60, 0.80, 0.82, vol=500) for i in range(20)]
        result = analyze_candles(candles)
        # Pre-game price should reflect the early candles at ~0.72
        assert 0.70 <= result["pre_game_price"] <= 0.80

    def test_max_bid_tracked_correctly(self):
        candles = [_make_candle(i * 60, 0.70, 0.72) for i in range(5)]
        candles.append(_make_candle(300, 0.85, 0.97))
        candles.append(_make_candle(360, 0.99, 0.99))
        result = analyze_candles(candles)
        assert result["max_bid"] == 0.99

    def test_custom_threshold(self):
        candles = [_make_candle(i * 60, 0.82, 0.84) for i in range(20)]
        candles.append(_make_candle(1200, 0.86, 0.90))
        result_80 = analyze_candles(candles, threshold=0.80)
        result_90 = analyze_candles(candles, threshold=0.90)
        # Should cross 80c but barely
        assert result_80["first_crossing_ts"] is not None
        # Should cross 90c at last candle only
        assert result_90["first_crossing_ts"] == 1200

    def test_single_candle(self):
        candles = [_make_candle(1000, 0.95, 0.97, vol=200)]
        result = analyze_candles(candles)
        assert result["first_crossing_ts"] == 1000
        assert result["minutes_to_crossing"] == 0.0

    def test_threshold_drop_then_recovery(self):
        # Cross 90c, drop below, cross again — should record FIRST crossing only
        candles = (
            [_make_candle(i * 60, 0.75, 0.79) for i in range(5)]
            + [_make_candle(300, 0.93, 0.95)]  # first crossing
            + [_make_candle(360, 0.75, 0.79)]  # drops below
            + [_make_candle(420, 0.93, 0.95)]  # second crossing
        )
        result = analyze_candles(candles)
        assert result["first_crossing_ts"] == 300

    def test_zero_volume_candles_ignored_for_pre_game_price(self):
        candles = [_make_candle(i * 60, 0.77, 0.79, vol=0) for i in range(5)]
        candles += [_make_candle(300 + i * 60, 0.77, 0.79, vol=100) for i in range(10)]
        result = analyze_candles(candles)
        assert result["pre_game_price"] > 0
