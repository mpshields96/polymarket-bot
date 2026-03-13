# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 59 — Kalshi API v2 breaking change fixed)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 60)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 60).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 59 — 2026-03-12 ~19:00 CDT):
  Bot RUNNING PID 8325 → /tmp/polybot_session59.log
  Sniper LIVE — expiry_sniper_v1 active in live mode (0 live bets yet)
  All drift strategies running normally with FIXED API parsing

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 59 — 2026-03-12):
  Bot: RUNNING PID 8325 → /tmp/polybot_session59.log
  All-time live P&L: -34.59 USD (no new bets yet this session — just restarted)
  Bankroll: 109.94 USD
  1075/1075 tests passing (3 skipped)
  Last commits: 03ca33f (Kalshi API v2 fix) + eb6b957 (KXBTCD threshold)

SESSION 59 BUILDS:

  1. CRITICAL FIX — KALSHI API V2 BREAKING CHANGE (March 12, 2026):
     Kalshi removed all integer cents price fields and integer count fields.
     New API returns: *_dollars (string "0.5900") and *_fp (string "100.00")

     ROOT CAUSE: 18+ hour trading drought — all markets showed YES=0c NO=0c
     because _parse_market() was reading removed fields (yes_bid, yes_price).

     FIXED in src/platforms/kalshi.py:
     - Added _dollars_to_cents() helper: "0.5900" → 59 cents
     - Added _fp_to_int() helper: "100.00" → 100
     - Updated _parse_market(): reads yes_bid_dollars/no_bid_dollars
     - Updated _parse_order(): reads yes_price_dollars/no_price_dollars + count fields
     - Updated get_fills(): reads *_dollars + count_fp + market_ticker fallback
     - Updated get_orderbook(): reads orderbook_fp.yes_dollars/no_dollars
     - create_order() UNCHANGED — API still accepts integer cents in request body
     - All helpers fall back to legacy integer fields for test mock compatibility

     Commit: 03ca33f. Bot restarted as PID 8325. Verified:
     - Markets show correct mid-range prices (YES=42c NO=57c BTC, YES=45c NO=52c SOL)
     - Fills parse correctly (59c/41c)
     - Orderbook levels parse correctly
     - Balance unchanged (still integer cents format)
     - 1075 tests pass, 3 skipped

SESSION 59 KEY DECISIONS:
  - API breaking change was platform-wide, not a bot bug or price guard drought
  - create_order still accepts cents — no order format change needed
  - Balance API still returns integer cents — no change needed

LIVE STRATEGY STATUS (Session 59 — same as S58, no new settled bets):
  btc_drift_v1:         STAGE 1  54/30 Brier 0.247  filter="no"   0 consec  -11.12 USD
  eth_drift_v1:         STAGE 1  86/30 Brier 0.249  filter="yes"  5 consec DB*  -11.51 USD
  sol_drift_v1:         STAGE 1  27/30 Brier 0.177  filter="no"   1 consec  +9.25 USD  3 FROM 30!
  xrp_drift_v1:         MICRO    18/30 Brier 0.261  filter="yes"  0 consec  -0.55 USD
  expiry_sniper_v1:     LIVE — 0 live bets yet, monitoring
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 60 — PRIORITY ORDER):

  #1 MONITOR FIRST LIVE BETS POST-FIX — confirm pricing correct on first trades
     grep "LIVE BET\|Trade executed" /tmp/polybot_session59.log
     All strategies were blocked 18+ hours. First bets will validate the fix end-to-end.

  #2 SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets -> milestone. When it fires, check --graduation-status.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.

  #3 MONITOR SNIPER LIVE BETS — first ever live sniper bets expected
     grep "expiry_sniper.*LIVE\|expiry_sniper.*execute" /tmp/polybot_session59.log
     Verify correct pricing when first fires (NO@90c+ = ~4.50-4.95 USD cost)

  #4 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed.

  #5 KXBTCD THRESHOLD STRATEGY (when expansion gate clears):
     .planning/KXBTCD_THRESHOLD_RESEARCH.md — research complete
     src/strategies/crypto_daily_threshold.py — prototype built
     Need: live loop in main.py, Deribit DVOL feed, KXBTCD market fetching

125 USD PROFIT GOAL:
  All-time: -34.59 USD. Need +159.59 more.
  Key levers: (1) sniper now LIVE (+1.75-3.50/day), (2) sol 30-bet milestone (3 away),
  (3) API fix restores all trading after 18hr drought, (4) KXBTCD when gate clears

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
