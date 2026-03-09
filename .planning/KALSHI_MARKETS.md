# KALSHI MARKETS — Complete Reference
# Last updated: Session 39 (2026-03-09) — FULL TAXONOMY + EVENTS ENDPOINT DISCOVERY
# Source: Live API probe (Session 23, all 8,719 series) + full re-probe Session 36
#         + Matthew's kalshi.com Crypto tab screenshot (Session 38)
#         + Events endpoint paginated search (Session 39) — 3,000 events scanned
#         Confirmed via get_markets() + GET /events against api.elections.kalshi.com
#
# PURPOSE: All future Claude sessions read this FIRST before any strategy work.
#          STANDING DIRECTIVE: New sessions must research undocumented categories.
#          See RESEARCH DIRECTIVES section at bottom — probe API, search Reddit/GitHub.
#          UPDATE THIS FILE whenever a new series is discovered or a strategy changes status.
#
# SESSION 39 KEY DISCOVERIES:
#   - CONFIRMED: KXBTCMAX100 ($2.7M), KXBTCMAXY ($2.2M), KXBTC2026200 ($3.4M)
#   - CONFIRMED: KXBTCMAXMON/KXBTCMINMON (monthly max/min, trimmed mean, ~$550k/mo)
#   - CONFIRMED: KXBTCY (annual year-end, 28 mkts, $1.4M) is BINARY not range-bracket
#   - CONFIRMED: KXBTCW/KXETHW/KXSOLW exist — 0 open on Sunday (expected, weekly timing)
#   - EVENTS ENDPOINT: GET /events?status=open scans all Kalshi categories
#   - ALL KALSHI CATEGORIES CONFIRMED: Crypto, Politics, Financials, Companies,
#     Mentions, Climate, Economics, Science, Sports, Entertainment, Elections, World
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

**SESSION 39 UPDATE: All major tickers now confirmed. Key corrections:**
- Annual markets (KXBTCY) are BINARY (B/T prefix), NOT range brackets — confirmed API probe
- Monthly markets (KXBTCMAXMON) use TRIMMED MEAN settlement — different from spot price
- One-time events use SERIES TICKER = KXBTCMAX100 (not "KXBTC150K" which is stale)
- Weekly tickers (KXBTCW etc) EXIST but open Mon only — probe confirmed on Sunday = 0 open
- Events endpoint GET /events?status=open is the correct way to discover new market types
- KXDOGED confirmed active but ZERO VOLUME — do not build

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
| KXDOGED | DOGE  | vol=0 all markets ❌| NOT BUILT           | Session 39: EXISTS but zero liquidity — skip |
| KXBNBD  | BNB   | ❌ No open markets  | NOT BUILT           | Series inactive |
| KXBCHD  | BCH   | ❌ No open markets  | NOT BUILT           | Series inactive |

**Strategy used:** CryptoDailyStrategy (Session 33)
  - _find_atm_market(): picks contract with mid-price closest to 50¢ in 30min–6hr window
  - Model: 70% drift momentum + 30% lognormal price model
  - Paper-only until expansion gate opens

═══════════════════════════════════════════════════════════════

## CATEGORY 2B — Crypto Price Level (Weekly) ✅ TICKER CONFIRMED — 0 OPEN MARKETS NOW

"Will [asset] be ABOVE or BELOW $[strike] on [day of week] at [time]?"
UI shows "Weekly (8)" under Crypto. Example: "Bitcoin price on Friday at 5pm EDT?"

| Series  | Asset | Vol (UI screenshot) | Status in bot | Notes |
|---------|-------|---------------------|---------------|-------|
| KXBTCW  | BTC   | ~$455,661 vol       | ❌ NOT BUILT  | ✅ ticker confirmed, 0 open NOW (Session 39 probe) |
| KXETHW  | ETH   | unknown             | ❌ NOT BUILT  | ✅ ticker confirmed, 0 open now |
| KXSOLW  | SOL   | unknown             | ❌ NOT BUILT  | ✅ ticker confirmed, 0 open now |
| KXBTCWK | BTC   | -                   | ❌ NOT BUILT  | ✅ confirmed exists, 0 open |
| KXBTCFRI| BTC   | -                   | ❌ NOT BUILT  | ✅ confirmed exists, 0 open |

