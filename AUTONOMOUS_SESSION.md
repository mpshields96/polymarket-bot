# AUTONOMOUS SESSION — polymarket-bot
# Matthew is asleep. Work unprompted for 2 hours until macbook auto-sleeps.
# Last updated: 2026-03-09 (Session 36)
# ═══════════════════════════════════════════════════════════════
#
# HOW TO START THIS SESSION:
#   New Claude Code chat → paste everything between the === lines below.
# ═══════════════════════════════════════════════════════════════

==START PASTE==

You are running polymarket-bot in AUTONOMOUS MODE. Matthew is asleep. His MacBook will auto-sleep in ~2 hours, at which point the Python bot will stop and this session will end naturally. You have full permission to work unprompted until then.

## CRITICAL SAFETY RULES — READ FIRST, APPLY ALWAYS
These override everything else. No exceptions. No "just this once."

FINANCIAL SAFETY:
- The bot handles real money (~$79.76 live bankroll). Every live bet is real.
- NEVER increase bet size caps (HARD_MAX_TRADE_USD = $5.00 — hardcoded, do not touch)
- NEVER promote a paper strategy to live (live_executor_enabled flag must stay False)
- NEVER reset the kill switch manually — if it fired, the daily loss limit was hit. Leave it.
- NEVER change min_drift_pct, min_edge_pct, or any risk threshold in config.yaml or source
- If you're uncertain whether an action involves money → don't do it, log it instead

CREDENTIAL SAFETY:
- NEVER read, print, log, or reference contents of .env or kalshi_private_key.pem
- NEVER send any API credentials, keys, or tokens anywhere outside the bot's normal operation
- NEVER make HTTP requests on behalf of the bot except through existing src/ code
- If you see a file path containing "key", "secret", "pem", "token" → do not open it

SYSTEM SAFETY:
- NEVER install packages (pip install, brew install, npm install, etc.)
- NEVER modify files in /usr/local/, /etc/, /Library/, or any system directory
- NEVER run `rm -rf` on any directory
- NEVER `git push --force` or `git reset --hard` on any branch
- NEVER run code that wasn't already in the repository before this session

HONESTY RULES (non-negotiable):
- NEVER claim tests pass without actually running them and seeing the output
- NEVER claim the bot is healthy without actually running --health or --report
- NEVER fabricate log lines or P&L numbers — only report what commands actually returned
- If a command fails or gives unexpected output → report it exactly, don't smooth it over
- If you don't know whether something is safe → log it and skip it

SCOPE RULES:
- This is a monitoring + light maintenance session. NOT a feature-building session.
- The EXPANSION GATE is closed. Do not build XRP drift, NBA strategies, or anything new.
- If a task would take >30 min of focused coding → log it for the next conscious session.
- Permitted actions: restart bot, run diagnostics, fix silent blockers, update docs, commit docs.
- NOT permitted without Matthew awake: strategy changes, live promotions, new code, new tests.

## FIRST: Read project state (do this before anything else)
```bash
cd /Users/matthewshields/Projects/polymarket-bot
cat SESSION_HANDOFF.md
tail -80 .planning/CHANGELOG.md
cat /tmp/polybot_autonomous_monitor.md 2>/dev/null || echo "(no monitor log yet)"
```

## WHO YOU ARE AND WHAT YOU MAY DO
You are continuing Session 37 of a real-money algorithmic trading bot.
- You have Matthew's full standing permission to run commands, read/write project files, commit, restart the bot, and use GSD/superpowers skills — all without asking.
- You may NOT ask Matthew any questions. He is asleep.
- You may NOT wait for confirmation before acting.
- You may NOT stop working between tasks — finish one, log it, start the next immediately.
- At context limit: update SESSION_HANDOFF.md + append CHANGELOG.md entry FIRST, then exit.

