# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 21 end — 492 tests, $100 bankroll, fully autonomous protocol set)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: **7396** (stored in `bot.pid`)
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **492/492 ✅**
Latest commit: **7f37a8d** — all Session 21 changes pushed to main

## DO NOT restart the bot unless it's stopped
Check first:
```
cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
```

If stopped, restart (ALWAYS use full venv path + pkill):
```
pkill -f "python main.py"; sleep 3; rm -f bot.pid && echo "CONFIRM" | nohup /Users/matthewshields/Projects/polymarket-bot/venv/bin/python /Users/matthewshields/Projects/polymarket-bot/main.py --live >> /tmp/polybot_session21.log 2>&1 &
sleep 6 && ps aux | grep "[m]ain.py" | awk '{print "PID:", $2}' && cat bot.pid
```
Verify exactly ONE PID. If two show up, orphan guard triggered — wait 10s, try again.

## P&L Status (as of 2026-02-28 23:03 UTC)
- **Live P&L today:** -$0.91 (2 settled: btc_lag +$3.50 win, btc_drift -$4.41 loss)
- **Paper P&L today:** +$25.57
- **All-time live:** -$0.91 | **All-time paper:** $37.81 | **Win rate:** 74%
- First live loss this session ($4.41) is within expected 31% loss rate at 69% accuracy

## Graduation Progress (2026-02-28 23:03 UTC)
| Strategy              | Trades | Status                        |
|-----------------------|--------|-------------------------------|
| btc_lag_v1            | 43/30  | READY FOR LIVE (already live) |
| btc_drift_v1          | 7/30   | 23 more (already live)        |
| eth_drift_v1          | 10/30  | 20 more needed (paper)        |
| eth_orderbook_v1      | 5/30   | 25 more needed (paper)        |
| orderbook_imbalance   | 1/30   | 29 more needed (paper)        |
| eth_lag_v1            | 0/30   | calm market (expected)        |
| weather_forecast_v1   | 0/30   | weekday HIGHNY only           |
| fomc_rate_v1          | 0/5    | active March 5-19             |

## What changed in Session 21 (2026-02-28) — all committed + pushed

### Tests: 440 → 492 (+52)
- tests/test_live_executor.py: 33 tests for live.py (was ZERO)
- tests/test_bot_lock.py: 12 tests for _acquire_bot_lock + process scan
- tests/test_live_announce.py: 7 tests for _announce_live_bet

### Critical fixes
1. **Sizing clamp**: bankroll >$100 → ALL live bets were blocked. Fixed: `trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD)` in trading_loop().
2. **Paper/live separation**: has_open_position() + count_trades_today() now pass is_paper filter.
3. **Orphan instance guard**: pgrep-based scan in _acquire_bot_lock() — exits if duplicate found.
4. **Live bet announcement**: _announce_live_bet() fires banner log + Reminders notification.

### Docs / protocol
- CLAUDE.md Workflow: **ALWAYS AUTONOMOUS** standing directive (never ask for confirmation)
- CLAUDE.md: Context Handoff Protocol section (mandatory when approaching token limit)
- CLAUDE.md: Step 5 pre-live audit expanded with 6 new checks
- .planning/todos.md: 7 roadmap items (CPI strategy, cross-market arb, confidence field, etc.)
- Stable log symlink: /tmp/polybot.log → /tmp/polybot_session21.log

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Monitor, no new code needed immediately**
- `tail -f /tmp/polybot.log` — watch for 💰 LIVE BET PLACED banners
- btc_drift needs 23 more live trades before Brier computable
- First live loss ($4.41) is expected variance

**#2 — eth_drift approaching graduation (10/30)**
When eth_drift hits 30 paper trades AND Brier < 0.30 AND streak < 4:
1. Run full Step 5 pre-live audit from CLAUDE.md
2. Check: sizing clamp? is_paper filters? announce wiring? scope bugs?
3. Flip `live_executor_enabled=live_mode` in eth_drift_task in main.py
4. Restart, verify FIRST 15-min window places a live bet
5. Confirm --graduation-status counter increments

**#3 — New strategies: DO NOT build yet**
- Log ideas only. See .planning/todos.md for roadmap.
- Next candidate: CPI release strategy (similar to fomc_rate_v1 structure)

## Loop stagger (what's running right now)
```
   0s → [trading]        btc_lag_v1                 — LIVE
   7s → [eth_trading]    eth_lag_v1                 — LIVE
  15s → [drift]          btc_drift_v1               — LIVE
  22s → [eth_drift]      eth_drift_v1               — paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper
  43s → [weather]        weather_forecast_v1        — paper
  51s → [fomc]           fomc_rate_v1               — paper, active March 5-19
  58s → [unemployment]   unemployment_rate_v1       — paper, active Feb 28 – Mar 7
```

## Key Commands
```
tail -f /tmp/polybot.log                                     → Watch live bot (always open)
source venv/bin/activate && python main.py --report          → Today's P&L
source venv/bin/activate && python main.py --graduation-status → Graduation progress
source venv/bin/activate && python main.py --status          → Live status snapshot
source venv/bin/activate && python -m pytest tests/ -q       → 492 tests
```

## AUTONOMOUS OPERATION — STANDING DIRECTIVE (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Security: never expose .env/keys/pem; never modify system files outside project dir.
- Never break the bot: confirm running/stopped before restart; verify single instance after.
- Expansion order: (1) perfect live/paper, (2) graduate paper→live with Step 5 audit, (3) new types.

## Context handoff: new chat reads POLYBOT_INIT.md first, then this file, then proceeds.
