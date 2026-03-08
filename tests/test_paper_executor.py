"""
Tests for src/execution/paper.py — PaperExecutor slippage model and settlement mapping.

Uses a real in-memory SQLite DB (no mocking) — same pattern as test_db.py.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db import DB
from src.execution.paper import PaperExecutor


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    """Fresh DB in a temp directory per test."""
    d = DB(tmp_path / "test.db")
    d.init()
    yield d
    d.close()


@pytest.fixture
def paper_exec(db):
    """PaperExecutor with default slippage (1 tick)."""
    return PaperExecutor(db=db, strategy_name="btc_lag_v1")


@pytest.fixture
def paper_exec_with_db(db):
    """Alias for settlement tests — PaperExecutor backed by a real DB."""
    return PaperExecutor(db=db, strategy_name="btc_lag_v1")


def _save_paper_trade(db, side="yes", price_cents=44, count=10):
    """Helper: save a paper trade directly to DB and return its trade_id."""
    return db.save_trade(
        ticker="KXBTC15M-TEST",
        side=side,
        action="buy",
        price_cents=price_cents,
        count=count,
        cost_usd=price_cents / 100.0 * count,
        strategy="btc_lag_v1",
        edge_pct=0.12,
        win_prob=0.62,
        is_paper=True,
    )


# ── TestSlippageModel ─────────────────────────────────────────────────


class TestSlippageModel:
    """Test the _apply_slippage static method and its effect on fills."""

    def test_apply_slippage_1_tick(self):
        """1 tick slippage should add 1 cent to fill price."""
        result = PaperExecutor._apply_slippage(44, ticks=1)
        assert result == 45

    def test_apply_slippage_0_ticks_no_change(self):
        """0 ticks slippage returns exact fill price."""
        result = PaperExecutor._apply_slippage(44, ticks=0)
        assert result == 44

    def test_apply_slippage_2_ticks(self):
        """2 ticks slippage adds 2 cents."""
        result = PaperExecutor._apply_slippage(44, ticks=2)
        assert result == 46

    def test_apply_slippage_clamped_to_99(self):
        """Slippage never pushes fill price above 99."""
        result = PaperExecutor._apply_slippage(99, ticks=5)
        assert result == 99

    def test_apply_slippage_near_99_clamped(self):
        """98 + 5 ticks = 99, not 103."""
        result = PaperExecutor._apply_slippage(98, ticks=5)
        assert result == 99

    def test_default_slippage_ticks_is_1(self):
        """PaperExecutor defaults to slippage_ticks=1 if not specified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            d = DB(Path(tmpdir) / "test.db")
            d.init()
            pe = PaperExecutor(db=d, strategy_name="btc_lag_v1")
            assert pe._slippage_ticks == 1
            d.close()

    def test_yes_execute_applies_slippage(self, paper_exec):
        """YES fill should result in fill_price 1 tick above the raw price."""
        result = paper_exec.execute(
            ticker="KXBTC15M-TEST",
            side="yes",
            price_cents=44,
            size_usd=4.40,
            reason="test signal",
        )
        assert result is not None
        # With 1-tick slippage, fill should be 45 (44 + 1)
        assert result["fill_price_cents"] == 45

    def test_no_execute_applies_slippage(self, paper_exec):
        """NO fill should result in fill_price 1 tick above the raw price."""
        result = paper_exec.execute(
            ticker="KXBTC15M-TEST",
            side="no",
            price_cents=56,
            size_usd=5.60,
            reason="test signal",
        )
        assert result is not None
        # With 1-tick slippage, fill should be 57 (56 + 1)
        assert result["fill_price_cents"] == 57

    def test_zero_slippage_gives_exact_fill(self, db):
        """slippage_ticks=0 gives exact fill with no adjustment."""
        pe = PaperExecutor(db=db, strategy_name="btc_lag_v1", slippage_ticks=0)
        result = pe.execute(
            ticker="KXBTC15M-TEST",
            side="yes",
            price_cents=44,
            size_usd=4.40,
            reason="test",
        )
        assert result is not None
        assert result["fill_price_cents"] == 44

    def test_slippage_higher_cost_lower_payout(self, db):
        """Higher fill price from slippage means higher fill_price_cents."""
        pe_no_slip = PaperExecutor(db=db, strategy_name="btc_lag_v1", slippage_ticks=0)
        pe_with_slip = PaperExecutor(db=db, strategy_name="btc_lag_v1", slippage_ticks=1)

        result_no_slip = pe_no_slip.execute(
            ticker="KXBTC15M-001",
            side="yes",
            price_cents=44,
            size_usd=5.00,
            reason="test",
        )
        result_with_slip = pe_with_slip.execute(
            ticker="KXBTC15M-002",
            side="yes",
            price_cents=44,
            size_usd=5.00,
            reason="test",
        )
        assert result_no_slip is not None and result_with_slip is not None
        assert result_with_slip["fill_price_cents"] > result_no_slip["fill_price_cents"]


# ── TestSettlementResultMapping ───────────────────────────────────────


