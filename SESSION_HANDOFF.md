# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-04-07 03:55 UTC (S168 wrap)
# ═══════════════════════════════════════════════════════════════

## ⚠️ READ FIRST: .planning/MATTHEW_DIRECTIVES.md — VERBATIM MANDATE DIRECTIVES (S150, 2026-03-27)
## ══════════════════════════════════════════════════════════════════════════════════════
## MANDATE: 15-25 USD/day ACHIEVE AND SUSTAIN. ANY market. ANY strategy. Figure it out.
## Deadline EXTENDED to April 3 (was March 31) — accounts for downtime.
## MONTHLY INCOME DIRECTIVE: few hundred USD/month consistently. 15-25/day × 20 trading days.
## ABSOLUTE FREEDOM DIRECTIVE: DO LITERALLY ANYTHING ON KALSHI. No strategy is sacred.
## No framework is required. No approval needed. Bet anything, any size, any market.
## ONE RULE ONLY: bankroll must never drop below 20 USD. Matthew will NOT add more funds. EVER.
## Everything else — kill switch, Kelly, stage caps, graduation gates — ALL NEGOTIABLE.
## ⚠️ ACHIEVE *AND SUSTAIN* — hitting 15-25 USD once means NOTHING. Zero. Does not count.
## The goal is a bot that RELIABLY produces 15-25 USD EVERY SINGLE DAY. Build systems.
## Full directive: .planning/MATTHEW_DIRECTIVES.md (ABSOLUTE FREEDOM DIRECTIVE section)
## ══════════════════════════════════════════════════════════════════════════════════════

## ⚠️ HYBRID CHAT — PERMANENT ARCHITECTURE (Matthew standing directive, S131)
## ═══════════════════════════════════════════════════════════════════════════
## ONE CHAT DOES EVERYTHING. /kalshi-main is the ONLY Kalshi chat.
## This chat does: live monitoring + CCA coordination + research + bug fixes + builds.
## /kalshi-research is PERMANENTLY RETIRED. Never run it again.
## During monitoring downtime/droughts: DO RESEARCH INLINE. Do not just watch cycles.
## ═══════════════════════════════════════════════════════════════════════════

## ⚠️ 5-DAY MANDATE — CLOCK STARTED 2026-03-27 00:11 UTC (Matthew standing directive)
## ═══════════════════════════════════════════════════════════════════════════════════
## GOAL: Achieve and SUSTAIN 15-25 USD DAILY within 5 days (extended to April 3).
## DEADLINE: 2026-04-03 ~00:11 UTC (extended from March 31 to account for downtime)
## CLOCK STARTED: 2026-03-27 00:11 UTC.
## Day 1 (March 27): +6.56 USD (below target — old sizing active most of Day 1)
## Day 2 (March 28): +60.04 USD (CRUSHED mandate — 42 settled, 100% WR)
## CONSTRAINTS: (1) Starting bankroll final — no new capital EVER. Matthew is explicit.
##              (2) FORBIDDEN: bankroll floor ≤ 20 USD.
##              (3) Do NOT ask Matthew for help. Use CCA for anything/everything.
## ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES ALL CONSERVATIVE CONSTRAINTS BELOW EXCEPT FLOOR.
## ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS. PERMANENT.
## ═══════════════════════════════════════════════════════════════════════════════════

## OVERHAUL STATUS: INCOMPLETE — blocked by visibility gate runtime path still unproven (live probe crawled huge pagination and produced no cache yet), stale startup/handoff priorities, and open mandatory overhaul tasks below.
## Do not count restart pressure, new strategy ideas, or side research as progress until those blockers are closed.

