# CCA ACTION MEMO — POST-BAN OVERHAUL
# Date: 2026-04-06
# Audience: Kalshi main chat, CCA, Codex
# Basis: live trade audit after 15-minute crypto ban

## Purpose

Turn the post-ban data into operating rules.

This memo is the tactical bridge between:

- [POST_15M_CRYPTO_BAN_ANALYSIS_2026-04-06.md](./POST_15M_CRYPTO_BAN_ANALYSIS_2026-04-06.md)
- the current overhaul plan
- the actual 25 USD/day mandate

## Reality Check

The current bot is not a diversified 25 USD/day machine.

It is:

- one proven BTC engine
- one losing ETH extension
- one promising NHL sample
- one broken MLB read due to the in-game bug
- one uncalibrated NBA branch that was oversized too early

That means the next phase must optimize for:

1. cleanup
2. calibration
3. concentration reduction
4. only then expansion

Not the other way around.

## Hard Portfolio Rules

### Rule 1 — BTC stays the core engine

`daily_sniper_v1` remains the only proven post-ban live engine.

Operational rule:

- Keep BTC live
- Do not use BTC profits as an excuse to loosen standards on every other strategy
- Judge all other strategies against whether they improve the portfolio without increasing negative-day frequency

### Rule 2 — ETH is not live until it proves a different payoff band

`eth_daily_sniper_v1` stays out of live mode.

Hard rule:

- `live_executor_enabled=False`
- Paper-only at materially better payoff bands, not at 90-91c
- Re-enable only if both are true:
  - at least `50` paper bets in the target band
  - observed WR clears break-even with cushion, not just barely

Working rule:

- test `<=85c` first
- if `85-86c` paper data does not clear break-even by several percentage points, keep ETH disabled

### Rule 3 — Sports are separate models, not one bucket

Never talk about "sports" as if NHL, MLB, NBA, and UCL are one strategy.

From now on:

- `sports_game_nhl_v1`
- `sports_game_mlb_v1`
- `sports_game_nba_v1`
- `sports_game_ucl_v1`

must each be evaluated and capped independently.

### Rule 4 — Open exposure cannot outrun settled evidence

If a sport has more open live exposure than settled evidence, the bot is scaling too fast.

Control rule:

- Before any cap raise, require:
  - at least `15` settled bets in that sport
  - open exposure in that sport no greater than one typical day's intended risk

### Rule 5 — The scoreboard is daily consistency, not mean alone

Track these as primary metrics:

- median CST daily P&L
- percent of days `>= 25 USD`
- percent of negative days
- profit concentration in top strategy

If BTC remains above `80-85%` of total profit, the system is still effectively single-engine.

## Immediate Cleanup Order

These happen before any new live expansion.

### 1. Fix bot correctness bugs

Mandatory before restart:

- in-game betting guard
- market date sort
- 24h sports horizon
- CST dedup reset
- ETH live disable
- NBA live disable

### 2. Clean Kalshi chat operating discipline

The Kalshi chat needs stricter startup and wrap behavior.

Required session-start order:

1. read latest handoff
2. read latest CCA delivery or local planning memo
3. run health
4. run balance / P&L reconciliation
5. inspect open positions by strategy
6. inspect open exposure by sport
7. only then decide whether the session is:
   - cleanup
   - calibration
   - research
   - deployment

### 3. Stop mixing calibration and expansion in the same decision

Current planning sometimes says:

- fix bugs
- expand sports
- scan all Kalshi
- add in-play sniper

That is too much at once.

New order:

1. fix bugs
2. calibrate current sports
3. verify stable behavior
4. then add one new lane

## Exact Recalibration Rules

### BTC daily sniper

Status:

- keep live
- keep as engine one

Rules:

- no structural change until sub-bucket analysis is complete
- next analysis must split by:
  - price bucket
  - hour bucket
  - CST day-of-week
- if no weak bucket appears, leave the strategy alone
- do not widen just to chase 25/day

### ETH daily sniper

Status:

- paper-only

Rules:

