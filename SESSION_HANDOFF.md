# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 55 WRAP — PID 11136, session54.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 56)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 56).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 55 WRAP — 2026-03-12 ~03:30 UTC):
  Bot RUNNING PID 11136 → /tmp/polybot_session54.log
  NOTE: Matthew will explicitly say "stop" to kill the old bot before new session starts fresh.
  When Matthew says "stop": pkill -f "python3 main.py"; sleep 3; verify 0 processes.
  Then restart with: bash scripts/restart_bot.sh 56

CHECK BOT HEALTH FIRST (Session 56 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 11136)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session56.log) — ONLY AFTER MATTHEW SAYS "stop":
  bash scripts/restart_bot.sh 56
  ⚠️ NEVER pipe restart_bot.sh through head/tail/grep — SIGPIPE will kill the running bot!
  ⚠️ Always run restart_bot.sh in isolation: `bash scripts/restart_bot.sh 56` only.
  ⚠️ After restart: if bot.pid is missing → echo "<new_PID>" > bot.pid immediately

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 55 WRAP — 2026-03-12 ~03:30 UTC):
  Bot: RUNNING (PID 11136) → /tmp/polybot_session54.log
  All-time live P&L: -20.20 USD (was -10.96 at S54 wrap — lost 9.24 this session)
  1041/1041 tests passing (no code changes S55)
  Last code commits: 214dcb3 (S54 wrap docs) — no new commits S55
  Today Mar 12 UTC: 7 settled live | 3W/4L | -0.76 USD today live

SESSION 55 — NO CODE CHANGES (monitoring + analysis only):

  1. Expiry sniper PAPER milestone: 38/30 paper bets (up from 21/30 at S54 wrap)
     31W/1L = 97% win rate. Paper P&L +180 USD (inflated — extreme price fills unrepresentative).
     Pre-live checklist analysis: NOT ready. Live path DOES NOT EXIST in expiry_sniper_loop().
     Expansion gate not cleared (btc_drift -11.12 all-time). Keep paper.

  2. Session characterized by extreme crypto volatility:
     YES prices bounced 0c → 99c → 53c → 80c → 99c multiple times in 2 hours.
     Price guard correctly blocked all signals when YES outside 35-65c.
     Zero live bets from ~02:31 UTC onward (1+ hour drought at session end).

  3. Parallel research chat started (new session): working on:
     - Sniper live path technical analysis → .planning/SNIPER_LIVE_PATH_ANALYSIS.md
     - KXBTCD Friday slot feasibility → .planning/KXBTCD_FRIDAY_FEASIBILITY.md

SESSION 55 FAILURES — READ THIS, NEXT CHAT DO BETTER:

  FAILURE 1 — LOST 9.24 USD ALL-TIME THIS SESSION:
    eth_drift YES bets at 02:18 (-4.84) and 02:31 (-4.40) lost in bearish/volatile session.
    This is variance, not a signal failure (YES all-time = +21.58 USD, 57% win rate).
    DO NOT change direction filters based on this. Wait for 30+ post-filter bets per PRINCIPLES.md.

  FAILURE 2 — DROUGHT NOT USED PRODUCTIVELY:
    1+ hour without live bets. Should have worked on code or docs instead of watching.
    S54 lesson still applies: when drought hits, pivot to code improvement. S55 repeated this error.

  FAILURE 3 — MONITORING SCRIPT KEPT DYING (exit 144):
    The 20-min background bash cycle kept failing. Fell back to 5-min single checks.
    5-min checks work fine but are less elegant. Next chat: use 5-min single-check chains.

PRICE GUARD DROUGHT — PATTERN (S53/S54/S55 confirmed):
  When crypto YES < 35c or > 65c, ZERO bets fire. THIS IS CORRECT. Not a bug.
  Logs: "Price Xc outside calibrated range (35-65c)" in every loop cycle.
  ACTION: None. Wait. Never disable. When drought hits: work on code instead.
  S55 PATTERN: extreme volatility (bouncing 0c-99c in single sessions) = multiple droughts/session.

