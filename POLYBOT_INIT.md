# POLYBOT — BUILD INSTRUCTIONS + LIVE STATUS
# For: Claude Code Desktop App | Owner: Matthew
# Read this fully before doing anything.

═══════════════════════════════════════════════════
## CURRENT STATUS — READ THIS FIRST (updated each session)
═══════════════════════════════════════════════════

BUILD COMPLETE: All 3 phases done. 107/107 tests passing.
BLOCKER: Kalshi API auth failing (401). One action needed from Matthew.

verify.py score: 17/18
  ✅ env file, key IDs, PEM file, PEM valid RSA
  ✅ Auth headers generated (KEY/SIG/TS)
  ✅ Kalshi demo API reachable
  ❌ Authenticated request → 401 (Key ID / PEM mismatch — see BLOCKER below)
  ✅ Binance.US WebSocket (BTC price feed live)
  ✅ Kill switch clear
  ✅ config.yaml valid (all sections present)
  ✅ DB write/read
  ✅ BTCLagStrategy loads + sizing works

OPEN BLOCKER: Kalshi 401 Unauthorized
  The Key ID in .env (KALSHI_API_KEY_ID) does not match the kalshi_private_key.pem.
  Fix: Go to kalshi.com → Settings → API.
       The Key ID shown next to the key whose .pem you have must match
       KALSHI_API_KEY_ID in .env.
       If you have multiple keys, delete old ones and re-download the .pem for the
       matching key. Re-run: python main.py --verify

WHEN VERIFY PASSES:
  Run paper mode: python main.py
  Watch dashboard: streamlit run src/dashboard.py  (localhost:8501)
  Target: 7+ days paper with positive P&L before going live.

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
  tests/test_db.py              25 tests for SQLite layer (all passing).
  tests/test_strategy.py        23 tests for BTCLagStrategy (all passing).
  Total: 107/107 passing.

═══════════════════════════════════════════════════
## KNOWN GOTCHAS — Learned through building
═══════════════════════════════════════════════════

1. BINANCE GEO-BLOCK: wss://stream.binance.com returns HTTP 451 in the US.
   Always use wss://stream.binance.us:9443/ws/btcusdt@trade

2. BINANCE TIMEOUT: The Binance.US WebSocket connects fine but trade messages
   can be silent for >10 seconds. verify.py uses a 30s recv timeout. Don't
   reduce it or the check will flap.

3. BLOCKERS.MD ACCUMULATES: kill_switch.py automatically appends a new blocker
   entry every time 3 consecutive auth failures occur. This fires whenever --verify
   is run without valid keys. Expected behavior — don't delete the mechanism,
   just clean up old duplicate entries periodically.

4. KILL SWITCH FALSE TRIGGER: The kill_switch.lock from early auth testing may
   still exist. Always run --reset-killswitch before --verify if blocked.
   Reset requires piping "RESET": echo "RESET" | python main.py --reset-killswitch

5. CONFIG.YAML storage SECTION: verify.py checks for ['kalshi','strategy','risk','storage'].
   The 'storage' section must be present. Template: storage:\n  db_path: data/polybot.db

6. WIN RATE BUG (fixed): db.win_rate() must compare result==side (not result=="yes").
   Betting NO and winning means result=="no"==side. The fix is in db.py.

7. LOAD_FROM_CONFIG lag_sensitivity (fixed): btc_lag.py load_from_config() previously
   silently dropped lag_sensitivity. Now reads: s.get("lag_sensitivity", _DEFAULT_LAG_SENSITIVITY)

8. KALSHI AUTH: Key ID is a UUID. The Key ID in .env must match EXACTLY the ID
   shown in Kalshi Settings → API for the specific .pem you downloaded.
   If you have multiple API keys, each has its own .pem. Match them exactly.

9. VENV: Always activate with: source venv/bin/activate (or use venv/bin/python directly)

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

source venv/bin/activate && pytest tests/ -v  → Run all 107 tests

═══════════════════════════════════════════════════
## CHECKPOINT GATES
═══════════════════════════════════════════════════

CHECKPOINT_0 — ✅ COMPLETE: Scaffold, gitignore, intel, reference repos.
CHECKPOINT_1 — ✅ COMPLETE: Auth, structure, verify.py passes.
CHECKPOINT_2 — ✅ COMPLETE: Strategy, kill switch, 107 tests passing.
CHECKPOINT_3 — ✅ COMPLETE: Dashboard, settlement loop, paper mode ready.
CHECKPOINT_4 — NEXT: python main.py --verify passes 18/18. Paper mode runs.

CHECKPOINT_4 gate:
  ✓ 18/18 verify checks pass (need Kalshi 401 fixed)
  ✓ python main.py runs 10 min without crashing
  ✓ At least one paper trade signal logged
  ✓ Dashboard shows data at localhost:8501

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
"We are resuming the polymarket-bot project.
Read these files first (in order), then continue where we left off:
1. POLYBOT_INIT.md — original build spec + live status + all learnings
2. SESSION_HANDOFF.md — current state, next actions, component status
3. BLOCKERS.md — open issues needing my input

Do NOT ask setup questions — the project is already built.
Resume from: [paste the 'Next action' section of SESSION_HANDOFF.md here]"
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

### 2026-02-26 — Session 4 (verify fixes)
Completed:
- Matthew created .env with Kalshi Key ID + .pem in project root.
- Diagnose verify failures: kill switch (reset), config storage section (added),
  Binance.com geo-block (HTTP 451) → switched to Binance.US everywhere.
- Verify score: 17/18. One blocker remains: Kalshi 401 (Key ID / PEM mismatch).
Next: Matthew fixes Key ID in .env to match .pem → re-run python main.py --verify
      → run python main.py (paper mode) → confirm trades log → CHECKPOINT_4.
