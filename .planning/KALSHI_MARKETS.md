# KALSHI MARKETS — Complete Reference
# Last updated: Session 38 (2026-03-09) — FULL TAXONOMY + UI CONFIRMATION (screenshot)
# Source: Live API probe (Session 23, all 8,719 series) + full re-probe Session 36
#         + Matthew's kalshi.com Crypto tab screenshot (Session 38)
#         Confirmed via get_markets() calls against trading-api.kalshi.com
#
# PURPOSE: All future Claude sessions read this FIRST before any strategy work.
#          STANDING DIRECTIVE: New sessions must research undocumented categories.
#          See RESEARCH DIRECTIVES section at bottom — probe API, search Reddit/GitHub.
#          UPDATE THIS FILE whenever a new series is discovered or a strategy changes status.
# ══════════════════════════════════════════════════════════════

## ⚠️ CRITICAL UPDATE — Session 38 Screenshot Confirms More Market Types Than Documented

Matthew's kalshi.com Crypto tab screenshot (Session 38) shows:

**CRYPTO SUBCATEGORIES (UI-confirmed, tickers NOT fully probed):**
- 15 Minute (4) — KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M ✅ documented
- Hourly (8)    — price-level bets settling within the hour (KXBTCD structure) ✅ partially built
- Daily (10)    — price-level bets settling today/tomorrow (KXBTCD) ✅ paper
- Weekly (8)    — price-level bets settling this week (Friday 5pm) ⚠️ NOT BUILT — $455K volume!
- Monthly (11)  — price-level bets settling this month ⚠️ NOT BUILT — tickers unknown
- Annual (8)    — price-level bets settling end-of-year ⚠️ NOT BUILT — $1.4M volume!
- One Time (14) — event bets (e.g. "When will BTC hit $150k?") ⚠️ NOT BUILT — $14.8M volume!

**CRYPTO ASSETS (UI-confirmed):**
- BTC (16), ETH (10), SOL (10), XRP (6) — documented
- DOGE (6) — ⚠️ NEVER DOCUMENTED OR PROBED. Exists. Tickers unknown. Probe needed.
- Pre-Market (4) — unknown, probe needed
- Others (11) — unknown, probe needed

**VOLUME REALITY CHECK (from screenshot):**
| Market | Volume | Built? |
|--------|--------|--------|
| "When will Bitcoin hit $150k?" | $14,790,425 | ❌ NOT BUILT |
| "When will Bitcoin cross $100k?" | $3,384,242 | ❌ NOT BUILT |
| "Bitcoin price at end of 2026" (annual) | $1,394,912 | ❌ NOT BUILT |
| "Bitcoin price on Friday 5pm" (weekly) | $455,661 | ❌ NOT BUILT |
| KXBTC15M (15-min direction) | ~103,000/window | ✅ LIVE |
| "Bitcoin price today at 8pm" (daily/hourly) | $2,448 | ✅ PAPER |

**CONCLUSION: The One Time event markets ("When will BTC hit $X?") and Weekly/Annual price**
**level markets have FAR more volume than KXBTCD daily/hourly. We are ignoring the most**
**liquid crypto markets on Kalshi. The next chat must research and document these.**

**FULL KALSHI MARKET CATEGORIES (top nav — most NOT documented):**
- Crypto ← documented below (incomplete)
- Politics ← ⚠️ NOT DOCUMENTED — likely high volume election/policy markets
- Sports ← partially documented (Category 5-7 below)
- Culture ← ⚠️ NOT DOCUMENTED
- Climate ← ⚠️ NOT DOCUMENTED — possibly overlaps weather
- Economics ← partially documented (FOMC/CPI/unemployment) — likely more series
- Mentions ← ⚠️ NOT DOCUMENTED — possibly social/news volume metrics
- Companies ← ⚠️ NOT DOCUMENTED — earnings? stock price?
- Financials ← ⚠️ NOT DOCUMENTED — interest rates, inflation indices?
- Tech & Science ← ⚠️ NOT DOCUMENTED — AI milestones? space? biotech?

## ⚠️ KEY INSIGHT — "Hourly BTC bets" exist, just named differently

