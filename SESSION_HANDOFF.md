# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 02:03 UTC (Session 24 — kill switch persistence + asyncio race fixes)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 53450 (Session 24, new code)
Log: `tail -f /tmp/polybot_session24.log`
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**7 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **577/577 ✅**
Latest commits:
- b31d63b — fix: all_time_live_loss_usd uses net P&L not gross losses
- 7204937 — fix: kill switch persistence + asyncio race + regression tests

## KILL SWITCH STATUS (2026-03-01)

**DAILY SOFT STOP ACTIVE** — Live bets blocked for rest of today.
- Daily live losses: $37.10 > $20 limit (20% of $100 starting bankroll)
- Resets at midnight UTC (~10 PM Eastern). Live bets resume then.
- **Paper bets are UNAFFECTED** — paper data collection continues all day on all 7 paper strategies.
- All-time net live P&L: **-$3.73** (well within 30% hard stop threshold of $30)
- No hard stop active. Bot will resume live betting at midnight UTC.

## P&L STATUS (2026-03-01)

- **Bankroll:** $95.37 (from $100 starting, -$4.63 net drawdown, 4.6%)
- **All-time live P&L:** -$3.73 (12 live trades settled today, terrible day)
- **Today live P&L:** -$16.59 (btc_drift worst performer: 3W/8 = -$10.63)
- **All-time paper P&L:** +$16.21
- **All-time win rate:** 62% (paper + live combined)

## WHAT CHANGED IN SESSION 24 (2026-03-01, overnight)

This session was an emergency bug-fix session after Matthew found the bot placing live
bets AFTER the daily kill switch limit had been reached. Root cause: every restart
reset all in-memory loss counters to 0.

### Bug 1: restore_daily_loss() double-counted _realized_loss_usd (CRITICAL — fixed)
- `restore_daily_loss()` was adding to BOTH `_daily_loss_usd` AND `_realized_loss_usd`
- Fix: `restore_daily_loss()` now ONLY touches `_daily_loss_usd`
- New `restore_realized_loss()` handles lifetime counter separately — uses SET not add

### Bug 2: _realized_loss_usd reset to 0 on every restart (CRITICAL — fixed)
- 30% lifetime hard stop counter reset to 0 each restart — made it per-session only
- Fix: `db.all_time_live_loss_usd()` queries NET live P&L loss from DB
  `kill_switch.restore_realized_loss()` seeds the counter on startup
  If lifetime losses already >= 30%, hard stop triggers immediately on startup

### Bug 3: all_time_live_loss_usd() used GROSS losses not NET (CRITICAL — fixed)
- Original `all_time_live_loss_usd()` summed gross losing trade amounts = $41.51
- This SPURIOUSLY triggered hard stop at startup ($41.51 > $30 threshold)
  even though net live P&L is only -$3.73 (3.7% drawdown, NOT 30%)
- Fix: Changed query to `MAX(0, -SUM(pnl_cents))` — net P&L, floors at 0 if profitable
- Tests updated to reflect net semantics

### Bug 4: asyncio race on hourly trade counter (LOW — fixed)
- Two concurrent live loops could both pass `check_order_allowed()` before either
  called `record_trade()`, allowing hourly limit to be exceeded by 1
- Fix: `_live_trade_lock = asyncio.Lock()` created in `main()`, shared across all 3
  live loops. Wraps check→execute→record_trade atomically.
  Paper loops: `trade_lock=None` (no lock, no hourly rate limit applies to paper)

### Also done in Session 23 (same context before summary):
- `btc_lag.py` price range guard (10-90¢) — commits bced652
- Daily loss persistence via `db.daily_live_loss_usd()` + `restore_daily_loss()` — commit a43a1cf
- `btc_drift.py` price range guard (10-90¢) — earlier commit

### Test count: 559 → 577 (+18 new regression tests)
- TestRestoreRealizedLoss: 9 tests (lifetime counter restore semantics)
- TestAllTimeLiveLossUsd: 8 tests (net P&L query correctness)
- TestRestoreDailyLoss: 7 tests (including new test_restore_daily_does_not_touch_realized_loss)

## WHAT NOT TO DO NEXT SESSION