LIVE STRATEGY STATUS (--graduation-status at Session 55 WRAP):
  btc_drift_v1:         STAGE 1 | 54/30 Brier 0.247 | direction_filter="no"  | 0 consec | -11.12 USD
  eth_drift_v1:         STAGE 1 | 83/30 Brier 0.249 | direction_filter="yes" | 2 consec | +3.27 USD
  sol_drift_v1:         STAGE 1 | 27/30 Brier 0.177 BEST | direction_filter="no" | 1 consec | +9.25 USD
    ⭐ 3 BETS FROM 30 — Stage 2 analysis ready the moment it hits 30. Highest lever remaining.
  xrp_drift_v1:         MICRO | 17/30 Brier 0.267 | direction_filter="yes" S54 | 0 consec | -0.94 USD
  eth_orderbook_imbalance_v1: PAPER | 15/30 Brier 0.337 | DISABLED LIVE
  btc_lag_v1:           STAGE 1 | 45/30 Brier 0.191 | 0 signals/week — dead
  expiry_sniper_v1:     PAPER  | 38/30 | 97% wins | LIVE PATH DOES NOT EXIST — needs code build

PENDING TASKS (Session 56 — PRIORITY ORDER):

  #1 HIGHEST IMPACT — SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets → milestone. Check --graduation-status when it fires.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.
     Impact: SOL bets scale up (calibration_max_usd=None already — Kelly + $5 cap).
     Actually: sol is already Stage 1. 30 bets just confirms Brier threshold for Stage 2 ($10 cap).

  #2 EXPIRY SNIPER LIVE PATH BUILD (when expansion gate clears):
     Research chat producing SNIPER_LIVE_PATH_ANALYSIS.md. Read it first session this completes.
     Must be built right: live executor integration, trade_lock, kill_switch, _announce_live_bet.
     Gate: btc_drift must turn positive all-time before enabling new live strategy.

  #3 KXBTCD FRIDAY SLOT (when expansion gate clears):
     Research chat producing KXBTCD_FRIDAY_FEASIBILITY.md. Read when available.
     770K volume = largest Kalshi series. Post-gate.

  #4 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets to confirm.
     Currently 17/30 — 13 more needed.

  #5 ETH drift YES filter validation:
     Need 30 YES-only post-filter bets. Filter applied ~S53. Continuing to accumulate.

  #6 btc_daily_v1 PAPER SUPPORT:
     Already running. Need ~18 more days of paper data. Check Brier at 30.

  #7 FOMC window closes March 18 (6 days): 0/5 paper bets placed.

125 USD PROFIT GOAL — SESSION 55 WRAP:
  All-time: -20.20 USD | Need +145.20 more
  Goal is urgent: Matthew's Claude Max subscription depends on demonstrating this works.
  S55 rate: -0.76 USD today (bearish volatile session).
  Key levers in priority order: (1) sol Stage 2 (3 bets away), (2) sniper live path, (3) let drift accumulate

RESPONSE FORMAT RULES (permanent — Matthew's instructions, BOTH mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose ($X.XX) — triggers LaTeX math mode → garbled text.
  USE INSTEAD: USD 10.96 | +29.13 | 10.96 dollars | P&L: -20.20

MONITORING LOOP — SESSION 56 STARTUP SEQUENCE:
  Use 5-min single-check chains (20-min scripts die with exit 144 on this system):
  For each check: sleep 300 && [pid check] && [python3 stats query]
  Run as run_in_background: true, chain 4 times per 20-min cycle.
  Goal: sol milestone (27/30 → need 3 more) and watch for live bet drought.

THREE DISTINCT KALSHI CRYPTO BET TYPES (permanent):
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M — ALL LIVE
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD — btc_daily_v1 paper accumulating
  TYPE 3 (Weekly/Friday THRESHOLD): KXBTCD Friday slots (770K vol) — NOT YET BUILT

DIRECTION FILTER SUMMARY (Session 55 final):
  btc_drift: filter="no"  — only NO bets
  eth_drift: filter="yes" — only YES bets (REVERSED — NO has negative EV)
  sol_drift: filter="no"  — only NO bets
  xrp_drift: filter="yes" — only YES bets (REVERSED — Applied S54, Matthew approved)

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. Urgent. Claude Max renewal depends on this.
  DO NOT change parameters under pressure. PRINCIPLES.md always governs.
  DO NOT enable new live strategies without (a) expansion gate clearing and (b) Matthew approval.
