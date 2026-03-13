# Side Chat Research Prompt — Session 61
# Feed this entire file to a fresh Claude Code chat opened in this project directory.
# Budget: 30% of 5-hour window. Model: Opus 4.6.

## CONTEXT

You are researching for polymarket-bot — a live Kalshi trading bot.
Read .planning/EDGE_RESEARCH_S60.md for the full research from last session.

The bot's expiry_sniper strategy just had its FIRST LOSSES:
- Lifetime: 20/22 wins (91%), NET -4.45 USD
- Average win: ~0.25 USD, average loss: ~4.65 USD
- Breakeven win rate at 93c entries: 93%. Current: 91%.
- At 95%+ true win rate, still +EV. But 22 trades is too small to confirm.

## RESEARCH TASK 1 — SNIPER OPTIMIZATION (highest priority)

The sniper buys at 90c+ when a coin has drifted in a direction with <3min left.
The thesis: at extreme prices near expiry, the Snowberg-Wolfers favorite-longshot
bias means the market underprices the favorite. Our edge is the last 2-3 minutes
of a 15-min window when the market is already very confident.

QUESTIONS TO ANSWER:
1. Is there an optimal ENTRY PRICE threshold? Currently fires at 90c+.
   At 90c: win +0.50, lose -4.50 → breakeven = 90%
   At 95c: win +0.25, lose -4.75 → breakeven = 95%
   At 98c: win +0.10, lose -4.90 → breakeven = 98%
   Higher price = safer bet but higher breakeven requirement.
   What does our paper data (75 bets) show for win rate by entry price bucket?

2. Is there an optimal TIME-TO-EXPIRY threshold? Currently fires at <3min.
   With less time remaining, the price should be MORE accurate (less uncertainty).
   But with MORE time, there's more chance of reversal.
   What does our data say about win rate by minutes_remaining bucket?

3. Should sniper have a MINIMUM DRIFT threshold? Currently any drift qualifies
   as long as price is 90c+. But a coin that drifted 0.01% and is at 90c is
   VERY different from one that drifted 1.0% and is at 98c.
   Do higher-drift entries win more often?

4. Multi-asset correlation: in the 22:30 window, BTC lost, SOL lost, ETH won.
   Should sniper avoid betting the same direction on correlated assets?
   (BTC and SOL are highly correlated). If BTC reverses, SOL likely does too.

HOW TO RESEARCH:
- Query the DB: data/polybot.db, table "trades", column "strategy" = "expiry_sniper_v1"
- Include BOTH paper (is_paper=1) and live (is_paper=0) for analysis
- price_cents column has entry price
- Look at edge_pct and win_prob columns for additional signal data
- Cross-reference with web research on favorite-longshot bias calibration

## RESEARCH TASK 2 — TIME-OF-DAY FILTER (from R8 in S60 research)

The S60 research found:
LOSING HOURS (UTC): 01, 04, 07, 08, 12, 17, 18 — combined -77.84 on 57 trades
PROFITABLE HOURS: 00, 03, 11, 14, 15, 16 — combined +50.94 on 68 trades

QUESTIONS:
1. Refresh this analysis with the LATEST DB data (228+ live trades now).
   Do the same hours still show as losers?

2. Cross-reference with crypto market microstructure research:
   - What happens at 01:00 UTC? (Asian session close?)
   - What happens at 04:00 UTC? (Asian session wind-down)
   - What happens at 07:00-08:00 UTC? (European session open?)
   - What happens at 12:00 UTC? (European/US overlap)
   - What happens at 17:00-18:00 UTC? (US afternoon, futures close)

3. Is there a simpler proxy: just suppress signals when volatility is low?
   Low-volatility hours = consolidation = drift signals are noise.
   This might capture the same effect without hardcoding hours.

## RESEARCH TASK 3 — LIMIT ORDER FEASIBILITY (from R1 in S60 research)

Kalshi fee schedule:
  Taker: ceil(0.07 * contracts * price * (1-price))
  Maker: ceil(0.0175 * contracts * price * (1-price))

We pay ~15-20 USD in total fees across all trades. Limit orders save 75%.

QUESTIONS:
1. What are Kalshi's order types? (limit, IOC, FOK, GTC?)
2. What's the typical orderbook depth on KXBTC15M at 50c?
3. If we post a limit at best_bid + 1c, what fill rate can we expect?
4. For sniper (entry at 90-98c): what's the spread at those prices?
   If spread is 1c (90c bid, 91c ask), limit orders save nothing.
   If spread is 2c+, limit orders capture 1c+ of edge per trade.

## OUTPUT

Write findings to .planning/EDGE_RESEARCH_S61.md
Include raw data, statistical analysis, and actionable recommendations.
Mark each recommendation as:
  IMPLEMENT NOW (zero risk, clear evidence)
  IMPLEMENT CAREFULLY (some risk, needs paper validation)
  DEFER (insufficient evidence or low priority)
