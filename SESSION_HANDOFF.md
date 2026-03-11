# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-10 (Session 45 — Coinbase backup + event-driven trigger)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 46)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 46).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

RESTART COMMAND (session46.log):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session46.log 2>&1 &
  sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
Verify: ps aux | grep "[m]ain.py" | wc -l should show 1 (exactly one process).

DIAGNOSTICS AFTER RESTART:
  source venv/bin/activate && python3 main.py --health
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-189 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart.

---

KEY STATE (Session 45 END — 2026-03-10 ~18:20 CDT):
* Bot: RUNNING (PID 36660) → /tmp/polybot_session45.log
* All-time live P&L: -$45.52 | Bankroll: ~$68.16 (approx)
* 980/980 tests passing (28 new: 20 coinbase + 8 event trigger)
* Last code commit: 3fef17a — feat: Coinbase backup + event-driven BTC trigger

LIVE STRATEGY STATUS (as of Session 45 end):
  - btc_drift_v1: STAGE 1 — 47/30 Brier 0.251 | P&L -$23.37 | direction_filter="no" ACTIVE
    ~20 NO-only bets. DECISION POINT at 30 NO-only bets.
  - eth_drift_v1: STAGE 1 (graduated Session 44!) — 31/30 Brier 0.256 | P&L +$0.41
    MILESTONE: First Stage 1 bets fired. Watch grep "LIVE BET" ...log | grep "eth_drift"
  - sol_drift_v1: MICRO-LIVE — 14/30 Brier 0.170 BEST SIGNAL | P&L +$1.93
  - xrp_drift_v1: MICRO-LIVE — 4/30 Brier 0.392 bad start | P&L -$2.45
  - eth_orderbook_imbalance_v1: MICRO-LIVE — 12/30 Brier 0.360 GETTING WORSE
    WATCHDOG: if Brier > 0.30 at bet 22 — disable live trading
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — effectively dead

SESSION 45 WORK DONE:
  1. src/data/coinbase.py (NEW) — CoinbasePriceFeed + DualPriceFeed
     - CoinbasePriceFeed: polls api.coinbase.com/v2/prices/{SYMBOL}-USD/spot
     - DualPriceFeed: Binance primary + Coinbase backup, falls back on stale
     - 20 tests in tests/test_coinbase_feed.py
  2. Event-driven asyncio.Condition trigger
     - btc_price_monitor() coroutine added to main.py
     - _wait_for_btc_move() replaces asyncio.sleep() in all trading_loop calls
     - All 8 crypto loops now wake within 1-3s of BTC move (vs 10s before)
     - 8 tests in tests/test_event_trigger.py
  3. main.py wiring
     - DualPriceFeed wraps all 4 Binance feeds (BTC/ETH/SOL/XRP)
     - btc_price_monitor task added to gather + signal handler + cleanup
     - btc_move_condition passed to all 8 crypto trading_loop calls
  4. --export-tax PID lock bypass fix (was blocked by bot.pid check)
  5. 980/980 tests passing, committed 3fef17a, pushed to GitHub
  6. Bot restarted to session45.log (PID 36660)
  7. DualPriceFeed CONFIRMED working (Coinbase fallback active at startup while Binance WebSocket reconnects)

PENDING FROM SESSION 45:
  - Kalshi CSV download was EMPTY (3-byte BOM only) — Matthew needs to re-download from Kalshi
    Once downloaded: python3 main.py --export-tax → reports/tax_trades.csv, then cross-reference
  - Brier gate docs update (REBUILD priority 6 from CODEBASE_AUDIT.md) — still TODO
  - eth_imbalance watchdog: check --graduation-status at bet 22; if Brier > 0.30, disable live

NEXT SESSION PRIORITIES (Session 46):
  1. Restart bot to session46.log
  2. Run diagnostics (--health, --report, --graduation-status)
  3. Watch for eth_drift Stage 1 bets and xrp_drift watchdog
  4. If Matthew re-downloads Kalshi CSV: cross-reference with --export-tax output
  5. Brier gate docs update (docs/GRADUATION_CRITERIA.md — set 0.20 for post-Grand Rounds strategies)
  6. Grand Rounds ~March 20 — post-GR = more build time

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* Expansion gate: DO NOT build new strategies until drift validates
* Grand Rounds: ~March 20, 2026. Post-Grand-Rounds = more time to work on the bot.
