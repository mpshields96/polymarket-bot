---
phase: quick-8
plan: 01
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/db.py
  - tests/test_db_graduation.py
  - main.py
  - setup/verify.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "graduation_stats() accepts is_paper=False and returns only live trade counts"
    - "graduation_stats() default behavior (is_paper=True) is unchanged — all existing tests pass"
    - "--graduation-status shows correct live settled counts for btc_drift_v1, eth_drift_v1, sol_drift_v1"
    - "setup/verify.py check_graduation_status() also queries live for live strategies"
  artifacts:
    - path: "src/db.py"
      provides: "graduation_stats(strategy, is_paper=True) with optional is_paper filter"
      contains: "is_paper: Optional[bool] = True"
    - path: "tests/test_db_graduation.py"
      provides: "regression tests proving is_paper=False returns live counts and ignores paper"
    - path: "main.py"
      provides: "print_graduation_status() passes is_paper=False for drift strategies"
  key_links:
    - from: "main.py print_graduation_status()"
      to: "src/db.py graduation_stats()"
      via: "is_paper kwarg per strategy"
      pattern: "graduation_stats\\(strategy, is_paper="
    - from: "setup/verify.py check_graduation_status()"
      to: "src/db.py graduation_stats()"
      via: "is_paper kwarg for live strategies"
---

<objective>
Fix graduation_stats() to accept an is_paper parameter so --graduation-status shows live settled
counts for live strategies (btc_drift_v1, eth_drift_v1, sol_drift_v1) instead of paper counts.

Purpose: Currently btc_drift_v1/eth_drift_v1/sol_drift_v1 show 0/30 in graduation status because
the query is hardcoded to is_paper=1. With 7+ live bets already placed, the display is wrong and
graduation tracking is broken for live strategies.

Output: graduation_stats() with is_paper param, updated callers, regression tests.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/src/db.py
@/Users/matthewshields/Projects/polymarket-bot/tests/test_db_graduation.py
@/Users/matthewshields/Projects/polymarket-bot/main.py
@/Users/matthewshields/Projects/polymarket-bot/setup/verify.py

<interfaces>
<!-- graduation_stats() current signature (src/db.py line 447) -->
```python
def graduation_stats(self, strategy: str) -> dict:
    """
    Only counts paper trades (is_paper=1). Returns a dict with keys:
        settled_count, win_rate, brier_score, consecutive_losses,
        first_trade_ts, days_running, total_pnl_usd
    """
    # SQL hardcodes is_paper = 1 (line 463-468):
    rows = self._conn.execute(
        """SELECT result, side, win_prob, pnl_cents, timestamp
           FROM trades
           WHERE strategy = ? AND is_paper = 1 AND result IS NOT NULL
           ORDER BY timestamp ASC""",
        (strategy,),
    ).fetchall()
    # first_trade_ts query also hardcodes is_paper = 1:
    first_row = self._conn.execute(
        "SELECT MIN(timestamp) FROM trades WHERE strategy = ? AND is_paper = 1",
        (strategy,),
    ).fetchone()
```

<!-- _GRAD dict from setup/verify.py — live strategies that need is_paper=False -->
```python
_GRAD = {
    "btc_lag_v1":                   (30, 0,  0.30, 4),  # paper-only (0 signals/week)
    "eth_lag_v1":                   (30, 0,  0.30, 4),  # paper-only
    "btc_drift_v1":                 (30, 0,  0.30, 4),  # LIVE — needs is_paper=False
    "eth_drift_v1":                 (30, 0,  0.30, 4),  # LIVE — needs is_paper=False
    "orderbook_imbalance_v1":       (30, 0,  0.30, 4),  # paper-only
    "eth_orderbook_imbalance_v1":   (30, 0,  0.30, 4),  # paper-only
    "weather_forecast_v1":          (30, 0,  0.30, 4),  # paper-only
    "fomc_rate_v1":                 (5,  0,  0.30, 4),  # paper-only
}
# Note: sol_drift_v1 is LIVE but NOT in _GRAD yet — add it when updating _GRAD
```

<!-- Caller in main.py (line 1610-1611) -->
```python
for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
    stats = db.graduation_stats(strategy)
```

<!-- Caller in setup/verify.py (line 293-294) -->
```python
for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
    stats = db.graduation_stats(strategy)
```

