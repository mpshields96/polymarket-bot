# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-09 (Session 37 autonomous close-out — 09:22 CDT)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 37+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 37).
Read these files immediately before doing anything else:
  1. cat SESSION_HANDOFF.md          <- exact bot state + what to do next
  2. cat .planning/CHANGELOG.md      <- what changed each session and WHY (permanent record)
  3. cat .planning/KALSHI_MARKETS.md <- complete Kalshi market map, volumes, what is built
Do NOT ask setup questions. Do NOT write code until you have read all three.

KEY STATE (Session 37 autonomous close — 2026-03-09 09:22 CDT):
* Bot: PID 90027, live mode, log /tmp/polybot_session37.log
* THREE MICRO-LIVE LOOPS: btc_drift + eth_drift + sol_drift (all ~$0.35-0.65/bet, unlimited/day)
* All others: PAPER-ONLY. 869/869 tests passing.
* Last commits: 69678a8 (execution-time price guard todo), 0745785 (graduation_stats bug todo)
* Bankroll: ~$79.76 | All-time live P&L: -$16.12 | Today live: +$2.73
* btc_drift: 30/30 ✅, Brier 0.2526 ✅ | eth_drift: 17 live settled | sol_drift: 10 live settled
* Kill switch: SOFT STOP active (4 consec losses, fired 09:04 CDT, expires ~11:02 CDT)
  DO NOT RESET — correct behavior after 4 consecutive losses
* Protection: 20% daily loss (38% used today = $6.30/$16.44) + $20 floor. Hard stop: CLEAR.
* 2 PENDING TODOS: graduation_stats bug (low) + execution-time price guard (HIGH)

NEXT SESSION DIRECTIVE: Fix execution-time price guard in live.py (HIGH PRIORITY — see todo).
After fix, graduation_stats() is_paper param fix. Then wait until expansion gate criteria met.

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: no new live strategies until btc_drift 30+ live trades + Brier < 0.30
* 869 tests must pass before any commit (count updates each session)
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

Bot RUNNING — PID 74462, live mode, log: /tmp/polybot_session36.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session36.log
Health: source venv/bin/activate && python3 main.py --health

### THREE Live drift loops (all micro-live, 1 contract/bet ~$0.35-0.65):
- btc_drift_v1 -> KXBTC15M | min_drift=0.05, min_edge=0.05 | RESTORED Session 36
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

### Tests: 869/869

### Last commits:
- 69678a8 — docs: capture todo - add execution-time price guard to live executor
- 0745785 — docs: capture todo - Fix graduation_stats to query live bets for live strategies
- 8a312d0 — docs: autonomous session final — btc_drift Brier gate MET + kill switch event
- d1f10f0 — docs: autonomous session 37 — bug discovery + live bet count update

### P&L (as of 2026-03-09 09:22 CDT — Session 37 autonomous close):
- Bankroll: ~$79.76 (daily loss offset)
- All-time live P&L: -$16.12
- Today: live +$2.73 (btc_drift 11/18 61%, eth_drift 10/17 59%, sol_drift 8/10 80%)
- btc_drift: **30/30** live settled bets ✅ | Brier = **0.2526** ✅ (< 0.30 threshold MET)
- eth_drift: 17 live settled. sol_drift: 10 live settled.
- Protection: daily loss $6.30/$16.44 (38%), $20 floor. NO lifetime hard stop.

### EXPANSION GATE STATUS (updated 09:22 CDT):
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (exactly 30) |
| Brier < 0.30 | ✅ MET (0.2526) |
| 2-3 weeks live P&L data | ❌ NOT MET (~1 day live) |
| No kill switch events | ❌ NOT MET (SECOND soft stop fired 09:04 CDT this session) |
Gate: STILL CLOSED. Two criteria unmet. Do not build XRP drift until criteria above both pass.

### PENDING TODOS (2):
1. HIGH — live.py execution-time price guard missing (filed 08:46 CDT today)
   → Signal at 59¢ placed at 84¢ (25¢ slippage bypasses price guard). See todo.
2. LOW — graduation_stats() only queries is_paper=1 (reporting bug, no trading impact)
   See: .planning/todos/pending/2026-03-09-fix-graduation-stats-to-query-live-bets-for-live-strategies.md
   See: .planning/todos/pending/2026-03-10-add-execution-time-price-guard-to-live-executor.md

