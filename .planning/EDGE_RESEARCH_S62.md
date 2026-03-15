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

---

## SESSION 69 ADDITIONS (2026-03-14)

### 32. KXBTCD DAILY THRESHOLD NEAR-EXPIRY SNIPER — CONFIRMED DEAD END

  Research question: Can the expiry sniper be expanded to KXBTCD daily markets
  in their final 840 seconds when BTC is clearly above/below the daily threshold?

  Market structure (live probe, 19:00 UTC March 14):
    KXBTCD 5pm ET slot (21:00 UTC): 40 markets, thresholds at $500 increments
    BTC current price: ~$70,750
    T70,250 YES: bid=0.87, ask=0.88 (at 2 hours remaining)
    T70,750 YES: bid=0.38, ask=0.39 (at 2 hours remaining)
    T69,750 YES: bid=0.98, ask=0.99 (at 2 hours remaining)
    KXBTCD 3pm ET slot (19:00 UTC, closing NOW): all at 99c or 0c, illiquid

  Why the sniper can't fire here:
    1. Threshold granularity ($500 steps) creates cliff from 38c to 87c to 98c
       No threshold naturally lands at 90-95c — the gap jumps over it
    2. In the FINAL 14 MINUTES before 5pm ET, BTC is usually far from threshold
       Markets jump to 99c directly (BTC moved hours ago)
    3. The rare case where BTC is $200-300 above threshold at t-14min:
       Market prices this at 90-95c but TRUE probability ≈ 90-95% (correctly priced)
       No systematic bias to exploit (unlike 15-min windows where drift commits early)
    4. Settlement is based on BTC price at exactly 5pm ET — one data point
       15-min sniper: settlement based on AVERAGE over interval (less volatile)
       Daily sniper: single-moment settlement = more susceptible to last-second moves
    5. Weekend KXBTCD markets: near-zero liquidity (confirmed: bid=0 ask=0.01)

  VERDICT: KXBTCD near-expiry sniper not viable. Dead end confirmed.

### 33. NCAA TOURNAMENT MARKETS — NOT OPEN YET (bracket announced March 15)

  Checked all series at 19:00 UTC March 14 (Selection Sunday eve):
    KXNCAABPICKS, KXNCAABCHAMP, KXCBB, KXNCAABBRACKET, KXMM26 — all 0 markets
    KXMARMAD (champion futures): 30 markets open, all at 0-1c bid (longshot losers)
    KXNCAAMBGAME open: 18 conference tournament games (March 28 close dates)
    No March Madness round-specific markets exist yet

  KXMARMAD champion futures: Nebraska 1.3M vol at 0c bid, Wisconsin 2M vol at 1c bid
    These are all teams that won't win the championship (correctly priced at ~0%)
    Even the "favorites" for the tournament would be priced at 5-15c max
    Capital efficiency terrible at any price: tournament takes 5 weeks to settle
    NOT worth building a scanner for these

  NEXT ACTION: Check Tuesday/Wednesday after bracket drops (March 15) for:
    - New KXNCAAMBGAME markets for Round 1 games (March 20+)
    - Any 1-vs-16 seed games at 90c+ (structural favorite-longshot edge)
    - Use ncaab_live_monitor.py as the observation tool

### 34. NCAA TOTAL POINTS + SPREAD MARKETS — LOW VOLUME, WIDE SPREADS

  Checked: KXNCAAMBTOTAL, KXNCAAMBSPREAD, KXNCAAMB1HSPREAD
    KXNCAAMBTOTAL: 20 markets, but volume 0-25 per market (near-zero liquidity)
    KXNCAAMBSPREAD: 20 markets, volume 0-32, bid-ask spreads 3-35c (wide)
    KXNCAAMB1HSPREAD: 10 liquid markets, but bid=0.13 / ask=0.80 = 67c spread (!)

  These markets are controlled by a single market maker with huge margins.
  Not suitable for any strategy (taker or maker) at these spreads.

  VERDICT: NCAAB totals and half-spreads are illiquid dead ends.

### 35. EDGE SCANNER — GAME-IN-PROGRESS FILTER ADDED (code fix)

  Bug fixed: S62 Section 22 documented "FIX NEEDED: Filter scanner to games
  with commence_time > now + 30min." This was never implemented.

  Symptoms (re-confirmed in live run): Wisconsin/Michigan and Vanderbilt/Florida
  showed 13.8% and 3.6% "taker edge" because games had started 2 hours earlier.
  Kalshi showed live in-game prices; Pinnacle still showed pre-game odds.
  Inverted bid/ask (bid=50c, ask=1c) was the telltale sign of settled markets.

  Fix implemented:
    - Added _game_started(commence_time: str) -> bool helper function
    - run_scan() now calls _game_started() before appending any opportunity
    - Games that started before current UTC time are silently skipped (DEBUG log)
    - Fail-safe: empty or unparseable timestamps are NOT filtered
    - 7 new tests in TestGameStarted (34 total, all passing)
    - Commit: 24a087e

  Post-fix scan results (19:11 UTC, March 14):
    50 matched markets | 0 pre-game opportunities above 2% taker edge
    Only pre-game market found: Washington vs Boston, 1.1% taker edge (not actionable)

  FINAL CONFIRMATION: Sports pre-game taker arb is dead — cleanly confirmed
  with correct filter. Max 1.1% edge tonight. The 2.4% S62 finding holds.

### REVISED PRIORITY STACK (Session 69)

  PRIORITY 1 — Bot monitoring and sniper operation (automated)
  PRIORITY 2 — Sol drift graduation (still 28/30 — need 2 more settled bets)
  PRIORITY 3 — GEFS weather test Monday March 16 (first weekday HIGHNY check)
  PRIORITY 4 — NCAA tournament markets after bracket drops (March 15 6pm ET)
    Watch for 1-vs-16 seed games opening at 90c+ for favorable sniper edge
    Use ncaab_live_monitor.py for observation. Do NOT build auto-trader yet.

  DEAD ENDS ADDED THIS SESSION:
    KXBTCD near-expiry sniper: threshold gaps prevent 90-95c zone (confirmed)
    KXMARMAD champion futures: longshot market, illiquid, weeks to settle
    NCAAB totals (KXNCAAMBTOTAL): near-zero volume, wide spreads
    NCAAB half-spreads (KXNCAAMB1HSPREAD): 67c bid-ask spread, untradeable


### 36. FOMC CROSS-MARKET CHAIN CONSISTENCY — NOT EXPLOITABLE (Session 70)

  Checked all 80 open KXFEDDECISION markets at ~19:30 UTC March 14.
  Five outcome types per meeting: H0 (hold), H25 (hold after 1 prior cut),
  H26 (hold after 2 cuts), C25 (cut 25bp), C26 (cut 50bp cumulative).

  Chain analysis (Hold probability by meeting date):
    26MAR: 99.5%  (11.2M vol, 1c spread) — near certain, 4 days away
    26APR: 92.5%  (254K vol, 1c spread) — liquid, efficiently priced
    26JUN: 64.0%  (44K vol, 4c spread) — moderate liquidity
    26JUL: 60.5%  (3,735 vol, 1c spread) — thin
    26SEP: 67.0%  (131 vol, 10c spread) — essentially illiquid
    26OCT: 71.0%  (414 vol, 10c spread) — illiquid
    26DEC: 74.5%  (2,476 vol, 5c spread) — low liquidity
    27JAN: 68.5%  (3,106 vol, 1c spread) — thin

  Chain "violations" detected (hold probability increasing over time):
    SEP > JUL, OCT > SEP, DEC > OCT
    These appear backward (later meetings can't be MORE certain of holding if
    earlier meeting held). But these are LIQUIDITY ARTIFACTS — with only 131-414
    contracts traded in these markets, a few retail bets can move prices 10%.

  Key finding: No cross-market arbitrage exists.
    Near-term markets (MAR, APR) are priced by sophisticated traders (10M+ vol)
    Far-term markets (JUL+) are illiquid noise (wide spreads eat any edge)
    The "violations" cannot be exploited — bid/ask spreads are 5-10c wide
    Any arb trade would immediately lose money to the spread

  FOMC edge only viable through INFORMATION SPEED (CPI speed-play):
    After April 10 CPI surprise: APR and JUN markets will reprice
    APR Hold (92.5c mid, 1c spread): significant repricing if CPI surprises
    JUN Hold (64.0c mid, 4c spread): larger movement expected
    Target: CPI monitor detects release → buy BEFORE repricing completes
    CPI release monitor (scripts/cpi_release_monitor.py) ready for April 10.

  VERDICT: No structural FOMC chain arb. Speed-play is the only viable FOMC edge.

