# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-27 ~23:20 UTC (Session 150)
# ═══════════════════════════════════════════════════════════════

## ⚠️ READ FIRST: .planning/MATTHEW_DIRECTIVES.md — VERBATIM MANDATE DIRECTIVES (S150, 2026-03-27)
## ══════════════════════════════════════════════════════════════════════════════════════
## MANDATE: 15-25 USD/day by 2026-03-31. ANY market. ANY strategy. Figure it out.
## ABSOLUTE FREEDOM DIRECTIVE: DO LITERALLY ANYTHING ON KALSHI. No strategy is sacred.
## No framework is required. No approval needed. Bet anything, any size, any market.
## ONE RULE ONLY: bankroll must never drop below 20 USD. Matthew will NOT add more funds. EVER.
## Everything else — kill switch, Kelly, stage caps, graduation gates — ALL NEGOTIABLE.
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
## PATH: expiry_sniper (~13/day at new sizing) + daily_sniper at 5 USD cap (~6 USD/day) = ~19/day
## CONSTRAINTS: (1) Starting bankroll final — no new capital EVER. Matthew is explicit.
##              (2) FORBIDDEN: bankroll floor ≤ 20 USD.
##              (3) Do NOT ask Matthew for help. Use CCA for anything/everything.
## ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES ALL CONSERVATIVE CONSTRAINTS BELOW EXCEPT FLOOR.
## ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS. PERMANENT.
## ═══════════════════════════════════════════════════════════════════════════════════

## BOT STATE (S150 — 2026-03-27 ~23:20 UTC)
  Bot RUNNING PID 88935 → /tmp/polybot_session150.log
  All-time live P&L: +15.16 USD
  March 27 today (mandate Day 1 in progress): +1.36 USD (10 settled live, 9/10 = 90% WR)
    - expiry_sniper: 9/9 wins +4.36 USD today
    - sol_drift: 0/1 wins -3.00 USD today
  daily_sniper: 28/30 live settled. ⚡ FIRES IMMINENT. On bet 30: raise cap 1→5 USD.
  Post-guard clean bets: 82/100 (Gate at 100 → HARD_MAX auto-raise to 50 USD — pre-authorized)
  Tests: 2001 passing (1 pre-existing failure — test_security shebang). Last commit: c35bc77

  S150 KEY CHANGES:
  1. ABSOLUTE FREEDOM DIRECTIVE added — Matthew explicit standing order. Overrides all frameworks.
  2. KELLY_FRACTION: 0.25 → 0.85 (85% Kelly for 5-day mandate)
  3. ABSOLUTE_MAX_USD: 15.00 → 25.00
  4. DEFAULT_MAX_LOSS_USD: 8.00 → 22.00 (kill-switch-safe max: ($200-$20)/8 = $22.50)
  5. Stage 2 cap: 10→25 USD, pct 5%→11% ($22 at $200 bankroll)
  6. Stage 3 cap: 15→25 USD, pct 4%→9%
  Expected daily P&L: 42 bets × 93% WR × $1.91/win ≈ $13/day sniper
    + daily_sniper@5 USD ≈ $6/day = ~$19/day total (mandate target: 15-25 USD)

