# KALSHI MARKETS — Complete Reference
# Last updated: Session 51 (2026-03-11) — First-hand API probe confirms all 3 crypto bet types + volume corrections
# Source: Live API probe (Session 23, all 8,719 series) + full re-probe Session 36
#         + Matthew's kalshi.com Crypto tab screenshot (Session 38)
#         + Events endpoint paginated search (Session 39) — 3,000 events scanned
#         + /series?limit=200 endpoint probe (Session 40) — 44,735 TOTAL SERIES confirmed
#         Confirmed via get_markets() + GET /events + GET /series against api.elections.kalshi.com
#         + Session 48 weekday API probe (2026-03-11) — KXBTCMAXW dormant confirmed on Tuesday
#
# TOTAL KALSHI SCALE (Session 40): 44,735 series
#   Politics: ~12,335 | Entertainment: ~10,355 | Sports: ~7,605 | Elections: ~2,140
#   Mentions: ~1,365 | Companies: ~1,520 | Economics: ~1,230 | Crypto: ~600+
#   Viable for statistical-edge bot: ONLY Crypto + Economics + Sports(futures)
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
#   - EVENTS ENDPOINT: GET /events?status=open scans all Kalshi categories
#   - ALL KALSHI CATEGORIES CONFIRMED: Crypto, Politics, Financials, Companies,
#     Mentions, Climate, Economics, Science, Sports, Entertainment, Elections, World
#
# SESSION 40 KEY CORRECTIONS + DISCOVERIES (2026-03-09 series endpoint /series?limit=100 probe):
#   - CORRECTION: KXBTCW/KXETHW/KXSOLW DO NOT EXIST. Weekly ticker is KXBTCMAXW (not KXBTCW).
#     0 open (expected Sunday). 5 finalized markets from Nov 2024. May be dormant series.
#   - CONFIRMED: KXBTCMAXW exists, KXBTCMAXM (monthly, 860k vol finalized) exists
#   - CORRECTION: KXFEDDECISION volume was 4,700 — WRONG. Actual: 23,394,968 (23.4M open)
#     March 2026 FOMC alone has 22M+ volume. Largest documented Kalshi market.
#   - CONFIRMED: KXRATECUTCOUNT (1.5M vol) — 'How many rate cuts in 2026?'
#   - CONFIRMED: KXBTC2026250 (454k vol) — 'Will BTC hit 250k in 2026?' yes=5c
#   - CONFIRMED: KXETHMAXY (1.26M vol) — 'How high will ETH get this year?' (8 markets)
#   - CONFIRMED: KXETHY (693k vol) — ETH price EOY binary (18 markets, like KXBTCY)
#   - CONFIRMED: KXETHMINY (283k vol) — 'How low will ETH fall this year?' (5 markets)
#   - CONFIRMED: KXBTCMAXD freq=daily (BTC daily max), KXBTCMINMAXY (annual min+max) — 0 open
#   - ETH market ecosystem discovered: KXETH (hourly range) + KXETHD (hourly above/below) exists
# ══════════════════════════════════════════════════════════════

## ══════════════════════════════════════════════════════════════
## ⚡ PERMANENT REFERENCE — THREE DISTINCT KALSHI CRYPTO BET TYPES
## This section is MANDATORY READING for every Claude session.
## CLAUDE: Do NOT skip this. Do NOT confuse these types. They are fundamentally different.
## Last confirmed by first-hand API probe: Session 51 (2026-03-11)
## ══════════════════════════════════════════════════════════════

## TYPE 1 — 15-MINUTE DIRECTION BETS (already live in bot)

Series:   KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M
Question: "BTC price UP in next 15 mins?" — binary YES (up) or NO (down)
Settlement: by price move direction (up or down vs open)
Time window: exactly 15 minutes, rolling 24/7
Strike: NONE — purely directional (not a price level bet)
Volume (Session 51 live probe):
  KXBTC15M: 99,794 per window
  KXETH15M: 12,574 per window
  KXSOL15M: 5,508 per window
  KXXRP15M: 7,941 per window
Bot status: ALL FOUR LIVE (drift strategies running)
Example ticker: KXBTC15M-26MAR111215-15
Example title:  "BTC price up in next 15 mins?"

Key characteristics vs Type 2/3:
  - No strike selection needed (YES = up, NO = down)
  - Shortest time horizon — 15 minutes
  - Highest frequency — fires every 15 min
  - Most liquid per-window
  - Settled by direction, not level
  - HFTs are active — btc_lag effectively dead (0 signals/week)
  - Drift strategy (momentum continuation) is the viable edge

## TYPE 2 — HOURLY/DAILY THRESHOLD BETS (paper-only in bot)

