# KALSHI BOT + CHAT OVERHAUL PLAN — Session 166
# Status: PLANNING (bot STOPPED per Matthew directive)
# Date: 2026-04-07 UTC
# Author: Kalshi main chat + CCA inputs

## THE HONEST DIAGNOSIS

**One strategy makes all the money. Everything else is a drag or losing.**

All-time live P&L by strategy:
  daily_sniper_v1         +118.70 USD  (190 bets, 99% WR) ← THE ENTIRE BUSINESS
  expiry_sniper_v1         +81.34 USD  (1125 bets, 95% WR) ← BANNED (15-min crypto)
  sports_game_nhl_v1       +33.66 USD  (4 bets, 100% WR) ← promising, tiny sample
  eth_daily_sniper_v1       -4.11 USD  (7 bets, 86% WR) ← STRUCTURALLY NEGATIVE
  sports_game_nba_v1       -19.67 USD  (2 bets, 0% WR) ← DISASTER, cause unknown
  eth_drift_v1             -27.35 USD  (158 bets, 46% WR) ← disabled (good)
  sol_drift_v1             -15.68 USD  (47 bets, 66% WR) ← disabled (good)
  btc_drift_v1              -9.53 USD  (80 bets, 50% WR) ← disabled (good)

April CST P&L:
  daily_sniper_v1          +67.12 USD  (89 bets, 100% WR)
  eth_daily_sniper_v1       -4.11 USD  (7 bets, 86% WR)
  sports_game_mlb_v1        -2.99 USD  (1 bet, 0%)

Today April 6 CST net: -1.81 USD. Sniper made +7.69, everything else lost -9.50.

**Matthew is right to question. The bot earns money through one edge. The diversification
attempts have been execution failures. The fix is not to abandon diversification — it's to
do it correctly.**

---

## CONFIRMED BUGS (not speculation — DB evidence)

### BUG 1 — IN-GAME BETTING (CRITICAL)
Bets placed at 23:46 UTC April 6 on games that started at 18:10-18:45 UTC (5+ hours in-game):
  KXMLBGAME-26APR061810KCCLE-CLE  (game started 18:10 UTC)
  KXMLBGAME-26APR061840CINMIA-MIA (game started 18:40 UTC)
  KXMLBGAME-26APR061845MILBOS-MIL (game started 18:45 UTC)
  KXMLBGAME-26APR061845STLWSH-STL (game started 18:45 UTC)
  KXMLBGAME-26APR061840SDPIT-PIT  (game started 18:40 UTC)

Root cause: _future_games() filters Odds API games by commence_time (future only).
But _match_game() has ±1 day tolerance. An April 7 Odds API game (passes filter) gets
matched to the April 6 Kalshi market (already played). The Kalshi market date is NEVER
independently verified as future before placing the bet.

Fix required: After parsing kalshi_date from ticker, check kalshi_date > now - 5min before
calling generate_signal(). One line, prevents all in-game bets.

### BUG 2 — 72h BETTING HORIZON BETS FUTURE GAMES BEFORE TODAY'S
The loop scans 72h ahead. With only 8 bets/day cap (now 30), April 7/8/9 games get bet first,
exhausting the cap before tonight's games run. 

Fix: Two changes:
  a. Sort markets by kalshi_date ascending (today first) before scanning
  b. Reduce horizon to 24h initially (can raise after validation)

### BUG 3 — ETH DAILY SNIPER NEGATIVE EV (STRUCTURAL)
At 91c: cost = 9.10 USD, payout if win = 0.90 USD. Breakeven WR = 91%.
Actual WR = 86% (7 bets). Every win returns 0.90 USD. Every loss costs 9.10 USD.
Mathematical result: 86% WR × 0.90 = 0.774 USD expected win - 14% × 9.10 = 1.274 USD expected loss.
Net EV per bet = -0.50 USD. Confirmed by the -4.11 USD on 7 bets.

Fix: Disable live execution immediately. To make it positive: need WR ≥ 92% OR lower the
price floor to 85-88c where payoff structure is less asymmetric.

### BUG 4 — NBA SPORTS: 0% WR, -19.67 USD (2 bets)
Cause unknown — could be team mapping error (wrong side bet), extreme variance on 2 bets,
or genuine lack of edge in NBA markets. Cannot diagnose without reviewing the two specific
bet tickers and what happened.

Fix: Disable NBA live until investigated. Keep paper data accumulating.

### BUG 5 — DEDUP RESETS AT UTC MIDNIGHT, NOT CST
Minor inconsistency: in-memory _bet_tickers_today and _bet_games_today reset at UTC midnight.
But count_trades_today() uses CST midnight (06:00 UTC). Between 00:00-06:00 UTC, dedup
resets but DB count doesn't — creates window where DB cap is still enforced but in-memory
dedup allows re-betting same game. Real impact: very low (cap catches it). Fix anyway.

