# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~19:30 UTC (Session 104 monitoring wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 28432 → /tmp/polybot_session104.log (running since 13:48 UTC restart)
  All-time live P&L: +23.50 USD
  Today (March 18): +34.55 USD live (80 settled, 78% WR) | expiry_sniper 60/62 (96.8% WR)
  Tests: 1584 passing. Last commit: 56648e7 (docs: CPI agent addendum)

## S104 MONITORING WRAP KEY EVENTS

  1. BOT DEAD ON ARRIVAL — restarted clean
     Bot PID 14095 and daemon were both dead at session start.
     Restarted with session 104 log → PID 21755 → daemon cycles → settled at PID 28432.
     Guards confirmed loaded: "Loaded 2 auto-discovered guard(s)" on startup.
     Root cause of death: previous session daemon died with no watchdog to restart it.

  2. UCL IN-PLAY SNIPER HYPOTHESIS CONFIRMED (research data)
     Barcelona vs Newcastle: BAR moved 47c (pre-game) → 74c (~18:36 UTC, early goal)
     → 99c by 19:20 UTC (game clinched). Active 90c+ hit confirmed.
     Volume: 5.29M contracts (10-100x crypto sniper depth).
     Kalshi updated BEFORE ESPN registered game as "live" — faster data source.
     Documented in /tmp/ucl_research_notes.md and /tmp/ucl_sniper_mar18.log.
     VERDICT: UCL sniper viable in principle but insufficient historical WR data to build yet.
     20:00 UTC games (Man City vs Real Madrid, Chelsea vs PSG, Arsenal vs Leverkusen) not
     yet resolved — UCL monitor (PID 34968) still running to capture them.

  3. P&L performance
     S103 wrap: +12.67 USD all-time. S104 monitoring wrap: +23.50 USD. Gain: +10.83 USD.
     Sniper: 60/62 today (96.8%), +36.09 USD. eth_drift drag: 2/9 today (-2.12 USD).

  4. Monitoring loop ran 3 complete cycles (PID tracking fix applied after cycle 1).

## SELF-IMPROVEMENT BUILD STATUS (unchanged from S104 research wrap)
  DONE (Sessions 98-104):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (2 auto-guards active)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() ACTIVE (n=301 >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (50+ paper bets needed)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT (S102), 34 tests
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding (n=4→301)

  SELF-IMPROVEMENT CHAIN FULLY ACTIVE:
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() (ACTIVE: n=301 >= 30)
    Page-Hinkley monitors for strategy deterioration at session start

  PENDING FOR S105+:
  #1 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21 (TOMORROW — URGENT)
  #2 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks)
  #3 SOL YES direction tracking — n=12 YES bets at 67% WR (promising, not significant yet)
  #4 Monitor Bayesian posterior growth (passive — currently n=301)
  #5 UCL 20:00 UTC games — check /tmp/ucl_sniper_mar18.log for Man City/Chelsea/Arsenal data

  CONFIRMED DEAD ENDS (do NOT re-investigate):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper without WR data,
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  non-crypto 90c+ markets, one-off market scanners

## STARTUP SEQUENCE FOR S105:
    1. ps aux | grep "[m]ain.py" (expect PID 28432 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session104.log | tail -1
       → MUST show "Loaded 2 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session104.log | tail -1
       → MUST show override_active=True (Bayesian is ACTIVE at n=301)
    4. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new)
    5. ./venv/bin/python3 scripts/bayesian_drift_status.py (n should be 301+)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (eth still alerting — no action needed)
    7. ./venv/bin/python3 scripts/ncaa_tournament_scanner.py (URGENT — March 19-20!)
    8. cat /tmp/ucl_sniper_mar18.log | grep "90c+" (check 20:00 UTC game results)

## RESTART COMMAND (for future restarts — session 105):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session105.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (19:30 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 62 settled today, 60 wins (96.8%), +36.09 USD today
                     Guards: 2 auto-guards loaded (KXXRP NO@95c, KXSOL NO@93c)
  sol_drift_v1:      LIVE Stage 1 — 43 total bets, 70% WR, +4.89 USD
  btc_drift_v1:      LIVE Stage 1 — 67 bets, 48% WR (NO side 55% WR), direction_filter="no"
  eth_drift_v1:      LIVE but PH ALERT — 145 bets, 47% WR, BLOCKED 5 consec. Bayesian corrects.
  xrp_drift_v1:      LIVE micro — 46 bets, 50% WR, YES side 54%, direction_filter="yes"
  Bayesian posterior: n=301, override_active=TRUE, kelly_scale=0.95, uncertainty=0.065

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 2 auto-guards)
  auto_guard_discovery.py: 0 new guards (all known buckets covered)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE

## GOAL TRACKER
  All-time P&L: +23.50 USD
  Target: +125 USD
  Remaining: 101.50 USD needed
  Today rate: +34.55 USD/day (sniper dominant)
  Estimated days at current rate: ~3 days
  Highest-leverage action: Keep expiry_sniper running clean, add guards daily if new buckets appear
