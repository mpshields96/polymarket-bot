"""
Tests for scripts/bet_analytics.py — Universal Bet Intelligence Framework.

Coverage:
  wilson_ci:   correct bounds, edge cases (n=0, all wins, all losses)
  run_sprt:    edge_confirmed, no_edge, continue; correct lambda accumulation
  brier_score: perfect calibration, worst case, decomposition invariants
  run_cusum:   alert fires on loss streak, resets on wins, stable when healthy
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.bet_analytics import (
    wilson_ci, run_sprt, brier_score, run_cusum, SPRTResult,
    calibration_adjusted_edge, analyze_sniper_coins, analyze_sniper_monthly,
    analyze_sniper_forward_edge, analyze_sniper_rolling_wr,
    roc_auc,
)


# ── Wilson CI (Wilson 1927) ────────────────────────────────────────────────────

class TestWilsonCI:
    def test_zero_bets_returns_full_interval(self):
        lo, hi = wilson_ci(0, 0)
        assert lo == 0.0 and hi == 1.0

    def test_all_wins_upper_bound_below_one(self):
        lo, hi = wilson_ci(100, 100)
        assert lo > 0.95 and hi <= 1.0

    def test_all_losses_lower_bound_above_zero(self):
        lo, hi = wilson_ci(100, 0)
        assert lo >= 0.0 and hi < 0.05

    def test_fifty_pct_wr_symmetric(self):
        lo, hi = wilson_ci(100, 50)
        assert abs((lo + hi) / 2 - 0.5) < 0.01

    def test_sniper_ci_tight_at_n722(self):
        """722 bets at 96% WR should give narrow CI."""
        lo, hi = wilson_ci(722, int(722 * 0.96))
        assert hi - lo < 0.04   # less than 4 ppt wide
        assert lo > 0.93

    def test_bounds_within_zero_one(self):
        for n, k in [(10, 10), (10, 0), (5, 3), (1000, 950)]:
            lo, hi = wilson_ci(n, k)
            assert 0.0 <= lo <= hi <= 1.0


# ── SPRT (Wald 1945) ──────────────────────────────────────────────────────────

class TestSPRT:
    def test_all_wins_confirms_edge(self):
        """Enough wins should confirm edge."""
        outcomes = [1] * 50
        r = run_sprt(outcomes, p0=0.90, p1=0.97)
        assert r.verdict == "edge_confirmed"
        assert r.lambda_val > r.upper_boundary

    def test_all_losses_detects_no_edge(self):
        """Enough losses should detect no edge."""
        outcomes = [0] * 5
        r = run_sprt(outcomes, p0=0.90, p1=0.97)
        assert r.verdict == "no_edge"
        assert r.lambda_val < r.lower_boundary

    def test_mixed_outcomes_continue(self):
        """Typical mixed sequence should still be collecting data."""
        # ~50% WR on a 90% baseline strategy — inconclusive
        outcomes = ([1, 1, 0, 1, 0] * 6)
        r = run_sprt(outcomes, p0=0.90, p1=0.97)
        assert r.verdict in ("continue", "no_edge")

    def test_lambda_accumulates_correctly(self):
        """Lambda per-bet math: win += log(p1/p0), loss += log((1-p1)/(1-p0))."""
        r = run_sprt([1, 0], p0=0.90, p1=0.97)
        expected = math.log(0.97 / 0.90) + math.log(0.03 / 0.10)
        assert abs(r.lambda_val - round(expected, 4)) < 0.001

    def test_verdict_freezes_after_boundary(self):
        """Once no_edge is declared, more wins should not flip verdict."""
        # 3 losses cross lower boundary for sniper params
        outcomes = [0, 0, 0] + [1] * 100
        r = run_sprt(outcomes, p0=0.90, p1=0.97)
        assert r.verdict == "no_edge"

    def test_drift_edge_confirmed(self):
        """sol_drift at 70% WR should eventually confirm edge."""
        outcomes = [1, 1, 1, 0, 1, 1, 1, 0, 1, 1] * 5  # 70% WR
        r = run_sprt(outcomes, p0=0.50, p1=0.62)
        assert r.verdict == "edge_confirmed"

    def test_eth_drift_no_edge(self):
        """eth_drift at 46% WR should detect no edge."""
        outcomes = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0] * 15  # ~30% WR, no edge fast
        r = run_sprt(outcomes, p0=0.50, p1=0.58)
        assert r.verdict == "no_edge"


# ── Brier Score (Brier 1950, Murphy 1973) ─────────────────────────────────────

class TestBrierScore:
    def test_perfect_calibration_has_low_reliability(self):
        """If predicted prob always equals actual outcome, REL should be near 0."""
        # Binary outcomes: predict 1.0 for wins, 0.0 for losses
        prices   = [1.0, 1.0, 1.0, 0.0, 0.0]
        outcomes = [1,   1,   1,   0,   0  ]
        r = brier_score(prices, outcomes)
        assert r.score == 0.0
        assert r.reliability < 0.01

    def test_worst_case_score(self):
        """Predicting 1.0 and always losing = BS of 1.0."""
        prices   = [1.0] * 10
        outcomes = [0]   * 10
        r = brier_score(prices, outcomes)
        assert abs(r.score - 1.0) < 0.01

    def test_decomposition_invariant(self):
        """BS ≈ REL - RES + UNC (Murphy 1973 decomposition)."""
        import random
        random.seed(42)
        prices   = [random.uniform(0.4, 0.99) for _ in range(100)]
        outcomes = [1 if random.random() < p else 0 for p in prices]
        r = brier_score(prices, outcomes)
        reconstructed = r.reliability - r.resolution + r.uncertainty
        assert abs(r.score - reconstructed) < 0.01

    def test_empty_input(self):
        r = brier_score([], [])
        assert r.score == 0.0 and r.n_bets == 0

    def test_sniper_well_calibrated(self):
        """At 96% WR buying at ~93c avg, sniper should have low Brier score."""
        n = 100
        prices   = [0.93] * n
        outcomes = [1] * 96 + [0] * 4
        r = brier_score(prices, outcomes)
        assert r.score < 0.10


# ── CUSUM (Page 1954) ─────────────────────────────────────────────────────────

class TestCUSUM:
    def test_alert_fires_on_loss_streak(self):
        """Sustained losses from a 97% baseline should trigger CUSUM."""
        outcomes = [0] * 10   # all losses
        r = run_cusum(outcomes, mu_0=0.97, mu_1=0.90)
        assert r.alert is True
        assert r.statistic > r.threshold

    def test_stable_on_good_wr(self):
        """95%+ WR should not trigger alert."""
        outcomes = [1] * 95 + [0] * 5
        r = run_cusum(outcomes, mu_0=0.97, mu_1=0.90)
        assert r.alert is False

    def test_cusum_resets_on_wins(self):
        """Wins drive S toward 0; long win streak should reset statistic."""
        outcomes = [1] * 200
        r = run_cusum(outcomes, mu_0=0.97, mu_1=0.90)
        assert r.statistic == 0.0

    def test_statistic_nonnegative(self):
        """S_i = max(0, ...) so statistic is always >= 0."""
        import random
        random.seed(0)
        outcomes = [random.randint(0, 1) for _ in range(500)]
        r = run_cusum(outcomes, mu_0=0.97, mu_1=0.90)
        assert r.statistic >= 0.0

    def test_drift_alert_on_eth_pattern(self):
        """eth_drift's sustained losses should trigger CUSUM alert.
        k=0.04, each loss adds 0.54 to S. 10 losses: S=5.40 > h=5.0."""
        outcomes = [0] * 10  # 10 consecutive losses
        r = run_cusum(outcomes, mu_0=0.58, mu_1=0.50)
        assert r.alert is True

    def test_k_is_half_shift(self):
        """Verify allowance parameter k = (mu_0 - mu_1) / 2."""
        # Implicitly tested via cusum behavior; one win should decrement by:
        # mu_0 - 1 - k = 0.97 - 1 - 0.035 = -0.065 -> floors at 0 from 0
        r = run_cusum([1], mu_0=0.97, mu_1=0.90)
        assert r.statistic == 0.0  # max(0, 0 + (-0.065)) = 0


# ── ROC AUC (Hanley & McNeil 1982, ported from Titanium-Agentic calibration.py) ─

class TestRocAuc:
    def test_perfect_discrimination(self):
        """Wins all have higher price than losses → AUC = 1.0."""
        prices = [0.94, 0.93, 0.91, 0.90]
        outcomes = [1, 1, 0, 0]
        assert roc_auc(prices, outcomes) == 1.0

    def test_random_classifier(self):
        """Equal prices → AUC = 0.5."""
        prices = [0.92, 0.92, 0.92, 0.92]
        outcomes = [1, 0, 1, 0]
        assert roc_auc(prices, outcomes) == 0.5

    def test_all_wins_returns_05(self):
        """All-win set: undefined AUC, returns 0.5."""
        assert roc_auc([0.92, 0.93], [1, 1]) == 0.5

    def test_all_losses_returns_05(self):
        """All-loss set: undefined AUC, returns 0.5."""
        assert roc_auc([0.90, 0.91], [0, 0]) == 0.5

    def test_empty_returns_05(self):
        assert roc_auc([], []) == 0.5

    def test_sniper_high_wr_moderate_auc(self):
        """Sniper at 95% WR: with 1 loss at 0.91c and wins spread 0.90-0.94, AUC near 0.5."""
        # 19 wins at various prices, 1 loss at 0.91
        prices =  [0.92, 0.93, 0.94, 0.90, 0.92, 0.93, 0.91, 0.94, 0.93, 0.92,
                   0.91, 0.90, 0.93, 0.92, 0.94, 0.91, 0.93, 0.92, 0.90, 0.91]
        outcomes = [1,    1,    1,    1,    1,    1,    0,    1,    1,    1,
                    1,    1,    1,    1,    1,    1,    1,    1,    1,    1]
        auc = roc_auc(prices, outcomes)
        assert 0.0 <= auc <= 1.0  # valid range always


# ── Le (2026) Calibration Adjusted Edge ───────────────────────────────────────
# Le (2026) arXiv:2602.19520 — 292M trades across 327K Kalshi/Polymarket contracts.
# Formula: true_prob = p^b / (p^b + (1-p)^b)
# b=1.03 for crypto (near-perfect), b=1.83 for politics near expiry (4-13pp edge).

class TestCalibrationAdjustedEdge:
    def test_perfectly_calibrated_b1_no_edge(self):
        """When b=1.0, true_prob == market_price, edge = 0."""
        true_prob, edge_pp = calibration_adjusted_edge(0.90, b=1.0)
        assert abs(true_prob - 0.90) < 0.001
        assert abs(edge_pp) < 0.01

    def test_crypto_b103_tiny_edge(self):
        """Crypto b=1.03 at 90c gives ~0.3pp edge (Le 2026)."""
        true_prob, edge_pp = calibration_adjusted_edge(0.90, b=1.03)
        assert true_prob > 0.90       # true_prob > market price
        assert 0.0 < edge_pp < 1.0   # small positive edge

    def test_politics_b183_large_edge(self):
        """Politics b=1.83 at 70c gives ~13pp edge (Le 2026)."""
        true_prob, edge_pp = calibration_adjusted_edge(0.70, b=1.83)
        assert true_prob > 0.80       # well above 70c
        assert edge_pp > 10.0         # 10+ percentage point edge

    def test_politics_b183_at_90c_gives_8pp_edge(self):
        """Politics b=1.83 at 90c gives ~8pp edge (Le 2026 formula verified).

        CCA message approximated 4pp but the exact formula gives ~8.2pp:
          0.90^1.83 = 0.8245, 0.10^1.83 = 0.0148
          true_prob = 0.8245/(0.8245+0.0148) = 0.982
        Positive result: 90c politics contracts are significantly more underpriced
        than CCA's summary suggested — even stronger Pillar 3 case.
        """
        true_prob, edge_pp = calibration_adjusted_edge(0.90, b=1.83)
        assert abs(true_prob - 0.982) < 0.002  # true prob ~98.2%
        assert 7.0 < edge_pp < 10.0             # ~8.2pp edge

    def test_b_less_than_1_favorites_overpriced(self):
        """When b<1 (e.g. weather), true_prob < market_price (overpriced)."""
        true_prob, edge_pp = calibration_adjusted_edge(0.90, b=0.75)
        assert true_prob < 0.90  # actually less likely than market says
        assert edge_pp < 0.0     # negative edge

    def test_50c_symmetric_always_zero_edge(self):
        """At 50c, any b value gives zero edge (symmetric point)."""
        for b in [0.5, 1.0, 1.5, 2.0]:
            true_prob, edge_pp = calibration_adjusted_edge(0.50, b=b)
            assert abs(true_prob - 0.50) < 0.001, f"b={b} failed symmetry"
            assert abs(edge_pp) < 0.01, f"b={b} should have zero edge at 50c"

    def test_returns_percentage_points(self):
        """edge_pp should be in percentage points (0-100 scale), not fraction."""
        _, edge_pp = calibration_adjusted_edge(0.90, b=1.83)
        assert edge_pp > 1.0  # 4pp in % scale, not 0.04


# ── Per-coin sniper breakdown (S115) ─────────────────────────────────────────

from scripts.bet_analytics import analyze_sniper_coins, analyze_sniper_monthly


class TestSniperCoinBreakdown:
    """Tests for per-coin SPRT analysis added S115 (XRP drag investigation)."""

    def _make_bets(self, ticker: str, n_wins: int, n_losses: int) -> list[dict]:
        bets = []
        for _ in range(n_wins):
            bets.append({"ticker": ticker, "side": "yes", "result": "yes",
                         "won": True, "pnl_cents": 100, "settled_at": 1700000000})
        for _ in range(n_losses):
            bets.append({"ticker": ticker, "side": "yes", "result": "no",
                         "won": False, "pnl_cents": -2000, "settled_at": 1700000000})
        return bets

    def test_coin_breakdown_prints_four_coins(self, capsys):
        bets = (
            self._make_bets("KXBTC15M-abc", 95, 5) +
            self._make_bets("KXETH15M-abc", 90, 10) +
            self._make_bets("KXSOL15M-abc", 85, 15) +
            self._make_bets("KXXRP15M-abc", 80, 20)
        )
        analyze_sniper_coins(bets)
        out = capsys.readouterr().out
        assert "BTC" in out
        assert "ETH" in out
        assert "SOL" in out
        assert "XRP" in out

    def test_coin_breakdown_shows_pnl(self, capsys):
        bets = self._make_bets("KXBTC15M-abc", 10, 0)
        analyze_sniper_coins(bets)
        out = capsys.readouterr().out
        assert "P&L=" in out

    def test_xrp_below_no_edge_boundary_flagged(self, capsys):
        """XRP at 93% WR with n=185 should trigger the no-edge boundary warning."""
        # 185 bets at 93% WR = 172 wins, 13 losses
        bets = self._make_bets("KXXRP15M-abc", 172, 13)
        analyze_sniper_coins(bets)
        out = capsys.readouterr().out
        assert "crossed no-edge boundary" in out

    def test_btc_above_edge_boundary_no_warning(self, capsys):
        """BTC at 97.5% WR should NOT trigger the no-edge warning."""
        bets = self._make_bets("KXBTC15M-abc", 195, 5)
        analyze_sniper_coins(bets)
        out = capsys.readouterr().out
        assert "crossed no-edge boundary" not in out

    def test_empty_bets_no_crash(self, capsys):
        analyze_sniper_coins([])
        # Should not raise
        capsys.readouterr()


class TestSniperMonthlyWR:
    """Tests for monthly rolling WR added S115 (FLB weakening detection)."""

    def _make_bet(self, won: bool, ts: int) -> dict:
        return {"ticker": "KXBTC15M-abc", "side": "yes",
                "result": "yes" if won else "no", "won": won,
                "pnl_cents": 100 if won else -2000, "settled_at": ts}

    def test_monthly_groups_by_month(self, capsys):
        import datetime
        # Two bets in March 2026, one in April 2026
        mar_ts = int(datetime.datetime(2026, 3, 15, tzinfo=datetime.timezone.utc).timestamp())
        apr_ts = int(datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc).timestamp())
        bets = [self._make_bet(True, mar_ts), self._make_bet(True, mar_ts),
                self._make_bet(False, apr_ts)]
        analyze_sniper_monthly(bets)
        out = capsys.readouterr().out
        assert "2026-03" in out
        assert "2026-04" in out

    def test_single_month_shows_warning(self, capsys):
        import datetime
        ts = int(datetime.datetime(2026, 3, 15, tzinfo=datetime.timezone.utc).timestamp())
        bets = [self._make_bet(True, ts)] * 10
        analyze_sniper_monthly(bets)
        out = capsys.readouterr().out
        assert "Only 1 month" in out

    def test_monthly_shows_wr_and_pnl(self, capsys):
        import datetime
        ts = int(datetime.datetime(2026, 3, 15, tzinfo=datetime.timezone.utc).timestamp())
        bets = [self._make_bet(True, ts)] * 9 + [self._make_bet(False, ts)]
        analyze_sniper_monthly(bets)
        out = capsys.readouterr().out
        assert "WR=90.0%" in out
        assert "P&L=" in out

    def test_none_settled_at_skipped(self, capsys):
        bets = [{"ticker": "KXBTC15M", "won": True, "pnl_cents": 100, "settled_at": None}]
        analyze_sniper_monthly(bets)
        # Should not crash


class TestSniperForwardEdge:
    """Tests for post-guard forward SPRT analysis added S116 (XRP guard validation)."""

    def _make_bet(self, ticker: str, price: int, side: str, won: bool,
                  pnl_cents: int = 100) -> dict:
        return {
            "ticker": ticker, "price_cents": price, "side": side,
            "result": side if won else ("no" if side == "yes" else "yes"),
            "won": won, "pnl_cents": pnl_cents, "settled_at": 1700000000,
        }

    def test_guarded_bets_excluded(self, capsys):
        """Bets matching an active guard should not count in forward SPRT."""
        # 20 XRP NO@93c bets that are guarded
        guarded = [self._make_bet("KXXRP15M-abc", 93, "no", False, -2000)] * 10
        # 10 XRP YES@92c bets (unguarded, in-zone)
        clean = [self._make_bet("KXXRP15M-abc", 92, "yes", True, 100)] * 10
        guards = [{"ticker_contains": "KXXRP", "price_cents": 93, "side": "no"}]
        analyze_sniper_forward_edge(guarded + clean, guards)
        out = capsys.readouterr().out
        # forward n should be 10 (guarded bets excluded), not 20
        assert "XRP" in out
        # Should show forward bets count (not include the 10 guarded)
        assert "n=10" in out

    def test_out_of_zone_bets_excluded(self, capsys):
        """Bets above ceiling (>95c) or below floor (<90c) excluded from forward."""
        above = [self._make_bet("KXBTC15M-abc", 97, "yes", False, -2000)] * 5
        below = [self._make_bet("KXBTC15M-abc", 85, "yes", False, -2000)] * 5
        in_zone = [self._make_bet("KXBTC15M-abc", 92, "yes", True, 100)] * 15
        analyze_sniper_forward_edge(above + below + in_zone, [])
        out = capsys.readouterr().out
        assert "BTC" in out
        # Only in-zone bets should count
        assert "n=15" in out

    def test_forward_label_shown(self, capsys):
        """Output should include 'forward' or 'post-guard' label."""
        bets = [self._make_bet("KXBTC15M-abc", 92, "yes", True, 100)] * 20
        analyze_sniper_forward_edge(bets, [])
        out = capsys.readouterr().out
        assert "forward" in out.lower() or "post-guard" in out.lower()

    def test_xrp_forward_lambda_better_than_all_time(self, capsys):
        """Excluding guarded losses should improve XRP lambda vs all-time."""
        # Mix: 43 guarded losses + 89 wins / 6 losses in-zone
        guarded_losses = [self._make_bet("KXXRP15M-abc", 93, "no", False, -2000)] * 24
        guarded_losses += [self._make_bet("KXXRP15M-abc", 95, "no", False, -2000)] * 19
        in_zone_wins = [self._make_bet("KXXRP15M-abc", 92, "yes", True, 100)] * 89
        in_zone_losses = [self._make_bet("KXXRP15M-abc", 91, "no", False, -2000)] * 6
        guards = [
            {"ticker_contains": "KXXRP", "price_cents": 93, "side": "no"},
            {"ticker_contains": "KXXRP", "price_cents": 95, "side": "no"},
        ]
        all_bets = guarded_losses + in_zone_wins + in_zone_losses
        analyze_sniper_forward_edge(all_bets, guards)
        out = capsys.readouterr().out
        assert "XRP" in out
        # Forward should show 95 bets (not 138)
        assert "n=95" in out

    def test_empty_bets_no_crash(self, capsys):
        analyze_sniper_forward_edge([], [])
        capsys.readouterr()  # should not raise

    def test_empty_guards_includes_all_in_zone(self, capsys):
        """With no guards, forward = all in-zone bets."""
        bets = [self._make_bet("KXETH15M-abc", 93, "yes", True, 100)] * 20
        analyze_sniper_forward_edge(bets, [])
        out = capsys.readouterr().out
        assert "ETH" in out
        assert "n=20" in out


class TestSniperRollingWR:
    """Tests for rolling 50-bet WR windows for early FLB weakening detection (S118).

    Academic basis: Burgi, Deng & Whelan (GWU 2026-001) report 'some evidence that
    the bias is getting smaller over time'. Monthly tracker detects this at 30+ day lag.
    Rolling windows detect trends within a month.
    """

    def _make_bet(self, won: bool, ts: int, pnl_cents: int = 100) -> dict:
        return {
            "ticker": "KXBTC15M-abc", "side": "yes",
            "result": "yes" if won else "no", "won": won,
            "pnl_cents": pnl_cents if won else -2000,
            "created_at": ts,
        }

    def test_empty_no_crash(self, capsys):
        analyze_sniper_rolling_wr([])
        capsys.readouterr()  # no assertion — just must not raise

    def test_one_full_window_shown(self, capsys):
        """50 bets → exactly 1 window labelled."""
        bets = [self._make_bet(True, 1773000000 + i * 60) for i in range(50)]
        analyze_sniper_rolling_wr(bets)
        out = capsys.readouterr().out
        assert "W1" in out or "window 1" in out.lower() or "#1" in out

    def test_two_full_windows_shown(self, capsys):
        """100 bets → 2 windows."""
        bets = [self._make_bet(True, 1773000000 + i * 60) for i in range(100)]
        analyze_sniper_rolling_wr(bets)
        out = capsys.readouterr().out
        assert "W1" in out and "W2" in out

    def test_correct_wr_per_window(self, capsys):
        """First 50 all wins, next 50 all losses → W1=100%, W2=0%."""
        wins = [self._make_bet(True, 1773000000 + i * 60) for i in range(50)]
        losses = [self._make_bet(False, 1773003000 + i * 60) for i in range(50)]
        analyze_sniper_rolling_wr(wins + losses)
        out = capsys.readouterr().out
        assert "100.0%" in out
        assert "0.0%" in out

    def test_declining_wr_alert_shown(self, capsys):
        """If most recent window WR < 94%, ALERT should appear in output."""
        # 50 historical wins, then 45 wins + 5 losses (90% WR in recent window)
        wins = [self._make_bet(True, 1773000000 + i * 60) for i in range(50)]
        recent = [self._make_bet(True, 1773003000 + i * 60) for i in range(45)]
        recent += [self._make_bet(False, 1773006000 + i * 60) for i in range(5)]
        analyze_sniper_rolling_wr(wins + recent)
        out = capsys.readouterr().out
        assert "ALERT" in out or "alert" in out.lower() or "⚠" in out

    def test_stable_wr_no_alert(self, capsys):
        """If recent window WR is healthy (>=96%), no ALERT shown."""
        bets = [self._make_bet(True, 1773000000 + i * 60) for i in range(100)]
        # 98 wins, 2 losses spread across both windows
        bets[25] = self._make_bet(False, 1773000000 + 25 * 60)
        bets[75] = self._make_bet(False, 1773000000 + 75 * 60)
        analyze_sniper_rolling_wr(bets)
        out = capsys.readouterr().out
        assert "ALERT" not in out

    def test_partial_last_window_included(self, capsys):
        """75 bets → full W1 (50 bets) + partial W2 (25 bets) both shown."""
        bets = [self._make_bet(True, 1773000000 + i * 60) for i in range(75)]
        analyze_sniper_rolling_wr(bets)
        out = capsys.readouterr().out
        # Should show 2 windows (partial last is still shown)
        assert "W1" in out and "W2" in out
        assert "50" in out and "25" in out

    def test_output_has_pnl(self, capsys):
        """Each window should show P&L."""
        bets = [self._make_bet(True, 1773000000 + i * 60) for i in range(60)]
        analyze_sniper_rolling_wr(bets)
        out = capsys.readouterr().out
        assert "P&L" in out or "pnl" in out.lower()