**Key findings (Session 39 API probe):**
- KXBTCW, KXETHW, KXSOLW tickers ARE REAL — series confirmed to exist via API
- All return "0 open markets" currently — weekly markets may only open Mon–Fri
- Session 39 probed on a Sunday → 0 open is EXPECTED (opens Monday, closes Friday 5pm EDT)
- Same multi-strike structure as KXBTCD (multiple price levels = B/T suffix)
- $455K volume per week = ~90x more liquid than KXBTCD daily slots
- Strategy potential: same as KXBTCD but with weekly settlement. Research after expansion gate.

**Next step:** Probe on a weekday to see open markets. Should work same as KXBTCD structure.

═══════════════════════════════════════════════════════════════

## CATEGORY 2C — Crypto Monthly Max/Min ✅ CONFIRMED ACTIVE — $547K+ volume

"How high/low will [asset] get during [month]?" — Uses TRIMMED MEAN, not spot price!
UI shows "Monthly (11)" under Crypto. Settlement: trimmed mean price by month-end.

⚠️ CRITICAL: These are NOT end-of-month spot price bets. Settlement = TRIMMED MEAN of BTC
price throughout the month (removes outliers). Harder to model than spot.

| Series       | Asset | Vol (Session 39)  | Status  | Description |
|--------------|-------|-------------------|---------|-------------|
| KXBTCMAXMON  | BTC   | $546,490 (6 mkts) | ❌ NOT BUILT | "How high will BTC get in March?" |
| KXBTCMINMON  | BTC   | $438,856 (8 mkts) | ❌ NOT BUILT | "How low will BTC get in March?" |
| KXETHMAXMON  | ETH   | $95,930 (7 mkts)  | ❌ NOT BUILT | "How high will ETH get in March?" |
| KXSOLMAXMON  | SOL   | $34,769 (7 mkts)  | ❌ NOT BUILT | "How high will SOL get in March?" |
| KXDOGEMAXMON | DOGE  | $8,202 (7 mkts)   | ❌ NOT BUILT | "How high will DOGE get in March?" |
| KXDOGEMINMON | DOGE  | $1,391 (8 mkts)   | ❌ NOT BUILT | "How low will DOGE get in March?" |
| KXBTCM       | BTC   | 0 open now        | ❌ NOT BUILT | Alt monthly ticker — confirmed exists |

**Market structure example (KXBTCMAXMON):**
- KXBTCMAXMON-BTC-26MAR31 with suffix 7500000 → "Will BTC trimmed mean be above $75,000 by 11:59pm March 31?"
- Strikes: $75k (45¢), $77.5k (30¢), $80k (19¢)
- Settlement: trimmed mean = removes top/bottom outlier prices across month

**Signal challenge:** Trimmed mean ≠ spot price. Would need to model rolling monthly average
distribution using realized vol + current price. Medium-complexity signal. Post-gate research.

**Recommended research order:** KXBTCMAXMON → KXBTCMINMON (highest vol, BTC only)

═══════════════════════════════════════════════════════════════

## CATEGORY 2D — Crypto Annual Year-End Price ✅ CONFIRMED ACTIVE — $1.4M+ volume

"Will [asset] be ABOVE or BELOW $[strike] on Jan 1, 2027?" — Binary YES/NO, not range!

⚠️ CORRECTION from Session 38: These are BINARY above/below bets, NOT range brackets.
Ticker structure: KXBTCY-27JAN0100-B82500 = "Will BTC be BELOW $82,500 on Jan 1, 2027?"
                  KXBTCY-27JAN0100-T20000 = "Will BTC be ABOVE $20,000 on Jan 1, 2027?"

| Series  | Asset | Vol (Session 39)  | Markets | Status  | Description |
|---------|-------|-------------------|---------|---------|-------------|
| KXBTCY  | BTC   | ~$1.4M+  (28 mkts)| 28      | ❌ NOT BUILT | BTC price on Jan 1, 2027 |
| KXETHY  | ETH   | ~$350K+ (18 mkts) | 18      | ❌ NOT BUILT | ETH price on Jan 1, 2027 |
| KXSOLD26| SOL   | $116,979 (8 mkts) | 8       | ❌ NOT BUILT | SOL price on Jan 1, 2027 |

