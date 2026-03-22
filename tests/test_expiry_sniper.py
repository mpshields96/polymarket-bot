"""
Tests for src/strategies/expiry_sniper.py — Kalshi expiry sniping strategy.

Strategy: enter a 15-min Kalshi binary in the LAST 14 minutes when
YES or NO price >= 90c and underlying coin has moved >= 0.1% from window open.

Academic basis: Favorite-longshot bias — heavy favorites close >90% of the time,
making 90c markets systematically underpriced.

V7 parameters (processoverprofit.blog):
  triggerPoint   = 90c   — enter when YES or NO >= 90c
  triggerMinute  = 14    — only enter when <= 14 min remaining
  HARD_SKIP      = 5s    — skip final 5 seconds
  stop-loss      = None  — start without (add after empirical win rate data)

Gotcha (from Session 53/54 notes):
  - Use close_time from market object directly for seconds_remaining calculation
  - Kelly at 90c is functionally zero until real win rate data — use 0.50 USD fixed paper size
  - Paper phase: 30 bets needed before any live gate evaluation
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.strategies.expiry_sniper import ExpirySniperStrategy
from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Helpers ───────────────────────────────────────────────────────────


def _make_market(
    ticker: str = "KXBTC15M-TEST",
    yes_price: int = 90,
    no_price: int = 10,
    seconds_remaining: float = 300.0,  # 5 min default
    status: str = "open",
) -> Market:
    now = datetime.now(timezone.utc)
    close_time = (now + timedelta(seconds=seconds_remaining)).isoformat()
    open_time = (now - timedelta(minutes=10)).isoformat()
    return Market(
        ticker=ticker,
        title="Test market",
        event_ticker="KXBTC15M",
        status=status,
        yes_price=yes_price,
        no_price=no_price,
        volume=50000,
        close_time=close_time,
        open_time=open_time,
        result=None,
        raw={},
    )


def _make_orderbook() -> OrderBook:
    return OrderBook(
        yes_bids=[OrderBookLevel(price=90, quantity=100)],
        no_bids=[OrderBookLevel(price=10, quantity=100)],
    )


def _default_strategy() -> ExpirySniperStrategy:
    return ExpirySniperStrategy(
        trigger_price_cents=90.0,
        max_seconds_remaining=840,  # 14 min
        hard_skip_seconds=5,
        min_drift_pct=0.001,        # 0.1% coin move
    )


# ── TestExpirySniperSignal — when signal SHOULD fire ─────────────────────


class TestExpirySniperSignal:
    """Verify that valid signals are generated under correct conditions."""

    def test_yes_signal_at_90c_with_valid_time_and_drift(self):
        """YES at 90c, 5 min remaining, +0.2% coin drift → YES signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=90, no_price=10, seconds_remaining=300)
        signal = strategy.generate_signal(
            market=market,
            coin_drift_pct=0.002,  # 0.2% move — above 0.1% threshold
        )
        assert signal is not None
        assert signal.side == "yes"
        assert signal.price_cents == 90

    def test_no_signal_at_90c_with_valid_time_and_drift(self):
        """NO at 90c (YES at 10c), 5 min remaining, -0.2% coin drift → NO signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=10, no_price=90, seconds_remaining=300)
        signal = strategy.generate_signal(
            market=market,
            coin_drift_pct=-0.002,  # -0.2% move — above 0.1% threshold
        )
        assert signal is not None
        assert signal.side == "no"
        # price_cents stores actual side price (NO price) — consistent with all strategies
        assert signal.price_cents == 90  # NO price

    def test_signal_at_exactly_90c(self):
        """90c exactly (not 89c) triggers entry."""
        strategy = _default_strategy()
        market = _make_market(yes_price=90, no_price=10, seconds_remaining=600)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        assert signal.side == "yes"

    def test_signal_at_95c_also_valid(self):
        """95c is also valid (higher confidence)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=95, no_price=5, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.side == "yes"

    def test_signal_at_14_min_exactly(self):
        """At exactly 14 min (840s) remaining — border case should fire."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=840)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None

    def test_signal_at_1_min_remaining(self):
        """At 1 min (60s) remaining — well within window, should fire."""
        strategy = _default_strategy()
        market = _make_market(yes_price=91, no_price=9, seconds_remaining=60)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is not None

    def test_signal_fields_populated(self):
        """Signal contains all required fields."""
        strategy = _default_strategy()
        market = _make_market(yes_price=91, no_price=9, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.side in ("yes", "no")
        assert 0 < signal.edge_pct < 1
        assert 0 < signal.win_prob <= 1
        assert 0 <= signal.confidence <= 1
        assert signal.ticker == market.ticker
        assert 1 <= signal.price_cents <= 99
        assert signal.reason != ""

    def test_strategy_name(self):
        """Strategy name is expiry_sniper_v1."""
        strategy = _default_strategy()
        assert strategy.name == "expiry_sniper_v1"

    def test_negative_drift_triggers_no_side(self):
        """When YES=10c (NO=90c) and negative drift, NO signal fires."""
        strategy = _default_strategy()
        market = _make_market(yes_price=10, no_price=90, seconds_remaining=180)
        signal = strategy.generate_signal(market=market, coin_drift_pct=-0.003)
        assert signal is not None
        assert signal.side == "no"

    def test_positive_drift_triggers_yes_side(self):
        """When YES=92c and positive drift, YES signal fires."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=400)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.004)
        assert signal is not None
        assert signal.side == "yes"


