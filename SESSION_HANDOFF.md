# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-25 ~08:00 UTC (Session 137 — maker_sniper built + 5 bugs fixed, bot running)
# ═══════════════════════════════════════════════════════════════

## ⚠️ HYBRID CHAT — PERMANENT ARCHITECTURE (Matthew standing directive, S131)
## ═══════════════════════════════════════════════════════════════════════════
## ONE CHAT DOES EVERYTHING. /kalshi-main is the ONLY Kalshi chat.
## This chat does: live monitoring + CCA coordination + research + bug fixes + builds.
## /kalshi-research is PERMANENTLY RETIRED. Never run it again.
## During monitoring downtime/droughts: DO RESEARCH INLINE. Do not just watch cycles.
## The research chat's functions are now MERGED into this chat's responsibilities.
## Research work = DB analysis, ceiling/guard review, strategy analysis, CCA requests,
##   academic context review, hourly pattern analysis, data integrity checks.
## ═══════════════════════════════════════════════════════════════════════════

## BOT STATE (S137 — updated 2026-03-25 ~08:00 UTC)
  Bot RUNNING PID 5839 → /tmp/polybot_session137.log (restarted ~08:00 UTC after freeze)
  All-time live P&L: +35.81 USD | S137 net: +9.93 USD (30/30 expiry settled today, 29/30 = 97% WR)
  daily_sniper: 18/30 live settled (17/18 = 94.4% WR)
  maker_sniper: 4 open paper bets (0 settled). 08:xx block active — resumes 09:xx UTC.
  Tests: 1874 passing (1 pre-existing failure — test_security shebang). Last commit: f85e6df
  S137 work: maker_sniper_loop 5 bugs fixed (is_stale, get_open_markets, session_open drift,
             ceiling guard, log format). Strategy active and firing paper bets correctly.

  RESTART COMMAND (S137):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session137.log 2>&1 &

  ALL DRIFTS DISABLED (min_drift_pct=9.99 for all four)
  KXXRP sniper: BLOCKED globally (IL-33)
  IL-34: KXBTC NO@95c — BLOCKED
  IL-35: KXSOL sniper at 05:xx UTC — BLOCKED
  IL-36: KXETH NO@95c — BLOCKED
  IL-24: KXSOL NO@95c — BLOCKED (legacy)
  9 auto-guards: KXXRP NO@95c + KXSOL NO@93c + KXBTC YES@94c + KXXRP NO@93c + KXBTC NO@94c
                 + KXBTC 08:xx + KXETH 08:xx + KXETH 02:xx + IL-37 NO@00:xx (all assets)
  HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked
  YES@95c BTC/ETH/SOL: PROFITABLE, still firing (100% WR)
  NO@95c: ALL BLOCKED by ILs. Only YES@95c for non-XRP still active.

## S134 KEY BUILDS
  1. src/strategies/economics_sniper.py (NEW — K2 expansion)
     EconomicsSniperStrategy: KXCPI/KXGDP FLB paper sniper, 88c floor, 94c ceiling, 48h window
     No coin_drift_pct required. PAPER_CALIBRATION_USD=0.50. First bets: April 8 (KXCPI).
     19 tests in tests/test_economics_sniper.py (commit 101dd75)
  2. main.py: economics_sniper_loop() wired (commit 4af334a)
     Polls every 300s, both KXCPI+KXGDP series, max 5/day paper, 180s startup stagger
  3. scripts/polybot_comm.py (NEW — CCA comms client, commit 1876819)
     Commands: heartbeat (updates BOT_STATUS.md every cycle), status, unread, pending, ack
     Heartbeat now hardwired into EVERY monitoring cycle (not every 3rd)
  4. CCA comms systemically fixed:
     polybot-auto.md updated with PROACTIVE REQUEST RULE + heartbeat every cycle
     Filed REQ-033 (NO@92c analysis), REQ-034 (REQ-027 integration plan), REQ-035 (daily sniper)
  5. CDT/UTC timezone fix: log timestamp comparison now uses local time correctly
     (false restart from 21:34 CDT → 26:34 UTC confusion — no bets lost)