- target paper band first: `<=85c`
- minimum paper sample before any live reconsideration: `50`
- required live gate:
  - WR above break-even by at least `3pp`
  - positive paper P&L
  - no evidence of cluster losses
- starting live cap if ever re-enabled: `2 USD`

### NHL

Status:

- promising
- still under-sampled

Rules:

- keep live, but small
- cap: `2 USD` until `15` settled NHL bets
- raise to `3 USD` only if:
  - WR `>=58%`
  - average edge remains `>=6%`
  - no single-day NHL drawdown larger than one day of expected NHL profit

### MLB

Status:

- high-priority research sport
- current live sample is contaminated by the in-game bug

Rules:

- after bug fix, treat prior contaminated MLB evidence as non-decisive
- restart MLB calibration almost from scratch
- use:
  - minimum `3` books
  - fixed `2 USD` cap
  - no cap raise before `20` clean pre-game settled bets
- prioritize MLB as the main sports research lane because the structural basis is strongest

### NBA

Status:

- probation / paper-only until audited

Rules:

- no live NBA until the two losses are explicitly explained
- paper-only until:
  - side mapping is verified
  - `20` settled paper bets collected
  - paper WR and CLV are not obviously broken
- when re-enabled live:
  - start at `2 USD`
  - never jump directly to old sizing

### UCL / soccer

Status:

- secondary lane

Rules:

- keep small
- do not size UCL like MLB
- manual or paper-first unless game-market liquidity is clearly present

## Sports Research Priority Stack

You asked not to dilute by betting too many sports. Correct.

Use this order:

### Tier 1 — active focus now

1. `MLB`
2. `NHL`
3. `NBA`

Why:

- MLB has the strongest current structural case
- NHL is the best early result set
- NBA has to be fixed, not ignored

### Tier 2 — research queue, not live focus yet

4. college baseball
5. UFC

Why:

- both may matter
- neither should steal execution focus from MLB/NHL/NBA cleanup
- keep them in research mode until the main sports stack is behaving correctly

### Tier 3 — non-sports untapped markets

This remains important, but it is a separate lane.

Do not let "find all untapped markets" contaminate the sports calibration loop.

Use a separate scout process for:

- economics
- politics
- entertainment / culture
- other Kalshi high-volume series

That research lane should produce a ranked queue, not immediate live deployment.

## Research Questions CCA Should Answer Next

### MLB

Highest priority.

CCA should produce:

- pre-game edge study by price band
- edge study by book-count strength
- edge study by game time bucket
- whether certain matchup contexts should be skipped
- whether team-strength or pitcher context improves signal quality materially

### NHL

CCA should produce:

- goalie / starter availability importance
- whether current wins came from true price gaps or one-off noise
- whether NHL needs a different minimum edge than MLB

### NBA

CCA should produce:

- audit of the two live losses
- whether NBA prices on Kalshi are too efficient for current bookmaker-consensus logic
- whether NBA needs a stricter filter than MLB/NHL

### College baseball

CCA should answer:

- does Kalshi list it with enough volume to matter
- do we have a reliable external odds reference
- can it be treated closer to MLB than to NCAAB

### UFC

CCA should answer:

- listing cadence
- usable external odds reference
- whether market depth is enough for small repeatable edges

## What the Kalshi Chat Should Stop Doing

Stop doing:

- talking about "sports" as one model
- raising coverage and risk in the same step
- treating ETH like BTC with a slightly different knob
- using average daily profit as the main success metric
- assuming every new market category should become a live strategy quickly

## What the Kalshi Chat Should Start Doing

Start doing:

- per-sport scorecards every wrap
- open exposure tracking by sport
- median-day tracking
- separate research queue for untapped non-sports markets
- one-lane-at-a-time deployment discipline

## Operating Goal for the Next Phase

The next objective is not "bet more things."

It is:

1. preserve BTC as the engine
2. turn MLB into the first real second engine
3. keep NHL as the third priority but constrained
4. keep NBA on probation until validated
5. keep college baseball and UFC in research queue
6. keep untapped non-sports as a separate weekly scout lane

That is the cleanest path to a real multi-engine Kalshi system without diluting into chaos.
