"""Tests for sports_game strategy and odds_api feed."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.strategies.sports_game import (
    SportsGameStrategy,
    _parse_title,
    _resolve_team,
    _match_game,
    load_nba_from_config,
    load_nhl_from_config,
)
from src.data.odds_api import OddsGame, OddsAPIFeed, _remove_vig, _decimal_to_implied
from src.platforms.kalshi import Market


# ── Helpers ──────────────────────────────────────────────────────────────────

def _market(ticker="KXNBAGAME-26FEB28HOUMIA-HOU", title="Houston at Miami Winner?",
            yes_price=67, no_price=33, volume=5000):
    m = MagicMock(spec=Market)
    m.ticker = ticker
    m.title = title
    m.yes_price = yes_price
    m.no_price = no_price
    m.volume = volume
    return m


def _game(home="Miami Heat", away="Houston Rockets", home_prob=0.35, away_prob=0.65, num_books=3):
    return OddsGame(
        sport="basketball_nba",
        game_id="test-id",
        home_team=home,
        away_team=away,
        commence_time="2026-03-14T20:30:00Z",
        home_prob=home_prob,
        away_prob=away_prob,
        num_books=num_books,
    )


# ── Title parsing ─────────────────────────────────────────────────────────────

def test_parse_title_standard():
    away, home = _parse_title("Houston at Miami Winner?")
    assert away == "Houston"
    assert home == "Miami"


def test_parse_title_multiword():
    away, home = _parse_title("Los Angeles C at Golden State Winner?")
    assert away == "Los Angeles C"
    assert home == "Golden State"


def test_parse_title_nhl():
    away, home = _parse_title("Edmonton at San Jose Winner?")
    assert away == "Edmonton"
    assert home == "San Jose"


def test_parse_title_invalid():
    assert _parse_title("No match here") is None
    assert _parse_title("") is None


# ── Team name resolution ──────────────────────────────────────────────────────

def test_resolve_nba_team():
    assert _resolve_team("Houston", "basketball_nba") == "Houston Rockets"
    assert _resolve_team("Miami", "basketball_nba") == "Miami Heat"
    assert _resolve_team("Los Angeles C", "basketball_nba") == "Los Angeles Clippers"
    assert _resolve_team("Los Angeles L", "basketball_nba") == "Los Angeles Lakers"


def test_resolve_nhl_team():
    assert _resolve_team("Edmonton", "icehockey_nhl") == "Edmonton Oilers"
    assert _resolve_team("San Jose", "icehockey_nhl") == "San Jose Sharks"
    assert _resolve_team("Vegas", "icehockey_nhl") == "Vegas Golden Knights"


def test_resolve_unknown_team():
    assert _resolve_team("Unknown City", "basketball_nba") is None


# ── Game matching ─────────────────────────────────────────────────────────────

def test_match_game_direct():
    games = [_game(home="Miami Heat", away="Houston Rockets")]
    result = _match_game(games, "Miami Heat", "Houston Rockets")
    assert result is not None
    assert result.home_team == "Miami Heat"


def test_match_game_partial():
    games = [_game(home="Miami Heat", away="Houston Rockets")]
    result = _match_game(games, "Miami", "Houston")
    assert result is not None


def test_match_game_flipped():
    """Kalshi sometimes flips home/away — still match."""
    games = [_game(home="Miami Heat", away="Houston Rockets")]
    result = _match_game(games, "Houston Rockets", "Miami Heat")
    assert result is not None


def test_match_game_no_match():
    games = [_game(home="Boston Celtics", away="Philadelphia 76ers")]
    result = _match_game(games, "Miami Heat", "Houston Rockets")
    assert result is None


# ── Vig removal ───────────────────────────────────────────────────────────────

def test_remove_vig_equal():
    h, a = _remove_vig(0.5, 0.5)
    assert h == pytest.approx(0.5)
    assert a == pytest.approx(0.5)


def test_remove_vig_sums_to_one():
    h, a = _remove_vig(0.55, 0.50)
    assert h + a == pytest.approx(1.0)
    assert h > a


def test_decimal_to_implied():
    assert _decimal_to_implied(2.0) == pytest.approx(0.5)
    assert _decimal_to_implied(1.5) == pytest.approx(1 / 1.5)


# ── Signal generation ─────────────────────────────────────────────────────────

def test_signal_yes_edge():
    """Kalshi shows HOU at 67¢, consensus says 80% → strong YES edge."""
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_books=2)
    market = _market(yes_price=67, volume=500)
    games = [_game(home="Miami Heat", away="Houston Rockets", home_prob=0.20, away_prob=0.80)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is not None
    assert sig.side == "yes"
    assert sig.edge_pct > 0.05
    assert sig.win_prob == pytest.approx(0.80)


def test_signal_no_edge():
    """Kalshi shows HOU at 90¢, consensus says only 70% → edge is on NO side."""
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_books=2)
    market = _market(yes_price=90, no_price=10, volume=500)
    games = [_game(home="Miami Heat", away="Houston Rockets", home_prob=0.30, away_prob=0.70)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is not None
    assert sig.side == "no"


def test_signal_insufficient_edge():
    """Kalshi price nearly matches consensus — no signal."""
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_books=2)
    market = _market(yes_price=67, volume=500)
    games = [_game(home="Miami Heat", away="Houston Rockets", home_prob=0.33, away_prob=0.67)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is None


def test_signal_too_few_books():
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_books=3)
    market = _market(yes_price=67, volume=500)
    games = [_game(home_prob=0.20, away_prob=0.80, num_books=2)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is None


def test_signal_low_volume():
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_volume=200)
    market = _market(yes_price=67, volume=50)
    games = [_game(home_prob=0.20, away_prob=0.80)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is None


def test_signal_no_games():
    strategy = SportsGameStrategy(sport="basketball_nba")
    market = _market()
    sig = strategy.generate_signal(market, [], yes_side_team="Houston")
    assert sig is None


def test_signal_no_yes_team():
    strategy = SportsGameStrategy(sport="basketball_nba")
    market = _market()
    games = [_game()]
    sig = strategy.generate_signal(market, games, yes_side_team=None)
    assert sig is None


def test_signal_near_resolved_skipped():
    """YES=99¢ or YES=1¢ markets are near resolution — skip."""
    strategy = SportsGameStrategy(sport="basketball_nba", min_edge_pct=0.05, min_books=1)
    market = _market(yes_price=99, no_price=1, volume=500)
    games = [_game(home_prob=0.20, away_prob=0.80)]
    sig = strategy.generate_signal(market, games, yes_side_team="Houston")
    assert sig is None


# ── NHL signal ────────────────────────────────────────────────────────────────

def test_nhl_signal():
    """NHL game signal fires correctly."""
    strategy = SportsGameStrategy(sport="icehockey_nhl", min_edge_pct=0.05, min_books=2)
    market = _market(
        ticker="KXNHLGAME-26FEB28EDMSJ-EDM",
        title="Edmonton at San Jose Winner?",
        yes_price=55, no_price=45, volume=200,
    )
    games = [OddsGame(
        sport="icehockey_nhl",
        game_id="test",
        home_team="San Jose Sharks",
        away_team="Edmonton Oilers",
        commence_time="2026-02-28T21:00:00Z",
        home_prob=0.30,
        away_prob=0.70,
        num_books=3,
    )]
    sig = strategy.generate_signal(market, games, yes_side_team="Edmonton")
    assert sig is not None
    assert sig.side == "yes"
    assert sig.win_prob == pytest.approx(0.70)


# ── Factories ─────────────────────────────────────────────────────────────────

def test_load_nba_from_config():
    cfg = {"strategy": {"sports_game": {"min_edge_pct": 0.07, "min_books": 3}}}
    s = load_nba_from_config(cfg)
    assert s.name == "sports_game_nba_v1"
    assert s.sport == "basketball_nba"
    assert s.min_edge_pct == 0.07
    assert s.min_books == 3


def test_load_nhl_from_config():
    cfg = {"strategy": {"sports_game": {"min_volume": 500}}}
    s = load_nhl_from_config(cfg)
    assert s.name == "sports_game_nhl_v1"
    assert s.sport == "icehockey_nhl"
    assert s.min_volume == 500


def test_load_defaults():
    s = load_nba_from_config({})
    assert s.min_edge_pct == 0.05
    assert s.min_books == 2
    assert s.min_volume == 100


# ── OddsAPIFeed factory ───────────────────────────────────────────────────────

def test_odds_api_feed_requires_key(monkeypatch):
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ODDS_API_KEY"):
        OddsAPIFeed.load_from_env()


def test_odds_api_feed_loads_key(monkeypatch):
    monkeypatch.setenv("ODDS_API_KEY", "test-key-123")
    feed = OddsAPIFeed.load_from_env()
    assert feed.api_key == "test-key-123"
