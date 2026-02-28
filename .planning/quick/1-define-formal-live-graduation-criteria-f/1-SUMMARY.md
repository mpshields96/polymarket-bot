---
phase: quick-1
plan: "01"
subsystem: db, verify, docs
tags: [graduation, paper-trading, live-enablement, db-stats, verify]
dependency_graph:
  requires: []
  provides: [graduation_stats, check_graduation_status, GRADUATION_CRITERIA.md]
  affects: [setup/verify.py, src/db.py]
tech_stack:
  added: []
  patterns: [TDD-red-green, non-critical-warn-checks]
key_files:
  created:
    - docs/GRADUATION_CRITERIA.md
    - tests/test_db_graduation.py
  modified:
    - src/db.py
    - setup/verify.py
decisions:
  - "Graduation check is WARN not FAIL — advisory, never blocks bot startup"
  - "first_trade_ts uses MIN(timestamp) across ALL paper trades (including unsettled) so days_running accurately reflects how long strategy has been running"
  - "fomc_rate min_trades=5 (not 30) because strategy fires ~8x/year — 30 would take 3+ years"
  - "weather_forecast min_days=14 (not 7) to capture seasonal/weekly weather variation"
metrics:
  duration_seconds: 221
  completed_date: "2026-02-28"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
  tests_before: 296
  tests_after: 324
  tests_added: 28
---

# Quick Task 1: Define Formal Live Graduation Criteria Summary

## One-Liner

Per-strategy graduation gates wired into verify.py — DB.graduation_stats() + GRADUATION_CRITERIA.md with thresholds (30 trades, 7 days, Brier < 0.25, < 5 consecutive losses).

## What Was Built

### Task 1: graduation_stats() + GRADUATION_CRITERIA.md

**`src/db.py`** — Added `DB.graduation_stats(strategy: str) -> dict` method in the `# ── Stats` section:
- Queries paper trades only (`is_paper=1`) for the given strategy
- Returns: `settled_count`, `win_rate`, `brier_score`, `consecutive_losses`, `first_trade_ts`, `days_running`, `total_pnl_usd`
- Empty DB returns all-None/zero dict (never raises)
- `brier_score = mean((win_prob - outcome)^2)` over trades where `win_prob IS NOT NULL`
- `consecutive_losses` = streak of losses at the tail of history (ordered by timestamp ASC)
- `first_trade_ts` = `MIN(timestamp)` including unsettled trades (so days_running is accurate from first bot activity)
- Read-only — no writes to DB

**`tests/test_db_graduation.py`** — 28 TDD tests covering:
- Empty DB behavior (8 tests)
- 50-trade stat accuracy (4 tests)
- Consecutive losses including NO-side bets (4 tests)
- Paper-only filter, unsettled exclusion, strategy isolation (3 tests)
- Brier score edge cases: perfect, worst, mean, None (4 tests)
- first_trade_ts and days_running (3 tests)
- total_pnl_usd from pnl_cents (2 tests)

**`docs/GRADUATION_CRITERIA.md`** — Human-readable graduation reference with:
- Standard thresholds table (30 trades, 7 days, Brier < 0.25, < 5 consecutive losses)
- Per-strategy notes for all 8 strategies including fomc (5 trade min) and weather (14-day min)
- How-to-check and how-to-graduate instructions
- Criteria version v1.0

### Task 2: check_graduation_status() in verify.py

**`setup/verify.py`** — Added:
- `_GRAD` dict at module level: 8 strategy threshold tuples `(min_trades, min_days, max_brier, max_consec)`
- `check_graduation_status()` function:
  - Reads DB path from config.yaml
  - Gracefully handles missing DB ("No DB yet — run bot first")
  - Calls `db.graduation_stats(strategy)` for each of 8 strategies
  - Evaluates 4 criteria per strategy: trades, days, brier, consecutive losses
  - All records use `critical=False` — graduation WARNs never cause exit 1
  - Shows gaps clearly: `"needs: trades 0/30, days 0.0/7"`
  - Shows READY FOR LIVE summary when all criteria met
- Wired into `run_all()` after `check_strategy()` as section [11]

## Verification Results

```
[11] Live graduation status (paper trading)
  ⚠️  WARN  Graduation: btc_lag_v1      trades=0 days=0.0 | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: eth_lag_v1      trades=0 days=0.0 | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: btc_drift_v1    trades=0 days=0.0 | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: eth_drift_v1    trades=0 days=0.0 | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: orderbook_imbalance_v1        | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: eth_orderbook_imbalance_v1    | needs: trades 0/30, days 0.0/7
  ⚠️  WARN  Graduation: weather_forecast_v1           | needs: trades 0/30, days 0.0/14
  ⚠️  WARN  Graduation: fomc_rate_v1                  | needs: trades 0/5

Results: 18/26 checks passed
✅ All critical checks passed. Bot is ready.
Exit code: 0
```

Test count: 296 → 324 (28 new graduation tests).

## Deviations from Plan

None — plan executed exactly as written. The TDD cycle went RED (28 fail) → GREEN (28 pass) without any unexpected issues.

## Self-Check: PASSED

| Item | Status |
|------|--------|
| docs/GRADUATION_CRITERIA.md | FOUND |
| tests/test_db_graduation.py | FOUND |
| src/db.py (modified) | FOUND |
| setup/verify.py (modified) | FOUND |
| Commit fa349ac (Task 1) | FOUND |
| Commit d6b9e21 (Task 2) | FOUND |
