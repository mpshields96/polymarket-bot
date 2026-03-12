# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 58 — sniper live path BUILT)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 59)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 59).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

BOT STATE (Session 58 — updated ~16:00 UTC):
  Bot RUNNING PID 47905 → /tmp/polybot_session57.log (polybot-monitor auto-restarted from 44178)
  ⚠️ Running bot has PRE-SNIPER code (started 08:50 CDT, commits landed 10:38+ CDT)
  ⚠️ Kalshi API DOWN since ~09:23 UTC — "Connection reset by peer" on api.elections.kalshi.com
     No live bets firing. Bot is alive and evaluating but cannot reach market.

  To activate sniper live path + recover from API outage: restart when Kalshi API recovers.
  RESTART COMMAND (session58.log):
  bash scripts/restart_bot.sh 58
  After restart: verify with ps aux | grep "[m]ain.py" | wc -l (should be 1)
  If bot.pid missing: echo "<new_PID>" > bot.pid immediately

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 58 — 2026-03-12):
  Bot: NOT RUNNING (needs restart when home on wifi)
  All-time live P&L: -34.59 USD
  Bankroll: 109.94 USD
  1078/1078 tests passing
  Last commits: eb6b957 (crypto_daily_threshold +24 tests) + dd7199d (sniper live path complete) + f606b99

SESSION 58 BUILDS:

  1. EXPIRY SNIPER LIVE PATH — COMPLETE (2 commits):
     - live.py: price_guard_min/max params on execute() — sniper passes 1/99
     - expiry_sniper.py: Fixed NO-side convention (price_cents = no_price, was yes_price)
       This also fixes the 10-15x paper P&L inflation bug (paper was using YES=8c as cost
       for NO contracts instead of actual NO=92c cost)
     - main.py: Full live/paper conditional in expiry_sniper_loop():
       lock + kill_switch + live_mod.execute(price_guard_min=1, price_guard_max=99)
       HARD_MAX sizing (no Kelly), _announce_live_bet(), daily bet cap (10/day)
       minutes_remaining=None (sniper has own 5s hard skip, kill switch 5-min check bypassed)
     - 4 new tests in TestSniperPriceGuardOverride, 1 test updated
     - Pre-live audit: all 12 checklist items verified
     - GOES LIVE AUTOMATICALLY on next --live restart (same as drift strategies)

  2. KXBTCD THRESHOLD RESEARCH + CALCULATOR — SAVED (research + side chat build):
     .planning/KXBTCD_THRESHOLD_RESEARCH.md — agent research on hourly/daily/weekly
     Key finding: Lognormal N(d2) pricing with Deribit DVOL as sigma source.
     Same-day KXBTCD = digital cash-or-nothing call option, NOT a drift bet.
     Side chat built: src/strategies/crypto_daily_threshold.py (N(d2) calculator)
       + tests/test_crypto_daily_threshold.py (24 tests) + scripts/test_deribit_dvol.py
       Commit eb6b957. Research/prototype only — no live loop, expansion gate not cleared.

  3. FULL AUDIT completed pre-Session 58 (from summary):
     - Per-strategy rolling trend analysis, direction filter validation
     - Edge-bucketed performance, sniper asymmetry analysis
     - Reddit research integration confirming drift is correct archetype

SESSION 58 KEY DECISIONS:
  - Eth drift recent losses (9 bets, 3/9 win) = VARIANCE in extreme bearish session.
    PRINCIPLES.md: do NOT change. YES filter all-time: 51 bets, 27W (53%), +6.80 USD.
    NO side: 35 bets, 16W (46%), -18.31 USD. YES filter is correct.
  - Sniper live expected P&L: ~+0.35 USD/bet (NOT +4-7 as paper showed — paper was inflated)
    At 5-10 bets/day: +1.75-3.50 USD/day incremental. Still positive.

LIVE STRATEGY STATUS (Session 58):
  btc_drift_v1:         STAGE 1  54/30 Brier 0.247  filter="no"   0 consec  -11.12 USD
  eth_drift_v1:         STAGE 1  86/30 Brier 0.249  filter="yes"  5 consec DB*  -11.51 USD
  sol_drift_v1:         STAGE 1  27/30 Brier 0.177  filter="no"   1 consec  +9.25 USD  3 FROM 30!
  xrp_drift_v1:         MICRO    18/30 Brier 0.261  filter="yes"  0 consec  -0.55 USD
  expiry_sniper_v1:     LIVE PATH BUILT — will go live on next restart with --live
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 59 — PRIORITY ORDER):

  #1 RESTART BOT as session 58 when Matthew is home on wifi.
     MONITOR FIRST SNIPER LIVE BET — verify it fires within 15 min of restart.
     Check log for: "[expiry_sniper] [LIVE] BUY" or "[live] Execution price"

  #2 SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets -> milestone. When it fires, check --graduation-status.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.

  #3 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed.

  #4 KXBTCD THRESHOLD STRATEGY (when expansion gate clears):
     .planning/KXBTCD_THRESHOLD_RESEARCH.md — N(d2) lognormal pricing model
     Side chat may have built prototype (src/strategies/crypto_daily_threshold.py)

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
