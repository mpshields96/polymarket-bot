"""Tests for EValue class in bet_analytics.py.

E-values are a modern alternative to SPRT that allow optional stopping
without inflating type-I error. Based on Grunwald et al (2024, JRSS-B).

The running e-value product E_n is the likelihood ratio for each bet:
  win  → multiply by p1/p0
  loss → multiply by (1-p1)/(1-p0)

Edge confirmed when E_n > 20 (alpha=0.05).
Edge eroding when E_n < 1.0.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.bet_analytics import EValue, run_evalue


class TestEValue:
    def test_initial_state(self):
        ev = EValue(p0=0.93, p1=0.95)
        assert ev.e_value == 1.0
        assert ev.n_bets == 0

    def test_win_increases_e_value(self):
        ev = EValue(p0=0.90, p1=0.95)
        ev.update(won=True)
        assert ev.e_value > 1.0

    def test_loss_decreases_e_value(self):
        ev = EValue(p0=0.90, p1=0.95)
        ev.update(won=False)
        assert ev.e_value < 1.0

    def test_edge_confirmed_after_many_wins(self):
        ev = EValue(p0=0.90, p1=0.95)
        # Feed 190 wins + 10 losses (95% WR, 200 bets) — enough to pass E_n > 20
        for _ in range(190):
            ev.update(won=True)
        for _ in range(10):
            ev.update(won=False)
        assert ev.edge_confirmed

    def test_edge_eroding_at_null_wr(self):
        ev = EValue(p0=0.93, p1=0.95)
        # Feed exactly p0 WR → e-value stays near 1, doesn't confirm
        wins = int(50 * 0.93)
        losses = 50 - wins
        for _ in range(wins):
            ev.update(won=True)
        for _ in range(losses):
            ev.update(won=False)
        assert not ev.edge_confirmed

    def test_e_value_below_null_signals_no_edge(self):
        ev = EValue(p0=0.93, p1=0.95)
        # Feed many losses → e-value drops below 1
        for _ in range(20):
            ev.update(won=False)
        assert ev.e_value < 1.0

    def test_n_bets_tracked(self):
        ev = EValue(p0=0.93, p1=0.95)
        ev.update(won=True)
        ev.update(won=False)
        ev.update(won=True)
        assert ev.n_bets == 3

    def test_run_evalue_confirms_edge(self):
        # 190 wins + 10 losses at p0=0.90, p1=0.95 → E_n >> 20
        outcomes = [1] * 190 + [0] * 10
        result = run_evalue(outcomes, p0=0.90, p1=0.95)
        assert result.edge_confirmed
        assert result.e_value > 20

    def test_run_evalue_no_edge_at_null_wr(self):
        outcomes = [1, 0] * 15  # exactly 50% WR
        result = run_evalue(outcomes, p0=0.50, p1=0.55)
        assert not result.edge_confirmed

    def test_run_evalue_empty_outcomes(self):
        result = run_evalue([], p0=0.93, p1=0.95)
        assert result.e_value == 1.0
        assert result.n_bets == 0

    def test_edge_eroding_property(self):
        ev = EValue(p0=0.93, p1=0.95)
        # Feed many losses — log_e goes negative → edge eroding
        for _ in range(30):
            ev.update(won=False)
        assert ev.edge_eroding
        assert ev.e_value < 1.0

    def test_edge_eroding_false_when_winning(self):
        ev = EValue(p0=0.93, p1=0.95)
        for _ in range(10):
            ev.update(won=True)
        assert not ev.edge_eroding

    def test_optional_stopping_property(self):
        """E-values support optional stopping: checking at N1 then N2 is valid.
        The e-value at N2 is always >= the e-value from an independent test."""
        ev = EValue(p0=0.93, p1=0.95)
        for _ in range(20):
            ev.update(won=True)
        mid_value = ev.e_value
        # Continue with more wins
        for _ in range(20):
            ev.update(won=True)
        assert ev.e_value >= mid_value  # grows monotonically with consecutive wins
