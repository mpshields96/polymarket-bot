# BOUNDS.md — Iron Laws + Danger Zones

Read this before editing any DANGER ZONE file. These invariants must hold
at all times. Each law cites the exact file and line enforcing it, the
historical incident it prevents, and the test that catches regression.

---

## DANGER ZONE FILES

### TIER 1 — CRITICAL (wrong edit = live money lost immediately)

PreToolUse hook enforces full test suite pass before any edit to these files.

| File | What it guards |
|---|---|
| `src/execution/live.py` | Real order placement, all execution guards |
| `src/risk/kill_switch.py` | All hard/soft stops and thresholds |
| `src/risk/sizing.py` | Kelly calculation and stage caps |

### TIER 2 — HIGH (wrong edit = silent misconfiguration or credential exposure)

Review BOUNDS.md checklist manually before editing. No hook.

| File | Risk |
|---|---|
| `src/auth/kalshi_auth.py` | RSA-PSS private key loading and signing |
| `src/platforms/kalshi.py` | All raw Kalshi API calls, order payload |
| `config.yaml` | Live strategy parameters, sniper thresholds |
| `main.py` | Strategy wiring, kill switch restores, live confirmation |

### TIER 3 — ELEVATED (wrong edit = strategy miscalibration, not immediate money)

| File | Risk |
|---|---|
| `src/strategies/expiry_sniper.py` | Sniper parameters (90c trigger, 840s window) |
| `src/strategies/btc_drift.py` | Live drift signal logic |
| `src/strategies/eth_drift.py` | Live drift signal logic |
| `src/db.py` | Financial records, calibration data |

---

## IRON LAWS

### IL-1: LIVE_TRADING double-gate is mandatory

**Rule:** `execute()` in `live.py` MUST check both `os.getenv("LIVE_TRADING") == "true"`
(line 89) AND `live_confirmed=True` (line 96). Both checks must exist. Neither
can be removed or defaulted to True.

**Why:** Defense-in-depth. Either can fail independently (env var typo, stale CLI flag)
without the other failing. Session 20 had a silent path where `live_confirmed`
was never set, allowing orders to fire with no operator acknowledgment.

**Test:** `tests/test_live_executor.py::TestExecuteGuards` (guards at lines 89–99)

---

### IL-2: kill_switch.check_order_allowed() is the last gate before every live order

**Rule:** No live order may be placed without a `True` return from
`kill_switch.check_order_allowed()`. The call must happen inside `_live_trade_lock`
(asyncio.Lock in main.py) alongside the order placement.

**Why:** Without the lock, two concurrent loops both pass the check before either
records the trade. Session 24 race condition allowed two orders through simultaneously,
exceeding the hourly rate limit by 1.

**Test:** `tests/test_kill_switch.py::TestCheckOrderAllowed`

---

### IL-3: HARD_MAX_TRADE_USD may only be raised by explicit Matthew directive

**Rule:** `HARD_MAX_TRADE_USD = 20.00` in `kill_switch.py` (line 39). Strategy loops
must clamp: `trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD)`.
No strategy code may pass a `trade_usd` larger than this constant.
To raise the cap: Matthew must explicitly direct it, document it in CHANGELOG.md,
and it must go through verify_change.sh.

**Why:** The 20 USD cap is the only mechanical backstop against Kelly over-sizing
at Stage 2+. Bankroll floor ($20) + consecutive cooling + this cap = the full
risk stack. Removing any layer leaves only the others.

**Test:** `tests/test_kill_switch.py::TestHardCapEnforced`

---

### IL-4: Sniper trigger threshold floor is 90c — never lower

**Rule:** `_DEFAULT_TRIGGER_PRICE_CENTS = 90.0` in `src/strategies/expiry_sniper.py`
(line 62). Must never be lowered below 90. Config.yaml `strategy.expiry_sniper.trigger_price_cents`
must also never go below 90.

**Why:** The favorite-longshot bias edge exists at 90c+. Below 90c, longshots are
OVERpriced (the bias reverses). Validated at 240 bets, 97.5% WR. This is the
primary P&L engine. Do not touch.

**Test:** `tests/test_expiry_sniper.py` (threshold coverage throughout)

---

### IL-5: Fee-floor guard must block 1c and 99c raw prices

