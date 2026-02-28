# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 22 end — 498 tests, $100 bankroll, 2 bug classes fixed)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: **7396** (stored in `bot.pid`)
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **498/498 ✅**
Latest commit: **d3a889e** — calculate_size kwargs fix + GRADUATION_CRITERIA v1.1

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

## P&L Status (as of 2026-02-28 23:54 UTC)
- **Live P&L today:** +$17.80 (4 settled: btc_lag +$3.50, btc_drift -$4.41, +$9.75, +$8.96)
- **Paper P&L today:** +$16.19 (28 settled)
- **All-time live:** +$17.80 | **All-time paper:** +$28.43 | **Win rate:** 72%
- Live is **profitable** — net positive on day 1 of real trading

## Graduation Progress (2026-02-28 23:54 UTC)
| Strategy              | Trades | Status                        |
|-----------------------|--------|-------------------------------|
| btc_lag_v1            | 43/30  | READY FOR LIVE (already live) |
| btc_drift_v1          | 7/30   | 23 more (already live)        |
| eth_drift_v1          | 13/30  | 17 more needed (paper)        |
| eth_orderbook_v1      | 5/30   | 25 more needed (paper)        |
| orderbook_imbalance   | 2/30   | 28 more needed (paper)        |
| eth_lag_v1            | 0/30   | calm market (expected)        |
| weather_forecast_v1   | 0/30   | weekday HIGHNY only           |
| fomc_rate_v1          | 0/5    | active March 5-19             |

## What changed in Session 22 (2026-02-28) — all committed + pushed to d3a889e

### Tests: 495 → 498 (+3)
- tests/test_kill_switch.py: TestPaperLoopSizingCallSignature (3 regression tests)

### Bug fixes (2 classes of silent failure found and fixed)

**Bug #1 (Session 22 start — from previous chat):** kill switch wrong kwargs in paper loops
- weather_loop, fomc_loop, unemployment_loop called `check_order_allowed(proposed_usd=..., current_bankroll=...)` — wrong kwarg names
- Fix: `ok, reason = kill_switch.check_order_allowed(trade_usd=1.0, current_bankroll_usd=...)` with tuple unpacking
- Committed d5204c7 (beginning of Session 22 from previous chat)

**Bug #2 (Session 22 this chat):** calculate_size wrong kwargs in paper loops — SAME loops
- All 3 paper-only loops (weather, fomc, unemployment) called `calculate_size(price_cents=..., ...)` — `price_cents` is NOT a parameter
- Also omitted required `payout_per_dollar` parameter
- TypeError silently caught by outer except → ALL paper trades from these loops were silently skipped
- Not yet triggered in production (weather=weekend, FOMC=March 5+, KXUNRATE not open yet)
- Fix: add `kalshi_payout()` call to compute `payout_per_dollar`, same pattern as trading_loop (line 161-172)
- Fix pattern: `_yes_p = price_cents if side=="yes" else (100-price_cents); payout=kalshi_payout(_yes_p, side)`
- Committed d3a889e

### Docs: GRADUATION_CRITERIA.md v1.1
- Added "Stage Promotion Criteria" section (Stage 1→2→3)
- Kelly calibration requirements BEFORE trusting higher bet sizes
- Volatility × Kelly interaction documented
- Explicit: do NOT promote to Stage 2 based solely on bankroll crossing $100
- Current status table: bankroll gate passed ✅, Kelly calibration gates all ❌ (need ~30 more live settled bets)
- File: docs/GRADUATION_CRITERIA.md

### Audits completed (all clean)
- live.py contract sizing: `int()` floor rounding correct, `max(1, ...)` matches paper.py, no bugs
- settlement_loop: kill switch filtering (live only), win detection (`result==side`), all correct
- Exception handling: all outer except clauses log properly; osascript pass is intentional
- paper graduation data: eth_drift 13/30, orderbook 2/30, eth_orderbook 5/30 — accumulating correctly

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Monitor, no new code needed immediately**
- `tail -f /tmp/polybot.log` — watch for 💰 LIVE BET PLACED banners
- btc_drift is placing live bets regularly — watch for more wins
- btc_drift needs more live trades; Brier not computable yet (< 5 with win_prob recorded)

**#2 — NO Stage 2 promotion yet (read docs/GRADUATION_CRITERIA.md)**
- Bankroll is ~$103.51 (Stage 2 threshold crossed)
- But Kelly calibration requires 30+ live settled bets with `limiting_factor=="kelly"` first
- Do NOT raise bet size to $10 yet — flying blind on Kelly until ~4-6 more weeks

**#3 — eth_drift approaching graduation (13/30)**
When eth_drift hits 30 paper trades AND Brier < 0.30 AND streak < 4:
1. Run full Step 5 pre-live audit from CLAUDE.md
2. Check: sizing clamp? is_paper filters? announce wiring? scope bugs?
3. **Verify calculate_size call uses payout_per_dollar (NOT price_cents)** ← new gotcha from Session 22
4. Flip `live_executor_enabled=live_mode` in eth_drift_task in main.py
5. Restart, verify FIRST 15-min window places a live bet

**#4 — Weather loop ready for Monday March 2**
- weather_loop + fomc_loop + unemployment_loop all now have correct calculate_size calls
- Weather fires on HIGHNY weekday markets — will start Monday
- Watch for first weather paper trade Monday morning

**#5 — FOMC active March 5**
- fomc_rate_v1 strategy fires ~8 days before meeting
- KXFEDDECISION markets open ~March 5 for March 19 meeting
- Fix confirmed: correct kwargs on kill_switch + calculate_size calls
- First paper trade expected March 5

**#6 — New strategies: DO NOT build yet**
- Log ideas only. See .planning/todos.md for roadmap.
- Expansion gate: btc_drift 30 live trades + Brier < 0.30 + 2-3 weeks consistent P&L + zero kill switch events

## Session 22 Matthew directives (reference for new chat)
- Focus: maintenance and optimization of 9 current strategies ONLY
- No new bet types until 4-condition expansion gate clears (~2-3 weeks)
- Volatility-adaptive parameters: logged in .planning/todos.md, DO NOT BUILD YET
- Kelly sizing: system documented in docs/GRADUATION_CRITERIA.md v1.1, not trusted for promotion yet
- btc/eth bet types are primary focus (they're the live strategies)

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
source venv/bin/activate && python -m pytest tests/ -q       → 498 tests
```

## AUTONOMOUS OPERATION — STANDING DIRECTIVE (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Security: never expose .env/keys/pem; never modify system files outside project dir.
- Never break the bot: confirm running/stopped before restart; verify single instance after.
- Expansion order: (1) perfect live/paper, (2) graduate paper→live with Step 5 audit, (3) new types.

## Context handoff: new chat reads POLYBOT_INIT.md first, then this file, then proceeds.
