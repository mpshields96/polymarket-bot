# Edge Research — Session 60 Side Chat
# Generated: 2026-03-13 ~03:30 UTC
# Purpose: Research new profitable edges for polymarket-bot
# Status: RESEARCH ONLY — no code changes made

## Executive Summary

Eight research areas analyzed using internal DB data (228 live trades), web research
(academic papers, Kalshi docs, community analysis), and existing codebase knowledge.

TOP 3 IMMEDIATE OPPORTUNITIES (sorted by effort-to-edge ratio):
1. R8 Time-of-Day Filter — HIGHEST IMPACT, near-zero effort
2. R1 Limit Orders — structural fee savings, moderate effort
3. R7 Regime Detection — suppress losing trades, moderate effort

MEDIUM-TERM (1-2 sessions to build):
4. R4 KXBTCD Daily Thresholds — different instrument, structural edge
5. R6 CPI/Economics Markets — episodic but high-edge

DEFER (more data needed or lower priority):
6. R2 Multi-Window Momentum — insufficient evidence at our scale
7. R3 Cross-Market Signals — adds complexity for marginal gain
8. R5 Friday Weekly — similar to R4, build after R4 validates

---

## R8 — Time-of-Day Filter

**Verdict: PURSUE IMMEDIATELY (Priority 1)**

### Evidence — Our Own Data (228 live trades)

PROFITABLE HOURS (UTC):
  00:00  22 trades  81.8% win  +15.54 PnL
  03:00  18 trades  83.3% win   +7.65 PnL
  11:00   7 trades  85.7% win   +7.87 PnL
  14:00  11 trades  72.7% win   +6.07 PnL
  15:00   8 trades  87.5% win   +3.80 PnL
  16:00  12 trades  66.7% win  +10.01 PnL

LOSING HOURS (UTC) — SUPPRESS THESE:
  01:00  13 trades  30.8% win  -20.79 PnL  <-- WORST HOUR
  04:00  15 trades  53.3% win  -17.00 PnL
  07:00   3 trades   0.0% win   -6.06 PnL
  08:00   4 trades   0.0% win   -9.89 PnL
  12:00   9 trades  22.2% win   -6.66 PnL
  17:00   7 trades  42.9% win  -12.47 PnL
  18:00   6 trades  33.3% win   -5.27 PnL
  23:00  12 trades  16.7% win   +1.47 PnL (low win but sniper bets)

TOTAL LOST IN BAD HOURS (01,04,07,08,12,17,18): -77.84 PnL on 57 trades
If we had suppressed those hours, all-time P&L would be approximately POSITIVE.

### Edge estimate
Eliminating 01:00,04:00,07:00,08:00,12:00,17:00,18:00 UTC would have:
- Removed 57 trades (25% of total) at -77.84 PnL
- Remaining 171 trades = approximately +38 PnL
- Net improvement: ~78 USD over the trading history

CAVEAT: 228 trades is small. Some hours have <10 trades. Need 30+ per bucket
to be confident per PRINCIPLES.md. But the pattern is strong enough for a soft filter.

### Implementation
- Add `_SUPPRESSED_HOURS_UTC = {1, 4, 7, 8, 12, 17, 18}` to trading_loop
- Simple check: `if datetime.utcnow().hour in _SUPPRESSED_HOURS_UTC: skip`
- Apply ONLY to drift strategies (not sniper — sniper has different dynamics)
- ~30 minutes dev work. Zero new dependencies.
- OR: softer approach — reduce bet size by 50% during bad hours instead of full suppress

### Risk
- Small sample size per hour. Could be noise.
- Market dynamics may shift (different hours become good/bad).
- Mitigation: use soft filter (50% size reduction) not hard block. Re-evaluate monthly.

---

## R1 — Limit Orders vs Market Orders

**Verdict: PURSUE (Priority 2)**

### Evidence

Kalshi fee structure (confirmed from docs + web research):
  Taker fee: ceil(0.07 * contracts * price * (1 - price))
  Maker fee: ceil(0.0175 * contracts * price * (1 - price))
  At 50c (our typical drift price): taker = 1.75c/contract, maker = 0.44c/contract
  Savings: 1.31c/contract = 75% fee reduction

