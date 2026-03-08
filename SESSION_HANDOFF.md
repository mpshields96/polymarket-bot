# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-08 (Session 35)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is RUNNING — PID 65654, live mode, log: /tmp/polybot_session35.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`
Watch: `tail -f /tmp/polybot_session35.log | grep --line-buffered "daily\|drift\|LIVE\|Kill switch"`

btc_drift MICRO-LIVE (1 contract/bet ~$0.35-0.65, UNLIMITED/day) — active (12/30 live bets so far)
All other strategies: PAPER-ONLY
Test count: 859/859
Last commit: see `git log --oneline -3`

═══════════════════════════════════════════════════

## SESSION 34 WORK COMPLETED

### 1. Lifetime hard stop REMOVED
- HARD_STOP_LOSS_PCT (30% cumulative hard stop) completely removed
- _realized_loss_usd kept for display/reporting only — no hard stop triggered
- Protection = daily loss limit (20%) + $20 bankroll floor
- All tests updated, 797 → 825 (28 new tests across commits)
- Commit: 116b2d8

### 2. btc_drift daily cap removed
- max_daily_bets: 20 → 0 (unlimited)
- Daily loss limit (~$15.95) is the only governor
- Commit: 56c3504

### 3. POST /v1/orders CONFIRMED — JSON format (session 34)
- API probe: `{"code":2, "message":"market metadata is required"}` → auth works, needs fields
- Schema: {marketSlug, intent, type, price:{value, currency}, quantity, tif}
- Response shape: {"id": "8P08FD200KVQ", "executions": []} (confirmed live)
- Commits: 0fc0806

### 4. place_order() implemented in src/platforms/polymarket.py
- OrderIntent, OrderType, TimeInForce constants
- PolymarketOrderResult dataclass (is_filled checks executions list)
- _post() helper for authenticated POST requests
- Live API probe: order accepted, id returned, executions=[] for FOK no-fill
- 18 new tests
- Commit: 0fc0806

### 5. copy_trade_loop FIXED + live execution path added
- BUG FIX: check_paper_order_allowed() called with no args (TypeError on first signal)
- BUG FIX: kill switch result used as raw bool (non-empty tuple always truthy)
- live_executor_enabled=False parameter (flip True after 30 paper trades)
- Live path: place_order(FOK), record DB on fill, kill_switch.record_trade()
- FOK no-fill: no DB record, no kill switch count
- 10 regression tests
- Commit: 14a5135

