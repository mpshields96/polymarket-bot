---
phase: quick
plan: 10
type: execute
wave: 1
depends_on: []
files_modified:
  - src/strategies/crypto_daily.py
  - main.py
  - tests/test_crypto_daily.py
autonomous: true
requirements: []
must_haves:
  truths:
    - "_HOURLY_VOL is asset-specific and reflects real intraday volatility (not a single constant)"
    - "5pm EDT (21:00 UTC) slot receives priority selection over other ATM-equivalent slots"
    - "crypto_daily_loop applies loop-level direction_filter guard identical to trading_loop"
    - "985/985 tests pass after all changes"
  artifacts:
    - path: "src/strategies/crypto_daily.py"
      provides: "updated _HOURLY_VOL values, slot priority logic, per-asset vol table"
    - path: "main.py"
      provides: "crypto_daily_loop with direction_filter param"
    - path: "tests/test_crypto_daily.py"
      provides: "tests for vol constants, priority slot, direction_filter loop guard"
  key_links:
    - from: "main.py crypto_daily_loop"
      to: "signal.side direction_filter"
      via: "loop-level guard matching trading_loop pattern"
      pattern: "direction_filter is not None and signal.side != direction_filter"
    - from: "CryptoDailyStrategy._find_atm_market"
      to: "5pm EDT slot priority"
      via: "prefer markets whose close_time hour == 21 UTC when tied on ATM distance"
---

<objective>
Improve CryptoDailyStrategy signal quality: fix _HOURLY_VOL constant, add 5pm EDT slot priority
filter, and wire direction_filter into crypto_daily_loop for defense-in-depth.

Purpose: The current _HOURLY_VOL=0.005 (0.5%/sqrt-hr) makes the lognormal position signal
too sharp for ETH/SOL. The 5pm EDT slot (21:00 UTC) has highest volume and liquidity on KXBTCD —
preferring it reduces fill risk. The loop-level direction_filter guard is missing from
crypto_daily_loop (present in trading_loop) — adding it creates a safety net independent
of strategy object construction.

Output: Updated strategy + loop, new tests covering all three changes, 985/985 tests passing.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/.planning/STATE.md
@/Users/matthewshields/Projects/polymarket-bot/src/strategies/crypto_daily.py
@/Users/matthewshields/Projects/polymarket-bot/tests/test_crypto_daily.py
</context>

<interfaces>
<!-- Key types used by the executor. No codebase exploration needed. -->

From src/strategies/crypto_daily.py — current constants:
```python
_MIN_SIGNAL_PRICE_CENTS = 35
_MAX_SIGNAL_PRICE_CENTS = 65
_KALSHI_FEE_COEFF = 0.07
_HOURLY_VOL = 0.005        # ≈ 0.5% intraday vol per sqrt(hour) — TOO LOW
_DRIFT_WEIGHT = 0.7
_DRIFT_SCALE = 5.0
```

CryptoDailyStrategy.__init__ signature:
```python
def __init__(
    self,
    asset: str,            # "BTC", "ETH", or "SOL"
    series_ticker: str,
    min_drift_pct: float = 0.005,
    min_edge_pct: float = 0.04,
    min_minutes_remaining: float = 30.0,
    max_minutes_remaining: float = 360.0,
    min_volume: int = 100,
    direction_filter: Optional[str] = None,
) -> None: ...
```

_find_atm_market signature:
```python
def _find_atm_market(self, markets: List[Market], spot: float) -> Optional[Market]: ...
# Currently: sorts candidates by abs(mid - 50.0), returns candidates[0][1]
```

_model_prob — uses _HOURLY_VOL:
```python
sigma = _HOURLY_VOL * math.sqrt(hours_to_settle)
```

From main.py — trading_loop direction_filter guard (lines 291-296):
```python
if direction_filter is not None and signal.side != direction_filter:
    logger.debug(
        "[%s] Direction filter active: skipping %s signal (only %s allowed)",
        loop_name, signal.side, direction_filter,
    )
    continue
```

From main.py — crypto_daily_loop current signature (no direction_filter param):
```python
async def crypto_daily_loop(
    kalshi,
    asset_feed,
    strategy,
    kill_switch,
    db,
    loop_name: str = "btc_daily",
    initial_delay_sec: float = 0.0,
    max_daily_bets: int = 5,
):
```

