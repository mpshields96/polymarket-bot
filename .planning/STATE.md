# Project State — polymarket-bot

## Current Status

**Phase:** 4.2 — Paper Data Collection
**Current Plan:** 1 of 1 (04.2-01 complete — awaiting Task 4 human checkpoint)
**Last activity:** 2026-02-28 — 04.2-01 tasks 1-3 complete: slippage, graduation reporter, settlement verification

## Key Context

- 8 paper-trading strategies: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather, fomc
- 346/346 tests passing, verify.py 18/26 (8 graduation WARNs advisory — non-critical)
- All loops run in paper mode (LIVE_TRADING=false)
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

- Graduation check is WARN not FAIL — advisory, never blocks bot startup
- fomc_rate min_trades=5 (not 30) — strategy fires ~8x/year, 30 trades would take 3+ years
- weather_forecast min_days=14 (not 7) — captures seasonal/weekly weather variation
- first_trade_ts includes unsettled trades so days_running is accurate from first bot activity
- slippage_ticks read by caller (main.py) from config, not inside paper.py — keeps paper.py config-free
- execute() uses keyword-arg signature (ticker, side, price_cents, size_usd, reason) — unified across all call sites
- result normalization in kalshi.py _parse_market() via .lower() — makes settlement robust to API casing changes
- print_graduation_status imports _GRAD from setup/verify.py as single source of truth

## Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Define formal live graduation criteria | 2026-02-28 | d6b9e21 | .planning/quick/1-define-formal-live-graduation-criteria-f/ |

## Phase Plans Completed

| Phase | Plan | Description | Commits |
|-------|------|-------------|---------|
| 04.2 | 01 | Paper data collection infra (slippage, graduation reporter, settlement verification) | f8bfafc, 6013c11, c03e382 |

## Last Session

**Stopped at:** Completed 04.2-01 tasks 1-3, awaiting Task 4 checkpoint (human-verify)
**Session timestamp:** 2026-02-28T08:25:00Z