### 37. SNIPER MAKER MODE ANALYSIS — NOT VIABLE FOR SNIPER (Session 70)

  Checked whether adding maker_mode=True to expiry_sniper_loop() would save fees.

  Fee math at 90c YES:
    Kalshi taker fee = 7% × price × (1-price) = 7% × 0.90 × 0.10 = 0.63c/contract
    For 5 USD bet at 90c: 5.56 contracts × 0.63c = 3.5c = 0.035 USD saved per bet
    At 135 bets/day: 135 × 0.035 = 4.73 USD/day potential savings

  Why maker mode fails for the sniper:
    1. Sniper fires in final 840 seconds — urgency requires guaranteed fills
    2. Post-only order at bid price (90c) waits for seller — market may skip to 95c
    3. If market is approaching expiry, takers are the natural flow, not makers
    4. At 90c, there's very little two-sided flow to fill maker orders against
    5. Risk of missing fill entirely > 0.035 USD fee savings per bet

  Current status: drift loops (btc/eth/sol/xrp) already use maker_mode=True (S65)
    These work because drift markets have longer windows and two-sided flow at 35-65c
    Sniper stays taker-only — correct design, no change needed.

  VERDICT: Sniper maker mode = dead end. Drift maker mode already implemented.

### REVISED PRIORITY STACK (Session 70)

  PRIORITY 1 — Bot monitoring (automated, ongoing)
  PRIORITY 2 — Sol drift graduation (28/30 — 2 more needed → Stage 2 eval)
  PRIORITY 3 — NCAA tournament markets after bracket drops (March 15 23:00 UTC)
    Specifically: 1-vs-16 seed Round 1 games, historical 99.4% 1-seed win rate
    If Kalshi prices these at 90-93c, edge is confirmed by FLB + historical data
    Use ncaab_live_monitor.py for observation. Research only, no auto-trading.
  PRIORITY 4 — GEFS weather test Monday March 16 (first weekday HIGHNY check)
  PRIORITY 5 — CPI release monitor ready (April 10 08:30 ET)

  DEAD ENDS ADDED THIS SESSION:
    FOMC cross-market chain arb: illiquidity artifacts beyond July, no exploitable gap
    Sniper maker mode: urgency incompatible with maker order risk of non-fill

---

## SESSION 72 ADDITIONS (2026-03-14)

### 38. SNIPER DEEP ANALYSIS — 192 LIVE BETS (updated)

  Price bucket breakdown (all 192 live settled, excluding 99c):
  
    85-89c: 2 bets, 100% WR, EV=1.54 USD/bet, ROI=37%+ [only 2 bets, tiny sample]
    90-94c: 91 bets, 97.8% WR, +58.2 USD — THE PROFIT ENGINE (97.8% vs 93% break-even)
    95-96c: 49 bets, 98.0% WR, +4.97 USD — marginal (1 large loss of -14.40 wiped gains)
    97-98c: 31 bets, 100% WR, +5.46 USD — profitable, small per-bet margins
    99c:    19 bets,  0% NET WR, -14.85 USD — ZERO profitable wins (all 0-net or 1 loss)

  Key insight: 99c bucket shows 0% EFFECTIVE WR because at 99c, taker fee = gross profit.
  18 of 19 bets won but had pnl_cents=0. 1 bet lost 14.85 USD. Net: -14.85 USD wasted.
  The 99c pre-execution guard (coded S70, commit 8d252ae) MUST be activated via restart.
  
  Correlated loss risk:
  - 4 losses in history. 2 occurred in same 15-min window (26MAR122330, BTC+SOL both at 93c YES)
  - This was the only multi-asset loss window in 192 bets
  - XRP has ZERO losses in 38 bets (perfect record)
  - ETH had 1 large loss (96c NO, -14.40 USD) in 45 bets
  
  Per-asset performance (excluding 99c):
    SOL: 51 bets, 98.0% WR, +23.34 USD
    XRP: 38 bets, 100% WR, +19.42 USD (ZERO losses — best asset)
    BTC: 39 bets, 97.4% WR, +16.44 USD
    ETH: 45 bets, 97.8% WR, +12.51 USD

  Hourly pattern (concerning): 
    03:xx UTC (10pm ET): 6 bets, 66.7% WR, -8.25 USD (2 losses at 93c)
    07:xx UTC (2am ET): 13 bets, 92.3% WR, -7.24 USD (1 loss at 96c)
    All other hours: 100% WR
    Note: 2 data points per hour is too few to conclude systematic pattern.

  RECOMMENDATION: 
    - Keep 90c trigger (confirmed optimal, 90-94c bucket is profit engine)
    - Do NOT raise to 95c (eliminates the main profit engine)
    - Do NOT lower to 87c without more paper test data (only 2 bets at 85c)
    - Consider soft cap at 98c (99c clearly zero/negative EV)

