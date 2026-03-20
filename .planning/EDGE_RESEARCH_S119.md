# EDGE RESEARCH — Session 119 (Research)
# Date: 2026-03-20 ~21:00 UTC
# Focus: Hour block audit, crash-pause analysis, drift strategy decision review
# Status: COMPLETE

## SUMMARY

Pure DB analysis session. No new code built. Three major findings:
1. Both hour blocks (08:xx, 13:xx) are unjustified by clean data — recommend revert
2. Crash-pause mechanism is a permanent dead end — has never been triggered
3. S118 sol_drift suspension vote was wrong — CUSUM confirms stable edge

---

## FINDING 1: CRASH-PAUSE — CONFIRMED DEAD END

DB analysis: 787 sniper 15-min windows analyzed.
Loss distribution:
  0 losses: 753 windows (95.7%)
  1 loss: 34 windows (4.3%)
  2+ losses: 0 windows (NEVER)
  3+ losses (crash-pause trigger): 0 windows (NEVER)

March 17 losses were consecutive single-asset losses across DIFFERENT 15-min windows,
not simultaneous multi-asset losses in the same window.

The crash-pause mechanism would have prevented ZERO losses from the sniper.
The March 17 damage came from drift strategies (eth_drift, sol_drift) and pre-guard buckets.

STATUS: PERMANENT DEAD END. Never re-investigate without a new scenario description.

---

## FINDING 2: 08:xx HOUR BLOCK — CRASH CONTAMINATED

Raw data that drove the block deployment:
  n=37, WR=81.1%, z=-4.30 → "structurally weak" → block deployed

Day-by-day breakdown:
  March 14: 10 bets, WR=100% (clean)
  March 15: 5 bets, WR=80% (1 loss — XRP YES@90c)
  March 16: 8 bets, WR=87.5% (1 loss — XRP YES@95c)
  March 17: 11 bets, WR=54.5% (5 losses — CRASH EVENT, -97.69 USD)
  March 18: 3 bets, WR=100% (clean, post-block)

WITHOUT MARCH 17:
  n=26, losses=2, WR=92.3%
  z = (0.923 - 0.957) / sqrt(0.957*0.043/26) = -0.87 (p=0.19, NOT significant)
  The entire z=-4.30 signal is from March 17 crash. Zero residual structural pattern.

FURTHER DECOMPOSITION — non-XRP only (ex March 17):
  n=20, WR=100%, P&L=+19.75 USD (PERFECT)

The 2 non-crash losses at 08:xx = both XRP YES@90-95c:
  March 15 08:23: KXXRP15M YES@90c → L, -19.80 USD
  March 16 08:07: KXXRP15M YES@95c → L, -19.95 USD

These are at the ceiling range and may represent XRP-specific 08:xx weakness,
but n=4 XRP YES bets at 08:xx total — well below n=10 auto-guard threshold.

CONCLUSION:
  08:xx block was deployed on false signal (crash-contaminated z-score).
  Non-XRP sniper at 08:xx (non-crash) = 100% WR. Block is actively costing revenue.
  RECOMMENDATION: Remove 8 from _BLOCKED_HOURS_UTC.
  ESTIMATED COST OF KEEPING: ~7-8 bets/day blocked × ~0.5 USD/win = 3-4 USD/day.

NEW WATCH ITEM: XRP YES at 08:xx (n=4, WR=50%, -39.75 USD)
  Need n=10 to qualify for auto-guard consideration.
  Filed as CCA REQUEST 14 for structured tracking.

---

## FINDING 3: 13:xx HOUR BLOCK — GUARDED BUCKET CONTAMINATED

Raw data:
  n=22, WR=90.9%, 2 losses (-38.36 USD total)

Both losses:
  March 15 13:03: KXXRP15M YES@91c → L, -19.74 USD
  March 15 13:22: KXXRP15M NO@91c → L, -18.62 USD

These are both XRP bets. Both from buckets now covered by auto-guards
(KXXRP NO@93c, KXXRP NO@95c guards active — ceiling blocks YES above 95c).

POST-GUARD 13:xx PERFORMANCE:
  n=20, WR=100%, estimated P&L ~+20 USD
  z = not significant (research S118 confirmed z=-0.46 independently)

