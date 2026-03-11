# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 53 mid — PID 75130, session53.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 54)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 54).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 54 start — 2026-03-11 ~19:30 UTC):
  Bot RUNNING PID 75130 → /tmp/polybot_session53.log
  NOTE: Matthew will explicitly say "stop" to kill the old bot before new session starts fresh.
  When Matthew says "stop": pkill -f "python3 main.py"; sleep 3; verify 0 processes.
  Then restart with: bash scripts/restart_bot.sh 54

CHECK BOT HEALTH FIRST (Session 54 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 75130)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session54.log) — ONLY AFTER MATTHEW SAYS "stop":
  bash scripts/restart_bot.sh 54
  ⚠️ NEVER pipe restart_bot.sh through head/tail/grep — SIGPIPE will kill the running bot!
  ⚠️ Always run restart_bot.sh in isolation: `bash scripts/restart_bot.sh 54` only.

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 53 mid — 2026-03-11 ~19:30 UTC):
* Bot: RUNNING (PID 75130) → /tmp/polybot_session53.log
* All-time live P&L: -28.01 USD (was -23.48 at S52 wrap — deteriorated from S52 eth NO bets)
* 1003/1003 tests passing
* Last code commits: 7db9c32 (S53 eth_drift filter + test fix) → 7a01b44 (S52 CHANGELOG)
* Today live P&L: +17.51 USD (70 settled, 58% win) — solid day
* Consecutive losses (global kill switch): ~1 (reset on restart + 1 settlement)

SESSION 53 CHANGES (already committed 7db9c32):
  1. eth_drift direction_filter="yes" ACTIVE — Matthew signed off, implemented, bot restarted
     Only YES signals fire for eth_drift. NO signals blocked. Estimated +2.54 USD/day improvement.
  2. Pre-existing test fix: TestATMPrioritySlot::test_no_regression_without_21utc_slot
     make_rel_market() now uses while loop +1hr to avoid hour 21 (not +10min which was insufficient)
  3. polybot-monitor updated to PID 75130 + session53.log

LIVE STRATEGY STATUS (from --graduation-status at Session 53 mid):
  - btc_drift_v1: STAGE 1 — 53/30 ✅ Brier 0.249 IMPROVING | direction_filter="no" ACTIVE
  - eth_drift_v1: STAGE 1 — 73/30 ✅ Brier 0.246 | direction_filter="yes" ACTIVE (S53!)
    Per-strategy consecutive=3 (from pre-filter NO losses). Filter prevents future bad bets.
  - sol_drift_v1: STAGE 1 — 25/30 Brier 0.171 BEST SIGNAL | direction_filter="no" ACTIVE
    5 more bets to formal graduation threshold. Watch for sol graduation checkpoint.
  - xrp_drift_v1: MICRO-LIVE — 15/30 Brier 0.264 | 1 consec
    xrp YES wins, NO loses (reversed). Consider direction_filter="yes" at 30 bets.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | DISABLED LIVE (Session 47)
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy

186 OPEN TRADES >48HR WARNING (from --health):
  All 186 are paper sports_futures_v1 bets on future sports events. NOT a settlement loop bug.
  Sports championship markets take months to settle. Ignore this warning.

PENDING TASKS (Session 54):
  1. sol_drift graduation watch: 25/30 — 5 more bets for formal graduation.
     When 30 bets reached: run --graduation-status + check Brier + confirm NO filter holding.
  2. xrp_drift direction analysis at 30 bets (currently 15/30).
     xrp YES outperforms NO (reversed pattern). Consider direction_filter="yes" when 30 bets.
  3. eth_drift YES filter validation: accumulate 30 YES-only settled bets post-filter,
     then evaluate win rate. If 60%+ holds, keep permanent. If reverts to 50%, remove.
  4. btc_drift NO-only validation at 30 NO-only settled bets (currently ~8, weeks away).
  5. eth_imbalance paper watchdog — if Brier < 0.25 at 30 bets, reconsider live.
  6. FOMC window: KXFEDDECISION-26MAR closes March 18. 0/5 settled. Will NOT make this cycle.
     Next FOMC window: June 2026.
  7. KXCPI strategy (post-expansion gate): 74 open markets. Build after sol + eth validated.
  8. KXBTCD Friday slot (770K volume): future work, post-expansion gate.

125 USD PROFIT GOAL — ASSESSMENT (2026-03-11 session 53 mid):
  Current all-time live P&L: -28.01 USD
  To reach +125 USD profit = need +153.01 USD cumulative from here.
  Today rate: +17.51 USD (70 bets, 58% win) — solid.
  With eth_drift YES filter: estimated +2.54 USD/day improvement → target ~+20 USD/day
  At +20/day average: ~8 more trading days to goal. At +15/day: ~10 days.
  Trajectory is realistic. Bot has consistent edge. eth_drift filter is the biggest recent improvement.

RESPONSE FORMAT RULES (permanent — Matthew's instructions, both mandatory):

RULE 1 — NO MARKDOWN TABLES:
  NEVER use markdown table syntax (| --- | --- |) in any response.
  Tables render in wrong font in Claude Code UI.

RULE 2 — NO DOLLAR SIGNS IN PROSE:
  NEVER write $X.XX in responses (e.g. $40.09, $5.43, $2.44).
  Dollar signs trigger LaTeX/KaTeX math mode in Claude Code UI — everything between two $ signs
  renders in italic math font causing garbled text.
  INSTEAD use: USD 40.09 | +40.09 | 40.09 dollars | P&L: -40.09
  This applies to ALL dollar amounts: P&L, bet sizes, bankroll, profit goals.

SCHEDULED MONITOR:
  polybot-monitor: every 30 minutes, PID 75130 + session53.log (updated S53)
  Runs autonomously while Matthew is away. Maintains live bets, detects blocking.

THREE DISTINCT KALSHI CRYPTO BET TYPES (permanent — documented Session 51):
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M
    "BTC Up or Down in next 15 mins?" — UP/DOWN binary. ALL 4 are LIVE.
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD/KXETHD/KXSOLD/KXXRPD
    "Bitcoin price today at 5pm EDT?" — above/below price at clock time. PAPER-ONLY.
  TYPE 3 (Weekly/Friday THRESHOLD): Same KXBTCD series, future Friday date slot.
    "Bitcoin price on Friday at 5pm EDT?" — 770K volume (largest). NOT YET BUILT.
  DO NOT confuse these types.

DIRECTION FILTER SUMMARY (all four drift strategies):
  btc_drift: direction_filter="no" — only NO bets (YES has -1.50 USD/bet EV)
  eth_drift: direction_filter="yes" — only YES bets (NO has -0.212 USD/bet EV) — REVERSED!
  sol_drift: direction_filter="no" — only NO bets (sol NO 11/11 wins, +0.63 USD/bet EV)
  xrp_drift: NO filter yet — evaluate at 30 bets. xrp YES wins, NO loses.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* MAKE MORE MONEY — target +125 USD all-time. Currently at -28.01. Need +153.01.
* 20 USD hard min bankroll — never let bot trade below this floor
* THREE BET TYPES: 15-min direction (live), hourly/daily threshold (paper), weekly/Friday (not built)
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
* Never use dollar sign in prose responses.
