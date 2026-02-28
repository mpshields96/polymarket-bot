# POLYBOT — BUILD INSTRUCTIONS + LIVE STATUS
# For: Claude Code Desktop App | Owner: Matthew
# Read this fully before doing anything.

═══════════════════════════════════════════════════
## CURRENT STATUS — READ THIS FIRST (updated each session)
═══════════════════════════════════════════════════

BUILD COMPLETE: All phases done. 289/289 tests passing.
verify.py: 18/18 ✅. 8 trading loops running in paper mode.
Commit: c61f3e3 (Session 15 — NWS ensemble, dedup, bet cap)

WHAT WORKS:
  ✅ Kalshi auth (api.elections.kalshi.com — old URLs deprecated)
  ✅ BTC + ETH feeds live — Binance.US @bookTicker, ~100 ticks/min
  ✅ [trading]        btc_lag_v1             — 0s stagger, 84.1% backtest
  ✅ [eth_trading]    eth_lag_v1             — 7s stagger, paper-only
  ✅ [drift]          btc_drift_v1           — 15s stagger, sensitivity=800, Brier=0.22
  ✅ [eth_drift]      eth_drift_v1           — 22s stagger, paper-only
  ✅ [btc_imbalance]  orderbook_imbalance_v1 — 29s stagger, paper-only
  ✅ [eth_imbalance]  eth_imbalance_v1       — 36s stagger, paper-only
  ✅ [weather]        weather_forecast_v1    — 43s stagger, ENSEMBLE (Open-Meteo+NWS)
  ✅ [fomc]           fomc_rate_v1           — 51s stagger, 30-min poll, paper-only
  ✅ Kill switch shared by all 8 loops, all triggers wired
  ✅ Settlement loop wired to kill switch (record_win/record_loss)
  ✅ Dashboard at localhost:8501 reads data/polybot.db
  ✅ SIGTERM/SIGHUP: clean shutdown on kill PID
  ✅ Position dedup: has_open_position() prevents duplicate bets on same market
  ✅ Daily bet cap: 5 bets/strategy/day prevents btc_drift tax churn
  ✅ User-Agent header on all Kalshi API calls

OPEN:
  No paper signal has fired yet. Bot needs to run during active BTC trading.
  btc_drift fires first (needs only ~0.15-0.3% drift from market open).
  btc_lag needs ~0.65% BTC move in 60s (rare in calm overnight market).
  Weather: HIGHNY markets only exist weekdays.
  FOMC: active 14 days before each meeting — next window opens March 5, 2026.

NEXT ACTION:
  python main.py — watch all 8 loops start up within 51s.
  First expected signal: "[drift] Signal: BUY YES/NO ..." (fires on any BTC drift)
  To lower bar if no signal: lower min_edge_pct in config.yaml (strategy.btc_lag section)

DO NOT enable live trading until:
  ✓ Both btc_lag + btc_drift log signals in paper mode
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
  Notes: Matthew is a doctor, new baby. Needs this profitable. Conservative, not clever.

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
    https://api.elections.kalshi.com          ← only valid Kalshi URL
    wss://stream.binance.us:9443/ws           ← BTC/ETH feeds (Binance.US only)
    https://api.open-meteo.com/v1/forecast    ← weather feed (free, no key)
    https://fred.stlouisfed.org/graph/fredgraph.csv  ← FRED economic data (free, no key)
    NOTE: wss://stream.binance.com is blocked in the US (HTTP 451). Use Binance.US only.
✓ All pip installs go into venv/ only
✓ Default mode: PAPER (PaperExecutor)
✓ Live trading: requires LIVE_TRADING=true in .env AND --live flag AND typing CONFIRM

═══════════════════════════════════════════════════
## WHAT'S ALREADY BUILT — DO NOT REBUILD
═══════════════════════════════════════════════════

Everything below exists and is tested. Read the files, don't rewrite them.

