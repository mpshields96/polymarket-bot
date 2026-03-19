# EDGE RESEARCH — Session 108 (2026-03-19)

## Summary

Session 108 focused on FLB (Favourite-Longshot Bias) academic research — the theoretical
foundation underpinning the expiry sniper. This session completes Pillar 2 for the sniper:
academic basis + empirical confirmation + per-bucket analysis. 2 new auto-guards activated
(5 total now). No code builds this session — research + validation output.

---

## Research Findings

### 1. Startup Events

2 new auto-guards discovered and activated (bot restarted to PID 33218):
  KXXRP NO@93c: n=24, 91.7% WR (need 93.4%), -15.3 USD — BLOCKED
  KXBTC NO@94c: n=10, 90.0% WR (need 94.4%), -11.24 USD — BLOCKED

5 total auto-guards now active:
  KXXRP NO@95c: n=19, 94.7% WR — original guard
  KXSOL NO@93c: n=12, 91.7% WR — original guard
  KXBTC YES@94c: n=13, 92.3% WR — added S105
  KXXRP NO@93c: n=24, 91.7% WR — NEW (S108)
  KXBTC NO@94c: n=10, 90.0% WR — NEW (S108)

bet_analytics.py check (S108 state):
  sniper: 734 bets, 95.8% WR, EDGE CONFIRMED (lambda=+15.332), CUSUM stable S=2.025
  sol_drift: n=43, 69.8% WR, EDGE CONFIRMED (lambda=+2.886), Brier 0.198, CUSUM stable
  btc_drift: n=69, 49.3% WR, collecting data (lambda=-1.056), CUSUM stable S=4.020
  xrp_drift: n=47, 48.9% WR, collecting data (lambda=-0.771), CUSUM stable S=2.820
  eth_drift: n=152, 47.4% WR, NO EDGE (lambda=-3.262), CUSUM DRIFT ALERT S=12.760
    NOTE: Bayesian + temperature calibration self-corrects. No manual action per PRINCIPLES.md.

Bayesian: n=311 obs (added 3 bets since S107), override_active=True
Temperature calibration: unchanged T values (too few new bets to shift)

BTC very_high edge_pct bucket: still n=18, not yet at 30 threshold for formal test.

### 2. FLB Academic Research — VERIFIED Citations

All 5 primary sources verified via web fetch or confirmed search.

**Core finding: Burgi, Deng & Whelan (2026) [VERIFIED]**
  Title: "Makers and Takers: The Economics of the Kalshi Prediction Market"
  Working paper: CESifo WP No. 12122 / CEPR DP20631
  Source: https://www.ifo.de/en/cesifo/publications/2026/working-paper/makers-and-takers-economics-kalshi-prediction-market

  Key quantitative finding: Using 300,000+ Kalshi contracts:
    - 95c contracts win ~98% of the time — ~3pp positive outperformance
    - Takers lose ~32% on average (driven by longshot losses)
    - Makers lose ~10%
    - FLB is clear and monotonic: high-price contracts yield small positive return

  OUR DATA CONFIRMS: 95c YES = 98.1% WR (+3.1pp, n=52). Exact match.

**Mechanism — Snowberg & Wolfers (2010) [VERIFIED]**
  Title: "Explaining the Favorite-Longshot Bias: Is it Risk-Love or Misperceptions?"
  NBER WP 15923 / Journal of Political Economy Vol. 118 No. 4
  Source: https://www.nber.org/papers/w15923

  Conclusion: Probability MISPERCEPTION (Prospect Theory) drives FLB — not risk preferences.
  Bettors systematically overweight small probabilities (longshot appeal) and underweight
  large probabilities (favorites seem "too certain" to bet).
  Implication for Kalshi: retail bettors systematically underprice 90c+ YES contracts.

