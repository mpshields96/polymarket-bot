# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-10 (Session 43 — direction_filter + Kalshi research)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 44+)

```
You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 44).

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
    nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session44.log 2>&1 &
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
    Session 43 COMPLETED: KXBTCMAXW dormant, KXNASDAQ100Y extreme prices, KXCPI low vol.
    GDP (KXGDP) confirmed active. KXPCE + KXJOLTS dormant.

  RULE D — SESSION WRAP-UP (mandatory before any session end):
    1. python3 main.py --report → capture output
    2. python3 main.py --graduation-status → capture output
    3. cat bot.pid && kill -0 $(cat bot.pid) && echo RUNNING → confirm bot alive
    4. Update SESSION_HANDOFF.md with current state, pending tasks, last actions
    5. Append entry to .planning/CHANGELOG.md with what was done and WHY
    6. git add + git commit with descriptive message + git push
    7. Write handoff summary to /tmp/polybot_autonomous_monitor.md

══════════════════════════════════════════════════════

KEY STATE (Session 43 AUTONOMOUS end — 2026-03-10 ~01:15 CDT):
* Bot: PID 11839, LIVE mode, log /tmp/polybot_session43.log
* All-time live P&L: -$18.15 | Today live: -$2.81 (18 settled) | Bankroll: ~$80+
* SIX LIVE LOOPS (daily loss cap REMOVED Session 42):
  - btc_drift_v1: STAGE 1 ($5 max/bet, Kelly governs) — 45/30 ✅ Brier 0.250 streak=0
    ⚠️ direction_filter="no" ACTIVE — blocks YES signals. Session 43 autonomous: trade 591 NO won +$6.30!
    To validate: 30+ NO-only bets → if win rate stays >55% → filter becomes permanent
  - eth_drift_v1: MICRO-LIVE — 27/30 (**3 MORE BETS NEEDED FOR GRADUATION!**) | Brier 0.251
  - sol_drift_v1: MICRO-LIVE — 13/30 (17 more needed) | Brier 0.151 🔥
  - xrp_drift_v1: MICRO-LIVE — 1/30 (29 more needed) | streak=1
  - eth_orderbook_imbalance_v1: STAGE 1 — 5/30 (25 more needed) | Brier 0.264 | streak=3 ⚠️
  - btc_lag_v1: STAGE 1 — 45/30 ✅ Brier 0.191 | LIVE but 0 signals/week (HFTs)
* DAILY SOFT STOP: CONFIRMED DISPLAY-ONLY — lines 187-189 in kill_switch.py are COMMENTED OUT
  --health shows "Daily loss soft stop active" — this is tracking only, NOT blocking bets
* Kill switch: daily_loss_cap=DISABLED, consecutive_loss_limit=8
  Active protection: bankroll floor $20 + 8 consecutive → 2hr pause + $5/bet hard cap
* 910/910 tests passing
* Last commit: e085536 — feat: block btc_drift YES signals via direction_filter (AUTONOMOUS updated CHANGELOG)
* All-time live P&L: -$18.15 | Today: -$2.81 (18 settled) | Bankroll: ~$80+
* SDATA quota: 80/500 (16%) — resets 2026-04-01

SESSION 43 WORK DONE (code) + AUTONOMOUS NIGHT MONITORING:
* btc_drift direction_filter="no" DEPLOYED (Session 43 code):
  - Statistical basis: YES side 6/20 wins (30%), -$30.07 | NO side 14/23 wins (61%), +$11.49
  - p-value ≈ 3.7% (significant). Mechanical: HFTs front-run YES drift, NO side preserves edge.
  - 6 new tests in TestDirectionFilter — COMMITTED e085536, pushed
* AUTONOMOUS MONITORING (2.5hr session): 11 live bets placed, 5.4/hr
  - direction_filter NO bet validated: trade 591 btc_drift NO@35¢ +$6.30 WIN
  - Key finding: daily soft stop CONFIRMED DISPLAY-ONLY (kill_switch.py lines 187-189 COMMENTED)
  - Key finding: "Trade executed" log appears for BOTH paper AND live — must grep "LIVE BET"
  - No kill switch events, no soft stops, no bot errors during autonomous period
  - eth_imbalance streak=3 consecutive losses — watch (limit is 8)

NEXT SESSION DIRECTIVES (in priority order):
1. RESTART BOT FIRST (log to session44.log) — ALWAYS, no exceptions
2. Run --health, --report, --graduation-status → log to /tmp/polybot_autonomous_monitor.md
3. ⚠️ MONITOR direction_filter="no" bets: eth_imbalance streak=3 (check global consecutive)
   After 10+ NO-only btc_drift bets settled: SQL win rate check on new filter regime
   If NO win rate < 50% over 15+ bets: revisit filter
4. **eth_drift graduation: 27/30 — only 3 more live bets needed!** Watch this actively
5. Watch eth_orderbook_imbalance: 5/30, streak=3 consecutive losses
6. sol_drift graduation: 13/30 (17 more needed) | Brier 0.151 🔥 exceptional calibration
7. Check fomc paper bets: KXFEDDECISION-26MAR closes March 18 (0 settled of 19 placed)

STANDING DIRECTIVES (never need repeating):
* Fully autonomous always — do work first, summarize after. Never ask for confirmation.
* EXPANSION GATE: closed for new strategy TYPES. Expansion order:
  KXXRP15M micro-live (done ✅) → KXBTCMAX100/150 (post-research, post-gate) → annual markets
* 910 tests must pass before any commit (count updates each session)
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

Bot RUNNING — PID 11839, live mode, log: /tmp/polybot_session43.log
Check:  cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
Watch:  tail -f /tmp/polybot_session43.log
Health: source venv/bin/activate && python3 main.py --health

### SIX Live loops:
- btc_drift_v1 → KXBTC15M | min_drift=0.05, min_edge=0.05 | 43/30 ✅ Brier 0.250 | STAGE 1 ($5 cap, Kelly)
  ⚠️ direction_filter="no" ACTIVE — only fires NO signals (Session 43 change)
- eth_drift_v1 → KXETH15M | min_drift=0.05, min_edge=0.05 | 24/30 needs 6 more | micro-live
- sol_drift_v1 → KXSOL15M | min_drift=0.15, min_edge=0.05 | 12/30 needs 18 more | micro-live
- xrp_drift_v1 → KXXRP15M | min_drift=0.10, min_edge=0.05 | 1/30 needs 29 more | micro-live
- btc_lag_v1   → KXBTC15M | 0 signals/week (HFTs) | tracked paper (45/30) | live but silent
- eth_orderbook_imbalance_v1 → KXETH15M | 1/30 live | STAGE 1 live (first live bet trade 556)

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

### Tests: 910/910

### Last commits:
- e085536 — feat: block btc_drift YES signals via direction_filter — statistical basis
- f6ccec6 — fix: graduation tracking for xrp_drift_v1 and eth_orderbook_imbalance_v1
- e7ac3ae — docs: Session 42 Kalshi market research — barrier events + non-crypto probes

### P&L (as of 2026-03-10 23:10 CDT):
- Bankroll: ~$83.57
- All-time live P&L: -$14.62
- Today live P&L: +$0.72 (8 settled, 61% win rate)
- Kill switch: consecutive=2, daily=DISABLED, hard stop CLEAR
- SDATA quota: 74/500 (15%) — resets 2026-04-01

### direction_filter tracking (NEW — Session 43):
- YES bets before filter: 20 live settled, 6 wins (30%), -$30.07
- NO bets before filter: 23 live settled, 14 wins (61%), +$11.49
- First NO-only bet: trade 567, btc_drift NO@37¢ $4.07 (KXBTC15M-26MAR100015-15)
- Monitor: after 10+ NO-only settled bets → run SQL to validate ongoing NO win rate

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
- ⚠️ Monitor NO-only btc_drift bets: 10+ settled → SQL win rate check
- eth_drift graduation: 6 more live bets needed (24/30)
- sol_drift graduation: 18 more live bets needed (12/30)
- xrp_drift calibration: 29 more live bets needed (1/30)
- eth_imbalance live calibration: 29 more live bets needed (1/30)
- Check fomc paper bets: KXFEDDECISION-26MAR closes March 18

### Kalshi market research status (Session 43 complete):
- KXBTCMAXW: DORMANT (0 markets any status, confirmed weekday)
- KXNASDAQ100Y: Active (773k vol) but extreme prices — unsuitable for signal strategy
- KXCPI: Active (6.7k vol, too low) — 14 near-mid markets but insufficient volume
- KXGDP: Active (8 markets, Q1 2026)
- KXPCE + KXJOLTS: Dormant (0 open markets)
- All logged to todos.md — no build under expansion gate

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

## CURRENT BOT ARCHITECTURE (16 loops total — updated Session 43)

main.py asyncio event loop [LIVE MODE — PID 11839]

Kalshi 15-min loops:
  [trading]       btc_lag_v1             LIVE BUT SILENT (0 signals/week — HFTs, tracked paper)
  [eth_trading]   eth_lag_v1             PAPER-ONLY
  [drift]         btc_drift_v1           STAGE 1 LIVE | KXBTC15M | drift=0.05 edge=0.05 | $5 cap
                                         ⚠️ direction_filter="no" — NO signals only (Session 43)
  [eth_drift]     eth_drift_v1           MICRO-LIVE | KXETH15M | drift=0.05 edge=0.05
  [sol_drift]     sol_drift_v1           MICRO-LIVE | KXSOL15M | drift=0.15 edge=0.05
  [xrp_drift]     xrp_drift_v1          MICRO-LIVE | KXXRP15M | drift=0.10 edge=0.05
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
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session44.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

### Watch drift loops (most active — live bets fire here)
  tail -f /tmp/polybot_session43.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

### Watch everything
  tail -f /tmp/polybot_session43.log

### Diagnostics
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA
  source venv/bin/activate && python3 -m pytest tests/ -q         # 910/910 required before commit
  grep "direction_filter\|btc_drift" /tmp/polybot_session43.log   # check NO-filter working

### SQL: check direction_filter effectiveness (run after 10+ NO-only bets)
  sqlite3 data/polybot.db "SELECT side, COUNT(*) bets, SUM(CASE WHEN result=side THEN 1 ELSE 0 END) wins, ROUND(AVG(CASE WHEN result=side THEN 1.0 ELSE 0.0 END)*100,1) win_pct, ROUND(SUM(pnl_cents)/100.0,2) pnl FROM trades WHERE is_paper=0 AND strategy='btc_drift_v1' AND result IS NOT NULL GROUP BY side ORDER BY side;"

# ═══════════════════════════════════════════════════════════════

## MANDATORY READING ORDER (every new session)
1. SESSION_HANDOFF.md (this file) — already done
2. .planning/AUTONOMOUS_CHARTER.md — autonomous ops rules (MANDATORY, acknowledge)
3. .planning/CHANGELOG.md — what changed and WHY, every session
4. .planning/KALSHI_MARKETS.md — full market map before any strategy work
5. .planning/SKILLS_REFERENCE.md — tool selection + token cost tiers
6. .planning/PRINCIPLES.md — before ANY strategy/risk/threshold change
