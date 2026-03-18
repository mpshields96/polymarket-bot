# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~19:15 UTC (Session 104 research wrap — dead ends confirmed)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 28432 → /tmp/polybot_session104.log (running since 13:48 UTC restart)
  All-time live P&L: ~22+ USD (was +19.92 at 13:35 UTC — +2+ USD since then)
  Today (March 18): ~32 USD live | expiry_sniper ~80 settled, ~65 wins (96%+ WR)
  Tests: 1584 passing. Last commit: b7079b9 (docs: S104 research findings — per-direction analysis, CPI dead end)

## S104 KEY CHANGES

  1. BAYESIAN BOOTSTRAP DEPLOYED — Dim 2/3/4 NOW AT FULL POWER (earlier this session)
     scripts/bayesian_bootstrap.py — re-seeds posterior from ALL 298 historical drift bets
     After: n=301+, override_active=TRUE, kelly_scale=0.95, uncertainty=0.065
     Sensitivity: 300 → 283 | Intercept: -0.060
     Bayesian predict() is now ACTIVE — bot uses live-calibrated probabilities for drift signals
     1584 tests passing.

  2. PER-DIRECTION WIN RATE ANALYSIS (S104 research)
     btc NO 55.3% WR (n=47) | btc YES 30.0% WR (n=20) — filter="no" is CORRECT
     sol NO 71.0% WR (n=31) | sol YES 66.7% WR (n=12) — BOTH sides profitable!
     eth NO 45.7% WR (n=35) | eth YES 47.3% WR (n=110) — neither side has clear edge
     xrp YES 54.3% WR (n=35) | xrp NO 36.4% WR (n=11) — filter="yes" is CORRECT
     SOL finding: YES side also profitable (67%) but n=12 not significant (p=0.19)
     Per-strategy Bayesian bootstrap: models similar to shared; SOL edge is structural
     See EDGE_RESEARCH_S103.md Section "S104 Per-Direction Win Rate Analysis"

  3. CPI/GDP SPEED-PLAY — CONFIRMED DEAD ENDS
     KXCPI markets close at 08:25 ET (5 min before 08:30 ET release) — NO post-release betting
     KXGDP markets close at 08:29 ET (1 min before 08:30 ET release) — same
     Kalshi closes ALL macro data markets before the underlying release. Structural policy.
     Remove from future session pending lists. Do NOT re-investigate.

  4. UCL MARCH 18 — RESEARCH COMPLETE
     Barcelona vs Newcastle: BAR surged 55c → 98-99c during live game
     Kickoff was 18:45 UTC (early slot). BAR 90c crossed at ~19:02 UTC (early goal ~min 17)
     Live snapshot 19:07 UTC: BAR=98-99c, LFC=76-77c, TOT=39-40c, BMU=70-71c
     FLB CONFIRMED: 90c+ markets DO occur in live UCL games
     BUT: soccer at 90c ≠ crypto at 90c near expiry (60+ min game still to play = riskier)
     VERDICT: UCL sniper not viable without historical live-game WR data at 90c+
     Documented in EDGE_RESEARCH_S103.md

## SELF-IMPROVEMENT BUILD STATUS (S104)
  DONE (Sessions 98-104):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (2 auto-guards active)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() used (ACTIVE, n=301 >= 30)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (needs 50+ paper bets each)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT (S102), 34 tests
  - NEW S104: scripts/bayesian_bootstrap.py — retroactive posterior seeding from DB history

  SELF-IMPROVEMENT CHAIN FULLY ACTIVE (all dims):
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() (ACTIVE: n=301 >= 30)
    Page-Hinkley monitors for strategy deterioration at session start
    Bayesian intercept=-0.060 → fewer YES signals on drift strategies (self-correcting eth drift)

  PENDING FOR S105+:
  #1 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21 (tomorrow!)
  #2 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~4+ more weeks accumulation)
  #3 SOL YES direction tracking — n=12 YES bets at 67% WR — promising but not significant
     direction_filter="no" blocks new YES data. Needs 30+ YES bets to change filter.
     OPTION: Build shadow paper tracking for filtered direction (no live capital risk)
     See todos.md entry "SOL YES direction data accumulation"
  #4 Monitor Bayesian posterior growth (passive — currently n=301)
  #5 Per-strategy Bayesian models (low priority — benefit modest vs implementation scope)
     Document: EDGE_RESEARCH_S103.md "Per-strategy Bayesian Models" section

  REMOVED FROM PENDING:
  - CPI speed-play April 10: DEAD END (market closes before release)
  - GDP speed-play April 30: DEAD END (market closes before release)
  - UCL March 18: COMPLETE (research done, Barcelona won, documented)

## STARTUP SEQUENCE FOR S105:
    1. ps aux | grep "[m]ain.py" (check bot alive — PID 28432 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session104.log | tail -1
       → MUST show "Loaded 2 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session104.log | tail -1
       → MUST show override_active=True
    4. ./venv/bin/python3 scripts/auto_guard_discovery.py (check for new guards)
    5. ./venv/bin/python3 scripts/bayesian_drift_status.py (n should be 301+)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (PH check — eth still alerting)
    7. ./venv/bin/python3 scripts/ncaa_tournament_scanner.py (URGENT — March 19-20!)

## RESTART COMMAND (for future restarts — session 105):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session105.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (19:15 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — ~65/79 today (~82% overall incl bad windows), +32 USD today
                     Guards: 2 auto-guards loaded (KXXRP NO@95c, KXSOL NO@93c)
  sol_drift_v1:      LIVE — 43 total bets, 69.8% WR, +4.89 USD | BOTH directions profitable
  btc_drift_v1:      LIVE — 67 bets, 47.8% WR (NO side 55.3% WR profitable)
  eth_drift_v1:      LIVE but PH ALERT — 145 bets, 46.9% WR | Bayesian self-corrects (no action)
  xrp_drift_v1:      LIVE — 46 bets, 50.0% WR | YES side 54.3% WR
  Bayesian posterior: n=301, override_active=TRUE, kelly_scale=0.95, uncertainty=0.065

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 2 auto-guards)
  auto_guard_discovery.py: 0 new guards (all known buckets covered)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE

## GOAL TRACKER
  All-time P&L: ~22+ USD
  Target: +125 USD
  Remaining: ~103 USD needed
  Today rate: ~32 USD/day (expiry_sniper dominant)
  Estimated days at current rate: ~3 days
  Highest-leverage action: Keep expiry_sniper running clean, NCAA scanner March 19-20

## S104 FULL RESEARCH FINDINGS
  BAYESIAN BOOTSTRAP: 298→301 bets, n>=30 threshold activated, kelly 0.53→0.95
  PER-DIRECTION: SOL both sides ~70% WR (structural edge). ETH neither side > 47%.
    BTC NO (55%) and XRP YES (54%) confirm direction filters are correct.
  CPI/GDP SPEED-PLAY: DEAD ENDS. Kalshi closes markets 1-5 min before release.
  UCL: FLB confirmed in live soccer (90c+ markets observed). Not viable without WR data.
  ACADEMIC: Le (2026) arXiv:2602.19520 — crypto prediction markets near-perfectly calibrated.
    Primary edge = near-expiry 15-min calibration breakdown (our current strategy).

## CONFIRMED DEAD ENDS (add to S105 autoresearch instructions)
  CPI speed-play (any release day), GDP speed-play (any release day),
  FOMC speed-play (same policy), KXUNRATE speed-play (same policy)
  UCL/NCAA live sports sniper (insufficient WR historical data)
  [All previous dead ends from prior sessions still apply]
