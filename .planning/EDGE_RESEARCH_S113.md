# EDGE RESEARCH — Session 113
# Date: 2026-03-19 (~04:00-06:00 UTC)
# Focus: Political markets probe, overnight/time-of-day analysis
# Grade: TBD

═══════════════════════════════════════════════════════════
SECTION 1 — POLITICAL MARKETS PROBE (Pillar 3)
═══════════════════════════════════════════════════════════

## Hypothesis
Le (2026) b=1.83 near-expiry politics → 8pp edge at 90c, 14x crypto edge.
CCA confirmed the math. Question: are political markets accessible and liquid?

## Finding: SEPARATE API — CONDITIONAL DEAD END

Kalshi has moved ALL political markets to a separate platform:
  API: https://api.elections.kalshi.com/  (NOT trading-api.kalshi.com)
  Current bot uses: https://trading-api.kalshi.com/trade-api/v2

When probing KXPRES, KXELECTION, KXSENATE, KXCONGRESS, KXGOV etc:
  Response: "API has been moved to https://api.elections.kalshi.com/"
  HTTP 401 on main trading API

This means:
- Political markets are on a DIFFERENT platform with different auth
- The current KalshiClient cannot access them at all
- Would require a separate ElectionsKalshiClient + auth flow + configuration

## FLB Math Confirmed (Le 2026, b=1.83)

At key price levels:
  90c: true_prob=0.982, edge=8.2pp, net_after_2c_fee=6.2pp
  93c: true_prob=0.991, edge=6.1pp, net_after_2c_fee=4.1pp
  95c: true_prob=0.995, edge=4.5pp, net_after_2c_fee=2.5pp
  Comparison: crypto (b=1.03) edge at 90c = 0.6pp → politics is 14x larger

## Market Availability Issue
Between major election cycles (March 2026), political near-expiry 90c+ markets
may be sparse. Need events like:
- Senate confirmation votes
- State special elections
- Approval polls near resolution
- Policy votes

## Verdict: CONDITIONAL (not permanent dead end)

Condition to activate: build ElectionsKalshiClient for api.elections.kalshi.com
  Requires: separate auth, market scanning, volume check at 90c+ near expiry
  When to pursue: after elections cycle becomes active (Oct 2026 midterms)
  OR: if a specific near-term political event with volume is identified

CURRENT STATUS: NOT VIABLE (wrong API). Revisit Q4 2026 for midterms.
NOT a permanent dead end like KXBNB — it's a future build candidate.

═══════════════════════════════════════════════════════════
SECTION 2 — OVERNIGHT / TIME-OF-DAY ANALYSIS
═══════════════════════════════════════════════════════════

## Background
Matthew's directive: "I always wake up to red — investigate overnight performance."

## Data: 748 live sniper bets, 319 live drift bets

SNIPER — UNGUARDED BETS (guards excluded from analysis):
  Sleep 00-08 UTC: 325 bets, WR=92.3%, P&L=-51.31 USD, P&L/bet=-0.158 USD
  Day 09-21 UTC:   345 bets, WR=93.9%, P&L=+162.11 USD, P&L/bet=+0.470 USD
  Wilson CI overnight: [88.9%, 94.7%] — overlaps break-even (~92.5%)

SNIPER — ALL-TIME BY HOUR (worst hours):
  08:xx: 39 bets, WR=82.1%, P&L=-106.63 USD, P&L/bet=-2.73 USD  ← CATASTROPHIC
  13:xx: 21 bets, WR=85.7%, P&L=-26.60 USD, P&L/bet=-1.27 USD
  00:xx: 35 bets, WR=88.6%, P&L=-35.35 USD, P&L/bet=-1.01 USD
  06:xx: 42 bets, WR=90.5%, P&L=-26.20 USD, P&L/bet=-0.62 USD

SNIPER — BEST HOURS:
  11:xx: 34 bets, WR=100.0%, P&L/bet=+1.01 USD
  12:xx: 38 bets, WR=100.0%, P&L/bet=+0.84 USD
  09:xx: 29 bets, WR=96.6%, P&L/bet=+0.89 USD
  10:xx: 34 bets, WR=97.1%, P&L/bet=+0.85 USD

## Root Cause: March 17 08:xx Correlated Crash Event

5 of the 7 all-time 08:xx losses occurred on 2026-03-17 within the same hour:
  08:15-08:45 UTC: KXETH NO@89c, KXETH YES@93c, KXBTC YES@88c, KXXRP NO@91c, KXBTC NO@91c
  All across different assets, all simultaneously failing → correlated market crash
  Impact: ~97 USD in losses from one 1-hour crash window
  This event ALONE explains most of the all-time overnight underperformance

