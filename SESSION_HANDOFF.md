# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-14 (Session 65 — maker_mode wired + sports sniper research)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 66)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 66).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 65 wrap — 2026-03-14 ~00:20 CDT / 05:20 UTC):
  Bot RUNNING PID 13072 — log at /tmp/polybot_session65.log
  Sniper: 50 live settled (96% WR), +1.55 USD
  btc_drift + eth_drift MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  maker_mode=True NOW WIRED for btc_drift + eth_drift (post_only, 30s expiration)
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone.

RESTART COMMAND (Session 66):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session66.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": The March 1 hard stop event is HISTORICAL (30% lifetime stop was DISABLED in S34). No lock file = safe to restart. Proceed.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 65 wrap — 2026-03-14 05:20 UTC):
  Bot: RUNNING PID 13072 → /tmp/polybot_session65.log
  All-time live P&L: -43.51 USD (improved +1.39 from -44.90 in S64)
  Bankroll: ~89+ USD (DB authoritative)
  Tests: 1127 passed, 3 skipped
  Last commit: 5633e7a (Session 65 research docs)

SESSION 65 WAS IMPLEMENTATION + RESEARCH:

  1. BOT RESTARTED (was stopped since S64):
     PID 13072 → /tmp/polybot_session65.log. All loops running clean.

  2. MAKER_MODE=TRUE WIRED — DONE:
     btc_drift and eth_drift now use maker_mode=True (post_only, 30s expiry).
     Saves ~75% on taker fees per trade. Commit: 2080b20.

  3. NON-CRYPTO SNIPER EXPANSION — COMPREHENSIVE DEAD END:
     Full investigation of NBA/NCAAB/NHL/PGA/Weather markets.
     KEY FINDING: All sports follow same pattern:
       pre-game liquid → in-game silent → 20-60 second settlement burst
     The 90c+ sustained window needed for sniper does NOT exist in any sports market.
     PGA golf and weather at 99c NO: real hours-long windows but terrible capital
     efficiency (1c profit on 99c capital = 1% return vs 11% for crypto sniper at 90c).
     Full findings: .planning/EDGE_RESEARCH_S62.md Section 23-25. Commit: 5633e7a.

SESSION 65 SELF-RATING: B
  Wired maker_mode (finally). Comprehensive sports sniper dead-end documented.
  Sniper at 96% WR (50 bets), P&L improved +1.39 USD.

PENDING TASKS (Session 66 — PRIORITY ORDER):

  #1 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled → Stage 2 milestone. Watch for it.

  #2 GEFS WEATHER TEST (Monday only — March 16):
     HIGHNY markets only open weekdays. Compare GEFS ensemble probs to Kalshi prices.
     If GEFS finds >5% edge in uncertain brackets (~50c), weather is viable.

  #3 SNIPER THRESHOLD ANALYSIS (when 200+ live bets):
     50 live settled. At 200+ bets, revisit whether to raise min from 90c to 95c.
     Current: 96% WR across all. But 90-94c bucket may still be marginal.

  #4 VOLUME EXPANSION (no clear path yet):
     Sniper ceiling = 4 crypto series. No sports/weather sniper viable at current scale.
     Next research: March Madness (March 20+) — does bracket blowout give sustained window?
     Cricket/tennis during matches — different market structure than US sports?

125 USD PROFIT GOAL:
  All-time: -43.51 USD. Need +168.51 more.
  Key levers: (1) sniper 96% WR, +0.28 USD/day = 602 days (too slow!)
  (2) sol_drift 2 bets from Stage 2 (bet sizes double), (3) maker_mode now wired

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
  .planning/EDGE_RESEARCH_S62.md — comprehensive findings (S65 sports sniper research at end)
  scripts/edge_scanner.py — reusable Kalshi-vs-Pinnacle scanner tool
  tests/test_edge_scanner.py — 27 tests