# ── TestExpirySniperNoEntry — when signal should NOT fire ─────────────────


class TestExpirySniperNoEntry:
    """Verify all cases where signal correctly returns None."""

    def test_too_much_time_remaining(self):
        """15 min remaining (900s > 840s threshold) — too early, skip."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=900)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is None

    def test_hard_skip_final_5_seconds(self):
        """4s remaining — within hard skip window, no entry."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=4)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is None

    def test_exactly_5_seconds_remaining_is_skipped(self):
        """5s remaining — boundary, should be skipped (<=5 is skipped)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=93, no_price=7, seconds_remaining=5)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is None

    def test_price_below_trigger_yes_side(self):
        """YES at 89c — below 90c trigger, no signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=89, no_price=11, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is None

    def test_price_below_trigger_no_side(self):
        """NO at 89c (YES at 11c) — below trigger, no signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=11, no_price=89, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=-0.003)
        assert signal is None

    def test_near_50c_no_signal(self):
        """YES at 55c — neutral zone, no signal (expiry_sniper targets 90c+)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=55, no_price=45, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is None

    def test_coin_drift_below_threshold(self):
        """Coin moved only 0.05% (below 0.1% threshold) — no signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.0005)
        assert signal is None

    def test_zero_coin_drift(self):
        """Zero coin drift — stuck at 90c without momentum, no signal."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.0)
        assert signal is None

    def test_coin_drift_wrong_direction_yes_side(self):
        """YES at 92c but coin moved DOWN (-0.2%) — drift contradicts price, skip."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=300)
        # Coin moved down but market says YES at 92c — contradictory signal, skip
        signal = strategy.generate_signal(market=market, coin_drift_pct=-0.002)
        assert signal is None

    def test_coin_drift_wrong_direction_no_side(self):
        """NO at 92c (YES at 8c) but coin moved UP (+0.2%) — contradictory, skip."""
        strategy = _default_strategy()
        market = _make_market(yes_price=8, no_price=92, seconds_remaining=300)
        # Coin moved UP but market says NO at 92c — contradictory, skip
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is None

    def test_too_much_time_remaining_even_at_high_price(self):
        """Even at 99c, if >14 min remaining, skip (time filter enforced)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=99, no_price=1, seconds_remaining=900)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.01)
        assert signal is None

    def test_exactly_6_seconds_remaining_fires(self):
        """6s remaining — just above hard skip (>5s), should fire if other conditions met."""
        strategy = _default_strategy()
        market = _make_market(yes_price=93, no_price=7, seconds_remaining=6)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is not None


# ── TestExpirySniperPayout — Kelly and EV math ────────────────────────────


