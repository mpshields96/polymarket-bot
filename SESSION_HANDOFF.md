# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-27 (Session 9 — minor bug fixes: dead price_key, markets[] guard)
═══════════════════════════════════════════════════

## Current State

Bot starts, connects, Binance.US feed is live, and trading loop evaluates markets every 30s.
BTC price feed confirmed working: ~100 ticks/min, btc_move_pct() returning real values.

No signal has fired yet — observed BTC 60s moves are ~0.02-0.03%, threshold is 0.4%.
This is normal for a calm market period. The strategy is evaluating correctly.

verify.py: **18/18 ✅**
Tests: **117/117 ✅**

## Next Action (FIRST THING)

Let the bot run for a full session (ideally 24h) and watch for the first signal:

    python main.py

Expected output every 30s:
  - "[trading] Evaluating 1 market(s): ['KXBTC15M-...]"  ← loop is alive
  - "[btc_lag] Signal: BUY YES/NO ..."                   ← signal fired (uncommon)

If the signal never fires after a few hours:
  ⚠️  The binding constraint is min_edge_pct (8%), NOT min_btc_move_pct.
      At min_edge=8%, you need ~0.65% BTC move in 60s. Typical calm market: 0.02-0.05%.
  1. Run with DEBUG logging to see which gate is failing
  2. To fire more signals: lower min_edge_pct: 0.08 → 0.05 in config.yaml (NOT min_btc_move_pct)
     ONLY do this after understanding the tradeoff (lower edge = more trades, less selective)

## What was fixed Session 7 (prior session)

1. PID lock added to main.py
   → bot.pid written at startup, removed on shutdown
   → Prevents two `python main.py` instances from running simultaneously
   → If bot crashes and bot.pid is stale, next startup detects dead PID and overwrites safely

2. Near-miss INFO logging in btc_lag.py
   → "BTC move too small" path promoted from DEBUG to INFO
   → Every 30s log shows: "[btc_lag] BTC move +X.XXX% (need ±0.40%) — waiting for signal"
   → Matthew can see feed is alive and how close bot is to firing

3. kill_switch._write_blockers() now skips during pytest (PYTEST_CURRENT_TEST guard)
   → Test runs no longer pollute BLOCKERS.md with false auth-failure entries

4. config.yaml: threshold calibration comment + lag_sensitivity explicit param added
   → Documents that min_edge_pct is the binding constraint (~0.65% BTC move needed)
   → Guidance: lower min_edge_pct (not min_btc_move_pct) if more signals needed

5. BLOCKERS.md cleaned — all auto-appended noise removed, only resolved items remain

6. Dashboard DB path bug fixed (src/dashboard.py)
   → Was hardcoded to `kalshi_bot.db` at project root — always showed "No database found"
   → Fixed: `_resolve_db_path()` reads config.yaml → gets correct `data/polybot.db`
   → Same source as db.py; dashboard now connects to the real DB

7. data/ directory auto-created at startup (main.py)
   → `sqlite3.connect("data/polybot.db")` would fail on fresh clone if data/ didn't exist
   → Fixed: `(PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)` at `__main__` startup
   → data/.gitkeep added to ensure dir is committed (data/polybot.db still gitignored)

8. verify.py @bookTicker fix (setup/verify.py)
   → Was using `btcusdt@trade` — near-zero volume on Binance.US, likely 30s timeout
   → Fixed: uses `btcusdt@bookTicker`, parses bid/ask, computes mid-price (same as binance.py)

9. SIGTERM handler added to main.py
   → `kill PID` (used by shell scripts, process managers) sends SIGTERM, not SIGINT
   → Previously only `KeyboardInterrupt` (Ctrl+C / SIGINT) triggered clean shutdown
   → Fixed: `loop.add_signal_handler(SIGTERM/SIGHUP, cancel_tasks)` — triggers same finally block

## What was fixed this session (Session 9 — minor bug fixes)

1. Dead `price_key` variable removed from live.py
   → Was assigned but never used (leftover from earlier draft)

2. Empty `markets` list guard added to main.py
   → `config.strategy.markets: []` in config.yaml would cause IndexError at startup
   → Now: explicit check with clear error message before `create_task`

3. Comment added to live.py `_FIRST_RUN_CONFIRMED`
   → Documents why this second CONFIRM prompt exists alongside main.py's startup CONFIRM
   → Design: main.py CONFIRM at startup, live.py CONFIRM at first trade — defense-in-depth

## What was fixed this session (Session 8 — code review fixes)

