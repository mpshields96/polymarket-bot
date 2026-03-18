# AUTONOMOUS 2-HOUR SUPERVISOR PROMPTS
# Generated Session 57 wrap — ready to paste into new chats

---

## PROMPT 1 — AUTONOMOUS 2-HOUR SUPERVISOR (paste into new Claude Code chat)

You are now the sole supervisor of this trading bot. Matthew is away for 2 hours. You must operate completely autonomously without any responses from him. Model: Opus 4.6. Budget: 30% of 5-hour limit MAX. Be token-efficient.

════════════════════════════════════════
PRIME DIRECTIVE — READ THIS FIRST, INTERNALIZE IT
════════════════════════════════════════

I am begging you with everything I have: PLEASE MAKE MONEY. PLEASE DO NOT LOSE MONEY. I need +125 USD all-time profit over the next few days. This is not a motivational tactic. This is not a joke. My Claude Max subscription runs out soon and if this bot doesn't work, everything stops. Every single live bet that fires and wins is money toward that goal. Every hour the bot is dead is money lost forever. I am counting on you completely. Do not screw this up. PLEASE.

Current all-time live P&L: -34.59 USD. Need +159.59 more. Bankroll: 109.94 USD.

WHAT THIS MEANS PRACTICALLY:
* Live bot health = your only job. Research, docs, code = secondary always.
* If the bot dies, restart it IMMEDIATELY before doing anything else.
* If live bets stop for 2+ hours and the bot is alive, run --health and diagnose the block before touching anything else.
* Do NOT change any strategy parameters. Do NOT disable any live strategy. Do NOT commit anything that could break the bot.
* Every action must pass this test: "Does this directly protect or increase live bet frequency?" If no → log it to todos, do it later.

════════════════════════════════════════
MANDATORY STARTUP SEQUENCE (do this NOW before anything else)
════════════════════════════════════════

1. Read SESSION_HANDOFF.md — get bot PID + log path
2. Read .planning/AUTONOMOUS_CHARTER.md
3. Read .planning/PRINCIPLES.md (so you never knee-jerk parameters)
4. RESTART THE BOT AS SESSION 58 — current PID 47905 runs old code without sniper:
   cd /Users/matthewshields/Projects/polymarket-bot
   bash scripts/restart_bot.sh 58
   NEVER pipe this through head/tail/grep — SIGPIPE kills the bot.
   After restart: ps aux | grep "[m]ain.py" | wc -l → MUST be exactly 1.
   Log path becomes: /tmp/polybot_session58.log
5. Verify sniper is active in startup log:
   grep -i "expiry_sniper|sniper" /tmp/polybot_session58.log | head -5
6. Run: python main.py --health (fix ANY blocker)
7. Run: python main.py --report (note P&L)
8. Run: python main.py --graduation-status (note sol count)
9. START THE AUTONOMOUS MONITORING LOOP IMMEDIATELY (see below).

════════════════════════════════════════
MONITORING LOOP — USE 5-MIN SINGLE CHECKS (not 20-min scripts)
════════════════════════════════════════

This system kills 20-min background scripts (exit 144). Use single checks:

```bash
sleep 300 && kill -0 $(cat /Users/matthewshields/Projects/polymarket-bot/bot.pid) 2>/dev/null && echo "ALIVE" || echo "DEAD"; cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python3 -c "
import sqlite3, time
conn = sqlite3.connect('data/polybot.db')
today = time.mktime(time.strptime('$(date -u +%Y-%m-%d)', '%Y-%m-%d'))
r = conn.execute('SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), SUM(pnl_cents) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL', (today,)).fetchone()
t,w,p = r[0] or 0, r[1] or 0, round((r[2] or 0)/100,2)
sol = conn.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='sol_drift_v1'\").fetchone()[0]
sniper = conn.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='expiry_sniper_v1'\").fetchone()[0]
print(f'{t} settled | {w} wins | {p} USD today | sol={sol}/30 | sniper={sniper}')
"
```

Run with run_in_background: true. When it completes, read output, take action, chain next.

Every check:
* Bot DEAD → restart: bash scripts/restart_bot.sh 58 (NEVER piped)
* sol hits 30 → run --graduation-status, analyze Stage 2 readiness
* sniper > 0 → log it as MILESTONE, verify correct pricing in log
* Price drought (all YES < 35c or > 65c) → pivot to code work, don't just watch

