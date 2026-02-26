# ARCHITECTURE.md — polymarket-bot
# Authoritative design document. Read before writing any src/ file.
# Derived from: INTEL.md + POLYBOT_INIT.md + Titanium patterns + ref repo audit
═══════════════════════════════════════════════════════════════════

## THE SINGLE RULE
One file = one job. A file that does two things does neither well.
If you're unsure which file owns a behavior, ask: "What is this file's job?"
If the answer has the word "and" in it, split it.

---

## FILE MAP — What each file owns (and does NOT own)

```
polymarket-bot/
│
├── main.py
│   DOES:   CLI entry point, arg parsing (--paper, --live, --verify, --report, --reset-killswitch)
│   DOES:   Wires all components together, runs the main loop
│   DOES NOT: Business logic, math, API calls, risk decisions
│
├── config.yaml                    → All tunable params (see POLYBOT_INIT.md for full spec)
├── USER_CONFIG.json               → Matthew's startup answers (read-only at runtime)
├── .env                           → Credentials only. NEVER created by code. Human fills.
├── .env.example                   → Template. Safe to commit.
│
├── setup/
│   ├── install.sh                 → Creates venv, installs deps. One command.
│   └── verify.py                  → Tests ALL connections (Kalshi demo, Binance WS). Exits with report.
│
├── src/
│   │
│   ├── auth/
│   │   ├── kalshi_auth.py
│   │   │   DOES:   Load .pem key, sign requests with RSA-PSS SHA256
│   │   │   DOES:   Build KALSHI-ACCESS-KEY/SIGNATURE/TIMESTAMP headers
│   │   │   DOES NOT: Make HTTP calls, know about markets, touch config
│   │   │   STOLEN FROM: refs/kalshi-btc/kalshi_client.py (_sign + _auth_headers)
│   │   │
│   │   └── poly_auth.py
│   │       DOES:   HMAC-SHA256 L2 signing for Polymarket (inactive until off waitlist)
│   │       DOES NOT: Make HTTP calls, know about markets
│   │       STOLEN FROM: refs/poly-official/py_clob_client/signing/hmac.py
│   │
│   ├── platforms/
│   │   ├── kalshi.py
│   │   │   DOES:   All Kalshi REST calls (markets, orders, fills, positions, balance)
│   │   │   DOES:   Rate limiting (read: 10/s, write: 5/s), retry with backoff
│   │   │   DOES:   Raises KalshiAPIError on 4xx/5xx
│   │   │   DOES NOT: Auth logic (delegates to kalshi_auth.py), strategy, risk
│   │   │   STOLEN FROM: refs/kalshi-btc/kalshi_client.py (full class)
│   │   │
│   │   └── polymarket.py
│   │       DOES:   Polymarket CLOB API calls (inactive until off waitlist)
│   │       DOES NOT: Auth (delegates to poly_auth.py), strategy, risk
│   │       STATUS: Built now, enabled=False in config. Zero cost.
│   │
│   ├── data/
│   │   ├── binance.py
│   │   │   DOES:   BTC spot price via public Binance WebSocket
│   │   │   DOES:   Maintains rolling 60-second price window for move detection
│   │   │   DOES NOT: Strategy logic, know about Kalshi, place orders
│   │   │   URL: wss://stream.binance.com:9443/ws/btcusdt@trade
│   │   │
│   │   └── whale_tracker.py
│   │       DOES:   Polymarket leaderboard scraping (inactive until off waitlist)
│   │       STATUS: Stub. Enable when Polymarket access confirmed.
│   │
│   ├── strategies/
│   │   ├── base.py
│   │   │   DOES:   Abstract Strategy class. All strategies inherit from this.
│   │   │   DEFINES: generate_signal() → Signal | None
│   │   │
│   │   ├── btc_lag.py
│   │   │   DOES:   BTC 15-min lag signal logic (PRIMARY strategy)
│   │   │   LOGIC:  1. BTC moved >0.4% on Binance in last 60s?
│   │   │             2. Kalshi YES/NO price hasn't moved to match yet (>5¢ gap)?
│   │   │             3. >5 minutes remain in current 15-min window?
│   │   │             4. Edge > 8%?
│   │   │             → Signal(side, edge_pct, confidence)
│   │   │   DOES NOT: Know about sizing, risk, order placement
│   │   │
│   │   └── whale_copy.py
│   │       DOES:   Copy qualified Polymarket whales (inactive until off waitlist)
│   │       STATUS: Built, enabled=False. Activates with Polymarket.
│   │
│   ├── risk/
│   │   ├── kill_switch.py
│   │   │   DOES:   All hard stops. Every trade must pass check_order_allowed() first.
│   │   │   TRIGGERS:
│   │   │     - Single trade > $5 OR > 5% bankroll (lower applies)
│   │   │     - Today's P&L loss > 15% starting bankroll
│   │   │     - 5 consecutive losses → 2hr cooling period (soft, auto-resets)
│   │   │     - Hourly trades > 15 → rate limit pause
│   │   │     - 3+ consecutive auth failures → halt, write BLOCKERS.md
│   │   │     - Total bankroll loss > 30% → HARD STOP (manual reset required)
│   │   │     - Bankroll < $20 → HARD STOP
│   │   │     - kill_switch.lock exists at startup → refuse to start
│   │   │   ON HARD STOP: cancel all orders, write kill_switch.lock,
│   │   │     write KILL_SWITCH_EVENT.log, print reset instructions
│   │   │   STOLEN FROM: refs/kalshi-btc/risk.py (RiskManager class structure)
│   │   │
│   │   └── sizing.py
│   │       DOES:   Calculate position size given signal and current bankroll
│   │       USES:   Stage system + Kelly (0.25x fractional) + hard caps
│   │       STAGE CAPS:
│   │         Stage 1 ($0–$100):    max $5.00/bet, 5% bankroll
│   │         Stage 2 ($100–$250):  max $10.00/bet, 5% bankroll
│   │         Stage 3 ($250+):      max $15.00/bet, 4% bankroll
│   │       RULE: Always use lower of (stage cap, kelly recommendation, hard cap)
│   │       STOLEN FROM: refs/poly-apex/core/kelly.py (Kelly formula + caps)
│   │
│   ├── execution/
│   │   ├── paper.py
│   │   │   DOES:   Simulated trade execution. Records to DB as paper trades.
│   │   │   DOES:   Realistic fill simulation (uses Kalshi orderbook spread)
│   │   │   DOES NOT: Call any Kalshi order endpoint
│   │   │
│   │   └── live.py
│   │       DOES:   Real order placement via kalshi.py
│   │       GUARD:  Checks LIVE_TRADING env var AND --live flag. Both required.
│   │       GUARD:  First run prints giant warning + requires Enter to confirm
│   │       DOES NOT: Bypass kill switch under any circumstance
│   │
│   ├── db.py
│   │   DOES:   SQLite persistence (trades, positions, P&L, bankroll snapshots)
│   │   TABLES: trades, daily_pnl, bankroll_history, kill_switch_events
│   │   DOES NOT: Business logic, just read/write
│   │
│   └── dashboard.py
│       DOES:   Streamlit UI (localhost:8501 only)
│       SHOWS:  Mode banner, kill switch status, bankroll, today's P&L,
│               win rate, open positions, last 10 trades, system health, tips
│       DOES NOT: Business logic, API calls, risk decisions
│
├── tests/
│   ├── test_security.py           → Red team tests — run FIRST, must pass 100%
│   └── test_kill_switch.py        → Kill switch trigger tests — must pass 100%
│
└── logs/
    ├── trades/                    → One JSON file per day
    └── errors/                    → Exception tracebacks
```

