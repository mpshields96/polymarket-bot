
---
## [2026-03-18 22:15 UTC] STANDING DIRECTIVE — Matthew
**Priority:** PERMANENT
**From:** kalshi-research

Cross-chat learning directive from Matthew (applies to all 3 chats):
  - Be open to learning from each other across domains, not just task-delegation
  - Original main roles ALWAYS take priority (monitoring is your primary job)
  - Self-learning mechanism should feed into cross-chat loop:
    * When you see live anomalies or guard triggers, note them in POLYBOT_TO_CCA.md
      so CCA can research the academic basis
    * When bet_analytics.py findings come through, check EDGE_RESEARCH files for context

Specific to main chat:
  - At session start, run: ./venv/bin/python3 scripts/bet_analytics.py
  - This is now a standard health check, same as auto_guard_discovery.py
  - If SPRT verdict changes or CUSUM crosses threshold, log to POLYBOT_TO_CCA.md

---
## [2026-03-18 22:15 UTC] S105 RESEARCH SUMMARY — for main chat context
**From:** kalshi-research

S105 PRIMARY BUILD: scripts/bet_analytics.py — 24 tests, all passing (commit e886a1a)
  Run this at every startup: ./venv/bin/python3 scripts/bet_analytics.py

S105 KEY FINDINGS:
  - sniper: EDGE CONFIRMED (lambda=+17.141). No changes needed. This is working.
  - eth_drift: NO EDGE + DRIFT ALERT. Bayesian self-corrects. No manual action.
  - btc_drift CUSUM at 4.48/5.0 — watch, alert if it crosses 5.0
  - sol_drift: edge barely confirmed (lambda=+2.886). Keep monitoring.

S105 NEW GUARD: KXBTC YES@94c (auto-guard #3 added from S104 late losses)
  3 auto-guards now active: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c

Bot should be running PID 2502 → /tmp/polybot_session105.log
Tests: 1605 passing
All-time P&L: +12.95 USD

## [2026-03-18] S107 RESEARCH SUMMARY — for main chat context
**From:** kalshi-research

S107 PRIMARY BUILD: Dim 8 — per-strategy temperature calibration (commit caf69e9)
  src/models/temperature_calibration.py (18 tests)
  scripts/calibration_bootstrap.py — seeds from DB history
  Wired into bayesian_settlement.py + btc_drift.py + main.py

S107 KEY FINDINGS:
  1. 1932 stale open trades = FALSE ALARM — all paper, long-duration markets (sports_futures, fomc, copy_trader). No settlement loop bug. Health check already patched in c2c6a8a.

  2. CUSUM h=5.0 IS CORRECT — ARL simulation: ARL(H0)=237, ARL(H1)=72. btc_drift S=4.480 is correctly near threshold (48.5% WR). No action needed. Observation only.

  3. Calibration overconfidence STATISTICALLY SIGNIFICANT:
     ETH: predicted 54.8%, actual 46.7%, p=0.015
     XRP: predicted 61%, actual 48.9%, p=0.033
     BTC: borderline p=0.063
     SOL: well-calibrated (T=1.29)

  4. Temperature calibration ACTIVE — bot restarted PID 28165 with new code:
     ETH T=0.500: 54.8% → 52.4% predicted win_prob
     BTC T=0.500: 57% → 53.5% predicted win_prob
     XRP T=0.500: 61% → 55.5% (many signals below 5% threshold → fewer bets)
     SOL T=1.290: 65.3% → 69.8% (larger Kelly for winning strategy)

  5. BTC very_high edge_pct (>15%) = anti-predictive: n=18, 39% WR, -17.36 USD
     OBSERVATION ONLY — need 30+ data points before action per PRIME DIRECTIVE

MONITORING NOTE: Bot restarted at 18:54 UTC — log at /tmp/polybot_session107.log
Tests: 1623 passing. Last commit: caf69e9

CCA REQUEST SENT: CUSUM optimal h threshold research (POLYBOT_TO_CCA.md)

---

## S108 Research Summary (2026-03-19 ~00:45 UTC) — RESEARCH CHAT

2 NEW GUARDS ACTIVATED (bot restarted PID 33218):
  KXXRP NO@93c: n=24, 91.7% WR — BLOCKED
  KXBTC NO@94c: n=10, 90.0% WR — BLOCKED
  5 total auto-guards now active.

FLB RESEARCH COMPLETE (Pillar 2):
  Burgi-Deng-Whelan (2026) confirms Kalshi 95c → 98% WR. Our data: 95c YES = 98.1%.
  Ceiling at 95c is theoretically AND empirically correct (96c+ = -1.9 to -5.7pp).
  FLB in fixed-odds markets strengthens with more sophisticated participants (long-term positive).

BET ANALYTICS STATE:
  sniper: EDGE CONFIRMED lambda=+15.332, CUSUM stable S=2.025
  btc_drift: CUSUM improved 4.480 → 4.020 (moving away from threshold)
  eth_drift: CUSUM improved 14.140 → 12.760 (still in DRIFT ALERT, Bayesian handles)

No code changes this session.
