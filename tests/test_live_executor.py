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


# ── Execution-time price guard ────────────────────────────────────────────


class TestExecutionPriceGuard:
    """Execution-time price guard: reject outside 35-65¢ (YES-equiv) or >10¢ slippage.

    Background: btc_drift's 35-65¢ guard fires at signal-generation time only.
    HFTs can reprice in the 0.1-1s asyncio gap, causing orders to fill at extreme
    prices (observed session 37, 2026-03-10 08:39 CDT: filled at 84¢).
    This guard is the last line of defense before create_order is called.
    """

    async def test_rejects_execution_price_above_guard(
        self, live_env, bypass_first_run
    ):
        """YES-side: execution price 80¢ is above 65¢ guard → returns None, no order."""
        # no_bid=20 → yes_ask = 100 - 20 = 80¢
        ob = make_orderbook(no_bid=20)
        signal = make_signal(side="yes", price_cents=55)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=80), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_rejects_execution_price_below_guard(
        self, live_env, bypass_first_run
    ):
        """YES-side: execution price 20¢ is below 35¢ guard → returns None, no order."""
        # no_bid=80 → yes_ask = 100 - 80 = 20¢
        ob = make_orderbook(no_bid=80)
        signal = make_signal(side="yes", price_cents=55)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=20), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_rejects_excessive_slippage(self, live_env, bypass_first_run):
        """YES-side: signal@55¢, execution@67¢ → 12¢ slippage > 10¢ max → rejected."""
        # no_bid=33 → yes_ask = 100 - 33 = 67¢ (within 35-65 range fails: 67 > 65)
        # Actually 67 > 65 → caught by range guard. Use 64¢ with 9¢ signal offset.
        # To test slippage guard independently: signal@50¢, exec@62¢ → 12¢ slip, exec in range.
        # no_bid=38 → yes_ask = 100 - 38 = 62¢ (in 35-65 range), signal=50¢ → 12¢ slip > 10¢
        ob = make_orderbook(no_bid=38)
        signal = make_signal(side="yes", price_cents=50)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=62), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_allows_execution_at_guard_boundary(
        self, live_env, bypass_first_run
    ):
        """YES-side: signal@55¢, exec@65¢ (10¢ slippage = at max, boundary ok) → proceeds."""
        # no_bid=35 → yes_ask = 100 - 35 = 65¢ (at upper guard boundary, 10¢ slip = at limit)
        ob = make_orderbook(no_bid=35)
        signal = make_signal(side="yes", price_cents=55)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=65), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_no_side_slippage_uses_yes_equivalent(
        self, live_env, bypass_first_run
    ):
        """NO-side: signal NO@45¢ (YES-eq=55¢), exec NO@32¢ (YES-eq=68¢) → 13¢ slip → rejected.

        Slippage must be computed in YES-equivalent space, not raw NO price.
        Raw NO comparison: |32 - 45| = 13¢ (would also catch it, but for wrong reason).
        YES-equiv comparison: |68 - 55| = 13¢ > 10¢ → correctly rejected.
        Also: YES-equiv 68 > 65 → also caught by range guard — tests correct conversion path.
        """
        # yes_bid=68 → no_ask = 100 - 68 = 32¢ (NO execution price)
        # YES-equivalent of NO@32¢ = 100 - 32 = 68¢ (outside 35-65 range)
        ob = make_orderbook(yes_bid=68)
        signal = make_signal(side="no", price_cents=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=68, no_price=32), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_valid_price_executes_normally(self, live_env, bypass_first_run):
        """Regression: signal YES@55¢, exec@59¢ (4¢ slip, in range) → order placed normally."""
        # no_bid=41 → yes_ask = 100 - 41 = 59¢ (in 35-65 range, 4¢ slip < 10¢ max)
        ob = make_orderbook(no_bid=41)
        signal = make_signal(side="yes", price_cents=55)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=59), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is not None
        kalshi.create_order.assert_called_once()
        db.save_trade.assert_called_once()


# ── execute() order status guard ──────────────────────────────────────────


class TestExecuteOrderStatusGuard:
    """Guard: canceled orders must NOT be recorded in DB.

    Kalshi cancels orders that cannot be matched (no liquidity, market closing,
    risk limit). Recording a canceled order as a live bet corrupts calibration
    data, inflates the trade counter, and poisons Brier scores.

    'resting' status (GTC order placed but not yet matched) must be recorded
    normally — the order is live and the settlement loop will handle it.
    """

    async def test_canceled_order_not_recorded_in_db(
        self, live_env, bypass_first_run
    ):
        """Order status 'canceled' → execute() returns None, db.save_trade NOT called."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock(order=make_order(status="canceled"))
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is None
        db.save_trade.assert_not_called()
        # Order WAS placed — guard fires after create_order, not before
        kalshi.create_order.assert_called_once()

    async def test_resting_order_recorded_normally(
        self, live_env, bypass_first_run
    ):
        """Order status 'resting' → execute() records trade and returns dict (not None)."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock(order=make_order(status="resting"))
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
        )

        assert result is not None
        assert result["status"] == "resting"
        db.save_trade.assert_called_once()


