# POLYBOT — BUILD INSTRUCTIONS + LIVE STATUS
# For: Claude Code Desktop App | Owner: Matthew
# Read this fully before doing anything.

═══════════════════════════════════════════════════
## CURRENT STATUS — READ THIS FIRST (updated each session)
═══════════════════════════════════════════════════

BUILD COMPLETE: All 3 phases done. 117/117 tests passing.
verify.py: 18/18 ✅. BTC price feed confirmed live. Trading loop evaluates every 30s.

WHAT WORKS:
  ✅ Kalshi auth (api.elections.kalshi.com — old URLs deprecated)
  ✅ Balance reads $75.00 from API
  ✅ BTC feed live — Binance.US @bookTicker, ~100 ticks/min, btc_move_pct() returning real values
     (@trade had near-zero volume; @bookTicker uses mid-price = (bid+ask)/2)
  ✅ Trading loop confirmed: "[trading] Evaluating 1 market(s): [KXBTC15M-...]" every 30s
  ✅ Kill switch clear, DB running, strategy loads
  ✅ KXETH15M also confirmed live (same structure as BTC — future expansion)
  ✅ tests/conftest.py: auto-cleans kill_switch.lock at test session start/end
  ✅ bot.pid lock: prevents two `python main.py` instances running simultaneously
  ✅ Near-miss log: every 30s shows "BTC move +X.XXX% (need ±0.40%) — waiting for signal"
  ✅ Dashboard DB path fixed: reads data/polybot.db from config.yaml (was hardcoded wrong)
  ✅ data/ dir auto-created at startup (safe on fresh clone)
  ✅ SIGTERM handler: `kill PID` triggers same clean shutdown as Ctrl+C

OPEN:
  No signal has fired yet. Bot needs to run during a BTC volatile period.
  Observed moves: ~0.02-0.03% in 60s, threshold is 0.4%. Normal for calm market.

NEXT ACTION:
  python main.py — let it run, watch for "[btc_lag] Signal: BUY" log lines.
  Every 30s you will see: "[btc_lag] BTC move +X.XXX% (need ±0.40%) — waiting for signal"
  If no signal after a few hours: lower min_edge_pct 0.08→0.05 in config.yaml
  (NOT min_btc_move_pct — min_edge_pct is the binding constraint, needs ~0.65% BTC in 60s)

DO NOT enable live trading until:
  ✓ Signal fires and is logged in paper mode
  ✓ 7+ days paper with positive P&L

═══════════════════════════════════════════════════
## STEP 0: ASK MATTHEW THESE QUESTIONS FIRST
## (Only if starting a brand new project — skip if resuming)
═══════════════════════════════════════════════════

Q1: "What is your starting bankroll in USD?"
Q2: "Kalshi account ready? (yes/no)"
Q3: "Have you created a Kalshi API key yet? (yes/no)"
     If no → tell Matthew: Go to kalshi.com → Settings → API →
     Create New API Key → download the .pem file → save it as
     kalshi_private_key.pem in this project folder
Q4: "Any market categories to exclude? (e.g. politics, sports)"
Q5: "Anything else to add before we build?"

Confirm answers back. Write USER_CONFIG.json. Then begin.

Answers already given (do not re-ask):
  Bankroll: $50.00
  Kalshi: yes, account ready
  API key: yes, created — kalshi_private_key.pem is in project root
  Exclusions: none
  Notes: Matthew is a doctor, first child (daughter) due August 2026.
         He needs this to be profitable. Be conservative, not clever.

═══════════════════════════════════════════════════
## SECURITY RULES — Non-negotiable. Read before writing code.
═══════════════════════════════════════════════════

✗ NEVER write files outside the polymarket-bot/ project folder
✗ NEVER touch system files, shell configs, ~/Library, ~/Documents
✗ NEVER commit .env or kalshi_private_key.pem to git (gitignore first)
✗ NEVER print private keys or credentials anywhere
✗ NEVER enable live trading yourself — paper/demo only
✗ NEVER exceed $5 per trade or 5% of bankroll (whichever is lower)
✗ NEVER exceed 30% total bankroll loss before hard stopping
✗ NEVER contact any URL outside this approved list:
    https://trading-api.kalshi.com
    https://demo-api.kalshi.co         ← use this first (free demo)
    wss://demo-api.kalshi.co
    wss://stream.binance.us:9443/ws    ← BTC price feed (Binance.US — .com is geo-blocked in US)
    NOTE: wss://stream.binance.com is blocked in the US (HTTP 451). Use Binance.US only.
