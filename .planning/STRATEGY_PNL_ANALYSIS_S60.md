# STRATEGY P&L ANALYSIS — Session 60 (2026-03-12)
# All data from live bets only (is_paper=0). DB-verified.

## THE CORE PROBLEM: ASYMMETRIC WIN/LOSS SIZES

Sniper wins small (+0.10 to +0.45 per bet). Drift losses are large (-4.68 to -5.00 per bet).
One drift loss wipes out 10-20 sniper wins. This is the #1 P&L drag.

### Why losses are bigger than wins (structural, not a bug):
- Drift bets at 35-50c YES: win = payout (100-price)c, loss = price c.
  At 39c YES: win = +6.10 per contract. Loss = -3.90. Risk/reward is FAVORABLE.
  At 50c YES: win = +5.00. Loss = -5.00. Even money.
- BUT: when drift fires at 35-43c (bearish conditions), market is pricing
  it as only 35-43% likely to go up. Our model must be RIGHT more than
  (price/100)% of the time to profit. At 39c, need >39% win rate.
- eth_drift YES win rate: 51% (27/53). At avg entry 49.3c, breakeven = ~49%.
  Edge: ~2% above breakeven. PAPER THIN.
- Compare sol_drift NO: 79% win rate, avg entry around 51c NO. MASSIVE edge.

### eth_drift at 49% overall is barely above breakeven because:
1. YES-only (post-filter) is 51% — marginal
2. The 5 most recent YES bets at 35-43c were ALL losses (bearish session)
3. Model says "ETH will go up" but during sustained bearish moves, it's wrong
4. Payout asymmetry is IN OUR FAVOR (win more than we lose per bet at <50c)
   but frequency (51%) barely exceeds the breakeven threshold

### btc_drift at 48% (26W/28L) is BELOW breakeven:
- Direction filter "no" (NO-only) helps: NO at 60c+ entries = smaller risk
- But avg NO entry ~55c means breakeven ~45%. 48% is only +3% edge.
- 54 settled bets is decent sample. Strategy IS marginal. -11.12 USD all-time.

## PER-STRATEGY VERDICT (Session 60 data, all-time live)

### PROFITABLE — Scale these up
sol_drift_v1: 28 settled, 22W 6L (79%), +13.48 USD, Brier 0.177
  WHY IT WORKS: SOL is more volatile than BTC/ETH, drift signals are stronger,
  NO-only filter captures directional edge. Best strategy by every metric.
  NEXT: 2 more bets to 30 → Stage 2 analysis (10 USD max bet).

expiry_sniper_v1: 15 settled (15W 0L 100%), +3.00 USD
  WHY IT WORKS: Favorite-longshot bias. Near-expiry, market overestimates
  upset probability. We buy the favorite at 90-97c, get paid 100c.
  Cap raised from 10→20/day this session. 97% paper + 100% live win rate.
  SCALING: More windows = more profit. Each win = +0.10 to +0.45.

### MARGINAL — Monitor, don't expand
eth_drift_v1: 87 settled, 43W 44L (49%), -16.24 USD
  YES-only (post-filter S53): 53 bets, 27W (51%), -2.61 USD
  NO (pre-filter, disabled): 35 bets, 16W (46%), -18.31 USD
  VERDICT: YES filter helped enormously but strategy is barely positive.
  DO NOT raise bet size. Continue at Stage 1 cap. May need tighter price guard.

xrp_drift_v1: 18 settled, 10W 8L (56%), -0.55 USD
  YES-only (post-filter S54): small sample, need 30 to evaluate.
  VERDICT: Too early. Continue at micro-live (0.01 USD cap).

btc_drift_v1: 54 settled, 26W 28L (48%), -11.12 USD
  NO-only: 48% win rate at avg ~55c entry. Breakeven ~45%. Edge ~3%.
  VERDICT: Marginal negative. 54 bets is enough to say this is not strongly
  profitable. Continue at Stage 1 but DO NOT promote to Stage 2.

### DEAD/DISABLED
btc_lag_v1: 0 signals/week (HFTs priced it out). Dead strategy.
eth_orderbook_imbalance_v1: 33% win rate, -18.20 USD. Disabled live.

## WHAT OTHERS DO DIFFERENTLY (hypothesis, needs research)

People DO profit on 15-min crypto direction bets. Possible edges we're missing:
1. ORDER FLOW: reading Kalshi orderbook imbalance in real-time (we have this but
   calibration is poor — 27% error rate on signal_scaling)
2. MOMENTUM PERSISTENCE: multi-window momentum (if BTC up in last 3 windows,
   probability of next up > 50%). We use single-window drift only.
3. LIMIT ORDERS: market maker spread capture. We always take (market orders).
   Limit orders at 48c YES in a 50/50 market = free 2c edge. Needs queue management.
4. CROSS-MARKET SIGNALS: Deribit options (DVOL), funding rates, liquidation data.
   Our only signal is spot price drift in last 15 min.
5. REGIME DETECTION: trending vs consolidating markets. Drift works in trends.
   In consolidation, mean reversion (bet opposite to drift) may work better.
6. TIME-OF-DAY: Signal quality varies by session (US, EU, Asia hours).
   We haven't filtered by time. Some hours may have zero edge.

## ASYMMETRIC WIN/LOSS SOLUTION OPTIONS

The "stop losing big if we're only winning small" problem:

Option A — TIGHTER PRICE GUARD FOR DRIFT (e.g., 40-60c instead of 35-65c):
  Fewer bets, but each has better risk/reward. Losses capped at 60c max.
  Trade-off: miss signals at 35-40c that occasionally produce big wins.

Option B — SCALE DOWN LOSING STRATEGIES, SCALE UP WINNERS:
  eth_drift → micro-live (0.01 cap) since it's barely above breakeven.
  btc_drift → micro-live (0.01 cap) since it's below breakeven at 48%.
  sol_drift → keep at Stage 1 (5.00), promote to Stage 2 at 30 bets.
  sniper → already scaling (20/day cap).
  NET EFFECT: drift losses shrink to pennies, sol+sniper carry the P&L.

Option C — LIMIT ORDERS INSTEAD OF MARKET ORDERS:
  Place YES at (market_price - 2c) instead of taking the ask.
  If filled: 2c better entry. If not filled: no loss (saved the bet).
  Needs implementation but structurally profitable.

Option D — ADD MINIMUM CONFIDENCE GATE ON DRIFT:
  Only fire when drift exceeds 2x threshold (e.g., 0.10% instead of 0.05%).
  Fewer signals but each has stronger conviction. Reduces noise trades.

## RECOMMENDATION FOR MATTHEW

IMMEDIATE (no code changes, just operational):
- sol_drift + sniper are the profit engine. Everything else is research.
- SOL at 28/30 → 2 more bets to Stage 2 analysis. Priority #1.
- Sniper cap raised to 20/day — keep capturing every window.

DISCUSS WITH MATTHEW (requires parameter changes):
- Option B (scale down losers) is the wisest near-term move.
  Reduces btc_drift and eth_drift losses to pennies while sol+sniper run.
  PRINCIPLES.md says don't change under pressure — but this is data-driven
  with 54+ and 87+ bets respectively. This IS enough data to act on.
