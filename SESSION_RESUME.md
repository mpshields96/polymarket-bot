SESSION RESUME — auto-updated by /polybot-wrap at session end.
Do NOT edit manually. Read by /polybot-init at session start.

═══════════════════════════════════════════════════
MAIN CHAT PROMPT — SESSION 161 (2026-04-02)
═══════════════════════════════════════════════════

--- SESSION 161 START ---
Bot: STOPPED (stale PID 87224) | Last log: /tmp/polybot_session159.log
All-time P&L: +69.89 USD | Need 55.11 more to +125 target
Bankroll: ~202 USD | Tests: 2019 passing | Last commit: fd223f0
Guards: 11 auto-guards (0 new) + 19 ILs active

MANDATE DEADLINE: 2026-04-03 ~00:11 UTC — 15-25 USD/day ACHIEVE AND SUSTAIN. TOMORROW.

PREVIOUS SESSION: S160 — 0 new settled bets. Bot stopped March 29. 4 days of missed income.
15 OPEN LIVE TRADES: KXBTCD-26MAR2903 daily_sniper bets — settlement loop will resolve on restart.

PRIME DIRECTIVE: Make 15-25 USD TODAY. Bot has been down 4 days. Every hour counts.
ABSOLUTE FREEDOM DIRECTIVE: Do literally anything on Kalshi. No strategy sacred. No approval needed.
ONE RULE: bankroll must never drop below 20 USD.

STARTUP SEQUENCE:
1. Run restart command below
2. tail -f /tmp/polybot_session161.log | grep -E "LIVE BET|settled|WIN|LOSS|ERROR|CRITICAL"
3. ./venv/bin/python3 scripts/auto_guard_discovery.py (guard check — 11 unchanged, 0 new expected)
4. ./venv/bin/python3 main.py --health (verify clean)
5. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -100 (CCA deliveries)

RESTART COMMAND (Session 161):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session161.log 2>&1 &

STRATEGY STANDINGS (2026-04-02):
  expiry_sniper_v1: PRIMARY — 90-94c profitable, 95-98c guarded (11 auto + 19 ILs)
  daily_sniper_v1: EDGE CONFIRMED (SPRT lambda=+15.2, CUSUM S=3.8 stable)
  btc_drift_v1: NEUTRAL — 80 bets, 50% WR — filter to 'no' side
  eth_drift_v1: UNDERPERFORMING — 46% WR, declining
  sol_drift_v1: HEALTHY — 47 bets, 66% WR
  orderbook_imbalance_v1: PAPER — 205 bets, needs live decision

GOAL TRACKER:
  All-time: +69.89 USD | Need: 55.11 more to +125 | Deadline: 2026-04-03

HYBRID CHAT: /kalshi-research PERMANENTLY RETIRED. This chat does everything.
Use /polybot-auto after startup. Research inline during downtime.
Budget: 30% of 5-hour token limit MAX. Model: Opus 4.6. Full autonomy active.

Go. Restart the bot. Make money today.
--- END SESSION 161 PROMPT ---

Live terminal feed:
  tail -f /tmp/polybot_session161.log | grep --line-buffered -iE "LIVE BET|LIVE.*execute|kill.switch|hard.stop|settled|WIN|LOSS|expiry_sniper|daily_sniper|consecutive|bankroll|restart|ERROR|CRITICAL"