## BOT STATE (S168 wrap — 2026-04-07 03:55 UTC)
  Bot: RUNNING PID 303 → /tmp/polybot_session168.log
  All-time live P&L: +130.44 USD | Today CST April 7: -1.28 USD (26 settled, 19 wins = 73% WR)
  Tests: 2308 passing, 3 skipped. Last commit: eae5456

  S168 COMPLETED:
  ✅ Fixed calculate_size() kwargs in sports_inplay_sniper_loop (current_bankroll_usd→bankroll_usd, payout_per_dollar=None→computed real payout). Bug was throwing TypeError every signal cycle.
  ✅ Fixed docstring in injury_kill_switch() — NBA PG example showed wrong result (True→False)
  ✅ VERIFIED DONE (stale from S167): efficiency_feed already wired into sports_game.py (commit da8f134)
  ✅ VERIFIED DONE (stale from S167): test_kalshi_visibility_report.py collection error already fixed
  ✅ VERIFIED DONE (stale from S167): yes_sub_title BUG-FLAG already addressed with tests

  ⚠️ BOT NEEDS RESTART to pick up main.py fix (inplay sniper TypeError still firing on old process)

  PENDING TASKS (priority order — Session 169):
  1. RESTART BOT → session169.log (to pick up calculate_size fix — inplay sniper is erroring every cycle)
  2. Run kalshi_series_scout.py (CCA Chat 48 mandate) — blocked by DNS in sandbox, run at production
  3. CPI April 10: confirm KXCPI open April 8, run cpi_release_monitor.py April 10 08:28 ET
  4. Phase 9 wrap template (CCA Chat 52) — check if CCA has delivered this
  5. eth_daily_sniper: was disabled in S167 (BUG-C). Check if it should be re-enabled after restart.

  RESTART COMMAND (Session 169 — fix is committed, restart picks it up):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session169.log 2>&1 &

  ⚠️ APRIL 13 NEW DEADLINE (S162 — Matthew directive):
  "Figure out and succeed by April 13. Bet sports or ANY market. CCA + Codex help."
  ALL markets authorized. Expansion gate SUSPENDED. ONE RULE: bankroll > 20 USD.
  Success = sustained 15-25 USD/day + at least 1 new market type live by April 13.

  S163 KEY FINDINGS:
  1. ETH daily sniper PROMOTED TO LIVE (commit db9fae0). max_price_cents=92 (CCA REQ-62).
     First live bet: NO KXETHD-26APR0303-T2099.99 @ 91c = 9.10 USD (trade 14146, pending 07:00 UTC).
     2 live bets pending: 14145 (KXBTCD @ 93c = 9.30 USD) + 14146 (KXETHD @ 91c = 9.10 USD)
  2. CCA REQ-068 received: CPI readiness WATCH. Keep economics_sniper paper-only through April 10 CPI.
     Confirm KXCPI markets open April 8. Run cpi_release_monitor.py April 10 08:28 ET.
  3. CCA REQ-069 received: tonight's sports board (NBA/NHL/MLB). sports_game already scanning.
     No code action needed — auto-fires at game time (~7PM ET = 23:00 UTC).
  4. CUSUM S=15 DRIFT ALERT on eth_drift_v1 — ALREADY DISABLED (min_drift_pct=9.99). Historical.
  5. Guard stack: 0 new guards. All WATCH items p > 0.30. Clean.
  6. HARD_MAX ramp: 124/200 clean bets. 76 more until 50→60 USD raise.
  7. daily_sniper analytics: 166 bets, 99.4% WR, +101.90 USD, SPRT lambda=+24.315 (sky high).
  8. Bot STOPPED per Matthew. 2 live bets pending settlement at 07:00 UTC.
     If next session starts AFTER 07:00 UTC, query DB for trade 14145 + 14146 results.

  PENDING TASKS (priority):
  1. Confirm trade 14145 + 14146 settled (check after 07:00 UTC = 02:00 CDT)
  2. Economics CPI: confirm KXCPI open April 8 + paper bets. Live decision April 9.
  3. Sports game tonight (April 3 ET = April 4 UTC): NBA/NHL/MLB auto-fire ~7PM ET.
  4. UCL April 7-8 soccer markets: CCA + Codex building infrastructure. Await response.
  5. HARD_MAX ramp: 76 clean bets to next gate (50→60 USD).

  RESTART COMMAND (Session 164):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session164.log 2>&1 &

  S162 KEY FINDINGS:
  1. Weather dead end CONFIRMED: DB WR 37-60% (Miami 37%). Miscalibrated model. Do NOT revisit.
  2. ETH daily sniper n=15 (15/15 wins). Live eval threshold reached. Use 92c ceiling (CCA REQ-62).
  3. Sports game timing: game-day markets open afternoon ET — bot will auto-fire then. Working.
  4. Odds API cap raised to 10,000 credits/month (was 4000). Matthew directive.
  5. CCA REQUEST 66 filed: UCL April 7-8, CPI live April 10, sports timing, MVE markets.
  6. Mandate deadline passed (April 3). New deadline April 13 — diversify income sources.
  7. Sniper 50/50 daily cap hit at 05:11 UTC. 100% WR. +37.77 USD today alone.

  STRATEGY ANALYZER INSIGHTS (S162):
  - Sniper profitable buckets: 90-94c. Guarded: 95-98c. EDGE CONFIRMED.
  - btc_drift: NEUTRAL (50% WR, -9.53 USD all-time). direction_filter="no" active.
  - eth_drift: UNDERPERFORMING (46% WR, declining). DISABLED.
  - sol_drift: HEALTHY (66% WR, -15.68 USD — still accumulating data).

  S160 KEY FINDINGS (still relevant — from 2026-03-29):
  1. SNIPER TIMING RE-CONFIRMED: CST midnight = 06:00 UTC = 01:00 AM CDT (not 9 PM CDT).
     Earlier session had wrong countdown. Corrected via DB timestamp query.
  2. GUARD STACK: auto_guard_discovery confirmed 0 new guards (11 unchanged). Clean.
  3. SPRT/CUSUM: daily_sniper EDGE CONFIRMED lambda=+15.205, CUSUM S=3.835 (stable).
     eth_drift DRIFT ALERT S=15.0 — already disabled, expected, no action.
  4. REQ-65 FILED: pre-implementation risk check for 88c floor widening.
     Live data at 88-89c: only 1 bet. Insufficient to validate floor change.
     Waiting for CCA response before any config change.
  5. SPORTS ANALYSIS: NBA losses (-9.75, -9.92) were at OLD 10 USD cap. At current 2 USD
     cap, NBA has 0 meaningful data points. NHL 4/4 wins. Cap stays 2 USD.
  6. ETH PAPER SNIPER: 5/5 wins (91-93c range). Positive early signal, n=5 too small.
  7. CCA UPDATES 84-87 all reviewed and logged to todos.md.

  5-DAY MANDATE STATUS:
  Day 1 (March 27 UTC): -4.13 USD — MISSED
  Day 2 (March 28 UTC): +42-49 USD — HIT
  Day 3 (March 29 UTC): started 00:00 UTC (S160 was monitoring this)
  Days 4-7: UNKNOWN from CCA — run --report for current P&L
  DEADLINE: 2026-04-03 00:11 UTC — Kalshi chat must verify mandate status

  OPEN BETS: unknown — verify with --health
  SNIPER: verify current cap/status with --health + --graduation-status

