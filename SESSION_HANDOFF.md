# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 54 WRAP — PID 11136, session54.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 55)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 55).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 54 WRAP — 2026-03-12 ~02:00 UTC):
  Bot RUNNING PID 11136 → /tmp/polybot_session54.log
  NOTE: Matthew will explicitly say "stop" to kill the old bot before new session starts fresh.
  When Matthew says "stop": pkill -f "python3 main.py"; sleep 3; verify 0 processes.
  Then restart with: bash scripts/restart_bot.sh 55

CHECK BOT HEALTH FIRST (Session 55 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 11136)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session55.log) — ONLY AFTER MATTHEW SAYS "stop":
  bash scripts/restart_bot.sh 55
  ⚠️ NEVER pipe restart_bot.sh through head/tail/grep — SIGPIPE will kill the running bot!
  ⚠️ Always run restart_bot.sh in isolation: `bash scripts/restart_bot.sh 55` only.
  ⚠️ After restart: if bot.pid is missing → echo "<new_PID>" > bot.pid immediately

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 54 WRAP — 2026-03-12 ~02:00 UTC):
  Bot: RUNNING (PID 11136) → /tmp/polybot_session54.log
  All-time live P&L: -10.96 USD (was -40.09 at S48 start — +29.13 USD gained across S49-S54)
  1041/1041 tests passing
  Last code commits: c527849 (xrp direction_filter=yes) + 40ec638 (progress docs)
  Today Mar 12 UTC: 0 settled (midnight UTC just passed, fresh day)

SESSION 54 CHANGES (fully committed):

  1. expiry_sniper_v1 IMPLEMENTED (wired prior context, confirmed S54)
     src/strategies/expiry_sniper.py + tests/test_expiry_sniper.py (37 tests)
     All 4 series: KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M. 90c+ threshold.
     Loop wired in main.py + setup/verify.py _GRAD entry.
     STATUS: 21/30 paper bets, 20W (95% win rate — strong early signal)

  2. xrp_drift direction_filter="yes" APPLIED (Matthew approved Session 54)
     commit c527849 — YES 83% (5/6) vs NO 36% (4/11) — reversed pattern like eth_drift
     Bot restarted (PID 11136). 17/30 live bets total (YES-only going forward).

  3. Fix: btc_price_feed → btc_feed variable name in main()
  4. Fix: has_open_position() wrong kwargs (commit 43bbd32)
  5. Monitoring: script reads bot.pid dynamically each check (stale PID prevention)

SESSION 54 FAILURES — READ THIS, NEXT CHAT DO BETTER:

  FAILURE 1 — MONITORING LOOP CHAOS (wasted 30+ min):
    Multiple overlapping monitoring cycles ran simultaneously. Old scripts not killed.
    bot.pid went missing after restart → all cycles showed BOT_DEAD (false alarms every cycle).
    PREVENTION: ALWAYS `pkill -f "polybot_monitor_cycle"` before starting any new cycle.
    Only ever ONE monitoring cycle running. Verify: ps aux | grep monitor_cycle | wc -l → 1.
    If bot.pid missing after restart: echo "<PID>" > bot.pid IMMEDIATELY.

  FAILURE 2 — "TOO SLOW FOR DEADLINE" REASONING (Matthew explicitly corrected):
    Dismissed hourly/daily bet development because "can't help in 2.5 days."
    CORRECT APPROACH: btc_daily_v1 paper IS ALREADY RUNNING (12 settled, 1/day cadence).
    Need 30 more days to accumulate data. START EVERYTHING NOW. Long timeline ≠ don't start.
    If any strategy takes 30 days to mature, that's 30 days of data accumulating while you
    work on other things. Never reject a good strategy because it's slow.

  FAILURE 3 — DROUGHT + CHAOS = NO CODE IMPROVEMENTS:
    Session spent most time on monitoring chaos. When crypto was bearish (YES 14-19c),
    zero live bets fired for hours. That's the perfect time to improve code.
    NEXT CHAT: When drought hits, run improvements, not monitoring debugging.

PRICE GUARD DROUGHT — PATTERN (S53/S54 confirmed):
  When crypto YES < 35c or > 65c, ZERO bets fire. THIS IS CORRECT. Not a bug.
  Logs: "Price Xc outside calibrated range (35-65c)" in every loop cycle.
  ACTION: None. Wait. Never disable. When drought hits: work on code instead.

