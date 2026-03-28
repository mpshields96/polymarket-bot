# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-28 ~17:45 UTC (Session 153)
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

## BOT STATE (S154 — 2026-03-28 ~19:40 UTC)
  Bot RUNNING PID 93047 → /tmp/polybot_session154b.log
  All-time live P&L: +9.67 USD (DB authoritative — prior summary had incorrect figure)
  Today March 28: 0 settled live so far (bot restarted mid-session during major pivot)
  Tests: 2002 passing, 3 skipped. Last commit: 73fd7b3

  S154 KEY CHANGES — MAJOR STRATEGIC PIVOT:
  1. ALL 15-MINUTE CRYPTO MARKETS PERMANENTLY BANNED FROM LIVE (Matthew standing directive)
     Banned: btc_lag, eth_lag, sol_lag, btc_drift, eth_drift, sol_drift, btc_imbalance,
             eth_imbalance, expiry_sniper, maker_sniper — all live_executor_enabled=False
     Reason: 3 consecutive days of losses despite high WR. FLB payoff asymmetry at 90c+
     destroyed daily income. NOT a statistics problem — structural dead end.
     Saved to: memory/feedback_15min_crypto_permanent_ban.md + learnings.md (severity 3)
  2. sports_game_loop BUILT AND LIVE:
     Pre-game NBA/NHL/MLB bookmaker arb. Price range 15-80c (NOT 90c+).
     Signal: Kalshi vs sharp bookmaker consensus (Pinnacle/DraftKings/FanDuel).
     Edge: retail crowd overweights favorites, underprices underdogs.
     Min edge: 5%. Live-enabled. Cap: 10 USD/bet.
  3. MLB support added: SportsFeed.get_mlb_games() + MLB city map + MLB code-to-city map
  4. commence_time filter: only bets on games starting within next 36 hours (not already played)
  5. CCA REQ-15 filed: economics markets audit + sports game validation + multi-day crypto ranges

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making income, drop it.
  1. MANDATE (ongoing): 15-25 USD/day. Sports game loop is now primary live engine.
     Monitor first few sports_game bets (settle next day typically — pre-game bets).
  2. FROZEN PROCESS WATCH: Check log recency (tail -5) every cycle. >15min stale = restart.
  3. CCA REQUEST 15: Economics markets audit + sports game validation (REQ-15A/B/C filed).
     Push CCA hard — these are the next untapped edges with correct payoff structure.
  4. CODEX_OBSERVATIONS.md: check at session start.
  5. Payoff framework: apply to all future strategy research — natural price range must be 20-75c.

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

## RESTART COMMAND (S154)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session154.log 2>&1 &

## CRITICAL STARTUP CHECKS (S154)
  - cat bot.pid → get PID. Then tail -5 /tmp/polybot_session153.log — MUST show recent entries.
    If stale >15min: RESTART to session154.log (frozen process pattern — happened S151).
  - FIRST: check today's P&L vs mandate target (15-25 USD):
    ./venv/bin/python3 -c "import sqlite3,calendar; from datetime import datetime; c=sqlite3.connect('data/polybot.db'); ts=calendar.timegm(datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0).timetuple()); r=c.execute('SELECT COUNT(*),SUM(CASE WHEN side=result THEN 1 ELSE 0 END),ROUND(SUM(pnl_cents)/100.0,2) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL',(ts,)).fetchone(); print(f'Today: {r[0]} settled | {r[1]} wins | {r[2]} USD')"
    If below 15 USD with <4hr left in UTC day: under ABSOLUTE FREEDOM — find more bets NOW.
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -50 (check for new deliveries)
  - Check CODEX_OBSERVATIONS.md for any Codex code review notes.

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
