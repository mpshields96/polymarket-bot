# EDGE RESEARCH — Session 62 (2026-03-13)
# Comprehensive audit of ALL Kalshi markets + academic research + Reddit sweep

## 1. FULL KALSHI MARKET AUDIT — RAW NUMBERS

303,578 open markets | 9,013 series | 10,000+ events | 16 categories

### Category Volume (what people actually trade)

Sports: 316M total vol, 38.9M 24h (42% of ALL Kalshi)
Politics: 190M total, 2.6M 24h (25%)
Entertainment: 67M total, 3.0M 24h
Economics: 48M total, 2.5M 24h
Elections: 37M total, 0.6M 24h
Crypto: 31M total, 1.9M 24h (only 4% of Kalshi!)
Sci/Tech: 17M total
Financials: 7.3M total
Climate/Weather: 1.9M total

### KEY INSIGHT: We trade in the smallest liquid category (crypto 4%)
Sports is 10x larger. Economics is 1.5x. Even Entertainment is 2x.

### Top ACTIVE series by 24h volume (what's trading RIGHT NOW)
PGA golf: 16.8M 24h
ATP tennis: 1.6M 24h
Fed decisions: 1.7M 24h
March Madness: 1.1M 24h
NBA games: 918K 24h
BTC daily (KXBTCD): 800K 24h
Oscars: 772K 24h
Cricket: 731K 24h

### SWEET SPOT: Uncertain + Volume (near 50c = market doesn't know the answer)
NCAA spreads: 145 active, 49% near 50c, 25% wide spreads
NCAA totals: 113 active, 58% near 50c
NBA player props: 109 active, 37% near 50c
NHL games: 44 active, 89% near 50c (!)
MLB spring training: 81% near 50c
ATP tennis: 33 active, 55% near 50c

### Raw data files
data/kalshi_all_markets_raw.json — 303K markets
data/kalshi_all_series_raw.json — 9K series
data/kalshi_all_events_raw.json — 10K events
data/kalshi_audit_report.json — summary

---

## 2. ACADEMIC EVIDENCE — WHELAN PAPER (300K+ Kalshi contracts)

Source: Whelan/Burgi/Deng "Makers and Takers: The Economics of the Kalshi Prediction Market"
VoxEU summary: cepr.org/voxeu/columns/economics-kalshi-prediction-market

### Key numbers
- Average pre-fee return ALL contracts: -20%
- Average post-fee return: -22%
- TAKERS lose ~32% on average
- MAKERS lose ~10% on average (22% structural advantage for makers!)
- **MAKERS BUYING CONTRACTS ABOVE 50c: +2.6% pre-fee, +1.9% AFTER FEE**
  ^^^ THIS IS THE SINGLE MOST ACTIONABLE NUMBER IN ALL OUR RESEARCH
- Contracts under 10c: investors lose OVER 60% of their money
- 5c contracts win only 2% of time (implied 5%) = -60% loss rate
- 95c contracts win 98% of time = small positive profit
- Bias appears across ALL categories: politics, entertainment, AND economics
- Favorite-longshot bias is STRUCTURAL (not category-specific)
- Takers suffer far bigger losses on longshot contracts than makers

### Return by price bucket (monotonic)
- Under 10c: -60%+ loss
- 10c-50c: negative returns, declining as price drops
- Above 50c: SMALL POSITIVE returns (statistically significant)
- 95c+: consistent small positive profit
- Pattern is monotonic — returns decline steadily as odds lengthen

### What this means for us
- Our sniper (90c+) IS the academically validated edge
- Our drift (35-65c) is in the neutral zone — no structural help
- SWITCHING TO LIMIT ORDERS (maker) on 50c+ contracts = +1.9% return after fees
- Being a TAKER on anything below 10c = catastrophic
- The -20% average return means most Kalshi bettors lose
- We should be MAKERS buying FAVORITES (above 50c) = documented profit

---

## 2B. FAVORITE-LONGSHOT BIAS — DEEP ACADEMIC DATA

### Snowberg & Wolfers (2010) — 6.4 MILLION horse starts
- 865,934 races, North America 1992-2001
- Horses at 100/1 or greater: -61% return
- Horses at 4/1 to 9/1: approximately -18% (constant across range)
- Random betting: -23% average returns
- Betting the FAVORITE in every race: -5.5% return
- Pattern is monotonic — returns decline steadily as odds lengthen
- Root cause: probability MISPERCEPTIONS (Prospect Theory), not risk-love
- Confirmed in college basketball, college football, AND on Kalshi

### What this means for us
- The bias is not Kalshi-specific — it's a deep human cognitive bias
- People systematically overestimate the probability of unlikely events
- On Kalshi: longshots (under 10c) are overpriced, favorites (above 50c) are underpriced
- This VALIDATES our sniper (90c+ = deep favorite territory)
- This EXPLAINS why drift at 35-65c is neutral — we're in between the bias

## 3. QUANTPEDIA — SYSTEMATIC EDGES

Source: quantpedia.com/systematic-edges-in-prediction-markets/

### Identified edges
1. Inter-exchange arbitrage (Kalshi vs Polymarket) — 1-2% discrepancies, exists seconds only
2. Intra-exchange arbitrage (contract sum != 1.00) — rare
3. Favorite-longshot bias — systematic, persistent

### Football betting study (12,084 matches)
- Betting favorites: -3.64% average profit
- Betting outsiders: -26.08% average profit
- Spread: 22.4% return difference (favorites massively outperform)

### Arbitrage reality
- Most opportunities exist "only for a few seconds, at best a few minutes"
- Transaction costs reduce potential profits significantly
- Polymarket "leads Kalshi due to higher liquidity"

---

## 4. PINNACLE CLOSING LINE VALUE (CLV) — THE KEY METRIC

### What it is
Pinnacle closing line = the sharpest odds in the market right before event starts.
Pinnacle closing odds correlate with actual outcomes at r-squared = 0.997.
Consistently beating Pinnacle closing line = proof of genuine edge.
CLV lets you evaluate edge with FAR FEWER samples than P&L alone.
A 2% CLV over 200 bets is statistically significant.
P&L needs 1000+ bets to distinguish skill from variance.

### Pinnacle API status (as of July 2025)
- CLOSED to general public since July 23, 2025
- Now bespoke data services for select high-value bettors only
- Alternative: apply to api@pinnacle.com for academic/handicapping access

### DATA SOURCES WE CAN USE (ranked by priority)

1. the-odds-api.com — WE ALREADY HAVE THIS (500 credits/month)
   - INCLUDES PINNACLE as an EU bookmaker
   - GET /v4/sports/{sport}/odds?bookmakers=pinnacle returns current Pinnacle line
   - Covers NBA, NCAAB, NHL, MLB, NFL
   - Poll every 5 min near game time to capture closing line
   - ZERO ADDITIONAL COST

2. BALLDONTLIE API — FREE API key
   - GET /nba/v2/odds — returns Kalshi, Polymarket, DraftKings, FanDuel, Pinnacle IN ONE CALL
   - Also covers NFL, NHL, MLB, NCAAB, NCAAF
   - Best for direct Kalshi-vs-Pinnacle comparison

