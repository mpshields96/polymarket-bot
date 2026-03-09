---
created: 2026-03-09T11:31:04.335Z
title: Fix graduation_stats to query live bets for live strategies
area: database
files:
  - src/db.py:447-524
  - main.py:1586-1650
---

## Problem

`graduation_stats()` in `src/db.py` only queries `is_paper=1` (paper trades). For live strategies
(btc_drift_v1, eth_drift_v1, sol_drift_v1), this means `--graduation-status` displays paper bet
counts instead of live bet counts.

Discovered during autonomous session (2026-03-10): btc_drift showed **12/30** in `--graduation-status`
but actually had **22 live settled bets** (confirmed via direct SQL). By shutdown it had reached
**30 live settled bets**, but the command still showed the wrong number.

The Task 3 Brier computation command in AUTONOMOUS_SESSION.md also fails because it calls
`db.brier_score()` which doesn't exist — Brier is nested inside `graduation_stats()`.

## Solution

1. Add `is_paper: bool = True` parameter to `graduation_stats()` in `src/db.py`
   - Change `WHERE strategy = ? AND is_paper = 1` to `WHERE strategy = ? AND is_paper = ?`
   - Pass `1 if is_paper else 0` as the parameter
   - Also fix `first_trade_ts` sub-query to match the `is_paper` filter

2. Update `print_graduation_status()` in `main.py` to call `graduation_stats(strategy, is_paper=False)`
   for strategies that have any live settled bets (check DB first), else fall back to `is_paper=True`

3. Optionally: expose a standalone `db.brier_score(strategy, is_paper=False)` helper that
   calls `graduation_stats(strategy, is_paper=is_paper)["brier_score"]` — makes AUTONOMOUS_SESSION.md
   Task 3 command work without modification

4. Write regression tests:
   - `test_graduation_stats_live_only()` — seeds live + paper bets, confirms `is_paper=False` returns live count
   - `test_graduation_stats_paper_default()` — confirms backward compat (default still returns paper)

**Reporting bug only — zero trading impact.** Bot does not use `graduation_stats()` for any
trading decisions. This is purely a diagnostic/display fix.
