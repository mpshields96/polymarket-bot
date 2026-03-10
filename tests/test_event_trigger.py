"""
Tests for event-driven asyncio.Condition trigger in main.py.

TDD — these tests were written BEFORE modifying main.py.

Tests:
1. btc_price_monitor fires condition when BTC moves >= threshold
2. btc_price_monitor does NOT fire for moves below threshold
3. btc_price_monitor updates reference price after firing
4. _wait_for_btc_move returns True when condition fires before timeout
5. _wait_for_btc_move returns False on timeout
6. _wait_for_btc_move with condition=None just awaits asyncio.sleep
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestBtcPriceMonitor:
    """Tests for the btc_price_monitor() coroutine added to main.py."""

    async def test_notifies_condition_on_significant_move(self):
        """Price move >= threshold triggers condition.notify_all()."""
        from main import btc_price_monitor

        condition = asyncio.Condition()
        notified = []

        async def waiter():
            async with condition:
                await condition.wait()
            notified.append(True)

        # Mock feed: first price 67000, then 67500 (0.75% move, above 0.05% threshold)
        call_count = 0

        def make_feed(prices):
            feed = MagicMock()
            call_idx = 0

            def get_price():
                nonlocal call_idx
                p = prices[min(call_idx, len(prices) - 1)]
                call_idx += 1
                return p

            feed.current_price = get_price
            return feed

        feed = make_feed([67000.0, 67000.0, 67500.0, 67500.0])

        waiter_task = asyncio.create_task(waiter())

        # Run monitor for a few check cycles (0.5s each, patched to instant)
        async def run_monitor_briefly():
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, None, asyncio.CancelledError()]
                try:
                    await btc_price_monitor(
                        btc_feed=feed,
                        condition=condition,
                        min_move_pct=0.05,
                        check_interval_sec=0.001,
                    )
                except asyncio.CancelledError:
                    pass

        await asyncio.gather(
            run_monitor_briefly(),
            asyncio.sleep(0.1),  # give waiter time to receive notification
        )
        # Cancel waiter if still running
        if not waiter_task.done():
            waiter_task.cancel()
            try:
                await waiter_task
            except asyncio.CancelledError:
                pass

        assert len(notified) >= 1

    async def test_does_not_notify_on_small_move(self):
        """Move below threshold does NOT trigger condition."""
        from main import btc_price_monitor

        condition = asyncio.Condition()
        notified = []

        # Track if notify_all is called by patching the condition
        original_notify = condition.notify_all
        notify_called = []

        async def patched_notify_all():
            notify_called.append(True)
            return original_notify()

        condition.notify_all = patched_notify_all

        # Feed: 67000 → 67001 (0.0015% move — below 0.05% threshold)
        call_idx = 0
        prices = [67000.0, 67001.0, 67001.0]

        def get_price():
            nonlocal call_idx
            p = prices[min(call_idx, len(prices) - 1)]
            call_idx += 1
            return p

        feed = MagicMock()
        feed.current_price = get_price

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, asyncio.CancelledError()]
            try:
                await btc_price_monitor(
                    btc_feed=feed,
                    condition=condition,
                    min_move_pct=0.05,
                    check_interval_sec=0.001,
                )
            except asyncio.CancelledError:
                pass

        assert len(notify_called) == 0

    async def test_updates_reference_price_after_notify(self):
        """After firing, reference price is updated so next move is relative to new base."""
        from main import btc_price_monitor

        condition = asyncio.Condition()
        notify_count = [0]
        original_notify = condition.notify_all

        def track_notify():
            notify_count[0] += 1
            original_notify()

        condition.notify_all = track_notify

        # Feed: 67000 → 67500 (fires, reference → 67500) → 67510 (only 0.015% move from 67500, no fire)
        call_idx = 0
        prices = [67000.0, 67500.0, 67510.0, 67510.0]

        def get_price():
            nonlocal call_idx
            p = prices[min(call_idx, len(prices) - 1)]
            call_idx += 1
            return p

        feed = MagicMock()
        feed.current_price = get_price

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, None, asyncio.CancelledError()]
            try:
                await btc_price_monitor(
                    btc_feed=feed,
                    condition=condition,
                    min_move_pct=0.05,
                    check_interval_sec=0.001,
                )
            except asyncio.CancelledError:
                pass

        # Should have fired exactly once (67000→67500), NOT twice
        assert notify_count[0] == 1

    async def test_handles_none_price_gracefully(self):
        """If feed returns None (stale), monitor does not crash."""
        from main import btc_price_monitor

        condition = asyncio.Condition()
        feed = MagicMock()
        feed.current_price.return_value = None  # stale feed

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, None, asyncio.CancelledError()]
            try:
                await btc_price_monitor(
                    btc_feed=feed,
                    condition=condition,
                    min_move_pct=0.05,
                    check_interval_sec=0.001,
                )
            except asyncio.CancelledError:
                pass
        # Must not raise


class TestWaitForBtcMove:
    """Tests for _wait_for_btc_move() helper used inside trading_loop."""

    async def test_returns_true_when_condition_fires(self):
        """Returns True when condition is notified before timeout."""
        from main import _wait_for_btc_move

        condition = asyncio.Condition()

        async def notify_soon():
            await asyncio.sleep(0.01)
            async with condition:
                condition.notify_all()

        asyncio.create_task(notify_soon())
        result = await _wait_for_btc_move(condition, timeout=1.0)
        assert result is True

    async def test_returns_false_on_timeout(self):
        """Returns False when timeout expires with no notification."""
        from main import _wait_for_btc_move

        condition = asyncio.Condition()
        result = await _wait_for_btc_move(condition, timeout=0.05)
        assert result is False

    async def test_none_condition_uses_sleep(self):
        """When condition is None, falls back to plain asyncio.sleep."""
        from main import _wait_for_btc_move

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await _wait_for_btc_move(None, timeout=0.5)

        mock_sleep.assert_called_once_with(0.5)
        assert result is False  # sleep doesn't signal "triggered"

    async def test_multiple_waiters_all_notified(self):
        """All concurrent waiters on the same condition are notified (notify_all)."""
        from main import _wait_for_btc_move

        condition = asyncio.Condition()
        results = []

        async def waiter():
            r = await _wait_for_btc_move(condition, timeout=1.0)
            results.append(r)

        tasks = [asyncio.create_task(waiter()) for _ in range(3)]
        await asyncio.sleep(0.05)  # let all waiters start

        async with condition:
            condition.notify_all()

        await asyncio.gather(*tasks)
        assert all(r is True for r in results), f"Not all notified: {results}"