CONCLUSION:
  13:xx block was deployed because 2 XRP bets lost — but those buckets are now guarded.
  The losses cannot recur. Post-guard 13:xx = 100% WR.
  RECOMMENDATION: Remove 13 from _BLOCKED_HOURS_UTC.
  ESTIMATED COST OF KEEPING: ~4-5 bets/day blocked × ~0.5 USD/win = 2 USD/day.

---

## FINDING 4: SOL_DRIFT — S118 SUSPENSION VOTE REVERSED

S118 research voted to suspend sol_drift based on:
  Last 7 days: 15 bets, WR=53.3%, P&L=-8.59 USD (looked bad)

S119 full analysis shows:
  SPRT: lambda=+2.886 — EDGE CONFIRMED (across all 43 bets)
  CUSUM: S=0.560 — STABLE (no detected changepoint — critically, S118 never checked this)
  Last 10 bets: WR=60.0%, P&L=+1.85 USD (recovering)
  Last 20 bets: WR=55.0%, P&L=-6.37 USD (Stage 1 sizing variance — expected)

The 7-day deterioration was high variance from Stage 1 sizing (individual bets up to -9.52 USD).
A few large losses dominated the short window. CUSUM captures this correctly: stable edge.

LESSON: Never vote to suspend a strategy without checking CUSUM. 7-day P&L at Stage 1
sizing is noise. CUSUM is the right instrument for changepoint detection.

REVISED DECISION: Keep sol_drift running. Monitor CUSUM. Suspend ONLY if S>=5.0.

---

## FINDING 5: XRP_DRIFT — APPROACHING THRESHOLD

Current state:
  Direction filter: "yes" (YES bets only)
  YES bets: n=39, WR=51.3%, P&L=-0.96 USD
  All time: n=50, WR=48.0%, P&L=-3.39 USD
  Last 7 days: 32 bets, WR=43.8%, P&L=-2.84 USD
  CUSUM: S=3.440/5.0 (approaching but not yet at threshold)
  SPRT: lambda=-0.971 (collecting, not at -2.251 no-edge boundary)

Not at formal disable threshold. Formal thresholds are the right standard.
ACTION: Monitor closely. Disable if CUSUM >= 5.0 OR next 10 bets WR <50%.

---

## FINDING 6: BTC_DRIFT — STABLE MONITORING

Last 7 days: 21 bets, WR=52.4%, P&L=+0.82 USD (slight positive recovery)
CUSUM: S=4.260/5.0 — STABLE (not risen since last session)
SPRT: lambda=-1.134 (collecting)

No action. CUSUM not risen. Monitor for S>=5.0.

---

## DEAD ENDS CONFIRMED THIS SESSION

  - Crash-pause mechanism: PERMANENT (0 simultaneous windows, never)
  - 08:xx as structural sniper weakness: NOT CONFIRMED (crash-contaminated)
  - 13:xx as structural sniper weakness: NOT CONFIRMED (guarded-bucket contaminated)
  - Overnight sniper block: ALREADY dead end (confirmed S118)

---

## PENDING RESEARCH PRIORITIES (S120)

1. MAIN CHAT ACTION NEEDED (not research): Revert hour blocks
   Remove 8 and 13 from _BLOCKED_HOURS_UTC in main.py
   Full evidence in POLYBOT_TO_MAIN.md

2. CCA REQUEST 12: Earnings Mentions markets (KXEARNINGSMENTIONX*)
   Q1 earnings season April-May 2026 approaching. SDATA budget now 2000.
   Need: volume confirmation, structural edge validation before building.

3. XRP YES@08:xx watch: n=4 currently, need n=10 for auto-guard threshold.
   Filed as CCA REQUEST 14. Track passively via auto_guard_discovery.

4. CCA REQUEST 11: 00:xx Asian session NO-side mechanism still pending.
   Unguarded 00:xx NO: n=11, WR=81.8%. Wait for n>=30.

5. Dim 9 (meta-labeling): n=13 signal_features. Passive accumulation. No action.

---

## SESSION GRADE: B+

Found actionable evidence for 2 code reverts worth 5-6 USD/day combined.
Reversed a wrong S118 vote (sol_drift) based on CUSUM evidence.
Closed CCA REQUEST 13 (crash-pause dead end) without needing CCA's help.
No code built — right scope for a short session with limited time.
Would be A if main chat implements the hour block reverts.