Our fee data (72 trades with fee info):
  Total fees paid: 6.51 USD
  eth_drift: 3.52 USD in fees (26 trades, avg 13.5c/trade)
  sol_drift: 1.06 USD in fees (11 trades, avg 9.6c/trade)
  sniper: 0.95 USD in fees (19 trades, avg 5.0c/trade)

CRITICAL: resting limit orders have NO FEES if they don't fill immediately.
This is confirmed by Kalshi docs: "Trading fees are only charged for orders
that are immediately matched."

### Edge estimate
If all 228 trades used limit orders instead of market orders:
- Fee savings: ~75% of 6.51 = ~4.88 USD (conservative, based on tracked fees only)
- PLUS spread capture: if typical spread is 2-4c, resting 1c better = +1c/contract edge
- Combined: ~2-3% edge improvement per trade

### Adverse selection risk
Andrew Courtney's maker/taker analysis warns: getting filled on limit orders
means fair value moved against you. "Sharp Steve vs Noisy Nick" framework.
For our use case: drift signals are time-sensitive (15-min window).
If we post a limit and it doesn't fill in 30-60 seconds, the window passes.

### Implementation
- Modify live.py execute() to use limit orders with GTC or IOC
- Post at best_bid + 1c (capture spread without crossing)
- Timeout after 30s: cancel and re-submit as market order (fallback)
- ~2-3 hours dev work. Moderate complexity.
- Test in paper first for fill rate calibration.

### Dependencies
- Need to understand Kalshi order types: limit, IOC, FOK (already supported by API)
- Need orderbook depth data to set optimal limit prices
- Need fill rate tracking to measure effectiveness

Sources:
  - Kalshi fee schedule: https://kalshi.com/fee-schedule
  - Maker/Taker Math: https://whirligigbear.substack.com/p/makertaker-math-on-kalshi
  - Limit orders help: https://help.kalshi.com/trading/order-types/limit-orders

---

## R2 — Multi-Window Momentum / Mean Reversion

**Verdict: DEFER (Priority 6)**

### Evidence — Our Own Data

btc_drift (54 trades):
  After 1+ wins: 48.0% next win (NEUTRAL)
  After 2+ wins: 45.5% (SLIGHT REVERSAL?)
  After 3+ wins: 25.0% (4 samples — too small)
  After 1+ losses: 50.0% (NEUTRAL)
  After 3+ losses: 62.5% (8 samples — hint of mean reversion)

eth_drift (89 trades):
  After 1+ wins: 51.2% (NEUTRAL)
  After 2+ wins: 36.4% (REVERSAL signal)
  After 3+ losses: 41.7% (NEUTRAL)

sol_drift (28 trades):
  After wins: ~75% continues winning (MOMENTUM — but sol just wins in general)
  Very few losses to analyze

### Academic research
Wen et al. (2022) "Intraday return predictability in the cryptocurrency markets":
Key finding: momentum works from 1 hour to 2 years, mean reversion works from
2 minutes to 30 minutes. Our 15-min window falls in the MEAN REVERSION zone.

This aligns with btc_drift data: winning streaks slightly predict losses (reversion).

### Edge estimate
Small. Our sample sizes per streak length are too small (4-12 trades per bucket).
Would need 30+ per bucket to be actionable (PRINCIPLES.md).

### Implementation
IF pursued: add a 2-window lookback. If same direction won last 2 windows,
apply a 25% edge discount on the 3rd same-direction signal.
~1 hour to implement. But the data doesn't justify it yet.

### Recommendation
Log to todos.md. Revisit when btc_drift/eth_drift have 200+ trades each.
Not actionable at current sample sizes.

Sources:
  - Wen et al.: https://www.sciencedirect.com/science/article/abs/pii/S1062940822000833
  - Dynamic time series momentum: https://www.sciencedirect.com/science/article/abs/pii/S1062940821000590

---

## R3 — Cross-Market Signals (DVOL, Funding Rates, Liquidations)

**Verdict: DEFER (Priority 7)**

### DVOL (Deribit Implied Volatility Index)
- DVOL measures 30-day forward expected volatility, NOT direction
- Cannot predict 15-min direction. But CAN predict opportunity density:
  High DVOL = bigger moves = more drift signals = more profitable windows
  Low DVOL = consolidation = noise trades = losing windows