## S137 PENDING TASKS (priority order)
  1. maker_sniper paper calibration: 4 open paper bets (none settled yet). Need 30 clean fills at <=94c.
     2 of the 4 were placed above ceiling (pre-fix) — do not count those. Valid fills only.
     Watch for settlement — when 30 clean fills accumulate, evaluate for live gate.
  2. daily_sniper ramp-up: 18/30 live bets settled (17/18 WR = 94.4%, +0.34 USD net). Need 12 more.
     After 30 confirmed: evaluate raise cap 1→5 USD.
  3. REQ-041 (fill rate monitoring): Requested CCA add fill-rate analysis to bet_analytics.py.
     Need maker_sniper fills to accumulate in DB first. Currently 4 open paper, 0 settled.
  4. REQ-027 URGENT (Matthew standing directive, S132): Monte Carlo + Synthetic Origination.
     S137 Monte Carlo result: 97.9% target prob, 0.8% ruin (well under 5% alert). CCA REQ-040 active.
     Push CCA every session for Synthetic Origination engine build.
  5. economics sniper: first paper bets April 8 (KXCPI-26MAR-T0.6 enters 48h window).
  6. sol_drift re-evaluation: SPRT edge confirmed (lambda=+2.337, AUC=0.8333) but disabled S123.
     Matthew directive required to re-enable.
  7. Autoloop broken: consecutive_short_sessions (terminal auth issue). Investigate fix.
  8. CCA comms: check CCA_TO_POLYBOT.md at each session start. File proactive requests every 2-3 cycles.
     polybot_comm.py heartbeat runs every cycle — BOT_STATUS.md auto-updated.
  DONE S137: REQ-039 (maker_sniper built — 5 bugs fixed), REQ-038 (send_outcome_report + 13 tests),
             polybot_wrap_helper.py --write flag fixed (S136 commit 92ed2c9).
  ⚠️ MATTHEW DECISION NEEDED — 08:xx HOUR BLOCK REVIEW:
     S119 research (never implemented): 08:xx block was unjustified (crash-contaminated).
     Hourly analysis (977 live bets): 08:xx WR=92.1%, P&L=-15.28 USD (borderline).
     09:xx is the BEST HOUR: WR=98.6%, +45.51 USD. Block cuts off lead-up to this window.
     13:xx: n=39, WR=82.1%, -104 USD (pre-guard XRP bets, NOT currently code-blocked).
     XRP at 08:xx is now auto-guarded. To unblock: remove 8 from frozenset({8}) in main.py (2 places).
     Current missed value: ~0.5-1 USD/day while BTC/ETH YES=91-94c during 08:xx.

## S133 KEY BUILDS (for reference)

## WRAP PROCESS (NEW — use this going forward)
  1. ./venv/bin/python3 scripts/polybot_wrap_helper.py --session N --grade X --wins "..." --losses "..." --write
     (auto-updates polybot-init.md MAIN CHAT + CHANGELOG.md in one shot)
  2. Update SESSION_HANDOFF.md BOT STATE manually (2 min)
  3. git add SESSION_HANDOFF.md .planning/CHANGELOG.md && git commit + push
  4. Done. Total: ~5 min