**Most liquid KXBTCY markets (Session 39 live probe):**
| Ticker suffix | YES price | Volume   | Description |
|---------------|-----------|----------|-------------|
| B42500        | 5¢        | 151,117  | Will BTC be below $42,500 on Jan 1, 2027? |
| B52500        | 7¢        | 122,502  | Will BTC be below $52,500 on Jan 1, 2027? |
| B47500        | 7¢        | 118,948  | Will BTC be below $47,500 on Jan 1, 2027? |
| B67500        | 7¢        | 107,617  | Will BTC be below $67,500 on Jan 1, 2027? |
| B82500        | 4¢        | 105,287  | Will BTC be below $82,500 on Jan 1, 2027? |
| T20000.00     | 4¢        | 45,750   | Will BTC be above $20,000 on Jan 1, 2027? |
| T149999.99    | 5¢        | 75,086   | Will BTC be above $149,999 on Jan 1, 2027? |

**Signal approach:** Lognormal price model, Jan 1, 2027 settlement. BTC is ~$80k now.
B82500 at 4¢ = market says only 4% chance BTC ends below $82,500 (very bullish consensus).
These markets have 9+ month settlement — capital tied up. But edge could be very high.

**Action:** Post-expansion-gate research task. Requires lognormal drift model + vol calibration.

═══════════════════════════════════════════════════════════════

## CATEGORY 2E — Crypto One-Time Events ✅ TICKERS CONFIRMED — $2.7M–$14.8M VOLUME

"When will Bitcoin cross $X?" / "Will Bitcoin be above $X by [date]?"
UI shows "One Time (14)" under Crypto. HIGHEST volume crypto markets on Kalshi.

**Session 39 findings:** Found via events endpoint `/events?status=open`. The series tickers
that returned "exists, 0 open" via get_markets() ARE these markets — they use the event_ticker
approach, not simple series_ticker. Multiple confirmed active series:

| Series       | Event ticker                   | Volume (Session 39) | Description |
|--------------|--------------------------------|---------------------|-------------|
| KXBTCMAX150  | KXBTCMAX150-25                 | $10,834,502 (3 mkts)| When will Bitcoin hit $150k? ← HIGHEST VOLUME |
| KXBTCMAX100  | KXBTCMAX100-26                 | $2,704,740 (6 mkts) | When will BTC cross $100k again? |
| KXBTCMAXY    | KXBTCMAXY-26DEC31              | $2,202,638 (7 mkts) | How high will BTC get in 2026? |
| KXBTCMINY    | KXBTCMINY-27JAN01              | $1,078,887 (5 mkts) | How low will BTC get in 2026? |
| KXBTC2026200 | KXBTC2026200-27JAN01           | $3,425,025 (1 mkt)  | Will BTC be above $200k by 2027? |
| KXBTC2026250 | KXBTC2026250-27JAN01           | $453,891 (1 mkt)    | Will BTC be above $250k by 2027? |
| KXETHMAXY    | KXETHMAXY-27JAN01              | $1,257,719 (8 mkts) | How high will ETH get in 2026? |
| KXETHMINY    | KXETHMINY-27JAN01              | $283,017 (5 mkts)   | How low will ETH get in 2026? |
| KXSOLMAXY    | KXSOLMAXY-27JAN01              | $205,273 (8 mkts)   | How high will SOL get in 2026? |
| KXBTCVSGOLD  | KXBTCVSGOLD-26                 | $113,035 (1 mkt)    | Will BTC outperform gold in 2026? |
| KXBTCRESERVE | KXBTCRESERVE-27                | $85,447 (1 mkt)     | Will Trump create BTC reserve? |

**Most liquid single market: KXBTC2026200 — $3.4M on "Will BTC be above $200k by 2027?" at 8¢**

**KXBTCMAX100 structure (When will BTC cross $100k again?):**
- Ticker: KXBTCMAX100 series, markets by DATE BRACKET (e.g. MAR, APR, JUNE...)
- KXBTCMAX100 MAR → "Will BTC be above $100k by April 1?" YES=1¢ vol=999k
- KXBTCMAX100 APR → "Will BTC be above $100k by May 1?"  YES=6¢ vol=681k
- KXBTCMAX100 JUNE → "Will BTC be above $100k by July 1?" YES=19¢ vol=513k
- BTC currently ~$80k → 1¢ on April deadline is essentially "BTC must cross $100k in 3 weeks"

