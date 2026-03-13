# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 59 wrap — sniper 10/10, API fix validated)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 60)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 60).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 59 wrap — 2026-03-12 ~19:50 CDT):
  Bot RUNNING PID 8325 → /tmp/polybot_session59.log
  Sniper LIVE — 10/10 wins, +1.90 USD (perfect record so far)
  All drift strategies running, API fix validated
  Drift strategies resumed mid-range firing on 21:00 window (sol + eth bets placed)

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 59 wrap — 2026-03-12):
  Bot: RUNNING PID 8325 → /tmp/polybot_session59.log
  All-time live P&L: -32.69 USD (gained +1.90 this session)
  Bankroll: ~112 USD
  1075/1075 tests passing (3 skipped)
  Last commits: 0083b08 (S59 docs) + 03ca33f (Kalshi API v2 fix)

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

     Commit: 03ca33f. Bot restarted as PID 8325.

  2. SNIPER LIVE VALIDATION — 10/10 wins, +1.90 USD:
     expiry_sniper_v1 placed 10 live bets across 3 windows (20:15, 20:30, 20:45).
     All 10 settled as wins. Entry prices: 93-98c YES. Favorite-longshot bias works.
     Kill switch 5% bankroll cap correctly throttled after 4 concurrent bets.

  3. DRIFT + SNIPER COMPLEMENTARY CONFIRMED:
     During extreme bullish session (YES 90-99c), drift was correctly blocked by
     35-65c price guard. Sniper thrived in that zone. When prices normalized on
     21:00 window (SOL YES=41c), drift resumed immediately. The two strategy types
     cover opposite price regimes — no dead zones.

SESSION 59 KEY DECISIONS:
  - API breaking change was platform-wide, not a bot bug or price guard drought
  - create_order still accepts cents — no order format change needed
  - Balance API still returns integer cents — no change needed
  - Sniper profit margins: 3-7% per bet (small but high win rate)
  - P&L includes Kalshi taker fees. Does NOT include taxes (tracked separately).

LIVE STRATEGY STATUS (Session 59 wrap):
  btc_drift_v1:         STAGE 1  54/30 Brier 0.247  filter="no"   0 consec  -11.12 USD
  eth_drift_v1:         STAGE 1  86/30 Brier 0.249  filter="yes"  5 consec DB*  -11.51 USD
  sol_drift_v1:         STAGE 1  28/30 Brier 0.177  filter="no"   1 consec  +9.25 USD  2 FROM 30!
  xrp_drift_v1:         MICRO    18/30 Brier 0.261  filter="yes"  0 consec  -0.55 USD
  expiry_sniper_v1:     LIVE — 10/10 wins +1.90 USD (validated!)
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 60 — PRIORITY ORDER):

  #1 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets (27 settled + 1 open). 2 more settled → milestone.
     When it hits 30: check --graduation-status. If Brier < 0.25 + Kelly limiting:
     present Stage 2 promotion to Matthew.

  #2 MONITOR SNIPER CONTINUED PERFORMANCE:
     10/10 perfect record. Watch for first loss to calibrate true win rate.
     Expected: ~85-95% win rate long-term. 100% at 10 bets = small sample.

  #3 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed.

  #4 KXBTCD THRESHOLD STRATEGY (when expansion gate clears):
     .planning/KXBTCD_THRESHOLD_RESEARCH.md — research complete
     src/strategies/crypto_daily_threshold.py — prototype built
     Need: live loop in main.py, Deribit DVOL feed, KXBTCD market fetching

  #5 KALSHI API CHANGELOG MONITORING:
     Consider scheduled task to check https://docs.kalshi.com/changelog weekly.
     The S58-S59 18hr drought was caused by a PLANNED breaking change we didn't catch.

125 USD PROFIT GOAL:
  All-time: -32.69 USD. Need +157.69 more.
  Key levers: (1) sniper validated +1.90/session at current rate, (2) sol 2 bets from 30,
  (3) API fix restored all trading, (4) drift + sniper complementary = fewer dead zones

RESPONSE FORMAT RULES (permanent — both mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose — triggers LaTeX math mode.
  USE: "40.09 USD" or "P&L: -32.69". NEVER "$40.09".

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