### KILL SWITCH STATE (at Session 37 autonomous close — 09:22 CDT):
- Soft stop: 4 consecutive losses → 2hr cooling (started 09:04 CDT, expires ~11:02-11:04 CDT)
- Hard stop: CLEAR (no lock file)
- Daily loss: $6.30 / $16.44 (38%) — safe, $10.14 remaining before daily limit
- On restart before 11:04 CDT: cooling will be seeded from DB and still active
- On restart after 11:04 CDT: cooling expired, counter resets, safe to trade

# ═══════════════════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE (15 loops total)

main.py asyncio event loop [LIVE MODE — PID 90027]

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

## SESSION 36 WORK COMPLETED (2026-03-08 to 2026-03-09)

1. btc_drift thresholds RESTORED — min_drift 0.10->0.05, min_edge 0.08->0.05
   Session 25 raised these with only 12 live trades (PRINCIPLES.md violation). Fixed.
   Result: 1 bet/day -> 8-15 signals/day. Commit: aa83e78

2. eth_drift MICRO-LIVE enabled — same 1-contract cap, shared lock. Commit: aa83e78

3. sol_drift_v1 NEW — KXSOL15M, min_drift=0.15 (3x BTC volatility). Commit: 11ff825

4. .planning/CHANGELOG.md CREATED — permanent append-only session log.
   Every future session MUST append. Never truncate. Commit: 1dc85c6

5. .planning/KALSHI_MARKETS.md CREATED + FULL LIVE RE-PROBE
   5 new market categories discovered (player props, parlays, MLB game winners, Oscars, CPI).
   Volume data added for all series. Expansion roadmap documented.
   Commits: 7197556, 25b5f2b

6. --report BUG FIXED — now splits by (strategy, is_paper) per trade.
   Old paper data never lost. Transition days show two rows (correct). Commit: 3477987

7. Kalshi copy trading RESEARCH re-confirmed infeasible.
   API docs confirm zero trader attribution. All GitHub bots use statistical edge.
   Documented in CLAUDE.md + MEMORY.md.

8. MEMORY.md rewritten — was over 200-line limit with stale facts. Now current.

9. GSD health W007 FIXED — phase 04.2 added to ROADMAP.md with correct `### Phase 04.2:` format.
   GSD health now: HEALTHY (0 errors, 0 warnings). Commit: e904715

10. Stale todos CLEARED — 2 todos from 2026-02-28 both completed in Sessions 31/35.
    Moved to .planning/todos/completed/. Pending queue: 0.

# ═══════════════════════════════════════════════════════════════

## PENDING DECISIONS + NEXT TASKS

1. ✅ BRIER GATE MET — btc_drift 30 live bets, Brier 0.2526. Expansion gate criteria check needed.
   DO NOT build XRP drift yet — 2 remaining criteria unmet (see EXPANSION GATE STATUS table above).
   Matthew: review kill switch event (5 consec losses, soft stop 01:49 CDT). Decide when to restart.

2. RESTART CAUTION — kill switch soft stop active at shutdown (expires 03:49 CDT).
   On restart before 03:49 CDT: cooling period will be seeded from DB and remain active.
   On restart after 03:49 CDT: cooling expired, consecutive counter resets to 0.
   Either way: bot is safe to restart.

3. XRP drift — NEXT safe expansion after drift validates.
   Same code as sol_drift, ~15 min. KXXRP15M ~5,900 volume confirmed.
   min_drift_pct ~0.10-0.12 (XRP ~2x BTC volatility). DO NOT BUILD YET.

4. KXNBAGAME/KXNHLGAME game winners — gate: sports_futures_v1 shows edge first.
   Skeleton exists in sports_game.py, not wired.

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
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session36.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

### Watch drift loops (most active — live bets fire here)
  tail -f /tmp/polybot_session36.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

### Watch everything
  tail -f /tmp/polybot_session36.log

### Diagnostics
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA
  source venv/bin/activate && python3 -m pytest tests/ -q         # 869/869 required before commit

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/CHANGELOG.md — what changed and WHY, every session
3. .planning/KALSHI_MARKETS.md — full market map before any strategy work
4. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
