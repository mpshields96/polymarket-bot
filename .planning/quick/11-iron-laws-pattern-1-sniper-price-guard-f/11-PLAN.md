---
phase: quick-11
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - tests/test_live_executor.py
  - main.py
  - .claude/hooks/danger_zone_guard.sh
autonomous: true
requirements: [IRON-LAW-3, IRON-LAW-5, IRON-LAW-2]
must_haves:
  truths:
    - "expiry_sniper passes price_guard_min=87 to execute() — no order placed when execution price is 86c"
    - "Test exists that FAILS before the fix and PASSES after"
    - "danger_zone_guard.sh prints advisory warnings for Iron Law violations (exits 0 always)"
    - "All 1292 existing tests continue to pass"
  artifacts:
    - path: "tests/test_live_executor.py"
      provides: "price_guard_min=87 rejection test"
      contains: "price_guard_min=87"
    - path: "main.py"
      provides: "expiry_sniper_loop with price_guard_min=87"
      contains: "price_guard_min=87"
    - path: ".claude/hooks/danger_zone_guard.sh"
      provides: "Iron Laws advisory checks"
      contains: "LAW 3"
  key_links:
    - from: "main.py expiry_sniper_loop"
      to: "src/execution/live.execute()"
      via: "price_guard_min kwarg"
      pattern: "price_guard_min=87"
    - from: ".claude/hooks/danger_zone_guard.sh"
      to: "main.py"
      via: "grep check"
      pattern: "price_guard_min=1"
---

<objective>
Enforce Iron Law 3 (sniper floor 87c) with a failing test first, then fix main.py,
and extend the advisory danger-zone hook script with Iron Laws checks.

Purpose: The model's price_confidence formula floors at 87c — any fill below 87c is
off-model. The expiry_sniper currently passes price_guard_min=1 which allows off-model
fills to slip through after the slippage guard added in S81. The hook additions give
ongoing enforcement visibility without blocking edits.

Output: 1 new test (red then green), 1-line main.py fix, extended hook script.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
@/Users/matthewshields/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md

<interfaces>
From src/execution/live.py:
```python
async def execute(
    signal,
    market,
    orderbook,
    trade_usd: float,
    kalshi,
    db,
    live_confirmed: bool = False,
    strategy_name: str = "unknown",
    price_guard_min: int = 35,   # default _EXECUTION_MIN_PRICE_CENTS
    price_guard_max: int = 65,   # default _EXECUTION_MAX_PRICE_CENTS
) -> dict | None:
    ...
    # Line ~165: guard rejects if execution_yes_price not in [price_guard_min, price_guard_max]
    if not (price_guard_min <= execution_yes_price <= price_guard_max):
        logger.warning(...)
        return None
```

From tests/test_live_executor.py (fixtures already defined):
- make_signal(side="yes", price_cents=55) — Signal helper
- make_market() — Market with yes_price=55, no_price=45
- make_orderbook(yes_bid=..., no_bid=...) — OrderBook helper
- make_kalshi_mock() — AsyncMock with create_order returning make_order()
- make_db_mock() — MagicMock with save_trade
- live_env fixture — sets LIVE_TRADING=true
- bypass_first_run fixture — sets _FIRST_RUN_CONFIRMED=True

From main.py line ~1604 (current state to replace):
```python
result = await live_mod.execute(
    signal=signal,
    market=market,
    orderbook=orderbook,
    trade_usd=trade_usd,
    kalshi=kalshi,
    db=db,
    live_confirmed=live_confirmed,
    strategy_name=strategy.name,
    price_guard_min=1,       # <-- CHANGE THIS to 87
    price_guard_max=99,
)
```

From .claude/hooks/danger_zone_guard.sh (current DANGER_ZONE_FILES):
```bash
DANGER_ZONE_FILES=(
    "src/execution/live.py"
    "src/risk/kill_switch.py"
    "src/risk/sizing.py"
)
# Script already wired as PreToolUse in .claude/settings.json
# hook command: bash .claude/hooks/danger_zone_guard.sh
# Exit 0 = allow, exit 2 = hard-block
```