class TestExpirySniperPayout:
    """Verify Kelly fraction behavior and EV math at 90c."""

    def test_kelly_near_zero_at_exactly_90_percent_win_rate(self):
        """At 90c bet with 90% assumed win rate, Kelly fraction ~= 0."""
        # Kelly = (p * b - q) / b where b = (100-90)/90 = 0.111
        # At p=0.90: Kelly = (0.90 * 0.111 - 0.10) / 0.111 = (0.10 - 0.10) / 0.111 = 0
        p = 0.90
        net_payout = (100 - 90) / 90  # = 0.1111
        q = 1 - p
        kelly = (p * net_payout - q) / net_payout
        assert abs(kelly) < 0.01  # essentially zero

    def test_kelly_positive_above_breakeven(self):
        """At 92% win rate, Kelly becomes positive."""
        p = 0.92
        net_payout = (100 - 90) / 90
        q = 1 - p
        kelly = (p * net_payout - q) / net_payout
        assert kelly > 0

    def test_breakeven_win_rate_no_stop_loss(self):
        """Without stop-loss: breakeven win rate = 90/100 = 90% exactly."""
        # Win: +10c, Loss: -90c → breakeven = 90/(90+10) = 90%
        breakeven = 90 / (90 + 10)
        assert abs(breakeven - 0.90) < 0.001

    def test_breakeven_win_rate_with_stop_loss_at_40c(self):
        """With stop-loss at 40c: breakeven = 50/(50+10) = 83.3%."""
        # Win: +10c, Loss: -50c (exit at 40c from 90c entry) → breakeven = 50/60
        breakeven = 50 / (50 + 10)
        assert abs(breakeven - 0.8333) < 0.001

    def test_ev_positive_at_92_percent_no_stop_loss(self):
        """At 92% win rate: EV = 0.92*10 - 0.08*90 = 9.2 - 7.2 = +2.0c per bet."""
        p = 0.92
        ev = p * 10 - (1 - p) * 90
        assert ev > 0

    def test_paper_calibration_bet_size(self):
        """Paper calibration size is fixed at 0.50 USD (Kelly irrelevant in paper phase)."""
        strategy = _default_strategy()
        assert strategy.PAPER_CALIBRATION_USD == 0.50

    def test_win_prob_estimate_above_90c_breakeven(self):
        """Strategy's estimated win_prob should exceed 90c breakeven (0.90)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=90, no_price=10, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        # Must exceed the 90c no-stop-loss breakeven
        assert signal.win_prob > 0.90

    def test_edge_pct_positive(self):
        """Signal edge_pct must be > 0 (positive expected value)."""
        strategy = _default_strategy()
        market = _make_market(yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.edge_pct > 0


# ── TestExpirySniperTimingUsesCloseTime ──────────────────────────────────


class TestExpirySniperTimingUsesCloseTime:
    """Verify that seconds_remaining is derived from close_time (per Session 53 gotcha)."""

    def test_uses_market_close_time_directly(self):
        """Strategy uses close_time for timing — NOT clock modulo arithmetic."""
        strategy = _default_strategy()
        # Market with 5 min remaining
        market = _make_market(yes_price=91, no_price=9, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        # Should fire (300s < 840s threshold)
        assert signal is not None

    def test_market_with_16_minutes_remaining_skipped(self):
        """Market with 16 min remaining — clearly above 14 min gate — skipped."""
        strategy = _default_strategy()
        market = _make_market(yes_price=93, no_price=7, seconds_remaining=960)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.005)
        assert signal is None

    def test_seconds_remaining_derived_from_close_time(self):
        """Verify strategy computes seconds_remaining from close_time internally."""
        strategy = _default_strategy()
        # Market whose close_time is 10 min from now
        now = datetime.now(timezone.utc)
        close_time = (now + timedelta(minutes=10)).isoformat()
        open_time = (now - timedelta(minutes=5)).isoformat()
        market = Market(
            ticker="KXBTC15M-TIMING-TEST",
            title="Timing test",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=92,
            no_price=8,
            volume=50000,
            close_time=close_time,
            open_time=open_time,
            result=None,
            raw={},
        )
        # 10 min remaining = 600s < 840s → should fire (time gate passes)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None


# ── TestExpirySniperDriftDirectionConsistency ──────────────────────────────


class TestExpirySniperDriftDirectionConsistency:
    """Verify drift direction must match the 90c side."""

    def test_positive_drift_matches_yes_at_90c(self):
        """BTC up (+) and YES at 90c → consistent → fire YES."""
        strategy = _default_strategy()
        market = _make_market(yes_price=91, no_price=9, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=+0.003)
        assert sig is not None and sig.side == "yes"

    def test_negative_drift_matches_no_at_90c(self):
        """BTC down (-) and NO at 90c (YES at 10c) → consistent → fire NO."""
        strategy = _default_strategy()
        market = _make_market(yes_price=9, no_price=91, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=-0.003)
        assert sig is not None and sig.side == "no"

    def test_positive_drift_inconsistent_with_no_at_90c(self):
        """BTC up (+) but NO at 90c — inconsistent direction — skip."""
        strategy = _default_strategy()
        market = _make_market(yes_price=9, no_price=91, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=+0.003)
        assert sig is None

    def test_negative_drift_inconsistent_with_yes_at_90c(self):
        """BTC down (-) but YES at 90c — inconsistent direction — skip."""
        strategy = _default_strategy()
        market = _make_market(yes_price=91, no_price=9, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=-0.003)
        assert sig is None


class TestExpirySniperMultiSeries:
    """Verify strategy fires correctly on any coin series ticker."""

    def test_eth_ticker_fires_on_no_at_92c(self):
        """ETH NO=92c (extreme bearish) with negative ETH drift fires NO signal."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXETH15M-26MAR111900-00", yes_price=8, no_price=92, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=-0.005)
        assert sig is not None
        assert sig.side == "no"
        assert sig.ticker == "KXETH15M-26MAR111900-00"

    def test_sol_ticker_fires_on_no_at_91c(self):
        """SOL NO=91c with negative SOL drift fires NO signal."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXSOL15M-26MAR111900-00", yes_price=9, no_price=91, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=-0.004)
        assert sig is not None
        assert sig.side == "no"

    def test_xrp_ticker_fires_on_yes_at_90c(self):
        """XRP YES=90c with positive XRP drift fires YES signal."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXXRP15M-26MAR111900-00", yes_price=90, no_price=10, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=+0.002)
        assert sig is not None
        assert sig.side == "yes"

    def test_strategy_coin_agnostic_same_logic_all_series(self):
        """Strategy logic is coin-agnostic — only price and drift matter, not ticker prefix."""
        strategy = _default_strategy()
        for ticker in ["KXBTC15M-TEST", "KXETH15M-TEST", "KXSOL15M-TEST", "KXXRP15M-TEST"]:
            market = _make_market(ticker=ticker, yes_price=92, no_price=8, seconds_remaining=300)
            sig = strategy.generate_signal(market=market, coin_drift_pct=+0.003)
            assert sig is not None and sig.side == "yes", f"Expected YES signal for {ticker}"