# ── Sniper price guard override ────────────────────────────────────────────


class TestSniperPriceGuardOverride:
    """expiry_sniper uses price_guard_min=1, price_guard_max=99 to bypass the
    drift 35-65¢ guard. These tests verify:
      1. NO-side sniper at YES-equivalent 8¢ passes when override is active
      2. Default guard (35-65¢) still blocks the same price without override
      3. Override does NOT disable the 1-99¢ validity check
      4. Drift strategies continue to use the default 35-65¢ guard
    """

    async def test_sniper_override_allows_no_at_extreme_yes_equiv(
        self, live_env, bypass_first_run
    ):
        """price_guard_min=1/max=99: NO sniper signal YES-equiv=8¢ executes normally.

        Scenario: YES=8¢, NO=92¢. Signal is NO@92¢ (sniper stores actual NO price).
        Without override: YES-equiv of NO=92 is 100-92=8¢ < 35¢ guard → rejected.
        With override (1-99): 8¢ is inside guard → order placed.
        """
        # yes_bid=8 → no_ask = 100 - 8 = 92¢ (NO execution price)
        ob = make_orderbook(yes_bid=8)
        # signal.price_cents = NO price = 92 (stores actual side price, consistent with drift)
        signal = make_signal(side="no", price_cents=92)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=8, no_price=92), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()
        db.save_trade.assert_called_once()

    async def test_default_guard_blocks_no_at_extreme_yes_equiv(
        self, live_env, bypass_first_run
    ):
        """Default guard (35-65¢): same NO sniper at YES-equiv=8¢ is rejected.

        Regression guard: drift strategies MUST NOT accidentally allow sniper prices.
        """
        ob = make_orderbook(yes_bid=8)
        signal = make_signal(side="no", price_cents=92)  # NO price = 92 (YES=8)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=8, no_price=92), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            # No price_guard_min/max → uses defaults 35/65
        )

        assert result is None
        kalshi.create_order.assert_not_called()

    async def test_sniper_override_yes_side_at_high_price(
        self, live_env, bypass_first_run
    ):
        """price_guard_min=1/max=99: YES sniper at 94¢ executes normally.

        YES@94¢ is a valid sniper entry (favorite at 94¢, YES-equiv=94¢).
        With override (1-99): 94¢ is inside guard → order placed.
        """
        # no_bid=6 → yes_ask = 100 - 6 = 94¢
        ob = make_orderbook(no_bid=6)
        signal = make_signal(side="yes", price_cents=94)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=94, no_price=6), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_override_does_not_bypass_1_99_validity_check(
        self, live_env, bypass_first_run
    ):
        """price_guard_min=0 still rejects price_cents=0 via the unreasonable-price guard.

        The 1-99¢ validity check (not (1 <= price_cents <= 99)) is independent
        of the guard range. Even with price_guard_min=0, a 0¢ price is still rejected.
        """
        ob = make_orderbook(no_bid=100)  # yields yes_ask = 0 (invalid)
        signal = make_signal(side="yes", price_cents=1)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=0, no_price=100), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()


# ── Post-only maker order tests ──────────────────────────────────────────


