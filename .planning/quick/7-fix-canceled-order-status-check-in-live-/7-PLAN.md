---
phase: quick-7
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - tests/test_live_executor.py
  - src/execution/live.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "execute() returns None and does NOT call db.save_trade() when order.status == 'canceled'"
    - "execute() records trade normally and returns dict when order.status == 'resting'"
    - "execute() records trade normally and returns dict when order.status == 'executed' (existing behavior preserved)"
  artifacts:
    - path: "tests/test_live_executor.py"
      provides: "Two new tests: canceled status guard + resting status success"
    - path: "src/execution/live.py"
      provides: "status guard block between create_order() and db.save_trade()"
  key_links:
    - from: "src/execution/live.py"
      to: "src/db.py"
      via: "db.save_trade() — must NOT be called when order.status == 'canceled'"
      pattern: "order\\.status.*canceled"
---

<objective>
Fix canceled order status check in src/execution/live.py.

After create_order() returns, the code must check order.status. If status is "canceled",
execute() must return None without calling db.save_trade(). A canceled order must not be
recorded as a live bet — it corrupts calibration data and graduation stats (trade counter
increments, kill switch consecutive-loss counter can fire, Brier score is poisoned).

"resting" status (GTC order placed but not yet matched) must be recorded normally — the
order is live and the settlement loop will handle it.

Purpose: Prevent phantom live trades from corrupting graduation stats and calibration data.
Output: 2 new tests + 1 guard block in live.py.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/src/execution/live.py
@/Users/matthewshields/Projects/polymarket-bot/tests/test_live_executor.py

<interfaces>
<!-- From src/platforms/kalshi.py — Order dataclass -->
```python
@dataclass
class Order:
    order_id: str
    client_order_id: str
    ticker: str
    side: str           # "yes" | "no"
    action: str         # "buy" | "sell"
    type: str           # "limit" | "market"
    status: str         # "resting" | "canceled" | "executed" | "pending"
    yes_price: Optional[int]
    no_price: Optional[int]
    initial_count: int
    remaining_count: int
    fill_count: int
    created_time: str
```

<!-- From tests/test_live_executor.py — existing helpers -->
```python
def make_order(order_id="server-order-123", status="executed"):
    return Order(order_id=..., status=status, ...)

def make_kalshi_mock(order=None):
    kalshi = MagicMock()
    kalshi.create_order = AsyncMock(return_value=order or make_order())
    return kalshi

@pytest.fixture() def bypass_first_run(monkeypatch): ...
@pytest.fixture() def live_env(monkeypatch): ...
```

<!-- Insertion point in src/execution/live.py — lines 165-171 -->
```python
    now_utc = datetime.now(timezone.utc).isoformat()
    logger.info(
        "[LIVE] Order placed: server_id=%s status=%s",
        order.order_id, order.status,
    )

    # ── Record to DB ──────────────────────────────────────────────────
    trade_id = db.save_trade(...)
```
<!-- Guard must be inserted AFTER the logger.info block, BEFORE db.save_trade() -->
</interfaces>
</context>

<tasks>

