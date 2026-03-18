SESSION STARTUP — fully autonomous, no confirmation needed.
Replaces copy-paste startup prompts. Run this at the start of every new session.
Updated automatically by /polybot-wrap and /polybot-wrapresearch at session end.

═══════════════════════════════════════════════════
STEP 1 — READ CONTEXT (mandatory, in this order)
═══════════════════════════════════════════════════
Read these files IN ORDER before doing anything else:
1. POLYBOT_INIT.md — full build instructions + live status
2. SESSION_HANDOFF.md — exact bot state, PID, log path, pending tasks, last commit
3. .planning/CHANGELOG.md — last 3 entries (what changed recently and WHY)
4. .planning/PRINCIPLES.md — before ANY strategy/risk parameter change
5. .planning/AUTONOMOUS_CHARTER.md — standing directives

If a research session was recent, also read:
6. .planning/EDGE_RESEARCH_S62.md — latest research findings

═══════════════════════════════════════════════════
STEP 2 — BOT STATUS CHECK
═══════════════════════════════════════════════════
Run: ps aux | grep "[m]ain.py"

If 0 processes AND SESSION_HANDOFF says bot should be running:
  → Restart immediately using the restart command in SESSION_HANDOFF.md
If 0 processes AND SESSION_HANDOFF says bot STOPPED (Matthew directive):
  → Note "STOPPED per Matthew". Do NOT restart unless he says to.
If 1 process:
  → Confirm PID matches bot.pid. Good to go.
If 2+ processes:
  → Kill all, restart clean. Never leave duplicates.

If bot is running, also run:
  ./venv/bin/python3 main.py --health
  ./venv/bin/python3 main.py --report

═══════════════════════════════════════════════════
STEP 3 — ANNOUNCE STATE (2-3 lines max)
═══════════════════════════════════════════════════
Tell Matthew (or just log if autonomous):
  - Bot status: RUNNING PID X / STOPPED
  - Today P&L + all-time P&L
  - Any blockers from --health
  - What SESSION_HANDOFF says the next priority is

═══════════════════════════════════════════════════
STEP 4 — ROUTE TO WORK MODE
═══════════════════════════════════════════════════
Based on SESSION_HANDOFF.md pending tasks and Matthew's instructions:

IF bot is running + Matthew is away:
  → Start autonomous monitoring loop immediately (see /polybot-auto)
  → 5-min background checks, chain indefinitely

IF bot is stopped + research mode:
  → Pick highest-impact research task from SESSION_HANDOFF
  → Work inline, no expensive agents

IF Matthew gives a specific task:
  → Do that task. Use gsd:quick for implementation.

IF no clear direction:
  → Read SESSION_HANDOFF pending tasks, pick the highest-impact one
  → Default to gsd:quick + TDD

═══════════════════════════════════════════════════
CURRENT STATE (auto-updated by wrap commands)
═══════════════════════════════════════════════════
Last updated: Session 103 (2026-03-18 12:32 UTC) — S103 monitoring wrap, 2 new guards activated, +24.56 USD today
Bot: RUNNING PID 14095 → /tmp/polybot_session103.log
All-time P&L: +12.67 USD (POSITIVE) | Need 112.33 more to +125 target
Bankroll: ~220 USD | Tests: 1565 passing
Last commit: 859cee1 (docs: S103 research wrap — FLB analysis complete)

SESSION STARTUP SELF-REFLECTION (MANDATORY — run every session):
  ./venv/bin/python3 scripts/strategy_analyzer.py --brief
  Surfaces: profitable sniper buckets, drift direction validation, graduation status, target gap.

  SELF-IMPROVEMENT CHAIN ACTIVE (all 7 dims since S101):
    Dim 1a/1b: auto_guard_discovery.py — 2 new guards discovered S103 (KXXRP NO@95c + KXSOL NO@93c)
    Dim 2-3: BayesianDriftModel + settlement_loop update — accumulating observations
    Dim 4: generate_signal() uses Bayesian predict when n_obs >= 30 (n=4+, needs 26 more)
    Dim 5: guard_retirement_check.py — tracking 16 IL guards (all warming up, 0-3 paper bets)
    Dim 7: strategy_drift_check.py — PH test, eth_drift PH=3.30 (recovering)
    Bayesian posterior: 4 observations (needs 30 to activate override — accumulating passively)

Live strategies:
  btc_drift: MICRO-LIVE — direction_filter="no", 65 bets, 47% WR UNDERPERFORMING
  eth_drift: STAGE 1 — direction_filter="yes", 144 bets, 49% WR, PH alert recovering
  sol_drift: STAGE 1 — 41 bets, 71% WR, Brier 0.196, +3.84 USD HEALTHY
  xrp_drift: MICRO — 45 bets, 50% WR, direction_filter="yes"
  expiry_sniper: PRIMARY ENGINE — IL-5 through IL-32 + 2 auto-guards, 85% WR today, +24.56 USD
    PROFITABLE: 90-95c YES/NO all assets (minus guarded buckets)
    BLOCKED IL-5 through IL-32: standard static guards (unchanged)
    AUTO-GUARDED: KXXRP NO@95c (n=19, activated S103), KXSOL NO@93c (n=12, activated S103)
    FLOOR: sub-90c blocked | CEILING: above 95c blocked | PER-WINDOW: 2 bets/30 USD

