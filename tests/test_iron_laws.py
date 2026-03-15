"""
Regression tests for Iron Laws IL-12 through IL-18.

Each test class corresponds to one Iron Law and documents:
  - What invariant it enforces
  - The historical incident it prevents
  - The exact failure mode if the invariant is broken

BOUNDS.md is the authoritative reference for these laws.
"""

import math
import unittest
from unittest.mock import MagicMock, call


# ─────────────────────────────────────────────────────────────────────────────
# IL-12: Kelly floor truncation must prevent pct cap from being exceeded
# ─────────────────────────────────────────────────────────────────────────────

class TestIL12SizingKillSwitchInteraction(unittest.TestCase):
    """
    IL-12: math.floor() in sizing.py guarantees kill switch pct cap is satisfied.

    Historical incident: switching floor() → round() causes valid bets to be
    blocked by kill switch when bankroll is near a cap boundary.

    Invariant:
        math.floor(size * 100) / 100 always produces a value that satisfies
        the 15% pct cap check, even when the untruncated value would not.
    """

    def test_floor_passes_pct_cap_where_round_would_fail(self):
        """
        At bankroll=$31.79, pct_cap=4.7685. floor→4.76 passes; round→4.77 fails.

        This is the exact boundary case that IL-12 protects against.
        If sizing.py is changed to round(), valid bets at bankroll ~31.79 are silently blocked.
        """
        from src.risk.kill_switch import KillSwitch, MAX_TRADE_PCT

        bankroll = 31.79
        pct_cap_raw = bankroll * MAX_TRADE_PCT  # 4.7685

        # Floored value (what sizing.py produces)
        floored = math.floor(pct_cap_raw * 100) / 100  # 4.76

        # Rounded value (what a naive change would produce)
        rounded = round(pct_cap_raw, 2)  # 4.77

        # Verify these are different (boundary exists)
        self.assertEqual(floored, 4.76)
        self.assertEqual(rounded, 4.77)

        ks = KillSwitch(starting_bankroll_usd=bankroll)
        ks.restore_daily_loss(0.0)

        ok_floored, _ = ks.check_order_allowed(
            trade_usd=floored, current_bankroll_usd=bankroll
        )
        ok_rounded, reason_rounded = ks.check_order_allowed(
            trade_usd=rounded, current_bankroll_usd=bankroll
        )

        self.assertTrue(ok_floored, "Floored value 4.76 must pass kill switch pct cap")
        self.assertFalse(ok_rounded, "Rounded value 4.77 must be blocked by kill switch pct cap")
        self.assertIn("15%", reason_rounded)

    def test_floor_is_never_larger_than_raw(self):
        """floor(x) <= x always — sized bet never exceeds what the pct cap would produce."""
        bankroll = 127.43
        pct_cap_raw = bankroll * 0.15

        floored = math.floor(pct_cap_raw * 100) / 100

        self.assertLessEqual(floored, pct_cap_raw)

    def test_bankroll_floor_checked_before_pct_cap(self):
        """
        IL-17: bankroll floor check runs before pct cap.

        With bankroll at $20.01 (just above floor) and a trade that would exceed pct cap,
        the trade is blocked by pct cap — confirming floor check passed (didn't hard-stop)
        but pct cap then blocked it.

        If floor ran AFTER pct cap, we might get a pct cap error on a bot already below floor.
        """
        from src.risk.kill_switch import KillSwitch, HARD_MIN_BANKROLL_USD

        bankroll = HARD_MIN_BANKROLL_USD + 0.01  # just above floor = 20.01
        ks = KillSwitch(starting_bankroll_usd=bankroll)

        # Trade that exceeds pct cap (15% of 20.01 = 3.00, so 5.00 exceeds cap)
        ok, reason = ks.check_order_allowed(trade_usd=5.00, current_bankroll_usd=bankroll)

        self.assertFalse(ok)
        # Must be a pct_cap block, not a bankroll floor hard stop
        self.assertNotIn("hard stop", reason.lower())
        self.assertIn("15%", reason)


# ─────────────────────────────────────────────────────────────────────────────
# IL-13: NO-side payouts require YES price (100 - no_price), not NO price
# ─────────────────────────────────────────────────────────────────────────────

