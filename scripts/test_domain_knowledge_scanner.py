"""Tests for domain_knowledge_scanner.py — core logic only (no API calls)."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from domain_knowledge_scanner import (
    KALSHI_FEE_RATE,
    ScanResult,
    analyze_calibration,
    build_probability_prompt,
    calculate_edge,
    categorize_market,
)


class TestCategorizeMarket(unittest.TestCase):
    def test_politics_keywords(self):
        self.assertEqual(categorize_market("Will Trump mention China in speech?"), "politics")
        self.assertEqual(categorize_market("Senate control 2026"), "politics")
        self.assertEqual(categorize_market("Presidential approval above 50%?"), "politics")

    def test_economics_keywords(self):
        self.assertEqual(categorize_market("Fed rate decision December"), "economics")
        self.assertEqual(categorize_market("CPI above 3.5%?"), "economics")
        self.assertEqual(categorize_market("Unemployment rate below 4%?"), "economics")

    def test_geopolitics_keywords(self):
        self.assertEqual(categorize_market("Ukraine ceasefire by June?"), "geopolitics")
        self.assertEqual(categorize_market("China invasion of Taiwan 2026"), "geopolitics")

    def test_no_match(self):
        self.assertIsNone(categorize_market("Bitcoin above 100k?"))
        self.assertIsNone(categorize_market("Lakers win NBA finals"))
        self.assertIsNone(categorize_market("Temperature in NYC above 80F"))


class TestCalculateEdge(unittest.TestCase):
    def test_positive_edge(self):
        # LLM says 70%, Kalshi at 50c → positive edge
        edge = calculate_edge(0.70, 50)
        # 0.70 - 0.50 - fee(0.07 * 0.5 * 0.5) = 0.20 - 0.0175 = 0.1825
        self.assertAlmostEqual(edge, 0.1825, places=3)

    def test_negative_edge(self):
        # LLM says 30%, Kalshi at 50c → negative edge (don't buy YES)
        edge = calculate_edge(0.30, 50)
        self.assertLess(edge, 0)

    def test_zero_edge(self):
        # LLM agrees with market
        edge = calculate_edge(0.50, 50)
        # Should be slightly negative due to fee
        self.assertLess(edge, 0)
        self.assertGreater(edge, -0.02)

    def test_extreme_prices(self):
        # High price: LLM=95%, Kalshi=90c
        edge = calculate_edge(0.95, 90)
        # 0.95 - 0.90 - fee(0.07 * 0.9 * 0.1) = 0.05 - 0.0063 = 0.0437
        self.assertAlmostEqual(edge, 0.0437, places=3)

    def test_fee_highest_at_midrange(self):
        # Fee is highest at 50c (0.07 * 0.25 = 0.0175)
        fee_50 = KALSHI_FEE_RATE * 0.5 * 0.5  # 0.0175
        # Fee at 90c is lower (0.07 * 0.9 * 0.1 = 0.0063)
        fee_90 = KALSHI_FEE_RATE * 0.9 * 0.1  # 0.0063
        self.assertGreater(fee_50, fee_90)


class TestBuildProbabilityPrompt(unittest.TestCase):
    def test_prompt_contains_title(self):
        prompt = build_probability_prompt("Will Trump win 2028?", 55, 45)
        self.assertIn("Will Trump win 2028?", prompt)

    def test_prompt_does_not_contain_price(self):
        # Deliberate: avoid anchoring bias
        prompt = build_probability_prompt("Fed cuts rates?", 65, 35)
        self.assertNotIn("65", prompt)
        self.assertNotIn("35", prompt)

    def test_prompt_asks_for_json(self):
        prompt = build_probability_prompt("Test market", 50, 50)
        self.assertIn("probability", prompt)
        self.assertIn("confidence", prompt)
        self.assertIn("JSON", prompt)


class TestCalibrationAnalysis(unittest.TestCase):
    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            f.write(b"")
            path = Path(f.name)
        try:
            # Should not raise
            analyze_calibration(path)
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        # Should not raise
        analyze_calibration(Path("/tmp/nonexistent_scans.jsonl"))

    def test_with_data(self):
        scans = [
            {
                "timestamp": "2026-03-28T00:00:00Z",
                "market_ticker": "TEST-1",
                "market_title": "Test market",
                "event_ticker": "TEST",
                "category": "politics",
                "kalshi_yes_cents": 50,
                "kalshi_no_cents": 50,
                "llm_probability": 0.65,
                "llm_confidence": "high",
                "llm_reasoning": "test",
                "edge_yes": 0.13,
                "edge_no": -0.17,
                "volume": 100,
                "close_time": "2026-04-01T00:00:00Z",
            },
            {
                "timestamp": "2026-03-28T00:01:00Z",
                "market_ticker": "TEST-2",
                "market_title": "Fed rate cut",
                "event_ticker": "ECON",
                "category": "economics",
                "kalshi_yes_cents": 70,
                "kalshi_no_cents": 30,
                "llm_probability": 0.75,
                "llm_confidence": "medium",
                "llm_reasoning": "test",
                "edge_yes": 0.04,
                "edge_no": -0.06,
                "volume": 500,
                "close_time": "2026-06-01T00:00:00Z",
            },
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False
        ) as f:
            for s in scans:
                f.write(json.dumps(s) + "\n")
            path = Path(f.name)
        try:
            # Should print calibration stats without errors
            analyze_calibration(path)
        finally:
            os.unlink(path)


class TestScanResult(unittest.TestCase):
    def test_dataclass_creation(self):
        r = ScanResult(
            timestamp="2026-03-28T00:00:00Z",
            market_ticker="TEST-1",
            market_title="Test",
            event_ticker="TEST",
            category="politics",
            kalshi_yes_cents=50,
            kalshi_no_cents=50,
            llm_probability=0.65,
            llm_confidence="high",
            llm_reasoning="test",
            edge_yes=0.13,
            edge_no=-0.17,
            volume=100,
            close_time="2026-04-01T00:00:00Z",
        )
        self.assertEqual(r.market_ticker, "TEST-1")
        self.assertEqual(r.category, "politics")

    def test_serializable(self):
        from dataclasses import asdict
        r = ScanResult(
            timestamp="2026-03-28T00:00:00Z",
            market_ticker="TEST-1",
            market_title="Test",
            event_ticker="TEST",
            category="politics",
            kalshi_yes_cents=50,
            kalshi_no_cents=50,
            llm_probability=0.65,
            llm_confidence="high",
            llm_reasoning="test",
            edge_yes=0.13,
            edge_no=-0.17,
            volume=100,
            close_time="2026-04-01T00:00:00Z",
        )
        d = asdict(r)
        s = json.dumps(d)
        self.assertIn("TEST-1", s)


if __name__ == "__main__":
    unittest.main()
