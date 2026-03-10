---
phase: quick-6
plan: 6
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/execution/live.py
  - tests/test_live_executor.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "Live executor rejects orders when execution price is outside 35-65¢"
    - "Live executor rejects orders when slippage from signal price exceeds 10¢"
    - "No-side signals correctly convert to YES-equivalent price for slippage calculation"
    - "Rejected orders return None with a warning log — no order placed, no DB write"
    - "Orders within guard bounds still execute normally (no regression)"
  artifacts:
    - path: "src/execution/live.py"
      provides: "Execution-time price guard constants + rejection logic"
      contains: "EXECUTION_MIN_PRICE_CENTS"
    - path: "tests/test_live_executor.py"
      provides: "Regression tests for price guard + slippage guard"
      exports: ["TestExecutionPriceGuard"]
  key_links:
    - from: "src/execution/live.py"
      to: "_determine_limit_price()"
      via: "price guard check immediately after price determination"
      pattern: "EXECUTION_MIN_PRICE_CENTS.*EXECUTION_MAX_PRICE_CENTS"
---

<objective>
Add execution-time price guard to live.py — after fetching the current orderbook price,
reject the order if execution price is outside 35-65¢ or if slippage from signal price
exceeds 10¢. Return None with a warning log in both rejection cases.

Purpose: btc_drift's 35-65¢ guard fires at signal generation time only. HFTs can reprice
in the 0.1-1s asyncio gap, causing orders to fill at 84¢ (observed session 37 2026-03-10
08:39 CDT). This corrupts the live Brier score and bets at prices the calibrated model
never tested.

Output: Two constants + ~10 lines in live.py, plus regression tests in test_live_executor.py.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/src/execution/live.py
@/Users/matthewshields/Projects/polymarket-bot/tests/test_live_executor.py
@/Users/matthewshields/Projects/polymarket-bot/.planning/todos/pending/2026-03-10-add-execution-time-price-guard-to-live-executor.md

<interfaces>
<!-- From src/execution/live.py — key structures executor needs -->

Signal has:
  signal.side: str          # "yes" or "no"
  signal.price_cents: int   # signal price in cents (YES-equivalent for YES side, NO-equivalent for NO side)
  signal.ticker: str

After _determine_limit_price():
  price_cents: Optional[int]  # execution price — YES-side: the cost to buy YES; NO-side: cost to buy NO

Slippage conversion rule (from todo spec):
  signal_yes_price = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
  execution_yes_price = price_cents if signal.side == "yes" else (100 - price_cents)
  slippage = abs(execution_yes_price - signal_yes_price)

