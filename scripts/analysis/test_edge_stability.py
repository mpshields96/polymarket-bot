#!/usr/bin/env python3
"""Tests for edge_stability.py — Edge Degradation Early Warning System."""

import json
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edge_stability import (
    theil_sen_slope,
    wilson_ci,
    cusum_proximity,
    BucketStability,
    AssetCorrelation,
    StabilityReport,
    EdgeStabilityAnalyzer,
    format_report,
)


class TestTheilSenSlope(unittest.TestCase):
    """Theil-Sen robust slope estimator."""

    def test_empty(self):
        self.assertEqual(theil_sen_slope([], []), 0.0)

    def test_single_point(self):
        self.assertEqual(theil_sen_slope([1], [2]), 0.0)

    def test_perfect_positive(self):
        slope = theil_sen_slope([0, 1, 2, 3], [0, 1, 2, 3])
        self.assertAlmostEqual(slope, 1.0)

    def test_perfect_negative(self):
        slope = theil_sen_slope([0, 1, 2, 3], [3, 2, 1, 0])
        self.assertAlmostEqual(slope, -1.0)

    def test_flat(self):
        slope = theil_sen_slope([0, 1, 2, 3], [5, 5, 5, 5])
        self.assertAlmostEqual(slope, 0.0)

    def test_outlier_robust(self):
        # One outlier shouldn't dominate (unlike OLS)
        slope = theil_sen_slope([0, 1, 2, 3, 4], [0, 1, 2, 3, 100])
        # Median of pairwise slopes should be close to 1.0, not ~25
        self.assertLess(slope, 5.0)

    def test_two_points(self):
        slope = theil_sen_slope([0, 10], [0, 5])
        self.assertAlmostEqual(slope, 0.5)

    def test_identical_x(self):
        # All same x → no valid slopes
        slope = theil_sen_slope([5, 5, 5], [1, 2, 3])
        self.assertEqual(slope, 0.0)


class TestWilsonCI(unittest.TestCase):
    """Wilson score confidence interval."""

    def test_zero_n(self):
        lo, hi = wilson_ci(0, 0)
        self.assertEqual(lo, 0.0)
        self.assertEqual(hi, 1.0)

    def test_perfect_wr(self):
        lo, hi = wilson_ci(100, 100)
        self.assertGreater(lo, 0.95)
        self.assertEqual(hi, 1.0)

    def test_zero_wr(self):
        lo, hi = wilson_ci(100, 0)
        self.assertEqual(lo, 0.0)
        self.assertLess(hi, 0.05)

    def test_50_percent(self):
        lo, hi = wilson_ci(100, 50)
        self.assertGreater(lo, 0.39)
        self.assertLess(hi, 0.61)


class TestCusumProximity(unittest.TestCase):
    """CUSUM proximity ratio."""

    def test_zero(self):
        self.assertAlmostEqual(cusum_proximity(0.0, 5.0), 0.0)

    def test_half(self):
        self.assertAlmostEqual(cusum_proximity(2.5, 5.0), 0.5)

    def test_at_threshold(self):
        self.assertAlmostEqual(cusum_proximity(5.0, 5.0), 1.0)

    def test_over_threshold(self):
        self.assertGreater(cusum_proximity(7.0, 5.0), 1.0)

    def test_zero_threshold(self):
        self.assertAlmostEqual(cusum_proximity(3.0, 0.0), 1.0)


class TestBucketStability(unittest.TestCase):
    """BucketStability dataclass."""

    def test_to_dict(self):
        b = BucketStability(
            bucket_key="KXBTC|93|no",
            status="STABLE",
            n_total=50,
            current_wr=0.96,
            wr_slope=-0.002,
            cusum_s=1.5,
            cusum_proximity=0.3,
            days_until_alert=10.5,
        )
        d = b.to_dict()
        self.assertEqual(d["bucket"], "KXBTC|93|no")
        self.assertEqual(d["status"], "STABLE")
        self.assertEqual(d["n_total"], 50)
        self.assertAlmostEqual(d["days_until_alert"], 10.5)

    def test_to_dict_no_days(self):
        b = BucketStability(bucket_key="X", status="STABLE")
        d = b.to_dict()
        self.assertNotIn("days_until_alert", d)


