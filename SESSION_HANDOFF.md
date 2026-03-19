# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-19 ~00:45 UTC (Session 108 research wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 33218 → /tmp/polybot_session108.log (restarted S108 for new guards)
  All-time live P&L: +22.91 USD (S107 data — S108 is research-only, no new P&L)
  Tests: 1623 passing. Last commit: caf69e9 (feat: Dim 8 temperature calibration)
  Note: No new commit this session (research-only)

## S108 RESEARCH WRAP KEY EVENTS

  1. 2 NEW AUTO-GUARDS ACTIVATED (5 total now)
     KXXRP NO@93c: n=24, 91.7% WR (need 93.4%), -15.3 USD — NEW
     KXBTC NO@94c: n=10, 90.0% WR (need 94.4%), -11.24 USD — NEW
     Bot restarted to activate. Now running 5 auto-guards.

  2. FLB ACADEMIC RESEARCH COMPLETE (Pillar 2)
     Verified papers confirm structural basis for sniper edge:
     - Burgi, Deng & Whelan (2026 CESifo WP 12122): Kalshi-specific — 95c → 98% WR (+3pp)
     - Snowberg & Wolfers (2010 NBER WP 15923 / JPE): probability misperception drives FLB
     - Ottaviani & Sorensen (2010 AEJ:Micro): fixed-odds FLB strengthens with informed bettors
     Full research: .planning/EDGE_RESEARCH_S108.md

  3. PER-BUCKET SNIPER VALIDATION (734 live bets analyzed)
     90-95c zone: all buckets show positive FLB excess (+0.6 to +10pp)
     96c+ zone: all negative (-1.9 to -5.7pp) — ceiling at 95c confirmed
     95c YES = 98.1% WR (+3.1pp, n=52) — exact match to Burgi-Deng-Whelan prediction

  4. BET ANALYTICS STATE (S108)
     sniper: 734 bets, EDGE CONFIRMED lambda=+15.332, CUSUM stable S=2.025
     sol_drift: n=43, EDGE CONFIRMED lambda=+2.886, Brier 0.198
     btc_drift: CUSUM improved 4.480 → 4.020 (S107 → S108), lambda=-1.056 (collecting)
     eth_drift: CUSUM 14.140 → 12.760 (slight improvement), SPRT NO EDGE confirmed
       NOTE: Bayesian + calibration handles. No manual action per PRINCIPLES.md.
     Bayesian: n=311, override_active=True, T values unchanged (insufficient new bets)

## SELF-IMPROVEMENT BUILD STATUS
  COMPLETE (Sessions 98-108):
  - Dim 1a: scripts/auto_guard_discovery.py — 5 auto-guards now active
  - Dim 1b: live.py — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop — posterior updated after each live drift bet
  - Dim 4:  generate_signal() — predict() ACTIVE (n=311 >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding
  - S105:   scripts/bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM (24 tests)
  - S107:   src/models/temperature_calibration.py — per-strategy T_s (18 tests)
  - S108:   FLB theoretical grounding complete (research-only, no code build)

## PENDING FOR S109+:
  #1 Check CCA_TO_POLYBOT.md — CUSUM h=5.0 research request sent S107, no response yet
  #2 Monitor new guards (KXXRP NO@93c, KXBTC NO@94c) performance
  #3 sol_drift Stage 2 evaluation — EDGE CONFIRMED, n=43, Brier 0.198, T=1.290
     READY FOR STAGE 3 consideration. Matthew's call on bet cap increase.
  #4 BTC very_high edge_pct guard: n=18 → need n>=30 before formal test
  #5 Monitor temperature calibration effect — T values still at bootstrapped values
  #6 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~3+ more weeks)

  CONFIRMED DEAD ENDS (cumulative):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper (no WR data),
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  time-of-day filtering, non-crypto 90c+ markets, annual BTC range markets,
  one-off market scanners, per-strategy full Bayesian models (marginal benefit),
  stale open trades investigation (false alarm — all paper long-duration markets),
  CUSUM h=5.0 change (ARL simulation confirms h=5.0 is correct)

## STARTUP SEQUENCE FOR S109:
    1. ps aux | grep "[m]ain.py" (expect PID 33218 or daemon-restarted)
    2. grep "Temperature calibrator loaded" /tmp/polybot_session108.log | tail -1
       MUST say: "ETH T=0.500  BTC T=0.500  SOL T=1.290  XRP T=0.500"
    3. grep "Loaded.*auto-discovered" /tmp/polybot_session108.log | tail -1
       MUST say: "Loaded 5 auto-discovered guard(s)"
    4. ./venv/bin/python3 scripts/bet_analytics.py (monitor new guard effect)
    5. ./venv/bin/python3 scripts/auto_guard_discovery.py (any new guards?)
    6. ./venv/bin/python3 main.py --graduation-status (sol Stage 2 readiness)
    7. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check CCA deliveries)

## RESTART COMMAND (for future restarts — session 109):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session109.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (~00:45 UTC March 19)
  expiry_sniper_v1:  PRIMARY ENGINE — 734 settled, 95.8% WR, +41.66 USD all-time
                     SPRT lambda=+15.332 EDGE CONFIRMED | CUSUM S=2.025 stable
                     5 auto-guards: KXXRP NO@95c + KXSOL NO@93c + KXBTC YES@94c +
                                    KXXRP NO@93c (NEW) + KXBTC NO@94c (NEW)
  sol_drift_v1:      LIVE Stage 2 — T=1.290 (calibration BOOSTING Kelly)
                     SPRT lambda=+2.886 EDGE CONFIRMED | Brier 0.198 | n=43
                     READY FOR STAGE 3 evaluation (Matthew's call on bet cap increase)
  btc_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=4.020 (improving from 4.480) | direction_filter="no"
  eth_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=12.760 (improving from 14.140) | Bayesian self-corrects
  xrp_drift_v1:      LIVE micro — T=0.500 | CUSUM S=2.820 stable | direction_filter="yes"
  Bayesian posterior: n=311, override_active=TRUE, kelly_scale=0.952
  Temperature calibration: ACTIVE (data/calibration.json, T values stable — few new bets)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 5 auto-guards)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE (original)
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE (original)
    KXBTC YES@94c: n=13, 92.3% WR — ACTIVE (added S105)
    KXXRP NO@93c: n=24, 91.7% WR — ACTIVE (NEW S108)
    KXBTC NO@94c: n=10, 90.0% WR — ACTIVE (NEW S108)

## GOAL TRACKER
  All-time P&L: +22.91 USD live (S107 data — no new P&L this research session)
  Monthly target: 250 USD self-sustaining (covers Claude Max20)
  At 34 USD/day sniper rate: ~6.7 days to monthly self-sustaining
  Distance to +125 USD milestone: ~102 USD

## FLB RESEARCH NOTE (S108)
  Research chat S108: FLB academic basis confirmed + per-bucket validation.
  Full findings: .planning/EDGE_RESEARCH_S108.md
  Key: 5 verified papers confirm structural FLB edge. Ceiling at 95c theoretically
  and empirically correct. Sniper edge = FLB, not noise.
