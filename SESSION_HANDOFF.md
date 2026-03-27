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

## BOT STATE (S153 — 2026-03-28 ~17:45 UTC)
  Bot RUNNING PID 95371 → /tmp/polybot_session153.log
  All-time live P&L: +40.17 USD
  March 28 Day 2 (ended 17:45 UTC, still running): +26.37 USD (40 settled, 39W/1L, 97.5% WR)
    - expiry_sniper: 18/18 wins +19.35 USD
    - daily_sniper: 10/10 wins +4.30 USD
    - sol_drift: 12 bets pending settlement
  Tests: 2002 passing, 3 skipped. Last commit: TBD (S153 test fixes pending)
  Post-guard clean streak: 113/200 (next gate at 200 → HARD_MAX auto-raise to 60 USD)

  S153 KEY CHANGES:
  1. HARD_MAX auto-raised 35→50 USD (gate 100 post-guard clean bets reached at 108 — pre-authorized)
  2. test_kill_switch.py: tests updated for HARD_MAX=50 USD
  3. test_security.py: test renamed + updated for 50 USD; shebang false positive fix
  4. AGENTS.md created (Codex CLI integration — reads project rules)
  5. CODEX_OBSERVATIONS.md created (Codex review output file — check each session)
  6. MATTHEW_DIRECTIVES.md: monthly income directive + compounding extrapolation appended
  7. Deadline extended to April 3 (downtime allowance from Matthew)
  8. SPRT/CUSUM: expiry_sniper EDGE CONFIRMED (lambda=+17.538, E_n=41M, CUSUM S=2.030)
     daily_sniper EDGE CONFIRMED (lambda=+5.317, E_n=203.8)
     eth_drift DRIFT ALERT (S=15.0) — already DISABLED, not a blocker
  9. Day 2 mandate target MET: +26.37 USD (above 25 ceiling)

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making 15-25 USD/day, drop it and find a better bet instead.
  1. MANDATE DAY 3 (March 29): Target 15-25 USD. Check P&L vs mandate at startup.
     Day 1: +6.56 USD. Day 2: +26.37 USD. Compounding working — all-time +40.17 USD.
  2. FROZEN PROCESS WATCH: Check log recency (tail -5) every cycle. ps alone misses frozen.
     Freeze pattern: log stale >15min = restart to session154.log.
  3. Post-guard clean bets: 113/200. 87 more → gate fires → HARD_MAX auto-raises to 60 USD.
     Pre-authorized by Matthew (S140/S142/S153 pattern). Just log when it fires.
  4. CODEX_OBSERVATIONS.md: check at session start. Codex may have filed code review notes.
  5. CCA audit request (UPDATE 59): bet_analytics.py P&L pipeline integrity. Run and respond.
  6. CCA REQUEST → REQ-027 simulation tools: push every session if not delivered.
  7. Monthly income compounding: at current rate (~20 USD/day), ~12 days to self-sustaining (250 USD/month).

## STRATEGY STATUS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these strategies are tools, not laws.

  - expiry_sniper_v1: PRIMARY ENGINE. SPRT lambda=+17.538, E_n=41M EDGE CONFIRMED. CUSUM S=2.030 stable.
    Ceiling: 93c BTC/SOL, 95c ETH. Floor: 90c. 08:xx blocked.
    Day 2: 18/18 wins +19.35 USD.
  - daily_sniper_v1: LIVE (5 USD cap). SPRT lambda=+5.317, E_n=203.8 EDGE CONFIRMED.
    38 settled, 97.4% WR, +5.35 USD all-time. Cap confirmed at 5 USD.
  - sol_drift_v1: LIVE. SPRT lambda=+2.277 edge confirmed. CUSUM S=1.800 stable.
  - sports_sniper_v1: PAPER-ONLY. ESPN polling every 3 min. 0/20 fills.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI).
  - eth_drift_v1: DISABLED (min_drift_pct=9.99). DRIFT ALERT S=15.0 — expected (disabled for this reason).
  - btc_drift_v1/xrp_drift_v1: DISABLED (min_drift_pct=9.99).

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
