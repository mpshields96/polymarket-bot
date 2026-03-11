---
created: 2026-03-11T17:37:53.450Z
title: Apply eth_drift direction_filter="yes" after Matthew sign-off
area: strategy
files:
  - main.py:2541-2565
  - src/strategies/btc_drift.py
  - .planning/todos.md
---

## Problem

Session 52 directional audit of 67 settled live eth_drift bets shows consistent YES outperformance:

- YES side: 36 bets, 61.1% wins, +25.58 USD total, **+0.711 USD/bet EV**
- NO side:  31 bets, 48.4% wins, -6.58 USD total, **-0.212 USD/bet EV**

Z-test for proportion difference: Z=1.04, p=0.148 — not yet statistically significant at 5%,
but practically significant. The EV gap (+0.711 vs -0.212 = +0.923/bet difference) is large.

Additional finding — eth_drift NO price bucket analysis:
- NO at 35-44c: 44% wins, -2.67 USD (neutral)
- NO at 45-49c: 0% wins, -5.66 USD **WORST BUCKET — all 9 bets LOST**
- NO at 50-54c: 86% wins, +5.51 USD (BEST — near-neutral prices)
- NO at 55-65c: 50% wins, -1.34 USD (neutral)

The 45-49c NO bucket is the primary driver of NO underperformance. These bets fire when the
market is leaning slightly against us (price says 51-55c chance of YES, we're betting NO).

Estimated daily improvement from direction_filter="yes": +2.54 USD/day (at current bet frequency).

## Solution

**DO NOT implement without explicit Matthew sign-off.**

Option A — direction_filter="yes" for eth_drift:
```python
# In main.py, find eth_drift_task and add:
direction_filter="yes"  # Blocks all NO bets for eth_drift
```
Pattern is identical to btc_drift direction_filter="no" (commit 61bc33b).
TDD required: test that eth_drift NO signals are blocked, YES pass through.

Option B (secondary) — min_no_price_cents=50 for eth_drift:
Only allows NO bets when market price >= 50c YES (i.e., we're betting NO when market is neutral).
This would block the 45-49c bucket (0% wins) while preserving 50-54c bucket (86% wins).
More surgical than full direction filter — keeps some NO data flowing.

Option C — Both filters combined (most conservative, best EV protection).

Statistical note: Need ~30 more YES-only bets to confirm filter is the right call. p=0.148 is
suggestive but not conclusive. Option B (price filter only) is lower risk if sign-off is delayed.

Read PRINCIPLES.md before implementing any threshold change.
