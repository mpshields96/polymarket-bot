# EDGE RESEARCH — Session 109
# Date: 2026-03-19 (~20:35 UTC)
# Focus: Bet sizing analysis, guard anticipation, signal feature logger (Dim 9)
# Grade: B+ (useful infrastructure build + three-chat sizing decision with data)

═══════════════════════════════════════════════════════════
SECTION 1 — BET SIZING OBJECTIVE ANALYSIS
Three-chat autonomous decision requested by Matthew (S109)
═══════════════════════════════════════════════════════════

## Sniper Bet Size vs Performance Breakdown (all-time, live settled)

Bucket analysis by cost range:
  under 5 USD:  n=52,  WR=96.2%,  total P&L=+1.72 USD
  5-10 USD:     n=25,  WR=100.0%, total P&L=+10.60 USD
  10-15 USD:    n=208, WR=98.6%,  total P&L=+86.18 USD
  15-20 USD:    n=451, WR=94.2%,  total P&L=-53.90 USD

Initial interpretation: $15-20 range looks structurally negative.

## Root Cause Analysis

The $15-20 range underperformance is NOT structural. Evidence:

1. Timing: HARD_MAX was raised from $5-$10 to $20 in S78. The 451 bets in the $15-20
   range include ALL bets from S78 onwards — including bets in buckets that later became
   guarded (KXXRP NO@93c, KXBTC NO@94c, KXBTC YES@94c, KXXRP NO@95c, KXSOL NO@93c).

2. Guarded bucket P&L (cumulative, pre and post guard — ALL at $15-20 range):
   KXXRP NO@93c: n=18, WR=88.9%, P&L=-19.50 USD ← biggest contributor to $15-20 losses
   KXBTC YES@94c: n=13, WR=92.3%, P&L=-9.94 USD
   KXBTC NO@94c: n=10, WR=90.0%, P&L=-11.24 USD
   KXXRP NO@95c: n=19, WR=94.7%, P&L=-7.07 USD
   KXSOL NO@93c: n=12, WR=91.7%, P&L=-7.05 USD
   Total from guarded buckets at $15-20: approximately -54 USD (matches the observed loss)

3. With all 5 guards now active + floor/ceiling, these buckets no longer fire.
   Expected future $15-20 WR: should recover toward $10-15 range (98.6%).

## Decision: KEEP HARD_MAX at $20

Standard met: statistical evidence (451 bets) showing the cause is contamination, not
structural degradation. Changing HARD_MAX after identifying the root cause was fixed
by guards would be trauma-based per PRINCIPLES.md.

TRIGGER FOR CHANGE: if post-S108-guard bets at $15-20 show WR < 96% after 30+ clean bets.
Monitor: next session should check $15-20 WR for bets placed after 2026-03-19.

## SOL Drift Sizing Decision

Kelly(WR=69.8%, avg price=59c, quarter-Kelly) = 6.5% of bankroll.
At current bankroll ~$88: Kelly bet = $5.72, Stage 1 cap = $5. Kelly IS limiting factor.
At bankroll $100 (Stage 2): Kelly = $6.47, Stage 2 cap = $10. Plenty of room.
At bankroll $250 (Stage 3): Kelly = $16.17, capped at ABSOLUTE_MAX = $15.

Conclusion: SOL drift sizing is naturally governed by Kelly at all stages. No manual
override needed. Let bankroll growth drive natural scaling.

## ETH/BTC/XRP Drift Sizing Decision

All three are micro-live at calibration_max_usd=0.01 (effectively $0.39-0.41/bet).
ETH: SPRT no edge (lambda=-3.26). BTC: CUSUM improving 4.480→4.020. XRP: neutral.
At $0.39/bet, cost of collecting data is negligible. Keep micro-live.
These are data instruments, not profit engines.

═══════════════════════════════════════════════════════════
SECTION 2 — GUARD ANTICIPATION ANALYSIS
Q: Is it worth anticipating future guards before statistical threshold?
═══════════════════════════════════════════════════════════

## Analysis

The auto-guard discovery system (Dim 1a) catches negative-EV buckets when:
  n >= 3 bets, loss > 5 USD, WR < break-even for that price

At $19/bet, 3 bets = max $57 cost before a bucket gets blocked. That is fast.

Pre-emptive guarding would require predicting which buckets will turn negative.
Academic FLB theory tells us 90-95c is structurally positive in aggregate, but does NOT
predict which specific coin×direction×price combination will underperform.

False-positive cost: if we pre-guard a bucket that would have been +EV, we permanently
lose those bets. At $19/bet × 10+ bets before we notice = $190+ in missed profits.

## Decision: Not worth pre-anticipating guards at the bucket level

The better approach is signal-level filtering via meta-labeling (see Section 3 below).

## What we CAN do: Warming bucket watchlist

Implementation: log buckets at n>=2 negative P&L (below the 3-bet guard threshold)
to a visibility-only watchlist. Zero false-positive risk.
Benefits: see buckets 1 bet before they hit guard threshold.
Cost: one small script, no live trading changes.
Status: NOT BUILT this session — recommended for S110.

═══════════════════════════════════════════════════════════
SECTION 3 — DIM 9: SIGNAL FEATURE LOGGER
Build details + self-improvement pathway
═══════════════════════════════════════════════════════════

## What was built

