"""
Tests for scripts/weather_edge_scanner.py

Covers:
  - parse_weather_bracket: all title formats (>, <, range, or higher, or lower)
  - gefs_prob_yes: probability computation for all directions
  - Edge calculation correctness
"""

import math
import sys
from pathlib import Path

# Bootstrap path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.weather_edge_scanner import (
    parse_weather_bracket,
    gefs_prob_yes,
    kalshi_taker_fee,
    CITIES,
)


# ── parse_weather_bracket ─────────────────────────────────────────────────


class TestParseWeatherBracket:
    """parse_weather_bracket should handle all market title formats."""

    def test_above_format_gt_symbol(self):
        title = "Will the **high temp in LA** be >79° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 79.0
        assert upper == float("inf")
        assert direction == "above"

    def test_below_format_lt_symbol(self):
        title = "Will the **high temp in LA** be <72° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == float("-inf")
        assert upper == 72.0
        assert direction == "below"

    def test_bracket_range_format(self):
        title = "Will the **high temp in LA** be 78-79° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 78.0
        assert upper == 79.0
        assert direction == "between"

    def test_bracket_range_format_integer(self):
        title = "Will the **high temp in NYC** be 47-48° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 47.0
        assert upper == 48.0
        assert direction == "between"

    def test_or_higher_format(self):
        title = "Will high temperature be 68° or higher today?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 68.0
        assert upper == float("inf")
        assert direction == "above"

    def test_or_lower_format(self):
        title = "Will high temperature be 63° or lower today?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == float("-inf")
        assert upper == 63.0
        assert direction == "below"

    def test_nyc_below_47_format(self):
        title = "Will the **high temp in NYC** be <47° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == float("-inf")
        assert upper == 47.0
        assert direction == "below"

    def test_decimal_bracket(self):
        title = "Will the **high temp in Denver** be 51-52° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 51.0
        assert upper == 52.0
        assert direction == "between"

    def test_unparseable_returns_none(self):
        assert parse_weather_bracket("Something completely different") is None
        assert parse_weather_bracket("Will this market resolve YES?") is None
        assert parse_weather_bracket("") is None

    def test_chicago_format_no_bold(self):
        # Chicago markets may lack **bold** markers
        title = "Will the high temp in Chicago be <60° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert upper == 60.0
        assert direction == "below"

    def test_miami_bracket_range(self):
        title = "Will the **high temp in Miami** be 79-80° on Mar 15, 2026?"
        result = parse_weather_bracket(title)
        assert result is not None
        lower, upper, direction = result
        assert lower == 79.0
        assert upper == 80.0
        assert direction == "between"


# ── gefs_prob_yes ─────────────────────────────────────────────────────────


class TestGefsProbYes:
    """gefs_prob_yes should compute empirical probability from ensemble members."""

    def test_above_all_members_above(self):
        # All members above threshold → probability approaches 1.0
        temps = [80.0, 81.0, 82.0, 83.0, 79.5] * 6 + [80.0]  # 31 members
        prob = gefs_prob_yes(temps, 79.0, float("inf"), "above")
        assert prob > 0.95

    def test_above_no_members_above(self):
        # No members above threshold → probability approaches 0.0
        temps = [70.0, 71.0, 72.0, 68.0, 69.0] * 6 + [70.0]  # 31 members
        prob = gefs_prob_yes(temps, 79.0, float("inf"), "above")
        assert prob < 0.05

    def test_above_half_members_above(self):
        # ~50% members above threshold
        temps = [78.0] * 15 + [80.0] * 16  # 31 members, 16 above 79
        prob = gefs_prob_yes(temps, 79.0, float("inf"), "above")
        assert 0.4 < prob < 0.6

    def test_below_all_members_below(self):
        temps = [45.0, 46.0, 44.0, 43.0, 45.5] * 6 + [44.5]
        prob = gefs_prob_yes(temps, float("-inf"), 47.0, "below")
        assert prob > 0.95

    def test_below_no_members_below(self):
        temps = [50.0, 51.0, 52.0, 53.0, 54.0] * 6 + [50.0]
        prob = gefs_prob_yes(temps, float("-inf"), 47.0, "below")
        assert prob < 0.05

    def test_between_all_members_in_bracket(self):
        temps = [78.5, 78.7, 78.9, 79.0, 78.6] * 6 + [78.8]
        prob = gefs_prob_yes(temps, 78.0, 79.0, "between")
        assert prob > 0.90

    def test_between_no_members_in_bracket(self):
        temps = [80.0, 81.0, 82.0, 83.0, 84.0] * 6 + [80.5]
        prob = gefs_prob_yes(temps, 78.0, 79.0, "between")
        assert prob < 0.05

    def test_empty_temps_returns_half(self):
        prob = gefs_prob_yes([], 79.0, float("inf"), "above")
        assert prob == 0.5

    def test_laplace_smoothing_prevents_zero(self):
        # No members above threshold, but probability should not be exactly 0
        temps = [70.0] * 31
        prob = gefs_prob_yes(temps, 79.0, float("inf"), "above")
        assert prob > 0.0
        assert prob < 0.05

    def test_laplace_smoothing_prevents_one(self):
        # All members above threshold, but probability should not be exactly 1
        temps = [85.0] * 31
        prob = gefs_prob_yes(temps, 79.0, float("inf"), "above")
        assert prob < 1.0
        assert prob > 0.95


