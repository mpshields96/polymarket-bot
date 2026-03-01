# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 23 cont'd — 540 tests, sol_lag + paper-during-softkill complete)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **stopped** — restart it before checking in.
PID: check `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**7 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, **sol_lag (NEW)**
Test count: **540/540 ✅**
Latest commit: pending this session's work (sol_lag + paper-during-softkill + kill switch threshold changes)

## DO NOT restart the bot unless it's stopped
Check first:
```
cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
```

If stopped, restart:
```
bash scripts/restart_bot.sh
```

## P&L Status (as of 2026-02-28 session)
- **Bankroll:** ~$115 (check `python main.py --report`)
- **All-time live P&L:** +$15.15 (9 settled: 5W 4L) — may have updated since
- **All-time win rate:** 67%
- **Kill switch thresholds (UPDATED Session 23)**:
  - consecutive_loss_limit = **4** (was 5)
  - daily_loss_limit = **20%** ($20 on $100 bankroll, was 15%)

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

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Monitor: SOL lag is now running paper**
- KXSOL15M markets, solusdt@bookTicker feed, min_btc_move_pct=0.8
- Watch for signals in log: `grep "\[sol_lag\]" /tmp/polybot.log`
- Paper data needed for 30 trades before any live consideration

**#2 — NO Stage 2 promotion yet**
- Bankroll ~$115, but Kelly calibration requires 30+ live bets with limiting_factor=="kelly"
- Do NOT raise bet size to $10

**#3 — eth_drift approaching graduation (14/30)**
- Run Step 5 pre-live audit when it hits 30 trades

**#4 — FOMC active March 5**
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
source venv/bin/activate && python -m pytest tests/ -q       → 540 tests
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
