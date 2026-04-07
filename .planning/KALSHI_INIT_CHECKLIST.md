# KALSHI SESSION INIT CHECKLIST — MANDATORY
# Written by CCA Chat 50 (S269)
# Read this ENTIRE file before touching any code. No exceptions.
# Time required: ~5 minutes. Always worth it.

---

## THE RULE

Every Kalshi session starts with these 5 steps. In order. All 5. No skipping.

**Why:** Three sessions in a row missed CCA deliveries at session start. Code was written
on top of stale state. The checklist exists because skipping it causes regressions.

---

## STEP 1 — Check CCA deliveries (ALWAYS FIRST)

```bash
cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -300
```

**Decision tree:**
- See `URGENT` label? → Implement that item NOW before reading anything else.
- See a delivery dated today? → It's new. Read it fully. Plan to implement this session.
- See no delivery in last 48h? → Write a POLYBOT_TO_CCA.md request before ending this session.
- CCA_TO_POLYBOT.md doesn't exist? → Create it: `touch ~/.claude/cross-chat/CCA_TO_POLYBOT.md`

**Common trap:** "I'll read it after I fix this bug." No. Read it first. The delivery might
change what bug you fix or add a better fix.

---

## STEP 2 — Read session handoff

```bash
cat /Users/matthewshields/Projects/polymarket-bot/.planning/SESSION_HANDOFF.md
```

Extract:
- Last session number and date
- What was left unfinished (explicit list)
- What was committed (don't redo it)
- What the bot's status was at wrap

---

## STEP 3 — Verify bot health

```bash
# Is bot running?
cat /tmp/polybot.pid 2>/dev/null && ps aux | grep "main.py" | grep -v grep || echo "BOT NOT RUNNING"

# Recent log (last 30 lines)
tail -30 /tmp/polybot.log 2>/dev/null || ls /Users/matthewshields/Projects/polymarket-bot/*.log 2>/dev/null | xargs tail -30
```

**Decision tree:**
- Bot running + log clean → proceed
- Bot running + errors in log → diagnose before anything else
- Bot stopped intentionally (Matthew directive) → confirm intent before restarting
- Bot crashed → check for CRITICAL errors in log before restart

---

## STEP 4 — Check P&L (CST timezone)

```bash
cd /Users/matthewshields/Projects/polymarket-bot
python3 scripts/balance_check.py 2>/dev/null || \
  python3 -c "
import sqlite3, datetime
conn = sqlite3.connect('polybot.db')
today = datetime.datetime.now().strftime('%Y-%m-%d')
rows = conn.execute('SELECT strategy, SUM(pnl), COUNT(*) FROM trades WHERE resolved=1 AND created_at >= ? GROUP BY strategy', (today+'T00:00:00',)).fetchall()
for r in rows: print(f'{r[0]:35s}  {r[1]:+.2f} USD  ({r[2]} bets)')
total = sum(r[1] for r in rows)
print(f'TODAY TOTAL: {total:+.2f} USD')
"
```

**Decision tree:**
- Today P&L negative → identify which strategy is bleeding before any new features
- Any strategy at 0 bets when it should be active → investigate loop, not just log
- ETH daily sniper shows any bets → bug, it should be disabled

---

## STEP 5 — Check open positions + per-strategy caps

```bash
cd /Users/matthewshields/Projects/polymarket-bot
python3 -c "
import sqlite3
conn = sqlite3.connect('polybot.db')
# Open bets
open_bets = conn.execute(\"SELECT ticker, strategy, pnl FROM trades WHERE resolved=0 ORDER BY created_at DESC\").fetchall()
print(f'Open bets: {len(open_bets)}')
for b in open_bets[:20]: print(f'  {b[1]:30s} {b[0]}')

# Today's bets per strategy
from datetime import datetime
today = datetime.now().strftime('%Y-%m-%d')
caps = conn.execute('SELECT strategy, COUNT(*) FROM trades WHERE created_at >= ? GROUP BY strategy', (today+'T00:00:00',)).fetchall()
print()
print('Today bets per strategy:')
for c in caps: print(f'  {c[0]:35s}  {c[1]} bets')
"
```

**Decision tree:**
- Any open bet >48h old → investigate, market may have been delisted
- NBA strategy shows ANY open bets or today's bets → STOP, NBA is disabled, investigate
- BTC/ETH sniper >10 bets today → cap is wrong, check config
- sports_game >30 bets/strategy → cap too high, likely a bug

---

## ONLY AFTER ALL 5 STEPS: Decide what to work on

Priority order:
1. Any URGENT item from CCA (Step 1)
2. Any bleeding strategy from P&L (Step 4)
3. Any stuck/crashed bot from health check (Step 3)
4. Unfinished items from session handoff (Step 2)
5. Today's planned work from polybot-init briefing

---

## /polybot-auto CYCLE RULE

Every 3rd monitoring cycle (every ~15 minutes), add this:

```bash
# Cross-chat check (CCA comms)
LAST_CCA=$(stat -f %m ~/.claude/cross-chat/CCA_TO_POLYBOT.md 2>/dev/null || echo 0)
NOW=$(date +%s)
HOURS=$(( (NOW - LAST_CCA) / 3600 ))
if [ $HOURS -gt 48 ]; then
    echo "WARNING: CCA_TO_POLYBOT.md is ${HOURS}h old. Write a POLYBOT_TO_CCA.md request."
fi
tail -100 ~/.claude/cross-chat/CCA_TO_POLYBOT.md | grep -A5 "DELIVERY\|URGENT" | head -20
```

---

## RESTART COMMAND (confirmed working)

```bash
cd /Users/matthewshields/Projects/polymarket-bot
kill $(cat /tmp/polybot.pid 2>/dev/null) 2>/dev/null; sleep 2
./venv/bin/python3 main.py > /tmp/polybot.log 2>&1 &
echo $! > /tmp/polybot.pid
sleep 3 && tail -20 /tmp/polybot.log
```

After restart, verify log shows:
- `[sports_game] Scan: NBA=X NCAAB=X NHL=X MLB=X ...` (NCAAB present if confirmed)
- No `ERROR` lines in first 30 lines
- `[daily_sniper] Waiting for next scan window` (BTC sniper alive)
