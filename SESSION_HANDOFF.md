# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-15 (Session 78 research — bet size reduced 15%→10%, 20→15 USD cap)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 79)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 79).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 78 research — 2026-03-15 ~14:00 UTC):
  Bot RUNNING PID 61970 → /tmp/polybot_session78.log
  All-time live P&L: ~-25 USD (sniper ~+46 USD, drift ~-71 USD)
  Tests: 1281 passing. Last commit: a3192d1 (risk: lower bet size caps S78)
  Bankroll: ~113 USD (Kalshi API, 13:30 UTC)

SESSION 78 KEY CHANGES:
  1. DEPLOYED 98c NO negative-EV bucket guard (commit dd53aac — monitoring chat):
     - 98c NO-side: BLOCKED (28 bets, 92.9% WR, -25.54 USD historical)
     - 98c YES-side: KEPT (20 bets, 100% WR, +3.02 USD profitable)
     - IL-11 added to BOUNDS.md.
  2. BET SIZE REDUCED (commit a3192d1 — research chat, Matthew directive):
     MAX_TRADE_PCT: 15% → 10% | HARD_MAX_TRADE_USD: 20 → 15 USD — ACTIVE IN RUNNING BOT
     At 113 USD bankroll: max bet now ~11.29 USD (was 16.95 USD)
     At 150 USD bankroll: max bet ~14.99 USD | At 200+ USD: capped at 15 USD
  3. SNIPER BUCKET STATUS (all blocked buckets — do NOT change without Matthew approval):
     - BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
     - PROFITABLE: 91c-95c both sides, 97c YES (100% WR), 98c YES (100% WR)
  4. TODAY P&L: -43.74 USD live — ALL 5 losses were pre-guard bets placed before 09:25 UTC restart
     Post-guard sniper: 35+ wins, 1 valid loss (YES@94c — structural variance)

SESSION 76 OVERNIGHT KEY CHANGES:
  1. DEPLOYED 96c/97c negative-EV bucket guard (commit cd32feb):
     - 96c both sides: BLOCKED (31 bets, 93.5% WR, -22.44 USD historical)
     - 97c NO-side: BLOCKED (13 bets, 92.3% WR, -15.03 USD historical)
     - 97c YES-side: KEPT (11 bets, 100% WR, +2.90 USD profitable)
     - 6 regression tests added. BOUNDS.md updated with IL-10.
     - Saves ~37.47 USD structural drag going forward.
  2. RESTORED sol_drift Stage 1 cap (commit 05bcd65):
     - Bankroll crossed 100 USD → sizing auto-promoted to Stage 2 (10 USD cap)
     - Single loss at 7.41 USD on sol_drift today triggered investigation
     - Manual graduation gate (30 bets + Brier + Kelly limiting_factor) not yet met
     - calibration_max_usd=5.0 restored. Re-evaluate after 30th bet settles (1 more needed).
  3. FULL GUARD AUDIT completed — all 10 Iron Laws verified in live.py ✓
  4. Security verified: .env NOT in git history, .gitignore working, credentials safe ✓
  5. Overnight monitor started at /tmp/polybot_night_monitor.log (5-min cycle checks)

RESTART COMMAND (Session 78 — use session76.log):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session76.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": HISTORICAL. The 30% lifetime stop was DISABLED in S34.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

## NEW IN SESSION 74: SAFETY INFRASTRUCTURE ADDED

### Iron Laws + Danger Zone PreToolUse Hook (Pattern 1)
  BOUNDS.md at project root — 9 Iron Laws with file:line, incident history, test references
  .claude/hooks/danger_zone_guard.sh — fires before any edit to TIER 1 files:
    src/execution/live.py, src/risk/kill_switch.py, src/risk/sizing.py
  Runs full test suite (1275 tests in ~3s) before allowing edit — exits 2 on failure.
  .claude/settings.json updated with PreToolUse hook wiring.

### Verify-Revert Loop (Pattern 2)
  scripts/verify_change.sh — stash→pytest→baseline check→restore or drop
  scripts/check_strategy_baseline.py — DB win-rate query vs threshold (17 tests)
  Usage: bash scripts/verify_change.sh expiry_sniper 0.95

