# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 16:15 UTC (Session 25 cont — CST timezone fix, dashboard, Polymarket plan)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID in bot.pid, log at /tmp/polybot_session25.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**2 strategies LIVE** (real money): btc_lag_v1, btc_drift_v1
**8 strategies paper**: eth_lag_v1 (demoted), eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **598/598 ✅**

Latest commits (most recent first):
- 317c04a — fix: daily loss counter resets at CST midnight (not UTC)
- 773f515 — feat: demote eth_lag to paper-only + add PRINCIPLES.md anti-bloat doc
- 84a977f — fix: restore consecutive loss streak on restart (prevent cooling bypass)

## KILL SWITCH STATUS (2026-03-01 16:15 UTC)

**NO SOFT STOP** — Live bets active. Daily CST counter reset at midnight CST (06:00 UTC).
- Daily live losses today (CST March 1): $0.00 — yesterday's losses were CST Feb 28
- All-time net live P&L: **-$3.73** (well within 30% hard stop)
- No hard stop active.
- Consecutive loss streak: 0 (last live trade was a win)

## WHAT CHANGED IN SESSION 25

### Fix 1: Consecutive loss counter now persists across restarts (commit 84a977f)
The missing piece after Session 24. Same class of bug as daily/lifetime counters.
- `db.current_live_consecutive_losses()` — queries DB for current streak on startup
- `kill_switch.restore_consecutive_losses(n)` — seeds counter; fires cooling if n >= 4
- Wired into main.py alongside daily/lifetime restores
- 19 new regression tests

### Fix 2: eth_lag_v1 demoted to paper-only (commit 773f515)
eth_lag was promoted to live with 0/30 paper graduation trades — process violation.
Changed in main.py: `live_executor_enabled=False`, `trade_lock=None`, `max_daily_bets=max_daily_bets_paper`.
Re-promote only after: 30+ settled paper trades + Brier < 0.25.

### New doc: .planning/PRINCIPLES.md (commit 773f515)
Permanent anti-bloat reference. Captures:
- Mechanical defect vs statistical outcome test
- Why paper bets continue during live soft stops
- Anti-trauma-coding principle with concrete examples
- Graduation criteria mandate
- win_prob floor analysis (floor bets are actually +$5.24 P&L — do not change)
Referenced from CLAUDE.md header so every future session sees it.

### Kill switch architecture (post-Session 25) — all three counters persist:
```
On startup (main.py):
  1. db.all_time_live_loss_usd()            → restore_realized_loss()    [SET not add]
  2. db.daily_live_loss_usd()               → restore_daily_loss()       [ADD today only]
  3. db.current_live_consecutive_losses()   → restore_consecutive_losses() [SET + cooling if >=4]
```

## P&L STATUS (2026-03-01)

- **Bankroll:** ~$95.37
- **All-time live P&L:** -$3.73 (adjusted for 2 guard-violation bets: +$6.25)
- **Today live P&L:** -$16.59 (12 settled, bad day — daily soft stop active)
- **All-time paper P&L:** +$264.34
- **All-time win rate:** 62%

## WHAT NOT TO DO

1. **DO NOT build new strategies** — expansion gate in effect
2. **DO NOT change kill switch thresholds** — deliberately set, not trauma-coded
3. **DO NOT re-promote eth_lag to live** until 30 paper trades + Brier < 0.25
4. **DO NOT touch btc_drift parameters** — needs 30+ live trades + Brier score first
5. **DO NOT add rules after bad outcomes** — read .planning/PRINCIPLES.md first

## KEY PRIORITIES FOR NEXT SESSION

1. **Midnight UTC** — daily soft stop clears, btc_lag + btc_drift resume live
2. **Monitor** — watch first live bets after midnight for correct behavior
3. **Data collection** — eth_lag, eth_drift, sol_lag accumulating paper calibration
4. **FOMC March 5** — fomc_rate_v1 paper loop activates automatically
5. **BLS March 7** — unemployment_rate_v1 paper loop activates automatically

## RESTART COMMAND (if bot is stopped)

```bash
cd /Users/matthewshields/Projects/polymarket-bot
pkill -f "python main.py" 2>/dev/null; sleep 3; rm -f bot.pid
# NOTE: use temp-file for stdin — nohup drops piped stdin (EOFError)
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session25.log 2>&1 &
sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep | grep -v zsh
```

## Loop stagger (reference)

```
   0s → [trading]        btc_lag_v1                 — LIVE (soft-stopped today)
   7s → [eth_trading]    eth_lag_v1                 — PAPER (demoted 2026-03-01)
  15s → [drift]          btc_drift_v1               — LIVE (soft-stopped today)
  22s → [eth_drift]      eth_drift_v1               — paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper
  43s → [weather]        weather_forecast_v1        — paper (no HIGHNY weekends)
  51s → [fomc]           fomc_rate_v1               — paper (active March 5-19)
  58s → [unemployment]   unemployment_rate_v1       — paper (active until March 7)
  65s → [sol_lag]        sol_lag_v1                 — paper
```

## Key Commands

```bash
tail -f /tmp/polybot_session25.log                                       → Watch bot
source venv/bin/activate && python main.py --report                      → Today's P&L
source venv/bin/activate && python main.py --graduation-status           → Paper progress
source venv/bin/activate && python main.py --status                      → Live snapshot
source venv/bin/activate && python -m pytest tests/ -q                   → 596 tests
```