✓ All pip installs go into venv/ only
✓ Default mode: PAPER (Kalshi demo environment)
✓ Live trading: requires LIVE_TRADING=true in .env AND --live flag

═══════════════════════════════════════════════════
## WHAT'S ALREADY BUILT — DO NOT REBUILD
═══════════════════════════════════════════════════

Everything below exists and is tested. Read the files, don't rewrite them.

PHASE 1 — Foundation + Risk
  src/auth/kalshi_auth.py       RSA-PSS signing. load_from_env() loads .env.
  src/risk/kill_switch.py       8 triggers, kill_switch.lock, --reset-killswitch.
  src/risk/sizing.py            Kelly criterion at 0.25x, stage caps ($5/$10/$15).
  setup/verify.py               Pre-flight checker. Run: python main.py --verify
  tests/test_kill_switch.py     Kill switch tests (all passing).
  tests/test_security.py        Security constraint tests (all passing).

PHASE 2 — Data + Strategy + Execution
  src/platforms/kalshi.py       Async REST client. Market, OrderBook dataclasses.
  src/data/binance.py           BTC WebSocket feed (Binance.US). btc_move_pct().
  src/strategies/base.py        BaseStrategy + Signal dataclass.
  src/strategies/btc_lag.py     BTCLagStrategy: 4-gate signal engine.
  src/db.py                     SQLite persistence: trades, bankroll, kill events.
  src/execution/paper.py        PaperExecutor: fill + settle simulation.
  src/execution/live.py         LiveExecutor: real order placement (locked behind flag).
  main.py                       CLI entry point + async trading/settlement loops.

PHASE 3 — Dashboard + Settlement
  src/dashboard.py              Streamlit UI at localhost:8501. Read-only.
  main.py settlement_loop()     Background asyncio task, polls Kalshi every 60s.

TESTS
  tests/conftest.py             Kill switch lock cleanup fixture (session-scoped).
  tests/test_db.py              29 tests for SQLite layer + dashboard DB path (all passing).
  tests/test_kill_switch.py     52 tests including settlement integration + pytest guard.
  tests/test_strategy.py        23 tests for BTCLagStrategy (all passing).
  Total: 117/117 passing.

═══════════════════════════════════════════════════
## KNOWN GOTCHAS — Learned through building (read before touching API code)
═══════════════════════════════════════════════════

0. KALSHI API MIGRATION: Old URLs are dead. Only valid URL is:
   https://api.elections.kalshi.com/trade-api/v2
   (trading-api.kalshi.com and demo-api.kalshi.co both 401/redirect)
   There is no separate demo environment. Paper mode = PaperExecutor, not a demo URL.
   Balance field = 'balance' (not 'available_balance'). In cents. /100 for USD.
   Market price fields = 'yes_bid'/'no_bid' (not 'yes_price'/'no_price').
   Valid status filter = 'open' (returns markets with status='active').
   'active', 'initialized' are NOT valid filter values (400 bad_request).

1. BINANCE GEO-BLOCK: wss://stream.binance.com returns HTTP 451 in the US.
   Always use wss://stream.binance.us:9443

2. BINANCE @TRADE STREAM HAS NEAR-ZERO VOLUME ON BINANCE.US: The @trade stream
   produces 0 messages — there are almost no individual BTC trades. Use @bookTicker
   instead. It fires on every best bid/ask change (~100 updates/min). Mid-price:
   (float(msg["b"]) + float(msg["a"])) / 2.0

3. BINANCE TIMEOUT: verify.py uses a 30s recv timeout for the WebSocket check.
   Don't reduce it — @bookTicker can have gaps of a few seconds between updates.

