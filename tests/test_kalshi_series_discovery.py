"""
Tests for src/data/kalshi_series_discovery.py

Tests classification logic, Odds API mapping, and SeriesInfo properties.
No Kalshi API calls — all sync logic tested in isolation.
"""
import pytest
from src.data.kalshi_series_discovery import (
    SeriesCategory,
    SeriesInfo,
    classify_series,
    get_odds_api_key,
    get_all_odds_api_mappings,
)


# ── classify_series ──────────────────────────────────────────────────────────

class TestClassifySeries:
    # Sports — confirmed series
    def test_nba(self):
        assert classify_series("KXNBAGAME") == SeriesCategory.SPORTS

    def test_nhl(self):
        assert classify_series("KXNHLGAME") == SeriesCategory.SPORTS

    def test_mlb(self):
        assert classify_series("KXMLBGAME") == SeriesCategory.SPORTS

    def test_ncaab(self):
        assert classify_series("KXNCAABGAME") == SeriesCategory.SPORTS

    def test_ncaab_alt(self):
        assert classify_series("KXNCAAMBGAME") == SeriesCategory.SPORTS

    def test_ucl(self):
        assert classify_series("KXUCLGAME") == SeriesCategory.SPORTS

    def test_epl(self):
        assert classify_series("KXEPLGAME") == SeriesCategory.SPORTS

    def test_bundesliga(self):
        assert classify_series("KXBUNDESLIGAGAME") == SeriesCategory.SPORTS

    def test_serie_a(self):
        assert classify_series("KXSERIEAGAME") == SeriesCategory.SPORTS

    def test_la_liga(self):
        assert classify_series("KXLALIGAGAME") == SeriesCategory.SPORTS

    def test_ligue1(self):
        assert classify_series("KXLIGUE1GAME") == SeriesCategory.SPORTS

    def test_ufc(self):
        assert classify_series("KXUFCFIGHT") == SeriesCategory.SPORTS

    def test_nfl_unverified(self):
        assert classify_series("KXNFLGAME") == SeriesCategory.SPORTS

    def test_mls_unverified(self):
        assert classify_series("KXMLSGAME") == SeriesCategory.SPORTS

    # Crypto
    def test_btc_daily(self):
        assert classify_series("KXBTCD") == SeriesCategory.CRYPTO

    def test_eth_15m(self):
        assert classify_series("KXETH15M") == SeriesCategory.CRYPTO

    def test_sol_15m(self):
        assert classify_series("KXSOL15M") == SeriesCategory.CRYPTO

    def test_xrp(self):
        assert classify_series("KXXRP15M") == SeriesCategory.CRYPTO

    def test_btc_prefix_variant(self):
        assert classify_series("KXBTCWEEKLY") == SeriesCategory.CRYPTO

    # Economics
    def test_cpi(self):
        assert classify_series("KXCPI") == SeriesCategory.ECONOMICS

    def test_gdp(self):
        assert classify_series("KXGDP") == SeriesCategory.ECONOMICS

    def test_fed(self):
        assert classify_series("KXFED") == SeriesCategory.ECONOMICS

    def test_unrate(self):
        assert classify_series("KXUNRATE") == SeriesCategory.ECONOMICS

    def test_fomc(self):
        assert classify_series("KXFOMC") == SeriesCategory.ECONOMICS

    # Politics — ticker prefix
    def test_senate_ticker(self):
        assert classify_series("KXSENATE2026") == SeriesCategory.POLITICS

    def test_gov_ticker(self):
        assert classify_series("KXGOV2026") == SeriesCategory.POLITICS

    # Politics — title keyword
    def test_election_title(self):
        assert classify_series("KXUNKNOWN", "2026 Midterm Election Winner") == SeriesCategory.POLITICS

    def test_president_title(self):
        assert classify_series("KXUNKNOWN", "Who will win the Presidential race?") == SeriesCategory.POLITICS

    # Culture — title keyword
    def test_oscar_title(self):
        assert classify_series("KXUNKNOWN", "Oscar Best Picture Winner") == SeriesCategory.CULTURE

    def test_grammy_title(self):
        assert classify_series("KXUNKNOWN", "Grammy Award for Album of the Year") == SeriesCategory.CULTURE

    # Other
    def test_unknown_ticker(self):
        assert classify_series("KXWEATHER") == SeriesCategory.OTHER

    def test_empty_ticker(self):
        # Should not raise, returns OTHER
        result = classify_series("")
        assert isinstance(result, SeriesCategory)

    # Case insensitivity
    def test_lowercase_ticker(self):
        assert classify_series("kxnbagame") == SeriesCategory.SPORTS

    def test_mixed_case(self):
        assert classify_series("KxCpi") == SeriesCategory.ECONOMICS


# ── get_odds_api_key ─────────────────────────────────────────────────────────

