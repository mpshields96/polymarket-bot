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

## BOT STATE (S158 wrap — 2026-03-28 ~20:40 UTC)
  Bot RUNNING PID 50933 → /tmp/polybot_session158.log
  All-time live P&L: +51.69 USD (was +19.71 at S158 start — +31.98 USD gained today)
  Today March 28: +60.04 USD live (42 settled, 100% WR)
  Tests: 2022 passing. Last commit: 073f90c

  S158 KEY CHANGES:
  1. SPORTS_GAME CAP REDUCED: 10→2 USD (CCA REQ-18: n<5, insufficient calibration). Commit 0c49994.
  2. KXETHD PAPER SNIPER BUILT: eth_daily_sniper_v1 active. make_eth_daily_sniper() factory added.
     daily_sniper_loop parameterized (series_ticker + loop_name + coin_feed). 5 tests added.
     ETH session open: 2026.07 USD. Paper-only, 5/day cap. Commit 2ca2ca1.
  3. ALL 3 NHL BETS WON: OTT NO +12.65 + NYI YES +9.80 + FLA NO +8.93 = +31.38 USD windfall.
     Double exposure (FLA/NYI same game) worked in our favor. Dedup now active (S157).
  4. CCA REQ-62 filed: KXETHD structural analysis (volume, ETH vs BTC FLB).
  5. LIVENESS CHECK GOTCHA: use `kill -0 PID` not grep-pipe for bot existence checks.
     Grep + `&&` + missing log file = silent false-alarm. Cost: unnecessary restart attempt.

  5-DAY MANDATE STATUS:
  Day 1 (March 27): +6.56 USD (settled data — below target)
  Day 2 (March 28): +60.04 USD — CRUSHED mandate (target 15-25 USD) ✓
  To +125 USD milestone: 73.31 USD remaining

  OPEN BETS: 0 live bets open

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making income, drop it.
  1. MANDATE (ongoing): 15-25 USD/day SUSTAIN. Day 2 = +60.04 USD (CRUSHED). Keep system running.
     Day 3 starts at midnight UTC (19:00 CDT tonight). Daily sniper resets then.
     NEXT CHAT PRIORITY: maintain daily_sniper health. Watch first bets of Day 3.
  2. FROZEN PROCESS WATCH: Check log recency every cycle. >15min stale = restart.
     CRITICAL: Machine is CDT (UTC-5). 14:xx in log = 19:xx UTC. Always account for timezone.
     ⚠️ LIVENESS CHECK: use `kill -0 PID` not grep-pipe. Grep on missing log file = false alarm.
  3. Sports_game calibration: n=5 settled (3W NHL / 2L NBA). Cap reduced to 2 USD/bet.
     With dedup + 5min window + 2 USD cap, strategy is correctly sized for calibration phase.
     Goal: reach n=30 settled. Raise cap when Brier < 0.30.
  4. KXETHD paper sniper: ACTIVE as of S158. eth_daily_sniper_v1, paper-only, max 5/day.
     Monitor first 10 bets. CCA REQ-62 pending for structural analysis.
  5. CCA REQ-62: KXETHD analysis (ETH vs BTC FLB, volume 64K sufficient?). Act when received.
  6. +125 USD milestone: 73.31 USD remaining. At current pace (~30-60 USD/day), within 1-3 days.
  7. CODEX_OBSERVATIONS.md: check at session start.

## STRATEGY STATUS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these strategies are tools, not laws.
  ⚠️ ALL 15-MINUTE CRYPTO MARKETS PERMANENTLY BANNED FROM LIVE. No exceptions. Ever.

  - sports_game_v1 (NBA/NHL/MLB): NEW LIVE ENGINE. 5-min poll, 15-80c, 5% edge threshold.
    n=5 settled (3W NHL / 2L NBA). Cap at 2 USD/bet. Goal: n=30, then raise cap.
  - daily_sniper_v1: LIVE (5 USD cap). SPRT edge confirmed (lambda=+15.205). 39 settled today. 100% WR.
    ⚠️ Note: KXBTCD IS a daily crypto threshold market (NOT a 15-min direction market). ALLOWED.
  - eth_daily_sniper_v1: PAPER-ONLY. Active as of S158. 0 bets so far (needs KXETHD at 90-94c).
  - weather: LIVE. HIGHNY/MIA/DEN/CHI/LAX signals firing.
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

## RESTART COMMAND (S159)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session159.log 2>&1 &

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
