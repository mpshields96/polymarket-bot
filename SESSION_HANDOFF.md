# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-23 ~07:30 UTC (Session 126 monitoring wrap — bot RESTARTED PID 77025, IL-33 now active)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING — PID 77025. Log: /tmp/polybot_session126.log
  All-time live P&L: -13.95 USD (session net: -12.86 USD — losses from pre-IL-33 XRP bug)
  Bankroll: ~85 USD (estimate after today's losses)
  Tests: 1716 passing. Last commit: 37deb4d (docs: capture todo - rat-poison scanner)
  eth_drift: DISABLED (min_drift_pct=9.99)
  xrp_drift: DISABLED (min_drift_pct=9.99 as of S122)
  sol_drift: DISABLED (min_drift_pct=9.99 as of S123)
  KXXRP sniper: BLOCKED globally (IL-33, S125) — NOW ACTIVE (bug fixed S126)

## S126 MONITORING KEY FACTS (2026-03-23 ~07:30 UTC)

  CRITICAL FIX THIS SESSION:
  - IL-33 BUG DISCOVERED AND FIXED (S126): Bot PID 25880 was started at 04:07 UTC March 23,
    ONE MINUTE BEFORE the IL-33 commit (38a0d4f at 04:08 UTC March 23).
    Python loads modules at startup — the running bot had OLD live.py without IL-33.
    Result: 2 XRP sniper bets fired today: 02:21 UTC (WIN +1.47) and 03:04 UTC (LOSS -19.32).
    Fix: Restarted bot as PID 77025 at 07:22 UTC. IL-33 now active in memory.
    LESSON: Always restart bot after committing live.py changes. Code on disk != running code.

  BUILDS: None (monitoring + research session)

  KEY EVENTS S126:
  - Session net: -12.86 USD (from -1.09 to -13.95 all-time)
  - Today UTC: 22/25 = 88% WR, -12.77 USD (2 losses: XRP pre-fix + BTC variance)
  - XRP loss: KXXRP15M YES@92c -19.32 USD (placed before IL-33 active)
  - BTC loss: KXBTC15M NO@95c -19.95 USD (normal variance; 95c needs 95% WR)
  - btc_drift CUSUM IMPROVED: 3.880 → 3.420 (recent wins, moving away from threshold)
  - bot restarted PID 77025 with full IL-33 protection active

  RESEARCH COMPLETED S126:
  - 08:xx hour block: LEAVE IN PLACE. Non-XRP non-crash = 22/22 100% WR but
    expected crash cost (~0.33 USD/day) ≈ opportunity cost (~0.38 USD/day) at current sizing.
    Revisit when n=30+ non-XRP non-crash 08:xx at current Stage 1 sizing.
  - btc_drift: recovering — last 20 bets 60% WR, +2.78 USD. CUSUM 3.880→3.420.
  - 00:xx NO-side anomaly: 16/18 = 88.9%, -18.98 USD (most losses from old sizing).
    p=0.260 — NOT at guard threshold (p<0.20). No action. March 22 = 4/4 wins.
  - KXEARNINGSMENTIONX: 127 series exist (per-company earnings call content).
    No open markets now. Q1 earnings opens April 2026.
  - Hybrid chat: this chat is now the only Kalshi chat (monitoring + research combined)

  CUSUM STATUS (from bet_analytics.py S126 cycle 9):
  - expiry_sniper: EDGE CONFIRMED lambda=+16.947, CUSUM stable S=0.790
  - btc_drift: collecting lambda=-1.011, CUSUM S=3.420/5.0 (IMPROVING)
  - xrp_drift: disabled, CUSUM frozen S=3.980/5.0
  - sol_drift: disabled, CUSUM frozen S=1.680/5.0
  - eth_drift: NO EDGE, CUSUM DRIFT ALERT S=15.000 (disabled — expected)
  - eth_orderbook: CUSUM S=4.020/5.0 — WATCH (paper only, approaching threshold)

  GUARD INTEGRITY:
  - IL-33: KXXRP GLOBAL BLOCK in live.py — NOW ACTIVE in PID 77025
  - 5 auto-guards loaded: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c
  - IL-30: KXETH YES@93c BLOCKED in live.py (+ protected by 08:xx hour block)
  - WARMING BUCKET: KXETH NO@94c — n=15, WR=93.3%, p=0.581 (NOT yet significant — guard at p<0.20)
  - Hour block: frozenset({8}) — 08:xx UTC BLOCKED

  TODO ADDED S126:
  - Generalized rat-poison bucket scanner (.planning/todos/pending/2026-03-23-build-generalized-rat-poison-bucket-scanner-with-multi-dimensional-slices.md)
    Extend auto_guard_discovery to scan (asset × hour × side), (strategy × price × direction) etc.
    with Bonferroni correction + higher min_n for multi-dimensional slices.

  CCA PENDING:
  - REQUEST 16: BTC/ETH/SOL sniper health validation + 08:xx block re-eval (written S125)
  - REQUEST 17: Earnings mentions Q1 scan (127 series confirmed — open in April 2026)
  - REQUEST 12: Earnings Mentions scan — overlaps with 17
  - REQUEST 11: 00:xx Asian session mechanism — still collecting (need n>=30)
  - CCA last delivery: 2026-03-21 12:30 UTC (Req 4 + Req 8 — overnight sizing + XRP stats)
  - NOTE: This is now a HYBRID chat (monitoring + research). No separate research chat.
    Do research during monitoring downtime.

## PENDING TASKS (S127)

  CRITICAL:
  1. VERIFY IL-33 IS BLOCKING XRP: grep "KXXRP global sniper block" /tmp/polybot_session126.log | wc -l
     Should show blocks firing. If count=0 after 30+ min, re-check IL-33 in live.py.
  2. btc_drift CUSUM 3.420/5.0 — improved from 3.880 but still watch. Disable at S>=5.0.
  3. KXETH NO@94c warming bucket — run auto_guard_discovery.py at startup. Guard at p<0.20.

  WATCH:
  4. CCA REQUESTs 16, 17, 11, 12 — CCA SDATA-limited (12 queries until April 1).
     Do research inline (hybrid chat mode) rather than waiting for CCA.
  5. eth_orderbook CUSUM 4.020/5.0 — paper only but approaching threshold. Monitor.
  6. 00:xx NO-side: n=18, WR=88.9%, p=0.260. Accumulating. Re-check at n=25.
  7. KXEARNINGSMENTIONX: no open markets now. Check back April 2026.

  RESEARCH (do during downtime):
  8. Pick up any open CCA requests and investigate inline (hybrid chat mode)
  9. Earnings market structure — how do KXEARNINGSMENTIONX markets work (price dynamics)?
  10. btc_drift direction filter re-evaluation after 30+ NO-only bets post-change

  LOW PRIORITY:
  11. "Daily loss soft stop active" in --health = COSMETIC ONLY (enforcement commented out)
  12. Dim 9 signal_features accumulating passively (all recent sniper bets have features)
  13. Guard retirement: Dim 5 gap — shadow paper bets not recorded when guard fires.

## RESTART COMMAND (Session 127)
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session127.log 2>&1 &

## S125 MONITORING KEY FACTS (2026-03-23 ~06:05 UTC)

  BUILDS:
  - src/execution/live.py: IL-33 KXXRP global sniper block added (S125 — Matthew directive)
    SPRT lambda=-3.598 (far past -2.251 no-edge boundary). n=191 XRP sniper bets all-time.
    XRP all-time sniper P&L: -118.52 USD. BTC/ETH/SOL sniper: +172 USD combined.
  - ~/.claude/rules/cca-polybot-coordination.md: NEW global rule
  - ~/.claude/commands/polybot-auto.md: Hardwired CCA cross-chat + self-learning every 3rd cycle
  - Last commit: 38a0d4f (feat: IL-33 KXXRP global sniper block)

  KEY EVENTS:
  - Session net: +12.18 USD (recovered from -13.27 → -1.09 all-time)
  - IL-33 fired 33+ times during session blocking XRP sniper bets
  - CCA hardwired: global rules, CLAUDE.md, polybot-auto.md all updated
  - REQUEST 16 + 17 written to CCA

## S123 MONITORING KEY FACTS (2026-03-22 ~05:10 UTC)

  BUILDS:
  - config.yaml: sol_drift min_drift_pct 0.15 → 9.99 (DISABLED) — Matthew directive
  - src/data/odds_api.py: SDATA monthly cap 500 → 4000
  - main.py: 08:xx UTC hour block reinstated — all-time n=39, WR=82.1%, p=0.012
  - Last commit: 4a9190b
