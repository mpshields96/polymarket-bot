---
phase: quick
plan: 4
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/log_backtest.py
  - scripts/real_backtest_results.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "Script parses all btc_lag log lines from sessions 20-25 and extracts BTC move%, YES cents, NO cents, minutes remaining"
    - "Each evaluation is associated with a market ticker (from nearest preceding [trading] Evaluating line)"
    - "Script pulls Binance 1-min klines for each unique 15-min window and determines actual settlement outcome"
    - "Threshold sweep across 0.20%, 0.30%, 0.40%, 0.50% reports: signal count, actual Kalshi price distribution, and directional accuracy"
    - "Output written to scripts/real_backtest_results.md and printed to stdout"
  artifacts:
    - path: "scripts/log_backtest.py"
      provides: "Log-mining calibration backtest script"
      min_lines: 200
    - path: "scripts/real_backtest_results.md"
      provides: "Backtest results using real Kalshi prices"
  key_links:
    - from: "scripts/log_backtest.py"
      to: "Binance.US REST API"
      via: "aiohttp fetch of 1-min BTCUSDT klines"
      pattern: "api.binance.us/api/v3/klines"
    - from: "log_backtest.py parser"
      to: "threshold sweep reporter"
      via: "List[EvalRecord] dataclass passed to analyze_threshold()"
---

<objective>
Build scripts/log_backtest.py — a calibration backtest that mines real bot log data instead of assuming Kalshi is always at 50¢.

Purpose: The existing backtest.py is blind to actual Kalshi prices. When btc_lag fires in live trading, HFTs may have already moved the market. This script answers the real question: at the actual YES/NO prices the bot observed, did those evaluations have a genuine edge, and at which BTC move threshold?

Output: scripts/log_backtest.py (new file, standalone script) + scripts/real_backtest_results.md (saved results).
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/.planning/STATE.md
@/Users/matthewshields/Projects/polymarket-bot/scripts/backtest.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build log_backtest.py — parser, Binance fetcher, threshold sweep, reporter</name>
  <files>scripts/log_backtest.py</files>
  <action>
Create scripts/log_backtest.py as a standalone async script. Do NOT modify backtest.py or any src/ file.

The script has four logical sections:

**Section 1 — Log parsing**

Parse all four session log files (hard-code their paths as a list, with a fallback to glob /tmp/polybot_session*.log):
- /tmp/polybot_session20.log
- /tmp/polybot_session21.log
- /tmp/polybot_session24.log
- /tmp/polybot_session25.log

Log timestamps have no date prefix (format: `HH:MM:SS INFO ...`). Use the file's mtime (os.path.getmtime) as the anchor date. Lines that cross midnight must be detected: if a line's HH:MM:SS is earlier than the previous line's, increment the date by one day.

Two line patterns to extract:

Pattern A — ticker context lines:
```
HH:MM:SS INFO     main | [trading] Evaluating N market(s): ['KXBTC15M-26MAR011145-45']
```
Extract: timestamp, ticker string (e.g. `KXBTC15M-26MAR011145-45`)

Pattern B — btc_lag evaluation lines:
```
HH:MM:SS INFO     src.strategies.btc_lag | [btc_lag] BTC +0.154% (need ±0.40%) | YES=51¢ NO=47¢ | 7.3min left
```
Extract: timestamp, btc_move_pct (signed float), yes_cents (int), no_cents (int), minutes_remaining (float)

Association rule: For each Pattern B line, the ticker is the most recent Pattern A ticker seen before it in the same log file. If no Pattern A line precedes it, ticker is None (skip the record).

Exclusion rules applied during parsing (not after):
- Skip if yes_cents == 0 or no_cents == 0 (near-settlement, bad price)
- Skip if minutes_remaining < 3.0

Store as a list of EvalRecord dataclass:
```python
@dataclass
class EvalRecord:
    log_file: str           # which log file
    timestamp: datetime     # full UTC datetime reconstructed
    ticker: str             # e.g. KXBTC15M-26MAR011145-45
    btc_move_pct: float     # signed, e.g. +0.154 or -0.203
    yes_cents: int          # actual Kalshi YES price
    no_cents: int           # actual Kalshi NO price
    minutes_remaining: float
    # Filled in later:
    window_open_ms: int = 0
    window_close_ms: int = 0
    settlement: Optional[int] = None  # 1=YES won, 0=NO won, None=unavailable
```

**Section 2 — Ticker parsing and Binance fetch**

Ticker format: `KXBTC15M-26MAR011145-45`
- Year: 20XX where XX is the two-digit year (`26` → 2026)
- Month: three-letter abbreviation (`MAR` → 3)
- Day: two digits (`01`)
- Time: four digits HHMM (`1145` → 11:45 UTC)
- The `-45` suffix is the strike price in cents, ignore it.

Parse each unique ticker into a UTC window_open datetime. window_close = window_open + 15 minutes.

