---
phase: quick-11
plan: 01
subsystem: execution-guards, risk-hooks
tags: [iron-laws, tdd, sniper, price-guard, danger-zone]
dependency_graph:
  requires: [src/execution/live.py, main.py, .claude/hooks/danger_zone_guard.sh]
  provides: [LAW-3 regression test, LAW-5 credential check, LAW-2 cap check]
  affects: [expiry_sniper_loop, danger_zone_guard]
tech_stack:
  added: []
  patterns: [TDD red-green, advisory shell hook, Iron Laws enforcement via tests]
key_files:
  created: []
  modified:
    - tests/test_live_executor.py
    - .claude/hooks/danger_zone_guard.sh
decisions:
  - "price_guard_min=1 kept intentionally — NO-side sniper bets have YES-equiv 5-9c (NO@91-95c), which would be blocked by min=87. Correct LAW 3 enforcement is the _MAX_SLIPPAGE_CENTS=3 pre-execution guard already present in main.py from S81."
  - "DANGER_ZONE_FILES extended to 6 files: added kalshi_auth.py, kalshi.py, main.py"
metrics:
  duration: "~12 minutes"
  completed: "2026-03-15T22:43:00Z"
  tasks_completed: 2
  files_modified: 2
---

# Phase quick-11 Plan 01: Iron Laws Pattern 1 — Sniper Price Guard Summary

One-liner: LAW-3 regression test via _MAX_SLIPPAGE_CENTS check + danger_zone_guard extended to 6 files with Iron Laws advisory output.

## What Was Built

### Task 1: TDD fix for LAW-3 price guard enforcement

The plan called for changing `price_guard_min=1` to `price_guard_min=87` in
`main.py expiry_sniper_loop`. During TDD RED phase, a concurrent session's commit
(`9cd3925 — Iron Laws IL-12 to IL-18`) revealed an architectural error in the plan:

- `price_guard_min` is checked against `execution_yes_price` (YES-equivalent)
- For NO-side sniper bets (e.g. NO@91c), YES-equiv = 9c, which is below 87
- Setting `min=87` would block all NO-side sniper bets

The correct LAW 3 enforcement is `_MAX_SLIPPAGE_CENTS = 3` in `main.py` (line 1555),
added in S81 (commit `9cf45b1`). This checks `_live_price < signal.price_cents - 3`
BEFORE orderbook fetch, catching the real failure mode (trade 2786: signal 90c, fill 86c).

Tests added to `TestExpirySnipPriceGuardLaw3`:
- `test_expiry_sniper_slippage_guard_present_in_main` — asserts `_MAX_SLIPPAGE_CENTS`
  and `signal.price_cents - _MAX_SLIPPAGE_CENTS` exist in main.py
- `test_execute_rejects_86c_when_guard_is_87` — verifies execute() guard logic works
  when a caller explicitly passes `price_guard_min=87`

### Task 2: danger_zone_guard.sh extensions

Extended `.claude/hooks/danger_zone_guard.sh`:

DANGER_ZONE_FILES expanded from 3 to 6 files:
- Added: `src/auth/kalshi_auth.py`, `src/platforms/kalshi.py`, `main.py`

Added `check_iron_laws()` function (advisory only, never blocks):
- LAW 3: checks `_MAX_SLIPPAGE_CENTS` present in main.py
- LAW 5: greps src/ and main.py for hardcoded credentials (RSA key, KALSHI_API_KEY_ID, sk-ant-)
- LAW 2: checks `HARD_MAX_TRADE_USD=20.00` in kill_switch.py

Function called after tests pass, before final `exit 0`. Warnings go to stderr.
Script exit codes unchanged (0 = allow, 2 = block on test failure).

## Commits

| Commit | Message | Task |
|--------|---------|------|
| ae3fb9c | test(quick-11): add LAW-3 failing test for expiry_sniper price_guard_min=87 | Task 1 RED |
| 9cd3925 | feat: Iron Laws IL-12 to IL-18 — concurrent session, updated LAW-3 test | Task 1 GREEN (concurrent) |
| 10b0a16 | feat(quick-11): extend danger_zone_guard with Iron Laws advisory checks | Task 2 |

## Deviations from Plan

### Auto-corrected: Architectural error in price_guard_min=87 approach

**Found during:** Task 1 TDD RED phase

**Issue:** The plan instructed changing `price_guard_min=1` to `price_guard_min=87`
in `expiry_sniper_loop`. This would break NO-side sniper bets: NO@91c has
YES-equivalent = 9c, which is below the 87c floor. The guard in `live.py` uses
YES-equivalent space for all comparisons.

**Fix:** Kept `price_guard_min=1` (intentional for NO-side bets). Updated tests to
verify the CORRECT enforcement mechanism: `_MAX_SLIPPAGE_CENTS = 3` pre-execution
guard in main.py (S81, commit `9cf45b1`).

**Rule applied:** Rule 1 (auto-fix architectural error in test premise).

**Files modified:** `tests/test_live_executor.py`

## Verification

- 1312 tests pass, 3 skipped (up from 1292 baseline: +18 from concurrent session IL-12 to IL-18, +2 from this task)
- `danger_zone_guard.sh` runs full suite + Iron Laws advisory on 6 danger zone files
- Iron Laws checks: all pass on current codebase
- Script exits 0 after tests pass (advisory only, never blocks)

## Self-Check: PASSED

Files modified exist and have expected content:
- tests/test_live_executor.py: contains `TestExpirySnipPriceGuardLaw3` class
- .claude/hooks/danger_zone_guard.sh: contains `check_iron_laws`, 6 DANGER_ZONE_FILES
- main.py: `price_guard_min=1` (correct, unchanged)
- Commits ae3fb9c, 10b0a16 confirmed in git log