4. BLOCKERS.MD ACCUMULATES: kill_switch.py automatically appends a new blocker
   entry every time 3 consecutive auth failures occur. This fires whenever --verify
   is run without valid keys. Expected behavior — don't delete the mechanism,
   just clean up old duplicate entries periodically.

5. KILL SWITCH FALSE TRIGGER: The kill_switch.lock from early auth testing may
   still exist. Always run --reset-killswitch before --verify if blocked.
   Reset requires piping "RESET": echo "RESET" | python main.py --reset-killswitch

6. CONFIG.YAML storage SECTION: verify.py checks for ['kalshi','strategy','risk','storage'].
   The 'storage' section must be present. Template: storage:\n  db_path: data/polybot.db

7. WIN RATE BUG (fixed): db.win_rate() must compare result==side (not result=="yes").
   Betting NO and winning means result=="no"==side. The fix is in db.py.

8. LOAD_FROM_CONFIG lag_sensitivity (fixed): btc_lag.py load_from_config() previously
   silently dropped lag_sensitivity. Now reads: s.get("lag_sensitivity", _DEFAULT_LAG_SENSITIVITY)

9. KALSHI AUTH: Key ID is a UUID. The Key ID in .env must match EXACTLY the ID
   shown in Kalshi Settings → API for the specific .pem you downloaded.
   If you have multiple API keys, each has its own .pem. Match them exactly.

10. VENV: Always activate with: source venv/bin/activate (or use venv/bin/python directly)

═══════════════════════════════════════════════════
## THE LOG SYSTEM — Build this first. Update after every action.
## This lets any future Claude session resume from exactly where you left off.
═══════════════════════════════════════════════════

Create and maintain these files throughout the build:

MASTER_LOG.md — one entry per action:
  ## [timestamp] — [what you did]
  Why: [one sentence]
  Result: success / failed / partial
  Files changed: [list]
  Error hit: [exact message or "none"]
  Retractable: delete [file] to undo
  ---

SESSION_HANDOFF.md — updated at end of every session:
  Current state: [what works right now]
  Next action: [exactly one thing to do next]
  To resume: python main.py --verify
  Known issues: [anything unstable]

BLOCKERS.md — anything needing Matthew:
  ## BLOCKER: [title]
  Need: [exact question]
  Severity: CRITICAL / LOW

═══════════════════════════════════════════════════
## PROJECT STRUCTURE (actual, as built)
═══════════════════════════════════════════════════

polymarket-bot/
├── POLYBOT_INIT.md              ← This file. The source of truth.
├── MASTER_LOG.md
├── SESSION_HANDOFF.md
├── BLOCKERS.md
├── CHECKPOINT_0.md              ← Scaffold + intel (complete)
├── CHECKPOINT_1.md              ← Auth + structure (complete)
├── CHECKPOINT_2.md              ← Strategy + kill switch (complete)
├── CHECKPOINT_3.md              ← Dashboard + settlement (complete)
├── ARCHITECTURE.md              ← System diagram
├── DECISIONS.md                 ← Why decisions were made
├── ERRORS_AND_FIXES.md          ← Bug history
├── INTEL.md                     ← Reference repo notes
├── .env                         ← REAL credentials (gitignored)
├── .env.example                 ← Template (safe to commit)
├── .gitignore
├── requirements.txt
├── config.yaml
├── USER_CONFIG.json             ← Matthew's startup answers
├── setup/
│   ├── install.sh               ← Creates venv, installs deps
│   └── verify.py                ← Pre-flight checker (10 checks)
├── src/
│   ├── auth/
│   │   └── kalshi_auth.py       ← RSA-PSS signing, load_from_env()
│   ├── platforms/
│   │   └── kalshi.py            ← Async REST client, Market/OrderBook types
│   ├── data/
│   │   └── binance.py           ← BTC WebSocket feed (Binance.US)
│   ├── strategies/
│   │   ├── base.py              ← BaseStrategy + Signal dataclass
│   │   └── btc_lag.py           ← Primary strategy: 4-gate BTC lag detector
│   ├── execution/
│   │   ├── paper.py             ← PaperExecutor (fill + settle)
│   │   └── live.py              ← LiveExecutor (locked behind --live flag)
│   ├── risk/
│   │   ├── kill_switch.py       ← 8 triggers + hard stop logic
│   │   └── sizing.py            ← Kelly 0.25x, stage caps
│   ├── db.py                    ← SQLite: trades, bankroll, kill events
│   └── dashboard.py             ← Streamlit app (localhost:8501)
├── tests/
│   ├── test_kill_switch.py
│   ├── test_security.py
│   ├── test_db.py               ← 25 tests
│   └── test_strategy.py         ← 23 tests
├── logs/
│   ├── trades/
│   └── errors/
└── main.py                      ← CLI: --verify --live --report --reset-killswitch

