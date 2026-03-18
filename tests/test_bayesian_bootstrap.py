"""
Tests for scripts/bayesian_bootstrap.py — Bayesian posterior bootstrap from DB.

Verifies that the bootstrap correctly processes historical drift bets,
resets from prior, and produces a tighter posterior than the flat prior.
"""

from __future__ import annotations

import json
import math
import sqlite3
import sys
from pathlib import Path

import pytest

PROJ = Path(__file__).parent.parent
sys.path.insert(0, str(PROJ))

# Lazy import of the bootstrap module (it imports main project modules)
def _import_bootstrap():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "bayesian_bootstrap",
        str(PROJ / "scripts" / "bayesian_bootstrap.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_PRIOR_LOG_S_MEAN = math.log(300.0)
_PRIOR_LOG_S_VAR = 1.0
_PRIOR_B_MEAN = 0.0
_PRIOR_B_VAR = 0.25


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_db(tmp_path: Path) -> tuple[sqlite3.Connection, Path]:
    """Create a minimal trades DB. Returns (conn, db_path)."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            side TEXT,
            strategy TEXT,
            win_prob REAL,
            result TEXT,
            is_paper INTEGER,
            settled_at REAL
        )
    """)
    conn.commit()
    return conn, db_path


def _insert_trade(conn, *, side, strategy, win_prob, result, is_paper=0, settled_at=1000.0):
    conn.execute(
        "INSERT INTO trades (ticker, side, strategy, win_prob, result, is_paper, settled_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("KXBTC15M-test", side, strategy, win_prob, result, is_paper, settled_at),
    )
    conn.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestBayesianBootstrapBasic:
    """Core bootstrap behaviour."""

    def test_empty_db_returns_zero(self, tmp_path):
        """Empty DB returns 0 (no bets processed)."""
        conn, db_path = _create_db(tmp_path)
        conn.close()
        posterior_path = tmp_path / "posterior.json"

        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 0

    def test_single_win_produces_n_equals_one(self, tmp_path):
        """A single valid drift bet produces n=1 in posterior."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.60, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 1

        data = json.loads(posterior_path.read_text())
        assert data["n_observations"] == 1

    def test_single_yes_win_nudges_intercept_positive(self, tmp_path):
        """After one YES win, intercept should shift slightly positive."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.60, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)

        data = json.loads(posterior_path.read_text())
        assert data["intercept_mean"] > _PRIOR_B_MEAN

    def test_only_drift_strategies_included(self, tmp_path):
        """Sniper and lag bets must be excluded."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.60, result="yes", settled_at=1000.0)
        _insert_trade(conn, side="no", strategy="expiry_sniper_v1",
                      win_prob=0.92, result="no", settled_at=1001.0)
        _insert_trade(conn, side="yes", strategy="btc_lag_v1",
                      win_prob=0.55, result="yes", settled_at=1002.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 1  # only the drift bet

    def test_paper_bets_excluded(self, tmp_path):
        """Paper bets (is_paper=1) must not feed the posterior."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.65, result="yes", is_paper=1, settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 0

    def test_invalid_win_prob_zero_skipped(self, tmp_path):
        """Bets with win_prob=0.0 must be skipped (logit undefined)."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.0, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 0

    def test_invalid_win_prob_one_skipped(self, tmp_path):
        """Bets with win_prob=1.0 must be skipped (logit undefined)."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=1.0, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 0

    def test_null_win_prob_skipped(self, tmp_path):
        """Bets with win_prob=NULL must be skipped."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=None, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 0

    def test_all_four_drift_strategies_count(self, tmp_path):
        """btc/eth/sol/xrp drift bets all contribute to n."""
        conn, db_path = _create_db(tmp_path)
        for strat in ["btc_drift_v1", "eth_drift_v1", "sol_drift_v1", "xrp_drift_v1"]:
            _insert_trade(conn, side="yes", strategy=strat,
                          win_prob=0.62, result="yes",
                          settled_at=float(1000 + list(["btc_drift_v1", "eth_drift_v1",
                                                         "sol_drift_v1", "xrp_drift_v1"]).index(strat)))
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 4

    def test_dry_run_does_not_write(self, tmp_path):
        """dry_run=True must not create the posterior file."""
        conn, db_path = _create_db(tmp_path)
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.62, result="yes", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path, dry_run=True)
        assert not posterior_path.exists()


class TestBayesianBootstrapPosterior:
    """Posterior quality after bootstrap."""

    def test_many_bets_narrows_uncertainty(self, tmp_path):
        """20+ bets should reduce posterior uncertainty below prior."""
        conn, db_path = _create_db(tmp_path)
        bets = [
            ("yes", "btc_drift_v1", 0.60, "yes"),
            ("yes", "btc_drift_v1", 0.65, "no"),
            ("yes", "eth_drift_v1", 0.55, "yes"),
            ("no",  "eth_drift_v1", 0.58, "no"),
            ("yes", "sol_drift_v1", 0.62, "yes"),
            ("no",  "sol_drift_v1", 0.70, "no"),
            ("yes", "xrp_drift_v1", 0.60, "yes"),
            ("yes", "btc_drift_v1", 0.63, "no"),
            ("yes", "btc_drift_v1", 0.58, "yes"),
            ("no",  "eth_drift_v1", 0.65, "no"),
            ("yes", "eth_drift_v1", 0.57, "yes"),
            ("yes", "sol_drift_v1", 0.61, "no"),
            ("yes", "btc_drift_v1", 0.66, "yes"),
            ("no",  "xrp_drift_v1", 0.60, "no"),
            ("yes", "btc_drift_v1", 0.59, "yes"),
            ("yes", "eth_drift_v1", 0.64, "no"),
            ("yes", "eth_drift_v1", 0.62, "yes"),
            ("no",  "sol_drift_v1", 0.63, "no"),
            ("yes", "btc_drift_v1", 0.61, "yes"),
            ("yes", "xrp_drift_v1", 0.59, "yes"),
        ]
        for i, (side, strat, wp, result) in enumerate(bets):
            _insert_trade(conn, side=side, strategy=strat, win_prob=wp,
                          result=result, settled_at=float(1000 + i))
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 20

        data = json.loads(posterior_path.read_text())
        assert data["n_observations"] == 20
        # Posterior variance must be less than prior (uncertainty narrowed)
        assert data["log_sensitivity_var"] < _PRIOR_LOG_S_VAR
        assert data["intercept_var"] < _PRIOR_B_VAR

    def test_n_observations_matches_return_value(self, tmp_path):
        """n_observations in posterior must equal return value from run_bootstrap."""
        conn, db_path = _create_db(tmp_path)
        for i in range(10):
            _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                          win_prob=0.62, result="yes" if i % 2 == 0 else "no",
                          settled_at=float(1000 + i))
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        data = json.loads(posterior_path.read_text())
        assert n == 10
        assert data["n_observations"] == 10

    def test_override_activates_after_30_bets(self, tmp_path):
        """After bootstrapping 30+ bets, should_override_static() returns True."""
        conn, db_path = _create_db(tmp_path)
        for i in range(35):
            _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                          win_prob=0.60, result="yes" if i % 2 == 0 else "no",
                          settled_at=float(1000 + i))
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)

        from src.models.bayesian_drift import BayesianDriftModel
        model = BayesianDriftModel.load(path=posterior_path)
        assert model.should_override_static() is True
        assert model.n_observations >= 30

    def test_chronological_order_deterministic(self, tmp_path):
        """Same bets in different insertion order produce same final n."""
        conn, db_path = _create_db(tmp_path)
        # Insert reverse chronological — bootstrap must sort by settled_at ASC
        _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                      win_prob=0.65, result="yes", settled_at=2000.0)
        _insert_trade(conn, side="no", strategy="btc_drift_v1",
                      win_prob=0.60, result="no", settled_at=1000.0)
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        n = mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)
        assert n == 2

    def test_missing_db_returns_zero(self, tmp_path):
        """Non-existent DB path returns 0 gracefully."""
        mod = _import_bootstrap()
        n = mod.run_bootstrap(
            db_path=tmp_path / "nonexistent.db",
            posterior_path=tmp_path / "posterior.json",
        )
        assert n == 0

    def test_no_wins_shifts_intercept_negative(self, tmp_path):
        """Sustained losses should shift intercept negative (model learns down-bias)."""
        conn, db_path = _create_db(tmp_path)
        # 10 YES bets all losing — YES is wrong direction, intercept should go negative
        for i in range(10):
            _insert_trade(conn, side="yes", strategy="btc_drift_v1",
                          win_prob=0.60, result="no",  # all losses
                          settled_at=float(1000 + i))
        conn.close()

        posterior_path = tmp_path / "posterior.json"
        mod = _import_bootstrap()
        mod.run_bootstrap(db_path=db_path, posterior_path=posterior_path)

        data = json.loads(posterior_path.read_text())
        # After 10 consecutive YES losses, intercept should be below prior (0.0)
        assert data["intercept_mean"] < _PRIOR_B_MEAN
