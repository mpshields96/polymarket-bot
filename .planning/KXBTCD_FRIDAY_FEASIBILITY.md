# KXBTCD FRIDAY SLOT — FEASIBILITY ANALYSIS
# Purpose: Technical and strategic analysis of the KXBTCD Friday weekly slot strategy.
# Written: Session 55 (2026-03-12) — research-only, no code changes.
# Source files: src/strategies/crypto_daily.py, main.py:915-1090 (crypto_daily_loop),
#               .planning/KALSHI_MARKETS.md

---

## 1. KXBTCD Series Structure

### Source: .planning/KALSHI_MARKETS.md (first-hand API probe Session 51)

KXBTCD is Kalshi's Bitcoin daily threshold market series. There is only ONE KXBTCD series.
Within it, there are multiple "slots" identified by the settlement date and time.

**Type 2 — Same-day (hourly/daily) slots:**
- Question: "Bitcoin price on Mar 12, 2026 at 5pm EDT?"
- Settles: today at a fixed clock time
- Most liquid slot: 5pm EDT (21:00 UTC) → 676,674 contracts confirmed Session 51
- Next most liquid: 1pm EDT (17:00 UTC) → 170,238 contracts
- These are what btc_daily_v1 currently targets

**Type 3 — Friday slots (weekly threshold):**
- Question: "Bitcoin price on Friday Mar 13, 2026 at 5pm EDT?"
- Settles: the NEXT FRIDAY at 5pm EDT
- Volume (Session 51 probe): KXBTCD-26MAR1317 → 770,784 contracts
  — this is the LARGEST SINGLE KXBTCD SLOT (more than same-day 5pm)
- Same series ticker: KXBTCD (NOT a separate KXBTCW series — that does not exist)
- Same ATM structure: 40-75 strikes per slot, pick the ~50c contract
- Example ticker: KXBTCD-26MAR1317-T70499.99 at 48c YES, 31,625 volume per strike

### How Type 2 vs Type 3 bets differ:

| Attribute          | Type 2 (same-day)            | Type 3 (Friday slot)         |
|--------------------|------------------------------|------------------------------|
| Settlement         | today at 1pm or 5pm EDT      | next Friday at 5pm EDT       |
| Time horizon       | 0.5 to 6 hours               | 1 to 5 days                  |
| Volume             | 676K (5pm slot)              | 770K (Friday slot)           |
| Spread             | tighter (intraday)           | wider (multi-day uncertainty) |
| Signal driver      | intraday drift from open     | multi-day trend, macro        |
| ATM dynamics       | resets daily                 | drifts over days as BTC moves |
| Uncertainty scale  | hours                        | days                          |

---

## 2. CryptoDailyStrategy Analysis — What Changes for Friday Slots

### Current btc_daily_v1 Configuration (main.py:2628-2638)

```python
btc_daily_strategy = CryptoDailyStrategy(
    asset="BTC",
    series_ticker="KXBTCD",
    min_drift_pct=0.005,          # 0.5% intraday drift to fire
    min_edge_pct=0.04,            # 4% edge after fees
    min_minutes_remaining=30.0,   # skip markets settling <30 min away
    max_minutes_remaining=360.0,  # skip markets settling >6 hours away
    min_volume=100,
    direction_filter="no",        # contrarian: only bet NO on upward drift
)
```

### The Key Parameter: max_minutes_remaining=360.0

This is the critical gate. `_find_atm_market()` in CryptoDailyStrategy filters:

```python
if minutes_remaining > self._max_minutes_remaining:  # skip if >6 hours away
    continue
```

A Friday slot with 2 days remaining = 2 × 24 × 60 = 2,880 minutes. This is WAY above 360 min.
The current strategy never evaluates Friday slots. They are always filtered out at this gate.

To target Friday slots, `max_minutes_remaining` would need to increase to at least 5 × 24 × 60 = 7,200
minutes (5 trading days max). This means the same CryptoDailyStrategy class CAN technically target
Friday slots with just a parameter change — but the signal logic would be wrong.

### Why the Current Signal Logic Does NOT Work for Friday Slots

**Signal driver (generate_signal())**:

