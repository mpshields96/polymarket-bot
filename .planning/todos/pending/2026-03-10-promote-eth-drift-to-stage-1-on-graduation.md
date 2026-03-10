---
created: 2026-03-10T12:09:36.004Z
title: Promote eth_drift to Stage 1 on graduation
area: general
files:
  - src/strategies/btc_drift.py
  - main.py
---

## Problem

eth_drift is at 29/30 live settled bets with Brier 0.253 (< 0.30 threshold).
ONE more live settled bet triggers graduation. As of 2026-03-10 bot was STOPPED
manually — next restart will resume trading and graduation could happen within
the first 15-min window if eth_drift fires a signal.

Graduation criteria per docs/GRADUATION_CRITERIA.md:
- 30+ live settled bets ✅ (needs 1 more)
- Brier < 0.30 ✅ (0.253)
- Kelly limiting_factor check needed at Stage 2, not required for Stage 1 promotion

## Solution

1. Start bot to session44.log
2. Monitor for eth_drift graduation: `python3 main.py --graduation-status`
3. When 30/30 reached: run Step 5 pre-live audit checklist from CLAUDE.md
4. Remove `calibration_max_usd=0.01` from eth_drift trading_loop call in main.py
5. Raise eth_drift cap from $0.65 micro-live → $5.00 Stage 1
6. Commit + restart