From main.py — crypto_daily_loop call sites (lines 2795-2833):
```python
btc_daily_task = asyncio.create_task(
    crypto_daily_loop(
        kalshi=kalshi, asset_feed=btc_feed, strategy=btc_daily_strategy,
        kill_switch=kill_switch, db=db,
        loop_name="btc_daily", initial_delay_sec=90.0, max_daily_bets=5,
    ), name="btc_daily_loop"
)
# eth_daily_task and sol_daily_task follow same pattern
```

Market dataclass (src/platforms/kalshi.py):
```python
@dataclass
class Market:
    ticker: str
    close_time: str   # ISO format "2026-03-11T21:00:00Z"
    yes_price: int    # bid in cents
    volume: int
    raw: dict         # contains "yes_ask"
    ...
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Fix _HOURLY_VOL + add 5pm EDT slot priority</name>
  <files>src/strategies/crypto_daily.py, tests/test_crypto_daily.py</files>
  <behavior>
    - Test 1: _hourly_vol_for("BTC") returns 0.01 (1% per sqrt-hour)
    - Test 2: _hourly_vol_for("ETH") returns 0.015 (1.5% per sqrt-hour — ETH ~50% more volatile)
    - Test 3: _hourly_vol_for("SOL") returns 0.025 (2.5% per sqrt-hour — SOL ~2.5x more volatile)
    - Test 4: _hourly_vol_for("XYZ") returns 0.01 (default fallback)
    - Test 5: _model_prob uses self.asset's vol, not the global constant — verify BTC sigma at 2hr is ~0.01*sqrt(2)=0.0141
    - Test 6: When two candidates tie on ATM distance (both within 1¢ of 50), prefer the one whose close_time hour == 21 (UTC, = 5pm EDT)
    - Test 7: When no 21:00 UTC slot available, normal ATM selection applies (no regression)
    - Test 8: Priority slot logic does NOT override price guard or time window filters
  </behavior>
  <action>
    RED — Write the 8 failing tests first in tests/test_crypto_daily.py. Add a new
    class TestHourlyVolConstants and extend TestATMSelection with priority slot tests.
    Confirm all 8 tests fail before touching production code.

    GREEN — Update src/strategies/crypto_daily.py:

    1. Remove the module-level _HOURLY_VOL = 0.005 constant.

    2. Add a per-asset vol lookup dict at module level:
       _HOURLY_VOL_BY_ASSET: dict[str, float] = {
           "BTC": 0.01,   # 1% per sqrt-hour (annualized ~85%)
           "ETH": 0.015,  # 1.5% per sqrt-hour (ETH ~50% more volatile than BTC)
           "SOL": 0.025,  # 2.5% per sqrt-hour (SOL ~2-3x BTC volatility)
       }
       _HOURLY_VOL_DEFAULT = 0.01

    3. Add module-level helper:
       def _hourly_vol_for(asset: str) -> float:
           return _HOURLY_VOL_BY_ASSET.get(asset.upper(), _HOURLY_VOL_DEFAULT)

    4. In CryptoDailyStrategy._model_prob(), replace:
           sigma = _HOURLY_VOL * math.sqrt(hours_to_settle)
       with:
           sigma = _hourly_vol_for(self.asset) * math.sqrt(hours_to_settle)

    5. In CryptoDailyStrategy._find_atm_market(), after sorting candidates by
       abs(mid - 50.0), add 5pm EDT priority. The 21:00 UTC close slot is the US
       equities close — highest volume and tightest spreads on KXBTCD. Logic:

       After building the sorted candidates list (sorted by ATM distance), pick
       the priority slot if one exists among the top candidates that are within
       2¢ of the best ATM distance. Specifically:

       a. Find best_dist = candidates[0][0]
       b. Collect top_tier = [(dist, mkt) for dist, mkt in candidates if dist <= best_dist + 2.0]
       c. From top_tier, prefer any market where close_dt.hour == 21 (UTC):
          priority = [m for _, m in top_tier if datetime.fromisoformat(...).hour == 21]
          if priority: return priority[0]
          else: return candidates[0][1]

       Note: The datetime parse for priority check is cheap — already done in the
       candidate building loop. Cache parsed close_dt alongside the Market to avoid
       re-parsing. Refactor _find_atm_market to store (dist, close_dt, mkt) tuples.

    Do NOT change any other constants, thresholds, or behaviors. Paper-only, no live promotion.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/test_crypto_daily.py -v -x 2>&1 | tail -20</automated>
  </verify>
  <done>All 8 new tests pass. No regression in existing 30 TestATMSelection/TestSignalDirection/TestSignalContents/TestEdgeCalculation/TestModelProbability/TestPriceGuard/TestAssetCoverage/TestDirectionFilter tests. _model_prob uses asset-specific vol.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add direction_filter param to crypto_daily_loop</name>
  <files>main.py, tests/test_crypto_daily.py</files>
  <behavior>
    - Test 1: crypto_daily_loop with direction_filter="no" skips a "yes" signal from strategy
      (even if strategy itself would emit it — defense-in-depth)
    - Test 2: crypto_daily_loop with direction_filter=None passes both "yes" and "no" signals through
    - Test 3: crypto_daily_loop with direction_filter="yes" skips a "no" signal
    - Test 4: Loop logs DEBUG message when direction_filter blocks a signal (same format as trading_loop)
  </behavior>
  <action>
    RED — Add class TestCryptoDailyLoopDirectionFilter in tests/test_crypto_daily.py.
    These tests must mock the loop's internals (strategy.generate_signal, db, kill_switch,
    paper_exec) and verify the direction_filter guard fires. Since crypto_daily_loop is async,
    use pytest-asyncio or test the guard logic unit-style by extracting a helper if needed.
    Simpler approach: test the filtering condition directly as a unit test of the guard logic
    (confirm the side != direction_filter branch blocks correctly), since the full async loop
    is hard to test in isolation.

    Specifically, write tests that call generate_signal on a real CryptoDailyStrategy,
    then simulate what the loop does: if signal.side != direction_filter → blocked.
    Assert the condition is True/False as expected.

    GREEN — Update main.py crypto_daily_loop:

    1. Add direction_filter: Optional[str] = None to the function signature (after max_daily_bets).

    2. After the signal is generated (after line "if signal is None: continue"), add the guard
       block matching trading_loop exactly:

       if direction_filter is not None and signal.side != direction_filter:
           logger.debug(
               "[%s] Direction filter active: skipping %s signal (only %s allowed)",
               loop_name, signal.side, direction_filter,
           )
           await asyncio.sleep(CRYPTO_DAILY_POLL_INTERVAL_SEC)
           continue

    3. Update the btc_daily_task call site to pass direction_filter="no":
       crypto_daily_loop(
           ...,
           direction_filter="no",   # add this line (defense-in-depth, strategy already filters)
       )
       eth_daily and sol_daily remain direction_filter=None (default).

    4. Update the type annotation import at top of crypto_daily_loop if Optional not imported
       (it's already in scope in main.py via "from typing import Optional").

    Important: The btc_daily_strategy is already constructed with direction_filter="no" in
    main.py (line 2464), so the strategy-level guard already works. The loop-level guard is
    defense-in-depth only — it does NOT change any behavior for current config, but protects
    against a future misconfiguration where strategy is instantiated without the filter.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/ -v -x -q 2>&1 | tail -25</automated>
  </verify>
  <done>
    985/985 tests pass (or prior count + new tests). crypto_daily_loop signature has
    direction_filter param. btc_daily_task call passes direction_filter="no". Guard logic
    matches trading_loop pattern exactly. `python -m pytest tests/ -v` exits 0.
  </done>
</task>

</tasks>

<verification>
After both tasks:
1. `source venv/bin/activate && python -m pytest tests/ -v -q` — all tests pass (new count = prior 985 + new tests)
2. `python -c "from src.strategies.crypto_daily import _hourly_vol_for, CryptoDailyStrategy; print(_hourly_vol_for('BTC'), _hourly_vol_for('ETH'), _hourly_vol_for('SOL'))"` → prints `0.01 0.015 0.025`
3. `grep "direction_filter" main.py | grep "crypto_daily_loop"` — shows param in signature and btc_daily call
4. `grep "_HOURLY_VOL\b" src/strategies/crypto_daily.py` — module-level constant gone, only dict + helper remain
</verification>

<success_criteria>
- _HOURLY_VOL module-level constant removed; replaced with _HOURLY_VOL_BY_ASSET dict and _hourly_vol_for() helper
- _model_prob uses _hourly_vol_for(self.asset) — BTC=0.01, ETH=0.015, SOL=0.025
- _find_atm_market prefers 21:00 UTC close slot when tied within 2¢ of best ATM distance
- crypto_daily_loop has direction_filter=None param; guard inserted after signal generation
- btc_daily_task call passes direction_filter="no"
- All 985+ tests pass; no regressions
- Paper-only — no live promotion changes made
</success_criteria>

<output>
After completion, create `.planning/quick/10-improve-cryptodailystrategy-signal-quali/10-SUMMARY.md`
with: what was changed, test count before/after, any decisions made during implementation.
</output>