═══════════════════════════════════════════════════
## REFERENCE REPOS — Already cloned and documented
═══════════════════════════════════════════════════

refs/kalshi-btc/    — Primary: Kalshi BTC 15-min bot. Auth stolen verbatim.
refs/kalshi-auth/   — Auth reference: RSA-PSS signing.

INTEL.md has the key learnings. Do not re-clone unless needed.

═══════════════════════════════════════════════════
## WHAT TO BUILD — AND ONLY THIS
═══════════════════════════════════════════════════

ONE strategy: BTC 15-min price lag on Kalshi. Already built in src/strategies/btc_lag.py.

The logic:
- Watch BTC spot price on Binance.US (free public WebSocket)
- Watch Kalshi "Will BTC go UP in next 15 min?" market price
- When ALL 4 conditions are true:
  1. BTC moved >0.4% on Binance in 60 seconds
  2. Implied Kalshi lag > 5 cents (btc_move_pct * lag_sensitivity)
  3. >5 minutes remain in the 15-min window
  4. Net edge (lag - fee) > 8%
  → Buy the directionally correct side
- Max $5 per bet, 5% of bankroll cap (lower applies)
- Log everything

Fees: Kalshi charges 0.07 × P × (1-P) where P is price in [0,1].
Edge formula: edge = (implied_lag_cents/100) - kalshi_fee(price)
Win prob: min(0.85, price_pct + implied_lag_pct * 0.8)

That's it. Not whale tracking. Not weather. Not Polymarket yet.
One thing. Working. Proven in paper mode. Then expand.

═══════════════════════════════════════════════════
## KALSHI AUTH — How it works (implemented in src/auth/kalshi_auth.py)
═══════════════════════════════════════════════════

- API Key ID + private .pem file (RSA 2048-bit, not a password)
- Every request needs signed headers:
    KALSHI-ACCESS-KEY: your key ID
    KALSHI-ACCESS-TIMESTAMP: ms timestamp
    KALSHI-ACCESS-SIGNATURE: RSA-PSS signed(timestamp + method + path)
- No session tokens — headers are per-request, no refresh needed
- Demo URL: https://demo-api.kalshi.co/trade-api/v2

If auth fails (401): Key ID in .env does not match the .pem file.
  Go to kalshi.com → Settings → API.
  Match the Key ID shown next to the key whose .pem you have.

═══════════════════════════════════════════════════
## KILL SWITCH — 8 triggers (implemented in src/risk/kill_switch.py)
═══════════════════════════════════════════════════

Triggers → cancel all orders, halt all trading, write kill_switch.lock:
1. Any single trade would exceed $5 OR 5% of current bankroll
2. Today's P&L loss > 15% of starting bankroll (soft stop, resets midnight)
3. 5 consecutive losses → 2-hour cooling off period
4. Total bankroll loss > 30% → HARD STOP (requires manual reset)
5. Bankroll drops below $20 → HARD STOP
6. kill_switch.lock file exists at startup → refuse to start
7. 3 consecutive auth failures → halt
8. Rate limit exceeded → pause

Hard stop recovery: echo "RESET" | python main.py --reset-killswitch
Or interactively: python main.py --reset-killswitch  (type RESET when prompted)

═══════════════════════════════════════════════════
## COMMANDS
═══════════════════════════════════════════════════

python main.py                    → Paper mode (default, safe)
python main.py --live             → Live (needs LIVE_TRADING=true in .env)
python main.py --verify           → Pre-flight check, exit with result
python main.py --report           → Print P&L summary, exit
python main.py --reset-killswitch → Reset after hard stop (type RESET)

