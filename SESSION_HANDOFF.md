# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-14 (Session 72 research — weather expansion + calibration)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 73)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 73).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 72 research wrap — 2026-03-14 ~23:50 UTC):
  Bot LIKELY STILL RUNNING PID 17982 — check with: ps aux | grep "[m]ain.py"
  Log: /tmp/polybot_session68.log (unchanged — research chat didn't touch bot)
  All-time live P&L: +11.35 USD approx (was +7.63 at session start, ran all day)
  Tests: 1195 passing (was 1164). Last commit: 1c5f12c (S72 weather expansion)

RESTART COMMAND (Session 73 — NEW LOG):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session73.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": HISTORICAL. The 30% lifetime stop was DISABLED in S34.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 72 research — 2026-03-14 ~23:50 UTC):
  Bot: CHECK WITH ps aux (may still be PID 17982 → /tmp/polybot_session68.log)
  All-time live P&L: ~+11.35 USD (check with --report)
  Bankroll: ~90+ USD (DB authoritative)
  Tests: 1195 passing
  Last commit: 1c5f12c (S72 weather expansion to 5 cities)

SESSION 72 RESEARCH KEY CHANGES (this chat — 2026-03-14):
  1. BUILT: scripts/weather_edge_scanner.py — 5-city GEFS vs Kalshi scanner (31 tests). Commit: db979f5
     First run found 18 opportunities: LAX +75.3% edge, CHI +70.2%, DEN +64.3%, NYC +58.1%
  2. FIX: parse_temp_bracket in weather_forecast.py — now handles 78-79deg bracket format.
     Was returning None for KXHIGH* bracket markets silently skipping them. Commit: fed5f4c
     3 regression tests added.
  3. EXPANDED: Weather loop now covers all 5 Kalshi KXHIGH* cities (LAX, CHI, DEN, MIA added).
     src/data/weather.py: added CITY_DEN, CITY_MIA, KALSHI_WEATHER_CITIES, build_gefs_feed().
     main.py: 4 new weather_loop tasks (weather_lax_v1, weather_chi_v1, weather_den_v1, weather_mia_v1).
     Commit: 1c5f12c. Restart required for new loops to activate.
  4. RESEARCH: Weather calibration analysis vs Kalshi settlements (7-day history):
     NYC: well-calibrated (±2F). Edges are HIGH CONFIDENCE.
     DEN: well-calibrated (±2-3F). Edges are HIGH CONFIDENCE.
     LAX: 4-7F systematic warm bias in Open-Meteo. LAX edges need calibration validation.
     CHI: high variance (5-12F discrepancy). CHI edges need paper data to trust.
  5. RESEARCH: Sniper 199-bet bucket analysis:
     90-94c: +58.95 USD (69% ROI) — PROFIT ENGINE
     95-98c: +11.93 USD (14.6% ROI) — positive, do NOT add guard
     99c: -14.85 USD (-75% ROI) — GUARD CODED (8d252ae) BUT NOT ACTIVE until restart
  6. Tests: 1195 passing (was 1164). +31 new tests.

PENDING TASKS (Session 73 — PRIORITY ORDER):

  #1 RESTART BOT — activates 99c pre-execution guard + new 5-city weather loops.
     BOTH uncommitted code changes now need restart: 99c guard (8d252ae) + weather expansion (1c5f12c).
     Without restart: missing 5 new city loops + losing money on every 99c sniper bet.
     Restart command above. New log: /tmp/polybot_session73.log.

  #2 SOL STAGE 2 GRADUATION — need 2 more settled bets (28/30 live).
     Each check: ./venv/bin/python3 main.py --graduation-status | grep sol
     When 30/30 achieved: run full Stage 2 analysis (10 USD max/bet evaluation).

  #3 NCAA TOURNAMENT (bracket drops March 15 evening, Round 1 = March 20-21).
     Check KXNCAAMBGAME on March 17-18 for 1-vs-16 matchups at 90c+.
     Use scripts/ncaab_live_monitor.py to scan. NO auto-trading until evaluated.

  #4 WEATHER PAPER DATA (collecting now, all 5 cities after restart):
     Check after 4+ weeks for calibration. Trust NYC/DEN first (well-calibrated).
     Run: python3 scripts/weather_edge_scanner.py --min-edge 0.10 for daily scan.

  #5 MONITOR CONSECUTIVE LOSSES (watch for streak during market volatility).
     Kill switch fires at 8 consecutive. Daily check: grep "consecutive" /tmp/polybot_session*.log | tail -5

  MONITORING NOTE FOR S73:
     Background tasks on this system timeout at ~18-20 min (exit 144 = SIGHUP).
     Use 5-min SINGLE-CHECK cycles. Helper at /tmp/polybot_check.py — rewrite each session.

125 USD PROFIT GOAL:
  All-time: ~+11.35 USD. Need ~+113.65 more.
  Sniper is profit engine. 99c guard (after restart) recovers 14.85 USD.
  Key levers: (1) restart for 99c guard + weather loops, (2) sol Stage 2 graduation,
              (3) weather edges (paper now, live after 4+ weeks calibration)

RESPONSE FORMAT RULES (permanent — both mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose — triggers LaTeX math mode.
  USE: "40.09 USD" or "P&L: -39.85". NEVER "$40.09".
  Matthew will terminate chat for violations of either rule.

DIRECTION FILTER SUMMARY (permanent):
  btc_drift: filter="no"  — only NO bets (MICRO-LIVE)
  eth_drift: filter="yes" — only YES bets (MICRO-LIVE)
  sol_drift: filter="no"  — only NO bets (STAGE 1)
  xrp_drift: filter="yes" — only YES bets (MICRO)

IMPORTANT — MARCH 1 HARD STOP IN --health (not a blocker):
  --health shows HARD STOP from 2026-03-01. This is HISTORICAL.
  The 30% lifetime stop was DISABLED in Session 34 (restore_realized_loss is display-only).
  No kill_switch.lock file exists. DO NOT be blocked by this. Just restart normally.

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. URGENT. Claude Max renewal depends on this.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.

RESEARCH FILES (for context if continuing R&D):
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S72 additions at end, sections 38-42)
  scripts/weather_edge_scanner.py — 5-city GEFS vs Kalshi daily edge scanner (NEW S72)
  tests/test_weather_edge_scanner.py — 31 tests
  scripts/edge_scanner.py — Kalshi-vs-Pinnacle scanner (game-in-progress filter)
  scripts/ncaab_live_monitor.py — ESPN + Kalshi NCAAB live cross-check tool
  scripts/cpi_release_monitor.py — CPI release monitor (run April 10 08:30 ET)