There is NO `KXBTC1H` series. Confirmed: probed all 8,719 Kalshi series in Session 23.
But KXBTCD (the daily price-level series) contains **24 separate hourly settlement windows
per day** — one closing each hour throughout the day. Example:

    KXBTCD-26MAR0921-T80000   → "Will BTC be above $80,000 at 9:21am?"
    KXBTCD-26MAR1021-T80000   → same strike, closes at 10:21am
    KXBTCD-26MAR1121-T80000   → closes at 11:21am
    ...~24 markets live at any given time

These are **price-level bets** (is BTC above/below $X at time T), NOT direction bets like 15-min.
Strike is parsed from ticker suffix: `KXBTCD-26MAR0921-T80000` → strike = $80,000.

**Volume comparison (Session 36 live probe):**
- KXBTC15M: ~103,000 contracts/window — the MOST LIQUID 15-min crypto market
- KXBTCD: ~5,000 total across all hourly/daily slots — 20x LESS liquid than 15-min direction
- Weekly price-level ("Bitcoin price on Friday"): ~$455K volume — much more than KXBTCD!
- One-Time events ("When will BTC hit $150k?"): ~$14.8M volume — 140x KXBTCD!
- Implication: 15-min direction is right for high-frequency. Weekly/annual/one-time events
  have enormous volume and could support a separate lower-frequency strategy.

═══════════════════════════════════════════════════════════════

## CATEGORY 1 — Crypto Price Direction (15-minute windows) ⚡ MOST LIQUID (HF)

"Will [asset] go UP or DOWN in the next 15 minutes?"
Each series has a YES side (up) and NO side (down). Markets open every 15 min, 24/7.
Volume confirmed via Session 36 live probe (contracts per current window):
  BTC: ~103,000 | ETH: ~9,400 | SOL: ~4,200 | XRP: ~5,900

| Series    | Asset | Status in bot                               | Notes |
|-----------|-------|---------------------------------------------|-------|
| KXBTC15M  | BTC   | ✅ MICRO-LIVE (btc_drift_v1, btc_lag paper) | Most liquid. HFTs closed lag. |
| KXETH15M  | ETH   | ✅ MICRO-LIVE (eth_drift_v1, eth_lag paper) | |
| KXSOL15M  | SOL   | ✅ MICRO-LIVE (sol_drift_v1, sol_lag paper) | min_drift_pct=0.15 (3x BTC) |
| KXXRP15M  | XRP   | 📋 NOT YET BUILT                            | Next expansion after drift validates |
| KXBNB15M  | BNB   | ❌ NO OPEN MARKETS (Session 36 probe)       | Inactive series |
| KXBCH15M  | BCH   | ❌ NO OPEN MARKETS (Session 36 probe)       | Inactive series |

**Strategy used:** BTCDriftStrategy (sigmoid probability model)
  - min_drift_pct: 0.05% for BTC/ETH, 0.15% for SOL (3x volatility)
  - min_edge_pct: 0.05 (5%) — restored Session 36 (was raised to 0.08 in Session 25, WRONG)
  - Price range guard: 35–65¢ (bets at extremes blocked — near expiry behavior)
  - calibration_max_usd=0.01 → always 1 contract/bet (~$0.35-0.65)

**Why btc_lag fires 0 signals/week:** Kalshi BTC markets now price in the BTC spot move within
the SAME 15-minute window as Binance.US ticks. HFTs (Jane Street, Susquehanna) closed the lag.
The drift model is different — it bets on momentum continuation, not price lag.

═══════════════════════════════════════════════════════════════

## CATEGORY 2A — Crypto Price Level (Hourly + Daily, KXBTCD structure)

"Will [asset] be ABOVE or BELOW $[strike] at [specific time today]?"
Each daily series generates ~24 hourly markets. Kalshi UI shows these as "Hourly (8)" + "Daily (10)".

