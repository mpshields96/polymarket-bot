# SELF-IMPROVEMENT ROADMAP
# Established S98 — 2026-03-17 — Matthew's explicit multi-session directive
# ═══════════════════════════════════════════════════════════════════════════
#
# MISSION: Build a prediction market bot that compounds passive income by
# continuously learning from its own trading data — without requiring Claude
# to manually analyze every session.
#
# The sniper (90-95c zone, ~97% WR on guarded buckets) is the validated engine.
# The question is not "what new market do I enter?" but "how does this bot get
# better automatically, every single day, from every single bet it places?"
# ═══════════════════════════════════════════════════════════════════════════

## PHILOSOPHY

Every live bet is a training example.
Every settled bet is a calibration update.
Every losing bucket is a signal to be learned.
Every winning bucket is evidence to be preserved.

The bot should be at least 1% smarter after every 100 bets, without any
Claude session required to make that happen.

## DIMENSION 1 — AUTO-GUARD DISCOVERY
**What it does:** Scans live bet DB nightly, finds buckets where WR < break-even
and total loss exceeds threshold, writes new guards to data/auto_guards.json.

**Status:**
- scripts/auto_guard_discovery.py — BUILT (S98)
- data/auto_guards.json loading in live.py — PENDING
- Session-start hook to auto-run — PENDING
- Guard retirement (50+ post-guard wins → retire) — PENDING

**Academic basis:**
- Break-even WR formula accounts for Kalshi taker fee (7% of gross profit)
- Negative-EV buckets identified via: WR < P/(P + (100-P)*(1-0.07*P/100))
- Conservative threshold: 3+ bets, 5+ USD loss before triggering guard

**How it compounds:**
Each session that runs auto_guard_discovery.py, the bot's guard stack grows
to cover new negative-EV buckets discovered from live data. No manual analysis needed.
Over 6 months: every structural loss pattern gets systematically blocked.

## DIMENSION 2 — BAYESIAN DRIFT MODEL
**What it does:** Instead of static sigmoid coefficients fit on historical paper data,
the drift strategy maintains a Bayesian posterior over its parameters. After each
settled live bet, the posterior updates. Over 100+ live bets, the model narrows
its uncertainty and Kelly sizing becomes genuinely calibrated to live performance.

**Status:**
- src/models/bayesian_drift.py — PENDING
- data/drift_posterior.json — PENDING
- Settlement hook in main.py — PENDING

**Academic basis:**
- Bayesian logistic regression: Jaakkola & Jordan (1997) variational Bayes
- Online update rule: treat each bet as likelihood observation, update Gaussian
  approximation to posterior over sigmoid weights
- Gibbs & MacKay (2000) — evidence framework for binary classifiers
- Alternative: simpler MAP update (gradient descent on log-posterior) — fewer parameters

**Key insight:** The current drift model's edge is uncertain because the sigmoid
was fit on paper data. The Bayesian model will start with that as the prior and
update toward live performance. If live WR diverges from the paper-calibrated
prediction, the model detects this automatically via KL divergence between
prior and posterior.

**Implementation plan:**
1. BayesianDriftModel class with Gaussian prior over (intercept, slope)
2. update(signal, outcome) method — online posterior update after each settled bet
3. predict(drift_pct) — returns (p_yes, uncertainty) from current posterior
4. edge_pct(drift_pct) — replaces current static sigmoid, uses posterior mean
5. kelly_fraction(drift_pct) — uses posterior uncertainty to scale Kelly bet
   (wider uncertainty → smaller bet, narrower → larger)
6. Persist posterior to data/drift_posterior.json on every update
7. Load posterior at bot startup, continue from where last session left off

**How it compounds:**
Each settled drift bet tightens the posterior. After 100 live bets, the model's
predictions are grounded in live market behavior, not paper simulation.
After 500 live bets, the model has seen enough to detect regime changes.

## DIMENSION 3 — KELLY SELF-CALIBRATION
**What it does:** Kelly fraction is currently determined by the static sigmoid's
confidence output. Once the Bayesian model is live, Kelly should automatically
scale with posterior uncertainty — wide prior → small bet, narrow posterior → larger.

**Status:** Dependent on Dimension 2.

**Academic basis:**
- Kelly (1956) — original paper
- Thorp (2006) — practical Kelly for investors
- MacLean, Thorp, Ziemba (2011) — growth-optimal betting with uncertainty
- Key result: fractional Kelly (bet fraction f where f < Kelly) is optimal
  when the win probability estimate is uncertain. Posterior variance maps
  directly to the fractional Kelly coefficient.