```python
drift_pct = (spot - session_open) / session_open
```

`session_open` is the BTC price at midnight UTC today (reset daily in `crypto_daily_loop()`).
This measures INTRADAY drift — how much BTC has moved since today's midnight.

For a Friday slot settling in 3 days, intraday drift from today's midnight is irrelevant.
What matters is: where is BTC now relative to the strike? Will BTC end above or below strike
by Friday? That requires multi-day trend analysis, not intraday momentum.

**Model probability (_model_prob)**:

```python
drift_signal = max(0.0, min(1.0, 0.5 + drift_pct * _DRIFT_SCALE))
sigma = _hourly_vol_for(asset) * math.sqrt(hours_to_settle)
z = (math.log(spot) - math.log(strike)) / sigma
position_prob = _norm_cdf(z)
return 0.7 * drift_signal + 0.3 * position_prob
```

The lognormal position component scales correctly with `hours_to_settle` — this part works for
multi-day horizons. But the drift_signal component (70% weight) is intraday noise.

For a 72-hour settlement, a 0.5% intraday drift has near-zero predictive power. The lognormal
position (spot vs strike with 3-day vol) is the only meaningful signal for weekly bets.

**min_drift_pct gate**:
With direction_filter="no", the current code requires drift_pct >= 0.005 (0.5% upward move).
This fires on any 0.5% intraday BTC move. For weekly bets, this would fire constantly
(BTC moves 0.5% intraday almost every day) even when the weekly forecast has no meaningful edge.

**Conclusion**: CryptoDailyStrategy with `max_minutes_remaining=7200` would technically SELECT
the Friday ATM market, but the signal quality for weekly bets would be poor. The 70% weighting
on intraday drift is inappropriate for a 3-5 day time horizon.

---

## 3. Is Friday Slot a Distinct Strategy?

### Time Horizon Difference

Same-day KXBTCD: 30 min to 6 hours. Signal: intraday momentum (drift from midnight open).
Weekly KXBTCD: 1-5 days. Signal: multi-day trend, macro factors, mean reversion vs momentum.

These require different signal logic. The academic edge for weekly bets is different from
intraday bets:
- Academic basis for weekly: "Bitcoin tends to mean-revert over 3-5 day periods" or
  "directional momentum persists for 1-2 days but reverses after" — none of these are
  the same as the 15-min drift-continuation thesis behind btc_drift.
- The favorite-longshot bias documented for same-day contracts does NOT necessarily apply
  identically to weekly contracts (wider spreads, different market participant mix).

### Signal for Friday's BTC Close vs Today's Close

What signal predicts BTC price at Friday 5pm EDT from a position entered Monday morning?

Relevant factors:
1. **Lognormal position**: where is BTC now vs strike? With 3-day sigma (~3% for BTC),
   if BTC is 3% above the strike, P(above at Friday) ≈ 84%. This is exploitable.
2. **Mean reversion vs momentum at 3-5 day horizon**: empirical question requiring data.
3. **Macro schedule**: FOMC meetings, CPI releases, options expiries (Friday is common).
4. **Weekend effect**: BTC historically has different volatility patterns on weekends.

None of these are captured by `drift_pct = (spot - session_open) / session_open`.

### Separate Strategy Class or Parameterize?

**Option A — Parameterize CryptoDailyStrategy** (simpler, lower risk):
- Add `use_lognormal_only: bool = False` parameter.
- When True: ignore drift_signal, use lognormal position with 100% weight.
- Add `max_minutes_remaining=7200` for weekly.
- This is 2-3 parameter additions + 1 conditional in _model_prob().

**Option B — Separate CryptoWeeklyStrategy class** (cleaner, higher effort):
- Separate model for weekly bets: pure lognormal with different volatility calibration.
- Different min_drift gate (use "spot vs strike distance" instead of intraday drift).
- Custom signal naming: btc_weekly_v1.

**Verdict**: Option A is lower risk for initial exploration. If weekly Brier differs significantly
from daily, a separate class would be warranted. Start with parameterization.

---

## 4. Graduation Gate Condition

### CLAUDE.md Expansion Gate (verbatim):