Series:   KXBTCD (BTC), KXETHD (ETH), KXSOLD (SOL), KXXRPD (XRP)
Question: "Bitcoin price on Mar 11, 2026 at 5pm EDT?" — YES = above strike, NO = below
Settlement: at a SPECIFIC CLOCK TIME (e.g., 1pm EDT or 5pm EDT) TODAY
Strike: multiple price levels open simultaneously (40-75 strikes per time slot)
Volume (Session 51 live probe — CORRECTS prior stale data):
  KXBTCD 1pm EDT slot: 170,238 contracts
  KXBTCD 5pm EDT slot: 676,674 contracts  ← most liquid daily slot
  KXETHD 1pm EDT slot: 7,606 contracts
  KXETHD 5pm EDT slot: 64,736 contracts   ← KXETHD IS NOT ZERO VOLUME (old data was wrong)
  KXSOLD 5pm EDT slot: 3,853 contracts
  KXXRPD 5pm EDT slot: 1,337 contracts
Bot status: PAPER-ONLY (btc_daily_v1 / eth_daily_v1 / sol_daily_v1 loops)
Example ticker: KXBTCD-26MAR1117-T70499.99
Example title:  "Bitcoin price on Mar 11, 2026 at 5pm EDT?"

Key characteristics vs Type 1/3:
  - Requires ATM strike selection (pick the ~50¢ contract)
  - Bet resolves at a fixed clock time (1pm EDT, 5pm EDT daily)
  - Multiple strikes open simultaneously — need to select the ATM (closest to 50¢)
  - 5pm EDT is by far the most liquid daily slot
  - Price is absolute (above/below $X at time T), not directional
  - Longer time horizon than 15-min — hours not minutes
  - Different signal logic needed vs 15-min (intraday drift from session open)
  - Academic research: contracts above 50¢ have small positive expected return
    (favorite-longshot bias confirmed — low-price < 10¢ contracts lose 60%+ of value)

## TYPE 3 — WEEKLY/FRIDAY THRESHOLD BETS (same series as Type 2, future date slots)

Series:   KXBTCD (same series — just a future Friday date slot within KXBTCD)
Question: "Bitcoin price on Friday at 5pm EDT?" — YES = above strike, NO = below
Settlement: at FRIDAY 5pm EDT (next Friday, not today)
Strike: same structure as Type 2 (40-75 strikes, ATM selection)
Volume (Session 51 live probe):
  KXBTCD-26MAR1317 (Friday Mar 13): 770,784 contracts  ← LARGEST KXBTCD SLOT
  ATM market: KXBTCD-26MAR1317-T70499.99 at 48¢ YES, 31,625 vol