---

## WHAT IS ACTUALLY WORKING

**daily_sniper_v1 is a proven edge:**
  - 99% WR on 190 live bets
  - +118.70 USD all-time from this one strategy alone
  - +67.12 USD in April alone
  - Mechanism confirmed: FLB at 90-93c near-expiry KXBTCD markets
  - Conservative cap at 10 USD/bet is correct given the asymmetric payoff

**sports_game_nhl_v1 shows structural promise:**
  - 4 bets, 100% WR, +33.66 USD (avg +8.40/bet)
  - Small sample (need 20+ bets for significance)
  - NHL margins are tighter → less favorite-longshot bias → genuine bookmaker arb edge
  - Needs: more volume, not a different approach

**economics_sniper is untested but has volume:**
  - KXCPI April 10: 1M+ volume market
  - Paper bets should run from April 8 when market opens
  - Live decision April 10 based on paper performance

---

## THE OVERHAUL PLAN

### PHASE 1: STOP THE BLEEDING (immediate, this session or next)

**1A. Disable eth_daily_sniper live execution**
   File: main.py — set live_executor_enabled=False for eth_daily_sniper_loop
   Paper data continues. Re-enable only after fixing the price ceiling (85-88c max).

**1B. Disable NBA live execution**
   File: main.py — remove or paper-only the sports_game_nba_v1 strategy from live path
   Investigate the 2 losing bets first. Too little data, too much loss per bet.

**1C. Fix in-game betting guard**
   File: main.py sports_game_loop — add kalshi_date > now - 5min check before generate_signal()
   This is a one-line fix that blocks all in-game bets.

**1D. Fix betting horizon: 72h → 24h**
   File: main.py sports_game_loop — add 24h horizon check after parsing kalshi_date
   Prevents April 8-9 games from burning the daily cap when April 6 games exist.

**1E. Sort markets by game start time**
   File: main.py sports_game_loop — sort markets by kalshi_date ascending before inner loop
   Ensures today's games are always evaluated before future games.

**1F. Fix dedup reset to CST midnight**
   Already planned. Change _today_utc to _today_cst using UTC+(-6h) offset.

### PHASE 2: ANALYTICS AUDIT (CCA mandate, this session)

Full bet-by-bet review going back to March 1 (all live bets).
Deliverable: strategy P&L table, win rate by price bucket, losing bucket identification.
Questions to answer:
  - Why did NBA lose both bets? Team mapping issue or genuine loss?
  - What price range is ETH daily sniper profitable at?
  - Are the MLB losses correlated with in-game bets (bug) or genuine edge failures?
  - Is the 4-bet NHL sample representative or outlier?
  - Are there any losing buckets in daily_sniper that should be guarded?

### PHASE 3: VOLUME EXPANSION (next 3-5 days)

**3A. Economics sniper live — April 10 (CPI)**
   Already planned. Paper April 8-9. Live April 10 if paper shows expected behavior.
   This is the single highest-confidence expansion path.

**3B. Sports volume increase**
   After Phase 1 fixes: sports should produce 5-10 legitimate bets/day instead of
   8 in-game bets. At 3 USD/bet × 8 bets = 24 USD risked. With 100% WR (NHL model),
   that's meaningful daily contribution.
   NHL is the model. NBA is on hold. MLB needs clean run after bug fix.

**3C. Dynamic Kalshi series discovery**
   Currently: 9 hardcoded sport series keys
   Goal: scan ALL 9,490 Kalshi series dynamically, find open markets by category
   CCA to design. This is the biggest infrastructure uplift.
   Benefits: find new market types (politics, culture, finance) that the bot never sees.
   Will reveal what volumes look like across the whole Kalshi landscape.

**3D. Politics / culture markets**
   Currently: zero coverage
   What exists: election-adjacent markets, award shows, entertainment
   Need: dynamic scan to understand what's available between elections
   CCA to research what has volume NOW

### PHASE 4: STRUCTURAL IMPROVEMENTS (multi-session)

**4A. Per-strategy live caps (not one global cap)**
   NHL: 3 USD (current, correct)
   MLB: 2 USD (lower until in-game bug confirmed fixed and sample grows)
   NBA: paper-only (until investigated)
   Soccer: 2 USD (current)
   NCAAB: paper-only (too sharp)
   Economics: 5 USD (first live run, conservative)