<task type="tdd">
  <name>Task 1: Write failing tests for canceled/resting status handling</name>
  <files>tests/test_live_executor.py</files>
  <behavior>
    - Test: canceled status → returns None, db.save_trade NOT called, create_order WAS called
    - Test: resting status → returns dict (not None), db.save_trade IS called once
    - Both tests use existing fixtures: live_env, bypass_first_run
    - Both tests use make_order(status="canceled") / make_order(status="resting")
    - Add both tests to a new class TestExecuteOrderStatusGuard inside test_live_executor.py
  </behavior>
  <action>
    Append a new test class `TestExecuteOrderStatusGuard` to the end of
    tests/test_live_executor.py. Two async test methods:

    1. `test_canceled_order_not_recorded_in_db`:
       - kalshi = make_kalshi_mock(order=make_order(status="canceled"))
       - db = make_db_mock()
       - Call execute() with live_env + bypass_first_run fixtures
       - Assert result is None
       - Assert db.save_trade.assert_not_called()
       - Assert kalshi.create_order.assert_called_once() (order WAS placed, guard fires after)

    2. `test_resting_order_recorded_normally`:
       - kalshi = make_kalshi_mock(order=make_order(status="resting"))
       - db = make_db_mock()
       - Call execute() with live_env + bypass_first_run fixtures
       - Assert result is not None
       - Assert result["status"] == "resting"
       - Assert db.save_trade.assert_called_once()

    Run tests to confirm BOTH fail (RED state):
    `source venv/bin/activate && python -m pytest tests/test_live_executor.py::TestExecuteOrderStatusGuard -v`
    Expected: 2 failures (test_canceled fails because save_trade IS called; test_resting passes already — that's fine, record it).
  </action>
  <verify>
    <automated>source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest /Users/matthewshields/Projects/polymarket-bot/tests/test_live_executor.py::TestExecuteOrderStatusGuard -v 2>&1 | tail -20</automated>
  </verify>
  <done>
    TestExecuteOrderStatusGuard exists with 2 test methods.
    test_canceled_order_not_recorded_in_db FAILS (RED — db.save_trade called when it should not be).
    test_resting_order_recorded_normally PASSES or FAILS (either is fine at this stage — record outcome).
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add canceled status guard to live.py and verify GREEN</name>
  <files>src/execution/live.py</files>
  <behavior>
    - After order = await kalshi.create_order(...) returns and logger.info logs the status,
      check if order.status == "canceled"
    - If canceled: log a warning with order_id + ticker, return None (do NOT call db.save_trade)
    - All other statuses ("executed", "resting", "pending") continue to db.save_trade normally
  </behavior>
  <action>
    In src/execution/live.py, insert the following guard block AFTER the logger.info block
    (line ~167) and BEFORE the `# ── Record to DB ──` comment (line ~171):

    ```python
    # ── Canceled order guard ─────────────────────────────────────────────
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

    Do NOT change any other code. The guard sits between logger.info and db.save_trade only.

    After implementing, run the full test suite to confirm:
    1. TestExecuteOrderStatusGuard passes (both tests GREEN)
    2. No previously passing tests regress (all 869 must still pass)
  </action>
  <verify>
    <automated>source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest /Users/matthewshields/Projects/polymarket-bot/tests/test_live_executor.py -v 2>&1 | tail -30</automated>
  </verify>
  <done>
    TestExecuteOrderStatusGuard::test_canceled_order_not_recorded_in_db PASSES (GREEN).
    TestExecuteOrderStatusGuard::test_resting_order_recorded_normally PASSES.
    All prior test_live_executor.py tests still pass.
    Full suite: 871/871 tests pass (869 + 2 new).
  </done>
</task>

</tasks>

<verification>
Full test suite must pass after implementation:
`source venv/bin/activate && python -m pytest tests/ -v 2>&1 | tail -10`
Expected: 871 passed (869 existing + 2 new).

Spot check the guard logic manually:
- grep for `order.status == "canceled"` in src/execution/live.py — must appear exactly once
- grep for `db.save_trade` in src/execution/live.py — must appear AFTER the canceled guard
</verification>

<success_criteria>
- order.status == "canceled" → execute() returns None, db.save_trade() never called
- order.status == "resting" → execute() records trade normally and returns trade dict
- order.status == "executed" → existing behavior unchanged (all prior tests still green)
- Test count: 871/871 (was 869/869)
- No changes to any file other than tests/test_live_executor.py and src/execution/live.py
</success_criteria>

<output>
After completion, commit with:
  git add src/execution/live.py tests/test_live_executor.py
  git commit -m "fix(live): guard against recording canceled orders as live bets"

Update .planning/STATE.md Quick Tasks table:
  | 8 | Fix canceled order status check in live.py (canceled → no DB write, resting → record normally) | {date} | {commit} | .planning/quick/7-fix-canceled-order-status-check-in-live-/ |
</output>
```