**KXBTCMAXY structure (How high will BTC get in 2026?):**
- 7 markets with price thresholds — binary: "Will BTC REACH ABOVE $X by Dec 31?"
- $99,999.99 at 36¢ (36% chance BTC breaks $100k this year), vol=597k
- $129,999.99 at 16¢, vol=261k | $199,999.99 at 8¢, vol=521k

**Signal approach for KXBTCMAX100 (highest priority for future research):**
- BTC path: geometric Brownian motion + realized vol → P(BTC > $100k before date T)
- Uses: option pricing models (first-passage-time probability for BM hitting a barrier)
- Formula: P(S_T > K) = Φ((ln(S0/K) + μT) / (σ√T)) for simplest version
- Vol calibration: use 30-day realized vol from Binance.US historical klines
- This is standard barrier option pricing — NOT a new signal, established math

**KXBTCMAX150 — "When will Bitcoin hit $150k?" — $10.8M total volume (Session 39 confirmed):**
- 3 markets, different deadline dates:
  - KXBTCMAX150-25-26MAR31 → YES=0¢ vol=3.7M — "Will BTC hit $150k before April 1?" (3 weeks → impossible)
  - KXBTCMAX150-25-26APR30 → YES=2¢ vol=2.7M — "Before May 1?" (7 weeks, 2% implied)
  - KXBTCMAX150-25-26MAY31 → YES=4¢ vol=4.4M — "Before June 1?" (3 months, 4% implied)
- Market type: ONE-TOUCH option ("Did BTC touch $149,999.99 at ANY point before deadline?")
- Settlement: if BTC spot price ≥ $150k at any moment before close_time → YES resolves
- Signal: barrier option pricing (first-passage-time probability for GBM)
  P(S_t ≥ K before T) = function of: current price, target, time, vol (σ), drift (μ)
  Known formula from options theory — NOT guesswork
- BTC currently ~$80k → $150k is +87.5% from here → very low probability → these 4-cent
  prices may actually be MISPRICED if vol is high. Worth investigating.

**KXBTCMAX100 structure (6 markets, $2.7M total):**
- Markets by BTC-must-reach-by-MONTH deadline:
  - MAR (by April 1): 1¢ vol=999k | APR (by May 1): 6¢ vol=681k
  - MAY: 14¢ vol=362k | JUNE: 19¢ vol=513k | SEP: 26¢ vol=62k | DEC: 38¢ vol=87k
- Close time note: some markets show close=2027-01-01 — may be SETTLEMENT date, not deadline
- Same one-touch structure as KXBTCMAX150 but for $100k target

