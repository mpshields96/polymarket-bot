# Kalshi Real-Price Backtest — btc_lag_v1

Generated: 2026-03-01 20:03:41 UTC
Elapsed: 103.0s

```

================================================================
  KALSHI REAL-PRICE BACKTEST — btc_lag_v1
  Source: Kalshi API (KXBTC15M) + Binance.US 1-min klines
  Period: last 30 days | Date range: 2026-01-30 to 2026-03-01
  Price range guard: 35-65c | Min remaining: 3.0min
  lag_sensitivity=15c/1% | min_edge=4% | 50c assumed in backtest.py
================================================================

  Settled markets pulled:              300
  Markets with Kalshi candle data:     297
  Markets with full settlement data:   300

  THRESHOLD SWEEP:

  BTC move threshold: >=0.20% (60s)
    Signals fired:                   8  (2.7% of windows)
    Directional accuracy:            62.5%
    Actual Kalshi YES price — mean:  52.8c | median: 54.0c | p25: 46c | p75: 62c
    Mean actual edge (real prices):  9.8%
    50c-assumed edge would show:     10.8%  (delta: -0.9pp)

  BTC move threshold: >=0.30% (60s)
    Signals fired:                   8  (2.7% of windows)
    Directional accuracy:            62.5%
    Actual Kalshi YES price — mean:  52.8c | median: 54.0c | p25: 46c | p75: 62c
    Mean actual edge (real prices):  9.8%
    50c-assumed edge would show:     10.8%  (delta: -0.9pp)

  BTC move threshold: >=0.40% (60s)  <-- current live threshold
    Signals fired:                   6  (2.0% of windows)
    Directional accuracy:            66.7%
    Actual Kalshi YES price — mean:  49.5c | median: 49.0c | p25: 43c | p75: 58c
    Mean actual edge (real prices):  13.5%
    50c-assumed edge would show:     14.9%  (delta: -1.5pp)

  BTC move threshold: >=0.50% (60s)
    Signals fired:                   2  (0.7% of windows)
    Directional accuracy:            100.0%
    Actual Kalshi YES price — mean:  54.0c | median: 54.0c | p25: 51c | p75: 57c
    Mean actual edge (real prices):  44.3%
    50c-assumed edge would show:     48.2%  (delta: -4.0pp)

  KEY FINDING:
  At >=0.40% threshold, actual Kalshi YES price was 49.5c avg (p25=43c, p75=58c).
  Kalshi price was near-neutral at signal time. 50c assumption is largely valid.
  Edge delta: -1.5pp vs 50c assumption.

  Directional accuracy at 0.40%: 66.7% — strong momentum continuation.

  Mean actual edge at real prices: 13.5% — positive after fees.

================================================================
```

## Methodology Notes

- Settlement determined from Binance BTC direction (same proxy as backtest.py)
- YES prices from Kalshi 1-min candlestick API (actual bid/ask mid prices)
- Price range guard: 35-65c (matches live btc_lag.py constants)
- Edge formula: implied_lag_pct - kalshi_fee_pct (0.07 * p * (1-p))
- lag_sensitivity = 15.0 cents per 1% BTC move (from config.yaml)
- min_edge_pct = 4% (current live btc_lag threshold)
- Each window simulated at 30s poll intervals (matches live bot behavior)
- First signal per window taken (matches live behavior — one bet per window)
