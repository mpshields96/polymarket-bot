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

## Stage Promotion Criteria (Stage 1 → Stage 2 → Stage 3)

**Key principle:** Crossing a bankroll threshold is NECESSARY but NOT SUFFICIENT to promote
to the next stage. Kelly calibration evidence is required first.

| Stage | Bankroll range | Max bet | Max % |
|-------|---------------|---------|-------|
| 1     | $0–$100       | $5.00   | 5%    |
| 2     | $100–$250     | $10.00  | 5%    |
| 3     | $250+         | $15.00  | 4%    |

### Why we cannot trust Kelly sizing today (Stage 1)

At Stage 1 ($5 cap, ~$100 bankroll), the sizing module's `pct_cap` (~$5.18) and the
main.py hard cap ($5.00) bind before Kelly does. The `limiting_factor` field in SIZE logs
will always say `"stage_cap"` or `"pct_cap"` — never `"kelly"`. This means:

- We cannot observe whether Kelly is well-calibrated (it never gets to express itself)
- All live bets are effectively flat-sized at ~$5.00 regardless of edge magnitude
- Kelly might be overconfident or underconfident — we have no signal

### Kelly calibration metrics to track (mandatory before Stage 2 promotion)

Before promoting to Stage 2 ($10 max), we need Kelly calibration evidence:

1. **Kelly-limited bets ≥ 10**: At least 10 settled live bets where `limiting_factor == "kelly"`
   (meaning Kelly said to bet LESS than the cap allows). This only becomes possible at Stage 2+.
2. **Brier score on live bets < 0.25**: Same threshold as paper graduation. Requires 30+ settled
   live bets with win_prob recorded. Currently at ~4 live bets — likely 4-6 weeks away.
3. **Edge_pct vs outcome correlation**: Higher-edge signals should win more often than lower-edge
   signals. Review last 30 live bets grouped by edge decile before promoting.
4. **No kill-switch events in last 10 live bets**: Zero hard/soft stops from consecutive losses.

### Volatility × Kelly interaction (current behavior)

Kelly sizing scales with edge_pct per signal:
- High vol day → larger BTC/ETH moves → higher edge signals → Kelly recommends larger bets
- Low vol day (e.g., weekends) → btc_lag fires 0-1 signals at threshold → Kelly is moot
- But at Stage 1, ALL this is hidden: bet is capped at $5 regardless of Kelly magnitude
- Kelly's volatility sensitivity only becomes visible at Stage 2+ when cap is $10

**implication:** We are currently flying blind on Kelly calibration. Static $5 cap is appropriate
for Stage 1. Do NOT promote to Stage 2 based solely on bankroll crossing $100. Follow the
Kelly calibration checklist above first.

### Current status (2026-02-28)

| Criterion | Required | Current |
|-----------|----------|---------|
| Bankroll > $100 | Yes | ~$103.51 ✅ |
| Live bets w/ `limiting_factor=="kelly"` ≥ 10 | Yes | 0 (all capped) ❌ |
| Brier score on live bets < 0.25 | Yes | N/A (only 4 live settled) ❌ |
| Edge_pct vs outcome correlation verified | Yes | Not computable (<10 live bets) ❌ |
| Kill switch clean last 10 bets | Yes | N/A (only 4 settled) ❌ |

**Do NOT promote to Stage 2 yet.** Earliest realistic date: ~30 live settled bets = 4-6 weeks.

## Criteria Version

v1.1 — 2026-02-28. Added Stage Promotion + Kelly calibration section. Review after 30 live settled bets.
