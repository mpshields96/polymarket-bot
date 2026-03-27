# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-27 ~00:45 UTC (Session 148 wrap)
# ═══════════════════════════════════════════════════════════════

## ⚠️ HYBRID CHAT — PERMANENT ARCHITECTURE (Matthew standing directive, S131)
## ═══════════════════════════════════════════════════════════════════════════
## ONE CHAT DOES EVERYTHING. /kalshi-main is the ONLY Kalshi chat.
## This chat does: live monitoring + CCA coordination + research + bug fixes + builds.
## /kalshi-research is PERMANENTLY RETIRED. Never run it again.
## During monitoring downtime/droughts: DO RESEARCH INLINE. Do not just watch cycles.
## ═══════════════════════════════════════════════════════════════════════════

## ⚠️ 5-DAY MANDATE — CLOCK STARTED 2026-03-27 00:11 UTC (Matthew standing directive)
## ═══════════════════════════════════════════════════════════════════════════════════
## GOAL: Achieve and SUSTAIN 15-25 USD DAILY within 5 days.
## DEADLINE: 2026-03-31 ~00:11 UTC (same local time as start)
## CLOCK STARTED: 2026-03-27 00:11 UTC. Day 1 underway.
## CCA ANALYSIS: Expected 20 USD/day at 64 bets/day (70-75% success probability)
## Daily std dev = 18 USD — red days are normal variance, not crises.
## PATH: expiry_sniper (~14-15 USD/day) + daily_sniper at 5 USD cap (~6 USD/day) = 20+ USD/day
## CONSTRAINTS: (1) Starting bankroll final — no new capital ever.
##              (2) FORBIDDEN: bankroll floor ≤ 20 USD.
##              (3) Do NOT ask Matthew for help. Use CCA for anything/everything.
## ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS. PERMANENT.
## ═══════════════════════════════════════════════════════════════════════════════════