### 6. COPY TRADING PLATFORM MISMATCH CONFIRMED (critical research finding)
- polymarket.US: sports-only (200 markets, all NBA/NFL/NHL/NCAA), integer market IDs
- polymarket.COM: full platform (politics/crypto/culture), hex condition IDs
- data-api.polymarket.com: .COM-only trades, NO .US data
- predicting.top leaderboard: .COM traders only, trade geopolitics/crypto/culture
- Result: ALL whale signals from predicting.top are for .COM markets (no .us venue)
- Signals seen today: Baden-Württemberg, US-Iran ceasefire, Crude Oil, Israel-Gaza
- NO sports signals from whales (sports traders don't appear in predicting.top rankings)
- IMPLICATION: Copy trading as designed CANNOT generate .US-executable signals
- PATH FORWARD: Either enable sports_futures_v1 (already built, bookmaker arbitrage)
  OR find sports-specific whale data source OR wait for .US platform expansion

═══════════════════════════════════════════════════

## KILL SWITCH STATUS

Lifetime loss: $18.85 (display only — 30% hard stop REMOVED Session 34)
Bankroll: $79.76 | Protection: daily loss limit 20% (~$15.95/day) + $20 floor hard stop
Daily loss limit: 20% = ~$15.95 on current bankroll

═══════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE (14 loops — sports_futures_loop active on next restart)

main.py asyncio event loop [LIVE MODE] — PID 63094
  Kalshi 15-min loops:
    [trading]       btc_lag_v1           PAPER-ONLY (0 signals/week, market mature)
    [eth_trading]   eth_lag_v1           PAPER-ONLY
    [drift]         btc_drift_v1         MICRO-LIVE 1 contract/bet, UNLIMITED/day -- ACTIVE (12/30)
    [eth_drift]     eth_drift_v1         PAPER-ONLY
    [btc_imbalance] orderbook_imb_v1     PAPER-ONLY
    [eth_imbalance] eth_orderbook_imb_v1 PAPER-ONLY
    [weather]       weather_forecast_v1  PAPER-ONLY (weekdays only)
    [fomc]          fomc_rate_v1         PAPER-ONLY (~8x/year)
    [unemployment]  unemployment_rate_v1 PAPER-ONLY (~12x/year)
    [sol_lag]       sol_lag_v1           PAPER-ONLY
  Kalshi daily loops:
    [btc_daily]     btc_daily_v1         PAPER-ONLY (KXBTCD, 24 hourly slots)
    [eth_daily]     eth_daily_v1         PAPER-ONLY (KXETHD, 24 hourly slots)
    [sol_daily]     sol_daily_v1         PAPER-ONLY (KXSOLD, 24 hourly slots)
  Polymarket:
    [copy_trade]    copy_trader_v1       PAPER-ONLY (5-min poll, 144 whales, 0 .us matches so far)
    [sports_futures] sports_futures_v1   PAPER-ONLY (30-min poll, NBA/NHL/NCAAB futures, NOT YET ACTIVE — needs restart)

═══════════════════════════════════════════════════

## SESSION 35 WORK COMPLETED

### 1. Bot restarted to pick up copy_trade_loop kill switch bug fix
- PID 63094 → 65654, log /tmp/polybot_session35.log
- Bug fix from Session 34 (check_paper_order_allowed with no args) now active

### 2. sports_futures_v1 research — TEAM NAME BUG FOUND (Session 35 early)
- Sports data feed working: SDATA_KEY valid, 30 NBA championship teams returned
- 178 championship/futures markets open on .US (NBA/NHL/NCAA) — supply side is FINE
- BUT strategy generated 0 signals due to team name matching bug:
  - PM raw_title = city only (e.g., "Memphis", "Golden State", "Los Angeles C")
  - normalize_team_name() stripped city → got empty or partial result
  - Odds team names = full name (e.g., "Memphis Grizzlies" → normalized to "grizzlies")
  - "Memphis" → "memphis" ≠ "grizzlies" → NO MATCH

### 3. sports_futures_v1 FIXED + WIRED (Session 35 — this session)
- Added `_CITY_TO_NICKNAMES` map (NBA + NHL + NCAAB top teams) to sports_futures_v1.py
- Added `_ABBREV_TO_NICKNAME` map (ESPN standard abbreviations)
- Added `_get_pm_team_nickname(title, identifier, odds_by_name)` — 3-stage fallback:
    Stage 1: normalize_team_name(title) — works for full names and bare nicknames
    Stage 2: City map — "Memphis" → "grizzlies", "Golden State" → "warriors"
             Sport-context aware: "Boston" picks "celtics" in NBA, "bruins" in NHL
    Stage 3: Abbreviation from identifier slug — "mem" → "grizzlies" as last resort
- Added `_extract_identifier_abbrev(identifier)` helper
- 26 new tests in TestCityMatchFix + TestGetPmTeamNickname + TestExtractIdentifierAbbrev
- Added `sports_futures_loop()` to main.py:
    - Paper-only (no live flag, no live path)
    - 30-min poll, 6-hour feed cache → ~30-90 SDATA credits/month (well within 500 cap)
    - Fetches NBA + NHL + NCAAB championship odds from SportsFeed
    - Filters PM markets to sportsMarketType=futures
    - kill_switch.check_paper_order_allowed(trade_usd, bankroll) called correctly
    - PaperExecutor uses strategy.name (not hardcoded) — avoids Session 20 pattern
    - Handles missing SDATA_KEY gracefully (logs + returns, no crash)
    - Hard stop skips poll
- 8 new tests in TestSportsFuturesLoop covering all execution paths
- 859/859 tests passing (up from 825)
- Loop wired into main.py asyncio.gather + _on_signal cancellation + finally cleanup
- **Bot NOT restarted** — sports_futures_loop will be active after next restart

═══════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS

1. btc_drift micro-live — collecting 30 settled bets for valid Brier score
   Currently at 12/30. With unlimited/day, should reach 30 within ~2-3 days.
   Do NOT change calibration_max_usd until 30+ settled bets.

2. *** RESTART NEEDED to activate sports_futures_loop ***
   The loop code is written and tested but the running bot (PID 65654) doesn't
   have it yet. Next restart will pick it up automatically.
   Restart command (see below). Paper-only — no risk.

3. copy trading still blocked (platform mismatch)
   All whale signals from predicting.top are .COM politics/crypto markets.
   polymarket.US is sports-only. sports_futures_loop is now the active path.
   Options still open:
   b) Find sports-specific whale data source for .US
      → no known source identified yet, requires research
   c) Wait for polymarket.US platform expansion (unknown timeline)

3. DO NOT re-promote btc_lag to live — 0 signals/week, bankroll $79.76 < $90 gate

4. Watch daily loops fire — evaluate Brier after 30+ settled bets
   After 30+ settled bets each: evaluate Brier score before any live promotion

5. Sports data feed: SDATA_KEY set in .env, _QuotaGuard active at 500 credits/month
   sports_game strategy disabled (enabled: false in config.yaml)
   Enable only after Matthew decides direction

═══════════════════════════════════════════════════

## RESTART COMMANDS

Live mode (Session 35):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session35.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

Watch all loops:
  tail -f /tmp/polybot_session35.log
Watch daily + drift only:
  tail -f /tmp/polybot_session35.log | grep --line-buffered "daily\|drift\|LIVE\|Trade executed\|Kill switch"

Key Commands:
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status
  source venv/bin/activate && python3 -m pytest tests/ -q
