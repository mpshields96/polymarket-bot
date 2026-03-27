# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-27 ~22:25 UTC (Session 149 wrap)
# ═══════════════════════════════════════════════════════════════

## ⚠️ READ FIRST: .planning/MATTHEW_DIRECTIVES.md — VERBATIM MANDATE DIRECTIVES (S150, 2026-03-27)
## ══════════════════════════════════════════════════════════════════════════════════════
## MANDATE: 15-25 USD/day by 2026-03-31. ANY market. ANY strategy. Figure it out.
## ABSOLUTE FREEDOM DIRECTIVE: DO LITERALLY ANYTHING ON KALSHI. No strategy is sacred.
## No framework is required. No approval needed. Bet anything, any size, any market.
## ONE RULE ONLY: bankroll must never drop below 20 USD. Matthew will NOT add more funds.
## Everything else — kill switch, Kelly, stage caps, graduation gates — NEGOTIABLE.
## Full directive: .planning/MATTHEW_DIRECTIVES.md (ABSOLUTE FREEDOM DIRECTIVE section)
## ══════════════════════════════════════════════════════════════════════════════════════

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
## CLOCK STARTED: 2026-03-27 00:11 UTC. Day 1 reporting at midnight UTC.
## CCA ANALYSIS: Expected 20 USD/day at 64 bets/day (70-75% success probability)
## Daily std dev = 18 USD — red days are normal variance, not crises.
## PATH: expiry_sniper (~14-15 USD/day) + daily_sniper at 5 USD cap (~6 USD/day) = 20+ USD/day
## CONSTRAINTS: (1) Starting bankroll final — no new capital ever.
##              (2) FORBIDDEN: bankroll floor ≤ 20 USD.
##              (3) Do NOT ask Matthew for help. Use CCA for anything/everything.
## ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS. PERMANENT.
## ═══════════════════════════════════════════════════════════════════════════════════

