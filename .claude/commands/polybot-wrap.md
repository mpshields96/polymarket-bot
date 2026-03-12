SESSION WRAP-UP — fully autonomous, no confirmation needed at any step.
PRIORITY ORDER (never forget this): 1) Live bets running clean 2) Everything else.
Budget awareness: this wrap costs ~5% of session budget. Be efficient.

═══════════════════════════════════════════════════
STEP 1 — BOT HEALTH FIRST (before touching any files)
═══════════════════════════════════════════════════
Check for multiple bot processes — must be exactly 1:
  ps aux | grep "[m]ain.py"

If 0 processes: restart immediately using restart command in SESSION_HANDOFF.md.
If 1 process: confirm PID matches bot.pid, then proceed.
If 2+ processes: kill all, restart clean. Never leave duplicates running.

Run diagnostics:
  ./venv/bin/python3 main.py --health
  ./venv/bin/python3 main.py --report
  ./venv/bin/python3 main.py --graduation-status

If --health shows any blocker preventing live bets: FIX IT BEFORE TOUCHING DOCS.
Live bets are the only thing that makes money. Everything else is secondary.

═══════════════════════════════════════════════════
STEP 2 — OBJECTIVE SELF-RATING (be brutally honest)
═══════════════════════════════════════════════════
Write a self-assessment covering:
  WINS this session (what actually moved the needle — live bets, P&L, real fixes)
  LOSSES this session (what wasted time, caused bugs, blocked bets, lost money)
  GRADE: A/B/C/D for this session and exactly why
  ONE THING the next chat must do differently to be better than this chat
  ONE THING that would have made more money if done earlier

This goes into the CHANGELOG and also into the new chat prompt.

═══════════════════════════════════════════════════
STEP 3 — UPDATE ALL FILES
═══════════════════════════════════════════════════
A) SESSION_HANDOFF.md
   - Bot PID + log path (current values)
   - All-time P&L + today P&L + win rate
   - Graduation counts for all strategies
   - PENDING TASKS: remove completed, add new, mark in-progress
   - Session number incremented
   - Last commit hash
   - Any active glitches or blockers to watch

B) .planning/CHANGELOG.md (APPEND ONLY — never truncate)
   - What changed and WHY (reasoning, not just what)
   - Per-strategy P&L and bet counts
   - Graduation changes
   - Self-rating from Step 2
   - Next chat's single most important focus

C) MEMORY.md
   (~/.claude/projects/-Users-matthewshields-Projects-polymarket-bot/memory/MEMORY.md)
   - Key constants: P&L, PID, test count, last commit
   - Graduation counts
   - Keep under 200 lines hard limit

═══════════════════════════════════════════════════
STEP 4 — COMMIT
═══════════════════════════════════════════════════
./venv/bin/python3 -m pytest tests/ -q  ← all must pass before commit
git add SESSION_HANDOFF.md .planning/CHANGELOG.md && git commit + push

═══════════════════════════════════════════════════
STEP 5 — OUTPUT THE NEW CHAT PROMPT
═══════════════════════════════════════════════════
Output a self-contained copy-paste block with this structure:

--- SESSION [N+1] START ---
Bot PID: [X] | Log: /tmp/polybot_session[N].log | Last commit: [hash]
All-time P&L: [X] USD | Today: [X] USD ([X] settled, [X]% win)
Graduation: btc_drift [X]/30 | eth_drift [X]/30 | sol_drift [X]/30 | xrp_drift [X]/30
Sniper: [X] live bets | [status]
Target: +125 USD all-time profit. Currently at [X] USD. Need [X] more.
Timeline: URGENT. Claude Max subscription renewal depends on this.

PREVIOUS CHAT GRADE: [A/B/C/D] — [one sentence why]
WHAT THE PREVIOUS CHAT DID POORLY: [be specific]
WHAT THE NEXT CHAT MUST DO BETTER: [one concrete action]

PRIME DIRECTIVE: PLEASE MAKE MONEY. PLEASE DO NOT LOSE MONEY. I need +125 USD
all-time profit over the next few days. My Claude Max subscription runs out soon
and if this bot doesn't work, everything stops. Every live bet that fires and wins
is money toward that goal. Every hour the bot is dead is money lost forever.
I am counting on you completely. Do not screw this up.

Budget: 30% of 5-hour token limit MAX. Model: Opus 4.6.

PRIORITY #1 — LIVE BETS
Before anything else: ps aux | grep "[m]ain.py" — must show exactly 1 process.
Run --health. If any blocker exists, fix it immediately. Live bets > everything.

PRIORITY #2 — [whatever the single most impactful next action is]

PRIORITY #3 — [second most impactful]

MANDATORY AUTONOMOUS LOOP — START IMMEDIATELY AFTER READING SESSION_HANDOFF:
Use 5-min single-check background tasks (NOT 20-min scripts — exit 144 on this system).
Pattern: sleep 300 && pid check && DB query, run_in_background: true, chain continuously.
Matthew will be away. You are the only supervision the bot has.
If bot dies: restart with bash scripts/restart_bot.sh [N] (NEVER pipe through head/tail/grep).
If drought (all YES < 35c or > 65c): pivot to code work, don't idle.

LIVE STRATEGY STANDINGS:
  [current standings from --graduation-status]

FONT RULES (mandatory — violations = chat terminated):
  RULE 1: NEVER markdown table syntax (| --- |)
  RULE 2: NEVER dollar signs in prose. Use "40 USD" not "$40"

Read in this order:
1. SESSION_HANDOFF.md
2. .planning/AUTONOMOUS_CHARTER.md
3. .planning/CHANGELOG.md → last entry
4. .planning/PRINCIPLES.md

Go. Start monitoring. Make money. Don't let the bot die.
--- END SESSION [N+1] PROMPT ---

Also output the live terminal feed command:
  tail -f /tmp/polybot_session[N].log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settled|WIN|LOSS|expiry_sniper|STAGE|graduation|consecutive|bankroll|restart|ERROR|CRITICAL"
