# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 03:10 UTC (Session 25 — consecutive loss persistence fix)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — check PID in bot.pid
Log: `tail -f /tmp/polybot_session25.log`
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**7 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **596/596 ✅**
Latest commits:
- 84a977f — fix: restore consecutive loss streak on restart (prevent cooling bypass)
- c5db0c5 — (previous session)

## KILL SWITCH STATUS (2026-03-01)

**DAILY SOFT STOP ACTIVE** — Live bets blocked for rest of today.
- Daily live losses: $37.10 > $20 limit (20% of $100 starting bankroll)
- Resets at midnight UTC (~10 PM Eastern). Live bets resume then.
- **Paper bets are UNAFFECTED** — paper data collection continues all day.
- All-time net live P&L: **-$3.73** (well within 30% hard stop threshold of $30)
- No hard stop active. Bot will resume live betting at midnight UTC.

## WHAT CHANGED IN SESSION 25 (2026-03-01, ~03:00 UTC)

### Bug fixed: consecutive loss counter NOT persisting across restarts

**Root cause**: `_consecutive_losses` was in-memory only. A restart between trade 85
(3rd consecutive loss) and trade 86 (gap = 2200s) reset the counter to 0, letting the
bot place 3 more losing bets (trades 86, 88, 90) totaling ~$14.74 in preventable losses.

This was the exact same class of bug as Session 24's daily/lifetime counter fixes.

**Fix** (commit 84a977f, 3 files, 19 new tests):
- `db.current_live_consecutive_losses()` — walks live settled trades newest-first,
  counts tail losses until a win, returns current streak
- `kill_switch.restore_consecutive_losses(n)` — seeds counter on startup;
  if n >= CONSECUTIVE_LOSS_LIMIT (4): fires a fresh 2hr cooling period immediately
- `main.py`: calls restore on startup alongside daily/lifetime restores

**Startup log proof** (03:07 UTC restart):
```
Lifetime live loss restored from DB: $3.73 (3.7% of $100.00 hard stop at 30%)
Daily live loss restored from DB: $37.10 (today's running limit: $37.10 / $20.00)
```
Consecutive streak = 0 (last live trade 96 was a WIN) → restore is noop, correct.

### What caused the 6-loss streak from the peak (+$24.96 → -$3.73):
1. Trades 81, 83, 85 = 3 consecutive losses (counter = 3)
2. **Restart happened** (2200s gap) — counter reset to 0
3. Trades 86 (@3¢, guard violation), 88, 90 = 3 more losses that shouldn't have fired
4. Fix now prevents this: restart restores counter from DB, 4th loss triggers cooling

### Kill switch architecture (post-Session 25) — all three counters persist:
```
On startup (main.py):
  1. db.all_time_live_loss_usd()       → restore_realized_loss()  [SET not add]
  2. db.daily_live_loss_usd()          → restore_daily_loss()     [ADD to daily]
  3. db.current_live_consecutive_losses() → restore_consecutive_losses()  [SET + cooling if >=4]

During trading (live only, locked by asyncio.Lock):
  check_order_allowed() → execute() → record_trade()

After settlement (live trades only):
  record_loss() → adds daily + lifetime, increments consecutive, triggers cooling at 4
  record_win()  → resets consecutive counter
```

## P&L STATUS (2026-03-01)

- **Bankroll:** ~$95.37 (from $100 starting)
- **All-time live P&L:** -$3.73
- **Today live P&L:** -$16.59 (12 settled, 38% win rate — bad day)
- **All-time paper P&L:** +$264.34
- **All-time win rate:** 62%

## WHAT NOT TO DO NEXT SESSION

1. **DO NOT build new strategies** — expansion gate in effect
2. **DO NOT change kill switch thresholds** — they were deliberately set
3. **DO NOT restart bot unless stopped** — check PID first
4. **DO NOT promote to Stage 2** — needs Kelly calibration at 30+ live trades

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Wait for midnight UTC (live bets auto-resume)**
Daily soft stop clears at midnight UTC. No action needed.

**#2 — Monitor btc_drift performance**
3 consecutive live losses as of end of Session 25. One more = cool-down.
Do not adjust parameters — wait for more data.

**#3 — Check paper graduation progress**
`python main.py --graduation-status` — eth_drift at 20/30 paper trades.

**#4 — FOMC March 5**
fomc_rate_v1 paper loop will fire automatically when KXFEDDECISION opens.

## RESTART COMMAND (only if bot is stopped)

```bash
kill -9 $(cat bot.pid) 2>/dev/null; sleep 2; rm -f bot.pid && echo "CONFIRM" | nohup /Users/matthewshields/Projects/polymarket-bot/venv/bin/python main.py --live >> /tmp/polybot_session25.log 2>&1 &
sleep 5 && cat bot.pid && ps aux | grep "[m]ain.py"
```

## Loop stagger (reference)

```
   0s → [trading]        btc_lag_v1                 — LIVE (soft-stopped today)
   7s → [eth_trading]    eth_lag_v1                 — LIVE (soft-stopped today)
  15s → [drift]          btc_drift_v1               — LIVE (soft-stopped today)
  22s → [eth_drift]      eth_drift_v1               — paper (running)
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper (running)
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper (running)
  43s → [weather]        weather_forecast_v1        — paper (no HIGHNY on weekends)
  51s → [fomc]           fomc_rate_v1               — paper (active March 5-19)
  58s → [unemployment]   unemployment_rate_v1       — paper (active until March 7 BLS)
  65s → [sol_lag]        sol_lag_v1                 — paper (running)
```

## Key Commands

```bash
tail -f /tmp/polybot_session25.log                                  → Watch live bot
source venv/bin/activate && python main.py --report                 → Today's P&L
source venv/bin/activate && python main.py --graduation-status      → Graduation progress
source venv/bin/activate && python main.py --status                 → Live status snapshot
source venv/bin/activate && python -m pytest tests/ -q              → 596 tests
```

## Autonomous Operation — Standing Directive (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Do the work first, summarize after. Matthew is a doctor with a newborn.
- Security: never expose .env/keys/pem; never modify system files outside project.
- Never break the bot: check PID before restart; verify single instance after.
- Expansion gate: DO NOT build new strategies until current live strategies are solid.
