# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 53 END — PID 75130, session53.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 54)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 54).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 54 start — 2026-03-11 ~20:15 UTC):
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

KEY STATE (Session 53 END — 2026-03-11 ~20:15 UTC):
* Bot: RUNNING (PID 75130) → /tmp/polybot_session53.log
* All-time live P&L: -17.54 USD (was -28.01 at S52 wrap — SESSION 53 GAINED +10.47!)
* 1003/1003 tests passing
* Last code commits: ca4a047 (trades.csv settlements) → e77db77 (autonomous monitoring) → c32a567 (CHANGELOG) → 7db9c32 (eth_drift filter)
* Today live P&L: +27.98 USD (73 settled, 58% win) — best day this week
* Consecutive losses (global kill switch): 0 (healthy)

SESSION 53 CHANGES (fully committed):
  1. eth_drift direction_filter="yes" ACTIVE — Matthew signed off, implemented, bot restarted
     Only YES signals fire for eth_drift. NO signals blocked. +2.54 USD/day improvement.
  2. Pre-existing test fix: TestATMPrioritySlot::test_no_regression_without_21utc_slot
     make_rel_market() now uses while loop +1hr to avoid hour 21
  3. polybot-monitor updated to PID 75130 + session53.log
  4. CLAUDE.md updated: Autonomous Monitoring Loop section added as MANDATORY startup
  5. Hourly EV analysis: confirmed bad hours (1, 7-8, 12-13, 17-18 UTC) = wrong-direction signals,
     all now blocked by direction filters. No further time-of-day changes needed (PRINCIPLES.md: need 30+ per bucket).

BET DROUGHT PATTERN — IMPORTANT (Session 53 finding):
  When all crypto markets are at YES < 35c or YES > 65c (extreme prices), ZERO bets fire.
  This is CORRECT behavior. The 35-65c price guard blocks signals at extreme prices where:
  (a) HFTs have already priced in certainty, (b) sigmoid model is extrapolating outside calibrated range.
  Example: 319-min bet drought 15:01-20:01 UTC on 2026-03-11 — markets at YES=25-32c (crypto bearish day).
  Check: "Price Xc outside calibrated range (35-65c)" logs = guard working, NOT a bug.
  Resolution: wait for next near-50c window; no action needed; never disable the price guard.

LIVE STRATEGY STATUS (from --graduation-status at Session 53 END):
  - btc_drift_v1: STAGE 1 — 53/30 Brier 0.249 | direction_filter="no" ACTIVE | 0 consec
  - eth_drift_v1: STAGE 1 — 75/30 Brier 0.246 | direction_filter="yes" ACTIVE (S53!) | 0 consec
    Accumulating YES-only settled bets post-filter (need 30 YES-only bets to validate filter).
  - sol_drift_v1: STAGE 1 — 25/30 Brier 0.171 BEST SIGNAL | direction_filter="no" ACTIVE | 0 consec
    5 more bets to formal graduation threshold. Watch for sol graduation checkpoint.
  - xrp_drift_v1: MICRO-LIVE — 16/30 Brier 0.272 | 2 consec
    xrp YES wins, NO loses (reversed). Consider direction_filter="yes" at 30 bets.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | DISABLED LIVE (Session 47)
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy

186 OPEN TRADES >48HR WARNING (from --health):
  All 186 are paper sports_futures_v1 bets on future sports events. NOT a settlement loop bug.
  Sports championship markets take months to settle. Ignore this warning.

PENDING TASKS (Session 54):
  1. sol_drift graduation watch: 25/30 — 5 more bets for formal graduation.
     When 30 bets reached: run --graduation-status + check Brier + confirm NO filter holding.
  2. xrp_drift direction analysis at 30 bets (currently 16/30).
     xrp YES outperforms NO (reversed pattern). Consider direction_filter="yes" when 30 bets.
  3. eth_drift YES filter validation: accumulate 30 YES-only settled bets post-filter.
     If 60%+ win rate holds, keep permanent. If reverts to 50%, remove.
  4. btc_drift NO-only validation at 30 NO-only settled bets (currently ~10, weeks away).
  5. eth_imbalance paper watchdog — if Brier < 0.25 at 30 bets, reconsider live.
  6. FOMC window: KXFEDDECISION-26MAR closes March 18. 0/5 settled. Will NOT make this cycle.
     Next FOMC window: June 2026.
  7. KXCPI strategy (post-expansion gate): 74 open markets. Build after sol + eth validated.
  8. KXBTCD Friday slot (770K volume): future work, post-expansion gate.
  9. Historical data enhancement: vol/regime features (trending vs consolidating) are the right
     next step but require 30+ live bets per regime bucket (PRINCIPLES.md). Log, do not build yet.
     Paper direction analysis valid supplement; paper P&L never valid for graduation/sizing.

125 USD PROFIT GOAL — ASSESSMENT (2026-03-11 session 53 END):
  Current all-time live P&L: -17.54 USD (IMPROVED from -28.01 — +10.47 gained this session!)
  To reach +125 USD profit = need +142.54 USD cumulative from here.
  Today rate: +27.98 USD (73 settled, 58% win) — exceptional.
  With direction filters all active: ~+20-28 USD/day is realistic.
  At +20/day average: ~7 more trading days to goal. At +15/day: ~10 days.
  Trajectory has IMPROVED this session. Direction filters are the primary driver.

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

AUTONOMOUS MONITORING LOOP (MANDATORY every session — see CLAUDE.md):
  Start background bash task using /tmp/polybot_monitor_cycle.sh at session start.
  Chains indefinitely: task finishes → notification fires → Claude responds without Matthew.
  Matthew requested 2-3 hr autonomous operation. This mechanism enables it.
  Do NOT let bot run unsupervised without this loop active.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* MAKE MORE MONEY — target +125 USD all-time. Currently at -17.54. Need +142.54.
* 20 USD hard min bankroll — never let bot trade below this floor
* THREE BET TYPES: 15-min direction (live), hourly/daily threshold (paper), weekly/Friday (not built)
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
* Never use dollar sign in prose responses.