| Series  | Asset | Volume (Session 36) | Status in bot       | Notes |
|---------|-------|---------------------|---------------------|-------|
| KXBTCD  | BTC   | ~5,000 total        | 📋 PAPER (btc_daily_v1) | 24 hourly windows/day |
| KXETHD  | ETH   | ~0 (new)            | 📋 PAPER (eth_daily_v1) | same structure |
| KXSOLD  | SOL   | ~0 (new)            | 📋 PAPER (sol_daily_v1) | same structure |
| KXXRPD  | XRP   | ~0 (confirmed ✅)   | NOT BUILT           | Exists but near-zero volume |
| KXDOGED | DOGE  | ⚠️ NOT PROBED       | NOT BUILT           | UI confirms DOGE (6) exists — probe needed |
| KXBNBD  | BNB   | ❌ No open markets  | NOT BUILT           | Series inactive |
| KXBCHD  | BCH   | ❌ No open markets  | NOT BUILT           | Series inactive |

**Strategy used:** CryptoDailyStrategy (Session 33)
  - _find_atm_market(): picks contract with mid-price closest to 50¢ in 30min–6hr window
  - Model: 70% drift momentum + 30% lognormal price model
  - Paper-only until expansion gate opens

═══════════════════════════════════════════════════════════════

## CATEGORY 2B — Crypto Price Level (Weekly) ⚠️ UNDOCUMENTED — $455K volume

"Will [asset] be ABOVE or BELOW $[strike] on [day of week] at [time]?"
UI shows "Weekly (8)" under Crypto. Example: "Bitcoin price on Friday at 5pm EDT?"

| Series   | Asset | Volume (UI screenshot) | Status in bot | Notes |
|----------|-------|------------------------|---------------|-------|
| KXBTCW?  | BTC   | ~$455,661 vol, 50 mkts | ❌ NOT BUILT  | ⚠️ TICKER NOT CONFIRMED — probe needed |
| KXETHW?  | ETH   | unknown                | ❌ NOT BUILT  | |
| KXSOLW?  | SOL   | unknown                | ❌ NOT BUILT  | |
| KXXRPW?  | XRP   | unknown                | ❌ NOT BUILT  | |
| KXDOGEW? | DOGE  | unknown                | ❌ NOT BUILT  | |

**Key facts (from screenshot):**
- "Bitcoin price on Friday at 5pm EDT?" = weekly settlement at end-of-week
- 50 markets at different strikes = same multi-strike structure as KXBTCD
- $455K volume = ~90x more liquid than KXBTCD daily slots
- Tickers UNKNOWN — "KXBTCW" is a guess. Probe via `client.get_markets(series_ticker="KXBTCW")`

**Research needed:** What is the actual series ticker? Check kalshi.com URL when clicking market.

═══════════════════════════════════════════════════════════════

## CATEGORY 2C — Crypto Price Level (Monthly) ⚠️ UNDOCUMENTED

"Will [asset] be ABOVE or BELOW $[strike] at end of [month]?"
UI shows "Monthly (11)" under Crypto.

| Series   | Asset | Volume | Status in bot | Notes |
|----------|-------|--------|---------------|-------|
| KXBTCM?  | BTC   | unknown | ❌ NOT BUILT  | ⚠️ TICKER NOT CONFIRMED |
| KXETHM?  | ETH   | unknown | ❌ NOT BUILT  | |
| KXSOLM?  | SOL   | unknown | ❌ NOT BUILT  | |

**Research needed:** Probe `client.get_markets(series_ticker="KXBTCM")` to confirm.

═══════════════════════════════════════════════════════════════

## CATEGORY 2D — Crypto Price Level (Annual) ⚠️ UNDOCUMENTED — $1.4M volume

"Will [asset] be in price range $[X] to $[Y] at end of year?"
UI shows "Annual (8)" under Crypto. Example: "Bitcoin price at the end of 2026"

| Market example           | Volume      | Markets | Notes |
|--------------------------|-------------|---------|-------|
| BTC price end of 2026    | $1,394,912  | 28      | Range betting: 45-49,999, 50-54,999, etc. |

| Series   | Asset | Volume | Status | Notes |
|----------|-------|--------|--------|-------|
| KXBTCY?  | BTC   | ~$1.4M | ❌ NOT BUILT | ⚠️ TICKER NOT CONFIRMED — range bets, not binary |
| KXETHY?  | ETH   | unknown | ❌ NOT BUILT | |