class TestPostOnlyMakerOrders:
    """Tests for post_only and expiration_ts parameters in live execution.

    Drift strategies should use post_only=True to save ~75% on fees.
    Sniper strategies should NOT use post_only (time-critical, fee savings minimal at 90c+).
    """

    async def test_post_only_passed_to_create_order(self, live_env, bypass_first_run):
        """post_only=True is forwarded to kalshi.create_order()."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True,
        )

        assert result is not None
        assert kalshi.create_order.call_args.kwargs["post_only"] is True

    async def test_post_only_default_false(self, live_env, bypass_first_run):
        """post_only defaults to False when not specified."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
        )

        assert result is not None
        assert kalshi.create_order.call_args.kwargs["post_only"] is False

    async def test_expiration_ts_passed_to_create_order(self, live_env, bypass_first_run):
        """expiration_ts is forwarded to kalshi.create_order()."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        exp_ts = 1741891200  # some future timestamp
        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True, expiration_ts=exp_ts,
        )

        assert result is not None
        assert kalshi.create_order.call_args.kwargs["expiration_ts"] == exp_ts

    async def test_expiration_ts_default_none(self, live_env, bypass_first_run):
        """expiration_ts defaults to None when not specified."""
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
        )

        assert result is not None
        assert kalshi.create_order.call_args.kwargs["expiration_ts"] is None

    async def test_post_only_canceled_order_not_recorded(self, live_env, bypass_first_run):
        """post_only order that crosses spread -> canceled -> NOT recorded in DB.

        Kalshi rejects post_only orders that would cross the spread (fill as taker).
        These come back with status='canceled'. The existing canceled-order guard
        must catch this -- no new code needed, just verifying the interaction.
        """
        ob = make_orderbook(no_bid=45)
        kalshi = make_kalshi_mock(order=make_order(status="canceled"))
        db = make_db_mock()

        result = await execute(
            make_signal(), make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True,
        )

        assert result is None
        db.save_trade.assert_not_called()
        # Order was placed (post_only rejection happens server-side)
        kalshi.create_order.assert_called_once()


# ── 99c fee-floor regression tests ─────────────────────────────────────────


class TestSniperFeeFlorBlock:
    """Regression: sniper NO@99c slipped through price guard (S72 incident).

    Bug: NO@99c → YES-equiv = 100-99 = 1c → passes price_guard_max=99 check (1 <= 1 <= 99).
    Fix: added raw price_cents >= 99 block before the YES-equiv guard converts away the info.

    Live incident: trade 2111 KXXRP15M NO@99c placed at 22:44 UTC 2026-03-15.
    Signal was 93c, orderbook drifted to 99c in the asyncio gap between signal and orderbook fetch.
    """

    async def test_no_at_99c_blocked_by_sniper_override(self, live_env, bypass_first_run):
        """NO@99c is blocked even when sniper override price_guard_min=1/max=99 is used.

        YES-equiv of NO@99 = 1c, which is within [1, 99]. Without the raw-price check
        the order would be placed. Fee-floor: NO@99c gross profit = 1c per contract =
        essentially zero net after fees on a loss scenario.
        """
        # Orderbook: no_ask = 99c (price drifted after signal at 93c)
        ob = make_orderbook(yes_bid=1)  # yes_bid=1 → no_ask = 100-1 = 99
        signal = make_signal(side="no", price_cents=93)  # signal was at 93c
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=1, no_price=99), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_yes_at_99c_blocked_by_sniper_override(self, live_env, bypass_first_run):
        """YES@99c is blocked even when sniper override price_guard_min=1/max=99 is used.

        A 99c YES bet also has near-zero margin (wins 1c per contract on loss).
        """
        # Orderbook: yes_ask = 99c
        ob = make_orderbook(no_bid=1)  # no_bid=1 → yes_ask = 100-1 = 99
        signal = make_signal(side="yes", price_cents=93)  # signal was at 93c
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=99, no_price=1), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()

    async def test_no_at_98c_blocked(self, live_env, bypass_first_run):
        """NO@98c is blocked -- historically -25.54 USD at 92.9% WR (need >98%).

        Pattern identical to 97c NO block (IL-10). Added S78 after 28-bet data.
        98c YES is NOT blocked -- 20 bets, 100% WR, +3.02 USD (profitable).
        """
        ob = make_orderbook(yes_bid=2)  # yes_bid=2 → no_ask = 98c
        signal = make_signal(side="no", price_cents=97)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=2, no_price=98), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()


# ── 96c/97c negative-EV bucket guard tests ──────────────────────────────────


class TestSniperNegativeEvBucketGuard:
    """Regression: 96c and 97c-NO are historically negative EV.

    Data (S75 analysis, all-time sniper live bets):
      96c YES: 17 bets, 94.1% WR, -13.35 USD  (needs >96% WR to break even)
      96c NO:  14 bets, 92.9% WR,  -9.09 USD  (needs >96% WR to break even)
      97c NO:  13 bets, 92.3% WR, -15.03 USD  (needs >97% WR to break even)
      97c YES: 11 bets, 100%  WR,  +2.90 USD  (profitable -- keep)

    Guard added S75: block 96c (both sides) and 97c NO only.
    """

    async def test_yes_at_96c_blocked(self, live_env, bypass_first_run):
        """YES@96c is blocked -- historically -13.35 USD at 94.1% WR (need >96%)."""
        ob = make_orderbook(no_bid=4)  # no_bid=4 -> yes_ask = 100-4 = 96c
        signal = make_signal(side="yes", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=96, no_price=4), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_no_at_96c_blocked(self, live_env, bypass_first_run):
        """NO@96c is blocked -- historically -9.09 USD at 92.9% WR (need >96%)."""
        ob = make_orderbook(yes_bid=4)  # yes_bid=4 -> no_ask = 100-4 = 96c
        signal = make_signal(side="no", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=4, no_price=96), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_no_at_97c_blocked(self, live_env, bypass_first_run):
        """NO@97c is blocked -- historically -15.03 USD at 92.3% WR (need >97%)."""
        ob = make_orderbook(yes_bid=3)  # yes_bid=3 -> no_ask = 100-3 = 97c
        signal = make_signal(side="no", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=3, no_price=97), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_yes_at_97c_not_blocked(self, live_env, bypass_first_run):
        """YES@97c is NOT blocked -- historically +2.90 USD at 100% WR (profitable)."""
        ob = make_orderbook(no_bid=3)  # no_bid=3 -> yes_ask = 100-3 = 97c
        signal = make_signal(side="yes", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=97, no_price=3), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_yes_at_95c_not_blocked(self, live_env, bypass_first_run):
        """YES@95c is NOT blocked -- 35 bets, 100% WR, +18.32 USD (profitable)."""
        ob = make_orderbook(no_bid=5)  # no_bid=5 -> yes_ask = 95c
        signal = make_signal(side="yes", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=95, no_price=5), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_yes_at_98c_not_blocked(self, live_env, bypass_first_run):
        """YES@98c is NOT blocked -- 26 bets, 100% WR, +3.47 USD (profitable)."""
        ob = make_orderbook(no_bid=2)  # no_bid=2 -> yes_ask = 98c
        signal = make_signal(side="yes", price_cents=93)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal, make_market(yes_price=98, no_price=2), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="expiry_sniper_v1",
            price_guard_min=1, price_guard_max=99,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()


# ── Iron Law 3: expiry_sniper price_guard_min must be 87 ────────────────────


class TestExpirySnipPriceGuardLaw3:
    """Iron Law 3: expiry_sniper must not fill at prices below the signal price floor.

    The model's price_confidence formula floors at 87c. Any fill far below the
    signal price is off-model territory (trade 2786: signal at 90c, fill at 86c = -19.78 USD).

    S81 implementation: slippage guard in main.py checks `_live_price < signal.price_cents - 3`
    BEFORE orderbook fetch. price_guard_min=1 in live.execute() is intentional to allow
    NO-side bets (YES-equiv can be 5-9c for NO@91-95c, which would be blocked by min=87).
    """

    def test_expiry_sniper_slippage_guard_present_in_main(self):
        """LAW 3: main.py expiry_sniper_loop must contain slippage guard (_MAX_SLIPPAGE_CENTS).

        S81: slippage guard replaces the price_guard_min=87 approach. The slippage guard
        checks current market price vs signal price before placing the order, catching
        the case where market moves from 90c to 86c between signal and execution.

        Fails if the guard is removed from main.py.
        """
        import re
        main_src = open("main.py").read()
        assert "_MAX_SLIPPAGE_CENTS" in main_src, (
            "LAW 3 VIOLATION: _MAX_SLIPPAGE_CENTS slippage guard missing from main.py. "
            "Trade 2786 (YES@86c, -19.78 USD) was caused by missing this guard. "
            "Signal fired at 90c but executed at 86c — must be caught before orderbook fetch."
        )
        # Verify the guard checks against signal.price_cents (not a hardcoded threshold)
        assert "signal.price_cents - _MAX_SLIPPAGE_CENTS" in main_src, (
            "LAW 3 VIOLATION: slippage guard must compare _live_price against signal.price_cents, "
            "not a hardcoded threshold."
        )

    async def test_execute_rejects_86c_when_guard_is_87(self, live_env, bypass_first_run):
        """execute() returns None when YES execution price is 86c and price_guard_min=87."""
        # no_bid=14 -> yes_ask = 100 - 14 = 86c
        ob = make_orderbook(no_bid=14)
        kalshi = make_kalshi_mock()
        db = make_db_mock()
        result = await execute(
            make_signal(side="yes", price_cents=88),
            make_market(yes_price=86),
            ob,
            5.0,
            kalshi,
            db,
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=87,
            price_guard_max=99,
        )
        assert result is None, "execute() must reject 86c when price_guard_min=87"
        kalshi.create_order.assert_not_called()


# ── Per-asset structural loss guards (S81) ───────────────────────────────────


@pytest.mark.asyncio
class TestPerAssetStructuralLossGuards:
    """Regression: XRP and SOL specific price buckets are structurally below break-even.

    XRP/SOL have higher intra-window volatility than BTC/ETH. Specific buckets
    confirmed negative EV via live data:
      KXXRP YES@94c:  15 bets, 93.3% WR, need 94.9%, -9.09 USD  (S81)
      KXXRP YES@95c:  10 bets, 90.0% WR, need 95.0%, -14.27 USD (S88)
      KXXRP YES@97c:   6 bets, 83.3% WR, need 98.0%, -18.04 USD (S81, terrible R/R)
      KXSOL YES@94c:  12 bets, 91.7% WR, need 94.9%, -7.28 USD  (S81)
      KXSOL YES@97c:   8 bets, 87.5% WR, need 97.0%, -17.18 USD (S88)
      BTC/ETH/SOL YES@95c: 100% WR — profitable, NOT blocked

    Guards added S81 (IL-10A/B/C), S88 (IL-19), S88 (IL-20). Revisit at 200+ bets per bucket.
    """

    async def test_xrp_yes_at_94c_blocked(self, live_env, bypass_first_run):
        """KXXRP YES@94c is blocked -- 93.3% WR at 15 bets, need 94.9% break-even."""
        ob = make_orderbook(no_bid=6)  # no_bid=6 -> yes_ask = 94c
        signal = make_signal(side="yes", price_cents=93, ticker="KXXRP15M-26MAR151500-94")
        result = await execute(
            signal,
            make_market(yes_price=94, no_price=6),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_xrp_yes_at_97c_blocked(self, live_env, bypass_first_run):
        """KXXRP YES@97c is blocked -- 83.3% WR at 6 bets, need 98% break-even."""
        ob = make_orderbook(no_bid=3)  # no_bid=3 -> yes_ask = 97c
        signal = make_signal(side="yes", price_cents=93, ticker="KXXRP15M-26MAR151500-94")
        result = await execute(
            signal,
            make_market(yes_price=97, no_price=3),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_sol_yes_at_94c_blocked(self, live_env, bypass_first_run):
        """KXSOL YES@94c is blocked -- 91.7% WR at 12 bets, need 94.9% break-even."""
        ob = make_orderbook(no_bid=6)  # no_bid=6 -> yes_ask = 94c
        signal = make_signal(side="yes", price_cents=93, ticker="KXSOL15M-26MAR151500-94")
        result = await execute(
            signal,
            make_market(yes_price=94, no_price=6),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_btc_yes_at_94c_not_blocked(self, live_env, bypass_first_run):
        """BTC YES@94c is NOT blocked -- BTC/ETH are profitable at 94c."""
        ob = make_orderbook(no_bid=6)  # yes_ask = 94c
        signal = make_signal(side="yes", price_cents=93, ticker="KXBTC15M-26MAR151500-94")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=94, no_price=6),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_eth_yes_at_94c_not_blocked(self, live_env, bypass_first_run):
        """ETH YES@94c is NOT blocked -- BTC/ETH are profitable at 94c."""
        ob = make_orderbook(no_bid=6)  # yes_ask = 94c
        signal = make_signal(side="yes", price_cents=93, ticker="KXETH15M-26MAR151500-94")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=94, no_price=6),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_xrp_no_at_94c_blocked_il28(self, live_env, bypass_first_run):
        """IL-28: KXXRP NO@94c IS blocked -- 17 bets, 94.1% WR, fee-adjusted break-even ~94.4%, -5.29 USD net.

        Previously test asserted result is not None (pre-IL-28). Updated S95 2026-03-17 when
        trade #3292 triggered -19.74 USD loss confirming structural negative EV at NO@94c.
        """
        ob = make_orderbook(yes_bid=6)  # no_ask = 100-6 = 94c
        signal = make_signal(side="no", price_cents=93, ticker="KXXRP15M-26MAR151500-06")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=6, no_price=94),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None
        kalshi.create_order.assert_not_called()

    async def test_btc_no_at_94c_not_blocked_by_il28(self, live_env, bypass_first_run):
        """KXBTC NO@94c is NOT blocked -- IL-28 targets KXXRP only. BTC at 94c NO is profitable."""
        ob = make_orderbook(yes_bid=6)
        signal = make_signal(side="no", price_cents=93, ticker="KXBTC15M-26MAR151500-06")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=6, no_price=94),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_xrp_yes_at_95c_blocked_il20(self, live_env, bypass_first_run):
        """KXXRP YES@95c IS blocked (IL-20) -- 90.0% WR at 10 bets, need 95.0% break-even.

        Previously this test asserted result is not None (pre-IL-20). Updated S88 when
        loss at KXXRP15M-26MAR160415-15 confirmed structural negative EV at 95c.
        """
        ob = make_orderbook(no_bid=5)  # yes_ask = 95c
        signal = make_signal(side="yes", price_cents=93, ticker="KXXRP15M-26MAR151500-95")
        result = await execute(
            signal,
            make_market(yes_price=95, no_price=5),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_sol_yes_at_97c_blocked(self, live_env, bypass_first_run):
        """KXSOL YES@97c is blocked -- IL-19: 87.5% WR at 8 bets, need 97% break-even, -17.18 USD.

        S88 2026-03-16: loss at KXSOL15M-26MAR160200-00 triggered analysis.
        BTC/ETH YES@97c remain profitable (100% WR) -- SOL only blocked.
        """
        ob = make_orderbook(no_bid=3)  # no_bid=3 -> yes_ask = 97c
        signal = make_signal(side="yes", price_cents=93, ticker="KXSOL15M-26MAR160200-00")
        result = await execute(
            signal,
            make_market(yes_price=97, no_price=3),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_btc_yes_at_97c_not_blocked(self, live_env, bypass_first_run):
        """KXBTC YES@97c is NOT blocked -- 100% WR, profitable. Only SOL is blocked at 97c."""
        ob = make_orderbook(no_bid=3)  # yes_ask = 97c
        signal = make_signal(side="yes", price_cents=93, ticker="KXBTC15M-26MAR160200-00")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=97, no_price=3),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_eth_yes_at_97c_not_blocked(self, live_env, bypass_first_run):
        """KXETH YES@97c is NOT blocked -- 100% WR, profitable. Only SOL is blocked at 97c."""
        ob = make_orderbook(no_bid=3)  # yes_ask = 97c
        signal = make_signal(side="yes", price_cents=93, ticker="KXETH15M-26MAR160200-00")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=97, no_price=3),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None

    async def test_xrp_yes_at_95c_blocked(self, live_env, bypass_first_run):
        """KXXRP YES@95c is blocked -- IL-20: 90.0% WR at 10 bets, need 95.0% break-even, -14.27 USD.

        S88 2026-03-16: loss at KXXRP15M-26MAR160415-15 triggered analysis.
        SOL/BTC/ETH YES@95c remain profitable (100% WR) -- XRP only blocked.
        """
        ob = make_orderbook(no_bid=5)  # no_bid=5 -> yes_ask = 95c
        signal = make_signal(side="yes", price_cents=93, ticker="KXXRP15M-26MAR160415-15")
        result = await execute(
            signal,
            make_market(yes_price=95, no_price=5),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_sol_yes_at_95c_not_blocked(self, live_env, bypass_first_run):
        """KXSOL YES@95c is NOT blocked -- 100% WR, profitable. Only XRP is blocked at 95c."""
        ob = make_orderbook(no_bid=5)  # yes_ask = 95c
        signal = make_signal(side="yes", price_cents=93, ticker="KXSOL15M-26MAR160415-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=95, no_price=5),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_btc_yes_at_95c_not_blocked(self, live_env, bypass_first_run):
        """KXBTC YES@95c is NOT blocked -- 100% WR, profitable. Only XRP is blocked at 95c."""
        ob = make_orderbook(no_bid=5)  # yes_ask = 95c
        signal = make_signal(side="yes", price_cents=93, ticker="KXBTC15M-26MAR160415-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=95, no_price=5),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()
        kalshi.create_order.assert_called_once()

    async def test_xrp_no_at_92c_blocked(self, live_env, bypass_first_run):
        """IL-21: KXXRP NO@92c blocked -- 75% WR needs 92% break-even, structurally unrecoverable."""
        ob = make_orderbook(yes_bid=8)  # no_ask = 92c
        signal = make_signal(side="no", price_cents=90, ticker="KXXRP15M-26MAR170000-15")
        result = await execute(
            signal,
            make_market(yes_price=8, no_price=92),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_btc_no_at_92c_not_blocked(self, live_env, bypass_first_run):
        """KXBTC NO@92c is NOT blocked -- IL-21 targets KXXRP only."""
        ob = make_orderbook(yes_bid=8)  # no_ask = 92c
        signal = make_signal(side="no", price_cents=90, ticker="KXBTC15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=8, no_price=92),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_eth_no_at_92c_not_blocked(self, live_env, bypass_first_run):
        """KXETH NO@92c is NOT blocked -- IL-21 targets KXXRP only."""
        ob = make_orderbook(yes_bid=8)  # no_ask = 92c
        signal = make_signal(side="no", price_cents=90, ticker="KXETH15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=8, no_price=92),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_sol_no_at_92c_blocked(self, live_env, bypass_first_run):
        """IL-22: KXSOL NO@92c blocked -- 67% WR needs 92% break-even, same asymmetric payout as IL-21."""
        ob = make_orderbook(yes_bid=8)  # no_ask = 92c
        signal = make_signal(side="no", price_cents=90, ticker="KXSOL15M-26MAR170000-15")
        result = await execute(
            signal,
            make_market(yes_price=8, no_price=92),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_sol_no_at_91c_not_blocked(self, live_env, bypass_first_run):
        """KXSOL NO@91c is NOT blocked -- IL-22 targets 92c only. 91c is 100% WR profitable."""
        ob = make_orderbook(yes_bid=9)  # no_ask = 91c
        signal = make_signal(side="no", price_cents=91, ticker="KXSOL15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=9, no_price=91),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_btc_no_at_92c_not_blocked_by_il22(self, live_env, bypass_first_run):
        """KXBTC NO@92c is NOT blocked -- IL-22 targets KXSOL only."""
        ob = make_orderbook(yes_bid=8)  # no_ask = 92c
        signal = make_signal(side="no", price_cents=90, ticker="KXBTC15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=8, no_price=92),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_xrp_yes_at_98c_blocked(self, live_env, bypass_first_run):
        """IL-23: KXXRP YES@98c blocked -- 90.9% WR at 11 bets, need 98% break-even, -17.89 USD."""
        ob = make_orderbook(no_bid=2)  # no_bid=2 -> yes_ask = 98c
        signal = make_signal(side="yes", price_cents=97, ticker="KXXRP15M-26MAR170000-15")
        result = await execute(
            signal,
            make_market(yes_price=98, no_price=2),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_btc_yes_at_98c_not_blocked_by_il23(self, live_env, bypass_first_run):
        """KXBTC YES@98c is NOT blocked -- IL-23 targets KXXRP only. BTC YES@98c is 100% WR."""
        ob = make_orderbook(no_bid=2)  # no_bid=2 -> yes_ask = 98c
        signal = make_signal(side="yes", price_cents=97, ticker="KXBTC15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=98, no_price=2),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_eth_yes_at_98c_not_blocked_by_il23(self, live_env, bypass_first_run):
        """KXETH YES@98c is NOT blocked -- IL-23 targets KXXRP only. ETH YES@98c is 100% WR (16 bets)."""
        ob = make_orderbook(no_bid=2)  # no_bid=2 -> yes_ask = 98c
        signal = make_signal(side="yes", price_cents=97, ticker="KXETH15M-26MAR170000-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=98, no_price=2),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_sol_no_at_95c_blocked(self, live_env, bypass_first_run):
        """IL-24: KXSOL NO@95c blocked -- 93.8% WR at 16 bets, need 95% break-even, -31.50 USD."""
        ob = make_orderbook(yes_bid=5)  # yes_bid=5 -> no_ask=95c
        signal = make_signal(side="no", price_cents=94, ticker="KXSOL15M-26MAR170015-15")
        result = await execute(
            signal,
            make_market(yes_price=5, no_price=95),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_btc_no_at_95c_not_blocked_by_il24(self, live_env, bypass_first_run):
        """KXBTC NO@95c is NOT blocked -- IL-24 targets KXSOL only. BTC NO@95c is 100% WR (11 bets)."""
        ob = make_orderbook(yes_bid=5)  # yes_bid=5 -> no_ask=95c
        signal = make_signal(side="no", price_cents=94, ticker="KXBTC15M-26MAR170015-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=5, no_price=95),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_eth_no_at_95c_not_blocked_by_il24(self, live_env, bypass_first_run):
        """KXETH NO@95c is NOT blocked -- IL-24 targets KXSOL only. ETH NO@95c is 100% WR (10 bets)."""
        ob = make_orderbook(yes_bid=5)  # yes_bid=5 -> no_ask=95c
        signal = make_signal(side="no", price_cents=94, ticker="KXETH15M-26MAR170015-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=5, no_price=95),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_btc_yes_at_88c_blocked(self, live_env, bypass_first_run):
        """IL-29: KXBTC YES@88c blocked -- 50% WR at 2 bets, need 88% break-even, -17.93 USD."""
        ob = make_orderbook(yes_bid=88)
        signal = make_signal(side="yes", price_cents=88, ticker="KXBTC15M-26MAR170415-15")
        result = await execute(
            signal,
            make_market(yes_price=88, no_price=12),
            ob,
            5.0,
            make_kalshi_mock(),
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is None

    async def test_eth_yes_at_88c_not_blocked_by_il29(self, live_env, bypass_first_run):
        """KXETH YES@88c is NOT blocked -- IL-29 targets KXBTC only. ETH YES@88c is 100% WR."""
        ob = make_orderbook(yes_bid=88)
        signal = make_signal(side="yes", price_cents=88, ticker="KXETH15M-26MAR170415-15")
        kalshi = make_kalshi_mock()
        result = await execute(
            signal,
            make_market(yes_price=88, no_price=12),
            ob,
            5.0,
            kalshi,
            make_db_mock(),
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
        )
        assert result is not None
        kalshi.create_order.assert_called_once()


# ── post_only taker fallback (S88) ───────────────────────────────────────────


@pytest.mark.asyncio
class TestPostOnlyTakerFallback:
    """Regression: drift strategies generate 50+ post_only rejections/session.

    When post_only=True and Kalshi returns 400 "post only cross", the market
    moved and our limit price would fill as taker. Signal is still valid.
    execute() should retry immediately as taker (post_only=False).

    S88 2026-03-16: drift loops missed ~50 profitable trades/session from
    post_only rejections with no fallback.
    """

    async def test_post_only_cross_retries_as_taker(self, live_env, bypass_first_run):
        """post_only=True fails with 'post only cross' → retries as taker, order placed."""
        ob = make_orderbook(no_bid=45)
        signal = make_signal(side="yes", price_cents=50)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        post_only_error = KalshiAPIError(
            400, {"error": {"code": "invalid_order", "message": "invalid order",
                            "details": "post only cross"}}
        )
        # First call raises post_only_cross; second call (taker) succeeds
        kalshi.create_order.side_effect = [post_only_error, kalshi.create_order.return_value]

        result = await execute(
            signal, make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True,
        )

        assert result is not None
        assert kalshi.create_order.call_count == 2
        # Second call must NOT have post_only=True
        second_call_kwargs = kalshi.create_order.call_args_list[1][1]
        assert second_call_kwargs.get("post_only") is False or second_call_kwargs.get("post_only") is None

    async def test_post_only_cross_taker_retry_fails_returns_none(
        self, live_env, bypass_first_run
    ):
        """If taker retry also fails, returns None — no silent errors."""
        ob = make_orderbook(no_bid=45)
        signal = make_signal(side="yes", price_cents=50)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        post_only_error = KalshiAPIError(
            400, {"error": {"code": "invalid_order", "message": "invalid order",
                            "details": "post only cross"}}
        )
        taker_error = KalshiAPIError(400, {"error": {"code": "insufficient_funds"}})
        kalshi.create_order.side_effect = [post_only_error, taker_error]

        result = await execute(
            signal, make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True,
        )

        assert result is None
        assert kalshi.create_order.call_count == 2
        db.save_trade.assert_not_called()

    async def test_non_post_only_error_not_retried(self, live_env, bypass_first_run):
        """Non-post_only errors do NOT trigger retry — only 'post only cross' does."""
        ob = make_orderbook(no_bid=45)
        signal = make_signal(side="yes", price_cents=50)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        other_error = KalshiAPIError(400, {"error": {"code": "insufficient_funds"}})
        kalshi.create_order.side_effect = other_error

        result = await execute(
            signal, make_market(), ob, 5.0, kalshi, db,
            live_confirmed=True, strategy_name="btc_drift_v1",
            post_only=True,
        )

        assert result is None
        assert kalshi.create_order.call_count == 1  # no retry


# ── Sniper per-call max_slippage_cents guard (S85) ───────────────────────────


@pytest.mark.asyncio
class TestSniperMaxSlippageCents:
    """Regression: SOL YES@83c loss on 2026-03-15 23:07 UTC.

    Signal fired at 90c. main.py slippage guard checked _live_price (90c >= 87c, passed).
    Orderbook showed 83c ask. live.py slippage guard: |83-90|=7c < 10c default → passed.
    Result: order placed at 83c, SOL dropped, -18.26 USD loss.

    Fix: execute() now accepts max_slippage_cents kwarg. Sniper passes 3.
    When orderbook diverges 3c+ from signal, execution is rejected.
    """

    async def test_sniper_rejects_7c_slippage_when_max_is_3(
        self, live_env, bypass_first_run
    ):
        """SOL YES signal@90c, orderbook ask=83c → 7c slip > 3c max → rejected."""
        ob = make_orderbook(no_bid=17)  # yes_ask = 100-17 = 83c
        signal = make_signal(side="yes", price_cents=90, ticker="KXSOL15M-26MAR151915-15")
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal,
            make_market(yes_price=83),
            ob,
            18.0,
            kalshi,
            db,
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
            max_slippage_cents=3,
        )

        assert result is None
        kalshi.create_order.assert_not_called()
        db.save_trade.assert_not_called()

    async def test_sniper_allows_2c_slippage_when_max_is_3(
        self, live_env, bypass_first_run
    ):
        """SOL YES signal@90c, orderbook ask=88c → 2c slip < 3c max → proceeds."""
        ob = make_orderbook(no_bid=12)  # yes_ask = 100-12 = 88c
        signal = make_signal(side="yes", price_cents=90, ticker="KXSOL15M-26MAR151915-15")
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal,
            make_market(yes_price=88),
            ob,
            18.0,
            kalshi,
            db,
            live_confirmed=True,
            strategy_name="expiry_sniper_v1",
            price_guard_min=1,
            price_guard_max=99,
            max_slippage_cents=3,
        )

        assert result is not None
        kalshi.create_order.assert_called_once()

    async def test_default_slippage_still_10c_for_drift(
        self, live_env, bypass_first_run
    ):
        """Drift strategies: no max_slippage_cents → default 10c guard applies.

        signal@55c, exec@64c → 9c slip < 10c default → proceeds (was blocked at 3c).
        """
        ob = make_orderbook(no_bid=36)  # yes_ask = 100-36 = 64c
        signal = make_signal(side="yes", price_cents=55)
        kalshi = make_kalshi_mock()
        db = make_db_mock()

        result = await execute(
            signal,
            make_market(yes_price=64),
            ob,
            5.0,
            kalshi,
            db,
            live_confirmed=True,
            strategy_name="btc_drift_v1",
        )

        assert result is not None
        kalshi.create_order.assert_called_once()
        kalshi.create_order.assert_called_once()
