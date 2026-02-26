# INTEL.md — Reference Repo Analysis
# Phase 0 intelligence gathering. Read before writing any code.
# Sources: refs/kalshi-btc, refs/kalshi-interface, refs/poly-gabagool,
#          refs/poly-apex, refs/poly-official, titanium-v36 (read-only)
═══════════════════════════════════════════════════════════════════

## REPO VERDICTS AT A GLANCE

| Repo | Quality | What to steal | What to avoid |
|------|---------|---------------|---------------|
| kalshi-btc | 9/10 | Auth, client, risk manager, rate limiter | Nothing — this is the primary ref |
| kalshi-interface | 6/10 | Fee calc, position tracking pattern | Auth signing (query-param bug) |
| poly-apex | 8.5/10 | Kelly criterion, executor pattern | Password zero-fill gap |
| poly-gabagool | 8/10 | Pydantic config, risk manager | SOCKS5 auth in URL |
| poly-official | 9/10 | HMAC signing, L1/L2 auth pattern | Assertions instead of exceptions |
| titanium-v36 | 10/10 | Architecture patterns, one-file-one-job, session state | Betting logic (wrong domain) |

---

## 1. KALSHI AUTH — STEAL THIS VERBATIM

**Source:** `refs/kalshi-btc/kalshi_client.py` lines 152–182
**Attribution comment to add:** `# Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot`

The signing logic is correct and battle-tested:

```python
# Message format: timestamp_ms + METHOD + path_without_query
def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
    path_clean = path.split("?")[0]          # strip query params
    message = (timestamp_ms + method + path_clean).encode("utf-8")
    signature = self._private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")

# Headers to send on every request:
# KALSHI-ACCESS-KEY: api_key_id
# KALSHI-ACCESS-SIGNATURE: base64(rsa-pss signature)
# KALSHI-ACCESS-TIMESTAMP: unix ms as string
```

**Key loading:** `serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())`

**DO NOT steal kalshi-interface auth** — it has a query-param bug where params are included in the
request but excluded from the signature, causing 401s on paginated GET requests.

---

## 2. KALSHI CLIENT — STEAL THE STRUCTURE

**Source:** `refs/kalshi-btc/kalshi_client.py` — steal the full class structure

What's excellent:
- Async aiohttp client with session lifecycle (start/close)
- Separate read/write rate limiters (AsyncRateLimiter token bucket)
- Retry with exponential backoff: 429 and 5xx → wait 2^attempt seconds (max 8s)
- 10-second request timeout
- Raises KalshiAPIError on 4xx/5xx instead of silent failures
- Dataclasses for Market, Order, Fill, Position, Balance — steal all of them
- `client_order_id` = UUID for idempotency on order creation

**Key Kalshi API facts (from the code):**
- Prices are in CENTS (0–100), not decimals
- YES bid at X cents = NO ask at (100-X) cents (binary market symmetry)
- Orderbook returns `yes` and `no` arrays of [price, quantity] pairs
- Order statuses: "resting", "canceled", "executed", "pending"

---

## 3. RISK MANAGER — STEAL THE PATTERN

**Source:** `refs/kalshi-btc/risk.py` — RiskManager class

The check order:
1. Kill switch active? → reject immediately
2. Daily loss limit breached? → trigger kill switch + reject
3. Max open orders? → reject
4. Max position size? → reject
5. Max order size? → reject
6. Too close to market close? → reject

**Key pattern:** Every order goes through `check_order_allowed()` before submission.
Returns `(bool, reason_str)` — always log the reason.

Daily PnL auto-rotates at midnight. Daily-loss-triggered kill switch auto-resets next day.

From poly-gabagool, add these layers (steal risk/manager.py):
- Consecutive loss counter with 2hr cooling period
- Session drawdown (separate from daily)
- Monthly drawdown ceiling

---

## 4. RATE LIMITER — STEAL THE ASYNC TOKEN BUCKET

**Source:** `refs/kalshi-btc/kalshi_client.py` AsyncRateLimiter class
Refills tokens every second. Separate limits for read (10/s) and write (5/s).
Clean and correct. Copy verbatim.

---

## 5. KELLY CRITERION — STEAL FROM POLY-APEX

**Source:** `refs/poly-apex/core/kelly.py`

Formula: `f* = (p*b - q) / b` then apply 0.25 fractional (conservative)

Kelly caps (steal these):
- winprob > 60% → 2.0 units max
- winprob > 54% → 1.0 units max
- otherwise → 0.5 units max
- Never Kelly-recommend above stage max_bet_usd

**Attribution:** `# Adapted from: https://github.com/djienne/Polymarket-bot`

---

## 6. PYDANTIC CONFIG — STEAL PATTERN FROM POLY-GABAGOOL

