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
(S79: restored 15→20 USD per Matthew directive — guards block structural losses, size on winners)
(S78: temporarily lowered 20→15 USD after high-loss day; reversed once guard analysis confirmed safety)

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

### IL-10: 96c and 97c-NO bets are blocked — structurally negative EV

**Rule:** `live.py` (after fee-floor guard): if `price_cents == 96`, return None.
If `price_cents == 97 and signal.side == "no"`, return None.
97c YES is NOT blocked (100% WR historically, profitable).

**Why:** At 96c, gross profit is 4c/contract. At 97c, it's 3c. Kalshi taker fee at these
prices plus correlated reversal risk means break-even requires 96%+ and 97%+ WR respectively.
Historical live data (S75, 44 bets in these buckets):
  96c both sides: 31 bets, 93.5% WR, -22.44 USD cumulative
  97c NO:         13 bets, 92.3% WR, -15.03 USD cumulative
Total structural drag: ~37.47 USD. Same mechanism as IL-5 (99c fee-floor).
Revisit when either bucket has 200+ bets at current bet size.

**Test:** `tests/test_live_executor.py::TestSniperNegativeEvBucketGuard`

---

### IL-11: 98c NO bets are blocked — structurally negative EV

**Rule:** `live.py` (after IL-10 guard): if `price_cents == 98 and signal.side == "no"`, return None.
98c YES is NOT blocked (20 bets, 100% WR, +3.02 USD historically, profitable).

**Why:** At 98c NO, gross profit is 2c/contract. Break-even requires 98%+ WR.
Live data (S78, 28 bets in this bucket):
  98c NO: 28 bets, 92.9% WR, -25.54 USD cumulative
Each loss = -18.62 USD, each win = +0.19 USD. 1 loss wipes 98 wins.
Same pattern as 97c NO (IL-10). Blocked after 28 bets of confirming data.
Revisit when bucket has 200+ bets at current bet size.

**Test:** `tests/test_live_executor.py::TestFeeFloorBoundary::test_no_at_98c_blocked`

---

---

### IL-12: Kelly floor truncation must remain synchronized with kill switch pct cap

**Rule:** `sizing.py` line 136: `size = math.floor(size * 100) / 100`.
The floored value must always satisfy `size / bankroll <= MAX_TRADE_PCT` at the same bankroll.
The kill switch pct cap check in `check_order_allowed()` (line 174) evaluates the same value
that sizing produces — they must agree. Never change `math.floor()` to `round()` or `math.ceil()`.

**Why:** At bankroll=$31.79, pct_cap=4.7685. `floor`→4.76 passes (4.76/31.79=14.97%).
`round`→4.77 fails (4.77/31.79=15.01% > 15% cap). A round() change silently blocks
valid bets at specific bankroll values with no clear error message.

**Test:** `tests/test_iron_laws.py::TestIL12SizingKillSwitchInteraction`

---

### IL-13: kalshi_payout() always receives YES price, regardless of bet side

**Rule:** For any call to `kalshi_payout(yes_price_cents, side)`:
- YES-side bet at price P: pass `yes_price_cents=P`
- NO-side bet at price P (where P is the NO price): pass `yes_price_cents=100-P`

Pattern: `yes_for_payout = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)`

**Why:** Session 20: `kalshi_payout(signal.price_cents, "no")` was called where price_cents
was the NO price (40c). Should have been 60c (YES price). Result: wrong edge calculation,
miscalibrated Brier scores, unreliable graduation data for several hours.

**Test:** `tests/test_iron_laws.py::TestIL13KalshiPayoutNOSideConversion`

---

### IL-14: Settlement loop only calls record_win/record_loss for live trades

**Rule:** `main.py` settlement_loop line 1192:
```python
if not trade["is_paper"]:
    if won:
        kill_switch.record_win()
    else:
        kill_switch.record_loss(abs(pnl_cents) / 100.0)
```
This `if not trade["is_paper"]` guard must never be removed.

