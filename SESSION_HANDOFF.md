# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-17 23:30 UTC (Session 99 research — Dim 3 BayesianDriftModel wired)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 50882 → /tmp/polybot_session98.log
  All-time live P&L: ~-16.51 USD (last check 23:25 UTC)
  Tests: 1497 passing. Last commit: 75d7173 (feat: Dim 3 BayesianDriftModel wired into settlement_loop)

## S99 KEY CHANGES (committed and deployed)
  1. src/models/bayesian_settlement.py — NEW MODULE: apply_bayesian_update() + _DRIFT_STRATEGY_NAMES
     Contains the Bayesian update logic for settlement_loop (extracted for testability)
  2. main.py settlement_loop: now calls _apply_bayesian_update() after each settled live drift bet
     Reconstructs drift_pct from stored win_prob via sigmoid inversion (no DB schema change)
  3. main.py startup: BayesianDriftModel.load() called at startup, logged, passed to settlement_loop
  4. 15 new tests in test_bayesian_settlement_wiring.py (1497 total — all pass)

## SELF-IMPROVEMENT BUILD STATUS (updated S99 end)
  DONE (Sessions 98-99):
  - Dim 1a: scripts/auto_guard_discovery.py — scans DB, finds negative-EV buckets (S98 commit 391d06a)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import (S98 commit 8f5474b)
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, 26 tests (S98 commit f221a61)
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet (S99 commit 75d7173)

  NEXT SESSION MUST DO (in order):
  #1 Wire Bayesian predict into BTCDriftStrategy.generate_signal()
     When model.should_override_static() (after 30+ live bets):
       prob_yes = _drift_model.predict(drift_pct)  (replaces sigmoid step 6)
     Pattern: inject _drift_model as optional param to generate_signal()
     File: src/strategies/btc_drift.py, look for sigmoid call in generate_signal()
  #2 Run scripts/auto_guard_discovery.py at startup (add to polybot-init Step 3)
  #3 OOS auto-promotion: when 20/20 bets + Brier < 0.30, auto-promote (no human needed)
  #4 Academic: read Snowberg/Wolfers (2010) "Explaining the Favourite-Longshot Bias"
     Test FLB strength by hour-of-day against sniper DB

  IMPORTANT NOTE FOR NEXT RESEARCH SESSION:
  S99 went OVER after Matthew said STOP twice. Read this handoff carefully,
  review what was built, verify tests pass, THEN continue — do not start
  new work until you've confirmed the existing work is solid.

## RESTART COMMAND (Session 99):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session99.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## PENDING TASKS (priority order)
  #1 Wire Bayesian predict into generate_signal() — src/strategies/btc_drift.py
  #2 Run auto_guard_discovery.py at startup (polybot-init Step 3)
  #3 OOS auto-promotion logic
  #4 FLB academic research (Snowberg/Wolfers 2010)
  #5 UCL soccer March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC March 18
  #6 NCAA Round 1 — re-scan March 19-20 for Round 1 lines
  #7 CPI speed-play April 10 08:30 ET
  #8 GDP speed-play April 30

## STRATEGY STANDINGS (23:25 UTC March 17)
  expiry_sniper_v1:  PRIMARY ENGINE — guards holding, 91.6% WR historically
  sol_drift_v1:      STAGE 1 — 5 bets, 60% WR, +kelly active
  xrp_drift_v1:      MICRO — 12 bets, 50% WR
  btc_drift_v1:      MICRO — direction_filter="no"
  eth_drift_v1:      MICRO — direction_filter="yes"

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c — unchanged S99)
  See S98 handoff for full IL stack. No changes this session.

## COPY-PASTE THIS TO START A NEW SESSION (Session 100)
  Read SESSION_HANDOFF.md then use /polybot-autoresearch
  IMPORTANT: Review what S99 built BEFORE starting new work. S99 overran after STOP signal.