class TestSettlementResultMapping:
    """Verify YES/NO win/loss settlement logic is correct."""

    def test_result_yes_side_yes_is_win(self, paper_exec_with_db, db):
        """Bet YES, market settles YES -> WIN (positive P&L)."""
        trade_id = _save_paper_trade(db, side="yes", price_cents=44, count=10)
        pnl = paper_exec_with_db.settle(
            trade_id=trade_id,
            result="yes",
            fill_price_cents=44,
            side="yes",
            count=10,
        )
        assert pnl > 0

    def test_result_no_side_yes_is_loss(self, paper_exec_with_db, db):
        """Bet YES, market settles NO -> LOSS (negative P&L)."""
        trade_id = _save_paper_trade(db, side="yes", price_cents=44, count=10)
        pnl = paper_exec_with_db.settle(
            trade_id=trade_id,
            result="no",
            fill_price_cents=44,
            side="yes",
            count=10,
        )
        assert pnl < 0

    def test_result_no_side_no_is_win(self, paper_exec_with_db, db):
        """Bet NO, market settles NO -> WIN (positive P&L)."""
        trade_id = _save_paper_trade(db, side="no", price_cents=55, count=10)
        pnl = paper_exec_with_db.settle(
            trade_id=trade_id,
            result="no",
            fill_price_cents=55,
            side="no",
            count=10,
        )
        assert pnl > 0

    def test_result_yes_side_no_is_loss(self, paper_exec_with_db, db):
        """Bet NO, market settles YES -> LOSS (negative P&L)."""
        trade_id = _save_paper_trade(db, side="no", price_cents=55, count=10)
        pnl = paper_exec_with_db.settle(
            trade_id=trade_id,
            result="yes",
            fill_price_cents=55,
            side="no",
            count=10,
        )
        assert pnl < 0


# ── TestFillProbability ────────────────────────────────────────────────


class TestFillProbability:
    """Test that fill_probability controls whether a paper trade executes."""

    def test_fill_probability_1_0_always_fills(self, db):
        """fill_probability=1.0 means every execute() call returns a trade."""
        pe = PaperExecutor(db=db, strategy_name="test", fill_probability=1.0)
        for _ in range(5):
            result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
            assert result is not None

    def test_fill_probability_0_0_never_fills(self, db):
        """fill_probability=0.0 means every execute() call returns None."""
        pe = PaperExecutor(db=db, strategy_name="test", fill_probability=0.0)
        for _ in range(5):
            result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
            assert result is None

    def test_fill_probability_default_is_1_0(self, db):
        """Default fill_probability is 1.0 — backward compatible."""
        pe = PaperExecutor(db=db, strategy_name="test")
        assert pe._fill_probability == 1.0

    def test_fill_probability_no_fill_when_random_above_threshold(self, db):
        """When random() >= fill_probability, no fill — returns None."""
        pe = PaperExecutor(db=db, strategy_name="test", fill_probability=0.7)
        with patch("src.execution.paper.random.random", return_value=0.8):
            result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
            assert result is None

    def test_fill_probability_fills_when_random_below_threshold(self, db):
        """When random() < fill_probability, trade fills — returns trade dict."""
        pe = PaperExecutor(db=db, strategy_name="test", fill_probability=0.7)
        with patch("src.execution.paper.random.random", return_value=0.5):
            result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
            assert result is not None

    def test_no_fill_does_not_write_to_db(self, db):
        """A no-fill does not create a trade record in the DB."""
        pe = PaperExecutor(db=db, strategy_name="test", fill_probability=0.0)
        pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
        trades = db.get_trades(is_paper=True)
        assert len(trades) == 0


# ── TestSignalPriceCents ───────────────────────────────────────────────


class TestSignalPriceCents:
    """Test that signal_price_cents (pre-slippage) is stored alongside fill_price_cents."""

    def test_signal_price_stored_before_slippage(self, db):
        """execute() returns signal_price_cents equal to original price_cents."""
        pe = PaperExecutor(db=db, strategy_name="test", slippage_ticks=3)
        result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
        assert result is not None
        assert result["signal_price_cents"] == 50   # original price
        assert result["fill_price_cents"] == 53     # 50 + 3 slippage

    def test_signal_price_differs_from_fill_price_with_slippage(self, db):
        """With non-zero slippage, signal_price_cents < fill_price_cents."""
        pe = PaperExecutor(db=db, strategy_name="test", slippage_ticks=2)
        result = pe.execute("KXBTC15M-TEST", "no", 45, 5.0)
        assert result is not None
        assert result["signal_price_cents"] == 45
        assert result["fill_price_cents"] == 47

    def test_signal_price_equals_fill_price_with_zero_slippage(self, db):
        """With slippage_ticks=0, signal_price_cents == fill_price_cents."""
        pe = PaperExecutor(db=db, strategy_name="test", slippage_ticks=0)
        result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
        assert result is not None
        assert result["signal_price_cents"] == 50
        assert result["fill_price_cents"] == 50

    def test_signal_price_cents_persisted_in_db(self, db):
        """signal_price_cents is stored in the trades table."""
        pe = PaperExecutor(db=db, strategy_name="test", slippage_ticks=2)
        result = pe.execute("KXBTC15M-TEST", "yes", 50, 5.0)
        assert result is not None
        cursor = db._conn.execute(
            "SELECT signal_price_cents, price_cents FROM trades WHERE id = ?",
            (result["trade_id"],),
        )
        row = cursor.fetchone()
        assert row[0] == 50   # signal_price_cents
        assert row[1] == 52   # fill price_cents (50 + 2 slippage)
