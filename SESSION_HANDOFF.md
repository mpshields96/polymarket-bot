# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 52 end — PID 72269, session52.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 53)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 53).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 53 start — 2026-03-11 ~18:40 CDT / 23:40 UTC):
  Bot RUNNING PID 72269 → /tmp/polybot_session52.log
  NOTE: Matthew will explicitly say "stop" to kill the old bot before new session starts fresh.
  When Matthew says "stop": pkill -f "python3 main.py"; sleep 3; verify 0 processes.
  Then restart with: bash scripts/restart_bot.sh 53
  sol_drift direction_filter="no" ACTIVE (committed 61bc33b, Matthew signed off S51).
  btc_drift direction_filter="no" ACTIVE (long-running, S43).
  DualPriceFeed active (Coinbase fallback for Binance.US cold starts — normal).
  CryptoDailyStrategy: per-asset _HOURLY_VOL dict (BTC=0.01, ETH=0.015, SOL=0.025), 5pm EDT slot priority.

CHECK BOT HEALTH FIRST (Session 53 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 72269)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session53.log) — ONLY AFTER MATTHEW SAYS "stop":
  bash scripts/restart_bot.sh 53
  (Requires SESSION_NUM arg — exits safely if not provided, preventing accidental kills)
  ⚠️ NEVER pipe restart_bot.sh through head/tail/grep — SIGPIPE will kill the running bot!
  ⚠️ Always run restart_bot.sh in isolation: `bash scripts/restart_bot.sh 53` only.

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 53 start — 2026-03-11 ~23:40 UTC):
* Bot: RUNNING (PID 72269) → /tmp/polybot_session52.log
* All-time live P&L: -23.48 USD (was -18.64 at S52 start — deteriorated ~5 USD from eth_drift NO losses)
* 1003/1003 tests passing
* Last code commits: 7a01b44 (Session 52 CHANGELOG) → d27f8f5 (eth_drift todo) → eb1d265 (restart fix)
* Today live P&L: +22.04 USD (60 settled, 59% win rate) — strong day despite all-time decline
* Consecutive losses: 2 (from eth_drift NO at bad price buckets — 45-49c zone)

LIVE STRATEGY STATUS (from --graduation-status at Session 52 end):
  - btc_drift_v1: STAGE 1 — 51/30 Brier 0.253 | P&L -22.82 USD | 0 consec
    direction_filter="no" ACTIVE.
  - eth_drift_v1: STAGE 1 — 68/30 Brier 0.245 IMPROVING | P&L +14.16 USD | 3 consec
    Best consistent earner. ALREADY LIVE. Direction bias found (YES outperforms NO) — see PENDING below.
  - sol_drift_v1: STAGE 1 — 24/30 Brier 0.173 BEST SIGNAL | P&L +6.54 USD | 1 consec
    direction_filter="no" ACTIVE as of S51. 6 more bets to graduation.
  - xrp_drift_v1: MICRO-LIVE — 13/30 Brier 0.263 | P&L -0.70 USD | 0 consec
    Improving. Monitor at 30 bets. REVERSED: xrp YES wins, NO loses (consider direction_filter="yes" at 30).
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | DISABLED LIVE (Session 47)
    Paper continues for data collection. Re-evaluate at 30 bets.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" wired in loop.
    Only 12 settled paper bets. Needs 30 NO-settled bets + Brier < 0.25 before live consideration.
  - crypto_daily_loop: now accepts direction_filter param (quick task 10). Paper-only.

CRITICAL FINDING FROM SESSION 52 — NEEDS MATTHEW SIGN-OFF:
⚠️ eth_drift directional bias (67 live settled bets):
  YES side: 36 bets, 61.1% wins, +25.58 USD, +0.711 USD/bet EV
  NO side:  31 bets, 48.4% wins, -6.58 USD, -0.212 USD/bet EV
  Z=1.04, p=0.148 — not stat significant yet but practically meaningful (+0.923/bet gap)
  Estimated impact of direction_filter="yes": +2.54 USD/day

⚠️ eth_drift NO price bucket (worst finding):
  NO bets at 45-49c: 0% wins (9 bets), -5.66 USD — WORST bucket
  NO bets at 50-54c: 86% wins, +5.51 USD — BEST bucket
  Root cause: betting NO when market leans only slightly against us = bad. Near-neutral prices = good.
  Option A: direction_filter="yes" (block all NO bets)
  Option B: min_no_price_cents=50 (block NO at 45-49c, keep 50-54c)
  Both options documented in .planning/todos/pending/2026-03-11-apply-eth-drift-direction-filter-yes-only-after-sign-off.md

SESSION 52 WORK DONE:
  1. Directional analysis of all drift strategies (140+ live bets, per-strategy Z-tests).
  2. eth_drift price bucket analysis — identified 45-49c NO as catastrophic bucket.
  3. restart_bot.sh safety guard added (SESSION_NUM mandatory — prevents SIGPIPE kill).
  4. Full CHANGELOG entry + todos.md updates + session wrap.
  5. All findings documented and committed. Awaiting Matthew sign-off before implementation.