## DIMENSION 4 — AUTO-PROMOTION
**What it does:** When a paper strategy hits the gate criteria (20 OOS bets,
Brier < 0.30, WR > break-even), it automatically promotes to live without
requiring a Matthew decision or Claude analysis.

**Status:** PENDING. Currently requires manual session intervention.

**Gate criteria (existing):**
- 20+ post-filter paper bets (OOS)
- WR > break-even (strategy-specific)
- Brier < 0.30
- No structural asset/direction asymmetry (check YES vs NO WR split)

**Implementation plan:**
- scripts/auto_promotion_check.py — runs at session start
- If gate met: modifies main.py parameter (or writes config file) + sends Reminders alert
- Writes decision + rationale to .planning/CHANGELOG.md

## DIMENSION 5 — GUARD RETIREMENT
**What it does:** A guard added at 5 bets and 80% WR may no longer be necessary
at 200 bets and 96% WR. Auto-retirement prevents over-blocking as sample sizes grow.

**Status:** PENDING.

**Criteria for retirement:**
- Guard was added N months ago
- Post-guard accumulation: 50+ bets in the bucket since guard was added (across paper)
- Post-guard WR > (break-even + 2pp margin)
- Retirement logged with full statistical rationale

## DIMENSION 6 — FLB ACADEMIC RESEARCH
**What it does:** The sniper's structural edge comes from the Favourite-Longshot Bias —
high-probability events are systematically underpriced relative to their true probability.
Deeper academic understanding of WHY this exists in crypto prediction markets will
reveal new exploitable patterns beyond what we currently guard/allow.

**Academic targets:**
- Thaler & Ziemba (1988) — "Anomalies: Parimutuel Betting Markets"
- Snowberg & Wolfers (2010) — "Explaining the Favourite-Longshot Bias"
- Ottaviani & Sorensen (2008) — "The Favourite-Longshot Bias: An Overview"
- Kuypers (2000) — "Information and Efficiency: An Empirical Study of a Fixed Odds Betting Market"

**Specific questions to research and test against our DB:**
1. Is the FLB stronger at certain times of day? (check our sniper win rates by hour)
2. Is FLB stronger closer to expiry? (check our win rates by time-remaining-at-signal)
3. Does the bias vary by asset (BTC vs ETH vs SOL vs XRP)?
4. Is there a "sweet spot" within 90-95c that has higher edge than the edges?
5. Does the bias correlate with BTC volatility? (higher vol → more uncertainty → more FLB)

**How to test:** Query DB, compute WR by (hour, asset, price_cents, time_remaining).
Look for statistically significant variation. Only build filters if p < 0.05 AND
sample size justifies it.

## DIMENSION 7 — CORRELATION LEARNING
**What it does:** Some losses cluster — same 15-min window, multiple assets reverse
together. Correlation learning would detect when loss probability is elevated due
to correlated positioning and reduce or skip bets in those conditions.

**Status:** Conceptual only.

**Research direction:**
- Analyze DB for loss clustering: are multi-bet losses within same 15-min window
  more common than single-bet losses? (Pearson chi-square test)
- If clustering is significant: add intra-window correlation guard
  (if 1 bet already lost this window, skip next same-window bet)
- Academic: portfolio Kelly with correlated assets (MacLean et al. 2011)

## PROGRESS TRACKING

Session-start checklist (run ALL 6 — adds ~2 min, catches problems early):
  1. python3 scripts/auto_guard_discovery.py        → any new guards found?
  2. python3 scripts/bayesian_drift_status.py       → posterior state, n_obs
  3. python3 scripts/auto_promotion_check.py        → any strategies at promotion gate?
  4. python3 scripts/guard_retirement_check.py      → any guards ready to retire?
  5. python3 scripts/strategy_drift_check.py        → any strategy WR declining?
  6. cat /tmp/ucl_sniper_mar18.log (if after 17:19 UTC March 18)

The bot is improving if: guard stack grows, posterior narrows, Kelly fraction
calibrates closer to true edge, P&L trends positive over rolling 30-day window.

## BUILD STATUS SUMMARY (as of Session 102 — 2026-03-18)

