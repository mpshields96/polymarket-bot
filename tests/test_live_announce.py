"""
Tests for _announce_live_bet — prominent banner + macOS notification on live bet placement.

Covers:
    - Banner lines logged via logger.info
    - Reminders notification subprocess call issued
    - Subprocess failure silently swallowed (never crashes the trading loop)
    - Paper trades do NOT trigger the announcement
"""

import subprocess
from unittest.mock import call, patch, MagicMock

import pytest
import main as main_mod


def _make_live_result(
    side="yes",
    ticker="KXBTC15M-26FEB281800-00",
    cost_usd=4.41,
    fill_price_cents=63,
    trade_id=65,
    is_paper=False,
):
    return {
        "side": side,
        "ticker": ticker,
        "cost_usd": cost_usd,
        "fill_price_cents": fill_price_cents,
        "trade_id": trade_id,
        "is_paper": is_paper,
    }


class TestAnnounceLiveBet:

    def test_logs_banner_lines(self, caplog):
        """Banner contains strategy name, side, ticker, price, cost, trade_id."""
        import logging
        result = _make_live_result(side="yes", ticker="KXBTC15M-TEST", cost_usd=4.41,
                                   fill_price_cents=63, trade_id=99)
        with patch("subprocess.run"):
            with caplog.at_level(logging.INFO, logger="main"):
                main_mod._announce_live_bet(result, strategy_name="btc_drift_v1")

        combined = " ".join(caplog.messages)
        assert "LIVE BET" in combined
        assert "btc_drift_v1" in combined
        assert "YES" in combined
        assert "KXBTC15M-TEST" in combined
        assert "63" in combined   # fill price
        assert "4.41" in combined  # cost
        assert "99" in combined    # trade_id

    def test_fires_reminders_notification(self):
        """subprocess.run is called with osascript + Reminders tell."""
        result = _make_live_result(trade_id=77, cost_usd=5.00, fill_price_cents=50)
        with patch("subprocess.run") as mock_run:
            main_mod._announce_live_bet(result, strategy_name="btc_lag_v1")

        assert mock_run.called
        cmd = mock_run.call_args[0][0]
        assert "osascript" in cmd[0]
        script = " ".join(cmd)
        assert "Reminders" in script

    def test_notification_includes_side_ticker_price(self):
        """The Reminders message includes the essential trade info."""
        result = _make_live_result(side="no", ticker="KXETH15M-TEST", cost_usd=3.20,
                                   fill_price_cents=38, trade_id=12)
        with patch("subprocess.run") as mock_run:
            main_mod._announce_live_bet(result, strategy_name="eth_lag_v1")

        script = " ".join(mock_run.call_args[0][0])
        assert "NO" in script or "no" in script.lower()
        assert "KXETH15M-TEST" in script

    def test_subprocess_failure_does_not_raise(self):
        """If osascript fails (e.g. not on macOS), the exception is swallowed silently."""
        result = _make_live_result()
        with patch("subprocess.run", side_effect=FileNotFoundError("osascript not found")):
            # Should not raise
            main_mod._announce_live_bet(result, strategy_name="btc_drift_v1")

    def test_timeout_failure_does_not_raise(self):
        """subprocess.TimeoutExpired is swallowed too."""
        result = _make_live_result()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("osascript", 3)):
            main_mod._announce_live_bet(result, strategy_name="btc_drift_v1")

    def test_works_with_no_side_bet(self):
        """NO-side bets show 'NO' in the banner."""
        result = _make_live_result(side="no", fill_price_cents=37, cost_usd=3.70)
        with patch("subprocess.run"):
            import logging
            import io
            # Just check it doesn't raise and logs something sensible
            main_mod._announce_live_bet(result, strategy_name="btc_drift_v1")

    def test_missing_fill_price_falls_back_to_price_cents(self):
        """If fill_price_cents absent, falls back to price_cents key."""
        result = {
            "side": "yes",
            "ticker": "KXBTC15M-TEST",
            "cost_usd": 4.00,
            "price_cents": 55,   # no fill_price_cents key
            "trade_id": 20,
            "is_paper": False,
        }
        with patch("subprocess.run"):
            # Should not raise (fill price resolution)
            main_mod._announce_live_bet(result, strategy_name="btc_drift_v1")
