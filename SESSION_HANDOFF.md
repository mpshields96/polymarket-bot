# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-28 ~20:40 UTC (Session 158 wrap)
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

## BOT STATE (S160 wrap — 2026-03-29 ~03:35 UTC)
  Bot RUNNING PID 87224 → /tmp/polybot_session159.log
  All-time live P&L: +69.89 USD
  Bankroll: ~202 USD (Matthew confirmed)
  Tests: 2019 passing (3 skipped). Last commit: 1227433

  S160 SESSION RESULTS (monitoring continuation of S159):
  All-time P&L: +69.89 USD (unchanged — sniper at 50/50 cap, no new settled bets)
  To +125 USD milestone: 55.11 USD remaining
  Day 3 (March 29 UTC): 0 new bets. Sniper resets at 06:00 UTC (01:00 CDT) = ~2.5hr out.

  S160 KEY CHANGES / FINDINGS:
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
  Day 3 (March 29 UTC): started 00:00 UTC. Sniper fires at 06:00 UTC (01:00 CDT).
  To +125 USD milestone: 55.11 USD remaining (all-time 69.89)

  OPEN BETS: 0 (all settled)
  SNIPER: 50/50 cap (CST Day 2). Resets at 06:00 UTC (01:00 CDT). Cron watchdog active.

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making income, drop it.
  1. MANDATE (ongoing): 15-25 USD/day SUSTAIN. Day 2 = +60.04 USD (CRUSHED). Day 3 starts.
     Sniper resets at 06:00 UTC (01:00 CDT). Watch first Day 3 bets fire then.
  2. FROZEN PROCESS WATCH: Check log recency every cycle. >15min stale = restart.
     ⚠️ LIVENESS CHECK: use `kill -0 PID` not grep-pipe. Grep on missing log file = false alarm.
     ⚠️ TIMEZONE: Machine is CDT (UTC-5). Log 14:xx = 19:xx UTC. Always convert.
  3. CCA REQ-65 RESPONSE: 88c floor widening risk check. When received: evaluate with live
     data (only 1 bet at 89c — insufficient). Do NOT change floor until CCA responds.
  4. Sports_game calibration: n=6 settled (4W NHL / 2L NBA). NBA losses were at OLD 10 USD cap.
     At 2 USD cap: effectively 0 NBA data points. Cap stays 2 USD until n=30.
     NHL 4/4 wins at current cap. Keep watching both sports separately.
  5. KXETHD paper sniper: 5/5 wins (91-93c). n=5 too small. Need 15-20 bets before live eval.
     CCA REQ-62 delivered: use 92c ceiling (not 94c) when going live.
  6. +125 USD milestone: 55.11 USD remaining. At current pace (~30-60 USD/day), within 1-3 days.
  7. CODEX_OBSERVATIONS.md: check at session start.
  8. CCA REQ-64 (NBA loss investigation): still pending CCA response.

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

## RESTART COMMAND (S161)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session161.log 2>&1 &

## CRITICAL STARTUP CHECKS (S159)
  - kill -0 $(cat bot.pid) 2>/dev/null && echo "ALIVE" || echo "DEAD"  ← USE THIS, not grep
    ⚠️ NEVER use ps grep + && + tail — grep on missing log file = false alarm exit 1.
    If stale >15min in log: RESTART to session159.log (frozen process pattern — happened S151, S155, S157, S158).
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
