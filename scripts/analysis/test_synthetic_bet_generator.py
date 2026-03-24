#!/usr/bin/env python3
"""Tests for synthetic_bet_generator.py — Synthetic Bet Sequence Generator."""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from synthetic_bet_generator import (
    SyntheticBet,
    BucketProfile,
    SyntheticSequence,
    SyntheticBetGenerator,
    ProfileBuilder,
    sequence_summary,
)


def _make_profile(bucket_key="KXBTC|93|no", price=93, wr=0.96, n=100):
    return BucketProfile(
        bucket_key=bucket_key,
        asset="KXBTC",
        price_cents=price,
        side="no",
        n_historical=n,
        win_rate=wr,
        avg_win_pnl_cents=100 - price,
        avg_loss_pnl_cents=-price,
        hour_weights={h: 1.0 / 24 for h in range(24)},
    )


class TestSyntheticBet(unittest.TestCase):

    def test_to_dict(self):
        b = SyntheticBet(
            synthetic_id=0, bucket_key="KXBTC|93|no",
            timestamp_offset=0.0, ticker="KXBTC15M-SYN-0000",
            side="no", price_cents=93, result="win", pnl_cents=7,
            hour_utc=10,
        )
        d = b.to_dict()
        self.assertEqual(d["synthetic_id"], 0)
        self.assertEqual(d["result"], "win")
        self.assertEqual(d["pnl_cents"], 7)

    def test_loss_pnl(self):
        b = SyntheticBet(
            synthetic_id=1, bucket_key="KXBTC|93|no",
            timestamp_offset=900.0, ticker="KXBTC15M-SYN-0001",
            side="no", price_cents=93, result="loss", pnl_cents=-93,
        )
        self.assertEqual(b.pnl_cents, -93)


class TestBucketProfile(unittest.TestCase):

    def test_break_even_wr(self):
        p = _make_profile(price=93)
        self.assertAlmostEqual(p.break_even_wr, 0.93)

    def test_break_even_90(self):
        p = _make_profile(price=90)
        self.assertAlmostEqual(p.break_even_wr, 0.90)

    def test_to_dict(self):
        p = _make_profile()
        d = p.to_dict()
        self.assertEqual(d["asset"], "KXBTC")
        self.assertEqual(d["price_cents"], 93)
        self.assertIn("break_even_wr", d)


class TestSyntheticSequence(unittest.TestCase):

    def test_to_dict_empty(self):
        seq = SyntheticSequence(
            bucket_key="X", mode="parametric", n_bets=0, win_rate_param=0.95,
        )
        d = seq.to_dict()
        self.assertEqual(d["bets"], [])
        self.assertEqual(d["mode"], "parametric")

    def test_to_dict_with_bets(self):
        bet = SyntheticBet(
            synthetic_id=0, bucket_key="X", timestamp_offset=0,
            ticker="T", side="no", price_cents=93, result="win", pnl_cents=7,
        )
        seq = SyntheticSequence(
            bucket_key="X", mode="parametric", n_bets=1,
            win_rate_param=0.95, bets=[bet],
        )
        d = seq.to_dict()
        self.assertEqual(len(d["bets"]), 1)


