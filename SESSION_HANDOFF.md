# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-15 (Session 75 null wrap — bot running, immediately stopped by Matthew)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 76)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 76).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 75 null — 2026-03-15):
  Bot RUNNING PID 33894 → /tmp/polybot_session74.log
  All-time live P&L: -4.07 USD (recovering — sniper winning since S74 losses)
  Session 75 was NULL: started, bot confirmed running, Matthew said stop. No changes made.
  Tests: 1275 passing. Last commit: bd94a1f (Session 74 research wrap)

URGENT FINDING (from S74 monitoring — needs Matthew decision):
  96c and 97c buckets are structurally negative EV:
    96c YES: 17 bets, 94% WR → -13.35 USD cumulative (needs >96% to break even)
    96c NO:  13 bets, 92% WR → -9.69 USD cumulative
    97c NO:  12 bets, 92% WR → -15.43 USD cumulative
    97c YES: 11 bets, 100% WR → +2.90 USD (safe)
    95c: 100% both sides (safe). 98c: 100% both sides (safe).
    RECOMMENDATION: add fee-floor guard for price_cents >= 96 (same logic as 99c guard).
    Needs Matthew approval before implementing. First task for Session 76.
  Tests: 1275 passing. Last commit: bd94a1f (Session 74 research wrap docs)

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

GRADUATION STATUS (2026-03-15 ~09:30 UTC):
  sol_drift_v1: 28/30 bets, Brier 0.176, P&L +13.48 USD — needs 2 more to Stage 2 eval
  xrp_drift_v1: 20/30 bets, Brier 0.270, P&L -1.71 USD — needs 10 more
  expiry_sniper_v1: 251+ settled live bets — LIVE 20 USD cap, all-time live P&L -4.07 USD

SNIPER CURRENT STATE — URGENT PRICE GUARD NEEDED:
  96c YES: 17 bets, 94% WR → -13.35 USD (needs >96% WR to break even)
  96c NO:  13 bets, 92% WR → -9.69 USD
  97c NO:  12 bets, 92% WR → -15.43 USD
  97c YES: 11 bets, 100% WR → +2.90 USD (safe)
  95c: 100% both sides (safe). 98c: 100% both sides (safe).
  ACTION NEEDED: Matthew must decide on 96c/97c NO-side guard. Same logic as 99c guard.
  DO NOT implement without Matthew's explicit approval.

SESSION 74 RESEARCH KEY CHANGES (2026-03-15 ~07:00-10:30 UTC):
  1. BUILT: scripts/weather_calibration.py — checks paper bets + infers outcomes from prices
     33 tests in tests/test_weather_calibration.py. Commit: 0c47366
  2. BUILT: BOUNDS.md + .claude/hooks/danger_zone_guard.sh + scripts/verify_change.sh
     + scripts/check_strategy_baseline.py (17 tests). Commit: 403f5d4
  3. FIXED: kalshi.py _dollars_to_cents bounds, KalshiAPIError truncation, .gitignore data/*.json
     27 tests in tests/test_kalshi_input_validation.py. Commit: 0e6f417
  4. CONFIRMED DEAD END: non-crypto 90c+ market scan — 0 found in 2000+ markets
  5. CONFIRMED DEAD END: annual BTC range markets (KXBTCMAXY/KXBTCMINY) — 9+ month lockup

PENDING TASKS (Session 75 — PRIORITY ORDER):
  #0 URGENT — 96c/97c PRICE GUARD DECISION (needs Matthew approval):
     Show Matthew: 96c bucket -23.04 USD, 97c NO -15.43 USD. Same pattern as 99c (-14.85 USD fixed by guard).
     Proposed guard: block price_cents >= 96 on NO side, price_cents == 96 on YES side.
     Once approved: ~30 min build, same pattern as fee-floor guard in live.py.
  #1 NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
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
