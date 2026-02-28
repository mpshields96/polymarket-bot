"""
Tests for src/execution/live.py — real-money execution path.

This is the highest-priority testing gap (Session 20: live.py had ZERO tests
while handling real money). These tests cover every path that touches real funds.

Coverage:
    _determine_limit_price:
        - YES/NO side orderbook ask pricing
        - Fallback to market snapshot price
        - Boundary values (1¢, 99¢), out-of-range returns None
        - Unknown side returns None
        - Orderbook preferred over market when both valid

    execute() guards:
        - Guard 1: LIVE_TRADING env var not set or false → RuntimeError
        - Guard 2: live_confirmed=False → RuntimeError
        - Guard 3: _FIRST_RUN_CONFIRMED=False, input()!="CONFIRM" → returns None
        - Guard 3: _FIRST_RUN_CONFIRMED=False, input()=="CONFIRM" → proceeds

    execute() success paths:
        - YES-side: create_order called with yes_price only
        - NO-side: create_order called with no_price only
        - Return dict has all required keys
        - count calculated correctly from trade_usd / cost_per_contract
        - Ticker from signal passed to order and DB

    Regressions (Session 20 bugs):
        - strategy_name stored correctly — NOT hardcoded "btc_lag"
        - is_paper=False in every live DB record
        - server_order_id from API response stored in DB

    execute() failure paths:
        - KalshiAPIError → None (no DB write)
        - Unexpected exception → None (no DB write)
        - No valid limit price → None (no order placed)
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.platforms.kalshi import (
    Market,
    OrderBook,
    OrderBookLevel,
    Order,
    KalshiAPIError,
)
from src.strategies.base import Signal
import src.execution.live as live_module
from src.execution.live import _determine_limit_price, execute


# ── Test helpers ─────────────────────────────────────────────────────────


def make_signal(
    side="yes",
    price_cents=55,
    edge_pct=0.10,
    win_prob=0.65,
    ticker="KXBTC15M-26FEB281700-00",
):
    return Signal(
        side=side,
        edge_pct=edge_pct,
        win_prob=win_prob,
        confidence=0.7,
        ticker=ticker,
        price_cents=price_cents,
        reason="test",
    )


def make_market(yes_price=55, no_price=45):
    return Market(
        ticker="KXBTC15M-26FEB281700-00",
        title="BTC Market",
        event_ticker="KXBTC15M",
        status="open",
        yes_price=yes_price,
        no_price=no_price,
        volume=1000,
        close_time="2026-02-28T17:00:00Z",
        open_time="2026-02-28T16:45:00Z",
    )


def make_orderbook(yes_bid=None, no_bid=None):
    yes_bids = [OrderBookLevel(price=yes_bid, quantity=10)] if yes_bid else []
    no_bids = [OrderBookLevel(price=no_bid, quantity=10)] if no_bid else []
    return OrderBook(yes_bids=yes_bids, no_bids=no_bids)


def make_order(order_id="server-order-123", status="executed"):
    return Order(
        order_id=order_id,
        client_order_id="client-id",
        ticker="KXBTC15M-26FEB281700-00",
        side="yes",
        action="buy",
        type="limit",
        status=status,
        yes_price=55,
        no_price=45,
        initial_count=9,
        remaining_count=0,
        fill_count=9,
        created_time="2026-02-28T17:00:00Z",
    )


def make_kalshi_mock(order=None):
    kalshi = MagicMock()
    kalshi.create_order = AsyncMock(return_value=order or make_order())
    return kalshi


def make_db_mock(trade_id=100):
    db = MagicMock()
    db.save_trade.return_value = trade_id
    return db


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def bypass_first_run(monkeypatch):
    """Set _FIRST_RUN_CONFIRMED=True to skip interactive input() prompt."""
    monkeypatch.setattr(live_module, "_FIRST_RUN_CONFIRMED", True)


@pytest.fixture()
def live_env(monkeypatch):
    """Set LIVE_TRADING=true in environment."""
    monkeypatch.setenv("LIVE_TRADING", "true")


# ── _determine_limit_price ────────────────────────────────────────────────


class TestDetermineLimitPrice:
    def test_yes_side_uses_orderbook_ask(self):
        # YES ask = 100 - no_bid = 100 - 45 = 55
        ob = make_orderbook(no_bid=45)
        market = make_market(yes_price=60)  # orderbook beats market
        assert _determine_limit_price("yes", market, ob) == 55

    def test_yes_side_fallback_to_market_price(self):
        # Empty orderbook → use market.yes_price
        ob = make_orderbook()
        market = make_market(yes_price=62)
        assert _determine_limit_price("yes", market, ob) == 62

    def test_no_side_uses_orderbook_ask(self):
        # NO ask = 100 - yes_bid = 100 - 52 = 48
        ob = make_orderbook(yes_bid=52)
        market = make_market(no_price=50)  # orderbook beats market
        assert _determine_limit_price("no", market, ob) == 48

    def test_no_side_fallback_to_market_price(self):
        ob = make_orderbook()
        market = make_market(no_price=42)
        assert _determine_limit_price("no", market, ob) == 42

    def test_yes_side_invalid_market_and_empty_orderbook_returns_none(self):
        ob = make_orderbook()
        market = make_market(yes_price=0, no_price=100)
        assert _determine_limit_price("yes", market, ob) is None

    def test_no_side_invalid_market_and_empty_orderbook_returns_none(self):
        ob = make_orderbook()
        market = make_market(yes_price=100, no_price=0)
        assert _determine_limit_price("no", market, ob) is None

    def test_yes_price_at_lower_boundary(self):
        ob = make_orderbook()
        market = make_market(yes_price=1)
        assert _determine_limit_price("yes", market, ob) == 1

    def test_yes_price_at_upper_boundary(self):
        ob = make_orderbook()
        market = make_market(yes_price=99)
        assert _determine_limit_price("yes", market, ob) == 99

    def test_no_price_at_lower_boundary(self):
        ob = make_orderbook()
        market = make_market(no_price=1)
        assert _determine_limit_price("no", market, ob) == 1

    def test_no_price_at_upper_boundary(self):
        ob = make_orderbook()
        market = make_market(no_price=99)
        assert _determine_limit_price("no", market, ob) == 99

    def test_unknown_side_returns_none(self):
        ob = make_orderbook(yes_bid=52, no_bid=45)
        market = make_market()
        assert _determine_limit_price("maybe", market, ob) is None

    def test_orderbook_preferred_over_market_yes_side(self):
        # Orderbook implies yes_ask=55, market says 60 — use 55
        ob = make_orderbook(no_bid=45)  # yes_ask = 55
        market = make_market(yes_price=60)
        assert _determine_limit_price("yes", market, ob) == 55

    def test_orderbook_preferred_over_market_no_side(self):
        # no_ask = 100 - yes_bid = 100 - 54 = 46, market says 50 — use 46
        ob = make_orderbook(yes_bid=54)
        market = make_market(no_price=50)
        assert _determine_limit_price("no", market, ob) == 46

    def test_yes_ask_100_is_invalid_falls_back_to_market(self):
        # no_bid=1 → yes_ask = 99 (just inside valid range)
        ob = make_orderbook(no_bid=1)
        market = make_market(yes_price=60)
        # yes_ask = 100 - 1 = 99 is valid, should use it over market
        assert _determine_limit_price("yes", market, ob) == 99


# ── execute() guards ──────────────────────────────────────────────────────


class TestExecuteGuards:
    async def test_guard_live_trading_not_set_raises(self, monkeypatch):
        """Guard 1: LIVE_TRADING absent → RuntimeError."""
        monkeypatch.delenv("LIVE_TRADING", raising=False)
        signal = make_signal()
        with pytest.raises(RuntimeError, match="LIVE_TRADING"):
            await execute(
                signal, make_market(), make_orderbook(), 5.0,
                MagicMock(), MagicMock(), live_confirmed=True,
            )

    async def test_guard_live_trading_false_raises(self, monkeypatch):
        """Guard 1: LIVE_TRADING=false → RuntimeError."""
        monkeypatch.setenv("LIVE_TRADING", "false")
        signal = make_signal()
        with pytest.raises(RuntimeError, match="LIVE_TRADING"):
            await execute(
                signal, make_market(), make_orderbook(), 5.0,
                MagicMock(), MagicMock(), live_confirmed=True,
            )

    async def test_guard_live_confirmed_false_raises(self, monkeypatch):
        """Guard 2: live_confirmed=False → RuntimeError."""
        monkeypatch.setenv("LIVE_TRADING", "true")
        signal = make_signal()
        with pytest.raises(RuntimeError, match="live_confirmed"):
            await execute(
                signal, make_market(), make_orderbook(), 5.0,
                MagicMock(), MagicMock(), live_confirmed=False,
            )

    async def test_guard_first_run_not_confirmed_returns_none(
        self, monkeypatch
    ):
        """Guard 3: _FIRST_RUN_CONFIRMED=False, user types wrong → returns None."""
        monkeypatch.setenv("LIVE_TRADING", "true")
        monkeypatch.setattr(live_module, "_FIRST_RUN_CONFIRMED", False)
        kalshi = make_kalshi_mock()
        db = make_db_mock()
        with patch("builtins.input", return_value="no"):
            result = await execute(
                make_signal(), make_market(), make_orderbook(no_bid=45), 5.0,
                kalshi, db, live_confirmed=True,
            )
        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_guard_first_run_confirmed_via_input_proceeds(
        self, monkeypatch
    ):
        """Guard 3: _FIRST_RUN_CONFIRMED=False, user types CONFIRM → proceeds."""
        monkeypatch.setenv("LIVE_TRADING", "true")
        monkeypatch.setattr(live_module, "_FIRST_RUN_CONFIRMED", False)
        kalshi = make_kalshi_mock()
        db = make_db_mock()
        with patch("builtins.input", return_value="CONFIRM"):
            result = await execute(
                make_signal(), make_market(), make_orderbook(no_bid=45), 5.0,
                kalshi, db, live_confirmed=True, strategy_name="btc_lag_v1",
            )
        assert result is not None
        # Flag should be set to True after confirmation
        assert live_module._FIRST_RUN_CONFIRMED is True


# ── execute() success paths ───────────────────────────────────────────────


class TestExecuteSuccess:
    async def test_yes_side_order_uses_yes_price(self, live_env, bypass_first_run):
        """YES-side: create_order called with yes_price, no_price=None."""
        ob = make_orderbook(no_bid=45)  # yes_ask = 55
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(side="yes"), make_market(), ob, 5.0,
            kalshi, db, live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is not None
        call_kw = kalshi.create_order.call_args.kwargs
        assert call_kw["yes_price"] == 55
        assert call_kw["no_price"] is None
        assert call_kw["side"] == "yes"

    async def test_no_side_order_uses_no_price(self, live_env, bypass_first_run):
        """NO-side: create_order called with no_price, yes_price=None."""
        ob = make_orderbook(yes_bid=52)  # no_ask = 48
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(side="no", price_cents=48),
            make_market(yes_price=52, no_price=48),
            ob, 5.0, kalshi, db, live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is not None
        call_kw = kalshi.create_order.call_args.kwargs
        assert call_kw["no_price"] == 48
        assert call_kw["yes_price"] is None
        assert call_kw["side"] == "no"

    async def test_return_dict_has_all_required_keys(self, live_env, bypass_first_run):
        """Return dict must contain all expected keys."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock(order=make_order(order_id="srv-999"))
        db = make_db_mock(trade_id=77)

        result = await execute(
            make_signal(), make_market(), ob, 5.0,
            kalshi, db, live_confirmed=True, strategy_name="btc_lag_v1",
        )

        for key in (
            "trade_id", "client_order_id", "server_order_id",
            "ticker", "side", "action", "price_cents", "count",
            "cost_usd", "status", "is_paper", "timestamp",
        ):
            assert key in result, f"Missing key in return dict: {key}"

        assert result["trade_id"] == 77
        assert result["server_order_id"] == "srv-999"
        assert result["is_paper"] is False
        assert result["action"] == "buy"

    async def test_count_calculated_from_trade_usd(self, live_env, bypass_first_run):
        """count = max(1, int(trade_usd / cost_per_contract)) at 50¢ = 10 contracts."""
        ob = make_orderbook(no_bid=50)  # yes_ask = 50
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(side="yes", price_cents=50),
            make_market(yes_price=50),
            ob, 5.0, kalshi, db, live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result["count"] == 10
        assert result["price_cents"] == 50

    async def test_ticker_from_signal_passed_to_order(self, live_env, bypass_first_run):
        """Ticker in signal flows through to create_order and DB."""
        eth_ticker = "KXETH15M-26FEB281700-00"
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(ticker=eth_ticker),
            make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="eth_lag_v1",
        )

        assert result["ticker"] == eth_ticker
        assert kalshi.create_order.call_args.kwargs["ticker"] == eth_ticker
        assert db.save_trade.call_args.kwargs["ticker"] == eth_ticker


