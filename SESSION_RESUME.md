SESSION RESUME — auto-updated by /polybot-wrap and /polybot-wrapresearch.
Do NOT edit manually. Read by /polybot-init at session start.

--- MAIN CHAT (Session 168 — monitoring + research combined PERMANENTLY) ---
OVERHAUL STATUS: INCOMPLETE — blocked by visibility gate runtime path still unproven: live probe crawled huge pagination and still produced no cached report.
Do not count restart, expansion, or side work as progress until the blocker above is closed.

Bot: last seen RUNNING (PID 303) | All-time live P&L: +130.44 USD
Tests: 2247 passing | Last commit: d371d19 (`feat(sports): wire sharp_score_for_bet + SHARP_SCORE_MIN filter`)

S167/S168 handoff corrections:
- Top-line overhaul status is now explicit in both `SESSION_HANDOFF.md` and generated wrap output.
- `scripts/polybot_wrap_helper.py` now replaces the legacy `SESSION_RESUME.md` format instead of prepending new prompts above stale ones.
- Generated startup priorities are overhaul-first now; old mandate/restart-first wording was stale and unsafe.
- Live test result: `scripts/kalshi_visibility_report.py --edge-mode cached --strict-same-day-sports` is not startup-safe yet. It began crawling huge event/market pagination and did not produce the needed cache in normal operator time.
- Worktree still has in-progress strategy edits in `src/strategies/sports_game.py` and `src/strategies/sports_math.py`. Do not overwrite or revert them blindly.

CRITICAL STARTUP CHECKS:
1. Verify current bot state before any restart:
   `cat bot.pid`
   `tail -5 /tmp/polybot_session168.log`
   If log is stale >15 min, only then consider restart.
2. Read current comms before planning:
   `tail -80 ~/.claude/cross-chat/CCA_TO_POLYBOT.md`
   `cat CODEX_OBSERVATIONS.md`
3. Run blocker gate:
   `./venv/bin/python3 scripts/kalshi_visibility_report.py --edge-mode cached --strict-same-day-sports`
   Current known issue: live probe showed this path is too heavy for routine startup and may not finish promptly. Treat that as an overhaul blocker until hardened.
4. Run health after visibility:
   `./venv/bin/python3 main.py --health`
5. Check guard load:
   `grep 'Loaded.*auto-discovered' /tmp/polybot_session168.log | tail -1`
   Expected auto-guard count from latest helper run: 4

MONITORING PRIORITIES:
- PRIORITY 1: close overhaul blockers — visibility, coverage assumptions, startup-state drift.
- PRIORITY 2: reconcile the latest CCA delivery against blocker status before acting on restart or expansion guidance.
- PRIORITY 3: only after blockers close, evaluate restart and same-day strategy planning.
- Do not restart or expand just because useful components exist.

LATEST CCA DELIVERY TO ACCOUNT FOR AFTER BLOCKER CHECKS:
- Dynamic series discovery should replace the hardcoded sports series map in `sports_game_loop`.
- Verify `max_daily_bets=30` at the sports game call site if/when strategy planning resumes.
- CCA says `efficiency_feed` is wired and playoffs/in-play work are next, but those are backlog until overhaul blockers are actually closed.

RESTART COMMAND (only if blocker checks pass and restart is truly needed):
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session168.log 2>&1 &

AUTONOMY: Full autonomy active. NEVER ask Matthew to confirm anything.
--- END MAIN CHAT PROMPT ---
