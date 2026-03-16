# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-16 22:25 UTC (Session 90 monitoring wrap — +51.21 USD all-time, Stage 2 bankroll!)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 91)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 91).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 90 monitoring — 2026-03-16 22:25 UTC):
  Bot RUNNING PID 31365 → /tmp/polybot_session90.log
  All-time live P&L: +51.21 USD (TODAY +96.21 USD live, 143 settled, 92% WR)
  Tests: 1388 passing. Last commit: 2d1ffed (fix: return_exceptions=True crash fix S90)
  Config: MAX_TRADE_PCT=15%, HARD_MAX=20 USD, ALL guards active (IL-5/IL-10/IL-10A/B/C/IL-11/IL-19/IL-20)
  STAGE 2: bankroll 213.34 USD → sizing.py Stage 2 (100-250 USD) → drift bets cap at 10 USD/bet
  XRP drift: 30/30 live bets — GRADUATION THRESHOLD MET (Brier 0.258 < 0.30)
    direction_filter="yes" already active since S54. Keeping MICRO-live (calibration_max=0.01).
    Reason: btc_drift and eth_drift BOTH demoted to micro-live in S60 (48%/49% WR). Conservative.
  SOL drift: 34/30 Stage 1 (full Kelly + 20 USD cap, graduated S81)
  SESSION 90 MONITORING KEY EVENTS (2026-03-16 21:17–22:25 UTC):
  - Bot crashed at 17:22 UTC (PID 18772 → 31365) — Binance.US WebSocket 1011 keepalive timeout
    All 4 feeds disconnected simultaneously. Auto-restarted successfully.
  - XRP drift hit 30/30 — graduation analyzed. direction_filter="yes" confirmed working.
    Keeping MICRO-live: btc_drift and eth_drift both demoted micro in S60 (main.py confirms).
  - Guard validation: IL-19 (KXSOL YES@97c) CONFIRMED WORKING — no bets since 05:58 UTC.
    YES@90c: 9 bets, 89% WR < 90.9% break-even. WATCH at 20+ bets.
  - NCAA scanner: 0 edges March 16. Run again today (March 17 UTC — lines NOW mature).
  - Strategy analyzer "losing buckets: 98/97/96c" = STALE (includes pre-guard data). Guards working.
  SESSION 90 RESEARCH KEY BUILDS (2026-03-16 earlier):
  - CRASH FIX: asyncio.gather() return_exceptions=True (commit 2d1ffed)
  - WEATHER DEAD END CONFIRMED: paper 25-57% WR vs 80%+ needed. Do NOT pursue live weather.
  - NCAA scanner: 0 edges (March 16, lines not mature). Re-run March 17-18.
  - XRP direction_filter="yes" confirmed already in place — no code change needed.
  SESSION 88 KEY BUILDS (2026-03-16 overnight):
  - IL-19 guard (commit a4f33ed): KXSOL YES@97c BLOCKED — 8 bets, 87.5% WR, -17.18 USD, 97% WR needed
    Loss at KXSOL15M-26MAR160200-00 triggered analysis. Guard is now live in execution/live.py.
    3 regression tests in TestPerAssetStructuralLossGuards (test_live_executor.py).
  - post_only taker fallback (commit e9dc10f): When drift strategies get 400 "post only cross",
    execute() now retries immediately as taker (post_only=False). Recovered 50+ missed trades/session.
    Error logs confirm 0 post_only_cross errors since restart at 02:32 CDT.
  KEY FINDINGS (Session 88 overnight research):
  - 39/39 sniper wins since March 16 00:00 UTC (full guard stack). Guards are working.
  - STRATEGY ANALYZER TIMEZONE BUG FIXED: was showing 0 USD today — now shows correct UTC value.
  - YES@97c appearing negative was historical KXXRP loss — guard IL-10B already in place.
    Non-XRP YES@97c (BTC/ETH/SOL): 100% WR, profitable.
  - SOL YES@93c: 14 bets, 92.9% WR vs 93% break-even. WATCH but don't guard yet (need 20+ bets).
  - Time-of-day loss pattern was entirely pre-guard era. No time-of-day filter needed.
  - Soccer sniper paper module: scripts/soccer_sniper_paper.py — 19 tests, ready for March 21+.

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