Direction filters (do not change):
  btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

═══════════════════════════════════════════════════
MAIN CHAT PROMPT — SESSION 104 (copy-paste to start monitoring session)
═══════════════════════════════════════════════════

--- SESSION 104 START ---
Bot PID: 14095 | Log: /tmp/polybot_session103.log | Last commit: 859cee1
All-time P&L: +12.67 USD | Need 112.33 more to +125 target
Guards: IL-5 through IL-32 + KXXRP NO@95c + KXSOL NO@93c (2 auto-guards active)
Today rate: +24.56 USD (March 18 through 12:27 UTC — 67 settled, 85% WR)

PREVIOUS CHAT GRADE: B+ — overnight monitoring, caught 2 guard triggers, restarted bot twice
S103 KEY EVENTS: KXXRP NO@95c and KXSOL NO@93c added as auto-guards after losses
WHAT THE NEXT CHAT MUST DO FIRST: Check /tmp/ucl_sniper_mar18.log after 20:00 UTC (launcher fires 17:21 UTC)

PRIME DIRECTIVE: PLEASE MAKE MONEY. PLEASE DO NOT LOSE MONEY. I need +125 USD
all-time profit. Every live bet that fires and wins is money toward that goal.
Every hour the bot is dead is money lost forever.

Budget: 30% of 5-hour token limit MAX. Model: Opus 4.6.

PRIORITY 1 — LIVE BETS
Before anything else: ps aux | grep "[m]ain.py" — must show exactly 1 process.
Confirm guard count: grep "Loaded.*auto-discovered" /tmp/polybot_session103.log | tail -1
MUST show "Loaded 2 auto-discovered guard(s)" — if only 1, run auto_guard_discovery.py.

PRIORITY 2 — UCL MARCH 18 LOG (URGENT after 20:00 UTC)
Check /tmp/ucl_sniper_mar18.log — launcher fires 17:21 UTC.
Teams eligible: BAR, BMU, LFC. See if any sniper bets fired, settled, wins/losses.

PRIORITY 3 — AUTO-GUARD SCAN
Run ./venv/bin/python3 scripts/auto_guard_discovery.py — confirm 0 new guards needed.
If new guard found: update auto_guards.json + restart bot immediately.

MANDATORY AUTONOMOUS LOOP — START IMMEDIATELY AFTER READING SESSION_HANDOFF:
Use 5-min single-check background tasks (NOT 20-min scripts — exit 144 on this system).
Pattern: sleep 300 && pid check && DB query, run_in_background: true, chain continuously.
Matthew will be away. You are the only supervision the bot has.
Restart command if bot dies:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session104.log 2>&1 &

LIVE STRATEGY STANDINGS:
  expiry_sniper: PRIMARY ENGINE, all guards active, 85% WR today, +24.56 USD
  sol_drift: STAGE 1 (41/30, 71% WR, Brier 0.196) — HEALTHY
  xrp_drift: MICRO (45/30, 50% WR)
  eth_drift: STAGE 1 (144/30, 49% WR, PH recovering)
  btc_drift: MICRO (65/30, 47% WR UNDERPERFORMING)
  Bayesian posterior: 4 observations (needs 30 to activate — accumulating passively)

GOAL TRACKER:
  All-time P&L: +12.67 USD | Need: 112.33 more to hit +125 USD target
  Today rate: +24.56 USD/day (March 18) | Est. days at current rate: ~5
  Highest-leverage action: Keep bot running, guards clean, run auto_guard_discovery.py each session.

FONT RULES (mandatory — violations = chat terminated):
  RULE 1: NEVER markdown table syntax (| --- |)
  RULE 2: NEVER dollar signs in prose. Use "40 USD" not the dollar symbol

Read in this order:
1. POLYBOT_INIT.md
2. SESSION_HANDOFF.md
3. .planning/AUTONOMOUS_CHARTER.md
4. .planning/CHANGELOG.md last entry
5. .planning/PRINCIPLES.md

Go. Start monitoring. Make money. Don't let the bot die.
--- END SESSION 104 PROMPT ---

Live terminal feed:
  tail -f /tmp/polybot_session103.log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settled|WIN|LOSS|expiry_sniper|STAGE|graduation|consecutive|bankroll|restart|ERROR|CRITICAL"

═══════════════════════════════════════════════════
RESEARCH CHAT PROMPT — SESSION 95 (copy-paste to start research session)
═══════════════════════════════════════════════════

--- SESSION 95 RESEARCH START ---
Bot: RUNNING PID 94102 | Log: /tmp/polybot_session94.log | Last commit: 1b53382
All-time P&L: +40.71 USD | Need 84.29 more to +125 target
This is a RESEARCH session. Do NOT touch bot monitoring — main chat handles that.

CONTEXT FILES (read in order):
1. POLYBOT_INIT.md
2. SESSION_HANDOFF.md
3. .planning/CHANGELOG.md last entry
4. .planning/PRINCIPLES.md

