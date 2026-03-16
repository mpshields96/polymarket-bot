# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-16 (Session 85 research wrap — cross-league soccer threshold, NCAA scanner bugs fixed)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 86)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 86).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 85 wrap — 2026-03-16 UTC):
  Bot RUNNING PID 24138 → /tmp/polybot_session85.log
  All-time live P&L: -40.90 USD (today +4.10 USD live, 100% WR — 6 settled)
  Tests: 1325 passing. Last commit: 0867a0a (fix: sniper max_slippage_cents=3)
  Config: MAX_TRADE_PCT=15%, HARD_MAX=20 USD, ALL guards active (IL-5/IL-10/IL-10A/B/C/IL-11)
  NEW S85: max_slippage_cents=3 for expiry_sniper (blocks 7c orderbook divergence)
  Bankroll: ~100 USD (estimate)
  XRP drift: 23/30 live bets (needs 7 more for graduation eval)
  SOL drift: 30/30, Brier 0.191, READY FOR LIVE (already Stage 1)

CRITICAL GUARD UPDATE (Session 81 — commit 9dbf889):
  NEW guards added in src/execution/live.py (per-asset structural losses):
    - KXXRP YES@94c: BLOCKED (15 bets, 93.3% WR, -9.09 USD, need 94.9% break-even)
    - KXXRP YES@97c: BLOCKED (6 bets, 83.3% WR, -18.04 USD, need 98.0% break-even)
    - KXSOL YES@94c: BLOCKED (12 bets, 91.7% WR, -7.28 USD, need 94.9% break-even)
  Expected structural savings: ~34.41 USD going forward.
  All BTC/ETH at same prices remain open (both profitable at 94c+ historically).

SESSION 81 KEY CHANGES (2026-03-15 monitoring chat):
  1. SOL DRIFT GRADUATED (commit earlier this session):
     calibration_max_usd=5.0 → None in main.py. Sol drift now runs full Kelly + 20 USD cap.
     30/30 live bets, Brier 0.191, +1.23 USD all-time (Stage 1 confirmed)
  2. IRON LAWS IL-12 through IL-18 added to BOUNDS.md:
     Tests in tests/test_iron_laws.py (18 regression tests)
     Covers: Kelly/kill_switch sync, kalshi_payout NO-side conversion, settlement paper filter,
     live_trade_lock atomicity, _FIRST_RUN_CONFIRMED state, bankroll floor ordering, strategy_name
  3. SLIPPAGE GUARD added to main.py expiry_sniper_loop:
     _MAX_SLIPPAGE_CENTS = 3
     Blocks fills 3c+ below signal price (fixes trade 2786: signal@90c, fill@86c, -19.78 USD)
  4. PER-ASSET GUARDS added to src/execution/live.py (commit 9dbf889):
     KXXRP YES@94c, KXXRP YES@97c, KXSOL YES@94c — all blocked
     7 regression tests in TestPerAssetStructuralLossGuards
  5. Pattern 2 verify-revert PostToolUse hook deployed (commit cd9702f)

RESTART COMMAND (Session 86 — use session86.log):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session86.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": HISTORICAL. The 30% lifetime stop was DISABLED in S34.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

## NEW IN SESSION 74: SAFETY INFRASTRUCTURE ADDED

### Iron Laws + Danger Zone PreToolUse Hook (Pattern 1)
  BOUNDS.md at project root — 18 Iron Laws with file:line, incident history, test references
  .claude/hooks/danger_zone_guard.sh — fires before any edit to TIER 1 files:
    src/execution/live.py, src/risk/kill_switch.py, src/risk/sizing.py
  Runs full test suite (1319 tests in ~4s) before allowing edit — exits 2 on failure.
  .claude/settings.json updated with PreToolUse hook wiring.

### Verify-Revert Loop (Pattern 2)
  scripts/verify_change.sh — stash→pytest→baseline check→restore or drop
  scripts/check_strategy_baseline.py — DB win-rate query vs threshold (17 tests)
  PostToolUse hook: auto-revert danger zone edits if tests fail (commit cd9702f)
  Usage: bash scripts/verify_change.sh expiry_sniper 0.95

---

GRADUATION STATUS (2026-03-16 UTC — Session 85):
  sol_drift_v1: 30/30 bets, Brier 0.191, P&L +1.23 USD — GRADUATED (calibration_max=None, full Kelly)
  xrp_drift_v1: 23/30 bets, Brier 0.258, P&L -1.26 USD — needs 7 more
  expiry_sniper_v1: 75+ live bets, P&L +306 USD all-time — CORE ENGINE

SNIPER BUCKET STATUS (full guard stack — do NOT change without Matthew approval):
  BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
  BLOCKED (per-asset S81): KXXRP YES@94c, KXXRP YES@97c, KXSOL YES@94c
  PROFITABLE: 91c-95c BTC/ETH both sides, 97c YES all assets, 98c YES all assets
  BTC/ETH sniper: historically 98-99% WR — core engine, do not touch

