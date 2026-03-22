# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-22 ~05:10 UTC (Session 123 monitoring wrap — bot STOPPED per Matthew, XRP block analysis)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot STOPPED — Matthew directive (sleep). Restart for S124 using restart command below.
  All-time live P&L: -1.18 USD (session net: +2.52 USD from sniper wins during S123 monitoring)
  Bankroll: ~98.82 USD (starting 100 + all-time -1.18)
  Tests: 1716 passing. Last commit: 4a9190b (feat: reinstate 08:xx sniper hour block S123)
  eth_drift: DISABLED (min_drift_pct=9.99)
  xrp_drift: DISABLED (min_drift_pct=9.99 as of S122) — last 10 WR=30%
  sol_drift: DISABLED (min_drift_pct=9.99 as of S123) — Matthew directive, -18.97 USD from 2 losses

## S123 MONITORING KEY FACTS (2026-03-22 ~05:10 UTC)

  BUILDS (all earlier in S123, before this monitoring run):
  - config.yaml: sol_drift min_drift_pct 0.15 → 9.99 (DISABLED) — Matthew directive, 0/2 losses -18.97 USD
  - src/data/odds_api.py: SDATA monthly cap 500 → 4000 — sub allows 20K/month (now 484/4000 = 12%)
  - main.py: 08:xx UTC hour block reinstated — all-time n=39, WR=82.1%, p=0.012 (significant)
  - Last commit: 4a9190b

  KEY EVENTS:
  - sol_drift DISABLED per Matthew (0/2 today = -18.97 USD from big Kelly-sized bets)
  - SDATA cap raised to 4000 — research scans now viable (484/4000 used)
  - 08:xx hour block REINSTATED — S119 crash-strip conclusion was wrong; ETH/BTC also below BE at 08:xx
  - All-time P&L improved -3.70 → -1.18 USD (+2.52 from sniper wins this session)
  - XRP global sniper block analysis: 189 bets, -100.67 USD all-time. REQUEST 15 filed to CCA.
  - btc_drift CUSUM improved 4.260 → 3.880 (2 recent wins)
  - Bot ran clean all session — no crashes, no freezes

  CUSUM STATUS (from bet_analytics.py S123):
  - expiry_sniper: EDGE CONFIRMED lambda=+16.653, CUSUM stable S=1.155
  - btc_drift: collecting lambda=-1.011, CUSUM S=3.880/5.0 (IMPROVING — was 4.260)
  - xrp_drift: disabled, CUSUM frozen S=3.980/5.0
  - sol_drift: disabled, CUSUM frozen S=1.680/5.0
  - eth_drift: NO EDGE, CUSUM DRIFT ALERT S=15.000 (disabled — expected)

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

## PENDING TASKS (S124)

  CRITICAL:
  1. CHECK CCA_TO_POLYBOT.md for REQUEST 15 response — XRP global sniper block analysis
     XRP all-time: 189 bets, 93.1% WR, -100.67 USD. All buckets negative. If CCA confirms
     structural basis: add global KXXRP filter in sniper (skip all XRP markets).
     Without XRP: sniper would be +172.55 USD all-time. This is the highest-leverage action.
  2. btc_drift CUSUM 3.880/5.0 — run bet_analytics.py at startup. Disable at S>=5.0.
  3. KXETH NO@94c warming bucket — run auto_guard_discovery.py EVERY startup.
     n=15, WR=93.3%, p=0.581. Add guard if p<0.20 or WR drops below break-even.

  WATCH:
  4. CCA REQUESTs 11, 12, 14 — SDATA now 484/4000, research viable. REQUEST 12 (Earnings) priority.
  5. sol_drift CUSUM 1.680/5.0 — frozen (disabled). No action needed unless re-enabling.
  6. xrp_drift DISABLED — frozen CUSUM 3.980/5.0. No action.
  7. Guard retirement: Dim 5 gap — blocked bets not recorded as paper, so post-guard accumulation = 0.
     Need "shadow paper bet" recording in live.py when guard fires. Low priority.

  LOW PRIORITY:
  8. "Daily loss soft stop active" in --health = COSMETIC ONLY (enforcement commented out)
  9. Dim 9 signal_features accumulating passively (all recent sniper bets have features)

## RESTART COMMAND (Session 124)
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session124.log 2>&1 &
