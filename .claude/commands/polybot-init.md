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
Last updated: Session 80 (2026-03-15) — RESEARCH SESSION
Bot: RUNNING PID 68296 → /tmp/polybot_session76.log (NOT session79.log)
All-time P&L: -18.88 USD | Session gain: +10.60 USD (125 bets, 94% WR)
Bankroll: ~131 USD | Tests: 1281 passing
Last commit: abfdb49 (S80 research wrap — research quality directive)

Live strategies:
  btc_drift: STAGE 1 (5 USD cap) — direction_filter="no"
  eth_drift: STAGE 1 (5 USD cap) — direction_filter="yes"
  sol_drift: STAGE 1 (5 USD cap) — 29/30 bets, Brier 0.184, +6.07 USD — NEEDS 1 MORE BET
    When 30th bet settles: remove calibration_max_usd=5.0 → None in main.py, restart
    Don't require limiting_factor==kelly — pct_cap governs at current bankroll
  xrp_drift: MICRO — 20/30 bets, Brier 0.270, -1.71 USD
  expiry_sniper: LIVE (20 USD cap, 15% pct cap) — ~320+ bets, PROFITABLE CORE
    BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
    ACTIVE BUCKETS: 91c-95c both sides (100% WR), 97c YES (100% WR), 98c YES (100% WR)

Direction filters (do not change):
  btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

RESEARCH QUALITY DIRECTIVE (Matthew S80 — MANDATORY):
  New edge research must meet SNIPER STANDARD or better:
  Named mechanism + Named counterparty + Different from sniper AND speed-play + Paper-test protocol
  Kalshi API scanning without structural hypothesis = data mining = NOT research.

Research state (S80):
  scripts/ncaa_tournament_scanner.py — run March 17-18, 1 credit/call, Round 1 March 20-21
  scripts/weather_calibration.py — check paper bets ~04:00 UTC March 16 (10 pending)
  scripts/cpi_release_monitor.py — run April 10, 08:30 ET (BLS quota burned — do NOT run before then)
  Dead ends (cumulative): sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper,
    sniper maker mode, NCAA totals, KXMV parlay, NBA in-game sniper, BNB/BCH/DOGE 15M,
    KXBTCD hourly non-5PM, FOMC March 2026, non-crypto 90c+ markets, annual BTC range,
    KXBTCD near-expiry (always 99c/0c or 50c — no 90-98c zone), hourly WR patterns (noise)
  Next: NCAA scanner March 17-18, sol drift graduation (29/30), CPI April 10

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
