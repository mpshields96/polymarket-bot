# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-13 (Session 64 wrap — research + monitoring, bot restarted)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 65)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 65).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 64 wrap — 2026-03-13 ~17:40 CDT / 22:40 UTC):
  Bot STOPPED by Matthew — will need restart for Session 65.
  Sniper: 42 live settled (95.2% WR). pct_cap fix active.
  btc_drift + eth_drift MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone.

RESTART COMMAND (Session 65):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session65.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": The March 1 hard stop event is HISTORICAL (30% lifetime stop was DISABLED in S34). No lock file = safe to restart. Proceed.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 64 wrap — 2026-03-13 22:40 UTC):
  Bot: STOPPED (Matthew stopping for the day)
  All-time live P&L: -44.90 USD (improved +0.70 from -45.60 in S63)
  Bankroll: ~89.56 USD (DB value — higher than S63 handoff, DB is authoritative)
  Tests: 1127 passed, 3 skipped (no code changes this session)
  Last commit: 4ff17d8 (S63 wrap docs)

SESSION 64 WAS A RESEARCH + MONITORING SESSION:

  1. BOT RESTARTED (was stopped since S61):
     PID 10100 → /tmp/polybot_session64.log
     All loops running clean. No blockers.

  2. SNIPER PRICE BUCKET ANALYSIS (key finding):
     90-94c: 21 bets, 90.5% WR, -3.01 USD (marginally unprofitable at breakeven)
     95-99c: 20 bets, 100% WR, +2.60 USD (profitable)
     CONCLUSION: Sample too small (42 total) to make threshold changes yet.
     Need 200+ before raising min from 90c to 95c.
     EV per bet: +0.007 USD. At 40 bets/day = +0.28 USD/day.

  3. CRYPTO 15-MIN EXPANSION: IMPOSSIBLE
     Checked BNB/BCH/ADA/DOGE/LINK — all have 0 open 15-min markets.
     Only BTC/ETH/SOL/XRP exist. Sniper volume ceiling confirmed.

  4. SPORTS SCANNER (afternoon run):
     All 3 "edges" were from in-progress games (fake edges from live vs pre-game odds).
     Pre-game max: ~2.4% taker — dead end confirmed for 3rd time.

  5. ETH_DRIFT MICRO-LIVE CONFIRMED:
     Today's -14.26 USD eth_drift loss was from PRE-DEMOTION full-size bets.
     Current bets: 1 contract (~0.35-0.49 USD each). Going forward: negligible impact.

SESSION 64 SELF-RATING: C+
  Restarted bot (good). Research found no new edge. Failed to activate maker_mode=True
  (built in S63, still not wired). Sports/crypto expansion dead ends confirmed again.

PENDING TASKS (Session 65 — PRIORITY ORDER):

  #1 RESTART BOT — stopped by Matthew end of S64.

  #2 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled → Stage 2 milestone.

  #3 ACTIVATE maker_mode=True FOR DRIFT (15 min of work!):
     ALREADY BUILT in S63. Just needs main.py wiring.
     Pass maker_mode=True to btc_drift + eth_drift trading_loop() calls.
     Saves ~5c/trade. Low risk — post_only rejected orders just don't fill.
     This is the easiest win available. Do it in Session 65.

  #4 GEFS WEATHER TEST (Monday only):
     Wait for HIGHNY markets Monday. Compare GEFS ensemble probs to Kalshi prices.
     If GEFS finds >5% edge where old parametric didn't, weather is viable.

  #5 SNIPER THRESHOLD ANALYSIS (when 200+ live bets):
     Currently only 42 live settled. At 200+ bets, revisit whether to raise
     min price from 90c to 95c (95-99c bucket profitable, 90-94c marginal).

  #6 NON-CRYPTO SNIPER EXPANSION:
     Research whether sports in-game markets (e.g. NBA game winner last 2 min)
     trade at 90c+ and could expand sniper volume. No development yet.

125 USD PROFIT GOAL:
  All-time: -44.90 USD. Need +169.90 more.
  Key levers: (1) sniper at +0.28 USD/day = 609 days at current rate (too slow!),
  (2) sol 2 from Stage 2, (3) maker_mode saves ~10 USD over 200 drift trades,
  (4) need higher-EV sniper volume or new strategy

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

IMPORTANT — MARCH 1 HARD STOP IN --health (not a blocker):
  --health shows HARD STOP from 2026-03-01. This is HISTORICAL.
  The 30% lifetime stop was DISABLED in Session 34 (restore_realized_loss is display-only).
  No kill_switch.lock file exists. Bot ran fine since March 1 with 42+ sniper bets.
  DO NOT be blocked by this. Just restart normally.

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. Urgent. Claude Max renewal depends on this.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.

RESEARCH FILES (for context if continuing R&D):
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S64 bucket analysis at end)
  scripts/edge_scanner.py — reusable Kalshi-vs-Pinnacle scanner tool
  tests/test_edge_scanner.py — 27 tests
