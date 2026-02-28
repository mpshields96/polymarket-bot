---
phase: quick-1
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - docs/GRADUATION_CRITERIA.md
  - setup/verify.py
  - src/db.py
autonomous: true
requirements: [GRAD-01]

must_haves:
  truths:
    - "docs/GRADUATION_CRITERIA.md exists with concrete per-strategy thresholds"
    - "verify.py check_graduation_status() queries DB and prints PASS/FAIL per strategy"
    - "Graduation check is non-critical (WARN, not FAIL) so it never blocks bot startup"
    - "Each strategy evaluated independently (strategies graduate individually)"
  artifacts:
    - path: "docs/GRADUATION_CRITERIA.md"
      provides: "Human-readable graduation thresholds with rationale"
      contains: "min_paper_trades, min_days_running, brier_score_threshold, max_consecutive_losses"
    - path: "setup/verify.py"
      provides: "check_graduation_status() function added and called in run_all()"
      exports: []
    - path: "src/db.py"
      provides: "graduation_stats(strategy) method returning dict of metrics per strategy"
  key_links:
    - from: "setup/verify.py"
      to: "src/db.py"
      via: "graduation_stats(strategy)"
      pattern: "db\\.graduation_stats"
    - from: "src/db.py"
      to: "trades table"
      via: "inline SQL grouping by strategy, is_paper=1"
      pattern: "SELECT.*strategy.*is_paper"
---

<objective>
Define and wire formal live-graduation criteria for each of the 8 paper-trading strategies.

Purpose: Prevent premature live enablement by making graduation criteria explicit,
checkable, and visible every time verify.py runs. Strategies graduate individually.

Output:
- docs/GRADUATION_CRITERIA.md — thresholds and rationale
- src/db.py — graduation_stats(strategy) DB helper
- setup/verify.py — check_graduation_status() section [11]
</objective>

<execution_context>
@/Users/matthewshields/.claude/get-shit-done/workflows/execute-plan.md
@/Users/matthewshields/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@/Users/matthewshields/Projects/polymarket-bot/.planning/STATE.md
@/Users/matthewshields/Projects/polymarket-bot/CLAUDE.md

<interfaces>
<!-- From src/db.py — DB methods available to verify.py -->
<!-- All methods below are synchronous (no await). -->

class DB:
    def win_rate(self, is_paper: Optional[bool] = None, limit: int = 100) -> Optional[float]:
        """Returns 0.0–1.0 or None if no settled trades. Compares result == side."""

    def count_trades_today(self, strategy: str, is_paper: Optional[bool] = None) -> int:
        """Count of bets placed today (UTC) for given strategy."""

    def has_open_position(self, ticker: str, is_paper: Optional[bool] = None) -> bool:
        """True if unsettled trade exists on this ticker."""

    def total_realized_pnl_usd(self, is_paper: Optional[bool] = None) -> float:
        """Sum of all settled P&L in USD."""

<!-- NEW method to add in Task 1 -->
    def graduation_stats(self, strategy: str) -> dict:
        """
        Returns per-strategy paper trading metrics needed for graduation check.
        Keys: settled_count, win_rate, brier_score, consecutive_losses,
              first_trade_ts, days_running, total_pnl_usd
        Returns None values for fields with no data.
        """

<!-- From setup/verify.py — existing pattern -->
def record(name: str, passed: bool, detail: str = "", critical: bool = True):
    status = "✅ PASS" if passed else ("❌ FAIL" if critical else "⚠️  WARN")
    ...

# Graduation check must use critical=False for all records —
# graduation is advisory, never blocks bot startup.
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add graduation_stats() to DB and write GRADUATION_CRITERIA.md</name>
  <files>src/db.py, docs/GRADUATION_CRITERIA.md, tests/test_db_graduation.py</files>

  <behavior>
    - graduation_stats("btc_lag") on empty DB returns dict with all None/0 values
    - graduation_stats("btc_lag") with 50 settled paper trades for btc_lag returns:
        settled_count=50, win_rate=float, days_running>=0, consecutive_losses=int
    - graduation_stats("btc_lag") with btc_lag wins: [W,W,L,L,L] returns consecutive_losses=3
    - graduation_stats("btc_lag") only counts is_paper=1 trades
    - brier_score computed as mean((win_prob - outcome)^2) over settled trades where win_prob is not NULL
    - first_trade_ts = earliest timestamp for strategy in trades table (paper only)
    - days_running = (now - first_trade_ts) / 86400, or 0 if no trades
  </behavior>

  <action>
