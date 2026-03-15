# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-15 (Session 72 research cont — fee-floor bug fixed)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 74)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 74).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 72 research cont — 2026-03-15 ~03:00 UTC):
  Bot RUNNING PID 32120 → /tmp/polybot_session73.log
  Log: /tmp/polybot_session73.log (restarted 22:54 UTC to activate fee-floor fix)
  All-time live P&L: +13.40 USD (--report authoritative)
  Tests: 1198 passing. Last commit: 1d12f46 (fee-floor guard fix)

RESTART COMMAND (Session 74 — NEW LOG):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session74.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": HISTORICAL. The 30% lifetime stop was DISABLED in S34.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 72 research cont — 2026-03-15 ~03:00 UTC):
  Bot: PID 32120 → /tmp/polybot_session73.log (CONFIRMED RUNNING)
  All-time live P&L: +13.40 USD (was +7.63 at S72 start — gained +5.77 today)
  Bankroll: ~147 USD (DB authoritative)
  Tests: 1198 passing
  Last commit: 1d12f46 (fee-floor guard fix — blocks 99c/1c raw execution prices)

WEATHER LOOPS STATUS (confirmed active after 22:00 UTC restart):
  All 5 city loops now running and placing paper trades:
  NYC: weather_forecast_v1 → KXHIGHNY (original loop, ~45F March 15)
  LAX: weather_lax_v1 → KXHIGHLAX (active — placed 5 paper trades, 80.1F forecast)
  CHI: weather_chi_v1 → KXHIGHCHI (active — placed 5 paper trades, 57.8F forecast)
  DEN: weather_den_v1 → KXHIGHDEN (active — placed 1 paper trade, 51.5F forecast)
  MIA: weather_mia_v1 → KXHIGHMIA (active — placed 3 paper trades, 80.3F forecast)
  First paper trades placed for all cities at ~21:59 UTC for March 15 markets.
  CHI YES@26c (GEFS 96.8%) and LAX YES@8c (GEFS 93.5%) are highest-confidence signals.

GRADUATION STATUS (checked 2026-03-15 ~02:10 UTC):
  sol_drift_v1: 28/30 bets, Brier 0.176, P&L +13.48 USD — needs 2 more to Stage 2
  xrp_drift_v1: 19/30 bets, Brier 0.266, P&L -1.12 USD — needs 11 more
  expiry_sniper_v1: 75/30 bets — LIVE uncapped

SESSION 72 RESEARCH KEY CHANGES (2026-03-14 to 2026-03-15):
  1. BUILT: scripts/weather_edge_scanner.py — 5-city GEFS vs Kalshi scanner (31 tests). Commit: db979f5
     First run found 18 opportunities: LAX +75.3% edge, CHI +70.2%, DEN +64.3%, NYC +58.1%
  2. FIX: parse_temp_bracket in weather_forecast.py — now handles 78-79deg bracket format.
     Was returning None for KXHIGH* bracket markets silently skipping them. Commit: fed5f4c
     3 regression tests added.
  3. EXPANDED: Weather loop now covers all 5 Kalshi KXHIGH* cities (LAX, CHI, DEN, MIA added).
     src/data/weather.py: added CITY_DEN, CITY_MIA, KALSHI_WEATHER_CITIES, build_gefs_feed().
     main.py: 4 new weather_loop tasks. Commit: 1c5f12c.
     NOTE: Bot needed 2nd restart (22:00 UTC) because S72 first restart was BEFORE commit 1c5f12c.
  4. RESEARCH: Weather calibration analysis vs Kalshi settlements (7-day history):
     NYC: well-calibrated (±2F). Edges are HIGH CONFIDENCE.
     DEN: well-calibrated (±2-3F). Edges are HIGH CONFIDENCE.
     LAX: 4-7F systematic warm bias in Open-Meteo. LAX edges need calibration validation.
     CHI: high variance (5-12F discrepancy). CHI edges need paper data to trust.
  5. RESEARCH: Sniper 199-bet bucket analysis:
     90-94c: +58.95 USD (69% ROI) — PROFIT ENGINE
     95-98c: +11.93 USD (14.6% ROI) — positive, do NOT add guard
     99c: -14.85 USD (-75% ROI) — GUARD CODED (8d252ae) + ACTIVE (restart at 22:00 UTC)
  6. DOCS: Off-peak double limits promotion documented in SESSION_HANDOFF + AUTONOMOUS_CHARTER + POLYBOT_INIT.
     Commit: 3c59276.
  7. BUG FIX: 99c fee-floor guard in live.py (S72 cont — commit 1d12f46).
     Bug: NO@99c → YES-equiv 1c passes price_guard_max=99 check. Trade 2111 placed at 99c.
     Fix: explicit raw price_cents >= 99 || <= 1 block BEFORE YES-equiv conversion.
     3 new regression tests in TestSniperFeeFlorBlock.
  8. Tests: 1198 passing (was 1164). +34 new tests total this session.

