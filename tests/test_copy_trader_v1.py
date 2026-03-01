"""
Tests for copy_trader_v1.py — whale copy trading strategy.

Strategy: fetch top whale wallet activity via whale_watcher + predicting_top,
apply decoy filters, and generate copy-trade signals on the surviving genuine trades.

Decoy filters (documented in "Copytrade Wars" research):
  1. SELL trades → skip (copy buys only)
  2. Size < $200 → skip (no real conviction behind tiny trades)
  3. Whale entry price extreme (< 5¢ or > 95¢) → skip (decoy territory)
  4. Trade too old (> 1 hour) → skip (stale, spread has moved)
  5. Trade too fresh (< 15 min) → skip (flash/pump-and-dump trap)
  6. No matching open position → skip (whale already exited = decoy confirmed)
  7. Unknown outcome (not Yes/No) → skip

Genuine = BUY + size >= $200 + price 5-95¢ + 15min–1hr old + confirmed by open position.
"""

from __future__ import annotations

import pytest

from src.data.whale_watcher import WhaleTrade, WhalePosition

# ── shared timestamps ─────────────────────────────────────────────

NOW_TS = 1_772_500_000
_GOOD_AGE_TS = NOW_TS - 1_200        # 20 min ago — passes both age filters
_TOO_FRESH_TS = NOW_TS - 300         # 5 min ago — below min_position_age_sec (900s)
_TOO_STALE_TS = NOW_TS - 7_200       # 2 hours ago — above max_trade_age_sec (3600s)


# ── shared fixtures ───────────────────────────────────────────────

def _make_trade(**overrides) -> WhaleTrade:
    base = dict(
        proxy_wallet="0xabc123",
        side="BUY",
        outcome="Yes",
        price=0.42,
        size=500.0,
        timestamp=_GOOD_AGE_TS,
        title="Thunder to win 2026 NBA Championship",
        slug="nba-2026-thunder",
        condition_id="0xdeadbeef001",
        transaction_hash="0xtxhash001",
    )
    base.update(overrides)
    return WhaleTrade(**base)


def _make_position(**overrides) -> WhalePosition:
    base = dict(
        proxy_wallet="0xabc123",
        outcome="Yes",
        avg_price=0.42,
        cur_price=0.44,
        size=500.0,
        cash_pnl=10.0,
        title="Thunder to win 2026 NBA Championship",
        slug="nba-2026-thunder",
        condition_id="0xdeadbeef001",
        end_date="2026-07-01T00:00:00Z",
    )
    base.update(overrides)
    return WhalePosition(**base)


# ── is_genuine_signal tests ───────────────────────────────────────


