# POST-15M-CRYPTO-BAN ANALYSIS
# Generated: 2026-04-06
# Scope: Live trades after the 15-minute crypto ban took effect

## Cutoff

The post-ban regime starts immediately after the last live 15-minute-crypto trade:

- Cutoff: `2026-03-27 23:12:03 UTC`
- Determination rule: `MAX(created_at)` across live trades for banned 15-minute crypto strategies
  (`expiry_sniper_v1`, `btc_drift_v1`, `eth_drift_v1`, `sol_drift_v1`, `xrp_drift_v1`,
  `eth_orderbook_imbalance_v1`, `btc_lag`, `btc_lag_v1`, `eth_lag_v1`)

All metrics below use:

- `is_paper=0`
- `created_at > cutoff`
- CST session accounting via fixed `UTC-6` as required by project directives

## Executive Verdict

The ban did not solve the core portfolio problem by itself. Post-ban profit is still almost
entirely one engine: `daily_sniper_v1`.

The diversification layer is not yet a portfolio. It is one strong BTC engine plus:

- one structurally losing ETH extension
- one promising but tiny NHL sample
- one failing NBA sample that was oversized relative to evidence
- one MLB sample polluted by the in-game betting bug

This means the bot is **not yet a stable 25 USD/day system** in the post-ban regime.
It is a volatile single-engine system with experimental add-ons.

## Core Numbers

### Portfolio-level

- Live rows after cutoff: `185`
- Settled live bets after cutoff: `166`
- Open live bets after cutoff: `19`
- Post-ban settled P&L: `+120.24 USD`
- Post-ban settled WR: `97.59%`

### Strategy breakdown

| Strategy | Settled | Open | WR | P&L USD | Avg stake USD | Avg P&L / bet USD |
|---|---:|---:|---:|---:|---:|---:|
| `daily_sniper_v1` | 152 | 3 | 100.0% | +113.35 | 9.27 | +0.75 |
| `eth_daily_sniper_v1` | 7 | 1 | 85.71% | -4.11 | 9.21 | -0.59 |
| `sports_game_nhl_v1` | 4 | 0 | 100.0% | +33.66 | 7.75 | +8.41 |
| `sports_game_nba_v1` | 2 | 0 | 0.0% | -19.67 | 9.84 | -9.84 |
| `sports_game_mlb_v1` | 1 | 12 | 0.0% | -2.99 | 2.99 | -2.99 |
| `sports_game_ucl_v1` | 0 | 3 | n/a | 0.00 | n/a | n/a |

### Concentration

- `daily_sniper_v1` generated `113.35 / 120.24 = 94.27%` of total post-ban profit.
- Everything except BTC daily sniper combined produced only `+6.89 USD`.
- Sports as a whole are positive only because NHL went `4/4`.
- If NHL regresses, the current diversification layer is negative.

## Daily Consistency vs 25 USD Goal

### CST daily net P&L

| CST day | Net P&L USD |
|---|---:|
| 2026-03-27 | -8.27 |
| 2026-03-28 | +68.49 |
| 2026-04-02 | +50.32 |
| 2026-04-05 | +11.51 |
| 2026-04-06 | -1.81 |

### Daily distribution

- Days with settled post-ban activity: `5`
- Mean daily P&L: `+24.05 USD`
- Median daily P&L: `+11.51 USD`
- Min daily P&L: `-8.27 USD`
- Max daily P&L: `+68.49 USD`
- Days >= `15 USD`: `2 / 5`
- Days >= `25 USD`: `2 / 5`
- Negative days: `2 / 5`

### Interpretation

The average looks acceptable only because two very large BTC-led days dominate the sample.
The median is far below the target. The current regime is **not sustainably hitting 25/day**.

## What the Data Actually Says

### 1. BTC daily sniper is the business

Post-ban BTC daily sniper:

- `152` settled bets
- `100%` WR
- `+113.35 USD`

Price buckets:

| Price cents | Bets | WR | P&L USD |
|---|---:|---:|---:|
| 88 | 1 | 100.0% | +1.21 |
| 89 | 1 | 100.0% | +1.10 |
| 90 | 31 | 100.0% | +30.69 |
| 91 | 20 | 100.0% | +15.60 |
| 92 | 61 | 100.0% | +42.35 |
| 93 | 37 | 100.0% | +22.20 |
| 95 | 1 | 100.0% | +0.20 |

Implication:

- The post-ban BTC edge is broad across the active 90-93c band.
- 92c is the highest-volume post-ban bucket.
- The edge still looks real after the regime change.

### 2. ETH daily sniper is not a small-tweak problem

Post-ban ETH daily sniper:

- `7` settled bets
- `85.71%` WR
- `-4.11 USD`

Price buckets:

| Price cents | Bets | WR | P&L USD |
|---|---:|---:|---:|
| 90 | 1 | 100.0% | +0.99 |
| 91 | 6 | 83.33% | -5.10 |

Break-even win rates for NO-side style sniper entries:

| Entry price | Break-even WR |
|---|---:|
| 85c | 85.77% |
| 86c | 86.73% |
| 87c | 87.69% |
| 88c | 88.66% |
| 89c | 89.61% |
| 90c | 90.57% |
| 91c | 91.52% |
| 92c | 92.48% |
| 93c | 93.43% |