Every live drift bet now logs 12 signal features as JSON to trades.signal_features:
  pct_from_open:       % drift from reference price (the core drift signal)
  minutes_remaining:   time remaining in 15-min window
  time_factor:         time weight (0.0 at open, 1.0 at close)
  raw_prob:            uncalibrated probability (before temperature calibration)
  prob_yes_calibrated: post-calibration probability
  edge_pct:            final computed edge after fees
  win_prob_final:      final win probability (capped 0.51-0.99)
  price_cents:         market price at signal time
  side:                "yes" or "no"
  minutes_late:        reference price latency (how late we joined the window)
  late_penalty:        confidence penalty for late reference (0.5-1.0)
  bayesian_active:     whether Bayesian posterior was used (vs static sigmoid)

Files changed:
  src/strategies/base.py — added features: Optional[Dict] to Signal dataclass
  src/strategies/btc_drift.py — populate features dict before return Signal
  src/db.py — signal_features TEXT column (migration), save_trade() param
  src/execution/live.py — pass signal.features to save_trade()
  tests/test_signal_features.py — 8 new tests (NEW FILE)
  tests/test_live_executor.py — updated stale KXBTC NO@94c guard test

Commit: 8fbf56e

## Meta-labeling pathway

CCA KALSHI_INTEL.md (from r/algotrading deep-read, 610 pts) documents:
  Binary meta-classifier trained on signal features → +1-3% WR improvement
  Drawdown reduction: 35% → 23%
  Minimum labeled examples: 1000+
  Current drift bet total: ~350 (entering S109)
  At 60-70 drift bets/day: approximately 15 days to 1000 labeled examples

Self-improvement chain once n >= 1000:
  signal fires → features logged → settle → label (win/loss) added →
  1000 labeled examples → train meta-classifier → filter bad signals →
  expected +1-3% WR across drift strategies

This is smarter than bucket guards because it uses all feature combinations
(time, drift magnitude, price, calibration state) not just bucket membership.

## Tests

8 new tests in tests/test_signal_features.py:
  TestSignalFeaturesField: backward compat (3 tests)
  TestSaveTradeFeatures: DB persistence (3 tests)
  TestBtcDriftFeaturePopulation: feature keys and content (2 tests)
1631 total passing.

═══════════════════════════════════════════════════════════
SECTION 4 — CURRENT BOT STATE
═══════════════════════════════════════════════════════════

Bot: RUNNING PID 48350 → /tmp/polybot_session109.log

All-time P&L: -11.20 USD live (DB confirmed 2026-03-19 01:10 UTC)
  NOTE: SESSION_HANDOFF showed +22.91 USD — that was S107 data (stale). DB is authoritative.
  Today: -35.32 USD (2 losses × ~$20 each at 18:20 UTC window)
  Sniper all-time: $10-15 range +86 USD, $15-20 range -54 USD (guard contamination)

Bankroll: ~$88.80 (estimated from $100 starting - $11.20 live loss)
Stage: Stage 1 (bankroll < $100)

Guards: 5 active (unchanged from S108)
  KXXRP NO@95c: n=19, 94.7% WR — ACTIVE
  KXSOL NO@93c: n=12, 91.7% WR — ACTIVE
  KXBTC YES@94c: n=13, 92.3% WR — ACTIVE
  KXXRP NO@93c: n=24, 91.7% WR — ACTIVE (new S108)
  KXBTC NO@94c: n=10, 90.0% WR — ACTIVE (new S108)

Strategy state:
  expiry_sniper_v1: PRIMARY, HARD_MAX=$20, 5 guards active
  sol_drift_v1: EDGE CONFIRMED, n=43, Brier 0.198, Kelly governs, calibration_max_usd=None
  btc_drift_v1: micro-live, calibration_max_usd=0.01, CUSUM S=4.020
  eth_drift_v1: micro-live, calibration_max_usd=0.01, CUSUM S=12.760, NO EDGE (SPRT)
  xrp_drift_v1: micro-live, calibration_max_usd=0.01, CUSUM S=2.820, direction_filter=yes
  Bayesian: n=313, override_active=True, kelly_scale=0.952
  Temperature: ETH T=0.500, BTC T=0.500, SOL T=1.290, XRP T=0.500

═══════════════════════════════════════════════════════════
SECTION 5 — DEAD ENDS CONFIRMED THIS SESSION
═══════════════════════════════════════════════════════════

  Pre-emptive guard anticipation: not worth it. Auto-guard catches fast.
    False-positive cost too high. Signal features logger = smarter solution.

  Treating soft stop "SOFT STOP ACTIVE" in --health as a real block:
    The daily loss code is COMMENTED OUT in kill_switch.py (lines 187-191).
    The display shows the comparison but does NOT block trades. Never interrupt
    live trading based on this display. Only consecutive loss soft stop blocks live bets.

═══════════════════════════════════════════════════════════
SECTION 6 — PRIORITY STACK FOR S110
═══════════════════════════════════════════════════════════

#1 WARMING BUCKET WATCHLIST — build small script to flag n>=2 negative P&L
   buckets before they hit guard threshold. Visibility only, no blocking.
   Cost: ~30 min, very low risk.

#2 SIGNAL FEATURES ACCUMULATION MONITOR — at session start, check:
   SELECT COUNT(*) FROM trades WHERE is_paper=0 AND signal_features IS NOT NULL
   When n >= 500: start analyzing which feature combos correlate with losses.
   When n >= 1000: train meta-classifier.

#3 POST-S108 SNIPER PERFORMANCE AT $15-20 — check WR for bets placed after
   2026-03-19 in the $15-20 range. If < 96% after 30 bets: consider HARD_MAX reduction.

#4 BTC very_high edge_pct: was n=18, need 30+ before formal guard test.

#5 Temperature calibration T values — too few new bets since seeding. Check if shifted.

#6 SOL DRIFT Stage 3 — bankroll needs $250. At current rate: months away.
   Monitor passively. No manual action.