**Key difference from other price-level:** Annual bets have RANGE brackets (e.g. "45-49,999")
not binary above/below. This is a different market structure — multiple outcome market.
Signal: lognormal price model with calibrated volatility. Research needed.
**Research needed:** Probe API, search Reddit /r/kalshi for strategies.

═══════════════════════════════════════════════════════════════

## CATEGORY 2E — Crypto One-Time Events ⚠️ UNDOCUMENTED — UP TO $14.8M VOLUME

"When will [asset] reach $[price] for the first time?"
UI shows "One Time (14)" under Crypto. HIGHEST volume crypto markets on Kalshi.

| Market example                  | Volume       | Markets | Notes |
|---------------------------------|--------------|---------|-------|
| "When will Bitcoin hit $150k?"  | $14,790,425  | 3       | Multiple date brackets |
| "When will Bitcoin cross $100k?"| $3,384,242   | 6       | Multiple date brackets |

| Series    | Asset | Volume | Status | Notes |
|-----------|-------|--------|--------|-------|
| unknown   | BTC   | $14.8M | ❌ NOT BUILT | ⚠️ TICKER COMPLETELY UNKNOWN |
| unknown   | ETH   | unknown | ❌ NOT BUILT | |

**Key structure:** Not binary binary yes/no. Example outcomes:
- "Before January 2027" (2.4x) at 40%
- "Before October 2026" (3.4x) at 27%
This is a multi-outcome market with date brackets.

**Signal hypothesis:** BTC price trajectory model + realized volatility →
estimate probability of hitting target before each date. Research existing approaches.

**THIS IS THE HIGHEST-VOLUME CRYPTO MARKET ON KALSHI.**
$14.8M on a single "When will BTC hit $150k?" market vs $103K per KXBTC15M window.
Settle only once → capital tied up longer, but edge could be substantial if model is good.

**Research needed (CRITICAL):**
1. Find actual series tickers via Kalshi API probe
2. Search reddit.com/r/kalshi for "bitcoin $150k" strategy discussions
3. Search GitHub for Kalshi one-time event prediction strategies
4. Understand settlement rules — when exactly does it settle after hitting price?

═══════════════════════════════════════════════════════════════

## CATEGORY 3 — Macro / Economic Events

| Series         | Event                       | Frequency     | Volume (probe) | Status in bot |
|----------------|-----------------------------|---------------|----------------|---------------|
| KXFEDDECISION  | Fed funds rate at FOMC      | ~8x/year      | ~4,700         | 📋 PAPER (fomc_rate_v1) |
| KXUNRATE       | US unemployment (BLS)       | Monthly       | Opens 2d pre-BLS | 📋 PAPER (unemployment_rate_v1) |
| KXCPI          | CPI inflation print         | Monthly       | ~1,400 ✅ confirmed | NOT BUILT (low freq) |
| KXJOLTS        | Job openings (JOLTS)        | Monthly       | not probed     | NOT BUILT |
| KXGDP          | GDP growth                  | Quarterly     | not probed     | NOT BUILT |

**Notes:**
- KXUNRATE markets open ~2 days before BLS release. No open markets outside that window = expected.
- KXFEDDECISION: uses FRED yield curve spread (DGS2-DFF) as signal.
- KXCPI: confirmed ✅ exists (Session 36 probe). ~1,400 volume when open. Not built — low freq.
- CPI/JOLTS/GDP: not built — low frequency + less reliable signal hypothesis than FOMC.

═══════════════════════════════════════════════════════════════

## CATEGORY 4 — Weather

| Series  | Market                              | Frequency  | Status in bot |
|---------|-------------------------------------|------------|---------------|
| HIGHNY  | High temp NYC (Central Park) for day | Weekdays only | 📋 PAPER (weather_forecast_v1) |
| HIGHCHI | Chicago high temp                    | ?          | ❌ No open markets (Session 36 probe) |
| HIGHLA  | Los Angeles high temp                | ?          | ❌ No open markets (Session 36 probe) |

