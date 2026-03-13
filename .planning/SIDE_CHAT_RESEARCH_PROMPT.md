# SIDE CHAT — Edge Research & New Market Exploration
# Copy-paste this into a fresh Claude Code chat.
# Model: Opus 4.6. This is RESEARCH ONLY — no live code changes.

You are researching new profitable edges for polymarket-bot — a real-money
algorithmic trading bot on Kalshi (CFTC-regulated US prediction market exchange).

## MANDATORY READING FIRST
```
cat CLAUDE.md
cat SESSION_HANDOFF.md
cat .planning/STRATEGY_PNL_ANALYSIS_S60.md
cat .planning/STRATEGIC_DIRECTION.md
cat .planning/KALSHI_MARKETS.md
cat .planning/PRINCIPLES.md
tail -100 .planning/CHANGELOG.md
```

## CONTEXT — WHERE WE ARE

Bot has 5 live strategies on Kalshi 15-minute crypto direction markets (KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M).
- sol_drift: PROFITABLE. 79% win rate, +13.48 USD, 28/30 bets. Our best signal.
- expiry_sniper: PROFITABLE. 100% win rate (15/15), +3.00 USD. Favorite-longshot bias.
- eth_drift: MARGINAL. 49% win rate, -16.24 USD. YES-only filter helped but still losing.
- btc_drift: LOSING. 48% win rate, -11.12 USD. 54 bets = enough data to confirm.
- xrp_drift: TOO EARLY. 56% win rate, -0.55 USD, 18 bets.

All-time live P&L: -36.17 USD. Need +161 more to hit +125 USD goal.
Bankroll: ~112 USD. Max bet: 5.00 USD (Stage 1).

## YOUR MISSION

Research these areas IN PRIORITY ORDER. For each, answer:
1. Does this edge exist? (cite evidence — academic papers, forum posts, trading results)
2. Can we capture it on Kalshi specifically? (API limitations, market structure, liquidity)
3. What's the expected edge size? (need >2% to overcome Kalshi taker fees of ~2%)
4. How complex to implement? (hours of dev work)
5. What data do we need that we don't have?

### RESEARCH AREAS (priority order)

**R1 — Limit Orders vs Market Orders on Kalshi**
We currently always TAKE (market orders). Market makers profit from spread.
Can we place limit orders at better prices and still get filled near expiry?
Kalshi API: POST /trade-api/v2/portfolio/orders supports limit orders.
Key question: what's the typical bid-ask spread on KXBTC15M markets?
If spread is 4-6c, placing limits 2c better than mid = structural edge.

**R2 — Multi-Window Momentum / Mean Reversion**
We use single-window drift only. Do 15-min crypto markets exhibit:
- Momentum persistence (up 3 windows in a row → 4th likely up)?
- Mean reversion (up 3 windows → 4th likely down)?
Research: is there published alpha on intraday crypto momentum at 15-min scale?

**R3 — Cross-Market Signals (Deribit DVOL, Funding Rates, Liquidations)**
Our only signal is Binance spot price drift. What other data predicts 15-min direction?
- Deribit DVOL (implied volatility index) — high vol = bigger moves = more opportunity?
- Perpetual funding rates — extreme positive = overcrowded long → reversal signal?
- Liquidation cascades — detect and trade in the direction of the cascade?
Research .planning/KXBTCD_THRESHOLD_RESEARCH.md — we already have DVOL research for threshold bets.

**R4 — KXBTCD Daily Threshold Bets (Hourly Slots)**
KXBTCD = "BTC price above $X at 5pm EDT?" — binary threshold.
Volume: 676K on 5pm slot. Much higher than 15-min direction markets.
We have a paper-only prototype (src/strategies/crypto_daily.py).
Research: what edge exists on daily thresholds? Is implied vol mispricing the tails?

**R5 — KXBTCD Friday Slots (Weekly Threshold)**
Same KXBTCD series but for Friday expiry. Volume: 770K (LARGEST on Kalshi).
No separate KXBTCW series — use KXBTCD with Friday date.
Research: are weekly thresholds more profitable than daily? Longer time horizon = more signal?

**R6 — Economics/Macro Markets (CPI, Fed Rate, Unemployment)**
KXCPI: 74 open markets. CPI announcement is a known calendar event.
Research: can we get an edge from inflation expectations data (TIPS breakevens,
Cleveland Fed Nowcast) vs Kalshi implied probabilities?
We have fomc_rate_v1 (paper) and unemployment_rate_v1 (paper). Neither has placed bets.

**R7 — Regime Detection (Trending vs Consolidating)**
Our drift strategy works when price trends persist. In consolidation, it noise-trades.
Research: can we detect regime in real-time? Bollinger Band width, ADX, ATR?
If we could suppress drift signals during consolidation, we'd eliminate ~50% of losing trades.

**R8 — Time-of-Day Filtering**
Some hours may have zero edge. US market hours (13:30-20:00 UTC) have different
dynamics than Asia hours (00:00-08:00 UTC).
Research: does our own historical data show time-of-day P&L patterns?
Query the DB: analyze win rate and P&L by hour of day for each strategy.

## OUTPUT FORMAT

For each research area, produce:
1. **Verdict**: PURSUE / DEFER / SKIP
2. **Evidence**: links, papers, data
3. **Edge estimate**: X% expected edge
4. **Implementation effort**: hours
5. **Dependencies**: what we need (data feeds, API access, etc.)
6. **Priority rank**: 1-8 based on effort-to-edge ratio

Write findings to: `.planning/EDGE_RESEARCH_S60.md`

## RULES
- DO NOT modify any live code. This is research only.
- DO NOT restart or touch the bot. Another chat is supervising it.
- DO NOT change any strategy parameters.
- You CAN query the database (data/polybot.db) for historical analysis.
- You CAN probe Kalshi API for market data (read-only).
- You CAN search the web for academic papers, forum discussions, etc.
- FONT RULES: No markdown tables (| --- |). No dollar signs in prose.
- Write ALL findings to .planning/ files for future sessions to read.
