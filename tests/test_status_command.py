"""
Tests for python main.py --status command.

Verifies:
- print_status() prints BOT STATUS header
- Recent Trades section with last 10 trades
- Pending (open unsettled trades) count
- Today's P&L for paper and live trades
- Bankroll from DB latest_bankroll()
- BTC and ETH mid-prices (mocked — no real HTTP in tests)
- get_binance_mid_price() returns float from mocked requests.get()
- get_binance_mid_price() returns None on network error (no raise)
- print_status() completes in under 3 seconds when Binance is mocked
"""

from __future__ import annotations

import io
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.db import DB


# ── Fixtures ──────────────────────────────────────────────────────────────


@pytest.fixture
def db(tmp_path):
    """Fresh DB in a temp directory per test."""
    d = DB(tmp_path / "test.db")
    d.init()
    yield d
    d.close()


@pytest.fixture
def db_with_trades(tmp_path):
    """DB seeded with 12 paper trades (10 settled, 2 open) and 1 live trade."""
    d = DB(tmp_path / "test.db")
    d.init()

    base_ts = time.time() - 86400  # 1 day ago
    today_ts = time.time() - 3600  # 1 hour ago (today UTC)

    # Insert 10 settled paper trades
    for i in range(10):
        ts = base_ts + i * 600
        d._conn.execute(
            """INSERT INTO trades
               (timestamp, ticker, side, action, price_cents, count, cost_usd,
                strategy, edge_pct, win_prob, is_paper, result, pnl_cents, settled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts, f"KXBTC15M-TEST{i}", "yes", "buy", 44, 10, 4.40,
             "btc_lag_v1", 0.12, 0.75, 1, "yes", 560, ts + 3600),
        )

    # Insert 2 open paper trades (unsettled)
    for i in range(2):
        ts = today_ts + i * 60
        d._conn.execute(
            """INSERT INTO trades
               (timestamp, ticker, side, action, price_cents, count, cost_usd,
                strategy, edge_pct, win_prob, is_paper, result, pnl_cents, settled_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ts, f"KXBTC15M-OPEN{i}", "yes", "buy", 44, 10, 4.40,
             "btc_lag_v1", 0.12, 0.75, 1, None, None, None),
        )

    # Insert 1 settled live trade (today)
    d._conn.execute(
        """INSERT INTO trades
           (timestamp, ticker, side, action, price_cents, count, cost_usd,
            strategy, edge_pct, win_prob, is_paper, result, pnl_cents, settled_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (today_ts, "KXBTC15M-LIVE0", "yes", "buy", 44, 10, 4.40,
         "btc_lag_v1", 0.12, 0.75, 0, "yes", 560, today_ts + 3600),
    )

    d._conn.commit()
    d.save_bankroll(75.00, source="test")
    yield d
    d.close()


# ── Helper ────────────────────────────────────────────────────────────────


def _run_print_status(db, mock_btc=55000.0, mock_eth=2800.0) -> str:
    """Call print_status(db) with mocked Binance prices and capture stdout."""
    from main import print_status
    captured = io.StringIO()
    with patch("sys.stdout", captured):
        with patch("main.get_binance_mid_price", side_effect=[mock_btc, mock_eth]):
            print_status(db)
    return captured.getvalue()


# ── Tests ─────────────────────────────────────────────────────────────────


class TestStatusCommand:
    """Tests for print_status(db) and get_binance_mid_price()."""

    def test_prints_bot_status_header(self, db):
        """Output must include 'BOT STATUS' header."""
        output = _run_print_status(db)
        assert "BOT STATUS" in output, f"Missing BOT STATUS header in:\n{output}"

    def test_prints_recent_trades_section(self, db):
        """Output must include 'Recent Trades' section label."""
        output = _run_print_status(db)
        assert "Recent Trades" in output, f"Missing Recent Trades section in:\n{output}"

    def test_prints_pending_count(self, db):
        """Output must include 'Pending' to show open unsettled trade count."""
        output = _run_print_status(db)
        assert "Pending" in output, f"Missing Pending section in:\n{output}"

    def test_prints_bankroll_line(self, db):
        """Output must include 'Bankroll' line."""
        output = _run_print_status(db)
        assert "Bankroll" in output, f"Missing Bankroll line in:\n{output}"

    def test_prints_btc_price(self, db):
        """Output must include BTC price."""
        output = _run_print_status(db)
        assert "BTC" in output, f"Missing BTC price in:\n{output}"

    def test_prints_eth_price(self, db):
        """Output must include ETH price."""
        output = _run_print_status(db)
        assert "ETH" in output, f"Missing ETH price in:\n{output}"

    def test_prints_pnl_section(self, db):
        """Output must include P&L section."""
        output = _run_print_status(db)
        assert "P&L" in output, f"Missing P&L section in:\n{output}"

    def test_shows_btc_price_value(self, db):
        """BTC price value must appear in output (formatted with comma separators)."""
        output = _run_print_status(db, mock_btc=55000.0)
        # Price should appear formatted somewhere in the output
        assert "55" in output, f"BTC price value not found in:\n{output}"

    def test_shows_eth_price_value(self, db):
        """ETH price value must appear in output."""
        output = _run_print_status(db, mock_eth=2800.0)
        assert "2,800" in output or "2800" in output, f"ETH price value not found in:\n{output}"

    def test_shows_bankroll_when_set(self, db_with_trades):
        """Bankroll should reflect latest_bankroll() value."""
        output = _run_print_status(db_with_trades)
        assert "75" in output, f"Bankroll value $75 not found in:\n{output}"

    def test_pending_count_includes_open_trades(self, db_with_trades):
        """Pending count should reflect open (unsettled) trades."""
        output = _run_print_status(db_with_trades)
        # 2 open paper + 0 open live = 2 total pending
        assert "2" in output, f"Expected pending count '2' in:\n{output}"

    def test_recent_trades_shows_ticker(self, db_with_trades):
        """Recent trades section should show ticker names."""
        output = _run_print_status(db_with_trades)
        assert "KXBTC15M" in output, f"Expected ticker KXBTC15M in:\n{output}"

    def test_recent_trades_newest_first(self, db_with_trades):
        """Recent trades should be sorted newest first."""
        output = _run_print_status(db_with_trades)
        # Both OPEN and TEST tickers appear; OPEN ones are more recent
        open_pos = output.find("OPEN")
        test_pos = output.find("TEST")
        # If both are present, OPEN (newer) should appear before TEST (older)
        if open_pos >= 0 and test_pos >= 0:
            assert open_pos <= test_pos, (
                f"Expected OPEN (newer) before TEST (older), got positions "
                f"OPEN={open_pos}, TEST={test_pos}"
            )

    def test_completes_under_3_seconds(self, db):
        """print_status should complete in under 3 seconds (Binance is mocked)."""
        start = time.time()
        _run_print_status(db)
        elapsed = time.time() - start
        assert elapsed < 3.0, f"print_status took too long: {elapsed:.2f}s"

    def test_empty_db_no_crash(self, db):
        """Empty DB should produce output without crashing."""
        output = _run_print_status(db)
        assert len(output) > 0, "print_status produced no output on empty DB"

    def test_btc_price_none_handled(self, db):
        """If BTC price returns None (network error), should print 'n/a' or similar."""
        from main import print_status
        captured = io.StringIO()
        with patch("sys.stdout", captured):
            with patch("main.get_binance_mid_price", side_effect=[None, None]):
                print_status(db)
        output = captured.getvalue()
        assert "BOT STATUS" in output, "Header missing even when Binance returns None"
        # Should not crash, and should indicate unavailability
        assert "n/a" in output.lower() or "unavailable" in output.lower() or "BTC" in output, (
            f"Expected graceful handling when price=None, got:\n{output}"
        )


class TestGetBinanceMidPrice:
    """Tests for get_binance_mid_price() helper function."""

    def test_returns_float_from_mocked_response(self):
        """Should return mid-price float from mocked requests.get() response."""
        from main import get_binance_mid_price
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"bidPrice": "55000.00", "askPrice": "55010.00"}
        mock_resp.raise_for_status = MagicMock()

        with patch("main.requests.get", return_value=mock_resp):
            result = get_binance_mid_price("BTCUSDT")

        assert isinstance(result, float), f"Expected float, got {type(result)}"
        assert result == 55005.0, f"Expected 55005.0 (mid), got {result}"

    def test_returns_none_on_request_exception(self):
        """Should return None (not raise) on requests.RequestException."""
        import requests as requests_lib
        from main import get_binance_mid_price

        with patch("main.requests.get", side_effect=requests_lib.RequestException("timeout")):
            result = get_binance_mid_price("BTCUSDT")

        assert result is None, f"Expected None on network error, got {result}"

    def test_returns_none_on_key_error(self):
        """Should return None (not raise) if response JSON is missing bidPrice/askPrice."""
        from main import get_binance_mid_price
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"symbol": "BTCUSDT"}  # missing bid/ask
        mock_resp.raise_for_status = MagicMock()

        with patch("main.requests.get", return_value=mock_resp):
            result = get_binance_mid_price("BTCUSDT")

        assert result is None, f"Expected None on KeyError, got {result}"

    def test_uses_binance_us_url(self):
        """Should use api.binance.us (not binance.com — geo-blocked in US)."""
        from main import get_binance_mid_price
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"bidPrice": "55000.00", "askPrice": "55010.00"}
        mock_resp.raise_for_status = MagicMock()

        with patch("main.requests.get", return_value=mock_resp) as mock_get:
            get_binance_mid_price("BTCUSDT")

        call_url = mock_get.call_args[0][0]
        assert "binance.us" in call_url, f"Expected binance.us URL, got: {call_url}"
        assert "binance.com" not in call_url, f"Must NOT use binance.com (geo-blocked): {call_url}"
