---
phase: quick
plan: 3
type: tdd
wave: 1
depends_on: []
files_modified:
  - src/strategies/unemployment_rate.py
  - src/data/fred.py
  - tests/test_unemployment_strategy.py
  - config.yaml
  - main.py
autonomous: true
requirements: []

must_haves:
  truths:
    - "FREDSnapshot has unrate_latest and unrate_prior fields without breaking existing fields"
    - "UnemploymentRateStrategy.generate_signal() skips outside the 7-day BLS window and returns Signal inside it"
    - "Linear trend extrapolation from 3 UNRATE readings produces model P(YES) via normal CDF"
    - "unemployment_loop() runs in main.py at 58s stagger with KXUNRATE series ticker"
    - "All 346+ existing tests continue to pass alongside new unemployment tests"
  artifacts:
    - path: "src/strategies/unemployment_rate.py"
      provides: "UnemploymentRateStrategy + BLS_RELEASE_DATES_2026 + compute_unrate_model_prob + load_from_config"
    - path: "src/data/fred.py"
      provides: "FREDSnapshot extended with unrate_latest + unrate_prior (backward-compatible)"
    - path: "tests/test_unemployment_strategy.py"
      provides: "Full TDD test suite — no live HTTP calls"
    - path: "config.yaml"
      provides: "strategy.unemployment section with series_ticker, days_before_release, min_edge_pct"
    - path: "main.py"
      provides: "unemployment_loop() + asyncio task at stagger 58s"
  key_links:
    - from: "src/data/fred.py FREDFeed.refresh()"
      to: "src/data/fred.py FREDSnapshot.unrate_latest"
      via: "_fetch_last_n('UNRATE', 3)"
      pattern: "unrate_latest"
    - from: "src/strategies/unemployment_rate.py"
      to: "src/data/fred.py FREDSnapshot"
      via: "snap.unrate_latest, snap.unrate_prior"
      pattern: "snap\\.unrate"
    - from: "main.py unemployment_loop()"
      to: "src/strategies/unemployment_rate.py"
      via: "generate_signal(market, orderbook, None)"
      pattern: "unemployment_loop"
---

<objective>
Add unemployment_rate_v1 as the 9th trading loop.

Purpose: Exploit Kalshi KXUNRATE markets by comparing BLS Employment Situation forecasts
(linear trend on last 3 UNRATE readings + ±0.2pp uncertainty band → normal CDF probability)
to market prices. Active in the 7-day window before each monthly BLS release.
Output: strategy file, FREDSnapshot extension, test suite, config section, main.py loop.
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/src/strategies/fomc_rate.py
@/Users/matthewshields/Projects/polymarket-bot/src/data/fred.py
@/Users/matthewshields/Projects/polymarket-bot/config.yaml
</context>

<interfaces>
<!-- Exact contracts the executor uses. No codebase exploration needed. -->

From src/data/fred.py — FREDSnapshot (current fields, ADD unrate_* below these):
```python
@dataclass
class FREDSnapshot:
    fed_funds_rate: float       # DFF
    yield_2yr: float            # DGS2
    cpi_latest: float           # CPIAUCSL latest
    cpi_prior: float            # CPIAUCSL prior month
    cpi_prior2: float           # CPIAUCSL 2 months ago
    fetched_at: datetime        # UTC timestamp
    # ADD (with defaults so existing callers don't break):
    unrate_latest: float = 0.0  # UNRATE: most recent reading (e.g. 4.3)
    unrate_prior: float = 0.0   # UNRATE: one reading before latest (e.g. 4.4)
    unrate_prior2: float = 0.0  # UNRATE: two readings before latest (e.g. 4.5)
```

From src/data/fred.py — FREDFeed.refresh() (add UNRATE fetch here):
```python
def refresh(self) -> bool:
    dff = self._fetch_latest("DFF")
    dgs2 = self._fetch_latest("DGS2")
    cpi_rows = self._fetch_last_n("CPIAUCSL", 3)
    # ADD:
    unrate_rows = self._fetch_last_n("UNRATE", 3)
    # unrate_rows may be [] on network error — use 0.0 defaults, don't fail
```