3. OddsPapi (oddspapi.io) — free tier
   - 350+ bookmakers including Pinnacle
   - GET https://api.oddspapi.io/v4/odds?bookmakers=polymarket,pinnacle,kalshi
   - Historical odds timestamped (can reconstruct CLV)
   - WebSocket on Pro tier for sub-second latency

4. BettingIsCool API — 22 EUR/month
   - GET /api/closing — devigged true odds with results
   - 2.6B+ odds records, 44 sports, data back to 2021
   - Purpose-built for CLV analysis and model calibration

5. PS3838 API (Pinnacle mirror via Sportmarket)
   - PyPI: ps3838api — reportedly still open access

### Kalshi vs Sportsbook discrepancies documented
- balldontlie.io NBA: 1-2% probability difference (Memphis +102 Kalshi vs -103 to -105 sportsbooks)
- Prediction markets have "different liquidity pools" and "different participant bases"
- Fees can turn 3% gross arb into 1-2% net — but LIMIT ORDERS fix this
- NO RETAIL TOOL EXISTS that systematically compares Kalshi sports vs Pinnacle — open niche

### The CLV signal formula
pinnacle_devigged_prob - kalshi_implied_prob > min_edge_threshold
--> place LIMIT ORDER on Kalshi at 1-2c better than current price (saves maker fees)

---

## 5. SPORTS: THE BIG UNTAPPED OPPORTUNITY

### Why sports on Kalshi might be different
- 42% of ALL Kalshi volume is sports
- NCAAB is THE MOST TRADED SPORT ON KALSHI — 2.27B USD in Feb 2026 alone
  (surpassing NFL at 1.8B and NBA at 1.74B)