**What happened to the $14.8M market from Session 38 screenshot:**
That WAS KXBTCMAX150 — confirmed! $10.8M open volume. NOT settled (BTC hasn't hit $150k).
The screenshot showed a higher number, likely volume displayed differently (may include settled).

**KXBTCATH — "When will Bitcoin hit a new all-time high?" (Session 39 discovery):**
- URL: kalshi.com/markets/kxbtcath/btc-ath
- Confirmed via website: series EXISTS and is titled "When will Bitcoin hit a new ATH?"
- API probe (Session 39, Sunday Mar 9): 0 open markets, 0 total markets
- Hypothesis: Market resolved YES when BTC hit $109k in Jan 2026, then no new series opened
- OR: Markets may only open when BTC is near ATH (proximity trigger)
- Action: Monitor — probe monthly to see if new markets open. Do NOT build until confirmed active.

**KXBTCMAX100 current pricing (Session 39 probe, BTC ~$84k, Sunday Mar 9):**
- DEC 2026 contract: 38¢ (38% chance BTC crosses $100k by December 2026)
- SEP 2026: 27¢ | MAY 2026: 14¢ | APR 2026: 6¢ | MAR 2026: 1¢ (3 weeks, near-impossible)
- Total volume: $2,704,832 across 6 markets
- Insight: December at 38¢ with BTC at $84k is a reasonable market. +$16k = +19% needed.

**KXBTCMAXY current pricing (Session 39 probe — "How high will BTC get in 2026?"):**
- $99,999: 36¢ (36% chance BTC hits $100k before Dec 31, 2026) vol=597k
- $109,999: 26¢ vol=sample | $149,999: 12¢ vol=sample | $199,999: 8¢ (8% chance 2.5x)
- Total: 7 markets, $2.2M vol

**KXBTCMINY current pricing (Session 39 probe — "How low will BTC get in 2026?"):**
- $40,000: 35¢ (35% chance BTC dips below $40k in 2026) | $45,000: 46¢ | $50,000: 57¢
- Total: 5 markets, $1.1M vol. Insight: market says 57% chance BTC dips below $50k this year.

**Signal approach (TIER 2 post-gate):**
Barrier option / first-passage-time model using GBM. Standard formula from options theory:
P(max S_t ≥ K, 0 ≤ t ≤ T) = Φ((-ln(K/S) + (μ-σ²/2)T)/(σ√T)) + (S/K)^(2μ/σ²-1) × Φ((-ln(K/S) - (μ+σ²/2)T)/(σ√T))
Where: S=current price, K=target, T=time to deadline, σ=realized vol, μ=drift
Calibration: Binance.US 30-day klines (already used in backtest.py)

**Expansion roadmap:** KXBTCMAX100 is Tier 2 priority (post-gate). Requires:
1. Barrier option pricing model (first-passage-time)
2. Vol calibration from Binance.US 30-day klines (scripts/backtest.py pattern)
3. Paper trading + Brier validation before live

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

## EXPANSION ROADMAP — Order of operations (Updated Session 39)

After expansion gate opens (2-3 weeks live data + no kill switch events):

**Tier 1 — Quick wins (same code pattern as existing strategies):**
1. **KXXRP15M** — XRP 15-min direction (same code as sol_drift, ~15 min to add)
2. **KXBTCD hourly live** — btc_daily_v1 already paper, promote after graduation met
3. **KXBTCW/KXETHW/KXSOLW** — Weekly price-level (tickers confirmed Session 39!)
   - Same structure as KXBTCD but weekly settlement (Friday 5pm EDT)
   - Tickers: KXBTCW, KXETHW, KXSOLW — probe on weekday to see open markets
   - Signal: same lognormal drift model as KXBTCD but with weekly σ√5 scaling

**Tier 2 — High-volume, new strategy needed (post-gate research):**
4. **KXBTCMAX100** ($2.7M) — "When will BTC cross $100k again?" — Barrier option model
   - Signal: P(S_t > $100k before date T) using first-passage-time formula
   - Calibration: 30-day realized vol from Binance.US (scripts/backtest.py pattern)
   - Settlement: binary YES if BTC > $100k before deadline
5. **KXBTCMAXY** ($2.2M) — "How high will BTC get in 2026?" — Annual max model
   - Signal: P(max(S_t) > K for any t ≤ Dec 31) = barrier option all-time-high probability
6. **KXBTCY** ($1.4M, 28 mkts) — "BTC price on Jan 1, 2027" — Annual endpoint price
   - Signal: lognormal model with 9+ month horizon, calibrated vol
7. **KXBTCMAXMON** ($546k) + **KXBTCMINMON** ($439k) — Monthly trimmed mean max/min
   - BLOCKER: Must understand "trimmed mean" settlement methodology first
   - Signal: monthly vol model, harder to calibrate than spot price bets
8. **KXBTC2026200** ($3.4M single market) — "Will BTC be above $200k by 2027?"
   - Only 1 market, 8¢ YES = essentially a macro bet. Low priority.

**Tier 3 — Sports / other (gate: sports_futures shows edge first):**
9. **KXNBAGAME / KXNHLGAME** — game winners (skeleton exists)
10. **KXNBA3D** — triple-double props (~13,600 volume, best player prop)
11. **KXCPI** — CPI monthly (confirmed exists, reuse FOMC pattern)
12. **KXMLBGAME** — MLB game winners (April+ season volume)

**Do NOT build:** KXMVE* parlays, KXMVEOSCARS, KXNBA/KXMLB season futures, KXBNB/KXBCH
**Do NOT build yet:** KXDOGED (DOGE daily) — vol=0 across all markets, no liquidity

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
