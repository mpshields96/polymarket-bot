# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-10 (Session 41 continued — btc_drift Stage 1 + KXXRP15M)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 43+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 42 continuation).

══════════════════════════════════════════════════════
MANDATORY: BEFORE WRITING A SINGLE LINE OF CODE, DO ALL OF THIS:
══════════════════════════════════════════════════════

STEP 1 — READ THESE FILES (required, in order):
  cat SESSION_HANDOFF.md                ← bot state + what to do next (this file, already reading)
  cat .planning/AUTONOMOUS_CHARTER.md   ← Matthew's complete autonomous ops rules — MANDATORY
  cat .planning/CHANGELOG.md            ← what changed every session and WHY
  cat .planning/KALSHI_MARKETS.md       ← COMPLETE Kalshi market map — ALL categories
  cat .planning/SKILLS_REFERENCE.md    ← ALL GSD/sc:/superpowers tools + token costs

STEP 2 — RESTART THE BOT FIRST. ALWAYS. NO EXCEPTIONS.
  RESTART COMMAND (check bot.pid for current PID first):
    pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
    sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
    echo "CONFIRM" > /tmp/polybot_confirm.txt
    nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session43.log 2>&1 &
    sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
  Verify: ps aux | grep "[m]ain.py" | wc -l should show 1 (exactly one process).

STEP 3 — RUN DIAGNOSTICS:
  source venv/bin/activate && python3 main.py --health        ← ALWAYS run this first
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status
  If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
  If --health shows "Consecutive loss cooling": ALREADY CLEARED BY RESTART in step 2.

STEP 4 — MANDATORY RULES:

  RULE A — AUTONOMOUS OPERATION (highest priority):
    Fully autonomous always. Do work first, summarize after. Never pause.
    All findings → /tmp/polybot_autonomous_monitor.md (append only, never overwrite)
    Monitor bot health every 10-15 minutes. Run --health on first sign of trouble.
    If paper OR live bets go silent for >1hr: run --health, diagnose, fix.

  RULE B — USE GSD + SUPERPOWERS TOOLS (MANDATORY, NOT OPTIONAL):
    DEFAULT for 90% of all work: gsd:quick + superpowers:TDD + superpowers:verification-before-completion
    ALWAYS FREE — use these on EVERY task:
      /superpowers:TDD                         ← before writing ANY implementation code
      /superpowers:verification-before-completion ← before claiming ANY work is done
      /superpowers:systematic-debugging        ← before proposing ANY bug fix
      /gsd:add-todo                           ← when any idea or issue surfaces
      /gsd:quick                              ← for any focused task, bug fix, or feature
    SESSION START (once only): /gsd:health then /gsd:progress
    Read .planning/SKILLS_REFERENCE.md — full tool list with token costs.

  RULE C — KALSHI MARKET RESEARCH (cannot be skipped every session):
    ACTION: Read RESEARCH DIRECTIVES in KALSHI_MARKETS.md. Probe API for undocumented series.

  RULE D — SESSION WRAP-UP (mandatory before any session end):
    1. python3 main.py --report → capture output
    2. python3 main.py --graduation-status → capture output
    3. cat bot.pid && kill -0 $(cat bot.pid) && echo RUNNING → confirm bot alive
    4. Update SESSION_HANDOFF.md with current state, pending tasks, last actions
    5. Append entry to .planning/CHANGELOG.md with what was done and WHY
    6. git add + git commit with descriptive message + git push
    7. Write handoff summary to /tmp/polybot_autonomous_monitor.md

══════════════════════════════════════════════════════

KEY STATE (Session 41 continued — 2026-03-10 ~21:40 CDT):
* Bot: PID 7868, LIVE mode, log /tmp/polybot_session42.log
* FOUR LIVE DRIFT LOOPS (last restart):
  - btc_drift_v1: STAGE 1 ($5 max/bet, Kelly governs) — calibration cap REMOVED
  - eth_drift_v1: MICRO-LIVE (1 contract ~$0.45/bet, calibration_max_usd=0.01)
  - sol_drift_v1: MICRO-LIVE (1 contract ~$0.45/bet, calibration_max_usd=0.01)
  - xrp_drift_v1: MICRO-LIVE NEW (1 contract ~$0.45/bet, calibration_max_usd=0.01) ← NEW Session 41
* 904/904 tests passing
* Last commit: 1c8a270 — feat: add KXXRP15M micro-live drift loop + btc_drift Stage 1 promotion
* Bankroll: ~$83.81 | All-time live P&L: -$15.28 (as of session end)
* Kill switch: CONSECUTIVE_LOSS_LIMIT=8 (raised from 4 this session)
* btc_drift: 42/30 ✅ Brier 0.249 STAGE 1 | eth_drift: 24/30 | sol_drift: 11/30 | xrp_drift: 0/30 NEW

