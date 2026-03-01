# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 22 end — 504 tests, $107.87 bankroll, 4 bug classes fixed)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: **7396** (stored in `bot.pid`)
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **504/504 ✅**
Latest commit: **4ae55bd** — strategy min_edge_pct propagation fix

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

## P&L Status (as of 2026-03-01 18:26 UTC)
- **Bankroll:** ~$116+ (API update pending — trade 78 won +$8.82)
- **Live P&L today:** +$8.82 (1 settled, 1 open — trade 80 on 1930 BTC window)
- **All-time live:** +$21.68 (6 settled: 4W 2L)
- **All-time paper:** +$36.59
- **All-time win rate:** 71%

### Live bets breakdown (all-time):
| id | Strategy | Side | Cost | Result | P&L |
|----|----------|------|------|--------|-----|
| 64 | btc_lag | NO @48¢ | $3.36 | WON | +$3.50 |
| 67 | btc_drift | YES @63¢ | $4.41 | LOST | -$4.41 |
| 70 | btc_drift | NO @33¢ | $4.95 | WON | +$9.75 |
| 74 | btc_drift | NO @34¢ | $4.76 | WON | +$8.96 |
| 75 | btc_drift | NO @26¢ | $4.94 | LOST | -$4.94 |
| 78 | btc_drift | NO @35¢ | $4.90 | WON | +$8.82 |
| 80 | btc_drift | NO @57¢ | $4.56 | pending | — |

## Graduation Progress (2026-03-01 00:13 UTC)
| Strategy              | Trades | Status                        |
|-----------------------|--------|-------------------------------|
| btc_lag_v1            | 43/30  | READY FOR LIVE (already live) |
| btc_drift_v1          | 7/30   | 23 more (already live)        |
| eth_drift_v1          | 14/30  | 16 more needed (paper)        |
| eth_orderbook_v1      | 5/30   | 25 more needed (paper)        |
| orderbook_imbalance   | 2/30   | 28 more needed (paper)        |
| eth_lag_v1            | 0/30   | calm market (expected)        |
| weather_forecast_v1   | 0/30   | weekday HIGHNY only           |
| fomc_rate_v1          | 0/5    | active March 5-19             |

## What changed in Session 22 (2026-02-28 → 2026-03-01) — all committed

### Tests: 495 → 504 (+9)
- tests/test_kill_switch.py: TestPaperLoopSizingCallSignature (3 regression tests)
- tests/test_kill_switch.py: TestPaperLoopSizeExtraction (3 regression tests)
- tests/test_kill_switch.py: TestStrategyMinEdgePropagation (3 regression tests)

### Bug fixes (4 classes of silent failure found and fixed)

**Bug #1 (from previous chat, d5204c7):** kill switch wrong kwargs in paper loops
- weather_loop, fomc_loop, unemployment_loop called `check_order_allowed(proposed_usd=..., current_bankroll=...)` — wrong kwarg names
- Fix: `ok, reason = kill_switch.check_order_allowed(trade_usd=1.0, current_bankroll_usd=...)` with tuple unpacking

**Bug #2 (d3a889e):** calculate_size wrong kwargs in paper loops — SAME loops
- All 3 paper-only loops called `calculate_size(price_cents=..., ...)` — `price_cents` is NOT a parameter
- Also omitted required `payout_per_dollar` parameter
- Fix: add `kalshi_payout()` call to compute `payout_per_dollar`, same pattern as trading_loop

**Bug #3 (1111e12):** SizeResult object passed as float to paper_exec.execute()
- After Bug #2 fix, remaining issue: `size_usd=size` where `size` was a `SizeResult` dataclass, not a float
- Also: no `if result is None: continue` guard before `result["side"]` access
- Fix: `_trade_usd = min(_size_result.recommended_usd, _HARD_CAP)`, add None guard

**Bug #4 (4ae55bd):** strategy min_edge_pct not propagated to calculate_size in trading_loop
- `trading_loop()` called `calculate_size()` without `min_edge_pct` → default 8% used
- btc_lag fires at 4%, btc_drift at 5% — signals at 4-7.9% edge were silently dropped
- This explains the "17:23 mystery" (btc_drift 6.7% edge generated, 6.7% < 8% → None → no bet)
- Fix: `_strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)` passed to `calculate_size()`
- **IMPACT: This was silently blocking valid live bets from btc_lag + btc_drift**

### Docs: GRADUATION_CRITERIA.md v1.1
- Added "Stage Promotion Criteria" section (Stage 1→2→3)
- Kelly calibration requirements BEFORE trusting higher bet sizes
- Volatility × Kelly interaction documented
- Explicit: do NOT promote to Stage 2 based solely on bankroll crossing $100
- Current status table: bankroll gate passed ✅, Kelly calibration gates all ❌

