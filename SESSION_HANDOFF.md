# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 23 cont'd — 559 tests, price guard + daily loss persistence)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running** — PID 40106 (check before restarting)
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**7 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **559/559 ✅**
Latest commit: a43a1cf — daily loss persistence fix

## DO NOT restart the bot unless it's stopped
Check first:
```
cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
```

If stopped, restart:
```
bash scripts/restart_bot.sh
```

## P&L Status (as of 2026-03-01 session 23 cont'd)
- **Bankroll:** $90.37 (significant drawdown from +$24.96 peak)
- **All-time live P&L:** -$2.58 (today alone: -$15.44, 10 settled)
- **Win rate today (live):** low — bad day, all strategy bets lost on extreme prices
- **Kill switch thresholds (UPDATED Session 23)**:
  - consecutive_loss_limit = **4** (was 5)
  - daily_loss_limit = **20%** ($20 on $100 bankroll, was 15%)
- **SOFT STOP active**: daily live loss restored to $34.30 > $20 limit. No new live bets until midnight UTC. Paper bets continuing.

## What changed in Session 23 (continued — 2026-02-28)

### Tests: 515 → 540 (+25)
- tests/test_kill_switch.py: TestPaperOrderAllowed (7 tests for check_paper_order_allowed)
- tests/test_sol_strategy.py: 18 tests (TestSolFeed, TestSolLagFactory, TestSolSignalGeneration)

### New: SOL 15-min lag strategy (paper-only)
- `load_sol_from_config()` in binance.py — solusdt@bookTicker feed
- `load_sol_lag_from_config()` in btc_lag.py — BTCLagStrategy(name_override="sol_lag_v1", min_btc_move_pct=0.8)
- config.yaml: sol_lag strategy section + sol feeds added
- main.py: sol_task wired at 65s stagger (paper-only, live_executor_enabled=False)

### New: Paper-during-softkill
- `kill_switch.check_paper_order_allowed()` — only hard stops block paper trades
- Soft stops (daily loss, consecutive losses, hourly rate limit) do NOT block paper data collection
- Wired in: trading_loop (paper path), weather_loop, fomc_loop, unemployment_loop
- Live path in trading_loop still uses check_order_allowed() (all soft stops apply to live bets)

### Kill switch threshold changes
- consecutive_loss_limit: 5 → 4 (src/risk/kill_switch.py CONSECUTIVE_LOSS_LIMIT)
- daily_loss_limit_pct: 0.15 → 0.20 (DAILY_LOSS_LIMIT_PCT) — $20 on $100 bankroll
- Tests updated in TestDailyLossLimit and TestConsecutiveLossCooling

### Research: Hourly BTC/ETH markets confirmed non-existent
- Kalshi has NO hourly BTC/ETH price-direction markets (probed all 8,719 series)
- Only 15-min crypto series exist: KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M, KXBNB15M, KXBCH15M
- Pivot: SOL 15-min (KXSOL15M confirmed open, SOLUSDT on Binance.US confirmed)

### New (session 23 cont'd, 2026-03-01): 3 more bug fixes
**1. Price range guard extended to btc_lag** (commit bced652)
- eth_lag_v1 placed NO@2¢ on KXETH15M [LIVE] — same structural gap as btc_drift
- Added `_MIN_SIGNAL_PRICE_CENTS=10` / `_MAX_SIGNAL_PRICE_CENTS=90` to btc_lag.py
- Applies to btc_lag_v1, eth_lag_v1, sol_lag_v1 (all use BTCLagStrategy)
- 4 new tests in TestPriceExtremesFilter (test_strategy.py)

**2. Daily loss counter now persists across restarts** (commit a43a1cf)
- On restart, _daily_loss_usd reset to 0, bypassing daily limit mid-session
- Fix: db.daily_live_loss_usd() + kill_switch.restore_daily_loss() + main.py wiring
- Bot now restores $34.30 today's losses → daily soft stop correctly firing
- 11 new tests: TestDailyLiveLossUsd (5) + TestRestoreDailyLoss (6)

**3. btc_drift price guard** (commit 819c2ce, previous)
- Added same 10-90¢ guard to btc_drift.py (was missing)

**Tests: 540 → 559 (+19)**

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Daily soft stop will clear at midnight UTC (02:00 AM Eastern)**
- Until then: live bets are soft-blocked ($34.30 loss restored > $20 limit)
- Paper bets continue on all 7 paper strategies
- Bankroll: $90.37. If the 3 pending bets (YES@56¢ ETH LIVE, NO@65¢ BTC LIVE, NO@33¢ ETH PAPER) win, bankroll recovers slightly

**#2 — Monitor: SOL lag is now running paper**
- KXSOL15M markets, solusdt@bookTicker feed, min_btc_move_pct=0.8
- Watch for signals in log: `grep "\[sol_lag\]" /tmp/polybot.log`
- Paper data needed for 30 trades before any live consideration

**#3 — NO Stage 2 promotion yet**
- Bankroll $90.37 (below Stage 2 $100 threshold anyway)
- Kelly calibration still needs 30+ live settled bets. Do NOT raise bet size.

**#4 — eth_drift approaching graduation**
- Run `python main.py --graduation-status` to check current count
- Run Step 5 pre-live audit when it hits 30 trades

**#5 — FOMC active March 5**
- KXFEDDECISION markets open ~March 5 for March 19 meeting

## Loop stagger (after restart)
```
   0s → [trading]        btc_lag_v1                 — LIVE
   7s → [eth_trading]    eth_lag_v1                 — LIVE
  15s → [drift]          btc_drift_v1               — LIVE
  22s → [eth_drift]      eth_drift_v1               — paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper
  43s → [weather]        weather_forecast_v1        — paper
  51s → [fomc]           fomc_rate_v1               — paper, active March 5-19
  58s → [unemployment]   unemployment_rate_v1       — paper, active Feb 28 – Mar 7
  65s → [sol_lag]        sol_lag_v1                 — paper (NEW)
```

## Key Commands
```
tail -f /tmp/polybot.log                                     → Watch live bot (always open)
source venv/bin/activate && python main.py --report          → Today's P&L
source venv/bin/activate && python main.py --graduation-status → Graduation progress
source venv/bin/activate && python main.py --status          → Live status snapshot
source venv/bin/activate && python main.py --export-trades   → Refresh reports/trades.csv
source venv/bin/activate && python -m pytest tests/ -q       → 559 tests
bash scripts/restart_bot.sh                                  → Safe restart
cat reports/trades.csv                                       → All trades (committed to git)
```

## Odds API — Standing Directives (never needs repeating)
- OddsAPI: 20,000 credits/month, renewed March 1
- **HARD CAP: 1,000 credits max for polymarket-bot**
- Sports props/moneyline/totals = ENTIRELY SEPARATE project — NOT for Kalshi bot
- Before ANY credit use: implement quota guard first

## AUTONOMOUS OPERATION — STANDING DIRECTIVE (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Security: never expose .env/keys/pem; never modify system files outside project dir.
- Never break the bot: confirm running/stopped before restart; verify single instance after.
- Expansion order: (1) perfect live/paper, (2) graduate paper→live with Step 5 audit, (3) new bet types.
- Framework overhead: ≤10-15% of 5-hour token limit total. Use gsd:quick only when multi-step tracking needed.

## Context handoff: new chat reads POLYBOT_INIT.md first, then this file, then proceeds.