PENDING TASKS (Session 86 — PRIORITY ORDER):
  #1 NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
     BUGS FIXED in Session 85 (commit f848adb) — was broken since creation, now works:
       Bug 1: fetch_odds_api_games args were swapped → HTTP 401 on every run
       Bug 2: comparison.sharp_prob → AttributeError (now uses sharp_yes_prob/sharp_no_prob)
     3 regression tests added (TestNCAATournamentScannerBugs, 1322 tests total)
     Focus: 1v16 underpriced at 93-95c, 2v15 at 90-94c. Round 1 tip-offs March 20-21.
  #2 Weather calibration — check paper bets when March 15-16 bets settle
     Currently only 2/41 settled. Run: python3 scripts/weather_calibration.py --pending
     Or direct DB query (script hangs on API): sqlite3 data/polybot.db "SELECT strategy, COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END) FROM trades WHERE strategy LIKE 'weather%' AND result IS NOT NULL GROUP BY strategy"
  #3 Soccer in-play sniper live monitoring — FIRST LIVE OPPORTUNITY:
     EPL: BRE vs WOL (March 30), UCL QF 1st legs: March 31 (ARS, MCI, CFC, SPO) + April 1 (BAR, LFC, BMU, ATM)
     Pre-game >= 0.60 threshold → 75% MID_GAME rate (6/8 games in Session 85 analysis)
     Decision: deploy sniper if UCL favorite leads 2-0+ at 90c+ with 30+ min remaining
  #4 XRP drift graduation watch — 23/30, needs 7 more bets
     When 30/30: run direction filter eval (NO side vs YES side WR split)
  #5 CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)
  #6 KXGDP speed-play — April 30 (GDP release, KXGDP at 0c/0 volume as of March 16 — check April 23-24)

SESSION 85 RESEARCH FINDINGS (2026-03-16):
  CROSS-LEAGUE SOCCER THRESHOLD ANALYSIS (57 games, 4 leagues):
  - Pre-game >= 0.60 → 75% MID_GAME rate (6/8 games). Revised from "45c" estimate in S83-84.
  - UCL: 44% MID_GAME (4/9), La Liga: 44% (4/9), EPL: 13% (2/15), Serie A: 20% (1/5) + mixed 17% (2/12)
  - FLB mechanism: market prices 10% reversal prob at 90c, actual rate 3-5% (confirmed across leagues)
  - Key filter: UCL and La Liga best for soccer sniper (higher market quality + pre-game >= 0.60)
  NCAA SCANNER BUG FIXES (commit f848adb):
  - Bug 1: args swapped in fetch_odds_api_games call → HTTP 401 on every run since creation
  - Bug 2: comparison.sharp_prob AttributeError → fixed to use sharp_yes_prob/sharp_no_prob per side
  - 3 regression tests added. Scanner now works. Run March 17-18.
  WEATHER CALIBRATION: only 2/41 paper bets settled as of March 16. Need 3-4 more weeks data.
  KXGDP: market at 0c, 0 volume — not liquid. Check April 23-24 (1 week before April 30 BEA release).

SESSION 84 RESEARCH FINDINGS (2026-03-15):
  SOCCER IN-PLAY SNIPER — EDGE VALIDATED (structural mechanism confirmed):
  - Mechanism: Favorite-Longshot Bias (FLB) — market implies 10% reversal at 90c, true rate ~3-5%
  - UCL analysis (10 games): 40% MID_GAME rate (4/10), avg hold 85 min, avg pre-game 0.46
  - FALSE POSITIVE RATE: 0/3 (Liverpool peak 0.60, Arsenal peak 0.64, Barcelona 0.43 — none hit 90c in losses)
  - EPL: 2/17 MID_GAME at 33c and 38c — La Liga 45c threshold doesn't apply; revised to 60c+
  - INTERNATIONAL BREAK: all games pushed — EPL March 30, UCL QF March 31/April 1
  - Volume anomalies: RMA 766K vs MCI 72K (low volume on unfavorite side = our market)

RESEARCH STATE:
  scripts/soccer_candle_analyzer.py — UCL/EPL MID_GAME analysis via Kalshi candlestick API
  scripts/cpi_release_monitor.py — run April 10, 08:30 ET
  scripts/ncaa_tournament_scanner.py — run March 17-18, 1 credit/call, Round 1 March 20-21
  scripts/weather_edge_scanner.py — daily scan, 5-city GEFS vs Kalshi
  scripts/weather_calibration.py — check paper bet outcomes and calibration
  Dead ends (cumulative): sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper,
    tennis/NCAAB at current scale, weather NO at 99c, KXBTCD near-expiry sniper,
    FOMC cross-market chain arb, sniper maker mode, NCAA totals/spreads,
    KXMV parlay markets (zero volume), NBA in-game sniper (75x worse capital efficiency),
    BNB/BCH/DOGE 15M (dormant series), KXBTCD hourly non-5PM slots (0 volume),
    FOMC March 2026 (no Kalshi market), non-crypto 90c+ markets (0/2000 scanned),
    annual BTC range markets KXBTCMAXY/KXBTCMINY (9+ month lockup, drift zone)
  Open leads: Soccer in-play sniper (UCL March 31/April 1 — first live test, 60c+ pre-game filter),
    NCAA Round 1 (March 17-18 — scanner now fixed), weather calibration (4+ weeks needed),
    XRP drift graduation (23/30), CPI speed-play (April 10), KXGDP speed-play (April 30)