Add `graduation_stats(strategy: str) -> dict` method to DB class in src/db.py.

Place it in the `# ── Stats` section, after `total_realized_pnl_usd`.

Implementation:

```python
def graduation_stats(self, strategy: str) -> dict:
    """
    Return per-strategy paper trading metrics needed for graduation check.

    Only counts paper trades (is_paper=1). Returns a dict with keys:
        settled_count       int   — number of settled paper trades
        win_rate            float | None — wins/settled (result==side)
        brier_score         float | None — mean((win_prob - outcome)^2), lower is better
        consecutive_losses  int   — current streak of losses at end of trade history
        first_trade_ts      float | None — unix timestamp of first paper trade
        days_running        float — calendar days since first paper trade (0 if none)
        total_pnl_usd       float — sum of settled P&L in USD (paper only)
    """
    import time as _time

    # Settled paper trades for this strategy, oldest first
    rows = self._conn.execute(
        """SELECT result, side, win_prob, pnl_cents, timestamp
           FROM trades
           WHERE strategy = ? AND is_paper = 1 AND result IS NOT NULL
           ORDER BY timestamp ASC""",
        (strategy,),
    ).fetchall()

    if not rows:
        return {
            "settled_count": 0,
            "win_rate": None,
            "brier_score": None,
            "consecutive_losses": 0,
            "first_trade_ts": None,
            "days_running": 0.0,
            "total_pnl_usd": 0.0,
        }

    rows = [dict(r) for r in rows]

    settled_count = len(rows)
    wins = sum(1 for r in rows if r["result"] == r["side"])
    win_rate = wins / settled_count

    # Brier score: only trades that have win_prob recorded
    brier_rows = [r for r in rows if r["win_prob"] is not None]
    if brier_rows:
        brier_score = sum(
            (r["win_prob"] - (1.0 if r["result"] == r["side"] else 0.0)) ** 2
            for r in brier_rows
        ) / len(brier_rows)
    else:
        brier_score = None

    # Consecutive losses at end of history
    consecutive_losses = 0
    for r in reversed(rows):
        if r["result"] != r["side"]:
            consecutive_losses += 1
        else:
            break

    # First trade timestamp (paper only, any result)
    first_row = self._conn.execute(
        "SELECT MIN(timestamp) FROM trades WHERE strategy = ? AND is_paper = 1",
        (strategy,),
    ).fetchone()
    first_trade_ts = first_row[0] if first_row and first_row[0] else None
    days_running = (_time.time() - first_trade_ts) / 86400.0 if first_trade_ts else 0.0

    total_pnl_usd = sum((r["pnl_cents"] or 0) for r in rows) / 100.0

    return {
        "settled_count": settled_count,
        "win_rate": win_rate,
        "brier_score": brier_score,
        "consecutive_losses": consecutive_losses,
        "first_trade_ts": first_trade_ts,
        "days_running": days_running,
        "total_pnl_usd": total_pnl_usd,
    }
```

After adding the method to src/db.py, write tests/test_db_graduation.py with the behavior
cases listed above (TDD: write tests first, run them to confirm RED, then implement,
then confirm GREEN).

Then create docs/ directory and write docs/GRADUATION_CRITERIA.md:

