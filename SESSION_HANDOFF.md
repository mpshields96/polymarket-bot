# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 30)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 14417, log at /tmp/polybot_session30.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**ALL 10 Kalshi strategies PAPER-ONLY** — no live bets firing
**Copy-trade loop RUNNING (paper-only)** — polls predicting.top every 5 min
Test count: **751/751 ✅**
Last commit: **a3714ee** — feat: wire copy_trade_loop into main.py (748 tests)
Note: 751 tests now (3 more added Session 30 for predicting.top API format fixes, not yet committed)

═══════════════════════════════════════════════════

## SESSION 30 WORK COMPLETED

### predicting.top API broke — two bugs found and fixed

The copy_trade loop was failing silently. Two separate API format changes caught this session:

**Bug 1**: Response wrapper changed from bare list `[...]` to `{"traders": [...]}`.
  Fix: unwrap `data["traders"]` when response is a dict with that key.

**Bug 2**: `smart_score` field changed from `float` to nested dict `{"tier":"Great","score":79.2,...}`.
  `float(dict)` raised TypeError, silently caught — skipped ALL 179 traders every poll.
  Fix: extract `.get("score", 0.0)` when smart_score is a dict.

New tests:
  - `test_get_leaderboard_wrapped_traders_key`
  - `test_get_leaderboard_unexpected_dict_no_traders_key`
  - `test_from_dict_smart_score_nested_dict`

Pending commit for these 3 tests + fixes.

═══════════════════════════════════════════════════

## CRITICAL ARCHITECTURE CLARIFICATION (Matthew confirmed Session 30)

### TWO SEPARATE POLYMARKET PLATFORMS — NEVER CONFUSE THEM

**polymarket.US** (our existing Ed25519 auth):
  - URL: api.polymarket.us/v1
  - US iOS users only, launched Dec 2025 (CFTC approval)
  - Sports-only: NBA/NFL/NHL/NCAA. Nothing else currently.
  - Existing credentials (POLYMARKET_KEY_ID/SECRET_KEY in .env) work here only.

**polymarket.COM** (global platform — separate account required):
  - Full market suite: **politics, crypto, sports, culture, economics, geopolitics, entertainment**
  - Has BTC/ETH/SOL 15-min up/down markets, US elections, cultural moments — everything
  - Auth: ECDSA secp256k1 (Ethereum wallet) — completely different from Ed25519
  - Python client: `py-clob-client` (Polymarket/py-clob-client, MIT licensed)
  - WHERE THE WHALES ARE — predicting.top leaderboard = polymarket.COM traders
  - data-api.polymarket.com returns .COM trade history (public, no auth)
  - Full copy trading requires .COM account + Polygon wallet from Matthew

### PRIMARY GOAL: COPY TRADING ON POLYMARKET.COM
  The whales we're tracking trade on .COM. The data we're reading is from .COM.
  Our .US account only overlaps for sports markets. For real copy trading we need .COM.
  Matthew's decision required: create polymarket.COM account + Polygon wallet?
    YES → ECDSA auth + py-clob-client integration (Path A — recommended)
    NO  → .US sports execution only (very limited whale signal overlap)

### Kalshi copy trading — OPEN RESEARCH QUESTION (Matthew raised Session 30)
  - Kalshi has a public leaderboard (top daily earners visible)
  - Unknown: is there a public trade history API equivalent to data-api.polymarket.com?
  - Research path: Reddit (r/Kalshi, r/predictionmarkets) + Kalshi API docs
  - If feasible: same copy-trade infrastructure, different data source

### Reddit intelligence — NEXT RESEARCH TASK (Matthew raised Session 30)
  - Search r/polymarket, r/predictionmarkets, r/Kalshi
  - Find known top traders, shared strategies, open-source bots on GitHub
  - Top accounts may have public repos — evaluate what can be adapted
  - This is prior art research, not code. Do it BEFORE building new strategies.

═══════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE

