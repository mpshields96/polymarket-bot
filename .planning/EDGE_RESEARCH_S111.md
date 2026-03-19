# EDGE RESEARCH — Session 111
# Date: 2026-03-19 (~02:30 UTC)
# Focus: CCA calibration research implementation, FLB weakening monitor, political markets investigation
# Grade: B+ (2 tools built, guard integrity confirmed, Pillar 3 lead validated with accurate data)

═══════════════════════════════════════════════════════════
SECTION 1 — CCA ACADEMIC DELIVERIES IMPLEMENTED
═══════════════════════════════════════════════════════════

## Le (2026) Calibration Formula — IMPLEMENTED

Source: Le (2026) arXiv:2602.19520 — 292M trades, 327K contracts (Kalshi + Polymarket)
Verified by CCA Session 111. Formula:
  true_prob = p^b / (p^b + (1-p)^b)
  where b = domain calibration slope

Domain slopes from Le (2026):
  Crypto 15-min:           b = 1.03  (near-perfectly calibrated)
  Finance:                 b = 1.10  (slight favorite underpricing)
  Politics 1+ week:        b = 1.31  (large mispricing)
  Politics near-expiry:    b = 1.83  (MASSIVE mispricing)
  Sports 1+ month:         b = 1.74  (large mispricing)
  Weather <48h:            b = 0.75  (favorites OVERPRICED — avoid)

Applied to sniper operating range (90-95c):
  90c crypto: true=90.6% (+0.6pp edge from calibration)
  90c politics near-expiry: true=98.2% (+8.2pp edge)
  95c crypto: true=95.4% (+0.4pp edge)
  95c politics near-expiry: true=99.5% (+4.5pp edge)

Key insight: The sniper's 95.8% WR vs ~93% break-even = ~2.8pp gross edge.
Only 0.3-0.5pp of that comes from calibration (crypto b=1.03).
The remaining ~2.5pp is structural FLB + liquidity premium near expiry.
This is GOOD: structural edge is harder to arbitrage away than calibration edge.

CCA correction: Their summary said "politics at 90c = 4pp edge". Actual formula = 8.2pp.
The formula was misrepresented in CCA's summary — exact math gives almost 2x more edge.

Built: calibration_adjusted_edge() in scripts/bet_analytics.py
Tests: 7 new tests in tests/test_bet_analytics.py (31 total in that file)
Calibration context section added to bet_analytics.py report output.

## FLB Weakening Monitor — BUILT

Source: Whelan (March 2026) VoxEU/CEPR column
"Some evidence of weakening favourite-longshot bias in 2025 Kalshi data vs earlier years."
This is a documented risk — not certain, but the signal exists.

Built: scripts/sniper_monthly_wr.py
  - Monthly WR tracking for sniper (grouped by calendar month)
  - Rolling 30-day window WR
  - Flag threshold: WR < 93% with n >= 30 bets
  - 15 tests in tests/test_sniper_monthly_wr.py

Current status: 2026-03 only month (739 bets, 95.8% WR). NO FLB WEAKENING SIGNAL.
Expected baseline: as data accumulates across months, this becomes the primary
FLB health monitor. Degradation below 93% sustained for 100+ bets = escalate.

## Multivariate Kelly — CCA DELIVERED ANSWER

CCA found no dedicated academic paper for correlated binary prediction market bets.
Standard portfolio theory (multivariate Kelly) applies via:
  f* = C^(-1) * (mu - r)
Practical recommendation: scale each Kelly fraction by 1/N for N simultaneous positions.
With 4 correlated crypto positions: scale by 0.25x each.
The bot's current Kelly sizing is already conservative (quarter-Kelly default).
No code change needed. Multivariate concern is addressed by existing conservative sizing.

═══════════════════════════════════════════════════════════
SECTION 2 — GUARD INTEGRITY AUDIT
═══════════════════════════════════════════════════════════

## Warming Bucket Watchlist — AUDIT COMPLETE

Ran comprehensive analysis of all sniper buckets with n>=2 and negative P&L.
Found 19 historically negative P&L buckets.
Cross-referenced against all guards (global floor/ceiling + IL-5 through IL-32 + 5 auto-guards).

Result: ALL 19 negative buckets are covered by existing guards. Zero genuine gaps.
  - 5 buckets covered by 5 auto-guards (KXXRP NO@93c etc.)
  - 8 buckets covered by IL-5 through IL-24 (global + asset-specific hardcoded)
  - 6 buckets covered by IL-25 through IL-32 (newer hardcoded guards)

Note: auto_guard_discovery.py _EXISTING_HARDCODED_GUARDS already includes IL-25 to IL-32.
Registry is up to date. No cleanup needed.

Guard stack is CLEAN and COMPREHENSIVE as of S111.

## Startup Confirmation

5 auto-guards loaded: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c
Bayesian: n=311, override_active=True
Bot PID: 57412 (note: SESSION_HANDOFF had stale PID 48350 — update in wrap)
Dim 9 VALIDATED: Trade 3814 (btc_drift_v1) has full signal_features JSON.

═══════════════════════════════════════════════════════════
SECTION 3 — POLITICAL MARKETS — PILLAR 3 INVESTIGATION
═══════════════════════════════════════════════════════════

## Finding: Political Markets Exist on Kalshi

CORRECTION to existing KALSHI_MARKETS.md documentation:
  Line 716-721 states "Politics / Geopolitical Events (Polymarket.COM only)".
  THIS IS INCORRECT. Political markets exist on Kalshi.

Evidence:
  - Kalshi series database: ~12,335 political series (25% of all 44,735 Kalshi series)
  - Election series: ~2,140 series (5.5% of total)
  - Real markets confirmed: "Will X win UK election?", "Will Mamdani become US President?"
  - Historical tickers: CONTROLS (Senate/House control), SENATEGA, SENATEOR, SENTEATX, etc.

