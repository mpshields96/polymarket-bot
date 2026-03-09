# KALSHI MARKETS — Complete Reference
# Last updated: Session 36 (2026-03-08)
# Source: Live API probe of all 8,719 Kalshi series (Session 23) + CryptoDailyStrategy build (Session 33)
#
# PURPOSE: Prevent "KXBTC1H doesn't exist" confusion. The hourly crypto bets DO exist —
# they're inside the daily KXBTCD/KXETHD/KXSOLD series as hourly settlement slots.
# This file is the authoritative reference for all Kalshi market types.
# UPDATE THIS FILE whenever a new series is discovered or a new strategy is built.
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

═══════════════════════════════════════════════════════════════

## CATEGORY 1 — Crypto Price Direction (15-minute windows)

"Will BTC go UP or DOWN in the next 15 minutes?"
Each series has a YES side (up) and NO side (down). Markets open every 15 min, 24/7.

| Series    | Asset | Status in bot         | Notes |
|-----------|-------|-----------------------|-------|
| KXBTC15M  | BTC   | MICRO-LIVE (btc_drift_v1, btc_lag_v1 paper) | lag: 0 signals/week (HFTs too fast) |
| KXETH15M  | ETH   | MICRO-LIVE (eth_drift_v1, eth_lag_v1 paper) | |
| KXSOL15M  | SOL   | MICRO-LIVE (sol_drift_v1, sol_lag_v1 paper) | |
| KXXRP15M  | XRP   | NOT YET BUILT         | Next expansion after drift validates |
| KXBNB15M  | BNB   | NOT YET BUILT         | Lower liquidity, lower priority |
| KXBCH15M  | BCH   | NOT YET BUILT         | Lower liquidity, lower priority |

**Strategy used:** BTCDriftStrategy (sigmoid probability model)
  - min_drift_pct: 0.05% for BTC/ETH, 0.15% for SOL (3x volatility)
  - min_edge_pct: 0.05 (5%)
  - Price range guard: 35–65¢ (bets at extremes are blocked)
  - calibration_max_usd=0.01 → always 1 contract/bet (~$0.35-0.65)

**Why btc_lag fires 0 signals/week:** Kalshi BTC markets now price in the BTC spot move within
the SAME 15-minute window as Binance.US ticks. HFTs (Jane Street, Susquehanna) closed the lag.
The drift model is different — it bets on momentum continuation, not price lag.

═══════════════════════════════════════════════════════════════

## CATEGORY 2 — Crypto Price Level (Daily series, 24 hourly slots)

"Will [asset] be ABOVE or BELOW $[strike] at [specific time today]?"
Each daily series generates ~24 hourly markets. ~2000+ active contracts per series at any time.

| Series  | Asset | Status in bot         | Notes |
|---------|-------|-----------------------|-------|
| KXBTCD  | BTC   | PAPER-ONLY (btc_daily_v1) | 24 hourly windows/day |
| KXETHD  | ETH   | PAPER-ONLY (eth_daily_v1) | same structure |
| KXSOLD  | SOL   | PAPER-ONLY (sol_daily_v1) | same structure |
| KXXRPD  | XRP   | NOT CONFIRMED         | Likely exists (XRP has 15-min series) |
| KXBNBD  | BNB   | NOT CONFIRMED         | Possible |
| KXBCHD  | BCH   | NOT CONFIRMED         | Possible |

**Strategy used:** CryptoDailyStrategy (Session 33)
  - _find_atm_market(): picks contract with mid-price closest to 50¢ in 30min–6hr window
  - Model: 70% drift momentum + 30% lognormal price model
  - Paper-only until btc_drift reaches 30 settled live bets + Brier < 0.30

**How to confirm KXXRPD existence:** `kalshi.list_markets(series_ticker="KXXRPD", limit=1)`
If markets returned → series exists.

═══════════════════════════════════════════════════════════════

## CATEGORY 3 — Macro / Economic Events

| Series         | Event                       | Frequency     | Status in bot |
|----------------|-----------------------------|---------------|---------------|
| KXFEDDECISION  | Fed funds rate at FOMC      | ~8x/year      | PAPER (fomc_rate_v1) |
| KXUNRATE       | US unemployment (BLS)       | Monthly       | PAPER (unemployment_rate_v1) |
| KXCPI          | CPI inflation print         | Monthly       | NOT BUILT |
| KXJOLTS        | Job openings (JOLTS)        | Monthly       | NOT BUILT |
| KXGDP          | GDP growth                  | Quarterly     | NOT BUILT |

**Notes:**
- KXUNRATE markets open ~2 days before BLS release. No open markets outside that window = expected.
- KXFEDDECISION: uses FRED yield curve spread (DGS2-DFF) as signal.
- CPI/JOLTS/GDP: not built — low frequency + less reliable signal hypothesis than FOMC.