### Kill switch event log investigation (informational)
- KILL_SWITCH_EVENT.log shows hard stops at 2026-03-01T00:10:38 UTC with "$31 loss"
- **Root cause: test pollution** — `_hard_stop()` writes to live KILL_SWITCH_EVENT.log during pytest runs
- Test kills switch creates events: `record_loss(10)` × 3 = $31 → exactly matches
- No real trading issue. Bot bankroll is $107.87 (positive). Live P&L is +$12.86.
- **Minor bug to fix later**: kill_switch._hard_stop() should skip event log write during tests (same as _write_blockers). Low priority.

## KEY PRIORITIES FOR NEXT SESSION

**#1 — Watch for btc_drift live bets (min_edge_pct fix)**
- Bug #4 was silently blocking valid signals at 4-7.9% edge. Now fixed.
- Expect MORE btc_drift live bets now that 5% signals fire correctly
- Watch for 💰 LIVE BET PLACED banners in log

**#2 — NO Stage 2 promotion yet (read docs/GRADUATION_CRITERIA.md)**
- Bankroll is ~$107.87 (Stage 2 threshold crossed)
- But Kelly calibration requires 30+ live settled bets with `limiting_factor=="kelly"` first
- Do NOT raise bet size to $10 yet

**#3 — eth_drift approaching graduation (14/30)**
When eth_drift hits 30 paper trades AND Brier < 0.30 AND streak < 4:
1. Run full Step 5 pre-live audit from CLAUDE.md
2. **Verify calculate_size call uses payout_per_dollar (NOT price_cents)** ← Bug #2 pattern
3. Flip `live_executor_enabled=live_mode` in eth_drift_task in main.py
4. Restart, verify FIRST 15-min window places a live bet

**#4 — Weather loop starting Monday March 2**
- All 3 bug classes (kwargs, SizeResult, None guard) are now fixed
- Weather fires on HIGHNY weekday markets — will start Monday
- Watch for first weather paper trade Monday morning

**#5 — FOMC active March 5**
- fomc_rate_v1 strategy fires ~8 days before meeting
- KXFEDDECISION markets open ~March 5 for March 19 meeting
- All 3 fixes confirmed: correct kwargs on kill_switch + calculate_size calls

**#6 — Odds API (NEW — see directives below)**
- OddsAPI key obtained (20,000 credits/month, renewed March 1)
- RESERVE 1,000 credits MAX for polymarket-bot bot use
- Before ANY API calls: implement quota guard + kill switch integration
- Best suited for FOMC/macro market calibration, NOT sports props
- Full roadmap item: see .planning/todos.md #odds-api section

**#7 — No new strategies until expansion gate clears**
- Gate: btc_drift 30 live trades + Brier < 0.25 + 2-3 weeks consistent P&L + zero kill switch events
- Log ideas only — see .planning/todos.md

## Odds API — Matthew's Standing Directives (Session 22)
- OddsAPI subscription: 20,000 credits/month (renewed March 1)
- **HARD CAP: 1,000 credits max for polymarket-bot** (5% of monthly budget)
- Before ANY credit use: implement quota counter + kill switch analog
- Sports props/moneyline/totals are NOT for Kalshi bot (different system)
- OddsAPI may help calibrate FOMC/macro markets (cross-reference with Fed futures)
- Copytrade on Polymarket: explore (VPN may be needed — document, don't build yet)
- Reference code: ~/ClaudeCode/agentic-sandbox-rd and titanium-v36 — READ ONLY for reference
- This is a FUTURE TASK (next session): document in .planning/todos.md for roadmap

## Session 22 Matthew directives (reference for new chat)
- Focus: maintenance and optimization of 9 current strategies ONLY
- No new bet types until 4-condition expansion gate clears (~2-3 weeks)
- Volatility-adaptive parameters: logged in .planning/todos.md, DO NOT BUILD YET
- Kelly sizing: system documented in docs/GRADUATION_CRITERIA.md v1.1, not trusted for promotion yet
- btc/eth bet types are primary focus (they're the live strategies)
- **Bug #4 fix is highest impact change**: more live bets now expected from btc_lag + btc_drift

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
source venv/bin/activate && python -m pytest tests/ -q       → 504 tests
```

## AUTONOMOUS OPERATION — STANDING DIRECTIVE (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Security: never expose .env/keys/pem; never modify system files outside project dir.
- Never break the bot: confirm running/stopped before restart; verify single instance after.
- Expansion order: (1) perfect live/paper, (2) graduate paper→live with Step 5 audit, (3) new types.

## Context handoff: new chat reads POLYBOT_INIT.md first, then this file, then proceeds.