## BOT STATE (S150 — 2026-03-27 ~23:15 UTC)
  Bot RUNNING PID 88935 → /tmp/polybot_session150.log
  All-time live P&L: +15.16 USD
  March 27 today (mandate Day 1 in progress): +1.36 USD (10 settled live, 9/10 = 90% WR)
    - expiry_sniper: 9/9 wins +4.36 USD today
    - sol_drift: 0/1 wins -3.00 USD today
  daily_sniper: 28/30 live settled. ⚡ FIRES IMMINENT. On bet 30: raise cap 1→5 USD.
  Post-guard clean bets: 82/100 (Gate at 100 → HARD_MAX auto-raise to 50 USD — pre-authorized)
  Tests: 2001 passing (1 pre-existing failure — test_security shebang). Last commit: 4776a15

  S150 KEY CHANGES (sizing mandate):
  1. KELLY_FRACTION: 0.25 → 0.85 (85% Kelly for 5-day mandate)
  2. ABSOLUTE_MAX_USD: 15.00 → 25.00
  3. DEFAULT_MAX_LOSS_USD: 8.00 → 22.00 (kill-switch-safe max: ($200-$20)/8 = $22.50)
  4. Stage 2 cap: 10→25 USD, pct 5%→11% ($22 at $200 bankroll)
  5. Stage 3 cap: 15→25 USD, pct 4%→9%
  Expected daily P&L: 42 bets × 93% WR × $1.91/win ≈ $13/day sniper
    + daily_sniper@5 USD ≈ $6/day = ~$19/day total (mandate target: 15-25 USD)

  S149 KEY CHANGES:
  1. mandate_monitor.py deployed to scripts/ (CCA S199 delivery). Tracks mandate daily P&L.
     Usage: ./venv/bin/python3 scripts/mandate_monitor.py status
     Record Day 1 at midnight UTC: python3 scripts/mandate_monitor.py record 1 <pnl> <bets> <wins>
  2. Ceiling guard confirmed working S149: 97c/98c YES and NO correctly blocked all session.
     Auto-guard discovery: 0 new guards fired. Guard stack clean at 9 auto-guards + IL guards.
  3. CUSUM improved: S=3.330 (was 3.915 at S148 wrap). SPRT lambda=+16.040 (was +15.366).
     E_n=9.2M (was 4.7M). Edge strengthening.
  4. sol_drift fired 1 live bet today at -3.00 USD loss. SPRT lambda=+2.277 still positive.
     CUSUM S=1.800 (stable). No action — single bet within normal variance.

  S149 PENDING TASKS (priority order):
  1. ⚡ IMMINENT (~23:00 UTC March 27): daily_sniper bet 30 fires → raise cap 1→5 USD
     Action: check DB count reaching 30.
     If SPRT lambda>0 (confirmed at +3.833): change `_DAILY_SNIPER_LIVE_CAP_USD = 1.0` → `5.0` in main.py:1141
     Restart bot to session149.log. Log in CHANGELOG. Adds ~6 USD/day to mandate P&L.
  2. MANDATE DAY 1 EOD: Record result in mandate_monitor.py at midnight UTC March 28.
     python3 scripts/mandate_monitor.py record 1 <pnl> <bets> <wins> <losses>
     (pnl = today's live P&L at midnight UTC, from DB query settled_at >= 1774569600)
  3. MANDATE DAYS 2-5: Target 15-25 USD/day. Day 1 ended at +1.36 USD (below target).
     Day 2 starts at midnight UTC March 28. Daily_sniper at 5 USD cap will add ~6 USD/day.
  4. HARD_MAX gate: 82/100 clean bets → auto-raise to 50 USD at 100 (passive, pre-authorized).
  5. Sports sniper paper fills: 0/20 needed. ESPN polling every 3 min.
  6. CUSUM: S=3.330 (stable, improved). SPRT lambda=+16.040. If S≥5.0: flag immediately.
     eth_orderbook CUSUM: check at startup. Last known S=3.960 (paper only, disable if S≥5.0).

  S148 CCA DELIVERIES (still relevant):
  - REQ-027 Monte Carlo COMPLETE (self-learning/monte_carlo_simulator.py)
  - REQ-054 Correlated Loss Analyzer COMPLETE (self-learning/correlated_loss_analyzer.py)
  - REQ-058 RESPONSE: expected 20 USD/day, 70-75% success, $8 max loss confirmed. No new edges in 5 days.
  - S199: mandate_monitor.py DEPLOYED to scripts/. mandate_tracker.py, kelly_optimizer.py,
    window_frequency_estimator.py, mandate_dashboard.py, signal_threshold_analyzer.py available in CCA.

  MANDATE MATH (CCA-confirmed):
  - Expiry sniper: 64 bets/day at 93.3% WR, $8 max loss → 19.44 USD/day expected
  - daily_sniper at 5 USD cap (IMMINENT): 28 bets/day * ~0.40 USD/win * 96.4% WR → ~6 USD/day
  - Combined: ~25 USD/day (above 15-25 target range)
  - Key risk: daily std dev = 18 USD. Expect one -15 USD day. NORMAL.
  - Day 1 result: +1.36 USD (10 settled, 90% WR) — below target. Note: heavy volatility (1-99c swings)
    reduced sniper windows. Day 2 should include daily_sniper at 5 USD cap = +6 USD/day boost.

  STRATEGY STATUS:
  - expiry_sniper_v1: PRIMARY ENGINE. CUSUM S=3.330 (stable, improved). SPRT lambda=+16.040 EDGE CONFIRMED.
    E_n=9.2M. Ceiling: 93c BTC/SOL, 95c ETH. Floor: 90c. 08:xx blocked.
    Today: 9/9 wins +4.36 USD. Market was extremely volatile (1-99c swings limited windows).
  - daily_sniper_v1: LIVE (1 USD cap). 28/30 settled. 96.4% WR. ⚡ FIRES TONIGHT 23:00 UTC.
    ⚡ RAISE TO 5 USD CAP ON BET 30. Pre-authorized. SPRT lambda=+3.833 confirmed.
  - sol_drift_v1: LIVE. 1 bet today (-3.00 USD loss). SPRT lambda=+2.277 EDGE CONFIRMED.
    CUSUM S=1.800 (stable). direction_filter="no". Single loss within normal variance.
  - sports_sniper_v1: PAPER-ONLY. 0/20 fills. ESPN polling every 3 min.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI). After mandate deadline.
  - eth_drift_v1: DISABLED (min_drift_pct=9.99). CUSUM DRIFT ALERT S=15.0 (historical, no action).
  - btc_drift_v1/xrp_drift_v1: DISABLED (min_drift_pct=9.99).

  GUARDS ACTIVE (11 total):
  - IL-33: KXXRP GLOBAL BLOCK (PERMANENT — XRP forever banned)
  - IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx UTC | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  - IL-38: Sniper ceiling 93c (BTC/SOL) | IL-38-ETH: ETH ceiling 95c
  - IL-39: sol_drift NO@<60c
  - 9 auto-guards from auto_guards.json (loaded at startup). 0 new guards S149.
  - HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked (structural, S144 confirmed)

  RESTART COMMAND (S151):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session151.log 2>&1 &

  CRITICAL STARTUP CHECKS (S151):
  - cat bot.pid → get PID. Then tail -5 /tmp/polybot_session150.log — MUST show recent entries.
    If stale >15min: RESTART to session151.log (frozen process pattern).
  - CUSUM: S=3.330 (stable). If S≥5.0 at startup: flag immediately.
  - daily_sniper: CHECK IMMEDIATELY if 30th bet settled since wrap.
    ./venv/bin/python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); n=c.execute(\"SELECT COUNT(*) FROM trades WHERE strategy='daily_sniper_v1' AND is_paper=0 AND result IS NOT NULL\").fetchone()[0]; print(f'daily_sniper settled: {n}/30')"
    If 30+: IMMEDIATELY change main.py:1141 _DAILY_SNIPER_LIVE_CAP_USD = 1.0 → 5.0, restart bot.
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -50 (check for new deliveries)
  - Record mandate Day 1 if midnight UTC has passed: python3 scripts/mandate_monitor.py status

  S147-S148 KEY BUILDS (still relevant):
  - ETH ceiling 95c (IL-38-ETH, CCA REQ-53)
  - DEFAULT_MAX_LOSS 8.00 USD (CCA WR cliff analysis S148)
  - sports_sniper_v1 ESPN feed + main.py loop (paper, bug fixed S148)
  - Trinity Monte Carlo (src/models/monte_carlo.py)
  - mandate_monitor.py deployed scripts/ (S149, CCA S199)
