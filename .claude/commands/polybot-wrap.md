SESSION WRAP-UP — fully autonomous, no confirmation needed at any step.
PRIORITY ORDER (never forget this): 1) Live bets running clean 2) Everything else.
Budget: ~5% of session budget. Be efficient.

CRITICAL PATH: Step 1 (bot health) → Step 3A (handoff) → Step 3B (changelog) →
               Step 3C (SESSION_RESUME.md) → Step 4 (commit) → Step 5 (output prompt)

═══════════════════════════════════════════════════
STEP 1 — BOT HEALTH FIRST (before touching any files)
═══════════════════════════════════════════════════
ps aux | grep "[m]ain.py"
  0 processes → restart (command in SESSION_HANDOFF.md)
  1 process → confirm PID matches bot.pid, proceed
  2+ processes → kill all, restart clean

./venv/bin/python3 main.py --health
./venv/bin/python3 main.py --report
./venv/bin/python3 main.py --graduation-status
./venv/bin/python3 scripts/kalshi_visibility_report.py --edge-mode cached --strict-same-day-sports

If --health shows any blocker preventing live bets: FIX IT BEFORE TOUCHING DOCS.
If visibility gate fails: document the same-day skipped series and treat it as an open overhaul blocker.
If the gate reports stale/corrupt/missing cache, rebuild deliberately with:
  ./venv/bin/python3 scripts/kalshi_visibility_report.py --refresh-live --edge-mode cached --strict-same-day-sports

═══════════════════════════════════════════════════
STEP 2 — OBJECTIVE SELF-RATING (be brutally honest)
═══════════════════════════════════════════════════
  WINS: what actually moved the needle (live bets, P&L, real fixes)
  LOSSES: what wasted time, caused bugs, blocked bets, lost money
  GRADE: A/B/C/D and exactly why
  ONE THING next chat must do differently
  ONE THING that would have made more money if done earlier

═══════════════════════════════════════════════════
STEP 3 — UPDATE ALL FILES
═══════════════════════════════════════════════════
A) SESSION_HANDOFF.md
   - Bot PID + log path, all-time P&L + today P&L + win rate
   - Graduation counts for all strategies, guard list
   - PENDING TASKS: remove completed, add new, mark in-progress
   - Session number incremented, last commit hash
   - Any active glitches or blockers to watch

B) .planning/CHANGELOG.md (APPEND ONLY — never truncate)
   - What changed and WHY (reasoning, not just what)
   - Per-strategy P&L and bet counts, graduation changes
   - Self-rating from Step 2
   - Next chat's single most important focus

C) SESSION_RESUME.md  ← WRITE BOTH PROMPTS HERE (not polybot-init.md)
   MAIN CHAT PROMPT block (--- SESSION [N+1] START ---):
     - PID, log path, last commit, all-time P&L, today P&L
     - Guard list (static IL-X through IL-Y + auto-guards)
     - Previous chat grade + key events + what next chat must do first
     - Strategy standings from --graduation-status
     - Restart command (from SESSION_HANDOFF.md)
   RESEARCH CHAT PROMPT block (--- SESSION [N+1] RESEARCH START ---):
     - Top research priorities (ranked)
     - Dead ends (do not re-investigate)

D) MEMORY.md  [OPTIONAL — skip if short on budget]
   ~/.claude/projects/-Users-matthewshields-Projects-polymarket-bot/memory/MEMORY.md
   - Key constants: P&L, PID, test count, last commit, graduation counts
   - Keep under 200 lines

═══════════════════════════════════════════════════
STEP 4 — BATCH LEARNING + COMMIT
═══════════════════════════════════════════════════
Run wrap helper (writes SESSION_RESUME.md + CHANGELOG + CCA journal in one pass):
  ./venv/bin/python3 scripts/polybot_wrap_helper.py \
    --session [N] --grade [A/B/C/D] \
    --wins "[one sentence]" --losses "[one sentence]" \
    --write

./venv/bin/python3 -m pytest tests/ -q  ← all must pass before commit
git add SESSION_HANDOFF.md SESSION_RESUME.md .planning/CHANGELOG.md && git commit + push

═══════════════════════════════════════════════════
STEP 5 — OUTPUT SUMMARY
═══════════════════════════════════════════════════
Output a 3-line summary:
  Session [N] grade: [A/B/C/D] | P&L today: [X] USD | All-time: [X] USD
  Bot: [RUNNING PID X / STOPPED] | Next priority: [one line]
  SESSION_RESUME.md written. Run /polybot-init to start next session.
