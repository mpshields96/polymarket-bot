# Project State — polymarket-bot

## Current Status

**Phase:** 4.2 — Paper Data Collection
**Current Plan:** 1 of 1 (04.2-01 complete — awaiting Task 4 human checkpoint)
**Last activity:** 2026-02-28 — 04.2-01 tasks 1-3 complete: slippage, graduation reporter, settlement verification

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

## Phase Plans Completed

| Phase | Plan | Description | Commits |
|-------|------|-------------|---------|
| 04.2 | 01 | Paper data collection infra (slippage, graduation reporter, settlement verification) | f8bfafc, 6013c11, c03e382 |

## Last Session

**Stopped at:** Completed quick task 4 — kalshi_real_backtest.py built and run. Key result: at 0.40% threshold, YES price avg 49.5c (50c assumption valid), accuracy 66.7%, edge 13.5% (vs 14.9% assumed, -1.5pp delta). 603/603 tests pass.
**Session timestamp:** 2026-03-01T20:10:00Z
