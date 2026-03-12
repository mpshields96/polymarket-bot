# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-12 (Session 56 WRAP — PID 19785, session56.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 57 — bot already running)

OVERNIGHT MONITORING SUMMARY (S56 overnight → S57 start, 2026-03-12):
  - Bot stayed alive all night (PID 19785 → died ~CDT 06:45, Matthew restarted → PID 44178)
  - Maintenance window: CDT 01:01-04:03 (3 hrs, longer than usual)
  - Post-maintenance: 0¢ prices on all crypto 15-min markets CDT 04:03-07:00+ (market makers
    not quoting in early morning hours — normal dead zone, price guard correctly blocking)
  - 0 new live bets placed overnight (bot was alive and evaluating, just nothing fired)
  - SESSION 57 STARTED: bot.pid=44178, /tmp/polybot_session57.log, kill switch clear,
    daily_loss restored 4.90 USD, consecutive reset to 0 (--reset-soft-stop)
  - eth_drift graduation_status shows "5 consec BLOCKED" — this is DB count for eth_drift
    only. Kill switch in-memory was reset to 0 on restart. NOT actually blocked.

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 57)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 57).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 56 WRAP — 2026-03-12 ~11:20 UTC):
  Bot RUNNING PID 44178 → /tmp/polybot_session57.log
  NOTE: Bot died (PID 19785) at ~06:45 UTC, polybot-monitor auto-restarted to PID 44178.
  NOTE: Matthew will explicitly say "stop" to kill the old bot before new session starts fresh.
  When Matthew says "stop": pkill -f "python3 main.py"; sleep 3; verify 0 processes.
  Then restart with: bash scripts/restart_bot.sh 57

CHECK BOT HEALTH FIRST (Session 57 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 44178)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session57.log) — ONLY AFTER MATTHEW SAYS "stop":
  bash scripts/restart_bot.sh 57
  ⚠️ NEVER pipe restart_bot.sh through head/tail/grep — SIGPIPE will kill the running bot!
  ⚠️ Always run restart_bot.sh in isolation: `bash scripts/restart_bot.sh 57` only.
  ⚠️ After restart: if bot.pid is missing → echo "<new_PID>" > bot.pid immediately

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 56 WRAP — 2026-03-12 ~11:20 UTC):
  Bot: RUNNING (PID 44178) → /tmp/polybot_session57.log (auto-restarted at 06:45 UTC)
  All-time live P&L: -34.59 USD (was -20.20 at S55 wrap — lost 14.39 this session)
  1041/1041 tests passing (no code changes S56)
  Last code commits: 214dcb3 (S54 wrap docs) — no new commits S55 or S56

SESSION 56 — NO CODE CHANGES (monitoring only):

  1. Extended price guard drought: ~12hrs from 00:49 UTC to 06:18+ UTC
     ALL markets showing YES=0c NO=0c — extreme bearish crypto session.
     Drought is CORRECT BEHAVIOR. Price guard protecting from unmodeled extremes.
     Bot was alive and evaluating every 10s the entire time.

  2. eth_drift: 9 live bets today, 3/9 wins, -11.06 USD live today.
     eth_drift all-time P&L: -11.51 USD (was +3.27 at S55 wrap — lost 14.78 USD).
     eth_drift now shows 5 consecutive losses in graduation_status.
     HOWEVER: kill switch in-memory consecutive counter was reset at 01:02:53 UTC
     by an xrp_drift win. Actual kill switch state = 0 consecutive (not 5).
     The "5 consec" in graduation_status is eth_drift-specific DB count, not the
     kill switch state. The kill switch limit is 8 for all-strategies combined.
     DO NOT change eth_drift parameters. This is variance. YES filter all-time
     still positive historically (only 3 losses out of 9 today is 33% win, but
     small sample in volatile session). PRINCIPLES.md governs.

  3. Research files from parallel S55 chat confirmed present:
     .planning/SNIPER_LIVE_PATH_ANALYSIS.md (23KB)
     .planning/KXBTCD_FRIDAY_FEASIBILITY.md (12KB)
     Both read-in but no code built this session (expansion gate not cleared).