class TestGetOddsApiKey:
    # Confirmed mappings
    def test_nba(self):
        assert get_odds_api_key("KXNBAGAME") == "basketball_nba"

    def test_nhl(self):
        assert get_odds_api_key("KXNHLGAME") == "icehockey_nhl"

    def test_mlb(self):
        assert get_odds_api_key("KXMLBGAME") == "baseball_mlb"

    def test_ncaab(self):
        assert get_odds_api_key("KXNCAABGAME") == "basketball_ncaab"

    def test_ncaab_alt(self):
        assert get_odds_api_key("KXNCAAMBGAME") == "basketball_ncaab"

    def test_ucl(self):
        assert get_odds_api_key("KXUCLGAME") == "soccer_uefa_champions_league"

    def test_epl(self):
        assert get_odds_api_key("KXEPLGAME") == "soccer_epl"

    def test_bundesliga(self):
        assert get_odds_api_key("KXBUNDESLIGAGAME") == "soccer_germany_bundesliga"

    def test_serie_a(self):
        assert get_odds_api_key("KXSERIEAGAME") == "soccer_italy_serie_a"

    def test_la_liga(self):
        assert get_odds_api_key("KXLALIGAGAME") == "soccer_spain_la_liga"

    def test_ligue1(self):
        assert get_odds_api_key("KXLIGUE1GAME") == "soccer_france_ligue_one"

    def test_ufc(self):
        assert get_odds_api_key("KXUFCFIGHT") == "mma_mixed_martial_arts"

    # Unverified but mapped
    def test_nfl_unverified(self):
        assert get_odds_api_key("KXNFLGAME") == "americanfootball_nfl"

    def test_mls_unverified(self):
        assert get_odds_api_key("KXMLSGAME") == "soccer_usa_mls"

    # No mapping (returns None explicitly)
    def test_btc_returns_none(self):
        assert get_odds_api_key("KXBTCD") is None

    def test_cpi_returns_none(self):
        assert get_odds_api_key("KXCPI") is None

    def test_fed_returns_none(self):
        assert get_odds_api_key("KXFED") is None

    def test_15m_crypto_banned(self):
        assert get_odds_api_key("KXBTC15M") is None

    # Unknown series returns None
    def test_unknown_series(self):
        assert get_odds_api_key("KXUNKNOWNXYZ") is None

    # Case insensitivity
    def test_lowercase_input(self):
        assert get_odds_api_key("kxnbagame") == "basketball_nba"

    def test_mixed_case(self):
        assert get_odds_api_key("KxNhlGame") == "icehockey_nhl"


# ── get_all_odds_api_mappings ─────────────────────────────────────────────────

class TestGetAllOddsApiMappings:
    def test_returns_dict(self):
        mappings = get_all_odds_api_mappings()
        assert isinstance(mappings, dict)

    def test_no_none_values(self):
        mappings = get_all_odds_api_mappings()
        assert all(v is not None for v in mappings.values())

    def test_nba_in_mappings(self):
        mappings = get_all_odds_api_mappings()
        assert "KXNBAGAME" in mappings

    def test_crypto_not_in_mappings(self):
        mappings = get_all_odds_api_mappings()
        assert "KXBTCD" not in mappings
        assert "KXBTC15M" not in mappings

    def test_economics_not_in_mappings(self):
        mappings = get_all_odds_api_mappings()
        assert "KXCPI" not in mappings
        assert "KXGDP" not in mappings

    def test_at_least_ten_confirmed(self):
        # Confirm we have a substantial mapping table
        assert len(get_all_odds_api_mappings()) >= 10


# ── SeriesInfo ────────────────────────────────────────────────────────────────

class TestSeriesInfo:
    def test_is_game_market_sports(self):
        s = SeriesInfo(ticker="KXNBAGAME", title="NBA", category=SeriesCategory.SPORTS)
        assert s.is_game_market is True

    def test_is_game_market_non_sports(self):
        s = SeriesInfo(ticker="KXCPI", title="CPI", category=SeriesCategory.ECONOMICS)
        assert s.is_game_market is False

    def test_has_odds_api_coverage_with_key(self):
        s = SeriesInfo(
            ticker="KXNBAGAME", title="NBA",
            category=SeriesCategory.SPORTS,
            odds_api_key="basketball_nba",
        )
        assert s.has_odds_api_coverage is True

    def test_has_odds_api_coverage_without_key(self):
        s = SeriesInfo(
            ticker="KXCPI", title="CPI",
            category=SeriesCategory.ECONOMICS,
            odds_api_key=None,
        )
        assert s.has_odds_api_coverage is False

    def test_default_volume_zero(self):
        s = SeriesInfo(ticker="KXTEST", title="Test", category=SeriesCategory.OTHER)
        assert s.volume == 0

    def test_default_tags_empty_list(self):
        s = SeriesInfo(ticker="KXTEST", title="Test", category=SeriesCategory.OTHER)
        assert s.tags == []