streamlit run src/dashboard.py   → Dashboard at http://127.0.0.1:8501

source venv/bin/activate && python -m pytest tests/ -v  → Run all 117 tests

═══════════════════════════════════════════════════
## CHECKPOINT GATES
═══════════════════════════════════════════════════

CHECKPOINT_0 — ✅ COMPLETE: Scaffold, gitignore, intel, reference repos.
CHECKPOINT_1 — ✅ COMPLETE: Auth, structure, verify.py passes.
CHECKPOINT_2 — ✅ COMPLETE: Strategy, kill switch, 107 tests passing.
CHECKPOINT_3 — ✅ COMPLETE: Dashboard, settlement loop, paper mode ready.
CHECKPOINT_4 — ✅ COMPLETE: 18/18 verify, loop evaluates every 30s, 117/117 tests.
  ⏳ First paper signal still pending (needs ~0.65% BTC move in 60s).

CHECKPOINT_4 gate:
  ✓ 18/18 verify checks pass
  ✓ python main.py runs without crashing, evaluates KXBTC15M every 30s
  ⏳ At least one paper trade signal logged (time-dependent, not code-dependent)
  ✓ Dashboard connects to data/polybot.db

═══════════════════════════════════════════════════
## THE RULE
═══════════════════════════════════════════════════

Build one thing that works before building two things that don't.
When blocked: write BLOCKERS.md, surface at next checkpoint.
When something breaks: fix it before moving forward.
Conservative > clever. Working > perfect. Logged > forgotten.

═══════════════════════════════════════════════════
## CONTEXT HANDOFF — When starting a new Claude chat
═══════════════════════════════════════════════════

When starting a new chat, paste this at the top:

────────────────────────────────────────
We are resuming the polymarket-bot project. Read these files first (in order), then continue:
1. POLYBOT_INIT.md — build spec, current status, all known gotchas
2. SESSION_HANDOFF.md — current state and exact next action

Do NOT ask setup questions. The bot is fully built, tested, and auth is working.

CURRENT STATE (as of last session):
- 117/117 tests passing. verify.py 18/18.
- Trading loop confirmed running: evaluates KXBTC15M every 30s.
- Every 30s you see: "[btc_lag] BTC move +X.XXX% (need ±0.40%) — waiting for signal"
- No paper trade signal has fired yet — BTC moves ~0.02-0.05% in calm market, need ~0.65%.
- All critical safety fixes applied: kill switch wired to settlement, live CONFIRM prompt,
  PID lock, SIGTERM handler, dashboard DB path, stale threshold 35s.
- LIVE_TRADING=false — paper mode only. No real orders possible without --live + .env change.
- All sessions 1-9 committed and pushed to GitHub (main branch).

RESUME FROM:
Run `python main.py` and let it watch for the first paper signal.
Every 30s you'll see the near-miss log. First signal fires when BTC moves ~0.65%+ in 60s.
If no signal after a few hours: lower min_edge_pct 0.08 → 0.05 in config.yaml (NOT min_btc_move_pct).

KEY FACTS:
- Kalshi API: api.elections.kalshi.com (old URLs dead — trading-api.kalshi.com 401s)
- BTC feed: Binance.US wss://stream.binance.us:9443/ws/btcusdt@bookTicker
  (binance.com HTTP 451 geo-blocked in US. @trade stream has near-zero volume — use @bookTicker)
- Balance: $75 confirmed from API. Starting bankroll: $50 in config.yaml.
- Next market after BTC proven: KXETH15M (same structure, same lag logic — do NOT add until 7+ paper days positive)
- Dashboard: streamlit run src/dashboard.py → localhost:8501
- Kill switch reset: echo "RESET" | python main.py --reset-killswitch
────────────────────────────────────────

WHAT CLAUDE SHOULD DO AUTOMATICALLY AT END OF EACH SESSION:
- Update SESSION_HANDOFF.md with current state and next action
- Update POLYBOT_INIT.md → CURRENT STATUS section and PROGRESS LOG
- Commit changes with descriptive message
- Update BLOCKERS.md if anything new came up

