# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 21 — 473 tests, $100 bankroll, paper/live separation fixed)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: stored in `bot.pid` (run `cat bot.pid` to get it)
Log: `/tmp/polybot_session21.log` — `tail -f /tmp/polybot_session21.log` to watch live

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **473/473 ✅** (33 new tests for live.py added this session)
Latest commit: **188d01c** — `fix: live executor hardcoded strategy name btc_lag → dynamic`
Uncommitted changes: main.py (paper/live separation fix), config.yaml ($100 bankroll)
GitHub: push pending — see "What changed in Session 21" below

## DO NOT restart the bot unless it's stopped
Check first: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

If stopped, restart:
```
rm -f bot.pid && source venv/bin/activate && echo "CONFIRM" | nohup python main.py --live >> /tmp/polybot_session21.log 2>&1 &
```

## What changed in Session 21 (2026-02-28)

### Priority #1 complete: tests for src/execution/live.py (was ZERO)
- Created `tests/test_live_executor.py` — 33 tests covering ALL paths in the real-money executor
- pytest.ini created with `asyncio_mode = auto` (enables async tests)
- pytest-asyncio==0.23.7 installed into venv
- Test classes: TestDetermineLimitPrice, TestExecuteGuards, TestExecuteSuccess, TestRegressions, TestExecuteFailures
- Regressions covered: strategy_name not hardcoded, is_paper=False, server_order_id stored, guards enforced
- **473/473 tests passing** (was 440)

### Bankroll updated to $100
- config.yaml: `starting_bankroll_usd: 100.00` (was 75.00)
- Matthew deposited $25 — Kalshi balance now $103.51 ($75 original + $25 deposit + $3.50 from first live win)
- Kill switch confirmed: "KillSwitch initialized (starting bankroll: $100.00)"
- New daily loss limit: 15% of $100 = $15.00 (was $11.25)

### Paper/live separation fix (main.py)
**Bug**: `has_open_position()` and `count_trades_today()` defaulted to mixing paper + live bets.
- Effect: 7 paper btc_drift bets were eating into the 10-bet live daily quota
- Effect: A paper bet on a market window would block a live bet on the same window

**Fix**: Pass `is_paper` filter to both calls in all 4 loop locations:
- `trading_loop()`: `is_paper_mode = not (live_executor_enabled and live_confirmed)` computed once
  → `has_open_position(ticker, is_paper=is_paper_mode)` — live dedup only blocks live, paper only blocks paper
  → `count_trades_today(strategy, is_paper=is_paper_mode)` — live cap counts live bets only
- `weather_loop()`, `fomc_loop()`, `unemployment_loop()`: hardcoded `is_paper=True` (always paper)

### Bot restarted
- Restart at 16:15 UTC with `nohup ... >> /tmp/polybot_session21.log`
- All 9 loops confirmed started (log shows all stagger delays)
- Fresh window (KXBTC15M-26FEB281730-30) ready for first live btc_drift bet this run

### Live P&L status (as of restart)
- First live bet (trade_id=64, "btc_lag" label, was btc_drift) — SETTLED WON: +$3.50
- All-time live P&L: $3.50 | All-time paper P&L: $45.73 | All-time win rate: 78%
- Note: trade_id=64 has wrong strategy label ("btc_lag" not "btc_drift_v1") — unfixable, from Session 20 bug

## Loop stagger (what's running right now)
```
   0s → [trading]        btc_lag_v1                 — LIVE, BTC momentum, min_edge=0.04
   7s → [eth_trading]    eth_lag_v1                 — LIVE, ETH momentum, min_edge=0.04
  15s → [drift]          btc_drift_v1               — LIVE, BTC drift, min_edge=0.05
  22s → [eth_drift]      eth_drift_v1               — paper, ETH drift
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper, VPIN-lite depth ratio
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper, ETH orderbook
  43s → [weather]        weather_forecast_v1        — paper, HIGHNY vs ensemble forecast
  51s → [fomc]           fomc_rate_v1               — paper, active March 5–19
  58s → [unemployment]   unemployment_rate_v1       — paper, active Feb 28 – Mar 7
```

## KEY PRIORITY FOR NEXT SESSION

