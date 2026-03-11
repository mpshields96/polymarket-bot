# Project State — polymarket-bot

## Current Status

**Phase:** 4.2 — Paper Data Collection
**Current Plan:** 1 of 1 (04.2-01 complete — awaiting Task 4 human checkpoint)
**Last activity:** 2026-03-11 — Session 48: sol_drift_v1 Stage 1 promotion (PID 47874), KALSHI_MARKETS.md probe update (quick task #9/GSD#10), Reddit research findings logged to todos.md

## Key Context

- 9 paper-trading strategies: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
- 412/412 tests passing, verify.py 18/26 (8 graduation WARNs advisory — non-critical)
- btc_lag_v1 is LIVE (LIVE_TRADING=true in .env, $75 bankroll, $5 max/bet)
- 7 other strategies in paper mode collecting calibration data
- Hard safety limits: $5 max bet, $20 bankroll floor, 30% stop-loss
- Graduation criteria checkable via `python main.py --graduation-status` (new) or `python setup/verify.py` (section [11])
- PaperExecutor: slippage_ticks=1 default — realistic 1-tick adverse fills
- Settlement: result field normalized .lower() in kalshi.py _parse_market()

## Blockers/Concerns

None currently.

## Accumulated Context

### Pending Todos

None — slippage model and settlement verification complete.

## Key Decisions

- POST /v1/orders on polymarket.us uses protobuf body format (not JSON) — confirmed by probe responses with explicit "proto: syntax error" messages. polymarket.COM path (py-clob-client) remains unblocked.
- Kalshi API status=settled (not 'finalized') for settled markets — confirmed correct filter
- Candlestick end_period_ts in seconds (not ms), yes_bid.close/yes_ask.close in cents
- At 0.40% BTC move threshold: YES avg 49.5c (50c assumption largely valid), accuracy 66.7%, edge 13.5%
- Graduation check is WARN not FAIL — advisory, never blocks bot startup
- fomc_rate min_trades=5 (not 30) — strategy fires ~8x/year, 30 trades would take 3+ years
- weather_forecast min_days=0 (removed) — 30 trades is the only gate, same as all strategies
- first_trade_ts includes unsettled trades so days_running is accurate from first bot activity
- slippage_ticks read by caller (main.py) from config, not inside paper.py — keeps paper.py config-free
- execute() uses keyword-arg signature (ticker, side, price_cents, size_usd, reason) — unified across all call sites
- result normalization in kalshi.py _parse_market() via .lower() — makes settlement robust to API casing changes
- print_graduation_status imports _GRAD from setup/verify.py as single source of truth
- min_days=0 for all strategies — 30 trades is the only volume gate
- --status bypasses bot lock — safe to run while bot is live (read-only DB + 2 REST calls)
- get_binance_mid_price() returns None on network error — never raises
- unemployment_rate uses math.erfc for norm.cdf — no scipy dependency, avoids adding a package
- shared fred_feed between fomc_loop and unemployment_loop — single HTTP feed, no double fetching

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Define formal live graduation criteria | 2026-02-28 | d6b9e21 | .planning/quick/1-define-formal-live-graduation-criteria-f/ |
| 2 | Commit graduation threshold + build --status command | 2026-02-28 | e999d6c, 74f5dbb, ab72b61 | .planning/quick/2-commit-graduation-threshold-change-and-b/ |
| 3 | Unemployment rate strategy (9th loop, KXUNRATE, BLS window, FRED UNRATE, TDD) | 2026-02-28 | d38f20d, 15307cf | .planning/quick/3-unemployment-rate-strategy/ |
| 4 | Build real Kalshi-calibrated backtest using Kalshi candlestick API | 2026-03-01 | ecce5be | .planning/quick/4-build-real-kalshi-calibrated-backtest-fr/ |
| 5 | Probe POST /v1/orders format on polymarket.us — found protobuf (not JSON) | 2026-03-08 | f3a3fef, b0added | .planning/quick/5-probe-post-v1-orders-format-on-polymarke/ |
| 6 | CryptoDailyStrategy + loops (KXBTCD/KXETHD/KXSOLD, 24 hourly slots, 30 tests) | 2026-03-08 | b815af8, fc03851 | src/strategies/crypto_daily.py |
| 7 | Add execution-time price guard to live.py (35-65c + 10c max slippage) | 2026-03-10 | 0ca6b5e, 3c8baa9 | .planning/quick/6-add-execution-time-price-guard-to-live-p/ |
| 8 | Fix canceled order status check in live.py (canceled → no DB write, resting → record normally) | 2026-03-09 | 6127cea, 9009fa8 | .planning/quick/7-fix-canceled-order-status-check-in-live-/ |
| 9 | Fix graduation_stats() is_paper param + sol_drift_v1 in _GRAD — live drift shows live bet counts | 2026-03-09 | 82c90c7, 2fab9e6 | .planning/quick/8-fix-graduation-stats-is-paper-param-to-s/ |
| 10 | Session 48 Kalshi probe: KXBTCMAXW dormant confirmed weekday, KXCPI 74 open (major revision), fresh KXBTCMAXMON/KXBTCMINMON/KXBTCMAXY/KXBTCMINY data | 2026-03-11 | 9171436 | .planning/quick/9-research-and-document-kalshi-undocumente/ |
| 11 | Improve CryptoDailyStrategy signal quality: per-asset _HOURLY_VOL (BTC=0.01, ETH=0.015, SOL=0.025), 5pm EDT ATM slot priority, direction_filter in crypto_daily_loop | 2026-03-11 | e71c498, 7a09d74 | .planning/quick/10-improve-cryptodailystrategy-signal-quali/ |

## Phase Plans Completed

| Phase | Plan | Description | Commits |
|-------|------|-------------|---------|
| 04.2 | 01 | Paper data collection infra (slippage, graduation reporter, settlement verification) | f8bfafc, 6013c11, c03e382 |

## Last Session

**Stopped at:** Quick task 11 — CryptoDailyStrategy signal quality improvements: per-asset vol, 5pm EDT slot priority, loop direction_filter guard. 1003/1003 tests.
**Session timestamp:** 2026-03-11T16:41:00Z