class TestSyntheticBetGenerator(unittest.TestCase):

    def test_parametric_basic(self):
        profile = _make_profile(wr=0.95)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 100)
        self.assertEqual(seq.n_bets, 100)
        self.assertEqual(len(seq.bets), 100)
        self.assertEqual(seq.mode, "parametric")
        # With seed=42 and p=0.95, WR should be close to 0.95
        self.assertGreater(seq.actual_wr, 0.85)
        self.assertLess(seq.actual_wr, 1.0)

    def test_parametric_win_rate_override(self):
        profile = _make_profile(wr=0.95)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 1000, win_rate_override=0.50)
        # With p=0.5 and n=1000, WR should be near 0.5
        self.assertGreater(seq.actual_wr, 0.40)
        self.assertLess(seq.actual_wr, 0.60)
        self.assertEqual(seq.win_rate_param, 0.50)

    def test_parametric_zero_bets(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 0)
        self.assertEqual(len(seq.bets), 0)
        self.assertEqual(seq.actual_wr, 0.0)

    def test_reproducibility_with_seed(self):
        profile = _make_profile()
        gen1 = SyntheticBetGenerator(seed=123)
        seq1 = gen1.generate_parametric(profile, 50)
        gen2 = SyntheticBetGenerator(seed=123)
        seq2 = gen2.generate_parametric(profile, 50)
        for b1, b2 in zip(seq1.bets, seq2.bets):
            self.assertEqual(b1.result, b2.result)
            self.assertEqual(b1.pnl_cents, b2.pnl_cents)

    def test_different_seeds_differ(self):
        profile = _make_profile()
        gen1 = SyntheticBetGenerator(seed=1)
        seq1 = gen1.generate_parametric(profile, 100)
        gen2 = SyntheticBetGenerator(seed=2)
        seq2 = gen2.generate_parametric(profile, 100)
        # Very unlikely to be identical
        results1 = [b.result for b in seq1.bets]
        results2 = [b.result for b in seq2.bets]
        self.assertNotEqual(results1, results2)

    def test_pnl_correct(self):
        profile = _make_profile(price=93)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 10)
        for bet in seq.bets:
            if bet.result == "win":
                self.assertEqual(bet.pnl_cents, 7)  # 100 - 93
            else:
                self.assertEqual(bet.pnl_cents, -93)

    def test_timestamp_spacing(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 5)
        for i, bet in enumerate(seq.bets):
            self.assertAlmostEqual(bet.timestamp_offset, i * 900.0)

    def test_hour_distribution(self):
        # Heavily weighted to hour 10
        profile = _make_profile()
        profile.hour_weights = {10: 0.9, 15: 0.1}
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 500)
        hour_10_count = sum(1 for b in seq.bets if b.hour_utc == 10)
        # Should be roughly 90% in hour 10
        self.assertGreater(hour_10_count / 500, 0.75)

    def test_sweep_basic(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        sequences = gen.generate_sweep(profile, 100, 0.85, 0.98, 5)
        self.assertEqual(len(sequences), 5)
        # Win rate params should span the range
        params = [s.win_rate_param for s in sequences]
        self.assertAlmostEqual(params[0], 0.85, places=2)
        self.assertAlmostEqual(params[-1], 0.98, places=2)
        # All should have mode "sweep"
        for s in sequences:
            self.assertEqual(s.mode, "sweep")

    def test_sweep_single_step(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        sequences = gen.generate_sweep(profile, 50, 0.90, 0.95, 1)
        self.assertEqual(len(sequences), 1)
        self.assertAlmostEqual(sequences[0].win_rate_param, 0.90)


class TestSaveLoad(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_save_and_load(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 20)
        path = gen.save_sequence(seq, output_dir=self.tmpdir)
        self.assertTrue(os.path.exists(path))

        loaded = gen.load_sequence(path)
        self.assertEqual(loaded.bucket_key, seq.bucket_key)
        self.assertEqual(loaded.n_bets, seq.n_bets)
        self.assertEqual(len(loaded.bets), len(seq.bets))
        self.assertEqual(loaded.bets[0].result, seq.bets[0].result)

    def test_save_creates_dir(self):
        subdir = os.path.join(self.tmpdir, "nested", "dir")
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 5)
        path = gen.save_sequence(seq, output_dir=subdir)
        self.assertTrue(os.path.exists(path))

    def test_jsonl_format(self):
        profile = _make_profile()
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 3)
        path = gen.save_sequence(seq, output_dir=self.tmpdir)
        with open(path) as f:
            lines = f.readlines()
        # 1 metadata line + 3 bet lines
        self.assertEqual(len(lines), 4)
        meta = json.loads(lines[0])
        self.assertEqual(meta["type"], "metadata")
        bet = json.loads(lines[1])
        self.assertIn("synthetic_id", bet)


class TestSequenceSummary(unittest.TestCase):

    def test_empty(self):
        seq = SyntheticSequence(bucket_key="X", mode="p", n_bets=0, win_rate_param=0.9)
        s = sequence_summary(seq)
        self.assertEqual(s["n"], 0)

    def test_basic_stats(self):
        profile = _make_profile(price=90)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 100)
        s = sequence_summary(seq)
        self.assertEqual(s["n"], 100)
        self.assertEqual(s["wins"] + s["losses"], 100)
        self.assertIsInstance(s["max_drawdown_cents"], int)
        self.assertGreaterEqual(s["max_drawdown_cents"], 0)

    def test_all_wins(self):
        profile = _make_profile(price=93)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 10, win_rate_override=1.0)
        s = sequence_summary(seq)
        self.assertEqual(s["wins"], 10)
        self.assertEqual(s["total_pnl_cents"], 70)  # 10 * 7
        self.assertEqual(s["max_drawdown_cents"], 0)

    def test_all_losses(self):
        profile = _make_profile(price=93)
        gen = SyntheticBetGenerator(seed=42)
        seq = gen.generate_parametric(profile, 10, win_rate_override=0.0)
        s = sequence_summary(seq)
        self.assertEqual(s["losses"], 10)
        self.assertEqual(s["total_pnl_cents"], -930)  # 10 * -93


class TestProfileBuilder(unittest.TestCase):

    def test_build_from_learning_state(self):
        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "learning_state.json")
        state = {
            "buckets": {
                "KXBTC|93|no": {
                    "history": [{"n": 50, "win_rate": 0.96, "ts": 1}]
                }
            }
        }
        with open(state_path, "w") as f:
            json.dump(state, f)

        builder = ProfileBuilder(
            db_path="/nonexistent/db.db",
            learning_state_path=state_path,
        )
        profile = builder.build_from_learning_state("KXBTC|93|no")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.asset, "KXBTC")
        self.assertEqual(profile.price_cents, 93)
        self.assertAlmostEqual(profile.win_rate, 0.96)

    def test_build_from_missing_state(self):
        builder = ProfileBuilder(
            db_path="/nonexistent/db.db",
            learning_state_path="/nonexistent/ls.json",
        )
        profile = builder.build_from_learning_state("KXBTC|93|no")
        self.assertIsNone(profile)

    def test_build_from_missing_bucket(self):
        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "learning_state.json")
        with open(state_path, "w") as f:
            json.dump({"buckets": {}}, f)

        builder = ProfileBuilder(
            db_path="/nonexistent/db.db",
            learning_state_path=state_path,
        )
        profile = builder.build_from_learning_state("KXBTC|99|yes")
        self.assertIsNone(profile)

    def test_invalid_bucket_key(self):
        tmpdir = tempfile.mkdtemp()
        state_path = os.path.join(tmpdir, "learning_state.json")
        with open(state_path, "w") as f:
            json.dump({"buckets": {"bad": {"history": [{"n": 10, "win_rate": 0.5}]}}}, f)
        builder = ProfileBuilder(db_path="/x", learning_state_path=state_path)
        profile = builder.build_from_learning_state("bad")
        self.assertIsNone(profile)


if __name__ == "__main__":
    unittest.main()
