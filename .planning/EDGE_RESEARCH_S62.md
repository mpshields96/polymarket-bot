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