Implication:

- The live problem is not just "91c is slightly too high."
- At the observed post-ban ETH live WR, the strategy is negative at 90-91c.
- A tiny ceiling trim is not enough. The live thesis needs a materially better payoff band,
  or ETH stays paper-only.

### 3. Sports are under-calibrated and mis-sized

Sports settled sample after the ban:

- NHL: `4` settled, `+33.66 USD`
- NBA: `2` settled, `-19.67 USD`
- MLB: `1` settled, `-2.99 USD`
- UCL: `0` settled, `3` still open

Sports open exposure right now:

- MLB open: `12` positions / `33.55 USD`
- UCL open: `3` positions / `8.32 USD`
- Total sports open exposure: `15` positions / `41.87 USD`

That means sports have:

- only `7` settled live bets
- but `15` open live bets

Implication:

- The system is scaling sports exposure faster than it is learning from sports outcomes.
- This is the exact opposite of a good calibration loop.

### 4. NBA was not just unlucky in sizing terms

The two NBA bets were:

| Created UTC | Ticker | Side | Price | Cost USD | Edge pct | Win prob | Result | P&L USD |
|---|---|---|---:|---:|---:|---:|---|---:|
| 2026-03-28 00:25:44 | `KXNBAGAME-26MAR27ATLBOS-BOS` | no | 31 | 9.92 | 13.31% | 50.07% | yes | -9.92 |
| 2026-03-28 02:28:56 | `KXNBAGAME-26MAR27DALPOR-POR` | yes | 65 | 9.75 | 11.97% | 79.42% | no | -9.75 |

Implication:

- These bets were nearly full sniper-sized despite zero sports calibration history.
- Even if the edge model was directionally right, the bankroll impact per miss was too large
  for a strategy with effectively no live sample.
- The main sports failure is not only selection quality. It is also stake discipline.

### 5. Post-ban daily outcomes are still dominated by one engine

Per-day contribution split:

| CST day | BTC sniper | ETH sniper | Sports | Net |
|---|---:|---:|---:|---:|
| 2026-03-27 | +1.65 | 0.00 | -9.92 | -8.27 |
| 2026-03-28 | +44.58 | 0.00 | +23.91 | +68.49 |
| 2026-04-02 | +50.32 | 0.00 | 0.00 | +50.32 |
| 2026-04-05 | +9.11 | +2.40 | 0.00 | +11.51 |
| 2026-04-06 | +7.69 | -6.51 | -2.99 | -1.81 |

Implication:

- BTC is carrying the system on every profitable day.
- ETH and sports can still flip a positive BTC day into a weak or negative session.
- The diversification layer is currently a drag-adjusted overlay, not a second engine.

## Blind Spots Exposed by the Data

### Blind spot 1: "Positive average" is hiding poor daily reliability

Mean daily P&L looks close to the target, but median and hit-rate do not.
The plan should optimize for:

- median daily P&L
- percent of days >= `25 USD`
- percent of negative days

not just average.

### Blind spot 2: Sports calibration is backwards

Right now the bot has more open sports risk than resolved sports evidence.
That means the portfolio is learning too late.

The correct order is:

1. small fixed live stakes by sport
2. reach minimum settled sample
3. then expand volume

not "expand coverage first, diagnose later."

### Blind spot 3: ETH is being treated like BTC with a slightly worse ceiling

The data does not support that assumption.
Post-ban ETH looks like a different distribution, not a lower-confidence clone of BTC.

### Blind spot 4: The portfolio still has only one proven post-ban edge

Post-ban, only `daily_sniper_v1` is both:

- meaningfully sampled
- strongly positive
- operationally repeatable

Everything else is still candidate territory.

## What Should Change Next

### Priority 1

Keep `daily_sniper_v1` as the core engine and stop pretending the portfolio is already diversified.

### Priority 2

Keep `eth_daily_sniper_v1` out of live mode until it clears a materially better payoff band in paper.
The current live evidence says 90-91c is not acceptable.

### Priority 3

Reset sports live calibration:

- fixed low caps per sport
- no sport-specific size ramps before `20+` settled bets in that sport
- treat NHL, NBA, MLB, UCL as separate models, not one generic "sports" bucket

### Priority 4

Measure the post-fix sports stack on calibration metrics, not just P&L:

- settled bets per sport
- median stake per sport
- WR by sport
- P&L per sport
- open exposure / settled-sample ratio

### Priority 5

Judge the 25 USD/day mission on this scorecard:

- median CST daily profit
- `>=25 USD` hit rate
- negative-day rate
- profit concentration in top strategy

If BTC remains >80-85% of total profit, the system is still effectively single-engine.

## Bottom Line

Post-ban, the bot is healthier than it was during 15-minute crypto live trading, but it is
not yet the robust multi-engine machine the current plans assume.

The hard data says:

- BTC sniper is real
- ETH sniper is not ready
- NHL is promising but tiny
- NBA/MLB are not calibrated yet
- the 25 USD/day target is not being hit consistently

The next phase should be built around **calibration discipline and concentration reduction**,
not just more coverage or more strategy ideas.
