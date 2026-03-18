
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