However, the structure differs fundamentally from crypto series:
  1. Event-based tickers (not systematic KX-prefixed series)
  2. Seasonal availability (primarily during election cycles — not always open)
  3. Longer horizons (days to months, not 15-minute windows)
  4. Lower liquidity than crypto 15-min markets (unknown exact volumes)
  5. No systematic daily creation like crypto direction markets

## Why This Matters (Le 2026 Application)

With b=1.83 for politics near-expiry:
  At 70c: true_prob = 0.83 → 13pp edge
  At 80c: true_prob = 0.92 → 12pp edge
  At 90c: true_prob = 0.98 → 8pp edge

This is 20-43x the calibration edge of the sniper (0.3-0.5pp).
If political markets have sufficient liquidity near resolution, the edge is enormous.

## Meeting the Standard Before Building

Standard: structural basis + math validation + DB backtest + p-value.
  Structural basis: CONFIRMED (Le 2026 calibration paper, verified by CCA)
  Math validation: CONFIRMED (formula validated in bet_analytics.py)
  DB backtest: NOT POSSIBLE YET (no political bet history in our DB)
  P-value: NOT POSSIBLE YET (no data)

Action: Do NOT build yet. Need to:
  1. Probe Kalshi API specifically for political market structures and volumes
  2. Map what political markets exist near-expiry with tradeable liquidity
  3. Understand settlement patterns (binary YES/NO? threshold? multi-outcome?)
  4. Paper-trade a small sample to gather calibration data
  5. ONLY THEN: if WR exceeds break-even by >3pp after 30+ paper bets: graduate

CCA request written: see POLYBOT_TO_CCA.md (session 111 entry)

## Dead End Check

Weather markets (<48h): b=0.75 means favorites OVERPRICED. Avoid. CONFIRMED dead end.
Near-expiry crypto: b=0.99 means near-perfect calibration. Sniper edge = structural, not calibration.

═══════════════════════════════════════════════════════════
SECTION 4 — SIGNAL FEATURES ACCUMULATION (DIM 9)
═══════════════════════════════════════════════════════════

Dim 9 validated: Trade 3814 has full signal_features JSON.
n=2 bets with signal_features (first 2 logged since Dim 9 deploy + restart).
Total live drift bets: 315.
Target: n=1000 for meta-classifier training.
At current rate (~60/day drift bets): ~15 more days.

No action needed. Accumulation proceeding automatically.

═══════════════════════════════════════════════════════════
SECTION 5 — BET ANALYTICS SNAPSHOT (S111 start)
═══════════════════════════════════════════════════════════

expiry_sniper_v1:  n=739, WR=95.8%, EDGE CONFIRMED lambda=+15.707, CUSUM S=1.700 stable
sol_drift_v1:      n=43, WR=69.8%, EDGE CONFIRMED lambda=+2.886, Brier=0.198
btc_drift_v1:      n=69, WR=49.3%, collecting, CUSUM S=4.020 stable
xrp_drift_v1:      n=49, WR=46.9%, collecting, CUSUM S=3.900, BLOCKED (5 consecutive)
eth_drift_v1:      n=153, WR=47.1%, NO EDGE, CUSUM S=13.300 DRIFT ALERT (Bayesian managing)

Monthly WR tracker: 2026-03 only month. WR=95.8%. No FLB weakening signal.

═══════════════════════════════════════════════════════════
SESSION GRADE: B+
Builds: sniper_monthly_wr.py (15 tests) + calibration formula (7 tests)
Research: guard audit clean, Pillar 3 lead validated, CCA corrections documented
Self-improvement: Pillar 2 academic findings implemented, Pillar 3 lead identified
Tests: 1631 → 1653 passing (+22 new tests)
═══════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════
SECTION 6 — POLITICAL MARKETS API PROBE (Session 111 addendum)
═══════════════════════════════════════════════════════════

## Direct API findings from Kalshi /events and /markets probes

Political events found on Kalshi (sample):
  [Politics] KXPERSONPRESMAM-45: vol=0, close=2045-01-29 — "Will Mamdani become President?"
  [Elections] KXBRUVSEAT-35: close=unknown — "Will Andrew Tate's party win UK election seat?"
  [Politics] KXXISUCCESSOR-45JAN01: yes=45c — "Who will be named Xi Jinping's successor?"
  [Financials] KXOAIANTH-40: — "Will OpenAI or Anthropic IPO first?"
  Other categories: World, Climate, Science, Social, Entertainment, Health

Key finding: Most Kalshi political markets are LONG-HORIZON (close dates 2030-2045)
with near-zero volume. They are NOT continuously tradeable like crypto 15-min markets.

Implication for Le (2026) b=1.83 strategy:
  The b=1.83 "near-expiry" slope applies specifically to markets within hours of resolution.
  For political markets, these windows only open during actual events:
    - Election day (results within hours)
    - Legislative votes
    - Major summits/decisions

This means a political sniper would need:
  1. Event detection (monitor for political markets opening near expiry)
  2. Volume check (many political markets have zero liquidity)
  3. Near-expiry price filter (90-95c YES or similar)
  4. Completely different architecture from crypto 15-min sniper

CONCLUSION: The Le (2026) calibration edge EXISTS in theory, but requires:
  - Episodic monitoring (not continuous like crypto)
  - Volume screening (most political markets are illiquid)
  - Event calendar integration
  - A different bot architecture

Grade: OPEN LEAD with significant structural complexity. Not viable as quick build.
CCA request filed. Wait for CCA investigation + paper-trade sample before building.
