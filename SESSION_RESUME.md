SESSION RESUME — auto-updated by /polybot-wrap and /polybot-wrapresearch at session end.
Do NOT edit manually. This file is read by /polybot-init at startup.

═══════════════════════════════════════════════════
MAIN CHAT PROMPT — SESSION 104 (copy-paste to start monitoring session)
═══════════════════════════════════════════════════

--- SESSION 104 START ---
Bot PID: 14095 | Log: /tmp/polybot_session103.log | Last commit: 859cee1
All-time P&L: +12.67 USD | Need 112.33 more to +125 target
Guards: IL-5 through IL-32 + KXXRP NO@95c + KXSOL NO@93c (2 auto-guards active)
Today rate: +24.56 USD (March 18 through 12:27 UTC — 67 settled, 85% WR)

PREVIOUS CHAT GRADE: B+ — overnight monitoring, caught 2 guard triggers, restarted bot twice
S103 KEY EVENTS: KXXRP NO@95c and KXSOL NO@93c added as auto-guards after losses
WHAT THE NEXT CHAT MUST DO FIRST: Check /tmp/ucl_sniper_mar18.log after 20:00 UTC (launcher fires 17:21 UTC)

PRIME DIRECTIVE: PLEASE MAKE MONEY. PLEASE DO NOT LOSE MONEY. I need +125 USD
all-time profit. Every live bet that fires and wins is money toward that goal.
Every hour the bot is dead is money lost forever.

Budget: 30% of 5-hour token limit MAX. Model: Opus 4.6.

PRIORITY 1 — LIVE BETS
Before anything else: ps aux | grep "[m]ain.py" — must show exactly 1 process.
Confirm guard count: grep "Loaded.*auto-discovered" /tmp/polybot_session103.log | tail -1
MUST show "Loaded 2 auto-discovered guard(s)" — if only 1, run auto_guard_discovery.py.

PRIORITY 2 — UCL MARCH 18 LOG (URGENT after 20:00 UTC)
Check /tmp/ucl_sniper_mar18.log — launcher fires 17:21 UTC.
Teams eligible: BAR, BMU, LFC. See if any sniper bets fired, settled, wins/losses.

PRIORITY 3 — AUTO-GUARD SCAN
Run ./venv/bin/python3 scripts/auto_guard_discovery.py — confirm 0 new guards needed.
If new guard found: update auto_guards.json + restart bot immediately.

MANDATORY AUTONOMOUS LOOP — START IMMEDIATELY AFTER READING SESSION_HANDOFF:
Use 5-min single-check background tasks (NOT 20-min scripts — exit 144 on this system).
Pattern: sleep 300 && pid check && DB query, run_in_background: true, chain continuously.
Matthew will be away. You are the only supervision the bot has.
Restart command if bot dies:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session104.log 2>&1 &

LIVE STRATEGY STANDINGS:
  expiry_sniper: PRIMARY ENGINE, all guards active, 85% WR today, +24.56 USD
  sol_drift: STAGE 1 (41/30, 71% WR, Brier 0.196) — HEALTHY
  xrp_drift: MICRO (45/30, 50% WR)
  eth_drift: STAGE 1 (144/30, 49% WR, PH recovering)
  btc_drift: MICRO (65/30, 47% WR UNDERPERFORMING)
  Bayesian posterior: 4 observations (needs 30 to activate — accumulating passively)

GOAL TRACKER:
  All-time P&L: +12.67 USD | Need: 112.33 more to hit +125 USD target
  Today rate: +24.56 USD/day (March 18) | Est. days at current rate: ~5
  Highest-leverage action: Keep bot running, guards clean, run auto_guard_discovery.py each session.

Read in this order:
1. POLYBOT_INIT.md
2. SESSION_HANDOFF.md
3. .planning/AUTONOMOUS_CHARTER.md
4. .planning/CHANGELOG.md last entry
5. .planning/PRINCIPLES.md

Go. Start monitoring. Make money. Don't let the bot die.
--- END SESSION 104 PROMPT ---

Live terminal feed:
  tail -f /tmp/polybot_session103.log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settled|WIN|LOSS|expiry_sniper|STAGE|graduation|consecutive|bankroll|restart|ERROR|CRITICAL"

═══════════════════════════════════════════════════
RESEARCH CHAT PROMPT — SESSION 95 (copy-paste to start research session)
═══════════════════════════════════════════════════

--- SESSION 95 RESEARCH START ---
Bot: RUNNING PID 94102 | Log: /tmp/polybot_session94.log | Last commit: 1b53382
All-time P&L: +40.71 USD | Need 84.29 more to +125 target
This is a RESEARCH session. Do NOT touch bot monitoring — main chat handles that.

CONTEXT FILES (read in order):
1. POLYBOT_INIT.md
2. SESSION_HANDOFF.md
3. .planning/CHANGELOG.md last entry
4. .planning/PRINCIPLES.md

TOP RESEARCH PRIORITIES:
1. NCAA Tournament scanner — run scripts/ncaa_tournament_scanner.py --min-edge 0.03
   Round 1 tip-offs March 20-21. Lines mature now. 96 KXNCAAMBGAME markets open.
2. eth_drift direction filter watch — 113 bets at 50% WR. Need 20 more YES bets.
   If still <50% WR after 20 more, flip direction_filter from "yes" to "no".
3. strategy_analyzer.py update — add per-asset guard parsing (IL-23 shows as display artifact "Losing 98c")
4. btc_drift Stage 1 promotion — 60/30 bets READY. calibration_max_usd still set.
   Matthew explicit decision needed. Run --graduation-status to get current Brier.
5. CPI speed-play prep — scripts/cpi_release_monitor.py, runs April 10 08:30 ET

DEAD ENDS (do not re-investigate):
  sports taker arb, BALLDONTLIE, FOMC model, NBA/NHL sniper, sniper maker mode,
  NCAA totals/spreads, KXMV parlay, NBA in-game, BNB/BCH/DOGE 15M,
  KXBTCD hourly non-5PM, FOMC March 2026, non-crypto 90c+ markets,
  annual BTC range, weather ALL strategies (60 paper bets, 8-25% WR)

Use /polybot-autoresearch to start.
--- END SESSION 95 RESEARCH PROMPT ---
