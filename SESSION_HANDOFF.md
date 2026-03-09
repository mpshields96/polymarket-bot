# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-09 (Session 38 — home restart + canceled order fix)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 39+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 38).
Read these files immediately before doing anything else:
  1. cat SESSION_HANDOFF.md          <- exact bot state + what to do next
  2. cat .planning/CHANGELOG.md      <- what changed each session and WHY (permanent record)
  3. cat .planning/KALSHI_MARKETS.md <- complete Kalshi market map, volumes, what is built
Do NOT ask setup questions. Do NOT write code until you have read all three.

KEY STATE (Session 38 — 2026-03-09 17:22 CDT):
* Bot: PID 96757, live mode, log /tmp/polybot_session38.log
* THREE MICRO-LIVE LOOPS: btc_drift + eth_drift + sol_drift (all ~$0.35-0.65/bet, unlimited/day)
* All others: PAPER-ONLY. 882/882 tests passing.
* Last commits: 76a4726 (canceled-order guard docs), 9009fa8 (canceled-order guard fix)
* Bankroll: ~$84.33 | All-time live P&L: -$13.99 | Kill switch: CLEAR (0/4 consec, $6.30/$20 daily)
* btc_drift: graduation_stats shows 12 (BUG — known todo, paper/live filter wrong)
* eth_drift: 64 paper bets in stats (BUG — same filter issue)
* Expansion gate: STILL CLOSED (2-3 weeks live data needed + no KS events)

NEXT SESSION DIRECTIVE:
1. Fix graduation_stats() is_paper param (LOW — reporting only, no trading impact)
2. Update POLYBOT_INIT.md with sc:analyze security findings + SKILLS_REFERENCE.md link (DOCS)
3. Monitor btc_drift YES vs NO directional win rates after 30 more clean bets
4. Wait for expansion gate criteria before building new strategies

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: no new live strategies until btc_drift 30+ live trades + Brier < 0.30
* 882 tests must pass before any commit (count updates each session)
* Read .planning/CHANGELOG.md at session start, append entries at session end
* Read .planning/KALSHI_MARKETS.md before any Kalshi strategy work
* Never touch files outside /Users/matthewshields/Projects/polymarket-bot/

