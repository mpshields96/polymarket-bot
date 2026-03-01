# TRADING SYSTEM PRINCIPLES
# polymarket-bot — permanent reference, not session state
# Last updated: 2026-03-01
#
# PURPOSE: These principles exist because of a hard-won lesson from a
# previous betting system built on Gemini that accumulated rules after
# every bad day until it became broken. This document is the antidote.
# Read this before making ANY change to strategy logic or risk parameters.

═══════════════════════════════════════════════════════════════

## THE CORE TEST: Mechanical Defect vs Statistical Outcome

Before touching any code after a loss, ask this question:

> "Does this change fix something that is OBJECTIVELY WRONG in the
> infrastructure, or does it attempt to prevent a statistical outcome
> that could happen even in a profitable system?"

**Mechanical defect (FIX IT):**
- A counter that resets when it shouldn't
- A bet placed outside the allowed price range
- A kill switch that doesn't persist across restarts
- A size calculation that ignores the min_edge parameter
- Any behavior that violates the documented design intent

**Statistical outcome (DO NOT TOUCH):**
- Lost 3 NO bets in a row → do not add "never bet NO below 30¢"
- Bad day on btc_drift → do not raise min_edge_pct from 5% to 8%
- Lost money on a Tuesday → do not add a day-of-week filter
- Consecutive losses → do not lower the consecutive loss limit from 4 to 3
- One bad week → do not disable a strategy

The difference: mechanical defects produce wrong behavior every time
they occur. Statistical outcomes are just outcomes — they happen in
profitable systems too.

═══════════════════════════════════════════════════════════════

## THE ANTI-BLOAT PRINCIPLE

Every rule added to a betting system has a cost:
1. It reduces the opportunity set (fewer bets placed)
2. It adds complexity (more code to maintain, more ways to break)
3. It may conflict with other rules added for different bad outcomes
4. It encodes emotional reasoning as permanent system logic

The previous Gemini system failed this way. One bad game → one rule.
Another bad game → another rule. After 50 iterations: a system of
contradictory constraints where every rule was a scar from a loss and
nothing was grounded in statistical evidence.

**The standard for adding a new parameter or constraint:**
- Must be supported by a minimum of 30 data points
- Must be directionally consistent with backtest data
- Must address a repeatable structural pattern, not a single event
- Must have a test written BEFORE the change

If a proposed change cannot meet these standards, log it in todos.md
and wait until there is enough data to evaluate it properly.

═══════════════════════════════════════════════════════════════

## WHY PAPER BETS CONTINUE DURING LIVE SOFT STOPS

When the kill switch fires a daily soft stop ($20 gross losses):
- Live bets stop: correct — capital preservation
- Paper bets continue: correct — independent data collection

**Why this is right:**

Paper-only strategies are calibration pipelines, not revenue sources.
Their purpose is to accumulate Brier score data so we can evaluate
whether a strategy has real predictive edge before promoting it live.

If paper collection stops during bad live days, you introduce
SELECTION BIAS into your calibration data. You'd only have Brier
scores from days when live conditions are favorable. That biases
the graduation criteria in a dangerous direction — it makes
strategies look better than they are.

The soft stop is about CAPITAL PRESERVATION, not STRATEGY QUALITY.
A strategy can have genuine long-run edge and still have a bad day.
Stopping data collection during bad days confuses the two.

**What would be wrong:** stopping paper bets when live bets are
stopped, on the theory that "if it's not good enough to bet live
it's not worth recording." That logic is backwards. The paper bets
are how you determine whether something is good enough to bet live.

═══════════════════════════════════════════════════════════════

## GRADUATION CRITERIA ARE MANDATORY, NOT SUGGESTIONS

Every strategy must complete paper graduation before going live:
- Minimum 30 settled paper trades
- Brier score computed and evaluated (target < 0.25)
- Win rate consistent with backtest expectations

**Why this matters:**

The graduation process exists because the backtest is optimistic.
Backtests run on historical data with perfect information. Live
trading has slippage, market impact, and adversarial counterparties
(Kalshi BTC markets have Jane Street, Susquehanna, Jump as market
makers). Paper trading is the bridge — it captures real market
conditions without real capital at risk.

Promoting a strategy to live before graduation is betting real money
on a hypothesis that hasn't been tested in live market conditions.

**Current violation (recorded 2026-03-01):**
eth_lag_v1 was promoted to live with 0/30 paper trades completed.
This was a process error. eth_lag is being returned to paper-only
until graduation criteria are met.

