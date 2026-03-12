# SNIPER LIVE PATH ANALYSIS
# Purpose: Technical analysis of what expiry_sniper_v1 needs to go live.
# Written: Session 55 (2026-03-12) — research-only, no code changes.
# Source files: src/strategies/expiry_sniper.py, main.py:1366-1521, src/execution/live.py:1-212

---

## 1. Strategy Internals

### PAPER_CALIBRATION_USD

`PAPER_CALIBRATION_USD = 0.50` is a class constant on `ExpirySniperStrategy`.
It is the **fixed paper bet size** used in the calibration phase. It is NOT Kelly sizing.

The docstring explains why: at exactly 90c with a model win rate of 91% (1pp favorite-longshot
premium), Kelly fraction is approximately zero because the edge is near-zero after fees.

At 90c YES: Kelly = (0.91 * 1/0.90 - 1) / (1/0.90 - 1) ≈ near-zero (edge is only 0.37pp after fee).

Result: Kelly sizing at paper phase would recommend $0 or near-$0 per bet. That is useless for
calibration. The strategy correctly uses fixed 0.50 USD to generate calibration data. The Kelly note
at lines 38-41 of the strategy file makes this explicit.

### 90c Threshold Logic

The 90c threshold is `_DEFAULT_TRIGGER_PRICE_CENTS = 90.0`. `generate_signal()` checks:

```
if yes_price >= 90c:    → side="yes", win_prob = min(0.99, yes_price/100 + 0.01 premium)
elif no_price >= 90c:   → side="no",  win_prob = min(0.99, no_price/100 + 0.01 premium)
else: → skip
```

For a NO=90c signal: `signal.side="no"` and `signal.price_cents = market.yes_price` (the YES price,
which at NO=90c would be ~10c). This is correct for payout calculation — signal.price_cents is
always the YES-equivalent price.

**Time gate**: only fires in last 840 seconds (14 min) of a 15-min window.
**Hard skip**: ignores final 5 seconds.
**Coin drift gate**: requires ≥0.1% coin move from window open in the SAME direction as the 90c side.

### generate_signal() Return Structure

Returns a `Signal` with:
- `side`: "yes" or "no"
- `price_cents`: always the YES price (even for NO signals — at NO=90c, YES=~10c, so price_cents≈10)
- `edge_pct`: small positive float (e.g., 0.0037 at 90c)
- `win_prob`: e.g., 0.91 at 90c YES entry
- `ticker`: the specific Kalshi market ticker
- `reason`: human-readable string

### PAPER_CALIBRATION_USD = 0.50 Live Sizing Implications

At extreme prices (NO@9c meaning YES=91c, or NO@90c meaning YES=10c):

**NO@9c (YES=91c):**
- 1 contract costs 9 cents. Trade of 0.50 USD → max(1, int(0.50/0.09)) = 5 contracts.
- Cost = 5 * 0.09 = 0.45 USD. If win: payout ≈ 5 contracts * (100-9)/100 = 4.55 USD. Net +4.10.
- This is a high-payout, small-bet structure. Risk = 0.45 USD to win 4.10 USD.

**NO@90c (YES=10c):**
- This is the target signal. 1 contract costs 90 cents. Trade of 0.50 USD → only 0 or 1 contract.
- Paper executor uses max(1, ...) so 1 contract at 90c = 0.90 USD actual cost.
- Paper immediately inflates size: 0.90 vs intended 0.50.
- Live Kelly at 90c YES=10c: payout = 10/100 = 0.10 per cent spent on NO. Kelly is near-zero.

**Key insight**: PAPER_CALIBRATION_USD is designed for the 90c side, meaning a NO@90c or YES@90c
bet costs ~90c per contract. The paper executor will round up to 1 contract (0.90 USD), not 0.50 USD.
This means paper bets at exactly 90c cost 80% MORE than the stated calibration size.
The paper P&L of +180+ USD across 38 bets includes this inflation — it overstates real performance.

---

## 2. Current expiry_sniper_loop() — Paper-Only Path

### Current Parameters (main.py:1366-1374)

