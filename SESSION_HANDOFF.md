# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~13:35 UTC (Session 104 research — Bayesian bootstrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 25008 → /tmp/polybot_session104.log (running since 13:26 UTC S104)
  All-time live P&L: +19.92 USD (was +12.67 at S103 wrap — +7.25 USD since)
  Today (March 18): ~27.90 USD live | expiry_sniper 54/56 wins (96% WR)
  Tests: 1584 passing. Last commit: 9ead390 (feat: Bayesian posterior bootstrap)

## S104 KEY CHANGES (research session — Bayesian bootstrap built)

  1. BAYESIAN BOOTSTRAP DEPLOYED — Dim 2/3/4 NOW AT FULL POWER
     scripts/bayesian_bootstrap.py — re-seeds posterior from ALL 298 historical drift bets
     Before: n=15, override_active=False, kelly_scale=0.53, uncertainty=0.64
     After:  n=298, override_active=TRUE, kelly_scale=0.95, uncertainty=0.066
     Sensitivity: 300 → 280 (live markets slightly less responsive to drift)
     Intercept:  -0.077 → -0.089 (bearish bias confirmed — consistent with eth YES losses)
     Uncertainty reduction: 94% (from 0.64 → 0.066)
     Bayesian predict() is now ACTIVE — bot uses live-calibrated probabilities for drift signals
     16 new tests added. 1584/1584 passing.
     CAUTION: Only run bootstrap again if posterior is corrupted (settlement_loop maintains it now)

  2. NCAA SCANNER RUN (March 18 13:18 UTC)
     86 Kalshi NCAAB markets open, 40 Odds API games
     No opportunities above 3% edge threshold
     Re-run March 19-20 as tip-offs approach (Round 1: March 20-21)

  3. eth_drift PH ALERT — SUSTAINED (no action per PRINCIPLES.md)
     PH=5.00 (threshold=4.0). WR last20=30.0%, last10=20.0%. Today: 2/9 = 22%
     Bayesian intercept now captures this (-0.089) — model will reduce YES bet frequency
     Bayesian predict() active — self-corrects without manual intervention

  4. UCL MONITOR — background watching /tmp/ucl_sniper_mar18.log
     UCL launcher fires at 17:21 UTC March 18
     Background monitor running → /tmp/ucl_monitor_output.txt
     Check /tmp/ucl_sniper_mar18.log after 20:00 UTC

## SELF-IMPROVEMENT BUILD STATUS (S104)
  DONE (Sessions 98-104):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (2 auto-guards active)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() used (now ACTIVE, n=298 >= 30)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (needs 50+ paper bets each)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT (S102), 34 tests
  - NEW S104: scripts/bayesian_bootstrap.py — retroactive posterior seeding from DB history

  SELF-IMPROVEMENT CHAIN FULLY ACTIVE (all dims):
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() (ACTIVE: n=298 >= 30)
    Page-Hinkley monitors for strategy deterioration at session start
    Bayesian intercept=-0.089 → fewer YES signals on drift strategies (self-correcting eth drift)

  PENDING FOR S105+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC (URGENT TODAY)
  #2 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21
  #3 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks accumulation)
  #4 Monitor Bayesian override effects on drift strategy signal frequency (passive)
  #5 CPI speed-play April 10 08:30 ET — research KXCPI markets
  #6 GDP speed-play April 30

## STARTUP SEQUENCE FOR S105:
    1. ps aux | grep "[m]ain.py" (check bot alive — PID 25008 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session104.log | tail -1
       → MUST show "Loaded 2 auto-discovered guard(s)"
    3. grep "override_active=True\|n=298\|n=[0-9]" /tmp/polybot_session104.log | tail -3
       → MUST show override_active=True and n>=298
    4. ./venv/bin/python3 scripts/auto_guard_discovery.py (check for new guards)
    5. ./venv/bin/python3 scripts/bayesian_drift_status.py (n should be 298+)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (PH check)
    7. cat /tmp/ucl_sniper_mar18.log (URGENT if after 17:21 UTC)
    8. ./venv/bin/python3 scripts/ncaa_tournament_scanner.py (if March 19-20)

## RESTART COMMAND (for future restarts — session 105):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session105.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (13:35 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 54/56 today (96% WR), +27.90 USD today
                     Guards: 2 auto-guards loaded (KXXRP NO@95c, KXSOL NO@93c)
  sol_drift_v1:      LIVE — 1/1 today +5.85 USD (total 42 bets, 71.4% WR)
  btc_drift_v1:      LIVE — 1/2 today +0.08 USD (total 66 bets, 47.0% WR)
  eth_drift_v1:      LIVE but PH ALERT — 2/9 today -2.12 USD | Bayesian self-corrects
  xrp_drift_v1:      LIVE — 1/3 today -0.74 USD (total 45 bets, 51.1% WR)
  Bayesian posterior: n=298, override_active=TRUE (ACTIVATED THIS SESSION)
                      kelly_scale=0.95, sensitivity=280, intercept=-0.089

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 2 auto-guards)
  auto_guard_discovery.py: 0 new guards (all known buckets covered)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE

## GOAL TRACKER
  All-time P&L: +19.92 USD
  Target: +125 USD
  Remaining: 105.08 USD needed
  Today rate: ~27.90 USD/day (expiry_sniper dominant)
  Estimated days at current rate: ~4 days
  Highest-leverage action: Keep expiry_sniper running clean, monitor Bayesian effects on drift

## S104 RESEARCH FINDINGS
  BAYESIAN BOOTSTRAP (key finding):
    Historical bets pre-date Dim 3 wiring (S99). win_prob stored in DB enables retroactive
    sigmoid inversion: drift_pct ≈ logit(win_prob) / sensitivity.
    This gives same informative MAP gradient steps as real-time updates.
    298 historical bets processed → immediate Bayesian activation.
    Intercept=-0.089 reflects sustained ETH YES losses — model will now correctly
    reduce YES-side signal probability, reducing false YES signals automatically.
    Kelly scale 0.53 → 0.95: bot was being too conservative due to small n; now confident.

  DEAD END (confirmed March 18): NCAA Round 1 at current (March 18) has no edges > 3%.
    Re-run March 19-20 — edges appear as spread consensus tightens near tip-off.
