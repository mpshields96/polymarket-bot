---
created: 2026-03-09T14:57:53.859Z
title: Monitor btc_drift directional calibration YES vs NO win rates
area: strategy
files:
  - src/strategies/btc_drift.py
  - src/execution/live.py
---

## Problem

btc_drift live data (34 settled bets as of 2026-03-09) shows a significant directional
asymmetry that suggests the model is overconfident on up-drift (BUY YES) signals:

- BUY YES: 5/14 wins = **35.7% win rate** (model predicts ~57%)
- BUY NO:  11/20 wins = **55.0% win rate** (model predicts ~57%)

By price bucket on clean 35-65¢ bets (20 total):
- 35-45¢: 71.4% win rate — model *underconfident* here (good)
- 45-55¢: 28.6% win rate — model badly overconfident ⚠️
- 55-65¢: 33.3% win rate — model overconfident ⚠️

Hypothesis: BUY YES signals at 45-65¢ fire when BTC is mid-surge. By the time the
order places, the move has peaked and the market is mean-reverting. HFTs have already
priced the drift in. BUY NO signals (down-drift) at similar prices may be catching
genuine overshoots, hence higher win rate.

Note: 14 of 34 historical bets (41%) were contaminated by the execution-time price
guard bug (now fixed: 3c8baa9). The clean-data Brier is 0.2562 on 20 bets.

## Solution

**Do NOT change any thresholds yet.** 20 clean bets is insufficient sample.

After 30 more clean bets (35-65¢ with execution guard active), re-run this analysis:
```python
# Run from project root:
source venv/bin/activate && python3 -c "
import sqlite3
conn = sqlite3.connect('data/polybot.db')
# Query bets after 2026-03-09 09:51 CDT (new guard active)
# Split by side (yes/no) and price bucket
# If YES win rate < 40% at 30 clean bets → recalibrate
"
```

If YES-side win rate remains < 40% after 30 clean bets:
1. Consider raising `min_drift_pct` for BUY YES signals only (directional asymmetry)
2. Or add a `max_yes_price_for_buy` filter (don't buy YES when market > 50¢)
3. Or investigate whether the BTC reference price window needs extending

Read PRINCIPLES.md before any threshold change.
