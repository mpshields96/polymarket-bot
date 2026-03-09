---
phase: quick-7
plan: 01
subsystem: execution
tags: [live-trading, order-status, data-integrity, tdd]
dependency_graph:
  requires: []
  provides: [canceled-order-guard]
  affects: [src/execution/live.py, calibration-data, graduation-stats]
tech_stack:
  added: []
  patterns: [canceled-status-guard-after-create-order]
key_files:
  created: []
  modified:
    - src/execution/live.py
    - tests/test_live_executor.py
decisions:
  - Guard fires AFTER create_order() — Kalshi placement is already attempted; we only block the DB write
  - All non-canceled statuses (executed, resting, pending) fall through to db.save_trade normally
  - Warning log emitted on canceled to aid ops visibility without triggering kill switch
metrics:
  duration: "~10 minutes"
  completed: "2026-03-09"
  tasks_completed: 2
  files_modified: 2
  tests_added: 2
---

# Quick-7: Fix Canceled Order Status Check in live.py — Summary

**One-liner:** Canceled-order guard inserted between `create_order()` and `db.save_trade()` in `live.py` — prevents phantom live trades from corrupting calibration data and graduation stats.

## What Was Done

After `kalshi.create_order()` returns, Kalshi can set `order.status = "canceled"` when no counterparty is available, the market is closing, or a risk limit is hit. Previously `execute()` would call `db.save_trade()` regardless of status, recording a canceled order as a real live bet. This poisoned:

- Brier score computation (calibration data)
- The live trade counter used for Stage 2 graduation gating
- The consecutive-loss counter in the kill switch (could fire a 2hr soft stop on a bet that never filled)

The fix inserts a guard block immediately after the `logger.info("[LIVE] Order placed: ...")` line and before `db.save_trade()`. If `order.status == "canceled"`, a warning is logged and `execute()` returns `None` without writing to DB.

## Implementation

**Guard block in `src/execution/live.py` (lines 175-183):**

```python
# ── Canceled order guard ──────────────────────────────────────────────
# Kalshi cancels orders that cannot be matched (no liquidity, market closing,
# risk limit). A canceled order must NOT be recorded as a live bet — doing so
# corrupts calibration data, inflates trade counters, and poisons Brier scores.
if order.status == "canceled":
    logger.warning(
        "[live] Order canceled by Kalshi — NOT recording as trade: "
        "server_id=%s ticker=%s",
        order.order_id, signal.ticker,
    )
    return None
```

## Tests Added (`tests/test_live_executor.py` — `TestExecuteOrderStatusGuard`)

1. `test_canceled_order_not_recorded_in_db` — `create_order()` returns status="canceled" → result is None, `db.save_trade` not called, `kalshi.create_order` was called once
2. `test_resting_order_recorded_normally` — `create_order()` returns status="resting" → result is not None, `result["status"] == "resting"`, `db.save_trade` called once

## Commits

| Hash | Message |
|------|---------|
| 6127cea | test(quick-7): add failing tests for canceled/resting order status guard |
| 9009fa8 | fix(live): guard against recording canceled orders as live bets |

## Test Results

- Before: 869/869 (prior baseline) + 13 execution-time price guard tests = existing suite
- After: **882/882 tests pass** (2 new tests added, zero regressions)

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- [x] `order.status == "canceled"` appears exactly once in `src/execution/live.py` (line 175)
- [x] `db.save_trade` appears AFTER the guard (line 184)
- [x] Both commits exist: 6127cea, 9009fa8
- [x] 882/882 tests pass
