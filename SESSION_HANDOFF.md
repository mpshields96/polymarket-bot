# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-14 (Session 70 — critical 99c sniper fix + CPI monitor + FOMC research)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 71)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 71).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 70 wrap — 2026-03-14 ~19:50 UTC):
  Bot RUNNING PID 17982 — log at /tmp/polybot_session68.log
  Sniper: 136 live settled today, 134W/2L (98.5% WR), +50.48 USD today
  btc_drift + eth_drift MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone. MONITOR THIS.
  All-time live P&L: +6.67 USD
  Tests: 1164 passing. Last commit: 8d252ae (sniper 99c price drift guard)

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

SESSION 70 KEY CHANGES (autoresearch — 2026-03-14):
  1. CRITICAL FIX: sniper 99c price drift guard (main.py + 5 tests). Commit: 8d252ae
     Root: generate_signal() rejects 99c (edge < 0) but execution price drifts 97→99c.
     At 99c: min fee (1c) = gross profit (1c) → 0 net. One loss = -14.85 USD, 16 wins = 0 USD.
     Fix: pre-execution price check in live path before orderbook fetch, logs and skips at 99c+.
  2. NEW: scripts/cpi_release_monitor.py + 12 tests. Run April 10, 2026 08:30 ET. Commit: fcedb57
     Polls BLS API + KXFEDDECISION every 10s, detects repricing lag after CPI surprise.
  3. RESEARCH: FOMC chain consistency — no cross-market arb. Near-term markets (MAR/APR)
     priced efficiently by institutions. Far-term violations are liquidity artifacts.
  4. RESEARCH: Sniper maker mode dead end — urgency in final 840s incompatible with maker fills.
  5. Tests: 1164 passing (was 1147)

SESSION 69 KEY CHANGES (kept for context):
  1. FIX: edge_scanner game-in-progress filter added (_game_started() helper, 7 tests)
  2. CONFIRMED DEAD ENDS: KXBTCD near-expiry sniper, NCAA totals/spreads, sports pre-game arb
  3. Tests: 1147 passing (was 1140)

PENDING TASKS (Session 71 — PRIORITY ORDER):

  #1 MONITOR BOT — bot has 99c guard now, but still monitoring needed.
     Sol drift at 28/30 — watch for graduation milestone.

  #2 SOL STAGE 2 GRADUATION — STILL 2 MORE BETS NEEDED!
     28/30 live bets. 2 more settled → Stage 2 analysis (10 USD max/bet eval).
     Run --graduation-status each check. THIS IS THE BIGGEST LEVER.

  #3 GEFS WEATHER TEST (Monday only — March 16):
     HIGHNY markets only open weekdays. Compare GEFS probs to Kalshi prices.
     If GEFS finds >5% edge in uncertain brackets (~50c), weather is viable.

  #3 GEFS WEATHER TEST (Monday only — March 16):
     HIGHNY markets only open weekdays. Compare GEFS probs to Kalshi prices.
     If GEFS finds >5% edge in uncertain brackets (~50c), weather is viable.

  #4 NCAA TOURNAMENT BRACKET (Selection Sunday March 15 — 6pm ET = 23:00 UTC):
     Bracket announced TONIGHT. Markets open tomorrow/Monday.
     1-vs-16 games: 99.4% historical WR (155-1 since 1985). Historical edge confirmed.
     If Kalshi opens 1-seed at 90c → pure favorable-longshot bias = exploit.
     Use scripts/ncaab_live_monitor.py to scan (research only, no auto-trading).
     DO NOT build automated NCAAB trader — settlement timing problem unsolved.

  #5 SNIPER PRICE GUARD — NEEDS BOT RESTART TO TAKE EFFECT
     The 99c pre-execution guard was added to main.py (commit 8d252ae) but the bot
     was NOT restarted (Matthew directive: autonomous restarts require check-in first).
     Restart at next opportunity to activate the 99c guard. Command in RESTART section above.

125 USD PROFIT GOAL:
  All-time: +6.67 USD. Need +118.33 more.
  At 25-40 USD/day (calm) or 60-80 USD/day (volatile): 3-5 days to goal!
  Key levers: (1) sniper at 15 USD cap sustaining 90c+ opportunities,
  (2) sol_drift Stage 2 graduation (10 USD max/bet, Brier 0.176 = excellent),
  (3) 99c guard now coded — once restarted, prevents future -14.85 USD 99c losses
  NOTE: All-time: +6.67 USD today. Today live P&L: +50.48 USD (134/136 = 98.5% WR).

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
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S69 additions at end)
  scripts/edge_scanner.py — Kalshi-vs-Pinnacle scanner (now with game-in-progress filter)
  tests/test_edge_scanner.py — 34 tests
  scripts/ncaab_live_monitor.py — ESPN + Kalshi NCAAB live cross-check tool