**Notes:**
- Markets only open on weekdays. "No open HIGHNY markets" on weekends = expected, not a bug.
- Signal: Open-Meteo GFS + NWS NDFD ensemble (EnsembleWeatherFeed), adaptive std_dev.
- Paper-only. Low priority for live promotion (seasonal edge unclear).

═══════════════════════════════════════════════════════════════

## CATEGORY 5 — Sports: Game Winners (Settle same day)

| Series       | Sport      | Volume (probe) | Status in bot |
|--------------|------------|----------------|---------------|
| KXNBAGAME    | NBA        | ~5,200         | 🔧 SKELETON (sports_game.py — not wired) |
| KXNHLGAME    | NHL        | ~3,100         | 🔧 SKELETON (sports_game.py — not wired) |
| KXNCAAMBGAME | NCAA Mens  | ~4 (very low)  | NOT BUILT |
| KXMLBGAME    | MLB        | ~250 (off-season) | NOT BUILT |

**Notes:**
- These are **game-by-game winner** markets. Settle same day.
- Signal: bookmaker moneyline consensus (same SDATA feed as sports_futures_v1).
- Skeleton in src/strategies/sports_game.py — parses KXNBAGAME-26FEB28HOUMIA-HOU format.
- NOT wired to main.py. NOT paper-trading yet.
- **Gate:** Build only after sports_futures_v1 shows real edge in paper trading.
- KXMLBGAME: confirmed exists. Low volume now (March = spring training). Opens higher in season.

═══════════════════════════════════════════════════════════════

## CATEGORY 6 — Sports: Player Props (NEW — Session 36 discovery)

"Will [player] score X+ points / get X+ assists / etc. in today's game?"
These are individual player performance markets. Settle after each game.

| Series    | Stat        | Volume (probe) | Notes |
|-----------|-------------|----------------|-------|
| KXNBAPTS  | NBA points  | ~0 (new)       | e.g. "OG Anunoby: 25+ points" |
| KXNBAAST  | NBA assists | ~0 (new)       | e.g. "Josh Hart: 8+ assists" |
| KXNBAREB  | NBA rebounds| ~0 (new)       | e.g. "Josh Hart: 12+ rebounds" |
| KXNBA3PT  | NBA 3-ptrs  | ~0 (new)       | e.g. "Josh Hart: 5+ threes" |
| KXNBA2D   | Double-double| ~0 (new)      | e.g. "OG Anunoby: Double Double" |
| KXNBA3D   | Triple-double| ~13,600       | e.g. "Josh Hart: Triple Double" — higher volume |
| KXNHLPTS  | NHL points  | ~680           | e.g. player points total |
| KXNHLAST  | NHL assists | ~170           | e.g. player assists |

**Current status:** NOT BUILT in bot.

**Why NOT building now:**
1. Most props have near-zero volume — extremely wide spreads, can't get filled at fair prices
2. Harder to predict than game direction (individual performance more variable than team outcomes)
3. Expansion gate in effect: no new strategies until drift model validates (30 bets + Brier < 0.30)
4. Sharp bookmaker data (SDATA feed) has player props — the signal EXISTS, just gated

**Future potential (post-validation):**
- Same SDATA feed already has player prop lines (spreads, totals, player stats)
- Strategy pattern: compare Kalshi implied prob vs bookmaker consensus line
- KXNBA3D has ~13,600 volume = most viable player prop market right now
- Would use same SDATA credits as sports_futures_v1 (shared 500/month cap)
- **Log in .planning/todos.md when ready to build — do NOT build until drift validates**

═══════════════════════════════════════════════════════════════

## CATEGORY 7 — Sports: Season Champions (Long-duration futures)

| Series | Sport | Volume (Session 36) | Duration      | Status in bot |
|--------|-------|---------------------|---------------|---------------|
| KXNBA  | NBA   | ~11.5M (very liquid!) | Season (~months) | NOT BUILT |
| KXMLB  | MLB   | ~1.4M               | Season (~months) | NOT BUILT |

**Notes:**
- These are season-winner markets (e.g. "Will the Lakers win the NBA championship?")
- Volume is HIGH (KXNBA = 11.5M) but these take months to settle.
- Capital tied up for months = bad for a high-frequency bot.
- NOT useful for this bot. Do not build. (Updated: confirmed volumes in Session 36 probe)