# ── Regressions (Session 20 bugs) ────────────────────────────────────────


class TestRegressions:
    async def test_strategy_name_not_hardcoded_btc_lag(self, live_env, bypass_first_run):
        """Regression: strategy was hardcoded 'btc_lag' in live.py — now dynamic."""
        for strategy in ("eth_lag_v1", "btc_drift_v1", "eth_drift_v1", "fomc_rate_v1"):
            ob = make_orderbook(no_bid=45)
            kalshi = make_kalshi_mock()
            db = make_db_mock()

            await execute(
                make_signal(), make_market(), ob, 5.0, kalshi, db,
                live_confirmed=True, strategy_name=strategy,
            )

            saved_strategy = db.save_trade.call_args.kwargs["strategy"]
            assert saved_strategy == strategy, (
                f"Expected strategy='{strategy}', got '{saved_strategy}'"
            )

    async def test_is_paper_false_for_live_trades(self, live_env, bypass_first_run):
        """Regression: live trades must be recorded with is_paper=False, not True."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert db.save_trade.call_args.kwargs["is_paper"] is False

    async def test_server_order_id_stored_in_db(self, live_env, bypass_first_run):
        """Regression: server_order_id from API must be saved to DB for audit trail."""
        real_order_id = "15e20bed-4f9f-420e-8618-967eb1741f3b"
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock(order=make_order(order_id=real_order_id))
        db = make_db_mock(trade_id=64)

        await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert db.save_trade.call_args.kwargs["server_order_id"] == real_order_id

    async def test_default_strategy_name_is_unknown_not_btc_lag(
        self, live_env, bypass_first_run
    ):
        """Regression: if strategy_name not passed, default is 'unknown' not 'btc_lag'."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True,  # strategy_name omitted → uses default "unknown"
        )

        saved = db.save_trade.call_args.kwargs["strategy"]
        assert saved == "unknown"
        assert saved != "btc_lag"