```markdown
# Live Graduation Criteria — polymarket-bot

## Overview

Each strategy graduates to live trading INDEPENDENTLY. A strategy may go live
while others remain in paper mode. Graduation is manually triggered after all
criteria are met (set LIVE_TRADING=true AND pass --live flag per strategy).

Run `python setup/verify.py` to see current status for all 8 strategies.

## Thresholds

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Minimum paper trades (settled) | **30** | Statistical significance (~4-sigma at 60% win rate) |
| Minimum days running | **7** | Captures intraday + weekly market patterns |
| Brier score (lower = better) | **< 0.25** | 0.2178 = STRONG; 0.25 = acceptable calibration |
| Maximum consecutive losses | **< 5** | Kill switch fires at 5; live graduation requires headroom |
| Win rate (informational) | >= 55% | Directional signal; Brier score is primary calibration metric |

## Strategy-Specific Notes

### btc_lag / eth_lag (momentum)
- Backtest: btc_lag 84.1% acc / 44 signals per 30 days
- Competing with Jane Street / Susquehanna / Jump HFTs (0.17pp spread)
- Monitor fill quality in paper mode — if fills frequently miss, recalibrate min_edge_pct
- Extra bar: require 30+ settled trades (signal fires ~1-2x/day, so ~15-30 days to hit count)

### btc_drift / eth_drift (sigmoid model)
- btc_drift Brier = 0.2178 (STRONG calibration on 30-day backtest)
- Capped at 5 bets/day to prevent tax churn — 30 settled trades = ~6-7 paper days minimum
- Brier score threshold is the primary graduation gate for drift strategies

### orderbook_imbalance (BTC + ETH)
- VPIN-lite signal: no backtest Brier score available (novel signal)
- Must accumulate 30 settled trades before Brier can be computed reliably
- If Brier is unavailable after 30 trades (no win_prob recorded), use win_rate >= 58% instead

### weather_forecast (HIGHNY)
- Only fires on HIGHNY weekday markets — lower signal frequency
- 30 settled trades may take 4-6 weeks given weekday-only operation
- Min days running extended to 14 days for weather (seasonal variation)

### fomc_rate (KXFEDDECISION)
- Fires ~8x/year (14 days before each FOMC meeting)
- Min settled trades threshold: 5 (cannot reach 30 in first year)
- Min days running: N/A — criterion replaced by "at least 2 FOMC cycles completed"
- Brier score threshold same: < 0.25

## How to Check

```bash
python setup/verify.py
```

Section [11] prints graduation status per strategy. WARN (not FAIL) — graduation
is advisory and never blocks bot startup.

## How to Graduate a Strategy

1. Confirm verify.py shows PASS on all criteria for that strategy
2. Review paper P&L for that strategy in dashboard (localhost:8501)
3. Update config.yaml: set `live: true` under the strategy section (once per-strategy live flag is added)
4. Restart bot with --live flag and LIVE_TRADING=true in .env
5. Monitor first 5 live bets manually

## Criteria Version

v1.0 — 2026-02-28. Review and tighten after first strategy goes live.
```
  </action>

  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python -m pytest tests/test_db_graduation.py -v</automated>
  </verify>

  <done>
    - tests/test_db_graduation.py passes (all behavior cases green)
    - graduation_stats() exists in DB class in src/db.py
    - docs/GRADUATION_CRITERIA.md exists with all 8 strategies documented
    - 296+ tests still pass (no regressions): python -m pytest tests/ -q
  </done>
</task>

<task type="auto">
  <name>Task 2: Add check_graduation_status() to verify.py</name>
  <files>setup/verify.py</files>

  <action>
Add a new check function `check_graduation_status()` to setup/verify.py and call it
in `run_all()` as section [11]. This check is NON-CRITICAL (all records use critical=False).

The thresholds to use match docs/GRADUATION_CRITERIA.md exactly:

```python
# Graduation thresholds (must match docs/GRADUATION_CRITERIA.md)
_GRAD = {
    # strategy_name: (min_trades, min_days, max_brier, max_consecutive_losses)
    "btc_lag_v1":                   (30, 7,  0.25, 4),
    "eth_lag_v1":                   (30, 7,  0.25, 4),
    "btc_drift_v1":                 (30, 7,  0.25, 4),
    "eth_drift_v1":                 (30, 7,  0.25, 4),
    "orderbook_imbalance_v1":       (30, 7,  0.25, 4),
    "eth_orderbook_imbalance_v1":   (30, 7,  0.25, 4),
    "weather_forecast_v1":          (30, 14, 0.25, 4),
    "fomc_rate_v1":                 (5,  0,  0.25, 4),  # low frequency — 5 trade minimum
}
```

Implementation of check_graduation_status():

