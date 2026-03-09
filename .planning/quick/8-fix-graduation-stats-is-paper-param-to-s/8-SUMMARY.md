---
phase: quick-8
plan: "01"
subsystem: db / graduation-tracking
tags: [bugfix, tdd, graduation, live-trading]
dependency_graph:
  requires: []
  provides: [graduation_stats is_paper param, live bet counts in --graduation-status]
  affects: [src/db.py, main.py, setup/verify.py]
tech_stack:
  added: []
  patterns: [is_paper filter param on DB query method, _LIVE_STRATEGIES set for caller dispatch]
key_files:
  created: []
  modified:
    - src/db.py
    - tests/test_db_graduation.py
    - main.py
    - setup/verify.py
    - tests/test_graduation_reporter.py
decisions:
  - graduation_stats() defaults to is_paper=True to preserve existing behavior for paper-only strategies
  - ip_filter built as f-string fragment (not bound param) because is_paper is a controlled boolean int conversion, not user input
  - _LIVE_STRATEGIES defined as a module-level set in verify.py — single source of truth, imported by main.py
  - sol_drift_v1 added to _GRAD (was live since Session 36 but missing from graduation tracking)
  - test_graduation_reporter.py count updated from 8→9 to reflect sol_drift_v1 addition
metrics:
  duration: "~10 minutes"
  completed: "2026-03-09"
  tasks_completed: 2
  files_changed: 5
---

# Quick Task 8: Fix graduation_stats() is_paper param — live strategies now show live bet counts

**One-liner:** Added `is_paper` param to `graduation_stats()` + `_LIVE_STRATEGIES` set in verify.py so `--graduation-status` shows real live bet counts (37/30, 19/30, 11/30) instead of 0/30 for btc/eth/sol drift.

## What Was Done

`graduation_stats()` was hardcoded to `is_paper = 1`, causing live strategies to always show
`0/30` in `--graduation-status` regardless of how many live bets had been placed. With 7+ live
bets already in the DB, graduation tracking was completely broken for the three live drift loops.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | TDD: add failing tests + implement graduation_stats() is_paper param | 82c90c7 | tests/test_db_graduation.py, src/db.py |
| 2 | Update callers in main.py and setup/verify.py | 2fab9e6 | main.py, setup/verify.py, tests/test_graduation_reporter.py |

## Changes Made

### src/db.py
- `graduation_stats(strategy, is_paper=True)` — new optional `is_paper: Optional[bool]` param
- Both SQL queries (settled trades + first_trade_ts) now filter by `is_paper` when not `None`
- Docstring updated to document all three modes (True/False/None)

### tests/test_db_graduation.py
- Added `TestGraduationStatsIsLiveParam` with 5 regression tests:
  - `test_live_param_counts_only_live_trades` — is_paper=False ignores paper rows
  - `test_live_param_returns_correct_win_rate` — live win rate isolated from paper
  - `test_default_is_paper_true_unchanged` — default behavior preserved
  - `test_is_paper_false_empty_returns_zero` — empty live DB returns 0
  - `test_first_trade_ts_from_live_trades_only` — first_trade_ts also filtered

### setup/verify.py
- `sol_drift_v1` added to `_GRAD` (was live since Session 36 but missing)
- `_LIVE_STRATEGIES = {"btc_drift_v1", "eth_drift_v1", "sol_drift_v1"}` defined as module-level set
- `check_graduation_status()` now passes `is_paper=False` for live strategies

### main.py
- `print_graduation_status()` imports `_LIVE_STRATEGIES` from verify.py
- Passes `is_paper=False` for live strategies, `is_paper=True` for paper-only strategies
- Docstring updated: "all 8 strategies" → "all tracked strategies"

### tests/test_graduation_reporter.py
- Updated `test_zero_of_8_ready_on_empty_db` → `test_zero_of_9_ready_on_empty_db` (count 8→9)

## Verification

```
$ python main.py --graduation-status

================================================================
  GRADUATION STATUS — 2026-03-09 22:43 UTC
================================================================
  Strategy                           Trades   Days  Brier  Streak      P&L  Status
  btc_lag_v1                          45/30   38.9  0.191       0   $15.06  READY FOR LIVE
  btc_drift_v1                        37/30    9.0  0.247       0  $-13.81  READY FOR LIVE  ← was 0/30
  eth_drift_v1                        19/30    0.8  0.247       0    $1.24  needs 11 more   ← was 0/30
  sol_drift_v1                        11/30    0.8  0.156       0    $1.66  needs 19 more   ← new row
================================================================
  3 / 9 strategies ready for live trading.
```

## Test Results

- 887/887 tests pass (up from 869 pre-quick-8, +18 via prior quick tasks + 5 new in this task)
- 33/33 test_db_graduation.py tests pass (28 existing + 5 new)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_zero_of_8_ready_on_empty_db in test_graduation_reporter.py**
- **Found during:** Task 2 full test run
- **Issue:** Test asserted "0 / 8" but _GRAD now has 9 strategies (sol_drift_v1 added)
- **Fix:** Updated test name and assertion to "0 / 9"
- **Files modified:** tests/test_graduation_reporter.py
- **Commit:** 2fab9e6

## Self-Check

- [x] src/db.py modified — graduation_stats() has is_paper param
- [x] tests/test_db_graduation.py — TestGraduationStatsIsLiveParam with 5 tests
- [x] setup/verify.py — _LIVE_STRATEGIES set + sol_drift_v1 in _GRAD
- [x] main.py — imports _LIVE_STRATEGIES, passes is_paper per strategy
- [x] Commits: 82c90c7, 2fab9e6 confirmed in git log
- [x] 887/887 tests pass

## Self-Check: PASSED