Bot status: NOT YET BUILT as separate strategy (paper-only via btc_daily loop,
  but btc_daily currently only targets today's slots — Friday slot not prioritized)
Example ticker: KXBTCD-26MAR1317-T70499.99
Example title:  "Bitcoin price on Mar 13, 2026 at 5pm EDT?"

IMPORTANT: There is NO separate "KXBTCW" series for weekly bets.
The "weekly" bet type is just the KXBTCD series with a future Friday date.
"KXBTCW/KXETHW/KXSOLW DO NOT EXIST" — that note refers to a separate weekly series.
But the Friday-slot weekly bet DOES exist within KXBTCD and has MORE volume than any daily slot.

Key characteristics vs Type 1/2:
  - Same series as Type 2 but settles on Friday (not today)
  - Multi-day time horizon — 1-5 days before settlement
  - Highest KXBTCD volume (770K vs 676K for same-day 5pm)
  - Different market dynamics: multi-day uncertainty vs intraday noise
  - Wider spreads initially (more uncertainty), but tightens as Friday approaches
  - Different signal needed: macro/weekly trend vs intraday drift
  - Retail-heavy (Webull launched these specifically for retail)
  - Expansion gate: build AFTER hourly/daily strategy validates (30+ live bets)

## CRITICAL: DO NOT CONFUSE THESE TYPES

WRONG: "The hourly bets are the 15-minute bets."
WRONG: "KXBTCD has ~5,000 volume" (stale Session 36 data — actual: 1.6M+ per day)
WRONG: "KXETHD has zero volume" (stale — actual: 64K in 5pm slot, Session 51 confirmed)
WRONG: "Weekly bets need KXBTCW" (KXBTCW does not exist — it's KXBTCD with Friday date)

CORRECT:
  - 15-min DIRECTION = KXBTC15M etc. (UP or DOWN, no strike, 15 min)
  - Hourly THRESHOLD (today) = KXBTCD 1pm/5pm slot (above/below $X today)
  - Weekly THRESHOLD (Friday) = KXBTCD Friday slot (above/below $X on Friday)

## ══════════════════════════════════════════════════════════════

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

**FULL KALSHI MARKET CATEGORIES (top nav — Session 39 events endpoint probe):**
Session 39 event endpoint probe (GET /events?status=open, 5 pages ~1000 events):

| Category | Count (open events) | Example | Strategy relevance |
|----------|---------------------|---------|-------------------|
| Elections | 453 | Will X win UK election? | ❌ Political edge hard to quantify |
| Politics | 339 | Will Mamdani become US President? | ❌ Not in scope |
| Entertainment | 57 | James Bond theme performer? | ❌ Not in scope |
| Economics | 57 | How high will unemployment get before 2030? | ✅ FOMC/CPI/unemployment (partial) |
| Sports | 39 | Canadian team wins Stanley Cup before 2031? | ✅ Already built (paper) |
| Science/Tech | 12 | Human on Mars before CA high-speed rail? | ❌ Long-dated, hard to model |
| World | 7 | Will Musk visit Mars in his lifetime? | ❌ Not in scope |
| Social | 7 | US state population decrease? | ❌ Not in scope |
| Climate | 10 | World pass 2°C? | ❌ Similar to weather (HIGHNY already built) |
| Companies | 11 | When will a company achieve AGI? | ❌ Not in scope |
| Financials | 3 | Will Ramp or Brex IPO first? | ❌ Not in scope |
| Health | 4 | FDA cure for Type 1 diabetes before 2033? | ❌ Not in scope |
| Transportation | 1 | Will Karl Bushby finish world walk? | ❌ Not in scope |

Note: Volume field returns 0 for events (volume tracked per market, not per event).
Economics (57) is most relevant — likely includes CPI, GDP, PCE, JOLTS series we haven't built.
KXGDP found active (92k vol), KXCPI active (890 vol) — both NOT BUILT yet in bot.

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

## ⚠️ KXBTCD STRUCTURE CLARIFICATION (Session 39 research — CRITICAL)

**The daily bracket price level is set ONCE per day** (likely at midnight or market open),
NOT as a new level per hour. All 24 hourly slots share the SAME dollar strike set that morning.

Example: If BTC opens at $84,000 and the daily bracket is set at $84,000:
- 9am slot: "Will BTC be above $84,000 at 9am EST?" → 50¢ at open (fair coin)
- 12pm slot: "Will BTC be above $84,000 at 12pm EST?" → 50¢ at open (same strike, more time)
- 5pm slot: same strike, but time uncertainty is lower as 5pm approaches

**Signal implication (from Session 39 GitHub research):**
If BTC has drifted significantly since the bracket was set (e.g., +1.5% since midnight),
early-morning YES contracts may be systematically underpriced because:
- Market prices the slot at ~50¢ when bracket is set
- BTC drifts → the YES should reprice toward 65-70¢ as the move persists
- Our btc_drift signal logic IS directly applicable to KXBTCD!
- This is why Kalshi-CryptoBot specifically paired BOTH 15-min + hourly — same signal.

**Key observation:** KXBTCD hourly slots are NOT "hourly direction" bets. They are daily
absolute-level bets with hourly sub-resolution windows. The "7am EST" means the signal
window closes at 7am, not that it resets. This is a path-independent binary: at expiry, is BTC above K?

**Community research (Session 39 agent):**
- Kalshi-CryptoBot (GitHub: Bh-Ayush/Kalshi-CryptoBot) explicitly pairs 15-min + hourly bots
  (repo now private = possibly profitable alpha being hidden — strong signal)
- HN #1 leaderboard trader (ammario): uses log-odds spread market-making across many markets.
  Different architecture from us but confirms Kalshi edge is real for systematic traders.
- Academic study (arXiv:2601.01706): 2-4% persistent price deviations between platforms.
- QuantPedia: confirms systematic edges exist in prediction markets for well-calibrated models.

**Volume comparison (Session 36 live probe):**
- KXBTC15M: ~103,000 contracts/window — the MOST LIQUID 15-min crypto market
- KXBTCD: ~5,000 total across all hourly/daily slots — 20x LESS liquid than 15-min direction
- Weekly price-level ("Bitcoin price on Friday"): ~$455K volume — much more than KXBTCD!
- One-Time events ("When will BTC hit $150k?"): ~$14.8M volume — 140x KXBTCD!
- Implication: 15-min direction is right for high-frequency. Weekly/annual/one-time events
  have enormous volume and could support a separate lower-frequency strategy.

## ⚠️ RESEARCH-VERIFIED EXPANSION PRIORITY (Session 39 findings)

Based on Session 39 Reddit/GitHub research agent findings:

| Priority | Market Type | Edge Source | Build When |
|----------|-------------|-------------|------------|
| Tier 1A | KXBTC15M drift (btc/eth/sol) | Momentum continuation | LIVE NOW ✅ |
| Tier 1B | KXBTCD early-morning hourly slots | Same drift signal vs fixed bracket | Expansion gate opens |
| Tier 2A | KXBTCMAX150/100 via options | Compare vs Deribit digital option price lag | Post-gate, needs Deribit API |
| Tier 2B | KXXRP15M drift | Same 15-min model, new asset | Post-gate (2 weeks live data) |
| Tier 3 | KXBTCW weekly | Macro signal (different from momentum) | Later — needs different model |
| Tier 4 | KXBTCMAXY/KXBTCMINY/KXBTCMAXMON | Lognormal range model (complex) | Later — log to todos only |

**DO NOT BUILD until expansion gate opens** (still closed as of Session 39)

**Red flags confirmed (do not pursue):**
- LLM-based "AI trading bots" — tested negative returns, educational only
- Cross-platform Kalshi/Polymarket arbitrage — US residents legally blocked (polymarket.COM closed)
- Monthly/yearly max-min brackets — too thin, capital lockup, complex signal
- KXBTCMAX150 as a long-duration position — capital locked months, poor vs 15-min 96x/day recycling

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
| KXDOGE15M | DOGE  | ❌ NO OPEN MARKETS (Session 40 probe)       | Series exists via /series endpoint, 0 open (inactive like BNB/BCH) |

**Strategy used:** BTCDriftStrategy (sigmoid probability model)
  - min_drift_pct: 0.05% for BTC/ETH, 0.15% for SOL (3x volatility)
  - min_edge_pct: 0.05 (5%) — restored Session 36 (was raised to 0.08 in Session 25, WRONG)
  - Price range guard: 35–65¢ (bets at extremes blocked — near expiry behavior)
  - calibration_max_usd=0.01 → always 1 contract/bet (~$0.35-0.65)

**Why btc_lag fires 0 signals/week:** Kalshi BTC markets now price in the BTC spot move within
the SAME 15-minute window as Binance.US ticks. HFTs (Jane Street, Susquehanna) closed the lag.
The drift model is different — it bets on momentum continuation, not price lag.

**Confirmed mechanism (Session 42, Protos article Feb 2026):** Polymarket previously had a 500ms
taker order delay. Quants exploited this by hedging Polymarket 5-min BTC bets through Kalshi 15-min
markets. This created massive HFT arbitrage pressure that efficiently priced Kalshi 15-min markets.
Polymarket removed the speed bump (Feb 2026) — but Kalshi 15-min markets remain very efficient.
Net effect: btc_lag remains 0 signals/week. btc_drift (momentum, not lag) is the viable strategy.

═══════════════════════════════════════════════════════════════

## CATEGORY 2A — Crypto Price Level (Hourly + Daily, KXBTCD structure)

"Will [asset] be ABOVE or BELOW $[strike] at [specific time today]?"
Each daily series generates ~24 hourly markets. Kalshi UI shows these as "Hourly (8)" + "Daily (10)".

| Series  | Asset | Volume (Session 51 FRESH PROBE) | Status in bot       | Notes |
|---------|-------|----------------------------------|---------------------|-------|
| KXBTCD  | BTC   | 676K (5pm slot), 170K (1pm), 770K (Fri) | 📋 PAPER (btc_daily_v1) | See TYPE 2/3 above |
| KXETHD  | ETH   | 64K (5pm slot), 7.6K (1pm)      | 📋 PAPER (eth_daily_v1) | NOT zero — 64K confirmed |
| KXSOLD  | SOL   | 3.8K (5pm slot)                  | 📋 PAPER (sol_daily_v1) | Low but nonzero |
| KXXRPD  | XRP   | 1.3K (5pm slot)                  | NOT BUILT           | Low volume, low priority |
| KXDOGED | DOGE  | ~0                               | NOT BUILT           | Zero liquidity — skip |
| KXBNBD  | BNB   | 0 open markets                   | NOT BUILT           | Series inactive |
| KXBCHD  | BCH   | 0 open markets                   | NOT BUILT           | Series inactive |

NOTE (Session 51): Old Session 36 "~5,000 total" for KXBTCD was WRONG — that probe summed
all OTM contracts (near-zero vol each). ATM contracts have 600K+ volume. The 5pm EDT slot
is the most liquid daily KXBTCD slot. Friday (weekly) slot has even more (770K+).

**Strategy used:** CryptoDailyStrategy (Session 33)
  - _find_atm_market(): picks contract with mid-price closest to 50¢ in 30min–6hr window
  - Model: 70% drift momentum + 30% lognormal price model
  - Paper-only until expansion gate opens

═══════════════════════════════════════════════════════════════

## CATEGORY 2B — Crypto Price Level (Weekly) ⚠️ TICKER CORRECTED Session 40

"How high will [asset] get this week?" — multi-strike range market, settles Friday 5pm EDT

| Series    | Asset | Vol (all-time finalized) | Status in bot | Notes |
|-----------|-------|--------------------------|---------------|-------|
| KXBTCMAXW | BTC   | ~177k (5 finalized mkts from Nov 2024) | ❌ NOT BUILT | Series exists, currently DORMANT (no open) |
| KXETHW    | ETH   | unknown                  | ❌ NOT BUILT  | ❌ NOT A REAL TICKER — does not exist |
| KXSOLW    | SOL   | unknown                  | ❌ NOT BUILT  | ❌ NOT A REAL TICKER — does not exist |

**⚠️ CRITICAL CORRECTION (Session 40, 2026-03-09):**
- KXBTCW, KXETHW, KXSOLW DO NOT EXIST. Series endpoint returns 404. Markets API returns 0.
- Session 39 incorrectly confirmed these. The actual weekly BTC ticker is KXBTCMAXW.
- KXBTCMAXW structure: "How high will BTC get this week?" — same multi-strike as KXBTCMAXMON
  Last active: November 2024 (5 finalized markets). Currently dormant — may reopen seasonally.
  Nov 2024 strikes: $95k-$99k range at BTC ATH. Volume 177k total across 5 markets.
- Strategy: NOT a priority — dormant series. Probe on weekdays to check if open.
- Session 40 (0 expected Sunday): 0 open markets.
- Session 48 (2026-03-11, Tuesday): still 0 open markets. CONFIRMED PERMANENTLY DORMANT — not a weekend-only artifact. DO NOT probe further.
- UI "Weekly (8)" count may refer to events or be inaccurate — don't rely on UI count.

**Next step:** No further probing needed. Series is confirmed dormant as of March 2026.

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

**Market structure example (KXBTCMAXMON — Session 48 fresh data, March 2026):**
- KXBTCMAXMON-BTC-26MAR31 with suffix 8500000 → "Will BTC trimmed mean be above $85,000 by 11:59pm March 31?"
- Top markets by volume (Session 48 probe):
  KXBTCMAXMON-BTC-26MAR31-8500000 vol=59,629 ($85,000 strike) — highest vol strike
  KXBTCMAXMON-BTC-26MAR31-8250000 vol=55,387 ($82,500 strike)
  KXBTCMAXMON-BTC-26MAR31-8750000 vol=35,821 ($87,500 strike)
- Strikes clustered around current BTC price (~$83k in March 2026). Near-ATM contracts most liquid.
- Settlement: trimmed mean = removes top/bottom outlier prices across month

**KXBTCMINMON — Session 48 fresh data (8 open, March 2026):**
- Top markets by volume:
  KXBTCMINMON-BTC-26MAR31-6500000 vol=112,301 ($65,000 floor) — highest vol
  KXBTCMINMON-BTC-26MAR31-6250000 vol=109,027 ($62,500 floor)
  KXBTCMINMON-BTC-26MAR31-6000000 vol=67,491 ($60,000 floor)
- Highest vol around $60-65k floor — market pricing meaningful downside tail risk.
- Total KXBTCMINMON vol across 8 markets: ~500k+. More liquid than KXBTCMAXMON.

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
| KXETHY  | ETH   | ~$692K (18 mkts) ✅ | 18      | ❌ NOT BUILT | ETH price on Jan 1, 2027 |
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

**KXBTCMAXY current pricing (Session 48 fresh probe, 2026-03-11 — "How high will BTC get in 2026?"):**
- 7 open markets confirmed. Top markets by volume:
  KXBTCMAXY-26DEC31-99999.99 vol=602,841 ($100k strike) — highest vol, most tradeable
  KXBTCMAXY-26DEC31-109999.99 vol=244,704 ($110k strike)
  KXBTCMAXY-26DEC31-149999.99 vol=184,334 ($150k strike)
- Note: vol=602,841 on the $100k strike is the highest single-market vol in the KXBTCMAXY series.
- Total: 7 markets, $2.2M+ vol (consistent with Session 39/41)

**KXBTCMINY current pricing (Session 48 fresh probe, 2026-03-11 — "How low will BTC get in 2026?"):**
- 5 open markets confirmed. Top markets by volume:
  KXBTCMINY-27JAN01-40000.00 vol=207,278 ($40k floor) — highest vol
  KXBTCMINY-27JAN01-45000.00 vol=184,689 ($45k floor)
  KXBTCMINY-27JAN01-50000.00 vol=184,789 ($50k floor)
- Note: market assigns meaningful probability to BTC dipping to $40-50k range in 2026.
- ~200k vol per floor level = moderately liquid for a 9-month horizon market.
- Total: 5 markets, ~$1.0M vol

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
| KXFEDDECISION  | Fed funds rate at FOMC      | ~8x/year      | ~23,400,000 ✅ CORRECTED | 📋 PAPER (fomc_rate_v1) |
| KXRATECUTCOUNT | # of rate cuts this year    | Annual        | ~1,548,484 ✅ confirmed  | NOT BUILT |
| KXRATECUT      | Will Fed cut at all in 2026 | Annual        | ~3,267 confirmed         | NOT BUILT |
| KXUNRATE       | US unemployment (BLS)       | Monthly       | Opens 2d pre-BLS | 📋 PAPER (unemployment_rate_v1) |
| KXCPI          | CPI inflation print         | Monthly       | 74 open (Session 48) — much more liquid than expected | NOT BUILT |
| KXJOLTS        | Job openings (JOLTS)        | Monthly       | 0 open (probe 2026-03-09, not active) | NOT BUILT |
| KXGDP          | GDP growth                  | Quarterly     | ~208,000 ✅ confirmed | NOT BUILT |
| KXPAYROLLS     | Non-farm payrolls (NFP)     | Monthly       | ~1,581 (Nov 2026 pre-release) | NOT BUILT |

**Notes:**
- KXUNRATE markets open ~2 days before BLS release. No open markets outside that window = expected.
- KXFEDDECISION: uses FRED yield curve spread (DGS2-DFF) as signal.
- **KXFEDDECISION VOLUME CORRECTION (Session 40 probe)**: Previous estimate 4,700 was WRONG.
  Real volume: 80 open markets, 23,394,968 total volume. March 2026 FOMC alone: 22M+ volume.
  Session 48 (2026-03-11): 80 open markets confirmed — still active (no change from Session 41).
  Market structure: each FOMC meeting has 5 markets — H0 (hold/no change), C25 (cut 25bps),
  C26 (cumulative 26×10bps cut?), H25 (hold at 2.5%?), H26 (hold at 2.6%?).
  March 2026 pricing: H0=97¢ (hold, 97% prob), C25=1¢ (cut 25bps, 1% prob) — market expects no change.
  Fee structure: quadratic_with_maker_fees (NOT standard). Higher cost for market orders.
  NBER/Fed study (2026 Jan): Kalshi FOMC markets beat fed funds futures for rate prediction accuracy.
  Volume context: $23.4M open > KXBTCMAX150 ($10.8M). This is the LARGEST documented Kalshi market.
- KXCPI: Session 48 probe (2026-03-11): 74 open markets — far more than expected. Prior ~1,400 vol was undercounting.
  Sample: KXCPI-26MAR-T1.0 vol=78, KXCPI-26MAR-T0.9 vol=97. Individual market volumes are low (tens to hundreds),
  but 74 markets open = much more active series than previously documented.
  Revised priority: log for post-gate feasibility study. Elevate from 'low freq' to 'moderate activity — revisit signal feasibility after expansion gate opens'.
- KXJOLTS/KXPCE/KXHOUSING/KXRETAIL/KXNFP: 0 open markets (probed 2026-03-09, not currently active).
  KXPAYROLLS: 10 markets open for November 2026 NFP release, 1,581 total vol. Very low volume.
- **KXRATECUTCOUNT confirmed (Session 40 probe)**: 20 markets, 1,548,484 volume.
  Session 48 (2026-03-11): 21 open confirmed — still active.
  Top markets: KXRATECUTCOUNT-26DEC31-T9 vol=98,432, KXRATECUTCOUNT-26DEC31-T8 vol=119,207.
  Market strongly concentrated at T8/T9 boundary — expects 1-3 rate cuts in 2026.
  Structure: "Will Fed cut rates ≥T times by Dec 31, 2026?" (T9=0¢, T8=1¢, T7=1¢ → market expects 1-3 cuts).
  Signal: could use FRED CME FedWatch implied probabilities or CME fed funds futures.
  Priority: research signal model before building — high volume, annual horizon.
- **KXRATECUT**: 1 market, 3,267 vol — "Will Fed cut at all in 2026?" yes=79¢.
- **KXPCE**: 0 open — confirmed still dormant (Session 48, 2026-03-11).
- **KXJOLTS**: 0 open — confirmed still dormant (Session 48, 2026-03-11).
- **KXUNRATE**: 0 open (Session 48, 2026-03-11) — outside active BLS release window, expected. Normal.
- Macro market hierarchy (largest to smallest): KXFEDDECISION(23.4M) > KXRATECUTCOUNT(1.5M+) > KXGDP(208k) > KXCPI(74 mkts, low per-mkt vol) > KXUNRATE(opens near BLS) > KXPAYROLLS(1.6k) > KXPCE/KXJOLTS (0 = dormant).
- **KXGDP confirmed active (Session 39 probe)**: 8 open markets Q1 2026, 208,040 total volume.
  Settlement = BEA advance GDP estimate (~late April). Structure: binary "Will real GDP exceed X%?"
  Market pricing (2026-03-09): T1.0=72¢, T1.5=59¢, T2.0=45¢, T2.5=38¢, T3.0=28¢, T3.5=17¢, T4.0=10¢, T4.5=7¢
  → Implied market consensus: ~1.5-2.0% Q1 GDP growth. 208k vol = 44x CPI (meaningful liquidity).
  Priority: log to todos.md — quarterly + requires macro model, not near-term target.

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
   - Confirmed active Session 41 probe: 1 open market at 43¢ ✅
2. **KXBTCD hourly live** — btc_daily_v1 already paper, promote after graduation met
3. **KXBTCMAXW** — Weekly BTC max (⚠️ KXBTCW/KXETHW/KXSOLW DO NOT EXIST — corrected Session 40)
   - KXBTCMAXW: 0 open Sunday (dormant since Nov 2024). Probe Mon–Fri.
   - KXETHW/KXSOLW equivalents: do NOT exist. Only BTC weekly confirmed.
   - Signal: same drift model but weekly settlement — needs σ√5 scaling. Do not build until active.

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

### Session 41 Probe Results (2026-03-09, 20:08 CDT)

All major series confirmed or updated. Key findings:
- KXXRP15M: 1 open at 43¢ — ACTIVE, confirmed next expansion candidate ✅
- KXBTCMAXW: 0 open (Sunday dormant — probe weekday) — NOT KXBTCW ⚠️
- KXBTCMAXM: 0 open (check weekday)
- KXDOGE15M: 0 open (dormant — skip)
- KXBTCMAX150: 3 open, vol=10,854,936 (volumes up from Session 39)
- KXBTCMAX100: 6 open, vol=2,706,392 (DEC now 38¢ — BTC at $84k needs +19%)
- KXBTC2026200: 1 open, vol=3,425,045 (8¢ YES)
- KXBTCY: 28 open, vol=1,432,993 (annual binary)
- KXETHY: 18 open, vol=696,273 (annual ETH binary)
- KXETHMAXY: 8 open, vol=1,257,721 (annual ETH max)
- KXSOLMAXY: 8 open, vol=205,285
- KXBTCMAXMON: 6 open, vol=546,756 (March trimmed mean max)
- KXBTCMINMON: 8 open, vol=442,516 (March trimmed mean min)
- KXRATECUTCOUNT: 21 open, vol=1,989,985 (1-3 cuts expected by market)
- KXFEDDECISION: 80 open, vol=23,410,906 (LARGEST — 80 markets, all FOMC dates 2026-2028)
- KXGDP: 8 open, vol=208,202

Reddit/GitHub research (Session 41):
- No Reddit r/kalshi strategy posts for weekly/barrier/annual markets — lightly traded by retail
- GitHub bots: all use signal-based approaches (NOT copy trading). No weekly/barrier strategy patterns found.
- Implication: markets remain potentially underexploited by retail algorithmic traders.

═══════════════════════════════════════════════════════════════

### Session 42 Probe Results (2026-03-10, 22:16 CDT — Tuesday)

**KXBTCMAXW**: 0 open markets on TUESDAY — CONFIRMED DORMANT (not seasonal to weekday)
  → Previously hypothesized it might open Mon-Fri. Tested on a Tuesday: still 0 open.
  → Conclusion: KXBTCMAXW was a one-time Nov 2024 series. DO NOT build for this.

**KXBTCMAX100 pricing update (BTC ~$82k, down from $84k)**:
  - MAR 2026: 1/3c (vol=999k) — expires ~Apr 1, essentially impossible
  - MAY 2026: 15/16c (vol=363k)
  - JUNE 2026: 21/22c (vol=515k)
  - SEP 2026: 29/30c (vol=62k)
  - DEC 2026: 41/42c (vol=88k)
  → DEC went from 38¢ → 41¢ despite BTC dropping $2k (market sees longer term recovery path)
  → Note: added JUNE contract (21c) vs Session 41 which showed only 6 contracts total

**KXBTCMAX150 pricing update (BTC at $82k, target=$150k = +83% away)**:
  - 26MAR31: 0/2c (vol=3.7M) — expires in 3 weeks, essentially 0%
  - 26APR30: 2/3c (vol=2.7M) — 7 weeks, ~2% implied
  - 26MAY31: 4/5c (vol=4.5M) — 12 weeks, ~4% implied
  → Still heavily priced toward NO. $10.8M volume but wide spreads (1c wide on 2-4c markets)
  → Wide spreads suggest market maker dominated, hard to trade efficiently

**KXBTC2026200**: 8/9c (vol=3.4M) — stable. Binary "Will BTC be above $200k by Jan 1, 2027?"

**KXBTCMAXY** (How high will BTC get in 2026?):
  - $100k: 37/38c | $110k: 29/30c | $130k: 17/19c | $140k: 14/15c | $150k: 12/13c

**KXBTCY** (EOY binary):
  - T20000: 4/4c | T149999: 5/5c | B97500: 3/3c | B92500: 3/3c | B87500: 4/4c

**KXETHMAXY**: $4250=21c | $4500=17c | $4750=14c | $5000=13c | $6000=9c

**Reddit/GitHub Research (Session 42)**:
- NO Reddit r/kalshi posts discussing KXBTCMAX100/150 barrier event strategies found
- NO GitHub bots using first-passage-time models for barrier events
- Kalshi barrier markets appear algorithmically UNDEREXPLORED — all GitHub bots use 15-min direction
- HFTs do NOT appear to dominate barrier markets (unlike KXBTC15M directional)
- Potential edge: first-passage-time GBM pricing vs market odds for KXBTCMAX100/150
- However: wide spreads on KXBTCMAX150 (1c wide on 2-4c markets) limit profitability
- KXBTCMAX100 has tighter spreads (1c wide on 15-41c) — more tradeable if edge exists
- CONCLUSION: Log to todos.md post-gate. Legitimate research opportunity, not ready to build.


### Session 42 Extended Probe — Non-Crypto Financial Series

Probed all 8,947 Kalshi series for financial/macro categories beyond crypto.
Key findings:

**NEW DISCOVERY: KXNASDAQ100Y** — Annual Nasdaq range (same structure as KXBTCMAXY)
  - 5 open markets | $516,451 total vol (top mkt: $467,972)
  - Sample: KXNASDAQ100Y-26DEC31H1600-T33000 | yes=2/6c
  - Structure: "Will Nasdaq be above X by Dec 31, 2026?"
  - SAME barrier option model as KXBTCMAXY — could reuse model when/if built
  - Volume is significant ($516k). Log to todos as future candidate.

**KXGDP** — US GDP quarterly growth: $199,493 total vol (already in doc from Session 39/40)
  - 5 open Q2/Q3/Q4 2026 markets, 97k top vol
  - Sample: KXGDP-26APR30-T4.5 | yes=7/8c (7% chance GDP >4.5%)

**KXGDPUSMAX** — "Will US GDP peak at X%?": $169,297 vol (1 open mkt at 56/59c)
  - 1 open market: KXGDPUSMAX-28-5 (will US GDP growth peak above 5% by 2028?)

**DORMANT series (not worth building):**
  - KXOILW (oil weekly): $14,601 total vol — too thin
  - KXGOLDW (gold weekly): 5 open but only $131 vol — no liquidity
  - KXINXMINW (S&P weekly knockout): $4,293 total — dormant
  - KXNASDAQ100Z (Nasdaq up binary): $21,484 — too thin
  - KXCPICORE: $35,431 — very thin
  - KXPCECORE: $63 vol — no liquidity
  - KXHOUSINGSTART: 5 open but $0 vol — brand new with no liquidity yet

**Confirmed non-existent on Kalshi (no series found):**
  - KXSPX / KXSPY: No daily or weekly S&P 500 direction bets
  - KXNFP: No Non-Farm Payrolls markets
  - KXDXY: No Dollar index markets
  - KXVIX: No volatility index bets
  - Individual stocks (NVDA, AAPL, MSFT): No individual stock prediction markets

**Conclusion for expansion roadmap:**
  - KXNASDAQ100Y is a legitimate future candidate (same model as KXBTCMAXY, $516k vol)
  - Everything else in non-crypto is too thin or dormant
  - Macro focus should remain on KXGDP/KXFEDDECISION which already have infrastructure

═══════════════════════════════════════════════════════════════

### Session 48 Probe Results (2026-03-11, Tuesday)

KXBTCMAXW: 0 open on TUESDAY — CONCLUSIVELY DORMANT.
  Session 42 tested on what was thought to be Tuesday. Session 48 re-confirms on a confirmed weekday.
  0 open on a confirmed weekday Tuesday March 11, 2026. NOT a weekend artifact.
  This series had 5 finalized markets from Nov 2024. No new markets since.
  Action: Remove from active probe rotation. Do not build.

KXBTCMAXMON (6 open, March 2026 trimmed mean max):
  Top markets by volume:
    KXBTCMAXMON-BTC-26MAR31-8500000 vol=59,629 ($85,000 strike)
    KXBTCMAXMON-BTC-26MAR31-8250000 vol=55,387 ($82,500 strike)
    KXBTCMAXMON-BTC-26MAR31-8750000 vol=35,821 ($87,500 strike)
  Insight: strikes clustered around current BTC price ($83k area). Near-ATM contracts most liquid.

KXBTCMINMON (8 open, March 2026 trimmed mean min):
  Top markets by volume:
    KXBTCMINMON-BTC-26MAR31-6500000 vol=112,301 ($65,000 floor) — highest vol
    KXBTCMINMON-BTC-26MAR31-6250000 vol=109,027 ($62,500 floor)
    KXBTCMINMON-BTC-26MAR31-6000000 vol=67,491 ($60,000 floor)
  Insight: highest vol around $60-65k floor — market pricing meaningful downside tail risk.
  Total KXBTCMINMON vol across 8 markets: ~500k+. More liquid than KXBTCMAXMON.

KXBTCMAXY (7 open, annual BTC max by Dec 2026):
    KXBTCMAXY-26DEC31-99999.99 vol=602,841 ($100k strike) — highest vol, most tradeable
    KXBTCMAXY-26DEC31-109999.99 vol=244,704 ($110k strike)
    KXBTCMAXY-26DEC31-149999.99 vol=184,334 ($150k strike)
  Insight: $100k is the focal strike. 600k vol = very liquid for an annual market.

KXBTCMINY (5 open, annual BTC min by Jan 2027):
    KXBTCMINY-27JAN01-40000.00 vol=207,278 ($40k floor) — highest vol
    KXBTCMINY-27JAN01-45000.00 vol=184,689
    KXBTCMINY-27JAN01-50000.00 vol=184,789
  Insight: market assigns meaningful prob to BTC dipping to $40-50k range in 2026.
  ~200k vol per floor level = moderately liquid for a 9-month horizon market.

KXCPI (74 open — MAJOR UPDATE from prior ~1,400 total vol estimate):
  Session 48 probe finds 74 open markets — far more than expected.
  Sample: KXCPI-26MAR-T1.0 vol=78, KXCPI-26MAR-T0.9 vol=97
  Note: individual market volumes are low (tens to hundreds), but 74 open markets
  suggests this is a more active series than previously documented.
  Revised priority: log for post-gate feasibility study. Not low-frequency obscure.

KXPCE: 0 open — confirmed still dormant.
KXJOLTS: 0 open — confirmed still dormant.
KXUNRATE: 0 open — outside BLS release window (expected).
KXFEDDECISION: 80 open — confirmed active (no change).
KXRATECUTCOUNT: 21 open — confirmed active.
  Top markets: KXRATECUTCOUNT-26DEC31-T9 vol=98,432, KXRATECUTCOUNT-26DEC31-T8 vol=119,207.
  Market strongly concentrated at T8/T9 boundary (1-3 rate cuts expected in 2026).

Macro market hierarchy (updated Session 48):
  KXFEDDECISION (23.4M) > KXRATECUTCOUNT (1.5M+) > KXGDP (208k) > KXCPI (74 mkts, low per-mkt vol)
  > KXUNRATE (opens near BLS) > KXPAYROLLS (1.6k) > KXPCE/KXJOLTS (0 = dormant)

No new series discovered. All previously documented series status confirmed.