```python
async def expiry_sniper_loop(
    kalshi,
    btc_feed,
    eth_feed,
    sol_feed,
    xrp_feed,
    db,
    kill_switch,
    initial_delay_sec: float = 110.0,
):
```

No `live_executor_enabled`, no `live_confirmed`, no `trade_lock`, no `calibration_max_usd`.
Hardcoded paper-only.

### What the Paper Path Does

1. Checks `kill_switch.is_hard_stopped` — hard stop blocks paper.
2. Fetches open markets for each of 4 series (KXBTC15M/ETH/SOL/XRP).
3. Tracks window-open coin price per ticker via `_window_open_price` dict.
4. Calls `strategy.generate_signal(market, coin_drift_pct)`.
5. Calls `db.has_open_position(ticker, is_paper=True)` — dedup.
6. Calls `kill_switch.check_paper_order_allowed(trade_usd, current_bankroll_usd)`.
7. Calls `paper_exec.execute(ticker, side, price_cents, size_usd, reason)`.
8. Logs the result.

### What Is MISSING for a Live Path

Comparing against `trading_loop()` (main.py:152-450):

**MISSING 1: live_executor_enabled + live_confirmed parameters.**
  The loop has no conditional live/paper branching. trading_loop() has:
  `is_paper_mode = not (live_executor_enabled and live_confirmed)` at line 192.

**MISSING 2: trade_lock parameter.**
  All live trading loops receive `_live_trade_lock` (asyncio.Lock created in main()).
  Without it, two concurrent live loops could both pass check_order_allowed() before either
  calls record_trade(), exceeding the hourly rate limit by 1. (Session 24 race condition fix.)
  The atomic block: `async with _lock_ctx: → check → execute → record_trade`.

**MISSING 3: check_order_allowed() (live kill switch check).**
  Current code only calls `check_paper_order_allowed()`. For live bets:
  `kill_switch.check_order_allowed(trade_usd, current_bankroll_usd, minutes_remaining)`.
  Note: `minutes_remaining` is needed. For expiry_sniper, this is seconds_remaining/60.

**MISSING 4: live.execute() call.**
  Current code only calls `paper_exec.execute()`. Live path needs:
  ```python
  import live_mod
  result = await live_mod.execute(
      signal=signal,
      market=market,
      orderbook=orderbook,  # ← REQUIRES ORDERBOOK FETCH (currently not done)
      trade_usd=trade_usd,
      kalshi=kalshi,
      db=db,
      live_confirmed=live_confirmed,
      strategy_name=strategy.name,
  )
  ```

**MISSING 5: orderbook fetch.**
  trading_loop() fetches the orderbook for EVERY market before generate_signal():
  `orderbook = await kalshi.get_orderbook(market.ticker)`.
  expiry_sniper_loop() does NOT fetch orderbooks at all — paper_exec doesn't need them.
  live.execute() REQUIRES the orderbook (line 101: `_determine_limit_price(side, market, orderbook)`).
  Adding an orderbook fetch for every market × every series × every 10s cycle adds
  significant API call overhead (4 series × up to 2 markets each = up to 8 orderbook calls/10s = 48/min).
  Kalshi rate limit is approximately 10 req/s = 600/min — 48/min is manageable but must be tracked.

**MISSING 6: kill_switch.record_trade() after successful live execution.**
  Current paper path calls `record_trade()` via paper_exec indirectly. Live path must call it
  explicitly after the lock-protected execute block: `kill_switch.record_trade()`.

**MISSING 7: _announce_live_bet() call.**
  trading_loop() calls `_announce_live_bet(result, strategy_name=strategy.name)` after every
  successful live bet. This sends a macOS Reminder notification. Not present in sniper loop.

**MISSING 8: Kelly/calculate_size() for live sizing.**
  Paper path uses fixed PAPER_CALIBRATION_USD = 0.50. Live path must call calculate_size()
  with proper parameters (win_prob, payout_per_dollar, edge_pct, bankroll_usd, min_edge_pct).
  payout_per_dollar calculation:
    yes_equiv = price_cents if side=="yes" else (100 - price_cents)
    payout = kalshi_payout(yes_equiv, side)
  Then clamp: trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD).
  Plus calibration_max_usd cap if using micro-live phase.