From src/risk/kill_switch.py line 39:
```python
HARD_MAX_TRADE_USD = 20.00
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing test then fix expiry_sniper price_guard_min to 87</name>
  <files>tests/test_live_executor.py, main.py</files>
  <behavior>
    - Test: execute() with price_guard_min=87 and orderbook execution price 86c returns None
    - Test: execute() with price_guard_min=87 and orderbook execution price 87c proceeds (not None)
    - The 86c test MUST fail before main.py is changed (proving guard was 1 before)
    - The 86c test MUST pass after main.py is changed to price_guard_min=87
  </behavior>
  <action>
    RED phase — add tests to TestExecuteGuards class in tests/test_live_executor.py:

    Test 1 (rejection at 86c): create an orderbook where the YES ask is 86c (no_bid=14 gives
    yes_ask=86 via _determine_limit_price logic — check: OrderBookLevel with ask_price=86 on yes
    side). Pass price_guard_min=87, price_guard_max=99. Assert result is None.
    Assert kalshi.create_order was NOT called. This test MUST fail initially (price_guard_min=1
    in expiry_sniper means main.py calls execute with 1, but this test directly calls execute with 87).

    Wait — the test calls execute() directly with price_guard_min=87. Since execute() already
    has the guard logic at line 165, the test WILL pass immediately. The test proves the guard
    WORKS when called correctly. The main.py fix is what makes expiry_sniper USE it.

    Correct RED strategy: Write a test that greps main.py to confirm price_guard_min=87 is present
    in the expiry_sniper call block. Use a simple assertion that reads main.py source. This test
    fails before the fix and passes after.

    Add to tests/test_live_executor.py in a new class TestExpirySnipPriceGuardLaw3:

    ```python
    class TestExpirySnipPriceGuardLaw3:
        """Iron Law 3: expiry_sniper must pass price_guard_min=87 to execute()."""

        def test_expiry_sniper_uses_87c_floor(self):
            """LAW 3: main.py expiry_sniper_loop must pass price_guard_min=87.
            Fails if price_guard_min=1 (the off-model permissive value).
            Passes once main.py is fixed to price_guard_min=87.
            """
            import re
            main_src = open("main.py").read()
            # Find the expiry_sniper execute() call block
            # It must contain price_guard_min=87, not price_guard_min=1
            sniper_block_match = re.search(
                r"expiry_sniper.*?price_guard_min\s*=\s*(\d+)",
                main_src,
                re.DOTALL,
            )
            assert sniper_block_match, "price_guard_min not found in expiry_sniper block"
            assert sniper_block_match.group(1) == "87", (
                f"LAW 3 VIOLATION: expiry_sniper price_guard_min={sniper_block_match.group(1)}, "
                f"expected 87 (model floor). Below 87c is off-model territory."
            )

        async def test_execute_rejects_86c_when_guard_is_87(self, live_env, bypass_first_run):
            """execute() returns None when YES execution price is 86c and price_guard_min=87."""
            # yes_ask = 86c: use OrderBookLevel directly in the yes-side ask
            from src.platforms.kalshi import OrderBook, OrderBookLevel
            ob = OrderBook(
                yes=[OrderBookLevel(price=86, quantity=100)],
                no=[],
            )
            kalshi = make_kalshi_mock()
            db = make_db_mock()
            result = await execute(
                make_signal(side="yes", price_cents=88),
                make_market(yes_price=86),
                ob,
                5.0,
                kalshi,
                db,
                live_confirmed=True,
                strategy_name="expiry_sniper_v1",
                price_guard_min=87,
                price_guard_max=99,
            )
            assert result is None, "execute() must reject 86c when price_guard_min=87"
            kalshi.create_order.assert_not_called()
    ```

    Run tests — test_expiry_sniper_uses_87c_floor FAILS (RED). Commit:
    `test(quick-11): add LAW-3 failing test for expiry_sniper price_guard_min=87`

    GREEN phase — fix main.py:
    Find the expiry_sniper execute() call (around line 1604). Change:
      price_guard_min=1,
    to:
      price_guard_min=87,
    Leave price_guard_max=99 unchanged.

    Run full test suite: venv/bin/python3 -m pytest tests/ -q --tb=short
    All 1292+ tests must pass (the new tests add to the count).

    Commit: `fix(quick-11): LAW-3 expiry_sniper price_guard_min 1→87 (model floor)`
  </action>
  <verify>
    <automated>venv/bin/python3 -m pytest tests/test_live_executor.py::TestExpirySnipPriceGuardLaw3 -v --tb=short</automated>
  </verify>
  <done>
    Both new tests pass. main.py line contains price_guard_min=87. Full suite still at 1292+ passing.
  </done>
</task>

<task type="auto">
  <name>Task 2: Extend danger_zone_guard.sh with Iron Laws advisory checks</name>
  <files>.claude/hooks/danger_zone_guard.sh</files>
  <action>
    The existing danger_zone_guard.sh already handles DANGER ZONE file detection and
    pre-edit test running (exits 0 or 2). It does NOT check Iron Laws content.

    Extend the script to add Iron Laws advisory warnings. Insert a new section AFTER
    the existing test-pass exit 0 block (around line 85), so it only fires when tests pass
    and the edit is about to proceed.

    Add a new function check_iron_laws() that:

    LAW 3 check (price guard floor):
      - grep main.py for the pattern: price_guard_min=1 near expiry_sniper context
      - Use: grep -n "price_guard_min=1" "$PROJ_ROOT/main.py"
      - If found: print warning to stderr that LAW 3 may be violated (price_guard_min=1
        found in main.py — should be 87 for expiry_sniper)

    LAW 5 check (no hardcoded credentials):
      - grep all .py files for: BEGIN RSA PRIVATE KEY
      - grep all .py files for: KALSHI_API_KEY_ID\s*=\s*"[^"]
      - grep all .py files for: sk-ant- (Anthropic key in source)
      - If any found: print warning to stderr with file:line

    LAW 2 check (kill_switch hard cap unchanged):
      - Extract current HARD_MAX_TRADE_USD value from src/risk/kill_switch.py
      - Expected value is 20.00 (from current codebase)
      - If value != 20.00: print warning to stderr

    The function always returns 0 (never blocks). Warnings go to stderr.
    Print a separator line and "IRON LAWS CHECK" header before the checks so
    output is scannable.

    Structure of additions (insert before the final "exit 0" in the tests-passed branch):

    ```bash
    check_iron_laws() {
        local warnings=0

        echo "" >&2
        echo "── IRON LAWS ADVISORY CHECK ────────────────────────────────────" >&2

        # LAW 3: expiry_sniper price_guard_min must be 87, not 1
        if grep -qn "price_guard_min=1" "$PROJ_ROOT/main.py" 2>/dev/null; then
            echo "WARNING [LAW 3]: price_guard_min=1 found in main.py" >&2
            echo "  Expected price_guard_min=87 for expiry_sniper (model floor)." >&2
            grep -n "price_guard_min=1" "$PROJ_ROOT/main.py" >&2
            warnings=$((warnings + 1))
        fi

        # LAW 5: no hardcoded credentials in .py files
        local cred_hits
        cred_hits=$(grep -rn "BEGIN RSA PRIVATE KEY\|KALSHI_API_KEY_ID\s*=\s*\"[^\"]\|sk-ant-" \
            "$PROJ_ROOT/src" "$PROJ_ROOT/main.py" 2>/dev/null | grep -v ".pyc" || true)
        if [[ -n "$cred_hits" ]]; then
            echo "WARNING [LAW 5]: Possible hardcoded credentials detected:" >&2
            echo "$cred_hits" >&2
            warnings=$((warnings + 1))
        fi

        # LAW 2: kill_switch HARD_MAX_TRADE_USD must be 20.00
        local hard_max
        hard_max=$(grep -m1 "HARD_MAX_TRADE_USD\s*=" "$PROJ_ROOT/src/risk/kill_switch.py" \
            2>/dev/null | grep -oE "[0-9]+\.[0-9]+" || echo "NOT_FOUND")
        if [[ "$hard_max" != "20.00" ]]; then
            echo "WARNING [LAW 2]: HARD_MAX_TRADE_USD=$hard_max in kill_switch.py" >&2
            echo "  Expected 20.00. Verify this change is intentional." >&2
            warnings=$((warnings + 1))
        fi

        if [[ $warnings -eq 0 ]]; then
            echo "All Iron Laws checks passed." >&2
        else
            echo "$warnings warning(s) above — advisory only, edit is NOT blocked." >&2
        fi
        echo "────────────────────────────────────────────────────────────────" >&2
        echo "" >&2
    }
    ```

    Call check_iron_laws just before the final `exit 0` in the tests-passed branch.
    The script's exit code is unchanged (0 on pass, 2 on fail) — Iron Laws checks
    are purely advisory.

    Also add the four DANGER ZONE files from the task description that are not yet
    in the DANGER_ZONE_FILES array:
      src/auth/kalshi_auth.py
      src/platforms/kalshi.py
      main.py

    These additions mean edits to those files also run the test suite first.

    Do NOT remove existing entries. The final array should be:
    ```bash
    DANGER_ZONE_FILES=(
        "src/execution/live.py"
        "src/risk/kill_switch.py"
        "src/risk/sizing.py"
        "src/auth/kalshi_auth.py"
        "src/platforms/kalshi.py"
        "main.py"
    )
    ```

    Commit: `feat(quick-11): extend danger_zone_guard with Iron Laws advisory checks`
  </action>
  <verify>
    <automated>bash /Users/matthewshields/Projects/polymarket-bot/.claude/hooks/danger_zone_guard.sh &lt;&lt;&lt; '{"file_path":"/Users/matthewshields/Projects/polymarket-bot/src/execution/live.py"}'; echo "exit=$?"</automated>
  </verify>
  <done>
    Script exits 0 after tests pass and prints Iron Laws advisory section to stderr.
    Script runs full test suite when any of the 6 DANGER ZONE files is edited.
    Iron Laws warnings print but never block.
  </done>
</task>

</tasks>

<verification>
venv/bin/python3 -m pytest tests/ -q --tb=short 2>&1 | tail -5
  Expected: 1294+ passed (1292 original + 2 new), 0 failed.

grep -n "price_guard_min" main.py | grep expiry_sniper -A5
  Expected: price_guard_min=87 in the expiry_sniper execute() call block.

bash .claude/hooks/danger_zone_guard.sh &lt;&lt;&lt; '{"file_path":"src/execution/live.py"}'
  Expected: runs test suite, prints IRON LAWS ADVISORY CHECK section, exits 0.
</verification>

<success_criteria>
- test_expiry_sniper_uses_87c_floor passes (confirms main.py has price_guard_min=87)
- test_execute_rejects_86c_when_guard_is_87 passes (confirms execute() guard works)
- main.py expiry_sniper_loop calls execute() with price_guard_min=87
- danger_zone_guard.sh covers 6 files (added kalshi_auth.py, kalshi.py, main.py)
- danger_zone_guard.sh prints Iron Laws advisory output, always exits 0 on pass
- All 1292+ tests pass, 0 regressions
- 2 atomic commits created
</success_criteria>

<output>
After completion, create .planning/quick/11-iron-laws-pattern-1-sniper-price-guard-f/11-SUMMARY.md
with what was built, commits made, and test count.
</output>
