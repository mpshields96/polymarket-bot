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
Last updated: Session 67 (2026-03-14)
Bot: RUNNING PID 15236 → /tmp/polybot_session66.log
All-time P&L: -34.53 USD
Bankroll: ~89+ USD (DB authoritative — check --report)
Tests: 1127 passing, 3 skipped
Last commit: 8b279e6

Live strategies:
  btc_drift: MICRO-LIVE (demoted S60) — confirmed loser
  eth_drift: MICRO-LIVE (demoted S60) — confirmed loser
  sol_drift: STAGE 1 — 28/30 bets, Brier 0.176, BEST SIGNAL, 2 from milestone!
  xrp_drift: MICRO — 19/30 bets, Brier 0.266
  expiry_sniper: LIVE — 89 live bets total, 42W/1L today (+9.28 USD today)
  RISK CAPS RAISED S67: HARD_MAX 5→15 USD, MAX_TRADE_PCT 5%→15% (Matthew directive)
  Sniper now bets 13-15 USD/bet vs old 4.47 USD/bet

Direction filters (do not change):
  btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

Research state (S67):
  GEFS ensemble built (S63) — needs weekday HIGHNY markets to test (Monday March 16)
  Sniper bucket analysis: 90-94c marginal, 95-99c profitable
  Dead ends: sports arb, crypto expansion (only 4 15-min series exist), BALLDONTLIE
  Next: GEFS test Monday, sol_drift Stage 2 graduation (2 bets away), sniper threshold analysis at 200+

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