PHASE 1 — Foundation + Risk
  src/auth/kalshi_auth.py       RSA-PSS signing. load_from_env() loads .env.
  src/risk/kill_switch.py       8 triggers, kill_switch.lock, --reset-killswitch.
  src/risk/sizing.py            Kelly criterion at 0.25x, stage caps ($5/$10/$15).
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
  src/data/weather.py           Open-Meteo GFS daily max temp (free, no key, 30-min cache)
  src/data/fred.py              FRED CSV: DFF, DGS2, CPIAUCSL (free, no key, 1-hr cache)
  src/db.py                     SQLite persistence: trades, bankroll, kill events.
  src/execution/paper.py        PaperExecutor: fill + settle simulation.
  src/execution/live.py         LiveExecutor: real order placement (locked behind flag).
  main.py                       CLI + 8 async trading loops + settlement loop.
  scripts/backtest.py           30-day BTC drift calibration via Binance.US klines API.

PHASE 3 — Dashboard + Settlement
  src/dashboard.py              Streamlit UI at localhost:8501. Read-only.
  main.py settlement_loop()     Background asyncio task, polls Kalshi every 60s.

TESTS — 257/257 passing
  tests/conftest.py             Kill switch lock cleanup fixture (session-scoped).
  tests/test_db.py              DB layer + bankroll + win_rate tests.
  tests/test_kill_switch.py     Kill switch: all 8 triggers + settlement integration.
  tests/test_security.py        Security constraint tests.
  tests/test_strategy.py        BTCLagStrategy gate + signal tests.
  tests/test_drift_strategy.py  BTCDriftStrategy: sigmoid gates, signal fields.
  tests/test_eth_support.py     ETH feed, name_override, ETH factory names.
  tests/test_orderbook_imbalance.py  VPIN-lite: depth gates, factory, signal direction.
  tests/test_weather_strategy.py     WeatherForecastStrategy: bracket parsing, normal CDF, gates.
  tests/test_fomc_strategy.py        FOMCRateStrategy: yield curve model, ticker parsing, calendar.

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

8. PYTEST GUARD: kill_switch._write_blockers() skips when PYTEST_CURRENT_TEST is set.
   Prevents test runs from polluting BLOCKERS.md.

9. BOT.PID: Written at startup, removed on clean shutdown. If it exists after a crash,
   delete it before restarting: rm bot.pid

10. SETTLEMENT LOOP: Must receive kill_switch param and call record_win/record_loss.
    Otherwise consecutive-loss and total-loss hard stops are dead code.

11. LIVE MODE: Requires --live flag + LIVE_TRADING=true in .env + type CONFIRM at runtime.
    All three gates required. Absence of any one falls back to paper silently.

12. WEATHER MARKETS: HIGHNY markets only exist weekdays. Weather loop logs
    "No open HIGHNY markets" on weekends — expected, not a bug.

13. FOMC STRATEGY: Only active in 14-day window before each 2026 meeting.
    Outside that window: timing gate blocks all signals (DEBUG log).
    CME FedWatch is blocked from server IPs. Use FRED CSV instead (free, no key).
    FRED CSV endpoint: fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}

14. ETH STRATEGIES: KXETH15M confirmed active. ETH lag/drift use name_override param
    to store eth_lag_v1/eth_drift_v1 in DB (not btc_lag_v1).

15. ALL GENERATE_SIGNAL() SKIP PATHS LOG AT DEBUG: Loop appears silent when no signal.
    Added INFO heartbeat "[trading] Evaluating N market(s)" to confirm loop alive.

═══════════════════════════════════════════════════
## PROJECT STRUCTURE (actual, as built)
═══════════════════════════════════════════════════