═══════════════════════════════════════════════════════════════

## CATEGORY 4 — Weather

| Series  | Market                              | Frequency  | Status in bot |
|---------|-------------------------------------|------------|---------------|
| HIGHNY  | High temp NYC (Central Park) for day | Weekdays   | PAPER (weather_forecast_v1) |

**Notes:**
- Markets only open on weekdays. "No open HIGHNY markets" on weekends = expected, not a bug.
- Signal: Open-Meteo GFS + NWS NDFD ensemble (EnsembleWeatherFeed), adaptive std_dev.
- Paper-only. Low priority for live promotion (seasonal edge unclear).

═══════════════════════════════════════════════════════════════

## CATEGORY 5 — Sports: Game Winners (Daily, resolves same day)

| Series    | Sport | Frequency      | Status in bot |
|-----------|-------|----------------|---------------|
| KXNBAGAME | NBA   | Every game day | SKELETON BUILT (sports_game.py) — not wired to main.py |
| KXNHLGAME | NHL   | Every game day | SKELETON BUILT (sports_game.py) — not wired to main.py |

**Notes:**
- These are **game-by-game winner** markets. Settle same day. ~1.35M volume per game.
- Signal: bookmaker moneyline consensus (same SDATA feed as sports_futures_v1).
- Skeleton in src/strategies/sports_game.py — parses KXNBAGAME-26FEB28HOUMIA-HOU format.
- NOT wired to main.py. NOT paper-trading yet.
- Would use same SDATA credits as sports_futures_v1 (shared 500/month cap).
- **Gate:** Build only after sports_futures_v1 shows real edge in paper trading.

═══════════════════════════════════════════════════════════════

## CATEGORY 6 — Sports: Season Champions (Long-duration futures)

| Series | Sport | Duration      | Status in bot |
|--------|-------|---------------|---------------|
| KXNBA  | NBA   | Season (~months) | NOT BUILT |
| KXMLB  | MLB   | Season (~months) | NOT BUILT |

**Notes:**
- These are season-winner markets (e.g. "Will the Lakers win the NBA championship?")
- Extremely illiquid. Take months to settle.
- NOT useful for this bot. Do not build.

═══════════════════════════════════════════════════════════════

## CATEGORY 7 — Politics / Geopolitical Events

These appear in predicting.top whale signal logs but are on **polymarket.COM only**, not .US.
Our account is polymarket.US (sports-only). Not currently targetable.

Examples seen in copy_trade signal logs:
- US elections, senate seats, policy decisions
- Geopolitics (ceasefire agreements, trade war outcomes)
- Cultural events (box office, awards)

**Status:** Not buildable on our .US account. Documented for context only.

═══════════════════════════════════════════════════════════════

## SERIES WE CONFIRMED DON'T EXIST

| Series searched | Result |
|-----------------|--------|
| KXBTC1H         | ❌ Does NOT exist — confirmed Session 23 (all 8,719 series probed) |
| KXETH1H         | ❌ Does NOT exist |
| KXBTC5M         | ❌ Does NOT exist |

The hourly equivalent IS KXBTCD with 24 hourly settlement slots. Not a separate series.

═══════════════════════════════════════════════════════════════

## STRATEGY → SERIES MAPPING

| Strategy file              | Series used        | Live? |
|----------------------------|--------------------|-------|
| btc_drift.py (btc_drift)   | KXBTC15M           | ✅ MICRO-LIVE |
| btc_drift.py (eth_drift)   | KXETH15M           | ✅ MICRO-LIVE |
| btc_drift.py (sol_drift)   | KXSOL15M           | ✅ MICRO-LIVE |
| btc_lag.py (btc_lag)       | KXBTC15M           | 📋 Paper (0 signals/week) |
| btc_lag.py (eth_lag)       | KXETH15M           | 📋 Paper |
| btc_lag.py (sol_lag)       | KXSOL15M           | 📋 Paper |
| orderbook_imbalance.py     | KXBTC15M+KXETH15M  | 📋 Paper |
| crypto_daily.py (btc)      | KXBTCD             | 📋 Paper |
| crypto_daily.py (eth)      | KXETHD             | 📋 Paper |
| crypto_daily.py (sol)      | KXSOLD             | 📋 Paper |
| weather_forecast.py        | HIGHNY             | 📋 Paper |
| fomc_rate.py               | KXFEDDECISION      | 📋 Paper |
| unemployment_rate.py       | KXUNRATE           | 📋 Paper |
| sports_game.py             | KXNBAGAME+KXNHLGAME| 🔧 Skeleton (not wired) |
| sports_futures_v1.py       | Polymarket.US      | 📋 Paper |
| copy_trader_v1.py          | Polymarket.US      | 📋 Paper (platform mismatch) |
