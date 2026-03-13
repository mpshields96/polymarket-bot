RESEARCH SESSION WRAP-UP — fully autonomous, no confirmation needed at any step.
This is for research-focused sessions (edge discovery, scanner builds, data analysis).
NOT for bot-monitoring sessions — use /polybot-wrap for those.
Budget awareness: this wrap costs ~5% of session budget. Be efficient.

═══════════════════════════════════════════════════
STEP 1 — BOT STATUS CHECK (quick — research sessions don't babysit the bot)
═══════════════════════════════════════════════════
Check bot status (NOT restart — just note it):
  ps aux | grep "[m]ain.py"

If bot is running: note PID. Do NOT restart or touch it.
If bot is stopped: note "STOPPED". Do NOT restart unless Matthew explicitly asked.
Research sessions are about building tools and finding edges, not monitoring.

═══════════════════════════════════════════════════
STEP 2 — RESEARCH SELF-RATING (be brutally honest)
═══════════════════════════════════════════════════
Write a self-assessment covering:
  DISCOVERIES this session (what NEW information was found — data, not theory)
  TOOLS BUILT (scripts, scanners, analysis code — with test counts)
  DEAD ENDS CONFIRMED (what was investigated and proven unprofitable — save future time)
  EDGES FOUND (any validated, exploitable inefficiency — be skeptical, require evidence)
  GRADE: A/B/C/D and exactly why
    A = found a real exploitable edge with evidence
    B = built useful tools + confirmed dead ends (saved future time)
    C = did research but no actionable findings
    D = wasted time on things already known or theorized without data
  ONE FINDING that changes how we should trade
  ONE THING the next research session should investigate first

═══════════════════════════════════════════════════
STEP 3 — UPDATE ALL FILES
═══════════════════════════════════════════════════
A) .planning/EDGE_RESEARCH_S[NN].md (primary output)
   - ALL findings documented with evidence (not just conclusions)
   - Dead ends logged with WHY they're dead (prevent re-investigation)
   - Priority stack updated based on what was learned
   - Scanner/tool results included (raw data, not just interpretation)

B) SESSION_HANDOFF.md
   - Note that this was a RESEARCH session (not monitoring)
   - Bot status (running/stopped, PID if running)
   - Last commit hash
   - What was built/discovered (2-3 bullet points)
   - PENDING RESEARCH TASKS: what to investigate next
   - Session number incremented

C) .planning/CHANGELOG.md (APPEND ONLY — never truncate)
   - Research focus and what was investigated
   - Tools/scripts built (with file paths)
   - Key data findings (numbers, not vibes)
   - Dead ends (save future sessions from re-investigating)
   - Self-rating from Step 2
   - Next research session's top priority

D) .claude/commands/polybot-init.md → CURRENT STATE section
   - Update: bot status, P&L, bankroll, test count, last commit
   - Update: research state (new findings, dead ends, open leads)
   - Update: "Last updated: Session [N]" line

E) MEMORY.md
   (~/.claude/projects/-Users-matthewshields-Projects-polymarket-bot/memory/MEMORY.md)
   - Only update if research changed strategic understanding
   - New dead ends worth remembering
   - New tools that future sessions should know about
   - Keep under 200 lines hard limit

═══════════════════════════════════════════════════
STEP 4 — TESTS + COMMIT
═══════════════════════════════════════════════════
If new code was written:
  ./venv/bin/python3 -m pytest tests/ -q  ← all must pass before commit
  git add [relevant files] && git commit + push

Commit message format: "research: [what was found/built] (S[NN])"
Do NOT commit large raw data files (JSON dumps > 1MB) — gitignore them.

═══════════════════════════════════════════════════
STEP 5 — OUTPUT THE NEW CHAT PROMPT
═══════════════════════════════════════════════════
Output a self-contained copy-paste block with this structure:

--- SESSION [N+1] START ---
Bot: [RUNNING PID X / STOPPED] | Last commit: [hash]
All-time P&L: [X] USD | Bankroll: ~[X] USD
This was a RESEARCH session. Bot was [running/stopped].

SESSION [N] RESEARCH FINDINGS:
  [2-3 bullet points of key discoveries]
  [1 bullet point of most important dead end confirmed]

TOOLS BUILT THIS SESSION:
  [list of new scripts/files with one-line descriptions]

PREVIOUS CHAT GRADE: [A/B/C/D] — [one sentence why]
TOP RESEARCH PRIORITY FOR NEXT SESSION: [one specific investigation]

CONTEXT FILES (read in order):
1. POLYBOT_INIT.md
2. SESSION_HANDOFF.md
3. .planning/EDGE_RESEARCH_S[NN].md (this session's full findings)
4. .planning/CHANGELOG.md → last entry

FONT RULES (mandatory — violations = chat terminated):
  RULE 1: NEVER markdown table syntax (| --- |)
  RULE 2: NEVER dollar signs in prose. Use "40 USD" not "$40"

If next session is RESEARCH: use /polybot-autoresearch
If next session is MONITORING: use /polybot-auto
--- END SESSION [N+1] PROMPT ---

═══════════════════════════════════════════════════
STEP 6 — FINAL REMINDERS
═══════════════════════════════════════════════════
- Do NOT restart the bot during research wrap-up (that's monitoring's job)
- Do NOT change strategy parameters based on research alone (needs live testing)
- Do NOT leave uncommitted code — research tools are valuable, commit them
- Research findings go in .planning/EDGE_RESEARCH_S[NN].md, not scattered files
- Dead ends are as valuable as discoveries — document them thoroughly