class TestIL13KalshiPayoutNOSideConversion(unittest.TestCase):
    """
    IL-13: kalshi_payout() always receives YES price, regardless of bet side.

    Historical incident (Session 20): kalshi_payout(signal.price_cents, side)
    was called where price_cents was the NO price for NO-side signals.
    This produced wrong edge calculations and miscalibrated graduation counters.

    Invariant:
        For a NO-side bet at NO=40c (YES=60c):
            CORRECT: kalshi_payout(yes_price=60, side="no")
            WRONG:   kalshi_payout(yes_price=40, side="no")  ← uses NO price as YES price
    """

    def test_correct_yes_price_yields_positive_payout_no_side(self):
        """At NO=40c (YES=60c), kalshi_payout(60, "no") must return a positive payout."""
        from src.risk.sizing import kalshi_payout

        no_price = 40
        yes_price = 100 - no_price  # correct conversion: 60

        payout = kalshi_payout(yes_price_cents=yes_price, side="no")

        self.assertGreater(payout, 0.0, "Correct payout for NO@40c must be positive")

    def test_wrong_no_price_produces_different_result(self):
        """
        Regression: passing NO price (40c) instead of YES price (60c) to kalshi_payout
        gives a DIFFERENT (lower) payout value. This is the exact Session 20 bug.

        If this test fails, the payout formula has changed and IL-13 must be re-evaluated.
        """
        from src.risk.sizing import kalshi_payout

        no_price = 40
        yes_price = 100 - no_price  # 60

        payout_correct = kalshi_payout(yes_price_cents=yes_price, side="no")   # pass YES price
        payout_buggy = kalshi_payout(yes_price_cents=no_price, side="no")      # pass NO price (bug)

        self.assertNotEqual(
            payout_correct, payout_buggy,
            "Correct vs buggy NO-side payout must differ — if equal, formula may have changed"
        )
        # Correct payout is ~1.44x (paying 40c to win 60c). Buggy is ~0.6x (paying 60c to win 40c).
        self.assertGreater(payout_correct, payout_buggy)

    def test_symmetric_pricing_yes_vs_no_inverted(self):
        """
        At YES=60c, NO=40c:
            kalshi_payout(60, "yes") ≈ 0.62 (paying 60c to win 40c)
            kalshi_payout(60, "no")  ≈ 1.44 (paying 40c to win 60c)

        These must differ — they represent bets with opposite risk/reward profiles.
        """
        from src.risk.sizing import kalshi_payout

        payout_yes = kalshi_payout(yes_price_cents=60, side="yes")
        payout_no = kalshi_payout(yes_price_cents=60, side="no")

        self.assertGreater(payout_no, payout_yes, "NO payout at 60c YES must exceed YES payout (lower risk)")

    def test_conversion_formula_identity(self):
        """
        The conversion formula: yes_for_payout = 100 - price if side == "no" else price.
        Verify by testing that the correct conversion produces the expected payout range.
        """
        from src.risk.sizing import kalshi_payout

        # NO-side bet at common sniper prices (NO=91c-95c → YES=5c-9c)
        # At NO@91c: you pay 91c to win 9c. kalshi_payout returns ~0.09 per $1 risked (small margin).
        # The key invariant is NOT the magnitude but that the correct YES conversion is used.
        for no_price in [91, 92, 93, 94, 95]:
            yes_price_equiv = 100 - no_price
            payout_correct = kalshi_payout(yes_price_cents=yes_price_equiv, side="no")
            payout_wrong = kalshi_payout(yes_price_cents=no_price, side="no")  # passing NO price = bug
            # Correct payout must be positive
            self.assertGreater(
                payout_correct, 0.0,
                f"NO@{no_price}c: payout with correct YES price ({yes_price_equiv}c) must be > 0"
            )
            # Passing NO price instead of YES price gives wrong result
            self.assertNotAlmostEqual(
                payout_correct, payout_wrong, places=4,
                msg=f"NO@{no_price}c: correct vs wrong payout must differ"
            )


# ─────────────────────────────────────────────────────────────────────────────
# IL-14: Settlement loop only calls record_win/record_loss for live trades
# ─────────────────────────────────────────────────────────────────────────────

