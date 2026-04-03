# POLYBOT — BUILD INSTRUCTIONS + LIVE STATUS
# For: Claude Code Desktop App | Owner: Matthew
# Read this fully before doing anything.

═══════════════════════════════════════════════════════════════════════
## ⚠️ MANDATORY RULES — NEW SESSIONS MUST FOLLOW ALL OF THESE
═══════════════════════════════════════════════════════════════════════

### RULE 1: READ THESE FILES FIRST, IN ORDER, EVERY SESSION
  1. SESSION_HANDOFF.md          — exact bot state, PID, log path, pending tasks, last commit
  2. .planning/CHANGELOG.md      — what changed every session and WHY (permanent record)
  3. .planning/KALSHI_MARKETS.md — FULL market map — ALL categories, what's built, what's not
  4. .planning/SKILLS_REFERENCE.md — ALL available GSD/sc:/superpowers commands + token costs
  5. .planning/PRINCIPLES.md     — before ANY strategy/risk parameter change
  6. Run self-learning reflection:
       ./venv/bin/python3 scripts/strategy_analyzer.py --reflect
     (generates data/session_reflection.md — automated session-start document with:
      funding status, sniper health, direction filter summary, graduation alerts,
      sniper quality benchmark, and top 3 actions for the session.
      Replaces manual Claude summarization with DB-driven pattern output.)
     Then read: cat data/session_reflection.md

### RULE 2: INVESTIGATE KALSHI MARKET TYPES EVERY SESSION
  KALSHI HAS FAR MORE MARKET TYPES THAN THE 15-MIN DIRECTION MARKETS WE TRADE.
  From Matthew's screenshot (Session 38): Crypto section alone has:
    15 Minute (built) | Hourly (paper) | Daily (built) |
    Weekly ($455K vol) | Monthly | Annual ($1.4M vol) | One Time ($14.8M vol!) | DOGE
  Full Kalshi nav: Politics | Sports | Culture | Climate | Economics |
                   Mentions | Companies | Financials | Tech & Science
  → Read .planning/KALSHI_MARKETS.md RESEARCH DIRECTIVES section
  → When bandwidth exists: probe API for undocumented tickers, search Reddit/GitHub
  → Document findings in .planning/KALSHI_MARKETS.md before building anything new
  → NEVER ignore these categories because they were "not built before"

### RULE 3: USE GSD + SUPERPOWERS SKILLS — THEY ARE MANDATORY TOOLS
  READ .planning/SKILLS_REFERENCE.md before choosing any implementation approach.
  DEFAULT for 90% of work: gsd:quick + superpowers:TDD + superpowers:verification-before-completion
  THESE ARE FREE (or low cost) — USE THEM ON EVERY TASK:
    superpowers:TDD                         — before writing ANY implementation code
    superpowers:verification-before-completion — before claiming work is done
    superpowers:systematic-debugging        — before proposing ANY fix for a bug
    gsd:add-todo                           — when any idea or issue surfaces
    gsd:quick                              — wraps any focused task with atomic commit + state tracking
  DO NOT improvise without these tools. They exist to prevent bugs that have cost real money.

### RULE 4: AUTONOMOUS OPERATION — NEVER WAIT FOR MATTHEW
  Fully autonomous always. Do work first, summarize after.
  If Matthew is away: append findings to /tmp/polybot_autonomous_monitor.md
  NEVER pause mid-task to ask for confirmation on: tests, file reads/edits, commits, diagnostics.

═══════════════════════════════════════════════════
## CURRENT STATUS — (always check SESSION_HANDOFF.md for live state)
═══════════════════════════════════════════════════

Live state is maintained in SESSION_HANDOFF.md — bot PID, P&L, bankroll, strategy status,
last commit, and pending tasks are all there. Do NOT trust any status data in this file —
it will be stale. Read SESSION_HANDOFF.md first, every session, no exceptions.

RESPONSE FORMAT RULES (BOTH MANDATORY — Matthew terminates chat for violations):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose ($X.XX) — triggers LaTeX math mode → garbled text.

