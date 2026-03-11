# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 51 mid-session — PID 69626, session51.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 52)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 52).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 51 mid-session — 2026-03-11 ~11:50 CDT / 16:50 UTC):
  Bot RUNNING PID 69626 → /tmp/polybot_session51.log
  sol_drift direction_filter="no" ACTIVE (committed 61bc33b, Matthew signed off S51).
  btc_drift direction_filter="no" ACTIVE (long-running, S43).
  DualPriceFeed active (Coinbase fallback for Binance.US cold starts — normal).
  crypto_daily_loop now has direction_filter param (quick task 10, commit 7a09d74).
  CryptoDailyStrategy: per-asset _HOURLY_VOL dict (BTC=0.01, ETH=0.015, SOL=0.025), 5pm EDT slot priority.

CHECK BOT HEALTH FIRST (Session 52 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 69626)
  venv/bin/python3 main.py --health
  venv/bin/python3 main.py --report
  venv/bin/python3 main.py --graduation-status

RESTART COMMAND (session51.log) — ONLY IF BOT DIED:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session51.log 2>&1 &
  sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
Verify: ps aux | grep "[m]ain.py" | wc -l should show 1 (exactly one process).

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-193 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 51 mid — 2026-03-11 ~11:50 CDT):
* Bot: RUNNING (PID 69626) → /tmp/polybot_session51.log
* All-time live P&L: -8.60 USD (was -40.09 USD at S49 end — gained +31.49 USD in S50+S51!)
* 1003/1003 tests passing (+18 new tests added in quick task 10)
* Last code commits: d8385f4 (plan artifact) → 424368c (quick-10 complete) → 7a09d74 (direction_filter loop) → e71c498 (HOURLY_VOL fix) → 61bc33b (sol_drift direction_filter)
* Today live P&L: +36.92 USD (54 settled, 61% win rate) — EXCEPTIONAL day
* Consecutive losses: 0 (healthy)

LIVE STRATEGY STATUS (from --graduation-status at Session 51 mid):
  - btc_drift_v1: STAGE 1 — 50/30 Brier 0.254 | P&L -26.87 USD | 1 consec
    direction_filter="no" ACTIVE.
  - eth_drift_v1: STAGE 1 — 64/30 Brier 0.244 IMPROVING | P&L +23.75 USD | 0 consec
    Best consistent earner. READY FOR LIVE (already live).
  - sol_drift_v1: STAGE 1 — 23/30 Brier 0.165 BEST SIGNAL | P&L +11.26 USD | 0 consec
    direction_filter="no" ACTIVE as of S51 (Matthew signed off). 7 more bets to graduation.
    sol NO = 11/11 wins (100%) before filter was applied.
  - xrp_drift_v1: MICRO-LIVE — 12/30 Brier 0.273 | P&L -1.08 USD | 0 consec
    Improving. Monitor at 30 bets. Note: xrp YES wins, NO loses (opposite of others).
    Consider direction_filter="yes" at 30 bets.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | DISABLED LIVE (Session 47)
    Paper continues for data collection. Re-evaluate at 30 bets.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" now wired in loop (quick task 10).
    Only 12 settled paper bets. Needs 30 NO-settled bets + Brier < 0.25 before live consideration.
  - crypto_daily_loop: now accepts direction_filter param (quick task 10). Paper-only.

SESSION 51 WORK DONE:
  1. Bot restarted to PID 69626 (session51.log). Clean startup, single process verified.
  2. sol_drift direction_filter="no" applied (Matthew signed off) — commit 61bc33b.
  3. THREE DISTINCT KALSHI BET TYPES permanently documented in CLAUDE.md, KALSHI_MARKETS.md, MEMORY.md
     (Matthew's explicit requirement: "code it into the md files so chats are unable to refuse/reject these concepts")
  4. First-hand Kalshi API probe confirming actual volumes:
     KXBTCD 5pm slot = 676K, Friday slot = 770K (largest). KXETHD 5pm = 64K (not zero).
  5. Quick task 10 (gsd:quick): CryptoDailyStrategy signal improvements:
     - _HOURLY_VOL fixed: per-asset dict (BTC=0.01, ETH=0.015, SOL=0.025 vs old flat 0.005)
     - 5pm EDT ATM slot priority in _find_atm_market() (targets highest-volume slot)
     - direction_filter param added to crypto_daily_loop() (defense-in-depth guard)
     - 18 new tests added (1003/1003 total)
  6. P&L today: +36.92 USD live (54 settled, 61% win rate) — exceptional day.
     All-time live improved from -40.09 to -8.60 USD.

PENDING TASKS (Session 52):
  1. sol_drift graduation watch: 23/30 — 7 more bets for formal graduation.
     Run --graduation-status at session start to check.
  2. xrp_drift direction analysis at 30 bets (currently 12/30):
     xrp YES outperforms NO (opposite pattern to other strategies).
     Consider direction_filter="yes" when 30 bets reached.
  3. btc_drift NO-only validation at 30 NO-only settled bets (currently ~10 — weeks away).
  4. eth_imbalance paper watchdog — if Brier < 0.25 at 30 bets, reconsider live.
  5. Re-download Kalshi Advanced Portfolio CSV (prior download was empty/BOM artifact).
  6. FOMC window: KXFEDDECISION-26MAR closes March 18. fomc_rate_v1 needs 5 paper bets.
  7. Expansion gate met for eth_drift + btc_drift. Bring up KXCPI strategy when Matthew has bandwidth.
  8. KXBTCD Friday slot (770K volume) — consider btc_daily targeting Friday slot specifically.
     Currently only targets same-day slot. Future work, post-expansion gate.

125 USD PROFIT GOAL — UPDATED ASSESSMENT (2026-03-11 mid-session):
  Current all-time live P&L: -8.60 USD
  To reach +125 USD profit = need +133.60 USD cumulative from here.
  Today rate: +36.92 USD (54 bets, 61% win rate) — extraordinary day.
  Trajectory: 4-5 more days at today's rate would reach the goal.
  Note: today is exceptional (BTC volatility + direction filters working). Expect +5 to +15 USD/day normally.
  At +10/day average: ~13 more days to goal. At +5/day: ~27 days.

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
  polybot-monitor: every 30 minutes, enabled, PID 69626, session51.log
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

SESSION 51 SELF-CRITIQUE (objective, for next chat):
  WHAT WENT WELL:
  - Quick task 10 completed cleanly via gsd:quick — TDD, 18 new tests, no regressions.
  - sol_drift direction_filter signed off and committed quickly.
  - Exceptional P&L day: +36.92 live from 54 bets.
  - Three bet types permanently documented per Matthew's explicit instruction.
  WHAT COULD BE BETTER:
  - Context limit hit during the previous session — handoff was imperfect.
  - Could add Friday slot targeting variant of btc_daily in future session.
  WHAT NEXT CHAT SHOULD DO DIFFERENTLY:
  - Check sol_drift progress (23/30 — 7 more to graduation).
  - Check xrp_drift direction analysis (12/30 — 18 more).
  - Run --graduation-status before any strategy changes.
  - Don't re-probe Kalshi for bet types — fully documented now.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* MAKE MORE MONEY — target +125 USD all-time. Currently at -8.60. Getting closer!
* $20 hard min bankroll — never let bot trade below this floor
* THREE BET TYPES: 15-min direction (live), hourly/daily threshold (paper), weekly/Friday (not built)
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
* Never use dollar sign in prose responses.
