"""
Tests for sports futures strategy components:
  - ChampionshipOdds dataclass and parsing
  - OddsAPIFeed championship methods (get_nba_championship etc.)
  - SportsFuturesStrategy signal generation
  - Team name normalizer

API facts confirmed via live probing 2026-03-01:
  Odds API: basketball_nba_championship_winner, icehockey_nhl_championship_winner,
            basketball_ncaab_championship_winner all return outrights data.
  Polymarket.us: 30 NBA Champion, 19 NHL Stanley Cup, 30 NCAA Tournament winner markets.
  All are futures (season-winner) — no game-by-game markets yet on .us.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── fixtures ─────────────────────────────────────────────────────────

# Odds API outright event structure (confirmed via live probe 2026-03-01)
SAMPLE_OUTRIGHT_EVENT = {
    "id": "abc123",
    "sport_key": "basketball_nba_championship_winner",
    "sport_title": "NBA Championship Winner",
    "home_team": None,
    "away_team": None,
    "commence_time": "2026-06-30T00:00:00Z",
    "bookmakers": [
        {
            "key": "pinnacle",
            "title": "Pinnacle",
            "markets": [
                {
                    "key": "outrights",
                    "outcomes": [
                        {"name": "Oklahoma City Thunder", "price": 2.43},
                        {"name": "Denver Nuggets",        "price": 6.89},
                        {"name": "Boston Celtics",        "price": 12.34},
                        {"name": "Cleveland Cavaliers",   "price": 13.5},
                        {"name": "San Antonio Spurs",     "price": 8.34},
                    ]
                }
            ]
        },
        {
            "key": "draftkings",
            "title": "DraftKings",
            "markets": [
                {
                    "key": "outrights",
                    "outcomes": [
                        {"name": "Oklahoma City Thunder", "price": 2.50},
                        {"name": "Denver Nuggets",        "price": 7.00},
                        {"name": "Boston Celtics",        "price": 12.00},
                        {"name": "Cleveland Cavaliers",   "price": 14.0},
                        {"name": "San Antonio Spurs",     "price": 8.50},
                    ]
                }
            ]
        }
    ]
}

# Polymarket.us NBA Champion market (from live probe 2026-03-01)
SAMPLE_PM_THUNDER_MARKET = {
    "id": "5042",
    "question": "2026 NBA Champion",
    "slug": "nba-champion-2026-thunder",
    "endDate": "2026-07-01T00:00:00Z",
    "startDate": "2026-02-01T00:00:00Z",
    "category": "sports",
    "active": True,
    "closed": False,
    "marketType": "futures",
    "sportsMarketType": "futures",
    "sportsMarketTypeV2": "SPORTS_MARKET_TYPE_FUTURE",
    "orderPriceMinTickSize": 0.001,
    "marketSides": [
        {
            "id": "10083",
            "identifier": "nba-champion-2026-thunder-yes",
            "description": "Yes",
            "price": "0.385",   # PM price 38.5¢ vs Odds ~40.5% → ~2pp edge below threshold
            "long": True,
            "team": {"id": 99, "name": "Thunder", "abbreviation": "okc", "league": "nba"},
        },
        {
            "id": "10084",
            "identifier": "nba-champion-2026-thunder-no",
            "description": "No",
            "price": "0.615",
            "long": False,
            "team": {"id": 99, "name": "Thunder", "abbreviation": "okc", "league": "nba"},
        },
    ],
    "outcomes": "[\"No\",\"Yes\"]",
    "outcomePrices": "[\"0.615\",\"0.385\"]",
    "title": "Thunder",
}

SAMPLE_PM_CELTICS_MARKET = {
    "id": "5043",
    "question": "2026 NBA Champion",
    "slug": "nba-champion-2026-celtics",
    "endDate": "2026-07-01T00:00:00Z",
    "startDate": "2026-02-01T00:00:00Z",
    "category": "sports",
    "active": True,
    "closed": False,
    "marketType": "futures",
    "sportsMarketType": "futures",
    "sportsMarketTypeV2": "SPORTS_MARKET_TYPE_FUTURE",
    "orderPriceMinTickSize": 0.001,
    "marketSides": [
        {
            "id": "10085",
            "identifier": "nba-champion-2026-celtics-yes",
            "description": "Yes",
            "price": "0.04",    # PM price 4¢ vs Odds ~8% → 4pp edge (below 5% threshold)
            "long": True,
            "team": {"id": 11, "name": "Celtics", "abbreviation": "bos", "league": "nba"},
        },
        {
            "id": "10086",
            "identifier": "nba-champion-2026-celtics-no",
            "description": "No",
            "price": "0.96",
            "long": False,
            "team": {"id": 11, "name": "Celtics", "abbreviation": "bos", "league": "nba"},
        },
    ],
    "outcomes": "[\"No\",\"Yes\"]",
    "outcomePrices": "[\"0.96\",\"0.04\"]",
    "title": "Celtics",
}


# ── mock helpers ─────────────────────────────────────────────────────

def _make_mock_response(status: int, body):
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=body)
    resp.text = AsyncMock(return_value=json.dumps(body))
    resp.headers = {"x-requests-remaining": "19990", "x-requests-used": "10"}
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


def _make_mock_session(responses: list):
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    call_count = [0]

    def get_side_effect(url, **kwargs):
        idx = call_count[0]
        call_count[0] += 1
        if idx < len(responses):
            return responses[idx]
        return _make_mock_response(404, [])

    session.get = MagicMock(side_effect=get_side_effect)
    return session


# ── ChampionshipOdds dataclass tests ─────────────────────────────────

class TestChampionshipOdds:
    def test_from_event_team_name(self):
        from src.data.odds_api import ChampionshipOdds
        odds = ChampionshipOdds.from_event(SAMPLE_OUTRIGHT_EVENT)
        names = [o.team_name for o in odds]
        assert "Oklahoma City Thunder" in names

    def test_from_event_decimal_odds_pinnacle(self):
        from src.data.odds_api import ChampionshipOdds
        odds = ChampionshipOdds.from_event(SAMPLE_OUTRIGHT_EVENT)
        thunder = next(o for o in odds if "Thunder" in o.team_name)
        # Consensus between Pinnacle 2.43 and DraftKings 2.50
        assert abs(thunder.decimal_odds - 2.43) < 0.1  # Pinnacle is first/preferred

    def test_from_event_implied_prob_vig_removed(self):
        """Implied probs should be vig-removed and not necessarily sum to 1 per team."""
        from src.data.odds_api import ChampionshipOdds
        odds = ChampionshipOdds.from_event(SAMPLE_OUTRIGHT_EVENT)
        thunder = next(o for o in odds if "Thunder" in o.team_name)
        # Pinnacle 2.43 → raw 1/2.43 = 0.412 — vig-removed prob
        assert 0.38 < thunder.implied_prob < 0.46

    def test_from_event_returns_all_teams(self):
        from src.data.odds_api import ChampionshipOdds
        odds = ChampionshipOdds.from_event(SAMPLE_OUTRIGHT_EVENT)
        # 5 teams in sample data
        assert len(odds) == 5

    def test_from_event_num_books(self):
        from src.data.odds_api import ChampionshipOdds
        odds = ChampionshipOdds.from_event(SAMPLE_OUTRIGHT_EVENT)
        thunder = next(o for o in odds if "Thunder" in o.team_name)
        assert thunder.num_books == 2  # pinnacle + draftkings

    def test_from_event_empty_bookmakers(self):
        from src.data.odds_api import ChampionshipOdds
        event = dict(SAMPLE_OUTRIGHT_EVENT, bookmakers=[])
        odds = ChampionshipOdds.from_event(event)
        assert odds == []


# ── OddsAPIFeed championship methods ─────────────────────────────────

class TestOddsAPIFeedChampionship:
    def _make_feed(self):
        from src.data.odds_api import OddsAPIFeed
        return OddsAPIFeed(api_key="test-key", cache_ttl_sec=900)

    @pytest.mark.asyncio
    async def test_get_nba_championship_returns_list(self):
        feed = self._make_feed()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [SAMPLE_OUTRIGHT_EVENT])]
            )
            result = await feed.get_nba_championship()
        assert len(result) == 5
        names = [o.team_name for o in result]
        assert "Oklahoma City Thunder" in names

    @pytest.mark.asyncio
    async def test_get_nhl_championship_returns_list(self):
        feed = self._make_feed()
        nhl_event = dict(SAMPLE_OUTRIGHT_EVENT,
                         sport_key="icehockey_nhl_championship_winner")
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [nhl_event])]
            )
            result = await feed.get_nhl_championship()
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_ncaab_championship_returns_list(self):
        feed = self._make_feed()
        ncaab_event = dict(SAMPLE_OUTRIGHT_EVENT,
                           sport_key="basketball_ncaab_championship_winner")
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(200, [ncaab_event])]
            )
            result = await feed.get_ncaab_championship()
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_nba_championship_returns_empty_on_error(self):
        feed = self._make_feed()
        with patch("aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = _make_mock_session(
                [_make_mock_response(429, {"error": "rate limit"})]
            )
            result = await feed.get_nba_championship()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_nba_championship_uses_outrights_endpoint(self):
        feed = self._make_feed()
        with patch("aiohttp.ClientSession") as mock_cls:
            sess = _make_mock_session([_make_mock_response(200, [])])
            mock_cls.return_value = sess
            await feed.get_nba_championship()
        call_url = sess.get.call_args[0][0]
        assert "basketball_nba_championship_winner" in call_url
        assert "outrights" in str(sess.get.call_args)


# ── Team name normalizer tests ────────────────────────────────────────

class TestTeamNameNormalizer:
    def test_thunder_matches(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        assert normalize_team_name("Oklahoma City Thunder") == "thunder"

    def test_nuggets_matches(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        assert normalize_team_name("Denver Nuggets") == "nuggets"

    def test_trail_blazers_matches(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        assert normalize_team_name("Portland Trail Blazers") == "trail blazers"

    def test_pm_short_name_thunder(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        assert normalize_team_name("Thunder") == "thunder"

    def test_seventy_sixers(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        # Polymarket uses "76ers", Odds API uses "Philadelphia 76ers"
        assert normalize_team_name("Philadelphia 76ers") == "76ers"
        assert normalize_team_name("76ers") == "76ers"

    def test_case_insensitive(self):
        from src.strategies.sports_futures_v1 import normalize_team_name
        assert normalize_team_name("CELTICS") == "celtics"
        assert normalize_team_name("Boston Celtics") == "celtics"


# ── SportsFuturesStrategy signal generation ───────────────────────────

class TestSportsFuturesSignal:
    def _make_strategy(self, min_edge_pct=0.05):
        from src.strategies.sports_futures_v1 import SportsFuturesStrategy
        return SportsFuturesStrategy(min_edge_pct=min_edge_pct)

    def _make_pm_market(self, team_name, yes_price):
        from src.platforms.polymarket import PolymarketMarket
        raw = {
            "id": "9999",
            "question": "2026 NBA Champion",
            "slug": f"nba-2026-{team_name.lower()}",
            "endDate": "2026-07-01T00:00:00Z",
            "startDate": "2026-01-01T00:00:00Z",
            "category": "sports",
            "active": True,
            "closed": False,
            "marketType": "futures",
            "sportsMarketType": "futures",
            "sportsMarketTypeV2": "SPORTS_MARKET_TYPE_FUTURE",
            "orderPriceMinTickSize": 0.001,
            "marketSides": [
                {
                    "id": "1001",
                    "identifier": f"nba-2026-{team_name.lower()}-yes",
                    "description": "Yes",
                    "price": str(yes_price),
                    "long": True,
                    "team": {"id": 1, "name": team_name, "abbreviation": team_name[:3].lower(), "league": "nba"},
                },
                {
                    "id": "1002",
                    "identifier": f"nba-2026-{team_name.lower()}-no",
                    "description": "No",
                    "price": str(round(1.0 - yes_price, 3)),
                    "long": False,
                    "team": {"id": 1, "name": team_name, "abbreviation": team_name[:3].lower(), "league": "nba"},
                },
            ],
            "outcomes": "[\"No\",\"Yes\"]",
            "outcomePrices": f"[{round(1.0-yes_price,3)},{yes_price}]",
            "title": team_name,
        }
        return PolymarketMarket.from_dict(raw)

    def _make_odds(self, team_name, implied_prob):
        from src.data.odds_api import ChampionshipOdds
        return ChampionshipOdds(
            team_name=team_name,
            decimal_odds=round(1.0 / implied_prob, 2) if implied_prob > 0 else 999.0,
            implied_prob=implied_prob,
            num_books=2,
        )

    def test_buy_yes_signal_when_pm_underpriced(self):
        """PM has Thunder at 30¢, Odds API says 41% → 11pp edge → BUY YES."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.30)
        odds = [self._make_odds("Oklahoma City Thunder", 0.41)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert len(signals) == 1
        assert signals[0].side == "yes"

    def test_buy_no_signal_when_pm_overpriced(self):
        """PM has Thunder at 55¢, Odds API says 41% → 14pp overpriced → BUY NO."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.55)
        odds = [self._make_odds("Oklahoma City Thunder", 0.41)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert len(signals) == 1
        assert signals[0].side == "no"

    def test_no_signal_when_edge_below_threshold(self):
        """PM at 40¢, Odds API says 41% → 1pp edge < 5% threshold → no signal."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.40)
        odds = [self._make_odds("Oklahoma City Thunder", 0.41)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert signals == []

    def test_no_signal_when_no_odds_match(self):
        """PM has Thunder market but Odds API only has Celtics → no match → no signal."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.30)
        odds = [self._make_odds("Boston Celtics", 0.08)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert signals == []

    def test_signal_edge_pct_correct(self):
        """Signal edge_pct should equal odds_prob - pm_price for YES underpriced."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.30)
        odds = [self._make_odds("Oklahoma City Thunder", 0.41)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert len(signals) == 1
        assert abs(signals[0].edge_pct - (0.41 - 0.30)) < 0.001

    def test_signal_price_cents_is_pm_price(self):
        """Signal price_cents should be the Polymarket price (where we'll execute)."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        pm_market = self._make_pm_market("Thunder", 0.30)
        odds = [self._make_odds("Oklahoma City Thunder", 0.41)]

        signals = strategy.scan_for_signals([pm_market], odds)
        assert signals[0].price_cents == 30  # 0.30 * 100

    def test_multiple_signals_from_multiple_markets(self):
        """Two mispriced markets generate two signals."""
        strategy = self._make_strategy(min_edge_pct=0.05)
        markets = [
            self._make_pm_market("Thunder", 0.30),  # Odds says 41% → +11pp YES
            self._make_pm_market("Celtics", 0.04),  # Odds says 8.1% → +4.1pp — below threshold
        ]
        odds = [
            self._make_odds("Oklahoma City Thunder", 0.41),
            self._make_odds("Boston Celtics", 0.081),
        ]
        signals = strategy.scan_for_signals(markets, odds)
        # Only Thunder has enough edge
        assert len(signals) == 1
        assert signals[0].side == "yes"

    def test_strategy_name(self):
        from src.strategies.sports_futures_v1 import SportsFuturesStrategy
        s = SportsFuturesStrategy()
        assert s.name == "sports_futures_v1"
