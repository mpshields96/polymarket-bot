# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 17 — Phase 4.2 complete, 346 tests)
═══════════════════════════════════════════════════

## Current State

8 strategies running in paper mode. All code pushed to GitHub main.
346/346 tests passing. Bot is ready to run.

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

## What was done this session (Session 17)

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

Start the bot and collect paper data:

    python main.py

Expected startup sequence (first 51s):
  [trading]       t=0s  → "Evaluating N market(s)"
  [eth_trading]   t=7s  → "Evaluating N market(s)"
  [drift]         t=15s → "Evaluating N market(s)"
  [eth_drift]     t=22s → "Evaluating N market(s)"
  [btc_imbalance] t=29s → "Evaluating N market(s)"
  [eth_imbalance] t=36s → "Evaluating N market(s)"
  [weather]       t=43s → "No open HIGHNY markets" (weekend) or fetches ensemble forecast
  [fomc]          t=51s → "timing gate" debug (FOMC active from March 5)

Check graduation progress anytime:
    python main.py --graduation-status

FOMC: Next meeting March 19, 2026 → strategy active from March 5, 2026

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
