# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~23:10 UTC (Session 106 monitoring wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 2502 → /tmp/polybot_session105.log (running since 21:25 UTC restart S105)
  All-time live P&L: +16.40 USD
  Today (March 18): +27.45 USD live (97 settled, 70/73 sniper wins 95.9% WR)
  Tests: 1605 passing. Last commit: 054be2f (docs: S105 research wrap)

## S106 MONITORING WRAP KEY EVENTS

  1. SHORT SESSION — startup + 1 monitoring cycle + wrap
     Bot PID 2502 confirmed alive and running clean throughout.
     3 auto-guards confirmed loaded at startup.
     Bayesian n=305, override_active=True confirmed.

  2. SNIPER DOMINANT — 70/73 = 95.9% WR, +27.45 USD live today
     All-time grew from +12.95 → +16.40 USD (+3.45 this session).

  3. bet_analytics.py confirmed:
     expiry_sniper: EDGE CONFIRMED (lambda=+17.366, CUSUM S=0.480) — healthy
     sol_drift:     EDGE CONFIRMED (lambda=+2.886, CUSUM S=0.560) — healthy
     btc_drift:     collecting, CUSUM S=4.480 — still stable, not crossed 5.0
     xrp_drift:     collecting, CUSUM S=2.820 — stable
     eth_drift:     NO EDGE (lambda=-3.707), CUSUM DRIFT ALERT S=14.140 — Bayesian handles

  4. sol_drift READY FOR STAGE 2 — observation only
     Brier 0.198 (< 0.25), n=43, SPRT edge confirmed, 1 consec (healthy).
     graduation-status shows READY FOR LIVE. No promotion without Matthew explicit call.

  5. OPEN TRADE WARNING — 1932 open trades older than 48hr
     --health shows "settlement loop may have missed them".
     Needs investigation next session before it becomes a data quality issue.

  6. SDATA quota at 85% (426/500) — resets 2026-04-01. No action needed.

  7. Old /tmp/polybot_monitor_cycle.sh from S105 had bash syntax error at end.
     Use inline 5-min single-check pattern going forward (not the script).

## SELF-IMPROVEMENT BUILD STATUS
  DONE (Sessions 98-106):
  - Dim 1a: scripts/auto_guard_discovery.py — WORKING (3 auto-guards active)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop wired — posterior updated after each live drift bet
  - Dim 4:  generate_signal() wired — predict() ACTIVE (n=305+ >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming (50+ paper bets needed)
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test BUILT, 34 tests
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding (n=4→301)
  - S105:   scripts/bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM (24 tests, CONFIRMED)

## PENDING FOR S107+:
  #1 INVESTIGATE 1932 open trades older than 48hr — settlement loop concern (URGENT)
  #2 sol_drift Stage 2 graduation eval — Brier 0.198, n=43, READY FOR LIVE. Matthew must decide.
  #3 NCAA Round 1 — re-scan if March 19-20 (tip-offs March 20-21) — check date
  #4 UCL 20:00 UTC games — check /tmp/ucl_sniper_mar18.log (Man City/Chelsea/Arsenal)
  #5 btc_drift CUSUM at S=4.480/5.0 — monitor passively, no action until crosses
  #6 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~3+ more weeks)
  #7 CCA: check CCA_TO_POLYBOT.md each cycle (no deliveries yet as of S106)

  CONFIRMED DEAD ENDS (do NOT re-investigate):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper without WR data,
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  non-crypto 90c+ markets, one-off market scanners, btc_drift YES side (30% WR, -30 USD)

## STARTUP SEQUENCE FOR S107:
    1. ps aux | grep "[m]ain.py" (expect PID 2502 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session105.log | tail -1
       → MUST show "Loaded 3 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session105.log | tail -1
       → MUST show override_active=True
    4. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new)
    5. ./venv/bin/python3 scripts/bet_analytics.py (confirm SPRT/CUSUM unchanged)
    6. ./venv/bin/python3 main.py --health (check for 48hr open trades warning)
    7. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check deliveries)

## RESTART COMMAND (for future restarts — session 107):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session107.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (23:08 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 75 bets today, 70/73 settled (95.9% WR), +27.45 USD today
                     SPRT lambda=+17.366 EDGE CONFIRMED | Brier n/a | CUSUM S=0.480 stable
                     Guards: 3 auto-guards loaded
  sol_drift_v1:      LIVE Stage 1 — 43 total bets, 70% WR, +4.89 USD
                     SPRT lambda=+2.886 EDGE CONFIRMED | Brier 0.198 | READY FOR STAGE 2
  btc_drift_v1:      LIVE Stage 1 — 68 bets, 49% WR, direction_filter="no"
                     CUSUM S=4.480 (approaching threshold 5.0 — monitor)
  eth_drift_v1:      LIVE but NO EDGE — 149 bets, 46% WR, direction_filter="yes"
                     CUSUM alert S=14.140. Bayesian self-corrects. No manual action.
  xrp_drift_v1:      LIVE micro — 47 bets, 49% WR, direction_filter="yes"
                     CUSUM S=2.820 stable
  Bayesian posterior: n=305+, override_active=TRUE, kelly_scale=0.95

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 3 auto-guards)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE
    KXBTC YES@94c: n=13, 92.3% WR — ACTIVE (added S105)

## GOAL TRACKER
  All-time P&L: +16.40 USD live
  Monthly target: 250 USD self-sustaining (covers Claude Max20)
  Today rate: ~27 USD/day sniper
  At 27 USD/day: ~8.7 days to monthly self-sustaining (~234/27 = 8.7)
  Distance to +125 USD milestone: 108.60 USD
  Highest-leverage action: Keep sniper running clean. Investigate settlement loop (1932 open trades).

## S106 RESEARCH CHAT NOTE
  Research chat runs separately. Check polybot-init.md RESEARCH CHAT section for their state.
