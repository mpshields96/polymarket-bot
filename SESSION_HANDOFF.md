# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-28 ~18:15 UTC (Session 156)
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
## Day 2 (March 28): +26.37 USD (ABOVE TARGET ✓ — 40 settled, 39W/1L, 97.5% WR)
## CONSTRAINTS: (1) Starting bankroll final — no new capital EVER. Matthew is explicit.
##              (2) FORBIDDEN: bankroll floor ≤ 20 USD.
##              (3) Do NOT ask Matthew for help. Use CCA for anything/everything.
## ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES ALL CONSERVATIVE CONSTRAINTS BELOW EXCEPT FLOOR.
## ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS. PERMANENT.
## ═══════════════════════════════════════════════════════════════════════════════════

## BOT STATE (S157 — 2026-03-28 ~19:20 UTC)
  Bot RUNNING PID 14783 → /tmp/polybot_session157.log
  All-time live P&L: +19.71 USD (was +12.31 at S157 start — +7.40 USD gained this session)
  Today March 28: +10.04 USD live (44 settled, 95% WR = 42 wins)
  Tests: 2017 passing. Last commit: 63b5337

  S157 KEY CHANGES:
  1. GAME-LEVEL DEDUP: sports_game_loop now tracks games not just tickers (prevented double-bet FLA/NYI)
     - _bet_games_today set added, persisted across restarts via db.open_live_tickers_for_strategy_prefix()
     - 4 new game-key tests + 4 new DB tests — all passing
  2. PRE-GAME WINDOW: tightened from 30min to 5min post-start (bookmaker signal stale vs live Kalshi price)
  3. SCANNER: Added politics/geopolitics series from CCA REQ-17 (KX538APPROVE, KXUKRAINE, KXNEWTARIFFS, etc.)
  4. CDT/UTC confusion lesson: machine logs in CDT (UTC-5) — 13:49 CDT = 18:49 UTC. Always account for timezone.
  5. CCA REQUEST 18 filed: sports_game sizing analysis (n=2 all-losses, 10 USD per bet vs daily_sniper 5 USD cap)

  LIVE BETS STATUS:
  - 3 sports_game_nhl bets open (OTT NO + NYI YES + FLA NO — games settle tonight)
    WARNING: FLA/NYI bets both live = double exposure on same game (19.49 USD combined stake)
    This was the LAST pre-dedup fire. Dedup now prevents future recurrence.
  - 1 daily_sniper open: KXBTCD-26MAR2816-T68199.99 NO (BTC at 66802 vs T=68200 — safe)

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making income, drop it.
  1. MANDATE (ongoing): 15-25 USD/day. Today = +10.04 USD live (BELOW 15 — 4 open bets).
     NHL games settling tonight + KXBTCD NO (BTC safe at 66802 vs T=68200) may push above 15.
  2. FROZEN PROCESS WATCH: Check log recency every cycle. >15min stale = restart.
     CRITICAL: Machine is in CDT (UTC-5). 14:xx in log = 19:xx UTC. Always account for timezone.
  3. Sports_game edge quality: n=5 total, n=2 settled (1W BOS/ 2L — see NBA losses). CCA REQ-18 filed.
     If NHL games all win tonight: n=5, better picture. If 0/3 NHL = investigate min_edge threshold.
     Consider lowering min_edge 5%→3% if <2 signals/day average over next 72h.
  4. CCA REQ-16+17+18: Check CCA_TO_POLYBOT.md for responses. Act on deliveries immediately.
  5. KXETHD expansion: daily_sniper validated at 98.6% WR (80+ bets). Gate reached.
     Todo added to .planning/todos.md. Build KXETHD loop when sports_game edge is understood.
  6. CODEX_OBSERVATIONS.md: check at session start for any open Codex items.

## STRATEGY STATUS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these strategies are tools, not laws.
  ⚠️ ALL 15-MINUTE CRYPTO MARKETS PERMANENTLY BANNED FROM LIVE. No exceptions. Ever.

  - sports_game_v1 (NBA/NHL/MLB): NEW LIVE ENGINE. 5-min poll, 15-80c, 5% edge threshold.
    First bets today (March 28). Settlement typically next day.
  - daily_sniper_v1: LIVE (5 USD cap). SPRT edge confirmed. 38 settled. 97.4% WR.
    ⚠️ Note: KXBTCD IS a daily crypto threshold market (NOT a 15-min direction market). ALLOWED.
  - weather: LIVE. HIGHNY/KXHIGHCHI etc. Signal fires regularly.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI).
  - sports_sniper_v1: PAPER-ONLY. ESPN polling. 0/20 fills. (This is FLB at 90c+ — same banned payoff structure. Keep paper for data only.)
  - expiry_sniper_v1: PAPER-ONLY. PERMANENTLY BANNED from live.
  - All 15-min crypto strategies (btc_drift, sol_drift, btc_imbalance etc): PAPER data only. LIVE=BANNED.

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

## RESTART COMMAND (S158)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session158.log 2>&1 &

## CRITICAL STARTUP CHECKS (S158)
  - cat bot.pid → get PID. Then tail -5 /tmp/polybot_session157.log — MUST show recent entries.
    If stale >15min: RESTART to session158.log (frozen process pattern — happened S151, S155, S157).
    ⚠️ TIMEZONE: Machine is CDT (UTC-5). Log timestamps like 14:xx = 19:xx UTC. Always convert.
  - FIRST: check today's P&L vs mandate target (15-25 USD):
    ./venv/bin/python3 -c "import sqlite3,calendar; from datetime import datetime; c=sqlite3.connect('data/polybot.db'); ts=calendar.timegm(datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0).timetuple()); r=c.execute('SELECT COUNT(*),SUM(CASE WHEN side=result THEN 1 ELSE 0 END),ROUND(SUM(pnl_cents)/100.0,2) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL',(ts,)).fetchone(); print(f'Today: {r[0]} settled | {r[1]} wins | {r[2]} USD')"
    If below 15 USD with <4hr left in UTC day: under ABSOLUTE FREEDOM — find more bets NOW.
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check for new deliveries + Codex relays)
  - cat CODEX_OBSERVATIONS.md (mandatory — Codex code review findings. OPEN items need action.)
  - cat ~/.claude/cross-chat/CODEX_TO_CLAUDE.md | tail -30 (via CCA relay — Codex durable notes to CCA)
  NOTE: 3-WAY BRIDGE ACTIVE (S157). Codex ↔ CCA ↔ Kalshi. CCA is the router.
    Kalshi writes to: CODEX_OBSERVATIONS.md (Codex reads), POLYBOT_TO_CCA.md (CCA reads)
    Codex writes to: CODEX_OBSERVATIONS.md (Kalshi reads), CODEX_TO_CLAUDE.md (CCA reads)
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