```python
def check_graduation_status():
    """Check paper trading graduation criteria for each strategy (non-critical)."""
    print("\n[11] Live graduation status (paper trading)")
    try:
        import yaml
        with open(PROJECT_ROOT / "config.yaml") as f:
            cfg = yaml.safe_load(f)
        db_path_str = cfg.get("storage", {}).get("db_path", "data/polybot.db")
        db_path = Path(db_path_str)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path

        if not db_path.exists():
            record("Graduation check", False,
                   "No DB yet — run bot first to collect paper trades", critical=False)
            return

        from src.db import DB
        db = DB(db_path)
        db.init()

        any_ready = False
        for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
            stats = db.graduation_stats(strategy)
            n = stats["settled_count"]
            days = stats["days_running"]
            brier = stats["brier_score"]
            consec = stats["consecutive_losses"]

            passes_trades = n >= min_trades
            passes_days = days >= min_days
            passes_brier = (brier is None and n < min_trades) or (brier is not None and brier < max_brier)
            passes_consec = consec < max_consec

            ready = passes_trades and passes_days and passes_brier and passes_consec

            if ready:
                any_ready = True
                detail = (
                    f"trades={n} days={days:.1f} brier={brier:.3f} consec_losses={consec} "
                    f"pnl=${stats['total_pnl_usd']:.2f} — READY FOR LIVE"
                )
            else:
                gaps = []
                if not passes_trades:
                    gaps.append(f"trades {n}/{min_trades}")
                if not passes_days:
                    gaps.append(f"days {days:.1f}/{min_days}")
                if not passes_brier and brier is not None:
                    gaps.append(f"brier {brier:.3f}>={max_brier}")
                if not passes_consec:
                    gaps.append(f"consec_losses {consec}>={max_consec}")
                brier_str = f"{brier:.3f}" if brier is not None else "n/a"
                detail = (
                    f"trades={n} days={days:.1f} brier={brier_str} consec_losses={consec} "
                    f"| needs: {', '.join(gaps)}"
                )

            record(f"Graduation: {strategy}", ready, detail, critical=False)

        db.close()

        if any_ready:
            record("At least one strategy ready for live", True,
                   "Review docs/GRADUATION_CRITERIA.md before enabling live trading",
                   critical=False)

    except Exception as e:
        record("Graduation check", False, f"Error: {e}", critical=False)
```

Add `check_graduation_status()` call to `run_all()` after `check_strategy()`:

```python
async def run_all():
    check_env()
    check_pem()
    check_auth_headers()
    await check_kalshi_demo()
    await check_kalshi_auth_live()
    await check_binance_feed()
    await check_kill_switch()
    check_config()
    check_db()
    check_strategy()
    check_graduation_status()   # <-- add this line

    # Summary ...
```

Also add `_GRAD` dict at module level (after the imports, before the check functions).

Note: The graduation check prints WARN (not FAIL) for unmet criteria because:
- Bot should always start in paper mode regardless of graduation status
- Graduation is a manual decision by the user after reviewing the data
  </action>

  <verify>
    <automated>cd /Users/matthewshields/Projects/polymarket-bot && source venv/bin/activate && python setup/verify.py 2>&1 | grep -E "^\[11\]|graduation|Graduation"</automated>
  </verify>

  <done>
    - verify.py runs without error
    - Section [11] appears in output with one line per strategy
    - All 8 strategies show WARN (not FAIL) — graduation check never causes verify.py exit 1
    - 296+ tests still pass: python -m pytest tests/ -q
    - verify.py total check count incremented (was 18, now 18 + 8 strategy rows + 1 summary = ~27 rows)
  </done>
</task>

</tasks>

<verification>
Run the full test suite and verify.py after both tasks:

    source venv/bin/activate && python -m pytest tests/ -v 2>&1 | tail -5
    python setup/verify.py

Expected:
- All prior 296 tests pass + new graduation tests added (total >= 300)
- verify.py section [11] shows all 8 strategies as WARN (not FAIL) with 0 settled trades
- verify.py exits 0 (graduation WARNs do not cause failure)
- docs/GRADUATION_CRITERIA.md exists and is human-readable
</verification>

<success_criteria>
- docs/GRADUATION_CRITERIA.md created with thresholds: min 30 paper trades, 7 days running,
  Brier < 0.25, < 5 consecutive losses (with fomc/weather exceptions documented)
- src/db.py has graduation_stats(strategy) returning settled_count, win_rate, brier_score,
  consecutive_losses, days_running, total_pnl_usd
- setup/verify.py has [11] section printing pass/fail per strategy (critical=False)
- graduation check never causes verify.py to exit 1
- All existing 296 tests still pass + new graduation tests added
</success_criteria>

<output>
After completion, create `.planning/quick/1-define-formal-live-graduation-criteria-f/1-SUMMARY.md`
capturing what was built, key decisions, and test count delta.
</output>
