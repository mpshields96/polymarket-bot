"""
Tests for scripts/strategy_analyzer.py

Covers: DB query logic, insight generation, safety gates (min sample sizes),
and output generation. Uses in-memory SQLite with synthetic data.
"""

import json
import sqlite3
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

# Patch the DB path before importing the module
_FAKE_DB = ":memory:"


def _make_conn(trades: list[dict]) -> sqlite3.Connection:
    """Create an in-memory DB with the trades schema and insert test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            timestamp REAL,
            ticker TEXT,
            side TEXT,
            action TEXT,
            price_cents INTEGER,
            count INTEGER,
            cost_usd REAL,
            strategy TEXT,
            edge_pct REAL,
            win_prob REAL,
            is_paper INTEGER,
            client_order_id TEXT,
            server_order_id TEXT,
            result TEXT,
            pnl_cents INTEGER,
            settled_at REAL,
            created_at REAL,
            signal_price_cents INTEGER,
            exit_price_cents INTEGER,
            kalshi_fee_cents INTEGER,
            gross_profit_cents INTEGER,
            tax_basis_usd REAL
        )
    """)
    now = time.time()
    for i, t in enumerate(trades):
        conn.execute("""
            INSERT INTO trades
                (id, timestamp, ticker, side, strategy, price_cents, is_paper,
                 result, pnl_cents, settled_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            i + 1,
            t.get("timestamp", now - (i * 300)),
            t.get("ticker", "KXBTC15M"),
            t["side"],
            t["strategy"],
            t["price_cents"],
            t.get("is_paper", 0),
            t.get("result"),
            t.get("pnl_cents"),
            t.get("settled_at", now - (i * 300)),
            t.get("created_at", now - (i * 300) - 900),
        ))
    conn.commit()
    return conn


# ──────────────────────────────────────────────────────────
# Helper: create synthetic sniper trades
# ──────────────────────────────────────────────────────────

def _sniper_trades(bucket_wins: dict) -> list[dict]:
    """
    bucket_wins: {price_cents: (total, wins)}
    e.g. {95: (40, 40), 97: (35, 33)}
    """
    trades = []
    for price, (total, wins) in bucket_wins.items():
        for i in range(total):
            side = "yes"
            result = "yes" if i < wins else "no"
            pnl = 5 if result == "yes" else -95
            trades.append({
                "side": side,
                "strategy": "expiry_sniper_v1",
                "price_cents": price,
                "result": result,
                "pnl_cents": pnl,
                "is_paper": 0,
            })
    return trades


class TestSniperAnalysis(unittest.TestCase):
    def _run(self, trades):
        from scripts.strategy_analyzer import analyze_sniper
        conn = _make_conn(trades)
        return analyze_sniper(conn)

    def test_profitable_bucket_identified(self):
        """90-94c bucket with enough trades and positive P&L is PROFITABLE."""
        trades = _sniper_trades({92: (50, 49)})  # 98% WR, strongly positive
        result = self._run(trades)
        bucket = result["buckets"].get("90-94")
        self.assertIsNotNone(bucket)
        self.assertGreater(bucket["pnl_usd"], 0)
        insights = result["insights"]
        profitable = [i for i in insights if i["bucket"] == "90-94"]
        self.assertEqual(len(profitable), 1)
        self.assertEqual(profitable[0]["status"], "PROFITABLE")

    def test_losing_bucket_identified(self):
        """97c bucket with enough trades and negative P&L is LOSING."""
        # At 97c: win pays 3c, lose costs 97c. Need 97/100 = 97% WR to break even.
        # 33/35 = 94.3% WR = losing
        trades = _sniper_trades({97: (35, 33)})
        result = self._run(trades)
        bucket = result["buckets"].get("97")
        self.assertIsNotNone(bucket)
        insights = result["insights"]
        losing = [i for i in insights if i["bucket"] == "97"]
        self.assertEqual(len(losing), 1)
        self.assertEqual(losing[0]["status"], "LOSING")

    def test_below_min_sample_no_insight(self):
        """Buckets with fewer than MIN_SNIPER_BUCKET bets generate no insight."""
        from scripts.strategy_analyzer import MIN_SNIPER_BUCKET
        trades = _sniper_trades({95: (MIN_SNIPER_BUCKET - 1, MIN_SNIPER_BUCKET - 1)})
        result = self._run(trades)
        insights = result["insights"]
        self.assertEqual(len(insights), 0, "Should not generate insight below min sample")

    def test_at_exactly_min_sample_generates_insight(self):
        """Exactly MIN_SNIPER_BUCKET bets should generate an insight."""
        from scripts.strategy_analyzer import MIN_SNIPER_BUCKET
        trades = _sniper_trades({95: (MIN_SNIPER_BUCKET, MIN_SNIPER_BUCKET)})
        result = self._run(trades)
        insights = result["insights"]
        self.assertEqual(len(insights), 1)

    def test_time_of_day_best_hours_populated(self):
        """Time-of-day analysis returns best_hours when data exists."""
        trades = _sniper_trades({92: (50, 50)})
        result = self._run(trades)
        self.assertIn("time_of_day", result)
        self.assertIn("best_hours", result["time_of_day"])

    def test_empty_db_returns_empty(self):
        """No sniper trades returns empty buckets and no insights."""
        result = self._run([])
        self.assertEqual(result["buckets"], {})
        self.assertEqual(result["insights"], [])


class TestDriftAnalysis(unittest.TestCase):
    def _run(self, trades):
        from scripts.strategy_analyzer import analyze_drift
        conn = _make_conn(trades)
        return analyze_drift(conn)

    def _make_drift(self, strategy, yes_bets, yes_wins, no_bets, no_wins,
                    price=55, pnl_yes=10, pnl_no=-5):
        trades = []
        for i in range(yes_bets):
            result = "yes" if i < yes_wins else "no"
            trades.append({
                "side": "yes", "strategy": strategy, "price_cents": price,
                "result": result, "pnl_cents": pnl_yes if result == "yes" else -pnl_yes,
                "is_paper": 0,
            })
        for i in range(no_bets):
            result = "no" if i < no_wins else "yes"
            trades.append({
                "side": "no", "strategy": strategy, "price_cents": price,
                "result": result, "pnl_cents": pnl_no if result == "no" else abs(pnl_no),
                "is_paper": 0,
            })
        return trades

    def test_no_data_strategy(self):
        """Strategy with zero bets returns NO_DATA."""
        result = self._run([])
        for strat in ["btc_drift_v1", "eth_drift_v1", "sol_drift_v1", "xrp_drift_v1"]:
            self.assertEqual(result[strat]["status"], "NO_DATA")

    def test_direction_filter_insight_generated(self):
        """Strategy with 30% direction spread and sufficient bets flags direction filter."""
        from scripts.strategy_analyzer import MIN_DIRECTION
        # YES: very low WR, NO: high WR — clear direction filter signal
        trades = self._make_drift(
            "btc_drift_v1",
            yes_bets=MIN_DIRECTION, yes_wins=int(MIN_DIRECTION * 0.30),  # 30% WR
            no_bets=MIN_DIRECTION, no_wins=int(MIN_DIRECTION * 0.70),    # 70% WR
        )
        result = self._run(trades)
        btc = result["btc_drift_v1"]
        self.assertIsNotNone(btc.get("insight"))
        self.assertIn("DIRECTION", btc["insight"])
        self.assertIn("no", btc["insight"])  # 'no' side is better

    def test_direction_filter_not_generated_below_min(self):
        """Below MIN_DIRECTION, no direction filter insight generated."""
        from scripts.strategy_analyzer import MIN_DIRECTION
        trades = self._make_drift(
            "btc_drift_v1",
            yes_bets=MIN_DIRECTION - 1, yes_wins=1,
            no_bets=MIN_DIRECTION - 1, no_wins=MIN_DIRECTION - 2,
        )
        result = self._run(trades)
        btc = result["btc_drift_v1"]
        insight = btc.get("insight", "")
        self.assertNotIn("DIRECTION", insight or "")

    def test_healthy_strategy_labeled(self):
        """Strategy with WR >= 55% labeled HEALTHY."""
        from scripts.strategy_analyzer import MIN_DRIFT_STRATEGY
        trades = self._make_drift(
            "sol_drift_v1",
            yes_bets=MIN_DRIFT_STRATEGY, yes_wins=MIN_DRIFT_STRATEGY,
            no_bets=MIN_DRIFT_STRATEGY, no_wins=MIN_DRIFT_STRATEGY,
        )
        result = self._run(trades)
        sol = result["sol_drift_v1"]
        self.assertIn("HEALTHY", sol.get("insight", ""))

    def test_recent_trend_calculated(self):
        """Recent trend is one of IMPROVING/DECLINING/STABLE."""
        trades = self._make_drift(
            "eth_drift_v1",
            yes_bets=25, yes_wins=12,
            no_bets=25, no_wins=12,
        )
        result = self._run(trades)
        eth = result["eth_drift_v1"]
        self.assertIn(eth["recent_trend"], ["IMPROVING", "DECLINING", "STABLE"])


class TestGraduationStatus(unittest.TestCase):
    def _run(self, trades):
        from scripts.strategy_analyzer import graduation_status
        conn = _make_conn(trades)
        return graduation_status(conn)

    def test_not_ready_below_30(self):
        """Strategy with 20 bets is not ready."""
        trades = [
            {"side": "yes", "strategy": "xrp_drift_v1", "price_cents": 55,
             "result": "yes", "pnl_cents": 10, "is_paper": 0}
            for _ in range(20)
        ]
        result = self._run(trades)
        xrp = result["xrp_drift_v1"]
        self.assertFalse(xrp["ready"])
        self.assertEqual(xrp["needs"], 10)
        self.assertEqual(xrp["live_bets"], 20)

    def test_ready_at_30(self):
        """Strategy with exactly 30 bets is ready."""
        trades = [
            {"side": "yes", "strategy": "btc_drift_v1", "price_cents": 55,
             "result": "yes", "pnl_cents": 10, "is_paper": 0}
            for _ in range(30)
        ]
        result = self._run(trades)
        btc = result["btc_drift_v1"]
        self.assertTrue(btc["ready"])
        self.assertEqual(btc["needs"], 0)

    def test_paper_bets_excluded(self):
        """Paper bets do not count toward graduation."""
        trades = [
            {"side": "yes", "strategy": "btc_drift_v1", "price_cents": 55,
             "result": "yes", "pnl_cents": 10, "is_paper": 1}  # paper!
            for _ in range(40)
        ]
        result = self._run(trades)
        btc = result["btc_drift_v1"]
        self.assertFalse(btc["ready"])
        self.assertEqual(btc["live_bets"], 0)


class TestOverallSummary(unittest.TestCase):
    def _run(self, trades):
        from scripts.strategy_analyzer import overall_summary
        conn = _make_conn(trades)
        return overall_summary(conn)

    def test_zero_bets_no_crash(self):
        """Empty DB returns zeros without crashing."""
        result = self._run([])
        self.assertEqual(result["all_time"]["bets"], 0)
        self.assertEqual(result["all_time"]["pnl_usd"], 0.0)

    def test_all_time_win_rate(self):
        """Win rate calculation is correct."""
        trades = [
            {"side": "yes", "strategy": "expiry_sniper_v1", "price_cents": 92,
             "result": "yes", "pnl_cents": 8, "is_paper": 0},
            {"side": "yes", "strategy": "expiry_sniper_v1", "price_cents": 92,
             "result": "no", "pnl_cents": -92, "is_paper": 0},
        ]
        result = self._run(trades)
        self.assertAlmostEqual(result["all_time"]["win_rate"], 0.5, places=2)

    def test_paper_excluded_from_all_time(self):
        """Paper trades not included in all-time summary."""
        trades = [
            {"side": "yes", "strategy": "expiry_sniper_v1", "price_cents": 92,
             "result": "yes", "pnl_cents": 8, "is_paper": 0},
            {"side": "yes", "strategy": "expiry_sniper_v1", "price_cents": 50,
             "result": "yes", "pnl_cents": 100, "is_paper": 1},  # paper — excluded
        ]
        result = self._run(trades)
        self.assertEqual(result["all_time"]["bets"], 1)

    def test_remaining_target_calculated(self):
        """Remaining target is 125 - current_pnl."""
        trades = [
            {"side": "yes", "strategy": "expiry_sniper_v1", "price_cents": 92,
             "result": "yes", "pnl_cents": 2000, "is_paper": 0},  # +20 USD
        ]
        result = self._run(trades)
        # pnl = +20 USD, target = 125, remaining = 125 - 20 = 105
        self.assertAlmostEqual(result["remaining_usd"], 105.0, places=1)


class TestRecommendationGeneration(unittest.TestCase):
    def test_profitable_sniper_in_recommendations(self):
        """Profitable sniper bucket appears in top recommendations."""
        from scripts.strategy_analyzer import _generate_recommendations
        sniper = {
            "buckets": {
                "90-94": {"pnl_usd": 92.0, "bets": 191, "win_rate": 0.97},
                "97": {"pnl_usd": -28.0, "bets": 36, "win_rate": 0.94},
            },
            "insights": [],
        }
        recs = _generate_recommendations(sniper, {}, {}, {"remaining_usd": 100.0})
        all_recs = " ".join(recs)
        self.assertIn("90-94", all_recs)

    def test_graduation_watch_near_threshold(self):
        """Strategy at 25-29 bets appears in graduation watch."""
        from scripts.strategy_analyzer import _generate_recommendations
        grad = {
            "xrp_drift_v1": {"live_bets": 27, "needs": 3, "ready": False, "graduation_pct": 90}
        }
        recs = _generate_recommendations({}, {}, grad, {"remaining_usd": 100.0})
        self.assertTrue(any("xrp_drift_v1" in r for r in recs))

    def test_target_remaining_in_recommendations(self):
        """Remaining target always appears in recommendations."""
        from scripts.strategy_analyzer import _generate_recommendations
        recs = _generate_recommendations({}, {}, {}, {"remaining_usd": 93.04})
        self.assertTrue(any("93.04" in r for r in recs))


class TestRunAnalysisIntegration(unittest.TestCase):
    def test_full_run_no_save(self):
        """run_analysis with save=False completes without crash."""
        from scripts.strategy_analyzer import run_analysis
        with patch("scripts.strategy_analyzer.DB_PATH",
                   new_callable=lambda: property(lambda self: ":memory:")):
            pass  # Can't patch Path easily — use actual DB
        # Just run against real DB with no save
        result = run_analysis(save=False, brief=True)
        self.assertIn("summary", result)
        self.assertIn("sniper", result)
        self.assertIn("drift", result)
        self.assertIn("graduation", result)
        self.assertIn("top_recommendations", result)

    def test_output_is_json_serializable(self):
        """run_analysis output can be JSON serialized."""
        from scripts.strategy_analyzer import run_analysis
        result = run_analysis(save=False, brief=True)
        # Should not raise
        serialized = json.dumps(result)
        self.assertIsInstance(serialized, str)


if __name__ == "__main__":
    unittest.main()
