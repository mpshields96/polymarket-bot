# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 58 wrap — bot restarted with sniper LIVE)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 59)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 59).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 58 wrap — 23:10 UTC 2026-03-12):
  Bot RUNNING PID 5699 → /tmp/polybot_session58.log
  Sniper LIVE for first time — expiry_sniper_v1 active in live mode
  No sniper live bets yet — needs qualifying market (YES or NO >= 90c + coin drift)
  All drift strategies running normally

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 58 wrap — 2026-03-12):
  Bot: RUNNING PID 5699 → /tmp/polybot_session58.log
  All-time live P&L: -34.59 USD
  Bankroll: 109.94 USD
  1078/1078 tests passing
  Last commits: eb6b957 (KXBTCD threshold) + dd7199d (sniper live) + f606b99 (price guard)

SESSION 58 BUILDS (2 chats — main + side):

  MAIN CHAT:
  1. EXPIRY SNIPER LIVE PATH — COMPLETE + RESTARTED:
     - live.py: price_guard_min/max params on execute() — sniper passes 1/99
     - expiry_sniper.py: Fixed NO-side convention (price_cents = no_price, was yes_price)
       This also fixes the 10-15x paper P&L inflation bug
     - main.py: Full live/paper conditional in expiry_sniper_loop()
     - 4 new tests in TestSniperPriceGuardOverride, 1 test updated
     - Pre-live audit: all 12 checklist items verified
     - Bot restarted as session 58 — sniper NOW LIVE

  SIDE CHAT:
  2. KXBTCD THRESHOLD RESEARCH + CALCULATOR:
     - src/strategies/crypto_daily_threshold.py — N(d2) fair-value calculator
     - tests/test_crypto_daily_threshold.py — 24 tests
     - scripts/test_deribit_dvol.py — Deribit DVOL API validated (DVOL=54.1)
     - scripts/check_kxbtcd_edge.py — Kalshi KXBTCD edge scanner
     - .planning/KXBTCD_THRESHOLD_RESEARCH.md — comprehensive research
     Research/prototype only — expansion gate not cleared.

SESSION 58 KEY DECISIONS:
  - Eth drift 3/9 = VARIANCE (extreme bearish session). Do NOT change filter.
  - Sniper live expected: ~+0.35 USD/bet, 5-10 bets/day = +1.75-3.50 USD/day

LIVE STRATEGY STATUS (Session 58 wrap):
  btc_drift_v1:         STAGE 1  54/30 Brier 0.247  filter="no"   0 consec  -11.12 USD
  eth_drift_v1:         STAGE 1  86/30 Brier 0.249  filter="yes"  5 consec DB*  -11.51 USD
  sol_drift_v1:         STAGE 1  27/30 Brier 0.177  filter="no"   1 consec  +9.25 USD  3 FROM 30!
  xrp_drift_v1:         MICRO    18/30 Brier 0.261  filter="yes"  0 consec  -0.55 USD
  expiry_sniper_v1:     LIVE (first time!) — 0 live bets yet, monitoring
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 59 — PRIORITY ORDER):

  #1 MONITOR SNIPER LIVE BETS — first ever live sniper bets expected
     grep "expiry_sniper.*LIVE\|expiry_sniper.*execute" /tmp/polybot_session58.log
     Verify correct pricing when first fires (NO@90c+ = ~4.50-4.95 USD cost)

  #2 SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets -> milestone. When it fires, check --graduation-status.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.

  #3 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed.

  #4 KXBTCD THRESHOLD STRATEGY (when expansion gate clears):
     .planning/KXBTCD_THRESHOLD_RESEARCH.md — research complete
     src/strategies/crypto_daily_threshold.py — prototype built
     Need: live loop in main.py, Deribit DVOL feed, KXBTCD market fetching

125 USD PROFIT GOAL:
  All-time: -34.59 USD. Need +159.59 more.
  Key levers: (1) sniper now LIVE (+1.75-3.50/day), (2) sol 30-bet milestone (3 away),
  (3) drought productivity, (4) KXBTCD when gate clears

RESPONSE FORMAT RULES (permanent — both mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose — triggers LaTeX math mode.
  USE: "40.09 USD" or "P&L: -34.59". NEVER "$40.09".

DIRECTION FILTER SUMMARY (permanent):
  btc_drift: filter="no"  — only NO bets
  eth_drift: filter="yes" — only YES bets (REVERSED from btc)
  sol_drift: filter="no"  — only NO bets
  xrp_drift: filter="yes" — only YES bets (REVERSED, S54)

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. Urgent. Claude Max renewal depends on this.
  DO NOT change parameters under pressure. PRINCIPLES.md always governs.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.
