# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 17:10 UTC (Session 25 cont2 — tighter filters, smarter odds)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 3206, log at /tmp/polybot_session25.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**2 strategies LIVE** (real money): btc_lag_v1, btc_drift_v1
**8 strategies paper**: eth_lag_v1 (demoted), eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **603/603 ✅**

Latest commits (most recent first):
- 14620d0 — fix: count_trades_today uses CST midnight (UTC-6), not UTC midnight
- 224b320 — feat: raise btc_drift min_edge 5%→8%, min_drift 0.05%→0.10%
- 1a6c136 — feat: tighten price range guard from 10-90¢ to 35-65¢ on live strategies
- d5d8568 — docs: clean slate — remove stale soft-stop warnings, fix test counts

## KILL SWITCH STATUS (2026-03-01 18:05 UTC)

**NO SOFT STOP** — Live bets active. Daily CST counter reset at midnight CST (06:00 UTC).
- Daily live losses today (CST March 1): **$11.27** / $20.00 limit (56% used — $8.73 remaining)
- All-time net live P&L: **-$15.00** (50% of $30 hard stop — **watch consecutive losses**)
- No hard stop active.
- Consecutive loss streak: **3** (limit 4 — ONE MORE LOSS triggers 2hr soft stop)
- ⚠️ --report "today" uses UTC dates — will show CST-yesterday losses as "today". Use kill switch logs for true CST daily figure.
- **btc_drift_v1 live CST March 1: 3/10 bets, 0W, 3L**
- **btc_lag_v1 live all-time: 2/2, 100% win, +$4.07** (hasn't fired today yet — needs ±0.40% BTC in 60s)

## WHAT CHANGED IN SESSION 25 cont2 (2026-03-01 17:10 UTC)

### Change 1: Tighten price range guard 10-90¢ → 35-65¢ (commit 1a6c136)
User objected to bets at 21¢ ("insane odds"). Near-even-odds only now.
- btc_drift.py: `_MIN_SIGNAL_PRICE_CENTS = 35`, `_MAX_SIGNAL_PRICE_CENTS = 65`
- btc_lag.py: same constants (applies to btc_lag, eth_lag, sol_lag via BTCLagStrategy)
- Updated 8 tests, added 2 new tests — 601/601 passing

### Change 2: Raise btc_drift edge + drift thresholds (commit 224b320)
Reviewed Titanium V36 betting model structure for single-signal edge philosophy.
btc_drift at 5% edge = "speculative" tier with no line movement data. Raised floor.
- `min_edge_pct: 0.05 → 0.08` — need genuine 8% net edge after Kalshi fee
- `min_drift_pct: 0.05 → 0.10` — need ≥0.10% BTC drift from market open (was 0.05)
- Math: at sensitivity=800, need ~0.19% BTC drift to achieve 8% edge at 50¢ market
- Note: Titanium V36 is NOT gospel — reviewed for structural patterns only

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

## P&L STATUS (2026-03-01 18:05 UTC)

- **Bankroll:** $83.74 (DB-based, down from $100 start)
- **All-time live P&L:** -$15.00 (15 settled live bets, 5W/10L = 33%)
- **Today live P&L (CST March 1):** -$11.27 (3 bets, 0W, 3L)
  - Trade 110: btc_drift YES@58¢ -$2.90 (pre-threshold-raise)
  - Trade 113: btc_drift YES@21¢ -$4.41 (pre-price-range-tighten — now BLOCKED)
  - Trade 118: btc_drift YES@44¢ -$3.96 (post-raise, passed all new filters, BTC reversed)
  - NOTE: --report "today" uses UTC date, shows large losses from CST Feb 28. Ignore it for daily limit.
- **All-time paper P&L:** +$222.00 (growing well)
- **btc_lag_v1 live all-time: 2W/0L = +$4.07** — best strategy, needs BTC momentum spike

## WHAT CHANGED IN SESSION 25 cont2 (2026-03-01 18:05 UTC)

### Fix 3: count_trades_today() now uses CST midnight (commit 14620d0)
Same pattern as daily_live_loss_usd(). Daily bet cap now resets at CST midnight, not UTC.
Effect: btc_drift_v1 regained 8/10 CST March 1 slots (CST-yesterday bets no longer eat cap).
A 9.4% edge signal at 53¢ was unblocked and trade 118 (14.1% edge, YES@44¢) was placed.
603/603 tests passing.

## WHAT NOT TO DO

1. **DO NOT build new strategies** — expansion gate in effect
2. **DO NOT change kill switch thresholds** — deliberately set, not trauma-coded
3. **DO NOT re-promote eth_lag to live** until 30 paper trades + Brier < 0.25
4. **DO NOT touch btc_drift parameters again** — just raised; need data collection now
5. **DO NOT add rules after bad outcomes** — read .planning/PRINCIPLES.md first

## KEY PRIORITIES FOR NEXT SESSION

1. **Monitor** — watch live bets (btc_lag_v1 + btc_drift_v1 active, no kill switch blocks)
2. **Data collection** — eth_lag, eth_drift, sol_lag accumulating paper calibration
3. **FOMC March 5** — fomc_rate_v1 paper loop activates automatically
4. **BLS March 7** — unemployment_rate_v1 paper loop activates automatically
5. **Polymarket retail API** — Matthew will provide credentials; wire into py-clob-client auth

## RESTART COMMAND (if bot is stopped)

```bash
cd /Users/matthewshields/Projects/polymarket-bot
kill -9 $(cat bot.pid) 2>/dev/null; sleep 3; rm -f bot.pid
# NOTE: use temp-file for stdin — nohup drops piped stdin (EOFError)
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session25.log 2>&1 &
sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep | grep -v zsh
```

## Loop stagger (reference)

```
   0s → [trading]        btc_lag_v1                 — LIVE
   7s → [eth_trading]    eth_lag_v1                 — PAPER (demoted 2026-03-01)
  15s → [drift]          btc_drift_v1               — LIVE
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
source venv/bin/activate && python -m pytest tests/ -q                   → 601 tests
```
