# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-08 (Session 32)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is STOPPED — being restarted with new paper calibration settings (Session 32).
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`
Start: see RESTART COMMANDS below.

btc_drift MICRO-LIVE ($1.00 cap, 3/day) — kill switch cooling may be active; check log
All other 9 Kalshi strategies: PAPER-ONLY
Copy-trade loop: RUNNING (paper-only, 5-min poll)
Test count: 768/768
Last commit: Session 32 — paper calibration fixes + Polymarket architecture docs

═══════════════════════════════════════════════════

## SESSION 32 WORK COMPLETED

### 1. Paper calibration fixed (3 structural gaps closed)
- paper_slippage_ticks: 2 → 3 (upper end of confirmed 2-3¢ Kalshi BTC spread)
- paper_fill_probability: 0.85 added (15% no-fill simulates market movement before order arrives)
- signal_price_cents DB column added (stores pre-slippage price for future real slippage measurement)
- DB migration: ALTER TABLE trades ADD COLUMN signal_price_cents INTEGER (safe, idempotent)
- PaperExecutor: fill_probability parameter added, signal_price_cents tracked in execute()
- 10 new tests: TestFillProbability (6) + TestSignalPriceCents (4)
- All PaperExecutor instantiations in main.py updated: trading_loop, weather, fomc, unemployment, copy_trade
- **768/768 tests pass**

### 2. Polymarket architecture FINAL clarified
- Previous sessions had wrong conclusion: "BLOCKED — need .COM account + Polygon wallet"
- Reality: Matthew is US-based, iOS app, $60 on polymarket.US — polymarket.COM is geo-restricted
- Correct path: data-api.polymarket.com (public whale data) + api.polymarket.us/v1 (Ed25519 orders)
- ONLY remaining blocker: POST /v1/orders protobuf format confirmation
- No VPN, no .COM account, no Polygon wallet needed
- CLAUDE.md + MEMORY.md + SESSION_HANDOFF.md all updated with correct architecture

### 3. Loading screen tip rule added
- Every response must end with `💡 Loading Screen Tip` block
- Shows single most useful next command + token cost estimate + yes/no approval
- Hardcoded in CLAUDE.md Workflow section + MEMORY.md User preferences

### 4. Weekly $20 live bet limit (this week only)
- Matthew set $20/week live bet limit for this week (not a permanent change)
- btc_drift at $1/bet × 3/day = max $21/week → already within limit
- Lifetime hard stop unchanged: $30 total loss limit (currently $18.85 used)

═══════════════════════════════════════════════════

## KILL SWITCH STATUS

Lifetime loss: $18.85 / $30.00 (62.8% of hard stop threshold)
Bankroll: $79.76 | Hard stop margin: $11.15 remaining
Daily loss limit: 20% = ~$15.95 on current bankroll

═══════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE

main.py asyncio event loop [LIVE MODE]
  Kalshi loops:
    [trading]       btc_lag_v1           PAPER-ONLY (0 signals/week, market mature)
    [eth_trading]   eth_lag_v1           PAPER-ONLY (never graduated)
    [drift]         btc_drift_v1         MICRO-LIVE $1.00 cap, 3/day -- ACTIVE
    [eth_drift]     eth_drift_v1         PAPER-ONLY (-$35.47 paper P&L)
    [btc_imbalance] orderbook_imb_v1     PAPER-ONLY
    [eth_imbalance] eth_orderbook_imb_v1 PAPER-ONLY
    [weather]       weather_forecast_v1  PAPER-ONLY (weekdays only)
    [fomc]          fomc_rate_v1         PAPER-ONLY (~8x/year)
    [unemployment]  unemployment_rate_v1 PAPER-ONLY (~12x/year)
    [sol_lag]       sol_lag_v1           PAPER-ONLY
  Polymarket:
    [copy_trade]    copy_trader_v1       PAPER-ONLY (5-min poll, 144 whales)

═══════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS

1. CONFIRM: POST /v1/orders protobuf format on polymarket.US
   This is the ONLY remaining blocker for live copy trading.
   Once confirmed + 30 paper copy trades → flip copy_trade_loop to live.

2. btc_drift micro-live — let it collect 30 real bets, then evaluate Brier score
   Do NOT change calibration_max_usd until 30+ settled bets.

3. DO NOT re-promote btc_lag to live — 0 signals/week, bankroll $79.76 < $90 gate

4. Weekly $20 live bet limit this week — Matthew reconvening next week on this

═══════════════════════════════════════════════════

## RESTART COMMANDS

Live mode (with new paper calibration — Session 32):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session32.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

Watch micro-live drift bets:
  tail -f /tmp/polybot_session32.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

Key Commands:
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status
  source venv/bin/activate && python3 -m pytest tests/ -q