From src/strategies/fomc_rate.py — the exact pattern to replicate:
```python
class FOMCRateStrategy(BaseStrategy):
    def __init__(self, fred_feed, min_edge_pct, min_minutes_remaining, days_before_meeting, ...): ...
    @property
    def name(self) -> str: return "fomc_rate_v1"
    def generate_signal(self, market, orderbook, btc_feed) -> Optional[Signal]: ...

def load_from_config() -> FOMCRateStrategy: ...
```

From main.py — fomc_loop() pattern (replicate exactly for unemployment_loop):
```python
FOMC_POLL_INTERVAL_SEC = 1800   # 30 min
# unemployment uses same 1800s poll or define UNEMPLOYMENT_POLL_INTERVAL_SEC = 1800

async def fomc_loop(kalshi, fomc_strategy, fred_feed, kill_switch, db,
                    series_ticker="KXFEDDECISION", loop_name="fomc",
                    initial_delay_sec=51.0, max_daily_bets=5): ...
# Replicate as:
async def unemployment_loop(kalshi, unemployment_strategy, fred_feed, kill_switch, db,
                            series_ticker="KXUNRATE", loop_name="unemployment",
                            initial_delay_sec=58.0, max_daily_bets=5): ...
```

From main.py — fomc task creation (replicate at stagger 58s):
```python
fomc_task = asyncio.create_task(
    fomc_loop(kalshi=kalshi, fomc_strategy=fomc_strategy, fred_feed=fred_feed,
              kill_switch=kill_switch, db=db, series_ticker="KXFEDDECISION",
              loop_name="fomc", initial_delay_sec=51.0, max_daily_bets=max_daily_bets),
    name="fomc_loop",
)
# ADD after fomc_task:
unemployment_task = asyncio.create_task(
    unemployment_loop(kalshi=kalshi, unemployment_strategy=unemployment_strategy,
                      fred_feed=fred_feed, kill_switch=kill_switch, db=db,
                      series_ticker=unrate_series, loop_name="unemployment",
                      initial_delay_sec=58.0, max_daily_bets=max_daily_bets),
    name="unemployment_loop",
)
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend FREDSnapshot + write UnemploymentRateStrategy (TDD)</name>
  <files>
    src/data/fred.py
    src/strategies/unemployment_rate.py
    tests/test_unemployment_strategy.py
  </files>
  <behavior>
    RED phase — write tests/test_unemployment_strategy.py first, then run, confirm all fail:

    Test group A — FREDSnapshot backward compat:
    - Existing FREDSnapshot(fed_funds_rate=3.64, yield_2yr=3.90, cpi_latest=320.0,
      cpi_prior=319.5, cpi_prior2=319.0, fetched_at=...) still constructs without error
    - snap.unrate_latest == 0.0 by default
    - snap.unrate_prior == 0.0 by default

    Test group B — FREDSnapshot with UNRATE:
    - FREDSnapshot(..., unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5)
    - snap.unrate_trend == -0.1 (linear slope: (4.3-4.5)/2 = -0.1)
    - snap.unrate_forecast == 4.3 + (-0.1) == 4.2 (extrapolate one step)

    Test group C — BLS window helpers:
    - next_bls_date(today=date(2026, 2, 28)) == date(2026, 3, 7)
    - next_bls_date(today=date(2026, 3, 7)) == date(2026, 3, 7)  # on release day
    - next_bls_date(today=date(2026, 3, 8)) == date(2026, 4, 3)  # next month
    - days_until_bls(today=date(2026, 2, 28)) == 7
    - days_until_bls(today=date(2026, 12, 31)) == None  # no 2026 dates left

    Test group D — compute_unrate_model_prob:
    - With unrate_latest=4.3, unrate_prior=4.4, unrate_prior2=4.5 (trend=-0.1):
      forecast=4.2, uncertainty=0.2
      market_threshold=4.0 (a KXUNRATE-YYYYMM-4.0 market)
      P(actual > 4.0) = 1 - norm.cdf((4.0 - 4.2) / 0.2) ≈ 0.841 (YES bet: rate above threshold)
    - With flat trend (all same): forecast = latest, P calculated from that
    - Returns float in [0, 1]

    Test group E — UnemploymentRateStrategy.generate_signal():
    - Returns None when days_until_bls > days_before_release (window gate)
    - Returns None when FRED feed is stale
    - Returns None when snap is None
    - Returns None when ticker does not match KXUNRATE pattern
    - Returns None when edge_yes < min_edge_pct AND edge_no < min_edge_pct
    - Returns Signal(side="yes") when model_prob_yes >> market yes_price/100 + fee
    - Returns Signal(side="no") when (1-model_prob_yes) >> market no_price/100 + fee
    - Signal.ticker matches market.ticker
    - Signal.reason contains "BLS" and days-until-release

    Test group F — load_from_config:
    - Returns UnemploymentRateStrategy instance
    - Uses fred_feed (shared FREDFeed — no second feed instance needed)

    GREEN phase — implement src/data/fred.py + src/strategies/unemployment_rate.py.
  </behavior>
  <action>
    RED: Write tests/test_unemployment_strategy.py covering all groups above. Use MagicMock
    for FREDFeed and Market (same pattern as tests/test_fomc_strategy.py). No live HTTP.

    Run: source venv/bin/activate && python -m pytest tests/test_unemployment_strategy.py -v
    Confirm ALL new tests fail (ImportError or assertion failures). That is the red state.

    GREEN — implement in two files:

    1. src/data/fred.py — extend FREDSnapshot:
       - Add three fields with defaults: unrate_latest: float = 0.0, unrate_prior: float = 0.0,
         unrate_prior2: float = 0.0
       - Add computed properties: unrate_trend (linear slope), unrate_forecast (extrapolate 1 step)
         unrate_trend = (unrate_latest - unrate_prior2) / 2.0 (rise/run over 2 intervals)
         unrate_forecast = unrate_latest + unrate_trend
       - In FREDFeed.refresh(): add `unrate_rows = self._fetch_last_n("UNRATE", 3)` (after cpi_rows)
         If len(unrate_rows) >= 3: set unrate_latest/prior/prior2 from rows[0]/[1]/[2]
         Else: use defaults 0.0 — do NOT fail the whole refresh if UNRATE unavailable
       - Update FREDSnapshot constructor call in refresh() to pass unrate_* kwargs

    2. src/strategies/unemployment_rate.py — new file, pattern = fomc_rate.py exactly:
       - Module docstring: same format as fomc_rate.py (JOB, SIGNAL MODEL, KALSHI MARKET STRUCTURE, TIMING)
       - BLS_RELEASE_DATES_2026: list[date] — all 12 BLS Employment Situation release dates:
         Jan 9, Feb 7, Mar 7, Apr 3, May 1, Jun 5, Jul 3, Aug 7, Sep 4, Oct 2, Nov 6, Dec 4
       - next_bls_date(today=None) -> Optional[date]: return next date >= today (or None if none left)
       - days_until_bls(today=None) -> Optional[int]: return days to next BLS release (or None)
       - parse_unrate_ticker(ticker: str) -> Optional[float]:
         Regex: KXUNRATE-\d{6}-(\d+\.\d+) → extract threshold float
         e.g. KXUNRATE-202503-4.0 → 4.0
         Returns None if no match
       - compute_unrate_model_prob(snap, uncertainty_band=0.2) -> float:
         Uses scipy.stats.norm.cdf (already in venv — check: python -c "import scipy; print(scipy.__version__)")
         forecast = snap.unrate_forecast
         For a given market_threshold (passed as arg): P(YES) = 1 - norm.cdf((threshold - forecast) / uncertainty_band)
         NOTE: this function takes threshold as a param — strategy calls it per market
         Signature: compute_unrate_model_prob(snap, threshold, uncertainty_band=0.2) -> float
       - _DEFAULT_MIN_EDGE_PCT = 0.05
       - _DEFAULT_MIN_MINUTES_REMAINING = 60.0
       - _DEFAULT_DAYS_BEFORE_RELEASE = 7
       - _DEFAULT_UNCERTAINTY_BAND = 0.2   # ±0.2pp uncertainty band
       - _kalshi_fee_pct(price_cents): same formula as fomc_rate.py
       - class UnemploymentRateStrategy(BaseStrategy): same __init__ pattern as FOMCRateStrategy
         @property name: return "unemployment_rate_v1"
         generate_signal(self, market, orderbook, btc_feed) -> Optional[Signal]:
           Gate 1: days_until_bls check (window gate — skip if outside days_before_release)
           Gate 2: fred stale check
           Gate 3: snap is None check
           Gate 4: parse_unrate_ticker(market.ticker) → threshold float (skip if None)
           Gate 5: minutes_remaining check (skip if < min_minutes_remaining)
           Compute: model_prob_yes = compute_unrate_model_prob(snap, threshold, self._uncertainty_band)
           Edge calc: same as fomc_rate.py (edge_yes, edge_no, fee)
           If no edge: log INFO with "[unemployment] ... skip" and return None
           Signal reason: "BLS {days_away}d away | unrate_forecast={snap.unrate_forecast:.2f}% ..."
       - load_from_config() -> UnemploymentRateStrategy: reads config.yaml strategy.unemployment section
         Shares the existing FREDFeed (import load_from_config from src.data.fred)

    IMPORTANT: scipy may not be installed. Check first:
      source venv/bin/activate && python -c "from scipy.stats import norm; print('ok')"
    If not installed: pip install scipy
    If scipy unavailable, implement norm.cdf manually using math.erfc:
      norm_cdf(x) = 0.5 * math.erfc(-x / math.sqrt(2))
    Use the math implementation unconditionally (no scipy dependency = fewer requirements).

    Run all tests: source venv/bin/activate && python -m pytest tests/ -v
    All 346 existing + new unemployment tests must pass.
  </action>
  <verify>
    <automated>source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest /Users/matthewshields/Projects/polymarket-bot/tests/test_unemployment_strategy.py /Users/matthewshields/Projects/polymarket-bot/tests/test_fomc_strategy.py -v 2>&1 | tail -20</automated>
  </verify>
  <done>
    - tests/test_unemployment_strategy.py exists with all 6 test groups
    - FREDSnapshot has unrate_latest, unrate_prior, unrate_prior2 with defaults (backward-compat)
    - FREDSnapshot.unrate_trend and .unrate_forecast properties work correctly
    - FREDFeed.refresh() fetches UNRATE but does not fail if UNRATE unavailable
    - UnemploymentRateStrategy.generate_signal() returns Signal only inside BLS window with sufficient edge
    - All existing FOMC tests still pass (no regression in FREDSnapshot)
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire unemployment_loop into main.py + add config.yaml section</name>
  <files>
    config.yaml
    main.py
  </files>
  <action>
    config.yaml — add unemployment section under strategy (after fomc block, before whale_copy):

    ```yaml
      unemployment:
        # Unemployment rate vs Kalshi KXUNRATE market strategy — paper-only.
        # Compares BLS Employment Situation forecast (linear trend on last 3 UNRATE readings)
        # to Kalshi KXUNRATE market prices. Active 7 days before each monthly BLS release.
        # Data: FRED CSV UNRATE series (free, no API key).
        # BLS 2026 release dates: Jan 9, Feb 7, Mar 7, Apr 3, May 1, Jun 5, Jul 3, Aug 7, Sep 4, Oct 2, Nov 6, Dec 4
        series_ticker: KXUNRATE          # Kalshi unemployment rate series prefix
        days_before_release: 7           # Active window: 7 days before each BLS release
        min_edge_pct: 0.05               # 5% net edge required after Kalshi fee
        min_minutes_remaining: 60.0      # Don't enter with < 60 min left in market window
        uncertainty_band: 0.2            # ±0.2pp normal distribution width for forecast
        fred_refresh_interval_seconds: 3600   # Reuse shared FRED feed interval
    ```

    main.py — four changes:

    1. Import at top of "Initialize components" block (after fomc_strategy_load import):
       ```python
       from src.strategies.unemployment_rate import load_from_config as unemployment_strategy_load
       ```

    2. Instantiate strategy (after fomc_strategy = fomc_strategy_load()):
       ```python
       unemployment_strategy = unemployment_strategy_load()
       logger.info("Strategy loaded: %s (paper-only BLS unemployment, fires ~12x/year)", unemployment_strategy.name)
       ```

    3. Add UNEMPLOYMENT_POLL_INTERVAL_SEC constant near FOMC_POLL_INTERVAL_SEC (line ~381):
       ```python
       UNEMPLOYMENT_POLL_INTERVAL_SEC = 1800   # 30 min — KXUNRATE markets don't move every second
       ```

    4. Add unemployment_loop() function (immediately after fomc_loop() definition, before settlement_loop):
       Copy fomc_loop() exactly. Change:
       - Function name: unemployment_loop
       - Param name: unemployment_strategy (not fomc_strategy)
       - Default series_ticker: "KXUNRATE"
       - Default loop_name: "unemployment"
       - Default initial_delay_sec: 58.0
       - POLL constant: UNEMPLOYMENT_POLL_INTERVAL_SEC (not FOMC_POLL_INTERVAL_SEC)
       - strategy_name param to PaperExecutor: unemployment_strategy.name
       - Heartbeat log: reference snap.unrate_forecast if snap is not None
         Format: "[unemployment] Evaluating {N} KXUNRATE market(s) | forecast={snap.unrate_forecast:.2f}%"
       - config re-read for slippage in loop body: same pattern as fomc_loop (re-read yaml for _fslip)
       - generate_signal call: unemployment_strategy.generate_signal(market, orderbook, None)

    5. Add asyncio task creation (immediately after fomc_task = asyncio.create_task(...)):
       ```python
       # Unemployment rate: paper-only, polls every 30 min, stagger 58s
       unrate_series = config.get("strategy", {}).get("unemployment", {}).get("series_ticker", "KXUNRATE")
       unemployment_task = asyncio.create_task(
           unemployment_loop(
               kalshi=kalshi,
               unemployment_strategy=unemployment_strategy,
               fred_feed=fred_feed,
               kill_switch=kill_switch,
               db=db,
               series_ticker=unrate_series,
               loop_name="unemployment",
               initial_delay_sec=58.0,
               max_daily_bets=max_daily_bets,
           ),
           name="unemployment_loop",
       )
       ```

    6. Add unemployment_task to the gather/wait block where other tasks are collected.
       Find the list of tasks passed to asyncio.gather() or asyncio.wait() and add unemployment_task.
       CRITICAL: `config` is NOT in scope inside unemployment_loop — do NOT read config inside the loop.
       The slippage_ticks value must be re-read from YAML inside the loop body (same pattern as fomc_loop
       which does `import yaml as _yaml; with open(...) as _f: _fcfg = yaml.safe_load(_f); _fslip = ...`).
  </action>
  <verify>
    <automated>source /Users/matthewshields/Projects/polymarket-bot/venv/bin/activate && python -m pytest /Users/matthewshields/Projects/polymarket-bot/tests/ -v 2>&1 | tail -5</automated>
  </verify>
  <done>
    - config.yaml has strategy.unemployment section with all params
    - main.py imports unemployment_strategy_load
    - UNEMPLOYMENT_POLL_INTERVAL_SEC constant defined
    - unemployment_loop() function defined following fomc_loop pattern exactly
    - asyncio task created at 58s stagger with name="unemployment_loop"
    - unemployment_task included in task gather/wait
    - All existing 346+ tests still pass (no regressions)
    - `python -c "import main" 2>&1` shows no import errors
  </done>
</task>

</tasks>

<verification>
Run full test suite: source venv/bin/activate && python -m pytest tests/ -v
Count must be >= 346 (new unemployment tests added).
Syntax check: python -c "import src.strategies.unemployment_rate; import src.data.fred; print('ok')"
Import check: python -c "import main" (no errors)
</verification>

<success_criteria>
- src/strategies/unemployment_rate.py exists with UnemploymentRateStrategy, BLS_RELEASE_DATES_2026,
  next_bls_date(), days_until_bls(), parse_unrate_ticker(), compute_unrate_model_prob(), load_from_config()
- FREDSnapshot has unrate_latest/prior/prior2 fields with 0.0 defaults (backward-compatible)
- FREDFeed.refresh() fetches UNRATE without breaking on network failure
- tests/test_unemployment_strategy.py has 20+ tests covering all behavior groups
- config.yaml strategy.unemployment section present
- main.py has unemployment_loop() + asyncio task at stagger 58s
- All 346 original tests still pass + new unemployment tests pass
- Strategy is paper-only — fires in 7-day window before each BLS monthly release (next: Mar 7, 2026)
</success_criteria>

<output>
After completion, update /Users/matthewshields/Projects/polymarket-bot/.planning/STATE.md:
- Add quick task 3 to the Quick Tasks Completed table
- Update test count (346 → new count)
- Note: 9th strategy loop added (unemployment_rate_v1)
</output>
