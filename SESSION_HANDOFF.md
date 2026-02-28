# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 18 — live trading enabled, slippage bug fixed)
═══════════════════════════════════════════════════

## Current State

btc_lag_v1 → LIVE MODE ENABLED ($75 starting bankroll, $5 max/bet)
7 other strategies → paper mode. All code pushed to GitHub main.
346/346 tests passing. DB seeded: 43 btc_lag trades, 81.4% acc, Brier 0.1906 (STRONG).

Loop stagger (seconds):
   0s → [trading]        btc_lag_v1                 — crypto momentum
   7s → [eth_trading]    eth_lag_v1                 — ETH momentum, paper
  15s → [drift]          btc_drift_v1               — BTC drift from open, paper
  22s → [eth_drift]      eth_drift_v1               — ETH drift, paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — VPIN-lite depth ratio, paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — ETH orderbook, paper
  43s → [weather]        weather_forecast_v1        — HIGHNY vs ensemble forecast, paper, 5-min poll
  51s → [fomc]           fomc_rate_v1               — KXFEDDECISION vs yield curve, paper, 30-min poll

verify.py: **18/26** (8 graduation WARNs — advisory only, never blocks startup)
Tests: **346/346 ✅** (was 324, +22 new in Phase 4.2)

## What was done this session (Session 18)

Live trading enabled + critical bug fixed:

1. LIVE_TRADING=true (.env), starting_bankroll_usd=75.00 (config.yaml)
2. Bug fix (4dd1344): NameError in trading_loop — `config` not in scope inside loop.
   All 6 paper executor paths were crashing on signal execution silently.
   Fixed: added `slippage_ticks: int = 1` param, passed from main() at all 6 call sites.
3. Monitoring: scripts/notify_monitor.sh — macOS notifications every 15min (first hr) then 30min
   Kill notifier: kill $(cat /tmp/polybot_notify.pid)
4. Audit: weather_loop, fomc_loop, settlement_loop — all clean, no other scope bugs.
5. Bot running live as of 2026-02-28 ~12:13 UTC. First live signal pending.

## What was done last session (Session 17)

Phase 4.2 — Paper Data Collection Infrastructure:

1. Slippage model (PaperExecutor):
   - `_apply_slippage(fill_price_cents, ticks)` static method — adds ticks, clamps to 99
   - `slippage_ticks: int = 1` param on __init__ — 1-tick adverse fill by default
   - `paper_slippage_ticks: 1` in config.yaml risk section
   - Caller (main.py) reads config and passes slippage_ticks= at construction — paper.py stays config-free
   - execute() signature fixed to keyword-args (ticker, side, price_cents, size_usd, reason)
   - Pre-existing bug fixed: weather/fomc loops were calling old positional signature (would crash at runtime)

2. Graduation progress reporter:
   - `python main.py --graduation-status` — offline command, no Kalshi/Binance startup
   - Prints 8-strategy table: Trades, Days, Brier, Streak, P&L, Status
   - Imports _GRAD thresholds from setup/verify.py (single source of truth)
   - fomc shows 0/5 threshold, weather shows 14-day minimum

3. Settlement result normalization:
   - `market.result` in kalshi.py `_parse_market()` now `.lower()` normalized
   - Robust to any Kalshi API casing changes
   - docs/SETTLEMENT_MAPPING.md created — documents WIN/LOSS logic, PnL formula, settlement flow

Token efficiency update:
   - Rewrote ~/.claude/rules/mandatory-skills-workflow.md — tier system, plan-phase now conditional
   - Rewrote ~/.claude/rules/gsd-framework.md — gsd:quick as default, no mandatory agents
   - Updated CLAUDE.md and MEMORY.md — dual-chat mode, ≤10-15% framework overhead per chat

Commits: f8bfafc, 6013c11, c03e382, c07e82e — all pushed to main

## What was done last session (Session 16)

- btc_drift: `_reference_prices` now stores `(price, minutes_late)` tuple
- Late-entry penalty: max(0.5, 1.0 - max(0, minutes_late-2)/16)
- Live graduation criteria wired: db.graduation_stats(), verify.py [11], docs/GRADUATION_CRITERIA.md
- GSD v1.22.0 installed globally
- 324/324 tests (was 296)

## Next Action (FIRST THING)

Bot is currently RUNNING. If stopped, restart with:

    source venv/bin/activate && python main.py --live
    # Type CONFIRM at the prompt

🔴 LIVE: btc_lag_v1 only ($75 bankroll, $5/bet max). No live trades yet — BTC calm today.
📋 PAPER: all 7 other strategies collecting data. 4 paper trades placed today, 3/3 wins.

### NEXT SESSION GOAL: Enable btc_drift + eth_drift for live trading

The user wants to go live with more strategies. Here's exactly what to do:

1. Check paper trade data first:
   sqlite3 data/polybot.db "SELECT strategy, COUNT(*), SUM(CASE WHEN won=1 OR result=side THEN 1 ELSE 0 END) as wins FROM trades WHERE is_paper=1 AND client_order_id NOT LIKE 'btc_lag_backtest_seed%' GROUP BY strategy"

2. If btc_drift + eth_drift paper win rates look healthy (>60%), enable live by editing main.py:
   Change these two trading_loop calls from live_executor_enabled=False → live_executor_enabled=live_mode:
   - drift_task (btc_drift, line ~950)
   - eth_drift_task (eth_drift, line ~966)
   Optionally also btc_imbalance + eth_imbalance (lines ~984, ~1007)

