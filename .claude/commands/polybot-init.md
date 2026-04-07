CRITICAL PATH: Read SESSION_RESUME.md → check bot → monitor.

SESSION STARTUP — fully autonomous, no confirmation needed.
Updated automatically by /polybot-wrap and /polybot-wrapresearch at session end.

═══════════════════════════════════════════════════
STEP 1 — READ CONTEXT (in order)
═══════════════════════════════════════════════════
1. POLYBOT_INIT.md — full build instructions + live status
2. SESSION_HANDOFF.md — PID, log path, pending tasks, last commit (canonical state)
3. SESSION_RESUME.md — current chat prompt (copy-paste ready for this session)
4. .planning/CHANGELOG.md — last 3 entries (what changed and WHY)
5. .planning/PRINCIPLES.md — before ANY strategy/risk parameter change
6. .planning/AUTONOMOUS_CHARTER.md — standing directives

═══════════════════════════════════════════════════
STEP 2 — BOT STATUS CHECK
═══════════════════════════════════════════════════
Run: ps aux | grep "[m]ain.py"
  0 processes + SESSION_HANDOFF says running → restart (command in SESSION_HANDOFF.md)
  0 processes + SESSION_HANDOFF says STOPPED → note "STOPPED per Matthew", do not restart
  1 process → confirm PID matches bot.pid. Good to go.
  2+ processes → kill all, restart clean. Never leave duplicates.

If running: ./venv/bin/python3 main.py --health && ./venv/bin/python3 main.py --report

SESSION STARTUP SELF-REFLECTION (MANDATORY):
  ./venv/bin/python3 scripts/strategy_analyzer.py --brief
  Surfaces: profitable sniper buckets, drift validation, graduation status, target gap.

MARKET VISIBILITY GATE (MANDATORY BEFORE STRATEGY PLANNING):
  ./venv/bin/python3 scripts/kalshi_visibility_report.py --edge-mode cached --strict-same-day-sports
  If this exits non-zero, review same-day visible vs skipped series before planning any sports work.
  Default path is cache-only and startup-safe. If cache is stale/corrupt/missing, rebuild intentionally:
  ./venv/bin/python3 scripts/kalshi_visibility_report.py --refresh-live --edge-mode cached --strict-same-day-sports

═══════════════════════════════════════════════════
STEP 3 — ANNOUNCE STATE (2-3 lines max)
═══════════════════════════════════════════════════
  - Bot status: RUNNING PID X / STOPPED
  - Today P&L + all-time P&L
  - Any blockers from --health
  - Next priority from SESSION_HANDOFF

═══════════════════════════════════════════════════
STEP 4 — ROUTE TO WORK MODE
═══════════════════════════════════════════════════
  Bot running + Matthew away → /polybot-auto (5-min background loop, chain indefinitely)
  Bot stopped + research mode → highest-impact task from SESSION_HANDOFF, work inline
  Matthew gives a specific task → do it (gsd:quick)
  No clear direction → SESSION_HANDOFF pending tasks, highest-impact, gsd:quick + TDD

═══════════════════════════════════════════════════
RULES
═══════════════════════════════════════════════════
Font rules and standing directives are in .claude/rules/ (auto-loaded).
See: font-rules.md, standing-directives.md