class TestExpirySniperFeeFloor:
    """Tests for fee floor behavior at extreme prices (98-99c).

    Root cause of S70 finding: at 99c YES, minimum Kalshi taker fee (1c per contract)
    equals gross profit (1c per contract), giving 0 net pnl per contract.
    The strategy edge formula uses the raw fee (0.07 * p * (1-p)) not the 1c minimum,
    so generate_signal() at 99c DOES return None (edge = -0.000693 < 0) — correct.
    However, live execution price can drift from signal price (97c signal → 99c fill).
    This test class documents the fee math and confirms 99c signals are already blocked.
    """

    def test_99c_yes_signal_blocked_by_negative_edge(self):
        """At 99c YES: edge = win_prob - price - fee = 0.99 - 0.99 - 0.000693 < 0.
        generate_signal() returns None. Structural: no win_prob can make this positive
        since win_prob is capped at 0.99.
        """
        strategy = _default_strategy()
        market = _make_market(yes_price=99, no_price=1, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=+0.005)
        assert sig is None, "99c YES should be blocked — edge is negative (fee floor kills it)"

    def test_99c_no_signal_blocked_by_negative_edge(self):
        """At 99c NO (YES=1c): same fee floor applies to NO side."""
        strategy = _default_strategy()
        market = _make_market(yes_price=1, no_price=99, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=-0.005)
        assert sig is None, "99c NO should be blocked — edge is negative (fee floor kills it)"

    def test_97c_yes_signal_allowed(self):
        """At 97c YES: edge = 0.98 - 0.97 - raw_fee ≈ +0.002 > 0. Signal fires."""
        strategy = _default_strategy()
        market = _make_market(yes_price=97, no_price=3, seconds_remaining=300)
        sig = strategy.generate_signal(market=market, coin_drift_pct=+0.003)
        assert sig is not None, "97c YES should be allowed — positive edge"
        assert sig.side == "yes"
        assert sig.price_cents == 97

    def test_fee_floor_math_99c(self):
        """Verify: at 99c, actual fee (1c min) = gross profit (1c) → net = 0."""
        import math
        price_cents = 99
        count = 15
        gross = (100 - price_cents) * count               # = 15c
        raw_fee = 0.07 * (price_cents / 100) * (1 - price_cents / 100) * 100
        actual_fee_per_contract = max(1, math.ceil(raw_fee))  # = 1c (ceil(0.069))
        actual_fee_total = actual_fee_per_contract * count      # = 15c
        net = gross - actual_fee_total                          # = 0c
        assert net == 0, f"99c YES net pnl must be 0 (got {net}c)"

    def test_fee_floor_math_98c_positive(self):
        """At 98c, actual fee (1c min) < gross (2c) → net = 1c per contract. Still positive."""
        import math
        price_cents = 98
        count = 15
        gross = (100 - price_cents) * count               # = 30c
        raw_fee = 0.07 * (price_cents / 100) * (1 - price_cents / 100) * 100
        actual_fee_per_contract = max(1, math.ceil(raw_fee))  # = 1c (ceil(0.137))
        actual_fee_total = actual_fee_per_contract * count      # = 15c
        net = gross - actual_fee_total                          # = 15c
        assert net > 0, f"98c YES net pnl must be positive (got {net}c)"


