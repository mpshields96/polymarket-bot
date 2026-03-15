"""
Tests for scripts/weather_calibration.py — weather GEFS calibration tracker.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module under test
import importlib.util
spec = importlib.util.spec_from_file_location(
    "weather_calibration",
    Path(__file__).parent.parent / "scripts" / "weather_calibration.py",
)
wc = importlib.util.util = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wc)

# Re-import the functions we need
_infer_outcome = wc._infer_outcome
_city_from_ticker = wc._city_from_ticker


class TestInferOutcome:
    """Tests for _infer_outcome — inferring win/loss from current market price."""

    def test_no_bet_yes_price_zero_is_likely_win(self):
        assert _infer_outcome("no", 0) == "LIKELY_WIN"

    def test_no_bet_yes_price_one_is_likely_win(self):
        assert _infer_outcome("no", 1) == "LIKELY_WIN"

    def test_no_bet_yes_price_two_is_likely_win(self):
        assert _infer_outcome("no", 2) == "LIKELY_WIN"

    def test_no_bet_yes_price_three_is_prob_win(self):
        result = _infer_outcome("no", 3)
        assert result == "PROB_WIN"

    def test_no_bet_yes_price_high_is_likely_loss(self):
        assert _infer_outcome("no", 98) == "LIKELY_LOSS"

    def test_no_bet_yes_price_99_is_likely_loss(self):
        assert _infer_outcome("no", 99) == "LIKELY_LOSS"

    def test_no_bet_yes_price_100_is_likely_loss(self):
        assert _infer_outcome("no", 100) == "LIKELY_LOSS"

    def test_no_bet_yes_price_90_is_prob_loss(self):
        result = _infer_outcome("no", 90)
        assert result == "PROB_LOSS"

    def test_no_bet_yes_price_midrange_is_open(self):
        assert _infer_outcome("no", 50) == "OPEN"

    def test_no_bet_yes_price_none_is_unknown(self):
        assert _infer_outcome("no", None) == "UNKNOWN"

    def test_yes_bet_yes_price_99_is_likely_win(self):
        assert _infer_outcome("yes", 99) == "LIKELY_WIN"

    def test_yes_bet_yes_price_98_is_likely_win(self):
        assert _infer_outcome("yes", 98) == "LIKELY_WIN"

    def test_yes_bet_yes_price_100_is_likely_win(self):
        assert _infer_outcome("yes", 100) == "LIKELY_WIN"

    def test_yes_bet_yes_price_zero_is_likely_loss(self):
        assert _infer_outcome("yes", 0) == "LIKELY_LOSS"

    def test_yes_bet_yes_price_two_is_likely_loss(self):
        assert _infer_outcome("yes", 2) == "LIKELY_LOSS"

    def test_yes_bet_yes_price_midrange_is_open(self):
        assert _infer_outcome("yes", 45) == "OPEN"

    def test_yes_bet_yes_price_90_is_prob_win(self):
        result = _infer_outcome("yes", 90)
        assert result == "PROB_WIN"

    def test_yes_bet_yes_price_10_is_prob_loss(self):
        result = _infer_outcome("yes", 10)
        assert result == "PROB_LOSS"

    def test_yes_bet_none_is_unknown(self):
        assert _infer_outcome("yes", None) == "UNKNOWN"


class TestCityFromTicker:
    """Tests for _city_from_ticker — extract city code from ticker."""

    def test_nyc_from_highny(self):
        assert _city_from_ticker("KXHIGHNY-26MAR15-T47") == "NYC"

    def test_lax_from_highlax(self):
        assert _city_from_ticker("KXHIGHLAX-26MAR15-T79") == "LAX"

    def test_chi_from_highchi(self):
        assert _city_from_ticker("KXHIGHCHI-26MAR14-T39") == "CHI"

    def test_den_from_highden(self):
        assert _city_from_ticker("KXHIGHDEN-26MAR15-B49.5") == "DEN"

    def test_mia_from_highmia(self):
        assert _city_from_ticker("KXHIGHMIA-26MAR15-B81.5") == "MIA"

    def test_unknown_ticker_returns_other(self):
        assert _city_from_ticker("KXBTC15M-26MAR15-UP") == "OTHER"

    def test_bracket_market_city_extracted(self):
        assert _city_from_ticker("KXHIGHCHI-26MAR15-B62.5") == "CHI"

    def test_threshold_market_city_extracted(self):
        assert _city_from_ticker("KXHIGHNY-26MAR16-T45") == "NYC"


class TestInferOutcomeBoundaries:
    """Edge cases for the inference logic."""

    def test_boundary_at_10_no_bet(self):
        # <= 10 is PROB_WIN for NO bet
        assert _infer_outcome("no", 10) == "PROB_WIN"

    def test_boundary_at_11_no_bet(self):
        # 11-89 is OPEN for NO bet
        assert _infer_outcome("no", 11) == "OPEN"

    def test_boundary_at_89_no_bet(self):
        # 89 is OPEN for NO bet
        assert _infer_outcome("no", 89) == "OPEN"

    def test_boundary_at_90_no_bet(self):
        # >= 90 is PROB_LOSS for NO bet
        assert _infer_outcome("no", 90) == "PROB_LOSS"

    def test_boundary_at_97_no_bet(self):
        # 97 is PROB_LOSS for NO bet (not LIKELY_LOSS)
        assert _infer_outcome("no", 97) == "PROB_LOSS"

    def test_boundary_at_98_no_bet(self):
        # >= 98 is LIKELY_LOSS for NO bet
        assert _infer_outcome("no", 98) == "LIKELY_LOSS"
