# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-22 ~02:30 UTC (Session 122 monitoring — xrp_drift disabled, -16 USD session net)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 73663 → /tmp/polybot_session122.log
  All-time live P&L: +2.87 USD (session net: -16.14 USD from +19.01 at S122 start)
  Today P&L: -21.17 USD live (19 settled: 13 sniper wins, 1 sniper loss, 2 sol_drift losses, 1 xrp_drift loss)
  Bankroll: ~103 USD (starting 100 + all-time +2.87)
  Tests: 1716 passing. Last commit: 4189028 (feat: disable xrp_drift S122 — last 10 bets WR=30%)
  eth_drift: DISABLED (min_drift_pct=9.99) — confirmed 0 bets
  xrp_drift: DISABLED (min_drift_pct=9.99 as of S122) — last 10 WR=30%, CUSUM 3.980/5.0

## S122 MONITORING KEY FACTS (2026-03-22 ~02:30 UTC)

  BUILDS:
  - config.yaml: xrp_drift min_drift_pct 0.10 → 9.99 (DISABLED)
  - tests/test_xrp_strategy.py: test_xrp_drift_fires_above_threshold now uses explicit BTCDriftStrategy params
  - Committed 4189028

  KEY EVENTS:
  - xrp_drift DISABLED (last 10 WR=30% triggers auto-disable threshold)
  - sol_drift 2 Stage 2 losses today: NO@46c (-9.66 USD) + NO@49c (-9.31 USD) = -18.97 USD
  - Sniper 1 loss: ETH NO@94c → result=yes → -19.74 USD (KXETH NO@94c warming bucket)
  - Bot stayed alive all session (PID 73663, no crashes, no freezes)

  CUSUM STATUS:
  - btc_drift: CUSUM S=4.260/5.0 — CRITICAL. Disable at S>=5.0 (no new btc bets this session)
  - xrp_drift: CUSUM S=3.980/5.0 — DISABLED (min_drift_pct=9.99)
  - eth_drift: CUSUM S=15.000 (expected — disabled strategy)
  - sol_drift: CUSUM S=1.680/5.0 — WATCH (was 1.120, now 1.680 after 2 losses)

  GUARD INTEGRITY:
  - 5 auto-guards loaded: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c
  - IL-30: KXETH YES@93c ALREADY BLOCKED in live.py
  - WARMING BUCKET: KXETH NO@94c — n=15, WR=93.3%, p=0.581 (NOT yet significant — monitor!)
  - Hour block: frozenset() — ALL HOURS ACTIVE

  CCA PENDING:
  - REQUEST 11: 00:xx Asian session mechanism — still collecting (need n>=30)
  - REQUEST 12: Earnings Mentions scan — SDATA 477/500 (95.4%), resets 2026-04-01
  - REQUEST 14: XRP YES@91c at 08:xx UTC (too early, n not growing since xrp disabled)

## S121 MONITORING KEY FACTS (2026-03-22 ~00:20 UTC)

  BUILDS: None — pure monitoring per Matthew's directive.

  BOT STABILITY ISSUE (S121):
  - Bot died twice: PID 36112 (died ~17:58 UTC, unknown cause), PID 52213 (froze 19:08 UTC, process alive but log stopped)
  - LESSON: Always check log tail for recent entries, not just ps aux. Frozen process looks alive.
  - PID 61788 = last session, PID 73663 = current

  CUSUM STATUS (from S121):
  - btc_drift: CUSUM S=4.260/5.0 — CRITICAL. Disable at S>=5.0
  - xrp_drift: CUSUM S=3.980/5.0 — NOW DISABLED S122
  - sol_drift: CUSUM S=1.680/5.0 — WATCH (risen after S122 losses)

## PENDING TASKS (S123)

  CRITICAL:
  1. btc_drift CUSUM 4.260/5.0 — CRITICAL: run bet_analytics.py at startup. Disable if S>=5.0 (min_drift_pct=9.99)
  2. KXETH NO@94c warming bucket — n=15, WR=93.3%, p=0.581. Run auto_guard_discovery.py at EVERY startup. If p crosses 0.20 or WR drops below ~91%, add guard.

  WATCH:
  3. sol_drift CUSUM 1.680/5.0 — rising after 2 losses. Still healthy (SPRT EDGE CONFIRMED). Monitor.
  4. xrp_drift DISABLED — log to todos whether to try re-enabling after 30+ paper data points accumulate (can't without live bets)
  5. CCA REQUESTs 11, 12, 14 — SDATA resets April 1, then research can resume

  LOW PRIORITY:
  6. "Daily loss soft stop active" in --health = COSMETIC ONLY (enforcement commented out)
  7. Signal_features: 7/825 total sniper bets have features (all recent ones do — Dim 9 working)

## RESTART COMMAND (Session 123)
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session123.log 2>&1 &
