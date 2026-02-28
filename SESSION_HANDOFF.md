# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 16 — btc_drift late-entry penalty, 296 tests)
═══════════════════════════════════════════════════

## Current State

8 strategies running in parallel in paper mode.
8 async trading loops + 1 settlement loop, staggered to spread Kalshi API calls.
296/296 tests passing.

Loop stagger (seconds):
   0s → [trading]        btc_lag_v1                 — crypto momentum
   7s → [eth_trading]    eth_lag_v1                 — ETH momentum, paper
  15s → [drift]          btc_drift_v1               — BTC drift from open, paper
  22s → [eth_drift]      eth_drift_v1               — ETH drift, paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — VPIN-lite depth ratio, paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — ETH orderbook, paper
  43s → [weather]        weather_forecast_v1        — HIGHNY vs ensemble forecast, paper, 5-min poll
  51s → [fomc]           fomc_rate_v1               — KXFEDDECISION vs yield curve, paper, 30-min poll

verify.py: **18/18 ✅**
Tests: **296/296 ✅** (was 289, +7 new late-entry penalty tests)

## What was done this session (Session 16)

btc_drift architecture fix #1:
- `_reference_prices` now stores `(price, minutes_late)` tuple instead of plain float
- `minutes_late` = minutes elapsed since market open when bot first observed the market
- Late-entry confidence penalty: `max(0.5, 1.0 - max(0, minutes_late - 2) / 16)`
  → No penalty within first 2 min of observation (grace period)
  → Penalty grows linearly to 0.5× at 10+ min late
- `_minutes_since_open()` static helper added to BTCDriftStrategy
- Reason string shows "[ref +X.Xmin late]" when late > 2 min (visible in paper logs)
- 4 test failures fixed (tuple indexing + test helper refactored for clean isolation)

Global workflow automation:
- Installed GSD v1.22.0 globally: npx get-shit-done-cc@latest --global --claude
- Created ~/.claude/rules/gsd-framework.md — MANDATORY trigger table
- Created ~/.claude/rules/mandatory-skills-workflow.md — superpowers skill requirements
- Both files auto-load into EVERY Claude Code session on this machine

Commits: a9f3b25 (btc_drift fix, 296 tests), c4f8c9a/b72c333/c61f3e3 (Session 15)

## What was done last session (Session 15)

Research phase:
- btc_lag 30-day backtest: 84.1% accuracy, 44 signals/30 days
  → scripts/backtest.py now supports --strategy lag|drift|both
  → ⚠ Jane Street / Susquehanna / Jump compete in BTC/ETH markets (0.17pp spread)
  → Entertainment/sports markets have 4.79-7.32pp spread — better long-term target
- btc_drift sensitivity calibrated: 300→800 (Brier 0.2330→0.2178 STRONG)
  → Updated config.yaml: btc_drift.sensitivity = 800, eth_drift.sensitivity = 800

Protections added:
- User-Agent header in Kalshi REST client (transparent bot identification)
- Position deduplication: has_open_position() in db.py — all 8 loops check before placing
- Daily bet cap: count_trades_today() in db.py — max_daily_bets_per_strategy: 5 in config
  → btc_drift fires on 96% of 15-min windows; cap prevents ~90+ bets/day tax churn

Weather ensemble upgrade:
- NWSFeed: NOAA api.weather.gov (free, US-only, 2-step point→forecast, User-Agent required)
- EnsembleWeatherFeed: blends Open-Meteo + NWS with adaptive uncertainty
  → |diff| < 1°F → std_dev = 2.5°F (high confidence)
  → |diff| > 4°F → std_dev = 5.0°F (low confidence)
  → One source fails → other used with +0.5°F penalty
- load_nyc_weather_from_config() now returns EnsembleWeatherFeed (drop-in replacement)

Tests: 32 new tests for NWSFeed, EnsembleWeatherFeed, count_trades_today, has_open_position
Fixed: db.py uses timezone-aware datetime.now(UTC) instead of deprecated utcnow()

Commit: c61f3e3 (pushed to main)

## Next Action (FIRST THING)

Run the bot and watch 8 loops start:

    python main.py
    # or: push commits first
    git push

Expected startup sequence (first 51s):
  [trading]       t=0s  → BTC lag evaluating
  [eth_trading]   t=7s  → ETH lag evaluating
  [drift]         t=15s → BTC drift evaluating
  [eth_drift]     t=22s → ETH drift evaluating
  [btc_imbalance] t=29s → BTC orderbook evaluating
  [eth_imbalance] t=36s → ETH orderbook evaluating
  [weather]       t=43s → "No open HIGHNY markets" (weekend) or fetches ensemble forecast
  [fomc]          t=51s → "No open KXFEDDECISION markets" OR evaluates with FRED data

