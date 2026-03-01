# Research Findings — 2026-03-01
# Session 26 deep research: Kalshi calibration, market microstructure, real backtest approach

## CRITICAL DISCOVERY: Kalshi Has Free Historical Candlestick API

**This changes everything.** No log mining needed. Real YES/NO price history is freely available.

```
GET https://api.elections.kalshi.com/trade-api/v2/series/{series_ticker}/markets/{ticker}/candlesticks
  ?start_ts={unix_epoch_seconds}
  &end_ts={unix_epoch_seconds}
  &period_interval=1   # 1-minute resolution
```

Get settled markets:
```
GET https://api.elections.kalshi.com/trade-api/v2/markets
  ?series_ticker=KXBTC15M&status=finalized&limit=200
```

- **Cost: FREE** (basic tier, no auth required for reads)
- **Rate limit: 20 req/sec**
- **Resolution: 1-minute OHLCV for YES bids/asks**
- **Data: OHLC in cents, volume, OI, timestamps**

New script built: `scripts/kalshi_real_backtest.py` — runs real backtest with actual Kalshi prices.

---

## Market Microstructure: Why btc_lag May Be Structurally Flawed

### HFT Response Latency
- Jane Street, Susquehanna, Jump: **100-300ms** response from BTC spot tick → Kalshi price update
- Their internal models: **microsecond timescale** (continuous order flow models)
- Our bot: ~200-500ms network + processing latency
- **Implication**: By the time btc_lag detects 0.40% BTC move, Kalshi price may already be updated

### The Core Problem (confirmed by academic research)
- Short-term BTC momentum (60-second) is accompanied by mean reversion, not pure continuation
- 10-minute prediction accuracy: only 50-55% using ML ensembles (noise dominates)
- Our backtest showed 84.1% — but that measured BTC continuing in same direction, NOT Kalshi settling correctly
- **The real question the backtest didn't answer: what was Kalshi price when signal fired?**

---

## What Actually Has Documented Edge on Kalshi

### 1. Mispriced Cheap Contracts (<20¢) — REAL EDGE
- Contracts <20¢ systematically overestimate true probability
- 5¢ contract wins ~2% of time, not 5% (market overestimates tail events)
- **Strategy**: Sell (short) cheap contracts via limit orders → consistent positive EV
- This is not what we're currently doing

### 2. Limit Orders (Makers) vs Market Orders (Takers) — DOCUMENTED
- Market makers earn positive returns; takers consistently lose money
- **Our live bets are market orders (takers)**. We are the losing side of this asymmetry.
- Consider: place limit orders instead of market orders for entry

### 3. Orderbook Imbalance (VPIN-lite) — THEORETICALLY SOUND
- 5-30 second edge window before it's arb'd away
- Our `orderbook_imbalance_v1` is paper-only and theoretically correct
- BUT: 5-30 seconds is too short for our 30-second polling loop to exploit

### 4. Volatility Clustering — SIZING SIGNAL (not direction)
- Strong BTC volatility clustering at 15-min timescale
- Use prior-hour realized vol to scale bet SIZE, not direction
- High-vol windows → larger Kelly fraction; low-vol → skip or reduce

---

## The Backtest Problem (Technical)

### What our backtest.py measures:
"When BTC moved 0.40%+ in 60 seconds (Binance), did BTC close higher/lower than window open (Binance)?"

### What the live strategy actually does:
"Bet in a Kalshi market at whatever price Jane St has quoted by the time our order arrives"

### The gaps:
1. **Kalshi price assumed 50¢** — in reality could be 70-80¢ (HFT already moved it)
2. **Settlement proxy** — backtest uses BTC close; Kalshi may use different reference
3. **The "lag" is imagined** — `implied_lag_cents = btc_move * 15.0` is a parameter, not a measurement
4. **Gate 3 (min_kalshi_lag_cents=5) is always passed** — any BTC >0.33% passes it; dead gate

### The real_backtest script (now building) will reveal:
- What actual Kalshi YES price is when btc_lag would fire
- Whether there's still measurable edge AFTER accounting for real prices
- Whether 84.1% or some lower number is the truth

---

## Polymarket vs Kalshi for Our Strategy

| Factor | Kalshi | Polymarket |
|--------|--------|-----------|
| HFT dominance | High (Susquehanna, Jane St) | Lower (more retail) |
| Latency | <15ms platform | ~500ms-1s |
| Spread (BTC/ETH) | ~0.17pp | Better on popular markets |
| Taker fees | 0.07 × p × (1-p) | 2% of winnings |
| Settlement | Fiat (USD) | USDC blockchain |
| BTC 15-min markets | KXBTC15M | Available but different |
| Retail edge opportunity | Lower (more professional) | Higher (more diverse) |

**Implication**: Our momentum signal might work better on Polymarket than Kalshi due to less HFT dominance. Worth testing once Polymarket credentials arrive.

---

## GitHub Repos of Interest

1. **[CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot](https://github.com/CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot)**
   - Arbitrage between Polymarket and Kalshi on same underlying
   - FastAPI + Next.js, detects 2-4¢ gaps
   - Low-friction, different risk profile from our strategy

2. **[Bh-Ayush/Kalshi-CryptoBot](https://github.com/Bh-Ayush/Kalshi-CryptoBot)**
   - ORIGINAL REPO we copied from (our architecture attribution)
   - Their approach: record own ticks during dry-run, replay.py for backtesting
   - Uses time-series cross-validation correctly

---

## Statistical Reality Check

With N=21 live bets (8W/13L), 38% win rate:
- Binomial test vs 50%: p ≈ 0.032 — marginally significant
- But strip extreme-odds wins (trades 70, 74, 78): 5W/18L = 28% on "normal" bets
- p ≈ 0.015 — that is meaningful. The system is losing on normal-price bets.

Need for real validation:
- N≥100 bets for strong calibration claim (not 30, which is the graduation gate minimum)
- Graduation gate (30 bets, Brier < 0.25) is a START, not proof of lasting edge
- Walk-forward cross-validation needed across multiple market regimes

---

## Recommended Next Steps (Priority Order)

1. **Run `scripts/kalshi_real_backtest.py`** — get the real win rate with actual Kalshi prices
   - If real win rate at actual prices is still >60%: btc_lag probably has edge
   - If real win rate is 48-52%: btc_lag is a coin flip, demote to paper

2. **Consider limit order entry** — stop being a taker. Place bids 1-2¢ below ask.
   - Documented: takers lose, makers win on prediction markets
   - Our current implementation: always market orders (takers)

3. **Consider mispriced cheap contract strategy** — completely different approach
   - Short contracts at <15¢ via limit orders
   - Well-documented edge in prediction market literature
   - Does NOT require momentum signal accuracy

4. **Wire volatility clustering into bet sizing** — scale Kelly fraction with prior-hour BTC vol
   - Don't change direction signal, just scale size
   - High-vol: bet $5 (current cap); low-vol: bet $2-3

5. **Polymarket API wiring** — once Matthew provides credentials
   - Test same btc_lag signal on Polymarket where HFT presence is lower
   - May find better execution and less efficient pricing

---
*Research conducted Session 26, 2026-03-01. Two parallel research agents + one execution agent.*
*Agent research output: ~115k tokens total.*