═══════════════════════════════════════════════════════════════════════
## LIVE RESTART COMMAND (always use this exact form — increment session number each restart)
═══════════════════════════════════════════════════════════════════════

  ⚠️ BEFORE RESTARTING: check if DB has 11+ consecutive live losses.
  If yes OR if the --health output shows "consecutive cooling X min remaining":
    ADD --reset-soft-stop to the nohup line (see SAFE RESTART below).
    Without --reset-soft-stop, restore_consecutive_losses() reads 11 from DB → 2hr cooling fires.

  SAFE RESTART (use this — includes --reset-soft-stop to prevent false cooling on restore):
    pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
    sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
    echo "CONFIRM" > /tmp/polybot_confirm.txt
    SESSION_N=$(cat SESSION_HANDOFF.md | grep -o 'polybot_session[0-9]*' | tail -1 | grep -o '[0-9]*')
    nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session${SESSION_N}.log 2>&1 &
    sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

  STANDARD RESTART (only when you're sure DB consecutive < 8):
    pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
    sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
    echo "CONFIRM" > /tmp/polybot_confirm.txt
    SESSION_N=$(cat SESSION_HANDOFF.md | grep -o 'polybot_session[0-9]*' | tail -1 | grep -o '[0-9]*')
    nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session${SESSION_N}.log 2>&1 &
    sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

  ⚠️ macOS: pkill may miss processes using different Python binary path.
     If old PID still shows: kill -9 <OLD_PID>, then restart.
     Always verify exactly 1 process: ps aux | grep "[m]ain.py" | wc -l should show 1.

## DIAGNOSTICS (safe while bot is live — bypass PID lock)
  source venv/bin/activate && python3 main.py --report            # today P&L, paper/live split
  source venv/bin/activate && python3 main.py --graduation-status # Brier + live bet count per strategy
  source venv/bin/activate && python3 main.py --health            # kill switch + open trades + SDATA quota

═══════════════════════════════════════════════════════════════════════
## AUTONOMOUS OPERATIONS — HARDCODED RESPONSIBILITIES
## (Applies whenever Matthew says "work autonomously", "I'll be back", or goes offline)
## THIS IS THE STANDARD LOOP. DO NOT DEVIATE. DO NOT WAIT FOR INSTRUCTIONS.
═══════════════════════════════════════════════════════════════════════

### STARTUP CHECKLIST (every autonomous session, no exceptions)
  1. Read SESSION_HANDOFF.md — get exact bot state, PID, pending tasks, last commit
  2. CHECK BOT STATUS FIRST:
       ps aux | grep "[m]ain.py" | grep -v grep
       cat bot.pid 2>/dev/null && kill -0 $(cat bot.pid 2>/dev/null) && echo "BOT RUNNING" || echo "BOT STOPPED"
     If RUNNING: check consecutive state BEFORE deciding to restart:
       grep "consecutive" /tmp/polybot_session*.log | tail -5
       source venv/bin/activate && python3 main.py --health
     If STOPPED: restart using SAFE RESTART command (always use --reset-soft-stop).
  3. RESTART DECISION (critical — see Session 46 warning):
     ⚠️ Always check DB consecutive loss count before restarting.
     If DB shows 8+ consecutive losses AND you restart without --reset-soft-stop → 2hr cooling fires.
     Rule of thumb: when in doubt, always add --reset-soft-stop to restart command.
     SAFE RESTART includes --reset-soft-stop by default (see LIVE RESTART COMMAND section).
     DO NOT restart if bot is running and in-memory consecutive < 8. Just run diagnostics.
  4. Run python3 main.py --health → log result to /tmp/polybot_autonomous_monitor.md
     "Daily loss soft stop active" = DISPLAY ONLY (lines commented out). Does NOT block bets.
     "Consecutive loss cooling X min remaining" = could be real OR a DB read artifact.
       Confirm with: grep "consecutive" /tmp/polybot_session*.log | tail -5
       If in-memory log shows consecutive=3 but --health shows cooling: DO NOT restart. Already fine.
     "HARD STOP" = do NOT restart — log it, wait for Matthew.
  5. Run python3 main.py --graduation-status → log
  6. Run python3 main.py --report → log current P&L

  ⚠️ SESSION 40 LESSON: Not restarting at session start left a soft stop active for 2 hours.
  ⚠️ SESSION 46 LESSON: DB shows 11 consecutive losses but in-memory=3 (no cooling). Restart without
     --reset-soft-stop would have triggered 2hr cooling unnecessarily. ALWAYS check in-memory state.
     The --health "consecutive cooling" warning is based on DB query, not live in-memory state.
     Authoritative source: grep the running log for "consecutive:" entries.

### MONITORING LOG — MANDATORY
  File: /tmp/polybot_autonomous_monitor.md
  Rule: APPEND ONLY — never overwrite. Every action and finding goes here.
  Format: ## [TIMESTAMP CDT] — [status] — [action taken or NONE]
  Frequency: log every cycle (every 10-15 min minimum while Matthew is away)

### RESPONSIBILITY 1 — BOT HEALTH (highest priority, every cycle)
  Every 10-15 minutes:
    a. Check bot alive (kill -0 check on PID from bot.pid)
    b. tail -20 /tmp/polybot_session*.log | grep -i "error\|exception\|kill switch\|CRITICAL"
    c. If no live bets in 24hr: run --health IMMEDIATELY — diagnose kill switch + loop errors
    d. Log cycle result to /tmp/polybot_autonomous_monitor.md
  If bot STOPPED:
    - Restart immediately using LIVE RESTART COMMAND
    - Log restart with timestamp + reason
  If kill switch fired (soft stop / consecutive loss cooling):
    - RESTART USING SAFE RESTART (with --reset-soft-stop). This clears the consecutive counter.
      The daily loss limit counter PERSISTS through restart (seeded from DB) — that stays.
      Consecutive loss cooling (2hr window) is cleared by --reset-soft-stop on restart.
    - Check DB consecutive count first: will restart trigger re-cooling without --reset-soft-stop?
      If yes, ALWAYS add --reset-soft-stop to avoid wasting 2hr of live bet time.
    - Do NOT manually --reset-killswitch. Use SAFE RESTART instead.
    - Log the restart with timestamp + reason to /tmp/polybot_autonomous_monitor.md.
  If kill switch hard stop (bankroll floor or daily loss > 20%):
    - Do NOT restart. Log it. This is a real safety stop. Wait for Matthew.

### RESPONSIBILITY 2 — LIVE AND PAPER BETS (verify both are firing every cycle)
  Watch live bets: tail -f /tmp/polybot_session*.log | grep --line-buffered "LIVE BET\|Trade executed"
  CRITICAL: "Trade executed" = BOTH paper and live. Must grep "LIVE BET" for live-only count.
  If any live loop silent for >2 hours: run --health, check kill switch, look for loop errors
  Watch paper bets: tail -f /tmp/polybot_session*.log | grep --line-buffered "paper\|PAPER"
  If paper loops also silent: likely a broader loop error — check logs, run --health
  Data collection always continues even during soft stops (check_paper_order_allowed design).

### RESPONSIBILITY 3 — DEBUGGING (use systematic approach, every cycle)
  After each monitoring cycle, scan for:
    - ValueError, TypeError, AttributeError, Exception traces in log
    - "silent" loops that fire no signals for >6 hours without explanation
    - Kill switch events that don't match DB data (KILL_SWITCH_EVENT.log pollution)
    - API connectivity failures (Kalshi 401/404/rate-limit, Binance.US reconnects)
  IF BUG FOUND:
    1. Use /superpowers:systematic-debugging to diagnose root cause
    2. Use /gsd:quick + /superpowers:TDD to fix with test-first approach
    3. Run all tests before committing
    4. Check sibling code for same bug pattern
    5. Log fix to /tmp/polybot_autonomous_monitor.md

### RESPONSIBILITY 4 — KALSHI MARKET RESEARCH (do when not debugging or monitoring)
  READ .planning/KALSHI_MARKETS.md RESEARCH DIRECTIVES section before starting.
  Probe Kalshi API directly for candidate series tickers (never assume — confirm via API).
  Search reddit.com/r/kalshi for strategy discussions on each market type.
  Search GitHub for kalshi python bot + strategy type.
  Update .planning/KALSHI_MARKETS.md with confirmed findings.
  DOCUMENT FINDINGS before building anything. Do not build strategies for unproven markets.

### RESPONSIBILITY 5 — DATA COLLECTION (ongoing, no special action needed)
  All paper loops collect data continuously — do not interrupt them.
  Check graduation progress with --graduation-status.
  If any strategy reaches graduation criteria: Log it. Do NOT promote without Matthew confirming.

### RESPONSIBILITY 6 — SESSION WRAP-UP (before context limit or session end)
  ALWAYS do this before stopping, even if mid-task:
  1. python3 main.py --report → capture output
  2. python3 main.py --graduation-status → capture output
  3. cat bot.pid && kill -0 $(cat bot.pid) && echo RUNNING → confirm bot alive
  4. Update SESSION_HANDOFF.md with current state, pending tasks, last actions
  5. Append entry to .planning/CHANGELOG.md with what was done and WHY
  6. git add + git commit with descriptive message
  7. Write handoff summary to /tmp/polybot_autonomous_monitor.md

### TOOLS FOR AUTONOMOUS WORK
  See .planning/SKILLS_REFERENCE.md for full reference. Every task:
  - gsd:quick: ~1-2% — ANY focused fix or feature — DEFAULT
  - superpowers:TDD: Free — before writing ANY implementation code
  - superpowers:verification-before-completion: Free — before claiming done
  - superpowers:systematic-debugging: Free — before proposing ANY bug fix
  - gsd:add-todo: Free — any idea or issue
  SESSION START (once only): /gsd:health then /gsd:progress

═══════════════════════════════════════════════════
## EXPANSION ROADMAP (gate: confirmed live data + no kill switch events)
═══════════════════════════════════════════════════
  Priority order once expansion gate opens:
  1. KXBTCD hourly live — btc_daily_v1 already paper. Promote once paper graduation met (30 bets).
     Price-level bets (is BTC above/below $X at time T), 24 slots/day. Lower volume, wider spread.
     Run --graduation-status to check paper bet count and Brier for btc_daily_v1.
  2. KXNBAGAME/KXNHLGAME — Kalshi game winners (skeleton built, disabled). Gate: sports_futures shows edge.
  3. KXNBA3D, KXNBAPTS, etc — player props (new Session 36 discovery). Lower priority.
  NOTE: KXXRP15M removed — XRP permanently banned (IL-33, Matthew explicit directive, S125).
  DO NOT BUILD any expansion item until gate criteria pass. Log ideas to .planning/todos.md.

### TOOLS CHEAT SHEET (community-sourced)
  Full reference: .planning/SKILLS_REFERENCE.md (read it — covers ALL skills + triggers)

  ALWAYS FREE — use on EVERY relevant task, no exceptions:
    superpowers:TDD                                     Before writing ANY implementation code
    superpowers:verification-before-completion          Before claiming ANY work done
    superpowers:systematic-debugging                    Before proposing ANY bug fix
    gsd:add-todo                                        When any idea or issue surfaces
    gsd:health + gsd:progress                           Session START only (once each)
    wrap-up                                             Session END (never skip)

  LOW COST — default workhorse:
    gsd:quick (~1-2%)                  Any fix or feature — DEFAULT for 90% of work
    gsd:quick --full (~3%)             Higher-risk changes (live.py, kill_switch.py, main.py)
    sc:analyze --focus security (~2%)  Before any live strategy promotion
    sc:explain --think (~2%)           Understanding complex code or bugs
    sc:test (~2%)                      Coverage report after implementation

  MEDIUM COST — when stuck or researching:
    sc:troubleshoot --think (~5%)  Bug resists 2+ inline attempts
    sc:research (~5%)              Before building any new market type or strategy
    gsd:debug (~5%)                Bug resists inline diagnosis + sc:troubleshoot

  EXPENSIVE — conditional only (ALL: 5+ tasks, 4+ subsystems, multi-session, PLAN.md needed):
    gsd:plan-phase + gsd:execute-phase (~20-40%)  Complex multi-session phases only
    gsd:map-codebase (~20%)                       Brownfield audit before major new feature
    gsd:verify-work (~15%)                        End of milestone only, not quick tasks

═══════════════════════════════════════════════════
## SECURITY RULES — Non-negotiable. Read before writing code.
═══════════════════════════════════════════════════

✗ NEVER write files outside the polymarket-bot/ project folder
✗ NEVER touch system files, shell configs, ~/Library, ~/Documents
✗ NEVER commit .env or kalshi_private_key.pem to git (gitignore first)
✗ NEVER print private keys or credentials anywhere
✗ NEVER enable live trading yourself — paper/demo only
✗ NEVER exceed daily loss limit (~15.95 USD) — soft stop fires automatically
✗ NEVER contact any URL outside this approved list:
    https://api.elections.kalshi.com          ← only valid Kalshi URL
    wss://stream.binance.us:9443/ws           ← BTC/ETH feeds (Binance.US only)
    https://api.open-meteo.com/v1/forecast    ← weather feed (free, no key)
    https://fred.stlouisfed.org/graph/fredgraph.csv  ← FRED economic data (free, no key)
    api.weather.gov                           ← NWS NDFD feed (free, User-Agent required)
    https://api.polymarket.us/v1              ← Polymarket.US (sports-only, our credentials)
    https://data-api.polymarket.com           ← public reads only
    https://predicting.top/api/leaderboard    ← public leaderboard, no auth
    https://api.the-odds-api.com              ← sports data (SDATA_KEY, 1000 credits max)
    https://api.fred.stlouisfed.org           ← FRED API (FRED_API_KEY in .env)
    NOTE: wss://stream.binance.com is geo-blocked US (HTTP 451). Use Binance.US only.
✗ NEVER use sports data feed credits until quota guard + kill switch analog are implemented
✗ NEVER promote to Stage 2 based on bankroll alone — requires Kelly calibration (30+ live bets with limiting_factor=="kelly")
✓ All pip installs go into venv/ only
✓ Default mode: PAPER (PaperExecutor)
✓ Live trading: requires LIVE_TRADING=true in .env AND --live flag AND typing CONFIRM

═══════════════════════════════════════════════════
## POLYMARKET.US PLATFORM NOTES
═══════════════════════════════════════════════════

polymarket.US (existing .us auth — Ed25519):
  - Sports-only: NBA/NFL/NHL/NCAA markets. No crypto, no politics.
  - Our existing Ed25519 credentials (.env POLYMARKET_KEY_ID/SECRET_KEY) work here only.
  - Phase 5.1 complete: polymarket_auth.py + polymarket.py built + tested (Sessions 28-30).

polymarket.COM (global — separate auth needed):
  - Full market suite: crypto, politics, sports, culture, economics.
  - Auth: ECDSA secp256k1 (Ethereum wallet) — completely different from Ed25519.
  - Where the whales are (predicting.top leaderboard). Where copy trading happens.
  - Requires Matthew to create .com account + Polygon wallet. Not yet enabled.

IMPLICATION: Our whale watcher (data-api.polymarket.com) reads .COM trades.
  Our copy_trader_v1 generates signals from .COM whale activity.
  But we can only execute on .US today (sports only). Full copy trading requires .COM account.

API facts (polymarket.us):
  Base URL: https://api.polymarket.us/v1 | Rate: 60 req/min | Price scale: 0.0-1.0 (not cents)
  GET /v1/markets, GET /v1/markets/{id}/book, GET /v1/portfolio/positions
  DO NOT call: /markets/{integer_id}/*, /v2/*, /balance, /orders (GET), /portfolio/balance

═══════════════════════════════════════════════════
## WHAT'S ALREADY BUILT — DO NOT REBUILD
═══════════════════════════════════════════════════

Everything below exists and is tested. Read the files, don't rewrite them.

PHASE 1 — Foundation + Risk
  src/auth/kalshi_auth.py       RSA-PSS signing. load_from_env() loads .env.
  src/risk/kill_switch.py       8 triggers, kill_switch.lock, --reset-killswitch.
                                PYTEST_CURRENT_TEST guard on _hard_stop() and _write_blockers().
  src/risk/sizing.py            Kelly criterion at 0.25x, stage caps ($5/$10/$15).
                                Returns SizeResult dataclass — always extract .recommended_usd.
  setup/verify.py               Pre-flight checker. Run: python main.py --verify

PHASE 2 — Data + Strategy + Execution
  src/platforms/kalshi.py       Async REST client. Market, OrderBook dataclasses.
  src/data/binance.py           BTC+ETH WebSocket feeds (Binance.US). load_from_config() + load_eth_from_config()
  src/strategies/base.py        BaseStrategy + Signal dataclass.
  src/strategies/btc_lag.py     BTCLagStrategy: 4-gate signal engine. Also: load_eth_lag_from_config()
  src/strategies/btc_drift.py   BTCDriftStrategy: sigmoid drift-from-open. Also: load_eth_drift_from_config()
  src/strategies/orderbook_imbalance.py  VPIN-lite YES/NO bid depth. load_btc_imbalance + load_eth_imbalance
  src/strategies/weather_forecast.py     Open-Meteo GFS vs HIGHNY Kalshi markets. load_from_config()
  src/strategies/fomc_rate.py            FRED yield curve vs KXFEDDECISION markets. load_from_config()
  src/strategies/unemployment_rate.py    BLS UNRATE vs KXUNRATE markets. load_from_config()
  src/data/weather.py           EnsembleWeatherFeed (Open-Meteo GFS + NWS NDFD, adaptive std_dev)
  src/data/fred.py              FRED CSV: DFF, DGS2, CPIAUCSL, UNRATE (free, no key, 1hr cache)
  src/db.py                     SQLite persistence: trades, bankroll, kill events.
  src/execution/paper.py        PaperExecutor: fill + settle simulation.
  src/execution/live.py         LiveExecutor: real order placement (locked behind flag).
  main.py                       CLI + async trading loops + settlement loop.
  scripts/backtest.py           30-day BTC drift calibration via Binance.US klines API.
  scripts/restart_bot.sh        Safe restart: pkill, clean pid, full venv path, single-instance verify.
  scripts/notify_midnight.sh    Midnight UTC daily P&L Reminders notifier.
  scripts/seed_db_from_backtest.py  Populate DB from 30d historical data (graduation bootstrap).

PHASE 3 — Dashboard + Settlement
  src/dashboard.py              Streamlit UI at localhost:8501. Read-only.
  main.py settlement_loop()     Background asyncio task, polls Kalshi every 60s.

NOTE: More files exist beyond the above — run `find src/ tests/ scripts/ -name "*.py" | sort`
to see the full list. Always search before building.

═══════════════════════════════════════════════════
## KNOWN GOTCHAS — Learned through building (read before touching API code)
═══════════════════════════════════════════════════

0. KALSHI API: Only valid URL: https://api.elections.kalshi.com/trade-api/v2
   (trading-api.kalshi.com and demo-api.kalshi.co both dead)
   Balance field = 'balance' (not 'available_balance'). In cents. /100 for USD.
   Valid status filter = 'open'. ('active', 'initialized' return 400)

1. BINANCE GEO-BLOCK: wss://stream.binance.com returns HTTP 451 in the US.
   Always use wss://stream.binance.us:9443

2. BINANCE @TRADE STREAM HAS NEAR-ZERO VOLUME ON BINANCE.US: Use @bookTicker.
   Mid-price: (float(msg["b"]) + float(msg["a"])) / 2.0. ~100 updates/min.

3. BINANCE TIMEOUT: recv timeout must be ≥30s. @bookTicker can be silent 10-30s.
   _STALE_THRESHOLD_SEC = 35.0 (not 10s — that caused false stale signals).

4. KILL SWITCH RESET: echo "RESET" | python main.py --reset-killswitch

5. CONFIG.YAML: Must have 4 sections: kalshi, strategy, risk, storage.
   Series ticker must be "KXBTC15M" (not "btc_15min" — returns 0 markets silently).

6. WIN RATE BUG (fixed): db.win_rate() compares result==side (not result=="yes").

7. KILL SWITCH ORDER: bankroll floor check runs BEFORE pct cap check.

8. PYTEST GUARD: kill_switch._write_blockers() AND _hard_stop() both skip file writes
   when PYTEST_CURRENT_TEST is set. Prevents test runs from polluting BLOCKERS.md
   and KILL_SWITCH_EVENT.log. In-memory state (is_hard_stopped) still set during tests.

9. BOT.PID: Written at startup, removed on clean shutdown. Orphan guard uses pgrep to
   detect duplicate instances and exits. If bot fails to start, check for stale bot.pid.

10. SETTLEMENT LOOP: Must receive kill_switch param and call record_win/record_loss.
    Otherwise consecutive-loss and total-loss hard stops are dead code.
    Must use `if not trade["is_paper"]:` guard — paper losses must NOT count toward limit.

11. LIVE MODE: Requires --live flag + LIVE_TRADING=true in .env + type CONFIRM at runtime.
    All three gates required. Absence of any one falls back to paper silently.

12. WEATHER MARKETS: HIGHNY markets only exist weekdays. Weather loop logs
    "No open HIGHNY markets" on weekends — expected, not a bug.

13. FOMC STRATEGY: Only active in 14-day window before each 2026 meeting.
    Outside that window: timing gate blocks all signals (DEBUG log).
    CME FedWatch is blocked from server IPs. Use FRED CSV instead (free, no key).

14. ETH STRATEGIES: KXETH15M confirmed active. ETH lag/drift use name_override param
    to store eth_lag_v1/eth_drift_v1 in DB (not btc_lag_v1).

15. ALL GENERATE_SIGNAL() SKIP PATHS LOG AT DEBUG: Loop appears silent when no signal.
    Added INFO heartbeat "[trading] Evaluating N market(s)" to confirm loop alive.

16. RESTART — ALWAYS USE pkill NOT kill:
    `kill $(cat bot.pid)` only kills the most recent instance. Orphaned old instances
    keep running and place duplicate trades.
    SAFE: `bash scripts/restart_bot.sh`
    MANUAL: `pkill -f "python main.py"; sleep 3; rm -f bot.pid`
    Then verify: `ps aux | grep "[m]ain.py"` — must be exactly 1 process.

17. PAPER/LIVE SEPARATION (fixed Session 21):
    has_open_position() and count_trades_today() both accept `is_paper=` filter.
    Live daily cap counts live bets only. Paper bets do NOT eat into live quota.

18. SIZING — calculate_size() API (critical, must never be called wrong):
    - Returns SizeResult dataclass — extract .recommended_usd (not the object itself)
    - Always compute: `yes_p = price_cents if side=="yes" else (100 - price_cents)`
    - Then: `payout = kalshi_payout(yes_p, side)` → pass `payout_per_dollar=payout`
    - Always pass: `min_edge_pct=getattr(strategy, '_min_edge_pct', 0.08)`
    - Apply clamp: `trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD)`
    - Bug #4 (Session 22): omitting min_edge_pct defaulted to 8% → silently dropped btc_lag (4%) and btc_drift (5%) signals

19. KILL_SWITCH_EVENT.log TEST POLLUTION (fixed Session 22):
    _hard_stop() previously wrote to the live event log during pytest runs.
    Tests calling record_loss() 31 times created fake loss hard stop entries.
    Fixed: PYTEST_CURRENT_TEST guard in _hard_stop() skips all file writes.
    Alarming midnight entries in KILL_SWITCH_EVENT.log before the fix = test artifacts.

20. STAGE 2 PROMOTION (blocked):
    Bankroll crossed $100 but Stage 2 requires: 30+ live bets with limiting_factor=="kelly"
    At Stage 1, $5 cap always binds before Kelly → limiting_factor is always "stage_cap".
    DO NOT raise bet size to $10 based on bankroll alone. Read docs/GRADUATION_CRITERIA.md.

21. ODDS API — 1,000 CREDIT HARD CAP:
    User has 20,000 credits/month subscription. Max 1,000 for this bot (5% of budget).
    Sports props/moneyline/totals are a SEPARATE project — NOT for Kalshi bot.
    Before ANY API credit use: implement QuotaGuard + kill switch analog first.
    See .planning/todos.md for full roadmap item.

22. CONFIG SCOPE: `config` only exists in `main()`, not inside loop functions.
    Pass needed values as explicit params (e.g., `slippage_ticks: int = 1`).
    All 6 paper executor paths crashed silently on Session 18 because of this.

23. MACROS NOTIFICATIONS: `osascript display notification` unreliable on newer macOS.
    Use Reminders app: `tell application "Reminders" to make new reminder`.

24. LIVE.PY SECURITY AUDIT FINDINGS (sc:analyze Session 37-38):
    Three issues found — two fixed, one documented.
    FIXED: Execution-time price guard (Sessions 37).
      Signal at 59c passed 35-65c check at signal time, then filled at 84c due to HFT repricing
      in the asyncio queue gap. live.py now re-checks YES-equiv price after orderbook fetch and
      rejects if outside 35-65c OR if slippage > 10c from signal price. See TestExecutionPriceGuard.
    FIXED: Canceled order recorded to DB (Session 38).
      Kalshi can return order.status=="canceled" (no liquidity, market closing mid-execution).
      Was: db.save_trade() called unconditionally — phantom live bet corrupted calibration + kill switch.
      Now: `if order.status == "canceled": log warning + return None` before db.save_trade().
      See TestExecuteOrderStatusGuard. Pattern: always check order.status before recording.
    KNOWN: strategy_name="unknown" default.
      execute() signature has `strategy_name: str = "unknown"`. Any call omitting this param silently
      records trades under "unknown" → corrupts --graduation-status and --report. Always pass explicitly.

25. SKILLS REFERENCE: .planning/SKILLS_REFERENCE.md — complete skill/command map with token costs.
    Read before each session to pick the right tool. Key tiers:
    - FREE: gsd:add-todo, superpowers:TDD, superpowers:verification-before-completion
    - LOW (~1-2%): gsd:quick, sc:analyze, sc:test, sc:git
    - MEDIUM (~3-5%): sc:troubleshoot --think, sc:research, gsd:add-tests
    - EXPENSIVE (~15-25%): gsd:plan-phase, gsd:execute-phase, gsd:verify-work
    Rule: gsd:quick + superpowers:TDD covers 90% of work. Escalate only when ALL 4 conditions met.

═══════════════════════════════════════════════════
## PROJECT STRUCTURE (actual, as built)
═══════════════════════════════════════════════════

polymarket-bot/
├── POLYBOT_INIT.md              ← This file. Permanent reference.
├── SESSION_HANDOFF.md           ← Current state + exact next action (updated each session)
├── CLAUDE.md                    ← Claude session startup instructions
├── .planning/SKILLS_REFERENCE.md ← All available skills/commands with token costs (read each session)
├── .planning/CHANGELOG.md       ← Full session history (permanent record — do not truncate)
├── BLOCKERS.md
├── config.yaml                  ← All strategy params, risk limits, series tickers
├── pytest.ini                   ← asyncio_mode=auto (required for async tests)
├── .env                         ← REAL credentials (gitignored)
├── .env.example                 ← Template (safe to commit)
├── .gitignore
├── requirements.txt
├── docs/
│   ├── GRADUATION_CRITERIA.md   ← Stage 1→2→3 promotion criteria + Kelly calibration requirements
│   └── SETTLEMENT_MAPPING.md   ← Kalshi result field → win/loss mapping
├── setup/
│   └── verify.py                ← Pre-flight checker
├── scripts/
│   ├── backtest.py              ← 30-day BTC lag+drift calibration
│   ├── restart_bot.sh           ← Safe restart: pkill + venv path + single-instance verify
│   ├── seed_db_from_backtest.py ← Populate DB from 30d historical data (graduation bootstrap)
│   ├── notify_monitor.sh        ← macOS Reminders-based bot monitor (15min→30min alerts)
│   └── notify_midnight.sh       ← Midnight UTC daily P&L Reminders notifier
├── src/
│   ├── auth/
│   │   └── kalshi_auth.py       ← RSA-PSS signing
│   ├── platforms/
│   │   └── kalshi.py            ← Async REST client, Market/OrderBook types
│   ├── data/
│   │   ├── binance.py           ← BTC+ETH WebSocket feeds (Binance.US)
│   │   ├── weather.py           ← EnsembleWeatherFeed (Open-Meteo GFS + NWS NDFD blend)
│   │   └── fred.py              ← FRED CSV: DFF, DGS2, CPIAUCSL, UNRATE
│   ├── strategies/
│   │   ├── base.py              ← BaseStrategy + Signal dataclass
│   │   ├── btc_lag.py           ← Primary: 4-gate BTC momentum (+ ETH factory)
│   │   ├── btc_drift.py         ← Sigmoid drift-from-open (+ ETH factory)
│   │   ├── orderbook_imbalance.py ← VPIN-lite YES/NO depth ratio (BTC + ETH)
│   │   ├── weather_forecast.py  ← GFS forecast vs HIGHNY temperature markets
│   │   ├── fomc_rate.py         ← Yield curve vs KXFEDDECISION markets
│   │   └── unemployment_rate.py ← BLS UNRATE vs KXUNRATE markets
│   ├── execution/
│   │   ├── paper.py             ← PaperExecutor (fill + settle, 1-tick slippage)
│   │   └── live.py              ← LiveExecutor (locked behind --live flag)
│   ├── risk/
│   │   ├── kill_switch.py       ← 8 triggers + hard stop logic + test pollution guard
│   │   └── sizing.py            ← Kelly 0.25x, stage caps, returns SizeResult dataclass
│   ├── db.py                    ← SQLite: trades, bankroll, kill events
│   └── dashboard.py             ← Streamlit app (localhost:8501)
├── tests/
│   └── ...                      ← Run `python -m pytest tests/ -q` for full count
├── .planning/
│   ├── todos.md                 ← Roadmap: sports data feed, copytrade, future ideas
│   └── quick/                   ← GSD quick-task plans
├── logs/
│   ├── trades/
│   └── errors/
├── data/                        ← Auto-created at startup
│   └── polybot.db               ← SQLite (gitignored)
└── main.py                      ← CLI: --verify --live --report --status --reset-killswitch --graduation-status

═══════════════════════════════════════════════════
## COMMANDS
═══════════════════════════════════════════════════

# Bot lifecycle
bash scripts/restart_bot.sh                      → Safe restart (use this, not manual kill)
python main.py --live                             → Manual start (needs LIVE_TRADING=true + CONFIRM)
cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"

# Monitoring (all safe while bot is live — bypass PID lock)
tail -f /tmp/polybot.log                         → Watch live bot
source venv/bin/activate && python main.py --report           → Today P&L
source venv/bin/activate && python main.py --status           → Live status snapshot
source venv/bin/activate && python main.py --graduation-status → Graduation progress table

# Tests
source venv/bin/activate && python -m pytest tests/ -q        → Full test run (use -m, not bare pytest)

# Other
streamlit run src/dashboard.py                   → Dashboard at http://127.0.0.1:8501
echo "RESET" | python main.py --reset-killswitch → Reset kill switch after hard stop
python scripts/backtest.py --strategy both       → BTC lag + drift 30-day simulation

═══════════════════════════════════════════════════
## KILL SWITCH — 8 triggers
═══════════════════════════════════════════════════

1. Any single trade would exceed $5 OR 5% of current bankroll
2. Today's live P&L loss > 20% of starting bankroll (soft stop, resets midnight CST) ← was 15%, raised Session 23
3. 4 consecutive live losses → 2-hour cooling off period ← was 5, lowered Session 23
4. Total bankroll loss > 30% → HARD STOP (requires manual reset)
5. Bankroll drops below $20 → HARD STOP
6. kill_switch.lock file exists at startup → refuse to start
7. 3 consecutive auth failures → halt
8. Rate limit exceeded → pause

NOTE (Session 23+): Soft stops (triggers 2, 3, hourly rate) block LIVE bets only.
Paper data collection continues during soft stops. Hard stops (4, 5) block everything.
All 3 counters (daily loss, lifetime loss, consecutive losses) now persist across restarts (Sessions 24-25).

Hard stop recovery: echo "RESET" | python main.py --reset-killswitch

═══════════════════════════════════════════════════
## KALSHI AUTH — How it works
═══════════════════════════════════════════════════

- API Key ID + private .pem file (RSA 2048-bit, not a password)
- Every request needs signed headers:
    KALSHI-ACCESS-KEY: your key ID (UUID from kalshi.com → Settings → API)
    KALSHI-ACCESS-TIMESTAMP: ms timestamp
    KALSHI-ACCESS-SIGNATURE: RSA-PSS signed(timestamp + method + path)
- No session tokens — headers are per-request, no refresh needed

If auth fails (401): Key ID in .env does not match the .pem file.
  Go to kalshi.com → Settings → API. Match the Key ID shown next to YOUR .pem.

═══════════════════════════════════════════════════
## SIGNAL CALIBRATION
═══════════════════════════════════════════════════

btc_lag / eth_lag:
  min_edge_pct: 0.04 — needs ~0.32% BTC move in 60s (binding constraint)
  To get more signals: lower min_edge_pct (NOT min_btc_move_pct)
  30d backtest: 84.1% accuracy, 44 signals/30d, Brier=0.2178

btc_drift / eth_drift:
  min_edge_pct: 0.05 — fires at ~0.15-0.3% drift from open, ~1-3 live bets/day
  30-day backtest: 69% directional accuracy, Brier=0.22
  Late-entry penalty: edge_pct reduced for signals >2 min after window open
  NOTE: Bug #4 (Session 22) fix means 5%+ edge signals now fire correctly

orderbook_imbalance (BTC + ETH):
  min_imbalance_ratio: 0.65 — VPIN-lite: >65% one side = informed money
  min_total_depth: 50 — skip thin markets

weather_forecast (NYC HIGHNY):
  Normal distribution model: N(forecast_temp_f, adaptive std_dev) vs Kalshi YES price
  std_dev: <1F source diff → 2.5F; >4F diff → 5.0F; else 3.5F (config)
  min_edge_pct: 0.05, min_minutes_remaining: 30
  Only weekdays; Open-Meteo + NWS ENSEMBLE; free, no key

fomc_rate (KXFEDDECISION):
  Yield curve: DGS2 - DFF → P(hold/cut/hike) model (4 regimes)
  CPI adjustment: ±8% shift on acceleration/deceleration
  Only active 14 days before each 2026 FOMC date

unemployment_rate (KXUNRATE):
  BLS UNRATE vs Kalshi market prices, normal CDF model
  KXUNRATE markets open ~2 days before BLS release

NOTE: Calibration values in config.yaml are authoritative. These numbers may be outdated.
Always read config.yaml + run --graduation-status before tuning signal parameters.

═══════════════════════════════════════════════════
## THE RULE
═══════════════════════════════════════════════════

Build one thing that works before building two things that don't.
When blocked: write BLOCKERS.md, surface at next checkpoint.
When something breaks: fix it before moving forward.
Conservative > clever. Working > perfect. Logged > forgotten.
