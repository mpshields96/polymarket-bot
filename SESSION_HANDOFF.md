# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-10 (Session 42 continued — graduation tracking fix + btc_daily gotcha)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 43+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 43).

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

KEY STATE (Session 42 end — 2026-03-10 ~22:40 CDT):
* Bot: PID 8442, LIVE mode, log /tmp/polybot_session42.log
* SIX LIVE LOOPS (daily loss cap REMOVED Session 42):
  - btc_drift_v1: STAGE 1 ($5 max/bet, Kelly governs) — 43/30 ✅ Brier 0.250
  - eth_drift_v1: MICRO-LIVE (1 contract ~$0.45/bet) — 24/30 (6 more needed)
  - sol_drift_v1: MICRO-LIVE (1 contract ~$0.45/bet) — 12/30 (18 more needed)
  - xrp_drift_v1: MICRO-LIVE (1 contract ~$0.45/bet) — 1/30 (29 more needed)
  - btc_lag_v1: LIVE but 0 signals/week (HFTs priced out the lag edge — tracked paper)
  - eth_orderbook_imbalance_v1: LIVE — 1/30 live bets (trade 556 today, first live WIN $4.24)
* Kill switch: daily_loss_cap=DISABLED, consecutive_loss_limit=8
  Active protection: bankroll floor $20 + 8 consecutive → 2hr pause + $5/bet hard cap
* 904/904 tests passing
* Last commit: f6ccec6 — fix: graduation tracking for xrp_drift_v1 and eth_orderbook_imbalance_v1
* Bankroll: ~$83.57 | All-time live P&L: -$14.62 | Today live P&L: +$0.72
* Graduation: btc_drift 43/30 ✅ | eth_drift 24/30 | sol_drift 12/30 | xrp_drift 1/30 (live) | eth_imbalance 1/30 (live)
* SDATA quota: 74/500 (15%) — resets 2026-04-01

SESSION 42 WORK DONE (this session and continuation):
* btc_lag_v1 promoted to LIVE: live_executor_enabled=live_mode. Pre-live audit passed.
* eth_orderbook_imbalance_v1 promoted to LIVE: first live bet = trade 556 (WIN +$4.24)
* Daily loss cap REMOVED from kill_switch.py (user directive). Only: bankroll floor + consecutive cooling.
* Bot restarted: PID 8442. XRP drift confirmed active in log.
* Kalshi market research: KXBTCMAXW confirmed dormant (0 open on both Sunday and Tuesday).
  KXBTCMAX100 updated pricing (DEC 41/42c). KXNASDAQ100Y discovered ($516k vol).
  Non-crypto series map complete in KALSHI_MARKETS.md.
  Polymarket BTC loophole mechanism documented (btc_lag HFT arbitrage explanation).
* GRADUATION TRACKING BUG FIXED (end of session):
  - xrp_drift_v1: was absent from _GRAD entirely → now tracked live (1/30)
  - eth_orderbook_imbalance_v1: was tracked against paper trades → now tracked live (1/30)
  - Test count assertion: 9 → 10 strategies. 904/904 passing.
* btc_daily/eth_daily/sol_daily silence CONFIRMED NOT A BUG: evaluation logs at DEBUG level,
  filtered by main.py basicConfig(level=INFO). Startup messages (INFO) confirm they run.
  Gotcha documented in CLAUDE.md. DO NOT RE-INVESTIGATE this in future sessions.

NEXT SESSION DIRECTIVES (in priority order):
1. RESTART BOT FIRST (log to session43.log) — ALWAYS, no exceptions
2. Run --health, --report, --graduation-status → log to /tmp/polybot_autonomous_monitor.md
3. Monitor all 6 live loops — focus on eth_drift (6 more bets to graduation)
4. Watch eth_orderbook_imbalance live bets accumulate (1/30 — just started live)
5. Watch xrp_drift live bets accumulate (1/30 — just started live, micro-live)
6. sol_drift graduation: 18 more live bets needed (12/30)
7. Probe KXBTCMAXW on WEEKDAY to confirm dormant (last probe was Tuesday confirmed 0 open)
8. IMPROVE LIVE P&L — currently -$14.62 all-time. btc_drift Brier=0.250 is at the edge.
   Do NOT change thresholds without 30+ live trades + PRINCIPLES.md review first.
   Focus: ensure no silent blockers, price guard not overfiring, signals timing correctly.
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

Bot RUNNING — PID 8442, live mode, log: /tmp/polybot_session42.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session42.log
Health: source venv/bin/activate && python3 main.py --health