## PENDING TASKS (priority order)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — if any task below conflicts with making 15-25 USD/day, drop it and find a better bet instead.
  1. ⚡ IMMINENT: daily_sniper bet 30 fires → raise cap 1→5 USD
     Action: check DB count reaching 30.
     Change `_DAILY_SNIPER_LIVE_CAP_USD = 1.0` → `5.0` in main.py:1141. Restart bot to session151.log.
  2. MANDATE DAY 1 EOD: Record result at midnight UTC March 28.
     python3 scripts/mandate_monitor.py record 1 <pnl> <bets> <wins> <losses>
     (pnl = today's live P&L at midnight UTC, from DB query settled_at >= 1774569600)
  3. MANDATE DAYS 2-5: Target 15-25 USD/day. Under ABSOLUTE FREEDOM — bet anything that achieves this.
     Do NOT restrict to current strategies if they're not hitting the target.
  4. HARD_MAX gate: 82/100 clean bets → auto-raise to 50 USD at 100 (passive, pre-authorized).
  5. CUSUM: S=3.330 (stable). SPRT lambda=+16.040. If S≥5.0: flag immediately.

## STRATEGY STATUS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these strategies are tools, not laws.
  ⚠️ If a strategy is not contributing to 15-25 USD/day, abandon it and find something that does.

  - expiry_sniper_v1: PRIMARY ENGINE. CUSUM S=3.330 (stable). SPRT lambda=+16.040 EDGE CONFIRMED.
    Ceiling: 93c BTC/SOL, 95c ETH. Floor: 90c. 08:xx blocked.
    Today: 9/9 wins +4.36 USD.
  - daily_sniper_v1: LIVE (1 USD cap → raising to 5 USD on bet 30). 28/30 settled. 96.4% WR.
  - sol_drift_v1: LIVE. SPRT lambda=+2.277 edge confirmed. CUSUM S=1.800 stable.
  - sports_sniper_v1: PAPER-ONLY. 0/20 fills. ESPN polling every 3 min.
  - economics_sniper_v1: PAPER-ONLY. First bets April 8 (KXCPI).
  - eth_drift_v1: DISABLED (min_drift_pct=9.99).
  - btc_drift_v1/xrp_drift_v1: DISABLED (min_drift_pct=9.99).

## GUARDS ACTIVE (11 total)
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — guards are risk management suggestions, not laws.
  ⚠️ Under the directive, any guard can be suspended if doing so moves toward 15-25 USD/day
  ⚠️ and bankroll stays above 20 USD. Use judgment.

  - IL-33: KXXRP GLOBAL BLOCK (PERMANENT — XRP forever banned, Matthew explicit)
  - IL-34: KXBTC NO@95c | IL-35: KXSOL 05:xx UTC | IL-36: KXETH NO@95c | IL-24: KXSOL NO@95c
  - IL-38: Sniper ceiling 93c (BTC/SOL) | IL-38-ETH: ETH ceiling 95c
  - IL-39: sol_drift NO@<60c
  - 9 auto-guards from auto_guards.json (loaded at startup).
  - HOUR BLOCK: frozenset({8}) — 08:xx UTC blocked

## SIZING PARAMETERS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — these are the current defaults, not hard limits.
  ⚠️ Under the directive, bet whatever size achieves 15-25 USD/day. Floor: bankroll > 20 USD.

  KELLY_FRACTION = 0.85
  ABSOLUTE_MAX_USD = 25.00
  DEFAULT_MAX_LOSS_USD = 22.00
  HARD_MAX_TRADE_USD = 35.00 (kill_switch)
  Stage 1 (bankroll < 100): max 5 USD, 5% bankroll
  Stage 2 (bankroll 100-250): max 25 USD, 11% bankroll
  Stage 3 (bankroll 250+): max 25 USD, 9% bankroll

## KILL SWITCH PARAMETERS
  ⚠️ ABSOLUTE FREEDOM DIRECTIVE OVERRIDES — kill switch is a safety suggestion, not a law.
  ⚠️ Under the directive, these thresholds can be adjusted to enable the mandate target.
  ⚠️ The ONE inviolable rule: bankroll must never drop below 20 USD.

  consecutive_loss_limit = 8 (→ 2hr cooling)
  daily_loss_cap = DISABLED
  bankroll_floor = 20 USD (INVIOLABLE — this one cannot be overridden)

## RESTART COMMAND (S151)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session151.log 2>&1 &

## CRITICAL STARTUP CHECKS (S151)
  - cat bot.pid → get PID. Then tail -5 /tmp/polybot_session150.log — MUST show recent entries.
    If stale >15min: RESTART to session151.log (frozen process pattern).
  - daily_sniper: CHECK IMMEDIATELY if 30th bet settled.
    ./venv/bin/python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); n=c.execute(\"SELECT COUNT(*) FROM trades WHERE strategy='daily_sniper_v1' AND is_paper=0 AND result IS NOT NULL\").fetchone()[0]; print(f'daily_sniper settled: {n}/30')"
    If 30+: IMMEDIATELY change main.py:1141 _DAILY_SNIPER_LIVE_CAP_USD = 1.0 → 5.0, restart bot.
  - cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -50 (check for new deliveries)
  - Record mandate Day 1 if midnight UTC has passed: python3 scripts/mandate_monitor.py status
  - READ .planning/MATTHEW_DIRECTIVES.md — ABSOLUTE FREEDOM DIRECTIVE section. Then ask:
    "Am I on track for 15-25 USD today?" If NO: stop and find a different bet. Any market.

## CCA DELIVERIES (still relevant)
  - REQ-027 Monte Carlo COMPLETE (self-learning/monte_carlo_simulator.py)
  - REQ-054 Correlated Loss Analyzer COMPLETE (self-learning/correlated_loss_analyzer.py)
  - S199: mandate_monitor.py DEPLOYED to scripts/.

## KEY BUILDS (still relevant)
  - ETH ceiling 95c (IL-38-ETH, CCA REQ-53)
  - sports_sniper_v1 ESPN feed + main.py loop (paper, bug fixed S148)
  - Trinity Monte Carlo (src/models/monte_carlo.py)
  - mandate_monitor.py deployed scripts/ (S149, CCA S199)
