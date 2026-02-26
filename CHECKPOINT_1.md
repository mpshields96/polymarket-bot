# CHECKPOINT_1 — Phase 1 Complete: Foundation + Risk System
# Date: 2026-02-25
# Gate: Human reviews before Phase 2 (platform clients + strategy) begins
═══════════════════════════════════════════════════════════════════

## STATUS: READY FOR REVIEW

---

## ✅ COMPLETED THIS PHASE

### Infrastructure
- [x] Full folder structure created (src/auth, platforms, data, strategies, risk, execution, setup, tests, logs)
- [x] requirements.txt — pinned versions, all packages verified
- [x] config.yaml — full config per spec (Kalshi demo, Polymarket disabled, all risk params)
- [x] .env.example — template with all required vars, LIVE_TRADING=false by default
- [x] setup/install.sh — venv creation, dependency install, sanity checks

### Auth
- [x] src/auth/kalshi_auth.py — RSA-PSS SHA256 signing stolen verbatim from kalshi-btc
  - Loads .pem from path in env var (never hardcodes)
  - Signs: `str(timestamp_ms) + METHOD.upper() + path_without_query_string`
  - Returns: KALSHI-ACCESS-KEY, KALSHI-ACCESS-SIGNATURE, KALSHI-ACCESS-TIMESTAMP headers
  - Never logs key contents. Only logs "key loaded (path=X, bits=N)"
  - No network imports at module level

### Verification
- [x] setup/verify.py — 7 checks before bot start:
  1. .env loaded + required vars present
  2. PEM file exists + is valid RSA key
  3. Auth headers generate correctly (no network)
  4. Kalshi demo API reachable (GET /exchange/status)
  5. Authenticated Kalshi demo request (GET /portfolio/balance)
  6. Binance WebSocket BTC price received
  7. kill_switch.lock absent

### Risk System
- [x] src/risk/kill_switch.py — all 8 triggers per spec:
  - SOFT (auto-reset): single trade >$5 or >5% bankroll, daily loss >15%, 5 consecutive losses (2hr cooling), hourly trades >15
  - HARD (manual reset): 3+ auth failures (also writes BLOCKERS.md), total loss >30%, bankroll ≤$20, lock file at startup
  - On hard stop: writes kill_switch.lock + KILL_SWITCH_EVENT.log, prints reset instructions
  - All synchronous (no await)
  - check_order_allowed() is the single gate for every trade

- [x] src/risk/sizing.py — Kelly + stage system stolen from poly-apex:
  - Stage 1 ($0–$100): max $5.00, 5% bankroll
  - Stage 2 ($100–$250): max $10.00, 5% bankroll
  - Stage 3 ($250+): max $15.00, 4% bankroll
  - 0.25x fractional Kelly, absolute cap $15 regardless
  - Returns None for: edge < 8%, negative Kelly, zero/negative inputs

### Tests
- [x] tests/test_kill_switch.py — 35 tests, all triggers covered
- [x] tests/test_security.py — 24 tests, red team checks

**Test result: 59/59 PASSING ✅**

---

## 🔴 FIXES MADE DURING TESTING

Four bugs caught and fixed before this checkpoint:

| Bug | Fix |
|-----|-----|
| Bankroll floor check ran after pct cap check — wrong order | Moved bankroll floor check BEFORE pct cap check |
| `< HARD_MIN_BANKROLL_USD` (strict less-than) | Changed to `<= HARD_MIN_BANKROLL_USD` (at $20 = stop) |
| `minutes_remaining < 5` | Changed to `<= 5` (block at exactly 5 min remaining) |
| test_security.py scanned itself for dangerous paths | Added self-exclusion for the test file |

All documented in ERRORS_AND_FIXES.md.

---

## 📋 WHAT'S BEEN VERIFIED

- `python -m pytest tests/` → 59/59 PASS
- No hardcoded credentials anywhere in codebase (test confirms)
- .env, *.pem, *.key all gitignored (test confirms)
- kill_switch.lock and logs/ gitignored (test confirms)
- No writes possible outside project folder (test confirms)
- Auth module doesn't log key contents (test confirms)
- Kelly math correct: thin edge → None, negative Kelly → None, stage caps enforced

---

## 🏗️ PHASE 2 — What happens next (pending your approval)

All platform + strategy code. Order:

1. **src/platforms/kalshi.py** — Async Kalshi client stolen from kalshi-btc
   - Markets, orders, fills, positions, balance
   - Rate limiting (read: 10/s, write: 5/s), retry with exponential backoff
   - Raises KalshiAPIError on 4xx/5xx

2. **src/data/binance.py** — BTC WebSocket price feed
   - Public stream: wss://stream.binance.com:9443/ws/btcusdt@trade
   - Rolling 60-second price window for move detection

3. **src/strategies/base.py + btc_lag.py** — Primary trading strategy
   - Signal: BTC moved >0.4% in 60s + Kalshi gap >5¢ + >5min remaining + edge >8%
   - Returns Signal(side, edge_pct, confidence) or None

4. **src/execution/paper.py** — Paper trade executor
   - Simulated fills, records to DB, no live API calls

5. **src/execution/live.py** — Live trade executor
   - Requires LIVE_TRADING=true AND --live flag
   - First run requires interactive confirmation

6. **src/db.py** — SQLite persistence
   - Tables: trades, daily_pnl, bankroll_history, kill_switch_events

7. **main.py** — CLI entry point + main loop

8. **CHECKPOINT_2** → surface to Matthew

---

## HOW TO PROCEED

Reply **"continue"** to begin Phase 2.

Or reply with corrections/concerns before I write any code.

---

## QUICK REFERENCE (for running tests yourself)

```bash
# Activate venv
source venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run verification (needs .env + kalshi_private_key.pem)
python setup/verify.py
```