SESSION 56 FAILURES — READ THIS, NEXT CHAT DO BETTER:

  FAILURE 1 — LOST 14.39 USD ALL-TIME THIS SESSION:
    eth_drift 9 bets with 3/9 win rate in extreme volatile session.
    This is variance in extreme conditions. Do NOT change direction filter.
    eth_drift YES all-time (before today's run) was +21.58 USD at 57% win rate.
    Today was an outlier session. Wait for 30+ post-filter bets before evaluating.

  FAILURE 2 — DROUGHT NOT USED PRODUCTIVELY (THIRD TIME):
    12+ hours of blocked markets. Zero code improvements made.
    S54 lesson → S55 repeated → S56 repeated again. THIS MUST STOP.
    Next session: when drought starts, immediately open SNIPER_LIVE_PATH_ANALYSIS.md
    and begin planning the sniper live path build (even if not building yet).
    Or: write tests. Or: review KXBTCD_FRIDAY_FEASIBILITY.md and document decision.
    ANY code-forward activity is better than just monitoring.

LIVE STRATEGY STATUS (--graduation-status at Session 56 WRAP 11:18 UTC):
  btc_drift_v1:         STAGE 1 | 54/30 Brier 0.247 | direction_filter="no"  | 0 consec | -11.12 USD
  eth_drift_v1:         STAGE 1 | 86/30 Brier 0.249 | direction_filter="yes" | 5 consec DB* | -11.51 USD
    *5 consec is DB count (eth_drift specific). Kill switch in-memory = 0 (reset by xrp win 01:02 UTC)
  sol_drift_v1:         STAGE 1 | 27/30 Brier 0.177 BEST | direction_filter="no" | 1 consec | +9.25 USD
    ⭐ 3 BETS FROM 30 — Stage 2 analysis ready the moment it hits 30.
  xrp_drift_v1:         MICRO | 18/30 Brier 0.261 | direction_filter="yes" S54 | 0 consec | -0.55 USD
  eth_orderbook_imbalance_v1: PAPER | 15/30 Brier 0.337 | DISABLED LIVE
  btc_lag_v1:           STAGE 1 | 45/30 Brier 0.191 | 0 signals/week — dead
  expiry_sniper_v1:     PAPER  | 75/30 | 97% wins | LIVE PATH DOES NOT EXIST — needs code build

PENDING TASKS (Session 57 — PRIORITY ORDER):

  #1 HIGHEST IMPACT — SOL STAGE 2 GRADUATION:
     27/30 live bets. 3 more bets → milestone. When it fires, check --graduation-status.
     If Brier < 0.25 + Kelly limiting: present Stage 2 promotion to Matthew.

  #2 DROUGHT PRODUCTIVITY — DO NOT REPEAT S54/S55/S56 PATTERN:
     When price guard drought starts: immediately pivot to code work.
     Best use: read SNIPER_LIVE_PATH_ANALYSIS.md, begin staging sniper build plan.
     Or: write tests for anything under-tested.
     NEVER spend a 12-hour drought just watching 0c/0c market evaluations.

  #3 EXPIRY SNIPER LIVE PATH BUILD (when expansion gate clears):
     .planning/SNIPER_LIVE_PATH_ANALYSIS.md exists — read it.
     ⚠️ GATE: Do NOT write any code without Matthew's explicit approval.
     Expansion gate: btc_drift must turn positive all-time first (-11.12 now).

  #4 KXBTCD FRIDAY SLOT (when expansion gate clears):
     .planning/KXBTCD_FRIDAY_FEASIBILITY.md exists — read it.

  #5 XRP direction filter validation:
     direction_filter="yes" applied S54. Need 30 YES-only post-filter live bets.
     Currently 18/30 — 12 more needed.

  #6 ETH drift YES filter validation:
     Need 30 YES-only post-filter bets. Still accumulating. DO NOT change based on today.

  #7 btc_daily_v1 PAPER SUPPORT:
     Already running. Need ~18 more days of paper data. Check Brier at 30.

  #8 FOMC window closes March 18 (6 days): 0/5 paper bets placed.

125 USD PROFIT GOAL — SESSION 56 WRAP:
  All-time: -34.59 USD | Need +159.59 more
  Goal is urgent: Matthew's Claude Max subscription depends on demonstrating this works.
  S56 rate: -14.39 USD (extreme volatile session, worst since S55).
  Key levers: (1) sol Stage 2 (3 bets away), (2) sniper live path, (3) drought productivity

RESPONSE FORMAT RULES (permanent — Matthew's instructions, BOTH mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose ($X.XX) — triggers LaTeX math mode → garbled text.
  USE INSTEAD: USD 10.96 | +29.13 | 10.96 dollars | P&L: -20.20

MONITORING LOOP — SESSION 57 STARTUP SEQUENCE:
  Use 5-min single-check chains (20-min scripts die with exit 144 on this system):
  For each check: sleep 300 && [pid check] && [python3 stats query]
  Run as run_in_background: true, chain continuously.
  Goal: sol milestone (27/30 → need 3 more) and watch for live bet drought.
  IMPORTANT: When drought starts, pivot to code work. Do NOT spend hours just monitoring.

THREE DISTINCT KALSHI CRYPTO BET TYPES (permanent):
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M — ALL LIVE
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD — btc_daily_v1 paper accumulating
  TYPE 3 (Weekly/Friday THRESHOLD): KXBTCD Friday slots (770K vol) — NOT YET BUILT

DIRECTION FILTER SUMMARY (Session 56 final):
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
