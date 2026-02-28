# Project State — polymarket-bot

## Current Status

**Phase:** 4.1 — Live Graduation Criteria
**Last activity:** 2026-02-28 — Quick task 1 complete: graduation criteria wired

## Key Context

- 8 paper-trading strategies: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather, fomc
- 324/324 tests passing, verify.py 18/26 (8 graduation WARNs advisory — non-critical)
- All loops run in paper mode (LIVE_TRADING=false)
- Hard safety limits: $5 max bet, $20 bankroll floor, 30% stop-loss
- Graduation criteria now checkable via `python setup/verify.py` (section [11])

## Blockers/Concerns

None currently.

## Key Decisions

- Graduation check is WARN not FAIL — advisory, never blocks bot startup
- fomc_rate min_trades=5 (not 30) — strategy fires ~8x/year, 30 trades would take 3+ years
- weather_forecast min_days=14 (not 7) — captures seasonal/weekly weather variation
- first_trade_ts includes unsettled trades so days_running is accurate from first bot activity

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Define formal live graduation criteria | 2026-02-28 | d6b9e21 | .planning/quick/1-define-formal-live-graduation-criteria-f/ |
