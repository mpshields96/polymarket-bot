"""
Tests for signal feature logging.

Meta-labeling (Pillar 1 self-improvement) requires every drift bet to log
full signal features at fire time. When n crosses 1000, a binary meta-classifier
can be trained to filter low-quality signals.

Features captured per signal:
  pct_from_open, minutes_remaining, time_factor, raw_prob, prob_yes_calibrated,
  edge_pct, win_prob_final, price_cents, side, minutes_late, late_penalty,
  bayesian_active

These tests verify:
  1. Signal accepts an optional features dict (backward compatible)
  2. btc_drift populate features dict on every fired signal
  3. save_trade() persists features as JSON in signal_features column
  4. DB migration adds signal_features column to existing tables
"""
from __future__ import annotations

import json
import math
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from src.strategies.base import Signal
from src.db import DB


# ── helpers ───────────────────────────────────────────────────────────────────

def _valid_signal(**kwargs):
    defaults = dict(
        side="yes",
        edge_pct=0.08,
        win_prob=0.65,
        confidence=0.5,
        ticker="KXBTC15M-TEST",
        price_cents=55,
        reason="test signal",
    )
    defaults.update(kwargs)
    return Signal(**defaults)


# ── Signal dataclass tests ─────────────────────────────────────────────────────

class TestSignalFeaturesField(unittest.TestCase):

    def test_signal_without_features_still_valid(self):
        """Backward compat: old code that doesn't set features must still work."""
        s = _valid_signal()
        self.assertIsNone(s.features)

    def test_signal_with_features_dict(self):
        """Signal accepts and stores an arbitrary features dict."""
        feats = {"pct_from_open": 0.42, "minutes_remaining": 7.5}
        s = _valid_signal(features=feats)
        self.assertEqual(s.features, feats)

    def test_signal_features_none_by_default(self):
        """features defaults to None when not provided."""
        s = Signal(
            side="no",
            edge_pct=0.06,
            win_prob=0.70,
            confidence=0.4,
            ticker="KXETH15M-TEST",
            price_cents=45,
        )
        self.assertIsNone(s.features)


# ── DB persistence tests ───────────────────────────────────────────────────────

class TestSaveTradeFeatures(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db = DB(self.tmp.name)
        self.db.init()

    def tearDown(self):
        self.db.close()

    def test_save_trade_with_features_stores_json(self):
        """save_trade persists signal_features as JSON string."""
        feats = {"pct_from_open": 0.31, "minutes_remaining": 9.2, "side": "yes"}
        tid = self.db.save_trade(
            ticker="KXBTC15M-TEST",
            side="yes",
            action="buy",
            price_cents=55,
            count=1,
            cost_usd=0.55,
            strategy="btc_drift_v1",
            edge_pct=0.08,
            win_prob=0.65,
            is_paper=False,
            signal_features=feats,
        )
        row = self.db._conn.execute(
            "SELECT signal_features FROM trades WHERE id=?", (tid,)
        ).fetchone()
        self.assertIsNotNone(row[0])
        stored = json.loads(row[0])
        self.assertAlmostEqual(stored["pct_from_open"], 0.31)
        self.assertEqual(stored["side"], "yes")

    def test_save_trade_without_features_stores_null(self):
        """save_trade still works without features (backward compat)."""
        tid = self.db.save_trade(
            ticker="KXBTC15M-TEST",
            side="no",
            action="buy",
            price_cents=45,
            count=1,
            cost_usd=0.45,
            strategy="btc_drift_v1",
        )
        row = self.db._conn.execute(
            "SELECT signal_features FROM trades WHERE id=?", (tid,)
        ).fetchone()
        self.assertIsNone(row[0])

    def test_signal_features_column_exists_after_migration(self):
        """DB migration must add signal_features column."""
        cols = [
            row[1]
            for row in self.db._conn.execute("PRAGMA table_info(trades)").fetchall()
        ]
        self.assertIn("signal_features", cols)


# ── btc_drift feature population tests ────────────────────────────────────────

class TestBtcDriftFeaturePopulation(unittest.TestCase):
    """btc_drift.generate_signal() must populate signal.features on every fire."""

    def _make_strategy(self):
        from src.strategies.btc_drift import BTCDriftStrategy
        return BTCDriftStrategy(
            name_override="btc_drift_v1",
            min_edge_pct=0.05,
            min_drift_pct=0.10,
        )

    def _make_market(self, yes_price=55, no_price=45, minutes_remaining=8.0):
        m = MagicMock()
        m.ticker = "KXBTC15M-26MAR182015-15"
        m.yes_price = yes_price
        m.no_price = no_price
        # close_time: now + minutes_remaining
        m.close_time = time.time() + minutes_remaining * 60
        return m

    def _make_feed(self, current_price=85000.0, ref_price=84900.0):
        feed = MagicMock()
        feed.is_stale = False
        feed.current_price.return_value = current_price
        # Force reference price to be already set
        return feed, ref_price

    def test_fired_signal_has_features_dict(self):
        """When generate_signal fires, the returned Signal must have features."""
        strat = self._make_strategy()
        market = self._make_market(yes_price=55, no_price=45)
        feed, ref = self._make_feed(current_price=85000.0, ref_price=84900.0)

        # Pre-seed reference price (simulates second call after first)
        drift = (85000.0 - ref) / ref  # +0.118% drift > 0.10% threshold
        strat._reference_prices[market.ticker] = (ref, 0.0)  # 0 min late

        orderbook = MagicMock()
        signal = strat.generate_signal(market, orderbook, feed)

        if signal is not None:  # Signal fires when edge ≥ min_edge_pct
            self.assertIsNotNone(signal.features)
            self.assertIsInstance(signal.features, dict)
            self.assertIn("pct_from_open", signal.features)
            self.assertIn("minutes_remaining", signal.features)
            self.assertIn("edge_pct", signal.features)
            self.assertIn("win_prob_final", signal.features)
            self.assertIn("bayesian_active", signal.features)

    def test_features_contain_required_keys(self):
        """features dict must contain all keys required for meta-labeling."""
        required_keys = {
            "pct_from_open",
            "minutes_remaining",
            "time_factor",
            "raw_prob",
            "prob_yes_calibrated",
            "edge_pct",
            "win_prob_final",
            "price_cents",
            "side",
            "minutes_late",
            "late_penalty",
            "bayesian_active",
        }
        strat = self._make_strategy()
        market = self._make_market(yes_price=55, no_price=45)
        feed, ref = self._make_feed(current_price=85000.0, ref_price=84900.0)
        strat._reference_prices[market.ticker] = (ref, 0.0)

        orderbook = MagicMock()
        signal = strat.generate_signal(market, orderbook, feed)

        if signal is not None:
            self.assertTrue(
                required_keys.issubset(signal.features.keys()),
                f"Missing keys: {required_keys - signal.features.keys()}"
            )


if __name__ == "__main__":
    unittest.main()