## PENDING TASKS (priority order)
  ⚠️ APRIL 13 DEADLINE — diversify beyond sniper. CCA + Codex available. ANY market authorized.
  1. ETH daily sniper LIVE PROMOTION: n=15 paper wins, all wins. Threshold reached.
     Action: flip eth_daily_sniper_v1 live_executor_enabled=True with 92c ceiling. ~5 LOC change.
     Gate: run pre-live audit (CLAUDE.md Step 5) first. This is the highest-leverage next action.
  2. CPI economics sniper LIVE DECISION (April 9): paper mode fires April 8 on KXCPI.
     If paper bet wins with edge >5%: flip live for April 10 CPI release.
     CCA REQ-66 pending: waiting for response on CPI timing + UCL soccer.
  3. Sports game auto-fire: game-day markets open afternoon ET. Bot already live — no action needed.
     Monitor: check DB for first sports_game bet at ~18:00 UTC (1pm ET today).
  4. UCL soccer sniper: April 7-8 (QF 2nd legs). CCA REQ-66 pending research.
     Arsenal/Chelsea/Man City/Spurs matches. FLB at 90c+ late in game. Need CCA to confirm edge.
  5. FROZEN PROCESS WATCH: check log recency every cycle. >15min stale = restart to session162.log.
  6. CCA REQ-65 RESPONSE: 88c floor widening. Do NOT change floor until CCA responds.
  7. REQ-65 implementation: paper_min_price=88c separate from live_min_price=90c (~40 LOC + tests).
  8. CODEX_OBSERVATIONS.md: check at session start.
  9. +125 USD milestone: HIT (120.21 USD all-time). Next: sustain 15-25 USD/day through April 13.

## STRATEGY STATUS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these strategies are tools, not laws.
  ⚠️ ALL 15-MINUTE CRYPTO MARKETS PERMANENTLY BANNED FROM LIVE. No exceptions. Ever.

  - sports_game_v1 (NBA/NHL/MLB): NEW LIVE ENGINE. 5-min poll, 15-80c, 5% edge threshold.
    n=5 settled (3W NHL / 2L NBA). Cap at 2 USD/bet. Goal: n=30, then raise cap.
  - daily_sniper_v1: LIVE (10 USD cap per bet, 50 bets/day max). SPRT edge confirmed (lambda=+11.699).
    ⚠️ Note: KXBTCD IS a daily crypto threshold market (NOT a 15-min direction market). ALLOWED.
    Cap raised 30→50 in S159 (config: max_daily_bets_live). ~0.70 USD per winning bet.
  - eth_daily_sniper_v1: PAPER-ONLY. Firing at KXETHD. CCA REQ-62 DELIVERED: use 92c ceiling
    (not 94c) when going live — ETH volatility warrants tighter ceiling. Paper cap 5/day.
  - weather: PAPER-ONLY (code confirmed: "always paper"). SESSION_HANDOFF had wrong status.
    Weather bets are 0 live P&L contribution.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI).
  - sports_sniper_v1: PAPER-ONLY. ESPN polling. 0/20 fills.
  - expiry_sniper_v1: PAPER-ONLY. PERMANENTLY BANNED from live.
  - All 15-min crypto strategies: PAPER data only. LIVE=BANNED.