PENDING TASKS (Session 53):
  1. ⭐ HIGHEST PRIORITY: Get Matthew's answer on eth_drift filters:
     a) direction_filter="yes" OR b) min_no_price_cents=50 OR c) both
     Present findings clearly: today's -5 USD deterioration = eth_drift NO at bad buckets.
  2. sol_drift graduation watch: 24/30 — 6 more bets for formal graduation.
     Run --graduation-status at session start to check.
  3. xrp_drift direction analysis at 30 bets (currently 13/30).
     xrp YES outperforms NO (reversed pattern). Consider direction_filter="yes" at 30 bets.
  4. btc_drift NO-only validation at 30 NO-only settled bets (currently 8 post-filter — weeks away).
  5. eth_imbalance paper watchdog — if Brier < 0.25 at 30 bets, reconsider live.
  6. Re-download Kalshi Advanced Portfolio CSV (prior download was empty/BOM artifact).
  7. FOMC window: KXFEDDECISION-26MAR closes March 18. fomc_rate_v1 needs 5 paper settled. Will NOT make it.
     Next FOMC window: June 2026.
  8. Expansion gate met for eth_drift + btc_drift. Bring up KXCPI strategy when Matthew has bandwidth.
  9. KXBTCD Friday slot (770K volume) — consider btc_daily targeting Friday slot specifically.
     Currently only targets same-day slot. Future work, post-expansion gate.
  10. polybot-monitor scheduled task: update PID from 69626 → 72269, session51.log → session52.log.

125 USD PROFIT GOAL — UPDATED ASSESSMENT (2026-03-11 session 52 end):
  Current all-time live P&L: -23.48 USD
  To reach +125 USD profit = need +148.48 USD cumulative from here.
  Today rate: +22.04 USD (60 bets, 59% win rate) — strong day.
  Trajectory: 7-8 more days at today's rate would reach the goal.
  Note: all-time deteriorated -4.88 USD today despite +22 day because eth_drift NO losses.
  With eth_drift direction filter: estimated +2.54 USD/day improvement → trajectory improves.
  At +10/day average: ~15 more days to goal. At +15/day: ~10 days.

RESPONSE FORMAT RULES (permanent — Matthew's instructions, both mandatory):

RULE 1 — NO MARKDOWN TABLES:
  NEVER use markdown table syntax (| --- | --- |) in any response.
  Tables render in wrong font in Claude Code UI.

RULE 2 — NO DOLLAR SIGNS IN PROSE:
  NEVER write $X.XX in responses (e.g. $40.09, $5.43, $2.44).
  Dollar signs trigger LaTeX/KaTeX math mode in Claude Code UI — everything between two $ signs
  renders in italic math font causing garbled text.
  INSTEAD use: USD 40.09 | +40.09 | 40.09 dollars | P&L: -40.09
  This applies to ALL dollar amounts: P&L, bet sizes, bankroll, profit goals.
  Example wrong:  "All-time P&L: -$40.09 (was -$41.58)"
  Example right:  "All-time P&L: -40.09 USD (was -41.58 at last wrap)"

SCHEDULED MONITOR:
  polybot-monitor: every 30 minutes, NEEDS PID UPDATE 69626 → 72269
  Runs autonomously while Matthew is away. Maintains live bets, detects blocking.
  If no live bet in 30 min during active trading hours: check --health immediately.

THREE DISTINCT KALSHI CRYPTO BET TYPES (permanent — documented Session 51):
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M
    "BTC Up or Down in next 15 mins?" — UP/DOWN binary. ALL 4 are LIVE.
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD/KXETHD/KXSOLD/KXXRPD
    "Bitcoin price today at 5pm EDT?" — above/below price at clock time. PAPER-ONLY.
    Volume: KXBTCD 5pm=676K (real), KXETHD 5pm=64K (real, not zero).
  TYPE 3 (Weekly/Friday THRESHOLD): Same KXBTCD series, future Friday date slot.
    "Bitcoin price on Friday at 5pm EDT?" — 770K volume (largest). NOT YET BUILT.
  DO NOT confuse these types. They have different signal approaches, timing, and promotion criteria.

SESSION 52 SELF-CRITIQUE (objective, for next chat):
  WHAT WENT WELL:
  - restart_bot.sh safety fix applied immediately after the accidental kill — no delay
  - Directional analysis was thorough: Z-tests, price buckets, per-strategy breakdown
  - eth_drift price bucket finding is actionable and specific (45-49c = 0% wins)
  - All findings documented in todos.md with implementation options ready
  - Correctly held all findings for sign-off — no scope creep or premature implementation
  - SIGPIPE mechanism correctly diagnosed (pkill ran before head terminated pipeline)
  WHAT COULD BE BETTER:
  - Ran `bash scripts/restart_bot.sh --help 2>&1 | head -5` without considering SIGPIPE
    LESSON: Never pipe restart_bot.sh through any command. Run in isolation only.
  - All-time P&L deteriorated -4.84 USD during session (eth_drift NO at bad buckets)
    LESSON: eth_drift direction/price filter is single highest-priority improvement pending
  - Used fewer skills than available — only wrap-up and gsd:add-todo. Should have used
    sc:analyze for directional analysis, sc:git for commit messages.
  WHAT SESSION 53 SHOULD DO DIFFERENTLY:
  - FIRST THING: Present eth_drift findings clearly to Matthew. Get sign-off on filter.
  - Check sol_drift: 24/30 → likely hit 30 today. Run graduation analysis.
  - Update polybot-monitor PID (69626 → 72269).
  - Use more GSD/superpowers skills proactively — they're free and useful.
  - NEVER pipe restart_bot.sh. Run in isolation only.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* MAKE MORE MONEY — target +125 USD all-time. Currently at -23.48. Need +148.48.
* 20 USD hard min bankroll — never let bot trade below this floor
* THREE BET TYPES: 15-min direction (live), hourly/daily threshold (paper), weekly/Friday (not built)
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
* Never use dollar sign in prose responses.