### Security Fixes (SEC-1/2/3)
  SEC-1: _dollars_to_cents() and _fp_to_int() now bounds-check parsed values
  SEC-2: KalshiAPIError body truncated to 300 chars in str() — not in .body attr
  SEC-3: data/*.json added to .gitignore — scan files reveal strategy focus areas
  27 new tests in tests/test_kalshi_input_validation.py

---

GRADUATION STATUS (2026-03-15 ~13:15 UTC):
  sol_drift_v1: 29/30 bets, Brier 0.184, P&L +6.07 USD — needs 1 more to Stage 2 eval
    Stage 1 cap at 5 USD (restored S76 overnight). When 30th settles: check Brier + limiting_factor.
  xrp_drift_v1: 20/30 bets, Brier 0.270, P&L -1.71 USD — needs 10 more
  expiry_sniper_v1: 292 live bets, all-time P&L +46.36 USD — PROFITABLE CORE

SNIPER BUCKET ANALYSIS (post-S76 guard — updated overnight):
  BLOCKED (96c, 97c NO): working ✓ — no new bets since restart
  PROFITABLE BUCKETS: 91c-95c both sides (100% WR), 98c (100% WR), 97c YES (100% WR)
  MONITORED — current-era analysis (bets placed since HARD_MAX raised to 15-20 USD):
    90c YES: 2/3 current-era bets (67% WR, -17.91 USD). 1 loss = XRP reversal. BTC 100%.
      Not systematic. Old-era bets had much smaller size. DO NOT BLOCK at 3 bets.
    92c NO: 5/6 current-era bets (83% WR). 1 loss = SOL reversal. BTC 3/3 = 100%.
      Not systematic. Need 20+ current-era bets before evaluating guard.
    93c YES: OLD concern resolved. Current-era = 9/9 = 100% WR. Old-era small bets skewed.
    Summary: SOL and XRP more volatile → single reversals at 90-92c. BTC = perfect.
      All are within normal statistical variance. No new guards needed at current data.
  DONE S78: MAX_TRADE_PCT lowered 15%→10%, HARD_MAX_TRADE_USD 20→15 USD per Matthew directive.
    At 10% with 113 USD bankroll, one 90c loss = -11.29 USD = 10% drawdown per bet. Active now.

SESSION 74 RESEARCH KEY CHANGES (2026-03-15 ~07:00-10:30 UTC):
  1. BUILT: scripts/weather_calibration.py — checks paper bets + infers outcomes from prices
     33 tests in tests/test_weather_calibration.py. Commit: 0c47366
  2. BUILT: BOUNDS.md + .claude/hooks/danger_zone_guard.sh + scripts/verify_change.sh
     + scripts/check_strategy_baseline.py (17 tests). Commit: 403f5d4
  3. FIXED: kalshi.py _dollars_to_cents bounds, KalshiAPIError truncation, .gitignore data/*.json
     27 tests in tests/test_kalshi_input_validation.py. Commit: 0e6f417
  4. CONFIRMED DEAD END: non-crypto 90c+ market scan — 0 found in 2000+ markets
  5. CONFIRMED DEAD END: annual BTC range markets (KXBTCMAXY/KXBTCMINY) — 9+ month lockup

PENDING TASKS (Session 79 — PRIORITY ORDER):
  #1 Sol drift graduation — 29/30, 1 more bet needed. Stage 1 cap at 5 USD.
     When 30th bet settles: check Brier < 0.25 + limiting_factor==kelly → raise cap to 10 USD
  #2 NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
     When Kalshi opens Round 1 KXNCAAMBGAME markets (games March 20-21)
  #3 Weather calibration — check paper bets when settled (March 15 markets settle ~04:00 UTC March 16)
     Run: python3 scripts/weather_calibration.py --pending
     Key bets: LAX YES@8c, CHI NO@91c, DEN NO@7c (NO@36c on DEN T49 likely LOST — Denver warm)
  #4 Weather edge scanner — run EARLY MORNING UTC (04:00-08:00 UTC) when GEFS date = open market date
     python3 scripts/weather_edge_scanner.py --min-edge 0.10
     TIMING: scanner only useful early morning when GEFS forecast = open market date
  #5 Monitor sniper at new bet sizes (10% pct cap, 15 USD hard max — active since S78 restart)
     Expected: max bet ~11.29 USD at 113 USD bankroll, growing with bankroll up to 15 USD
  #6 CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)

RESEARCH STATE:
  scripts/cpi_release_monitor.py — run April 10, 08:30 ET
  scripts/ncaa_tournament_scanner.py — run March 17-18, 1 credit/call, Round 1 March 20-21
  scripts/weather_edge_scanner.py — daily scan, 5-city GEFS vs Kalshi
  scripts/weather_calibration.py — NEW: check paper bet outcomes and calibration
  Dead ends (cumulative): sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper,
    tennis/NCAAB at current scale, weather NO at 99c, KXBTCD near-expiry sniper,
    FOMC cross-market chain arb, sniper maker mode, NCAA totals/spreads,
    KXMV parlay markets (zero volume), NBA in-game sniper (75x worse capital efficiency),
    BNB/BCH/DOGE 15M (dormant series), KXBTCD hourly non-5PM slots (0 volume),
    FOMC March 2026 (no Kalshi market), non-crypto 90c+ markets (0/2000 scanned),
    annual BTC range markets KXBTCMAXY/KXBTCMINY (9+ month lockup, drift zone)
  Open leads: NCAA Round 1 (March 17-18), weather calibration (4+ weeks needed),
    sol drift graduation (28/30), CPI speed-play (April 10)