# ── kalshi_taker_fee ──────────────────────────────────────────────────────


class TestKalshiTakerFee:
    """kalshi_taker_fee should return 7% * P * (1-P)."""

    def test_fee_at_50c_is_max(self):
        fee = kalshi_taker_fee(50)
        assert abs(fee - 0.07 * 0.5 * 0.5) < 1e-9

    def test_fee_at_90c(self):
        fee = kalshi_taker_fee(90)
        assert abs(fee - 0.07 * 0.9 * 0.1) < 1e-9

    def test_fee_at_99c_is_small(self):
        fee = kalshi_taker_fee(99)
        assert fee < 0.01  # Less than 1%

    def test_fee_at_5c_is_small(self):
        fee = kalshi_taker_fee(5)
        assert fee < 0.01


# ── Edge calculation sanity ───────────────────────────────────────────────


class TestEdgeCalculation:
    """Edge = gefs_prob - kalshi_prob - fee should match expectations."""

    def test_strong_yes_edge_when_gefs_much_higher(self):
        """GEFS=80%, Kalshi=5% → YES edge should be large positive."""
        gefs_p = 0.80
        yes_price = 5
        fee = kalshi_taker_fee(yes_price)
        edge_yes = gefs_p - (yes_price / 100.0) - fee
        assert edge_yes > 0.70  # Should be ~75% edge

    def test_strong_no_edge_when_gefs_much_lower(self):
        """GEFS=3%, Kalshi=70% YES → NO edge should be large positive."""
        gefs_p = 0.03
        yes_price = 70
        no_price = 100 - yes_price
        fee = kalshi_taker_fee(no_price)
        edge_no = (1.0 - gefs_p) - (no_price / 100.0) - fee
        assert edge_no > 0.60

    def test_no_edge_when_gefs_matches_kalshi(self):
        """GEFS=50%, Kalshi=50% → net edge should be ~0 or negative (fee eats it)."""
        gefs_p = 0.50
        yes_price = 50
        fee = kalshi_taker_fee(yes_price)
        edge_yes = gefs_p - (yes_price / 100.0) - fee
        assert edge_yes < 0  # Fee makes it slightly negative


# ── City config validation ────────────────────────────────────────────────


class TestCityConfigs:
    """All city configs should have required fields."""

    def test_all_cities_present(self):
        for key in ["nyc", "lax", "chi", "den", "mia"]:
            assert key in CITIES

    def test_all_cities_have_required_fields(self):
        for city_key, cfg in CITIES.items():
            assert "latitude" in cfg, f"{city_key} missing latitude"
            assert "longitude" in cfg, f"{city_key} missing longitude"
            assert "timezone" in cfg, f"{city_key} missing timezone"
            assert "series" in cfg, f"{city_key} missing series"
            assert cfg["series"].startswith("KXHIGH"), f"{city_key} series must be KXHIGH*"

    def test_latitude_longitude_ranges(self):
        for city_key, cfg in CITIES.items():
            assert 25.0 <= cfg["latitude"] <= 50.0, f"{city_key} latitude out of US range"
            assert -130.0 <= cfg["longitude"] <= -65.0, f"{city_key} longitude out of US range"
