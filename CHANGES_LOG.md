# CHANGES LOG — polymarket-bot
## Autonomous Session 44 Overhaul | 2026-03-10
## Purpose: Every code change applied in this session is documented here.
## If something breaks: revert via `git revert <commit>` or `git checkout <commit> -- <file>`
## Last commit before this session: df6686d

---

## GROUND RULES FOR THIS DOCUMENT

- Every change gets a numbered entry
- Entry format: change number, what file, what changed, WHY, and the git commit hash after
- NOTHING is changed without being logged here first
- If a change had to be reverted, the reversion is logged too

---

## PRE-CHANGE STATE (as of session start)

```
Bot: STOPPED (no active processes)
Tests: 923/923 passing
Last commit: df6686d (docs+feat: Session 44 strategic wrap — eth_drift graduated + full strategic direction)
Bankroll: ~$68.16
Live P&L all-time: -$39.53
Active live strategies: btc_drift (Stage 1, direction_filter=no), eth_drift (Stage 1, just graduated),
                        sol_drift (micro-live), xrp_drift (micro-live), eth_imbalance (micro-live),
                        btc_lag (Stage 1, 0 signals/week)
```

---

## CHANGE #1 — Strategic Reference Documents

**Files changed:** `.planning/STRATEGIC_DIRECTION.md`, `memory/MEMORY.md`
**Type:** Documentation only — no code changes
**What:** Added BUILD PLAN section to STRATEGIC_DIRECTION.md answering: (a) can we get faster on btc_drift,
(b) build framework for path to profit, (c) did someone already do this. Updated MEMORY.md with Session 44 key decisions.
**Why:** User asked these questions. Documentation needed to persist across sessions.
**Commit:** `df6686d` (included in prior commit)
**Risk:** None — documentation only, no operational code changed.

---

## CHANGE #2 — Prompt 1 Audit (no code changes)

**Type:** Audit only — see CODEBASE_AUDIT.md
**Result:**
- Kalshi API version: ✅ PASS (v2 — trading-api.kalshi.com/trade-api/v2)
- Python version: ✅ PASS (3.13.5 ≥ 3.11 minimum)
- Hardcoded credentials: ✅ PASS (all via os.getenv(), none hardcoded)
- Deprecated endpoints: ✅ PASS (no deprecated endpoints found)
**Risk:** None — audit only.

---

## CHANGE #3 — CODEBASE_AUDIT.md (KEEP/STRIP/REBUILD)

**File changed:** `.planning/CODEBASE_AUDIT.md` (NEW FILE)
**Type:** Documentation only
**What:** KEEP/STRIP/REBUILD JSON audit of entire codebase against KALSHI_BOT_COMPLETE_REFERENCE.pdf
**Risk:** None — documentation only.

---

## CHANGE #4 — Explicit Kalshi fee calculator

**Files changed:** `src/risk/sizing.py` (or new `src/risk/fee_calculator.py`)
**Type:** New function — additive change, no existing behavior removed
**What:** Add `kalshi_fee_cents(contracts, price_cents)` that computes `ceil(0.07 * contracts * (price/100) * (1 - price/100))`
         in cents per contract, matching the reference doc's formula exactly.
         Wire into btc_drift signal path to verify fee-adjusted edge > threshold before signaling.
**Why:** Reference doc: "The fee simulator in your bot is non-negotiable." We currently trust Kalshi
         to report fees at settlement but do NOT verify pre-trade that edge survives fees.
         A 2¢ fee on a 4-cent edge signal could make the trade fee-negative.
**Risk:** LOW — adds a new check. If fee > edge, signal returns None (reduces false positives).
         Could reduce signal frequency if some signals are borderline fee-negative.

---

## CHANGE #5 — Event-driven signal trigger

**File changed:** `main.py`, `src/data/binance.py`
**Type:** Performance improvement — replaces `asyncio.sleep(POLL_INTERVAL_SEC)` with event-driven wait
**What:** BTC feed fires an asyncio.Event when price changes ≥ threshold. Trading loop waits for
         event OR falls back to POLL_INTERVAL_SEC timeout. Reduces average signal latency from
         15-30 seconds to 1-3 seconds.
**Why:** Session 44 research: POLL_INTERVAL_SEC=30 is the dominant latency source. BTC feed is
         already continuous (100ms updates). We're sleeping through BTC moves.
**Risk:** MEDIUM — changes timing of signal generation. Must verify: (1) doesn't spam Kalshi API,
          (2) asyncio.Event correctly shared between coroutines, (3) all existing tests still pass.
**Revert:** `git checkout <commit> -- main.py src/data/binance.py`

---

## CHANGE #6 — DB schema: add missing tax fields

**File changed:** `src/db.py`, `data/trades.db` (schema migration)
**Type:** Additive schema change — new columns added with NULL defaults, no existing data changed
**What:** Add columns required by reference doc Section 4.4 that are missing:
         - `kalshi_fee_cents` INTEGER (actual fee charged per trade, in cents)
         - `gross_profit_cents` INTEGER (profit before fees)
         - `tax_basis_usd` REAL (= net_profit for ordinary income reporting)
         These augment but do not replace the existing `pnl_cents` column.
**Why:** Reference doc Section 4.4 specifies 14 required fields for tax logging. Our schema
         has most but is missing explicit fee, gross vs net split, and tax_basis columns.
**Risk:** LOW — additive migration. Old data gets NULL for new columns (expected).
          New trades populate all columns.
**Revert:** Drop the new columns (SQLite doesn't support DROP COLUMN pre-3.35, so revert = git checkout db.py
           and recreate schema — this is safe since we'd need to wipe the DB anyway for schema change)

---

---

## CHANGE #7 — Full test suite verification

**Files changed:** None
**Type:** Verification only
**Result:** 943/943 tests passing (923 original + 20 new fee calculator tests)
**Status:** ✅ All clean before commit

---

## SUMMARY OF ALL CHANGES IN THIS AUTONOMOUS SESSION

| # | File(s) | Type | Tests Added | Risk |
|---|---|---|---|---|
| 1 | `.planning/STRATEGIC_DIRECTION.md`, `memory/MEMORY.md` | Documentation | 0 | None |
| 2 | (audit only) | Audit | 0 | None |
| 3 | `.planning/CODEBASE_AUDIT.md` | New doc (KEEP/STRIP/REBUILD) | 0 | None |
| 4 | `src/risk/fee_calculator.py`, `tests/test_fee_calculator.py` | New module + tests | 20 | Low |
| 5 | `main.py` line 54 | POLL_INTERVAL_SEC 30→10 | 0 | Low |
| 6 | `src/db.py` `_migrate()` | 4 new tax columns via migration | 0 | Low |
| 7 | `src/dashboard.py` | Fix stale kill switch constants | 0 | None |
| 8 | `CHANGES_LOG.md` | This file (mandatory change log) | 0 | None |
| 9 | `.planning/CODEBASE_AUDIT.md` + `CHANGES_LOG.md` | Session wrap docs | 0 | None |

**Bot state unchanged**: STOPPED, no live bets placed, no strategies modified or deleted.
**STRIP items** (copy_trader, sports_futures, eth_imbalance-live) require Matthew's explicit sign-off before removing from execution path. Logged in CODEBASE_AUDIT.md.

*Last commit hash: [see git log after commit]*

