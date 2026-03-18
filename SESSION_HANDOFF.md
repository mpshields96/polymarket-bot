# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 00:30 UTC (Session 100 research — Dims 4+5+FLB complete)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 50882 → /tmp/polybot_session98.log (bot still using S98 log)
  All-time live P&L: -9.37 USD (improved from -16.51 at S99 end, +7.14 gained S100)
  Tests: 1511 passing. Last commit: 69ea04c (auto_promotion_check + FLB research)

## S100 KEY CHANGES (committed and deployed, bot NOT restarted)

NOTE: Bot was NOT restarted this session. New code (Dim 4 injection) will activate on
next restart. Currently running S98 binary. Core self-improvement is active via S99 wiring.

  1. src/strategies/btc_drift.py — Dim 4 COMPLETE
     self._drift_model = None added to __init__
     generate_signal() step 6: if model.should_override_static() (30+ obs),
       raw_prob = self._drift_model.predict(pct_from_open) replaces static sigmoid
     Time adjustment still applied after Bayesian raw_prob (both paths identical downstream)
     Commits: ae869fe (btc_drift.py + test) + 7705ff3 (main.py injection)

  2. main.py — Bayesian model injected into all 4 drift strategies after strategy load
     After: drift_strategy, eth_drift_strategy, sol_drift_strategy, xrp_drift_strategy
     all receive _drift_model via ._drift_model attribute injection

  3. scripts/bayesian_drift_status.py — session-start health check for posterior
     Shows: n_obs, sensitivity shift from prior (300), intercept bias, uncertainty
     reduction, kelly_scale, DB cross-check. Exit 0 = active, Exit 1 = warming up.
     Commit: 65e069e

  4. scripts/auto_promotion_check.py — Dim 4 of SELF_IMPROVEMENT_ROADMAP.md
     Gates: n>=20, Brier<0.30, WR>break-even, no directional asymmetry (if 2-sided)
     Brier from live bets (paper trades have NULL win_prob). Reminders alert if ready.
     Currently: no strategies ready. eth_orderbook_imbalance_v1 at Brier=0.337 (need <0.30)
     Commit: 69ea04c

  5. .planning/EDGE_RESEARCH_S100.md — FLB structural analysis from 653 live sniper bets
     Key findings:
       - Profit zone 90-95c confirmed valid. Above 95c: fee math kills edge structurally.
       - BTC(+87) > ETH(+84) > SOL(+60) > XRP(-30 USD at 90-95c, all losses guarded).
       - 08:00 UTC losses = pre-guard artifact CONFIRMED. All 5 losses in guarded buckets.
       - Time-of-day guard STILL dead end. Do NOT add.

  6. tests/test_bayesian_drift_wiring.py — 14 new tests for Dim 4 (1511 total)
     Commit: ae869fe

## SELF-IMPROVEMENT BUILD STATUS (updated S100 end)
  DONE (Sessions 98-100):
  - Dim 1a: scripts/auto_guard_discovery.py — scans DB, finds negative-EV buckets (S98)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import (S98)
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update (S98)
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet (S99)
            src/models/bayesian_settlement.py — apply_bayesian_update() helper
  - Dim 4:  generate_signal() wired — predict() used when model.should_override_static() (S100)
            main.py injects _drift_model into 4 drift strategies
  - Dim 4 STATUS: scripts/auto_promotion_check.py — gate monitoring built (S100)
  - Dim 4 STATUS: scripts/bayesian_drift_status.py — session-start health check (S100)
  - FLB:    .planning/EDGE_RESEARCH_S100.md — validated guard stack, per-asset analysis (S100)

  SELF-IMPROVEMENT CHAIN COMPLETE:
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() when 30+ obs (after next restart)

  PENDING FOR S101+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC (URGENT tonight)
  #2 NCAA Round 1 — re-scan March 19-20 for Round 1 tip-offs March 20-21
  #3 Guard retirement script (Dim 5) — build when 4+ weeks post-guard paper data accumulates
     Currently 0-1 paper bets per guarded bucket — insufficient for statistical retirement test
  #4 Kelly for correlated bets (Thorp 2006) — test our DB for loss clustering in same window
  #5 Drift detection for guard bucket health (CUSUM / Page-Hinkley test on rolling WR)
  #6 CPI speed-play April 10 08:30 ET
  #7 GDP speed-play April 30
  #8 Restart bot to activate Dim 4 (Bayesian predict in generate_signal) — NEEDED before
     the model can override static sigmoid. Currently bot runs S98 binary without Dim 4.

## RESTART COMMAND (activate Dim 4):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session101.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (00:20 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — guards holding, 2 bets/2 wins +1.68 USD today
  sol_drift_v1:      STAGE 1 — 41 bets, 71% WR, +3.84 USD
  xrp_drift_v1:      MICRO — 42 bets, 50% WR, -1.76 USD
  btc_drift_v1:      MICRO — direction_filter="no", 64 bets
  eth_drift_v1:      MICRO — direction_filter="yes", 136 bets

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c — unchanged S100)
  auto_guard_discovery.py: 0 new guards found (all negative-EV buckets covered)
  Guard stack fully protecting all known structural loss patterns.

## COPY-PASTE THIS TO START SESSION 101
  Read SESSION_HANDOFF.md then use /polybot-autoresearch (research) or /polybot-auto (monitoring)
  STARTUP SEQUENCE:
    1. ps aux | grep "[m]ain.py" (check bot alive)
    2. ./venv/bin/python3 scripts/auto_guard_discovery.py (guard scan)
    3. ./venv/bin/python3 scripts/bayesian_drift_status.py (posterior health — NEW S100)
    4. ./venv/bin/python3 scripts/auto_promotion_check.py (promotion gates — NEW S100)
    5. Restart bot if needed to activate Dim 4 Bayesian wiring
  Then pick next task from PENDING list above.