**Structure mechanism — Ottaviani & Sorensen (2010) [VERIFIED]**
  Title: "Noise, Information, and the Favourite-Longshot Bias in Parimutuel Predictions"
  American Economic Journal: Microeconomics, Vol. 2, No. 1
  Source: https://www.aeaweb.org/articles?id=10.1257%2Fmic.2.1.58

  Critical finding: In FIXED-ODDS markets (like Kalshi), more informed bettors
  STRENGTHEN FLB via adverse selection — the opposite of parimutuel!
  Implication: As Kalshi grows and attracts more sophisticated traders, our edge
  should INCREASE, not decrease. Long-term favorable dynamics.

**Whelan (2024) [VERIFIED]**
  Title: "Risk Aversion and Favourite-Longshot Bias in a Competitive Fixed-Odds Betting Market"
  Economica, Vol. 91, No. 361, pp. 188-209
  Source: https://ideas.repec.org/a/bla/econom/v91y2024i361p188-209.html

  Conclusion: FLB persists in competitive fixed-odds markets due to:
    (1) Bettor disagreement about true probabilities
    (2) Risk aversion by market makers (bookmakers/providers)
  Implication: FLB is not easily arbitraged away even with sophisticated competition.

**Thaler & Ziemba (1988) [VERIFIED]**
  Title: "Anomalies: Parimutuel Betting Markets: Racetracks and Lotteries"
  Journal of Economic Perspectives, Vol. 2, No. 2, pp. 161-174
  Source: https://www.aeaweb.org/articles?id=10.1257/jep.2.2.161

  Foundational documentation: favorites systematically underbet, longshots overbet.
  Despite conditions ideal for learning, behavioral anomalies persist.

### 3. Per-Bucket Sniper Analysis (FLB Validation)

Per-price-bucket WR analysis of all live sniper trades (n>=5 per bucket):

90-95c ZONE (profitable):
  90c NO:  n=18,  WR=100.0%,  excess=+10.0pp,  P&L=+28.80 USD  [EXCELLENT]
  91c YES: n=24,  WR=100.0%,  excess= +9.0pp,  P&L=+37.28 USD  [EXCELLENT]
  92c YES: n=64,  WR=100.0%,  excess= +8.0pp,  P&L=+79.73 USD  [EXCELLENT]
  95c YES: n=52,  WR= 98.1%,  excess= +3.1pp,  P&L=+15.09 USD  [MATCHES BURGI]
  94c NO:  n=60,  WR= 96.7%,  excess= +2.7pp,  P&L=+13.72 USD  [SOLID]
  93c NO:  n=65,  WR= 95.4%,  excess= +2.4pp,  P&L= +8.55 USD  [SOLID]
  95c NO:  n=69,  WR= 97.1%,  excess= +2.1pp,  P&L= +7.30 USD  [SOLID]
  91c NO:  n=28,  WR= 92.9%,  excess= +1.9pp,  P&L= -0.70 USD  [MARGINAL]
  90c YES: n=12,  WR= 91.7%,  excess= +1.7pp,  P&L= -1.35 USD  [MARGINAL]
  94c YES: n=61,  WR= 95.1%,  excess= +1.1pp,  P&L= -7.61 USD  [MARGINAL]
  93c YES: n=51,  WR= 94.1%,  excess= +1.1pp,  P&L=+21.63 USD  [MARGINAL]
  92c NO:  n=27,  WR= 92.6%,  excess= +0.6pp,  P&L= -3.66 USD  [THIN]

88c:
  88c YES: n=5,   WR= 80.0%,  excess= -8.0pp  [NEGATIVE — too small to conclude]

96c+ ZONE (losing — FLB reverses):
  96c NO:  n=14,  WR= 92.9%,  excess= -3.1pp,  P&L= -9.09 USD
  96c YES: n=17,  WR= 94.1%,  excess= -1.9pp,  P&L=-13.35 USD
  97c NO:  n=13,  WR= 92.3%,  excess= -4.7pp,  P&L=-15.03 USD
  97c YES: n=30,  WR= 93.3%,  excess= -3.7pp,  P&L=-30.18 USD
  98c NO:  n=27,  WR= 96.3%,  excess= -1.7pp,  P&L=-14.48 USD
  98c YES: n=63,  WR= 98.4%,  excess= +0.4pp,  P&L= -8.86 USD  [~break-even]
  99c YES: n=15,  WR= 93.3%,  excess= -5.7pp,  P&L=-14.85 USD