"Do NOT build new strategy types until current live strategies are producing solid, consistent
results. Hard gate: btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks of live P&L data
+ no kill switch events + no silent blockers. Until then: log ideas to .planning/todos.md only.
Do not build."

### Current State vs Gate (Session 55):

btc_drift: 54 live trades ✅ | Brier 0.247 ✅ | All-time P&L -11.12 USD ❌
eth_drift: 83 live trades ✅ | Brier 0.247 ✅ | All-time P&L +12.51 USD ✅
2-3 weeks live P&L data: approximately met (bot live since ~late Feb 2026) ✅
No kill switch events recently: approximately met ✅

**Gate status: borderline.** btc_drift is all-time negative (pre-filter YES bets were losers).
Post-filter NO-only data is ~10 bets — insufficient for solid conclusions. eth_drift is positive
and consistent, supporting the overall system.

### Specific gate failure for Friday slot strategy:

The gate requires btc_daily_v1 PAPER validation before building a LIVE weekly strategy.
btc_daily_v1 paper state: 12/30 settled bets, Brier unknown, 1 bet/day cadence.
At current rate: ~18 more days to reach 30 bets. Gate opens around 2026-03-30.

Building ANY weekly/Friday strategy while btc_daily_v1 paper phase is incomplete would violate
PRINCIPLES.md: "re-evaluate with data, not intuition."

---

## 5. Feasibility Verdict

### Should we build this now?

**NO. Build after the expansion gate fully clears.**

Specific reasons:

1. **btc_daily_v1 paper gate must clear first.** We need 30 paper bets from same-day KXBTCD
   to understand the signal quality for daily BTC threshold bets. We have 12. The Friday slot
   is more complex (multi-day horizon) — we should prove same-day works first.

2. **Signal model needs design work.** The current CryptoDailyStrategy is explicitly designed
   for same-day intraday drift. Using it for weekly bets would produce low-quality signals
   (intraday noise predicting 3-day outcome). A proper weekly signal requires rethinking
   the model (lognormal-only with 3-day sigma, or macro signal).

3. **Volume argument is compelling but not urgent.** Friday slot at 770K volume vs 676K same-day
   5pm is the single largest KXBTCD slot. This is worth building. But the edge source for
   weekly bets is fundamentally different and requires calibration data.

4. **btc_drift is still all-time negative.** The gate explicitly requires "solid, consistent
   results" from current strategies. btc_drift post-filter needs 20 more NO-only settled bets
   before we have a clear picture. That's ~2 weeks.

### What to do RIGHT NOW (within this session):

- Ensure btc_daily_v1 paper is running and accumulating. (Already confirmed: 12/30 settled.)
- Log the Friday slot as a high-priority todo for when gate clears.
- DO NOT touch crypto_daily.py or add new parameters until btc_daily Brier is known at 30 bets.

### What to do WHEN gate clears (~2026-03-30 at 30 btc_daily paper bets):

1. Check btc_daily Brier. If < 0.30: evaluate live promotion for same-day KXBTCD 5pm slot.
2. Then build CryptoWeeklyStrategy (or parameterize CryptoDailyStrategy) for Friday slots.
3. Paper the Friday slot for 30 bets before any live consideration.
4. Target signal: lognormal position (spot vs strike with 3-5 day sigma), direction_filter=TBD.
5. ATM selection: use `_find_atm_market()` with max_minutes_remaining=7200 and a priority
   for the 21:00 UTC Friday close slot (same as current, but selecting the Friday date).

### Implementation estimate (when gate clears):

Simple parameterization path (Option A): 1-2 hours of work.
Full separate class (Option B): 3-4 hours including tests.
Paper validation: ~30 days (1 bet/day max frequency for weekly, may be less).

**Priority ranking among expansion candidates:**
1. SOL Stage 2 graduation (3 bets away — immediate, highest lever)
2. btc_daily same-day live promotion (after 30 paper bets)
3. XRP YES filter validation (17/30 live bets — ongoing)
4. KXBTCD Friday slot strategy (paper gate must clear first)

The Friday slot is worth building but is correctly placed 4th in priority order.
Do not skip steps 1-3 to get to step 4.