**MISSING 9: Bankroll snapshot logic.**
  trading_loop() periodically calls `kalshi.get_balance()` to keep bankroll fresh.
  expiry_sniper_loop() only calls `db.latest_bankroll()` — valid for paper, but for live
  the bankroll snapshot should be kept current.

**MISSING 10: max_daily_bets cap.**
  trading_loop() enforces a per-day per-strategy bet count cap. Sniper loop has no daily cap.
  For live, uncapped bet frequency is risky especially if price guard triggers frequently.

---

## 3. live.execute() Parameters — Signal Structure Compatibility

### live.execute() Signature (src/execution/live.py:48-58):
```python
async def execute(
    signal: Signal,
    market: Market,
    orderbook: OrderBook,
    trade_usd: float,
    kalshi: KalshiClient,
    db: DB,
    *,
    live_confirmed: bool = False,
    strategy_name: str = "unknown",
) -> Optional[dict]:
```

### Signal Structure Compatibility:

expiry_sniper's signal has: `side`, `price_cents`, `edge_pct`, `win_prob`, `ticker`, `confidence`, `reason`.

live.execute() uses:
- `signal.side` → YES or NO for order direction ✅
- `signal.price_cents` → YES price for slippage check (line 114) ✅
  BUT: note that for a NO@90c signal, signal.price_cents = 10 (the YES price at 10c).
  live.execute() converts: `execution_yes_price = price_cents if side=="yes" else (100 - price_cents)`.
  For NO signal: execution_yes_price = 100 - 10 = 90. This is 90c — outside the 35-65c guard!

**CRITICAL PROBLEM**: live.py has a hardcoded price guard at lines 116-122:
```python
_EXECUTION_MIN_PRICE_CENTS: int = 35
_EXECUTION_MAX_PRICE_CENTS: int = 65
if not (35 <= execution_yes_price <= 65):
    → REJECT
```

At NO=90c (YES-equiv = 90c), live.execute() REJECTS the order with:
"Execution price 90¢ (YES-equiv) outside guard 35-65¢"

The expiry sniper operates EXACTLY in the zone that live.py's execution guard blocks (87-100c).
These two modules are fundamentally incompatible without modifying live.py.

To go live, live.py would need to accept that the price guard can be bypassed for expiry_sniper,
OR the guard constants need to be parameterized (e.g., per-strategy guard ranges).
This is a non-trivial code change with safety implications.

---

## 4. Liquidity Risk Analysis at Extreme Prices

### Paper Executor Assumptions (paper.py)
Paper executor simulates instant fills at any size. It applies 1-tick slippage (1 cent) and
assumes 100% fill probability. It does NOT model:
- Order queue position (HFTs queue first at Kalshi)
- Market depth (how many contracts are available at 90c)
- Partial fills
- Market closing mid-execution

### Reality at NO@9c (YES=91c) — Sniper "rich" signal

The 91c side is near-certain. At this price, the spread is typically 1-2 cents (90-92c range).
Market depth at 91c YES is typically deep — this is where market makers rest orders to collect
the spread from retail. Fill should be possible, but at 91c the YES cost is 91 cents per contract.

For a 5 USD bet: 5 contracts at 91c = 4.55 USD cost. If win: payout = 5 * (100-91)/100 = 0.45 USD net.
This is the WRONG math for NO@9c. Let me redo:

NO@9c means: you spend 9 cents per contract to bet NO. If NO wins, you get 100 cents per contract.
For 0.50 USD bet: int(0.50/0.09) = 5 contracts × 9c = 0.45 USD cost. Win payout = 5 × 91c = 4.55 USD.
This is a 10:1 payout if the nearly-certain NO outcome happens (coin went DOWN significantly).

The market at NO=9c is usually driven by HFTs who have established the outcome is nearly certain
(coin moved decisively UP). At this point there may be NO sellers of NO at 9c — they've already
won and moved on. The thin liquidity at 9c means partial fills or cancellation are likely.

### Reality at NO@90c (YES=10c) — Primary sniper target

