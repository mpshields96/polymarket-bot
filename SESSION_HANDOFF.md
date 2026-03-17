# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-17 01:45 UTC (Session 94 continuation — IL-22 guard, fee analysis, guard audit)
# ═══════════════════════════════════════════════════════════════

## ⚠️ UCL SOCCER SNIPER — TIME-SENSITIVE
## March 17 (TODAY): Start at 17:25 UTC CDT=12:25
##   python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR17
##   Game 1: SPO (Sporting CP) @64c — kicks 17:45 UTC
##   Game 2: ARS (Arsenal) @77c — kicks 20:00 UTC
##   Game 3: MCI (Man City) @67c — kicks 20:00 UTC
## March 18: Same command with --date 26MAR18
##   BAR@62c, BMU@72c, LFC@76c eligible (all above 60c threshold)

## COPY-PASTE THIS TO START A NEW SESSION (Session 95)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 95).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 94 continuation — 2026-03-17 01:45 UTC):
  Bot RUNNING PID 65713 → /tmp/polybot_session93.log
  All-time live P&L: +45.96 USD (794 total bets settled, 536 sniper bets)
  Tests: 1410 passing. Last commit: 53c337c (feat: IL-22 guard KXSOL NO@92c)
  Guards: IL-5 through IL-22 ALL ACTIVE. Guard stack VERIFIED COMPLETE as of S94.
  STAGE 2: bankroll ~213 USD → sizing.py Stage 2 → drift bets cap at 10 USD/bet
  XRP drift: 32 total (21 YES-only post-filter). Need 9 MORE YES-only bets for Stage 1 eval.
    direction_filter="yes" active. Keeping MICRO-live. ETA: ~March 20-21 for 30 YES-only.
  SOL drift: 38/30 Stage 1 (full Kelly + 20 USD cap, 71% WR, Brier 0.195)
  Orderbook imbalance: asymmetric filter active (min_yes=52c, max_no=44c). Paper-only, no restart.
  SESSION 90 MONITORING KEY EVENTS (2026-03-16 21:17–23:10 UTC):
  - Bot crashed at 17:22 UTC (PID 18772 → 31365) — Binance.US WebSocket 1011 keepalive timeout
    All 4 feeds disconnected simultaneously. Auto-restarted successfully.
  - XRP drift hit 30/30 — graduation analyzed. direction_filter="yes" confirmed working.
    Keeping MICRO-live: btc_drift and eth_drift both demoted micro in S60 (main.py confirms).
  - Guard validation: ALL guards CONFIRMED working. Zero post-deployment bypass bets.
    strategy_analyzer --brief false alarm fixed (commit 6557d09) — now shows "Guarded" not "needs guard".
  - NCAA scanner scheduled for 00:01 UTC March 17 (shell background process).
  - WEATHER DEAD END CONFIRMED: 60 paper bets — chi=25%%, den=8%%, lax=17%%, mia=8%% WR.
    GEFS model not calibrated to Kalshi weather markets. Do NOT pursue live weather bets.
  - 19:00 ET window: ETH NO@95c +0.84, XRP YES@92c +1.47 — both WIN.
  - 19:15 ET window: ETH NO@95c, SOL NO@94c, BTC NO@95c — all placed, awaiting settlement.
  SESSION 90 KEY BUILDS (2026-03-16):
  - CRASH FIX: asyncio.gather() return_exceptions=True (commit 2d1ffed)
  - STRATEGY ANALYZER FIX: --brief now correctly shows "Guarded (historical losses blocked)"
    instead of "Losing buckets (guards recommended)" for 96/97/98c (commit 6557d09)
  - Guard audit: ALL guards confirmed working. Zero post-deployment bypass bets in any bucket.
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