### 39. WEATHER MARKETS — MAJOR SYSTEMATIC INEFFICIENCY DISCOVERED

  Core finding: Kalshi weather markets are severely mispriced because participants
  use historical seasonal averages instead of actual weather model forecasts.
  GEFS ensemble consistently shows 30-80% different probabilities than Kalshi prices.

  Market structure (KXHIGH* series):
    Open: daily for NYC (KXHIGHNY), LAX (KXHIGHLAX), CHI (KXHIGHCHI), 
          MIA (KXHIGHMIA), DEN (KXHIGHDEN) — confirmed OPEN DAILY not just weekdays
    Settlement: same day (daily high temperature recorded by NWS)
    Formats: 
      T-prefix = threshold ("be >79°" or "be <72°") — parse_temp_bracket handles these
      B-prefix = bracket ("be 78-79°") — parse_temp_bracket CANNOT parse these (returns None)

  Live edge scan (March 14, 23:00 UTC — markets for March 15):
  
    BEST: LAX YES@5c — "Will LA high be >79° on Mar 15?"
      GEFS: 83.9% probability above 79F (mean=79.8F, all members 77.6-81.6F)
      Open-Meteo point forecast: 83.5F for March 15
      Kalshi market: 5% probability (YES=5c)
      Edge: +78.9% | EV per 5 USD bet: +78.87 USD (if GEFS correct)
      CAVEAT: March 14 actual high was ~78-79F vs point forecast of 83.2F (4F overestimate)
      Adjusted real probability: likely 40-70% (vs Kalshi's 5%) → still massive edge
    
    NYC YES@38c — "Will NYC high be <47° on Mar 15?"
      GEFS: 96.8% probability below 47F (mean=45.3F, range [42.3, 47.4F])
      Kalshi: 38% probability (YES=38c) — market thinks high will EXCEED 47F
      Edge: +58.8% | EV per 5 USD bet: +7.73 USD
      GEFS confidence: very tight distribution, all members < 47.4F
      
    CHI YES@19c — "Will CHI high be >60° on Mar 15?"
      GEFS: mean=57.9F, range [54.7, 61.5F]
      Kalshi: 19% probability of above 60F
      Edge: data calculation has date-mismatch bug (see below), directional finding valid
      
    DEN NO@30c — "Will DEN high be <49°?" Kalshi YES=68c, GEFS says mostly above
      GEFS: mean=51.1F, range [48.4, 53.4F] — some uncertainty around 49F threshold
  
  Historical accuracy check (March 13-14 LAX settled data):
    March 13: actual high = 87-88F (B87.5 settled YES). GEFS would predict warm day. ✓
    March 14: actual high = ~78-79F (B78.5 settling YES, T79 settling NO).
              Point forecast said 83.2F — overestimate by 4-5F.
    Implication: models are directionally correct but can overestimate by 4-5F.
    REAL edge on LAX T79 March 15: probably 30-50% true probability vs Kalshi's 5%.
  
  WHY THIS INEFFICIENCY EXISTS:
    1. Kalshi weather participants set prices based on historical seasonal averages
    2. March average highs: NYC ~45-50F, LA ~68-72F, CHI ~45-55F
    3. Participants anchor on "normal March temperatures" ignoring active weather models
    4. GEFS updates every 6 hours with 31 member ensemble — far more information
    5. Low volume markets (1K-22K fp) means few sophisticated participants updating prices
    6. High volume markets (100K+) like KXHIGHLAX-26MAR14-T79 (settled) HAD already moved
       to correct prices by late day — early-day prices are where the edge lives

  BUGS IN CURRENT WEATHER STRATEGY (explain why it never fires):
    BUG 1: Only monitors KXHIGHNY (NYC) — misses LAX, CHI, DEN, MIA
           These other cities often have bigger mispricings (more unusual weather)
    BUG 2: parse_temp_bracket() returns None for B-prefix bracket markets ("78-79°")
           Only handles T-prefix threshold markets (">79°" or "<47°")
           The B-prefix markets represent 50-60% of all weather market volume
    BUG 3: Date mismatch possible — GEFS fetches next forecast date but strategy may
           evaluate markets for today (T-date market still open but day nearly over)
    BUG 4: config.yaml only specifies NYC series, no multi-city support

  WHAT NEEDS TO BE BUILT (prioritized):
    1. Multi-city weather loop: run weather_loop for each of 5 cities in parallel
    2. Fix parse_temp_bracket for B-prefix bracket markets ("be 78-79°")
    3. Date-awareness: skip markets closing today before confirming GEFS date matches
    4. Weather strategy live activation: paper test shows 5+ clear signals per day
    5. Consider higher max_daily_bets (currently likely 1-3 per day cap)
  
  EXPECTED EDGE QUANTIFICATION:
    Conservative estimate: 20-40% edge after GEFS calibration uncertainty
    With 10 markets per day at 5 USD/bet: 5-20 USD expected daily profit
    Capital efficiency: 1-day settlement (same day as weather measurement)
    Competition: essentially zero — market participants clearly not using weather models

  PRIORITY: HIGH — this is a buildable, daily-recurring edge with zero HFT competition
  The GEFS ensemble is public and free. The inefficiency is structural.
  Implementation: 1-2 sessions of work.

### 40. NCAA TOURNAMENT MARKETS — NOT YET OPEN (S72 status check)

  Checked March 14 23:xx UTC (Selection Sunday eve):
  - KXNCAAMBGAME: only 2 markets open (Wichita vs Tulsa conference game, closes March 28)
  - KXMARMAD: 20 "champion futures" markets, all at 0-1c YES (longshot losers)
  - No Round 1 tournament markets open yet (bracket announced March 15 evening)
  
  Next action: Check Tuesday/Wednesday March 17-18 for:
    - KXNCAAMBGAME Round 1 games (March 20+)
    - 1-vs-16 matchups at 90c+ for sniper edge
    - Use ncaab_live_monitor.py

### 41. WEATHER CALIBRATION ANALYSIS — Session 72 (2026-03-14)

  Compared Open-Meteo historical archive temps to Kalshi settlement data (last 7 days)
  to understand GEFS calibration bias by city:

  NYC: WELL CALIBRATED. Open-Meteo archive within ±2F of Kalshi settlement.
    - March 13 actual: < 45F (Kalshi) — consistent with Open-Meteo 41.7F
    - March 10: > 73F (Kalshi) — consistent with Open-Meteo 75.9F
    - March 11: 72-73F (Kalshi) vs Open-Meteo 72.1F — near-exact match
    CONCLUSION: GEFS predictions for NYC are reliable. Large edges at NYC are real.

  LAX: SYSTEMATIC 4-7F WARM BIAS. Open-Meteo archive consistently warmer than Kalshi:
    - March 13 actual: 87-88F (Kalshi) vs Open-Meteo 92.5F (+5F warm bias)
    - March 12 actual: < 85F (Kalshi) vs Open-Meteo 91.7F (+6-7F warm bias)
    - March 11 actual: < 70F (Kalshi) vs Open-Meteo 77.7F (+7-8F warm bias)
    - March 10 actual: 67-68F (Kalshi) vs Open-Meteo 71.4F (+3-4F warm bias)
    NOTE: Open-Meteo archive (ERA5) ≠ GEFS ensemble (different models). Bias may differ.
    CRITICAL: GEFS ensemble for LAX may ALSO have warm bias. Need to monitor settlements.
    If GEFS warm bias ~5F for LAX: March 15 predicted mean 79.8F → actual maybe 74-75F
    → "above 79F YES@8c" edge is likely smaller than calculated (maybe 20-30% not 80%)

  CHI: MIXED, HIGH VARIANCE. Open-Meteo sometimes off by 5-12F:
    - March 13: Kalshi 48-49F vs Open-Meteo 36F (Open-Meteo too cold by 12F — big discrepancy)
    - March 12: Kalshi 44-45F vs Open-Meteo 44.5F — nearly exact
    - March 10: Kalshi 63-64F vs Open-Meteo 58.9F (Open-Meteo too cold by 5F)
    CHI is highly location-sensitive (lakefront vs inland temp varies). Use with caution.

  DEN: WELL CALIBRATED. Generally within 2-3F:
    - March 13 actual: < 68F (Kalshi) vs Open-Meteo 68.5F — 0.5F off
    - March 12 actual: 66-67F (Kalshi) vs Open-Meteo 64.7F — 2F off
    - March 9 actual: 73-74F (Kalshi) vs Open-Meteo 70.7F — 3F off
    CONCLUSION: DEN edges are likely real. Current DEN NO edge (+64%) is credible.

  IMPORTANT CAVEAT: Open-Meteo archive (ERA5 reanalysis) is a DIFFERENT model than GEFS
  ensemble forecast. The calibration biases above may not apply to GEFS forecasts.
  Best calibration approach: run paper weather loop for 4+ weeks and track GEFS vs Kalshi.

  TACTICAL IMPLICATIONS:
  - NYC weather edges: HIGH CONFIDENCE (well-calibrated model, large vol, structured edge)
  - DEN weather edges: HIGH CONFIDENCE (well-calibrated, DEN swings match GEFS predictions)
  - CHI weather edges: MEDIUM CONFIDENCE (high variance location, validate with paper data)
  - LAX weather edges: LOWER CONFIDENCE until bias characterized (may be 5F warm bias)
  - MIA weather edges: UNKNOWN (insufficient data, stable tropical climate helps GEFS)

### 42. SNIPER BUCKET PERFORMANCE — Full 199-bet analysis (Session 72)

  As of 2026-03-14, 199 live settled sniper bets total:

  90-94c bucket: 92 bets | 90W/2L (97.8%) | +58.95 USD | avg@93c | ROI 69.0%
    → PROFIT ENGINE. Clear structural edge. Both losses are within statistical variance.
    → At 97.8% WR vs 93c breakeven ~93%, edge = ~5% per bet.

  95-98c bucket: 85 bets | 84W/1L (98.8%) | +11.93 USD | avg@96c | ROI 14.6%
    → POSITIVE EV but thin (4c payout, tiny margin). Do NOT add guard here — still +EV.
    → At 98.8% WR vs 96c breakeven ~96%, edge = ~2.8% per bet.

  99c bucket: 20 bets | 19W/1L (95.0%) | -14.85 USD | avg@99c | ROI -75.0%
    → CATASTROPHIC. 99c gives 1c payout, 1 loss wipes ~15 USD of wins.
    → Guard coded (commit 8d252ae) but NOT active until bot restart.
    → WITHOUT guard: losing 14.85 USD (25% of all sniper profit hidden by this drag)
    → WITH guard (after restart): projected all-time sniper = +73.96 USD instead of 59.11 USD

  other (85-89c): 2 bets | 2W | +3.08 USD | avg@85c | ROI 181.2%
    → Only 2 bets — statistically useless. Monitor if trigger changes.

  TOTAL: 199 bets | 195W/4L | +59.11 USD. Guard will recover ~14.85 USD after restart.

### REVISED PRIORITY STACK (Session 72 end-of-session)

  COMPLETED THIS SESSION:
  - scripts/weather_edge_scanner.py: 5-city GEFS vs Kalshi scanner, 31 tests
  - src/strategies/weather_forecast.py: parse_temp_bracket fix for 78-79deg format
  - main.py + weather.py: 5-city weather loop expansion (LAX, CHI, DEN, MIA added)
  - Calibration analysis: NYC/DEN calibrated, LAX has warm bias warning
  - Sniper bucket analysis: full 199-bet breakdown confirms 99c guard is critical

  PRIORITY 1 — RESTART BOT to activate 99c guard (other chat — not this chat)
    Impact: +14.85 USD recovery (25% improvement on sniper profits)

  PRIORITY 2 — Monitor paper weather loop for 4+ weeks (all 5 cities now collecting)
    Check calibration after 20+ paper bets per city
    Cities to trust first: NYC, DEN (well-calibrated)
    Cities to validate: CHI, MIA (limited data), LAX (warm bias risk)

  PRIORITY 3 — NCAA tournament markets (March 17-18)
    Round 1 games start March 20. 1-vs-16 seed matchups at 90c+ for sniper.
    Check KXNCAAMBGAME series after bracket drops March 15 evening.

  PRIORITY 4 — Sol drift graduation (28/30 live bets, 2 more needed)
    Other chat handles this via monitoring loop.

  PRIORITY 5 — CPI release monitor ready (April 10 08:30 ET)

  DEAD ENDS (cumulative — do not revisit):
    PGA golf sniper, non-crypto 90c+ markets, Kalshi copy trading, FOMC cross-market arb,
    sniper maker mode, NBA/NHL at current scale, tennis/NCAAB sniper at current scale,
    weather NO at 99c, KXBTCD near-expiry sniper, FOMC chain arb, sports taker arb,
    BALLDONTLIE API, NCAA totals/spreads

  OPEN LEADS:
    - LAX weather bias: need 10+ paper bets to characterize (if systematic warm bias, adjust)
    - CHI weather calibration: high variance — run paper before trusting
    - NCAA 1-vs-16 seed game sniper (March 17-18 check)
    - CPI speed-play signal (April 10 08:30 ET)

### 43. SESSION 72 RESEARCH CONTINUATION (2026-03-15 ~03:00 UTC)

**BOT STATUS AFTER S72 RESEARCH:**
- All 5 city weather loops now CONFIRMED ACTIVE (bot restarted twice — 2nd restart at 22:00 UTC needed because 1st restart was BEFORE commit 1c5f12c)
- First paper bets placed for all 5 cities (March 15 markets):
  - LAX: YES@8c (GEFS 93.5% ≥79F) — 5 bets placed
  - CHI: YES@26c (GEFS 96.8% <60F) — 5 bets placed
  - DEN: NO@7c (GEFS 93.5% ≥49F) — 1 bet placed
  - MIA: 3 bets placed (NO@72c, NO@61c, YES@18c)
  - NYC: 0 bets (no open markets at restart time)

**FEE-FLOOR BUG FOUND AND FIXED (commit 1d12f46):**
- Bug: NO@99c slips through 99c guard in live.py. Root cause: YES-equiv(NO@99c) = 1c ∈ [1,99].
- Live incident: trade 2111 KXXRP15M NO@99c placed at 22:44 UTC (signal was 93c, orderbook drifted)
- Fix: added raw price_cents >= 99 || <= 1 block BEFORE YES-equiv conversion in execute()
- 3 new regression tests (TestSniperFeeFlorBlock). 1198 tests total.
- Impact: prevents exact repeat of -14.85 USD scenario from the 99c bucket analysis

**MARKETS SCANNED (no opportunities found):**
- FOMC: No March 2026 market on Kalshi (gap from 26JAN settled to 26DEC open). FOMC loop is running paper but finds no March markets. The strategy is effectively dormant until June 2026.
- NBA/NHL: 20 NBA + 20 NHL game markets open. No high-confidence (90c+) tonight except GSW/NYK at 86c (below threshold). Edge scanner: 0 opportunities at 2% threshold (same as before).
- NCAA: No KXNCAAMBGAME markets open yet. Bracket drops March 15 evening US time. Re-check March 17-18.
- KXBTCD daily: All markets within 2% of Black-Scholes fair value at BTC~71K. No edge.
- CPI: KXCPI-26MAR open (30K+ vol on T0.7 at 49c). No forecasting edge without Bloomberg consensus. Speed-play only (April 10 08:30 ET).

**REVISED PRIORITY STACK (Session 72 final):**

COMPLETED THIS SESSION:
- 5-city weather scanner, fix, expansion — all done, paper collecting
- Off-peak promotion documented (all 3 key files + commit 3c59276)
- Fee-floor bug fixed (commit 1d12f46, 3 regression tests)
- Bot PID 32120 → session73.log, all fixes active

PRIORITY 1 — Sol drift graduation (28/30 bets)
  Check hourly: ./venv/bin/python3 main.py --graduation-status | grep sol
  When 30/30: full Stage 2 analysis (10 USD max/bet evaluation per PRINCIPLES.md)

PRIORITY 2 — NCAA bracket (March 15 evening US time)
  Re-check KXNCAAMBGAME March 17-18 for 1-vs-16 seed matchups at 90c+
  Use scripts/ncaab_live_monitor.py. First Four games March 19-20.

PRIORITY 3 — Weather calibration check (after March 14 settlements ~04:00 UTC)
  Key calibration bets: LAX YES@8c (93.5%), CHI YES@26c (96.8%), DEN NO@7c (93.5%)
  If all 3 win: strong GEFS validation for these cities
  If LAX loses: confirms warm bias — adjust LAX edge threshold upward (needs 10+ bets)

PRIORITY 4 — Weather paper data accumulation (collect 4+ weeks before going live)
  Daily scanner: python3 scripts/weather_edge_scanner.py --min-edge 0.10
  Trust first: NYC (±2F), DEN (±2-3F)
  Validate before live: LAX (warm bias risk), CHI (high variance), MIA (unknown)

DEAD ENDS (cumulative — do not revisit):
  PGA golf sniper, non-crypto 90c+ markets, Kalshi copy trading, FOMC cross-market arb,
  sniper maker mode, NBA/NHL at current scale, tennis/NCAAB sniper at current scale,
  weather NO at 99c, KXBTCD near-expiry sniper, FOMC chain arb, sports taker arb,
  BALLDONTLIE API, NCAA totals/spreads, KXBTCD daily sniper (markets are fair-priced),
  FOMC March 2026 (no market exists on Kalshi — gap from Jan to Dec 2026)

### 44. SESSION 73 RESEARCH (2026-03-15 ~05:00 UTC)

**BOT STATUS:**
- Running PID 33894 → /tmp/polybot_session74.log
- All-time live P&L: +20.24 USD (was +13.40 at session start — +6.84 gained)
- HARD_MAX_TRADE_USD raised from 15→20 USD (commit a5f9a82, active after restart)
- Sniper today: 24/25 (96%), +3.76 USD at 20 USD bet size

**MARKETS SCANNED (all confirmed dead ends for today):**
- KXNCAAMBGAME: 0 open (bracket dropped March 15 evening, Round 1 starts March 20-21)
- KXBNB15M/KXBCH15M: 0 active (series don't have meaningful live markets)
- KXMV parlay markets (KXMVESPORTSMULTIGAMEEXTENDED, KXMVECROSSCATEGORY): zero volume, Kalshi is only market maker, can't trade at scale
- NBA in-game sniper (KXNBAGAME at 90c+): capital efficiency 75x worse than crypto sniper (120-min game vs 2.5-min window). Not worth building.
- No other short-expiry (≤30 min) binary series found on Kalshi

**SNIPER DEEP ANALYTICS (199 settled bets):**
By asset:
  XRP: 57 bets, 100% WR, +23.91 USD (avg@96c) — best performer
  BTC: 49 bets, 98% WR, +22.98 USD (avg@94c)
  ETH: 57 bets, 98% WR, +17.59 USD (avg@95c)
  SOL: 67 bets, 96% WR, +0.79 USD (avg@95c) — near zero but explained by fee-floor bug

By side:
  NO: 113 bets, 98% WR, +34.78 USD
  YES: 117 bets, 97% WR, +30.49 USD

All 5 structural losses:
  1. SOL YES@99c x15 | -14.85 USD — FEE-FLOOR BUG (now fixed by guard in live.py)
  2. SOL NO@92c x16 | -14.72 USD — structural reversal (coin recovered)
  3. ETH NO@96c x15 | -14.40 USD — structural reversal (coin recovered)
  4. SOL YES@93c x5 | -4.65 USD — early micro-bet period
  5. BTC YES@93c x5 | -4.65 USD — early micro-bet period

KEY INSIGHT: SOL's poor +0.79 USD total was entirely explained by the fee-floor bug
(7 bets at 99c = -14.85 USD). After fee-floor fix, SOL 90-98c = +15.64 USD expected.
No systematic NO-side bias: 2 NO-side structural losses are within normal variance for
2% loss rate at n=200. No filter justified without more data.

The sniper code already has drift direction consistency filter — well-implemented, no
obvious improvements without historical price-at-loss-time data.

**NCAA TOURNAMENT SCANNER BUILT (scripts/ncaa_tournament_scanner.py):**
- One-shot scanner: Kalshi KXNCAAMBGAME vs the-odds-api sharp book comparison
- Highlights heavy favorites (90c+) underpriced by Kalshi vs Pinnacle
- Uses ~1 odds-api credit per run
- Commit: cab991f
- RUN March 17-18 when Kalshi opens Round 1 markets

**DEAD ENDS ADDED:**
  KXMV parlay markets (zero volume), NBA in-game sniper (75x capital efficiency loss)

**REVISED PRIORITY STACK (Session 73 end):**
  1. Sol drift graduation — 28/30 live bets → 2 more needed for Stage 2 eval (monitoring chat)
  2. NCAA scanner — run scripts/ncaa_tournament_scanner.py on March 17-18 (1 API credit/run)
     Focus on Round 1 1-vs-16 and 2-vs-15 seed matchups at 90c+ if underpriced vs Pinnacle
  3. Weather calibration — check March 14 settlements when available (~morning March 15)
     Run: python3 scripts/weather_edge_scanner.py --min-edge 0.10
  4. Monitor sniper performance at 20 USD bet size (first full day active today)
  5. CPI speed-play — ready for April 10 08:30 ET (run scripts/cpi_release_monitor.py then)

### 45. SESSION 74 RESEARCH (2026-03-15 ~07:00-10:00 UTC)

**BOT STATUS:**
- Running PID 33894 → /tmp/polybot_session74.log
- All-time live P&L at session start: +24.77 USD
- All-time live P&L at session end: +7.64 USD (large SOL loss mid-session)
- Sniper bet size: 20 USD (raised S72 15→20 per Matthew)

**SNIPER LOSS INVESTIGATION (trade 2169, -19.20 USD):**
- SOL YES@96c x20 — lost at 02:30 UTC March 15
- SOL reversed hard in final seconds before expiry
- This is the FOURTH SOL structural loss (all 4 listed in S73 analytics)
- Per PRINCIPLES.md: 71 SOL bets is insufficient to conclude structural issue
  z-score for SOL vs other assets: ~1.3, p~0.10 (not significant)
  Decision: do NOT add SOL-specific guard. Revisit at 200 SOL sniper bets.
- Current SOL sniper P&L: -16.56 USD (94.4% WR, 4 losses)
- XRP comparison: 100% WR, +27.66 USD (no losses at all)

**SNIPER BUCKET ANALYSIS (240 bets, updated):**
  85-89c (below threshold): not fired (guard prevents)
  90-94c: 110 bets, 107W/3L (97.3%), +62.95 USD — PROFIT ENGINE
  95-96c: 61 bets, 59W/2L (96.7%), -7.30 USD — NEGATIVE but distorted
  97-98c: 45 bets, 45W/0L (100%), +8.79 USD
  99c: 22 bets, 21W/1L, -14.85 USD — 99c guard ACTIVE (prevents future)
  Total: 240 bets, 234W/6L (97.5%), +52.67 USD

IMPORTANT — 95-96c bucket EV distortion:
  The -7.30 USD at 95-96c is NOT evidence of negative EV at that price.
  Historical contamination: old wins at 5 USD cap, recent losses at 20 USD cap.
  Decision: do NOT add 95-96c guard per PRINCIPLES.md. Need 200+ bets at
  current 20 USD size for valid EV assessment. Current data is poisoned by
  3 different bet sizes across the strategy's history.

**PER-ASSET SNIPER BREAKDOWN (Session 74 deep analysis):**
  XRP: 100% WR, +27.66 USD — no losses ever (57+ bets)
  BTC: ~98% WR, +24.84 USD
  ETH: ~98.3% WR, +19.88 USD
  SOL: 94.4% WR, -16.56 USD — only negative-P&L asset (4 losses)

  SOL risk flag: All 4 structural losses are SOL. But 71 bets, p~0.10.
  Wait for 200 SOL bets before any SOL-specific action.

**NON-CRYPTO 90c+ MARKET SCAN (CONFIRMED DEAD END):**
- Exhaustively scanned 2000+ Kalshi markets across all non-crypto series
- Result: ZERO markets found at 88c+ YES for non-crypto
- Checked: PGA PLAYERS Championship (Aberg 58c YES = drift zone, not sniper)
  NBA game markets, NHL game markets, entertainment, politics, economics
- Sports/entertainment market structure doesn't produce sustained 90c+ windows
  compatible with sniper timing (840-second window requirement)
- CONCLUSION: Sniper expansion to non-crypto is a DEAD END. Do not revisit.
- Best non-crypto lead from scan: PGA favorites at 60-80c (drift zone research)

**WEATHER CALIBRATION TRACKER BUILT:**
- Script: scripts/weather_calibration.py
- Checks all weather paper bets in DB
- Fetches current market prices via Kalshi API
- Infers outcomes: YES@0-2c + NO bet = LIKELY_WIN, YES@98-100c + NO bet = LIKELY_LOSS
- 5-tier inference: LIKELY_WIN, PROB_WIN, OPEN, PROB_LOSS, LIKELY_LOSS
- 33 tests in tests/test_weather_calibration.py (all passing)
- Commit: 0c47366
- March 15 paper bets all show OPEN (Kalshi settlement delayed 1-2 days)
  Markets show status=closed but result=OPEN → settlement loop won't trigger
  Need "finalized" status. Check again March 16-17.

**CPI MARKET STRUCTURE ANALYSIS:**
- KXCPI series: 20 markets open for April 10 BLS CPI release
- Settlement: "CPI increases by more than X% in March 2026" = MoM change
- Key thresholds: T0.6 at ~80c YES, T0.7 at ~56c YES
- Market pricing 80% chance MoM > 0.6% (tariff narrative dominant)
- Speed-play approach: detect BLS surprise at 08:30 ET April 10
  Trade before market fully reprices the surprise
- Script ready: scripts/cpi_release_monitor.py
- Key risk: BLS releases are instant-priced by algorithms now (sub-second)
  Our edge window: 5-15 seconds after release if strong surprise
  Smaller surprise (consensus miss) = more exploitable window

**NCAA TOURNAMENT:**
- KXNCAAMBGAME: 0 markets open as of 06:41 UTC March 15
- Bracket dropped March 15 evening ET — markets not yet created
- Confirmed: scanner script works correctly (scripts/ncaa_tournament_scanner.py)
- RUN: March 17-18 for Round 1 market creation (games March 20-21)
- Command: python3 scripts/ncaa_tournament_scanner.py --min-edge 0.03

**ANNUAL BTC MARKETS (KXBTCMAXY/KXBTCMINY):**
- Analyzed KXBTCMAXY (annual BTC high) and KXBTCMINY (annual BTC low)
- Problem: 9+ month settlement window = capital locked up with no information edge
- These are essentially drift zone (35-65c) markets stretched over a year
- GEFS-style signal doesn't exist for annual crypto forecasting at our scale
- CONCLUSION: Dead end. No edge, capital inefficiency.

**DEAD ENDS ADDED (Session 74):**
  Non-crypto 90c+ market expansion (exhaustive scan, 0 found in 2000 markets)
  Annual BTC price range markets (KXBTCMAXY/KXBTCMINY — 9+ month lockup, drift zone)

**REVISED PRIORITY STACK (Session 74 end):**
  1. Sol drift graduation — 28/30 → passive (other chat monitoring)
  2. NCAA scanner — run March 17-18 (scripts/ncaa_tournament_scanner.py --min-edge 0.03)
  3. Weather calibration — check March 15 paper bets when finalized (est. March 16-17)
     Key bet: LAX YES@8c for ">79°F March 15" — if LAX loses, confirms warm bias
     Action if loss: raise LAX edge threshold from 20% to 30%+ in weather strategy
  4. CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)
  5. Sniper per-asset monitoring — flag if SOL reaches 200 bets with WR still ~94%

---

## Session 76 Overnight Research (2026-03-15 ~08:10-13:15 UTC)

**PRIMARY OUTPUT: 96c/97c NEGATIVE-EV BUCKET GUARD DEPLOYED**

Matthew explicitly approved the 96c/97c guard during the session.
Implementation: src/execution/live.py (IL-10), 6 regression tests, BOUNDS.md updated.
Commit: cd32feb
Forward savings: ~37.47 USD structural drag eliminated.

Blocked buckets (data):
  96c both sides: 31 bets, 93.5% WR, -22.44 USD cumulative (needs >96% WR to break even)
  97c NO-side:    13 bets, 92.3% WR, -15.03 USD cumulative (needs >97% WR to break even)
  97c YES-side:   NOT blocked — 11 bets, 100% WR, +2.90 USD profitable

**BUG FOUND AND FIXED: SOL_DRIFT STAGE 2 AUTO-PROMOTION**

When bankroll crossed 100 USD, sizing module auto-promoted sol_drift to Stage 2 (10 USD cap).
This happened before the manual graduation gate (30 bets + Brier + limiting_factor) was met.
Evidence: trade 2243, sol_drift NO@57c, 13 contracts = 7.41 USD — double the historical avg of ~2 USD.
Fix: calibration_max_usd=5.0 restored in main.py. Commit: 05bcd65.
Re-evaluate when 30th bet settles (currently 29/30, Brier 0.184 = exceptional).

**SNIPER BUCKET ANALYSIS (ERA-CORRECTED)**

Historical bucket stats were contaminated by old small-bet era (5 contracts, ~4.65 USD/bet)
when HARD_MAX was 5 USD. Current era = 16-20 contracts, ~18.62-19.80 USD/bet.

Current-era (16+ contract) bucket performance:
  93c YES: 9/9 = 100% WR (old-era had 2 losses at 4.65 USD — not representative)
  92c NO:  5/6 = 83.3% WR (1 SOL reversal — not systematic, BTC = 3/3 = 100%)
  90c YES: 2/3 = 66.7% WR (1 XRP reversal — only 3 bets, not actionable)
  94-98c:  essentially 100% WR across all assets

Pattern: BTC sniper near-perfect at all price levels. SOL and XRP (more volatile) each had
1 single reversal in current era. Not systematic. Statistical noise at small sample sizes.

Statistical significance tests (all at alpha=0.20):
  92c NO (6 bets, 1 loss): p=39% vs H0: WR=92% — NOT significant
  90c YES (3 bets, 1 loss): p=27% vs H0: WR=90% — NOT significant
  Conclusion: No new guards warranted at current sample sizes.

**CORRELATED SNIPER RISK — STRUCTURAL CONCERN DOCUMENTED**

All 4 crypto assets (BTC/ETH/SOL/XRP) fire sniper simultaneously when prices move together.
At ~18.62 USD/asset, 4 simultaneous open positions = ~75 USD of capital at risk per window.
With HARD_MAX_TRADE_USD = 20 and MAX_TRADE_PCT = 15%, individual trades pass kill switch
but combined exposure can reach 60-80% of bankroll in one 15-minute window.

If a correlated reversal occurs (all 4 assets flip in final seconds), potential loss = ~75 USD.
Historical evidence: has NOT happened yet, but the structural risk exists.

Open question for Matthew: should a per-window concurrent position cap be added?
Example: max 2 simultaneous live positions = max ~40 USD per window vs 75 USD.
DO NOT implement without explicit approval — requires main.py + kill_switch changes.

**FORWARD EV WITH GUARDS**

Allowed buckets (90-95c, 97c YES, 98c):
  191 historical bets, 97.9% WR, +75.73 USD total P&L, +0.39 USD EV per bet

Blocked buckets (96c, 97c NO, 99c):
  66 historical bets, 93.9% WR, -52.32 USD total P&L — structurally blocked going forward

All drift strategies (btc/eth demoted to micro-live 0.01 cap, xrp micro-live):
  These contributed ~52 USD of historical losses before demotion. Now negligible.
  Sol_drift Stage 1 (5 USD cap): 29 bets, 75.9% WR, Brier 0.184 — positive EV going forward.

**SECURITY AUDIT COMPLETED**

.env file: NOT in git history (git log confirmed zero commits of .env).
.gitignore: .env properly excluded.
Credentials in source code: NONE found (IL-6 verified).
data/*.json: gitignored (SEC-3 fix from S74 confirmed active).
Remote: github.com/mpshields96/polymarket-bot — 4 commits ahead, not pushed.
Conclusion: Credentials are safe. No credential exposure risk.

**DEAD ENDS CONFIRMED (Session 76 overnight):**
  Historical bucket analysis without era-correction: misleading (now corrected)
  Treating bank-roll-triggered Stage 2 as equivalent to manually-gated Stage 2: bug, fixed

**REVISED PRIORITY STACK (Session 76 end):**
  1. Correlated sniper risk — Matthew decision needed on per-window position cap
  2. MAX_TRADE_PCT decision — currently 15% (raised S65); at 90c, 1 loss = 15.9% bankroll drawdown
     Matthew should decide: lower to 5% (smaller losses) or keep 15% (higher variance, higher volume)
  3. NCAA scanner — run March 17-18 (scripts/ncaa_tournament_scanner.py --min-edge 0.03)
  4. Weather calibration — check March 15 paper bets when finalized (est. March 16-17)
  5. Sol drift graduation — 29/30 → Stage 2 eval when 30th bet settles, Brier 0.184 outstanding
  6. CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)

---

## SESSION 78 RESEARCH FINDINGS (2026-03-15)

**BET SIZE REDUCTION — COMPLETED**

Matthew directive (explicit): "change the max bet size down if that's objectively wise"

Decision analysis at 113 USD bankroll, 15% cap:
- 1 loss at 90c = -16.95 USD = 15% drawdown per bet
- Today: -43.74 USD total from pre-guard losses (5 losses, 2 at 98c NO = -37.24 USD)
- Structural drag from blocked buckets was masking variance risk at current sizing

Decision: LOWERED to 10% / 15 USD hard max (commit a3192d1)
- At 113 USD: max bet = 11.29 USD (was 16.95 USD, -33% reduction)
- At 150 USD: max bet = 14.99 USD  
- At 200+ USD: capped at 15 USD

3 kill_switch tests updated. All 1281 tests pass. BOUNDS.md IL-3 updated.

**BUCKET GUARD STATUS — CONFIRMED COMPLETE**

All blocked buckets verified in live.py (lines 125-152):
- IL-5: 1c and 99c — BLOCKED (fee-negative, always)
- IL-10: 96c both sides — BLOCKED (93.5% WR, -22.44 USD historical)
- IL-10: 97c NO — BLOCKED (92.3% WR, -15.03 USD historical)
- IL-11: 98c NO — BLOCKED (92.9% WR, -25.54 USD historical)
- 97c YES: KEPT (100% WR, +2.90 USD)
- 98c YES: KEPT (100% WR, +3.02 USD)

Active profitable buckets: 90-95c both sides, 97c YES, 98c YES
Historical performance of active buckets only: 205/210 settled (97.6% WR), +80.14 USD

**NEW BOT VERIFICATION (PID 61970, started 13:42 UTC)**

First bets from new bot (13:51 UTC):
- YES@95c: 11.40 USD (10% of ~114 USD bankroll — within bounds)
- YES@94c: 9.40 USD
- YES@93c: 9.30 USD
- YES@95c: 9.50 USD

All bets in profitable buckets. No 96c/97c-NO/98c-NO bets since restart.
Bet size reduction is ACTIVE and VERIFIED.

**TODAY P&L ANALYSIS**

-43.74 USD session total, but:
- ALL 5 losses were pre-guard bets from bot instance before 09:25 UTC restart
- 2 losses at 98c NO (-18.62 USD each) = guard was not yet deployed
- Post-guard bot (PID 61970): 35+ wins, 1 valid loss (YES@94c — structural variance)
- All-time P&L: -39.10 USD (updated from -25 USD estimate; new losses from old bot)
- Forward EV with full guard stack in place: +0.39 USD per bet on active buckets

**WEATHER SCANNER TIMING**

GEFS forecasts 24-48 hours ahead. Scanner useless when open market date != GEFS forecast date.
- At 13:30 UTC March 15: GEFS forecasting March 16, markets open for March 15 = mismatch
- Bot placed valid paper bets at 02:59 UTC (early morning, GEFS date = market date)
- Run scanner ONLY in 04:00-08:00 UTC window for correct signal

**REVISED PRIORITY STACK (Session 78 end):**
  1. Sol drift graduation — 29/30, 1 more bet needed. Stage 1 cap still at 5 USD.
     When 30th settles: check Brier < 0.25 + limiting_factor==kelly → raise cap to 10 USD
  2. NCAA scanner — run March 17-18 (scripts/ncaa_tournament_scanner.py --min-edge 0.03)
     Focus on 1v16 seed matches opening at 90c+ on KXNCAAMBGAME series
  3. Weather calibration — March 15 paper bets settle ~04:00 UTC March 16
     Key bets: LAX YES@8c, CHI NO@91c, DEN NO@7c (DEN T49 NO@36c likely lost)
  4. Monitor sniper at new sizes — verify 11.29 USD → 15 USD ceiling as bankroll grows
  5. CPI speed-play — April 10 08:30 ET (scripts/cpi_release_monitor.py)
  6. Correlated sniper risk — still unresolved (need Matthew decision on per-window cap)

---

## SESSION 79 RESEARCH FINDINGS (2026-03-15)

**MARCH 14 GUARD-ADJUSTED ANALYSIS — DEFINITIVE**

Guard-separated March 14 performance:
  Active buckets (90-95c, 97c YES, 98c YES): 107 bets, 107W/0L, +79.87 USD
  Blocked buckets (96c, 97c NO, 98c NO, 99c): 52 bets, 50W/2L, -19.61 USD

Guards would have IMPROVED March 14 from +60.26 to +79.87 USD (no losses blocked).
The 2 blocked-bucket losses (-14.40 USD at 96c NO, -14.85 USD at 99c YES) are permanently prevented.

**BET SIZE RESTORATION ANALYSIS**

March 14 avg active-bucket bet size: 13.77 USD (15% cap, ~92 USD bankroll)
After restoration (15%/20 USD): at 113 USD bankroll, bet = min(16.95, 20) = 16.95 USD
First confirmed new-size bet: yes@97c = 18.43 USD (15% of ~123 USD bankroll)

Bankroll has grown to ~123 USD from session 78 wins:
  At 123 USD: 15% = 18.45 → 19 contracts @ 97c = 18.43 USD ✓

Forward EV calculation at restored sizes:
  All-time active-bucket WR: 97.7% (222 settled)
  EV scales with bet size: +0.39 USD/bet * (18.43/13.17) = +0.55 USD/bet
  At March 14 volume (107 active bets/day): projected ~+59 USD/day
  With March 14 blocked bets eliminated: no structural drag

**88c EXECUTION INVESTIGATION — NOT A BUG**

Trade 2650 stored in DB at 88c despite IL-4 90c trigger:
  Signal generated: "BUY YES @ 91c" (ABOVE 90c trigger — correct)
  Order executed at 88c (orderbook showed better price available)
  Result: WIN +1.43 USD
  DB stores EXECUTION price, not signal price. IL-4 enforced correctly at signal level.

**KXBTCD FRIDAY SNIPER — DEAD END**

KXBTCD 5PM markets have meaningful volume (35K+ on nearest-money contract at 94c).
Could theoretically fire in final 840s before 5PM ET Friday.
Dead end because: only 1 bet/day per expiry vs 15M series (96 windows/day).
Volume: ~35K vs 15M BTC at hundreds of thousands.
Capital efficiency: 15M wins by overwhelming margin. Not worth engineering cost.

**ALTERNATIVE CRYPTO 15M SERIES — CONFIRMED DEAD**

Checked: KXBNB15M, KXBCH15M, KXDOGE15M, KXAVAX15M, KXLINK15M, KXADA15M, KXLTC15M
All show 0 open markets. Bot already covers all 4 active series (BTC/ETH/SOL/XRP).

**NCAA SEED MATCHUP PRE-ANALYSIS**

Ready for March 17-18 when KXNCAAMBGAME markets open:
  1v16 matchups: 99.3% WR historically → prices at ~99c → BLOCKED by IL-5
    But: if Kalshi underprices at 93-95c → massive 4-6% structural edge (active bucket!)
  2v15 matchups: 94% WR historically → prices at ~94c → ACTIVE BUCKET
    Sweet spot: exactly in the 90-95c range with structural edge vs sharp books
  3v14: 84.7% → ~84c (below sniper range)
  
Action: run ncaa_tournament_scanner.py --min-edge 0.03 on March 17-18
Focus on: 1v16 underpriced at 93-95c (if any), 2v15 at 90-94c
Expected: 1-2 high-confidence pre-game bets at ~14-18 USD each

**ASSET EV BREAKDOWN (all-time active buckets)**

BTC: 47 bets, 46W/1L (97.9% WR), +29.70 USD, +0.63 USD/bet
ETH: 58 bets, 58W/0L (100% WR), +39.34 USD, +0.68 USD/bet (BEST)
SOL: 66 bets, 64W/2L (97.0% WR), +23.53 USD, +0.36 USD/bet
XRP: 55 bets, 53W/2L (96.4% WR), -3.19 USD, -0.06 USD/bet
  Note: XRP negative EV is from 2 losses at old 19.74 USD bet sizes. 
  At 16.95 USD max: forward EV positive (96.4% WR > 94% break-even at 95c avg).
  Need 200+ bets before considering guard per PRINCIPLES.md.

**UPDATED PRIORITY STACK (Session 79 end):**
  1. Sol drift graduation — 29/30, 1 more bet needed (Stage 1 cap 5 USD)
  2. NCAA scanner — run March 17-18 (focus: 1v16 underpriced, 2v15 near 94c)
  3. Weather calibration — March 15 bets settle ~04:00 UTC March 16
  4. Monitor bet sizes at restored levels (first win: 18.43 USD at 123 USD bankroll)
  5. CPI speed-play — April 10 08:30 ET
  6. XRP monitoring — 96.4% WR active bucket needs 200+ bets before evaluation

---

## SESSION 80 RESEARCH FINDINGS (2026-03-15, continuation)

**GUARD VALIDATION — CURRENT BOT CONFIRMED WORKING**

Session 80 started with context compaction from S79. Bot PID 68296 verified alive.
Session76.log (current active log) shows guard stack operating correctly:
- 96c YES/NO: signals generated, execution BLOCKED (live.py IL-10 working)
- 97c NO: signals blocked (IL-10)
- 97c YES: ALLOWED — first bet placed at 10:10 AM local (15:10 UTC) = 18.43 USD WIN
- 98c NO: BLOCKED (IL-11 working)
- 98c YES: ALLOWED — placed throughout session

All guard-violation losses in today's DB (06:31, 07:15, 13:30 UTC) are from PRE-GUARD
bot instances that ran before the S78/S79 restarts. Current bot (PID 68296) has 0 guard
violations since 15:07 UTC restart.

**TODAY'S P&L RECONCILIATION (2026-03-15)**

Today's total losses: -119 USD in raw losses, +56 USD in wins = -63 USD
Guard-violation losses (old bots): -19.2 (96c YES), -18.43 (97c NO), -18.62 (98c NO) = -56.25 USD
Valid active-bucket losses: -19.8 (90c YES), -19.74 (94c YES), -15.98 (94c YES), -7.41 (sol_drift)
Active-bucket-only P&L: -6.68 USD (with 67 bets, 64W/3L = 96% WR)

Key takeaway: If guards had been in ALL bot restarts from session start = -6.68 USD, not -63 USD.
Going forward, no more guard violations. Active-bucket P&L should dominate.

**SNIPER BUCKET ANALYSIS — ASYMMETRY FINDING (NOTE: LOW SAMPLE)**

All-time price bucket breakdown reveals:
YES@94c: 33 bets, 31W/2L (94%WR), -13.37 USD — AT BREAK-EVEN (94% needed)
YES@93c: 18 bets, 16W/2L (89%WR), +3.36 USD — BELOW break-even (93% needed) but +P&L
YES@90c: 4 bets, 3W/1L (75%WR), -16.74 USD — BELOW break-even (90% needed)

NO side at all prices: 100%WR (with only 1 exception: 92c NO at 89%WR from 9 bets)

Pattern: YES side loses occasionally at lower prices (90-94c); NO side nearly perfect.
CONCLUSION: NOT statistically significant at current sample sizes (need 200+ per bucket).
Do NOT add new YES-side guards based on this. Continue monitoring.
Break-even WRs: 90c=90%, 93c=93%, 94c=94% — very thin margins at these prices.

**CORRELATION RISK — LOW CONCERN**

Multi-bet windows (2+ simultaneous bets same 15-min window):
- 189 bets across multi-windows, +66.08 USD
- Only 4 multi-loss events in history, worst = -18.75 USD
- No new guards needed. Single large loss per event is within normal variance.

**CPI MARKET STATUS**

KXCPI-26MAR-T0.5: YES=90c, vol=33,066 — confirmed open (but NOT in default get_markets query!)
Must query all statuses: await client.get_markets(series_ticker='KXCPI', limit=200) to see it.
T0.4: YES=93c, T0.3: YES=98c also in active/near-active range.
These are NOT sniper targets (not 15M crypto markets). CPI speed-play = April 10 event.
No action needed now. Script scripts/cpi_release_monitor.py handles April 10.

**ALL-TIME ACTIVE BUCKET P&L (updated S80)**

Active buckets (excluding 96c, 97cNO, 98cNO, 99c, 1c):
- 230 bets, 224W/6L (97.4%WR), +75.82 USD
All-time total with blocked buckets: -43.42 USD
Guards have prevented -66.8 USD in blocked-bucket losses.
With guards now permanent: forward P&L should track active-bucket positive EV.

**GUARD SAVINGS RATE (estimated)**

From session76.log: ~20+ blocked 96c signals per hour (YES and NO sides)
Per blocked 96c bet EV = -0.47 USD (93.5%WR at 18 USD bet)
Savings: 20 × 0.47 = 9.4 USD/hour prevented in expected losses from 96c alone
Actual savings: blocked bucket in S80 alone (today's violations) = -56.25 USD prevented.

**UPDATED PRIORITY STACK (Session 80):**
  1. Sol drift graduation: 29/30, Brier 0.184. When 30th settles:
     - Remove calibration_max_usd=5.0 from main.py line 2952
     - Restart bot. Kelly will govern at ~5 USD (Stage 2 cap 10 USD, Kelly ≈ 5 USD)
  2. NCAA scanner: March 17-18 (KXNCAAMBGAME opens before Round 1 March 20-21)
  3. Weather calibration: check ~04:00 UTC March 16 (pending bets from today settle)
  4. CPI speed-play: April 10 08:30 ET (script ready)
  5. XRP monitoring: 58 bets, 97%WR, -0.76 USD (small sample, no guard warranted)

---

## Session 80 Research (2026-03-15 monitoring + research chat)

**BOT STATE:** PID 68296, writing to /tmp/polybot_session76.log. Post-guard all-time P&L improving from -43 → -22 USD over 3 hours. Pre-guard violations explained: 3 blocked-bucket losses (07:15, 13:30 UTC) from stale bot instance before S79 restart at 15:07 UTC.

**SOL/XRP VOLATILITY ASYMMETRY — MONITORING LEAD (NOT ACTIONABLE YET):**

All-time sniper by asset:
- BTC: 72 bets, 99%WR, +38.97 USD
- ETH: 86 bets, 99%WR, +35.96 USD  
- SOL: 95 bets, 95%WR, -18.73 USD
- XRP: 90 bets, 96%WR, -29.81 USD

SOL+XRP together destroy the strategy's P&L (-48.54 USD combined) while BTC+ETH are the profit center (+74.93 USD). Many losses are in pre-guard blocked buckets.

**Specific watch: 94c YES bucket for SOL and XRP:**
- SOL 94c YES: 11 bets, 90.9%WR, -8.33 USD (fee break-even = 94.37%. Below break-even.)
- XRP 94c YES: 14 bets, 92.9%WR, -9.69 USD (also below break-even.)
- BTC+ETH 94c YES: ~10 bets, ~100%WR, positive (no losses)

Structural explanation: SOL/XRP are 3-5x more volatile than BTC/ETH on 15M timeframes. At 94c YES near expiry, reversal is more likely for volatile assets because 6c gross margin is wiped by a single reversal. Fee break-even at 94c requires 94.37%WR — SOL/XRP can't sustain this.

**ACTION: Do NOT guard yet. Need 200+ bets at 94c YES for SOL and XRP separately (PRINCIPLES.md). Currently 25 combined. Monitor at 100+ bets for preliminary evidence.**

If SOL 94c YES hits 100+ bets still below 94.37%WR with p<0.1, flag as IL-12 candidate.

**KXGDP SPEED-PLAY (April 30) — NEW SERIES:**

KXGDP markets (Q1 2026 GDP, close April 30):
- T1.0 YES=86c vol=45,813 (86% chance GDP > 1.0%)
- T1.5 YES=77c vol=51,541
- T2.0 YES=65c vol=52,937

BEA publishes GDP advance estimate on April 30 at 08:30 ET. Same speed-play mechanism as CPI:
- Detect BEA release via API
- Bet markets at 86c+ before Kalshi reprices (30-120 second window)

BLOCKER: No FRED/BEA API key in .env. Register at fred.stlouisfed.org (free) to get FRED key. FRED has GDP data (series GDPC1) with same access pattern as BLS.

Same mechanism as CPI speed-play (not a new structural edge — just another data release event). The cpi_release_monitor.py could be extended to cover GDP and payrolls with minimal changes.

**PRIORITY STACK (updated Session 80 research):**
1. Sol drift graduation (29/30, Brier 0.184 — waiting for 30th bet)
2. NCAA scanner: March 17-18 (KXNCAAMBGAME opens, check 1v16 underpriced)
3. Weather calibration: March 16 ~04:00 UTC (10 pending paper bets settle)
4. CPI speed-play: April 10 08:30 ET (BLS quota burned today — don't run until April 10)
5. GDP speed-play: April 30 08:30 ET (register FRED key first)
6. SOL/XRP 94c YES monitoring: watch for IL-12 candidate at 100+ bets

**DEAD END CONFIRMED: KXBTCD near-expiry sniper (both 2PM and 5PM ET slots)**
All daily KXBTCD threshold markets are priced at 99c/0c when far from threshold (blocked by IL-5).
When near threshold, priced at ~50c (no structural edge).
No middle ground exists for 90-98c sniper zone. Same confirmed for KXETHD.

**RESEARCH METHODOLOGY NOTE (Session 80 feedback from Matthew):**
The polybot-autoresearch framework needs tighter criteria. Valid research must have:
1. Named mechanism (why does the market misprice this? who is the losing counterparty?)
2. Academic or economic basis (not just pattern-matching on historical data)
3. Quantifiable edge with clear paper-test protocol and minimum N
4. Different mechanism from existing sniper (not threshold/asset variants)
5. Willing to spend days validating — quality over quantity
Data-mining existing trades for time-of-day or minor asset patterns is NOT valid research.
