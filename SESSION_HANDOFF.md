# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~12:35 UTC (Session 103 monitoring wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 14095 → /tmp/polybot_session103.log (running since 05:18 UTC S103)
  All-time live P&L: +12.67 USD (was +13.67 at S102 wrap — dipped then recovered)
  Today (March 18): +23.72 USD live (66 settled, 78% overall WR) | expiry_sniper 52/54 wins
  Tests: 1565 passing. Last commit: 859cee1 (docs: S103 research wrap)

## S103 KEY CHANGES (monitoring wrap — overnight session)

  1. TWO LARGE SNIPER LOSSES — auto-guarded, now blocked permanently
     04:17 UTC: KXXRP NO@95c — LOST -19.95 USD (market resolved YES unexpectedly)
     05:16 UTC: KXSOL NO@93c — LOST -19.53 USD (market resolved YES unexpectedly)
     TOTAL LOSS: -39.48 USD from two bets
     RECOVERY: +52.15 USD won back by 12:35 UTC (3 hours later)
     AUTO-GUARD RESPONSE (Dim 1 self-improvement worked):
       - KXXRP NO@95c guard discovered/written at 04:17 UTC (n=19, 94.7% WR, BE=95.3%)
       - KXSOL NO@93c guard discovered/written at 05:18 UTC (n=12, 91.7% WR, BE=93.4%)
       - PID 14095 (current bot) loaded BOTH guards at startup — neither bucket will fire again
     LESSON: After any restart, grep startup log for "Loaded N auto-discovered guard(s)" — N should
       match len(data/auto_guards.json guards). If N=1 but file has 2, auto_guard_discovery needed.

  2. Bot daemon watchdog (polybot_daemon.py PID 47620) handled 3 restarts autonomously
     PID 68913 → 9655 (04:18 UTC) → 14095 (05:18 UTC)
     Daemon restarts with --reset-soft-stop to /tmp/polybot_session103.log
     Daemon is running and healthy — no action needed.

  3. Guard stack: NOW 2 active auto-guards (up from 1 at session start)
     auto_guard_discovery.py confirms: 0 additional guards needed

  4. UCL launcher: fires 17:21 UTC March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC
     Currently sleeping (confirmed sleeping at 12:35 UTC)

## SELF-IMPROVEMENT BUILD STATUS (unchanged from S102)
  DONE (Sessions 98-102):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (discovered 2 guards this session)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() used when model.should_override_static()
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (needs 50+ paper bets each)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT (S102), 34 tests

  SELF-IMPROVEMENT CHAIN FULLY ACTIVE:
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() when 30+ obs (currently n=4+)
    Page-Hinkley monitors for strategy deterioration at session start

  PENDING FOR S104+:
  #1 UCL March 18 — check /tmp/ucl_sniper_mar18.log after 20:00 UTC (URGENT TODAY)
  #2 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21
  #3 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks accumulation)
  #4 Bayesian posterior — n=4+, needs ~26 more to activate (passive accumulation)
  #5 CPI speed-play April 10 08:30 ET
  #6 GDP speed-play April 30

## STARTUP SEQUENCE FOR S104:
    1. ps aux | grep "[m]ain.py" (check bot alive — expect PID 14095 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session103.log | tail -1
       → MUST show "Loaded 2 auto-discovered guard(s)" — if only 1, run auto_guard_discovery.py
    3. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new guards)
    4. ./venv/bin/python3 scripts/bayesian_drift_status.py (posterior health)
    5. ./venv/bin/python3 scripts/strategy_drift_check.py (PH drift check)
    6. cat /tmp/ucl_sniper_mar18.log (URGENT if after 17:21 UTC March 18)

## RESTART COMMAND (for future restarts — session 104):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session104.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (12:35 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 75 live bets total, 52/54 today, +23.72 USD today
                     All-time sniper cumulative: +306.69 USD paper equiv
                     Guards: 2 auto-guards loaded (KXXRP NO@95c, KXSOL NO@93c)
  sol_drift_v1:      READY FOR LIVE — 41 bets, 70.7% WR, +3.84 USD, Brier 0.196
  btc_drift_v1:      READY FOR LIVE — 65 bets, Brier 0.250, -12.13 USD (direction_filter="no")
  eth_drift_v1:      READY FOR LIVE but BLOCKED — 144 bets, Brier 0.250, -26.34 USD
                     4 consecutive losses at graduation check. Bayesian self-corrects.
  xrp_drift_v1:      READY FOR LIVE — 45 bets, Brier 0.265, -2.50 USD
  Bayesian posterior: n=4+ observations (passive accumulation, 26+ more to activate)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 2 auto-guards)
  auto_guard_discovery.py: 0 new guards (all negative-EV buckets covered)
  NEW THIS SESSION:
    KXXRP NO@95c: n=19, 94.7% WR (need 95.3%) — ACTIVE in PID 14095
    KXSOL NO@93c: n=12, 91.7% WR (need 93.4%) — ACTIVE in PID 14095
  Guard stack protecting all known structural loss patterns.

## GOAL TRACKER
  All-time P&L: +12.67 USD
  Target: +125 USD
  Remaining: 112.33 USD needed
  Today rate: +23.72 USD/day (expiry_sniper dominant engine)
  Estimated days at current rate: ~5 days (high variance — single loss day resets progress)
  Highest-leverage action: Keep expiry_sniper running clean, add any new negative-EV guards daily
