---
created: 2026-03-09T15:05:35.482Z
title: Update POLYBOT_INIT docs with live.py security findings and skills reference
area: docs
files:
  - POLYBOT_INIT.md
  - CLAUDE.md
  - .planning/SKILLS_REFERENCE.md
  - src/execution/live.py
---

## Problem

`sc:analyze --focus security --think` on `src/execution/live.py` surfaced 3 findings that should
be documented in POLYBOT_INIT.md and CLAUDE.md Gotchas so they're not repeated:

**HIGH — Canceled order recorded to DB (no order status check)**
`db.save_trade()` is called regardless of `order.status`. If Kalshi returns `status="canceled"`
or `"resting"`, the trade is recorded as a completed live bet, corrupting calibration data
and graduation stats. Fix: `if order.status == "canceled": return None` before `db.save_trade()`.

**MEDIUM — No internal count cap in live.py**
`count = max(1, int(trade_usd / cost_per_contract))` can exceed intended limits if
`trade_usd` is miscalculated upstream. live.py fully trusts the caller's `trade_usd`.
Note: currently mitigated by `HARD_MAX_TRADE_USD = $5.00` clamp in main.py, but live.py
has no independent guard if called from a new path.

**LOW — `strategy_name="unknown"` default silently corrupts reporting**
`execute()` accepts `strategy_name: str = "unknown"` as default. Any call that omits
this param silently records trades under "unknown" strategy — corrupts graduation stats,
`--report` output, and Brier calculations. Every caller must pass an explicit strategy name.

Also: Add link to `.planning/SKILLS_REFERENCE.md` in the POLYBOT_INIT.md session startup
checklist so it's surfaced at the start of each session.

## Solution

1. Update `CLAUDE.md` Gotchas section: add bullets for each of the 3 sc:analyze findings
2. Update `POLYBOT_INIT.md`: add SKILLS_REFERENCE.md to session startup reading list
3. Apply HIGH fix in `live.py`: add `if order.status not in ("filled", "resting"): return None`
   guard between `create_order()` response and `db.save_trade()` call
4. Add regression test for the canceled-order case to `tests/test_live_executor.py`

Note: Item 3 (the actual live.py fix) is the only code change — items 1-2 are doc-only.
