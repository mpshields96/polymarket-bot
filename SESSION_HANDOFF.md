# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-04-07 23:45 UTC (S169 wrap)
# ═══════════════════════════════════════════════════════════════

## ⚠️ READ FIRST: .planning/MATTHEW_DIRECTIVES.md — VERBATIM MANDATE DIRECTIVES (S150, 2026-03-27)
## ══════════════════════════════════════════════════════════════════════════════════════
## MANDATE: 15-25 USD/day ACHIEVE AND SUSTAIN. ANY market. ANY strategy. Figure it out.
## Deadline: April 13 (extended from April 3).
## ABSOLUTE FREEDOM DIRECTIVE: DO LITERALLY ANYTHING ON KALSHI. No strategy is sacred.
## ONE RULE ONLY: bankroll must never drop below 20 USD. Matthew will NOT add more funds. EVER.
## ══════════════════════════════════════════════════════════════════════════════════════

## ⚠️ HYBRID CHAT — PERMANENT ARCHITECTURE (Matthew standing directive, S131)
## ONE CHAT DOES EVERYTHING. /kalshi-main is the ONLY Kalshi chat.
## /kalshi-research is PERMANENTLY RETIRED. Never run it again.

## BOT STATE (S169 wrap — 2026-04-07 23:45 UTC)
  Bot: RUNNING PID 23626 → /tmp/polybot_session169.log
  All-time live P&L: +131.04 USD | Today CST April 7: +0.60 USD (1 settled, 1 win)
  Tests: 2337 passing, 3 skipped. Last commits: a92fc86 (MLB paper-only), c548fc5 (max_days_ahead)

  S169 COMPLETED:
  ✅ Restarted bot to session169.log (was on stale PID 303 from S168)
  ✅ Wired PDO kill switch into sports_game.py generate_signal() (NBA only, static snapshot)
  ✅ Fixed _last_fetch_ts=float("-inf") in weather.py (4 classes) + fred.py — is_stale always True before first fetch
  ✅ Added max_days_ahead=1.5 (36h) filter to SportsGameStrategy — blocks games 2+ days out (commit c548fc5)
  ✅ MLB moved to paper-only: 1/7 WR on settled bets. Root causes: (a) in-game guard bug APR06 (CCA says already fixed ddfdd4f), (b) efficiency_feed uses 2024 ERA (2 years stale for 2026 season), (c) no per-game starting pitcher signal (commit a92fc86)
  ✅ REQ-093 (MLB analysis) + REQ-094 (starting pitcher mandate) posted to CCA
  ✅ 4 SIGTERMs throughout session (2 unexplained external ~15min apart, 2 from manual kills)

## HOT UPDATE — Codex MLB Review + Wiring
  ✅ Reviewed CCA REQ-094 deliverable and wired MLB probable-pitcher signal into `src/strategies/sports_game.py`
  ✅ Corrected CCA sketch issues in live code: game date now resolves from ticker/game time, not subtitle text; away-side pitcher edge now boosts away bets correctly; pitcher kill switch now applies side-specifically to YES and NO paths
  ✅ Added regression coverage for MLB pitcher side-selection + away-side edge scoring
  ✅ Targeted verification after patch: `249 passed` across `test_sports_game`, `test_sports_math`, `test_sports_clv`, `test_mlb_pitcher_feed`, `test_sports_analytics`
  ⚠️ MLB remains PAPER-ONLY. Pitcher wiring is complete, but 2026 efficiency data is still pending before any live re-enable discussion.

  PENDING TASKS (priority order — Session 170):
  1. MLB paper validation after pitcher wiring
     Starting pitcher data is now wired. Next step: collect clean paper sample with the pitcher kill switch + edge bonus active, then reassess MLB edge quality.
  2. Check if 9 open daily_sniper bets (KXBTCD-26APR0720-T68299-70599) settled after 20:00 UTC
     BTC was ~72,330 USD — all YES bets should WIN (thresholds 68299-70599, all below BTC price)
     Query: SELECT ticker,side,result,pnl_cents/100.0 FROM trades WHERE ticker LIKE 'KXBTCD-26APR0720%' AND is_paper=0
  3. Open sports bets: 11 total (7 MLB April 8, 1 MLB April 7 in-game, 3 UCL April 14)
     UCL April 14 bets: PSG YES 2.80, BAR YES 2.88, BMU NO 2.64 — 2nd legs, 8 days out when placed
  4. CPI April 10: confirm KXCPI open April 8, run cpi_release_monitor.py April 10 08:28 ET
  5. NHL tonight April 7: NSH@ANA, VGK@VAN, SEA@MIN, CGY@DAL — all show negative edge, monitoring
  6. SIGTERM mystery: bot received 2 unexplained SIGTERMs at 18:05 and 18:20 CDT (15min apart)
     Pattern: ~15min cycles. Investigate if macOS app management or another Claude process is culprit.
  7. Efficiency_feed.py MLB data: update to 2026 season stats (or drop MLB from efficiency ratings)
     NBA data also likely stale — review after starting pitcher work complete.
  8. polybot-auto.md and polybot-init.md size audit — both approaching limits (check wc -c)

  RESTART COMMAND (Session 170):
  kill -9 $(ps -A -o pid,args | grep "main.py" | grep -v grep | awk '{print $1}') 2>/dev/null; sleep 2; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session170.log 2>&1 & sleep 5 && ps -A -o pid,args | grep "main.py" | grep -v grep | awk '{print $1}' > bot.pid && echo "PID=$(cat bot.pid)"

  NOTE: ps aux | grep "[m]ain.py" DOES NOT WORK on this machine — macOS truncates the long Python path.
  Use: ps -A -o pid,args | grep "main.py" | grep -v grep
  OR:  kill -0 $(cat bot.pid) 2>/dev/null && echo "ALIVE" || echo "DEAD"