class TestAssetCorrelation(unittest.TestCase):
    """AssetCorrelation dataclass."""

    def test_to_dict(self):
        a = AssetCorrelation(
            asset="KXBTC", n_buckets=5, n_degrading=3,
            degradation_ratio=0.6, is_asset_wide=True,
        )
        d = a.to_dict()
        self.assertEqual(d["asset"], "KXBTC")
        self.assertTrue(d["is_asset_wide"])


class TestStabilityReport(unittest.TestCase):
    """StabilityReport dataclass."""

    def test_to_dict_empty(self):
        r = StabilityReport(timestamp="2026-03-24T00:00:00Z")
        d = r.to_dict()
        self.assertEqual(d["buckets"], [])
        self.assertEqual(d["asset_correlations"], [])


class TestEdgeStabilityAnalyzer(unittest.TestCase):
    """Core analyzer tests with synthetic learning state."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.tmpdir, "learning_state.json")
        self.guards_path = os.path.join(self.tmpdir, "auto_guards.json")
        self.db_path = os.path.join(self.tmpdir, "polybot.db")

    def _write_state(self, state):
        with open(self.state_path, "w") as f:
            json.dump(state, f)

    def _write_guards(self, guards):
        with open(self.guards_path, "w") as f:
            json.dump(guards, f)

    def _make_analyzer(self):
        return EdgeStabilityAnalyzer(
            learning_state_path=self.state_path,
            auto_guards_path=self.guards_path,
            db_path=self.db_path,
        )

    def test_empty_state(self):
        self._write_state({})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(len(report.buckets), 0)
        self.assertEqual(report.summary["total_buckets"], 0)

    def test_insufficient_data(self):
        self._write_state({
            "buckets": {
                "KXBTC|93|no": {
                    "history": [{"n": 5, "win_rate": 0.8, "cusum_s": 0.0, "ts": 1}]
                }
            }
        })
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(report.buckets[0].status, "INSUFFICIENT_DATA")

    def test_stable_bucket(self):
        history = [
            {"n": 50 + i, "win_rate": 0.95, "cusum_s": 0.5, "ts": i,
             "wilson_lo": 0.88, "wilson_hi": 0.98}
            for i in range(5)
        ]
        self._write_state({"buckets": {"KXBTC|93|no": {"history": history}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(report.buckets[0].status, "STABLE")

    def test_degrading_by_slope(self):
        # Win rate dropping 2% per session
        history = [
            {"n": 50, "win_rate": 0.96 - i * 0.02, "cusum_s": 0.5 + i * 0.3,
             "ts": i, "wilson_lo": 0.85, "wilson_hi": 0.98}
            for i in range(5)
        ]
        self._write_state({"buckets": {"KXBTC|93|no": {"history": history}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(report.buckets[0].status, "DEGRADING")
        self.assertLess(report.buckets[0].wr_slope, 0)

    def test_degrading_by_cusum(self):
        history = [
            {"n": 100, "win_rate": 0.90, "cusum_s": 4.5, "ts": i,
             "wilson_lo": 0.83, "wilson_hi": 0.95}
            for i in range(3)
        ]
        self._write_state({"buckets": {"KXBTC|93|no": {"history": history}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        b = report.buckets[0]
        self.assertEqual(b.status, "DEGRADING")
        self.assertGreaterEqual(b.cusum_proximity, 0.8)

    def test_improving_bucket(self):
        history = [
            {"n": 50 + i * 5, "win_rate": 0.88 + i * 0.02, "cusum_s": 0.2,
             "ts": i, "wilson_lo": 0.82, "wilson_hi": 0.95}
            for i in range(5)
        ]
        self._write_state({"buckets": {"KXBTC|93|no": {"history": history}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(report.buckets[0].status, "IMPROVING")

    def test_guarded_bucket(self):
        history = [
            {"n": 50, "win_rate": 0.90, "cusum_s": 0.5, "ts": i,
             "wilson_lo": 0.80, "wilson_hi": 0.96}
            for i in range(3)
        ]
        self._write_state({"buckets": {"KXBTC|95|no": {"history": history}}})
        self._write_guards([{"bucket": "KXBTC|95|no", "reason": "test"}])
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertTrue(report.buckets[0].is_guarded)
        self.assertIn("guarded", report.buckets[0].recommendation.lower())

    def test_asset_correlation_wide(self):
        # 3 of 4 KXBTC buckets degrading → asset-wide
        buckets = {}
        for price in [90, 91, 92, 93]:
            slope_val = -0.02 if price < 93 else 0.0
            history = [
                {"n": 50, "win_rate": 0.95 + i * slope_val, "cusum_s": 0.5,
                 "ts": i, "wilson_lo": 0.88, "wilson_hi": 0.98}
                for i in range(5)
            ]
            buckets[f"KXBTC|{price}|no"] = {"history": history}
        self._write_state({"buckets": buckets})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        btc_corr = [a for a in report.asset_correlations if a.asset == "KXBTC"]
        self.assertEqual(len(btc_corr), 1)
        self.assertTrue(btc_corr[0].is_asset_wide)

    def test_asset_correlation_not_wide(self):
        # 1 of 4 degrading → not asset-wide
        buckets = {}
        for i, price in enumerate([90, 91, 92, 93]):
            slope_val = -0.02 if i == 0 else 0.0
            history = [
                {"n": 50, "win_rate": 0.95 + j * slope_val, "cusum_s": 0.5,
                 "ts": j, "wilson_lo": 0.88, "wilson_hi": 0.98}
                for j in range(5)
            ]
            buckets[f"KXBTC|{price}|no"] = {"history": history}
        self._write_state({"buckets": buckets})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        btc_corr = [a for a in report.asset_correlations if a.asset == "KXBTC"]
        self.assertFalse(btc_corr[0].is_asset_wide)

    def test_days_until_alert_projection(self):
        # CUSUM climbing 0.5/session → should project ~4 sessions = ~0.5 days
        history = [
            {"n": 50, "win_rate": 0.90, "cusum_s": 1.0 + i * 0.5, "ts": i,
             "wilson_lo": 0.80, "wilson_hi": 0.95}
            for i in range(5)
        ]
        self._write_state({"buckets": {"KXBTC|93|no": {"history": history}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        b = report.buckets[0]
        self.assertIsNotNone(b.days_until_alert)
        self.assertGreater(b.days_until_alert, 0)

    def test_bucket_filter(self):
        buckets = {
            "KXBTC|93|no": {"history": [{"n": 50, "win_rate": 0.95, "cusum_s": 0.5, "ts": 1, "wilson_lo": 0.88, "wilson_hi": 0.98}]},
            "KXETH|90|yes": {"history": [{"n": 50, "win_rate": 0.92, "cusum_s": 0.3, "ts": 1, "wilson_lo": 0.82, "wilson_hi": 0.97}]},
        }
        self._write_state({"buckets": buckets})
        analyzer = self._make_analyzer()
        report = analyzer.run(bucket_filter="KXBTC|93|no")
        self.assertEqual(len(report.buckets), 1)
        self.assertEqual(report.buckets[0].bucket_key, "KXBTC|93|no")

    def test_missing_state_file(self):
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(len(report.buckets), 0)

    def test_missing_guards_file(self):
        self._write_state({"buckets": {"X|1|y": {"history": [{"n": 50, "win_rate": 0.9, "cusum_s": 0.1, "ts": 1, "wilson_lo": 0.8, "wilson_hi": 0.95}]}}})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertFalse(report.buckets[0].is_guarded)

    def test_summary_counts(self):
        buckets = {}
        # 1 degrading, 1 stable, 1 insufficient
        buckets["KXBTC|90|no"] = {"history": [
            {"n": 50, "win_rate": 0.96 - i * 0.02, "cusum_s": 0.5, "ts": i, "wilson_lo": 0.85, "wilson_hi": 0.98}
            for i in range(5)
        ]}
        buckets["KXBTC|91|no"] = {"history": [
            {"n": 50, "win_rate": 0.95, "cusum_s": 0.5, "ts": i, "wilson_lo": 0.88, "wilson_hi": 0.98}
            for i in range(5)
        ]}
        buckets["KXBTC|92|no"] = {"history": [
            {"n": 3, "win_rate": 0.67, "cusum_s": 0.0, "ts": 0}
        ]}
        self._write_state({"buckets": buckets})
        analyzer = self._make_analyzer()
        report = analyzer.run()
        self.assertEqual(report.summary["total_buckets"], 3)
        self.assertEqual(report.summary["degrading"], 1)
        self.assertEqual(report.summary["stable"], 1)
        self.assertEqual(report.summary["insufficient_data"], 1)

    def test_format_report_brief(self):
        report = StabilityReport(
            timestamp="2026-03-24T00:00:00Z",
            summary={"total_buckets": 5, "degrading": 1, "stable": 3, "improving": 1, "insufficient_data": 0},
        )
        output = format_report(report, brief=True)
        self.assertIn("EDGE STABILITY REPORT", output)
        self.assertIn("DEGRADING: 1", output)

    def test_format_report_full(self):
        b = BucketStability(
            bucket_key="KXBTC|93|no", status="DEGRADING",
            n_total=50, current_wr=0.88, wr_slope=-0.015,
            cusum_s=3.5, cusum_proximity=0.7,
            days_until_alert=2.5, recommendation="Monitor closely",
        )
        report = StabilityReport(
            timestamp="2026-03-24T00:00:00Z",
            buckets=[b],
            summary={"total_buckets": 1, "degrading": 1, "stable": 0, "improving": 0,
                     "insufficient_data": 0, "asset_wide_degradation": [], "critical_buckets": []},
        )
        output = format_report(report, brief=False)
        self.assertIn("KXBTC|93|no", output)
        self.assertIn("Monitor closely", output)


class TestEdgeStabilityAnalyzerClassification(unittest.TestCase):
    """Test classification edge cases."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.analyzer = EdgeStabilityAnalyzer(
            learning_state_path=os.path.join(self.tmpdir, "ls.json"),
            auto_guards_path=os.path.join(self.tmpdir, "ag.json"),
            db_path=os.path.join(self.tmpdir, "db.db"),
        )

    def test_cusum_critical_overrides_stable_slope(self):
        b = BucketStability(
            bucket_key="X", status="",
            wr_slope=0.0,  # flat slope (would be STABLE)
            cusum_proximity=0.85,  # but CUSUM is critical
        )
        status = self.analyzer._classify_status(b)
        self.assertEqual(status, "DEGRADING")

    def test_cusum_warning_with_flat_slope(self):
        b = BucketStability(
            bucket_key="X", status="",
            wr_slope=0.0,
            cusum_proximity=0.65,
        )
        status = self.analyzer._classify_status(b)
        self.assertEqual(status, "DEGRADING")

    def test_positive_slope_overrides_moderate_cusum(self):
        b = BucketStability(
            bucket_key="X", status="",
            wr_slope=0.01,  # improving
            cusum_proximity=0.3,  # low
        )
        status = self.analyzer._classify_status(b)
        self.assertEqual(status, "IMPROVING")


if __name__ == "__main__":
    unittest.main()