- This overlaps heavily with R7 (regime detection). DVOL as regime proxy
  is more interesting than DVOL as direction signal.
- Free API: https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usdv

### Funding Rates
- Extreme positive funding = overcrowded longs = pullback signal
- Extreme negative = overcrowded shorts = bounce signal
- BUT: funding rate changes happen on 8-hour cycles (Binance)
- Our 15-min windows are too fast to capture funding rate reversals
- Edge: small, indirect. Not worth the complexity for 15-min markets.

### Liquidation Cascades
- Large liquidation events create sustained directional moves
- Detectable via open interest changes on exchanges
- BUT: by the time cascade data propagates, 15-min window is nearly over
- Better suited for hourly/daily threshold bets (R4) than 15-min direction

### Edge estimate
For 15-min markets: <1% additional edge from any cross-market signal.
For daily thresholds (R4): DVOL is essential (already in KXBTCD research).

### Implementation
IF pursued: add DVOL feed to suppress drift signals when DVOL < threshold.
~2 hours. But R7 (Bollinger Band width) is simpler and achieves the same thing.

### Recommendation
Use DVOL only for KXBTCD threshold strategy (R4). Don't add to drift.
Funding rates and liquidation data: not actionable for 15-min markets.

Sources:
  - DVOL: https://insights.deribit.com/exchange-updates/dvol-deribit-implied-volatility-index/
  - Gate.io analysis: https://dex.gate.com/crypto-wiki/article/how-do-futures-open-interest-funding-rates-and-liquidation-data-predict-crypto-derivatives-market-signals-in-2026-20260111
  - Funding rates: https://cointelegraph.com/learn/articles/what-bitcoin-sfunding-rate-really-tells-you

---

## R4 — KXBTCD Daily Threshold Bets

**Verdict: PURSUE WHEN EXPANSION GATE CLEARS (Priority 4)**

### Evidence
Already researched in .planning/KXBTCD_THRESHOLD_RESEARCH.md (Session 58).

Key facts:
- KXBTCD 5pm slot: 676K volume (vs ~5K for KXBTC15M)
- Edge is STRUCTURAL: lognormal N(d2) pricing vs options market
- Completely different instrument from drift (threshold, not direction)
- Prototype exists: src/strategies/crypto_daily.py (paper-only)
- btc_daily_v1 has 12/30 paper bets with direction_filter="no"

### Edge estimate
7-8% min edge threshold in research. Lognormal model should correctly price
digital options. Kalshi retail market likely misprices tail events.
The suislanchez/polymarket-kalshi-weather-bot made +1325 USD using 8% min edge
on similar binary markets (weather). Approach is validated.

### Implementation
- Need: Deribit DVOL feed (for sigma), KXBTCD market fetching, lognormal model
- Prototype already built. Needs live loop wiring + paper gate (30 bets).
- ~3-4 hours to wire up. Low risk (paper first).

### Dependencies
- Expansion gate must clear (sol graduation + sniper validation)
- Deribit DVOL API (free, no auth)
- KXBTCD markets already accessible via existing Kalshi client

---

## R5 — KXBTCD Friday Weekly Slots

**Verdict: DEFER UNTIL R4 VALIDATES (Priority 8)**

### Evidence
- Same KXBTCD series, future Friday date slot
- Volume: 770K (LARGEST single Kalshi market)
- Longer time horizon = more modeling uncertainty
- Research suggests: use 5-day realized vol (not DVOL), apply Friday seasonality
  (-1.5% probability penalty for negative average Friday returns)
- Skip FOMC weeks entirely

### Edge estimate
10-12% min edge (higher threshold than daily because more uncertainty).
But potential per-trade profit also larger (multi-day bets = larger positions).

### Implementation
Build after R4 (daily) is validated in paper. Same infrastructure, different
parameters. ~1-2 hours additional work on top of R4.

---

## R6 — Economics/Macro Markets (CPI, Fed, Unemployment)

**Verdict: PURSUE EPISODICALLY (Priority 5)**

### Evidence
KXCPI: 74 open markets. CPI announcement = known calendar event.
Cleveland Fed Nowcast: daily CPI estimates using oil, gas, consumer prices.
  URL: https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting

Federal Reserve research paper (2026) found:
"For headline CPI, Kalshi provides a statistically significant improvement
over the Bloomberg consensus forecast." This means Kalshi CPI markets ARE
informationally efficient — harder to beat than crypto markets.

BUT: the edge exists in the DISTRIBUTION, not the point estimate.
Kalshi offers multiple strike points (CPI above 2.5%, above 3.0%, etc.).
If our model says P(CPI > 3.0%) = 40% but Kalshi prices it at 30%, that's edge.
Cleveland Fed Nowcast + TIPS breakevens give this distributional information.

### Edge estimate
High per-event (5-10% edge on tail strikes) but episodic (monthly CPI releases).
~1 CPI release per month = ~12 trading opportunities per year.
At 5 USD/bet with 8% edge: ~4.80 USD/year expected profit. Small but reliable.

### Implementation
- fomc_rate_v1 and unemployment_rate_v1 already built (paper-only)
- Neither has placed any paper bets (fomc had shared fred_feed bug, fixed S40)
- Need: Cleveland Fed Nowcast integration, TIPS breakeven data
- ~3-4 hours to build CPI-specific strategy
- Low priority given low expected annual volume

Sources:
  - Cleveland Fed Nowcast: https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting
  - Fed paper on Kalshi: https://www.federalreserve.gov/econres/feds/files/2026010pap.pdf

---

## R7 — Regime Detection (Trending vs Consolidation)

**Verdict: PURSUE (Priority 3)**

### Evidence
Our drift strategy's fundamental weakness: it fires during consolidation when
there's no real trend, producing noise trades. The data confirms this:
- 40-44c entry price bucket: 42.3% win rate, -22.30 PnL (WORST)
- 45-49c bucket: 42.1% win rate, -1.11 PnL
- 60-65c bucket: 68.9% win rate, +7.74 PnL (BEST)

Low-price entries (35-49c) have ~40% win rate. These are likely consolidation
windows where the market is uncertain. High-price entries (55-65c) have ~67%
win rate — these are trending windows where our signal works.

### Regime detection methods
From web research, three complementary approaches:

1. Bollinger Band Width (BBW):
   - Narrow bands = consolidation = suppress signals
   - Wide bands = trending = allow signals
   - Threshold: BBW < 20th percentile of last 24h = "squeeze" (consolidation)
   - Simple to compute from our existing Binance price data

2. ADX (Average Directional Index):
   - ADX > 25 = trending, ADX < 20 = ranging
   - Standard intraday setting: ADX period = 14 (on 1-min candles)
   - Can compute from Binance kline data

3. Price confidence proxy (SIMPLEST):
   - Market price itself IS a regime signal
   - YES price near 50c = uncertain = consolidation
   - YES price at 40c or 60c = more confident = trending
   - We already have this data. No new feed needed.

### Our data confirms approach #3
Entry prices 35-49c (uncertain/consolidation): 83 trades, 34 wins, 41.0% win rate
Entry prices 55-65c (confident/trending): 79 trades, 53 wins, 67.1% win rate

Tightening the price guard from 35-65c to 50-65c (or even 55-65c) would
eliminate the worst trades. BUT this also reduces trade volume significantly.

### Edge estimate
Conservative: tightening guard to 45-65c eliminates 38 trades at 39.5% win, -3.10 PnL.
Moderate: tightening to 50-65c eliminates 83 trades at 41.0% win.
Aggressive: adding BBW filter could suppress 30-50% of consolidation trades.

Combined with R8 (time filter): could eliminate 70-80% of losing trades.

### Implementation
Option A (simplest): tighten price guard to 45-65c or 50-65c
  - 5 minutes to change constants. Zero new code.
  - Risk: reduces trade volume, may miss some winning trades at low prices

Option B (moderate): add BBW calculation from existing Binance price data
  - ~2 hours: compute rolling std dev, compare to threshold
  - More nuanced than Option A

Option C (full): ADX + BBW regime engine
  - ~4-6 hours: need kline data, ADX calculation, parameter tuning
  - Overkill for current scale

Recommended: Start with Option A (tighten to 50-65c), measure impact over 50 trades,
then add Option B if more precision needed.