## GUARDS ACTIVE (11 total)
  - IL-33: KXXRP GLOBAL BLOCK (PERMANENT — XRP forever banned, Matthew explicit)
  - IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx UTC | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  - IL-38: Sniper ceiling 93c (BTC/SOL) | IL-38-ETH: ETH ceiling 95c
  - IL-39: sol_drift NO@<60c
  - 9 auto-guards from auto_guards.json (loaded at startup).
  - HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked

## SIZING PARAMETERS
  KELLY_FRACTION = 0.85
  ABSOLUTE_MAX_USD = 25.00
  DEFAULT_MAX_LOSS_USD = 22.00
  HARD_MAX_TRADE_USD = 50.00 (kill_switch — raised S153 from 35→50)
  Stage 2 (bankroll 100-250): max 25 USD, 11% bankroll
  Stage 3 (bankroll 250+): max 25 USD, 9% bankroll

## KILL SWITCH PARAMETERS
  consecutive_loss_limit = 8 (→ 2hr cooling)
  daily_loss_cap = DISABLED
  bankroll_floor = 20 USD (INVIOLABLE — this one cannot be overridden)

## RESTART COMMAND (S162 wrap — use session163 for next restart)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session163.log 2>&1 &

## STOP COMMAND (verified by Codex 2026-04-05)
  PID=$(cat bot.pid) && kill -TERM "$PID"
  Then wait until `kill -0 "$PID" 2>/dev/null` fails.
  If the process is gone but `bot.pid` still exists, run `rm -f bot.pid`.
  Do NOT use `pkill`/`kill -9` for routine overnight stop unless clean shutdown fails.

## CRITICAL STARTUP CHECKS
  - kill -0 $(cat bot.pid) 2>/dev/null && echo "ALIVE" || echo "DEAD"  ← USE THIS, not grep
    ⚠️ NEVER use ps grep + && + tail — grep on missing log file = false alarm exit 1.
    If stale >15min in log: RESTART (frozen process pattern — happened S151, S155, S157, S158).
    Current log: /tmp/polybot_session161.log (PID 12448 as of S252 init)
    ⚠️ TIMEZONE: Machine is CDT (UTC-5). Log timestamps like 14:xx = 19:xx UTC. Always convert.
  - FIRST: check today's P&L vs mandate target (15-25 USD):
    ./venv/bin/python3 -c "import sqlite3,calendar; from datetime import datetime, timezone; c=sqlite3.connect('data/polybot.db'); ts=calendar.timegm(datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0).timetuple()); r=c.execute('SELECT COUNT(*),SUM(CASE WHEN side=result THEN 1 ELSE 0 END),ROUND(SUM(pnl_cents)/100.0,2) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL',(ts,)).fetchone(); print(f'Today: {r[0]} settled | {r[1]} wins | {r[2]} USD')"
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check for new deliveries + Codex relays)
  - cat CODEX_OBSERVATIONS.md (mandatory — Codex code review findings. OPEN items need action.)
  NOTE: 3-WAY BRIDGE ACTIVE (S157). Codex ↔ CCA ↔ Kalshi. CCA is the router.
    Kalshi writes to: CODEX_OBSERVATIONS.md (Codex reads), POLYBOT_TO_CCA.md (CCA reads)
    Every session: write fresh ack to CODEX_OBSERVATIONS.md + POLYBOT_TO_CCA.md.

## CCA DELIVERIES (still relevant)
  - REQ-027 Monte Carlo COMPLETE (self-learning/monte_carlo_simulator.py)
  - REQ-054 Correlated Loss Analyzer COMPLETE (self-learning/correlated_loss_analyzer.py)
  - S199: mandate_monitor.py DEPLOYED to scripts/.

## KEY BUILDS (still relevant)
  - ETH ceiling 95c (IL-38-ETH, CCA REQ-53)
  - sports_sniper_v1 ESPN feed + main.py loop (paper, bug fixed S148)
  - Trinity Monte Carlo (src/models/monte_carlo.py)
  - mandate_monitor.py deployed scripts/ (S149, CCA S199)
  - AGENTS.md + CODEX_OBSERVATIONS.md (Codex CLI integration, S153)
  - KXETHD paper sniper: eth_daily_sniper_v1 (S158, commit 2ca2ca1)