PENDING TASKS (Session 74 — PRIORITY ORDER):

  #1 SOL STAGE 2 GRADUATION — need 2 more settled bets (28/30 live).
     Each check: ./venv/bin/python3 main.py --graduation-status | grep sol
     When 30/30 achieved: run full Stage 2 analysis (10 USD max/bet evaluation).

  #2 NCAA TOURNAMENT (bracket drops March 15 evening US time, Round 1 = March 20-21).
     Check KXNCAAMBGAME on March 17-18 for 1-vs-16 matchups at 90c+.
     Use scripts/ncaab_live_monitor.py to scan. NO auto-trading until evaluated.
     First Four games: March 19 (First Four = March 19-20).

  #3 WEATHER CALIBRATION DATA — check March 14 settlements (available ~04:00+ UTC March 15).
     Run after 04:00 UTC: python3 scripts/weather_edge_scanner.py --min-edge 0.10
     Also check KXHIGHNY-26MAR14, KXHIGHLAX-26MAR14, etc. settlement results vs GEFS forecast.
     Key question: LAX warm bias (4-7F) vs GEFS — does GEFS actually beat Kalshi pricing?
     March 15 paper bets: LAX YES@8c (GEFS 93.5%), CHI YES@26c (GEFS 96.8%), MIA NO@72c.
     Check these settlements tomorrow (2026-03-16) for calibration.

  #4 WEATHER PAPER DATA (collecting now, all 5 cities — data starts March 15).
     Check after 4+ weeks for calibration. Trust NYC/DEN first (well-calibrated).
     Run: python3 scripts/weather_edge_scanner.py --min-edge 0.10 for daily scan.

  #5 MONITOR CONSECUTIVE LOSSES (watch for streak during market volatility).
     Kill switch fires at 8 consecutive. Daily check: grep "consecutive" /tmp/polybot_session*.log | tail -5

  MONITORING NOTE FOR S74:
     Background tasks on this system timeout at ~18-20 min (exit 144 = SIGHUP).
     Use 5-min SINGLE-CHECK cycles. Helper at /tmp/polybot_check.py — rewrite each session.

125 USD PROFIT GOAL:
  All-time: +13.40 USD. Need ~+111.60 more.
  Sniper is profit engine. Fee-floor fix (1d12f46) NOW ACTIVE — blocks all 99c bets.
  Key levers: (1) sol Stage 2 graduation (+5 USD/bet potential at 10 USD max),
              (2) weather edges (paper calibration building — live after 4+ weeks),
              (3) NCAA 1-vs-16 seed sniper opportunities (March 19-21).
  WARNING: Today's P&L was -3.67 (16 bets, 15W/1L). The 1 loss = the 99c NO bug (trade 2111)
  which lost 14.85 USD. Without the bug, today would be ~+11.18 USD from 15 wins.

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
  MARCH PROMOTION (active thru 2026-03-27): Off-peak = outside 8AM-2PM ET.
    During off-peak: 5-hour rolling limit DOUBLES. Auto-applied, no action needed.
    Both chats benefit. Schedule heavy research/monitoring work during off-peak hours.
    Peak hours (8AM-2PM ET / 5-11AM PT): standard limits apply, use budget carefully.

RESEARCH FILES (for context if continuing R&D):
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S72 additions at end, sections 38-42)
  scripts/weather_edge_scanner.py — 5-city GEFS vs Kalshi daily edge scanner (NEW S72)
  tests/test_weather_edge_scanner.py — 31 tests
  scripts/edge_scanner.py — Kalshi-vs-Pinnacle scanner (game-in-progress filter)
  scripts/ncaab_live_monitor.py — ESPN + Kalshi NCAAB live cross-check tool
  scripts/cpi_release_monitor.py — CPI release monitor (run April 10 08:30 ET)
