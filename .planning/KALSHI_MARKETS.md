# KALSHI MARKETS — Complete Reference
# Last updated: Session 36 (2026-03-09) — FULL LIVE API RE-PROBE
# Source: Live API probe (Session 23, all 8,719 series) + full re-probe Session 36
#         Confirmed via get_markets() calls against trading-api.kalshi.com
#
# PURPOSE: All future Claude sessions read this FIRST before any strategy work.
#          Prevents "KXBTC1H doesn't exist" and "I don't know about player props" blindspots.
#          UPDATE THIS FILE whenever a new series is discovered or a strategy changes status.
# ══════════════════════════════════════════════════════════════

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
- KXBTC15M: ~103,000 contracts/window — the MOST LIQUID crypto market on Kalshi
- KXBTCD: ~5,000 total across all hourly slots — 20x LESS liquid than 15-min direction
- Implication: 15-min direction markets are the right focus for automated trading. Daily slots
  are paper-only until we have enough edge data to justify the wider spread.

═══════════════════════════════════════════════════════════════

## CATEGORY 1 — Crypto Price Direction (15-minute windows) ⚡ MOST LIQUID

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

## CATEGORY 2 — Crypto Price Level (Daily series, 24 hourly slots)

"Will [asset] be ABOVE or BELOW $[strike] at [specific time today]?"
Each daily series generates ~24 hourly markets. Much less liquid than 15-min direction.

| Series  | Asset | Volume (Session 36) | Status in bot       | Notes |
|---------|-------|---------------------|---------------------|-------|
| KXBTCD  | BTC   | ~5,000 total        | 📋 PAPER (btc_daily_v1) | 24 hourly windows/day |
| KXETHD  | ETH   | ~0 (new)            | 📋 PAPER (eth_daily_v1) | same structure |
| KXSOLD  | SOL   | ~0 (new)            | 📋 PAPER (sol_daily_v1) | same structure |
| KXXRPD  | XRP   | ~0 (confirmed ✅)   | NOT BUILT           | Exists but near-zero volume |
| KXBNBD  | BNB   | ❌ No open markets  | NOT BUILT           | Series inactive |
| KXBCHD  | BCH   | ❌ No open markets  | NOT BUILT           | Series inactive |

**Strategy used:** CryptoDailyStrategy (Session 33)
  - _find_atm_market(): picks contract with mid-price closest to 50¢ in 30min–6hr window
  - Model: 70% drift momentum + 30% lognormal price model
  - Paper-only until btc_drift reaches 30 settled live bets + Brier < 0.30

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

After drift validates (30 bets + Brier < 0.30), ranked by viability:
1. **KXXRP15M** — XRP 15-min direction (same code as sol_drift, ~15 min to add)
2. **KXNBAGAME / KXNHLGAME** — game winners (skeleton exists, wire to main after sports_futures shows edge)
3. **KXNBA3D** — triple-double props (best volume among player props, ~13,600)
4. **KXNBAPTS/KXNBAAST/KXNBAREB** — only after #3 proves out, volume grows
5. **KXCPI** — CPI inflation (confirmed exists, monthly, could reuse FOMC strategy pattern)
6. **KXMLBGAME** — MLB game winners (volume picks up mid-season, April+)
7. Do NOT build: KXMVE* parlays, KXMVEOSCARS, KXNBA/KXMLB season futures, KXBNB/KXBCH

═══════════════════════════════════════════════════════════════