polymarket-bot/
├── POLYBOT_INIT.md              ← This file. The source of truth.
├── SESSION_HANDOFF.md           ← Current state + exact next action (updated each session)
├── CLAUDE.md                    ← Claude session startup instructions
├── BLOCKERS.md
├── config.yaml                  ← All strategy params, risk limits, series tickers
├── .env                         ← REAL credentials (gitignored)
├── .env.example                 ← Template (safe to commit)
├── .gitignore
├── requirements.txt
├── setup/
│   └── verify.py                ← Pre-flight checker (18 checks)
├── scripts/
│   └── backtest.py              ← 30-day BTC drift calibration
├── src/
│   ├── auth/
│   │   └── kalshi_auth.py       ← RSA-PSS signing
│   ├── platforms/
│   │   └── kalshi.py            ← Async REST client, Market/OrderBook types
│   ├── data/
│   │   ├── binance.py           ← BTC+ETH WebSocket feeds (Binance.US)
│   │   ├── weather.py           ← Open-Meteo GFS daily max temp feed
│   │   └── fred.py              ← FRED CSV: DFF, DGS2, CPIAUCSL
│   ├── strategies/
│   │   ├── base.py              ← BaseStrategy + Signal dataclass
│   │   ├── btc_lag.py           ← Primary: 4-gate BTC momentum (+ ETH factory)
│   │   ├── btc_drift.py         ← Sigmoid drift-from-open (+ ETH factory)
│   │   ├── orderbook_imbalance.py ← VPIN-lite YES/NO depth ratio (BTC + ETH)
│   │   ├── weather_forecast.py  ← GFS forecast vs HIGHNY temperature markets
│   │   └── fomc_rate.py         ← Yield curve vs KXFEDDECISION markets
│   ├── execution/
│   │   ├── paper.py             ← PaperExecutor (fill + settle)
│   │   └── live.py              ← LiveExecutor (locked behind --live flag)
│   ├── risk/
│   │   ├── kill_switch.py       ← 8 triggers + hard stop logic
│   │   └── sizing.py            ← Kelly 0.25x, stage caps
│   ├── db.py                    ← SQLite: trades, bankroll, kill events
│   └── dashboard.py             ← Streamlit app (localhost:8501)
├── tests/
│   ├── conftest.py              ← Kill switch lock cleanup
│   ├── test_kill_switch.py
│   ├── test_security.py
│   ├── test_db.py
│   ├── test_strategy.py
│   ├── test_drift_strategy.py
│   ├── test_eth_support.py
│   ├── test_orderbook_imbalance.py
│   ├── test_weather_strategy.py
│   └── test_fomc_strategy.py
├── logs/
│   ├── trades/
│   └── errors/
├── data/                        ← Auto-created at startup
│   └── polybot.db               ← SQLite (gitignored)
└── main.py                      ← CLI: --verify --live --report --reset-killswitch

═══════════════════════════════════════════════════
## COMMANDS
═══════════════════════════════════════════════════

python main.py                    → Paper mode (8 strategies, default)
python main.py --live             → Live (needs LIVE_TRADING=true in .env + CONFIRM)
python main.py --verify           → Pre-flight check (18/18)
python main.py --report           → Print P&L summary, exit
python main.py --reset-killswitch → Reset after hard stop (pipe RESET)

streamlit run src/dashboard.py   → Dashboard at http://127.0.0.1:8501

source venv/bin/activate && python -m pytest tests/ -v  → Run all 257 tests
python scripts/backtest.py --days 30  → 30-day BTC drift calibration

echo "RESET" | python main.py --reset-killswitch  → Reset kill switch

═══════════════════════════════════════════════════
## KILL SWITCH — 8 triggers
═══════════════════════════════════════════════════

1. Any single trade would exceed $5 OR 5% of current bankroll
2. Today's P&L loss > 15% of starting bankroll (soft stop, resets midnight)
3. 5 consecutive losses → 2-hour cooling off period
4. Total bankroll loss > 30% → HARD STOP (requires manual reset)
5. Bankroll drops below $20 → HARD STOP
6. kill_switch.lock file exists at startup → refuse to start
7. 3 consecutive auth failures → halt
8. Rate limit exceeded → pause

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
  min_edge_pct: 0.08 — needs ~0.65% BTC move in 60s (binding constraint)
  To lower bar: reduce min_edge_pct in config.yaml (NOT min_btc_move_pct)

btc_drift / eth_drift:
  min_drift_pct: 0.05, min_edge_pct: 0.05 — fires at ~0.15-0.3% drift from open
  30-day backtest: 69% directional accuracy, Brier=0.2330

orderbook_imbalance (BTC + ETH):
  min_imbalance_ratio: 0.65 — VPIN-lite: >65% one side = informed money
  min_total_depth: 50 — skip thin markets