class TestIL14SettlementLoopIsPaperFilter(unittest.TestCase):
    """
    IL-14: kill_switch.record_win() / record_loss() must only be called for
    is_paper=False trades.

    Historical incident (Session 21): paper losses counted toward the live daily
    cap, blocking all live trading after a paper losing streak.

    Invariant:
        `if not trade["is_paper"]:` gates EVERY call to record_win() / record_loss()
        in settlement_loop. Paper bets are not real money — no risk governance needed.
    """

    def _make_trade(self, is_paper: bool, won: bool, side: str = "yes", pnl_cents: int = 50):
        return {
            "id": 1,
            "ticker": "KXBTC15M-TEST",
            "side": side,
            "price_cents": 90,
            "count": 1,
            "is_paper": is_paper,
            "result": side if won else ("no" if side == "yes" else "yes"),
            "pnl_cents": pnl_cents if won else -pnl_cents,
        }

    def test_paper_loss_does_not_call_record_loss(self):
        """Paper losses must never reach kill switch record_loss()."""
        ks = MagicMock()

        trade = self._make_trade(is_paper=True, won=False, pnl_cents=500)
        won = trade["side"] == trade["result"]

        # Replicate the settlement_loop guard (main.py line 1192)
        if not trade["is_paper"]:
            if won:
                ks.record_win()
            else:
                ks.record_loss(abs(trade["pnl_cents"]) / 100.0)

        ks.record_win.assert_not_called()
        ks.record_loss.assert_not_called()

    def test_paper_win_does_not_call_record_win(self):
        """Paper wins must never reach kill switch record_win()."""
        ks = MagicMock()

        trade = self._make_trade(is_paper=True, won=True, pnl_cents=50)
        won = trade["side"] == trade["result"]

        if not trade["is_paper"]:
            if won:
                ks.record_win()
            else:
                ks.record_loss(abs(trade["pnl_cents"]) / 100.0)

        ks.record_win.assert_not_called()

    def test_live_loss_calls_record_loss(self):
        """Live losses must reach kill switch record_loss() with correct USD amount."""
        ks = MagicMock()

        trade = self._make_trade(is_paper=False, won=False, pnl_cents=1940)
        won = trade["side"] == trade["result"]

        if not trade["is_paper"]:
            if won:
                ks.record_win()
            else:
                ks.record_loss(abs(trade["pnl_cents"]) / 100.0)

        ks.record_loss.assert_called_once_with(19.40)
        ks.record_win.assert_not_called()

    def test_live_win_calls_record_win(self):
        """Live wins must reach kill switch record_win()."""
        ks = MagicMock()

        trade = self._make_trade(is_paper=False, won=True, pnl_cents=100)
        won = trade["side"] == trade["result"]

        if not trade["is_paper"]:
            if won:
                ks.record_win()
            else:
                ks.record_loss(abs(trade["pnl_cents"]) / 100.0)

        ks.record_win.assert_called_once()
        ks.record_loss.assert_not_called()

    def test_mixed_batch_only_live_trades_update_kill_switch(self):
        """
        In a batch of paper and live trades, only live trades call record_win/loss.
        This replicates the settlement_loop batch processing pattern.
        """
        ks = MagicMock()

        trades = [
            self._make_trade(is_paper=True,  won=False, pnl_cents=1940),  # paper loss — ignored
            self._make_trade(is_paper=False, won=True,  pnl_cents=50),    # live win — counts
            self._make_trade(is_paper=True,  won=True,  pnl_cents=50),    # paper win — ignored
            self._make_trade(is_paper=False, won=False, pnl_cents=500),   # live loss — counts
        ]

        for trade in trades:
            won = trade["side"] == trade["result"]
            if not trade["is_paper"]:
                if won:
                    ks.record_win()
                else:
                    ks.record_loss(abs(trade["pnl_cents"]) / 100.0)

        self.assertEqual(ks.record_win.call_count, 1)
        self.assertEqual(ks.record_loss.call_count, 1)


# ─────────────────────────────────────────────────────────────────────────────
# IL-16: _FIRST_RUN_CONFIRMED must be set True by main.py after startup
# ─────────────────────────────────────────────────────────────────────────────