Build a set of unique (window_open_ms, window_close_ms) pairs. For each unique pair, check if Binance data covers the window. Only fetch Binance if the window_open is more than 16 minutes in the past (can't determine settlement of an open window).

Binance fetch: reuse the _fetch_klines_chunk pattern from backtest.py verbatim (same URL, same params, same error handling). Fetch 1-min klines for each unique window. Cache results: fetch all minutes from the earliest window_open to the latest window_close in a single batched call (batch by 1000-candle chunks, same approach as fetch_all_klines in backtest.py).

Settlement: window open candle close price is the reference. Window close candle close price determines outcome. If BTC close > open reference: YES wins (settlement=1). If BTC close < open reference: settlement=0. If exact candle missing, use _price_at with 90-second tolerance. If neither candle available: settlement=None, skip this record.

Fill window_open_ms, window_close_ms, settlement into each EvalRecord.

**Section 3 — Threshold sweep**

Thresholds to sweep: [0.20, 0.30, 0.40, 0.50] (abs(btc_move_pct) must meet threshold to "fire").

For each threshold, among records with settlement is not None:
- `fired` = records where abs(btc_move_pct) >= threshold
- For each fired record, determine signal_side: "yes" if btc_move_pct > 0 else "no"
- `correct` = fired records where signal_side == ("yes" if settlement==1 else "no")
- directional_accuracy = correct / fired if fired else 0
- yes_prices_at_signal = [r.yes_cents for r in fired] (actual Kalshi prices at evaluation moment)
- Report: mean, median, p25, p75 of yes_prices_at_signal using statistics.quantiles
- Also compute: what edge would we have gotten using actual price vs the 50¢ assumption?
  For a YES signal: actual_edge = (1.0 - yes_cents/100) * directional_accuracy - (yes_cents/100) * (1-directional_accuracy) - _lag_fee_pct(yes_cents)
  For a NO signal: actual_edge = (1.0 - no_cents/100) * directional_accuracy - (no_cents/100) * (1-directional_accuracy) - _lag_fee_pct(100 - no_cents)
  Compute a mean_actual_edge across all fired records.

_lag_fee_pct: copy the exact formula from backtest.py: `0.07 * p * (1.0 - p)` where p = price_cents / 100.0

**Section 4 — Reporter**

Print to stdout and write to scripts/real_backtest_results.md.

Output format:

```
============================================================
  LOG-CALIBRATED BACKTEST — btc_lag_v1
  Source: 4 session logs, N evaluation lines parsed
  Filters: YES/NO > 0¢, >= 3.0 min remaining, ticker matched
  Date range: YYYY-MM-DD to YYYY-MM-DD
============================================================

  Total evaluations parsed:       N
  After exclusion filters:        N
  With Binance settlement data:   N

  THRESHOLD SWEEP:

  BTC move threshold: >=0.20% (60s)
    Signals that would have fired:  N
    Directional accuracy:           XX.X%
    Actual Kalshi YES price — mean: XXc | median: XXc | p25: XXc | p75: XXc
    Mean actual edge (real prices): X.X%
    50c-assumed edge would show:    X.X%  (delta: X.Xpp)

  BTC move threshold: >=0.30% (60s)
    ...

  BTC move threshold: >=0.40% (60s)  <-- current live threshold
    ...

  BTC move threshold: >=0.50% (60s)
    ...

  KEY FINDING:
  [If actual Kalshi prices meaningfully differ from 50¢, note the direction and magnitude]
  [E.g. "At >=0.40% threshold, actual YES price was 53c avg — HFTs had already priced in ~3c of BTC move"]
  [This reduces effective edge by ~Xpp vs the 50c backtest assumption]
============================================================
```

The KEY FINDING section: compute average yes_cents across all evaluations that fired at the current threshold (0.40%). If avg > 52 or avg < 48, write a note explaining the direction. If within 48-52, note "Kalshi price was near-neutral at signal time — 50¢ assumption is valid."

**Main entrypoint:**
```python
if __name__ == "__main__":
    asyncio.run(main())
```

main() does: parse logs → print parse summary → fetch Binance → fill settlements → run threshold sweep → print report → write results.md.

**Script-level constants (at top):**
```python
_LOG_FILES = [
    "/tmp/polybot_session20.log",
    "/tmp/polybot_session21.log",
    "/tmp/polybot_session24.log",
    "/tmp/polybot_session25.log",
]
_MIN_MINUTES_REMAINING = 3.0
_THRESHOLDS = [0.20, 0.30, 0.40, 0.50]
_RESULTS_PATH = Path(__file__).parent / "real_backtest_results.md"
_KLINES_URL = "https://api.binance.us/api/v3/klines"
_SYMBOL = "BTCUSDT"
_MAX_KLINES_PER_REQUEST = 1000
```

Imports needed: asyncio, re, math, statistics, sys, os, dataclasses, datetime, pathlib, typing, aiohttp. All already installed in the venv.
  </action>
  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python scripts/log_backtest.py 2>&1 | tail -40</automated>
  </verify>
  <done>
Script runs to completion without error. Prints parse summary (N evaluations parsed, N after filters, N with settlement data). Prints threshold sweep table for all 4 thresholds. Writes scripts/real_backtest_results.md. If any log files are missing, script logs a warning and continues with available files rather than crashing.
  </done>
</task>

</tasks>

<verification>
1. `python scripts/log_backtest.py` completes without exception
2. Output includes all four threshold rows (0.20%, 0.30%, 0.40%, 0.50%)
3. Parsed evaluation count is in the thousands (expected: ~3,000-4,000 after filters from 4,100 raw lines)
4. scripts/real_backtest_results.md exists and contains the full report
5. backtest.py and all src/ files are unchanged (verify with `git diff --name-only`)
</verification>

<success_criteria>
- scripts/log_backtest.py exists and runs cleanly
- Threshold sweep covers 0.20/0.30/0.40/0.50% with real Kalshi price distribution per bucket
- scripts/real_backtest_results.md written with actionable KEY FINDING about 50¢ assumption validity
- No existing files modified
</success_criteria>

<output>
After completion, no SUMMARY.md needed — this is a quick analysis task. Commit with:
`git add scripts/log_backtest.py scripts/real_backtest_results.md && git commit -m "feat: log-calibrated btc_lag backtest using real Kalshi prices from session logs"`
</output>