TOP RESEARCH PRIORITIES:
1. NCAA Tournament scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03
   Round 1 tip-offs March 20-21. Lines mature now. 96 KXNCAAMBGAME markets open.
2. eth_drift direction filter watch — 113 bets at 50% WR. Need 20 more YES bets.
   If still <50% WR after 20 more, flip direction_filter from "yes" to "no".
3. strategy_analyzer.py update — add per-asset guard parsing (IL-23 shows as display artifact "Losing 98c")
4. btc_drift Stage 1 promotion — 60/30 bets READY. calibration_max_usd still set.
   Matthew explicit decision needed. Run --graduation-status to get current Brier.
5. CPI speed-play prep — scripts/cpi_release_monitor.py, runs April 10 08:30 ET

DEAD ENDS (do not re-investigate):
  sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper, sniper maker mode,
  NCAA totals/spreads, KXMV parlay, NBA in-game, BNB/BCH/DOGE 15M,
  KXBTCD hourly non-5PM, FOMC March 2026, non-crypto 90c+ markets,
  annual BTC range, weather ALL strategies (60 paper bets, 8-25% WR)

FONT RULES (mandatory — violations = chat terminated):
  RULE 1: NEVER markdown table syntax (| --- |)
  RULE 2: NEVER dollar signs in prose. Use "40 USD" not the dollar symbol

Use /polybot-autoresearch to start.
--- END SESSION 95 RESEARCH PROMPT ---

Safety hooks (Pattern 1 + 2):
  PreToolUse: .claude/hooks/danger_zone_guard.sh — advisory Iron Laws check on 6 DANGER ZONE files
  PostToolUse: .claude/hooks/verify_revert.sh — auto-revert if tests fail after editing DANGER ZONE file
  BOUNDS.md: 18 Iron Laws with file:line, incident history, test references

RESEARCH QUALITY DIRECTIVE (Matthew S80 — MANDATORY):
  New edge research must meet SNIPER STANDARD or better:
  Named mechanism + Named counterparty + Different from sniper AND speed-play + Paper-test protocol
  Kalshi API scanning without structural hypothesis = data mining = NOT research.

Research state (S90):
  scripts/strategy_analyzer.py — self-learning pattern detector, run --brief at startup
  scripts/soccer_candle_analyzer.py — UCL/EPL MID_GAME analysis via Kalshi candlestick API
    VALIDATED: FLB edge, 0/3 false positive rate at 90c, UCL 40% MID_GAME rate
    FIRST LIVE TEST: EPL BRE vs WOL (March 30), UCL QF (March 31 + April 1)
  scripts/ncaa_tournament_scanner.py — run March 17-18, 1 credit/call, Round 1 March 20-21
    NOTE: 96 KXNCAAMBGAME markets open as of March 16. 0 edges > 3%. Lines mature March 17.
  scripts/weather_calibration.py — FAILING (25-57% WR vs 80%+ needed). Do NOT live trade weather.
    Continue paper for calibration. Check at 20+ bets per city (end of April).
  scripts/cpi_release_monitor.py — run April 10, 08:30 ET
  BOT CRASH ROOT CAUSE FOUND (S90 monitoring): Binance.US WebSocket 1011 keepalive timeout
    ALL 4 feeds disconnected simultaneously → process exit. Crash fix: return_exceptions=True
    deployed (commit 2d1ffed). Check data/polybot_crash.log after any unexpected restart.
  Dead ends (cumulative): sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper,
    sniper maker mode, NCAA totals, KXMV parlay, NBA in-game sniper, BNB/BCH/DOGE 15M,
    KXBTCD hourly non-5PM, FOMC March 2026, non-crypto 90c+ markets, annual BTC range,
    KXBTCD near-expiry, hourly WR patterns, soccer underdogs below 60c pre-game,
    WEATHER LIVE TRADING (paper calibration failing — 25-57% WR vs 80%+ needed)
  Next: NCAA March 17-18 (lines now mature), soccer UCL March 31/April 1, CPI April 10

IMPORTANT — MARCH 1 HARD STOP IN --health: HISTORICAL, NOT BLOCKING.
  30% lifetime stop was DISABLED in S34. No kill_switch.lock file. Safe to restart.

═══════════════════════════════════════════════════
FONT RULES (mandatory — Matthew terminates chat for violations)
═══════════════════════════════════════════════════
RULE 1: NEVER markdown table syntax (| --- |)
RULE 2: NEVER dollar signs in prose. Use "40 USD" not the symbol

═══════════════════════════════════════════════════
STANDING DIRECTIVES
═══════════════════════════════════════════════════
- Fully autonomous — bypass permissions ACTIVE
- Never ask for confirmation on: tests, reads, edits, commits, restarts, reports, research
- Do work first, summarize after
- Matthew is a doctor with a new baby — no time for back-and-forth
- Two parallel chats may run — keep overhead under 15% per chat
- Loading screen tip at end of every response (one recommendation)
- Target: +125 USD all-time profit. Currently -4.96 USD. Need 129.96 more.