## STRATEGY STATUS
  ⚠️ ALL 15-MINUTE CRYPTO MARKETS PERMANENTLY BANNED FROM LIVE. No exceptions.

  - daily_sniper_v1: LIVE (10 USD cap, 10 bets/day). PRIMARY ENGINE. +118.70 USD all-time. 99% WR.
    SNIPER RESETS: 06:00 UTC = 01:00 AM CDT (NOT midnight UTC, NOT midnight CST).
  - sports_game_nhl_v1: LIVE (3 USD cap). 4/4 wins, +33.66 USD all-time. PROFITABLE.
  - sports_game_mlb_v1: PAPER-ONLY (0 USD cap). Starting pitcher feed is wired; still need 2026 efficiency data + paper validation.
  - sports_game_nba_v1: PAPER-ONLY (0 USD cap). Only 2 settled bets (old, pre-cap).
  - sports_game soccer (EPL/UCL/Bundesliga/SerieA/LaLiga/Ligue1): LIVE (2 USD cap each).
    max_days_ahead=1.5 (36h) now active — no more 3-day-out soccer bets.
  - eth_daily_sniper_v1: PAPER-ONLY. Was disabled S167 BUG-C. Ceiling 85c. Accumulating data.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI). Live decision April 10.
  - expiry_sniper_v1: PAPER-ONLY. PERMANENTLY BANNED from live (15-min crypto ban).
  - All 15-min crypto strategies: PAPER data only. LIVE=BANNED.

## STRATEGY ANALYZER INSIGHTS (S169)
  - SNIPER: Profitable buckets: 90-94c. Guarded: 95-98c. EDGE CONFIRMED.
  - btc_drift_v1: NEUTRAL — 80 live bets, 50% WR, -9.53 USD [direction filter "no" active]
  - eth_drift_v1: UNDERPERFORMING — 46% WR below break-even. DISABLED.
  - sol_drift_v1: HEALTHY — 47 live bets, 66% WR, -15.68 USD (still accumulating data)
  - All-time: +131.04 USD (86% WR, 1696 bets)

## GUARDS ACTIVE
  - IL-33: KXXRP GLOBAL BLOCK (PERMANENT)
  - IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx UTC | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  - IL-38: Sniper ceiling 93c (BTC/SOL) | IL-38-ETH: ETH ceiling 95c | IL-39: sol_drift NO@<60c
  - 9 auto-guards from auto_guards.json (loaded at startup)
  - HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked

## SIZING PARAMETERS
  KELLY_FRACTION = 0.85
  ABSOLUTE_MAX_USD = 25.00
  DEFAULT_MAX_LOSS_USD = 22.00
  HARD_MAX_TRADE_USD = 50.00
  Stage 2 (bankroll 100-250): max 25 USD, 11% bankroll
  Stage 3 (bankroll 250+): max 25 USD, 9% bankroll

## KILL SWITCH PARAMETERS
  consecutive_loss_limit = 8 (→ 2hr cooling)
  daily_loss_cap = DISABLED
  bankroll_floor = 20 USD (INVIOLABLE)

## STOP COMMAND (clean shutdown)
  PID=$(cat bot.pid) && kill -TERM "$PID"
  Wait until: kill -0 "$PID" 2>/dev/null fails. Then rm -f bot.pid if needed.

## CRITICAL STARTUP CHECKS
  - kill -0 $(cat bot.pid) 2>/dev/null && echo "ALIVE" || echo "DEAD"
  - ps -A -o pid,args | grep "main.py" | grep -v grep  (correct method on this machine)
  - ⚠️ TIMEZONE: Machine is CDT (UTC-5). Log 18:xx = 23:xx UTC. Always convert.
  - MONITORING: ALWAYS query DB for bet counts. Never trust log tail alone.

## CCA COMMS STATE
  REQ-093: MLB overnight loss analysis — awaiting CCA response (filed S169)
  REQ-094: Starting pitcher data — DELIVERED by CCA and reviewed by Codex; wiring landed locally
  CCA latest delivery: REQ-094 pitcher feed was directionally right, but Codex corrected the wire-in details in `sports_game.py`
  Cross-chat: ~/.claude/cross-chat/ | Board: cross_chat_board.py brief

## KEY BUILDS (still relevant)
  - sports_math.py (S165): kill switches, grade tiers, collar checks
  - efficiency_feed.py (S167): adj_em ratings NBA/NHL — MLB data STALE (2024 ERA)
  - sports_inplay_sniper (S168): calculate_size bug fixed
  - PDO kill switch (S169): wired into sports_game.py NBA path
  - max_days_ahead=1.5 filter (S169): blocks 2+ day future games
  - MLB paper-only (S169): starting pitcher wiring complete; pending 2026 efficiency refresh + paper sample
