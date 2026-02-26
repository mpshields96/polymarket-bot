# POLYBOT — BUILD INSTRUCTIONS
# For: Claude Code Desktop App | Owner: Matthew
# Read this fully before doing anything.

═══════════════════════════════════════════════════
## STEP 0: ASK MATTHEW THESE QUESTIONS FIRST
## Print to screen. Wait for answers. Save to USER_CONFIG.json.
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
    https://demo-api.kalshi.co       ← use this first (free demo)
    wss://demo-api.kalshi.co
    wss://stream.binance.com:9443/ws ← BTC price feed, public
✓ All pip installs go into venv/ only
✓ Default mode: PAPER (Kalshi demo environment)
✓ Live trading: requires LIVE_TRADING=true in .env AND --live flag

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
## PROJECT STRUCTURE
═══════════════════════════════════════════════════

polymarket-bot/
├── MASTER_LOG.md
├── SESSION_HANDOFF.md
├── BLOCKERS.md
├── CHECKPOINT_1.md          ← After auth + structure (human reviews)
├── CHECKPOINT_2.md          ← After strategy + kill switch (human reviews)
├── CHECKPOINT_3.md          ← After dashboard passes (human reviews)
├── .env.example
├── .gitignore
├── requirements.txt
├── config.yaml
├── USER_CONFIG.json         ← Startup answers
├── setup/
│   ├── install.sh           ← Creates venv, installs deps
│   └── verify.py            ← Tests Kalshi demo connection
├── src/
│   ├── auth.py              ← Kalshi RSA-PSS signing
│   ├── kalshi.py            ← Kalshi API client
│   ├── binance.py           ← BTC spot price WebSocket (public)
│   ├── strategy.py          ← BTC lag signal logic
│   ├── kill_switch.py       ← Hard stops
│   ├── sizing.py            ← Position sizing with hard caps
│   ├── paper.py             ← Paper trading simulation
│   ├── live.py              ← Real execution (locked)
│   ├── db.py                ← SQLite: trades + P&L
│   └── dashboard.py         ← Streamlit app
├── tests/
│   ├── test_security.py
│   └── test_kill_switch.py
├── logs/
└── main.py

═══════════════════════════════════════════════════
## REFERENCE REPOS — Clone and steal from these. Don't reinvent.
═══════════════════════════════════════════════════

mkdir refs && cd refs

# PRIMARY — Kalshi BTC 15-min bot. Best match for this project.
# Has: kill switch, demo env, risk controls, BTC price feed, replay engine
git clone https://github.com/Bh-Ayush/Kalshi-CryptoBot kalshi-btc

# AUTH REFERENCE — RSA-PSS signing implementation
git clone https://github.com/sswadkar/kalshi-interface kalshi-auth

cd ..

For each repo, read and document in MASTER_LOG.md:
- What auth method it uses (steal kalshi-btc auth verbatim if it works)
- Kill switch implementation (steal if clean)
- Any known bugs (check their GitHub issues tab)
- Add attribution comment above any stolen code:
  # Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot

═══════════════════════════════════════════════════
## WHAT TO BUILD — AND ONLY THIS
═══════════════════════════════════════════════════

ONE strategy: BTC 15-min price lag on Kalshi.

The logic:
- Watch BTC spot price on Binance (free public WebSocket)
- Watch Kalshi "Will BTC go UP in next 15 min?" market price
- When BTC moves >0.4% on Binance in 60 seconds AND
  Kalshi hasn't priced it in yet (>5 cent gap) AND
  >5 minutes remain in the 15-min window:
  → Buy the directionally correct side
- Max $5 per bet, 5% of bankroll cap (lower applies)
- Log everything

That's it. Not whale tracking. Not weather. Not Polymarket yet.
One thing. Working. Proven in paper mode. Then expand.

═══════════════════════════════════════════════════
## KALSHI AUTH — The critical part. Get this right first.
═══════════════════════════════════════════════════

