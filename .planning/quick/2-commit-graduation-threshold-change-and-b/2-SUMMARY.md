---
phase: quick-2
plan: 01
subsystem: cli
tags: [status, monitoring, tdd, graduation, binance]
tech-stack:
  added: [requests==2.32.5]
  patterns: [TDD RED-GREEN, synchronous REST snapshot, argparse CLI flag]
key-files:
  created:
    - tests/test_status_command.py
  modified:
    - main.py
    - setup/verify.py
    - tests/test_graduation_reporter.py
    - requirements.txt
decisions:
  - "--status bypasses bot lock so it runs safely while bot is live"
  - "Binance prices via REST snapshot (api.binance.us) — no WebSocket, exits in <2s"
  - "get_binance_mid_price() returns None on any error (never raises)"
  - "Today P&L split into paper vs live columns for clarity"
metrics:
  duration: "~15 minutes"
  completed: "2026-02-28"
  tasks: 2
  files: 5
  new_tests: 20
  total_tests_before: 346
  total_tests_after: 366
---

# Quick Task 2: Commit Graduation Threshold Change and Build --status Command

**One-liner:** Committed min_days=0 graduation fix, then built `python main.py --status` — a 2-second bot health snapshot with BTC/ETH prices (Binance.US REST), bankroll, pending bets, today P&L (paper+live split), and recent 10 trades.

## Tasks Completed

| # | Task | Commit | Key Output |
|---|------|--------|------------|
| 1 | Commit graduation threshold changes | e999d6c | setup/verify.py + test_graduation_reporter.py — min_days=0 for all strategies |
| 2a | TDD RED — write failing tests | 74f5dbb | tests/test_status_command.py (20 tests, all failing) |
| 2b | TDD GREEN — implement --status | ab72b61 | main.py: get_binance_mid_price() + print_status() + --status flag |

## What Was Built

### Task 1: Graduation Threshold Commit

The already-modified `setup/verify.py` and `tests/test_graduation_reporter.py` were clean and all 346 tests passed. Both files committed with message confirming min_days=0 is the new standard (30 trades is the only volume gate).

### Task 2: `python main.py --status`

**New function: `get_binance_mid_price(symbol: str) -> Optional[float]`**
- Synchronous REST call to `https://api.binance.us/api/v3/ticker/bookTicker?symbol={symbol}`
- Returns `(bidPrice + askPrice) / 2` as a float
- Returns `None` on any `requests.RequestException` or `KeyError` — never raises
- Uses `api.binance.us` exclusively (binance.com is geo-blocked in the US)

**New function: `print_status(db) -> None`**
- Fetches BTC + ETH mid-prices via two REST calls
- Reads from DB: latest bankroll, open trades, today's trades (paper vs live split), all-time P&L
- Prints formatted BOT STATUS block: header, bankroll, prices, pending count, P&L rows, recent 10 trades newest-first
- Completes in under 2 seconds

**New argparse flag: `--status`**
- Added to `main()` argument parser
- Handler placed BEFORE `_acquire_bot_lock()` so it works while the bot process is running
- Loads DB from config, calls `print_status(db)`, exits cleanly

**Sample output (live data, 2026-02-28):**
```
================================================================
  BOT STATUS — 2026-02-28 19:36 UTC
================================================================
  Bankroll (DB):   $75.00
  BTC mid:         $66,192.38
  ETH mid:         $1,944.69
  Pending bets:    1 (paper: 1, live: 0)

  Today's P&L (paper):   $19.73   (6 settled)
  Today's P&L (live):    n/a     (0 settled)
  All-time P&L (paper):  $31.97
  All-time P&L (live):   $0.00

  Recent Trades (last 10):
  --------------------------------------------------------------
  2026-02-28 19:31  KXETH15M-...  yes   49c  [PAPER]  [open]
  ...
================================================================
```

## Test Coverage

20 new tests in `tests/test_status_command.py`:

- `TestStatusCommand` (16 tests): header, sections (Recent Trades, Pending, Bankroll, BTC, ETH, P&L), price values, bankroll value, pending count from open trades, ticker in recent trades, newest-first ordering, 3-second time limit, empty DB no crash, None price graceful handling
- `TestGetBinanceMidPrice` (4 tests): returns float from mocked response, returns None on RequestException, returns None on KeyError, uses binance.us URL (not binance.com)

**Total: 346 → 366 tests, 366/366 passing**

## Deviations from Plan

**[Rule 3 - Blocking] `requests` library not installed in venv**
- Found during: Task 2 GREEN phase setup
- Issue: `import requests` fails — not in venv or requirements.txt
- Fix: `pip install requests` + added `requests==2.32.5` to requirements.txt
- Files modified: requirements.txt
- Commit: ab72b61

No architectural deviations. All changes stayed within plan scope.

## Self-Check: PASSED

- `tests/test_status_command.py`: EXISTS (260 lines, 20 tests)
- `main.py` get_binance_mid_price: EXISTS (function defined at line ~750)
- `main.py` print_status: EXISTS (function defined at line ~770)
- `main.py` --status flag: EXISTS (argparse + handler)
- Commits: e999d6c, 74f5dbb, ab72b61 — all verified in git log
- `python main.py --status` smoke test: PASSED (live data confirmed)
- 366/366 tests: PASSED
