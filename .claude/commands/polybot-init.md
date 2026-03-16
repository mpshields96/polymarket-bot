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
Last updated: Session 87 final wrap (2026-03-16) — monitoring clean, +14.56 USD today, -30.44 all-time
Bot: RUNNING PID 26391 → /tmp/polybot_session86.log
All-time P&L: -30.44 USD (today: +14.56 USD, 21 settled, 100% WR)
Bankroll: ~100 USD | Tests: 1348 passing, 3 skipped
Last commit: 5c45557 (feat: self-learning strategy analyzer + NCAA scanner verification)

SESSION STARTUP SELF-REFLECTION (NEW — run every session):
  ./venv/bin/python3 scripts/strategy_analyzer.py --brief
  Surfaces: profitable sniper buckets, drift direction validation, graduation status, target gap.
  Output saved to data/strategy_insights.json.

Live strategies:
  btc_drift: STAGE 1 — direction_filter="no", 49% WR (-10.76 USD), trend=IMPROVING
  eth_drift: STAGE 1 — direction_filter="yes", 49% WR (-24.41 USD), trend=DECLINING — watch
  sol_drift: GRADUATED — 30/30 bets, Brier 0.191, +1.23 USD — full Kelly active (calibration_max=None)
  xrp_drift: MICRO — 24/30 bets, Brier 0.253, -0.68 USD — needs 6 more
  expiry_sniper: LIVE (20 USD cap, 15% pct cap) — PRIMARY ENGINE (+14.56 USD today, 100% WR)
    PROFITABLE RANGE: 90-94c (+92.41 USD all-time), 95c (+33.52 USD all-time)
    BLOCKED: 96c both (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
    BLOCKED per-asset (S81): KXXRP YES@94c, KXXRP YES@97c, KXSOL YES@94c
    ACTIVE BUCKETS: 91c-95c BTC/ETH both sides, 97c YES all assets, 98c YES all assets

Direction filters (do not change):
  btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

Safety hooks (Pattern 1 + 2):
  PreToolUse: .claude/hooks/danger_zone_guard.sh — advisory Iron Laws check on 6 DANGER ZONE files
  PostToolUse: .claude/hooks/verify_revert.sh — auto-revert if tests fail after editing DANGER ZONE file
  BOUNDS.md: 18 Iron Laws with file:line, incident history, test references

RESEARCH QUALITY DIRECTIVE (Matthew S80 — MANDATORY):
  New edge research must meet SNIPER STANDARD or better:
  Named mechanism + Named counterparty + Different from sniper AND speed-play + Paper-test protocol
  Kalshi API scanning without structural hypothesis = data mining = NOT research.

Research state (S87):
  scripts/strategy_analyzer.py (NEW S87) — self-learning pattern detector, run --brief at startup
  scripts/soccer_candle_analyzer.py — UCL/EPL MID_GAME analysis via Kalshi candlestick API
    VALIDATED: FLB edge, 0/3 false positive rate at 90c, UCL 40% MID_GAME rate
    FIRST LIVE TEST: EPL BRE vs WOL (March 30), UCL QF (March 31 + April 1)
  scripts/ncaa_tournament_scanner.py — run March 17-18, 1 credit/call, Round 1 March 20-21
    NOTE: 64 KXNCAAMBGAME markets open as of March 16. 0 edges above 3% (lines not mature).
  scripts/weather_calibration.py — check again ~March 18-20, need 3-4 more weeks data
  scripts/cpi_release_monitor.py — run April 10, 08:30 ET
  Dead ends (cumulative): sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper,
    sniper maker mode, NCAA totals, KXMV parlay, NBA in-game sniper, BNB/BCH/DOGE 15M,
    KXBTCD hourly non-5PM, FOMC March 2026, non-crypto 90c+ markets, annual BTC range,
    KXBTCD near-expiry, hourly WR patterns, soccer underdogs below 60c pre-game
  Next: NCAA March 17-18, soccer UCL March 31/April 1, CPI April 10

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
- Target: +125 USD all-time profit. Currently -34.53 USD. Need +159.53 more.
