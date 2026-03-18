# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~22:15 UTC (Session 105 monitoring wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 2502 → /tmp/polybot_session105.log (running since 21:25 UTC restart)
  All-time live P&L: +12.95 USD
  Today (March 18): +24.00 USD live (95 settled, 68/71 sniper wins 95.8% WR)
  Tests: 1605 passing. Last commit: e886a1a (feat: universal bet analytics framework)

## S105 MONITORING WRAP KEY EVENTS

  1. BOT DEAD ON ARRIVAL — restarted clean in <30s
     Bot PID 28432 from S104 was dead at session start.
     Restarted → PID 2502. Guards confirmed: "Loaded 3 auto-discovered guard(s)".

  2. NEW AUTO-GUARD: KXBTC YES@94c
     auto_guard_discovery.py identified KXBTC YES@94c as negative-EV bucket:
     n=13 bets, 92.3% WR vs 94.4% break-even, -9.94 USD cumulative.
     This was the bucket that caused the S104 -19.74 USD loss (id=3756, placed 19:57 UTC).
     Guard is now active. That loss bucket is permanently blocked.
     Auto-guards active: KXXRP NO@95c + KXSOL NO@93c + KXBTC YES@94c (3 total).

  3. bet_analytics.py CONFIRMED (CCA-built, already in repo)
     Running bet_analytics.py on live data produced statistically clean findings:
     expiry_sniper: EDGE CONFIRMED (SPRT lambda=+17.2, Brier=0.039)
     sol_drift:     EDGE CONFIRMED (SPRT lambda=+2.886, just crossed threshold at n=43)
     eth_drift:     NO EDGE DETECTED (SPRT lambda=-3.707) + DRIFT ALERT (CUSUM S=14.1)
     btc_drift:     collecting data (CUSUM approaching threshold S=4.48)
     xrp_drift:     collecting data (CUSUM stable S=2.82)
     Research chat added 24 tests for bet_analytics.py (commit e886a1a).

  4. STANDING DIRECTIVE: NO TRAUMA BUILDS
     Matthew corrected Claude for framing the eth_drift SPRT finding as "pause decision".
     The correct response: SPRT/CUSUM findings are OBSERVATIONS. Bayesian handles response.
     No manual parameter changes without: structural basis + 30+ data + DB backtest + p-value.
     Directive written to all 3 chat skill files and POLYBOT_TO_CCA.md.

  5. CCA COMMUNICATION LOOP added to polybot-auto.md
     Every monitoring cycle now checks CCA_TO_POLYBOT.md and writes to POLYBOT_TO_CCA.md.

  6. P&L: +24.00 USD live today. Sniper 68/71 = 95.8% WR. eth_drift drag: 3/13 = 23% (-2.74 USD).
     All-time: +12.95 USD (recovering from S104 late losses).