**Why:** Session 21: paper losses counted toward the live daily loss limit, halting live
trading after a paper losing streak. Paper bets are not real money — risk governance
(consecutive loss cooling, daily limits) must only trigger on live outcomes.

**Test:** `tests/test_iron_laws.py::TestIL14SettlementLoopIsPaperFilter`

---

### IL-15: All live orders must pass kill_switch + execute atomically inside _live_trade_lock

**Rule:** In every live loop in `main.py`, the sequence:
  1. `kill_switch.check_order_allowed()`
  2. `await live.execute()`
  3. `kill_switch.record_trade()`
must be wrapped inside `async with _live_trade_lock:`. The lock is created once in `main()`
and passed to all live loops. Never remove the lock or move any of these three steps outside it.

**Why:** Session 24: two concurrent loops both passed check_order_allowed() before either
called record_trade(). The hourly counter incremented only after execution, so both loops
went through — exceeding the rate limit by 1.

**Test:** `tests/test_kill_switch.py::TestCheckOrderAllowed` (shallow); integration test not yet written.

---

### IL-16: _FIRST_RUN_CONFIRMED must be set True by main.py after startup confirmation

**Rule:** `live.py` line 34 initializes `_FIRST_RUN_CONFIRMED = False`.
After the operator types "CONFIRM" at the interactive startup prompt, `main.py` must set:
```python
import src.execution.live as live_exec_mod
live_exec_mod._FIRST_RUN_CONFIRMED = True
```
This must happen before any live trading loop starts.

**Why:** Session 20: when stdin is piped (`nohup ... < /tmp/confirm.txt`), `input()` receives
"" not "CONFIRM". The flag is never set to True, so every call to `execute()` silently returns
None. The bot runs for hours without placing any live bets — no error in the log.

**Test:** `tests/test_iron_laws.py::TestIL16FirstRunConfirmedModuleState`
`tests/test_live_executor.py::TestExecuteGuards::test_guard_first_run_not_confirmed_returns_none`

---

### IL-17: Bankroll floor check runs before pct-of-bankroll cap check

**Rule:** In `kill_switch.check_order_allowed()` (lines 165–179), the order of checks is:
  1. Bankroll floor (line 166): absolute constraint — never bet if bankroll <= $20
  2. Per-trade hard cap (line 171): absolute ceiling on bet size
  3. Pct-of-bankroll cap (line 174): relative constraint
Never reorder these. Absolute constraints before relative constraints.

**Why:** Code clarity and debugging. If pct cap runs first at low bankroll, the error
message says "15% exceeded" when the real issue is "bankroll at floor". The floor
check always runs first so the error is unambiguous.

**Test:** `tests/test_iron_laws.py::TestIL12SizingKillSwitchInteraction::test_bankroll_floor_checked_before_pct_cap`

---

### IL-18: strategy_name passed to live.execute() must come from strategy.name, never hardcoded

**Rule:** Every live loop call to `live.execute(..., strategy_name=...)` must pass the value
from the strategy object (`strategy.name`) or a loop parameter. Never a string literal like
`strategy_name="btc_lag"`.

For loops reusing BTCDriftStrategy (eth/sol/xrp drift), the `name_override` parameter at
construction time is the sole mechanism: `BTCDriftStrategy(name_override="eth_drift_v1")`.

**Why:** Session 20: eth_lag loop was copy-pasted from btc_lag with hardcoded `strategy="btc_lag"`.
eth_lag bets were recorded as "btc_lag" in the DB for several hours. Calibration data and
graduation counters for both strategies became unreliable.

**Test:** `tests/test_iron_laws.py::TestIL18StrategyNameNotHardcoded`
`tests/test_live_executor.py::TestRegressions::test_strategy_name_not_hardcoded_btc_lag`

---

---

### IL-19: KXSOL YES@97c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXSOL" in signal.ticker and price_cents == 97 and signal.side == "yes"`.

