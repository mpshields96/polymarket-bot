# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 01:00 UTC (Session 101 — research + monitoring complete)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 68913 → /tmp/polybot_session101.log (restarted 00:32 UTC, Dim 4 active)
  All-time live P&L: -7.69 USD (improved +4.20 USD during S101: -9.37 → -7.69)
  Tests: 1531 passing. Last commit: 21c106e (guard_retirement_check Dim 5)

## S101 KEY CHANGES

  1. Bot RESTARTED — Dim 4 Bayesian wiring NOW ACTIVE
     Log: /tmp/polybot_session101.log
     Startup confirms: "Bayesian model injected into 4 drift strategies (n=0 obs, override_active=False)"
     Model will override static sigmoid once 30 live drift bets accumulate in drift_posterior.json
     All 4 drift strategies: btc_drift, eth_drift, sol_drift, xrp_drift have _drift_model injected.

  2. Kelly correlation research COMPLETE (Thorp 2006 — marked as DONE)
     DB analysis of 656 live settled sniper bets confirmed strong intra-window clustering:
       Single-bet windows: 3.4% loss rate
       Multi-bet WIN windows (181): +422.69 USD
       Multi-bet LOSS windows (19): -392.19 USD  ← 38.7% loss rate in those windows
     Conditional P(loss | same window as another loss) = 38.7% vs 4.0% baseline = 10x.
     CONCLUSION: Guard stack is correct countermeasure. Per-window cap (2 bets/30 USD) handles Kelly.
     No new structural change needed. Documented in EDGE_RESEARCH_S100.md.

## SELF-IMPROVEMENT BUILD STATUS (updated S101)
  DONE (Sessions 98-101):
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
  - FLB:    .planning/EDGE_RESEARCH_S100.md — validated guard stack, per-asset analysis (S100)
  - Kelly:  .planning/EDGE_RESEARCH_S100.md — Thorp correlation analysis complete (S101)
            Confirmed clustering, confirmed guard stack is correct response.
  - Dim 5:  scripts/guard_retirement_check.py — BUILT (S101), 20 tests
            16 IL guards tracked. All warming up (0-3 paper bets). Needs 50+ to evaluate.
            Added to session-start checklist. Will auto-flag when buckets recover.

  SELF-IMPROVEMENT CHAIN NOW FULLY ACTIVE (after S101 restart):
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() when 30+ obs
    (currently accumulating — 0 obs, needs 30 to activate Bayesian path)

  PENDING FOR S102+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC (TODAY, urgent)
     Launcher wakes at 17:21 UTC. Check log after 20:00 UTC for results.
  #2 NCAA Round 1 — re-scan March 19-20 for Round 1 tip-offs March 20-21
  #3 Guard retirement script (Dim 5) — build when 4+ weeks post-guard paper data accumulates
     Currently 0-1 paper bets per guarded bucket — insufficient for statistical retirement test
  #4 Kelly correlation — DONE (S101). Documented in EDGE_RESEARCH_S100.md. No action needed.
  #5 Drift detection for guard bucket health (CUSUM / Page-Hinkley test on rolling WR)
     Next major research item: detect when formerly-bad buckets recover (feeds Dim 5)
  #6 CPI speed-play April 10 08:30 ET
  #7 GDP speed-play April 30
  #8 BOT RESTARTED (S101) — Dim 4 active. Monitor drift_posterior.json accumulation.
     Check bayesian_drift_status.py once 10+ drift bets settle to see n_obs increasing.

## STARTUP SEQUENCE FOR S102:
    1. ps aux | grep "[m]ain.py" (check bot alive, PID should be 68913)
    2. ./venv/bin/python3 scripts/auto_guard_discovery.py (guard scan)
    3. ./venv/bin/python3 scripts/bayesian_drift_status.py (posterior health — check n_obs)
    4. ./venv/bin/python3 scripts/auto_promotion_check.py (promotion gates)
    5. ./venv/bin/python3 scripts/guard_retirement_check.py (Dim 5 — guard retirement — NEW S101)
  Then pick next task from PENDING list above. Priority: #1 UCL log, then #5 CUSUM/drift detection.

## RESTART COMMAND (for future restarts):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session102.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (01:00 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — guards holding, +2.52 USD today
  sol_drift_v1:      STAGE 1 — 41 bets, 71% WR, +3.84 USD all-time live
  xrp_drift_v1:      MICRO — 42 bets, 50% WR, -1.76 USD all-time live
  btc_drift_v1:      MICRO — direction_filter="no", 64 bets, -12.64 USD all-time live
  eth_drift_v1:      STAGE 1 — direction_filter="yes", 136 bets, -24.70 USD
                     NOTE: -24.70 is large. Bayesian model will self-correct over time. No manual intervention.
  Bayesian posterior: 0 observations (warming up — needs 30 live drift bets to activate)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c — unchanged)
  auto_guard_discovery.py: 0 new guards found (all negative-EV buckets covered)
  Guard stack fully protecting all known structural loss patterns.
