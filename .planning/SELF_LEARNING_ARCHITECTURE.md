# Self-Learning Architecture — Kalshi Bot
# Authored: 2026-03-24 | Matthew standing directive (S129)
# "How do you take its self-learning capabilities and analytical tools
#  to engage in a more advanced self-learning tool for yourself for both
#  active and passive use to generate a smarter Kalshi bot?"

## Why This Exists

The bot's existing self-learning (Bayesian posterior, auto-guards, CUSUM in bet_analytics.py)
operated as isolated components. This architecture unifies them into one pipeline that:

1. Analyzes every bet at the bucket level (asset × price × side)
2. Detects systematic mispricing via calibration curves
3. Computes optimal Kelly sizing per bucket (not one global estimate)
4. Persists findings across sessions so each session builds on the last
5. Generates ranked actionable proposals automatically

## The Three-Layer Self-Learning Stack

### Layer 1: Per-Cycle Passive Learning (every 3rd monitoring cycle)
**Tool:** scripts/analysis/kalshi_self_learning.py --brief
**What it does:**
- Reads all settled live trades from polybot.db (read-only)
- Computes Wilson CI + CUSUM for every (asset × price × side) bucket
- Flags guard candidates (WR < BE, p < 0.20, n >= 10)
- Flags CUSUM-triggered degradation (S >= 5.0)
- Saves bucket trajectories to data/learning_state.json (cross-session persistence)

**Why this is better than bet_analytics.py alone:**
- bet_analytics.py runs SPRT/CUSUM per strategy (btc_drift, sol_drift...)
- Self-learning runs at bucket level: KXBTC NO@95c is a separate bucket from KXBTC NO@94c
- 256 buckets analyzed vs ~5 strategies. Much more granular signal detection.

### Layer 2: Active Session Analysis (manual / when directed)
**Tool:** scripts/analysis/kalshi_self_learning.py (full mode)
**What it does (adds to passive):**
- CalibrationBias analysis: detects systematic mispricing zones per price level
  - Example finding: 50-60% bucket is overpriced by 5% (market says 55%, true is ~50%)
  - Implication: drift strategies at near-50c prices face systematic headwind
- DynamicKelly recommendations: per-bucket optimal Kelly fraction
  - For confirmed-edge buckets (Wilson CI above break-even), computes half-Kelly
  - Compares to current flat 500c/bet to identify over/under-sizing
- Full bucket report with CI bounds, CUSUM state, p-values
- LEARNING_REPORT.md saved to reports/ directory

### Layer 3: Cross-Session Learning State
**File:** data/learning_state.json
**What it persists:**
- Per-bucket history: n, win_rate, pnl_usd, cusum_s, wilson bounds (last 50 observations)
- Guard candidates observed across sessions with timestamps
- Session summaries (count, proposals, calibration state)

**Why this matters:**
- CUSUM doesn't reset each session — degradation accumulates properly
- A bucket that's "p=0.22" in session 128 and "p=0.18" in session 129 triggers a guard
- Warming buckets get proper multi-session trend analysis

## Analytical Tools and Their Roles

### scripts/analysis/kalshi_self_learning.py (MASTER)
Created: 2026-03-24. The new unified orchestrator.
Inputs: polybot.db (read-only)
Outputs: console report + data/learning_state.json + reports/learning_report_*.md

### scripts/analysis/strategy_health_scorer.py (FIXED 2026-03-24)
Role: Strategy-level health (expiry_sniper, btc_drift, etc.)
Key fix applied: win condition was result=="yes" → now result==side (handles NO-side bets)
Key fix applied: pnl used pnl_cents → now uses normalized pnl_usd field
Current result: expiry_sniper = HEALTHY (96% WR, +72 USD)

### scripts/analysis/calibration_bias.py (FROM CCA, UNCHANGED)
Role: Detects systematic price zone mispricing via binned calibration curves
Key finding (2026-03-24): 50-60% bucket is overpriced by 5% (confidence=0.86, n=126)
Implication: Drift strategies operate in the mispriced zone — structural headwind confirmed

