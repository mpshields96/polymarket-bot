# KILL SWITCH LESSONS — Hard-Won Truths
# Every entry here cost real money or real bets. Never repeat these.
# Updated: Session 35 (2026-03-08)

---

## LESSON 1 — Stale consecutive loss streak blocks forever on restart
**Session:** 35 | **Impact:** 7 days of zero live bets (12+ lost opportunities)
**Root cause:** `restore_consecutive_losses()` always triggered a FRESH 2hr cooling
period using `time.time()` as the start, regardless of when the losses actually
happened. Trades 110-121 settled 2026-03-01 (7 days before discovery). Every
restart after that imposed a new 2-hour block.

**Fix:** Pass `last_loss_ts` from `db.current_live_consecutive_losses()` to
`restore_consecutive_losses(count, last_loss_ts)`. If the losses are older than
COOLING_PERIOD_HOURS, the window has expired — seed the counter, don't block.

**Rule:** When restoring ANY time-bounded state from DB on restart, always check
whether the time window was already served. Restore remaining time, not fresh full window.

**Regression test:** `test_restore_stale_streak_does_not_block` in
`tests/test_kill_switch.py::TestRestoreConsecutiveLosses`

---

## LESSON 2 — Settlement loop sends Polymarket tickers to Kalshi API
**Session:** 35 | **Impact:** Log spam, wasted API calls, settlement not working
**Root cause:** `settlement_loop()` was built for Kalshi-only trades. When
`sports_futures_v1` paper trades were added to the DB, the loop tried to call
`kalshi.get_market("tec-cbb-champ-2026-04-04-uconn")` — 404 on every poll.

**Fix:** Filter to only `KX*` tickers before the Kalshi API call. Kalshi tickers
always start with `KX` (KXBTC15M, KXETH15M, etc.). Polymarket tickers never do.

**Rule:** Every settlement path must be platform-aware. When adding a new platform's
trades to the shared DB, immediately audit the settlement loop. Add a platform filter
BEFORE touching the external API — never let it spam 404s silently.

**Pattern:** Any new platform = new settlement path. Do NOT share settlement across
platforms without explicit ticker routing.

---

## LESSON 3 — Restart-based time recovery requires timestamp, not duration
**Session:** 25/35 | **Impact:** Compounding soft stops across sessions
**Root cause:** In-memory state (cooling_until, daily_loss_usd) lost on restart.
Fix was to restore from DB. But restoration must compute REMAINING time from the
original event timestamp — not restart fresh from now.

Correct pattern:
```python
elapsed = time.time() - original_event_timestamp
remaining = window_seconds - elapsed
if remaining > 0:
    restore_with_expiry(time.time() + remaining)
else:
    # Window already expired — seed state only, don't block
    seed_counter_without_blocking()
```

**Rule:** Every "restore on restart" function must store AND use the original
event timestamp. Never use `time.time()` as the start of a restored window.

---

## LESSON 4 — Silent kill switch blocks are invisible unless you check
**Session:** 35 | **Discovery:** User noticed zero live bets, not bot
**Root cause:** Kill switch blocks log at INFO level but the USER has no
visibility unless watching the log. The bot appeared "healthy" from outside.

**Fix (implemented Session 35):** Startup kill switch health check that prints
the FULL kill switch state to the startup banner, including:
- consecutive_loss_streak + last_loss_ts
- daily_loss_usd vs limit
- is_hard_stopped
- cooling_until (if any)

**Rule:** The startup banner must surface any active soft/hard stop. If a block
is in place, it MUST appear in the first 10 lines of startup output, not buried
in logs.

---

## LESSON 5 — Multiple restarts can amplify a bug before discovery
**Session:** 35 | **Impact:** 7 days × multiple daily restarts = chronic block
**Pattern:** Bug was introduced Session 23-25 (consecutive loss persistence).
The original fix was correct for "restart during active cooling window." The edge
case (restart after cooling expired) wasn't covered. Went undetected because:
1. No test for stale streak scenario
2. No startup alert for active soft stops
3. btc_drift normally has low signal rate anyway

**Rule:** Persistence bugs are the hardest to detect. Any time you add "persist X
across restarts," immediately write tests for:
(a) Restore mid-window (partial remaining time)
(b) Restore after window expired (stale, should not block)
(c) Restore with no data (clean start)

---

## LESSON 6 — Kill switch "cooling period" and "soft stop" are separate mechanisms
**Session:** 23-35 | **Confusion source:** Code mixes `_cooling_until` and `_soft_stop`
**Current state:**
- `_cooling_until` = timestamp until consecutive loss cooling expires
- `_soft_stop` = general soft stop flag (set True for daily loss OR consecutive)
- `_soft_stop_until` = also used for consecutive cooling expiry
These three interact in `check_order_allowed()` in a non-obvious way.

**Rule:** Never add a NEW blocking mechanism without first reading `check_order_allowed()`
top-to-bottom and understanding all 3-4 separate blocking paths. Draw it out if needed.
The current code has: bankroll floor → hard stop → daily loss → consecutive cooling.

---

## STARTUP HEALTH CHECK — MANDATORY
At every bot startup, the log must contain a kill switch status block like:
```
Kill switch state:
  Hard stopped:     NO
  Daily loss:       $0.00 / $15.95 limit
  Consecutive:      4 / 4 limit (STALE — last loss 173.7hr ago, no block)
  Cooling until:    None
```
If this block shows any active block, the user MUST see it immediately.
Implement: `kill_switch.log_startup_status()` called after all restores in main.py.

---

## THE META-RULE
Before any soft stop or hard stop mechanism goes into production:
1. Write a test for "window already expired on restart" — the stale case
2. Write a test for "window partially elapsed on restart" — the remaining time case
3. Write a test for "first-ever clean start with no DB data"
4. Add the blocking condition to the startup status log
5. Confirm the log message is visible at INFO level in normal operation

If any of these 5 are missing, the mechanism WILL cause a silent bug.
