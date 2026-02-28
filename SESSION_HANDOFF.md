# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 14 — FOMC/FRED strategy, 257 tests)
═══════════════════════════════════════════════════

## Current State

9 strategies running in parallel in paper mode.
8 async trading loops + 1 settlement loop, staggered to spread Kalshi API calls.
257/257 tests passing.

Loop stagger (seconds):
   0s → [trading]        btc_lag_v1                 — crypto momentum
   7s → [eth_trading]    eth_lag_v1                 — ETH momentum, paper
  15s → [drift]          btc_drift_v1               — BTC drift from open, paper
  22s → [eth_drift]      eth_drift_v1               — ETH drift, paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — VPIN-lite depth ratio, paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — ETH orderbook, paper
  43s → [weather]        weather_forecast_v1        — HIGHNY vs Open-Meteo, paper, 5-min poll
  51s → [fomc]           fomc_rate_v1               — KXFEDDECISION vs yield curve, paper, 30-min poll

verify.py: **18/18 ✅**
Tests: **257/257 ✅** (was 212, +45 new FOMC strategy tests)

## What was done this session (Session 14)

1. Researched FOMC data sources:
   → CME FedWatch blocked from server IPs (scrape-ban)
   → FRED CSV endpoint FREE, no API key: fred.stlouisfed.org/graph/fredgraph.csv
   → Kalshi KXFEDDECISION confirmed active: 5M+ volume, tickers H0/C25/C26/H25/H26

2. Built FRED economic data feed (src/data/fred.py)
   → FREDFeed: fetches DFF (fed funds rate), DGS2 (2yr yield), CPIAUCSL (3 months)
   → FREDSnapshot: computed yield_spread, cpi_accelerating, cpi_mom_latest
   → Caches 1 hour (FRED updates once/day), synchronous CSV fetch (~600ms)
   → No API key required — uses public fredgraph.csv endpoint

3. Built FOMC rate strategy (src/strategies/fomc_rate.py)
   → Signal model: yield_spread = DGS2 - DFF
     * spread < -0.50% → aggressive cut regime (P(hold)=0.30, P(cut25)=0.50)
     * spread < -0.25% → mild cut bias  (P(hold)=0.55, P(cut25)=0.35)
     * |spread| ≤ 0.25% → hold regime   (P(hold)=0.75, P(cut25)=0.15)
     * spread > +0.25% → hike bias      (P(hold)=0.45, P(hike25)=0.40)
   → CPI adjustment: ±8% shift between hold/cut when CPI accelerating/decelerating
   → Hardcoded 2026 FOMC dates (8 meetings) — only fires in 14-day window before each
   → Ticker parser: KXFEDDECISION-26MAR-H0 → FedAction.HOLD
   → 45 tests in tests/test_fomc_strategy.py

4. Updated config.yaml: strategy.fomc section
5. Updated main.py: fomc_loop() function + fomc_task (stagger 51s, polls 30min)
6. 257/257 tests passing

## Next Action (FIRST THING)

Run the bot and watch 8 loops start:

    python main.py

Expected startup sequence (first 51s):
  [trading]       t=0s  → BTC lag evaluating
  [eth_trading]   t=7s  → ETH lag evaluating
  [drift]         t=15s → BTC drift evaluating
  [eth_drift]     t=22s → ETH drift evaluating
  [btc_imbalance] t=29s → BTC orderbook evaluating
  [eth_imbalance] t=36s → ETH orderbook evaluating
  [weather]       t=43s → "No open HIGHNY markets" (weekend) or fetches forecast
  [fomc]          t=51s → "No open KXFEDDECISION markets" OR evaluates with FRED data

FOMC strategy fires 14 days before each meeting:
  → Next meeting: March 19, 2026 → strategy active from March 5
  → Current date: Feb 28, 2026 → FOMC loop will log "timing gate" debug messages

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | $75 balance confirmed                          |
| Kalshi REST client           | ✅ Working  | api.elections.kalshi.com                       |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| BTCLagStrategy               | ✅ Running  | btc_lag_v1, 0s stagger                         |
| BTCDriftStrategy             | ✅ Running  | btc_drift_v1, paper, 15s stagger               |
| ETH lag strategy             | ✅ Running  | eth_lag_v1, paper, 7s stagger                  |
| ETH drift strategy           | ✅ Running  | eth_drift_v1, paper, 22s stagger               |
| Orderbook imbalance (BTC)    | ✅ Running  | paper, 29s stagger                             |
| Orderbook imbalance (ETH)    | ✅ Running  | paper, 36s stagger                             |
| WeatherForecastStrategy      | ✅ Running  | paper, 5-min poll, 43s stagger                 |
| FOMCRateStrategy             | ✅ NEW      | fomc_rate_v1, paper, 30-min poll, 51s stagger  |
| FREDFeed                     | ✅ NEW      | DFF/DGS2/CPI from FRED CSV, hourly cache       |
| Kill switch                  | ✅ Working  | Shared by all 8 loops                          |
| Database                     | ✅ Working  | data/polybot.db                                |
| Dashboard                    | ✅ Working  | localhost:8501                                 |
| Settlement loop              | ✅ Ready    | Runs, wired to kill switch                     |

## Key Commands

    python main.py                    → Paper mode (8 strategies + settlement)
    python main.py --verify           → Pre-flight check (18/18)
    streamlit run src/dashboard.py   → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 257 tests
    echo "RESET" | python main.py --reset-killswitch
    python scripts/backtest.py --days 30   → 30-day BTC drift calibration

## Signal calibration

  btc_lag / eth_lag:
    min_edge_pct: 0.08 — needs ~0.65% BTC move in 60s

  btc_drift / eth_drift:
    min_drift_pct: 0.05, min_edge_pct: 0.05 — fires at ~0.15-0.3% drift
    30-day backtest: 69% accuracy, Brier=0.2330

  orderbook_imbalance (BTC + ETH):
    min_imbalance_ratio: 0.65 — VPIN-lite smart money signal

  weather_forecast (NYC HIGHNY):
    Normal distribution model: N(forecast_temp_f, 3.5°F) vs Kalshi YES price
    min_edge_pct: 0.05, min_minutes_remaining: 30

  fomc_rate (KXFEDDECISION):
    Yield curve: DGS2 - DFF spread → P(hold/cut/hike) at next meeting
    CPI adjustment: ±8% on acceleration/deceleration
    Only active 14 days before each 2026 FOMC date
    Current: DFF=3.64%, DGS2=3.90%, spread=+0.26% → hold-biased
    Next meeting: March 19 → active from March 5

## Research findings (Sessions 13-14)

Highest documented edge strategies:
1. ✅ Weather markets (HIGHNY) — jazzmine-p bot: +20% in 1 week
2. ✅ FOMC/Fed rate markets — Fed working paper Jan 2026: near-perfect day-before record
3. ✅ Orderbook imbalance — VPIN/PIN (Easley, Kiefer, O'Hara 1996)
4. ⬜ Market making (Avellaneda-Stoikov) — nikhilnd/kalshi-market-making: 20.3% in 1 day
5. ⬜ Unemployment rate (KXUNRATE) — rmmomin/kalshi-urate-pmf: PMF extraction technique

Priority after 7+ paper days: Compare all 8 strategy Brier scores → enable best for live.