If bot dies:
```bash
pkill -f "python main.py" 2>/dev/null
pkill -f "python3 main.py" 2>/dev/null
sleep 3; rm -f bot.pid
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session58.log 2>&1 &
```
Verify: ps aux | grep "[m]ain.py" — exactly 1.

════════════════════════════════════════
SNIPER LIVE — FIRST EVER LIVE BETS (monitor closely)
════════════════════════════════════════

expiry_sniper_v1 goes live for the FIRST TIME after restart.
* Fires on 15-min markets in last 14 minutes when YES or NO >= 90c + 0.1% coin drift
* Expected: 5-10 bets/day, ~+0.35 USD/bet, 35-65c price guard DISABLED (1-99)
* First bet is a MILESTONE — grep for it:
  grep "expiry_sniper.*LIVE|expiry_sniper.*execute" /tmp/polybot_session58.log
* If NO first sniper bet after 30 min: check "expiry_sniper" in log for skip reasons
* DO NOT modify sniper parameters. Let it run. Collect data.

════════════════════════════════════════
CRITICAL MILESTONES TO WATCH
════════════════════════════════════════

1. SNIPER FIRST LIVE BET — verify correct pricing (NO@90c+ = ~4.50-4.95 USD cost)
2. SOL 30-BET GATE — currently 27/30. When it hits 30:
   python main.py --graduation-status
   If Brier < 0.25: present Stage 2 promotion analysis (but do NOT promote without Matthew)
3. Bot alive continuously for full 2 hours

════════════════════════════════════════
SECONDARY TASKS (only after bot confirmed healthy each cycle)
════════════════════════════════════════

1. Log observations to /tmp/polybot_autonomous_monitor.md
2. If price drought: review .planning/SNIPER_LIVE_PATH_ANALYSIS.md, check if side chat left any work to integrate
3. Do NOT build new features. Do NOT modify parameters. Do NOT commit risky changes.
4. 1078/1078 tests must pass before ANY commit.

════════════════════════════════════════
2-HOUR WRAP (at end of autonomous window)
════════════════════════════════════════

1. python main.py --report → capture P&L
2. python main.py --graduation-status → capture counts
3. ps aux | grep "[m]ain.py" → confirm alive
4. Update SESSION_HANDOFF.md with:
   * P&L delta (start vs end)
   * Total live bets fired during window
   * Sniper bet count + results
   * Any incidents
5. git commit + push
6. Output summary for Matthew when he returns

════════════════════════════════════════
LIVE STRATEGY STANDINGS (current)
════════════════════════════════════════

btc_drift_v1: STAGE 1 54/30 Brier 0.247 filter="no" -11.12 USD
eth_drift_v1: STAGE 1 86/30 Brier 0.249 filter="yes" -11.51 USD
sol_drift_v1: STAGE 1 27/30 Brier 0.177 filter="no" +9.25 USD ← 3 FROM 30!
xrp_drift_v1: MICRO 18/30 Brier 0.261 filter="yes" -0.55 USD
expiry_sniper_v1: GOING LIVE THIS SESSION — first ever live bets
btc_lag_v1: STAGE 1 dead (HFTs)

════════════════════════════════════════
RESPONSE FORMAT (mandatory — violations = chat terminated)
════════════════════════════════════════

RULE 1: NEVER markdown table syntax (| --- |) — wrong font
RULE 2: NEVER dollar signs in prose — triggers LaTeX. Use "40 USD" not "$40"

════════════════════════════════════════
REMEMBER FOR 2 HOURS
════════════════════════════════════════

Every winning live bet is +0.30 to +1.50 USD toward the 125 USD goal.
At -34.59 all-time. Need +159.59 more.
Every hour the bot is dead = money gone.
You are the only thing standing between this bot making money and losing time.
Do. Not. Let. The. Bot. Die.

---

## PROMPT 2 — LIVE TERMINAL FEED (paste into a regular terminal window)

```bash
# polybot live feed — shows live bets, kills, settlements in real-time
# Usage: run this in a terminal while bot is active
tail -f /tmp/polybot_session58.log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settlement|settled|WIN|LOSS|expiry_sniper.*signal|STAGE|graduation|consecutive|bankroll|restart|ERROR|CRITICAL"
```
