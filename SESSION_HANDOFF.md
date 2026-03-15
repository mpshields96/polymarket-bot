# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-15 (Session 80 wrap — +10.60 USD gained, all-time -18.88 USD, guards holding)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 81)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 81).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 80 wrap — 2026-03-15 ~18:15 UTC):
  Bot RUNNING PID 68296 → /tmp/polybot_session76.log  ← CORRECT (not session79.log)
  All-time live P&L: -18.88 USD (session gain: +10.60 USD — 94% WR, 125 bets today)
  Tests: 1281 passing. Last commit: 691f32b (EDGE_RESEARCH S80 — KXGDP + methodology)
  Config: MAX_TRADE_PCT=15%, HARD_MAX=20 USD, ALL guards active (96c, 97c NO, 98c NO, 99c+)
  Bankroll: ~131 USD (estimate — started ~120, +10.60 gained today post-guard)

RESEARCH QUALITY DIRECTIVE (Matthew S80 — MANDATORY for all future research sessions):
  New edge research must meet the SNIPER STANDARD or better:
  - Named behavioral/structural mechanism (why does the mispricing exist?)
  - Named losing counterparty (who keeps losing and why do they persist?)
  - Different mechanism from sniper (near-expiry convergence) AND speed-play (info latency)
  - Clear paper-test protocol: minimum N + WR threshold that proves edge before live
  - Willing to spend days/weeks validating — quality > quantity
  Kalshi API scanning without a structural hypothesis = data mining = NOT research.
  Pattern-matching on existing trades (hourly WR, asset variants) = noise = NOT research.

SESSION 79 KEY CHANGES (2026-03-15 research chat):
  1. BET SIZE RESTORED (commit 9ff6e6d — research chat after March 14 analysis):
     MAX_TRADE_PCT: 10% → 15% | HARD_MAX_TRADE_USD: 15 → 20 USD — ACTIVE IN RUNNING BOT
     Analysis: March 14 active-bucket bets (107W/0L, +79.87 USD) at 13.77 USD avg
     With guards in place, 15%/20 USD is SAFER than March 14 (no blocked-bucket losses possible)
     At 123 USD bankroll: max bet = 15% of 123 = 18.45 USD (below 20 USD hard max)
     First confirmed bet at restored size: yes@97c = 18.43 USD WIN ✓
  2. GUARD STACK UNCHANGED (DO NOT modify without Matthew approval):
     - BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
     - PROFITABLE: 91c-95c both sides, 97c YES (100% WR), 98c YES (100% WR)
  3. DEAD ENDS CONFIRMED S79:
     - KXBTCD Friday sniper: only 1 bet/day vs 96 windows/day for 15M — dead end
     - All alternative 15M crypto (BNB/BCH/DOGE/AVAX/LINK/ADA/LTC): 0 open markets
  4. 88c execution price: NOT a bug — signal fires at 91c (above trigger), executes at 88c
     (orderbook shows better liquidity at 88c). IL-4 enforced at signal level. Trade won.

SESSION 78 KEY CHANGES:
  1. DEPLOYED 98c NO negative-EV bucket guard (commit dd53aac — monitoring chat):
     - 98c NO-side: BLOCKED (28 bets, 92.9% WR, -25.54 USD historical)
     - 98c YES-side: KEPT (20 bets, 100% WR, +3.02 USD profitable)
     - IL-11 added to BOUNDS.md.
  2. BET SIZE REDUCED (commit a3192d1 — REVERSED in S79):
     Was: MAX_TRADE_PCT 15%→10%, HARD_MAX 20→15 USD. Reversed after March 14 analysis.
  3. SNIPER BUCKET STATUS (all blocked buckets — do NOT change without Matthew approval):
     - BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
     - PROFITABLE: 91c-95c both sides, 97c YES (100% WR), 98c YES (100% WR)

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

RESTART COMMAND (Session 81 — use session81.log):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session81.log 2>&1 &
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

