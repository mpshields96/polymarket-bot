# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 18:33 UTC (Session 25 cont3 — soft stop active, cooling 2hr)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 4408, log at /tmp/polybot_session25.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**2 strategies LIVE** (real money): btc_lag_v1, btc_drift_v1
**8 strategies paper**: eth_lag_v1 (demoted), eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **603/603 ✅**

Latest commits (most recent first):
- 14620d0 — fix: count_trades_today uses CST midnight (UTC-6), not UTC midnight
- 224b320 — feat: raise btc_drift min_edge 5%→8%, min_drift 0.05%→0.10%
- 1a6c136 — feat: tighten price range guard from 10-90¢ to 35-65¢ on live strategies
- d5d8568 — docs: clean slate — remove stale soft-stop warnings, fix test counts

## KILL SWITCH STATUS (2026-03-01 18:33 UTC)

⛔ **2-HOUR SOFT STOP ACTIVE** — triggered at 12:31 CST (18:31 UTC) by 4th consecutive loss.
- Live bets BLOCKED until ~14:31 CST (20:31 UTC)
- Paper bets CONTINUE uninterrupted
- Daily live losses today (CST March 1): **$15.12** / $20.00 limit (75.6% used — $4.88 remaining)
- All-time net live P&L: **-$18.85** (62.8% of $30 hard stop — ⚠️ watch closely)
- Consecutive loss streak: **4** (limit 4 — soft stop active, resets when cooling ends)
- ⚠️ --report "today" uses UTC dates — will show CST-yesterday losses as "today". Use kill switch logs.
- **btc_drift_v1 live CST March 1: 4/10 bets, 0W, 4L** (all lost to BTC mean reversion)
- **btc_lag_v1 live all-time: 2/2, 100% win, +$4.07** — best strategy, hasn't fired today

## P&L STATUS (2026-03-01 18:33 UTC)

- **Bankroll:** $79.76 (DB-based, down from $100 start)
- **All-time live P&L:** -$18.85 (16 settled live bets, 5W/11L = 31%)
- **Today live P&L (CST March 1):** -$15.12 (4 bets, 0W, 4L)
  - Trade 110: btc_drift YES@58¢ -$2.90 (pre-threshold-raise)
  - Trade 113: btc_drift YES@21¢ -$4.41 (pre-price-range-tighten — now BLOCKED)
  - Trade 118: btc_drift YES@44¢ -$3.96 (post-raise, +0.109% drift, BTC reversed)
  - Trade 121: btc_drift NO@55¢ -$3.85 (post-raise, -0.125% drift, BTC reversed at window close)
  - NOTE: --report "today" uses UTC date, shows large losses from CST Feb 28. Ignore for daily limit.
- **All-time paper P&L:** +$229.43 (paper is profitable — model logic is sound)
- **btc_lag_v1 live all-time: 2W/0L = +$4.07** — signals need ±0.40% BTC in 60s (rare in calm markets)

## btc_drift_v1 pattern analysis (DO NOT change parameters — observation only)
All 4 CST March 1 live losses are the same failure mode: BTC drifts in one direction during
the 15-min window, triggers the model, then MEAN REVERTS before settlement. The drift signal
is detecting real moves but they're reversing, not continuing. This is a statistical pattern —
NOT a mechanical bug. Per PRINCIPLES.md: do NOT change anything based on 4-trade sample.
Need 30+ live trades minimum. The 2hr cooling period is the correct response.

## WHAT CHANGED IN SESSION 25 cont3 (2026-03-01 18:33 UTC)

### Sequence of events:
1. Raised btc_drift thresholds (min_edge 5→8%, min_drift 0.05→0.10%) — commit 224b320
2. Tightened price range guard 10-90¢ → 35-65¢ — commit 1a6c136
3. Fixed count_trades_today() UTC→CST — commit 14620d0
4. Trade 121 placed at 12:19 CST: btc_drift NO@55¢, -0.125% drift, 23.6% edge — BTC reversed in final minute → LOSS
5. Consecutive=4 triggered 2hr soft stop at 12:31 CST

### Kill switch architecture (post-Session 25) — all three counters persist:
```
On startup (main.py):
  1. db.all_time_live_loss_usd()            → restore_realized_loss()    [SET not add]
  2. db.daily_live_loss_usd()               → restore_daily_loss()       [ADD today only]
  3. db.current_live_consecutive_losses()   → restore_consecutive_losses() [SET + cooling if >=4]
```

## WHAT NOT TO DO

1. **DO NOT build new strategies** — expansion gate in effect
2. **DO NOT change kill switch thresholds** — deliberately set, not trauma-coded
3. **DO NOT re-promote eth_lag to live** until 30 paper trades + Brier < 0.25
4. **DO NOT touch btc_drift parameters again** — just raised; need data collection now
5. **DO NOT add rules after bad outcomes** — read .planning/PRINCIPLES.md first
6. **DO NOT panic about btc_drift 4L streak** — 4 trades is statistically meaningless (need 30+)

## KEY PRIORITIES FOR NEXT SESSION

1. **Monitor** — cooling ends ~14:31 CST (20:31 UTC). Watch first few bets after cooling.
2. **Data collection** — eth_lag, eth_drift, sol_lag accumulating paper calibration
3. **FOMC March 5** — fomc_rate_v1 paper loop activates automatically
4. **BLS March 7** — unemployment_rate_v1 paper loop activates automatically
5. **Polymarket retail API** — Matthew will provide credentials; wire into py-clob-client auth
6. **btc_lag_v1 focus** — this is the winning strategy (2/2, +$4.07). Needs ±0.40% BTC spike.

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
source venv/bin/activate && python -m pytest tests/ -q                   → 603 tests
```
