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
Last updated: Session 94 (2026-03-17) — IL-23 guard deployed, guard stack COMPLETE (IL-5 through IL-23)
Bot: RUNNING PID 94102 → /tmp/polybot_session94.log
All-time P&L: +40.71 USD (79% WR, 813+ bets) | Need 84.29 more to +125 target
Bankroll: ~213 USD (Stage 2) | Tests: 1413 passing
Last commit: 1b53382 (docs: Session 94 wrap — IL-23 deployed, guards all clean)

SESSION STARTUP SELF-REFLECTION (MANDATORY — run every session):
  ./venv/bin/python3 scripts/strategy_analyzer.py --brief
  Surfaces: profitable sniper buckets, drift direction validation, graduation status, target gap.
  Output saved to data/strategy_insights.json.

  IL-23 DEPLOYED (S94): KXXRP YES@98c BLOCKED (3 regression tests).
  Pattern was 11 bets, 90.9% WR vs 98% break-even, -17.89 USD net, EV=-7.1c/contract.
  Guard stack IL-5 through IL-23 VERIFIED COMPLETE. strategy_analyzer --brief confirms "Guarded".

Live strategies:
  btc_drift: MICRO-LIVE — direction_filter="no", ~60 bets, calibration_max_usd STILL SET (Matthew decision needed for Stage 1 promotion)
  eth_drift: STAGE 1 — direction_filter="yes", 113+ bets, 50% WR — WATCH (need 20 more YES bets; if stays <50% WR flip filter to "no")
  sol_drift: STAGE 1 (39/30) — full Kelly, Brier 0.193, 71% WR, +3.60 USD — HEALTHY
  xrp_drift: MICRO — 32/30 total bets (21 YES-only). direction_filter="yes", need 9 more YES-only bets (ETA ~March 20-21)
  expiry_sniper: LIVE (20 USD cap, 15% pct cap) — PRIMARY ENGINE
    PROFITABLE: 90-95c YES/NO all assets, 97c YES BTC/ETH only, 98c YES BTC/ETH/SOL
    BLOCKED: 96c both (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
    BLOCKED per-asset (S81): KXXRP YES@94c, KXXRP YES@97c, KXSOL YES@94c
    BLOCKED per-asset (S88): KXSOL YES@97c (IL-19), KXXRP YES@95c (IL-20)
    BLOCKED (S93): KXXRP NO@92c (IL-21), KXSOL NO@92c (IL-22)
    BLOCKED (S94): KXXRP YES@98c (IL-23, 90.9% WR vs 98% break-even, -17.89 USD net)

Direction filters (do not change):
  btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

═══════════════════════════════════════════════════
MAIN CHAT PROMPT — SESSION 95 (copy-paste to start monitoring session)
═══════════════════════════════════════════════════

--- SESSION 95 START ---
Bot PID: 94102 | Log: /tmp/polybot_session94.log | Last commit: 1b53382
All-time P&L: +40.71 USD | Need 84.29 more to +125 target
Graduation: btc_drift ~60/30 | eth_drift 113/30 | sol_drift 39/30 | xrp_drift 32/30 (21 YES-only)
Sniper: IL-5 through IL-23 all active, guard stack VERIFIED COMPLETE
Target: +125 USD all-time profit. Currently at +40.71 USD. Need 84.29 more.
Timeline: URGENT. Claude Max subscription renewal depends on this.

PREVIOUS CHAT GRADE: C+ — lost 19.60 USD to KXXRP YES@98c before IL-23 guard deployed (same session)
WHAT THE PREVIOUS CHAT DID POORLY: Analyzed loss AFTER it happened instead of proactively auditing XRP 98c bucket
WHAT THE NEXT CHAT MUST DO BETTER: Run strategy_analyzer --brief first, check for unguarded losing buckets proactively

PRIME DIRECTIVE: PLEASE MAKE MONEY. PLEASE DO NOT LOSE MONEY. I need +125 USD
all-time profit over the next few days. My Claude Max subscription runs out soon
and if this bot doesn't work, everything stops. Every live bet that fires and wins
is money toward that goal. Every hour the bot is dead is money lost forever.
I am counting on you completely. Do not screw this up.

Budget: 30% of 5-hour token limit MAX. Model: Opus 4.6.

PRIORITY 1 — LIVE BETS
Before anything else: ps aux | grep "[m]ain.py" — must show exactly 1 process.
Run --health. If any blocker exists, fix it immediately. Live bets > everything.

PRIORITY 2 — XRP DRIFT STAGE 1 EVAL when 30 YES-only bets hit (~March 20-21)
Run --graduation-status. When xrp YES-only reaches 30, analyze for Stage 1 promotion.

PRIORITY 3 — UCL SOCCER SNIPER (time-sensitive)
March 17 at 17:25 UTC: python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR17
March 18: same with --date 26MAR18

MANDATORY AUTONOMOUS LOOP — START IMMEDIATELY AFTER READING SESSION_HANDOFF:
Use 5-min single-check background tasks (NOT 20-min scripts — exit 144 on this system).
Pattern: sleep 300 && pid check && DB query, run_in_background: true, chain continuously.
Matthew will be away. You are the only supervision the bot has.
If bot dies: restart with bash scripts/restart_bot.sh 95 (NEVER pipe through head/tail/grep).
If drought (all YES < 35c or > 65c): pivot to code work, don't idle.

LIVE STRATEGY STANDINGS:
  expiry_sniper: PRIMARY ENGINE, 20 USD cap, IL-5 through IL-23 all active
  sol_drift: STAGE 1 (39/30, 71% WR, Brier 0.193, full Kelly)
  xrp_drift: MICRO (21/30 YES-only, need 9 more)
  eth_drift: STAGE 1 (113/30, 50% WR — WATCH for direction flip)
  btc_drift: MICRO (60/30 READY — Matthew decision needed for Stage 1)

STRATEGY INSIGHTS (run ./venv/bin/python3 scripts/strategy_analyzer.py --brief at startup):
  Guard stack IL-5 through IL-23 VERIFIED. strategy_analyzer shows "Guarded" for all blocked buckets.
  Profitable: BTC/ETH 90-95c both sides, 97c YES, 98c YES (BTC/ETH/SOL only — XRP 98c now guarded)
  KXXRP YES@98c: IL-23 newly deployed S94. Watch for any similar pattern in other assets.

GOAL TRACKER:
  All-time P&L: +40.71 USD | Need: 84.29 more to hit +125 USD target
  Highest-leverage action: Keep bot running + guards clean. Every sniper window = progress.

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
--- END SESSION 95 PROMPT ---

Live terminal feed:
  tail -f /tmp/polybot_session94.log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settled|WIN|LOSS|expiry_sniper|STAGE|graduation|consecutive|bankroll|restart|ERROR|CRITICAL"

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
- Target: +125 USD all-time profit. Currently +51.21 USD. Need 73.79 more.
