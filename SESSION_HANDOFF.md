# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-14 (Session 68 — research: NCAAB monitor, sniper bucket analysis)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 69)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 69).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 68 wrap — 2026-03-14 ~17:35 UTC):
  Bot RUNNING PID 17982 — log at /tmp/polybot_session68.log
  Sniper: 168 live settled total, 122W/1L today (+60.92 USD — exceptional day!)
  btc_drift + eth_drift MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone. MONITOR THIS.
  All-time live P&L: +17.11 USD (was -34.53 at S67 start = +51.64 gained!)
  Tests: 1140 passing. Last commit: e624877 (S68 NCAAB monitor + research)

RESTART COMMAND (Session 69):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session69.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": The March 1 hard stop event is HISTORICAL (30% lifetime stop was DISABLED in S34). No lock file = safe to restart. Proceed.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 68 wrap — 2026-03-14 17:35 UTC):
  Bot: RUNNING PID 17982 → /tmp/polybot_session68.log
  All-time live P&L: +17.11 USD (was -34.53 at S67 start = massive gain in 2 sessions)
  Bankroll: ~90+ USD (DB authoritative — check --report)
  Tests: 1140 passing
  Last commit: e624877 (S68 research)

SESSION 68 KEY CHANGES (autoresearch session):
  1. RESEARCH: Sniper price bucket analysis — 90-94c = profit engine (ROI 5.6%)
  2. RESEARCH: 95-96c bucket = nearly break-even (0.4% ROI). DO NOT raise threshold to 95c.
  3. NEW CODE: scripts/ncaab_live_monitor.py (research tool, ESPN + Kalshi live cross-check)
  4. NEW TESTS: tests/test_ncaab_monitor.py (10 tests, all passing)
  5. CONFIRMED DEAD ENDS: BCH/BNB/ADA/DOGE inactive, FOMC no liquidity, KXMVE not tradeable
  6. CONFIRMED: Sniper expected daily P&L = 25-40 USD calm / 60-80 USD volatile

RISK NOTE FOR SESSION 68:
  Daily loss (live) = 14.40 / 22.31 USD (65%). This is the ONE sniper loss today.
  If another large loss fires today: daily loss counter hits 65%+, approaching soft cap display.
  Soft stop is DISABLED so bot keeps trading. But watch for consecutive losses.
  At 15 USD/bet, 2 consecutive losses = -28 USD drawdown on ~89 USD bankroll = painful.

PENDING TASKS (Session 69 — PRIORITY ORDER):

  #1 MONITOR BOT — all clear. 0 consecutive losses. Sniper at 99% WR.
     If 3+ consecutive losses: note it. Bot keeps trading (soft stop disabled).
     If 5+ consecutive losses: consider pausing manually (Matthew decision).

  #2 SOL STAGE 2 GRADUATION — STILL 2 MORE BETS NEEDED!
     28/30 live bets. 2 more settled → Stage 2 analysis (10 USD max/bet eval).
     Run --graduation-status each check. THIS IS THE BIGGEST LEVER.

  #3 GEFS WEATHER TEST (Monday only — March 16):
     HIGHNY markets only open weekdays. Compare GEFS probs to Kalshi prices.
     If GEFS finds >5% edge in uncertain brackets (~50c), weather is viable.

  #4 SNIPER THRESHOLD ANALYSIS — COMPLETED S68. KEY FINDING:
     DO NOT raise trigger to 95c. 90-94c bucket is the profit engine (5.6% ROI).
     95-96c bucket has 0.4% ROI — nearly break-even. Threshold stays at 90c.

  #5 NCAA TOURNAMENT BRACKET (Selection Sunday March 15):
     Bracket announced today (March 15) at 6pm ET. Markets open tonight/Monday.
     1-vs-16 games: 99%+ historical WR. If Kalshi opens at 90c for 1-seed = edge.
     Run scripts/ncaab_live_monitor.py (research only, no auto-trading).
     Current sniper handles ONLY crypto 15-min — NCAA needs separate logic.

125 USD PROFIT GOAL:
  All-time: +17.11 USD. Need +107.89 more.
  At 25-40 USD/day (calm) or 60-80 USD/day (volatile): 2-5 days to goal!
  Key levers: (1) sniper at 15 USD cap sustaining 90c+ opportunities,
  (2) sol_drift Stage 2 graduation (10 USD max/bet, Brier 0.176 = excellent),
  (3) avoid consecutive losses (each costs 14+ USD now)

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
  No kill_switch.lock file exists. Bot ran fine since March 1 with 89+ sniper bets.
  DO NOT be blocked by this. Just restart normally.

MATTHEW'S STANDING DIRECTIVES:
  Fully autonomous always. Do work first, summarize after.
  Never ask for confirmation on: tests, reads, edits, commits, restarts, reports.
  Bypass permissions mode: ACTIVE.
  Goal: +125 USD all-time profit. URGENT. Claude Max renewal depends on this.
  Explicit directive: 100 USD profit in 10 days — hence the 15 USD bet cap.
  Budget: 30% of 5-hour token limit. Model: Opus 4.6.

RESEARCH FILES (for context if continuing R&D):
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S66 tennis/NCAAB in-play at end)
  scripts/edge_scanner.py — reusable Kalshi-vs-Pinnacle scanner tool
  tests/test_edge_scanner.py — 27 tests
