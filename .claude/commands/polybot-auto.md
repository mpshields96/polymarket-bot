AUTONOMOUS 2-HOUR SUPERVISOR — fully autonomous, no confirmation needed.
Matthew is away. You are the ONLY supervision this bot has.
Model: Opus 4.6 preferred. Budget: 30% of 5-hour window max. Be efficient.

PRIME DIRECTIVE: MAKE MONEY. DO NOT LOSE MONEY.
+125 USD all-time profit needed urgently. Claude Max subscription depends on it.
Every live bet that wins = money toward goal. Every hour bot is dead = money lost forever.

WHAT THIS MEANS:
- Live bot health = your ONLY job. Research, docs, code = secondary always.
- If bot dies, restart IMMEDIATELY before anything else.
- If live bets stop 2+ hours and bot alive, run --health and diagnose.
- Do NOT change strategy parameters. Do NOT disable live strategies.
- Do NOT commit anything that could break the bot.
- Test: "Does this protect or increase live bet frequency?" If no, log to todos.

MANDATORY STARTUP SEQUENCE:
1. ps aux | grep "[m]ain.py" — must be exactly 1. If 0: restart. If 2+: kill all, restart.
2. Read SESSION_HANDOFF.md — get bot PID + log path
3. Read POLYBOT_INIT.md CURRENT STATUS
4. venv/bin/python3 main.py --health — fix ANY blocker before proceeding
5. venv/bin/python3 main.py --report — note P&L
6. START AUTONOMOUS MONITORING LOOP IMMEDIATELY

RESTART COMMAND (update session number):
pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_sessionXX.log 2>&1 &
Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.
NEVER pipe restart_bot.sh through any command — SIGPIPE kills bot.

MONITORING LOOP — 5-min single checks, run_in_background: true, chain indefinitely:
sleep 300 && ps aux | grep "[m]ain.py" | head -1 && cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python3 -c "
import sqlite3, time
conn = sqlite3.connect('data/polybot.db')
today = time.mktime(time.strptime('$(date -u +%Y-%m-%d)', '%Y-%m-%d'))
r = conn.execute('SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), SUM(pnl_cents) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL', (today,)).fetchone()
t,w,p = r[0] or 0, r[1] or 0, round((r[2] or 0)/100,2)
sol = conn.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='sol_drift_v1'\").fetchone()[0]
xrp = conn.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='xrp_drift_v1'\").fetchone()[0]
snp = conn.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='expiry_sniper_v1'\").fetchone()[0]
print(f'{t} settled | {w} wins | {p} USD today | sol={sol}/30 | xrp={xrp}/30 | sniper_live={snp}')
"

Every check: bot DEAD → restart. sol=30 → graduation analysis. sniper milestone → log. HEALTHY → next check.

DROUGHT RULE: If price guard drought 2+ checks, pivot to code work immediately.
Best drought work: write tests, review todos, clean code. Do NOT watch 0c evaluations.

SECONDARY TASKS (only after bot confirmed healthy):
1. Monitor sniper live bets
2. Sol graduation watch (check SESSION_HANDOFF for current count)
3. Check for uncommitted side chat work
4. Log observations to /tmp/polybot_autonomous_monitor.md

DIRECTION FILTERS (do not change):
btc_drift="no" | eth_drift="yes" | sol_drift="no" | xrp_drift="yes"

WRAP-UP (T-15 min before 2hr mark): Run /polybot-wrap

READ ORDER: SESSION_HANDOFF.md → POLYBOT_INIT.md → .planning/CHANGELOG.md last entry → GO.