SESSION 91 KEY BUILDS (2026-03-16 evening research):
  1. Orderbook imbalance asymmetric price filter (commit a870a60):
     min_yes_price_cents=52, max_no_price_cents=44 (data-driven, 162 paper bets).
     YES@52+c: 63% WR. YES@35-51c: 40% WR (noise). Filtered set: 62% WR, p=0.011.
     7 new tests (TestAsymmetricPriceFilter). No restart needed (paper-only).
  2. Session 90 research docs committed (commit bb91dfc):
     UCL date correction (March 17-18, not March 31). Guard-aware analyzer.
  3. Weather DEAD END confirmed (20 settled bets, 45% WR, -60 USD paper).
     Disable weather in next restart (burns API quota with no edge, extreme prices).

SESSION 87 KEY BUILDS (2026-03-16):
  1. scripts/strategy_analyzer.py (NEW) — self-learning pattern detector
     Run at session start: ./venv/bin/python3 scripts/strategy_analyzer.py --brief
     Surfaces: profitable/losing sniper buckets, direction filter validation, graduation status.
     Saves to data/strategy_insights.json. 23 tests.
  2. POLYBOT_INIT.md updated: Rule 1 step 6 = run strategy_analyzer --brief at startup.
  3. NCAA scanner verified: 64 KXNCAAMBGAME markets open, 0 edges above 3% today (March 16).
     Lines mature March 17-18. Run then.

SESSION 93 KEY FINDINGS (2026-03-17 ~01:40 UTC — MONITORING):
  1. XRP NO@92c structural loss confirmed: 5 bets now, 75% WR vs 92% break-even.
     TODAY: XRP NO@92c LOST -19.32 USD. Pattern: NO@91c=100%, NO@92c=75%, NO@93c+=100%.
     IL-21 guard MUST be added ASAP (threshold met: 5+ bets, clear structural loss).
  2. Guard monitoring embedded every 5 min: strategy_analyzer.py --brief in each cycle.
     Guards CLEAN confirmed: 96/97/98c all "Guarded (historical losses blocked)".
  3. NCAA scanner ran at 00:01 UTC March 17: 96 KXNCAAMBGAME open, 0 edges found.
     Normal — re-run 12:00-18:00 ET today when Round 1 lines mature.
  4. Weather dead end CONFIRMED: 60 paper bets, avg WR 15% (chi=25%, den=8%, lax=17%, mia=8%).
     GEFS not calibrated to Kalshi. Disable weather loops next restart.
  5. sol_drift HEALTHY: 72% WR, +7.33 USD (strategy_analyzer confirmed).
  6. P&L impact: All-time dropped +65.68 → +48.42 USD due to XRP NO@92c -19.32 USD loss.