class TestIsGenuineSignal:
    def _make_strategy(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        return CopyTraderStrategy()

    def test_returns_true_for_good_buy(self):
        strat = self._make_strategy()
        trade = _make_trade()
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is True

    def test_false_for_sell_trade(self):
        strat = self._make_strategy()
        trade = _make_trade(side="SELL")
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_for_small_size(self):
        strat = self._make_strategy()
        trade = _make_trade(size=50.0)       # $50 < $200 threshold
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_for_extreme_low_price(self):
        """Entry at 3¢ — likely a decoy (too cheap to be genuine)."""
        strat = self._make_strategy()
        trade = _make_trade(price=0.03)
        positions = [_make_position(avg_price=0.03)]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_for_extreme_high_price(self):
        """Entry at 97¢ — near certainty, likely pump or wash trade."""
        strat = self._make_strategy()
        trade = _make_trade(price=0.97)
        positions = [_make_position(avg_price=0.97)]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_for_too_fresh_trade(self):
        """Trade 5 min ago — not enough time to confirm it wasn't reversed."""
        strat = self._make_strategy()
        trade = _make_trade(timestamp=_TOO_FRESH_TS)
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_for_stale_trade(self):
        """Trade 2 hours ago — spread has moved, stale signal."""
        strat = self._make_strategy()
        trade = _make_trade(timestamp=_TOO_STALE_TS)
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_false_when_no_open_position(self):
        """Whale already exited — trade was a decoy (pump-and-dump confirmed)."""
        strat = self._make_strategy()
        trade = _make_trade()
        assert strat.is_genuine_signal(trade, [], NOW_TS) is False

    def test_false_when_position_outcome_mismatch(self):
        """Whale traded YES but only holds NO position — something is wrong."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="Yes")
        wrong_pos = _make_position(outcome="No")   # different outcome
        assert strat.is_genuine_signal(trade, [wrong_pos], NOW_TS) is False

    def test_false_when_position_conditionid_mismatch(self):
        """Position is for a different market entirely."""
        strat = self._make_strategy()
        trade = _make_trade(condition_id="0xdeadbeef001")
        wrong_pos = _make_position(condition_id="0xdifferentmarket")
        assert strat.is_genuine_signal(trade, [wrong_pos], NOW_TS) is False

    def test_false_for_unknown_outcome(self):
        """Outcome is something we don't understand — skip."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="Draw")
        positions = [_make_position(outcome="Draw")]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_min_size_boundary_passes(self):
        """Trade exactly at min_trade_size_usd threshold should pass."""
        strat = self._make_strategy()
        trade = _make_trade(size=200.0)   # exactly at threshold
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is True

    def test_price_boundary_min_passes(self):
        """Price exactly at 5¢ should pass."""
        strat = self._make_strategy()
        trade = _make_trade(price=0.05)
        positions = [_make_position(avg_price=0.05)]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is True

    def test_price_boundary_max_passes(self):
        """Price exactly at 95¢ should pass."""
        strat = self._make_strategy()
        trade = _make_trade(price=0.95)
        positions = [_make_position(avg_price=0.95)]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is True


# ── generate_signal tests ─────────────────────────────────────────


class TestGenerateSignal:
    def _make_strategy(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        return CopyTraderStrategy()

    def test_generates_yes_signal_for_yes_buy(self):
        strat = self._make_strategy()
        trade = _make_trade(outcome="Yes")
        positions = [_make_position(outcome="Yes")]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig is not None
        assert sig.side == "yes"

    def test_generates_no_signal_for_no_buy(self):
        strat = self._make_strategy()
        trade = _make_trade(outcome="No", price=0.58)
        positions = [_make_position(outcome="No", avg_price=0.58)]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig is not None
        assert sig.side == "no"

    def test_price_cents_is_current_market_yes_price(self):
        """For YES signal, price_cents = round(current_market_price * 100)."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="Yes")
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig.price_cents == 44

    def test_price_cents_is_no_price_for_no_signal(self):
        """For NO signal, price_cents = round((1 - current_market_price) * 100)."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="No", price=0.58)
        positions = [_make_position(outcome="No", avg_price=0.58)]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig.price_cents == 56   # 1 - 0.44 = 0.56

    def test_edge_pct_high_for_high_smart_score(self):
        """Smart score >= 80 → higher base edge."""
        strat = self._make_strategy()
        trade = _make_trade()
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=85.0)
        assert sig.edge_pct >= 0.07   # high-conviction tier

    def test_edge_pct_lower_for_low_smart_score(self):
        """Smart score < 60 → lower base edge."""
        strat = self._make_strategy()
        trade = _make_trade()
        positions = [_make_position()]
        sig_high = strat.generate_signal(trade, positions, NOW_TS,
                                         current_market_price=0.44, smart_score=85.0)
        sig_low = strat.generate_signal(trade, positions, NOW_TS,
                                        current_market_price=0.44, smart_score=55.0)
        assert sig_low.edge_pct < sig_high.edge_pct

    def test_win_prob_from_trade_price_yes(self):
        """YES signal: win_prob ≈ whale's entry price (their implied fair value)."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="Yes", price=0.42)
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.40, smart_score=75.0)
        assert abs(sig.win_prob - 0.42) < 0.01

    def test_win_prob_from_trade_price_no(self):
        """NO signal: win_prob = whale's NO entry price (probability NO wins)."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="No", price=0.60)
        positions = [_make_position(outcome="No", avg_price=0.60)]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.42, smart_score=75.0)
        assert abs(sig.win_prob - 0.60) < 0.01

    def test_ticker_is_condition_id(self):
        """Signal ticker should be the Polymarket condition ID."""
        strat = self._make_strategy()
        trade = _make_trade(condition_id="0xdeadbeef001")
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=75.0)
        assert sig.ticker == "0xdeadbeef001"

    def test_returns_none_when_not_genuine(self):
        """Decoy trade → generate_signal returns None."""
        strat = self._make_strategy()
        trade = _make_trade(side="SELL")   # SELL is filtered
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig is None

    def test_returns_none_when_price_cents_would_be_invalid(self):
        """If current market price rounds to 0 or 100 cents, skip the trade."""
        strat = self._make_strategy()
        trade = _make_trade(outcome="Yes")
        positions = [_make_position()]
        # current_market_price = 0.004 → rounds to 0 → invalid
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.004, smart_score=82.0)
        assert sig is None


# ── strategy metadata tests ───────────────────────────────────────


class TestCopyTraderStrategy:
    def test_strategy_name(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        s = CopyTraderStrategy()
        assert s.name == "copy_trader_v1"

    def test_default_min_trade_size(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        s = CopyTraderStrategy()
        assert s.min_trade_size_usd == 200.0

    def test_custom_min_trade_size(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        s = CopyTraderStrategy(min_trade_size_usd=500.0)
        strat = s
        trade = _make_trade(size=300.0)    # 300 < 500 → filtered
        positions = [_make_position()]
        assert strat.is_genuine_signal(trade, positions, NOW_TS) is False

    def test_reason_included_in_signal(self):
        from src.strategies.copy_trader_v1 import CopyTraderStrategy
        strat = CopyTraderStrategy()
        trade = _make_trade()
        positions = [_make_position()]
        sig = strat.generate_signal(trade, positions, NOW_TS,
                                    current_market_price=0.44, smart_score=82.0)
        assert sig.reason != ""
        assert "0xabc123" in sig.reason or "Thunder" in sig.reason