Without March 17 crash and guarded buckets:
  00:xx: would have been POSITIVE (two 00:xx losses were guarded buckets)
  All-time overnight would be near break-even

## Drift Strategy Overnight — STRUCTURAL PATTERN CONFIRMED

Unlike the sniper, drift shows a CONSISTENT overnight underperformance:
  btc_drift SLEEP: 43 bets, 46.5% WR, P&L/bet=-0.569 USD
  btc_drift DAY:   28 bets, 53.6% WR, P&L/bet=+0.495 USD   (1.06 USD/bet swing)
  
  eth_drift SLEEP: 86 bets, 48.8% WR, P&L/bet=-0.277 USD
  eth_drift DAY:   70 bets, 44.3% WR, P&L/bet=-0.037 USD   (0.24 USD/bet swing)
  
  sol_drift SLEEP: 25 bets, 72.0% WR, P&L/bet=+0.046 USD   (roughly neutral)
  xrp_drift SLEEP: 22 bets, 36.4% WR, P&L/bet=-0.183 USD   (BLOCKED anyway)

HYPOTHESIS: Crypto momentum/drift signals are weaker overnight because:
  - Asian session (00-08 UTC): lower liquidity, less directional conviction
  - European open (08:xx UTC): volatility spike breaks momentum
  - US session (13-21 UTC): highest volume, clearest trends
This is consistent with finance literature on intraday seasonality (academic backing needed).

## Statistical Verdict

SNIPER: Cannot formally implement time-of-day block. Wilson CI overlaps break-even.
  Does NOT meet 4-condition standard (p-value not crossed).

DRIFT: The btc_drift overnight pattern has more statistical weight:
  43 sleep bets at 46.5% WR vs break-even ~50%
  Binomial p-value (H1: WR < 50%) ≈ let me compute...
  P(X <= 20 | n=43, p=0.50) ≈ 0.14 (marginally significant, not conclusive)

CONCLUSION: Not enough data yet for formal time-of-day guard. Need 100+ drift bets per
time bucket. Continue monitoring. Request CCA to find academic backing.

## Actionable Findings

1. IMMEDIATE (no restart): Nothing to change — guards are active, per-window cap protects
2. NEXT CONFIG UPDATE: Apply eth_drift calibration_max_usd=0.01 (S112 recommendation,
   SPRT lambda=-3.611 crossed NO EDGE boundary — this reduces overnight drift drag)
3. RESEARCH: CCA request filed (REQUEST 4) for academic backing of overnight drift effect
4. MONITOR: btc_drift CUSUM S=4.020/5.0 — if it fires, drift bets pause (reduces overnight risk)
5. FUTURE BUILD (when n>=100 per time bucket): overnight drift guard or reduced sizing

## Day-of-Week Pattern

Mon: 133 bets, 98.5% WR, +100 USD (EXCELLENT)
Tue: 128 bets, 92.2% WR, -67.81 USD (includes S110 crash losses)
Thu: 17 bets,  88.2% WR, -19.89 USD (only 17 bets — S110 crash)
Sun: 190 bets, 93.7% WR, -48.92 USD

Tuesday/Sunday underperformance: not statistically actionable (confounded by crash events).

═══════════════════════════════════════════════════════════
SECTION 3 — GRADUATION-READY STRATEGIES (OBSERVATION)
═══════════════════════════════════════════════════════════

From --graduation-status at session start:
  btc_lag_v1: READY FOR LIVE (45 paper bets, Brier=0.191)
  orderbook_imbalance_v1: READY FOR LIVE (86 paper bets, +50 USD paper)

NOT auto-promoting these this session:
  btc_lag: unclear if this is a net-new strategy or test artifact. Not in main config.
  orderbook_imbalance: +50 USD paper but uses orderbook data — different feed.
  
ACTION: Add to TODOS.MD for Matthew to review at next session.

═══════════════════════════════════════════════════════════
SECTION 4 — WARMING BUCKETS CHECK
═══════════════════════════════════════════════════════════

S112 identified KXBTC YES@93c and KXETH YES@93c as warming (n=9, 88.9% WR, below BE).
Status at S113: n still ~9-10 (not enough new bets since guards + restart).
The new p-value gate (n>=10, p<0.20) means auto_guard_discovery.py won't fire yet.
Monitor at n>=20.