═══════════════════════════════════════════════════
## PROGRESS LOG — Updated by Claude at end of each session
═══════════════════════════════════════════════════

### 2026-02-25 — Session 1 (CHECKPOINT_0)
Completed: Project scaffold, gitignore, USER_CONFIG.json, log files, reference repo intel.
Result: CHECKPOINT_0 committed.

### 2026-02-25 — Session 2 (CHECKPOINT_1 + CHECKPOINT_2)
Completed:
- Phase 1: auth (RSA-PSS), kill switch (59/59 tests), sizing (Kelly + stage caps),
  setup/verify.py (7-check pre-flight), full test suite passing.
- Phase 2: src/platforms/kalshi.py (async REST client), src/data/binance.py (BTC WS feed),
  src/strategies/btc_lag.py (4-condition gate), src/db.py (SQLite),
  src/execution/paper.py + live.py, main.py (CLI + async loop).
Result: CHECKPOINT_1 + CHECKPOINT_2 committed and pushed.

### 2026-02-25 — Session 3 (CHECKPOINT_3)
Completed:
- src/dashboard.py: Streamlit UI at localhost:8501.
- Settlement loop: background asyncio task in main.py.
- Bug fixes: db.win_rate() (result==side), btc_lag load_from_config lag_sensitivity.
- Tests expanded: test_db.py (25 tests), test_strategy.py (23 tests). Total: 107/107.
- setup/verify.py: 3 new checks (config, DB write, strategy).
Result: CHECKPOINT_3 committed and pushed.

### 2026-02-26 — Session 4 (API fixes + first bot run)
Completed:
- .env created with correct Key ID + .pem in project root.
- verify.py: 18/18 all checks passing.
- Kalshi API URL changed: trading-api.kalshi.com → api.elections.kalshi.com
- Balance field: available_balance → balance (API renamed it)
- Market price fields: yes_price/no_price → yes_bid/no_bid (API renamed)
- data/ directory created (DB lives at data/polybot.db)
- Bot starts and runs in paper mode. Balance $75 confirmed from API.
- One active KXBTC15M market found with real prices (yes_bid=87¢, no_bid=10¢).
- Trading loop confirmed running but no signal output observed yet.
  (Hypothesis: 60s warm-up + market had <5 min remaining when tested)

### 2026-02-26 — Session 5 (trading loop confirmed + market catalog)
Completed:
- ROOT CAUSE of silence found: config.yaml had "btc_15min" as series ticker.
  Correct Kalshi ticker is "KXBTC15M". Fixed.
- main.py: added INFO heartbeat "[trading] Evaluating N market(s)" each poll cycle.
  Previously all skip paths were DEBUG-only — loop appeared silent when no signal.
- Confirmed loop runs: evaluates KXBTC15M every 30s, no signal fired yet (normal).
- Kalshi market catalog probed live: KXETH15M confirmed active (same structure as BTC).
  Next market after BTC proven = KXETH15M (add ETH feed, run parallel strategy instance).
- 107/107 tests still passing.
Next: Let bot run during volatile BTC session. Watch for first paper trade signal.
      If no signal in several hours: lower min_btc_move_pct 0.4→0.3 and re-observe.

### 2026-02-26 — Session 6 (Binance.US bookTicker fix + feed verified)
Completed:
- ROOT CAUSE of zero price data: Binance.US @trade stream has near-zero BTC volume.
  0 messages over 5 minutes. btc_move_pct() always returned None → gate 1 always failed.
- Fix: switched src/data/binance.py to @bookTicker stream.
  Mid-price = (best_bid + best_ask) / 2. ~100 updates/min confirmed on Binance.US.
  config.yaml binance_ws_url also updated to btcusdt@bookTicker.
- Feed verified live: 49 ticks in 30s, price=$67,474, btc_move_pct()=+0.030%, is_stale=False.
- Kill switch stale lock issue: tests/conftest.py created.
  Session-scoped autouse fixture cleans kill_switch.lock at test start/end.
  Prevents interrupted pytest run from blocking main.py startup.
