# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-09 (Session 38 close-out — full docs + POLYBOT_INIT update)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 39+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 38 close-out).

══════════════════════════════════════════════════════
MANDATORY: BEFORE WRITING A SINGLE LINE OF CODE, DO ALL OF THIS:
══════════════════════════════════════════════════════

STEP 1 — READ THESE FILES (required, in order):
  cat SESSION_HANDOFF.md          ← bot state + what to do next (this file, already reading)
  cat .planning/CHANGELOG.md      ← what changed every session and WHY
  cat .planning/KALSHI_MARKETS.md ← COMPLETE Kalshi market map — ALL categories
  cat .planning/SKILLS_REFERENCE.md ← ALL GSD/sc:/superpowers tools + token costs

STEP 2 — MANDATORY RULES FOR EVERY SESSION:

  RULE A — KALSHI MARKET RESEARCH (CANNOT BE SKIPPED):
    Kalshi has MANY market types beyond the 15-min direction markets we trade.
    From kalshi.com Crypto tab: 15 Minute ✅ | Hourly ✅paper | Daily ✅paper |
      Weekly ($455K vol) | Monthly | Annual ($1.4M vol) | One Time ($14.8M vol!)
    Full Kalshi nav UNDOCUMENTED: Politics | Culture | Climate | Economics |
      Mentions | Companies | Financials | Tech & Science
    ACTION: Read RESEARCH DIRECTIVES section of KALSHI_MARKETS.md.
    When bandwidth exists: probe API for weekly/monthly/annual/one-time tickers.
    Search reddit.com/r/kalshi for strategies. Search GitHub. Update KALSHI_MARKETS.md.
    DO NOT ignore these categories. DO NOT say "that's for later". Investigate now.

  RULE B — USE GSD + SUPERPOWERS TOOLS (MANDATORY, NOT OPTIONAL):
    These tools exist to prevent bugs that have cost real money. Use them every time.
    DEFAULT for 90% of all work: gsd:quick + superpowers:TDD + superpowers:verification-before-completion
    ALWAYS FREE — use these on EVERY task without asking:
      /superpowers:TDD                         ← before writing ANY implementation code
      /superpowers:verification-before-completion ← before claiming ANY work is done
      /superpowers:systematic-debugging        ← before proposing ANY bug fix
      /gsd:add-todo                           ← when any idea or issue surfaces
      /gsd:quick                              ← for any focused task, bug fix, or feature
    SESSION START (once only): /gsd:health then /gsd:progress
    Read .planning/SKILLS_REFERENCE.md — full tool list with token costs.
    NEVER implement code without superpowers:TDD. NEVER say "done" without superpowers:verification.

  RULE C — FULLY AUTONOMOUS (Matthew is a doctor with a new baby):
    Never pause to ask for confirmation. Do work first, summarize after.
    If Matthew is away: append to /tmp/polybot_autonomous_monitor.md
    Never break the bot: verify PID before restart, verify single instance after.

══════════════════════════════════════════════════════

KEY STATE (Session 38 close-out — 2026-03-09 ~18:00 CDT):
* Bot: PID 96757, LIVE mode, log /tmp/polybot_session38.log
* THREE MICRO-LIVE LOOPS: btc_drift + eth_drift + sol_drift (all ~$0.35-0.65/bet, unlimited/day)
* All others: PAPER-ONLY. 887/887 tests passing.
* Last commits: c2a2192 (POLYBOT_INIT docs), 159eead (graduation stats todo complete)
* Bankroll: ~$84.33 | All-time live P&L: -$13.37 | P&L today: +$5.48 live
* Kill switch: CLEAR — daily $6.30/$16.88 (37%), consecutive 0/4, hard stop CLEAR
* btc_drift: 37/30 ✅ Brier 0.247 | eth_drift: 19/30 | sol_drift: 11/30
* SDATA: 53/500 (11%) — resets 2026-04-01
* Expansion gate: STILL CLOSED (2-3 weeks live data needed + no KS events)
* KXBTCD hourly bets: paper via btc_daily_v1 — 24 hourly price-level slots/day
* Kalshi weekly/annual/one-time bets: $14.8M volume — UNDOCUMENTED, research needed