1. **DO NOT build new features** — the expansion gate is in effect. btc_drift needs 30+ live trades
   with Brier < 0.30 before any new bet types. Hard gate: Matthew's standing directive.

2. **DO NOT try to promote btc_lag to Stage 2** — graduation status shows READY FOR LIVE but
   that means ready for live (it already IS live). Stage 2 = $10/bet requires Kelly calibration
   which can't be evaluated at Stage 1 ($5 cap always binds before Kelly).

3. **DO NOT restart the bot unless it's stopped** — check PID first.

4. **DO NOT change kill switch thresholds** — they were just deliberately set.

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Wait for midnight UTC**
- Daily soft stop clears automatically at midnight UTC (~10 PM Eastern)
- Live bets will resume automatically. No action needed.
- Paper bets are running now and all day.

**#2 — Monitor: btc_drift performance**
- Had a very bad day: 3W/8 = -$10.63 live. Watch if this is an anomaly or pattern.
- If 3 more consecutive losses (4 total with current streak), cooling period kicks in.
- Don't adjust strategy parameters — wait for more data.

**#3 — Check paper strategy progress**
- `python main.py --graduation-status` — eth_drift_v1 at 20/30 paper trades
- `python main.py --report` — today's P&L when resuming

**#4 — No Stage 2 promotion**
- Bankroll $95.37, below Stage 2 $100 threshold anyway
- Do NOT raise bet cap until graduation criteria met (30 live trades + Brier < 0.25)

**#5 — FOMC March 5**
- KXFEDDECISION markets open ~March 5 for March 19 meeting
- fomc_rate_v1 paper loop will start firing automatically — no action needed

## RESTART COMMAND (only if bot is stopped)

```bash
kill -9 $(cat bot.pid) 2>/dev/null; sleep 2; rm -f bot.pid && echo "CONFIRM" | nohup /Users/matthewshields/Projects/polymarket-bot/venv/bin/python main.py --live >> /tmp/polybot_session24.log 2>&1 &
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
  43s → [weather]        weather_forecast_v1        — paper (running, no HIGHNY on weekends)
  51s → [fomc]           fomc_rate_v1               — paper (active March 5-19)
  58s → [unemployment]   unemployment_rate_v1       — paper (active until March 7 BLS release)
  65s → [sol_lag]        sol_lag_v1                 — paper (running)
```

## Key Commands

```bash
tail -f /tmp/polybot_session24.log                                  → Watch live bot
source venv/bin/activate && python main.py --report                 → Today's P&L
source venv/bin/activate && python main.py --graduation-status      → Graduation progress
source venv/bin/activate && python main.py --status                 → Live status snapshot
source venv/bin/activate && python -m pytest tests/ -q              → 577 tests
```

## Kill Switch Architecture (post-Session 24)

```
On startup (main.py):
  1. db.all_time_live_loss_usd()   → NET live loss ever (MAX(0, -SUM(pnl_cents)))
     kill_switch.restore_realized_loss(value)  → SET _realized_loss_usd (not add)
     → Triggers hard stop immediately if >= 30% ($30 on $100 bankroll)

  2. db.daily_live_loss_usd()      → Today's gross live losses since midnight UTC
     kill_switch.restore_daily_loss(value)     → ADD to _daily_loss_usd (today only)
     → Triggers daily soft stop if >= $20

During trading (trading_loop, live path only):
  async with _live_trade_lock:           → asyncio.Lock, shared across 3 live loops
    kill_switch.check_order_allowed()    → ALL checks: hard + soft stops
    live_mod.execute()                   → Place the bet
    kill_switch.record_trade()           → Increment hourly counter

After settlement (settlement_loop, live trades only):
  kill_switch.record_loss(loss_usd)      → Adds to _daily_loss_usd + _realized_loss_usd
  kill_switch.record_win()               → Resets consecutive_losses counter

Paper trades use check_paper_order_allowed() — only hard stops block paper.
```

## Autonomous Operation — Standing Directive (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Do the work first, summarize after. Matthew is a doctor with a newborn.
- Security: never expose .env/keys/pem; never modify system files outside project.
- Never break the bot: check PID before restart; verify single instance after.
- Expansion gate: DO NOT build new strategies until current live strategies are solid.
  Hard gate: btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks data + no kill switch events.
