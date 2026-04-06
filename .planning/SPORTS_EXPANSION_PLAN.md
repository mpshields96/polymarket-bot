# Sports Betting Expansion Plan — agentic-rd-sandbox Integration
# Created: 2026-04-06 Session 165
# Directive: Steal and clone useful components from agentic-rd-sandbox to improve
# sportsbetting on Kalshi. Achieve consistent 15-25 USD/day by April 13.
# Owner: All future Kalshi chats + CCA chats + Codex
# Status: ACTIVE — implement across multiple sessions

## Context

agentic-rd-sandbox lives at: /Users/matthewshields/Projects/agentic-rd-sandbox/
Matthew's directive: "steal and clone literally anything from it to help sportsbetting
or any betting on Kalshi"

Current sports_game_v1 in Kalshi bot:
- Compares The Odds API sharp consensus vs Kalshi price
- Fires on >5% edge, min 3 books
- Covers: MLB, NBA, NHL, UCL, EPL, BUN, SER, LAL, L1
- Date-aware matching: _parse_ticker_date() extracts game datetime from Kalshi ticker
- No kill switches. No efficiency feed. No injury detection. No PDO.
- Result: misses profitable opportunities and occasionally bets into bad spots.

agentic-rd-sandbox has (verified by reading source):
- math_engine.py (81K): kill switches for NBA/NFL/NHL/NCAAB/soccer/tennis,
  Sharp Score composite ranking, Kelly sizing with grade tiers, no-vig math
- efficiency_feed.py (32K): 250+ teams across 10 leagues, adj_em ratings, static (no API)
- injury_data.py (13K): positional leverage tables, zero external API calls
- nba_pdo.py (17K): PDO regression via nba_api (free), 1-hour TTL cache
- nhl_data.py (12K): goalie detection via free NHL API
- odds_fetcher.py (45K): The Odds API integration with daily budget cap (300 credits)
- parlay_builder.py (12K): Trinity MC parlay construction
- originator_engine.py (15K): Trinity MC core simulation
- calibration.py (13K): line movement / RLM detection
- clv_tracker.py (9K): Closing Line Value tracking

## Phase 1 — Kill Switches + Sharp Score (TODAY, 1-2 hours)
### Goal: Immediately reduce bad bets by applying kill switches to existing sports_game_v1

Components to clone:
1. nba_kill_switch() from math_engine.py → stop betting NBA teams on B2B road games
2. nhl_kill_switch() from math_engine.py → stop betting when backup goalie confirmed
3. passes_collar() / passes_collar_soccer() → tighter odds collar guard
4. implied_probability() + no_vig_probability() → already in sports_game.py but verify
5. assign_grade() → A/B/C grade tiers to filter low-confidence bets

Implementation plan:
- Create src/strategies/sports_math.py — copy all pure math functions from math_engine.py
  (no Streamlit, no odds_fetcher, no scheduler dependencies)
- Modify sports_game.py: apply nba_kill_switch() before placing any NBA bet
- Modify sports_game.py: NHL — skip if backup goalie field present in Odds API response
- Tests: mirror agentic-rd-sandbox doctest patterns

Files to touch: src/strategies/sports_math.py (NEW), src/strategies/sports_game.py,
               tests/test_sports_math.py (NEW), tests/test_sports_game.py

Expected impact: Avoid 1-2 bad NBA/NHL bets per week. Mostly defensive.

## Phase 2 — Efficiency Feed Integration (Next session, 2-3 hours)
### Goal: Use adj_em ratings to require that statistical edge aligns with team quality

Components to clone:
1. efficiency_feed.py → copy wholesale — zero API calls, pure static lookup
   ALL 250+ teams already mapped: NBA/NCAAB/NFL/MLB/MLS/EPL/Bundesliga/Ligue1/Serie A/La Liga
2. efficiency_gap scoring (0-20 pts) → add as filter in sports_game._score_bet()

Key insight: agentic-rd-sandbox uses efficiency_gap as 20 of 100 pts in Sharp Score.
At minimum, use it as a disqualifier: don't bet on a 3% edge if efficiency strongly
disagrees with the direction.

