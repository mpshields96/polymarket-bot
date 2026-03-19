# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-18 ~19:10 UTC (Session 107 research wrap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 28165 → /tmp/polybot_session107.log (restarted 18:54 UTC S107)
  All-time live P&L: +22.91 USD
  Today (March 18): +33.96 USD live (102 settled)
  Tests: 1623 passing. Last commit: caf69e9 (feat: Dim 8 temperature calibration)

## S107 RESEARCH WRAP KEY EVENTS

  1. STALE OPEN TRADES = FALSE ALARM — resolved
     1932 "stale" open trades are all paper (sports_futures=1878, fomc=48, copy_trader=6).
     Health check already patched (c2c6a8a). No settlement loop bug.

  2. CUSUM h=5.0 VALIDATED — ARL simulation confirmed h=5.0 is correct
     ARL(H0=0.58)=237, ARL(H1=0.50)=72. btc_drift S=4.480 consistent with ~50% WR.
     No threshold change needed. Observation only.

  3. DIM 8 BUILT: Per-strategy temperature calibration (commit caf69e9)
     Statistical finding: ETH calibration overconfidence p=0.015, XRP p=0.033.
     Platt (1999) temperature scaling applied per strategy.
     T values bootstrapped from 308 historical bets:
       ETH T=0.500: 54.8% → 52.4% win_prob
       BTC T=0.500: 57% → 53.5% win_prob
       XRP T=0.500: 61% → 55.5% win_prob (many signals below 5% floor)
       SOL T=1.290: 65.3% → 69.8% win_prob (larger Kelly for good strategy)
     Self-updating: calibrator.update() called after each settled drift bet.

  4. CCA REQUEST SENT: CUSUM h=5.0 theoretical optimality research
     Written to POLYBOT_TO_CCA.md — check next session for CCA response.

  5. BTC very_high edge_pct (>15%) = 39% WR, n=18 — OBSERVATION ONLY
     Anti-predictive but insufficient data for formal test (need 30+).

## SELF-IMPROVEMENT BUILD STATUS
  COMPLETE (Sessions 98-107):
  - Dim 1a: scripts/auto_guard_discovery.py — 3 auto-guards active
  - Dim 1b: live.py — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop — posterior updated after each live drift bet
  - Dim 4:  generate_signal() — predict() ACTIVE (n=308+ >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding
  - S105:   scripts/bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM (24 tests)
  - S107:   src/models/temperature_calibration.py — per-strategy T_s (18 tests)

## PENDING FOR S108+:
  #1 Monitor temperature calibration effect — is XRP WR improving? SOL P&L growing?
  #2 sol_drift Stage 2 evaluation — Brier 0.198, n=43, READY (Matthew's call)
  #3 CCA CUSUM threshold research — check CCA_TO_POLYBOT.md for response
  #4 BTC very_high edge_pct (>15%) guard: wait for n>=30 (currently n=18)
  #5 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~3+ more weeks)
  #6 Academic research: FLB dynamics in crypto prediction markets (pending)

  CONFIRMED DEAD ENDS (do NOT re-investigate):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper without WR data,
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  non-crypto 90c+ markets, one-off market scanners, btc_drift YES side (30% WR),
  per-strategy full Bayesian models (marginal benefit vs shared),
  stale open trades warning (false alarm — all paper long-duration trades)

## STARTUP SEQUENCE FOR S108:
    1. ps aux | grep "[m]ain.py" (expect PID 28165 or daemon-restarted)
    2. grep "Temperature calibrator loaded" /tmp/polybot_session107.log | tail -1
       MUST say: "ETH T=0.500  BTC T=0.500  SOL T=1.290  XRP T=0.500"
    3. grep "override_active=True" /tmp/polybot_session107.log | tail -1
    4. ./venv/bin/python3 scripts/bet_analytics.py (check if T_s changed behavior)
    5. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new guards)
    6. ./venv/bin/python3 main.py --health (should show: Stale live >48hr: none)
    7. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check CCA deliveries)

## RESTART COMMAND (for future restarts — session 108):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session108.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (~19:10 UTC March 18)
  expiry_sniper_v1:  PRIMARY ENGINE — 102 settled, sniper dominant, ~33 USD today
                     SPRT lambda=+17.516 EDGE CONFIRMED | CUSUM S=0.350 stable
                     Guards: 3 auto-guards loaded
  sol_drift_v1:      LIVE Stage 2 — T=1.290 (calibration BOOSTING Kelly)
                     SPRT lambda=+2.886 EDGE CONFIRMED | Brier 0.198 | n=43
                     READY FOR STAGE 3 evaluation (Matthew's call on bet cap increase)
  btc_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=4.480 (near threshold) | direction_filter="no"
  eth_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=14.140 DRIFT ALERT | Bayesian + calibration self-corrects
  xrp_drift_v1:      LIVE micro — T=0.500 (many signals now fall below 5% floor)
                     CUSUM S=2.820 stable | direction_filter="yes"
  Bayesian posterior: n=308+, override_active=TRUE, kelly_scale=0.952
  Temperature calibration: ACTIVE (data/calibration.json seeded from 308 bets)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 3 auto-guards)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE
    KXBTC YES@94c: n=13, 92.3% WR — ACTIVE

## GOAL TRACKER
  All-time P&L: +22.91 USD live
  Monthly target: 250 USD self-sustaining (covers Claude Max20)
  Today rate: ~34 USD/day sniper
  At 34 USD/day: ~6.7 days to monthly self-sustaining
  Distance to +125 USD milestone: 102.09 USD

## S107 RESEARCH CHAT NOTE
  Research chat S107: Dim 8 built, stale trades resolved, CUSUM validated.
  Full findings: .planning/EDGE_RESEARCH_S107.md
