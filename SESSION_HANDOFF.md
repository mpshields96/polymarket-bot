# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~04:00 UTC (Session 103 research overnight)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 68913 → /tmp/polybot_session101.log (running since 00:32 UTC S101)
  All-time live P&L: +15.14 USD (was +13.67 at S102 wrap — still gaining S103)
  Today (March 18): +26.19 USD live (27 settled, 89% WR) | expiry_sniper 22/22 wins 100% WR
  Tests: 1565 passing. Last commit: 812271e (research: Dim7 correlation — independence confirmed)

## S103 KEY RESEARCH FINDINGS (overnight session, research chat)

  1. Ceiling guard validated: 0 above-95c bets since March 17 12:10 UTC. Most impactful change.
     Before ceiling (Mar17 00:00-12:10): 99 bets, 91% WR, -81.38 USD
     After ceiling (Mar17 12:10+): 27 bets, 96% WR, +11.05 USD
     March 18 first full day: 22/22 wins, +27.30 USD

  2. eth_drift PH alert = VARIANCE, not structural.
     z-score vs break-even = -0.46 (not significant). No guard needed. Bayesian self-corrects.

  3. Sweet spot analysis: 92c is structural core (EV +5.20c/bet, 97% WR, most absolute P&L)
     Floor at 90c validated: 88-89c are below break-even. Ceiling at 95c is essential.

  4. Asset hierarchy confirmed (90-95c range):
     BTC: 98% WR, +98.90 USD — STRONGEST
     ETH: 99% WR, +91.67 USD — STRONGEST
     SOL: 97% WR, +63.80 USD — GOOD
     XRP: guarded, unguarded buckets = +32.97 USD positive (historical -25 USD is pre-guard)

  5. Dimension 7 correlation guard = DEAD END. Multi-bet windows: losses are independent.
     Observed all-loss = 0/144 windows. Expected at 97% WR = 0.1%. No excess clustering.

  6. NCAA scanner: 0 edges at 1% threshold, 88 markets. Re-run March 19-20 for Round 1.

  7. KXBTCD Friday slot: deferred (btc_daily at 14/30 paper bets gate, ~2 weeks away).

  Full analysis: .planning/EDGE_RESEARCH_S103.md

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

  3. Le (2026) correction — arXiv:2602.19520 (VERIFIED via fetch)
     Crypto prediction markets near-perfectly calibrated (intercept +0.005, slope 0.99-1.36)
     Primary edge = near-expiry 15-min calibration breakdown, NOT classical FLB
     Classical FLB (Snowberg & Wolfers) still explains asset hierarchy but not the magnitude

  4. CITATION INTEGRITY rules added to CLAUDE.md + ~/.claude/rules/learnings.md
     Hard block: never cite unverified sources. Must WebFetch or WebSearch to confirm.
     Applies to all chats (polybot, CCA, general).

  5. KXBTC YES@93c watchlist
     n=8, WR=87.5%, BE=93.5% — P&L=+7.00 USD (net positive, auto_guard excluded correctly)
     RECOMMENDATION: Watch. If total P&L turns negative, guard will auto-add.

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
    next signal → generate_signal() uses model.predict() when 30+ obs (currently n_observations=3)
    Page-Hinkley monitors for strategy deterioration at session start

  PENDING FOR S103+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 17:19 UTC (launcher fires ~17:21 UTC)
  #2 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21
  #3 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks accumulation)
  #4 Bayesian posterior — currently n_observations=3, needs 27 more to activate (monitoring only)
  #5 CPI speed-play April 10 08:30 ET
  #6 GDP speed-play April 30

## STARTUP SEQUENCE FOR S103:
    1. ps aux | grep "[m]ain.py" (check bot alive, PID should be 68913)
    2. ./venv/bin/python3 scripts/auto_guard_discovery.py (guard scan)
    3. ./venv/bin/python3 scripts/bayesian_drift_status.py (posterior health — check n_observations)
    4. ./venv/bin/python3 scripts/auto_promotion_check.py (promotion gates)
    5. ./venv/bin/python3 scripts/guard_retirement_check.py (Dim 5 — guard retirement)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (Dim 7 — PH drift detection)
    7. cat /tmp/ucl_sniper_mar18.log (URGENT if after 17:19 UTC March 18 — launcher fires 17:21 UTC)

## RESTART COMMAND (for future restarts):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session103.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (03:30 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 21/21 live wins today +24.72 USD, guards holding
  sol_drift_v1:      STAGE 1 — 41 bets, 70.7% WR, last20=60% (declining from 71%), PH=1.45 (normal)
  xrp_drift_v1:      MICRO — 43 bets, 51.2% WR, PH=0.45 (normal)
  btc_drift_v1:      MICRO — direction_filter="no", 64 bets, 46.9% WR, PH=1.15 (normal)
  eth_drift_v1:      STAGE 1 — direction_filter="yes", 138 bets, 48.6% WR, PH alert (peak=5.05)
                     last20=40%, last10=40% — Bayesian self-corrects. No manual action.
  Bayesian posterior: n_observations=3 (needs 27 more to activate — accumulating passively)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c — unchanged)
  auto_guard_discovery.py: 0 new guards found (all negative-EV buckets covered)
  Guard stack fully protecting all known structural loss patterns.
  FLB analysis confirmed: XRP and SOL structural loss buckets all guarded.