- CLAUDE.md + POLYBOT_INIT.md gotchas updated (bookTicker, conftest.py, diagnostic kill pattern).
- 107/107 tests still passing.
Next: Let bot run during a volatile BTC period. Observed moves ~0.02-0.03%; need ~0.65%.
      If no signal in a few hours: lower min_edge_pct 0.08→0.05 (NOT min_btc_move_pct).

### 2026-02-27 — Session 7 (safeguards + observability + bug fixes)
Completed:
- PID lock: main.py writes bot.pid at startup, releases on shutdown.
  Prevents two bot instances from running simultaneously (dual execution, double API calls).
  bot.pid added to .gitignore.
- Near-miss INFO logging: btc_lag.py "BTC move too small" path promoted DEBUG→INFO.
  Every 30s: "[btc_lag] BTC move +X.XXX% (need ±0.40%) — waiting for signal"
  Matthew can now see feed is alive + how close bot is to firing without DEBUG mode.
- kill_switch._write_blockers() guards on PYTEST_CURRENT_TEST env var.
  Test runs no longer pollute BLOCKERS.md with false auth-failure entries.
- config.yaml: explicit lag_sensitivity param + signal calibration comment.
  Documents binding constraint: min_edge_pct=8% needs ~0.65% BTC move in 60s.
  Guidance corrected: lower min_edge_pct, not min_btc_move_pct.
- BLOCKERS.md cleaned. SESSION_HANDOFF.md guidance corrected.
- Dashboard DB path bug fixed: was hardcoded to kalshi_bot.db (wrong path).
  Fixed via _resolve_db_path() → reads config.yaml → data/polybot.db. Dashboard now works.
- data/ directory auto-created at main.py startup (fresh clone safety).
  data/.gitkeep added to repo (DB itself still gitignored).
- verify.py Binance check fixed: was using @trade (near-zero volume, timeouts).
  Now uses @bookTicker (same as binance.py), parses bid/ask for mid-price.
- SIGTERM handler added to main.py: `kill PID` now triggers clean shutdown.
  Uses loop.add_signal_handler for SIGTERM + SIGHUP — same finally cleanup block.
- 107/107 tests still passing.
Next: Let bot run. Watch for "[btc_lag] Signal: BUY" log line.
      Moves needed: ~0.65%+ in 60s. To fire more often: lower min_edge_pct to 0.05.

### 2026-02-27 — Session 9 (minor bug fixes + commit + push)
Completed:
- Removed dead `price_key` variable from live.py (assigned but never used).
- Guarded `strategy.markets[0]` against empty list in main.py — explicit error message.
- Commented `_FIRST_RUN_CONFIRMED` in live.py to document dual-CONFIRM design.
- Added `claude/` to .gitignore (Claude Code settings dir).
- Committed all sessions 5-9 changes as `067a723` and pushed to GitHub.
- 117/117 tests passing.
Next: `python main.py` — let it run and watch for first paper signal.

### 2026-02-27 — Session 8 (code review critical fixes)
Completed:
- CRITICAL: kill_switch was fully disconnected from settlement loop.
  settlement_loop now takes kill_switch param. Calls record_win()/record_loss() each settlement.
  Consecutive-loss cooling, daily-loss soft stop, total-loss hard stop were dead code. Now live.
- CRITICAL: live_confirmed=False was hardcoded — live mode silently fell back to paper.
  Now: live mode shows warning banner, requires user to type 'CONFIRM' at runtime.
  Matches the described behavior in dashboard Tips.
- IMPORTANT: PermissionError in PID lock now exits (process IS alive under another user).
  Was being swallowed as "stale PID" — could allow dual instances in multi-user scenario.
- IMPORTANT: Removed dead sizing/paper_executor params from trading_loop signature.
  Both were always None, never used — dead code in the function signature.
- MINOR: Stale threshold in binance.py raised 10s→35s.
  Binance.US @bookTicker documented to be silent 10-30s — 10s threshold caused false stale signals.
- Added 5 TestSettlementIntegration tests in test_kill_switch.py.
  Covers: win resets counter, loss accumulates daily/realized, hard stop at 30%, zero ignored.
- 117/117 tests passing.
Next: Let bot run. Watch for "[btc_lag] Signal: BUY" log line. First live trade after 7+ paper days.
