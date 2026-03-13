# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-13 (Session 63 wrap — RESEARCH session, GEFS ensemble + post_only)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 64)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 64).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 63 wrap — 2026-03-13 ~16:00 CDT / 21:00 UTC):
  Bot STOPPED — was stopped S61, research-only S62+S63. Must restart for S64 monitoring.
  Sniper: 39W/2L all-time (95.1%) — ABOVE breakeven. pct_cap float fix deployed.
  btc_drift + eth_drift remain MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone (no sol signals in S61-S63).

RESTART COMMAND (Session 64):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session64.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 63 wrap — 2026-03-13 21:00 UTC):
  Bot: STOPPED (research-only session — no live bets)
  All-time live P&L: -45.60 USD (unchanged — bot was off)
  Bankroll: ~54.40 USD
  Tests: 1127 passed, 3 skipped (26 new tests this session)
  Last commits: 9fda952 (research doc) + ecc5641 (post_only) + 1bb7107 (GEFS wiring) + 718fcdc (GEFS feed)

SESSION 63 WAS A RESEARCH SESSION (not monitoring):

  1. GEFS 31-MEMBER ENSEMBLE WEATHER FEED (BUILT + TESTED):
     GEFSEnsembleFeed class in src/data/weather.py — fetches all 31 GEFS ensemble members
     from Open-Meteo free API. Replaces parametric N(mu,3.5F) with empirical bracket
     probabilities (count members in bracket / 31). 21 new tests, wired into main.py
     and weather strategy. Zero weather trades ever recorded — old model never fired.

  2. POST_ONLY MAKER ORDER SUPPORT (BUILT + TESTED):
     KalshiClient.create_order() now accepts post_only and expiration_ts params.
     live.execute() passes them through. trading_loop gains maker_mode param.
     When True: post_only=True with 30s auto-cancel. Saves ~75% on fees for drift.
     NOT YET ACTIVATED — pass maker_mode=True in main.py when ready. 5 new tests.

  3. EVENING EDGE SCANNER RESULTS:
     77 games matched near game time. Max taker edge 2.4% (NCAAB).
     RECONFIRMS: Kalshi sports efficiently priced even near tip-off. Dead end.

SESSION 63 SELF-RATING: B
  Built 2 concrete deliverables with 26 new tests. No new edge found, but tools
  ready to test when HIGHNY markets open Monday. Sports dead end reconfirmed.

PENDING TASKS (Session 64 — PRIORITY ORDER):

  #1 RESTART BOT — it's been stopped since S61. Every hour off = money lost.

  #2 TEST GEFS VS LIVE HIGHNY MARKETS (Monday only — weekday markets):
     Run GEFS ensemble feed and compare empirical probabilities to HIGHNY prices.
     If GEFS finds >5% edge where old parametric model didn't, weather is viable.

  #3 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled -> milestone.

  #4 ACTIVATE maker_mode=True FOR DRIFT (when comfortable):
     Pass maker_mode=True to btc_drift + eth_drift trading_loop() calls.
     Saves ~5c/trade. Low risk — post_only rejected orders just don't fill.

  #5 MONITOR SNIPER:
     39W/2L all-time (95.1%). pct_cap float fix deployed.

125 USD PROFIT GOAL:
  All-time: -45.60 USD. Need +170.60 more.
  Key levers: (1) sniper accumulates at 0.17/win, (2) sol 2 from Stage 2,
  (3) losers contained at micro-live, (4) post_only saves ~10 USD over 200 trades

RESPONSE FORMAT RULES (permanent — both mandatory):
  RULE 1: NEVER markdown table syntax (| --- |) — wrong font in Claude Code UI.
  RULE 2: NEVER dollar signs in prose — triggers LaTeX math mode.
  USE: "40.09 USD" or "P&L: -39.85". NEVER "$40.09".
  Matthew will terminate chat for violations of either rule.

DIRECTION FILTER SUMMARY (permanent):
  btc_drift: filter="no"  — only NO bets (MICRO-LIVE)
  eth_drift: filter="yes" — only YES bets (MICRO-LIVE)
  sol_drift: filter="no"  — only NO bets (STAGE 1)
  xrp_drift: filter="yes" — only YES bets (MICRO)

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. Urgent. Claude Max renewal depends on this.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.

RESEARCH FILES (for context if continuing R&D):
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (19 sections, S63 additions at end)
  scripts/edge_scanner.py — reusable Kalshi-vs-Pinnacle scanner tool
  tests/test_edge_scanner.py — 27 tests