weather_forecast (NYC HIGHNY):
  Normal distribution model: N(forecast_temp_f, 3.5°F) vs Kalshi YES price
  min_edge_pct: 0.05, min_minutes_remaining: 30
  Only weekdays; Open-Meteo API is free, no key

fomc_rate (KXFEDDECISION):
  Yield curve: DGS2 - DFF → P(hold/cut/hike) model (4 regimes)
  CPI adjustment: ±8% shift on acceleration/deceleration
  Only active 14 days before each 2026 FOMC date
  Current: DFF=3.64%, DGS2=3.90%, spread=+0.26% → hold-biased
  Next meeting: March 19, 2026 → active from March 5

═══════════════════════════════════════════════════
## CONTEXT HANDOFF — Paste into new Claude chat
═══════════════════════════════════════════════════

────────────────────────────────────────
We are resuming the polymarket-bot project. Read these files first (in order), then continue:
1. POLYBOT_INIT.md — build spec, current status, all known gotchas
2. SESSION_HANDOFF.md — current state and exact next action

Do NOT ask setup questions. The bot is fully built, tested, and auth is working.

CURRENT STATE (as of 2026-02-28, Session 14):
- 257/257 tests passing. verify.py 18/18.
- 8 trading loops running in paper mode:
    0s  btc_lag_v1              — BTC 15-min momentum
    7s  eth_lag_v1              — ETH 15-min momentum (paper)
   15s  btc_drift_v1            — BTC drift from open (paper)
   22s  eth_drift_v1            — ETH drift (paper)
   29s  orderbook_imbalance_v1  — VPIN-lite YES/NO depth (paper)
   36s  eth_imbalance_v1        — ETH orderbook (paper)
   43s  weather_forecast_v1     — Open-Meteo GFS vs HIGHNY Kalshi markets (paper, 5-min poll)
   51s  fomc_rate_v1            — FRED yield curve vs KXFEDDECISION (paper, 30-min poll)
- FOMC strategy active window: 14 days before each 2026 meeting → next: March 5-19
- LIVE_TRADING=false — paper mode only. No real orders possible without --live + .env change.
- GitHub: main branch, sessions 1-9 committed (bf60715); sessions 10-14 uncommitted.
- Polymarket is geo-blocked in the US — Kalshi is the correct platform.

RESUME FROM:
Run `python main.py` and watch all 8 loops start within 51 seconds.
Expected output:
  "[trading] Evaluating 1 market(s): ['KXBTC15M-...']"       ← t=0s, every 30s
  "[eth_trading] Evaluating 1 market(s): ['KXETH15M-...']"   ← t=7s
  "[drift] Evaluating 1 market(s): ['KXBTC15M-...']"         ← t=15s
  "[weather] No open HIGHNY markets" OR forecast fetch        ← t=43s, every 5min
  "[fomc] No open KXFEDDECISION markets" (until March 5)     ← t=51s, every 30min

KEY FACTS:
- Kalshi API: api.elections.kalshi.com (old URLs dead)
- BTC/ETH feeds: Binance.US wss://stream.binance.us:9443 (@bookTicker, NOT @trade)
  (binance.com HTTP 451 geo-blocked in US. @trade has near-zero Binance.US volume)
- Balance: $75 confirmed. Starting bankroll in config.yaml: $50.
- Weather data: Open-Meteo free API (no key), HIGHNY = NYC daily high-temp markets
- FOMC data: FRED CSV endpoint free (DFF, DGS2, CPIAUCSL — no API key required)
- Dashboard: streamlit run src/dashboard.py → localhost:8501
- Kill switch reset: echo "RESET" | python main.py --reset-killswitch
- Next live trading criteria: 7+ paper days positive P&L from btc_lag or btc_drift
────────────────────────────────────────

═══════════════════════════════════════════════════
## PROGRESS LOG — Updated by Claude at end of each session
═══════════════════════════════════════════════════

### 2026-02-25 — Session 1 (CHECKPOINT_0)
Completed: Project scaffold, gitignore, USER_CONFIG.json, log files, reference repo intel.

### 2026-02-25 — Session 2 (CHECKPOINT_1 + CHECKPOINT_2)
Completed: Auth (RSA-PSS), kill switch, sizing, verify.py, Kalshi REST client,
Binance feed, btc_lag strategy, SQLite DB, paper/live executors, main.py CLI.
Result: CHECKPOINT_1 + CHECKPOINT_2 committed and pushed.