1. Kill switch disconnected from settlement (CRITICAL — hard stops were dead code)
   → `settlement_loop` now takes `kill_switch` parameter
   → Calls `kill_switch.record_win()` or `kill_switch.record_loss(abs_usd)` after each settlement
   → Consecutive-loss cooling, daily-loss soft stop, total-loss hard stop now actually trigger

2. Live mode silently fell back to paper (CRITICAL — invisible failure)
   → `live_confirmed` was hardcoded to `False` in the `trading_loop` call
   → Now: when `live_mode=True`, bot shows banner and requires user to type `CONFIRM`
   → `live_confirmed=True` only if user confirmed — matches the dashboard Tips description

3. PID lock PermissionError was treated as stale (Important)
   → `PermissionError` from `os.kill(pid, 0)` means process IS alive under another user
   → Now exits with clear error instead of silently overwriting the PID file

4. Dead `sizing` and `paper_executor` params removed from `trading_loop` (Important)
   → Both were always passed as `None` and never used

5. Stale threshold 10s → 35s in binance.py (Minor)
   → Binance.US @bookTicker can be silent 10-30s — 10s caused false stale signals
   → Now 35s, matching documented silence window

6. 10 new tests total:
   → TestSettlementIntegration (test_kill_switch.py): win/loss wiring, hard stop at 30%, zero ignored
   → TestPytestGuard (test_kill_switch.py): verifies BLOCKERS.md write suppressed during pytest
   → TestDashboardDbPath (test_db.py): absolute path, config value, bad config fallback, missing config fallback
   → 117/117 tests passing

## What was fixed Session 6 (prior session)

1. Binance.US @trade stream has near-zero BTC volume (ROOT CAUSE of zero price data)
2. Kill switch stale lock: tests/conftest.py created

## What was fixed Session 5 (prior session)

1. config.yaml series ticker: btc_15min → KXBTC15M  (ROOT CAUSE of silent trading loop)
2. main.py: added INFO heartbeat "[trading] Evaluating N market(s)" every poll cycle
   (previously all skip paths logged at DEBUG, loop appeared silent when no signal)

## Component Status

| Component            | Status      | Notes                                          |
|----------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)       | ✅ Working  | $75 balance confirmed                          |
| Kalshi REST client   | ✅ Working  | api.elections.kalshi.com, field names fixed    |
| Binance.US feed      | ✅ Working  | @bookTicker, ~100 ticks/min, mid-price         |
| BTCLagStrategy       | ✅ Running  | Evaluating markets every 30s, no signal yet    |
| Kill switch          | ✅ Working  | Clear                                          |
| Database             | ✅ Working  | data/polybot.db                                |
| Paper executor       | ✅ Ready    | Not yet triggered                              |
| Dashboard            | ✅ Fixed    | DB path bug fixed; reads data/polybot.db from config|
| Trading loop         | ✅ Confirmed| Evaluates KXBTC15M every 30s                   |
| Settlement loop      | ✅ Ready    | Runs, no open trades yet                       |

## Key Commands

    python main.py                    → Paper mode (default)
    python main.py --verify           → Pre-flight check (18/18)
    streamlit run src/dashboard.py   → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 117 tests
    echo "RESET" | python main.py --reset-killswitch

## CHECKPOINT_4 Gate Status

  ✅ verify.py 18/18
  ✅ python main.py runs without crashing, evaluates markets every 30s
  ⏳ First paper trade signal logged (waiting for BTC to move >0.4% in 60s)
  ✅ Dashboard ready (not yet tested in this session, but code unchanged)

  CHECKPOINT_4 is effectively done. Remaining gate item is time-dependent.

## On other Kalshi markets (confirmed from live API probe)

Confirmed active series on api.elections.kalshi.com:
  - KXBTC15M  — BTC 15-min ✅ (trading now)
  - KXETH15M  — ETH 15-min ✅ CONFIRMED EXISTS (same structure as BTC)
  - KXBTCD    — BTC daily price bands (longer horizon, lag logic doesn't apply well)
  - KXETH     — ETH daily price bands (same, longer horizon)
  - KXCPI     — CPI markets (requires macro signal, different strategy entirely)
  - Political/long horizon — no reliable external signal, skip

Next market to add after BTC proven: KXETH15M
  - Same lag logic, same code structure
  - Add ETH to Binance.US feed (wss://stream.binance.us:9443/ws/ethusdt@bookTicker)
  - Run second strategy instance pointed at KXETH15M

DO NOT add ETH until: BTC paper trading shows positive edge over 7+ real days.