═══════════════════════════════════════════════════════════════

## CATEGORY 8 — Entertainment / Pop Culture

| Series       | Event           | Volume | Status in bot |
|--------------|-----------------|--------|---------------|
| KXMVEOSCARS  | Oscars winners  | ~48 markets open | NOT BUILT |

**Examples seen:** Best Actor/Actress nominees, Best Picture nominees
**Notes:**
- Confirmed ✅ exists on Kalshi (Session 36 probe)
- No reliable signal edge identified. Very low volume. Do not build.

═══════════════════════════════════════════════════════════════

## CATEGORY 9 — Parlay / Multi-Leg Markets

| Series                        | Description                | Volume   | Notes |
|-------------------------------|----------------------------|----------|-------|
| KXMVECROSSCATEGORY            | Same-game parlays (SGPs)   | 8,914 markets! | Complex correlated bets |
| KXMVENBASINGLEGAME            | NBA single-game parlays    | 4 markets | |
| KXMVESPORTSMULTIGAMEEXTENDED  | Multi-game parlays         | 903 markets | |

**Notes:**
- These are combination bets — multiple outcomes bundled into one market
- Extremely complex pricing — correlation between legs is hard to model
- 8,914 KXMVECROSSCATEGORY markets = Kalshi's largest category by count
- NOT useful for this bot. Correlation risk + pricing complexity = no edge. Do not build.

═══════════════════════════════════════════════════════════════

## CATEGORY 10 — Politics / Geopolitical Events (Polymarket.COM only)

These appear in predicting.top whale signal logs but are on **polymarket.COM only**, not Kalshi.
Our account is polymarket.US (sports-only). Not currently targetable on Kalshi.

**Status:** Not buildable on our accounts. Documented for context only.

═══════════════════════════════════════════════════════════════

## SERIES CONFIRMED DON'T EXIST (on Kalshi)

| Series searched | Result |
|-----------------|--------|
| KXBTC1H         | ❌ Does NOT exist — confirmed Session 23 (all 8,719 series probed) |
| KXETH1H         | ❌ Does NOT exist |
| KXBTC5M         | ❌ Does NOT exist |
| KXBNB15M        | ❌ No open markets (Session 36) — series may exist but inactive |
| KXBCH15M        | ❌ No open markets (Session 36) — inactive |
| KXBNBD          | ❌ No open markets (Session 36) |
| KXBCHD          | ❌ No open markets (Session 36) |
| KXNHLGOALS      | ❌ No open markets (Session 36) |
| KXNHLSAV        | ❌ No open markets (Session 36) |
| KXNHLSOG        | ❌ No open markets (Session 36) |

The "hourly BTC bet" IS KXBTCD with 24 hourly settlement slots. Not a separate series.

═══════════════════════════════════════════════════════════════

## STRATEGY → SERIES MAPPING (authoritative)

| Strategy file              | Series used              | Live? |
|----------------------------|--------------------------|-------|
| btc_drift.py (btc_drift)   | KXBTC15M                 | ✅ MICRO-LIVE |
| btc_drift.py (eth_drift)   | KXETH15M                 | ✅ MICRO-LIVE |
| btc_drift.py (sol_drift)   | KXSOL15M                 | ✅ MICRO-LIVE |
| btc_lag.py (btc_lag)       | KXBTC15M                 | 📋 Paper (0 signals/week) |
| btc_lag.py (eth_lag)       | KXETH15M                 | 📋 Paper |
| btc_lag.py (sol_lag)       | KXSOL15M                 | 📋 Paper |
| orderbook_imbalance.py     | KXBTC15M+KXETH15M        | 📋 Paper |
| crypto_daily.py (btc)      | KXBTCD                   | 📋 Paper |
| crypto_daily.py (eth)      | KXETHD                   | 📋 Paper |
| crypto_daily.py (sol)      | KXSOLD                   | 📋 Paper |
| weather_forecast.py        | HIGHNY                   | 📋 Paper (weekdays only) |
| fomc_rate.py               | KXFEDDECISION            | 📋 Paper (~8x/year) |
| unemployment_rate.py       | KXUNRATE                 | 📋 Paper (2d window/month) |
| sports_game.py             | KXNBAGAME+KXNHLGAME      | 🔧 Skeleton (not wired) |
| sports_futures_v1.py       | Polymarket.US            | 📋 Paper |
| copy_trader_v1.py          | Polymarket.US            | 📋 Paper (platform mismatch) |