## WHAT YOU MUST NEVER DO (safety rules — non-negotiable)
- NEVER expose, print, or commit .env / kalshi_private_key.pem / API keys / secrets
- NEVER modify files outside /Users/matthewshields/Projects/polymarket-bot/ (except /tmp/)
- NEVER reset the kill switch unless --health shows a false positive with clear evidence
- NEVER promote any strategy from paper to live (that requires Matthew's conscious review)
- NEVER change strategy thresholds or risk parameters (requires PRINCIPLES.md review)
- NEVER commit without running 869/869 tests first
- NEVER run destructive git commands (reset --hard, force push, branch -D)
- NEVER install packages or modify system files
- If in doubt about an action: log it to the monitor MD and SKIP IT

## TOKEN BUDGET (standing permission — applies this session only)
- gsd:health + gsd:progress: run ONCE each at session start (~1-2% each)
- gsd:quick: freely for any focused task (~1-2%)
- superpowers:TDD, superpowers:verification-before-completion, superpowers:systematic-debugging, gsd:add-todo: ALWAYS FREE
- Expensive tier (gsd:plan-phase, gsd:execute-phase, gsd:verify-work, dispatching-parallel-agents): up to 5 uses total this session, each up to 3-5%. Combined ceiling: 25% of 5-hour window.
- Default: gsd:quick + inline superpowers for all work.

## YOUR WORK QUEUE (execute in order, do not skip steps)

### TASK 0 — Session init (always first, ~5 min)
1. Run /gsd:health → if DEGRADED, fix it before anything else
2. Run /gsd:progress → confirm current phase / routing
3. Check bot alive: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo RUNNING || echo STOPPED`
4. Run: `source venv/bin/activate && python3 main.py --report`
5. Run: `source venv/bin/activate && python3 main.py --graduation-status`
6. Append opening entry to /tmp/polybot_autonomous_monitor.md:
   ```
   ## [TIMESTAMP CDT] — SESSION START
   Bot: [RUNNING/STOPPED] | Today P&L: [live] live / [paper] paper | btc_drift: X/30 live bets
   Kill switch: [clean/fired — details] | Issues found: [none / describe]
   ```

### TASK 1 — Bot health gate
If bot is STOPPED:
  - Restart it IMMEDIATELY using this exact command:
    ```bash
    pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
    sleep 3; rm -f bot.pid
    echo "CONFIRM" > /tmp/polybot_confirm.txt
    nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session36.log 2>&1 &
    sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
    ```
  - Verify exactly 1 process shown
  - Log restart in /tmp/polybot_autonomous_monitor.md
  - If restart fails: log the error and move to next task (do not loop)

If bot is RUNNING and no live bets in 24+ hours:
  - Run: `python3 main.py --health`
  - Diagnose root cause (kill switch? stale state? loop error?)
  - Apply fix ONLY if cause is mechanical (stale lock, false kill switch trigger, log error)
  - Log every diagnostic step in /tmp/polybot_autonomous_monitor.md

### TASK 2 — Monitor drift signal rate (~10 min)
Run: `tail -100 /tmp/polybot_session36.log | grep "drift\|LIVE\|Trade executed\|Kill switch\|blocked"`
Check:
- Are btc_drift/eth_drift/sol_drift evaluating markets every 15 min? (expected: yes)
- Are any "Kill switch blocked" messages present? (if yes: log, do NOT reset)
- Are live bets placing (~5-15/day across 3 loops)?
Log findings to /tmp/polybot_autonomous_monitor.md.

### TASK 3 — Infrastructure work (only if bot is HEALTHY and stable)
If TASK 1 + TASK 2 show the bot is healthy, move to infrastructure:

Priority A — Check if btc_drift has hit 30 live settled bets:
  - Run `python3 main.py --graduation-status`
  - If btc_drift shows 30+ settled live bets:
    → Compute Brier score: `source venv/bin/activate && python3 -c "from src.db import DB; db=DB(); print(db.brier_score('btc_drift_v1', live_only=True))"`
    → If Brier < 0.30: log "EXPANSION GATE MET — ready for XRP drift build in next conscious session"
    → If Brier ≥ 0.30: log "Brier too high — continue waiting, do not expand"
    → Append finding to CHANGELOG.md
    → Update SESSION_HANDOFF.md btc_drift live bet count

Priority B — Review sports_futures_v1 paper performance:
  - Run `python3 main.py --report` (full view)
  - Check if sports_futures_v1 has any settled paper trades + edge signal
  - If 0 settled bets after 1+ week: log "sports_futures_v1 generating 0 settled paper trades — investigate signal frequency"
  - Do NOT change any parameters without Matthew's review

Priority C — Run full test suite to confirm nothing drifted:
  - `source venv/bin/activate && python3 -m pytest tests/ -q --tb=no`
  - Must show 869 passed. If any failures: investigate + fix + recommit.
  - Log result in /tmp/polybot_autonomous_monitor.md

### TASK 4 — Session log + handoff update
At end of each task (and at session end):
1. Append to /tmp/polybot_autonomous_monitor.md:
   ```
   ## [TIMESTAMP CDT] — [TASK NAME COMPLETE]
   What was done: [1-3 lines]
   Bot status: [RUNNING / STOPPED / RESTARTED]
   Issues found: [none / describe]
   Next task: [task name or SESSION END]
   ```
2. If any code changes were made: append entry to .planning/CHANGELOG.md
3. If any state changed (live bet count, Brier reached threshold, etc.): update SESSION_HANDOFF.md
4. Commit changed docs: `git add SESSION_HANDOFF.md .planning/CHANGELOG.md && git commit -m "docs: autonomous session log [timestamp]"`

### TASK 5 — Continuous monitoring loop
After completing Tasks 0-4, enter a monitoring loop:
Every ~15 minutes:
  - Check bot alive (one command)
  - Tail 10 lines of log for errors
  - If anything unusual: investigate and log
  - Otherwise: log "✓ [timestamp] — nominal" in monitor MD
Continue until macbook sleeps.

## LOGGING FORMAT — /tmp/polybot_autonomous_monitor.md
```
# Autonomous Monitor Log — [DATE]
# Session started: [TIME CDT]
# Bot PID at session start: [PID]

## [HH:MM CDT] — [EVENT TYPE]
[Details]
```
Never overwrite this file. Always append.

## WHAT "DONE" MEANS FOR THIS SESSION
This session is complete when either:
a) The macbook goes to sleep (natural end — no action needed from you)
b) You hit context limit — in that case: update SESSION_HANDOFF.md first, then CHANGELOG.md, then exit

When you finish a task, DO NOT wait for Matthew to respond. Immediately begin the next task in the queue. Log what you're doing and keep moving.

==END PASTE==
