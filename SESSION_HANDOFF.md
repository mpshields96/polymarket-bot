# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 20 post-compaction — 4 live bugs fixed, first live bet placed)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: stored in `bot.pid` (run `cat bot.pid` to get it)
Log: `/tmp/polybot_session20.log` — `tail -f /tmp/polybot_session20.log` to watch live

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **440/440 ✅**
Latest commit: **188d01c** — `fix: live executor hardcoded strategy name btc_lag → dynamic`
GitHub: pushed to main, all clean

## DO NOT restart the bot unless it's stopped
Check first: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

If stopped, restart:
```
rm -f bot.pid && source venv/bin/activate && echo "CONFIRM" | nohup python main.py --live >> /tmp/polybot_session20.log 2>&1 &
```

## What changed in Session 20 (this session — 2026-02-28)

### Promoted to LIVE
- **eth_lag_v1**: was paper, now LIVE (same executor path, min_edge=0.04)
- **btc_drift_v1**: was paper, now LIVE (69.1% accuracy, Brier=0.22, fires ~96% of windows)
- **min_edge_pct**: btc_lag + eth_lag lowered 0.06 → 0.04 (~8 signals/day, 77.1% acc)

### 4 live-trading bugs found and fixed (Session 20 post-compaction)

**Bug 1 — Kill switch counting paper losses toward daily limit** (main.py settlement_loop)
- Paper trades (3x ~$3.74 each = $11.18) were near the $11.25 daily limit
- Fix: `settlement_loop` now calls `record_win/record_loss` ONLY for `is_paper=False` trades
- Without this fix, paper losses would have triggered the daily kill switch on real-money days

**Bug 2 — Live executor double-CONFIRM (primary cause of 0 live bets for 2 hours)**
- `live.py` has `_FIRST_RUN_CONFIRMED` module-level global that calls `input()` on first order
- When `echo "CONFIRM" | python main.py --live` is used, CONFIRM is consumed by main.py startup
- When live.py ran later, `input()` got `""` ≠ "CONFIRM" → returned `None` silently → no bet
- Fix: main.py now sets `_live_exec_mod._FIRST_RUN_CONFIRMED = True` after startup confirmation

**Bug 3 — kalshi_payout() called with NO price for NO-side signals**
- `kalshi_payout(yes_price_cents, side)` always expects YES price
- For NO-side signals, `signal.price_cents` is the NO price (e.g. 4¢ when YES=96¢)
- Result: payout = 0.042 → Kelly went negative → `sizing.calculate_size()` returned None → no bet
- Fix: `yes_price_cents_for_payout = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)`

**Bug 4 — Hardcoded strategy name in live.py** (found post-bugs, fixed after first live bet)
- `db.save_trade(strategy="btc_lag")` was hardcoded — every live trade was labeled "btc_lag"
- Fix: added `strategy_name: str = "unknown"` param to `execute()`, pass `strategy.name` from main.py
- Trade_id=64 (first live bet ever) was saved with wrong strategy name — cannot fix retroactively

### First live bet placed
- trade_id=64, strategy mislabeled "btc_lag" (was actually btc_drift — can't fix retroactively)
- BUY NO, 7 contracts @ 48¢ = $3.36, KXBTC15M-26FEB281700-00
- server_id=15e20bed-4f9f-420e-8618-967eb1741f3b, status=executed
- Window had 12+ min remaining when placed. Awaiting settlement result.

### sports_game_v1 skeleton (built but DISABLED)
- `src/data/odds_api.py` + `src/strategies/sports_game.py` + 28 tests
- Will NOT be wired into main.py until live results are confirmed (user decision)
- ODDS_API_KEY not yet in .env

### Session 20 commits (all pushed to main)
- `0f6bae7` — feat: enable btc_drift_v1 for live trading
- `891e988` — fix: two critical live trading bugs (paper losses + double-CONFIRM)
- `e41b059` — fix: kalshi_payout called with NO price for NO-side signals
- `188d01c` — fix: live executor hardcoded strategy name btc_lag → dynamic

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

**#1 — Write tests for `src/execution/live.py`** — ZERO tests currently exist for real-money execution
This is the highest-priority testing gap. Before adding any features, add integration tests that:
- Mock the Kalshi API (mock `kalshi.create_order()`)
- Exercise the full path: signal → live.execute() → DB record
- Verify strategy_name is stored correctly
- Verify price conversion (NO-side signals use YES price for payout)
- Verify kill switch is the last gate called

**#2 — Monitor live trade results**
- Run `python main.py --report` to see P&L
- Run `python main.py --graduation-status` to see paper graduation progress
- First live bet (trade_id=64) needs to settle — watch the 17:00 UTC settlement
- btc_lag_v1 needs ±0.40% BTC move in 60s — calm days = 0 signals (expected, not a bug)
- btc_drift fires on ~96% of windows → expect 1-3 live bets per day from drift

**#3 — User priority: "perfect and optimize the current framework"**
- No new strategies until live results data is in
- No sports_game wiring until live P&L confirmed profitable
- Focus: stability, observability, debugging, fixing anything that's off

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
| sports_game_v1               | ✅ Built    | DISABLED — awaiting live results + ODDS_API_KEY|
| PaperExecutor                | ✅ Working  | 1-tick adverse slippage                       |
| LiveExecutor (live.py)       | ✅ Working  | 4 bugs fixed Session 20, ZERO unit tests      |
| Kill switch                  | ✅ Working  | 9 loops share it, paper losses excluded now   |
| Position dedup               | ✅ Working  | db.has_open_position() on all 9 loops         |
| Daily bet caps               | ✅ Working  | live=10/day, paper=35/day per strategy        |
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
source venv/bin/activate && python -m pytest tests/ -v  → 440 tests
echo "RESET" | python main.py --reset-killswitch
tail -f /tmp/polybot_session20.log          → Watch live bot output
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
  Risk: daily loss limit 15% of $75 = $11.25 before auto-halt (live losses only)

## Graduation thresholds

All strategies: 30 live trades, Brier < 0.30, < 4 consecutive losses
fomc_rate: 5 trades (fires ~8x/year)
No day minimums — 30 real trades is the only volume gate

## Context handoff
New chat: read POLYBOT_INIT.md first, then this file, then proceed.
Bot is running — DO NOT restart unless confirmed stopped.