RESTART COMMAND (Session 91 — use session91.log):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session91.log 2>&1 &
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

GRADUATION STATUS (2026-03-16 UTC — Session 90 research):
  sol_drift_v1: 34/30 bets, Brier 0.191, +9.04 USD — GRADUATED Stage 1 (full Kelly, calibration_max=None)
  xrp_drift_v1: 30/30 bets DONE — direction_filter="yes" ALREADY ACTIVE since S54
    YES-only (post-filter): 19 bets, 63.2% WR. Need 30 YES-only bets for Stage 1 eval. Keep micro-live.
  expiry_sniper_v1: 140+ live bets today, 91% WR, +92.22 USD today — CORE ENGINE

SNIPER BUCKET STATUS (full guard stack — do NOT change without Matthew approval):
  BLOCKED: 96c both sides (IL-10), 97c NO (IL-10), 98c NO (IL-11), 99c/1c (IL-5)
  BLOCKED (per-asset S81): KXXRP YES@94c, KXXRP YES@97c, KXSOL YES@94c
  BLOCKED (per-asset S88): KXSOL YES@97c (IL-19 — 87.5% WR, 97% needed to break even)
  BLOCKED (per-asset S88): KXXRP YES@95c (IL-20 — 90% WR, 95% needed to break even)
  PROFITABLE: 91c-95c BTC/ETH/SOL, 97c YES BTC/ETH, 98c YES all assets
  BTC/ETH sniper: historically 98-99% WR — core engine, do not touch

S85 KEY FIXES (commits f848adb + 0867a0a):
  1. NCAA scanner: 2 bugs fixed (HTTP 401 + AttributeError). Now fully functional.
  2. Sniper slippage guard: max_slippage_cents=3 added to execute(). Blocks orderbook
     divergence of 3c+ from signal. Closed gap between main.py 3c guard and live.py 10c guard.
  3. Guard audit: all 5+ bet negative-EV buckets confirmed guarded. SOL YES 93c watch at 20+ Stage 1 bets.
  4. 6 new regression tests (1325 total).

SESSION 87 KEY BUILDS (2026-03-16):
  1. scripts/strategy_analyzer.py (NEW) — self-learning pattern detector
     Run at session start: ./venv/bin/python3 scripts/strategy_analyzer.py --brief
     Surfaces: profitable/losing sniper buckets, direction filter validation, graduation status.
     Saves to data/strategy_insights.json. 23 tests.
  2. POLYBOT_INIT.md updated: Rule 1 step 6 = run strategy_analyzer --brief at startup.
  3. NCAA scanner verified: 64 KXNCAAMBGAME markets open, 0 edges above 3% today (March 16).
     Lines mature March 17-18. Run then.

