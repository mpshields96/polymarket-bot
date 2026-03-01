---
phase: quick-2
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - setup/verify.py
  - tests/test_graduation_reporter.py
  - main.py
  - tests/test_status_command.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "python main.py --status prints recent trades (last 10), pending count, today P&L, bankroll, and BTC/ETH mid-prices"
    - "BTC/ETH prices come from a synchronous Binance.US REST snapshot (no WebSocket)"
    - "346/346 tests pass after all changes"
    - "Uncommitted verify.py + test_graduation_reporter.py changes are committed first"
  artifacts:
    - path: "tests/test_status_command.py"
      provides: "Tests for print_status() written before implementation (TDD RED)"
      exports: ["TestStatusCommand"]
    - path: "main.py"
      provides: "print_status(db) function + --status argparse flag"
  key_links:
    - from: "main.py print_status()"
      to: "src/db.py"
      via: "db.get_trades(limit=10), db.get_open_trades(), db.latest_bankroll()"
      pattern: "db\\.get_trades|db\\.get_open_trades|db\\.latest_bankroll"
    - from: "main.py print_status()"
      to: "api.binance.us"
      via: "requests.get() REST snapshot (synchronous)"
      pattern: "requests\\.get.*binance\\.us"
---

<objective>
Two sequential tasks:
1. Commit already-changed files: setup/verify.py (min_days removed) + tests/test_graduation_reporter.py (test updated to match)
2. Build `python main.py --status` — a rich live-bot status view using TDD

Purpose: Give Matthew a single command to check bot health without tailing logs.
Output: Committed verify.py changes + new --status flag with tests.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/CLAUDE.md
@/Users/matthewshields/Projects/polymarket-bot/src/db.py

<interfaces>
<!-- Key DB methods available for status display -->

From src/db.py:
```python
db.get_trades(is_paper=None, ticker=None, limit=100) -> List[Dict]
  # Dict keys: id, timestamp, ticker, side, price_cents, count, cost_usd,
  #            strategy, is_paper, result, pnl_cents, settled_at

db.get_open_trades(is_paper=None) -> List[Dict]
  # Unsettled trades (result IS NULL)

db.latest_bankroll() -> Optional[float]
  # Most recent balance_usd from bankroll_history

db.total_realized_pnl_usd(is_paper=None) -> float
  # Sum of all settled pnl_cents / 100

db.win_rate(is_paper=None, limit=100) -> Optional[float]
  # wins/settled, None if no settled trades
```

<!-- Existing CLI pattern from main.py -->
From main.py ~line 760:
```python
parser.add_argument("--graduation-status", action="store_true", ...)

# Handler pattern (runs before bot loop):
if args.graduation_status:
    print_graduation_status(db)
    db.close()
    return
```

<!-- --report function for P&L pattern reference -->
From main.py print_report(db) ~line 723:
```python
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
trades = db.get_trades(limit=50)
today_trades = [t for t in trades if ...]
total_pnl_cents = sum(t.get("pnl_cents", 0) or 0 for t in settled)
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Commit the graduation threshold changes</name>
  <files>setup/verify.py, tests/test_graduation_reporter.py</files>
  <action>
Run 346/346 tests to confirm the already-changed files are clean:
```
source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest /Users/matthewshields/Projects/polymarket-bot/tests/ -v --tb=short 2>&1 | tail -20
```

If all pass, commit both files:
```
git add setup/verify.py tests/test_graduation_reporter.py && git commit -m "feat: remove min_days gate from graduation criteria (30 trades is the only volume gate)"
```

The verify.py change: _GRAD tuples already have min_days=0 for all strategies (confirmed in file).
The test change: test_weather_shows_trade_threshold now asserts "0/30" not "0/30 days" (or similar fix that matches the updated _GRAD).
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/ -v --tb=short 2>&1 | tail -5</automated>
  </verify>
  <done>346/346 tests pass. Both files committed to git. `git status` shows clean working tree for those files.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: TDD — write tests then implement python main.py --status</name>
  <files>tests/test_status_command.py, main.py</files>
  <behavior>
    - Test: --status prints a "BOT STATUS" header line
    - Test: --status prints "Recent Trades" section with last 10 trades (newest first): timestamp, ticker, side, price_cents, is_paper label
    - Test: --status prints "Pending" count (open unsettled trades)
    - Test: --status prints today's P&L in USD (paper trades) and today's P&L (live trades, or "n/a" if none)
    - Test: --status prints bankroll estimate from DB latest_bankroll()
    - Test: --status prints BTC mid-price line (mocked — no real HTTP in tests)
    - Test: --status prints ETH mid-price line (mocked)
    - Test: get_binance_mid_price("BTCUSDT") returns a float from mocked requests.get()
    - Test: get_binance_mid_price returns None on network error (requests.RequestException), does not raise
    - Test: print_status() completes in under 3 seconds when Binance is mocked
  </behavior>
  <action>
RED phase — write tests/test_status_command.py first (all tests fail because print_status doesn't exist yet).

Test file structure:
```python
"""Tests for python main.py --status command."""
import io, time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
from src.db import DB