```
main.py asyncio event loop
  ├── Kalshi loops (10 — ALL paper)
  │   ├── [trading]        btc_lag_v1           stagger 0s
  │   ├── [eth_trading]    eth_lag_v1           stagger 7s
  │   ├── [drift]          btc_drift_v1         stagger 15s
  │   ├── [eth_drift]      eth_drift_v1         stagger 22s
  │   ├── [btc_imbalance]  orderbook_imb_v1     stagger 29s
  │   ├── [eth_imbalance]  eth_orderbook_imb_v1 stagger 36s
  │   ├── [weather]        weather_forecast_v1  stagger 43s
  │   ├── [fomc]           fomc_rate_v1         stagger 51s
  │   ├── [unemployment]   unemployment_rate_v1 stagger 58s
  │   └── [sol_lag]        sol_lag_v1           stagger 65s
  └── Polymarket loops
      └── [copy_trade]     copy_trader_v1       stagger 80s, 5-min poll (PAPER-ONLY)
```

Key Polymarket files:
  - src/data/predicting_top.py       — whale leaderboard from predicting.top (18 tests)
  - src/data/whale_watcher.py        — trade/position history from data-api.polymarket.com (28 tests)
  - src/strategies/copy_trader_v1.py — 6 decoy filters + Signal generation (29 tests)
  - src/strategies/sports_futures_v1.py — Odds API mispricing signals (25 tests, SUPPLEMENTAL only)

═══════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS (priority order)

1. COMMIT the Session 30 predicting.top fixes (not yet committed)
2. CONFIRM copy_trade_loop now loads whale accounts:
     tail -f /tmp/polybot_session30.log | grep --line-buffered "predicting_top\|copy_trade"
     Should see "Loaded X whale accounts" (not "returned empty list") every 5 min
3. ARCHITECTURE DECISION — Matthew: do you want a polymarket.COM account + Polygon wallet?
4. REDDIT RESEARCH — find top Polymarket accounts/bots, open-source repos
5. KALSHI COPY TRADING — research public trade history API feasibility
6. POST /v1/orders format — iOS Proxyman capture when ready (blocker for live .US execution)

═══════════════════════════════════════════════════

## P&L STATUS (2026-03-01)

  All-time live:   -$18.85  (21 settled, 8W/13L = 38%)
  All-time paper: +$217.90
  Bankroll:         $79.76
  Hard stop margin: $11.15 remaining before -$30 lifetime forced shutdown

  ⚠️ DO NOT re-promote any strategy live. Too close to hard stop.
  Re-promotion gate: bankroll > $90 AND 30+ settled live trades AND Brier < 0.25

═══════════════════════════════════════════════════

## KILL SWITCH STATUS

All strategies paper-only. Kill switch NOT active. No lock file.
All 3 counters persist across restarts (fixed Sessions 23-25):
  - Daily loss limit: 20% = $15.95
  - Lifetime loss limit: 30% = $30.00 ($11.15 remaining)
  - Consecutive loss limit: 4

═══════════════════════════════════════════════════

## RESTART COMMANDS

**Paper mode (current state):**
```bash
cd /Users/matthewshields/Projects/polymarket-bot
pkill -f "python main.py" 2>/dev/null; pkill -f "Python main.py" 2>/dev/null
sleep 3; kill -9 $(ps aux | grep "[m]ain.py" | awk '{print $2}') 2>/dev/null
sleep 2; rm -f bot.pid
nohup ./venv/bin/python main.py >> /tmp/polybot_session30.log 2>&1 &
sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
```

**Live mode (only after bankroll >$90 + explicit decision):**
```bash
pkill -f "python main.py" 2>/dev/null; sleep 3; rm -f bot.pid
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session30.log 2>&1 &
sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
```

**Watch copy-trade loop:**
```bash
tail -f /tmp/polybot_session30.log | grep --line-buffered "copy_trade\|predicting_top\|whale"
```

## Key Commands
```bash
source venv/bin/activate && python main.py --report
source venv/bin/activate && python main.py --graduation-status
source venv/bin/activate && python -m pytest tests/ -q
source venv/bin/activate && python setup/verify.py
```