Steal the RSA-PSS signing from refs/kalshi-btc/kalshi_client.py.
Key facts:
- API Key ID + private .pem file (not a password)
- Every request needs signed headers:
    KALSHI-ACCESS-KEY: your key ID
    KALSHI-ACCESS-TIMESTAMP: ms timestamp
    KALSHI-ACCESS-SIGNATURE: RSA-PSS signed(timestamp + method + path)
- Session tokens expire every 30 min → implement auto-refresh
- Demo URL: https://demo-api.kalshi.co/trade-api/v2
  (identical to prod, free, use this first)

If auth fails at any point → write BLOCKERS.md, halt cleanly,
print exactly what Matthew needs to fix.

═══════════════════════════════════════════════════
## KILL SWITCH — Build before any strategy code.
═══════════════════════════════════════════════════

Triggers → cancel all orders, halt all trading, write kill_switch.lock:
1. Any single trade would exceed $5 OR 5% of current bankroll
2. Today's P&L loss > 15% of starting bankroll (resets midnight)
3. 5 consecutive losses → 2-hour cooling off period
4. Total bankroll loss > 30% → HARD STOP (requires manual reset)
5. Bankroll drops below $20 → HARD STOP
6. kill_switch.lock file exists at startup → refuse to start with instructions

Hard stop recovery: python main.py --reset-killswitch
(print exact instructions when it triggers)

═══════════════════════════════════════════════════
## CONFIG.YAML
═══════════════════════════════════════════════════

# Kalshi platform
kalshi:
  mode: demo                      # Start here. Change to live manually.
  demo_url: https://demo-api.kalshi.co/trade-api/v2
  live_url: https://trading-api.kalshi.com/trade-api/v2

# Strategy
strategy:
  markets: [btc_15min]            # Only this. Expand later with proof.
  min_btc_move_pct: 0.4           # BTC must move 0.4% in 60s to signal
  min_kalshi_lag_cents: 5         # Kalshi must lag spot by 5+ cents
  min_minutes_remaining: 5        # Don't enter with < 5 min left
  min_edge_pct: 0.08              # Only trade if edge > 8%

# Risk — all caps enforced in code, not just config
risk:
  starting_bankroll: 0            # Set from USER_CONFIG.json
  max_single_trade_usd: 5.00      # Hard cap
  max_single_trade_pct: 0.05      # 5% of bankroll
  daily_loss_limit_pct: 0.15
  consecutive_loss_pause: 5
  hard_stop_loss_pct: 0.30
  min_bankroll_usd: 20.00

# Dashboard
dashboard:
  port: 8501                      # Streamlit default
  host: "127.0.0.1"              # Localhost only, never 0.0.0.0

═══════════════════════════════════════════════════
## .ENV.EXAMPLE — Human fills .env themselves. Never create .env yourself.
═══════════════════════════════════════════════════

# COPY TO .env — FILL IN YOUR VALUES
# NEVER share. NEVER commit to git.

KALSHI_API_KEY_ID=YOUR_KEY_ID_HERE
KALSHI_PRIVATE_KEY_PATH=./kalshi_private_key.pem

# Leave false until 7+ days paper with positive P&L
LIVE_TRADING=false

═══════════════════════════════════════════════════
## STREAMLIT DASHBOARD — src/dashboard.py
═══════════════════════════════════════════════════

Clean, mobile-friendly, auto-refreshes every 30s.

Show:
- Mode banner: PAPER (green) or LIVE (big red warning)
- Kill switch status: OK or TRIGGERED (with reason)
- Bankroll: current vs starting, % change
- Today's P&L
- Win rate (last 7 days, only meaningful after 20+ trades)
- Open positions (max 5 shown)
- Last 10 trades with outcome
- System health: Kalshi API up/down, Binance feed up/down

Rotating tip in footer (one tip every 60 seconds):
Tips should teach Matthew:
- What the strategy is actually doing
- What each number means
- Key commands: --verify, --report, --reset-killswitch
- When to go live (7+ days positive paper P&L)
- How to resume a session (feed SESSION_HANDOFF.md to Claude)
- That .env and .pem files must never be shared
- How to read the edge metric in trade logs