**#1 — Commit and push Session 21 changes** (uncommitted):
- tests/test_live_executor.py (33 new tests)
- pytest.ini (asyncio_mode = auto)
- main.py (paper/live separation fix)
- config.yaml ($100 bankroll)

**#2 — Monitor live results**
- `python main.py --report` — check P&L, verify btc_drift shows live bets (🔴 not 📋)
- `python main.py --graduation-status` — track toward 30 live trades threshold
- Watch `/tmp/polybot_session21.log` for [LIVE] order placement messages
- btc_drift should now place live bets on each 15-min window it hasn't already bet on

**#3 — Ongoing: no new strategies until live P&L data is in**
- Sports game skeleton built but disabled — enable after 30 live trades collected
- Focus: data quality, monitoring, stability

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | api.elections.kalshi.com                       |
| Kalshi REST client           | ✅ Working  |                                                |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| btc_lag_v1                   | ✅ LIVE     | 0s stagger, 77.1% at 4% threshold             |
| eth_lag_v1                   | ✅ LIVE     | 7s stagger, same model as btc_lag             |
| btc_drift_v1                 | ✅ LIVE     | 15s stagger, 69.1% acc, Brier=0.22            |
| eth_drift_v1                 | ✅ Paper    | 22s stagger                                   |
| orderbook_imbalance_v1       | ✅ Paper    | 29s stagger                                   |
| eth_orderbook_imbalance_v1   | ✅ Paper    | 36s stagger                                   |
| weather_forecast_v1          | ✅ Paper    | ENSEMBLE (Open-Meteo + NWS), weekdays only    |
| fomc_rate_v1                 | ✅ Paper    | 30-min poll, active March 5–19               |
| unemployment_rate_v1         | ✅ Paper    | 30-min poll, active Feb 28 – Mar 7           |
| sports_game_v1               | ✅ Built    | DISABLED — awaiting 30 live trades + ODDS_API_KEY|
| PaperExecutor                | ✅ Working  | 1-tick adverse slippage                       |
| LiveExecutor (live.py)       | ✅ Working  | 33 tests now cover all paths                  |
| Kill switch                  | ✅ Working  | $100 base, 15% daily limit = $15.00           |
| Position dedup               | ✅ Fixed    | Now separate: live dedup only blocks live bets |
| Daily bet caps               | ✅ Fixed    | Live cap counts live only, paper cap counts paper only |
| Graduation reporter          | ✅ Working  | python main.py --graduation-status            |
| --status / --report          | ✅ Working  | bypass PID lock, safe while bot is live       |

## Key Commands

```
python main.py --live                       → Start bot (9 loops + settlement)
python main.py --status                     → Live status (works while bot running)
python main.py --graduation-status          → Graduation progress table
python main.py --report                     → Today's P&L (per-strategy breakdown)
python setup/verify.py                      → Pre-flight (18/26, 8 advisory WARNs)
streamlit run src/dashboard.py              → Dashboard at localhost:8501
source venv/bin/activate && python -m pytest tests/ -v  → 473 tests
echo "RESET" | python main.py --reset-killswitch
tail -f /tmp/polybot_session21.log          → Watch live bot output
```

## Signal calibration (live strategies)

btc_lag_v1 / eth_lag_v1 (LIVE):
  min_edge_pct: 0.04 — needs ~0.32% BTC/ETH move in 60s (binding constraint)
  Calm market → 0 signals/day. Expected. Not a bug.
  Backtest: 77.1% accuracy, ~8 signals/day (30-day avg includes volatile days)

btc_drift_v1 (LIVE):
  min_drift_pct: 0.05, min_edge_pct: 0.05, sensitivity: 800
  Fires on ~96% of 15-min windows → generates bets in all market conditions
  30-day backtest: 69.1% accuracy, Brier=0.22 (STRONG)
  Risk: daily loss limit 15% of $100 = $15.00 before auto-halt

## Graduation thresholds

All strategies: 30 live trades, Brier < 0.30, < 4 consecutive losses
fomc_rate: 5 trades (fires ~8x/year)
No day minimums — 30 real trades is the only volume gate

## Context handoff
New chat: read POLYBOT_INIT.md first, then this file, then proceed.
Bot is running — DO NOT restart unless confirmed stopped.
