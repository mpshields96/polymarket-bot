# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-08 (Session 31)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is RUNNING — PID 53490, log at /tmp/polybot_session31.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

btc_drift MICRO-LIVE ($1.00 cap, 3/day) — in 2hr cooling until ~15:19 UTC (consecutive_losses=4 on restart)
All other 9 Kalshi strategies: PAPER-ONLY
Copy-trade loop: RUNNING (paper-only, 5-min poll)
Test count: 758/758
Last commit: ed87261 — feat: micro-live calibration phase for btc_drift ($1.00 cap, 3/day)

═══════════════════════════════════════════════════

## SESSION 31 WORK COMPLETED

### 1. Paper P&L anomaly found + fixed
- eth_orderbook_imbalance had $233.24 single trade at NO@2c (YES=98c)
- Price range guard (35-65c) was missing from orderbook_imbalance.py
- Fixed: same guard as btc_lag/btc_drift added to both BTC and ETH paths
- 3 regression tests added (TestPriceRangeGuard)
- Real paper P&L without anomaly: ~$7 for eth_orderbook_imbalance (not $240)

### 2. Paper vs live discrepancy diagnosed
- Paper P&L is structurally optimistic: no real slippage, no fill timing, no counterparty
- Paper slippage_ticks raised 1->2 (Kalshi BTC spreads avg 2-3c at near-50c)

### 3. Micro-live calibration phase implemented
- Matthew decision: use real $1.00 bets instead of fake paper for btc_drift
- calibration_max_usd=1.00 parameter added to trading_loop
- btc_drift loop: live_executor_enabled, $1.00 cap, max 3/day (~$3/day, $20/week max)
- Kill switch applies fully — daily/lifetime/consecutive limits enforced
- PRINCIPLES.md updated with micro-live phase rules

### 4. Copy trading research completed
- Kalshi copy trading: CONFIRMED INFEASIBLE (no public user attribution)
- Polymarket.COM: full market suite, whales trade here, py-clob-client for ECDSA auth
- Top traders: HyperLiquid0xb $1.4M, Erasmus $1.3M, WindWalk3 $1.1M, BAdiosB 90.8% wr
- Research doc: .planning/research/copy_trading_research.md

═══════════════════════════════════════════════════

## KILL SWITCH STATUS (2026-03-08 13:19 UTC)

2hr cooling active until ~15:19 UTC — consecutive_losses=4 restored from DB on restart.
After cooling expires, btc_drift micro-live bets can fire normally.

Lifetime loss: $18.85 / $30.00 (62.8% of hard stop threshold)
Bankroll: $79.76 | Hard stop margin: $11.15 remaining

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

1. WAIT: 2hr cooling expires ~15:19 UTC — watch for first micro-live btc_drift bet
   tail -f /tmp/polybot_session31.log | grep --line-buffered "LIVE\|drift\|Trade executed"

2. GATE: Matthew — polymarket.COM account + Polygon wallet?
   This is the SINGLE blocker for real copy trading on .COM (where all whales trade).
   YES -> ECDSA auth + py-clob-client integration in src/auth/ + src/platforms/

3. btc_drift micro-live — let it collect 30 real bets, then evaluate Brier score
   Do NOT change calibration_max_usd until 30+ settled bets.

4. DO NOT re-promote btc_lag to live — 0 signals/week, bankroll $79.76 < $90 gate

═══════════════════════════════════════════════════

## RESTART COMMANDS

Live mode (current — standard restart):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session31.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

Watch micro-live drift bets:
  tail -f /tmp/polybot_session31.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

Key Commands:
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status
  source venv/bin/activate && python3 -m pytest tests/ -q