═══════════════════════════════════════════════════
## COMMANDS
═══════════════════════════════════════════════════

python main.py              → Paper mode (default)
python main.py --live       → Live (needs LIVE_TRADING=true in .env)
python main.py --verify     → Test connections, exit
python main.py --report     → Print P&L summary, exit
python main.py --reset-killswitch → Reset after hard stop

streamlit run src/dashboard.py → Open dashboard manually

pytest tests/ -v           → Run all safety tests

═══════════════════════════════════════════════════
## GITHUB SETUP
═══════════════════════════════════════════════════

First thing before any code files:
git init
git add .gitignore          ← FIRST. Contains: .env, *.pem, *.key, logs/, venv/
git commit -m "init: gitignore before anything else"

Commit after each checkpoint:
"CHECKPOINT_1: auth + structure"
"CHECKPOINT_2: strategy + kill switch tested"  
"CHECKPOINT_3: dashboard live, paper mode running"

═══════════════════════════════════════════════════
## CHECKPOINT GATES — Human reviews before continuing
═══════════════════════════════════════════════════

CHECKPOINT_1 — surface after:
  ✓ Folder structure built
  ✓ .gitignore committed first
  ✓ .env.example created (no real values)
  ✓ config.yaml created
  ✓ Auth works against Kalshi demo

CHECKPOINT_2 — surface after:
  ✓ python setup/verify.py passes
  ✓ Kill switch tests pass: pytest tests/test_kill_switch.py
  ✓ Security tests pass: pytest tests/test_security.py
  ✓ python main.py runs 10 min in paper mode without crashing
  ✓ At least one trade signal logged

CHECKPOINT_3 — surface after:
  ✓ Streamlit dashboard loads at http://127.0.0.1:8501
  ✓ Tips display and rotate
  ✓ SESSION_HANDOFF.md current
  ✓ GitHub commit tagged

═══════════════════════════════════════════════════
## THE RULE
═══════════════════════════════════════════════════

Build one thing that works before building two things that don't.
When blocked: write BLOCKERS.md, surface at next checkpoint.
When something breaks: fix it before moving forward.
Conservative > clever. Working > perfect. Logged > forgotten.

═══════════════════════════════════════════════════
## CONTEXT HANDOFF — When a Claude chat hits its token limit
═══════════════════════════════════════════════════

When a Claude Code session fills up (you see "context limit" or responses slow down),
start a NEW chat and paste the following at the top:

────────────────────────────────────────
"We are resuming the polymarket-bot project.
Read these files first (in order), then continue where we left off:
1. POLYBOT_INIT.md — original build spec + progress log
2. SESSION_HANDOFF.md — current state, next actions, component status
3. BLOCKERS.md — open issues needing my input
4. CHECKPOINT_N.md — most recent completed checkpoint

Do NOT ask setup questions — the project is already built.
Resume from: [paste the 'Next action' section of SESSION_HANDOFF.md here]"
────────────────────────────────────────

Claude will read the docs, orient to current state, and pick up exactly where we left off.
The files above are kept up-to-date after every session by Claude.

WHAT CLAUDE SHOULD DO AUTOMATICALLY AT END OF EACH SESSION:
- Update SESSION_HANDOFF.md with current state and next action
- Update POLYBOT_INIT.md progress log below
- Commit new CHECKPOINT_N.md if a phase was completed
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
- src/dashboard.py: Streamlit UI at localhost:8501. Read-only. Kill switch banner,
  mode header (PAPER/LIVE), 4 key metrics, today's activity, system health,
  last 10 trades, kill switch events log, tips expander. Auto-refreshes every 30s.
- Settlement loop: background asyncio task in main.py. Polls Kalshi every 60s for
  settled markets, calls PaperExecutor.settle() for both paper and live trades.
- BLOCKERS.md: consolidated duplicate auth-failure entries into single blocker.
- SESSION_HANDOFF.md: current state documented.
Current state: All three phases built. Auth not yet verified with real keys.
Next action: Matthew sets up .env + .pem, runs python main.py --verify.