BTC/ETH YES@97c remain profitable (100% WR) — only SOL is blocked.
KXXRP YES@97c is separately blocked by IL-10B.

**Stats at time of guard (S88 2026-03-16):** 8 bets, 87.5% WR, -17.18 USD.
Break-even requires 97% WR. Current WR 87.5% is 9.5 points below.
Loss pattern: KXSOL15M-26MAR160200-00 $19.40 loss triggered analysis.

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_sol_yes_at_97c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_yes_at_97c_not_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_eth_yes_at_97c_not_blocked`

---

### IL-20: KXXRP YES@95c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXXRP" in signal.ticker and price_cents == 95 and signal.side == "yes"`.

SOL/BTC/ETH YES@95c remain profitable (100% WR) — only XRP is blocked.
KXXRP YES@94c and YES@97c are separately blocked by IL-10A and IL-10B.

**Stats at time of guard (S88 2026-03-16):** 10 bets, 90.0% WR, -14.27 USD.
Break-even requires 95% WR. Current WR 90.0% is 5 points below.
Loss pattern: KXXRP15M-26MAR160415-15 YES@95c (-19.95 USD) triggered analysis.
Pattern: same XRP YES-side intra-window volatility as IL-10A/B.

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_xrp_yes_at_95c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_xrp_yes_at_95c_blocked_il20`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_sol_yes_at_95c_not_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_yes_at_95c_not_blocked`

---

### IL-21: KXXRP NO@92c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXXRP" in signal.ticker and price_cents == 92 and signal.side == "no"`.

BTC/ETH NO@92c remain unaffected — only XRP is blocked.
KXXRP NO@91c and NO@93c+ remain profitable (100% WR).

**Stats at time of guard (S92 2026-03-17):** 4 bets, 75.0% WR, -15.33 USD net.
Break-even requires 92.0% WR. Asymmetric payout: wins ~1.40 USD each, losses ~19 USD each.
Loss pattern: KXXRP15M-26MAR170000 NO@92c (-19.32 USD) triggered analysis.
Pattern: NO@91c=100% WR, NO@92c=75% WR, NO@93c+=100% WR. 92c is the single bad bucket.

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_xrp_no_at_92c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_no_at_92c_not_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_eth_no_at_92c_not_blocked`

---

### IL-22: KXSOL NO@92c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXSOL" in signal.ticker and price_cents == 92 and signal.side == "no"`.

BTC/ETH/XRP NO@92c remain unaffected — only SOL is blocked here (XRP covered by IL-21).
KXSOL NO@91c and NO@93c+ remain profitable (100% WR).

**Stats at time of guard (S94 2026-03-17):** 3 bets, 67.0% WR, -12.97 USD net.
Break-even requires 92.0% WR. Same asymmetric payout as IL-21: wins ~1.40 USD each, losses ~18 USD each.
Guard added proactively based on payout asymmetry math (n=3 is small but break-even math is asset-independent).
Pattern: NO@91c=100% WR, NO@92c=67% WR, NO@93c+=100% WR. Same per-asset volatility notch as XRP.

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_sol_no_at_92c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_no_at_92c_not_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_eth_no_at_92c_not_blocked`

---

### IL-23: KXXRP YES@98c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXXRP" in signal.ticker and price_cents == 98 and signal.side == "yes"`.

BTC/ETH/SOL YES@98c remain unaffected — all 100% WR (13/13, 16/16, 12/12). XRP-specific volatility notch.

**Stats at time of guard (S94 2026-03-17):** 11 bets, 90.9% WR, -17.89 USD net.
Break-even requires 98.0% WR. Extreme asymmetric payout: wins ~0.20 USD each, losses ~19.60 USD each.
Triggered by trade #3224 KXXRP YES@98c -> NO at 02:31 UTC, -19.60 USD.
Same per-asset pattern as KXXRP YES@94c (IL-10A), YES@95c (IL-20), YES@97c (IL-10B).

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_xrp_yes_at_98c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_yes_at_98c_not_blocked_by_il23`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_eth_yes_at_98c_not_blocked_by_il23`