### 2026-02-25 — Session 3 (CHECKPOINT_3)
Completed: Streamlit dashboard, settlement loop, db bug fixes, 107/107 tests.
Result: CHECKPOINT_3 committed and pushed.

### 2026-02-26 — Session 4 (API fixes + first bot run)
Completed: .env created, verify.py 18/18, Kalshi URL fix, balance field fix,
market price field fix, data/ dir, bot runs in paper mode. Balance $75 confirmed.

### 2026-02-26 — Session 5 (trading loop confirmed + market catalog)
Completed: Series ticker bug fix (btc_15min→KXBTC15M), INFO heartbeat added,
KXETH15M confirmed active. 107/107 tests.

### 2026-02-26 — Session 6 (Binance.US bookTicker fix + feed verified)
Completed: @trade→@bookTicker switch, conftest.py lock cleanup, feed verified live
(49 ticks in 30s, price=$67,474). 107/107 tests.

### 2026-02-27 — Session 7 (safeguards + observability)
Completed: PID lock, near-miss INFO log (YES/NO prices + time remaining),
pytest BLOCKERS.md guard, dashboard DB path fix, data/ auto-create, SIGTERM handler.
107/107 tests.

### 2026-02-27 — Session 8 (code review critical fixes)
Completed: Kill switch wired to settlement loop, live CONFIRM prompt,
PID PermissionError fix, dead params removed, stale threshold 10s→35s, +5 tests.
117/117 tests.

### 2026-02-27 — Session 9 (minor fixes + commit + push)
Completed: Dead price_key var removed, markets[] guard, claude/ gitignored.
Committed sessions 5-9 as 067a723. 117/117 tests.

### 2026-02-28 — Session 10 (observability + security audit)
Completed: CancelledError fix (SIGTERM clean shutdown), enhanced near-miss log
(adds YES/NO prices + time remaining). Security audit passed. 117/117 tests.

### 2026-02-28 — Session 11 (btc_drift strategy + dual loop)
Completed: BTCDriftStrategy (sigmoid model), test_drift_strategy.py (20 tests),
dual [trading]+[drift] loops, main.py loop_name+initial_delay_sec params.
137/137 tests.

### 2026-02-28 — Session 12 (ETH feed + 4 loops + backtest)
Completed: ETH feed (ethusdt@bookTicker), name_override on strategies,
eth_lag_v1 + eth_drift_v1, near-miss INFO log in btc_drift, scripts/backtest.py
(30-day test: 69% accuracy, Brier=0.2330). 4 loops staggered 0/7/15/22s.
149/149 tests.

### 2026-02-28 — Session 13 (orderbook imbalance + weather forecast)
Completed:
- orderbook_imbalance_v1 (VPIN-lite YES/NO bid depth ratio) + eth variant
- weather_forecast_v1: Open-Meteo GFS vs Kalshi HIGHNY NYC temperature markets
- WeatherFeed (src/data/weather.py): free API, 30-min cache
- Normal distribution model: N(forecast, 3.5°F) → P(temp in bracket)
- 7 loops total (0/7/15/22/29/36/43s), 212/212 tests.

### 2026-02-28 — Session 14 (FOMC rate strategy + FRED feed)
Completed:
- FREDFeed (src/data/fred.py): DFF (3.64%), DGS2 (3.90%), CPIAUCSL — free CSV, no key
- fomc_rate_v1: yield_spread=DGS2-DFF → P(hold/cut/hike) model + CPI adjustment
- 2026 FOMC calendar hardcoded (8 meetings); only fires 14 days before each
- fomc_loop() in main.py: 30-min poll, 51s stagger
- 8 loops total (0/7/15/22/29/36/43/51s), 257/257 tests.

═══════════════════════════════════════════════════
## THE RULE
═══════════════════════════════════════════════════

Build one thing that works before building two things that don't.
When blocked: write BLOCKERS.md, surface at next checkpoint.
When something breaks: fix it before moving forward.
Conservative > clever. Working > perfect. Logged > forgotten.
