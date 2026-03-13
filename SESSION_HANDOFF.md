# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-13 (Session 62 wrap — RESEARCH session, edge scanning + FOMC analysis)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 63)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 63).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 62 wrap — 2026-03-13 ~09:30 CDT / 14:30 UTC):
  Bot STOPPED — was stopped S61, research-only S62. Must restart for S63 monitoring.
  Sniper: 39W/2L all-time (95.1%) — ABOVE breakeven. pct_cap float fix deployed.
  btc_drift + eth_drift remain MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone (no sol signals in S61 or S62).

RESTART COMMAND (Session 63):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session63.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 62 wrap — 2026-03-13 14:30 UTC):
  Bot: STOPPED (research-only session — no live bets)
  All-time live P&L: -45.60 USD (unchanged — bot was off)
  Bankroll: ~54.40 USD
  Tests: all passing (27 new tests added for edge scanner)
  Last commits: b846343 (FOMC analysis) + 920db9d (edge scanner) + e191b4d (audit)

SESSION 62 WAS A RESEARCH SESSION (not monitoring):

  1. EDGE SCANNER BUILT (scripts/edge_scanner.py, 27 tests):
     Kalshi-vs-Pinnacle sports price comparison tool.
     Scanned 170 Kalshi sports markets. Result: efficiently priced (0-3% edge, fees eat it).
     Dead end confirmed: sports taker arbitrage is NOT profitable.

  2. FOMC LIVE MARKET ANALYSIS:
     Fetched live FRED data: yield spread 0.00%, CPI accelerating.
     March 19 meeting fully priced at 99c hold — zero edge.
     Our FOMC model is BROKEN: no term structure (outputs 83% hold for ALL meetings).
     FOMC strategy NOT ready for live activation.

  3. LIMIT ORDER (post_only) ANALYSIS:
     Maker fee = 25% of taker fee. Drift savings: 5c/trade. Sniper savings: ~0c.
     Implementation: add post_only=True to KalshiClient.create_order() for drift.

  4. DEAD ENDS CONFIRMED:
     - Sports taker arbitrage (Kalshi efficiently priced vs Pinnacle)
     - BALLDONTLIE API (overpriced vs existing the-odds-api)
     - FOMC model live activation (broken term structure)
     - Mid-range drift optimization (Whelan paper kills this)

  5. NEW COMMANDS:
     /polybot-autoresearch — autonomous research sessions
     /polybot-wrapresearch — research session wrap-up

SESSION 62 KEY FINDING:
  SNIPER VOLUME IS THE ONLY VALIDATED LEVER.
  39W/2L at 95.1% win rate — favorite-longshot bias is structural (Whelan, Snowberg-Wolfers).
  At 2.69 USD/bet: each win ~0.17 USD. Need ~1000 wins over ~50 days.
  If bankroll recovers to 100 USD: each win ~0.35 USD. Timeline halves.
  PRIORITY: restart bot, let sniper accumulate, watch sol graduation.

PENDING TASKS (Session 63 — PRIORITY ORDER):

  #1 RESTART BOT — it's been stopped since S61. Every hour off = money lost.

  #2 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled -> milestone.
     When it hits 30: check --graduation-status. If Brier < 0.25:
     present Stage 2 promotion analysis (10 USD max bet, up from 5).

  #3 MONITOR SNIPER:
     39W/2L all-time (95.1%). pct_cap float fix deployed.
     Watch: win rate trend, correlation risk, fee impact at low bankroll.

  #4 IMPLEMENT post_only MAKER ORDERS (when time permits):
     Add post_only=True to KalshiClient for drift strategies.
     Saves ~5c/trade. Implementation: 2-3 hours. Low risk.
     Details: .planning/EDGE_RESEARCH_S62.md Section 14.

  #5 BANKROLL CONCERN (unchanged from S61):
     Bankroll at ~54 USD. Max bet = min(5.00, 54*0.05-0.01) = 2.69 USD.
     Sniper bets are SMALLER now. Each win ~0.12-0.19 USD vs ~0.25-0.35 before.

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
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (16 sections)
  scripts/edge_scanner.py — reusable Kalshi-vs-Pinnacle scanner tool
  tests/test_edge_scanner.py — 27 tests