### SIX Live loops:
- btc_drift_v1 → KXBTC15M | min_drift=0.05, min_edge=0.05 | 43/30 ✅ Brier 0.250 | STAGE 1 ($5 cap, Kelly)
- eth_drift_v1 → KXETH15M | min_drift=0.05, min_edge=0.05 | 24/30 needs 6 more | micro-live
- sol_drift_v1 → KXSOL15M | min_drift=0.15, min_edge=0.05 | 12/30 needs 18 more | micro-live
- xrp_drift_v1 → KXXRP15M | min_drift=0.10, min_edge=0.05 | 1/30 needs 29 more | micro-live
- btc_lag_v1   → KXBTC15M | 0 signals/week (HFTs) | tracked paper (45/30) | live but silent
- eth_orderbook_imbalance_v1 → KXETH15M | 1/30 live | STAGE 1 live (first live bet trade 556 today)

Kill switch: CONSECUTIVE_LOSS_LIMIT=8, daily_loss_cap=DISABLED, bankroll floor $20.
btc_drift: Kelly sizing + $5 hard max. All others: calibration_max_usd=0.01 (1 contract).

### Paper-only (12 loops):
btc_lag (0 signals/week), eth_lag, sol_lag
orderbook_imbalance (btc_imbalance)
btc_daily, eth_daily, sol_daily (KXBTCD/KXETHD/KXSOLD hourly slots — logs at DEBUG level)
weather_forecast (HIGHNY weekdays only)
fomc_rate (~8x/year — WORKING Session 40)
unemployment_rate (~12x/year — WORKING Session 40)
sports_futures_v1 (Polymarket.US bookmaker arb, paper-only, min_books=2)
copy_trader_v1 (Polymarket.US — 0 matches, platform mismatch confirmed)

### Tests: 904/904

### Last commits:
- f6ccec6 — fix: graduation tracking for xrp_drift_v1 and eth_orderbook_imbalance_v1
- e7ac3ae — docs: Session 42 Kalshi market research — barrier events + non-crypto probes
- 3f4611c — feat: btc_lag + eth_imbalance live + remove daily loss cap

### P&L (as of 2026-03-10 22:40 CDT):
- Bankroll: ~$83.57
- All-time live P&L: -$14.62
- Today live P&L: +$0.72 (8 settled, 61% win rate)
- Kill switch: consecutive=2, daily=DISABLED, hard stop CLEAR
- SDATA quota: 74/500 (15%) — resets 2026-04-01

### EXPANSION GATE STATUS:
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (43+) |
| Brier < 0.30 | ✅ MET (0.250) |
| 2-3 weeks live P&L data | ❌ NOT MET |
| No kill switch events in window | ❌ NOT MET |
Gate: CLOSED for NEW strategy types.
KXXRP15M added as micro-live (Session 41) — calibration, not new type.
eth_imbalance live since Session 42 — already built/tested strategy.

### PENDING TODOS:
- eth_drift graduation: 6 more live bets needed (24/30)
- sol_drift graduation: 18 more live bets needed (12/30)
- xrp_drift calibration: 29 more live bets needed (1/30)
- eth_imbalance live calibration: 29 more live bets needed (1/30)
- Probe KXBTCMAXW weekday (Tuesday: 0 open, not seasonal — may be permanently dormant)
- Check fomc paper bets: KXFEDDECISION-26MAR closes March 18

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

## CURRENT BOT ARCHITECTURE (16 loops total — updated Session 42)

main.py asyncio event loop [LIVE MODE — PID 8442]

Kalshi 15-min loops:
  [trading]       btc_lag_v1             LIVE BUT SILENT (0 signals/week — HFTs, tracked paper)
  [eth_trading]   eth_lag_v1             PAPER-ONLY
  [drift]         btc_drift_v1           STAGE 1 LIVE | KXBTC15M | drift=0.05 edge=0.05 | $5 cap
  [eth_drift]     eth_drift_v1           MICRO-LIVE | KXETH15M | drift=0.05 edge=0.05
  [sol_drift]     sol_drift_v1           MICRO-LIVE | KXSOL15M | drift=0.15 edge=0.05
  [xrp_drift]     xrp_drift_v1           MICRO-LIVE | KXXRP15M | drift=0.10 edge=0.05
  [btc_imbalance] orderbook_imb_v1       PAPER-ONLY
  [eth_imbalance] eth_orderbook_imb_v1   STAGE 1 LIVE | KXETH15M | 1/30 live
  [weather]       weather_forecast_v1    PAPER-ONLY (weekdays only)
  [fomc]          fomc_rate_v1           PAPER-ONLY (~8x/year — WORKING Session 40)
  [unemployment]  unemployment_rate_v1   PAPER-ONLY (~12x/year — WORKING Session 40)
  [sol_lag]       sol_lag_v1             PAPER-ONLY

Kalshi daily loops (KXBTCD/KXETHD/KXSOLD — 24 hourly price-level slots/day):
  [btc_daily]     btc_daily_v1           PAPER-ONLY (logs at DEBUG — silent in INFO log = EXPECTED)
  [eth_daily]     eth_daily_v1           PAPER-ONLY (same)
  [sol_daily]     sol_daily_v1           PAPER-ONLY (same)

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