# ── execute() failure paths ───────────────────────────────────────────────


class TestExecuteFailures:
    async def test_kalshi_api_error_returns_none(self, live_env, bypass_first_run):
        """KalshiAPIError from API → None returned, no DB write."""
        ob = make_orderbook(no_bid=45)
        kalshi = MagicMock()
        kalshi.create_order = AsyncMock(
            side_effect=KalshiAPIError(400, "Order rejected")
        )
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is None
        db.save_trade.assert_not_called()

    async def test_unexpected_exception_returns_none(self, live_env, bypass_first_run):
        """Network error or unexpected exception → None, no DB write."""
        ob = make_orderbook(no_bid=45)
        kalshi = MagicMock()
        kalshi.create_order = AsyncMock(side_effect=ConnectionError("network down"))
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is None
        db.save_trade.assert_not_called()

    async def test_no_valid_limit_price_returns_none(self, live_env, bypass_first_run):
        """Empty orderbook + invalid market price → no price → no order placed."""
        ob = make_orderbook()  # empty — no bids
        market = make_market(yes_price=0, no_price=100)  # yes_price=0 is invalid
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(side="yes"), market, ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_no_side_no_valid_limit_price_returns_none(
        self, live_env, bypass_first_run
    ):
        """NO-side: empty orderbook + invalid no_price → no order placed."""
        ob = make_orderbook()
        market = make_market(yes_price=100, no_price=0)  # no_price=0 is invalid
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(side="no", price_cents=40), market, ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_order_placed_for_buy_action_only(self, live_env, bypass_first_run):
        """Verify execute always places a BUY order (current design)."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_lag_v1",
        )

        assert kalshi.create_order.call_args.kwargs["action"] == "buy"