PENDING TASKS (Session 91 — PRIORITY ORDER):
  #0 NCAA scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03 (March 17 UTC = TODAY)
     Lines now mature. Round 1 tip-offs March 20-21. 1 credit/call. SDATA: 339/500 (68%).
     Watch: Purdue 96c, UConn 95c, Illinois 96c — public money may push below sharp books.
  #1 YES@90c resolved — KXXRP YES@90c single loss (-19.8 USD, 1 bet) skewed the aggregate.
     BTC/ETH/SOL YES@90c: all 100% WR, profitable. Not a guard candidate.
     Re-check KXXRP YES@90c at 5+ bets. Currently 1 bet, noise only.
  #2 Investigate auto-restart mechanism — bot auto-restarted at 17:22 UTC (PID 18772 → 31365)
     Something is running the restart command. Find what it is. Document in CLAUDE.md.
     Check: crontab -l, launchctl list | grep poly, nohup jobs, /tmp/polybot_confirm.txt.
  #3 XRP drift Stage 1 eval — currently at 30/30 with direction_filter="yes". Keeping MICRO.
     When 30 YES-only bets accumulate (currently ~19 post-filter), re-evaluate Stage 1 promotion.
     IMPORTANT: btc_drift and eth_drift were DEMOTED from Stage 1 in S60 (48%/49% WR).
     Check main.py lines 2902 and 2933 for "S60: demoted" comments before any promotion.
  #4 Strategy_analyzer improvement — DONE in S90 research (commit dfc04c6)
     Fixed: added _KNOWN_GUARDS, _is_guarded(), detect_guard_gaps(). Now shows GUARDED/PARTIAL GUARD
     vs unguarded paths. Guard stack clean = no false "Guard candidate" alarms. 9 new tests.
  #5 Soccer in-play sniper — SCRIPT READY (scripts/soccer_sniper_paper.py):
     *** URGENT: UCL R16 2ND LEGS ARE TOMORROW (March 17) AND MARCH 18 ***
     SESSION_HANDOFF WAS WRONG: dates are NOT March 31/April 1.

     MARCH 17 (TOMORROW — start script before kickoff!):
       17:30 UTC start: python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR17
         Game 1: Bodo/Glimt vs Sporting CP — 17:45 UTC — SPO eligible (64c pre-game)
         Game 2: Arsenal vs Leverkusen — 20:00 UTC — ARS eligible (77c pre-game)
         Game 3: Real Madrid vs Man City at Etihad — 20:00 UTC — MCI eligible (67c pre-game)
         (Chelsea 46c and PSG 33c do NOT qualify — below 60c threshold)

     MARCH 18 (day after tomorrow):
       17:30 UTC start: python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR18
         Game 1: Newcastle vs Barcelona at Camp Nou — 17:45 UTC — BAR eligible (62c pre-game)
         Game 2: Atalanta vs Bayern Munich at Allianz — 20:00 UTC — BMU eligible (72c pre-game)
         Game 3: Galatasaray vs Liverpool at Anfield — 20:00 UTC — LFC eligible (76c pre-game)
         (Atletico 39c, Tottenham 36c do NOT qualify)

     Expected: ~40% of 6 eligible teams cross 90c mid-game = 2-3 paper bets placed
     Need 3+ paper wins before live activation. UCL QF March 31/April 1 = 2nd legs.
     La Liga/EPL resume March 21-22. Pre-game >= 0.60 threshold.
  #6 SOL YES 93c bucket watch — check at 20+ Stage 1 bets (currently 14 total)
  #7 CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)
  #8 KXGDP speed-play — April 30 (GDP release, check April 23-24)
  #9 Weather calibration — FAILING (CHI=57%, LAX=50%, MIA=25%, DEN=33% WR, needs 80%+)
     Do NOT live-trade weather. Check at 20+ bets per city (end of April).

SESSION 88 KEY BUILDS (2026-03-16 overnight):
  1. IL-19 guard (commit a4f33ed): KXSOL YES@97c BLOCKED in src/execution/live.py
     3 regression tests: test_sol_yes_at_97c_blocked, test_btc_yes_at_97c_not_blocked, test_eth_yes_at_97c_not_blocked
  2. post_only taker fallback (commit e9dc10f): drift strategies now retry as taker on "post only cross"
     KalshiAPIError.body dict checked for details=="post only cross" → immediate taker retry
     Resolves 50+ missed drift trades/session.
  3. BOUNDS.md updated with IL-19 entry (stats, incident ref, test refs).
  4. SESSION S87 KEY BUILDS (carried forward):
     scripts/soccer_sniper_paper.py (NEW) — paper bet execution on mid-game 90c+ crossings
     SoccerSniperExec + SoccerPaperTracker classes. 19 tests, all passing.
     Run for UCL QF 1st legs March 31/April 1 (ARS 76c, LFC 77c, BMU 74c, MCI 64c pre-game)

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
