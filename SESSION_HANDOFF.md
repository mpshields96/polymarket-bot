# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-08 (Session 33)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is RUNNING — PID 59386, live mode, log: /tmp/polybot_session33.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`
Watch: `tail -f /tmp/polybot_session33.log | grep --line-buffered "daily\|drift\|LIVE\|Kill switch"`

btc_drift MICRO-LIVE ($0.50 cap, 8/day) — active (raised from $1/3 to get 30 trades faster)
All other strategies: PAPER-ONLY
Test count: 798/798
Last commit: fc03851 — wire crypto_daily_loop into main.py

═══════════════════════════════════════════════════

## SESSION 33 WORK COMPLETED

### 1. CryptoDailyStrategy — KXBTCD / KXETHD / KXSOLD (24 hourly slots)
- src/strategies/crypto_daily.py: CryptoDailyStrategy covering all 24 hourly settlement slots/day
- tests/test_crypto_daily.py: 30 TDD tests (all pass)
- Strategy: find ATM market (closest to 50¢ mid) in 30min-6hr window, bet on intraday drift
- Probability model: 70% drift momentum signal + 30% lognormal position
- Price guard: 35-65¢ enforced (same as all other strategies)
- Covers BTC (KXBTCD), ETH (KXETHD), SOL (KXSOLD)

### 2. crypto_daily_loop wired into main.py
- crypto_daily_loop(): 5-min poll, session_open tracking (resets midnight UTC), limit=500 markets/fetch
- 3 paper-only tasks: btc_daily (90s delay), eth_daily (100s), sol_daily (110s)
- All 3 added to signal handlers, gather, and finally cleanup
- config.yaml: crypto_daily section (min_drift=0.5%, min_edge=4%, 30-360min window)

### 3. Kalshi leaderboard research confirmed
- Kalshi HAS a public leaderboard (kalshi.com/social/leaderboard, opt-in) but shows ONLY P&L
- Individual user trade history is NOT public on Kalshi — only aggregate market trades
- Kalshi copy trading confirmed infeasible (no per-user trade attribution in public API)
- Polymarket copy trading remains feasible (data-api.polymarket.com exposes full user history)

### 4. CLAUDE_CODE_MAX_OUTPUT_TOKENS
- Add `export CLAUDE_CODE_MAX_OUTPUT_TOKENS=64000` to ~/.zshrc

═══════════════════════════════════════════════════

## KILL SWITCH STATUS

Lifetime loss: $18.85 / $30.00 (62.8% of hard stop threshold)
Bankroll: $79.76 | Hard stop margin: $11.15 remaining
Daily loss limit: 20% = ~$15.95 on current bankroll

═══════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE (13 loops)

main.py asyncio event loop [LIVE MODE] — PID 58614
  Kalshi 15-min loops:
    [trading]       btc_lag_v1           PAPER-ONLY (0 signals/week, market mature)
    [eth_trading]   eth_lag_v1           PAPER-ONLY
    [drift]         btc_drift_v1         MICRO-LIVE $1.00 cap, 3/day -- ACTIVE
    [eth_drift]     eth_drift_v1         PAPER-ONLY
    [btc_imbalance] orderbook_imb_v1     PAPER-ONLY
    [eth_imbalance] eth_orderbook_imb_v1 PAPER-ONLY
    [weather]       weather_forecast_v1  PAPER-ONLY (weekdays only)
    [fomc]          fomc_rate_v1         PAPER-ONLY (~8x/year)
    [unemployment]  unemployment_rate_v1 PAPER-ONLY (~12x/year)
    [sol_lag]       sol_lag_v1           PAPER-ONLY
  Kalshi daily loops (NEW Session 33):
    [btc_daily]     btc_daily_v1         PAPER-ONLY (KXBTCD, 24 hourly slots)
    [eth_daily]     eth_daily_v1         PAPER-ONLY (KXETHD, 24 hourly slots)
    [sol_daily]     sol_daily_v1         PAPER-ONLY (KXSOLD, 24 hourly slots)
  Polymarket:
    [copy_trade]    copy_trader_v1       PAPER-ONLY (5-min poll, 144 whales)

═══════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS

1. btc_drift micro-live — let it collect 30 real bets, then evaluate Brier score
   Do NOT change calibration_max_usd until 30+ settled bets.

2. CONFIRM: POST /v1/orders protobuf format on polymarket.US
   Single remaining blocker for live copy trading.

3. DO NOT re-promote btc_lag to live — 0 signals/week, bankroll $79.76 < $90 gate

4. Watch daily loops fire — first signals expected within first full day
   After 30+ settled bets each: evaluate Brier score before any live promotion

═══════════════════════════════════════════════════

## RESTART COMMANDS

Live mode (Session 33):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session33.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

Watch all loops:
  tail -f /tmp/polybot_session33.log
Watch daily + drift only:
  tail -f /tmp/polybot_session33.log | grep --line-buffered "daily\|drift\|LIVE\|Trade executed\|Kill switch"

Key Commands:
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status
  source venv/bin/activate && python3 -m pytest tests/ -q
