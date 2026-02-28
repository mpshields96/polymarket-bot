# Live Graduation Criteria — polymarket-bot

## Overview

Each strategy graduates to live trading INDEPENDENTLY. A strategy may go live
while others remain in paper mode. Graduation is manually triggered after all
criteria are met (set LIVE_TRADING=true AND pass --live flag per strategy).

Run `python setup/verify.py` to see current status for all 8 strategies.

## Thresholds

| Criterion | Threshold | Rationale |
|-----------|-----------|-----------|
| Minimum paper trades (settled) | **30** | Statistical significance (~4-sigma at 60% win rate) |
| Minimum days running | **7** | Captures intraday + weekly market patterns |
| Brier score (lower = better) | **< 0.25** | 0.2178 = STRONG; 0.25 = acceptable calibration |
| Maximum consecutive losses | **< 5** | Kill switch fires at 5; live graduation requires headroom |
| Win rate (informational) | >= 55% | Directional signal; Brier score is primary calibration metric |

## Strategy-Specific Notes

### btc_lag / eth_lag (momentum)
- Backtest: btc_lag 84.1% acc / 44 signals per 30 days
- Competing with Jane Street / Susquehanna / Jump HFTs (0.17pp spread)
- Monitor fill quality in paper mode — if fills frequently miss, recalibrate min_edge_pct
- Extra bar: require 30+ settled trades (signal fires ~1-2x/day, so ~15-30 days to hit count)

### btc_drift / eth_drift (sigmoid model)
- btc_drift Brier = 0.2178 (STRONG calibration on 30-day backtest)
- Capped at 5 bets/day to prevent tax churn — 30 settled trades = ~6-7 paper days minimum
- Brier score threshold is the primary graduation gate for drift strategies

### orderbook_imbalance (BTC + ETH)
- VPIN-lite signal: no backtest Brier score available (novel signal)
- Must accumulate 30 settled trades before Brier can be computed reliably
- If Brier is unavailable after 30 trades (no win_prob recorded), use win_rate >= 58% instead

### weather_forecast (HIGHNY)
- Only fires on HIGHNY weekday markets — lower signal frequency
- 30 settled trades may take 4-6 weeks given weekday-only operation
- Min days running extended to 14 days for weather (seasonal variation)

### fomc_rate (KXFEDDECISION)
- Fires ~8x/year (14 days before each FOMC meeting)
- Min settled trades threshold: 5 (cannot reach 30 in first year)
- Min days running: N/A — criterion replaced by "at least 2 FOMC cycles completed"
- Brier score threshold same: < 0.25

## How to Check

```bash
python setup/verify.py
```

Section [11] prints graduation status per strategy. WARN (not FAIL) — graduation
is advisory and never blocks bot startup.

## How to Graduate a Strategy

1. Confirm verify.py shows PASS on all criteria for that strategy
2. Review paper P&L for that strategy in dashboard (localhost:8501)
3. Update config.yaml: set `live: true` under the strategy section (once per-strategy live flag is added)
4. Restart bot with --live flag and LIVE_TRADING=true in .env
5. Monitor first 5 live bets manually

## Criteria Version

v1.0 — 2026-02-28. Review and tighten after first strategy goes live.
