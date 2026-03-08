"""
Regression tests for copy_trade_loop in main.py.

Focus: kill switch integration and live/paper execution paths.
These tests prevent regression of the bug where check_paper_order_allowed()
was called with no arguments (TypeError) and as a raw bool (always-truthy tuple).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ────────────────────────────────────────────────────────


def _make_whale(name="WhaleFoo", proxy_wallet="0xabc", smart_score=85.0):
    w = MagicMock()
    w.name = name
    w.proxy_wallet = proxy_wallet
    w.smart_score = smart_score
    return w


def _make_trade(
    condition_id="0xcond001",
    outcome="Yes",
    price=0.55,
    size=500.0,
    title="Thunder NBA Championship",
    slug="nba-thunder",
    transaction_hash="0xtx001",
    side="BUY",
    proxy_wallet="0xabc",
    timestamp=1_772_500_000 - 1_800,  # 30 min ago — within 15min-1hr window
):
    t = MagicMock()
    t.condition_id = condition_id
    t.outcome = outcome
    t.price = price
    t.size = size
    t.title = title
    t.slug = slug
    t.transaction_hash = transaction_hash
    t.side = side
    t.proxy_wallet = proxy_wallet
    t.timestamp = timestamp
    return t


def _make_pm_market(
    yes_identifier="tec-thunder-2026",
    no_identifier="tec-thunder-2026-no",
    yes_price=0.55,
):
    m = MagicMock()
    m.yes_identifier = yes_identifier
    m.no_identifier = no_identifier
    m.yes_price = yes_price
    m.active = True
    m.closed = False
    m.market_id = "mkt001"
    m.raw = {"title": "thunder nba"}
    return m


def _make_signal(side="yes", price_cents=55, edge_pct=0.08, win_prob=0.63, ticker="0xcond001"):
    sig = MagicMock()
    sig.side = side
    sig.price_cents = price_cents
    sig.edge_pct = edge_pct
    sig.win_prob = win_prob
    sig.ticker = ticker
    sig.reason = "copy test signal"
    return sig


def _make_kill_switch(paper_allowed=True, live_allowed=True):
    ks = MagicMock()
    ok_paper = (paper_allowed, "OK" if paper_allowed else "blocked-reason")
    ok_live  = (live_allowed,  "OK" if live_allowed  else "blocked-reason")
    ks.check_paper_order_allowed = MagicMock(return_value=ok_paper)
    ks.check_order_allowed       = MagicMock(return_value=ok_live)
    ks.record_trade              = MagicMock()
    return ks


def _make_db(bankroll=80.0):
    db = MagicMock()
    db.latest_bankroll = MagicMock(return_value=bankroll)
    db.save_trade      = MagicMock(return_value=42)
    return db


def _make_paper_exec_result(trade_id="pt-001", cost_usd=5.0):
    return {"trade_id": trade_id, "cost_usd": cost_usd}


# ── test class ─────────────────────────────────────────────────────


class TestCopyTradeLoopKillSwitch:
    """Regression tests for kill switch integration in copy_trade_loop."""

    async def _run_one_cycle(
        self,
        *,
        paper_allowed=True,
        live_executor_enabled=False,
        order_is_filled=False,
    ):
        """
        Run copy_trade_loop through one whale poll cycle, then cancel it.
        Returns a dict of call observations for assertions.
        """
        from main import copy_trade_loop
        from src.platforms.polymarket import PolymarketOrderResult

        whale = _make_whale()
        trade = _make_trade()
        pm_market = _make_pm_market()
        signal = _make_signal()
        kill_switch = _make_kill_switch(
            paper_allowed=paper_allowed,
            live_allowed=paper_allowed,  # same flag for simplicity
        )
        db = _make_db()
        pm_client = AsyncMock()
        pm_client.get_markets = AsyncMock(return_value=[pm_market])

        order_result = PolymarketOrderResult(
            order_id="ord-test",
            executions=[{"quantity": 1}] if order_is_filled else [],
        )
        pm_client.place_order = AsyncMock(return_value=order_result)

        paper_exec_result = _make_paper_exec_result()
        mock_paper_exec = MagicMock()
        mock_paper_exec.execute = MagicMock(return_value=paper_exec_result)

        sleep_calls = [0]

        async def fake_sleep(sec):
            sleep_calls[0] += 1
            if sleep_calls[0] >= 2:  # cancel after initial delay + one cycle
                raise asyncio.CancelledError()

        with (
            patch("main.asyncio.sleep", side_effect=fake_sleep),
            patch("src.data.predicting_top.PredictingTopClient") as MockPT,
            patch("src.data.whale_watcher.WhaleDataClient") as MockWD,
            patch("src.strategies.copy_trader_v1.CopyTraderStrategy") as MockStrategy,
            patch("src.strategies.copy_trader_v1.find_market_for_trade", return_value=pm_market),
            patch("src.execution.paper.PaperExecutor", return_value=mock_paper_exec),
        ):
            mock_pt_inst = AsyncMock()
            mock_pt_inst.get_leaderboard = AsyncMock(return_value=[whale])
            MockPT.return_value = mock_pt_inst

            mock_wd_inst = AsyncMock()
            mock_wd_inst.get_trades = AsyncMock(return_value=[trade])
            mock_wd_inst.get_positions = AsyncMock(return_value=[])
            MockWD.return_value = mock_wd_inst

            mock_strat_inst = MagicMock()
            mock_strat_inst.name = "copy_trader_v1"
            mock_strat_inst.generate_signal = MagicMock(return_value=signal)
            MockStrategy.return_value = mock_strat_inst

            with pytest.raises(asyncio.CancelledError):
                await copy_trade_loop(
                    pm_client=pm_client,
                    db=db,
                    kill_switch=kill_switch,
                    initial_delay_sec=0,
                    poll_interval_sec=0,
                    live_executor_enabled=live_executor_enabled,
                )

        return {
            "kill_switch": kill_switch,
            "db": db,
            "pm_client": pm_client,
            "paper_exec": mock_paper_exec,
        }

    @pytest.mark.asyncio
    async def test_paper_path_calls_kill_switch_with_correct_args(self):
        """
        Regression: check_paper_order_allowed must be called with trade_usd
        and current_bankroll_usd (not zero-arg which raises TypeError).
        """
        obs = await self._run_one_cycle(paper_allowed=True)
        ks = obs["kill_switch"]
        assert ks.check_paper_order_allowed.called, "check_paper_order_allowed not called"
        call_kwargs = ks.check_paper_order_allowed.call_args
        # Must pass trade_usd AND current_bankroll_usd
        assert call_kwargs is not None
        all_args = {**call_kwargs.kwargs}
        if call_kwargs.args:
            all_args.update({"trade_usd": call_kwargs.args[0], "current_bankroll_usd": call_kwargs.args[1]})
        assert "trade_usd" in all_args or len(call_kwargs.args) >= 2, \
            f"trade_usd not passed. Got args={call_kwargs.args} kwargs={call_kwargs.kwargs}"
        assert "current_bankroll_usd" in all_args or len(call_kwargs.args) >= 2, \
            f"current_bankroll_usd not passed. Got args={call_kwargs.args} kwargs={call_kwargs.kwargs}"

    @pytest.mark.asyncio
    async def test_paper_path_executes_when_allowed(self):
        """Paper trade is executed when kill switch allows it."""
        obs = await self._run_one_cycle(paper_allowed=True)
        assert obs["paper_exec"].execute.called, "PaperExecutor.execute should be called"

    @pytest.mark.asyncio
    async def test_paper_path_blocked_when_kill_switch_denies(self):
        """Paper trade is NOT executed when kill switch blocks it."""
        obs = await self._run_one_cycle(paper_allowed=False)
        assert not obs["paper_exec"].execute.called, \
            "PaperExecutor.execute must NOT be called when kill switch blocks"

    @pytest.mark.asyncio
    async def test_live_path_calls_place_order_when_enabled(self):
        """Live path calls pm_client.place_order() when live_executor_enabled=True."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
        )
        assert obs["pm_client"].place_order.called, "place_order must be called in live mode"

    @pytest.mark.asyncio
    async def test_live_path_does_not_call_paper_exec(self):
        """When live_executor_enabled=True, PaperExecutor.execute is NOT called."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
        )
        assert not obs["paper_exec"].execute.called, \
            "PaperExecutor.execute must NOT be called in live mode"

    @pytest.mark.asyncio
    async def test_live_path_fok_fill_records_in_db(self):
        """A filled FOK order writes a DB trade record with is_paper=False."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
            order_is_filled=True,
        )
        assert obs["db"].save_trade.called, "DB save_trade must be called on FOK fill"
        call_kwargs = obs["db"].save_trade.call_args.kwargs
        assert call_kwargs.get("is_paper") is False, "Live trade must set is_paper=False"

    @pytest.mark.asyncio
    async def test_live_path_fok_no_fill_does_not_record_db(self):
        """A FOK order with no fill must NOT write to DB (no money spent)."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
            order_is_filled=False,
        )
        assert not obs["db"].save_trade.called, \
            "DB save_trade must NOT be called when FOK has no fill"

    @pytest.mark.asyncio
    async def test_live_path_fok_fill_calls_record_trade(self):
        """A filled FOK order increments the hourly trade counter via kill_switch.record_trade."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
            order_is_filled=True,
        )
        ks = obs["kill_switch"]
        assert ks.record_trade.called, "kill_switch.record_trade must be called on live fill"

    @pytest.mark.asyncio
    async def test_live_path_fok_no_fill_does_not_call_record_trade(self):
        """No-fill FOK must not increment hourly trade counter."""
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
            order_is_filled=False,
        )
        ks = obs["kill_switch"]
        assert not ks.record_trade.called, \
            "kill_switch.record_trade must NOT be called when FOK has no fill"

    @pytest.mark.asyncio
    async def test_live_path_uses_fok_by_default(self):
        """Live path always uses FOK — never GTC — to avoid being liquidity provider."""
        from src.platforms.polymarket import TimeInForce
        obs = await self._run_one_cycle(
            live_executor_enabled=True,
            paper_allowed=True,
            order_is_filled=True,
        )
        call_kwargs = obs["pm_client"].place_order.call_args.kwargs
        assert call_kwargs.get("tif") == TimeInForce.FOK, \
            f"copy_trade_loop must use FOK. Got: {call_kwargs.get('tif')}"