Guard constants (from todo spec):
  EXECUTION_MIN_PRICE_CENTS = 35
  EXECUTION_MAX_PRICE_CENTS = 65
  EXECUTION_MAX_SLIPPAGE_CENTS = 10
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Write failing tests for execution-time price guard</name>
  <files>tests/test_live_executor.py</files>
  <behavior>
    - test_rejects_execution_price_above_guard: signal YES@55¢, execution price 80¢ → returns None, no create_order call
    - test_rejects_execution_price_below_guard: signal YES@55¢, execution price 20¢ → returns None, no create_order call
    - test_rejects_excessive_slippage: signal YES@55¢, execution price 67¢ (12¢ slippage > 10¢ max) → returns None
    - test_allows_execution_at_guard_boundary: signal YES@55¢, execution price 65¢ exactly (10¢ slippage = at max) → proceeds
    - test_no_side_slippage_uses_yes_equivalent: signal NO@45¢ (YES-eq=55¢), execution NO@32¢ (YES-eq=68¢) → 13¢ slippage → rejected
    - test_valid_price_executes_normally: signal YES@55¢, execution 59¢ (4¢ slip, in range) → order placed (regression check)
  </behavior>
  <action>
    Append a new class TestExecutionPriceGuard to tests/test_live_executor.py.

    Each test uses the existing make_signal(), make_market(), make_orderbook(), make_kalshi_mock(),
    make_db_mock() helpers plus live_env and bypass_first_run fixtures already in the file.

    To force a specific execution price, pass an orderbook whose ask price computes to the desired
    value. For YES side: yes_ask = 100 - no_bid, so no_bid = 100 - desired_yes_price.
    For NO side: no_ask = 100 - yes_bid, so yes_bid = 100 - desired_no_price.

    All tests in this class should call execute() with live_confirmed=True, strategy_name="btc_drift_v1".

    Run tests immediately after writing — they MUST fail (live.py guard does not exist yet):
      source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest tests/test_live_executor.py::TestExecutionPriceGuard -v 2>&1 | tail -20
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/test_live_executor.py::TestExecutionPriceGuard -v 2>&1 | tail -20</automated>
  </verify>
  <done>All 6 tests in TestExecutionPriceGuard are collected and FAILING (red). No import errors.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Implement price guard in live.py — make tests pass</name>
  <files>src/execution/live.py</files>
  <behavior>
    After _determine_limit_price() returns and the basic 1-99 range check passes,
    add the execution-time guard block before the count calculation.
    All 6 new tests pass. All 869 existing tests continue to pass.
  </behavior>
  <action>
    Add three module-level constants near the top of live.py (after imports, before _FIRST_RUN_CONFIRMED):

      _EXECUTION_MIN_PRICE_CENTS: int = 35
      _EXECUTION_MAX_PRICE_CENTS: int = 65
      _EXECUTION_MAX_SLIPPAGE_CENTS: int = 10

    In the execute() function, after the existing `if not (1 <= price_cents <= 99)` check
    (line ~98-100) and BEFORE the count calculation (line ~103), insert:

      # ── Execution-time price guard ────────────────────────────────────────
      # Convert execution price to YES-equivalent for range + slippage checks
      execution_yes_price = price_cents if signal.side == "yes" else (100 - price_cents)
      signal_yes_price = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)

      if not (_EXECUTION_MIN_PRICE_CENTS <= execution_yes_price <= _EXECUTION_MAX_PRICE_CENTS):
          logger.warning(
              "[live] Execution price %d¢ (YES-equiv) outside guard %d-%d¢ — rejecting "
              "(signal was %d¢, ticker=%s)",
              execution_yes_price, _EXECUTION_MIN_PRICE_CENTS, _EXECUTION_MAX_PRICE_CENTS,
              signal_yes_price, signal.ticker,
          )
          return None

      slippage_cents = abs(execution_yes_price - signal_yes_price)
      if slippage_cents > _EXECUTION_MAX_SLIPPAGE_CENTS:
          logger.warning(
              "[live] Slippage %d¢ exceeds max %d¢ — rejecting (signal=%d¢, exec=%d¢, ticker=%s)",
              slippage_cents, _EXECUTION_MAX_SLIPPAGE_CENTS,
              signal_yes_price, execution_yes_price, signal.ticker,
          )
          return None

    After implementing, run ALL tests (not just the new class) to confirm no regression:
      source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest tests/ -q 2>&1 | tail -10
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/ -q 2>&1 | tail -10</automated>
  </verify>
  <done>
    - All 6 TestExecutionPriceGuard tests pass (green)
    - Total test count is 869 + 6 = 875/875 passing
    - No regressions in existing TestExecuteSuccess / TestExecuteFailures / TestDetermineLimitPrice
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. `python -m pytest tests/test_live_executor.py -v` — 100% pass, TestExecutionPriceGuard visible
2. `python -m pytest tests/ -q` — 875/875 pass
3. Manually inspect live.py — confirm guard appears AFTER limit price determination and BEFORE contract count calculation
4. Confirm no_bid=20 (yes_ask=80) with signal YES@55¢ is rejected by the range guard
5. Confirm no_bid=33 (yes_ask=67) with signal YES@55¢ is rejected by the slippage guard (12¢ > 10¢ max)
</verification>

<success_criteria>
- Live executor never places an order when execution price is outside 35-65¢ (YES-equivalent)
- Live executor never places an order when slippage from signal price exceeds 10¢
- NO-side slippage is correctly computed via YES-equivalent conversion (not raw NO price comparison)
- Zero regression: all existing 869 tests still pass
- 875/875 total tests pass
</success_criteria>

<output>
After completion, commit: `fix(live): add execution-time price guard (35-65¢ + 10¢ max slippage)`

Update .planning/STATE.md quick tasks table:
| 7 | Add execution-time price guard to live.py | 2026-03-10 | {commit} | .planning/quick/6-add-execution-time-price-guard-to-live-p/ |

Delete todo file: .planning/todos/pending/2026-03-10-add-execution-time-price-guard-to-live-executor.md
</output>