SESSION 41 CONTINUED WORK DONE:
* btc_drift Stage 1 promotion: removed calibration_max_usd cap from trading_loop. 42/30 live bets,
  Brier 0.249. Kelly + $5 HARD_MAX now governs. Up from ~$0.45/bet to up to $5/bet.
* CONSECUTIVE_LOSS_LIMIT raised 4→8: daily loss limit governs at Stage 1 before consecutive fires.
  Not a statistical-outcome reaction — structural redesign of which gate governs at Stage 1.
* KXXRP15M drift loop built and deployed:
  - src/data/binance.py: _BINANCE_XRP_WS_URL + load_xrp_from_config()
  - src/strategies/btc_drift.py: load_xrp_drift_from_config()
  - config.yaml: xrp_drift section (min_drift_pct=0.10, 2x BTC) + xrp_ws_url feed
  - main.py: xrp_drift_task (KXXRP15M, stagger=33s, calibration_max_usd=0.01)
  - tests/test_xrp_strategy.py: 13 new tests (all passing)
  - tests/test_kill_switch.py: 8 tests updated to match new limit of 8
* Bot restarted with new code, confirmed running as PID 7868
* All 4 drift loops confirmed in startup log: [xrp_drift] Startup delay 33s ✅

NEXT SESSION DIRECTIVES (in priority order):
1. RESTART BOT FIRST (log to session43.log) — ALWAYS, no exceptions
2. Run --health, --report, --graduation-status → log to /tmp/polybot_autonomous_monitor.md
3. Monitor xrp_drift live bets placing (first live bet should happen within ~1-2 hours of restart)
4. Monitor btc_drift Stage 1 bets: should see larger bet sizes now (~$1-5 vs prior ~$0.45)
5. eth_drift graduation: 6 more live bets needed (24/30 as of this session)
6. sol_drift graduation: 19 more live bets needed (11/30)
7. xrp_drift calibration: target 30 live bets (0/30 NEW)
8. Probe KXBTCMAXW on WEEKDAY (dormant Sunday — check Mon-Fri for open weekly markets)
9. Check fomc paper bets progress: KXFEDDECISION-26MAR closes March 18

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: closed for new strategy TYPES. btc_drift graduated; expansion order is
  KXXRP15M micro-live (done ✅) → KXBTCMAX100/150 (post-research, post-gate) → annual markets