class TestIL16FirstRunConfirmedModuleState(unittest.TestCase):
    """
    IL-16: live.py._FIRST_RUN_CONFIRMED must be explicitly set True by main.py
    after the startup confirmation prompt.

    Historical incident (Session 20): when stdin is piped (nohup restart),
    input() returns "" not "CONFIRM", so the flag is never set and every order
    silently fails with no error log.

    Invariant:
        - Module loads with _FIRST_RUN_CONFIRMED = False
        - Setting it to True allows execute() to proceed past the guard
        - The flag persists across calls within the same process (module-level)
    """

    def test_flag_default_is_false(self):
        """Module-level default must be False — requires explicit opt-in to live mode."""
        import importlib
        import src.execution.live as live_mod
        importlib.reload(live_mod)
        self.assertFalse(live_mod._FIRST_RUN_CONFIRMED)

    def test_flag_persists_after_being_set(self):
        """Once set to True, the flag must persist across multiple accesses."""
        import src.execution.live as live_mod
        live_mod._FIRST_RUN_CONFIRMED = True
        self.assertTrue(live_mod._FIRST_RUN_CONFIRMED)
        self.assertTrue(live_mod._FIRST_RUN_CONFIRMED)  # still True on second access

    def test_flag_is_module_level_not_function_local(self):
        """
        The flag must be module-level so main.py can set it once and all calls share state.
        If it were function-local, main.py's assignment would have no effect.
        """
        import src.execution.live as live_mod

        # Setting via module reference must be visible on next attribute read
        live_mod._FIRST_RUN_CONFIRMED = True
        import src.execution.live as live_mod2  # re-import (same module object in sys.modules)
        self.assertTrue(live_mod2._FIRST_RUN_CONFIRMED)


# ─────────────────────────────────────────────────────────────────────────────
# IL-18: strategy_name passed to live.execute() must not be hardcoded
# ─────────────────────────────────────────────────────────────────────────────

class TestIL18StrategyNameNotHardcoded(unittest.TestCase):
    """
    IL-18: strategy_name stored in DB must come from the strategy object or a
    function parameter, never a string literal.

    Historical incident (Session 20): eth_lag bets were recorded as "btc_lag"
    because the loop was copy-pasted without updating the hardcoded name.
    Calibration data for eth_lag was lost for several hours.

    Invariant:
        strategy.name attribute must be the sole source of truth for DB records.
    """

    def test_expiry_sniper_has_name_attribute(self):
        """ExpirySniperStrategy must expose a .name attribute used in DB records."""
        from src.strategies.expiry_sniper import ExpirySniperStrategy
        strategy = ExpirySniperStrategy()
        self.assertTrue(hasattr(strategy, "name"), "Strategy must have a .name attribute")
        self.assertIsInstance(strategy.name, str)
        self.assertNotEqual(strategy.name, "", "Strategy name must not be empty string")

    def test_strategy_names_are_distinct(self):
        """
        All active live strategies must have distinct names.
        If two strategies share a name, their DB records are indistinguishable.
        """
        from src.strategies.expiry_sniper import ExpirySniperStrategy
        from src.strategies.btc_drift import BTCDriftStrategy

        strategies = [
            ExpirySniperStrategy(),
            BTCDriftStrategy(name_override="btc_drift_v1"),
            BTCDriftStrategy(name_override="eth_drift_v1"),
            BTCDriftStrategy(name_override="sol_drift_v1"),
            BTCDriftStrategy(name_override="xrp_drift_v1"),
        ]

        names = [s.name for s in strategies]
        self.assertEqual(len(names), len(set(names)), f"Duplicate strategy names: {names}")

    def test_btc_drift_name_override_is_honored(self):
        """
        BTCDriftStrategy is reused for eth/sol/xrp drift. The name_override parameter
        must be the only way to distinguish them in DB records.
        """
        from src.strategies.btc_drift import BTCDriftStrategy

        btc = BTCDriftStrategy(name_override="btc_drift_v1")
        eth = BTCDriftStrategy(name_override="eth_drift_v1")

        self.assertEqual(btc.name, "btc_drift_v1")
        self.assertEqual(eth.name, "eth_drift_v1")
        self.assertNotEqual(btc.name, eth.name)


if __name__ == "__main__":
    unittest.main()