---

## DATA FLOW — How a trade happens

```
Binance WS (BTC price) ──→ btc_lag.py ──→ Signal?
                                              │
                                         sizing.py (Kelly + stage caps)
                                              │
                                         kill_switch.py (check_order_allowed)
                                              │
                                    ┌─────────┴──────────┐
                                 PAPER                  LIVE
                                paper.py              live.py
                                    │                    │
                                   db.py ←──────────────┘
                                    │
                               dashboard.py
```

Every component between Signal and db.py is synchronous.
Kill switch check is ALWAYS the last gate before any order action.

---

## KEY DESIGN DECISIONS

### 1. Async for I/O, sync for risk
All API calls (Kalshi, Binance WS) are async (aiohttp/websockets).
All risk checks are synchronous — no await in kill_switch.py.
Reason: Kill switch must be instant and deterministic. Cannot await while a trade is at risk.

### 2. Kill switch state is persisted to file
`kill_switch.lock` exists on disk when triggered. Checked at startup.
This survives process restarts. Cannot be bypassed by restarting the bot.
Only `python main.py --reset-killswitch` removes it (with confirmation).

### 3. Paper mode is the default and cannot be accidentally overridden
`LIVE_TRADING=false` in .env by default.
Even if someone sets `LIVE_TRADING=true`, `--live` flag is also required at CLI.
Even with both, first live run prints a warning and requires interactive confirmation.