NO=90c means the coin has moved DOWN significantly and the NO market is near-certain.
Spread is typically 1-2c (89-91c). Market makers provide depth here.
A small order (1 contract at 90c = 0.90 USD) should fill.

BUT: if multiple signals fire simultaneously (4 series each checking every 10s), there could be
multiple concurrent orders at 90c across KXBTC/ETH/SOL/XRP15M. This is manageable.

### Why Paper P&L of +180 USD from 38 Bets Does NOT Represent Live Performance

From graduation status: expiry_sniper 38/30 bets, P&L +180.20, ~95% wins.

**Inflation sources:**
1. **Fixed-size paper bets at 0.50 USD** vs actual contract price: at 90c, 1 contract costs 90c,
   not 50c. Paper always buys at least 1 contract. So effective paper bet size = max(0.50, 0.90) = 0.90.
   Each "win" at 90c: win = (100-90)/100 × contracts × contract_price = 10c × 1 = 0.10 per contract.
   Expected paper P&L per bet at NO=90c: 0.91 × 0.10 - 0.09 × 0.90 = 0.091 - 0.081 = 0.010 USD.
   For 38 bets at 95% win rate: ~36 wins × 0.10 USD + ~2 losses × -0.90 = +3.60 - 1.80 = 1.80 USD.
   But the report shows +180 USD. This suggests the actual contract counts are much higher than 1.

2. **Price variation**: when YES=91c (NO=9c), a win on NO pays 91c per contract.
   int(0.50/0.09) = 5 contracts → 5 × 0.91 = 4.55 USD win for a 0.45 USD bet = +4.10 net.
   38 bets at this structure: 36 wins × 4.10 = 147.60 USD. 2 losses × -0.45 = -0.90 USD.
   Net ≈ +147 USD. This is closer to the +180 reported figure — the sniper fires frequently
   at the YES=91c (NO=9c) side where payout ratio is extreme.

3. **Paper fills are instant**: in reality, at NO=9c there is likely no seller. The order
   would cancel or partially fill. Paper assumes 100% fill.

4. **Paper has no execution-time price guard**: live.py would reject these signals outright
   (90c YES-equiv is outside 35-65c guard). Paper has no such gate.

**Quantified real P&L degradation estimate**:
- live.py execution guard rejection: ~100% of signals at NO=90c+ (execution_yes_price outside 35-65c)
- Unless live.py is modified, zero live bets would be placed
- If guard is modified: liquidity-adjusted fills at extreme prices are partial (~50-75% fill rate)
- Real P&L at 50% fill rate: approximately 50% of paper P&L, or ~90 USD lifetime
- Real P&L with execution guard modification + order cancellations: unknown but likely 30-60% of paper

**Conclusion**: The +180 USD paper P&L is NOT predictive of live performance. The live.py
execution guard completely blocks this strategy's price range. This must be resolved first.

---

## 5. Specific Code Changes Needed in main.py for Live Path

Reference: `trading_loop()` starting at main.py:152 as the template.

### Change 1: Add parameters to expiry_sniper_loop() signature
At main.py:1366, add:
```python
live_executor_enabled: bool = False,
live_confirmed: bool = False,
trade_lock: Optional[asyncio.Lock] = None,
calibration_max_usd: Optional[float] = None,
max_daily_bets: int = 35,  # paper default; live might be lower (5-10)
```

### Change 2: Add is_paper_mode flag (after parameter defaults)
Before the while True loop:
```python
is_paper_mode = not (live_executor_enabled and live_confirmed)
```
Used for dedup and daily cap filtering.

### Change 3: Add bankroll snapshot logic (inside while True, top)
Same pattern as trading_loop():
```python
now = time.time()
if now - last_bankroll_snapshot > BANKROLL_SNAPSHOT_SEC:
    try:
        balance = await kalshi.get_balance()
        db.save_bankroll(balance.available_usd, source="api")
    except Exception as e:
        ...
    last_bankroll_snapshot = now
current_bankroll = db.latest_bankroll() or 50.0
```

### Change 4: Add orderbook fetch inside the per-market loop
After fetching markets and before generate_signal():
```python
try:
    orderbook = await kalshi.get_orderbook(market.ticker)
except Exception as e:
    logger.warning("[expiry_sniper] Orderbook fetch failed: %s", e)
    continue
```
Only needed for live path, but must be present to pass to live.execute().