NEXT SESSION DIRECTIVE (in priority order):
1. Probe Kalshi API for Weekly/Monthly/Annual/One-Time crypto tickers (KXBTCW? etc.)
   Search reddit.com/r/kalshi + GitHub for these market strategies
   Update .planning/KALSHI_MARKETS.md with findings
2. Monitor eth_drift + sol_drift graduation (11 + 19 more live bets needed)
3. Check btc_daily_v1 paper graduation progress (--graduation-status)
4. Monitor btc_drift YES vs NO win rate asymmetry (wait 30 more clean bets)
5. Expansion gate still closed — no new live strategies yet

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: no new live strategies until 2-3 weeks live data + no KS events
* 887 tests must pass before any commit (count updates each session)
* Read .planning/CHANGELOG.md at session start, append entries at session end
* Read .planning/KALSHI_MARKETS.md BEFORE any Kalshi strategy or market work
* Read .planning/SKILLS_REFERENCE.md BEFORE choosing any implementation tool
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
```

# ═══════════════════════════════════════════════════════════════

## EXACT CURRENT STATE

Bot RUNNING — PID 96757, live mode, log: /tmp/polybot_session38.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session38.log
Health: source venv/bin/activate && python3 main.py --health

### THREE Live drift loops (all micro-live, 1 contract/bet ~$0.35-0.65):
- btc_drift_v1 -> KXBTC15M | min_drift=0.05, min_edge=0.05 | 37/30 ✅ Brier 0.247
- eth_drift_v1 -> KXETH15M | min_drift=0.05, min_edge=0.05 | 19/30 needs 11 more
- sol_drift_v1 -> KXSOL15M | min_drift=0.15, min_edge=0.05 | 11/30 needs 19 more
All share: _live_trade_lock, calibration_max_usd=0.01, price guard 35-65 cents.
Combined: ~15-25 live bets/day.

### KXBTCD Hourly Bets (btc_daily_v1) — PAPER, monitor graduation
24 hourly price-level slots/day. KXBTC1H does NOT exist — these are inside KXBTCD.
Strategy: CryptoDailyStrategy — ATM contract (closest to 50¢, 30min–6hr window)
Model: 70% drift + 30% lognormal. ~5,000 total volume (20x less liquid than 15-min).
Gate to go live: expansion gate criteria. Check: python3 main.py --graduation-status

### Paper-only (12 loops):
btc_lag, eth_lag, sol_lag (0 signals/week — HFTs closed the lag)
orderbook_imbalance, eth_orderbook_imbalance
btc_daily, eth_daily, sol_daily (KXBTCD/KXETHD/KXSOLD hourly slots — paper)
weather_forecast (HIGHNY weekdays only), fomc_rate (~8x/year), unemployment_rate (~12x/year)
sports_futures_v1 (Polymarket.US bookmaker arb, paper-only, min_books=2)
copy_trader_v1 (Polymarket.US — 0 matches, platform mismatch confirmed)

### Tests: 887/887

### Last commits:
- c2a2192 — docs: update POLYBOT_INIT with live.py security findings + SKILLS_REFERENCE link
- 159eead — docs: move graduation_stats todo to completed
- 992abd6 — docs(quick-8): complete graduation_stats is_paper param fix — SUMMARY + STATE update
- 2fab9e6 — fix(quick-8): update callers to pass is_paper per strategy
- 82c90c7 — test(quick-8): RED — add failing tests for graduation_stats is_paper param
- 9009fa8 — fix(live): guard against recording canceled orders as live bets

### P&L (as of 2026-03-09 18:00 CDT — Session 38 close-out):
- Bankroll: ~$84.33
- All-time live P&L: -$13.37
- P&L today (live): +$5.48 (btc_drift 14/21, eth_drift 12/19, sol_drift 9/11)
- Kill switch: CLEAR — daily $6.30/$16.88 (37%), consecutive 0/4, hard stop CLEAR
- SDATA quota: 53/500 (11%) — resets 2026-04-01

### EXPANSION GATE STATUS (Session 38 close-out):
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (37+) |
| Brier < 0.30 | ✅ MET (0.247) |
| 2-3 weeks live P&L data | ❌ NOT MET (~2 days live) |
| No kill switch events in window | ❌ NOT MET (multiple soft stops) |
Gate: STILL CLOSED. Next expansion = KXXRP15M drift (same code as sol_drift, ~15 min).

### PENDING TODOS (0):
All todos cleared this session.

### SESSION 37-38 WORK COMPLETED:
Session 37:
1. Execution-time price guard — live.py (signal@59¢ filled@84¢ → blocked). 6 tests.
2. --reset-soft-stop flag — clears consecutive loss counter/cooling on startup. 5 tests.
3. btc_drift calibration analysis — 34 live bets, Brier 0.2503. BUY YES 35.7% vs BUY NO 55%.
4. sc:analyze security audit on live.py — found 3 issues, highest filed as todo.
5. SKILLS_REFERENCE.md created — complete skill/command map with token cost tiers.

Session 38:
6. sports_futures ValueError fix — %.1%% → %.1f%% (was spamming logs). Commit: b6e32ae
7. Canceled order guard — status=="canceled" → return None before db.save_trade(). 2 tests.
8. graduation_stats(is_paper) fix — live strategies now show live bet counts. 5 tests.
   btc_drift: 12 → 37 ✅, eth_drift: 0 → 19, sol_drift: not tracked → 11
   sol_drift_v1 added to _GRAD in verify.py (was missing entirely).
9. POLYBOT_INIT.md — full current status update (Session 31 → Session 38). Autonomous ops guide.
   KXBTCD hourly bets expansion roadmap added.

# ═══════════════════════════════════════════════════════════════

## AUTONOMOUS OPERATION MODE (active when Matthew is asleep or away)
* NEVER pause to ask questions. NEVER wait for confirmation. NEVER stop mid-task.
* All findings + actions → append to /tmp/polybot_autonomous_monitor.md (never overwrite)
  Format each entry: ## [TIMESTAMP CDT] — [status] — [action taken or NONE]
* Check bot alive: cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo RUNNING
* If bot STOPPED: restart immediately using live restart command (COMMANDS section below)
* If kill switch fired: log it, do NOT reset — daily loss limit governs, leave it alone
* Run --report + --graduation-status at each monitoring cycle; log results to MD
* If approaching context limit: update SESSION_HANDOFF.md + append CHANGELOG.md FIRST, then exit
* At session end (with or without work done): always append CHANGELOG.md entry

## RESUMING AFTER AUTONOMOUS PERIOD:
* cat /tmp/polybot_autonomous_monitor.md  <- what happened while you were away
* python3 main.py --report                <- current P&L state
* python3 main.py --graduation-status     <- live bet progress toward Brier
* python3 main.py --health                <- kill switch + open trades + quota

Once loaded: run /gsd:health then /gsd:progress (session start only, not mid-session).
Then: gsd:quick + superpowers:TDD + superpowers:verification-before-completion for all work.

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

Kalshi daily loops (KXBTCD/KXETHD/KXSOLD — 24 hourly price-level slots/day):
  [btc_daily]     btc_daily_v1           PAPER-ONLY (price-level, 70% drift + 30% lognormal)
  [eth_daily]     eth_daily_v1           PAPER-ONLY
  [sol_daily]     sol_daily_v1           PAPER-ONLY

Polymarket:
  [copy_trade]    copy_trader_v1         PAPER-ONLY (0 .us matches — platform mismatch)
  [sports_futures] sports_futures_v1     PAPER-ONLY (NBA/NHL/NCAAB futures, min_books=2)

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
  source venv/bin/activate && python3 -m pytest tests/ -q         # 887/887 required before commit

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/CHANGELOG.md — what changed and WHY, every session
3. .planning/KALSHI_MARKETS.md — full market map before any strategy work
4. .planning/SKILLS_REFERENCE.md — tool selection + token cost tiers
5. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
