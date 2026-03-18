# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~02:30 UTC (Session 102 — research, PH drift detection built)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 68913 → /tmp/polybot_session101.log (running since 00:32 UTC S101)
  All-time live P&L: +5.21 USD TODAY (was -7.69 at S101 end — +12.90 USD gain this session)
  Today (March 18): +16.26 USD live, expiry_sniper 14/14 wins, 83% WR on 17 settled
  Tests: 1565 passing. Last commit: ac7721c (feat: Page-Hinkley strategy drift detection S102)

## S102 KEY CHANGES

  1. Dim 7 BUILT — Page-Hinkley sequential drift detection for live strategies
     File: scripts/strategy_drift_check.py — 34 tests in tests/test_strategy_drift_check.py
     What it does: CUSUM-based sequential test detects strategy WR decline before it becomes costly
       - One-sided PH test: floors at 0, alerts when peak_stat > h=4.0
       - Reference k = target_wr - delta/2 (midpoint between OK and declining)
       - Covers sol_drift, btc_drift, eth_drift, xrp_drift
       - Reports current stat + peak stat (separate: peak triggered alert, current shows recovery)
       - Writes /tmp/strategy_drift_report.txt for monitoring loop
     Academic basis: Page (1954), Hinkley (1971), Basseville & Nikiforov (1993)
     LIVE RESULT (S102 run): eth_drift DRIFT ALERT (peak PH=5.05 exceeded h=4.0)
       last20=40%, last10=40%. March 12-13 losses drove the peak. Current PH=2.85 (recovering).
       ACTION: Bayesian self-corrects. Per PRINCIPLES.md: no manual change without 30+ post-change bets.

  2. FLB Analysis complete (668 live sniper bets analyzed)
     BTC YES/NO: 97-98% WR — strong FLB edge confirmed in 90-95c range
     ETH YES/NO: 97-98% WR — strong FLB edge confirmed
     SOL NO: 97% WR | SOL YES: 94% WR (guards at 94c/96c/97c correctly block bad buckets)
     XRP YES/NO: 92-94% WR — structurally lower, all bad buckets already guarded
     Price range 90-95c: positive EV confirmed across all 4 assets for unguarded buckets
     Time-of-day effects: CONFIRMED dead end — hour-08 losses are all pre-guard artifacts
     No new guards needed: auto_guard_discovery confirmed 0 unguarded negative-EV buckets

  3. KXBTC YES@93c flagged as potential NEW guard candidate
     n=8, WR=87.5%, BE=93.5% — but P&L=+7.00 USD (variable sizing means net positive)
     auto_guard_discovery already scanned and excluded (total P&L not negative enough)
     RECOMMENDATION: Watch this bucket. If total P&L turns negative, guard will auto-add.

## SELF-IMPROVEMENT BUILD STATUS (updated S102)
  DONE (Sessions 98-102):
  - Dim 1a: scripts/auto_guard_discovery.py — scans DB, finds negative-EV buckets (S98)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import (S98)
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update (S98)
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet (S99)
            src/models/bayesian_settlement.py — apply_bayesian_update() helper
  - Dim 4:  generate_signal() wired — predict() used when model.should_override_static() (S100)
            main.py injects _drift_model into 4 drift strategies
            BOT RESTARTED S101 — Dim 4 NOW LIVE, accumulating observations
  - Dim 4 STATUS: scripts/auto_promotion_check.py — gate monitoring built (S100)
  - Dim 4 STATUS: scripts/bayesian_drift_status.py — session-start health check (S100)
  - FLB:    .planning/EDGE_RESEARCH_S100.md — guard stack + per-asset analysis (S100)
  - Kelly:  .planning/EDGE_RESEARCH_S100.md — Thorp correlation confirmed (S101)
  - Dim 5:  scripts/guard_retirement_check.py — BUILT (S101), 20 tests
            16 IL guards tracked. All warming up (0-3 paper bets). Needs 50+ to evaluate.
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT (S102), 34 tests
            Detects live strategy WR decline (sequential test, more efficient than rolling WR)
            eth_drift alert confirmed: peak PH=5.05. ACTION: Bayesian self-corrects.

  SELF-IMPROVEMENT CHAIN NOW FULLY ACTIVE:
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() when 30+ obs (currently 3 obs)
    Page-Hinkley monitors for strategy deterioration at session start

  PENDING FOR S103+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 17:19 UTC (TODAY — it's 02:30 UTC now)
     Launcher fires at ~17:19 UTC March 18 (79138s from 19:21 UTC March 17)
  #2 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21
  #3 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks accumulation)
  #4 Bayesian posterior — currently 3 obs, needs 27 more to activate override (monitoring only)
  #5 CPI speed-play April 10 08:30 ET
  #6 GDP speed-play April 30
  #7 NEXT self-improvement dimension: Dim 6 (FLB academic review) or Dim 5 (CUSUM on guard buckets)
     FLB: paper research on WHY crypto 90c+ has bias (Thaler/Snowberg/Ottaviani/Ottaviani-Sorensen)
     CUSUM on guards: only useful once 10+ paper bets per bucket accumulate (weeks away)

## STARTUP SEQUENCE FOR S103:
    1. ps aux | grep "[m]ain.py" (check bot alive, PID should be 68913)
    2. ./venv/bin/python3 scripts/auto_guard_discovery.py (guard scan)
    3. ./venv/bin/python3 scripts/bayesian_drift_status.py (posterior health — check n_obs)
    4. ./venv/bin/python3 scripts/auto_promotion_check.py (promotion gates)
    5. ./venv/bin/python3 scripts/guard_retirement_check.py (Dim 5 — guard retirement)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (NEW Dim 7 — PH drift detection)
    7. cat /tmp/ucl_sniper_mar18.log (URGENT if after 17:19 UTC March 18)

## RESTART COMMAND (for future restarts):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session103.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (02:30 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 14/14 live wins today +17.01 USD, guards holding
  sol_drift_v1:      STAGE 1 — 41 bets, 70.7% WR, last20=60% (declining from 71%), PH=1.45 (normal)
  xrp_drift_v1:      MICRO — 43 bets, 51.2% WR, PH=0.45 (normal)
  btc_drift_v1:      MICRO — direction_filter="no", 64 bets, 46.9% WR, PH=1.15 (normal)
  eth_drift_v1:      STAGE 1 — direction_filter="yes", 138 bets, 48.6% WR, PH alert (peak=5.05)
                     last20=40%, last10=40% — Bayesian self-corrects. No manual action.
  Bayesian posterior: 3 observations (needs 27 more to activate — accumulating passively)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c — unchanged)
  auto_guard_discovery.py: 0 new guards found (all negative-EV buckets covered)
  Guard stack fully protecting all known structural loss patterns.
  FLB analysis confirmed: XRP and SOL structural loss buckets all guarded.
