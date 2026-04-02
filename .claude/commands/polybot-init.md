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
SESSION RESUME PROMPTS (auto-updated by wrap)
═══════════════════════════════════════════════════
Read SESSION_RESUME.md — contains the current MAIN CHAT PROMPT and RESEARCH CHAT PROMPT.
Updated every session by /polybot-wrap and /polybot-wrapresearch.

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
Font rules and standing directives are in .claude/rules/ (auto-loaded).
See: font-rules.md, standing-directives.md
