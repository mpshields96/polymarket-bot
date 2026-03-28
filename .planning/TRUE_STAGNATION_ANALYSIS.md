# TRUE STAGNATION ANALYSIS — PERMANENT REFERENCE
# Written: 2026-03-24 (Session 129)
# NEVER DELETE. EVERY FUTURE SESSION MUST READ THIS.
# Source: Matthew's explicit correction of prior wrong analysis (S129 directive)

## MATTHEW'S DIRECTIVE (S129 — word for word)
"Leak 2 (drift strategies) did cause a loss of money, but leak 2 wasn't responsible
for losses for the past 2 weeks and there's more than just leak 1 causing our losses
over 2 weeks, we've lost a fuck ton elsewhere. We don't build on trauma. But we
analyze our bet results and see the numbers and become smarter and stop being so blind."

## WHAT THE S128 REPORT GOT WRONG
The S128 full spectrum report oversimplified the 2-week stagnation as two leaks:
  "Leak 1: NO@95c (-41.67 USD)" and "Leak 2: Drift strategies (-69.29 USD)"
This was WRONG in two ways:
  1. Drift strategies were MINOR contributors to the recent 2 weeks — their historical
     losses accumulated over months. During March 10-23, drift added ~-59 USD total,
     much of which was from eth_drift/eth_orderbook which were still running early March.
  2. The REAL causes of the 2-week P&L hole are MULTIPLE and BEYOND NO@95c.

## REAL BREAKDOWN — PAST 14 DAYS (DB-verified, March 10-23 2026)

### SNIPER TOXIC ZONE LOSSES (all-time, but most fired in the 14-day window):
  YES sub-90c: n=13, WR=77%, PnL=-36.91 USD (floor guard not yet in place)
  NO  sub-90c: n=4,  WR=75%, PnL=-14.37 USD (same)
  YES 96-99c:  n=125, WR=96%, PnL=-67.24 USD (ceiling guard not yet in place)
  NO  96-99c:  n=61,  WR=95%, PnL=-38.60 USD (same)
  NO  95c:     n=85,  WR=94%, PnL=-41.67 USD (now fixed: IL-36)

  TOTAL sniper toxic zone: -198.79 USD

### CRASH AMPLIFICATION — March 15 and March 17:
  March 17: sniper fired 128 bets at 92% WR = -67.81 USD in ONE DAY
  March 15: sniper fired 190 bets at 95% WR = -48.92 USD in ONE DAY
  Root cause: during high-volatility crash, sniper fired sub-90c bets (floor not yet active)
  AND fired many 96-99c bets (ceiling not yet active). Each loss at extreme prices costs ~20 USD.
  Sub-90c big losses:
    March 17: YES@88c -19.36, NO@89c -19.58 = -38.94 USD from sub-90c alone
    March 15: YES@83c -18.26, YES@86c -19.78 = -38.04 USD from sub-90c alone
  LESSON: The crash was a sniper problem caused by missing floor/ceiling guards — NOT a market
  event that required a "crash pause" mechanism. The guards ARE the fix.

### DRIFT STRATEGY DAMAGE (14 days, real DB numbers):
  eth_drift_v1:                 n=136, PnL=-27.93 USD (disabled during period)
  eth_orderbook_imbalance_v1:   n=15,  PnL=-18.20 USD (live for part of period)
  sol_drift_v1:                 n=34,  PnL=-15.74 USD (disabled March 22)
  xrp_drift_v1:                 n=51,  PnL=-3.80 USD  (disabled earlier)
  btc_drift_v1:                 n=40,  PnL=+5.59 USD  (disabled March 23)
  TOTAL DRIFT 14 DAYS: -59.08 USD
  NOTE: Drift losses during this period are real but NOT the dominant cause.
  The dominant cause was the sniper firing in toxic zones during crash days.

## CURRENTLY ACTIVE WATCH BUCKETS (not yet guarded):
  NO@92c: n=34, WR=91%, BE=92%, PnL=-14.16 USD, p=0.52 (not significant yet — watch at 50)
  YES@94c: n=66, WR=95%, BE=94%, PnL=-2.36 USD, p=0.77 (marginal, monitor)
  NOTE: do NOT add guards prematurely. Wait for p<0.20 auto-guard threshold.

## STATUS OF FIXES:
  Floor guard (sub-90c blocked): ACTIVE — prevents crash-day sub-90c sniper losses
  Ceiling guard (96-99c blocked): ACTIVE — prevents high-price sniper losses
  NO@95c: FULLY BLOCKED across all 4 assets (IL-24/34/36 + auto-guards)
  Drift strategies: ALL DISABLED (btc/eth/sol/xrp all at min_drift_pct=9.99)
  With all fixes active: clean zone is YES@90-95c + NO@90-94c = +258.71 USD all-time

## FORWARD ANALYSIS PROTOCOL (Matthew's standing directive):
1. NEVER simplify "what caused losses" to 1-2 leaks. Run the actual DB queries.
2. ALWAYS break down by: (side × price_cents) AND (daily × strategy)
3. LOOK AT THE BIGGEST INDIVIDUAL LOSSES first — they reveal the real cause.
4. Ask: "were these causes active during the period in question?" Check guard timelines.
5. Use CCA's analytical tools (trading_analysis_runner.py, strategy_health_scorer.py)
   in addition to the local scripts. CCA has better tooling.
6. Matthew gave monitoring chat full access to CCA's tools (S129 — PERMANENT authorization).

## CCA TOOL ACCESS — PERMANENT AUTHORIZATION (Matthew S129)
Matthew explicitly: "You have my permission for access to USE those tools effectively."
  CCA trading analysis runner: python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/self-learning/trading_analysis_runner.py --db data/polybot.db
  CCA strategy health scorer: python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/self-learning/strategy_health_scorer.py --db data/polybot.db
  Research outcomes tracker: python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/self-learning/research_outcomes.py list
  CCA inbox (write requests): ~/.claude/cross-chat/POLYBOT_TO_CCA.md
  CCA deliveries (read/implement): ~/.claude/cross-chat/CCA_TO_POLYBOT.md

## DO NOT REPEAT THESE ANALYSIS ERRORS:
  ERROR 1: "Leak 2 (drift) caused the 2-week stagnation" — WRONG. Drift was a minor
    contributor during this period. The sniper's own toxic zones caused most damage.
  ERROR 2: "One cause explains the stagnation" — WRONG. Multiple overlapping sources.
  ERROR 3: Summarizing P&L without running actual DB queries first.
  ERROR 4: Treating the 14-day loss data as equivalent to all-time data.
  ERROR 5: Forgetting to ask "when was this guard added?" before attributing historical losses.