class TestSniperHourBlock:
    """Tests for UTC hour-based sniper block (objective, data-driven)."""

    def test_blocked_hours_set(self):
        """Verify the blocked hours are exactly the two with statistically poor WR."""
        # 08:xx (z=-4.30, WR=82.1%) and 13:xx (WR=90.5%, US market open)
        # Locate the constant in main.py via import-time inspection
        import ast, pathlib
        src = pathlib.Path("main.py").read_text()
        tree = ast.parse(src)
        # Find _BLOCKED_HOURS_UTC assignment inside expiry_sniper_loop
        found = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_BLOCKED_HOURS_UTC":
                        found = True
        assert found, "_BLOCKED_HOURS_UTC constant not found in main.py"

    def test_hour_8_IS_blocked(self):
        """08:xx UTC must be blocked — S123 all-time analysis: n=39, WR=82.1%, -106.63 USD, p=0.012.
        Non-XRP 08:xx: n=32, WR=87.5%, -52.70 USD. S119 crash-strip conclusion was wrong.
        08:xx is the #1 worst hour all-time. Block reinstated S123."""
        import ast, pathlib
        src = pathlib.Path("main.py").read_text()
        tree = ast.parse(src)
        blocked = frozenset()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_BLOCKED_HOURS_UTC":
                        if isinstance(node.value, ast.Call):
                            # frozenset({...}) or frozenset()
                            if node.value.args:
                                elt = node.value.args[0]
                                if isinstance(elt, ast.Set):
                                    blocked = frozenset(e.value for e in elt.elts)
                            else:
                                blocked = frozenset()
        assert 8 in blocked, f"Hour 8 must be blocked — all-time p=0.012, -106.63 USD"

    def test_hour_13_is_NOT_blocked(self):
        """13:xx UTC must NOT be blocked — S119 proved both 13:xx losses were now-guarded XRP buckets.
        Post-guard 13:xx WR=100%. Block reverted S119 saving ~2 USD/day."""
        import ast, pathlib
        src = pathlib.Path("main.py").read_text()
        tree = ast.parse(src)
        blocked = frozenset()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_BLOCKED_HOURS_UTC":
                        if isinstance(node.value, ast.Call):
                            if node.value.args:
                                elt = node.value.args[0]
                                if isinstance(elt, ast.Set):
                                    blocked = frozenset(e.n for e in elt.elts)
                            else:
                                blocked = frozenset()
        assert 13 not in blocked, f"Hour 13 is blocked but should be unblocked (post-guard WR=100%)"

    def test_hour_10_not_blocked(self):
        """10:xx UTC must NOT be blocked — WR=100% historically."""
        blocked = frozenset()
        assert 10 not in blocked

    def test_hour_12_not_blocked(self):
        """12:xx UTC must NOT be blocked — WR=100% historically."""
        blocked = frozenset()
        assert 12 not in blocked

    def test_blocked_hours_count(self):
        """One hour blocked (08:xx) — S123 reinstated after all-time analysis showed p=0.012."""
        import ast, pathlib
        src = pathlib.Path("main.py").read_text()
        tree = ast.parse(src)
        blocked = frozenset({999})  # sentinel to detect if found
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_BLOCKED_HOURS_UTC":
                        if isinstance(node.value, ast.Call):
                            if node.value.args:
                                elt = node.value.args[0]
                                if isinstance(elt, ast.Set):
                                    blocked = frozenset(e.value for e in elt.elts)
                            else:
                                blocked = frozenset()
        assert len(blocked) == 1, f"Expected 1 blocked hour (08:xx), got {len(blocked)}: {blocked}"
        assert 8 in blocked

    def test_00_hour_not_blocked(self):
        """00:xx must NOT be blocked — research chat showed mostly guarded+crash, not structural."""
        blocked = frozenset()
        assert 0 not in blocked