- NCAA spreads: 49% of markets near 50c (market doesn't know the answer)
- NHL games: 89% near 50c with decent volume
- NBA player props: 37% near 50c
- NCAAB has 350+ teams — retail bettors worst at pricing mid-major conference tournaments
- March Madness is happening RIGHT NOW = massive volume + maximum inefficiency

### Why sports might have edge vs crypto
- Crypto 15-min: HFTs reprice in seconds, we can't compete on speed
- Sports games: outcomes unknown for hours, domain knowledge > speed
- Sports data is abundant and free (stats APIs everywhere)
- The crowd on Kalshi sports may be less sophisticated than crypto HFTs
- Pinnacle closing line gives us a sharp benchmark to compare against

### What we'd need to build
- Real-time odds comparison: Kalshi prices vs sharp book consensus
- Focus on sports where Kalshi deviates from Pinnacle/sharp consensus
- Use limit orders (maker not taker) to capture the 22% structural advantage
- NCAA basketball during March Madness = massive volume RIGHT NOW

---

## 6. ECONOMICS MARKETS — DOMAIN KNOWLEDGE EDGE

### CPI/FOMC — NBER Working Paper #34702 (Diercks, Katz, Wright)
- Kalshi FOMC modal forecast: PERFECT record predicting fed funds rate day-before EVERY meeting since 2022
- Statistically significant improvement over fed funds futures AND NY Fed Survey
- September 2024: Kalshi correctly predicted 50bp cut when professional forecasters were divided
- CPI headline: 40.1% lower mean absolute error vs Bloomberg Wall Street consensus
- During shocks > 0.2pp: 50% lower MAE than consensus
- 75% win rate when Kalshi participants disagreed with consensus
- Day before release with 0.1pp+ deviation: ~82.4% shock prediction rate
- "Positive CPI surprises moved fed funds rate distribution FOUR TIMES more than negative ones"
- Fed decisions (KXFEDDECISION): 1.7M 24h volume, 22% near 50c, 22% wide spreads
- CPI (KXCPI): 47 active markets, 32% near 50c
- IMPORTANT: paper does NOT identify systematic retail-exploitable biases in macro
  Kalshi prices ARE efficient — they match or beat professional forecasters
  The edge here is in being ON the right side of the consensus, not against it
- Our FOMC strategy exists but has 0 paper bets — never properly tested

### Why this might work for us
- Less HFT competition (you can't speed-trade a monthly release)
- Domain knowledge matters (reading BLS methodology)
- Free external data (Cleveland Fed, Atlanta Fed GDP nowcast)
- Our existing fomc_rate_v1 and unemployment_rate_v1 already built

---

## 7. WEATHER — ENSEMBLE FORECAST EDGE

### GitHub weather bot (suislanchez/polymarket-kalshi-weather-bot)
- Uses 31-member GFS ensemble forecasts
- Compares ensemble probability vs Kalshi KXHIGH market prices
- Trades when edge > 8%
- Claims 1,325 USD sim profit
- Author admits: liquidity caps real profit at ~20 USD/week
- Our existing weather strategy doesn't use ensemble data

---

## 8. MAKER VS TAKER — THE SINGLE BIGGEST LEVER

Whelan paper: takers lose 32%, makers lose 10%.
THAT'S A 22% STRUCTURAL ADVANTAGE FOR LIMIT ORDERS.

### Kalshi taker fee formula: 0.07 * P * (1-P) per contract
- At 50c: 1.75c per contract (max fee)
- At 35c or 65c: ~1.59c per contract
- At 10c or 90c: 0.63c per contract
- At 5c or 95c: 0.33c per contract

### Maker fee: 0-0.44% (scaled by probability, updated July 2025)
- Some markets: flat 0.25% maker fee per contract
- Net savings: 1.3-1.75c per contract advantage for makers

### Adverse selection warning
When your limit order fills, the market has moved against you.
For FAST markets (crypto 15-min): taker orders fine, speed > fee savings.
For SLOW markets (sports, hours to game time): limit orders safe.
1-2c better than current price saves 1-3.5% with no adverse selection risk.

### Implementation
- Kalshi API supports limit orders already (order_type="limit")
- We'd need: price calculation (what limit to set), fill monitoring, timeout logic
- BEST APPLICATION: sports bets where game is hours away (no speed pressure)

---

## 9. NEXT STEPS — R&D ROADMAP

### Immediate (this session / next few sessions)
A. Save and index all raw market data for analysis
B. Build a Kalshi-vs-sportsbook price comparison tool
C. Wire up BALLDONTLIE API for NBA odds comparison (free tier)
D. Test limit order execution on one strategy (sniper is easiest)

### Short term (1-2 weeks)
E. Build a market scanner that runs hourly, flags discrepancies
F. Paper-test sports game winner bets (NHL, NCAA) using sharp book consensus
G. Actually use our FOMC/CPI strategies (they exist, have 0 bets)
H. Evaluate weather ensemble approach (GFS data is free)

### Medium term (if early results are promising)
I. Build real-time odds comparison with WebSocket feeds
J. Develop NCAA/NBA model using publicly available stats
K. Switch all strategies to limit orders
L. Build a dashboard that shows edge opportunities across all categories

### Research needed (parallel to building)
- Deep dive into every sport on Kalshi (which has the widest Kalshi-vs-sharp spread?)
- Historical settlement analysis: which Kalshi categories have the most inefficient pricing?
- Academic literature on specific sports biases (home ice advantage, back-to-back fatigue, etc.)
- Community research across all Reddit subs (running now)

---

## 10. REDDIT SWEEP — ALL 10 SUBREDDITS (Session 62)

Searched: r/ClaudeCode, r/ClaudeAI, r/Claude, r/algobetting, r/algotrading,
r/vibecoding, r/AI_agents, r/Kalshi, r/polymarket_bets, r/PredictionMarkets

### ZERO results from Claude/AI subs
r/ClaudeCode, r/ClaudeAI, r/Claude, r/vibecoding, r/AI_agents — zero posts about Kalshi.
r/algobetting, r/polymarket_bets, r/PredictionMarkets — zero indexed relevant posts.
Only r/Kalshi had any presence, mostly referenced indirectly.

### GENUINE people who shared real results (all LOST money or barely broke even):

1. Rodney LaFuente — market maker bot, lost 150 USD in 20 minutes. Six specific bugs.
   NOT selling anything. Honest post-mortem.

2. Jordan Metzner — Claude Opus 4.5 bot. 12 trades, 8 wins (66%), DOWN ~7 USD from 250 USD.
   "The only real way to make money is inside information."
   KEY FINDING: 66% WIN RATE STILL LOSES MONEY DUE TO FEES.

3. HackingTheMarkets — NFL bot using ESPN win probability. FAILED.
   "Professional traders access data feeds 30+ seconds faster than ESPN API."

4. TSA Trading Bot (Ferraiolo) — claims "surprisingly well" then says "will stop soon."
   Admits no liquidity for scale. Has referral commissions.

5. HN user "ammario" (top volume leaderboard) — use log-odds space, not linear probability.
   Declined collaboration offers to protect edge. No P&L shared.

### The 2 actually profitable people (NPR verified):
Logan Sudeith (25, Atlanta): 100K USD/month. Trades 100 hrs/week. Former risk analyst.
Evan Semet (26, Boston): six figures monthly. Former quant researcher. AWS-hosted models.
BOTH quit their jobs. NEITHER shares their edge. These are top 0.1% survivors.

### PURE MARKETING / BS (6+ sources):
- botforkalshi.com — commercial product, no results
- OctagonAI — promotes product, no results
- ryanfrigo/kalshi-ai-trading-bot — impressive README, zero profitability evidence
- "Just Built A Two-Layer AI System" — Medium clickbait
- Digital Journal "Copy Trading Platform" — paid press release
- Various SEO articles (5reasonstovisit, tradingstrategyguides) — content farm spam

### The weather bot "1,325 USD profit":
README explicitly states: "simulation tool for educational purposes. Does not place real trades."
The 1,325 is PAPER TRADING. Headline is misleading. Still — the GFS ensemble approach is sound.

### Critical findings:
- 85-90% of retail Kalshi traders LOSE money (cited in multiple sources)
- ESPN/public sports data is 30+ SECONDS behind HFTs — speed edge impossible for retail
- AI/LLM market analysis alone: 66% win rate still loses after fees (Metzner proved this)
- Public GitHub bots = zero edge (anyone can copy = edge disappears)
- The fee math: at 50c, taker fee is 1.75c. On small bets, fee as % of profit is huge.
- SWITCHING TO LIMIT/MAKER ORDERS eliminates taker fee entirely

### What the genuine sources agree works:
1. Maker/limit orders (zero fees vs 1.75c taker)
2. Weather markets with GFS ensemble data (free NOAA data, inefficient markets)
3. Domain expertise in specific niches (CPI, TSA — the profitable traders ALL specialize)
4. Favorite-longshot bias exploitation (academic confirmation)

### What genuine sources agree does NOT work:
1. Public data speed plays (ESPN is 30s behind, crypto is repriced by HFTs in seconds)
2. AI/LLM analysis alone (66% win rate loses money after fees)
3. Cross-platform arbitrage at retail scale (windows too short, capital too small)
4. Any public GitHub bot repo (copied = no edge)

---

## 11. THE HONEST ASSESSMENT

What we've been doing: trading crypto 15-min (4% of Kalshi) against HFTs with a signal
that the Whelan paper says has no structural edge at 35-65c.

What we should explore: sports (42% of Kalshi), economics (domain knowledge > speed),
and the single biggest lever = switching to limit orders (22% structural savings).

The sniper strategy IS academically validated. Keep it running.
The drift strategies are in a dead zone. They're not broken — the market is too efficient there.

The real question for Matthew: do you want to pivot the bot from "execute a known edge"
to "find edges first, then execute"? That's a fundamentally different tool.

---

## 12. LIVE SCANNER RESULTS — SESSION 62 (2026-03-13 ~08:50 CDT)

### Tool built: scripts/edge_scanner.py
Pulls live Kalshi sports markets, compares to Pinnacle/DraftKings/FanDuel/BetMGM
consensus odds, calculates taker and maker edge. Run: `python scripts/edge_scanner.py`

### Full scan results
- 170 Kalshi game markets found (NBA 40, NHL 44, NCAAB 72, MLB 14)
- 52 matched to odds API data (team name matching across platforms)
- API credit cost per scan: ~4 credits (4 sports x 1 credit each)

### THE HONEST RESULT: Kalshi sports markets are efficiently priced

Best taker edges found:
  #1 NBA: Bulls at Clippers NO side — 1.5% taker edge, 2.8% maker edge
  #2 NBA: Grizzlies at Pistons — 1.2% taker edge
  #3 NCAAB: SC State at Howard — 0.8% taker edge
  #4 NBA: Cavaliers at Mavericks — 0.6% taker edge
  #5 NCAAB: Duquesne at VCU — 0.5% taker edge

ALL other markets: 0% or negative edge vs sharp book consensus.

### Why this matters
- Kalshi sports prices track Pinnacle within 0-3% on most games
- The 1-2% edge that exists is barely above taker fees (1.75c max at 50c)
- Using LIMIT ORDERS (maker) saves ~1.5c, making 2-3% edges potentially profitable
- BUT: fill rate on limit orders is uncertain — if your order doesn't fill, zero profit
- NHL has only 2-4 games matched (many Kalshi NHL markets not in odds API or too far out)
- NCAAB has the most markets (72 open) and best team matching (35+ matched)

### Critical bug found and fixed during build
The initial scan showed a fake 8.9% NHL edge (Kings at Islanders). Root cause:
short team name "LA" matched "Is**la**nders" (substring "la") before "Los Angeles Kings".
Fixed by requiring 4+ char minimum for substring matching and preferring word-boundary
matches. After fix: real edge was 0% on that game. ALL edges shrunk dramatically.

LESSON: Any "edge" found by automated scanning MUST be manually verified before trading.
Short name fuzzy matching is extremely prone to false positives in sports data.

### Implication for strategy
Sports betting on Kalshi is NOT a free lunch. The platform is efficiently priced against
Pinnacle and other sharp books. The edges that exist (~1-3%) are small enough that:
- Taker fees eat most of the edge
- Maker orders might capture it but with uncertain fill rates
- You need high volume (many games per day) to compound small edges

This means the strategy must be one of:
A. High-frequency maker orders on high-volume games (NBA, NCAAB) — 0.5-2% edge per trade
B. Wait for rare large mispricings (>3%) — may only happen a few times per week
C. Focus on niche markets with less efficient pricing (lower-volume sports, props)

### BALLDONTLIE API evaluation
- Free tier: 5 req/min, 1 sport only, basic data (likely no odds)
- Paid: 9.99/month per sport for odds data
- Verdict: NOT WORTH IT — our existing the-odds-api (free, includes Pinnacle) covers everything
- BALLDONTLIE adds Kalshi odds directly, but we already have that from the Kalshi API

---

## 13. REVISED STRATEGIC ASSESSMENT (post-scanner)

### What we know now (empirically tested, not just theorized)
1. Crypto drift 35-65c: no structural edge (Whelan) — confirmed by 60+ sessions of data
2. Expiry sniper 90c+: validated by favorite-longshot bias — 39W/2L but marginal P&L
3. Sports vs Pinnacle: 0-3% edge at best, eaten by fees as taker
4. Maker orders: 22% structural advantage (Whelan) but fill rate unknown
5. Economics (CPI/FOMC): built but never tested (0 bets), domain knowledge edge possible

### Where the edge MIGHT actually be
A. **Limit orders on any strategy** — the single biggest lever (22% savings)
B. **Expiry sniper with limit orders** — validated edge + fee savings = double win
C. **FOMC/CPI** — domain knowledge > speed, less competition, already built
D. **Weather ensemble** — free GFS data, no HFT competition, our weather strategy exists
E. **Live line movement** — scan closer to game time when lines move most
F. **Props/totals** — NCAAB over/under totals have different pricing dynamics

### What we should probably STOP doing
- Optimizing drift parameters (it's structural, not parametric)
- Looking for sports arbitrage (Kalshi is efficiently priced)
- Chasing large obvious mispricings (they don't exist at scale)

### Recommended next steps (prioritized)
1. **Test limit order execution** on one strategy (sniper — easiest candidate)
2. **Activate FOMC/CPI strategies** — they exist with 0 bets, waste of built code
3. **Run scanner near game time** — edges may be larger 15-60 min before games
4. **Scan props/totals** (not just h2h) — different pricing dynamics
5. **Weather ensemble** — build GFS ensemble comparison for KXHIGH markets

---

## 14. LIMIT ORDER (post_only) DEEP DIVE — SESSION 62 CONTINUED

### Current state
- live.py already uses `order_type="limit"` at line 159
- BUT: does NOT set `post_only=True` — so orders that cross the spread fill as TAKER
- Kalshi API supports: `post_only`, `time_in_force`, `expiration_ts`
- KalshiClient `create_order()` currently lacks `post_only` and `expiration_ts` params

### Fee math (confirmed from Kalshi API + our fee_calculator.py)
  Taker fee formula: ceil(0.07 * contracts * P * (1-P) * 100)
  Maker fee formula: ceil(0.0175 * contracts * P * (1-P) * 100)
  Makers pay 25% of taker rate. post_only=True guarantees maker execution.

  At 50c, 5 contracts (typical drift bet at 54 USD bankroll):
    Taker fee: 5 * 2c = 10c
    Maker fee: 5 * 1c = 5c
    Savings per trade: 5c

  At 90c, 3 contracts (typical sniper bet):
    Taker fee: 3 * 1c = 3c (fee is small at 90c — P*(1-P) is low)
    Maker fee: 3 * 1c = 3c (floor of 1c per contract regardless)
    Savings per trade: 0c — FEE SAVINGS NEGLIGIBLE FOR SNIPER

  Over 200 drift trades: 200 * 5c = 10 USD saved
  Over 200 sniper trades: ~0 USD saved (fees already minimal at 90c+)

### Strategy recommendation (from S61 research, confirmed)
  DRIFT: post_only=True, expiration_ts=30s, price=best_bid+1c
    - 30s wait is acceptable in 15-min windows (12 min of viable signal time)
    - If rejected (would cross): fall back to regular limit order
    - Fill rate unknown — need live testing. Tight spreads (1-2c at 50c) suggest high fill

  SNIPER: keep current behavior (IOC/limit, no post_only)
    - Time-critical (last 2-3 min before expiry). Can't afford non-fill.
    - Fee savings negligible at 90c+ anyway (1c or less)

### Implementation needed
  1. Add `post_only` and `expiration_ts` to KalshiClient.create_order()
  2. Add `maker_mode` param to live.execute()
  3. When maker_mode=True: set post_only=True, expiration_ts=now+30s
  4. Track fill_rate for post_only orders in DB
  5. If fill_rate < 70% after 50 trades: revert to taker mode
  6. Wire drift loops to use maker_mode=True, sniper keeps False
  Estimated: ~2-3 hours to implement and test

### Verdict: MEDIUM PRIORITY
  10 USD savings over 200 trades is meaningful at 54 USD bankroll (~18%).
  But implementation effort is 2-3 hours and fill rate is uncertain.
  Should implement when bot is restarted and drift is active.

---

## 15. FOMC STRATEGY LIVE MARKET ANALYSIS — SESSION 62

### Live FRED data (fetched 2026-03-13 14:03 UTC)
  Fed funds rate (DFF): 3.64%
  2yr Treasury (DGS2): 3.64%
  Yield spread: 0.000% (exactly zero — hold regime)
  CPI accelerating: YES (MoM 0.267% vs prior 0.171%)

### Our model output (static for ALL meetings)
  Hold: 83.0%, Cut 25bp: 7.0%, Hike 25bp: 5.0%, Cut >25bp: 3.0%, Hike >25bp: 2.0%

### Live Kalshi KXFEDDECISION prices (March 13, 2026)

  MARCH 19 (T-6 days, volume 11M):
    Hold: 99c bid — FULLY PRICED. Zero edge. No trade possible.
    Cut 25bp: 0-1c | Cut >25bp: 0-1c | Hike: 0-1c
    Our model says 83% hold but market says 99%. Model is LESS certain than market.

  APRIL (T-45 days, volume 246K):
    Hold: 92-93c | Cut 25bp: 7-9c | Hike 25bp: 1-3c
    Our model says 83% hold vs market 92-93%. Again, model undersells hold.
    Implied: market expects NO policy change through April.

  JUNE (T-97 days, volume 42K):
    Hold: 59-65c | Cut 25bp: 35-38c | Cut >25bp: 6-8c | Hike: 2-3c
    Market prices ~43% total cut probability for June. Our model says only 10%.
    HUGE DIVERGENCE: model says 83% hold, market says 59-65%.

  JULY (T-139 days, volume 3.2K):
    Hold: 60-65c | Cut 25bp: 15-23c | Hike: 0-8c
    Similar pattern — far-out meetings have more uncertainty.

### CRITICAL FINDING: Model has no term structure

  Our FOMC model outputs the SAME probabilities (83% hold) for every meeting
  regardless of distance. But market pricing shows a clear term structure:
    T-6 days:  99% hold (nearly certain)
    T-45 days: 92% hold (very likely)
    T-97 days: 59% hold (significant cut probability)

  The model doesn't account for:
  1. Proximity effect — closer meetings are more certain
  2. Multiple meetings between now and far-out dates (cuts could happen earlier)
  3. Cumulative macro uncertainty over longer horizons

  RESULT: Model would wrongly SHORT hold on March meeting (83 vs 99 = sell hold)
  and wrongly LONG hold on June meeting (83 vs 59 = buy hold). Both are wrong
  because the model is miscalibrated for time horizon.

### CME FedWatch as alternative signal source
  CME FedWatch is the gold standard for FOMC probabilities (derived from Fed Funds futures).
  Free web tool at cmegroup.com. Paid API: 25 USD/month.
  pyfedwatch Python library: free, but requires futures pricing data we don't have.

  THE REAL EDGE: If Kalshi prices diverge from CME FedWatch by >3%, that's a
  structural inefficiency (retail Kalshi traders vs sophisticated futures market).
  Would require either: (1) 25 USD/month CME API, (2) web scraping, or
  (3) manual comparison before each meeting.

### FOMC activation verdict: NOT READY

  Do NOT activate FOMC strategy for live trading. The model is fundamentally broken
  for anything except same-meeting-day comparison. It would place WRONG bets on
  both near-term and far-term meetings.

  To fix:
  A. Add term-structure adjustment: scale uncertainty with days_until_meeting
  B. Better: use CME FedWatch as the signal (compare to Kalshi for edge)
  C. Best: subscribe to CME FedWatch API (25 USD/month) and build Kalshi-vs-CME
     scanner. This is the same pattern as our sports scanner (Kalshi vs Pinnacle).

  PAPER TRADING IS FINE — let it accumulate data. But live trading would lose money.

### What about event-driven edge (CPI/employment releases)?

  Potential approach: when CPI data releases (monthly), check if Kalshi FOMC prices
  adjust immediately. If Kalshi is slow (minutes behind CME), there's a window.

  CPI release schedule: 8:30 AM ET on fixed dates (known months ahead).
  Next CPI: March 12 was yesterday. April 10 is next.

  This is a pure speed play — our FRED feed already gets CPI data, we already
  have the FOMC model. The question is: does Kalshi adjust slower than CME?

  CANNOT TEST WITHOUT LIVE DATA. Log this as a monitoring task:
  on next CPI release day (April 10), compare KXFEDDECISION prices before/after
  8:30 AM and check if edge appears in the adjustment window.

---

## SESSION 63 ADDITIONS (2026-03-13)

### 17. GEFS 31-MEMBER ENSEMBLE WEATHER FEED — BUILT + TESTED

  Replaced parametric normal distribution assumption (N(forecast, 3.5F))
  with empirical probabilities from 31 GEFS ensemble members.

  How it works:
  - Open-Meteo free ensemble API: ensemble-api.open-meteo.com/v1/ensemble
  - Returns all 31 GEFS members (1 control + 30 perturbed) as JSON
  - Probability = count(members in bracket) / 31 (empirical, not parametric)
  - Handles skewed/bimodal distributions that normal CDF cannot

  Live test (2026-03-14 NYC):
  - 31 members, mean=49.6F, std=1.3F, range=46.6-52.2F
  - Bracket "48-51F": 22/31 = 71.0% empirical probability
  - No HIGHNY markets open (Friday evening) — can't compare to prices yet

  Code: GEFSEnsembleFeed class in src/data/weather.py
  Tests: 21 new tests (77 total weather tests), all passing
  Wired into main.py and weather_forecast.py load_from_config()
  Strategy auto-detects GEFS feed and uses empirical probabilities

  IMPORTANT: Zero weather paper trades ever recorded (strategy never fired).
  The 5% min_edge threshold was too high for the old parametric model.
  GEFS ensemble may fire more often with better-calibrated probabilities.
  Need to wait for weekday HIGHNY markets to test.

### 18. POST_ONLY MAKER ORDER SUPPORT — BUILT + TESTED

  KalshiClient.create_order() now supports post_only and expiration_ts.
  live.execute() passes them through. trading_loop gains maker_mode param.

  When maker_mode=True:
  - post_only=True (order rejected if it would fill as taker)
  - expiration_ts=now+30s (auto-cancel if unfilled after 30s)
  - Saves ~75% on fees (maker fee = 25% of taker fee)

  NOT YET ACTIVATED in any live loop.
  To activate: pass maker_mode=True to trading_loop() in main.py for drift strategies.
  Should NOT be used for sniper (time-critical, fee savings negligible at 90c+).

  Fee savings estimate: ~5c/trade on drift x 200 trades = 10 USD saved.
  At 54 USD bankroll, that's ~18% savings.

  Tests: 5 new tests in test_live_executor.py, all passing.

### 19. EVENING EDGE SCANNER RESULTS (2026-03-13 ~15:30 CDT)

  Ran edge scanner with 11 NBA, 16 NHL, 32 NCAAB, 1 MLB games.
  77 matched to odds API data.

  Best edges found:
  - NCAAB Kennesaw St at Sam Houston: 2.4% taker / 4.2% maker
  - NCAAB Wisconsin at Illinois: 2.3% taker / 4.0% maker

  CONFIRMS S62 FINDING: Kalshi sports efficiently priced even near game time.
  Max taker edge ~2.4% (eaten by 1.75c max fee at 50c).
  Maker edges ~4% possible but fill rate uncertain.

  DEAD END RECONFIRMED: Sports arbitrage is NOT a viable edge source.

---

## 16. COMPREHENSIVE SESSION 62 CONCLUSIONS

### What we built
  1. scripts/edge_scanner.py — Kalshi vs Pinnacle sports price comparison tool
  2. tests/test_edge_scanner.py — 27 tests
  3. Documented live scan results across 170 Kalshi sports markets

### What we learned (empirically, not theoretically)
  1. Kalshi sports are efficiently priced vs sharp books (0-3% edge, eaten by fees)
  2. Favorite-longshot bias is REAL (Whelan, Snowberg-Wolfers): 90c+ = structural edge
  3. Maker orders save 75% on fees but fill rate is uncertain
  4. Our FOMC model is broken (no term structure) — would place wrong bets
  5. CME FedWatch vs Kalshi comparison is the right FOMC edge approach (25 USD/month)
  6. BALLDONTLIE API is not worth the cost vs our existing the-odds-api

### Revised priority stack (HONEST, based on evidence)

  PRIORITY 1 — KEEP RUNNING (validated edge, proven profitable):
    Expiry sniper at 90c+ — 39W/2L, favorite-longshot bias is structural.
    Only tweak: investigate sniper maker orders (though fee savings minimal at 90c+).

  PRIORITY 2 — IMPLEMENT (concrete, low-risk improvement):
    post_only maker orders on drift strategies — 10 USD savings over 200 trades.
    Implementation: 2-3 hours. No strategy logic changes, just execution optimization.

  PRIORITY 3 — INVESTIGATE (promising but needs more data):
    Near-game-time edge scanning — run scanner 30-60 min before NBA/NHL tip-off.
    CPI release day monitoring — check KXFEDDECISION price adjustment speed.
    Weather ensemble — free GFS data, no HFT competition.

  PRIORITY 4 — DEFER (requires investment or model rebuild):
    CME FedWatch vs Kalshi scanner (needs 25 USD/month API or web scraping).
    FOMC model term structure fix (significant model rebuild, paper-test first).
    Props/totals scanning (need to understand Kalshi's prop market structure).

  PRIORITY 5 — ABANDON (dead ends confirmed this session):
    Mid-range drift optimization (35-65c) — Whelan paper kills this, 60 sessions confirm.
    Sports arbitrage as taker — efficiently priced, fees eat edge.
    BALLDONTLIE API — overpriced vs existing data sources.
    FOMC live activation — model is broken, would lose money.

### Single biggest lever for profitability
  SNIPER VOLUME. The sniper at 95.1% win rate is the only validated edge.
  Increasing sniper volume (more markets, more windows, higher bet size)
  is worth more than any new strategy. At 2.69 USD/bet, each win nets ~0.17 USD.
  Need ~1000 more wins to reach 170 USD profit target. At 20 bets/day = 50 days.

  If bankroll recovers to 100 USD: max bet = 4.99 USD, each win nets ~0.35 USD.
  Same 1000 wins = 350 USD = profit target exceeded. Timeline: ~50 days.

  THE MATH: sniper IS the strategy. Everything else is optimization.

---

## SESSION 64 ADDITIONS (2026-03-13)

### 20. SNIPER LIVE PERFORMANCE — PRICE BUCKET BREAKDOWN (42 live settled bets)

  This is the most detailed sniper analysis to date.

  90-94c bucket (21 bets, 90.5% WR): -3.01 USD
  95-99c bucket (20 bets, 100% WR): +2.60 USD
  85-89c bucket (1 bet, 100% WR): +0.70 USD (too small to mean anything)

  MATH: At 93c, breakeven = 93% WR. We got 90.5%. Marginally unprofitable.
        At 97c, breakeven = 97% WR. We got 100%. Profitable (but 20 bets, small).

  The two losses today: both YES bets at 93c in same window (KXSOL + KXBTC).
  Correlated losses — BTC dropped in final seconds, both contracts flipped.
  Total loss: -9.30 USD. Wiped 38 wins totaling +9.59 USD. Net: +0.29 USD.

  CONCLUSION: At only 42 bets, cannot statistically confirm the bucket split is real.
  At 90% WR with 21 bets, 95% CI is [77.9%, 100%] — includes breakeven (90%) and
  includes structural loss territory. Raising threshold to 95c is premature.
  Decision point: revisit at 200+ live settled sniper bets.

  EV estimate: +0.007 USD/bet. At 40 bets/day = +0.28 USD/day.
  At this rate: 609 days to reach +170 USD profit target. MUCH TOO SLOW.

  What could improve sniper EV:
  A. Raise threshold to 95c (better EV/bet, fewer bets — net effect unclear)
  B. Lower threshold to 85c (more volume, lower EV/bet — probably net negative)
  C. Find non-crypto 90c+ markets to expand volume without changing threshold
  D. Increase bet size (requires bankroll growth first)

### 21. CRYPTO 15-MIN EXPANSION: ALL ALTERNATIVES EXHAUSTED

  Probed: KXBNB15M, KXBCH15M, KXADA15M, KXDOGE15M, KXLINK15M
  Result: ALL have 0 open markets. Confirmed dead.

  Only active 15-min crypto series on Kalshi (as of March 2026):
  KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M

  Sniper volume ceiling = 4 cryptos × ~10% fire rate = ~4 bets/window.
  Cannot increase sniper volume by adding more crypto series. Period.

### 22. SPORTS SCANNER — IN-PROGRESS GAME BUG IDENTIFIED

  Afternoon scan (March 13, 5 PM CDT) showed fake "15% edges" on NCAAB games.
  Root cause: games had already started at 2-3 PM CDT.
  Kalshi showed live in-game prices (wild), odds API showed pre-game Pinnacle odds.
  Comparing live in-game Kalshi to pre-game sharp = meaningless.

  FIX NEEDED: Filter scanner to games with commence_time > now + 30min.
  Until this filter exists, afternoon/evening scans will always show fake edges.

  Pre-game scan (6-12 hours before tip-off) remains the only valid approach.
  Even then: max 2.4% taker edge (barely above fees). Dead end confirmed again.

### REVISED PRIORITY STACK (post S64, based on actual data)

  PRIORITY 1 — ONLY VALIDATED EDGE:
    Expiry sniper at 90c+. Everything else is research.

  PRIORITY 2 — ACTIVATE (15 minutes of work):
    maker_mode=True in main.py for drift. ALREADY BUILT. Just wire it.

  PRIORITY 3 — TIME-SENSITIVE (wait for Monday):
    GEFS weather test vs live HIGHNY markets (weekday only)

  PRIORITY 4 — NEEDS 200+ BETS:
    Sniper threshold analysis (90c→95c) — statistically premature now

  PRIORITY 5 — RESEARCH (no execution yet):
    Non-crypto sniper expansion: can sports in-game markets trade at 90c+?
    If NBA game winner is 95c+ at half-time, sniper might fire there.
    Would massively expand volume. No analysis done yet.

  DEAD ENDS (stop revisiting):
    Sports pre-game arbitrage (2.4% max, dead)
    Crypto 15-min expansion (only 4 series exist, dead)
    FOMC model without term structure (broken, confirmed)
    BALLDONTLIE API (overpriced vs existing data sources, dead)

---

## SESSION 65 ADDITIONS (2026-03-14)

### 23. NON-CRYPTO SNIPER EXPANSION — FULL INVESTIGATION (DEAD END)

  Research question: Do any Kalshi sports or weather markets provide a sustained
  90c+ window (like crypto 15-min) that our sniper could target?

  Markets investigated:
    KXNBAGAME (NBA game winner): zero in-game liquidity, zero volume
    KXNCAABGAME (NCAAB game winner): zero in-game liquidity, zero volume
    KXNBASPREAD (NBA spread): ~309K fp volume but ALL in the last 60 seconds
    KXNBATOTAL (NBA over/under): same pattern as spread — burst at settlement
    KXNCAAMBGAME (NCAAB game winner): 3-13 trades per game, all at 99c during settlement
    KXPGATOUR (PGA golf tournament): sustained 98-99% for 8+ hours BUT terrible capital efficiency

  Key finding — market structure:
    Pre-game: liquid, 45-55c (pre-game spread bets placed)
    During game: near-zero active trading
    Game end: 20-60 second burst from 50c to 99c during settlement
    Post-game: stays at 99c for hours (settlement period)

  The 90-96c zone that matters for efficient sniper (10c profit on 90-96c cost)
  appears only in the FINAL 20 SECONDS before settlement. Zero sustained window.

  This is fundamentally different from crypto 15-min where:
    - Continuous price discovery throughout the 15-min window
    - Gradual drift to 90c+ as BTC moves
    - Stable 2-3 minute window at 90c+ with room to execute

  VERDICT: Sports sniper expansion is NOT viable. Market structure doesn't support it.

### 24. WEATHER MARKETS AT 99c — WRONG APPROACH FOR OUR SCALE

  Discovery: KXHIGH* markets (LA, Chicago, Miami, Denver) have many bracket
  contracts at 99% NO for hours when the actual temperature is clearly outside
  the bracket.

  Example: KXHIGHLAX >88°F on March 13 at 99% NO, volume 381,869 fp,
  trading continuously for hours once the daily high is recorded.

  Why this seems interesting: long window, structural certainty, real liquidity

  Why it DOESN'T work at our scale:
    Capital efficiency: pay 99c to earn 1c = 1% return on capital
    Compare: pay 90c to earn 10c = 11% return on capital (crypto sniper)
    At $90 bankroll, buying 90 contracts of weather NO = $89.10 at risk for $0.90 profit
    That's our ENTIRE bankroll for less profit than one crypto sniper bet

  When this WOULD work:
    At $10,000+ bankroll: deploy $9,900 on weather NO for $100 profit
    Daily weather P&L at large scale could be $50-100/day
    But we need 110x bankroll growth first

  VERDICT: Weather NO sniper = viable strategy for large capital, not our current scale.
  Continue with GEFS signal trading (already built) for uncertain brackets near 50c.

### 25. SPORTS MARKET STRUCTURE — DEFINITIVE MAP

  True active sports series on Kalshi (where real trading happens):
    KXNBASPREAD (NBA point spread): 100K-400K fp/game, mostly pre-game
    KXNBATOTAL (NBA total points): similar structure to spread
    KXNCAAMBGAME (NCAAB game winner): 2K-20K fp/game, minimal liquidity
    KXPGATOUR (PGA golf tournament winner): 2M+ fp per player, multi-day
    KXNHLEAST/KXNHLPLAYOFF: season-long markets, long settlement period
    KXHIGH* (weather high temp): 5-10 bracket markets per city per day

  Series with ZERO meaningful volume:
    KXNBAGAME (NBA game winner — not spread): zero volume, zero trades
    KXNCAABGAME (different from KXNCAAMBGAME): zero volume
    KXNBAPTS (NBA player points props): zero volume
    KXNBASPREAD for future games: zero pre-game prices (markets empty until game day)

  Market-making observation:
    Many trades are at recurring counts (93, 187, 935, 2000 fp) — likely automated
    market makers. The 93/187/935/2000 pattern suggests systematic MM activity.

### 26. ATP TENNIS + NCAAB IN-PLAY MARKET STRUCTURE (Session 66 — 2026-03-14)

  RESEARCH QUESTION: Do tennis and NCAAB markets have sustained 90c+ in-play windows
  like crypto sniper? S65 found NBA/NHL go silent during games. Tennis and NCAAB untested.

  DATA SOURCE: Kalshi /markets/trades endpoint. KXATPMATCH (ATP match winner).
  Series analyzed: KXATPMATCH (8 settled matches, Miami Open March 12 2026).
  KXNCAAMBGAME (KU vs Houston, Big 12 Championship March 13 2026).

  ATP TENNIS FINDINGS:

  A. GENUINE IN-PLAY PRICING EXISTS (unlike NBA/NHL which go silent)
     Evidence: Medvedev vs Drakos match (KXATPMATCH-26MAR12DRAMED-MED)
       Pre-match: 58-65c consistently all of March 12 (Medvedev slight favorite)
       Match starts ~23:45 UTC: prices ramp from 63c → 81c → 92c+ over 2 hours
       3149 total trades across 22 hours. Volume SPIKES from 292 to 711 to 478 to 455/bucket
       during the match (volume spike = match in progress).
       90c+ window: 62 min (00:59 → 02:01 UTC March 13)

  B. HEAVY FAVORITES SHOW PRE-MATCH 90c+ (NOT in-play)
     Evidence: Sinner vs Tiafoe (KXATPMATCH-26MAR12TIESIN-SIN)
       FIRST TRADE was already at 92c (before match started!)
       Held 91-93c for 26+ hours, then settlement burst
       Pattern: Sinner (#1-2 world) vs Tiafoe — pre-match odds reflect heavy favorite status
       NOT exploitable — can't enter before match when settlement timing unknown

  C. SUSPENDED MATCHES CREATE FALSE LONG WINDOWS
     Evidence: Alcaraz vs Norrie (KXATPMATCH-26MAR12ALCNOR-ALC)
       503-minute "window" at 90c+
       Pattern: match started at night (~74c → 91c in first 30 min), then SUSPENDED
       Next day completion. Market stayed at 91-95c overnight waiting for resumption.
       REAL in-play window was maybe 30-60 min. Remaining 400+ min = suspension delay.

  D. CAPITAL EFFICIENCY COMPARISON
     Medvedev match (genuine case): buy at 90c at 00:59, settle at 99c at 02:01
     Return: 9c on 90c = 10% in 62 min
     Crypto sniper: 10% in 2-3 min (30x better per unit time)
     Tennis sniper: 10% per hour vs crypto 10% per 2.5 min. 24x worse capital efficiency.

  E. FATAL STRUCTURAL PROBLEM: Settlement timing unknown
     Cannot predict when match ends. Capital could be locked 30 min or 20+ hours.
     No live score API integrated. Cannot distinguish "match at set point" from "match suspended".

  F. HOW TO DISTINGUISH MATCH-IN-PROGRESS FROM PRE-MATCH:
     Volume signature: pre-match = 5-50 trades/30min. In-match = 300-700 trades/30min.
     Price signature: pre-match is flat (63c for hours). In-match ramps continuously.
     A volume monitoring system could detect match start (volume spike) and estimate completion.

  NCAAB BASKETBALL FINDINGS:

  A. GENUINE IN-PLAY PRICING (unlike NBA/NHL which go silent)
     Evidence: KU vs Houston Big 12 Championship (KXNCAAMBGAME-26MAR13KUHOU-*)
       Houston pre-match: 67-70c (consistent for 18 hours before game)
       Game starts ~01:00 UTC March 14: volume spikes from 180/bucket to 1138/bucket
       Houston rises: 67c → 69c → 81c → 93c over 2 hours
       KU falls: 32c → 32c → 23c → 18c → 9c → 1c
       12,628 total trades across 2 games (massive volume vs crypto sniper games)

  B. 90c+ WINDOW: 56 MINUTES, MOSTLY POST-GAME
     Houston hits 90c at 02:56 UTC (estimate: ~3-4 min before game ends)
     Settlement at 03:52 UTC = 56 min total at 90c+
     In-game 90c+ time: ~4 min. Post-game settlement wait: ~52 min.
     PROBLEM: 90c threshold only crossed in final 4 min of a blowout — too short to trade manually.
     PROBLEM: 52 min settlement delay for 10c profit = 10% in 56 min. 14x worse than crypto.

  C. CAPITAL EFFICIENCY REALITY
     Entry at 90c with 4 min game time left → wait 56 min → settle at 99c
     Without live scores, impossible to know the 4-minute window to enter.
     With live scores + code: possible in theory. But 56-min tie-up of capital is poor.

  D. NCAAB IS DIFFERENT FROM NBA/NHL
     NBA/NHL markets on Kalshi go SILENT during games (confirmed S65).
     NCAAB markets actively price throughout (8437 trades for KU, continuous price movement).
     This is a structural difference — NCAAB market makers stay active during games.
     Why: NCAA audiences are college students + fans who trade in-game more actively.

  COMBINED VERDICT — TENNIS AND NCAAB SNIPER AT CURRENT SCALE:

  NOT viable as sniper replacements. Two hard problems:
  1. Settlement timing unknown (tennis: variable 30 min to 20+ hours; NCAAB: 52 min post-game)
  2. Capital efficiency: 14-24x worse than crypto sniper on per-minute basis

  WHAT WOULD MAKE IT VIABLE (higher bankroll, future research):
  - Tennis: free live score API (ATP Tour has one, unofficial) + volume-spike detection for match start
  - NCAAB: live score API (ESPN unofficial: site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard)
    + entry logic: "leading by 20+ with 3 min remaining" = 90c+ entry
  - Both require: $500+ bankroll to make 52-min wait worthwhile
  - Both require: new code module (sports_sniper_v2.py with live score integration)

  MARCH MADNESS RELEVANCE (March 20+):
  - Sweet 16 markets open (KXNCAAMBGAME-26MAR14*): 1-vs-4 seed games
  - High-seed vs low-seed blowouts could create 90c+ in final 5 min
  - Same capital efficiency problem. Same settlement delay.
  - Monitor but do not build at current bankroll/scale.

### REVISED FINAL PRIORITY STACK (Session 66)

  PRIORITY 1 — ONLY VALIDATED EDGE (unchanged):
    Expiry sniper at 90c+. 96% WR at 50 bets. Everything else is research.

  PRIORITY 2 — WEATHER GEFS ON WEEKDAYS (Monday March 16):
    HIGHNY markets open weekdays only. GEFS ensemble already built (S63).
    Signal fires when GEFS probability differs from Kalshi price by 5%+.
    Cannot test until Monday — test FIRST THING Monday morning.

  PRIORITY 3 — SOL DRIFT GRADUATION (2 more bets):
    28/30 live settled bets. 2 more → Stage 2 analysis.
    Monitor each session with --graduation-status.

  DEAD ENDS — STOP REVISITING:
    Tennis sniper at current scale: settlement timing unknown, 24x worse capital efficiency
    NCAAB sniper at current scale: 52-min post-game wait, 14x worse capital efficiency
    NBA/NHL sniper: market goes silent during games (S65 confirmed)
    Weather NO at 99c: terrible capital efficiency at our scale
    Sports pre-game arbitrage: efficiently priced (S62/S63 confirmed)
    FOMC model without CME FedWatch: broken
    BALLDONTLIE API: overpriced

  OPEN FOR FUTURE RESEARCH (when bankroll >500 USD):
    Tennis sniper + live score API: volume spike detects match start, score detects match end
    NCAAB in-game sniper: live score integration for "blowout with 3 min left" detection
    March Madness upset structure: 1-vs-16 blowouts with known game end time

---

## SESSION 68 ADDITIONS (2026-03-14)

### 27. SNIPER PRICE BUCKET DEEP ANALYSIS (167 live settled bets)

  FINDING: 90-94c bucket is the profit engine. Do NOT raise trigger to 95c.

  Bucket breakdown (all-time 167 live settled):

    below 87c: 2 bets, 100% WR, EV=1.54 USD/bet, ROI=16.5% [too few to trust]
    90-94c: 84 bets, 97.6% WR, EV=0.618 USD/bet, ROI=5.6% [MAIN PROFIT ENGINE]
    95-96c: 43 bets, 97.7% WR, EV=0.042 USD/bet, ROI=0.4% [NEARLY BREAK-EVEN]
    97-98c: 26 bets, 100% WR, EV=0.17 USD/bet, ROI=1.6% [small sample, ok]
    99c: 12 bets, 100% WR, EV=0 USD/bet, ROI=0% [break-even, Kalshi fees eat margin]

  WHY 95-96c is terrible despite high WR:
    At 95c, you win 5c per contract. One loss of 14.40 USD = wipes 342 win-profits.
    At 90c, you win 10c per contract. One loss = wipes 88 win-profits.
    LOWER trigger price = HIGHER margin per win = better loss absorption.

  RECOMMENDATION:
    - Keep trigger at 90c (confirmed optimal)
    - Do NOT raise to 95c (eliminates the profit engine)
    - Do NOT lower to 87c without paper testing (only 2 data points)
    - Consider a SOFT MAX at 97c (bets above 97c have zero to negative real EV)

### 28. OTHER CRYPTO 15-MIN SERIES — CONFIRMED INACTIVE

  Checked: KXBCH15M, KXBNB15M, KXADA15M, KXDOGE15M
  All returned 0 open markets via API (March 14, 2026).
  KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M are the only active series.
  Cannot increase opportunity count by adding new crypto series.

### 29. KALSHI-WIDE 90c+ MARKET SCAN — NOTHING ACTIONABLE

  Scanned all open markets for 90c+ bid/ask with volume > 500:
  Result: 67 markets found — ALL are KXMVE parlay markets.
  KXMVE parlays at "100c": these are settled-but-unresolved parlays where
  YES=0c (all legs lost) → NO implied at 100c. Not tradeable for profit.
  NO other market categories have sustained 90c+ prices with real liquidity.
  Crypto 15-min is the UNIQUE venue for this strategy.

### 30. TODAY'S EXCEPTIONAL PERFORMANCE — WHAT DROVE IT

  March 14, 2026: 125 bets, 124W (99% WR), +60.92 USD
  Compare: March 13, 2026: 42 bets, 40W (95% WR), +0.29 USD

  Two factors explain the 200x P&L increase:
  1. Bet size increase: avg 4.5 USD → 12.91 USD (bet size increase from S67)
     15% bankroll cap: at 89 USD bankroll, max per bet = 13.34 USD
  2. Volatility: 3x more opportunities (125 vs 42 bets) due to crypto volatility

  Implied daily P&L range at new bet cap:
    Low volatility day: ~30-40 bets, ~18-25 USD expected
    High volatility day: ~100-130 bets, ~60-80 USD expected
    Average estimate: ~40-60 bets, ~25-40 USD expected daily

### 31. MARCH MADNESS ANALYSIS — NOT WORTH BUILDING (March 20+)

  NCAA tournament Round 1 starts March 20, 2026.
  1-vs-16 seeds: 99.2% historical WR → structural edge IF Kalshi prices at 90c+
  
  Why NOT to build a March Madness sniper module:
    Capital efficiency: 2+ hour game + 52 min settlement = 60x worse than crypto sniper
    Total EV for whole tournament: ~10-20 USD (vs 25-60 USD from sniper daily)
    Settlement timing unknown (no live score API integrated)
    Capital tied up 2.5+ hours per game = can't redeploy for crypto sniper

  Monitor but do not build at current scale.

### REVISED PRIORITY STACK (Session 68)

  PRIORITY 1 — Bot monitoring and sniper operation (automated)
  PRIORITY 2 — Sol drift graduation (need 2 more bets — passive)
  PRIORITY 3 — GEFS weather test Monday March 16 (HIGHNY markets)
  PRIORITY 4 — March Madness bracket review March 15 (passive, monitor only)
  
  DEAD ENDS CONFIRMED THIS SESSION:
    Other crypto 15-min series (BCH/BNB/ADA/DOGE): 0 active markets
    FOMC/FED markets: no liquid near-term markets
    NCAAB conference tournament: no bid/ask (illiquid)
    KXMVE parlay markets: settled-but-not-paid, not tradeable
    KXBTCD weekly markets: null bid/ask (weekend illiquidity)
    Lowering sniper trigger to 87c: insufficient data (only 2 bets)
    Raising sniper trigger to 95c: confirmed terrible EV (0.4% ROI)