**Source:** `refs/poly-gabagool/src/rarb/config.py`

Use `pydantic-settings` BaseSettings for all config. Key patterns:
- `SecretStr` for any sensitive field → prevents accidental logging in tracebacks
- Field validators on startup (fail loud if config is wrong)
- `is_configured()` gate on every module that touches external services

**Attribution:** `# Adapted from: https://github.com/Gabagool2-2/polymarket-trading-bot-python`

---

## 7. POLYMARKET AUTH — REFERENCE ONLY (build now, activate later)

**Source:** `refs/poly-official/py_clob_client/`

Two-tier auth:
- L1: EIP-712 struct hash signed with private key (one-time)
- L2: HMAC-SHA256 over timestamp+method+path+body (every request)

sig_type = 1 for email/Magic wallet (Matthew's type)
FUNDER = proxy wallet address from polymarket.com/settings (not derivable from key)

HMAC payload: `timestamp + method + path + body` — normalize quotes (single→double)
Headers: ADDRESS, SIGNATURE, TIMESTAMP, API_KEY, PASSPHRASE

---

## 8. KALSHI FEE CALCULATION

**Source:** `refs/kalshi-interface/kalshi_positions.py` lines 89-95

`fee = 0.07 * P * (1 - P)` where P is the YES price in decimal (0–1)

At 44¢ YES price: fee = 0.07 × 0.44 × 0.56 = 1.73¢ per contract
Factor this into edge calculation — need > fee to be profitable.

---

## 9. TITANIUM ARCHITECTURE PATTERNS — READ-ONLY, NO BETTING LOGIC

**Source:** `/Users/matthewshields/Projects/titanium-v36/CLAUDE.md`

Patterns to adopt (structure only):

**One file = one job:**
- auth.py does ONLY signing, no API calls
- kalshi.py does ONLY HTTP calls, no math
- strategy.py does ONLY signal logic, no orders
- kill_switch.py does ONLY risk checks, no trading

**is_configured() gate:** Every module that touches external services exposes
`is_configured() → bool`. Check before use. Fail gracefully if not configured.

**Circular import guard:** If module A imports module B, module B must never
import module A. Use deferred imports (inside function body) to break cycles.

**SESSION_HANDOFF.md as resume document:** Already implemented. Keep it current.

**Project index:** Create PROJECT_INDEX.md after Phase 1 for token-efficient session resumption.

**Test isolation:** Module-level singletons (kill_switch state, bankroll) bleed between tests.
Use setup_method to reset state. `kill_switch.lock` file must be cleaned up in teardown.

**Loading tips:** Rotate tips in dashboard footer. Already planned. Teach the system.

---

## 10. KNOWN BUGS IN REFERENCE REPOS — DO NOT REPEAT

| Bug | Repo | Impact | Fix |
|-----|------|--------|-----|
| Query param signing (GET params excluded from sig) | kalshi-interface | 401s on paginated requests | Sign path without params (already correct in kalshi-btc) |
| SELL flip position calc broken | kalshi-interface | Wrong position tracking | Use kalshi-btc position tracking instead |
| No retry on network errors | kalshi-interface | Bot dies on transient errors | Use kalshi-btc retry pattern |
| Kelly trades file non-atomic write | poly-apex | History corrupts on crash | Use atomic write (write temp, rename) |
| Password not zero-filled after use | poly-apex | Memory dump leaks pw | Use secrets module, clear after use |
| Assertions instead of exceptions | poly-official | Disabled with python -O | Use explicit ValueError/RuntimeError |
| originator_engine: bet.line as mean | titanium-v36 | Wrong MC simulation | Not relevant to us, noted for awareness |

---

## 11. ADVERSARIAL AUDIT — WHAT TO WATCH FOR

Questions asked of every ref repo. Same checks apply to our code:

✓ Does it ever log private keys? → kalshi-btc does NOT. We must audit this in every log.info call.
✓ Can it write outside its folder? → None do. We enforce this via deny list in settings.json.
✓ Can it accidentally drain a wallet? → kalshi-btc guards with kill switch + order size check. Copy both.
✓ Does it hardcode credentials? → None do. We enforce via .env only, never in .py files.
✓ What's the worst single bug? → kalshi-interface auth signing bug. Already avoided by using kalshi-btc.

**Worst-case scenarios for our bot:**
1. Kill switch fails → uncapped losses. Mitigation: kill switch is synchronous, checked first, before any network call.
2. .pem file leaked → attacker can place orders. Mitigation: never log, gitignore, .env path only.
3. Infinite retry loop on auth failure → locks up. Mitigation: 3 retries max, then halt and write BLOCKERS.md.
4. Clock skew → KALSHI-ACCESS-TIMESTAMP rejected. Mitigation: use `time.time() * 1000`, sync NTP.