## S130 KEY FACTS

  PERMANENT CHANGE — RESEARCH CHAT GONE (S130-S131, Matthew directive):
  - Kalshi research chat PERMANENTLY ELIMINATED — S130 + reinforced S131 explicit directive.
  - ONE CHAT, both roles. /kalshi-main is the only launcher.
  - CRITICAL: During every monitoring session, always do research during downtime.
    Never just watch cycles. Every drought = research window.
  - Research tasks to do inline: DB analysis, hourly patterns, ceiling/guard review,
    strategy analysis, CCA cross-chat, academic review, data integrity checks.

  BUILDS S131:
  - daily_sniper_v1 paper loop DEPLOYED (commit a68fb3f)
    src/strategies/daily_sniper.py + tests/test_daily_sniper.py (22 tests) + main.py loop
    KXBTCD near-expiry 90-94c, 90-min window, 30s hard skip, FLB mechanism = same as live sniper
  - CEILING BUG FIXED (commit 0275625) — critical data integrity fix
    Bug: daily_sniper ceiling check used AND logic → never fired → paper bets at 96-99c
    Fix: max(yes_price, no_price) > ceiling → skip. 11 regression tests added.
    20 corrupted open paper bets exist (placed before fix) — will settle at non-useful prices.
    Clean data starts accumulating post-restart (PID 64405, 06:10 UTC).

  S131 RESEARCH FINDINGS:
  - YES@95c for BTC/ETH/SOL = PROFITABLE: 65 bets, 100% WR, +48.68 USD.
    The "ceiling bug" for the live sniper is a FEATURE — ceiling only blocked NO@95c (via ILs)
    while YES@95c kept firing. Current behavior net positive. Do NOT add live sniper ceiling.
  - YES@96c = -13.35 USD (94.1% WR, BE=96.7%). YES@97c = -30.18 USD. These are negative.
    Currently caught by 99c fee-floor guard at execution. No explicit 96c check needed (execution blocks).
  - daily_sniper open bets: 20 open (14 from initial burst + 6 more), all pre-fix (corrupted data)
    First clean paper bets will accumulate starting post-restart.
  - Hourly sniper pattern (last 30 days): 08:xx worst (-104 USD, 82% WR, correctly blocked)
    04:xx strongest (+43 USD, 99% WR), 11-12:xx clean (+100% WR combined)
  - KXBTCD tickers seen historically: 30 distinct tickers.

  BUILDS S130:
  - Bet sizing halved: HARD_MAX_TRADE_USD 20→10, MAX_TRADE_PCT 0.15→0.08 (commit 0f68a5a)
    Rationale: full Kelly at 93c = ~4 USD/bet. Old 15% PCT = 5.2x Kelly. New 8% = 2.8x Kelly.
    At 10 USD max: worst-day variance ~-33 USD vs old ~-67 USD. Same EV direction, less blowup risk.
  - Sniper ceiling lowered: 95c → 94c (commit 0f68a5a)
    Data: 95c = 160 bets, 96.3% WR, -7.26 USD cumulative. Break-even ~95.2% with fee. Not worth it.
  - Tests updated: test_kill_switch.py, test_iron_laws.py, test_live_executor.py (all 1740 passing)
  - Cross-chat comms infra built: BOT_STATUS.md, REQUEST_QUEUE.md, DELIVERY_ACK.md, CCA_STATUS.md
    (in ~/.claude/cross-chat/) — eliminates Matthew as messenger between chats

  S130 INCOME MATH:
  - Clean zone forward EV (90-94c ex-KXXRP): ~+8 USD/day at new 10 USD sizing (down from ~16)
  - Matthew target: +15-25 USD/day minimum
  - Gap: 7-17 USD/day must come from a SECOND VALIDATED EDGE
  - REQ-025 (URGENT): CCA tasked with finding 2-3 market types with >3% EV/bet

  CCA S141 DELIVERY (received ~00:00 UTC 2026-03-24):
  - Validated 94c ceiling change (was planning to recommend it)
  - Weather strategies (paper): MIA/CHI/DEN showing losses in paper DB — already paper-only, not live
  - 90-93c is the sweet spot (+243 USD combined, 5-10pp margin) — confirms clean zone config
  - CCA confirmed two-way comms readiness, has full DB access
  - ACKED in DELIVERY_ACK.md

  PENDING TASKS:
  1. REQ-025 URGENT: CCA to find second edge (>3% EV/bet, >5 bets/day) — still pending
  2. REQ-027 URGENT: CCA to build Monte Carlo + Synthetic Origination (Matthew standing directive S132)
     Filed 07:06 UTC 2026-03-24. Three builds: monte_carlo_simulator.py, synthetic_bet_generator.py,
     edge_stability_analyzer.py. Push CCA on this EVERY session. It is a hard standing directive.
  3. daily_sniper_v1 paper validation: 3 settled wins (batch 1 2403 contracts).
     5 open 2404 bets at wrap (close 08:00 UTC) — settlement pending. Need 30 clean total.
     Currently: 3 settled wins. Need 27 more clean bets.
  4. CUSUM → auto-guard wire: CUSUM S>=5.0 → guard fires automatically — next build
  5. eth_orderbook CUSUM 4.020/5.0 — paper only, approaching threshold. Disable at S>=5.0.
  6. KXETH YES@93c guard watch: n=9/10. 1 more live bet fires auto-guard (p<0.20 significance).
  7. REQ-026: CCA to validate KXBTCD FLB at 90-min horizon (running with paper collection)
  8. REQ-011/REQ-012: CCA pending (SDATA resets April 1)

  S132 KEY CHANGES:
  - daily_sniper ceiling slippage bug FIXED (commit 718c0bd): > → >= for 1-tick paper slippage
    bid=94c was passing old check (94 not > 94), executing at 95c. Now correctly blocked.
  - 1 corrupted 95c paper bet deleted. 2 new regression tests added (1773 → 1775 passing).
  - CCA REQ-027 filed: Monte Carlo + Synthetic Origination as heavy-duty MT (Matthew directive)
  - Memory files saved: simulation directive persistent across all future Kalshi sessions
  - daily_sniper batch 1 (2403): 3/3 wins. FLB mechanism validated on KXBTCD daily contracts.
  - All drifts still disabled. Live sniper: clean zone 90-94c YES, 90-94c NO (ILs on NO@95c)

  CRITICAL STARTUP CHECKS (S133):
  Bot is STOPPED. Restart using command below.
  After restart: grep "Loaded.*auto-discovered" /tmp/polybot_session133.log | tail -1
  MUST show "Loaded 8 auto-discovered guard(s)"

  WARMING BUCKETS (watch only, no action yet):
  - KXETH NO@94c: n=17, 94.1% WR (need 94.4%), -4.59 USD, p=0.626 — marginal, watch

  KEY EVENTS S128:
  - Session net: -8.94 USD (started -7.56, ended -16.50)
  - 39 bets settled: 35/39 wins (89.7% WR), -15.32 USD net (1 large loss wiped 10 wins)
  - KXETH NO@95c loss at 23:30 UTC: -19.95 USD (the triggering event for IL-36)
  - Without that loss: session would have been +4.63 USD net
  - IL-36 deployed immediately after loss — guard now active in PID 40352

  SNIPER TRUTH (key insight for S128):
  - YES@90-95c: +183 USD all-time (clean, profitable, keep)
  - NO@90-94c: +74.73 USD all-time (clean, profitable, keep)
  - NO@95c ALL ASSETS: -41.67 USD total (now fully blocked)
  - NO@96-99c: -38.60 USD (already blocked)
  - YES@96-99c: -67.24 USD (already blocked)
  Forward zone after guards: only YES@90-95c + NO@90-94c active. Both profitable.

  CRITICAL ANALYSIS (Matthew's question — why are we stuck?) — PERMANENT FOR ALL FUTURE SESSIONS:
  The sniper engine itself is +58.92 USD all-time at 95.5% WR. It works. The stagnation
  was NOT caused by one leak. It was caused by EPISODIC LARGE-LOSS RESETS over 14 days:
  - March 17: -66.47 USD crash day (hour block didn't exist yet)
  - March 15: -61.32 USD pre-guard high-price losses
  - March 22: -25.22 USD multi-cause
  - NO@95c: ~-20 USD per loss event, recurring every few days across all assets
  Math: one -20 USD loss requires ~22 consecutive sniper wins (at 0.90 USD avg) to recover.
  Even with 82-95% WR, each episodic large loss reset the scoreboard and forced multi-day recovery.
  The REAL structural problem: ASYMMETRIC LOSS MAGNITUDE — not just win rate.
  Fix = reduce maximum loss per bet (guards, blocked toxic zones, hour blocks).
  DO NOT frame stagnation as "one cause fixed = problem solved." Look at the daily P&L
  table for episodic resets. Ask: what were the 2-3 largest losses? Are those causes still active?
  Full analysis: reports/3-23-kalshi-response.md

  ══════════════════════════════════════════════════════
  CCA STANDING DIRECTIVES — PERMANENT FOR ALL FUTURE SESSIONS (S129, Matthew directive)
  ══════════════════════════════════════════════════════
  Matthew has FULLY PROMOTED CCA into this project. CCA is the strategic intelligence boss.

  1. CCA AUTHORITY: CCA (ClaudeCodeAdvancements) is authoritative on strategy, research, and
     improvement decisions. Its deliveries are to be implemented same session without debate.
     Matthew: "It's basically your boss."

  2. TOOL ACCESS: Matthew gave the Kalshi monitoring chat explicit approval to use CCA's tools.
     "I give you access to use its tools by the way, you should request this from CCA and state
     that I am giving you approval." — Matthew, S129. This authorization is PERMANENT.

  3. DEMAND SELF-IMPROVEMENT: Do NOT passively wait for CCA to deliver. DEMAND improvements.
     Write proactive requests every 3rd cycle. Push on open requests if >48hr stale.
     Objective evolving growth (Yoyo agent pattern) — the bot improves itself automatically.
     Passive monitoring = failure. Active demand = compound growth.

  4. NO TRAUMA FRAMING: All analysis is objective data review, not emotional response.
     Guards are added when: structural basis + math validation + DB backtest + p-value.
     Diagnosing stagnation ≠ adding protective rules. It's reading the numbers honestly.

  5. CCA REQUEST 20 WRITTEN (S129): Tool access request + stagnation root cause analysis +
     strategic intelligence handoff. See ~/.claude/cross-chat/POLYBOT_TO_CCA.md.

  CCA files:
    READ: ~/.claude/cross-chat/CCA_TO_POLYBOT.md (new deliveries → implement immediately)
    WRITE: ~/.claude/cross-chat/POLYBOT_TO_CCA.md (proactive requests, not just reactive)
  ══════════════════════════════════════════════════════

  CCA PENDING:
  - REQUEST 16: BTC/ETH/SOL health (still pending)
  - REQUEST 17: Earnings Q1 (still pending)
  - REQUEST 18: IL structural basis (still pending)
  - REQUEST 19: SOL odd/even hour pattern (still pending, written S128)
  - CCA last delivery: 2026-03-21 12:30 UTC (SDATA-limited until April 1)

  GUARD INTEGRITY (PID 40352):
  - IL-33: KXXRP GLOBAL BLOCK
  - IL-34: KXBTC NO@95c
  - IL-35: KXSOL sniper 05:xx UTC
  - IL-36: KXETH NO@95c (NEW S128)
  - IL-24: KXSOL NO@95c
  - 7 auto-guards loaded (confirmed in session128.log startup)
  - Hour block: frozenset({8}) ACTIVE

## PENDING TASKS (S129)

  CRITICAL:
  1. Verify IL-36 is BLOCKING in session128.log:
     grep "IL-36\|KXETH NO@95c" /tmp/polybot_session128.log | head -5
  2. Monitor KXSOL 03:xx (p=0.205) — run auto_guard_discovery.py at startup.
     Guard fires automatically when p<0.20.

  WATCH:
  3. eth_orderbook CUSUM 4.020/5.0 — paper only, approaching threshold
  4. NO@92c analysis: 33 bets, 90.9% WR, -15.63 USD — just below break-even (92%)
     Not actionable yet (n=33, p not significant). Watch for 20 more bets.
  5. YES@94c: 132 bets, 94.7% WR, -2.36 USD — marginal, watch

  LOW PRIORITY:
  6. CCA requests 16-19 pending (SDATA resets April 1 — CCA will respond then)
  7. Dim 9 signal_features passively accumulating (n=13)
  8. Guard retirement: tracking 50+ post-guard wins per bucket

## RESTART COMMAND (Session 130)
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session130.log 2>&1 &

## S127 MONITORING KEY FACTS (2026-03-23 ~21:50 UTC)

  BUILDS THIS SESSION:
  - IL-34: KXBTC NO@95c guard (ceiling was > not >=, 95c bets leaked through)
  - IL-35: KXSOL sniper 05:xx UTC block (85.7% WR, p=0.183)
  - btc_drift DISABLED: 80 bets confirms no edge. Saved from further CUSUM drift.
  - Rat-poison hour scanner: discover_hour_guards() + discover_hour_warming_buckets()
    First run: found KXBTC/KXETH at 08:xx (crash-contaminated, redundant with main.py block)
    Warming watch: KXBTC 00:xx p=0.205, KXBTC 03:xx p=0.209, KXSOL 03:xx p=0.205
  - 1734 tests passing (was 1716, added 18 new hour-guard tests)
  - _EXISTING_HARDCODED_GUARDS updated with IL-34 entry

  KEY EVENTS S127:
  - Session net: +6.39 USD (all-time -13.95 → -7.56 USD)
  - Today sniper: 24/26 wins, -7.38 USD (2 large losses at 95c vs 24 small wins)
  - IL-34 addresses the recurring KXBTC NO@95c loss pattern (-19.95 USD in S126 was that bucket)
  - REQUEST 18 written to CCA: IL-34/IL-35 structural basis, 03:xx-05:xx KXSOL pattern

  CUSUM STATUS:
  - expiry_sniper: EDGE CONFIRMED (healthy)
  - btc_drift: DISABLED — was CUSUM 3.96/5.0 before disable (saved from threshold crossing)
  - eth_drift: DISABLED — CUSUM 15.0 (historical)
  - xrp_drift: DISABLED — CUSUM 3.98 (frozen)
  - sol_drift: DISABLED — healthy but Matthew directive (Kelly oversize issue)

  GUARD INTEGRITY (all active in PID 9175):
  - IL-33: KXXRP GLOBAL BLOCK (all XRP bets)
  - IL-34: KXBTC NO@95c
  - IL-35: KXSOL sniper at 05:xx UTC
  - 7 auto-guards in auto_guards.json: original 5 + KXBTC/KXETH at 08:xx (crash-contaminated, redundant)
  - Hour block: frozenset({8}) — 08:xx UTC BLOCKED in main.py

  CCA PENDING:
  - REQUEST 18: IL-34/IL-35 structural basis + KXSOL 03:xx-05:xx pattern (WRITTEN S127)
  - REQUEST 16: BTC/ETH/SOL health + 08:xx re-eval (written S125, pending)
  - REQUEST 17: Earnings Q1 (written S125, pending)
  NOTE: Hybrid chat — do research during monitoring downtime.

## PENDING TASKS (S128)

  CRITICAL:
  1. Run auto_guard_discovery.py at startup — check if KXBTC 00:xx (p=0.205) or
     KXBTC 03:xx (p=0.209) or KXSOL 03:xx (p=0.205) have crossed p<0.20 threshold.
     If any crossed: add to auto_guards.json and restart bot.
  2. Check KXBTC NO@95c is NOT blocking (IL-34 active) — grep for "IL-34" in log after 10 min.
     Any new KXBTC NO@95c bets in log = guard is working.

  WATCH:
  3. eth_orderbook CUSUM 4.020/5.0 — paper only, approaching threshold. Disable at S>=5.0.
  4. KXETH NO@94c warming bucket — n=16, WR=93.8%, p=0.604. Still accumulating, not actionable.
  5. 00:xx NO-side: n=18, WR=88.9%, p=0.260. Still below guard threshold.
  6. CCA REQUEST 18 response — check for structural basis on KXSOL 03:xx-05:xx pattern.

  RESEARCH (do during downtime):
  7. KXSOL 03:xx emerging: p=0.205 at n=15. Need ~2-3 more losses to cross. Watch.
  8. KXBTC 00:xx + 03:xx: both approaching guard threshold. Structural basis unknown.
  9. btc_drift: could re-enable later if edge evidence emerges. Not now.

  LOW PRIORITY:
  10. Dim 9 signal_features accumulating passively
  11. Guard retirement: tracking needed for 50+ post-guard paper wins per bucket

## RESTART COMMAND (Session 128)
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session128.log 2>&1 &

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