### scripts/analysis/dynamic_kelly.py (FROM CCA, UNCHANGED)
Role: Per-bucket Kelly fraction computation with Bayesian updating + time decay
Current use: Advisory only — flags buckets where half-Kelly differs >50% from flat 500c

### scripts/analysis/trade_reflector.py (FROM CCA, FIXED 2026-03-24)
Role: Pattern detection → proposals (win rate drift, streak analysis, time-of-day)
Key fix applied: win condition, streak analysis booleans, side column in queries

### scripts/analysis/trading_analysis_runner.py (FROM CCA, FIXED 2026-03-24)
Role: Full analysis pipeline runner + KALSHI_INTEL.md integration
Key fix applied: win condition, side column in SELECT

## Monitoring Loop Integration

Every 3rd monitoring cycle (cycles 3, 6, 9, 12...), add to the standard cycle:

```bash
cd /Users/matthewshields/Projects/polymarket-bot && \
source venv/bin/activate && \
python3 scripts/analysis/kalshi_self_learning.py --db data/polybot.db --brief
```

Output interpretation:
- "0 CRITICAL, 0 HIGH" = bot operating cleanly in all buckets
- "1 HIGH: Strategy PAUSE: X" = strategy X degrading (if not already disabled)
- "1 CRITICAL: Guard candidate: KXETH YES@94c" = add guard immediately

Full analysis (run when directed or when any HIGH/CRITICAL appears):
```bash
python3 scripts/analysis/kalshi_self_learning.py --db data/polybot.db --save
```

## Key Findings from First Run (2026-03-24)

1. Sniper clean zone confirmed: All 90-95c YES + 90-94c NO buckets show WR > BE. No active guard candidates.

2. Disabled strategy remnants: eth_drift, sol_drift, btc_drift, xrp_drift all show MONITOR/PAUSE — correctly flagging their historical performance. Already disabled.

3. Calibration finding: 50-60% price zone is systematically overpriced by 5%. This is the exact zone where drift strategies bet. This is structural confirmation that near-50c crypto direction markets are NOT efficiently priced in our favor — the market overestimates certainty.

4. KXXRP yes@98c approaching guard threshold: n=12, WR=91.7% vs BE=98%, PnL=-17.69 USD, p=0.215. One more bad cycle brings this to guard range. However KXXRP is already globally blocked (IL-33) so this is moot.

5. No Kelly oversizing detected: Current flat 500c/bet is conservative enough that no confirmed-edge bucket shows dramatic undersizing.

## How This Grows Over Time

Sessions 1-10: Bucket statistics are noisy (n < 20 per bucket)
Sessions 10-30: Wilson CIs narrow, clear edge/loser separation emerges
Sessions 30+: Calibration bias stabilizes, Kelly recommendations become reliable
Sessions 50+: Cross-session trends in learning_state.json reveal seasonal patterns

The passive layer (--brief every 3rd cycle) runs continuously, building the history.
The active layer (full report) is called to interpret findings and drive decisions.
CCA can read learning_state.json to provide deeper research when patterns emerge.

## Files Owned by This System

scripts/analysis/kalshi_self_learning.py    — Master orchestrator (new)
scripts/analysis/strategy_health_scorer.py  — Fixed for NO-side win condition
scripts/analysis/trade_reflector.py         — Fixed for NO-side win condition
scripts/analysis/trading_analysis_runner.py — Fixed for NO-side win condition
scripts/analysis/calibration_bias.py        — From CCA, unchanged
scripts/analysis/dynamic_kelly.py           — From CCA, unchanged
scripts/analysis/metric_config.py           — From CCA, config reader
scripts/analysis/metric_defaults.json       — From CCA, defaults
data/learning_state.json                    — Cross-session persistence (auto-updated)
reports/learning_report_*.md                — Timestamped analysis reports

## What This Does NOT Do (by design)

- Does NOT execute trades or change parameters automatically
- Does NOT modify auto_guards.json directly (proposals require human review)
- Does NOT disable strategies (that requires Matthew approval)
- Does NOT use Kelly recommendations directly (advisory, requires 30+ bets + review)

Every output is advisory. The bot still needs a human in the loop for structural changes.
The learning is about FINDING the signal — acting on it remains Matthew's decision.