3. Run tests: python -m pytest tests/ -q
4. Restart bot: Ctrl+C → python main.py --live → CONFIRM

⚠ btc_drift fires on ~every 15-min window → hits 5/day cap fast → ~$15-20/day real spend
⚠ weather won't fire on weekends, fomc won't fire until March 5

FOMC: Next meeting March 19, 2026 → strategy active from March 5, 2026

### Monitoring reminder
Reminders-based notifier PID in /tmp/polybot_notify.pid (15min → 30min intervals)
Kill: kill $(cat /tmp/polybot_notify.pid)
Restart: /tmp/polybot_notify_v3.sh & echo $! > /tmp/polybot_notify.pid

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | api.elections.kalshi.com                       |
| Kalshi REST client           | ✅ Working  | result field .lower() normalized               |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| BTCLagStrategy               | ✅ Running  | btc_lag_v1, 0s stagger, 84.1% backtest         |
| BTCDriftStrategy             | ✅ Running  | btc_drift_v1, paper, sensitivity=800, late-penalty |
| ETH lag strategy             | ✅ Running  | eth_lag_v1, paper, 7s stagger                  |
| ETH drift strategy           | ✅ Running  | eth_drift_v1, paper, sensitivity=800           |
| Orderbook imbalance (BTC)    | ✅ Running  | paper, 29s stagger                             |
| Orderbook imbalance (ETH)    | ✅ Running  | paper, 36s stagger                             |
| WeatherForecastStrategy      | ✅ Running  | ENSEMBLE (Open-Meteo + NWS), adaptive std_dev  |
| FOMCRateStrategy             | ✅ Running  | fomc_rate_v1, paper, 30-min poll, 51s stagger  |
| FREDFeed                     | ✅ Working  | DFF/DGS2/CPI from FRED CSV, hourly cache       |
| PaperExecutor                | ✅ UPGRADED | 1-tick adverse slippage, correct kwarg signature |
| Position deduplication       | ✅ Working  | db.has_open_position() on all 8 loops          |
| Daily bet cap                | ✅ Working  | 5 bets/strategy/day                            |
| Kill switch                  | ✅ Working  | Shared by all 8 loops                          |
| Graduation reporter          | ✅ NEW      | python main.py --graduation-status             |
| Settlement normalization     | ✅ NEW      | market.result .lower() in kalshi.py            |
| Database                     | ✅ Working  | data/polybot.db                                |
| Dashboard                    | ✅ Working  | localhost:8501                                 |
| Settlement loop              | ✅ Ready    | Wired to kill switch, record_win/record_loss   |

## Key Commands

    python main.py                             → Paper mode (8 strategies + settlement)
    python main.py --graduation-status         → Graduation progress table (offline, fast)
    python main.py --report                    → Today's P&L
    python setup/verify.py                     → Pre-flight (18/26, 8 advisory WARNs)
    streamlit run src/dashboard.py             → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 346 tests
    echo "RESET" | python main.py --reset-killswitch
    python scripts/backtest.py --strategy both → BTC lag + drift 30-day simulation

## Signal calibration

  btc_lag / eth_lag:
    min_edge_pct: 0.08 — needs ~0.65% BTC move in 60s
    30-day backtest: 84.1% accuracy, 44 signals/30 days
    ⚠ HFTs compete (Jane St / Susquehanna / Jump) — monitor fill quality vs paper

  btc_drift / eth_drift:
    min_drift_pct: 0.05, min_edge_pct: 0.05, sensitivity: 800
    30-day backtest: 69.1% accuracy, Brier=0.2178 (STRONG)
    Late-entry penalty: max(0.5, 1.0 - max(0, minutes_late-2)/16)
    Capped: 5 bets/day

  orderbook_imbalance (BTC + ETH):
    min_imbalance_ratio: 0.65 — VPIN-lite smart money signal

  weather_forecast (NYC HIGHNY) — ENSEMBLE:
    EnsembleWeatherFeed: Open-Meteo GFS + NOAA NWS/NDFD weighted blend
    Adaptive std_dev: 2.5°F (sources agree) / 3.5°F (normal) / 5.0°F (sources diverge)

  fomc_rate (KXFEDDECISION):
    Yield curve: DGS2 - DFF spread → P(hold/cut/hike) at next meeting
    Only active 14 days before each 2026 FOMC date — next active March 5

## Graduation thresholds (from setup/verify.py _GRAD)

  Most strategies: 30 trades, 7 days, Brier < 0.25, < 5 consecutive losses
  weather_forecast: 30 trades, 14 days (seasonal variation)
  fomc_rate: 5 trades, 0 days (fires ~8x/year)
  All checks: WARN only, never blocks startup

## Research findings — next strategies to consider

1. ✅ Weather ensemble (HIGHNY) — paper running
2. ✅ FOMC/Fed rate markets — paper running
3. ✅ Orderbook imbalance — paper running
4. ⬜ Entertainment/sports markets — 4.79-7.32pp spread vs crypto 0.17pp, less HFT competition
5. ⬜ Market making (Avellaneda-Stoikov) — nikhilnd/kalshi-market-making: 20.3% in 1 day
6. ⬜ Unemployment rate (KXUNRATE) — rmmomin/kalshi-urate-pmf: PMF extraction technique

Priority: Run paper 7+ days → compare all 8 Brier scores → enable best for live.