═══════════════════════════════════════════════════════════════

## WHAT WE ARE ACTUALLY DOING HERE

This bot bets on Kalshi 15-minute BTC/ETH price direction markets.
The edge hypothesis is: BTC spot price moves on Binance.US precede
Kalshi market price adjustments by enough time to place a profitable
bet. That lag, if real and consistent, is the alpha.

**Who we're competing against:**
Jane Street, Susquehanna, Jump Trading — professional HFTs with
co-located infrastructure, full order books, and teams of quants.

**What this means:**
- The lag strategy only works if HFTs haven't already closed the
  gap before our signal fires
- As Kalshi BTC markets mature and more capital enters, the lag
  likely shrinks — strategies may degrade over time
- This is NOT a guaranteed edge — it is a hypothesis being tested

**The honest current state (as of 2026-03-01, 17 live trades):**
- 17 live trades is not enough data to confirm or deny alpha
- All-time live P&L: -$3.73 (net), +$6.25 adjusted (removing 2
  confirmed guard-violation bets that shouldn't have been placed)
- btc_lag: 43 paper trades, Brier 0.191 — best calibrated strategy
- btc_drift: 12 live trades, Brier n/a — model validity unproven
- eth_lag: 0 paper calibration — not ready for live

At 50+ live trades per strategy with Brier scores, we will have
enough data to evaluate whether the edge hypothesis holds.

═══════════════════════════════════════════════════════════════

## WHEN TO CHANGE SOMETHING vs WHEN TO WAIT

**Change immediately (mechanical defects):**
- Bug is reproducible and violates documented behavior
- Test can be written that fails before fix and passes after
- The fix doesn't change strategy logic — it corrects infrastructure

**Wait for data (strategy parameters):**
- min_edge_pct, consecutive_loss_limit, daily_loss_limit_pct
- Any threshold based on probability or statistical calibration
- Signal filters, price range guards beyond what's already proven
- Anything that would have prevented a specific bad outcome in hindsight

**Never do:**
- Add a rule because of a single bad day
- Lower a threshold because a recent stretch was painful
- Add complexity because something feels broken after losses
- Make changes while emotionally reactive (wait until sober/calm)

═══════════════════════════════════════════════════════════════

## SIGNAL QUALITY: THE win_prob FLOOR CONCERN

**Documented 2026-03-01, not yet acted on (needs data first):**

btc_drift has `win_prob = max(0.51, min(0.99, win_prob))`. When the
sigmoid model computes a probability ≤ 0.51, the floor clamps it to
0.51 and the bet still fires if min_edge_pct passes. This means:
- The "must be above coin flip" quality gate is bypassed for
  low-conviction signals
- Bets with true model confidence ≤ 50% are being placed

This is a legitimate design concern but requires 30+ live trades
with Brier scores before any parameter change is justified.
Documented here so it is not forgotten and not acted on prematurely.

**Do not touch until:** btc_drift has 30+ settled live trades and
a computed Brier score to compare against.

**2026-03-01 analysis (17 live trades):**
win_prob=0.51 floor bets: 3W/5L = 38% win rate, P&L = +$5.24 POSITIVE.
win_prob>0.51 higher bets: 5W/4L = 56% win rate, P&L = -$8.97 NEGATIVE.
The floor bets are profitable because they are NO bets at 26-35¢ with
favorable payout structure — 38% actual win rate beats the 33-35% market
implied probability. The "fix the floor" concern is not supported by data.
Revisit at 30+ trades with Brier score.

═══════════════════════════════════════════════════════════════

## EXPANSION GATE (Matthew's standing directive)

Do NOT build new strategy types until current live strategies
are producing solid, consistent results.

Hard gate:
- btc_drift at 30+ live trades + Brier < 0.30
- 2-3 weeks of live P&L data
- No active kill switch events
- No silent blockers

Until the gate clears: log new ideas in todos.md. Do not build.

The temptation after a bad day is to think "we need more strategies
to diversify." Resist it. More strategies before the current ones
are proven just means more untested hypotheses risking real money.

═══════════════════════════════════════════════════════════════

## REVISION LOG

2026-03-01 — Initial creation (Matthew + Claude session 25)
  Context: Three straight sessions of kill switch persistence bugs
  were fixed. btc_drift had a 3W/8 day. eth_lag discovered to have
  bypassed graduation criteria. Matthew explicitly asked for this
  document after describing how a previous Gemini betting system was
  destroyed by trauma-based rule accumulation. This doc is the
  permanent encoded response to that lesson.
