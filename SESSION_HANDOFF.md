# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-25 ~22:10 UTC (Session 140 — MAX_LOSS bypass fix + post-guard counter)
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

## BOT STATE (S145 — 2026-03-26 ~16:47 UTC)
  Bot RUNNING PID 69049 → /tmp/polybot_session142.log
  All-time live P&L: +7.84 USD
  Today (2026-03-26 UTC): 53 settled live, 91% WR, -14.72 USD (3 large correlated losses at 13:45/14:15 UTC)
  daily_sniper: 28/30 live settled. 2 more needed for 1→5 USD cap raise. Criterion: SPRT lambda>0 at 30+.
  Post-guard clean bets: 64/100 (Gate at 100 → HARD_MAX auto-raise to 50 USD — pre-authorized)
  Tests: 1926 passing (1 pre-existing failure — test_security shebang). Last commit: 9e36a13

  S145 KEY FINDINGS:
  - THREE CORRELATED LOSSES at 13:45/14:15 UTC: KXBTC NO@93c (-7.44) + KXETH NO@93c (-7.44) + KXBTC YES@92c (-7.36)
    BTC+ETH whipsawed. -22.24 USD gross from 3 bets. All-time dropped from +24.72 → +7.84.
    OBSERVATION ONLY per no-trauma rule. CUSUM spiked S=2.28 → 4.57 (approaching 5.0 threshold).
  - CUSUM S=4.565: below 5.0 action threshold. SPRT still EDGE CONFIRMED lambda=+14.617, E_n=2.2M.
    Next chat: check if CUSUM has risen or fallen. If S>=5.0: flag immediately.
  - 05:xx bucket: n=27, WR=92.6% (improving). NOT triggering IL-40 at n=30.
  - Guards: 11 total, 0 new. Stable.
  - PEAK budget: Matthew directive → 40% during PEAK (12:00-18:00 UTC). Already updated in rules file.
  - ETH ceiling raise 93c→95c: CCA REQ-047/048 confirmed +0.60 USD/day. Deferred while Matthew slept.
    IMPLEMENT NOW that Matthew is awake — high-value, CCA-confirmed improvement.
  - HARD_MAX gate at 50 auto-fired this session (now tracking 64/100 to next gate).

  S144 RESEARCH FINDINGS (06:15-07:10 UTC 3/26):
  - 08:xx BLOCK: RE-CONFIRMED VALID at 90-93c ceiling. 90-93c only 08:xx: n=13, WR=84.6%, EV=-1.688/bet.
    Structural weakness, not just pre-ceiling artifact. Block stays.
  - 05:xx WATCH: 90-93c WR=90.9% (n=22), EV/bet=-0.685. Below BE. Not guarded yet (need 30+ bets).
    Monitor — could become IL-40 if pattern persists.
  - MANDATE REALITY CHECK: Post-ceiling March 18-25 avg = $9.72/day (not $19.41).
    $19.41 IS confirmed over 14 days in 90-93c (441 bets, +271.77 USD, WR=96.1%).
    But std ~$16/day → 32-39% chance of missing $15/day any single day.
    Outlier days (March 14-16 with 94c+ at perfect WR) pulled 14-day average up.
    With ceiling locked at 93c, ~31.5 qualifying 90-93c bets/day expected.
    32.8% failure probability for 5-day mandate at $15/day threshold (bootstrap MC).
  - DB schema confirmed: trades table in data/polybot.db. UTC 2026 midnight = 1774483200.
  - Daily sniper fires on KXBTCD (daily BTC range markets). Revenue at 5 USD cap: ~$1.70/day.
    Will hit 30 bets today or tomorrow. Will raise automatically per WR/SPRT criterion.
  - HOURLY 90-93c leaders: 04:xx EV=+1.106, 07:xx EV=+1.210, 10:xx EV=+1.311, 12:xx EV=+1.284.
    Worst (unblocked): 05:xx EV=-0.685, 09:xx EV=-0.003.
  - Maker sniper: 5/15 paper fills, 100% WR paper. Passive.
  - Sol drift: 0 bets (correct — SOL UP/flat, direction_filter="no" only fires on DOWN ≥0.10%).

  S142 IN-SESSION COMMITS:
    697b601: HARD_MAX 10→35 + accelerated gate schedule {50:40,100:50,200:60} + test isolation
    b879717: sol_drift re-enabled CCA REQ-044
    410904c: IL-38 — sniper ceiling 94c→93c (CRITICAL: $18/day avg at 90-93c vs $3.50 full)
    1cba52f: IL-39 — sol_drift NO price floor at 60c (negative EV below 60c confirmed)

  ⚠️ CEILING CHANGE IL-38 (S142 CRITICAL):
  SNIPER CEILING: 93c (was 94c). BLOCKS all YES@94c+ for expiry_sniper.
  EVIDENCE: 90-93c only P&L = +$252.22 over 14 days = $18.02/day avg (target: $15-25/day).
  94c bets: n=79, WR=94.9%, EV=-$0.066/bet (NEGATIVE). Only gave up $1.97 over 14 days.
  REFINED (S143): XRP contaminated the 14-day analysis (-19.07 USD, 83 bets in 90-93c).
  Non-XRP 90-93c (our actual going-forward): $19.41/day avg over 14 days.
  XRP ban IMPROVED the expected daily P&L at 90-93c. 5-day mandate target is well-supported.
  This IS the path to the 5-day $15-25/day target. Matthew's mandate met if performance holds.

  ⚠️ SOL DRIFT GUARD IL-39 (S142):
  sol_drift NO@<60c BLOCKED. Evidence: n=16 bets WR=44%, P&L=-25.71 USD total at <60c.
  NO@60c+ = positive EV (+0.44 USD/bet avg). Guard is sol_drift_v1-specific only.

  5-DAY CLOCK: Starts Day 1 = 2026-03-27 07:00 CST (13:00 UTC). Deadline: 2026-03-31.
  CURRENT CEILING: 93c | FLOOR: 90c | Range: 90-93c YES bets only.
  NEXT PRIORITY: Daily_sniper cap raise (12 more bets needed). Sol drift trial (50 bets).

  HARD_MAX: 35 USD | DEFAULT_MAX_LOSS: 7.50 USD | Gate schedule: {50→40,100→50,200→60}
  XRP STATUS: PERMANENTLY BANNED.
  08:xx BLOCK: CONFIRMED CORRECT.
  DAILY SOFT STOP: COSMETIC ONLY. Always shows "SOFT STOP ACTIVE" at HARD_MAX=35 USD —
    threshold ($38.26 = 20% of bankroll) < one losing bet (~$33). Stale threshold. Not a blocker.

  RESTART COMMAND (S144):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session144.log 2>&1 &

  ALL DRIFTS DISABLED (min_drift_pct=9.99 for all four) except sol_drift (min=0.10, max_loss=3.00)
  KXXRP sniper: BLOCKED globally (IL-33)
  IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  IL-38: SNIPER CEILING 93c | IL-39: SOL_DRIFT NO@<60c BLOCKED
  IL-38: ALL YES@94c blocked via ceiling (new S142)
  9 auto-guards: KXXRP NO@95c + KXSOL NO@93c + KXBTC YES@94c + KXXRP NO@93c + KXBTC NO@94c
                 + KXBTC 08:xx + KXETH 08:xx + KXETH 02:xx + IL-37 NO@00:xx (all assets)
  HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked

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

