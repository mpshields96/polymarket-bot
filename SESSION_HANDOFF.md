# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-23 ~06:05 UTC (Session 125 monitoring wrap — bot RUNNING, +12.18 USD session net)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING — PID 25880. Log: /tmp/polybot_session125.log
  All-time live P&L: -1.09 USD (session net: +12.18 USD — recovered from -13.27 USD)
  Bankroll: ~98.91 USD
  Tests: 1716 passing. Last commit: 38a0d4f (feat: IL-33 KXXRP global sniper block — SPRT lambda=-3.598)
  eth_drift: DISABLED (min_drift_pct=9.99)
  xrp_drift: DISABLED (min_drift_pct=9.99 as of S122)
  sol_drift: DISABLED (min_drift_pct=9.99 as of S123)
  KXXRP sniper: BLOCKED globally (IL-33, S125) — all XRP bets blocked regardless of price
## S125 MONITORING KEY FACTS (2026-03-23 ~06:05 UTC)

  BUILDS:
  - src/execution/live.py: IL-33 KXXRP global sniper block added (S125 — Matthew directive)
    SPRT lambda=-3.598 (far past -2.251 no-edge boundary). n=191 XRP sniper bets all-time.
    XRP all-time sniper P&L: -118.52 USD. BTC/ETH/SOL sniper: +190+ USD combined.
    Code: "if 'KXXRP' in signal.ticker: logger.info('[live] KXXRP global sniper block (IL-33)...'); return None"
  - ~/.claude/rules/cca-polybot-coordination.md: NEW global rule — CCA authority + every-3rd-cycle enforcement
  - ~/.claude/commands/polybot-auto.md: Hardwired CCA cross-chat + self-learning every 3rd cycle
  - polymarket-bot/CLAUDE.md: CCA authority block added to CROSS-CHAT BRIDGE section
  - Last commit: 38a0d4f (feat: IL-33 KXXRP global sniper block)

  KEY EVENTS:
  - Bot found DEAD at session start (PID 2054 gone, log stale). Restarted → PID 20059 → later at PID 25880
  - Session net: +12.18 USD (recovered from -13.27 all-time → -1.09 all-time)
  - Today live: -0.75 USD (14 wins / 15 settled = 93% WR; 1 loss outweighs 14 small wins)
  - IL-33 fired 33+ times during session blocking XRP sniper bets — working correctly
  - CCA coordination hardwired: global rules, CLAUDE.md, polybot-auto.md all updated
  - XRP blocked was NOT a trauma move — SPRT formally crossed no-edge boundary at lambda=-3.598
  - REQUEST 16 written to CCA (BTC/ETH/SOL health + 08:xx block re-eval)
  - REQUEST 17 written to CCA (Earnings mentions Q1 scan)
  - No CCA responses received — REQUESTS 11, 12, 15 (now closed), 16, 17 all pending

  CUSUM STATUS (from bet_analytics.py S125):
  - expiry_sniper: EDGE CONFIRMED lambda=+16.722, CUSUM stable S=0.985
  - btc_drift: collecting lambda=-1.011, CUSUM S=3.880/5.0 (UNCHANGED — no new btc bets)
  - xrp_drift: disabled, CUSUM frozen S=3.980/5.0
  - sol_drift: disabled, CUSUM frozen S=1.680/5.0
  - eth_drift: NO EDGE, CUSUM DRIFT ALERT S=15.000 (disabled — expected)
  - eth_orderbook: CUSUM S=4.020/5.0 — WATCH (paper only, approaching threshold)

  GUARD INTEGRITY:
  - IL-33: KXXRP GLOBAL BLOCK in live.py (S125) — all XRP sniper bets blocked
  - 5 auto-guards loaded: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c
  - IL-30: KXETH YES@93c BLOCKED in live.py (+ protected by 08:xx hour block)
  - WARMING BUCKET: KXETH NO@94c — n=15, WR=93.3%, p=0.581 (NOT yet significant — guard at p<0.20)
  - Hour block: frozenset({8}) — 08:xx UTC BLOCKED

  CCA PENDING:
  - REQUEST 16: BTC/ETH/SOL sniper health validation + 08:xx block re-eval (written S125)
  - REQUEST 17: Earnings mentions Q1 scan (SDATA 493/4000 = 12%, viable. Q1 April-May 2026)
  - REQUEST 12: Earnings Mentions scan — older request, overlaps with 17
  - REQUEST 11: 00:xx Asian session mechanism — still collecting (need n>=30)
  - CLOSED: REQUEST 15 — XRP global block implemented (IL-33) without academic citation
    Rationale: lambda=-3.598 far past formal boundary. Action justified on statistical grounds.

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
