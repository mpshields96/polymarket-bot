# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-14 (Session 67 — bet size increase + monitoring, +10.37 USD)
# ═══════════════════════════════════════════════════════════════

## COPY-PASTE THIS TO START A NEW SESSION (Session 68)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 68).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/PRINCIPLES.md

BOT STATE (Session 67 wrap — 2026-03-14 ~08:35 UTC):
  Bot RUNNING PID 15236 — log at /tmp/polybot_session66.log
  Sniper: 89 live bets placed (75 settled per graduation), 42W/1L today (+9.28 USD)
  btc_drift + eth_drift MICRO-LIVE (0.01 cap) — confirmed losers, contained.
  sol_drift: 28/30 — STILL 2 from Stage 2 milestone.
  KEY CHANGE THIS SESSION: HARD_MAX raised 5→15 USD, MAX_TRADE_PCT raised 5%→15%

RESTART COMMAND (Session 68):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session68.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

If --health shows "HARD STOP": The March 1 hard stop event is HISTORICAL (30% lifetime stop was DISABLED in S34). No lock file = safe to restart. Proceed.
"Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py lines 187-193 commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 67 wrap — 2026-03-14 08:35 UTC):
  Bot: RUNNING PID 15236 → /tmp/polybot_session66.log
  All-time live P&L: -34.53 USD (improved from -43.51 at session start = +10.37 USD gained)
  Bankroll: ~89+ USD (DB authoritative — check --report)
  Tests: 1127 passed, 3 skipped
  Last commit: 8b279e6 (S67 risk cap raise)

SESSION 67 KEY CHANGES:
  1. HARD_MAX_TRADE_USD: 5.00 → 15.00 (Matthew explicit directive: 100 USD in 10 days)
  2. MAX_TRADE_PCT: 0.05 → 0.15 (sniper now bets 13-15 USD/bet vs old 4.47 USD)
  3. Sniper at new sizes: 42W/1L today. +9.28 USD from 43 settled bets.
  4. One loss: 14.40 USD at 96c went wrong (-14.40). Recovered partially in session.
  5. All 1127 tests pass. Commit 8b279e6.

RISK NOTE FOR SESSION 68:
  Daily loss (live) = 14.40 / 22.31 USD (65%). This is the ONE sniper loss today.
  If another large loss fires today: daily loss counter hits 65%+, approaching soft cap display.
  Soft stop is DISABLED so bot keeps trading. But watch for consecutive losses.
  At 15 USD/bet, 2 consecutive losses = -28 USD drawdown on ~89 USD bankroll = painful.

PENDING TASKS (Session 68 — PRIORITY ORDER):

  #1 MONITOR BOT — daily loss counter is at 65%. No blocking risk but watch.
     If 2+ consecutive losses: note it. Bot will keep trading (soft stop disabled).
     If 5+ consecutive losses: consider pausing manually (Matthew decision).

  #2 SOL STAGE 2 GRADUATION — 2 MORE BETS!
     28/30 live bets. 2 more settled → Stage 2 milestone (10 USD max/bet).
     At 10 USD/bet with Brier 0.176, sol_drift becomes a serious earner.
     Watch --graduation-status.

  #3 GEFS WEATHER TEST (Monday only — March 16):
     HIGHNY markets only open weekdays. Compare GEFS probs to Kalshi prices.
     If GEFS finds >5% edge in uncertain brackets (~50c), weather is viable.

  #4 SNIPER THRESHOLD ANALYSIS (when 200+ live bets):
     Currently 75 settled. At 200+ bets, revisit raising min from 90c to 95c.
     (90-94c bucket: marginal EV. 95-99c: negative EV at exact 95% WR.)

125 USD PROFIT GOAL:
  All-time: -34.53 USD. Need +159.53 more.
  Key levers: (1) sniper at new 15 USD cap = ~8-12 USD/day theoretical EV,
  (2) sol_drift 2 bets from Stage 2 (10 USD max/bet, Brier 0.176 = excellent),
  (3) avoid consecutive losses (each costs 14+ USD now)
  At 8 USD/day: goal reached in ~20 days. At 12 USD/day: ~13 days.

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