@pytest.fixture
def db(tmp_path):
    d = DB(tmp_path / "test.db")
    d.init()
    yield d
    d.close()

def _run_print_status(db, mock_btc=55000.0, mock_eth=2800.0) -> str:
    from main import print_status
    captured = io.StringIO()
    with patch("sys.stdout", captured):
        with patch("main.get_binance_mid_price", side_effect=[mock_btc, mock_eth]):
            print_status(db)
    return captured.getvalue()
```

Tests: assert "BOT STATUS" in output, assert "Pending" in output, assert "BTC" in output,
assert "ETH" in output, assert "Bankroll" in output, assert "P&L" in output, etc.

GREEN phase — implement in main.py:

1. Add `get_binance_mid_price(symbol: str) -> Optional[float]` function:
   - Uses `requests.get("https://api.binance.us/api/v3/ticker/bookTicker?symbol={symbol}", timeout=5)`
   - Returns `(float(data["bidPrice"]) + float(data["askPrice"])) / 2`
   - Returns `None` on any `requests.RequestException` or KeyError
   - `requests` is already available (standard library complement, in venv)

2. Add `print_status(db)` function:
   - Fetch BTC mid: `get_binance_mid_price("BTCUSDT")`
   - Fetch ETH mid: `get_binance_mid_price("ETHUSDT")`
   - DB reads: `db.get_trades(limit=10)`, `db.get_open_trades()`, `db.latest_bankroll()`, `db.total_realized_pnl_usd()`
   - Today's P&L: filter get_trades(limit=200) by today's UTC date, split paper vs live, sum pnl_cents/100
   - Print output format:
     ```
     ================================================================
       BOT STATUS — 2026-02-28 12:00 UTC
     ================================================================
       Bankroll (DB):   $75.23
       BTC mid:         $55,123.45
       ETH mid:         $2,801.33
       Pending bets:    3 (paper: 3, live: 0)

       Today's P&L (paper):   $0.00   (0 settled)
       Today's P&L (live):    n/a     (0 settled)
       All-time P&L (paper):  $-1.20
       All-time P&L (live):   $0.00

       Recent Trades (last 10):
       ----------------------------------------------------------------
       2026-02-28 11:45  KXBTC15M-25FEB2026-T98749  yes  44c  [PAPER]
       ...
     ================================================================
     ```

3. Add `--status` argparse argument (alongside --report, --graduation-status)

4. Add handler in `main()` BEFORE the bot loop:
   ```python
   if args.status:
       print_status(db)
       db.close()
       return
   ```

Note: `requests` must be verified in venv. If not installed, add to requirements.txt and pip install.
Check: `source venv/bin/activate && python -c "import requests; print(requests.__version__)"`.
If missing: `pip install requests`.

Do NOT open WebSocket for --status. REST-only snapshot, completes in <2 seconds.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/test_status_command.py -v && python -m pytest tests/ -v --tb=short 2>&1 | tail -5</automated>
  </verify>
  <done>
    - tests/test_status_command.py exists with 10+ tests, all passing
    - 346+N tests pass total (N = new tests added)
    - `python main.py --status` prints BOT STATUS block with BTC/ETH prices, bankroll, pending count, today P&L, recent trades
    - No WebSocket opened — exits in under 3 seconds
    - Commit: `git add tests/test_status_command.py main.py && git commit -m "feat: add --status CLI command with rich bot status (recent trades, pending, P&L, Binance price snapshot)"`
  </done>
</task>

</tasks>

<verification>
After both tasks:
- `git log --oneline -3` shows 2 new commits (graduation threshold + status command)
- `python -m pytest tests/ -v 2>&1 | tail -3` shows all tests passing
- `python main.py --status` exits without error and prints the status block (requires DB to exist at data/polybot.db; if DB empty, shows zeroed values — acceptable)
</verification>

<success_criteria>
- 346+N tests pass (N >= 10 for new status tests)
- verify.py + test_graduation_reporter.py committed
- main.py --status works: shows BOT STATUS table with bankroll, BTC/ETH price, pending bets, today P&L (paper + live), recent 10 trades
- Binance REST snapshot — no WebSocket, no connection held open
- All CLAUDE.md rules respected: one file one job, requests only from venv, no writes outside project root
</success_criteria>

<output>
After completion, create `/Users/matthewshields/Projects/polymarket-bot/.planning/quick/2-commit-graduation-threshold-change-and-b/2-SUMMARY.md` summarizing what was built and committed.
</output>
