---
phase: quick
plan: 3
subsystem: strategies
tags: [unemployment, fred, bls, tdd, 9th-loop]
dependency_graph:
  requires: [src/data/fred.py, src/strategies/base.py, src/platforms/kalshi.py]
  provides: [src/strategies/unemployment_rate.py, FREDSnapshot.unrate_*, unemployment_loop]
  affects: [main.py, config.yaml, tests/test_unemployment_strategy.py]
tech_stack:
  added: [math.erfc-based norm.cdf (no scipy)]
  patterns: [TDD red-green, fomc_loop replication, dataclass field defaults for backward-compat]
key_files:
  created:
    - src/strategies/unemployment_rate.py
    - tests/test_unemployment_strategy.py
  modified:
    - src/data/fred.py
    - config.yaml
    - main.py
decisions:
  - "Use math.erfc for norm.cdf — scipy not installed in venv, avoids adding a dependency"
  - "Shared fred_feed between fomc_loop and unemployment_loop — single HTTP feed, no double fetching"
  - "UNRATE fetch failure is non-fatal — snapshot created with 0.0 defaults if unavailable"
  - "Backward-compat via dataclass field defaults (unrate_latest=0.0 etc.) — no existing caller changes needed"
metrics:
  duration: ~25 min
  completed: 2026-02-28
  tasks_completed: 2
  files_modified: 5
  tests_added: 46
  tests_total: 412
---

# Phase quick Plan 3: Unemployment Rate Strategy Summary

Unemployment rate strategy (9th trading loop) implemented via TDD. Exploits Kalshi KXUNRATE markets by comparing BLS Employment Situation linear-trend forecast (FRED UNRATE, last 3 readings + normal CDF probability) to market prices; active in 7-day window before each monthly BLS release.

## What Was Built

### Task 1: FREDSnapshot extension + UnemploymentRateStrategy (TDD)

**src/data/fred.py** — Extended FREDSnapshot with three backward-compatible UNRATE fields:
- `unrate_latest: float = 0.0`, `unrate_prior: float = 0.0`, `unrate_prior2: float = 0.0` (dataclass defaults — existing callers unchanged)
- `unrate_trend` property: `(latest - prior2) / 2` (linear slope per month)
- `unrate_forecast` property: `latest + trend` (one-step extrapolation)
- `FREDFeed.refresh()` now fetches UNRATE in the same cycle — if unavailable, uses 0.0 defaults (non-fatal)

**src/strategies/unemployment_rate.py** — New file:
- `BLS_RELEASE_DATES_2026`: all 12 BLS Employment Situation dates hardcoded
- `next_bls_date()`, `days_until_bls()`: window helpers
- `parse_unrate_ticker()`: regex `KXUNRATE-\d{6}-(\d+\.\d+)` → threshold float
- `_norm_cdf()`: standard normal CDF via `math.erfc` (no scipy dependency)
- `compute_unrate_model_prob(snap, threshold, uncertainty_band)`: `P(YES) = 1 - norm.cdf((threshold - forecast) / sigma)`
- `UnemploymentRateStrategy(BaseStrategy)`: 5-gate `generate_signal()` matching fomc_rate.py pattern
- `load_from_config()`: reads `strategy.unemployment` section, shares existing FREDFeed

**tests/test_unemployment_strategy.py** — 46 tests in 7 groups:
- Group A: FREDSnapshot backward compatibility (3 tests)
- Group B: UNRATE fields and computed properties (5 tests)
- Group C: BLS window helpers (9 tests)
- Group D: compute_unrate_model_prob accuracy (5 tests)
- Group E: generate_signal gates + signal generation (13 tests)
- Group F: parse_unrate_ticker (7 tests)
- Group G: load_from_config factory (2 tests)

**TDD commit:** `d38f20d`

### Task 2: Wire into main.py + config.yaml

**config.yaml** — Added `strategy.unemployment` section with series_ticker, days_before_release, min_edge_pct, min_minutes_remaining, uncertainty_band, fred_refresh_interval_seconds.

**main.py** — 6 changes:
1. Import `unemployment_strategy_load` from `src.strategies.unemployment_rate`
2. `UNEMPLOYMENT_POLL_INTERVAL_SEC = 1800` constant
3. `unemployment_strategy = unemployment_strategy_load()` after fomc_strategy
4. `unemployment_loop()` function (exact fomc_loop pattern) with stagger 58s, reads slippage_ticks from YAML inside loop body (avoids config scope bug)
5. `unemployment_task` asyncio task created at stagger 58s
6. `unemployment_task` added to signal handler, gather, and finally cleanup blocks

**Task 2 commit:** `15307cf`

## Test Results

| Metric | Value |
|--------|-------|
| Tests before | 366 |
| Tests added | 46 |
| Tests after | 412 |
| Regressions | 0 |
| FOMC tests still passing | yes |

## Deviations from Plan

None — plan executed exactly as written.

The one anticipated deviation (scipy not installed → use math.erfc) was pre-planned in the task spec. Implemented exactly as specified.

## Self-Check: PASSED

- FOUND: src/strategies/unemployment_rate.py
- FOUND: tests/test_unemployment_strategy.py
- FOUND: .planning/quick/3-unemployment-rate-strategy/3-SUMMARY.md
- FOUND: commit d38f20d (Task 1 - TDD implementation)
- FOUND: commit 15307cf (Task 2 - wire loop into main.py)