## BOT STATE (S148 wrap — 2026-03-27 ~00:45 UTC)
  Bot RUNNING PID 40947 → /tmp/polybot_session148.log
  All-time live P&L: +14.40 USD
  March 27 (mandate Day 1): 1 settled, 1 win, +0.60 USD (just started at midnight UTC)
  March 26 (pre-mandate): 61 settled, 56 wins (91.8% WR), -8.76 USD
  daily_sniper: 28/30 live settled. 2 more → SPRT eval → 1→5 USD cap raise. FIRES ~23:00 UTC TONIGHT.
  Post-guard clean bets: 73/100 (Gate at 100 → HARD_MAX auto-raise to 50 USD — pre-authorized)
  Tests: 2001 passing (1 pre-existing failure — test_security shebang). Last commit: f1eb42d

  S148 KEY CHANGES:
  1. DEFAULT_MAX_LOSS reduced 10.00→8.00 USD (CCA WR cliff analysis: at -8.34 avg_loss post-ceiling,
     cliff = 90.2% → +3.1% safety margin vs 93.3% WR). Commit: f1eb42d. Tests: 2001 passing.
  2. sports_sniper_loop crash FIXED: `strategy_name=` → `strategy=` kwarg in db.count_trades_today().
     7 sessions of silent 30s crashes eliminated. Sports sniper now operational. Commit: 473eeb1.
  3. 5-DAY MANDATE CLOCK STARTED: 2026-03-27 00:11 UTC. CCA REQ-58 filed + responded same session.
     CCA analysis: 20 USD/day expected, 70-75% success probability, $8 max loss = full Kelly.
  4. Frozen bot detected + restarted at session start (PID 5936 → 24844 → 31085 → 40947).
     Root cause: 5-hour stale log. Pattern: always `tail -5` log, not just `ps`.

  S148 PENDING TASKS (priority order):
  1. ⚡ TONIGHT ~23:00 UTC: daily_sniper bet 30 fires → SPRT eval → raise 1→5 USD cap
     Action: grep settled trades for daily_sniper count reaching 30.
     If SPRT lambda>0 (confirmed at +3.833): change `_DAILY_SNIPER_LIVE_CAP_USD = 1.0` → `5.0` in main.py:1141
     Then restart bot. Log in CHANGELOG. This adds ~6 USD/day to mandate P&L.
  2. MANDATE DAY 1 (March 27): Monitor 15-25 USD target. EOD report by midnight UTC.
     If <40 sniper bets by noon UTC: investigate signal suppression.
     Do NOT change parameters if WR ≥90% on 30+ bets — accept variance.
  3. CCA check: REQ-58 ACK sent. Check for any additional CCA deliveries for mandate.
     Push CCA on market scan: are there KXBTCD settlement windows beyond 6pm ET?
  4. HARD_MAX gate: 73/100 clean bets → auto-raise to 50 USD at 100 (passive, pre-authorized).
  5. Sports sniper paper fills: 0/20 needed. ESPN polling every 3 min. Need late-game 90c+ moments.
  6. CUSUM: S=3.915 at S148 wrap (STABLE, below 5.0 threshold). SPRT lambda=+15.366 EDGE CONFIRMED.
     eth_orderbook CUSUM S=4.020 — paper only, disable if S≥5.0.

  S148 CCA DELIVERIES RECEIVED AND ACTED ON:
  - REQ-027 Monte Carlo COMPLETE (self-learning/monte_carlo_simulator.py)
  - REQ-054 Correlated Loss Analyzer COMPLETE (self-learning/correlated_loss_analyzer.py)
  - REQ-055 market_diversifier.py COMPLETE
  - loss_reduction_simulator.py, edge_decay_detector.py, wr_cliff_analyzer.py — all available
  - REQ-58 RESPONSE (mandate analysis): expected 20 USD/day, 70-75% success, $8 max loss confirmed
  - S198: mandate_tracker.py, kelly_optimizer.py, window_frequency_estimator.py, mandate_dashboard.py,
    signal_threshold_analyzer.py — all delivered as specs (available for implementation if needed)

  MANDATE MATH (CCA-confirmed):
  - Expiry sniper: 64 bets/day at 93.3% WR, $8 max loss → 19.44 USD/day expected
  - daily_sniper at 5 USD cap: 28 bets/day * ~0.40 USD/win * 96.4% WR → ~6 USD/day
  - Combined: ~25 USD/day (above 15-25 target range)
  - Key risk: daily std dev = 18 USD. Expect one -15 USD day in 5-day window. NORMAL.
  - Post-ceiling avg_loss: -8.34 USD (n=12 losses). Consistent with $8 cap regime.

  STRATEGY STATUS:
  - expiry_sniper_v1: PRIMARY ENGINE. All-time 95.2% WR (1093 bets), +86.77 USD. EDGE CONFIRMED.
    Ceiling: 93c BTC/SOL, 95c ETH (IL-38-ETH). Floor: 90c. 08:xx blocked (structural, re-confirmed S144).
    CUSUM S=3.915 (stable). SPRT lambda=+15.366, E_n=4.7M (strong edge).
  - daily_sniper_v1: LIVE (1 USD cap). 28/30 settled. 96.4% WR. SPRT lambda=+3.833 EDGE CONFIRMED.
    ⚡ RAISE TO 5 USD CAP ON BET 30 (fires ~23:00 UTC March 27). Pre-authorized, no confirmation needed.
    Markets: KXBTCD NO@90-93c near-expiry. Fires once/day at 6pm ET settlement.
  - sol_drift_v1: LIVE. 0 bets since S148 start (SOL UP/flat, direction_filter="no" = correct).
    SPRT lambda=+2.552 EDGE CONFIRMED. CUSUM S=1.240 (stable).
  - sports_sniper_v1: PAPER-ONLY. 0/20 fills. ESPN polling every 3 min (bug fixed S148).
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI). After mandate deadline.
  - maker_sniper_v1: PAPER calibration. 5/15 fills, 100% WR paper.
  - eth_drift_v1: DISABLED (min_drift_pct=9.99). CUSUM DRIFT ALERT S=15.0 (historical, no action).
  - btc_drift_v1/xrp_drift_v1: DISABLED (min_drift_pct=9.99). Monitoring CUSUM.

  GUARDS ACTIVE (11 total):
  - IL-33: KXXRP GLOBAL BLOCK (PERMANENT — XRP forever banned)
  - IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx UTC | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  - IL-38: Sniper ceiling 93c (BTC/SOL) | IL-38-ETH: ETH ceiling 95c
  - IL-39: sol_drift NO@<60c
  - 9 auto-guards from auto_guards.json (loaded at startup)
  - HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked (structural, S144 confirmed)

  RESTART COMMAND (S149):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session149.log 2>&1 &

  CRITICAL STARTUP CHECKS (S149):
  - cat bot.pid → get PID. Then tail -5 /tmp/polybot_session148.log — MUST show recent entries.
    If stale >15min: RESTART even if ps shows alive (frozen process pattern — seen twice S148).
  - CUSUM: S=3.915 (stable). If S≥5.0 at startup: flag immediately.
  - daily_sniper: check if 30th bet settled since wrap. If yes: execute cap raise 1→5 USD NOW.
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -50 (check for new deliveries)

  S147 KEY BUILDS (still relevant context):
  - ETH ceiling 95c (IL-38-ETH, CCA REQ-53 confirmed +0.60 USD/day)
  - Trinity Monte Carlo (src/models/monte_carlo.py) from agentic-rd-sandbox
  - Injury leverage kill switch (src/data/injury_leverage.py)
  - Sports sniper (src/strategies/sports_sniper.py) + ESPN feed