### Change 5: Add calculate_size() for live path sizing
After signal is confirmed, before kill switch check, for live path:
```python
from src.risk.sizing import calculate_size, kalshi_payout
yes_equiv = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)
payout = kalshi_payout(yes_equiv, signal.side)
_strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)  # sniper has small edge
size_result = calculate_size(
    win_prob=signal.win_prob,
    payout_per_dollar=payout,
    edge_pct=signal.edge_pct,
    bankroll_usd=current_bankroll,
    min_edge_pct=_strat_min_edge,
)
if size_result is None:
    continue
from src.risk.kill_switch import HARD_MAX_TRADE_USD as _HARD_CAP
trade_usd = min(size_result.recommended_usd, _HARD_CAP)
if calibration_max_usd is not None:
    trade_usd = min(trade_usd, calibration_max_usd)
```
Note: Kelly will return near-zero at 90c with 91% win prob. Calibration_max_usd needed.

### Change 6: Add daily bet cap check
After sizing, before kill switch:
```python
if max_daily_bets > 0:
    today_count = db.count_trades_today(strategy.name, is_paper=is_paper_mode)
    if today_count >= max_daily_bets:
        logger.info("[expiry_sniper] Daily cap reached — skip")
        continue
```

### Change 7: Add conditional live/paper execution block
Replace the current single paper execute block with a branching structure:
```python
if live_executor_enabled and live_confirmed:
    minutes_remaining = (strategy._seconds_remaining(market) or 0) / 60.0
    _lock_ctx = trade_lock if trade_lock is not None else contextlib.nullcontext()
    async with _lock_ctx:
        ok, reason = kill_switch.check_order_allowed(
            trade_usd=trade_usd,
            current_bankroll_usd=current_bankroll,
            minutes_remaining=minutes_remaining,
        )
        if not ok:
            logger.info("[expiry_sniper] Kill switch blocked live: %s", reason)
            continue
        from src.execution import live as live_mod
        result = await live_mod.execute(
            signal=signal,
            market=market,
            orderbook=orderbook,
            trade_usd=trade_usd,
            kalshi=kalshi,
            db=db,
            live_confirmed=live_confirmed,
            strategy_name=strategy.name,
        )
        if result:
            kill_switch.record_trade()
            _announce_live_bet(result, strategy_name=strategy.name)
else:
    # paper path (unchanged from current)
    ok, block_reason = kill_switch.check_paper_order_allowed(...)
    ...
```

### Change 8: Update the loop call in main() (~line 3043)
Add parameters to the asyncio.create_task call:
```python
expiry_sniper_loop(
    ...existing args...,
    live_executor_enabled=False,   # keep False until live gate clears
    live_confirmed=live_confirmed,
    trade_lock=_live_trade_lock,
    calibration_max_usd=0.01,      # micro-live phase
    max_daily_bets=10,
)
```

---

## 6. Pre-Live Audit Checklist (CLAUDE.md Step 5) — Pass/Fail

### kill_switch.check_order_allowed() called at every live order path?
STATUS: FAIL — not present in current loop. Would need to add (Change 7 above).

### settlement_loop calling record_win/record_loss for LIVE trades only?
STATUS: PASS — settlement_loop already handles this correctly with `if not trade["is_paper"]:`
guard. No changes needed for sniper.

### strategy_name passed correctly (not hardcoded)?
STATUS: PASS — `strategy.name` property returns "expiry_sniper_v1". Would be passed explicitly
in live_mod.execute(strategy_name=strategy.name).

### Price conversion correct (YES price for kalshi_payout, not NO price)?
STATUS: NEEDS WORK — signal.price_cents is always the YES price (correctly set at line 188 of
expiry_sniper.py: `price_cents = yes_price` for NO signals). BUT: kalshi_payout needs the
YES-equivalent at the entry price, and for NO@90c, yes_equiv = 100 - 90 = 10.
kalshi_payout(10, "no") would return a very high payout_per_dollar (10:1).
Kelly at 91% win prob, 10:1 payout = Kelly fraction = (0.91×10 - 0.09) / 10 ≈ 0.902 = 90%!
This seems wrong — Kelly would recommend 90% of bankroll at NO@9c (10c YES price).
RISK: Kelly sizing at extreme prices produces extreme bet sizes. calibration_max_usd is ESSENTIAL.

