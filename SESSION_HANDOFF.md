# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-04-02 (S252 CCA init — bot status confirmed, CCA Phase 6 complete)
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

## BOT STATE (S166 wrap — 2026-04-07 00:40 UTC)
  Bot STOPPED (Matthew directive — overhaul plan mode). Log: /tmp/polybot_session166.log
  All-time live P&L: +129.91 USD | Today CST April 6: -1.81 USD (16 settled, 87.5% WR)
  April CST: +60.02 USD (97 settled, 97.9% WR)
  Tests: 3 failed (test_fomc + test_unemployment — pre-existing), 2101 passing. Last commit: 534e3b6
  HARD_MAX ramp: 3/50 clean bets (next gate: 40 USD HARD_MAX)
  ⚠️ NOTE: all-time dropped from 139.10 to 129.91 — eth_daily_sniper + in-game MLB losses this session

  S166 KEY FINDINGS:
  1. CONFIRMED BUGS IN SPORTS LOOP (do NOT restart without fixing these first):
     BUG A — IN-GAME BETTING: Bot placed 6 MLB bets on April 6 games already 5+ hours in.
       Tickers: 14318 (DET-MIN 19:40), 14319 (STL-WSH 18:45), 14320 (SD-PIT 18:40),
                14321 (MIL-BOS 18:45), 14322 (CIN-MIA 18:40), 14323 (KC-CLE 18:10)
       Root cause: _future_games() checks Odds API time, _match_game() ±1 day tolerance
       means April 7 Odds API game matches April 6 Kalshi market. Kalshi date not verified.
       Fix location: main.py sports_game_loop inner market loop — add _parse_ticker_date check.
     BUG B — 72h HORIZON / CAP BURN: Future games (Apr 7-9) consume daily cap before tonight.
       Fix: sort markets by game date ascending + reduce horizon 72h → 24h.
     BUG C — ETH DAILY SNIPER NEGATIVE EV: At 91c, EV = -0.50/bet. 7 live bets = -4.11 USD.
       Fix: disable live execution pending ceiling fix (85-88c recommended).
     BUG D — NBA 0% WR (-19.67 USD on 2 bets): cause unknown. Disable live until investigated.
  2. OVERHAUL PLAN written: .planning/OVERHAUL_PLAN_S166.md — 4-phase plan, read before coding.
  3. CCA REQ-082 posted (URGENT): 5-part audit mandate (analytics, NBA investigation, ETH fix,
     dynamic series discovery, BTC sniper sub-bucket analysis).
  4. Codex CLAUDE_TO_CODEX.md: 5 bug fix tasks with exact code locations.
  5. CST timezone now permanent across all chats (standing-directives.md updated).
  6. max_daily_bets already updated to 30 in main.py.

  OPEN LIVE BETS (19 total):
  SNIPER (settle April 7 ~21:00 UTC):
    14330: KXBTCD-26APR0621 YES@93c — 9.30 USD
    14331: KXBTCD-26APR0621 YES@92c — 9.20 USD
    14332: KXETHD-26APR0621 YES@91c — 9.10 USD (NEGATIVE EV — this strategy should be disabled)
    14333: KXBTCD-26APR0621 YES@90c — 9.90 USD
  UCL (settle April 14-15):
    14215: KXUCLGAME-26APR15BMURMA BMU NO@44c
    14216: KXUCLGAME-26APR14ATMBAR BAR YES@48c
    14224: KXUCLGAME-26APR14LFCPSG PSG YES@35c
  MLB future bets (April 7-9) — likely fine:
    14208: DET-MIN April 7 MIN YES@44c | 14303: MIL-BOS April 7 MIL YES@43c
    14242: HOU-COL April 8 HOU YES@58c | 14280: DET-MIN April 8 MIN YES@47c
    14317: PHI-SF April 8 PHI YES@53c | 14316: DET-MIN April 9 DET YES@54c
  MLB IN-GAME BETS April 6 (PROBLEMATIC — games already over/finishing):
    14318: DET-MIN April 6 19:40 UTC MIN NO@43c (bet placed 23:46 UTC)
    14319: STL-WSH April 6 18:45 UTC STL YES@25c
    14320: SD-PIT April 6 18:40 UTC PIT YES@46c
    14321: MIL-BOS April 6 18:45 UTC MIL YES@20c
    14322: CIN-MIA April 6 18:40 UTC MIA YES@37c
    14323: KC-CLE April 6 18:10 UTC CLE YES@37c

  OPEN LIVE BETS (12 total):
  SETTLING TONIGHT at 22:00 UTC (April 6):
    14305: KXETHD-26APR0618-T2099.99 YES@91c → ETH above 2099.99 at 18:00 ET
    14313: KXBTCD-26APR0618-T69899.99 NO@92c → BTC below 69899.99 at 18:00 ET
    14314: KXETHD-26APR0618-T2139.99 YES@91c → ETH above 2139.99 at 18:00 ET (2nd ETH bet)
    14315: KXBTCD-26APR0618-T69799.99 NO@92c → BTC below 69799.99 at 18:00 ET (2nd BTC bet)
  IN PROGRESS (CHC game started ~16:10 ET):
    14312: KXMLBGAME-26APR061610CHCTB-CHC YES@23c → Cubs win? (long shot)
  SETTLING APRIL 7:
    14208: KXMLBGAME-26APR071940DETMIN-MIN YES@44c → Minnesota Twins (19:40 ET)
    14303: KXMLBGAME-26APR071845MILBOS-MIL YES@43c → Milwaukee Brewers (18:45 ET)
  SETTLING APRIL 8:
    14242: KXMLBGAME-26APR081510HOUCOL-HOU YES@58c → Houston Astros (15:10 ET)
    14280: KXMLBGAME-26APR081940DETMIN-MIN YES@47c → Minnesota Twins (19:40 ET)
  SETTLING APRIL 14-15 (UCL):
    14215: KXUCLGAME-26APR15BMURMA-BMU NO@44c → Bayern Munich loses? (Apr 15)
    14216: KXUCLGAME-26APR14ATMBAR-BAR YES@48c → Barcelona wins (Apr 14)
    14224: KXUCLGAME-26APR14LFCPSG-PSG YES@35c → PSG wins (Apr 14)

  PENDING TASKS (priority order — OVERHAUL MODE):
  ⚠️ DO NOT RESTART BOT until Phase 1 bugs are fixed. Read OVERHAUL_PLAN_S166.md first.

  PHASE 1 — STOP THE BLEEDING (fix ALL before restarting):
  1. Fix BUG A (in-game betting): sports_game_loop inner market loop, add after parsed=parse_kalshi_game_ticker(ticker):
       from src.strategies.sports_game import _parse_ticker_date as _ptd
       _kg_dt = _ptd(ticker)
       if _kg_dt is not None and _kg_dt < (_now_ts - timedelta(minutes=5)):
           logger.warning("[sports_game] SKIPPING IN-GAME %s", ticker)
           continue
  2. Fix BUG B (horizon + sort): After markets = await kalshi.get_markets(...):
       markets = sorted(markets, key=lambda m: _parse_ticker_date(m.ticker) or datetime.max.replace(tzinfo=timezone.utc))
       Add horizon check: if (kalshi_date - _now_ts).total_seconds() > 24*3600: continue
  3. Fix BUG C (ETH daily sniper): In main.py, set live_executor_enabled=False for eth_daily_sniper_loop
  4. Fix BUG D (NBA): Remove sports_game_nba_v1 from live execution, paper only
  5. Fix dedup reset: sports_game_loop ~line 2230, change UTC date to CST date using timedelta(hours=-6)
  6. Run tests, commit, then restart bot to Session 167

  PHASE 2 — WAIT FOR CCA (concurrent with bot running):
  7. Read REQ-082 response from CCA (bet analytics audit, NBA investigation, ETH fix recommendation)
  8. Economics CPI April 10: confirm KXCPI markets open April 8, run cpi_release_monitor.py
  9. Investigate the 6 in-game MLB bets that settled (what were the outcomes?)

  BACKGROUND CONTEXT:
  - OVERHAUL_PLAN_S166.md: full 4-phase overhaul plan (read before any strategy decisions)
  - daily_sniper is the ONLY strategy making money (+118.70 all-time). Protect it.
  - April 13 deadline still active: 3 live types (daily_sniper, eth_daily_sniper, sports_game)
    eth_daily_sniper counts but is losing — fix or replace with economics_sniper

  ⚠️ SPORTS EXPANSION MANDATE (Matthew directive S165 — PERMANENT for all future chats):
  "Steal and clone literally anything from agentic-rd-sandbox to help sportsbetting on Kalshi."
  Source: /Users/matthewshields/Projects/agentic-rd-sandbox/core/
  Plan: .planning/SPORTS_EXPANSION_PLAN.md (6 phases over multiple sessions)
  CCA coordinates on Phases 2-5. Future Kalshi chats own wire-in + validation.
  Phase 1 DONE. Phase 2 = efficiency_feed.py integration (next session).

  RESTART COMMAND (Session 167 — ONLY AFTER Phase 1 bugs fixed):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session167.log 2>&1 &

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