LIVE STRATEGY STATUS (--graduation-status at Session 54 WRAP):
  btc_drift_v1:         STAGE 1 | 54/30 Brier 0.247 | direction_filter="no"  | 0 consec
  eth_drift_v1:         STAGE 1 | 81/30 Brier 0.247 | direction_filter="yes" | 0 consec
  sol_drift_v1:         STAGE 1 | 27/30 Brier 0.177 BEST | direction_filter="no" | 0 consec
    ⭐ 3 BETS FROM 30 — Stage 2 analysis ready the moment it hits 30. Highest lever remaining.
  xrp_drift_v1:         MICRO | 17/30 Brier 0.267 | direction_filter="yes" JUST APPLIED | 0 consec
  eth_orderbook_imbalance_v1: PAPER | 15/30 Brier 0.337 ❌ | DISABLED LIVE
  btc_lag_v1:           STAGE 1 | 45/30 Brier 0.191 | 0 signals/week — dead
  expiry_sniper_v1:     PAPER  | 21/30 | 20W (95%) | strong early signal

PENDING TASKS (Session 55 — PRIORITY ORDER):

  #1 HIGHEST IMPACT — SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets → milestone. Check --graduation-status when it fires.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.
     Impact: SOL bets double (avg 2-3 USD → avg 5-10 USD). Single biggest daily upside lever.

  #2 btc_daily_v1 PAPER SUPPORT (NOT "too slow to bother with"):
     Already running, 12 settled, direction_filter="no" active since S47.
     Need ~18 more days. Check its Brier at 30 bets. If < 0.30: surface live gate to Matthew.
     KXBTCD 5pm slot = 676K volume. Worth developing. Do not ignore.

  #3 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter bets to confirm.
     If YES stays 70%+: keep permanent. If regresses to 50%: remove.

  #4 ETH drift YES filter validation:
     81 bets total, Brier 0.247. Need 30 YES-only post-filter bets.

  #5 Expiry sniper paper phase:
     21/30, 95% wins. 9 more for live gate. When 30: check Brier, surface to Matthew.

  #6 FOMC window closes March 18 (6 days): 0/5 paper bets. Next FOMC: June 2026.

  #7 KXBTCD Friday slot (770K vol, largest Kalshi market): post-expansion gate.

  #8 btc_drift NO-only validation: ~10 NO-only settled, need 30. Weeks away.

125 USD PROFIT GOAL — SESSION 54 WRAP:
  All-time: -10.96 USD | Need +135.96 more
  S49-S54 rate: +29 USD improvement over ~2 days with direction filters.
  At current rate (~20 USD/day clean session): ~7 more trading days to goal.
  SOL Stage 2 promotion = single biggest accelerant.

RESPONSE FORMAT RULES (permanent — Matthew's instructions, BOTH mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose ($X.XX) — triggers LaTeX math mode → garbled text.
  USE INSTEAD: USD 10.96 | +29.13 | 10.96 dollars | P&L: -10.96

MONITORING LOOP — SESSION 55 STARTUP SEQUENCE:
  Step 1: pkill -f "polybot_monitor_cycle"   (kill any stale scripts FIRST — mandatory)
  Step 2: cat > /tmp/polybot_monitor_cycle.sh (rebuild the script fresh)
  Step 3: bash /tmp/polybot_monitor_cycle.sh  (run_in_background: true)
  Step 4: verify exactly ONE cycle: ps aux | grep monitor_cycle | grep -v grep | wc -l → 1
  Chains indefinitely: cycle completes → notification → Claude chains next. Matthew can be absent.

THREE DISTINCT KALSHI CRYPTO BET TYPES (permanent):
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M — ALL LIVE
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD — btc_daily_v1 paper accumulating (12/30 bets)
  TYPE 3 (Weekly/Friday THRESHOLD): KXBTCD Friday slots (770K vol) — NOT YET BUILT

DIRECTION FILTER SUMMARY (Session 54 final):
  btc_drift: filter="no"  — only NO bets
  eth_drift: filter="yes" — only YES bets (REVERSED! NO has negative EV)
  sol_drift: filter="no"  — only NO bets
  xrp_drift: filter="yes" — only YES bets (REVERSED! Applied S54, Matthew approved)

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  MAKE MORE MONEY — target +125 USD all-time P&L. Currently -10.96.
  START all long-term strategies NOW. "Too slow for deadline" is never valid reasoning.
  20 USD hard min bankroll floor.
  FONT FORMAT: no markdown tables, no dollar signs in prose. Both mandatory. Always.