* 904 tests must pass before any commit (count updates each session)
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
```

# ═══════════════════════════════════════════════════════════════

## EXACT CURRENT STATE

Bot RUNNING — PID 7868, live mode, log: /tmp/polybot_session42.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session42.log
Health: source venv/bin/activate && python3 main.py --health

### FOUR Live drift loops:
- btc_drift_v1 → KXBTC15M | min_drift=0.05, min_edge=0.05 | 42/30 ✅ Brier 0.249 | STAGE 1 ($5 cap)
- eth_drift_v1 → KXETH15M | min_drift=0.05, min_edge=0.05 | 24/30 needs 6 more | micro-live
- sol_drift_v1 → KXSOL15M | min_drift=0.15, min_edge=0.05 | 11/30 needs 19 more | micro-live
- xrp_drift_v1 → KXXRP15M | min_drift=0.10, min_edge=0.05 | 0/30 NEW | micro-live
Kill switch: CONSECUTIVE_LOSS_LIMIT=8, daily_loss_limit=20%. btc_drift: Kelly + $5 hard max.

### Paper-only (12 loops):
btc_lag, eth_lag, sol_lag (0 signals/week — HFTs closed the lag)
orderbook_imbalance, eth_orderbook_imbalance
btc_daily, eth_daily, sol_daily (KXBTCD/KXETHD/KXSOLD hourly slots — paper)
weather_forecast (HIGHNY weekdays only)
fomc_rate (~8x/year — WORKING Session 40)
unemployment_rate (~12x/year — WORKING Session 40)
sports_futures_v1 (Polymarket.US bookmaker arb, paper-only, min_books=2)
copy_trader_v1 (Polymarket.US — 0 matches, platform mismatch confirmed)

### Tests: 904/904

### Last commits:
- 1c8a270 — feat: add KXXRP15M micro-live drift loop + btc_drift Stage 1 promotion (Session 41)
- 825e40d — (session 41 docs)

### P&L (as of 2026-03-10 21:40 CDT — Session 41 continued):
- Bankroll: ~$83.81 (approx)
- All-time live P&L: -$15.28
- Kill switch: consecutive=? | daily=? | hard stop CLEAR (run --health for exact)
- SDATA quota: 53/500 (11%) — resets 2026-04-01

### EXPANSION GATE STATUS:
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (42+) |
| Brier < 0.30 | ✅ MET (0.249) |
| 2-3 weeks live P&L data | ❌ NOT MET |
| No kill switch events in window | ❌ NOT MET |
Gate: CLOSED for NEW strategy types. btc_drift promoted to Stage 1 (this session).
KXXRP15M added as micro-live (this session) — same calibration pattern, not new type.

### PENDING TODOS:
- Monitor xrp_drift first live bets (should start placing within ~1-2 hours after restart)
- Monitor btc_drift Stage 1 bet sizes (should be larger than prior ~$0.45)
- eth_drift graduation: 6 more live bets needed (24/30)
- Probe KXBTCMAXW on WEEKDAY (dormant Sunday — check Mon-Fri for open weekly markets)
- Check fomc paper bets (KXFEDDECISION-26MAR closes March 18)

# ═══════════════════════════════════════════════════════════════

## AUTONOMOUS OPERATION MODE (active when Matthew is asleep or away)
* NEVER pause to ask questions. NEVER wait for confirmation. NEVER stop mid-task.
* All findings + actions → append to /tmp/polybot_autonomous_monitor.md (never overwrite)
  Format each entry: ## [TIMESTAMP CDT] — [status] — [action taken or NONE]
* ALWAYS restart bot at session start (clears soft stop — see step 2 above)
* Check bot alive: cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo RUNNING
* If bot STOPPED between monitoring cycles: restart immediately
* If kill switch HARD STOP: do NOT restart — log it, wait for Matthew
* Run --report + --graduation-status at each monitoring cycle; log results to MD
* If approaching context limit: update SESSION_HANDOFF.md + append CHANGELOG.md FIRST, then exit
* At session end: always append CHANGELOG.md entry

## RESUMING AFTER AUTONOMOUS PERIOD:
* cat /tmp/polybot_autonomous_monitor.md  <- what happened while you were away
* python3 main.py --report                <- current P&L state
* python3 main.py --graduation-status     <- live bet progress toward Brier
* python3 main.py --health                <- kill switch + open trades + quota

Once loaded: run /gsd:health then /gsd:progress (session start only, not mid-session).
Then: gsd:quick + superpowers:TDD + superpowers:verification-before-completion for all work.

# ═══════════════════════════════════════════════════════════════

## CURRENT BOT ARCHITECTURE (16 loops total — updated Session 41)

main.py asyncio event loop [LIVE MODE — PID 7868]

Kalshi 15-min loops:
  [trading]       btc_lag_v1             PAPER-ONLY (0 signals/week — market mature)
  [eth_trading]   eth_lag_v1             PAPER-ONLY
  [drift]         btc_drift_v1           STAGE 1 LIVE | KXBTC15M | drift=0.05 edge=0.05 | $5 cap
  [eth_drift]     eth_drift_v1           MICRO-LIVE | KXETH15M | drift=0.05 edge=0.05
  [sol_drift]     sol_drift_v1           MICRO-LIVE | KXSOL15M | drift=0.15 edge=0.05
  [xrp_drift]     xrp_drift_v1           MICRO-LIVE NEW | KXXRP15M | drift=0.10 edge=0.05
  [btc_imbalance] orderbook_imb_v1       PAPER-ONLY
  [eth_imbalance] eth_orderbook_imb_v1   PAPER-ONLY
  [weather]       weather_forecast_v1    PAPER-ONLY (weekdays only)
  [fomc]          fomc_rate_v1           PAPER-ONLY (~8x/year — WORKING Session 40)
  [unemployment]  unemployment_rate_v1   PAPER-ONLY (~12x/year — WORKING Session 40)
  [sol_lag]       sol_lag_v1             PAPER-ONLY

Kalshi daily loops (KXBTCD/KXETHD/KXSOLD — 24 hourly price-level slots/day):
  [btc_daily]     btc_daily_v1           PAPER-ONLY
  [eth_daily]     eth_daily_v1           PAPER-ONLY
  [sol_daily]     sol_daily_v1           PAPER-ONLY

Polymarket:
  [copy_trade]    copy_trader_v1         PAPER-ONLY (0 .us matches — platform mismatch)
  [sports_futures] sports_futures_v1     PAPER-ONLY (NBA/NHL/NCAAB futures, min_books=2)

# ═══════════════════════════════════════════════════════════════

## COMMANDS

### Check bot
  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"

### Live restart (use at EVERY session start — clears soft stop)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session43.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

### Watch drift loops (most active — live bets fire here)
  tail -f /tmp/polybot_session42.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

### Watch everything
  tail -f /tmp/polybot_session42.log

### Diagnostics
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA
  source venv/bin/activate && python3 -m pytest tests/ -q         # 904/904 required before commit
  grep "xrp_drift" /tmp/polybot_session42.log                     # check xrp_drift signals/bets

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/AUTONOMOUS_CHARTER.md — autonomous ops rules (MANDATORY, acknowledge)
3. .planning/CHANGELOG.md — what changed and WHY, every session
4. .planning/KALSHI_MARKETS.md — full market map before any strategy work
5. .planning/SKILLS_REFERENCE.md — tool selection + token cost tiers
6. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