### DB save has correct is_paper flag?
STATUS: NEEDS REVIEW — live.execute() always passes `is_paper=False`. This is correct for live.
Paper path via paper_exec always passes is_paper=True. This should be fine.

### All parameters received by function from caller (no scope leakage from main())?
STATUS: PASS for current paper path. Would need to verify for live parameters added in Change 1.
`config` is not accessed inside the loop (confirmed: loop uses direct parameters).

### sizing clamp applied?
STATUS: NEEDS WORK — current paper path uses fixed PAPER_CALIBRATION_USD (no sizing calc at all).
Live path would need full Calculate 7 changes including HARD_CAP clamp.

### has_open_position() and count_trades_today() both pass is_paper= filter?
STATUS: PARTIAL — `db.has_open_position(ticker=ticker, is_paper=True)` is hardcoded True.
For live path, needs `is_paper=is_paper_mode` (the conditional flag). Needs fixing.

### _announce_live_bet() wired in for new strategy?
STATUS: FAIL — not present in sniper loop. Must add (Change 7 above).

### Live bets placed for FIRST window after enabling — verify in log within 15 min?
STATUS: N/A — pre-live audit item, procedural check at go-live time.

### --graduation-status run after first live bet to confirm trade counter increments?
STATUS: N/A — procedural post-enable check.

### No silent blocking: watch log for "Kill switch blocked" or "exceeds hard cap" on first window?
STATUS: N/A — procedural post-enable check.

---

## 7. Risk Verdict

### The Expansion Gate Condition (CLAUDE.md)

CLAUDE.md states: "Do NOT build new strategy types until current live strategies are producing
solid, consistent results. Hard gate: btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks
of live P&L data + no kill switch events + no silent blockers. Until then: log ideas to
.planning/todos.md only. Do not build."

Current state of expansion gate at Session 55:
- btc_drift: 54 live trades ✅ | Brier 0.247 ✅ | P&L -11.12 USD ❌ (all-time negative)
- No kill switch events recently ✅
- 2-3 weeks live P&L data: bot has been live for ~2 weeks ✅

The gate is borderline. btc_drift is all-time negative due to the pre-filter YES trades.
Post-filter NO-only data is insufficient (need 30 NO-only settled, have ~10).

### Specific Risks of Enabling Sniper Live Now

1. **live.py execution guard will block all signals.** execution_yes_price at 90c+ is outside
   35-65c guard. Every single live order would be rejected by live.execute() with a warning.
   The strategy produces ZERO live bets without modifying live.py. This is not a small change —
   it touches the core security layer of the bot.

2. **Kelly sizing at extreme prices is dangerous.** At NO@9c (YES=10c), Kelly recommends 90%+
   of bankroll. calibration_max_usd cap is essential, but adds complexity.

3. **Paper P&L of +180 USD is not representative.** The actual edge at 90c is 0.37pp after fees —
   extremely thin. The paper gains are driven by high-payout lottery-structure bets (NO@9c paying
   10:1) where paper assumes full fills with no liquidity constraints. Real fills at 9c may not
   happen at all.

4. **btc_drift is still negative all-time.** The expansion gate explicitly requires solid results
   from current strategies before enabling new live strategies.

### Verdict: DO NOT ENABLE LIVE YET

**Conditions needed before live evaluation:**
1. Modify live.py to support sniper's price zone (87-100c) — requires security review
2. btc_drift post-filter NO-only P&L must be positive over 30+ bets
3. 30 paper bets at the paper calibration size with Brier < 0.30 (currently at 38 bets, Brier n/a
   in graduation status — Brier calculation may not be wired for sniper)
4. Present to Matthew with full liquidity analysis before flipping live_executor_enabled=True

**Expiry sniper is a promising complementary strategy. The paper results are real.**
**But the path to live requires more infrastructure work than a simple flag flip.**