Implementation plan:
- Copy efficiency_feed.py to src/data/efficiency_feed.py (no changes needed)
- Add efficiency_gap to sports_game.py score function
- Require: edge_pct > 0.05 AND efficiency_gap > 0 (team we're backing has advantage)
- OR: edge_pct > 0.10 (large enough to override efficiency)

Files: src/data/efficiency_feed.py (COPY), src/strategies/sports_game.py,
       tests/test_efficiency_feed.py (NEW)

## Phase 3 — NHL Goalie Detection (Next 2 sessions, 3-4 hours)
### Goal: Automatically detect backup goalies via free NHL API, not manual flags

Components to clone:
1. nhl_data.py → copy wholesale — uses official NHL API (free, no key)
   get_starting_goalies() returns dict of {team: goalie_name, is_confirmed: bool}
   60-min TTL cache, graceful fallback

Implementation plan:
- Copy src/data/nhl_data.py
- Wire into sports_game.py NHL loop: before placing any NHL bet, fetch goalie status
- If backup confirmed → apply nhl_kill_switch() → skip or reduce size
- Requires: NHL game must be within 3 hours of game time for goalie data to be accurate

Files: src/data/nhl_data.py (COPY), src/strategies/sports_game.py,
       tests/test_nhl_data.py (COPY/ADAPT)

## Phase 4 — PDO Regression for NBA (2 sessions, research + build)
### Goal: Use PDO (luck normalization) to identify regressing NBA teams

Components to clone:
1. nba_pdo.py → copy wholesale — uses nba_api (free, no key)
   pdo_kill_switch() interface mirrors nhl_kill_switch()
   1-hour TTL, fetches all 30 teams at once

Key mechanic: Teams with PDO >= 102 are "lucky" — fade them. PDO <= 98 → back them.
This is validated R&D from agentic-rd-sandbox S15 analysis.

Implementation plan:
- Copy src/data/nba_pdo.py
- Wire into sports_game.py NBA loop
- Before placing NBA bet: check PDO of BOTH teams
- PDO >= 102 for team we're backing AND spread > -3: skip (luck regression risk)
- PDO <= 98 for team we're backing: add to signal confidence

Files: src/data/nba_pdo.py (COPY), src/strategies/sports_game.py,
       tests/test_nba_pdo.py (COPY/ADAPT)

## Phase 5 — Sharp Score Integration (3+ sessions, full pipeline)
### Goal: Replace simple edge_pct threshold with Sharp Score composite ranking

Components to clone:
1. calculate_sharp_score() from math_engine.py
2. rank_bets() from math_engine.py (applies Sharp Score across a slate of bets)
3. calibration.py → RLM (Reverse Line Movement) detection

Sharp Score = 100-pt composite:
- EDGE (40 pts): (edge% / 10%) × 40
- RLM (25 pts): 25 if confirmed reverse line movement
- EFFICIENCY (20 pts): efficiency gap from efficiency_feed
- SITUATIONAL (15 pts): rest + injury + motivation + matchup

Current threshold: edge_pct > 5% = bet. This is naive.
New threshold: Sharp Score > 45 = bet, > 60 = full size, > 75 = max size

Implementation plan:
- Implement RLM detection by comparing current Kalshi price to opening price
  (Kalshi candlestick API: GET /series/{series}/markets/{market}/candlesticks?period_interval=1)
- Build sports_game._calculate_sharp_score() wrapper
- Store Sharp Score in DB alongside bets for analysis

Files: src/strategies/sports_math.py (extend), src/strategies/sports_game.py,
       src/strategies/sports_rli.py (NEW — RLM detection using Kalshi candlesticks),
       tests/test_sports_math.py, tests/test_sports_game.py

## Phase 6 — Parlay Builder (CCA research + 2-3 sessions)
### Goal: Build Trinity MC-based parlay construction for Kalshi sports markets

Components to clone:
1. originator_engine.py — Trinity Monte Carlo simulation core
2. parlay_builder.py — 2-3 leg parlay construction

Key constraint: Kalshi does not support parlays natively.
Workaround: Place multiple independent bets on same slate. Not true parlays but
correlated exposure management requires the same math.

CCA research needed: Does Kalshi expose any correlated multi-market instruments?
If not, use parlay math for SIZING ONLY (maximize Kelly across correlated same-slate bets).

## Implementation Priority for April 13 Deadline

MUST HAVE (do Phase 1 NOW):
- Kill switches protect from known bad spots
- Grade tiers (A/B/C) increase bet selectivity

SHOULD HAVE (Phase 2-3 by April 10):
- Efficiency feed raises win rate on MLB/NBA
- NHL goalie detection removes biggest single NHL risk

NICE TO HAVE (Phase 4+ after April 13):
- PDO regression: complex, less urgent than kill switches
- Sharp Score: full pipeline, multi-session

## CCA Asks (cross-chat)

1. Which agentic-rd-sandbox components translate best to 2-outcome binary markets?
   (Kalshi is YES/NO, not spread/total — some math doesn't port directly)
2. Does the efficiency_feed's adj_em apply to soccer (EPL/UCL) or just NBA/NFL/MLB?
   La Liga and Serie A adj_em are in the file but verify confidence.
3. For PDO-like normalization in MLB: what's the equivalent metric? BABIP? xFIP?
   (PDO is NBA-specific. CCA to research MLB equivalent for luck normalization.)
4. Can Trinity MC be adapted to size multiple independent Kalshi bets on same slate
   without native parlay support?
5. Research: Does Kalshi provide opening line data or only current price?
   Need for RLM detection. Candlestick API may work (period_interval=1).

## Notes for Future Sessions

- agentic-rd-sandbox CLAUDE.md has full context on each module (52K file)
- agentic-rd-sandbox tests/ has 1154 tests for reference implementations
- All kill switch functions return (bool, str) tuples — simple to wire into sports_game
- No external API keys needed for Phase 1 (pure math) or Phase 2 (static data)
- nhl_data.py and nba_pdo.py DO make external API calls (free APIs) — Phase 3/4
- The Odds API (MARKET_TOKEN) is shared between both projects via .env
- Matthew's .env already has ODDS_API_KEY for polymarket-bot

