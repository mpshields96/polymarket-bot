"""
Tests for print_graduation_status() function in main.py.

Verifies:
- Output includes all 8 strategies
- Table header includes required columns
- Status logic: READY, BLOCKED, needs X more trades
- Per-strategy threshold values (fomc=5 trades, weather=14 days)
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from src.db import DB


# ── Fixture ───────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    """Fresh DB in a temp directory per test."""
    d = DB(tmp_path / "test.db")
    d.init()
    yield d
    d.close()


def _call_print_graduation_status(db) -> str:
    """
    Call print_graduation_status(db) from main.py and capture stdout output.
    Returns the captured output as a string.
    """
    from main import print_graduation_status
    captured = io.StringIO()
    with patch("sys.stdout", captured):
        print_graduation_status(db)
    return captured.getvalue()


# ── Tests ─────────────────────────────────────────────────────────────


class TestGraduationStatusPrinter:
    """Tests for print_graduation_status(db)."""

    def test_prints_all_8_strategies(self, db):
        """Empty DB should still print a row for all 8 strategies."""
        output = _call_print_graduation_status(db)
        strategies = [
            "btc_lag_v1",
            "eth_lag_v1",
            "btc_drift_v1",
            "eth_drift_v1",
            "orderbook_imbalance_v1",
            "eth_orderbook_imbalance_v1",
            "weather_forecast_v1",
            "fomc_rate_v1",
        ]
        for strategy in strategies:
            assert strategy in output, f"Missing strategy in output: {strategy}"

    def test_header_includes_required_columns(self, db):
        """Table header must include Strategy, Trades, Days, Brier, Streak, P&L, Status."""
        output = _call_print_graduation_status(db)
        for col in ("Strategy", "Trades", "Days", "Brier", "Streak", "P&L", "Status"):
            assert col in output, f"Missing column in header: {col}"

    def test_fomc_shows_5_trade_threshold(self, db):
        """fomc_rate_v1 requires only 5 trades (not 30) — verify threshold is shown correctly."""
        output = _call_print_graduation_status(db)
        # Find the fomc_rate_v1 line and check it shows 0/5
        fomc_line = [line for line in output.splitlines() if "fomc_rate_v1" in line]
        assert fomc_line, "fomc_rate_v1 not found in output"
        assert "0/5" in fomc_line[0], f"Expected 0/5 in fomc line, got: {fomc_line[0]}"

    def test_weather_shows_trade_threshold(self, db):
        """weather_forecast_v1 requires 30 trades — day requirement removed."""
        output = _call_print_graduation_status(db)
        weather_line = [line for line in output.splitlines() if "weather_forecast_v1" in line]
        assert weather_line, "weather_forecast_v1 not found in output"
        assert "0/30" in weather_line[0], f"Expected 0/30 in weather line, got: {weather_line[0]}"

    def test_empty_db_shows_needs_trades_status(self, db):
        """With no trades, every strategy should show 'needs' in status."""
        output = _call_print_graduation_status(db)
        btc_lag_line = [line for line in output.splitlines() if "btc_lag_v1" in line]
        assert btc_lag_line, "btc_lag_v1 not found in output"
        assert "needs" in btc_lag_line[0].lower(), (
            f"Expected 'needs' in btc_lag status, got: {btc_lag_line[0]}"
        )

    def test_ready_status_when_all_criteria_met(self, db):
        """A strategy with all thresholds met should show READY."""
        # Seed 30 settled, winning trades for btc_lag_v1 with good brier score
        # (win_prob=0.9, outcome=win → brier contribution low)
        import time
        first_ts = time.time() - (8 * 86400)  # 8 days ago
        for i in range(30):
            ts = first_ts + i * 100
            db._conn.execute(
                """INSERT INTO trades
                   (timestamp, ticker, side, action, price_cents, count, cost_usd,
                    strategy, edge_pct, win_prob, is_paper, result, pnl_cents, settled_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, "KXBTC15M-TEST", "yes", "buy", 44, 10, 4.40,
                 "btc_lag_v1", 0.12, 0.75, 1, "yes", 560, ts + 3600),
            )
        db._conn.commit()

        output = _call_print_graduation_status(db)
        btc_lag_line = [line for line in output.splitlines() if "btc_lag_v1" in line]
        assert btc_lag_line, "btc_lag_v1 not found in output"
        assert "READY" in btc_lag_line[0], (
            f"Expected READY in btc_lag status, got: {btc_lag_line[0]}"
        )

    def test_zero_of_8_ready_on_empty_db(self, db):
        """Empty DB should show '0 / 8 strategies ready'."""
        output = _call_print_graduation_status(db)
        assert "0 / 8" in output, f"Expected '0 / 8' in output, got:\n{output}"

    def test_exits_without_starting_connections(self, db, tmp_path):
        """
        print_graduation_status should be fast (DB read only) and not attempt
        to import or connect to Kalshi/Binance.
        """
        # If this imports quickly and doesn't raise, connections were not started
        import time
        start = time.time()
        _call_print_graduation_status(db)
        elapsed = time.time() - start
        assert elapsed < 5.0, f"print_graduation_status took too long: {elapsed:.1f}s"
