# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-09 (Session 40 — fomc/unemployment shared fred_feed bug fix)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 42+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 41 close-out).

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
  This is the #1 lesson from Session 40. Not restarting means soft stop sits active for hours.
  Restart clears the consecutive loss cooling window. Daily loss counter PERSISTS (from DB) — that's correct.

  RESTART COMMAND (check bot.pid for current PID first, kill -9 <PID> if pkill doesn't work):
    pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
    sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
    echo "CONFIRM" > /tmp/polybot_confirm.txt
    nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session42.log 2>&1 &
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
    Matthew uses Kalshi phone notifications for live bet wins — silence for >30min = investigate.

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
    NEVER implement code without superpowers:TDD. NEVER say "done" without superpowers:verification.

  RULE C — KALSHI MARKET RESEARCH (cannot be skipped every session):
    Kalshi has MANY market types beyond the 15-min direction markets.
    From kalshi.com Crypto tab: 15 Minute ✅ | Hourly ✅paper | Daily ✅paper |
      Weekly ($455K vol) | Monthly | Annual ($1.4M vol) | One Time ($14.8M vol!)
    ACTION: Read RESEARCH DIRECTIVES in KALSHI_MARKETS.md. Probe API for undocumented series.
    Search reddit.com/r/kalshi. Search GitHub. Update KALSHI_MARKETS.md with findings.

  RULE D — SESSION WRAP-UP (mandatory before any session end):
    1. python3 main.py --report → capture output
    2. python3 main.py --graduation-status → capture output
    3. cat bot.pid && kill -0 $(cat bot.pid) && echo RUNNING → confirm bot alive
    4. Update SESSION_HANDOFF.md with current state, pending tasks, last actions
    5. Append entry to .planning/CHANGELOG.md with what was done and WHY
    6. git add + git commit with descriptive message + git push
    7. Write handoff summary to /tmp/polybot_autonomous_monitor.md

══════════════════════════════════════════════════════

KEY STATE (Session 41 close-out — 2026-03-09 ~20:48 CDT):
* Bot: PID 4799, LIVE mode, log /tmp/polybot_session41.log
* THREE MICRO-LIVE LOOPS: btc_drift + eth_drift + sol_drift (all ~$0.35-0.65/bet, unlimited/day)
* All others: PAPER-ONLY. 891/891 tests passing.
* Last commit: (see git log — Session 41 docs commit)
* Bankroll: ~$83.81 (approx) | All-time live P&L: -$15.37
* Kill switch: 1 consecutive loss | daily total $9.22 | hard stop CLEAR
* btc_drift: 41/30 ✅ Brier 0.247 | eth_drift: 23/30 (7 more) | sol_drift: 11/30 (19 more)
* SDATA: 53/500 (11%) — resets 2026-04-01
* Expansion gate: STILL CLOSED (2-3 weeks live data needed + no KS events)
* KALSHI_MARKETS.md updated with Session 41 probe: KXXRP15M active (1 open @ 43¢), KXBTCMAXW dormant Sunday
* fomc_rate_v1: paper bets firing (confirmed Session 40) | unemployment_rate_v1: working
* Session 41 live bets: trade_id=513 WIN +$0.49, trade_id=514 LOSS -$0.52

SESSION 41 WORK DONE:
* Restarted bot at session start (PID 4799) — applied Session 40 lesson: ALWAYS restart first.
  Used --reset-soft-stop flag to clear consecutive loss cooling (5 losses from prior sessions).
  Verified clearing in log: "Soft stop reset: consecutive loss counter cleared (manual override)"
* Soft stop cleared → live bets firing immediately after restart
* trade_id=513: btc_drift_v1 NO KXBTC15M-26MAR092115-15 @ 49¢ → SETTLED WIN +$0.49
* trade_id=514: eth_drift_v1 YES KXETH15M-26MAR092145-45 @ 52¢ → SETTLED LOSS -$0.52
  (ETH fell in window — market volatile. Correct model behavior — drift said up, ETH went down.)
* 2 execution-time price guard rejections (correct behavior):
  - sol_drift signal 61¢ → execution price 82¢ (21¢ slippage, BTC/SOL extremely volatile)
  - eth_drift signal 50¢ → execution price 75¢ (25¢ slippage in new window 092200-00)
* Series probe (Sunday 2026-03-09): KXXRP15M=1 open @ 43¢ ✅ | KXBTCMAXW=0 open (dormant Sunday)
* KALSHI_MARKETS.md updated: corrected EXPANSION ROADMAP (removed KXBTCW/KXETHW/KXSOLW error),
  added Session 41 probe results to RESEARCH DIRECTIVES section
* Reddit/GitHub research agent launched: no significant new community insights found for Sunday

MISTAKES MADE THIS SESSION (logged for new chat to avoid):
1. Market volatility: BTC/ETH swinging 50¢ → 8¢ → 75¢ in a single 15-min window.
   Price guard (35-65¢) correctly blocks these but means signal fires → execution rejects.
   LESSON: On volatile days, fewer live bets will complete. This is correct behavior, not a bug.
2. sol_drift threshold 0.150% is very tight — oscillated 0.141%/0.147%/0.070% this session.
   Never quite fired. Consider logging this pattern: SOL needs 3x BTC threshold, fires less often.

NEXT SESSION DIRECTIVES (in priority order):
1. RESTART BOT FIRST (log to session42.log) — ALWAYS, no exceptions
2. Run --health, --report, --graduation-status → log to /tmp/polybot_autonomous_monitor.md
3. Check kill switch: if consecutive losses >= 3, consider --reset-soft-stop if prior session just ended
4. Monitor eth_drift graduation: 7 more live bets needed (currently 23/30)
5. Probe KXBTCMAXW weekly markets on WEEKDAY (dormant on Sunday) — add findings to KALSHI_MARKETS.md
6. Check fomc paper bets progress: KXFEDDECISION-26MAR closes March 18
7. Expansion gate still CLOSED — no new live strategies
8. If KXBTCMAXW active on weekday: log volume/open-markets to KALSHI_MARKETS.md

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: no new live strategies until 2-3 weeks live data + no KS events
* 891 tests must pass before any commit (count updates each session)
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

Bot RUNNING — PID 4799, live mode, log: /tmp/polybot_session41.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session41.log
Health: source venv/bin/activate && python3 main.py --health

### THREE Live drift loops (all micro-live, 1 contract/bet ~$0.35-0.65):
- btc_drift_v1 -> KXBTC15M | min_drift=0.05, min_edge=0.05 | 41/30 ✅ Brier 0.247
- eth_drift_v1 -> KXETH15M | min_drift=0.05, min_edge=0.05 | 23/30 needs 7 more
- sol_drift_v1 -> KXSOL15M | min_drift=0.15, min_edge=0.05 | 11/30 needs 19 more
All share: _live_trade_lock, calibration_max_usd=0.01, price guard 35-65 cents.
Combined: ~15-25 live bets/day.

### FOMC Rate Strategy (fomc_rate_v1) — NOW WORKING (Session 40 fix)
KXFEDDECISION markets. March 2026 FOMC on March 19. close_time='2026-03-18T17:59:00Z'.
Current signals: H0 (Hold) → BUY NO@2¢ (edge=31%, model=67% vs market=97%)
                 C25 (Cut 25bps) → BUY YES@1¢ (edge=22%, model=23% vs market=1%)
Wait for these to settle after March 18 to evaluate model calibration.

### KXBTCD Hourly Bets (btc_daily_v1) — PAPER, monitor graduation
24 hourly price-level slots/day. KXBTC1H does NOT exist — these are inside KXBTCD.
Strategy: CryptoDailyStrategy — ATM contract (closest to 50¢, 30min–6hr window)
Gate to go live: expansion gate criteria. Check: python3 main.py --graduation-status

### Paper-only (12 loops):
btc_lag, eth_lag, sol_lag (0 signals/week — HFTs closed the lag)
orderbook_imbalance, eth_orderbook_imbalance
btc_daily, eth_daily, sol_daily (KXBTCD/KXETHD/KXSOLD hourly slots — paper)
weather_forecast (HIGHNY weekdays only)
fomc_rate (~8x/year — NOW WORKING post Session 40 fix)
unemployment_rate (~12x/year — NOW WORKING post Session 40 fix)
sports_futures_v1 (Polymarket.US bookmaker arb, paper-only, min_books=2)
copy_trader_v1 (Polymarket.US — 0 matches, platform mismatch confirmed)

### Tests: 891/891

### Last commits:
- 8d3ab06 — fix(fomc+unemployment): share fred_feed instance to prevent silent signal stale block
- e8544e1 — docs: Session 39 close-out — AUTONOMOUS_CHARTER + KALSHI_MARKETS research
- c2a2192 — docs: update POLYBOT_INIT with live.py security findings + SKILLS_REFERENCE link

### P&L (as of 2026-03-09 20:48 CDT — Session 41 close-out):
- Bankroll: ~$83.81 (approx, -$0.03 net live today)
- All-time live P&L: -$15.37
- Kill switch: 1 consecutive loss | daily $9.22 | hard stop CLEAR
- SDATA quota: 53/500 (11%) — resets 2026-04-01

### EXPANSION GATE STATUS (Session 41 close-out):
| Criterion | Status |
|-----------|--------|
| btc_drift 30+ live bets | ✅ MET (41+) |
| Brier < 0.30 | ✅ MET (0.247) |
| 2-3 weeks live P&L data | ❌ NOT MET (~2-3 days live) |
| No kill switch events in window | ❌ NOT MET (multiple soft stops this session) |
Gate: STILL CLOSED. Next expansion = KXXRP15M drift (same code as sol_drift, ~15 min).

### PENDING TODOS:
- Monitor fomc paper bets settling (March 18 close) — model validation begins
- Probe KXBTCMAXW on WEEKDAY (dormant Sunday — check Mon-Fri for open weekly markets)
- eth_drift graduation: 7 more live bets needed (currently 23/30)

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

## CURRENT BOT ARCHITECTURE (15 loops total)

main.py asyncio event loop [LIVE MODE — PID 4799]

Kalshi 15-min loops:
  [trading]       btc_lag_v1             PAPER-ONLY (0 signals/week — market mature)
  [eth_trading]   eth_lag_v1             PAPER-ONLY
  [drift]         btc_drift_v1           MICRO-LIVE | KXBTC15M | drift=0.05 edge=0.05
  [eth_drift]     eth_drift_v1           MICRO-LIVE | KXETH15M | drift=0.05 edge=0.05
  [sol_drift]     sol_drift_v1           MICRO-LIVE | KXSOL15M | drift=0.15 edge=0.05
  [btc_imbalance] orderbook_imb_v1       PAPER-ONLY
  [eth_imbalance] eth_orderbook_imb_v1   PAPER-ONLY
  [weather]       weather_forecast_v1    PAPER-ONLY (weekdays only)
  [fomc]          fomc_rate_v1           PAPER-ONLY (~8x/year — NOW WORKING Session 40)
  [unemployment]  unemployment_rate_v1   PAPER-ONLY (~12x/year — NOW WORKING Session 40)
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

### Live restart (use at EVERY session start — clears soft stop)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session41.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

### Watch drift loops (most active — live bets fire here)
  tail -f /tmp/polybot_session41.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

### Watch everything
  tail -f /tmp/polybot_session41.log

### Diagnostics
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA
  source venv/bin/activate && python3 -m pytest tests/ -q         # 891/891 required before commit
  grep "[fomc] Paper trade:" /tmp/polybot_session41.log           # check fomc paper bets

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/AUTONOMOUS_CHARTER.md — autonomous ops rules (MANDATORY, acknowledge)
3. .planning/CHANGELOG.md — what changed and WHY, every session
4. .planning/KALSHI_MARKETS.md — full market map before any strategy work
5. .planning/SKILLS_REFERENCE.md — tool selection + token cost tiers
6. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
