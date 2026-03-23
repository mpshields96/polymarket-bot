---
created: 2026-03-23T06:37:00.492Z
title: Build generalized rat-poison bucket scanner with multi-dimensional slices
area: strategy
files:
  - scripts/auto_guard_discovery.py
---

## Problem

`auto_guard_discovery.py` only scans sniper (coin × side × price) tuples for negative-EV buckets. The broader pattern space — (asset × hour × side), (strategy × price × direction), etc. — is not covered. A structurally losing combination in any of these dimensions could accumulate losses without triggering a guard.

The self-learning loop should naturally identify and block "rat poison" bet types whenever evidence is sufficient, not on a schedule. This is variable-interval by design: fire when the statistical gate is crossed, not daily.

## Solution

Extend auto_guard_discovery.py (or build a companion script) to:

1. Define a set of slice dimensions beyond coin/side/price — candidates:
   - asset × UTC hour × side
   - strategy × price × direction
   - asset × day-of-week × side
   - Any combo with n>=10 live bets and p<0.20 significance gate

2. Apply Bonferroni correction (or Benjamini-Hochberg FDR) for multiple comparisons.
   Scanning 20 slices without correction means ~1 false positive at p<0.05 by chance.

3. Require higher minimum n for multi-dimensional slices (e.g. n>=20 vs n>=10 for 1-D).

4. Output format same as current auto_guards.json — drop-in compatible with live.py guard loader.

5. Run on same variable-interval cadence as current scanner (session start + every 3rd cycle).

Scope: research chat to design the slice space and correction method first.
Implementation only after research chat sign-off on thresholds.

## Key constraints

- False positive risk is the main danger — blocking a good bucket due to variance.
- Current conservative gates (p<0.20, n>=10) are correct starting points.
- Do NOT change existing sniper guard logic — this is additive only.
- The bot must not be broken during rollout — paper-test new guards before live activation.