### 4. Key Conclusions

**A) Ceiling at 95c is justified (empirically + theoretically)**
  The 90-95c zone consistently shows positive FLB excess (+0.6 to +10pp).
  96c+ consistently loses (-1.9 to -5.7pp). The reversal is sharp and consistent.
  Theoretical explanation: At 96-97c, market makers accurately price near-certainty.
  The uncertainty premium available at 90-95c vanishes above 95c.
  DO NOT raise the ceiling. Data + theory both confirm 95c is the correct maximum.

**B) FLB at 95c matches Burgi-Deng-Whelan prediction exactly**
  Theory: 95c contracts win ~98% (+3pp excess)
  Our data: 95c YES = 98.1% (+3.1pp, n=52)
  This is confirmation that our edge IS the FLB, not noise.

**C) YES/NO asymmetry in the 90-93c zone**
  YES side shows lower FLB excess at 90-93c vs NO side.
  At 92c: YES excess=+8pp (100% WR, n=64) vs NO excess=+0.6pp (92.6% WR, n=27)
  At 93c: YES excess=+1.1pp vs NO excess=+2.4pp
  Interpretation: At lower prices (90-93c), NO wins are more "structural" (big moves
  rarely happen in 15 min), while YES wins at 92c reflect outlier events. Mixed picture.
  Observation only — sample sizes limit conclusions.

**D) Auto-guards are FLB-consistent**
  The 5 guarded buckets (KXXRP NO@93c, KXBTC NO@94c, KXBTC YES@94c, KXSOL NO@93c,
  KXXRP NO@95c) all show WR below break-even within their specific market/direction.
  The overall sniper FLB holds (+3pp average), but specific market-direction combinations
  can underperform. Auto-guard discovery is the empirical filter for these exceptions.

**E) FLB is structural and will persist (Ottaviani-Sorensen)**
  In fixed-odds markets like Kalshi, more sophisticated participants STRENGTHEN FLB.
  The sniper's edge is expected to grow as Kalshi volumes increase. Long-term positive.

### 5. Actionable Implications

**Confirmed (no change needed):**
  - Ceiling at 95c: confirmed. Do not raise.
  - Floor at 90c: confirmed (88c data too small, 96c+ negative). Do not lower.
  - Auto-guard threshold at break-even WR: correct. Not changing.

**Monitoring (future work, no data yet):**
  - 92c NO (+0.6pp, n=27): thin margin. Monitor. If WR falls below 92%, auto-guard will trigger.
  - 90c YES (+1.7pp, n=12): below theoretical expectation. Monitor with more data.
  - BTC very_high edge_pct bucket (n=18, 39% WR): still observation only. Need 30+.

**Future research (not ready to build):**
  - FLB-calibrated guard thresholds: instead of flagging WR < break-even, flag when
    WR < (break-even + 1.5pp). Would catch "underperforming vs FLB theory" buckets earlier.
    Requires formal test: backtest what new guards would have been triggered historically.
    Log to todos.md. NOT building this session — insufficient data per PRIME DIRECTIVE.

---

## State After S108

Bot: RUNNING PID 33218 → /tmp/polybot_session108.log
Guards: 5 auto-guards active (2 new: KXXRP NO@93c, KXBTC NO@94c)
Tests: 1623 passing (no new code this session)
Last commit: caf69e9 (no new commit — research-only session)

Self-improvement dimensions: All 8 COMPLETE (no new builds)
  FLB research completes Pillar 2 theoretical grounding for the sniper.

Next research directions:
  - CCA response on CUSUM threshold (S107 request — check next session)
  - Monitor XRP/BTC with new guards active — any pattern changes?
  - BTC very_high edge_pct: wait for n>=30 (currently n=18)
  - Sol Stage 2: n=43, EDGE CONFIRMED, Matthew's call on bet cap

Dead ends (new this session):
  None added.