PENDING TASKS (Session 95 — PRIORITY ORDER):
  #0 COMPLETED S94: IL-22 guard deployed (commit 53c337c). KXSOL NO@92c BLOCKED. 1410 tests pass.
  #0b KEY FINDING S94: Gross P&L = +135 USD (target is +125). Fees = 89.68 USD is the only gap.
      Sniper pays 82.63 USD in taker fees. Fee/bet = 0.15 USD. Net/bet = 0.19 USD. Path: ~412 bets, ~23 days.
      btc_drift and eth_drift have maker_mode=True. sol_drift and xrp_drift do NOT (missing in main.py).
      ACTION FOR MATTHEW: Add maker_mode=True to sol_drift and xrp_drift tasks in main.py? (low risk)
  #0 URGENT TODAY: UCL soccer sniper — March 17 start at 17:25 UTC (12:25 CDT):
     python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR17
     SPO@64c (17:45 UTC kickoff), ARS@77c + MCI@67c (20:00 UTC kickoff)
     CFC@46c and PSG@33c NOT eligible (below 60c threshold)
  #0b NEXT DAY: UCL March 18 at 17:25 UTC:
     python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR18
     BAR@62c (17:45), BMU@72c + LFC@76c (20:00)
  #1 NCAA scanner — run March 17-18 when Round 1 markets open (tip-offs March 20-21):
     python3 scripts/ncaa_tournament_scanner.py --min-edge 0.03
     (At 23:35 UTC March 16: 96 KXNCAAMBGAME open but 0 edges found above 3%)
  #2 Weather strategy DISABLE — confirmed dead end (20 bets, 45% WR, -60 USD paper):
     Next restart: remove weather_* loops from main.py or comment them out.
     Extreme prices (YES@4c, NO@91c) — no 35-65c price guard was applied.
  #3 XRP drift Stage 1 eval — 21 YES-only bets. Need 9 more YES-only.
     ETA: March 20-21 (at ~3 YES/day). Current: 62% WR, Brier 0.235, +1.45 USD.
     IMPORTANT: btc_drift is micro-live (calibration_max_usd still set — Matthew's call to promote).
  #4 eth_orderbook_imbalance OOS validation — new filter deployed March 17.
     Need 20+ NEW paper bets (post-filter) at 60%+ WR before considering live re-activation.
     Retrospective: 42/64 = 65.6% WR on filtered bets (in-sample). Strong signal.
  #5 COMPLETED S93: XRP NO@92c guard (IL-21) deployed. Commit fd02a5b. 3 regression tests.
  #5b BTC YES@93c watch — 6 bets, 83.3% WR (break-even 93%). Need 10-15 bets for guard.
  #6 CPI speed-play — April 10 08:30 ET. scripts/cpi_release_monitor.py.
  #7 KXGDP speed-play — April 30. Check April 23-24 (1 week before release).
  Soccer in-play sniper — SCRIPT READY (scripts/soccer_sniper_paper.py):
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
  #6 eth_drift YES direction filter UNDERPERFORMING — Matthew's decision needed:
     Post-filter (since March 11): 16/37 = 43.2% WR, -26.54 USD — LOSING MONEY
     Break-even at YES@50c: ~52%. 43.2% is significantly below.
     btc_drift NO-only (post-filter): 58.3% WR, +18.66 USD — works correctly.
     Options: (1) wait for 50+ bets, (2) flip filter to "no", (3) disable eth_drift.
     Per PRINCIPLES.md: 37 bets not conclusive (p~0.19). Recommend: watch 20 more bets.
     NOT urgent since eth_drift is micro-live (max $0.65/bet). Just losing slowly.
  #7 btc_drift NO PROMOTION CANDIDATE — Matthew's decision needed:
     38 NO-only live bets, 57.9% WR, Brier 0.237 (< 0.25 threshold), +18.68 USD
     ALL Stage 1 criteria met. Currently micro-live (S60 demotion). Upgrade to Stage 1?
     Command: In main.py btc_drift trading_loop, set calibration_max_usd=None
     Risk: bet size goes from 0.40 USD to up to 5 USD. Read PRINCIPLES.md first.
     eth_drift YES: 76 bets, 52.6% WR, Brier 0.250, last 20 at 60% WR — watch more bets.
  #7 SOL YES 93c bucket watch — check at 20+ Stage 1 bets (currently 14 total)
  #8 CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)
  #9 KXGDP speed-play — April 30 (GDP release, check April 23-24)

SESSION 92 KEY FINDINGS (2026-03-17 00:00 UTC):
  1. eth_orderbook_imbalance retrospective filter analysis:
     After asymmetric filter (YES>=52c, NO<=44c): 42/64 = 65.6% WR
     YES 52-65c: 26/39 = 66.7% WR | YES 35-51c: 11/31 = 35.5% WR (correctly blocked)
     NO 35-44c: 6/13 = 46.2% WR | p~0.006 (z=2.50)
     NOTE: 64 bets are in-sample (filter derived from this data). Need 20+ OOS bets.
     Filter deployed commit a870a60. All new paper bets will use asymmetric filter.
  2. NCAA scanner: 96 KXNCAAMBGAME open, 0 edges found. Normal — re-run March 17-18.
  3. XRP drift: 19 YES-only, 63.2% WR, Brier 0.232 (already meets <0.25 threshold!)
  4. All-time P&L: 52.50 USD (+SOL NO@63c loss -9.45 USD vs earlier +60.28 estimate)
  5. Guards CLEAN — detect_guard_gaps() confirms no bypass bets in last 30 days.

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
