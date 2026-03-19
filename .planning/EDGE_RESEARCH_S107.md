# EDGE RESEARCH — Session 107 (2026-03-18)

## Summary

This session built Dimension 8 of the self-improvement roadmap: per-strategy temperature
calibration for drift signal win probabilities.

## Research Findings

### 1. Stale Open Trades — False Alarm (resolved)
1932 "stale open trades" flagged by --health was entirely paper trades:
  - 1878 sports_futures_v1 — season-length markets, months to settle (expected)
  - 48 fomc_rate_v1 — FOMC decision market (settles today, expected)
  - 6 copy_trader_v1 — no settlement path (platform mismatch, expected)
  - 1 live open: eth_drift, 0.1hr old (fresh, normal)
The --health stale check was already patched in c2c6a8a to exclude paper trades.
No settlement loop bug exists.

### 2. CUSUM h=5.0 Validation
Simulation (n=20,000 per condition) with our parameters (mu_0=0.58, mu_1=0.50, k=0.04):

  h=5.0: ARL(p=0.58)=237  ARL(p=0.54)=117  ARL(p=0.50)=72

Interpretation: h=5.0 gives 237 bets average between false alarms (strategy truly
working at 58%) and detects genuine no-edge in 72 bets. This is calibrated correctly.

btc_drift CUSUM S=4.480 (68 bets, 48.5% WR) = consistent with true no-edge behavior.
CUSUM is doing its job. h=5.0 threshold is appropriate. No change needed.

### 3. Per-Strategy Calibration Analysis (Pillar 1 + 2)

Statistical comparison of predicted vs actual win rates across 308 live drift bets:

  sol_drift_v1:  n=43,  predicted=65.3%, actual=69.8%, error=4.4pp,  p=0.325 (not sig)
  btc_drift_v1:  n=68,  predicted=57.0%, actual=48.5%, error=8.5pp,  p=0.063 (borderline)
  eth_drift_v1:  n=150, predicted=54.8%, actual=46.7%, error=8.5pp,  p=0.015 (significant)
  xrp_drift_v1:  n=47,  predicted=61.0%, actual=48.9%, error=12.1pp, p=0.033 (significant)

Root cause: the shared Bayesian model averages across SOL (70% WR) and ETH/BTC/XRP
(~47-49% WR). SOL inflates the shared posterior; the other strategies remain miscalibrated.
The model's sensitivity decreased from 300 (static) to 287 (Bayesian) but this is
insufficient to correct per-strategy overconfidence.

Edge_pct bucket analysis for btc_drift showed very_high signals (edge_pct >15%) have
39% WR (n=18, -17.36 USD) — they are anti-predictive. Consistent with the CLAUDE.md
gotcha: "btc_drift has no price extremes filter." OBSERVATION ONLY — need 30+ bets
per bucket for formal test.

### 4. Temperature Calibration Built (Dim 8)

Academic basis: Platt (1999) "Probabilistic Outputs for Support Vector Machines";
Guo et al. (2017) "On Calibration of Modern Neural Networks" — temperature scaling
is the standard single-parameter post-hoc calibration method for binary classifiers.

Method:
  T_s = sum_actual_excess / sum_predicted_excess  (running OLS estimate)
  corrected_win_prob = 0.5 + (win_prob - 0.5) * T_s

Bootstrapped from DB history:
  BTC T=0.500 (clamped min): 57% predicted → 53.5%
  ETH T=0.500 (clamped min): 54.8% predicted → 52.4%
  SOL T=1.290: 65.3% predicted → 69.8%
  XRP T=0.500 (clamped min): 61% predicted → 55.5% (many signals below 5% floor)

Self-improving: update() called after each settled drift bet via bayesian_settlement.py.
T_MIN=0.5, T_MAX=2.0 clamp prevents extreme corrections.

Commit: caf69e9 | Tests: 1623 passing (18 new tests for temperature calibration)

### 5. Open Research Question (sent to CCA)
CCA request submitted: is CUSUM h=5.0 theoretically optimal for binary series at p≈0.5?
What does Page (1954) / Basseville & Nikiforov (1993) recommend?
Does having Bayesian + temperature calibration make CUSUM redundant?

## State After S107

Bot: RUNNING PID 28165 → /tmp/polybot_session107.log
Temperature calibration: ACTIVE (data/calibration.json seeded from 308 historical bets)
Tests: 1623 passing
Last commit: caf69e9

Self-improvement dimensions COMPLETE (1-8):
  1a: auto_guard_discovery.py
  1b: live.py auto-guard loading
  2:  bayesian_drift.py — online MAP update
  3:  settlement_loop — posterior update after each bet
  4:  generate_signal() — Bayesian predict() replaces static sigmoid
  5:  guard_retirement_check.py
  7:  strategy_drift_check.py — Page-Hinkley
  Bootstrap: bayesian_bootstrap.py — retroactive seeding
  Analytics: bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM
  8:  temperature_calibration.py — per-strategy T_s (this session)

Next research directions:
  - Monitor XRP behavior with temperature correction (fewer bets — is WR improving?)
  - Monitor SOL with T=1.29 (larger Kelly bets — is P&L growing?)
  - BTC very_high edge_pct guard: wait for n>=30 in that bucket before building
  - CCA response on CUSUM threshold (sent)
  - sol_drift Stage 2 progression: monitor bet count and Brier post-calibration