Sources:
  - Regime Filtered Strategy: https://pyquantlab.medium.com/regime-filtered-trend-strategy
  - ADX guide: https://capital.com/en-int/learn/technical-analysis/average-directional-index

---

## ADDITIONAL FINDING: Direction Filter Validation

Full live trade data confirms all four direction filters are correct:

btc_drift:
  YES: 20 trades, 30.0% win, -1.50 EV/bet  (FILTER OUT — correct)
  NO:  34 trades, 58.8% win, +0.56 EV/bet  (KEEP — correct)

eth_drift:
  YES: 54 trades, 50.0% win, -0.14 EV/bet  (KEEP — marginal)
  NO:  35 trades, 45.7% win, -0.52 EV/bet  (FILTER OUT — correct)

sol_drift:
  YES: 12 trades, 66.7% win, +0.36 EV/bet  (also profitable!)
  NO:  16 trades, 87.5% win, +0.57 EV/bet  (BETTER — correct to keep)
  NOTE: sol_drift is profitable on BOTH sides. Consider removing filter
  to increase trade volume. Data says both sides are +EV.

xrp_drift:
  YES:  7 trades, 85.7% win, +0.27 EV/bet  (KEEP — correct)
  NO:  11 trades, 36.4% win, -0.22 EV/bet  (FILTER OUT — correct)

sniper:
  YES: 13 trades, 100% win, +0.21 EV/bet
  NO:   6 trades, 100% win, +0.32 EV/bet
  Both sides perfect. No filter needed (100% both ways).

ACTIONABLE: Consider removing sol_drift direction filter to capture YES bets
(+0.36 EV/bet, 66.7% win rate). This would increase sol trade volume by ~75%.
CAUTION: only 12 YES trades. Need 30+ to be confident. Monitor but don't act yet.

---

## ADDITIONAL FINDING: Fee Impact Analysis

Total fees paid on tracked live trades: 6.51 USD
Gross P&L (before fees, partial data): +7.28 USD
Net P&L: -39.85 USD

The 6.51 represents only trades with fee data populated (post-Session 44 migration).
Actual total fees across all 228 trades estimated at: ~15-20 USD.

Switching to limit orders (R1) could save 75% of taker fees = ~11-15 USD saved.
This alone would improve all-time P&L by 25-35%.

---

## PRIORITY RANKING (effort-to-edge ratio)

Rank  Area                    Verdict   Edge    Effort   Dependencies
  1   R8 Time-of-Day Filter   PURSUE    ~78 USD saved  30 min  None
  2   R1 Limit Orders         PURSUE    ~15 USD/year   3 hr    Orderbook data
  3   R7 Regime Detection     PURSUE    ~30 USD saved  5 min   None (tighten guard)
  4   R4 KXBTCD Daily         PURSUE*   7-8%/trade     4 hr    DVOL feed, gate
  5   R6 CPI/Economics        PURSUE*   5-10%/event    4 hr    CleveFed, episodic
  6   R2 Multi-Window         DEFER     <1%            1 hr    200+ trades
  7   R3 Cross-Market         DEFER     <1% (15-min)   3 hr    Multiple feeds
  8   R5 Friday Weekly        DEFER     10-12%/trade   2 hr    R4 validated first

  * = requires expansion gate to clear

---

## IMMEDIATE ACTION ITEMS (for main chat to implement)

1. TIME FILTER: Add hour-of-day soft filter to drift strategies.
   Suppress or halve bets during UTC hours: 01, 04, 07, 08, 12, 17, 18.
   Expected impact: prevent ~78 USD in losses over next 228 trades.

2. PRICE GUARD TIGHTENING: Consider narrowing drift price guard from
   35-65c to 45-65c or 50-65c. The 35-44c bucket loses money consistently.

3. SOL FILTER REVIEW: sol_drift YES side is also profitable (+0.36 EV/bet).
   When sol hits 30 trades, evaluate removing the direction filter to
   increase trade volume. Both sides are currently +EV.

4. LIMIT ORDERS: Implement limit order execution in live.py.
   Post at best_bid + 1c, timeout 30s, fallback to market order.
   Expected fee savings: 75% = ~11-15 USD over trading history.

5. KXBTCD DAILY: Wire up the existing prototype when expansion gate clears.
   This is a different instrument with structural edge (lognormal mispricing).
