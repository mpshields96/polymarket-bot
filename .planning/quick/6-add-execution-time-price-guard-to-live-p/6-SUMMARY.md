---
phase: quick-6
plan: 6
subsystem: execution
tags: [live-trading, price-guard, slippage, tdd, regression]
dependency_graph:
  requires: [src/execution/live.py, src/strategies/base.Signal]
  provides: [execution-time price guard in live.py]
  affects: [btc_drift_v1, eth_drift_v1, sol_drift_v1 live loops]
tech_stack:
  added: []
  patterns: [guard-constants, YES-equivalent-conversion, TDD-red-green]
key_files:
  created: [tests/test_live_executor.py (TestExecutionPriceGuard class added)]
  modified: [src/execution/live.py]
decisions:
  - Guard fires AFTER _determine_limit_price() and BEFORE count calculation — correct placement
  - Slippage computed in YES-equivalent space for both sides (not raw NO price comparison)
  - Boundary is inclusive: 65c exactly with 10c slippage is allowed (<=, not <)
  - Constants prefixed with _EXECUTION_ to distinguish from signal-generation constants
metrics:
  duration: ~10 minutes
  completed: 2026-03-10
  tasks_completed: 2
  files_changed: 2
  tests_added: 6
  tests_total: 875
---

# Phase quick-6 Plan 6: Execution-Time Price Guard Summary

**One-liner:** Execution-time 35-65c range guard + 10c max slippage check in live.py using YES-equivalent conversion, preventing HFT-repriced fills (observed 84c fill session 37).

## What Was Built

Two constants plus ~20 lines of guard logic added to `src/execution/live.py` `execute()` function. The guard fires after `_determine_limit_price()` determines the live orderbook price and before the contract count calculation. It rejects orders in two cases:

1. **Range guard**: execution price (converted to YES-equivalent) is outside 35-65c
2. **Slippage guard**: absolute difference between execution YES-equiv price and signal YES-equiv price exceeds 10c

Both rejection paths return `None` with a `logger.warning()` — no order placed, no DB write.

## Problem Solved

btc_drift's 35-65c price guard fires at signal-generation time only. In the 0.1-1s asyncio gap between signal generation and order placement, HFTs can reprice the market significantly. Session 37 (2026-03-10 08:39 CDT) observed a live fill at 84c — far outside the model's calibrated range, corrupting the Brier score.

## Implementation Details

**Constants added** (module-level, after `_FIRST_RUN_CONFIRMED`):
```python
_EXECUTION_MIN_PRICE_CENTS: int = 35
_EXECUTION_MAX_PRICE_CENTS: int = 65
_EXECUTION_MAX_SLIPPAGE_CENTS: int = 10
```

**Guard block** (after 1-99 range check, before count calculation):
```python
execution_yes_price = price_cents if signal.side == "yes" else (100 - price_cents)
signal_yes_price = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)

if not (_EXECUTION_MIN_PRICE_CENTS <= execution_yes_price <= _EXECUTION_MAX_PRICE_CENTS):
    logger.warning("[live] Execution price %dc (YES-equiv) outside guard %d-%dc ...", ...)
    return None

slippage_cents = abs(execution_yes_price - signal_yes_price)
if slippage_cents > _EXECUTION_MAX_SLIPPAGE_CENTS:
    logger.warning("[live] Slippage %dc exceeds max %dc ...", ...)
    return None
```

## Tests (6 new in TestExecutionPriceGuard)

| Test | Signal | Execution | Result |
|------|--------|-----------|--------|
| test_rejects_execution_price_above_guard | YES@55c | YES@80c | None (range) |
| test_rejects_execution_price_below_guard | YES@55c | YES@20c | None (range) |
| test_rejects_excessive_slippage | YES@50c | YES@62c (12c slip) | None (slippage) |
| test_allows_execution_at_guard_boundary | YES@55c | YES@65c (10c slip = at limit) | proceeds |
| test_no_side_slippage_uses_yes_equivalent | NO@45c (YES-eq=55c) | NO@32c (YES-eq=68c) | None (range+slip) |
| test_valid_price_executes_normally | YES@55c | YES@59c (4c slip) | proceeds |

## Deviations from Plan

None — plan executed exactly as written.

The `test_rejects_excessive_slippage` test was adjusted slightly from the plan spec (signal@55c, exec@67c → 67 > 65 so range guard fires first). To test the slippage guard independently, used signal@50c, exec@62c (12c slippage, 62 is inside 35-65 range). This is more correct as it isolates the slippage code path.

## Self-Check

Files exist:
- src/execution/live.py — FOUND (modified)
- tests/test_live_executor.py — FOUND (modified, TestExecutionPriceGuard added)

Commits:
- 0ca6b5e — test(quick-6): failing tests (RED)
- 3c8baa9 — fix(quick-6): guard implementation (GREEN)

Test count: 875/875 passing (869 prior + 6 new)

## Self-Check: PASSED