## EXPANSION ROADMAP — Order of operations

After expansion gate opens (2-3 weeks live data + no kill switch events):

**Tier 1 — Quick wins (same code pattern as existing strategies):**
1. **KXXRP15M** — XRP 15-min direction (same code as sol_drift, ~15 min to add)
2. **KXBTCD hourly live** — btc_daily_v1 already paper, promote after graduation met
3. **Weekly price-level** — if KXBTCW ticker confirmed, ~same as KXBTCD but weekly settlement

**Tier 2 — High-volume, new strategy needed:**
4. **One-Time events** ("When will BTC hit $150k?") — $14.8M volume, completely new strategy type
   Signal: price trajectory model + realized vol → probability of hitting target before date
   Research before building: search Reddit, GitHub, probe API for tickers + settlement rules
5. **Annual price-level** ("Bitcoin price at end of 2026") — $1.4M volume, range-betting structure
   Different from binary above/below — multiple brackets, different Kelly sizing

**Tier 3 — Sports / other (gate: sports_futures shows edge first):**
6. **KXNBAGAME / KXNHLGAME** — game winners (skeleton exists)
7. **KXNBA3D** — triple-double props (~13,600 volume, best player prop)
8. **KXCPI** — CPI monthly (confirmed exists, reuse FOMC pattern)
9. **KXMLBGAME** — MLB game winners (April+ season volume)

**Do NOT build:** KXMVE* parlays, KXMVEOSCARS, KXNBA/KXMLB season futures, KXBNB/KXBCH

═══════════════════════════════════════════════════════════════

## ⚠️ RESEARCH DIRECTIVES — NEW SESSIONS MUST INVESTIGATE

**STANDING INSTRUCTION: Do not skip this section. Document findings in this file.**

The following are UNDOCUMENTED market categories on Kalshi. Each new session that has
budget for research work should investigate and update this file with findings.

### Research Task 1 — CRYPTO TICKERS (probe API)
```python
# Run this to discover actual series tickers for weekly/monthly/annual/one-time:
from src.auth.kalshi_auth import KalshiAuth
from src.platforms.kalshi import KalshiClient
# Try: KXBTCW, KXBTCM, KXBTCY, KXBTCA, KXDOGE15M, KXDOGED
# Check: client.get_markets(series_ticker="KXBTCW", limit=5)
```
Find tickers → update Categories 2B/2C/2D/2E above.

### Research Task 2 — UNDOCUMENTED KALSHI CATEGORIES
Search `reddit.com/r/kalshi` for:
- "weekly crypto" strategy discussions
- "bitcoin $150k" or "one-time" event betting strategies
- "monthly" price prediction approaches
- strategies for Politics, Economics, Companies, Financials, Tech markets

Search GitHub for:
- `kalshi python bot` → look for strategies beyond 15-min direction
- `kalshi one-time event` or `kalshi price prediction annual`
- Any open-source approaches to Kalshi weekly/monthly/annual bets

### Research Task 3 — FULL CATEGORY MAP
Visit kalshi.com top nav and document ALL categories:
- Politics: what types? Volume? Any statistical edge possible?
- Culture: what markets exist? Volume?
- Climate: distinct from weather/HIGHNY?
- Economics: beyond CPI/FOMC/unemployment?
- Mentions: social media volume metrics? How are these structured?
- Companies: earnings-based? Stock price prediction?
- Financials: S&P 500? Bond yields? Forex?
- Tech & Science: AI releases? space missions? FDA approvals?

**Update this file with findings before any strategy work.**
**Do NOT build a strategy for any category not yet probed and documented here.**

═══════════════════════════════════════════════════════════════