**4B. Sports market quality filters**
   Wire sports_math.py kill switches (already built S165) into sports_game_loop
   Grade A/B/C system should gate bet size, not just fire/no-fire
   Need: Phase 2 sports_expansion efficiency_feed.py for team strength context

**4C. ETH daily sniper fix**
   Lower max_price_cents from 92c to 85c (reduce asymmetric loss risk)
   At 85c: cost = 8.50, payout = 1.50, breakeven = 85%. Achievable.
   Run 10 paper bets at new threshold before live.

**4D. BTC daily sniper volume optimization**
   Currently: uncapped bets per day (good)
   Question: is there a diminishing edge at certain hours or price sub-buckets?
   CCA to analyze: does the 99% WR hold uniformly across times and prices, or are there
   weaker sub-buckets we should guard?

---

## CCA MANDATE FOR THIS SESSION

Post to CCA immediately with these specific requests:

REQUEST A — BET ANALYTICS AUDIT (TODAY)
Full P&L audit, all live bets from March 1 onward. Strategy-by-strategy:
  - Total bets, settled bets, open bets
  - Win rate, average bet size, average P&L per bet
  - P&L by week (trend up or down?)
  - Identify every bucket with WR < 50% and n > 5
  - Specific question: what are the 2 NBA bet tickers? What happened?

REQUEST B — ETH DAILY SNIPER FIX
What price threshold makes eth_daily_sniper positive EV?
  - Current: 91c ceiling, WR 86%, EV = -0.50/bet
  - At 85c: breakeven 85%, need paper data
  - Recommend: new ceiling, run paper validation, live criteria

REQUEST C — IN-GAME BET VALIDATION
Check all open sports_game_mlb_v1 bets (listed above).
For each April 6 game ticker: did the game already complete? What was the result?
This will confirm whether we just lost 10-15 USD on games that were already over.

REQUEST D — DYNAMIC KALSHI SERIES DISCOVERY
Design the KalshiSeriesDiscovery module:
  - Paginated scan of ALL Kalshi series
  - Filter by: open markets, volume > 100, close_time > now
  - Categorize by series type (sports/politics/econ/culture/crypto)
  - Return: volume-ranked list of viable betting categories
  - This replaces the hardcoded 9-series dict permanently

REQUEST E — BTC DAILY SNIPER SUB-BUCKET ANALYSIS
Is the 99% WR uniform? Or are there time-of-day/price-bucket patterns we should guard?
  - Pull all 190 daily_sniper bets from DB
  - Analyze by: hour of day, price (90c vs 91c vs 92c vs 93c), day of week
  - Are there any losing buckets worth guarding?

---

## CODEX MANDATE

Post to Codex via CLAUDE_TO_CODEX.md:

TASK 1: Fix in-game betting guard in sports_game_loop (1-2 hours)
TASK 2: Fix betting horizon 72h → 24h + market sort by game date (1 hour)
TASK 3: Disable eth_daily_sniper live execution pending price fix (30 min)
TASK 4: Disable NBA live execution pending investigation (30 min)
TASK 5: Fix dedup reset UTC → CST midnight (30 min)

---

## WHAT MATTHEW NEEDS TO KNOW

The bot has one proven edge (daily_sniper) that is working well (+67 USD in April).
The sports and ETH sniper additions have been net negative so far due to execution bugs
and incorrect parameter choices. These are fixable — the bugs are specific and the fixes
are clear. The underlying sports edge (NHL 4/4 100% WR) appears real.

The plan: fix the execution, clean up the losers, then expand volume properly.
The timeline: Phase 1 fixes take one session. Phase 2 analytics takes CCA one session.
Phase 3 expansion starts after Phase 1 is validated (2-3 days).

The daily target of 15-25 USD/day requires approximately:
  - daily_sniper: ~8-12 USD/day (current rate in April)
  - sports: ~5-8 USD/day (after fixing, at NHL quality)
  - economics: ~3-5 USD/day (after April 10 CPI live)
  - Total feasible: 16-25 USD/day

April 13 mandate is achievable IF Phase 1 fixes land today/tomorrow.

---

## WHAT STAYS THE SAME

- daily_sniper_v1: untouched, it works
- Paper accumulation for all disabled strategies
- All drift strategies: remain disabled
- 15-min crypto ban: permanent
- HARD_MAX 50 USD
- CST timezone for all P&L tracking
- CCA coordination every monitoring cycle

---

## STATUS TRACKING

Phase 1: NOT STARTED (bot stopped per Matthew)
Phase 2: CCA request being posted now
Phase 3: PENDING Phase 1 completion
Phase 4: PENDING Phase 2 completion

Next session should start with: Phase 1 code changes, bot restart, verify sports loop
produces clean bets (no in-game, today-first ordering, 24h horizon).
