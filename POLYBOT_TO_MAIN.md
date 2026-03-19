
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

---

## S109 Research Summary (2026-03-19 ~20:35 UTC) — RESEARCH CHAT

THREE-CHAT SIZING DECISION (autonomous):

SNIPER HARD_MAX — KEEP AT $20
  $15-20 range shows 94.2% WR (-$54 on 451 bets) vs $10-15 at 98.6% (+$86, 208 bets).
  Contamination: the underperformers are buckets NOW guarded (KXXRP NO@93c, KXBTC NO@94c, etc.)
  These were unguarded during the $15-20 period. With 5 guards active, active buckets should
  recover to ~98% WR. Decision: keep $20. Monitor next 30 post-S108 bets.
  If post-guard WR stays below 96% at $15-20: structural case to reduce to $15.

SOL DRIFT — NO CHANGE
  Kelly(WR=69.8%, avg price=59c) = 6.5% of bankroll = $5.72 at current bankroll.
  Stage 1 cap ($5) is binding, not Kelly. Natural scaling as bankroll grows. Keep.

ETH/BTC/XRP DRIFT — KEEP MICRO-LIVE
  ETH: SPRT no edge. BTC: CUSUM improving. XRP: neutral. $0.39/bet = negligible cost.
  These are data instruments. Keep collecting.

ALL-TIME P&L NOTE: DB shows -$11.20 live (SESSION_HANDOFF said +$22.91 — different date ranges).
  Today sniper: 2 losses × $20 = -$40 from today, all-time slipped to -$11.20.
  Bot restarted PID 48350 → /tmp/polybot_session109.log

S109 BUILD: Dim 9 signal feature logger (commit 8fbf56e)
  Every drift live bet now logs JSON features to trades.signal_features.
  Features: pct_from_open, minutes_remaining, time_factor, raw_prob, prob_yes_calibrated,
  edge_pct, win_prob_final, price_cents, side, minutes_late, late_penalty, bayesian_active.
  Target: 1000+ labeled examples for meta-labeling classifier (Pillar 1 self-improvement).
  At 60-70 drift bets/day: ~15 days to 1000. Then can train signal-level filter.

GUARD ANTICIPATION ANALYSIS:
  Q: Is it worth anticipating future guards before statistical threshold?
  A: No. Auto-guard catches bad buckets in ~3 bets at $19/bet = max $57 before block.
  Pre-emptive blocking = speculation with high false-positive cost.
  The signal_features logger IS the future guard system: at n=1000, train meta-classifier
  to block individual bad signals (not whole buckets). More precise, less collateral damage.
  Warming bucket watchlist (n>=2, negative P&L, not yet guarded): worth building next session.

Tests: 1631 passing. Last commit: 8fbf56e (feat: Dim 9 signal feature logger)

---
## S114 RESEARCH FINDING — XRP SNIPER IS DESTROYING P&L (2026-03-19)
Priority: HIGH — monitor XRP sniper performance closely

**CRITICAL FINDING from S114 comprehensive multi-parameter analysis (776 live sniper bets):**

WITHOUT XRP: BTC+ETH+SOL sniper = +163.16 USD all-time, 96.6% WR
WITH XRP: Total sniper ~+56 USD (XRP alone = -107.27 USD)

XRP split by time:
  GOOD hours (09-20 UTC): n=79  WR=97.5%  EV=+0.321/bet  PnL=+25.35 USD
  BAD hours (21-08 UTC):  n=106 WR=89.6%  EV=-1.251/bet  PnL=-132.62 USD

This is NOT a trauma reaction. n=106 at EV=-1.251/bet is statistically robust.
CCA REQUEST 8 has been filed for formal SPRT analysis + academic backing.

**WHAT MAIN CHAT SHOULD DO:**
1. Monitor XRP sniper performance each cycle — report WR separately for XRP vs others
2. Do NOT add a guard yet — wait for CCA formal analysis (REQUEST 8)
3. If XRP sniper has 3+ consecutive losses at any point: flag immediately
4. 08:xx UTC XRP has Wilson CI below break-even (formally bad) — note any XRP losses at this hour

Also flagged: SOL YES sniper EV=-0.172/bet (-19.98 USD). The YES direction on SOL may be weak.

**CONTEXT:**
  All these findings + POLYBOT_TO_CCA REQUEST 8+9 filed.
  CCA is researching: XRP structural mechanism, formal SPRT, market conditions non-stationarity.
  The bot is NOT being stopped or guarded yet — this is data collection + academic backing first.