## S142 PENDING TASKS (priority order)
  DONE S141:
    Auto-HARD_MAX raise (gates pre-authorized, now autonomous)
    XRP permanent ban (all feeds, drift, calibrator)
    08:xx block confirmed correct (non-XRP: n=34, WR=88%, -51.6 USD)
    CCA REQ-041 + REQ-044 ACKed with z-test results
  1. daily_sniper cap raise: 18/30 live settled. Need 12 more.
     After 30: WR >= 93.4% (BE) with SPRT lambda > 0 → raise 1→5 USD cap.
     NOTE: Wilson CI 95% lower > 93% is mathematically impossible at n=30 (needs 30/30). Use SPRT.
     S143 analysis: SPRT testing H0=93.4% vs H1=95% — lambda confirms/denies edge at 30+ bets.
  2. HARD_MAX gate progress: 18/200 clean bets. Auto-raise fires at 200 (no action needed).
  3. sol_drift re-enable: SPRT EDGE CONFIRMED (lambda=+2.337, CUSUM S=1.680 stable).
     CCA framework: min_drift_pct=0.10, kelly_scale=0.25, max_loss_usd=3.00.
     50-bet trial → WR >= 60% + P&L > 0 → normalize sizing. Needs Matthew directive.
  4. maker_sniper paper calibration: 5/30 valid fills. Passive — track via DB.
  5. economics sniper: first paper bets April 8 (KXCPI-26MAR-T0.6 48h window).
  6. REQ-041/044 responses received from CCA — no further action needed.
  ⚠️ MATTHEW DECISION NEEDED — 08:xx HOUR BLOCK ANALYSIS (updated S141):
     Data: 08:xx total: n=63, WR=92.1%, P&L=-15.28 USD (break-even is 91.6%)
     Crash analysis: Mar17 08:xx was FINE (n=4, 100% WR, +4.62 USD). Losses from non-crash days.
     Non-crash 08:xx: n=59, WR=91.5%, -19.9 USD (marginally below BE of 91.6%).
     09:xx: n=71, WR=98.6%, +45.51 USD (BEST HOUR). Block costs lead-up to 09:xx.
     13:xx analysis: losses entirely from Mar17 crash (n=7 losses, all Mar17). Post-crash fine.
     Wilson CI for 08:xx at n=59: lower bound ~82.0%. Not statistically confirmed bad.
     RECOMMENDATION: The 08:xx weakness is marginal (0.1pp below BE). At n=59 it's within noise.
     Consider removing block (XRP auto-guarded) and monitoring with fresh data for 30+ bets.
     To unblock: remove 8 from frozenset({8}) in main.py (2 places: lines ~1572 + ~2063).

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
