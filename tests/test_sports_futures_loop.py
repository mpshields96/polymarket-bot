"""
Tests for sports_futures_loop in main.py.

Focus:
- kill switch integration (check_paper_order_allowed called with correct args)
- paper execution path fires when signal generated
- kill switch block prevents paper execution
- SDATA_KEY missing → loop exits gracefully (no crash)
- strategy.name used for PaperExecutor (not hardcoded)
- hard_stop prevents poll execution
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_kill_switch(
    paper_allowed: bool = True,
    hard_stopped: bool = False,
) -> MagicMock:
    ks = MagicMock()
    ks.is_hard_stopped = hard_stopped
    ok = (paper_allowed, "OK" if paper_allowed else "paper blocked reason")
    ks.check_paper_order_allowed = MagicMock(return_value=ok)
    ks.record_trade = MagicMock()
    return ks


def _make_db(bankroll: float = 80.0) -> MagicMock:
    db = MagicMock()
    db.latest_bankroll = MagicMock(return_value=bankroll)
    db.save_trade = MagicMock(return_value=99)
    return db


def _make_pm_client(futures_markets: list) -> MagicMock:
    client = MagicMock()
    client.get_markets = AsyncMock(return_value=futures_markets)
    return client


def _make_pm_market(
    market_type: str = "futures",
    yes_price: float = 0.20,
    identifier: str = "nba-champion-2026-mem-yes",
) -> MagicMock:
    m = MagicMock()
    m.market_type = market_type
    m.active = True
    m.closed = False
    m.yes_price = yes_price
    m.yes_identifier = identifier
    m.no_identifier = identifier.replace("-yes", "-no")
    m.yes_price_cents = round(yes_price * 100)
    m.no_price_cents = 100 - round(yes_price * 100)
    m.raw = {
        "title": "Memphis",
        "sportsMarketType": "futures",
        "sportsMarketTypeV2": "SPORTS_MARKET_TYPE_FUTURE",
    }
    m.question = "2026 NBA Champion"
    return m


def _make_signal(
    side: str = "yes",
    price_cents: int = 20,
    edge_pct: float = 0.10,
    ticker: str = "nba-champion-2026-mem-yes",
) -> MagicMock:
    sig = MagicMock()
    sig.side = side
    sig.price_cents = price_cents
    sig.edge_pct = edge_pct
    sig.win_prob = 0.30
    sig.confidence = 0.8
    sig.ticker = ticker
    sig.reason = "Memphis PM=0.20 vs odds 0.30 (+10pp YES)"
    return sig


# ── test class ────────────────────────────────────────────────────────────────

class TestSportsFuturesLoop:
    """Tests for sports_futures_loop kill switch + paper execution integration."""

    async def _run_one_cycle(
        self,
        *,
        paper_allowed: bool = True,
        hard_stopped: bool = False,
        signals: list | None = None,
        sdata_key_missing: bool = False,
    ) -> dict:
        """
        Run sports_futures_loop through one poll cycle, then cancel.
        Returns call observations.
        """
        from main import sports_futures_loop

        if signals is None:
            signals = [_make_signal()]

        ks = _make_kill_switch(paper_allowed=paper_allowed, hard_stopped=hard_stopped)
        db = _make_db()
        pm_client = _make_pm_client([_make_pm_market()])

        paper_exec_result = {"trade_id": "sf-paper-001", "cost_usd": 5.0}

        env_patch = {"SDATA_KEY": ""} if sdata_key_missing else {"SDATA_KEY": "test-key-xyz"}

        # Provide at least one odds entry so the loop doesn't skip the scan
        _dummy_odds = MagicMock()
        mock_feed = MagicMock()
        mock_feed.get_nba_championship = AsyncMock(return_value=[_dummy_odds])
        mock_feed.get_nhl_championship = AsyncMock(return_value=[])
        mock_feed.get_ncaab_championship = AsyncMock(return_value=[])
        mock_feed.quota_status = MagicMock(return_value="5/500")

        mock_strategy = MagicMock()
        mock_strategy.name = "sports_futures_v1"
        mock_strategy.scan_for_signals = MagicMock(return_value=signals)

        mock_paper_exec = MagicMock()
        mock_paper_exec.execute = MagicMock(return_value=paper_exec_result)

        with patch.dict(os.environ, env_patch, clear=False):
            with patch("src.data.odds_api.SportsFeed.load_from_env",
                       return_value=mock_feed):
                with patch("src.strategies.sports_futures_v1.SportsFuturesStrategy",
                           return_value=mock_strategy):
                    with patch("src.execution.paper.PaperExecutor",
                               return_value=mock_paper_exec):
                        task = asyncio.create_task(
                            sports_futures_loop(
                                pm_client=pm_client,
                                db=db,
                                kill_switch=ks,
                                initial_delay_sec=0.0,
                                poll_interval_sec=9999,
                            )
                        )
                        # Let one iteration run
                        await asyncio.sleep(0.05)
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

        return {
            "kill_switch": ks,
            "paper_exec": mock_paper_exec,
            "pm_client": pm_client,
            "strategy": mock_strategy,
        }

    @pytest.mark.asyncio
    async def test_paper_executes_when_signal_and_allowed(self):
        """Signal generated + kill switch allows → paper_exec.execute() called."""
        obs = await self._run_one_cycle(paper_allowed=True, signals=[_make_signal()])
        obs["paper_exec"].execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_kill_switch_check_called_with_correct_args(self):
        """check_paper_order_allowed must be called with (trade_usd=5.0, current_bankroll_usd=80.0)."""
        obs = await self._run_one_cycle(paper_allowed=True, signals=[_make_signal()])
        ks = obs["kill_switch"]
        ks.check_paper_order_allowed.assert_called_once_with(
            trade_usd=5.0,
            current_bankroll_usd=80.0,
        )

    @pytest.mark.asyncio
    async def test_paper_blocked_when_kill_switch_says_no(self):
        """Kill switch blocks paper order → paper_exec.execute() NOT called."""
        obs = await self._run_one_cycle(paper_allowed=False, signals=[_make_signal()])
        obs["paper_exec"].execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_execution_when_no_signals(self):
        """Zero signals → kill switch check not called, paper_exec not called."""
        obs = await self._run_one_cycle(paper_allowed=True, signals=[])
        obs["kill_switch"].check_paper_order_allowed.assert_not_called()
        obs["paper_exec"].execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_hard_stop_skips_poll(self):
        """Hard stop active → PM markets not fetched, no execution."""
        obs = await self._run_one_cycle(
            hard_stopped=True, signals=[_make_signal()]
        )
        # PM client get_markets should NOT be called when hard stopped
        obs["pm_client"].get_markets.assert_not_called()
        obs["paper_exec"].execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_strategy_name_passed_to_paper_executor(self):
        """PaperExecutor must be constructed with strategy_name=strategy.name (not hardcoded)."""
        from main import sports_futures_loop

        ks = _make_kill_switch()
        db = _make_db()
        pm_client = _make_pm_client([_make_pm_market()])

        captured_kwargs: dict = {}

        def _capture_paper_exec(*args, **kwargs):
            captured_kwargs.update(kwargs)
            mock = MagicMock()
            mock.execute = MagicMock(return_value=None)
            return mock

        with patch.dict(os.environ, {"SDATA_KEY": "test-key-xyz"}, clear=False):
            mock_feed = MagicMock()
            mock_feed.get_nba_championship = AsyncMock(return_value=[])
            mock_feed.get_nhl_championship = AsyncMock(return_value=[])
            mock_feed.get_ncaab_championship = AsyncMock(return_value=[])
            mock_feed.quota_status = MagicMock(return_value="0/500")

            with patch("src.data.odds_api.SportsFeed.load_from_env",
                       return_value=mock_feed):
                with patch("src.execution.paper.PaperExecutor",
                           side_effect=_capture_paper_exec):
                    task = asyncio.create_task(
                        sports_futures_loop(
                            pm_client=pm_client,
                            db=db,
                            kill_switch=ks,
                            initial_delay_sec=0.0,
                            poll_interval_sec=9999,
                        )
                    )
                    await asyncio.sleep(0.02)
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        assert captured_kwargs.get("strategy_name") == "sports_futures_v1", (
            f"PaperExecutor strategy_name must be 'sports_futures_v1', "
            f"got {captured_kwargs.get('strategy_name')!r}"
        )

    @pytest.mark.asyncio
    async def test_missing_sdata_key_loop_exits_gracefully(self):
        """SDATA_KEY missing → loop exits without crashing (RuntimeError handled)."""
        from main import sports_futures_loop

        ks = _make_kill_switch()
        db = _make_db()
        pm_client = _make_pm_client([_make_pm_market()])

        # Load_from_env raises RuntimeError when key is missing
        with patch(
            "src.data.odds_api.SportsFeed.load_from_env",
            side_effect=RuntimeError("SDATA_KEY not set"),
        ):
            # Should complete without raising — loop returns early
            await asyncio.wait_for(
                sports_futures_loop(
                    pm_client=pm_client,
                    db=db,
                    kill_switch=ks,
                    initial_delay_sec=0.0,
                    poll_interval_sec=9999,
                ),
                timeout=2.0,
            )
        # No crash = pass

    @pytest.mark.asyncio
    async def test_multiple_signals_all_checked_and_executed(self):
        """Two signals → kill switch checked twice, paper_exec called twice."""
        sigs = [_make_signal(ticker="tkr1"), _make_signal(ticker="tkr2")]
        obs = await self._run_one_cycle(paper_allowed=True, signals=sigs)
        assert obs["kill_switch"].check_paper_order_allowed.call_count == 2
        assert obs["paper_exec"].execute.call_count == 2