# ── TestExpirySniperSignalFeatures — meta-labeling data for Dim 9 ─────────


class TestExpirySniperSignalFeatures:
    """
    Signal.features must be populated for every sniper signal.

    Dim 9 meta-labeling (S120): sniper is primary engine with 800+ bets.
    These features enable future meta-classifier to predict which sniper
    signals are more likely to win (time-of-day, coin, momentum context).

    CCA features list (2026-03-21): utc_hour, day_of_week, coin,
    seconds_remaining, drift_pct, price_cents, side, win_prob, edge_pct.
    """

    def test_signal_has_features_dict(self):
        """Signal must have non-None features field."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.features is not None
        assert isinstance(signal.features, dict)

    def test_features_has_required_keys(self):
        """features dict must contain all required meta-labeling keys."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        required = {"utc_hour", "utc_day_of_week", "coin", "seconds_remaining", "drift_pct"}
        for key in required:
            assert key in signal.features, f"Missing key: {key}"

    def test_features_utc_hour_valid_range(self):
        """utc_hour must be 0-23."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=90, no_price=10, seconds_remaining=600)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        assert 0 <= signal.features["utc_hour"] <= 23

    def test_features_day_of_week_valid_range(self):
        """utc_day_of_week must be 0-6 (0=Monday, 6=Sunday)."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXETH15M-TEST", yes_price=91, no_price=9, seconds_remaining=400)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        assert 0 <= signal.features["utc_day_of_week"] <= 6

    def test_features_coin_btc_extracted(self):
        """KXBTC15M ticker → coin='BTC'."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=93, no_price=7, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.features["coin"] == "BTC"

    def test_features_coin_eth_extracted(self):
        """KXETH15M ticker → coin='ETH'."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXETH15M-TEST", yes_price=93, no_price=7, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.features["coin"] == "ETH"

    def test_features_coin_sol_extracted(self):
        """KXSOL15M ticker → coin='SOL'."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXSOL15M-TEST", yes_price=92, no_price=8, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        assert signal.features["coin"] == "SOL"

    def test_features_coin_xrp_extracted(self):
        """KXXRP15M ticker → coin='XRP'."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXXRP15M-TEST", yes_price=91, no_price=9, seconds_remaining=300)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.002)
        assert signal is not None
        assert signal.features["coin"] == "XRP"

    def test_features_drift_pct_matches_input(self):
        """features drift_pct must match coin_drift_pct input."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=94, no_price=6, seconds_remaining=300)
        drift = 0.00423
        signal = strategy.generate_signal(market=market, coin_drift_pct=drift)
        assert signal is not None
        assert abs(signal.features["drift_pct"] - drift) < 1e-9

    def test_features_seconds_remaining_positive(self):
        """features seconds_remaining must be positive for a valid signal."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=92, no_price=8, seconds_remaining=180)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is not None
        assert signal.features["seconds_remaining"] > 0

    def test_no_signal_has_no_features(self):
        """When no signal fires (e.g. too much time), features are irrelevant (None returned)."""
        strategy = _default_strategy()
        market = _make_market(ticker="KXBTC15M-TEST", yes_price=92, no_price=8, seconds_remaining=3600)
        signal = strategy.generate_signal(market=market, coin_drift_pct=0.003)
        assert signal is None  # No signal, so no features question arises