**Rule:** `live.py` lines 125–130:
```python
if price_cents >= 99 or price_cents <= 1:
    return None
```
This block must never be removed.

**Why:** At 99c (or 1c NO side), gross margin is 1c/contract. After Kalshi fee,
net is negative. The -14.85 USD loss (trade ~622, SOL YES@99c x15) was caused by
this guard being absent. Fee = 0.07 * 0.99 * 0.01 = 0.000693/contract. At 1c profit/contract,
you net negative on every win.

**Test:** `tests/test_live_executor.py::TestFeeFloorGuard`

---

### IL-6: No API credentials in source code — ever

**Rule:** `KALSHI_API_KEY_ID` and `KALSHI_PRIVATE_KEY_PATH` must always be loaded
from `.env` / environment variables. Never hardcoded. The `.pem` file path must
never appear in any log output (only filename logged, not full path contents).

**Enforcement:** `src/auth/kalshi_auth.py` line 64 logs only `key_path.name` (filename)
not `key_path.read_bytes()`. `load_from_env()` at line 117 validates env vars.

**Why:** Key leakage = unauthorized API access to real Kalshi account. RSA private key
cannot be rotated without re-configuring Kalshi — it's permanent damage.

**Test:** `tests/test_security.py` (credential leak scanner)

---

### IL-7: Canceled orders are never recorded as trades

**Rule:** `live.py` lines 199–205: if `order.status == "canceled"`, return None
without any DB write. This guard must survive all refactors.

**Why:** A canceled-order recorded as a live bet corrupts: (1) calibration data and
Brier scores, (2) graduation counters (strategy thinks it has more bets than it does),
(3) consecutive-loss kill switch (phantom "loss" triggers cooling period).
Bug hit at Session 38.

**Test:** `tests/test_live_executor.py::TestExecuteOrderStatusGuard`

---

### IL-8: Paper bets use is_paper=True, live bets use is_paper=False — never mix

**Rule:** `db.save_trade()` must always receive the correct `is_paper` flag.
Live executor always passes `is_paper=False` (live.py line 218).
Paper executor always passes `is_paper=True`.
Kill switch: live loops call `check_order_allowed()`, paper loops call
`check_paper_order_allowed()`. These must never be swapped.

**Why:** At Session 21, paper losses counted toward the live daily limit, blocking
real trades. Paper losses are not real money — stopping paper data collection
during a soft kill wastes calibration data.

**Test:** `tests/test_kill_switch.py::TestPaperVsLiveSeparation`

---

### IL-9: Money math uses floor truncation, never rounding up

**Rule:** `sizing.py` line 136: `size = math.floor(size * 100) / 100`.
Must not be changed to `round()` or `math.ceil()`.

**Why:** `round($4.7685)` → $4.77. Kill switch then checks $4.77 / $95.37 = 5.0016%
of bankroll, which exceeds the 5.0% pct cap and blocks the trade the sizing module
just approved. Floor ensures the sized bet always satisfies the pct cap at the same
bankroll value.

**Test:** `tests/test_sizing.py::TestFloorTruncation`

---

## VERIFY-REVERT LOOP (Pattern 2)

For any change to a strategy parameter or numeric threshold, run before committing:

```bash
bash scripts/verify_change.sh <strategy_name> <min_win_rate>
```

Examples:
```bash
# After changing expiry_sniper trigger or window parameters:
bash scripts/verify_change.sh expiry_sniper 0.95

# After changing btc_drift thresholds:
bash scripts/verify_change.sh btc_drift_v1 0.55

# After changing sol_drift thresholds:
bash scripts/verify_change.sh sol_drift_v1 0.60 30
```

The script stashes your changes, runs pytest + DB baseline check, then either
restores (VERIFIED) or drops (REVERTED) the stash automatically.

---

## WHEN TO READ THIS FILE

- Before editing any TIER 1, 2, or 3 file listed above
- Before changing any numeric constant in kill_switch.py, sizing.py, or config.yaml
- Before adding a new strategy (complete the full 6-step CLAUDE.md workflow first)
- After any production loss — verify the relevant Iron Law is still enforced

---

*Last updated: Session 74 (2026-03-15). Add new laws here when new invariants are established.*