<!-- Existing test helper in tests/test_db_graduation.py -->
```python
def _insert_trade(db: DB, strategy: str, side: str, result: str | None,
                  win_prob: float | None = None, pnl_cents: int = 0,
                  is_paper: bool = True, ts: float | None = None):
    # accepts is_paper param — can insert live trades for new tests
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add failing tests for is_paper param, then implement graduation_stats() fix</name>
  <files>tests/test_db_graduation.py, src/db.py</files>
  <behavior>
    - Test: graduation_stats(strategy, is_paper=False) returns live trade count (not paper count)
    - Test: graduation_stats(strategy, is_paper=False) ignores paper trades entirely
    - Test: graduation_stats(strategy) with no param still defaults to is_paper=True (paper only — existing behavior preserved)
    - Test: graduation_stats(strategy, is_paper=False) on empty live DB returns settled_count=0
    - Test: first_trade_ts also filters by is_paper when param is provided
  </behavior>
  <action>
    RED phase — Add new test class TestGraduationStatsIsLiveParam to tests/test_db_graduation.py:

    ```python
    class TestGraduationStatsIsLiveParam:
        def test_live_param_counts_only_live_trades(self, fresh_db):
            """is_paper=False must count live trades, ignore paper."""
            # 5 live wins
            for i in range(5):
                _insert_trade(fresh_db, "btc_drift_v1", "yes", "yes", is_paper=False)
            # 20 paper wins — must NOT be counted
            for i in range(20):
                _insert_trade(fresh_db, "btc_drift_v1", "yes", "yes", is_paper=True)

            result = fresh_db.graduation_stats("btc_drift_v1", is_paper=False)
            assert result["settled_count"] == 5

        def test_live_param_returns_correct_win_rate(self, fresh_db):
            """Win rate from live trades only."""
            # 3 live wins, 1 live loss
            for i in range(3):
                _insert_trade(fresh_db, "btc_drift_v1", "yes", "yes", is_paper=False)
            _insert_trade(fresh_db, "btc_drift_v1", "yes", "no", is_paper=False)
            # Paper loss — must not affect live win rate
            _insert_trade(fresh_db, "btc_drift_v1", "yes", "no", is_paper=True)

            result = fresh_db.graduation_stats("btc_drift_v1", is_paper=False)
            assert abs(result["win_rate"] - 0.75) < 0.01

        def test_default_is_paper_true_unchanged(self, fresh_db):
            """Calling with no is_paper arg still returns paper-only stats."""
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "yes", is_paper=False)  # live win
            _insert_trade(fresh_db, "btc_lag_v1", "yes", "no",  is_paper=True)   # paper loss

            result = fresh_db.graduation_stats("btc_lag_v1")  # default is_paper=True
            assert result["settled_count"] == 1
            assert result["win_rate"] == 0.0  # only paper loss counted

        def test_is_paper_false_empty_returns_zero(self, fresh_db):
            """is_paper=False with no live trades returns empty dict."""
            result = fresh_db.graduation_stats("btc_drift_v1", is_paper=False)
            assert result["settled_count"] == 0
            assert result["win_rate"] is None

        def test_first_trade_ts_from_live_trades_only(self, fresh_db):
            """first_trade_ts uses live trades when is_paper=False."""
            early_paper_ts = time.time() - 86400 * 30  # 30 days ago
            live_ts = time.time() - 86400 * 5           # 5 days ago

            _insert_trade(fresh_db, "btc_drift_v1", "yes", "yes",
                          is_paper=True, ts=early_paper_ts)
            _insert_trade(fresh_db, "btc_drift_v1", "yes", "yes",
                          is_paper=False, ts=live_ts)

            result = fresh_db.graduation_stats("btc_drift_v1", is_paper=False)
            assert abs(result["first_trade_ts"] - live_ts) < 1.0
    ```

    Run tests — confirm they FAIL (TypeError: graduation_stats() got unexpected keyword argument 'is_paper').

    GREEN phase — Update graduation_stats() in src/db.py:

    Change signature from:
    ```python
    def graduation_stats(self, strategy: str) -> dict:
    ```
    To:
    ```python
    def graduation_stats(self, strategy: str, is_paper: Optional[bool] = True) -> dict:
    ```

    Update the two SQL queries inside graduation_stats():
    1. Main settled trades query — replace `AND is_paper = 1` with conditional:
       ```python
       ip_filter = ""
       if is_paper is not None:
           ip_filter = f" AND is_paper = {int(is_paper)}"
       rows = self._conn.execute(
           f"""SELECT result, side, win_prob, pnl_cents, timestamp
              FROM trades
              WHERE strategy = ? {ip_filter} AND result IS NOT NULL
              ORDER BY timestamp ASC""",
           (strategy,),
       ).fetchall()
       ```
    2. first_trade_ts query — replace `AND is_paper = 1` with same conditional:
       ```python
       first_row = self._conn.execute(
           f"SELECT MIN(timestamp) FROM trades WHERE strategy = ? {ip_filter}",
           (strategy,),
       ).fetchone()
       ```

    Also update the docstring to reflect new signature:
    "When is_paper=True (default): counts paper trades only.
     When is_paper=False: counts live trades only.
     When is_paper=None: counts all trades regardless of paper/live."

    Run tests — confirm all 5 new tests pass plus all existing tests still pass.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python3 -m pytest tests/test_db_graduation.py -v 2>&1 | tail -30</automated>
  </verify>
  <done>All test_db_graduation.py tests pass (existing + 5 new). graduation_stats() accepts is_paper param.</done>
</task>

<task type="auto">
  <name>Task 2: Update callers in main.py and setup/verify.py to pass is_paper per strategy</name>
  <files>main.py, setup/verify.py</files>
  <action>
    Define the set of LIVE strategies that need is_paper=False. These are the three drift strategies
    currently in MICRO-LIVE mode. Also add sol_drift_v1 to _GRAD in setup/verify.py since it went
    live in Session 36 but was never added.

    In setup/verify.py — add sol_drift_v1 to _GRAD and define LIVE_STRATEGIES set:
    ```python
    _GRAD = {
        "btc_lag_v1":                   (30, 0,  0.30, 4),
        "eth_lag_v1":                   (30, 0,  0.30, 4),
        "btc_drift_v1":                 (30, 0,  0.30, 4),
        "eth_drift_v1":                 (30, 0,  0.30, 4),
        "sol_drift_v1":                 (30, 0,  0.30, 4),  # LIVE Session 36
        "orderbook_imbalance_v1":       (30, 0,  0.30, 4),
        "eth_orderbook_imbalance_v1":   (30, 0,  0.30, 4),
        "weather_forecast_v1":          (30, 0,  0.30, 4),
        "fomc_rate_v1":                 (5,  0,  0.30, 4),
    }

    # Strategies currently in LIVE mode — graduation checked against live trades only
    _LIVE_STRATEGIES = {"btc_drift_v1", "eth_drift_v1", "sol_drift_v1"}
    ```

    In check_graduation_status() in setup/verify.py — update the graduation_stats() call:
    ```python
    for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
        is_paper = False if strategy in _LIVE_STRATEGIES else True
        stats = db.graduation_stats(strategy, is_paper=is_paper)
    ```

    In main.py — update print_graduation_status() the same way:
    ```python
    from setup.verify import _GRAD, _LIVE_STRATEGIES  # add _LIVE_STRATEGIES to import

    # Inside the loop:
    for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
        is_paper = False if strategy in _LIVE_STRATEGIES else True
        stats = db.graduation_stats(strategy, is_paper=is_paper)
    ```

    Also update the print_graduation_status() docstring comment from "all 8 strategies" to
    "all tracked strategies" since count is now 9.

    Do NOT change any other logic in print_graduation_status() — only the import and the
    graduation_stats() call site.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python3 -m pytest tests/ -q 2>&1 | tail -5</automated>
  </verify>
  <done>
    882+ tests pass (882 existing + new graduation tests). main.py and setup/verify.py updated.
    `python main.py --graduation-status` shows live bet counts for btc_drift_v1/eth_drift_v1/sol_drift_v1
    (non-zero instead of 0/30). sol_drift_v1 now appears in _GRAD.
  </done>
</task>

</tasks>

<verification>
After both tasks complete:

1. All tests pass: `python3 -m pytest tests/ -q` — zero failures
2. Spot-check graduation output: `python main.py --graduation-status` — btc_drift_v1 row shows
   non-zero settled count (matches actual live bet count from DB), not 0/30
3. Verify sol_drift_v1 appears in graduation table (was missing before)
4. Confirm paper strategies (btc_lag_v1, weather_forecast_v1) still show paper counts unchanged
</verification>

<success_criteria>
- graduation_stats() signature: `def graduation_stats(self, strategy: str, is_paper: Optional[bool] = True) -> dict`
- 5 new regression tests in TestGraduationStatsIsLiveParam all pass
- All 882+ existing tests continue to pass (zero regressions)
- _LIVE_STRATEGIES = {"btc_drift_v1", "eth_drift_v1", "sol_drift_v1"} defined in verify.py
- sol_drift_v1 added to _GRAD in verify.py
- Both callers (main.py + setup/verify.py) use is_paper=False for live strategies
- `python main.py --graduation-status` shows correct live bet counts (not 0) for drift strategies
</success_criteria>

<output>
After completion, update .planning/STATE.md quick tasks table with:
| 8 | Fix graduation_stats() is_paper param + sol_drift_v1 in _GRAD | {date} | {commit} | .planning/quick/8-fix-graduation-stats-is-paper-param-to-s/ |

Commit message: `fix(db): add is_paper param to graduation_stats() — live strategies now show live bet counts`
</output>
