# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-15 (Session 74 research wrap — security hardening, Iron Laws, verify-revert loop)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 75)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 75).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 74 research wrap — 2026-03-15 ~10:30 UTC):
  Bot RUNNING PID 33894 → /tmp/polybot_session74.log
  All-time live P&L: -4.66 USD (dropped due to two large sniper losses this session)
  NOTE: Two major losses hit during session: SOL NO@96c x20 = -19.20 USD, XRP NO@97c x19 = -18.43 USD
  Both losses are within normal variance (SOL 94.5% WR, XRP now 98.4% WR first loss ever)
  Per PRINCIPLES.md: do NOT change sniper parameters — insufficient data for structural conclusion
  Tests: 1275 passing. Last commit: 0e6f417 (SEC-1/SEC-2/SEC-3 security hardening)

RESTART COMMAND (Session 75 — SAME LOG):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session74.log 2>&1 &
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

GRADUATION STATUS (2026-03-15 ~10:30 UTC):
  sol_drift_v1: 28/30 bets, Brier 0.176, P&L +13.48 USD — needs 2 more to Stage 2 eval
  xrp_drift_v1: 20/30 bets, Brier 0.270, P&L -1.71 USD — needs 10 more
  expiry_sniper_v1: 249 settled, 97.2% WR, +40.37 USD — LIVE 20 USD cap

SNIPER CURRENT STATE (critical — do not change parameters):
  BTC: 52 bets, 98.1% WR, +25.03 USD
  ETH: 62 bets, 98.4% WR, +21.05 USD
  SOL: 73 bets, 94.5% WR, -14.94 USD (4 losses — within variance per PRINCIPLES.md)
  XRP: 62 bets, 98.4% WR, +9.23 USD (first structural loss this session: XRP NO@97c x19 = -18.43 USD)
  DO NOT add asset-specific guards without 200+ bets per asset and p < 0.05.

SESSION 74 RESEARCH KEY CHANGES (2026-03-15 ~07:00-10:30 UTC):
  1. BUILT: scripts/weather_calibration.py — checks paper bets + infers outcomes from prices
     33 tests in tests/test_weather_calibration.py. Commit: 0c47366
  2. BUILT: BOUNDS.md + .claude/hooks/danger_zone_guard.sh + scripts/verify_change.sh
     + scripts/check_strategy_baseline.py (17 tests). Commit: 403f5d4
  3. FIXED: kalshi.py _dollars_to_cents bounds, KalshiAPIError truncation, .gitignore data/*.json
     27 tests in tests/test_kalshi_input_validation.py. Commit: 0e6f417
  4. CONFIRMED DEAD END: non-crypto 90c+ market scan — 0 found in 2000+ markets
  5. CONFIRMED DEAD END: annual BTC range markets (KXBTCMAXY/KXBTCMINY) — 9+ month lockup

PENDING TASKS (next session priority order):
  1. NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
     When Kalshi opens Round 1 KXNCAAMBGAME markets (games March 20-21)
  2. Weather calibration — check March 15 paper bets when finalized (est March 16-17)
     Run: python3 scripts/weather_calibration.py --pending
     Key: if LAX YES@8c loses, raise LAX edge threshold from 20% to 30%+
  3. Sol drift graduation — 28/30 → passive, notify when 30 bets
  4. XRP first structural loss analysis — XRP NO@97c x19 lost when XRP reversed
     Per PRINCIPLES.md: 1 loss at 62 bets is p=0.07, not significant. Wait for 200 bets.
  5. CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)

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