---

---

### IL-24: KXSOL NO@95c is structurally negative EV — block execution

**Rule:** `src/execution/live.py execute()` must return `None` when `"KXSOL" in signal.ticker and price_cents == 95 and signal.side == "no"`.

BTC/ETH/XRP NO@95c remain unaffected — all 100% WR (11/11, 10/10, 12/12). SOL-specific volatility notch.

**Stats at time of guard (S95 2026-03-17):** 16 bets, 93.8% WR, -31.50 USD net.
Break-even requires 95.0% WR. Extreme asymmetric payout: wins ~0.84 USD each, losses ~19.95 USD each.
Triggered by trade KXSOL15M-26MAR170000-00 no@95c at 04:05 UTC, -19.95 USD.
Same per-asset pattern as KXSOL YES@94c (IL-10C), YES@97c (IL-19), NO@92c (IL-22).

**Test:** `tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_sol_no_at_95c_blocked`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_btc_no_at_95c_not_blocked_by_il24`
`tests/test_live_executor.py::TestPerAssetStructuralLossGuards::test_eth_no_at_95c_not_blocked_by_il24`

---

**IL-28 (2026-03-17 06:40 UTC): KXXRP NO@94c BLOCKED**
Trigger: trade #3292 KXXRP NO@94c -19.74 USD. Net -5.29 USD over 17 bets (94.1% WR).
Fee-adjusted break-even at 94c is ~94.4%; actual WR of 94.1% is net negative.
One loss (~18-20 USD) wipes ~16 prior wins (~1.05 USD each). Pattern matches IL-21/25/26.
KXXRP NO@93c and NO@95c remain profitable (100% WR, n=17 and n=12 respectively).

**IL-29 (2026-03-17 08:05 UTC): KXBTC YES@88c BLOCKED**
Trigger: trade #3380 KXBTC YES@88c -19.36 USD. Below 90c sniper floor — insufficient historical data.
2 bets, 50% WR, -17.93 USD net. One of three simultaneous losses in 26MAR170415-15 window.

**IL-30 (2026-03-17 08:16 UTC): KXETH YES@93c BLOCKED**
Trigger: trade #3382 KXETH YES@93c -19.53 USD. 9 bets, 88.9% WR, needs 93.0% break-even, -10.83 USD.
One loss wipes ~13 wins (~1.26 USD each). ETH YES@90-92c and YES@94c+ remain viable.

**IL-31 (2026-03-17 08:16 UTC): KXXRP NO@91c BLOCKED**
Trigger: trade #3383 KXXRP NO@91c -19.11 USD. 5 bets, 80% WR, needs 91% break-even, -14.07 USD.
All three losses (IL-29/30/31) occurred in same 15-min settlement window — correlated macro move.
KXXRP NO@91c was previously 4/4 (100% WR) but single loss wiped all prior gains.

**IL-32 (2026-03-17 08:46 UTC): KXBTC NO@91c BLOCKED**
Trigger: trade #3391 KXBTC NO@91c -19.11 USD. 7 bets, 85.7% WR, needs 91% break-even, -11.27 USD.
Second two-loss window at 08:46 UTC: KXBTC NO@91c + KXETH NO@89c (n=1, watch only).

**SNIPER EXECUTION FLOOR (2026-03-17 09:00 UTC): price_cents >= 90 enforced**
Root cause: sniper signals at 90c+ but asyncio gap allows execution at 88-89c.
IL-29 (KXBTC YES@88c) and KXETH NO@89c (n=1) both executed below the signal floor.
Fix: execute() rejects ANY sniper execution price < 90c, regardless of asset or side.
This is a structural guard — prevents future slippage losses without per-bucket rules.

*Last updated: Session 95 (2026-03-17). IL-32 + sniper execution floor (90c min) added.*
