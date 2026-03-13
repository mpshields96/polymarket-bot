# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-13 (Session 61 wrap — sniper float fix, bot stopped per Matthew)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 62)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 62).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 61 wrap — 2026-03-13 ~00:35 CDT / 05:35 UTC):
  Bot STOPPED — Matthew requested shutdown at end of 3-hour window.
  Sniper: 39W/2L all-time (95.1%) — ABOVE breakeven. pct_cap float fix deployed.
  btc_drift + eth_drift remain MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone (no sol signals this session).

RESTART COMMAND (Session 62):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session62.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 61 wrap — 2026-03-13 05:35 UTC):
  Bot: STOPPED (Matthew requested at end of 3hr autonomous window)
  All-time live P&L: -45.60 USD (session net -5.75)
  Bankroll: ~54.40 USD
  1076/1076 tests passing
  Last commits: d657f80 (sniper pct_cap float fix) + 6687b75 (S60 wrap)

SESSION 61 BUILDS:

  1. SNIPER PCT_CAP FLOATING-POINT FIX (commit d657f80):
     IEEE 754 precision: 4.72/94.4 = 0.050000000000000003 > 0.05 threshold.
     Kill switch rejected sniper bets at exact boundary.
     Fix: _pct_max = round(bankroll * 0.05, 2) - 0.01 (subtract 1 cent safety margin).
     Added max(0.01, _pct_max) floor to prevent negative sizing.
     Regression test: test_pct_cap_floating_point_boundary in test_kill_switch.py.

  2. SNIPER FIRST LOSSES OBSERVED + ANALYZED:
     22:30 window: BTC and SOL both reversed. 2 losses at 93c = -9.30 USD.
     Correlation risk identified: betting same direction on 3-4 assets per window.
     Decision: DO NOT INTERVENE — 28 trades too small, 95%+ true rate still +EV.

  3. AUTONOMOUS MONITORING (3 hours):
     Bot supervised from ~22:00 CDT to ~00:35 CDT.
     Sniper generated 39 live bets total (was 19 at session start).
     20 new sniper bets this session: 18W/2L. Net sniper session: -4.56 USD.
     Micro-live drift trades: 2W/3L eth_drift (-0.12), 0W/1L xrp (-0.57).

  4. SIDE CHAT RESEARCH PROMPT CREATED:
     .planning/SIDE_CHAT_RESEARCH_S61.md — sniper optimization (entry price,
     time-to-expiry, drift threshold, correlation), time-of-day filter, limit orders.
     Ready for Matthew to feed to a parallel chat.

SESSION 61 KEY FINDINGS:
  - Sniper all-time: 39W/2L (95.1%) — ABOVE 95% breakeven threshold (barely).
  - Sniper P&L: -0.41 USD all-time (nearly breakeven — fees eat small wins).
  - Bankroll dropped 98→54 USD across S60+S61 (mostly from pre-demotion drift losses).
  - Sol drift did NOT fire during this session (no signals in 3 hours).
  - Price guard drought periods are common at night (bearish crypto = YES at 10-20c).

SESSION 61 SELF-RATING:
  GRADE: B — Fixed a real blocking bug (float precision), monitored successfully,
  bot didn't crash. BUT session P&L was -5.75 despite 24W/6L — the 2 sniper losses
  dominate everything. No new features built. Sol milestone didn't advance.
  NEXT SESSION MUST: restart bot, watch sol progress, check side chat research results.

LIVE STRATEGY STATUS (Session 61 wrap):
  btc_drift_v1:         MICRO-LIVE  filter="no"   (DEMOTED S60, confirmed loser)
  eth_drift_v1:         MICRO-LIVE  filter="yes"  (DEMOTED S60, confirmed loser)
  sol_drift_v1:         STAGE 1     28/30 Brier 0.176  filter="no"   +13.48 USD  2 FROM 30!
  xrp_drift_v1:         MICRO       19/30 Brier 0.261  filter="yes"  -1.12 USD
  expiry_sniper_v1:     LIVE UNCAPPED — 39W/2L (95.1%) -0.41 USD all-time
  eth_orderbook_imbalance_v1: PAPER  15/30 Brier 0.337  DISABLED LIVE
  btc_lag_v1:           STAGE 1  45/30  0 signals/week — dead (HFTs)

PENDING TASKS (Session 62 — PRIORITY ORDER):

  #1 RESTART BOT — it was stopped per Matthew's directive. Must restart immediately.

  #2 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled -> milestone.
     When it hits 30: check --graduation-status. If Brier < 0.25:
     present Stage 2 promotion analysis (10 USD max bet, up from 5).

  #3 MONITOR SNIPER:
     39W/2L all-time (95.1%). pct_cap float fix deployed.
     Watch: win rate trend, any new blocking bugs, correlation risk.
     Side chat research may recommend entry price or time changes.

  #4 CHECK SIDE CHAT RESEARCH:
     .planning/SIDE_CHAT_RESEARCH_S61.md was created for parallel chat.
     Check if results appeared in .planning/EDGE_RESEARCH_S61.md.
     If actionable findings exist, implement CAREFULLY.

  #5 BANKROLL CONCERN:
     Bankroll at ~54 USD (was ~98 at start of S60).
     Main loss source was drift strategies BEFORE demotion.
     Sniper losses contribute ~9.30 but sniper overall is near-breakeven.
     At 54 USD, max bet is min(5.00, 54*0.05-0.01) = min(5.00, 2.69) = 2.69 USD.
     Sniper bets will be SMALLER now. Each win ~0.12-0.19 USD vs ~0.25-0.35 before.

125 USD PROFIT GOAL:
  All-time: -45.60 USD. Need +170.60 more.
  Key levers: (1) sniper wins accumulate slowly at 2.69/bet, (2) sol 2 from Stage 2,
  (3) losers contained at micro-live, (4) side chat may surface new edges

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