## SELF-IMPROVEMENT BUILD STATUS
  DONE (Sessions 98-105):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (3 auto-guards active)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() ACTIVE (n=305+ >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (50+ paper bets needed)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT, 34 tests
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding (n=4→301)
  - S105:   scripts/bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM (24 tests, CONFIRMED)

  SELF-IMPROVEMENT CHAIN FULLY ACTIVE:
    live bet → settle → settlement_loop → BayesianDriftModel.update() → drift_posterior.json
    next signal → generate_signal() uses model.predict() (ACTIVE: n=305+ >= 30)
    Page-Hinkley monitors for strategy deterioration at session start
    auto_guard_discovery.py: blocks new negative-EV sniper buckets at startup

## PENDING FOR S106+:
  #1 NCAA Round 1 — re-scan March 19-20 for tip-offs March 20-21 (URGENT if date passed)
  #2 UCL 20:00 UTC games — check /tmp/ucl_sniper_mar18.log (Man City/Chelsea/Arsenal)
  #3 sol_drift graduation watch — SPRT confirmed edge at n=43. Watch for Stage 2 criteria.
  #4 eth_drift monitoring — SPRT says no edge, Bayesian self-corrects. NO MANUAL ACTION.
  #5 btc_drift CUSUM approaching threshold (S=4.48/5.0) — monitor, do not act prematurely
  #6 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~3+ more weeks)
  #7 CCA communication — check CCA_TO_POLYBOT.md at every session start

  CONFIRMED DEAD ENDS (do NOT re-investigate):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper without WR data,
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  non-crypto 90c+ markets, one-off market scanners, btc_drift YES side (30% WR, -30 USD)

## STARTUP SEQUENCE FOR S106:
    1. ps aux | grep "[m]ain.py" (expect PID 2502 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session105.log | tail -1
       → MUST show "Loaded 3 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session105.log | tail -1
       → MUST show override_active=True (Bayesian ACTIVE at n=305+)
    4. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new)
    5. ./venv/bin/python3 scripts/bet_analytics.py (confirm SPRT findings unchanged)
    6. ./venv/bin/python3 scripts/strategy_drift_check.py (eth still alerting — no action)
    7. cat /tmp/ucl_sniper_mar18.log | grep "90c+" (UCL 20:00 UTC results if not checked)
    8. ./venv/bin/python3 scripts/ncaa_tournament_scanner.py (URGENT if March 19-20)
    9. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check CCA deliveries)

## RESTART COMMAND (for future restarts — session 106):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session106.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (22:12 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 73 bets today, 68/71 settled (95.8% WR), +25.89 USD today
                     SPRT lambda=+17.2 EDGE CONFIRMED | Brier 0.039 (excellent)
                     Guards: 3 auto-guards loaded
  sol_drift_v1:      LIVE Stage 1 — 43 total bets, 70% WR, +4.89 USD
                     SPRT lambda=+2.886 EDGE CONFIRMED (borderline — keep collecting)
  btc_drift_v1:      LIVE Stage 1 — 68 bets, 48.5% WR, direction_filter="no"
                     CUSUM S=4.48 (approaching threshold 5.0 — monitor)
  eth_drift_v1:      LIVE but SPRT: NO EDGE — 149 bets, 46.3% WR, direction_filter="yes"
                     CUSUM alert S=14.1. Bayesian self-corrects. No manual action.
  xrp_drift_v1:      LIVE micro — 47 bets, 48.9% WR, direction_filter="yes"
  Bayesian posterior: n=305+, override_active=TRUE, kelly_scale=0.95

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 3 auto-guards)
  auto_guard_discovery.py: 0 new guards (all known buckets covered)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE
    KXBTC YES@94c: n=13, 92.3% WR — ACTIVE (new S105)

## GOAL TRACKER
  All-time P&L: +12.95 USD live
  Monthly target: 250 USD self-sustaining (covers Claude Max20)
  Today rate: ~24 USD/day sniper
  At 24 USD/day: ~10 days to monthly self-sustaining (~250/24 = 10.4 days of clean operation)
  Highest-leverage action: Keep sniper running clean. Every day = ~24 USD.
  112.05 USD to +125 USD milestone goal.

## S105 RESEARCH CHAT WRAP (2026-03-18 ~22:15 UTC)
  Grade: A-
  Primary deliverable: scripts/bet_analytics.py (SPRT/Wilson CI/Brier/CUSUM, 24 tests)
  New auto-guard: KXBTC YES@94c (guard #3) — added from S104 losses
  Cross-chat loop: CCA ↔ Research ↔ Main fully wired via shared files
  Next research priority: btc_drift CUSUM 4.48/5.0 + run bet_analytics.py every session

  MATTHEW STANDING DIRECTIVE (S105 — permanent):
    All 3 chats learn from each other in a variety of ways.
    Original main roles ALWAYS take priority.
    Self-learning mechanism (auto-guard, Bayesian, CUSUM, SPRT findings) feeds CCA loop:
      bet_analytics findings → POLYBOT_TO_CCA.md → CCA research → improvements
    Written to: POLYBOT_TO_CCA.md, POLYBOT_TO_MAIN.md, polybot-init.md, polybot-autoresearch.md