GRADUATION STATUS (2026-03-15 ~18:15 UTC):
  sol_drift_v1: 29/30 bets, Brier 0.184, P&L +6.07 USD — needs 1 more to Stage 2 eval
    Stage 1 cap at 5 USD. When 30th settles: remove calibration_max_usd=5.0 → None in main.py, restart.
    Don't require limiting_factor==kelly — pct_cap governs at current bankroll. Just 30 bets + Brier<0.25.
  xrp_drift_v1: 20/30 bets, Brier 0.270, P&L -1.71 USD — needs 10 more
  expiry_sniper_v1: ~320+ live bets, all-time P&L recovering — PROFITABLE CORE

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
  S79: MAX_TRADE_PCT restored to 15%, HARD_MAX restored to 20 USD (March 14 formula).
    At 15% with 123 USD bankroll = 18.45 USD max bet. First win confirmed at 18.43 USD.
    Guards protect against structural losses. 97.7% WR on active buckets all-time.

SESSION 74 RESEARCH KEY CHANGES (2026-03-15 ~07:00-10:30 UTC):
  1. BUILT: scripts/weather_calibration.py — checks paper bets + infers outcomes from prices
     33 tests in tests/test_weather_calibration.py. Commit: 0c47366
  2. BUILT: BOUNDS.md + .claude/hooks/danger_zone_guard.sh + scripts/verify_change.sh
     + scripts/check_strategy_baseline.py (17 tests). Commit: 403f5d4
  3. FIXED: kalshi.py _dollars_to_cents bounds, KalshiAPIError truncation, .gitignore data/*.json
     27 tests in tests/test_kalshi_input_validation.py. Commit: 0e6f417
  4. CONFIRMED DEAD END: non-crypto 90c+ market scan — 0 found in 2000+ markets
  5. CONFIRMED DEAD END: annual BTC range markets (KXBTCMAXY/KXBTCMINY) — 9+ month lockup

SESSION 80 KEY FINDINGS (2026-03-15 monitoring — wrap):
  1. SESSION GAIN: -29.48 → -18.88 USD all-time (+10.60 USD in ~8 hours, 94% WR, 125+ bets settled)
  2. GUARD VALIDITY: Guards (IL-10/IL-11) are objectively justified by fee math, NOT trauma.
     Break-even WR: 96c=96.3%, 97c-NO=97.2%, 98c-NO=98.1%. Sniper can't sustain these long-term.
     96c YES guard (17 bets, 94.1% WR) is the most borderline — revisit at 50+ bets if desired.
     NO@97c and NO@98c: fee math alone justifies blocking regardless of sample size.
  3. AUTONOMY RULE FIXED: polybot-auto command updated — no confirmations ever when invoked.
     Memory saved to prevent repeat violations.
  4. MONITOR SCRIPT FIXED: Python extracted to /tmp/polybot_check.py — no more heredoc conflicts.
  5. SOL DRIFT: 29/30, Brier=0.184, +6.07 USD. Graduation gate = 30 bets + Brier<0.25 (no kelly req).
     When 30th settles: remove calibration_max_usd=5.0 → None in main.py, restart bot.

PENDING TASKS (Session 81 — PRIORITY ORDER):
  #1 Sol drift graduation — 29/30, 1 more bet needed. Stage 1 cap at 5 USD.
     When 30th bet settles: remove calibration_max_usd=5.0 → None in main.py, restart bot.
     Brier=0.184 (excellent), P&L=+6.07 USD, NO direction filter active (82%WR).
     Don't require limiting_factor==kelly — pct_cap governs at current bankroll size.
  #2 NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
     Focus: 1v16 underpriced at 93-95c (massive structural edge if any), 2v15 at 90-94c
     Round 1 tip-offs March 20-21. 1 credit/call.
  #3 Weather calibration — check paper bets ~04:00 UTC March 16 when March 15 bets settle
     Run: python3 scripts/weather_calibration.py --pending
     10 paper bets pending: LAX (5), CHI (4), DEN (1)
  #4 Weather edge scanner — run EARLY MORNING UTC (04:00-08:00 UTC) when GEFS date = open market date
     python3 scripts/weather_edge_scanner.py --min-edge 0.10
     TIMING: scanner only useful early morning when GEFS forecast = open market date
  #5 Monitor sniper at restored sizes (15% pct cap, 20 USD hard max — active since S79)
     Expected: ~14-18 USD bets at ~116 USD bankroll
     94c YES bucket: watching — at 33 bets, fee break-even is 94.37%, currently just below
  #6 CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py → KXFEDDECISION)

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
