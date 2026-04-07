# ACTIVE DIRECTIVES — S269 (April 6-7, 2026)
# Rewrite this at EVERY session start. Max 200 words.
# Read by PostCompact hook. Injected into post-compaction context automatically.

1. **BOT STATUS:** STOPPED (Matthew directive — restart only after all bug fixes verified)

2. **DISABLED STRATEGIES (permanent until gates cleared):**
   - ETH daily sniper: DISABLED (structural negative EV at 91c — see SNIPER_LIMITS_RATIONALE.md)
   - NBA sports_game: DISABLED (0% WR on 2 bets, cause unknown — REQ-082A investigation required)
   - All 15-min crypto (KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M): PERMANENTLY BANNED

3. **TODAY'S PRIORITY (in order):**
   - Fix BUG 1: in-game betting guard (one line, high priority)
   - REQ-082A: pull NBA 2 bet tickers, identify cause of loss
   - Wire sports_math.py (at src/strategies/sports_math.py) into sports_game_loop
   - REQ-082E: BTC sub-bucket analysis by hour/price/day-of-week
   - Restart bot only after all fixes verified

4. **CAPS (non-negotiable):**
   - BTC sniper: $5/bet, max 10 bets/day (near-term, until 500 live bets confirm 99% WR)
   - Sports game: $3/bet (cap), paper mode for NBA/UCL/soccer until validated
   - In-play sports sniper: NOT YET BUILT — paper only when live
   - ETH sniper: PAPER ONLY at ≤85c floor, live gate = 50 bets at WR ≥ 92%

5. **ANTI-CONCENTRATION RULE:**
   - If one strategy exceeds `80%` of trailing profit, do NOT propose another variant of it.
   - Trigger a `build second engine` sprint instead:
     - MLB first
     - NHL second
     - NBA third
     - non-sports market scout in parallel

6. **MANDATORY FIRST STEP:** Read KALSHI_INIT_CHECKLIST.md — all 5 steps — before any code.