TOKEN BUDGET (Matthew's standing permission — never needs repeating):
* gsd:health + gsd:progress: ONCE at session start only (~1-2% each, ~Low tier)
* gsd:quick: use freely for any focused task, bug fix, or feature (~1-2%, Low tier)
* superpowers:TDD, superpowers:verification-before-completion,
  superpowers:systematic-debugging, gsd:add-todo: ALWAYS FREE (inline markdown, no agent)
* Tier-expensive (gsd:plan-phase, gsd:execute-phase, gsd:verify-work,
  superpowers:dispatching-parallel-agents): max 5 uses per 5-hour window, each ~3-5%
  budget. ONLY when ALL conditions met: 5+ tasks, 4+ subsystems, multi-session, PLAN.md needed.
* Default: gsd:quick + superpowers:TDD + superpowers:verification-before-completion
* sc:analyze, sc:test, sc:troubleshoot --think: Low-Medium tier (~1-5%) — use freely
  when auditing security, reviewing test coverage, or debugging stuck issues.

AUTONOMOUS OPERATION MODE (active when Matthew is asleep or away):
* NEVER pause to ask questions. NEVER wait for confirmation. NEVER stop mid-task.
* All findings + actions → append to /tmp/polybot_autonomous_monitor.md (never overwrite)
  Format each entry: ## [TIMESTAMP CDT] — [status] — [action taken or NONE]
* Check bot alive: cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo RUNNING
* If bot STOPPED: restart immediately using live restart command (COMMANDS section below)
* If kill switch fired: log it, do NOT reset — daily loss limit governs, leave it alone
* Run --report + --graduation-status at each monitoring cycle; log results to MD
* If approaching context limit: update SESSION_HANDOFF.md + append CHANGELOG.md FIRST, then exit
* At session end (with or without work done): always append CHANGELOG.md entry

RESUMING AFTER AUTONOMOUS PERIOD:
* cat /tmp/polybot_autonomous_monitor.md  <- what happened while you were away
* python3 main.py --report                <- current P&L state
* python3 main.py --graduation-status     <- live bet progress toward Brier
* python3 main.py --health                <- kill switch + open trades + quota

Once loaded: run /gsd:health then /gsd:progress (session start only, not mid-session).
Then: gsd:quick + superpowers:TDD + superpowers:verification-before-completion for all work.
```

# ═══════════════════════════════════════════════════════════════

## EXACT CURRENT STATE

Bot RUNNING — PID 96757, live mode, log: /tmp/polybot_session38.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session38.log
Health: source venv/bin/activate && python3 main.py --health

### THREE Live drift loops (all micro-live, 1 contract/bet ~$0.35-0.65):
- btc_drift_v1 -> KXBTC15M | min_drift=0.05, min_edge=0.05 | thresholds RESTORED Session 36
- eth_drift_v1 -> KXETH15M | min_drift=0.05, min_edge=0.05 | ENABLED Session 36
- sol_drift_v1 -> KXSOL15M | min_drift=0.15, min_edge=0.05 | NEW Session 36 (3x BTC volatility)
All share: _live_trade_lock, calibration_max_usd=0.01, price guard 35-65 cents.
Combined: ~15-25 live bets/day. Target: 30 settled each for Brier computation.

### Paper-only (12 loops):
btc_lag, eth_lag, sol_lag (0 signals/week — HFTs closed the lag)
orderbook_imbalance, eth_orderbook_imbalance
btc_daily, eth_daily, sol_daily (KXBTCD/KXETHD/KXSOLD hourly slots)
weather_forecast (HIGHNY weekdays only), fomc_rate (~8x/year), unemployment_rate (~12x/year)
sports_futures_v1 (Polymarket.US bookmaker arb, paper-only, min_books=2)
copy_trader_v1 (Polymarket.US — 0 matches, platform mismatch confirmed)

### Tests: 882/882

### Last commits:
- 76a4726 — docs(quick-7): canceled-order guard SUMMARY + STATE update
- 9009fa8 — fix(live): guard against recording canceled orders as live bets
- 6127cea — test(quick-7): add failing tests for canceled/resting order status guard
- b6e32ae — fix: correct %.1f%% format in sports_futures logger
- ebf7150 — docs: capture todo - Update POLYBOT_INIT docs with live.py security findings

### P&L (as of 2026-03-09 17:22 CDT — Session 38):
- Bankroll: ~$84.33
- All-time live P&L: -$13.99
- Kill switch: CLEAR — daily $6.30/$20 (32%), consecutive 0/4, hard stop CLEAR
- Live bet confirmed today: trade_id=446 btc_drift YES@36¢ (status=executed)

### EXPANSION GATE STATUS (updated Session 38):
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (34+) |
| Brier < 0.30 | ✅ MET (0.2526 clean) |
| 2-3 weeks live P&L data | ❌ NOT MET (~2 days live) |
| No kill switch events in window | ❌ NOT MET (multiple soft stops) |
Gate: STILL CLOSED. Do not build XRP drift until criteria above both pass.

### PENDING TODOS (3):
1. LOW — graduation_stats() only queries paper trades for live strategies (reporting bug)
   See: .planning/todos/pending/2026-03-09-fix-graduation-stats-to-query-live-bets-for-live-strategies.md
2. MONITOR — btc_drift YES vs NO win rate asymmetry (BUY YES 35.7% vs BUY NO 55%)
   See: .planning/todos/pending/2026-03-09-monitor-btc-drift-directional-calibration-yes-vs-no-win-rates.md
3. DOCS — Update POLYBOT_INIT.md with sc:analyze security findings + SKILLS_REFERENCE.md link
   See: .planning/todos/pending/2026-03-09-update-polybot-init-docs-with-live-py-security-findings-and-skills-reference.md

### SECURITY FIXES APPLIED (Sessions 37-38):
- Execution-time price guard: added to live.py (signal@59¢ filled@84¢ → blocked)
- Canceled order guard: added to live.py (status="canceled" → return None, never save to DB)
- sports_futures ValueError fix: %.1%% → %.1f%% (was spamming logs)

# ═══════════════════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE (15 loops total)

main.py asyncio event loop [LIVE MODE — PID 96757]

Kalshi 15-min loops:
  [trading]       btc_lag_v1             PAPER-ONLY (0 signals/week — market mature)
  [eth_trading]   eth_lag_v1             PAPER-ONLY
  [drift]         btc_drift_v1           MICRO-LIVE | KXBTC15M | drift=0.05 edge=0.05
  [eth_drift]     eth_drift_v1           MICRO-LIVE | KXETH15M | drift=0.05 edge=0.05
  [sol_drift]     sol_drift_v1           MICRO-LIVE | KXSOL15M | drift=0.15 edge=0.05
  [btc_imbalance] orderbook_imb_v1       PAPER-ONLY
  [eth_imbalance] eth_orderbook_imb_v1   PAPER-ONLY
  [weather]       weather_forecast_v1    PAPER-ONLY (weekdays only)
  [fomc]          fomc_rate_v1           PAPER-ONLY (~8x/year)
  [unemployment]  unemployment_rate_v1   PAPER-ONLY (~12x/year)
  [sol_lag]       sol_lag_v1             PAPER-ONLY

Kalshi daily loops:
  [btc_daily]     btc_daily_v1           PAPER-ONLY (KXBTCD, 24 hourly slots/day)
  [eth_daily]     eth_daily_v1           PAPER-ONLY (KXETHD)
  [sol_daily]     sol_daily_v1           PAPER-ONLY (KXSOLD)

Polymarket:
  [copy_trade]    copy_trader_v1         PAPER-ONLY (0 .us matches — platform mismatch)
  [sports_futures] sports_futures_v1     PAPER-ONLY (NBA/NHL/NCAAB futures, min_books=2)

# ═══════════════════════════════════════════════════════════════

## SESSION 37-38 WORK COMPLETED (2026-03-09)

Session 37 (autonomous + home work):
1. Execution-time price guard — added to live.py after orderbook fetch:
   - Re-checks YES-equiv price against 35-65¢ at execution time
   - Rejects if slippage > 10¢ from signal price
   - Fixes: signal@59¢ filled@84¢ (25¢ slippage, happened in prod)
   - 6 new tests in TestExecutionPriceGuard. Commit: 3c8baa9
2. --reset-soft-stop flag — clears consecutive loss counter/cooling at startup
   5 new tests. Commit: 92aee5f
3. btc_drift calibration analysis — 34 live bets, Brier 0.2503 overall
   Clean data (35-65¢): 20 bets, BUY YES 35.7% vs BUY NO 55% — directional asymmetry
4. sc:analyze security audit on live.py — found 3 issues, highest filed as todo
5. SKILLS_REFERENCE.md created — complete skill/command map with token costs

Session 38 (home restart):
6. sports_futures ValueError fix — %.1%% → %.1f%% in logger (two lines)
   Commit: b6e32ae
7. Canceled order guard — live.py now checks order.status == "canceled" before db.save_trade()
   Return None instead of recording a phantom live bet. 2 new tests. Commit: 9009fa8
8. CLAUDE.md Gotchas updated — live.py unit tests status corrected, canceled-order finding added
9. SESSION_HANDOFF.md updated (this file)

# ═══════════════════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS

1. Fix graduation_stats() is_paper param — LOW priority reporting bug.
   graduation_stats() doesn't pass is_paper=0 for live strategies, shows wrong counts.

2. POLYBOT_INIT.md + docs update — add sc:analyze findings + SKILLS_REFERENCE.md link.
   Captures the 3 security findings for future session awareness.

3. XRP drift — NEXT expansion after gate criteria met.
   Same code as sol_drift, ~15 min. KXXRP15M ~5,900 volume confirmed.
   min_drift_pct ~0.10-0.12 (XRP ~2x BTC volatility). DO NOT BUILD YET.

4. KXNBAGAME/KXNHLGAME game winners — gate: sports_futures_v1 shows edge first.

5. Copy trading blocked (platform mismatch). No action until .US platform expands.

6. Run python3 main.py --health first if no live bets for 24hr+.

# ═══════════════════════════════════════════════════════════════

## COMMANDS

### Check bot
  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"

### Live restart (use when bot needs restart)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session38.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

### Watch drift loops (most active — live bets fire here)
  tail -f /tmp/polybot_session38.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

### Watch everything
  tail -f /tmp/polybot_session38.log

### Diagnostics
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA
  source venv/bin/activate && python3 -m pytest tests/ -q         # 882/882 required before commit

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/CHANGELOG.md — what changed and WHY, every session
3. .planning/KALSHI_MARKETS.md — full market map before any strategy work
4. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