ALL DIMENSIONS BUILT AND LIVE:

  Dim 0: Operational baseline — RUNNING (bot alive 24/7, guards intact)
  Dim 1: Auto-guard discovery — COMPLETE (S98/S99)
         scripts/auto_guard_discovery.py, live.py reloads auto_guards.json
  Dim 2: Bayesian drift model — COMPLETE (S98-S100)
         src/models/bayesian_drift.py, drift_posterior.json persisted
  Dim 3: Kelly self-calibration — COMPLETE (S99, uses Bayesian kelly_scale)
         src/models/bayesian_settlement.py wired into settlement_loop
  Dim 4: Auto-promotion — COMPLETE (S100)
         scripts/auto_promotion_check.py (monitoring, no manual action needed)
         BTCDriftStrategy.generate_signal() uses predict() at 30+ obs
  Dim 5: Guard retirement — COMPLETE (S101)
         scripts/guard_retirement_check.py, 16 guards tracked
         All WARMING UP — needs 50+ paper bets per bucket (~weeks away)
  Dim 6: FLB academic research — COMPLETE (S102)
         Documented in EDGE_RESEARCH_S100.md S102 appendix
         FLB driven by probability misweighting (Snowberg & Wolfers 2010)
         90-95c window structurally justified. Asset hierarchy confirmed.
  Dim 7: Strategy drift detection — COMPLETE (S102)
         scripts/strategy_drift_check.py, Page-Hinkley CUSUM test
         eth_drift ALERT (peak PH=5.05). sol/btc/xrp normal.

WAITING ON DATA (not code-blocked):
  - Bayesian activation: 3 obs, needs 27 more live drift bets (days)
  - Guard retirement: 0-3 paper bets per bucket, needs 50 (weeks)
  - btc_drift Stage 1 promotion: last20 WR 50%, hold until 55%+

## NEXT FRONTIER (Sessions 103+)

Phase 1 complete: all self-improvement infrastructure is built.
Phase 2: let the system accumulate data and self-correct autonomously.

Sessions 103+ priorities:
  1. Monitor Bayesian accumulation (passive) — no code needed
  2. UCL log check (March 18 17:19 UTC)
  3. NCAA Round 1 scanner (March 19-20)
  4. CPI speed-play (April 10 08:30 ET)
  5. GDP speed-play (April 30)

Longer-term (when data accumulates):
  - Dim 5: retire guards once 50+ paper bets per bucket confirm recovery
  - Bayesian override: monitor first 30-obs prediction vs actual WR
  - Potential Dim 8: cross-asset correlation guard (multi-asset loss windows)
    Academic basis: Kelly (1956) for correlated bets — but per-window cap (S101)
    already handles this. Low priority unless P&L data shows new pattern.

## MULTI-SESSION CONTINUITY

Session 98: Dim 1 built
Session 99: Dim 2+3 built, settlement wiring
Session 100: Dim 4 built (Bayesian predict wired), auto-promotion
Session 101: Kelly correlation confirmed, Dim 5 (guard retirement) built
Session 102: Dim 7 (PH drift detection) built, Dim 6 (FLB research) complete
             All-time P&L turned POSITIVE (+12.77 USD) for first time

## DIMENSION 0 — OPERATIONAL BASELINE (non-negotiable, always running)
This is the floor. Self-improvement only matters if the bot is alive and profitable.

**Always maintained:**
- Bot running 24/7, auto-restart on death
- Guard stack intact (no new unguarded losing buckets open)
- Zero coding errors causing missed bets or wrong-size bets
- Kill switch properly calibrated (not triggering on normal variance)
- Every live bet correctly recorded in DB with right strategy/side/price

**Principle:** Don't break even. Don't lose money. Generate profit.
Self-improvement dims 1-7 are the multiplier on a working base.
A broken bot learning nothing compounds losses. A healthy bot learning
automatically compounds wins.

**Session start checklist (2 minutes, always):**
1. Bot alive? → restart if dead
2. Guards intact? → run auto_guard_discovery.py --dry-run
3. Recent bet P&L trending? → check last 20 sniper bets
4. Any new losing buckets? → guard them
5. Then and only then: work on self-improvement dimensions

## WHAT NOT TO BUILD

These are explicitly NOT self-improvement:
- One-off sports event launchers (UCL, NCAA, CPI, GDP checks)
- Market scanners that Claude runs manually
- New strategies without DB-validated edge
- Anything that improves only for one session then goes stale

If it doesn't run automatically from live bet data, it's not self-improvement.
