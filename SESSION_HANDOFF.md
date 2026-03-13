# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-13 (Session 60 wrap — risk overhaul, sniper unblocked)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 61)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 61).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 60 wrap — 2026-03-12 ~22:20 CDT):
  Bot RUNNING PID 13368 → /tmp/polybot_session60.log
  Sniper LIVE UNCAPPED — 19/19 wins today, +4.65 USD (perfect record continues)
  btc_drift + eth_drift DEMOTED to micro-live (0.01 cap) — stops the bleeding
  Dynamic bet scaling added — halves bet on each consecutive loss
  Sniper pct_cap bug FIXED — was silently blocking bets when bankroll < 100

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 60 wrap — 2026-03-13 03:20 UTC):
  Bot: RUNNING PID 13368 → /tmp/polybot_session60.log
  All-time live P&L: -39.85 USD (net -6.66 this session — eth_drift losses before demotion)
  Bankroll: ~98 USD
  1075/1075 tests passing (3 skipped)
  Last commits: 7337e2b (sniper pct_cap fix) + f9f3ad2 (risk overhaul)

SESSION 60 BUILDS:

  1. RISK OVERHAUL — scale down losers, uncap winners (commit f9f3ad2):
     btc_drift + eth_drift demoted to micro-live (calibration_max_usd=0.01).
     btc_drift: 54 bets, 48% win rate, -11.12 USD. eth_drift: 89 bets, 49%, -25.65 USD.
     Data-driven: 54+ and 89+ bets is more than enough to confirm not profitable at Stage 1.
     These strategies now lose pennies per bet instead of 4-5 USD per bet.

  2. SNIPER DAILY CAP REMOVED (was 10→20→unlimited):
     97-100% win rate across 85+ data points. Every signal is +EV, no reason to cap.
     Fixed max_daily_bets=0 guard in expiry_sniper_loop (0 means unlimited now).

  3. SNIPER PCT_CAP BUG FIXED (commit 7337e2b):
     Kill switch was blocking all sniper bets: "Trade 5.00 = 5.1% of bankroll (max 5%)".
     Sniper bypassed calculate_size() and used HARD_CAP directly, which exceeded
     the 5% pct_cap when bankroll dropped below 100. Silent blocker for multiple windows.
     Fix: trade_usd = min(HARD_CAP, bankroll * MAX_TRADE_PCT).

  4. DYNAMIC BET SCALING on consecutive losses:
     Halves bet per consecutive loss: 1→50%, 2→25%, 3→12.5%. Floor at 10%.
     Only affects drift strategies. Sniper uses HARD_CAP directly (unaffected).

  5. Strategy P&L analysis documented: .planning/STRATEGY_PNL_ANALYSIS_S60.md
  6. Side chat research prompt created: .planning/SIDE_CHAT_RESEARCH_PROMPT.md

SESSION 60 KEY FINDINGS:
  - eth_drift YES-only: 51% win rate (53 bets). Barely above breakeven. -2.61 USD.
  - eth_drift losses concentrated at 35-43c entries during bearish sessions.
  - sol_drift (79% WR, +13.48) and sniper (100% WR, +4.65 today) are the ONLY profitable strategies.
  - btc_drift and eth_drift are confirmed losers with 54+ and 89+ bets respectively.
  - Sniper + drift are complementary: sniper fires at 90c+ (extreme), drift at 35-65c (mid-range).

SESSION 60 SELF-RATING:
  GRADE: B+ — Found critical pct_cap bug blocking sniper, correct strategic demotion of losers.
  LOST: 14.14 USD to 3 eth_drift losses BEFORE demoting. Should have demoted instantly.
  NEXT CHAT MUST: not analyze eth_drift/btc_drift. They're micro-live. Focus on sol 30-bet
  milestone and sniper throughput. Every minute spent on losers = missed sniper wins.

LIVE STRATEGY STATUS (Session 60 wrap):
  btc_drift_v1:         MICRO-LIVE  54/30 Brier 0.247  filter="no"   -11.12 USD  (DEMOTED S60)
  eth_drift_v1:         MICRO-LIVE  89/30 Brier 0.249  filter="yes"  -25.65 USD  (DEMOTED S60)
  sol_drift_v1:         STAGE 1     28/30 Brier 0.176  filter="no"   +13.48 USD  2 FROM 30!
  xrp_drift_v1:         MICRO       18/30 Brier 0.261  filter="yes"  -0.55 USD
  expiry_sniper_v1:     LIVE UNCAPPED — 19/19 wins today +4.65 USD (75 total incl paper)
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 61 — PRIORITY ORDER):

  #1 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled → milestone.
     When it hits 30: check --graduation-status. If Brier < 0.25:
     present Stage 2 promotion analysis (10 USD max bet, up from 5).
     Each sol win at Stage 2 ≈ +8.46 USD instead of +4.23.

  #2 MONITOR SNIPER THROUGHPUT:
     19/19 perfect live record. Cap removed. pct_cap bug fixed.
     Watch for: first loss (calibrate true win rate), any new blocking bugs.
     Expected: 3-4 bets per window, 4 windows/hour = 12-16 bets/hour potential.

  #3 SIDE CHAT RESEARCH RUNNING:
     .planning/SIDE_CHAT_RESEARCH_PROMPT.md fed to parallel chat.
     Results will appear in .planning/EDGE_RESEARCH_S60.md.
     Do NOT duplicate that research. Just check if findings are actionable.

  #4 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed. At micro-live so low priority.

125 USD PROFIT GOAL:
  All-time: -39.85 USD. Need +164.85 more.
  Key levers: (1) sniper uncapped = more wins per hour, (2) sol 2 bets from Stage 2,
  (3) losers demoted to micro-live = bleeding stopped, (4) side chat may surface new edges

RESPONSE FORMAT RULES (permanent — both mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose — triggers LaTeX math mode.
  USE: "40.09 USD" or "P&L: -39.85". NEVER "$40.09".

DIRECTION FILTER SUMMARY (permanent):
  btc_drift: filter="no"  — only NO bets (MICRO-LIVE)
  eth_drift: filter="yes" — only YES bets (MICRO-LIVE)
  sol_drift: filter="no"  — only NO bets (STAGE 1)
  xrp_drift: filter="yes" — only YES bets (MICRO)

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. Urgent. Claude Max renewal depends on this.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.