### 4. Credentials never in code
`kalshi_auth.py` reads path from env, loads file, never stores key in memory longer than needed.
Never logged. Never printed. Scanning for key patterns is part of `test_security.py`.

### 5. Config drives everything, code enforces minimums
`config.yaml` holds tunable params. But code enforces hard minimums that config cannot override.
Example: config says `max_single_trade_usd: 5.00`. Code rejects anything above $5 regardless
of what config says. The floor is in code, not config.

### 6. One approved URL per module
`kalshi.py` can ONLY reach demo-api.kalshi.co or trading-api.kalshi.com.
`binance.py` can ONLY reach stream.binance.com.
`polymarket.py` can ONLY reach clob.polymarket.com.
`test_security.py` verifies this by checking all outgoing URLs.

### 7. Polymarket built now, enabled=False
`polymarket.py` and `whale_copy.py` are implemented but gated behind `platforms.polymarket.enabled: false`.
Zero risk. When Matthew gets off the waitlist: set enabled=true in config, add .env keys, done.

---

## ANTI-PATTERNS — DO NOT DO THESE

✗ Don't add `await` inside kill_switch.py — risk checks must be synchronous
✗ Don't log anything from kalshi_auth.py except "auth initialized" (never log key contents)
✗ Don't catch KalshiAPIError silently — log it and let kill_switch handle auth failures
✗ Don't put bankroll calculation inside strategy.py — that's sizing.py's job
✗ Don't call live.py from paper.py or vice versa — they are completely separate executors
✗ Don't write files outside /Users/matthewshields/Projects/polymarket-bot/ — period
✗ Don't import kalshi.py from auth/ — auth has no knowledge of API structure (circular import guard)
✗ Don't use assert for validation — use ValueError/RuntimeError (assert can be disabled with -O)

---

## STARTUP SEQUENCE (what main.py orchestrates)

1. Check for kill_switch.lock → refuse to start if exists
2. Load .env → fail loud if KALSHI_API_KEY_ID or KALSHI_PRIVATE_KEY_PATH missing
3. Load config.yaml → fail loud if required fields missing
4. Load USER_CONFIG.json → merge with config
5. Initialize DB (create tables if not exist)
6. Initialize KalshiClient (loads key, tests connection to demo/live)
7. Initialize BinanceFeed (opens WebSocket)
8. Initialize RiskManager (loads bankroll from DB)
9. Check --verify flag → if set, print status report and exit
10. Print startup banner (mode: PAPER or LIVE, bankroll, stage, kill switch status)
11. If LIVE mode: print warning, require interactive confirmation
12. Start main loop

---

## PACKAGES NEEDED (requirements.txt)

aiohttp>=3.9          # Async HTTP for Kalshi
websockets>=12.0      # Binance price feed
cryptography>=41.0    # RSA-PSS signing
python-dotenv>=1.0    # .env loading
pyyaml>=6.0           # config.yaml parsing
pydantic-settings>=2  # Config validation (Polymarket auth pattern)
streamlit>=1.32       # Dashboard
pytest>=8.0           # Tests
pytest-asyncio>=0.23  # Async test support
eth-account>=0.10     # Polymarket EIP-712 signing (for when off waitlist)