FOMC strategy fires 14 days before each meeting:
  → Next meeting: March 19, 2026 → strategy active from March 5
  → Current date: Feb 28, 2026 → FOMC loop will log "timing gate" debug messages

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | api.elections.kalshi.com                       |
| Kalshi REST client           | ✅ Working  | User-Agent header added                        |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| BTCLagStrategy               | ✅ Running  | btc_lag_v1, 0s stagger, 84.1% backtest         |
| BTCDriftStrategy             | ✅ Running  | btc_drift_v1, paper, sensitivity=800           |
| ETH lag strategy             | ✅ Running  | eth_lag_v1, paper, 7s stagger                  |
| ETH drift strategy           | ✅ Running  | eth_drift_v1, paper, sensitivity=800           |
| Orderbook imbalance (BTC)    | ✅ Running  | paper, 29s stagger                             |
| Orderbook imbalance (ETH)    | ✅ Running  | paper, 36s stagger                             |
| WeatherForecastStrategy      | ✅ Running  | ENSEMBLE (Open-Meteo + NWS), adaptive std_dev  |
| FOMCRateStrategy             | ✅ Running  | fomc_rate_v1, paper, 30-min poll, 51s stagger  |
| FREDFeed                     | ✅ Working  | DFF/DGS2/CPI from FRED CSV, hourly cache       |
| Position deduplication       | ✅ NEW      | db.has_open_position() on all 8 loops          |
| Daily bet cap                | ✅ NEW      | 5 bets/strategy/day, db.count_trades_today()   |
| Kill switch                  | ✅ Working  | Shared by all 8 loops                          |
| Database                     | ✅ Working  | data/polybot.db                                |
| Dashboard                    | ✅ Working  | localhost:8501                                 |
| Settlement loop              | ✅ Ready    | Runs, wired to kill switch                     |

## Key Commands

    python main.py                    → Paper mode (8 strategies + settlement)
    python main.py --verify           → Pre-flight check (18/18)
    streamlit run src/dashboard.py   → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 289 tests
    echo "RESET" | python main.py --reset-killswitch
    python scripts/backtest.py --days 30              → 30-day BTC drift calibration
    python scripts/backtest.py --strategy lag         → btc_lag 30-day simulation
    python scripts/backtest.py --strategy both        → both strategies

## Signal calibration

  btc_lag / eth_lag:
    min_edge_pct: 0.08 — needs ~0.65% BTC move in 60s
    30-day backtest: 84.1% accuracy, 44 signals/30 days
    ⚠ HFTs compete (Jane St / Susquehanna / Jump) — monitor fill quality vs paper

  btc_drift / eth_drift:
    min_drift_pct: 0.05, min_edge_pct: 0.05, sensitivity: 800
    30-day backtest: 69.1% accuracy, Brier=0.2178 (STRONG)
    Capped: 5 bets/day (fires on 96% of windows otherwise = tax nightmare)

  orderbook_imbalance (BTC + ETH):
    min_imbalance_ratio: 0.65 — VPIN-lite smart money signal

  weather_forecast (NYC HIGHNY) — ENSEMBLE:
    EnsembleWeatherFeed: Open-Meteo GFS + NOAA NWS/NDFD weighted blend
    Adaptive std_dev: 2.5°F (sources agree) / 3.5°F (normal) / 5.0°F (sources diverge)
    min_edge_pct: 0.05, min_minutes_remaining: 30

  fomc_rate (KXFEDDECISION):
    Yield curve: DGS2 - DFF spread → P(hold/cut/hike) at next meeting
    CPI adjustment: ±8% on acceleration/deceleration
    Only active 14 days before each 2026 FOMC date
    Next meeting: March 19 → active from March 5

## Architecture issues to address next

  1. ✅ btc_drift reference price: FIXED — late-entry penalty applied (Session 16, a9f3b25)
  2. Paper executor: fills at limit price, no slippage model (optimistic P&L)
  3. Live graduation criteria: not yet formally defined (need N days, Brier threshold, etc.)
  4. Settlement proxy: verify result from Kalshi API response field directly

## Research findings (Sessions 13-15)

Highest documented edge strategies:
1. ✅ Weather ensemble (HIGHNY) — jazzmine-p bot: +20% in 1 week, now using 2 sources
2. ✅ FOMC/Fed rate markets — Fed working paper Jan 2026: near-perfect day-before record
3. ✅ Orderbook imbalance — VPIN/PIN (Easley, Kiefer, O'Hara 1996)
4. ⬜ Entertainment/sports markets — 4.79-7.32pp spread vs crypto 0.17pp, less HFT competition
5. ⬜ Market making (Avellaneda-Stoikov) — nikhilnd/kalshi-market-making: 20.3% in 1 day
6. ⬜ Unemployment rate (KXUNRATE) — rmmomin/kalshi-urate-pmf: PMF extraction technique

Priority after 7+ paper days: Compare all 8 strategy Brier scores → enable best for live.
