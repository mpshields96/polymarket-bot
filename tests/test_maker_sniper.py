"""
Tests for MakerSniperStrategy — paper-only maker-side FLB variant.

TDD: Tests written before implementation.

Strategy basis: same FLB signal as expiry_sniper_v1, but executes at (ask - offset_cents)
via post_only limit order. 30-fill paper gate before any live promotion.

Maker edge source: Becker (2026) — Kalshi makers earn +1.12% structural vs takers -1.12%.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.platforms.kalshi import Market, OrderBook, OrderBookLevel


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_market(
    ticker: str = "KXBTC15M-26MAR250300-00",
    yes_price: int = 92,
    no_price: int = 8,
    close_time: str | None = None,
) -> Market:
    """Build a Market fixture."""
    if close_time is None:
        # 10 minutes from now
        dt = datetime.now(timezone.utc) + timedelta(minutes=10)
        close_time = dt.isoformat().replace("+00:00", "Z")
    open_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    return Market(
        ticker=ticker,
        title="Test Market",
        event_ticker="KXBTC15M",
        status="open",
        yes_price=yes_price,
        no_price=no_price,
        volume=5000,
        close_time=close_time,
        open_time=open_time,
    )


def _make_orderbook(yes_bids: list[int], no_bids: list[int]) -> OrderBook:
    """Build an OrderBook fixture from simple price lists."""
    return OrderBook(
        yes_bids=[OrderBookLevel(price=p, quantity=10) for p in yes_bids],
        no_bids=[OrderBookLevel(price=p, quantity=10) for p in no_bids],
    )


# ── Import target ──────────────────────────────────────────────────────────

def _get_strategy():
    from src.strategies.maker_sniper import MakerSniperStrategy
    return MakerSniperStrategy()


# ══════════════════════════════════════════════════════════════════════════
# Group 1: Strategy basics
# ══════════════════════════════════════════════════════════════════════════

class TestMakerSniperBasics:
    def test_name_is_maker_sniper_v1(self):
        strat = _get_strategy()
        assert strat.name == "maker_sniper_v1"

    def test_default_offset_cents_is_one(self):
        strat = _get_strategy()
        assert strat.offset_cents == 1

    def test_default_expiry_seconds_is_300(self):
        strat = _get_strategy()
        assert strat.expiry_seconds == 300

    def test_default_min_spread_cents_is_two(self):
        strat = _get_strategy()
        assert strat.min_spread_cents == 2

    def test_ceiling_price_is_94c(self):
        strat = _get_strategy()
        assert strat.ceiling_price_cents == 94

    def test_custom_params_accepted(self):
        strat = _get_strategy().__class__(offset_cents=2, expiry_seconds=180, min_spread_cents=3)
        assert strat.offset_cents == 2
        assert strat.expiry_seconds == 180
        assert strat.min_spread_cents == 3


# ══════════════════════════════════════════════════════════════════════════
# Group 2: compute_maker_adjustment — spread check + maker price
# ══════════════════════════════════════════════════════════════════════════

class TestComputeMakerAdjustment:
    """
    compute_maker_adjustment(signal, orderbook) -> (maker_price | None, skip_reason | None)
    """

    def _get_yes_signal(self, price_cents: int = 92):
        from src.strategies.base import Signal
        return Signal(
            side="yes",
            edge_pct=0.01,
            win_prob=0.93,
            confidence=0.8,
            ticker="KXBTC15M-26MAR250300-00",
            price_cents=price_cents,
        )

    def _get_no_signal(self, price_cents: int = 92):
        from src.strategies.base import Signal
        return Signal(
            side="no",
            edge_pct=0.01,
            win_prob=0.93,
            confidence=0.8,
            ticker="KXBTC15M-26MAR250300-00",
            price_cents=price_cents,
        )

    def test_yes_signal_normal_spread_returns_maker_price(self):
        """YES spread=3c → YES ask=92, NO bid=8, maker_price=92-1=91."""
        strat = _get_strategy()
        signal = self._get_yes_signal(price_cents=92)
        # NO bid=8 → YES ask=100-8=92. YES bid=89 → spread=3c ≥ min_spread=2.
        ob = _make_orderbook(yes_bids=[89], no_bids=[8])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert skip is None
        assert maker_price == 91  # 92 - 1 offset

    def test_yes_signal_narrow_spread_skipped(self):
        """Spread=1c < min_spread=2c → skip."""
        strat = _get_strategy()
        signal = self._get_yes_signal(price_cents=92)
        # NO bid=8 → YES ask=92. YES bid=91 → spread=1c.
        ob = _make_orderbook(yes_bids=[91], no_bids=[8])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert maker_price is None
        assert skip is not None
        assert "spread" in skip.lower()

    def test_no_signal_normal_spread_returns_maker_price(self):
        """NO side: YES bid=7 → NO ask=93. NO bid=90 → spread=3c. maker_price=92."""
        strat = _get_strategy()
        signal = self._get_no_signal(price_cents=92)
        ob = _make_orderbook(yes_bids=[7], no_bids=[90])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert skip is None
        assert maker_price == 92  # 93 - 1 offset

    def test_no_signal_narrow_spread_skipped(self):
        """NO spread=1c → skip."""
        strat = _get_strategy()
        signal = self._get_no_signal(price_cents=92)
        # YES bid=7 → NO ask=93. NO bid=92 → spread=1c.
        ob = _make_orderbook(yes_bids=[7], no_bids=[92])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert maker_price is None
        assert skip is not None

    def test_missing_orderbook_bids_skipped(self):
        """Empty YES bids → cannot compute ask → skip."""
        strat = _get_strategy()
        signal = self._get_yes_signal()
        ob = _make_orderbook(yes_bids=[], no_bids=[])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert maker_price is None
        assert skip is not None

    def test_maker_price_below_floor_skipped(self):
        """ask=91c, offset=5c → maker_price=86c < floor=87c → skip."""
        strat = _get_strategy().__class__(offset_cents=5)
        from src.strategies.base import Signal
        signal = Signal(
            side="yes", edge_pct=0.01, win_prob=0.92, confidence=0.8,
            ticker="KXBTC15M-X", price_cents=91,
        )
        # NO bid=9 → YES ask=91. YES bid=84 → spread=7c ≥ min_spread=2.
        ob = _make_orderbook(yes_bids=[84], no_bids=[9])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert maker_price is None
        assert skip is not None

    def test_offset_two_applied(self):
        """offset_cents=2 → maker_price = ask - 2."""
        strat = _get_strategy().__class__(offset_cents=2)
        signal = self._get_yes_signal(price_cents=92)
        # YES ask=92 (NO bid=8), YES bid=88 → spread=4c ≥ min_spread=2
        ob = _make_orderbook(yes_bids=[88], no_bids=[8])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert skip is None
        assert maker_price == 90  # 92 - 2

    def test_exact_min_spread_allowed(self):
        """Spread == min_spread_cents is allowed (≥, not >)."""
        strat = _get_strategy()
        signal = self._get_yes_signal(price_cents=92)
        # YES ask=92 (NO bid=8), YES bid=90 → spread=2c = min_spread=2
        ob = _make_orderbook(yes_bids=[90], no_bids=[8])
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert skip is None
        assert maker_price == 91


# ══════════════════════════════════════════════════════════════════════════
# Group 3: generate_signal — ceiling check added vs expiry_sniper
# ══════════════════════════════════════════════════════════════════════════

class TestMakerSniperGenerateSignal:
    def _market_with_yes(self, yes_price: int, minutes_left: float = 10.0) -> Market:
        dt = datetime.now(timezone.utc) + timedelta(minutes=minutes_left)
        close_time = dt.isoformat().replace("+00:00", "Z")
        open_time = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        return Market(
            ticker="KXBTC15M-26MAR250300-00",
            title="BTC",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=yes_price,
            no_price=100 - yes_price,
            volume=5000,
            close_time=close_time,
            open_time=open_time,
        )

    def test_valid_yes_signal_below_ceiling(self):
        """YES=92c, drift=+0.5% → signal fires (92 <= 94 ceiling)."""
        strat = _get_strategy()
        market = self._market_with_yes(92)
        sig = strat.generate_signal(market, coin_drift_pct=0.005)
        assert sig is not None
        assert sig.side == "yes"
        assert sig.price_cents == 92

    def test_yes_above_ceiling_blocked(self):
        """YES=95c > ceiling=94c → no signal (too close to certainty, spread too narrow)."""
        strat = _get_strategy()
        market = self._market_with_yes(95)
        sig = strat.generate_signal(market, coin_drift_pct=0.005)
        assert sig is None

    def test_yes_at_ceiling_allowed(self):
        """YES=94c == ceiling → signal fires (≤ 94)."""
        strat = _get_strategy()
        market = self._market_with_yes(94)
        sig = strat.generate_signal(market, coin_drift_pct=0.005)
        assert sig is not None

    def test_no_signal_below_trigger_skipped(self):
        """YES=85c < trigger=90c → no signal."""
        strat = _get_strategy()
        market = self._market_with_yes(85)
        sig = strat.generate_signal(market, coin_drift_pct=0.005)
        assert sig is None

    def test_inconsistent_direction_skipped(self):
        """YES=92c but coin drifted DOWN → no signal (direction inconsistency)."""
        strat = _get_strategy()
        market = self._market_with_yes(92)
        sig = strat.generate_signal(market, coin_drift_pct=-0.003)
        assert sig is None

    def test_no_side_signal_fires(self):
        """NO=92c with coin down → signal fires on NO side."""
        strat = _get_strategy()
        dt = datetime.now(timezone.utc) + timedelta(minutes=10)
        open_dt = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        market = Market(
            ticker="KXBTC15M-26MAR250300-00",
            title="BTC",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=8,
            no_price=92,
            volume=5000,
            close_time=dt.isoformat().replace("+00:00", "Z"),
            open_time=open_dt,
        )
        sig = strat.generate_signal(market, coin_drift_pct=-0.005)
        assert sig is not None
        assert sig.side == "no"

    def test_no_side_above_ceiling_blocked(self):
        """NO=96c > ceiling=94c → no signal."""
        strat = _get_strategy()
        dt = datetime.now(timezone.utc) + timedelta(minutes=10)
        open_dt = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        market = Market(
            ticker="KXBTC15M-26MAR250300-00",
            title="BTC",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=4,
            no_price=96,
            volume=5000,
            close_time=dt.isoformat().replace("+00:00", "Z"),
            open_time=open_dt,
        )
        sig = strat.generate_signal(market, coin_drift_pct=-0.005)
        assert sig is None

    def test_too_early_skipped(self):
        """17 minutes left > max_seconds=840 (14 min) → no signal."""
        strat = _get_strategy()
        market = self._market_with_yes(92, minutes_left=17)
        sig = strat.generate_signal(market, coin_drift_pct=0.005)
        assert sig is None

    def test_name_is_maker_sniper_v1(self):
        """Strategy name is always maker_sniper_v1."""
        strat = _get_strategy()
        assert strat.name == "maker_sniper_v1"


# ══════════════════════════════════════════════════════════════════════════
# Group 4: Integration — generate_signal + compute_maker_adjustment
# ══════════════════════════════════════════════════════════════════════════

class TestMakerSniperIntegration:
    def test_full_yes_path_produces_maker_price(self):
        """End-to-end: valid YES signal + normal spread → maker_price returned."""
        strat = _get_strategy()
        dt = datetime.now(timezone.utc) + timedelta(minutes=10)
        open_dt = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        market = Market(
            ticker="KXBTC15M-26MAR250300-00",
            title="BTC",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=92,
            no_price=8,
            volume=5000,
            close_time=dt.isoformat().replace("+00:00", "Z"),
            open_time=open_dt,
        )
        ob = _make_orderbook(yes_bids=[89], no_bids=[8])
        signal = strat.generate_signal(market, coin_drift_pct=0.005)
        assert signal is not None
        maker_price, skip = strat.compute_maker_adjustment(signal, ob)
        assert skip is None
        assert maker_price == 91

    def test_full_path_ceiling_blocks_before_orderbook_needed(self):
        """Price above ceiling → signal=None → no orderbook needed."""
        strat = _get_strategy()
        dt = datetime.now(timezone.utc) + timedelta(minutes=10)
        open_dt = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        market = Market(
            ticker="KXBTC15M-26MAR250300-00",
            title="BTC",
            event_ticker="KXBTC15M",
            status="open",
            yes_price=96,
            no_price=4,
            volume=5000,
            close_time=dt.isoformat().replace("+00:00", "Z"),
            open_time=open_dt,
        )
        signal = strat.generate_signal(market, coin_drift_pct=0.005)
        assert signal is None  # never reaches orderbook step
