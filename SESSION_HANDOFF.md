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

## BOT STATE (S170 wrap — 2026-04-08 01:45 UTC)
  Bot: RUNNING PID 23626 → /tmp/polybot_session169.log
  All-time live P&L: +135.26 USD | Today CST April 8: +4.82 USD (11 settled, 10 wins, 90% WR)
  April: 118 settled | 110 wins | +65.37 USD
  Tests: 2398 passing, 3 skipped. Last commit: 8a20675 (test: lock in pitcher-side wiring review)

  S170 COMPLETED:
  ✅ Confirmed 9 daily_sniper KXBTCD-26APR0720 bets ALL SETTLED as WINs (BTC ~72k, above all thresholds)
  ✅ Wired mlb_pitcher_feed.py into sports_game.py generate_signal() (commit fb9e476)
     - pitcher_kill_switch() applied to YES/NO paths independently (direction-aware)
     - ERA edge pts boost sharp score before send (+0-10 pts based on ERA quality)
     - Away-side pitcher correctly boosted for away bets
  ✅ Corrected CCA sketch issues: game date from ticker/game_time, away-side logic, side-specific kill
  ✅ Added regression tests for pitcher side-selection (commit 8a20675)
  ✅ Wired sports CLV tracking into settlement path
     - live.execute now persists `signal_price_cents` for live sports trades
     - settlement_loop now calls `sports_clv.maybe_log_clv_for_trade()` for `sports_game*` trades when signal/fill/close prices exist
     - CLV log now measures whether sports entries beat the close instead of relying on P&L only
  ✅ Confirmed KXCPI open (81 markets April 8). Economics sniper timing confirmed correct:
     48h gate fires at April 8 12:25 UTC. No fix needed — sniper working as designed.
  ✅ Processed CCA REQ-094 delivery. Posted REQ-095 (NBA PDO playoff threshold) to CCA.
  ✅ 5 monitoring cycles completed. Bot alive all session. 0 new guards from auto_guard_discovery.
  ✅ CUSUM check: eth_drift S=15.0 confirmed expected (disabled strategy, not actionable).
  ⚠️ MLB remains PAPER-ONLY. Pitcher wiring complete. Need 2026 efficiency data + clean paper sample.
  ⚠️ sports_analytics.py still not wired into any operator-facing report path. CLV is now logged, but the full sports performance report is still a latent library, not part of the runtime workflow.

  PENDING TASKS (priority order — Session 171):
  1. UCL 2nd legs April 8 ~19:00 UTC: LFC vs PSG + BAR vs ATM
     Open bets: 14215 NO KXUCLGAME BMU/RMA (April 15), 14216 YES KXUCLGAME BAR (April 14), 14224 YES KXUCLGAME PSG (April 14)
     Check 1st leg results (April 7-8) to assess 2nd leg bet quality
  2. Economics sniper monitoring: starts firing April 8 12:25 UTC (KXCPI 48h window opens)
     Monitor paper bets. Live decision April 10. Run cpi_release_monitor.py at 08:28 ET April 10.
  3. NHL April 8: re-evaluate tonight's games with current data
  4. MLB paper validation: collect clean paper sample with pitcher signal active (wired S170)
  5. SIGTERM mystery: 2 unexplained kills at 18:05 + 18:20 CDT (15min apart). Still open.
  6. NBA PDO playoff threshold (before April 18): CCA REQ-095 filed. Disable or raise PDO kill for playoffs.
  7. sports_analytics.py runtime/report wiring
     CLV now logs automatically, but no session/report command surfaces sports calibration/ROI/CLV summary yet.
  8. Efficiency_feed.py MLB data: 2024 ERA stale. Update or drop MLB from efficiency ratings.

  RESTART COMMAND (Session 171):
  kill -9 $(ps -A -o pid,args | grep "main.py" | grep -v grep | awk '{print $1}') 2>/dev/null; sleep 2; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session171.log 2>&1 & sleep 5 && ps -A -o pid,args | grep "main.py" | grep -v grep | awk '{print $1}' > bot.pid && echo "PID=$(cat bot.pid)"

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

## STRATEGY ANALYZER INSIGHTS (S170)
  - SNIPER: Profitable buckets: 90-94c. Guarded: 95-98c. EDGE CONFIRMED.
  - btc_drift_v1: NEUTRAL — 80 live bets, 50% WR, -9.53 USD [direction filter "no" active]
  - eth_drift_v1: UNDERPERFORMING — 46% WR below break-even. DISABLED.
  - sol_drift_v1: HEALTHY — 47 live bets, 66% WR, -15.68 USD (still accumulating data)
  - All-time: +135.26 USD (85.6% WR, 1706 bets)

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
  REQ-094: Starting pitcher data — DELIVERED + WIRED S170. Pitcher signal active in sports_game.py.
  REQ-095: NBA PDO playoff threshold — FILED S170. Before April 18 playoffs, need to disable or raise PDO kill.
  CCA board: python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/cross_chat_board.py brief
  Cross-chat: ~/.claude/cross-chat/ | Board: cross_chat_board.py brief

## KEY BUILDS (still relevant)
  - sports_math.py (S165): kill switches, grade tiers, collar checks
  - efficiency_feed.py (S167): adj_em ratings NBA/NHL — MLB data STALE (2024 ERA)
  - sports_inplay_sniper (S168): calculate_size bug fixed
  - PDO kill switch (S169): wired into sports_game.py NBA path
  - max_days_ahead=1.5 filter (S169): blocks 2+ day future games
  - MLB paper-only (S169): starting pitcher wiring complete; pending 2026 efficiency refresh + paper sample
  - sports_clv.py: settlement wiring complete; CLV entries now generated for eligible sports_game trades
