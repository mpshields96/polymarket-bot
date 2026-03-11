# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 49 wrap-up — PID 47874, session48.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 50)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 50).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 49 wrap-up — 2026-03-11 ~07:15 CDT):
  Bot RUNNING PID 47874 → /tmp/polybot_session48.log
  sol_drift_v1 STAGE 1 ACTIVE — first Stage 1 bet fired overnight ($2.44, WON). MILESTONE.
  eth_imbalance PAPER-ONLY (live_executor_enabled=False). btc_daily direction_filter="no".
  DualPriceFeed active (Coinbase fallback for Binance.US cold starts — normal).

CHECK BOT HEALTH FIRST (Session 49 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 47874)
  source venv/bin/activate && python3 main.py --health
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status

RESTART COMMAND (session48.log) — ONLY IF BOT DIED:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session48.log 2>&1 &
  sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
Verify: ps aux | grep "[m]ain.py" | wc -l should show 1 (exactly one process).

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-189 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart with --reset-soft-stop.

---

KEY STATE (Session 49 END — 2026-03-11 ~07:15 CDT):
* Bot: RUNNING (PID 47874) → /tmp/polybot_session48.log
* All-time live P&L: -$40.09 (was -$41.58 start of S49 context — improved +$1.49)
* 985/985 tests passing (no code changes this session)
* Last code commits: 509cf30 (sol_drift Stage 1) + 9171436 (KALSHI_MARKETS.md) + 01679f4 (S48 wrap)
* Consecutive losses: 1 (last loss at 07:01 UTC — normal, well under limit of 8)
* Today live P&L: +$5.43 (32 settled) — profitable day with sol_drift Stage 1 active

LIVE STRATEGY STATUS (from --graduation-status at Session 49 end):
  - btc_drift_v1: STAGE 1 — 49/30 Brier 0.252 | P&L -$24.95 | 0 consec
    direction_filter="no" ACTIVE. 6 NO-only settled bets since activation. Need 30 for analysis.
  - eth_drift_v1: STAGE 1 — 54/30 Brier 0.249 IMPROVING | P&L +$2.22 | 1 consec (recent loss)
    Best consistent earner. 23 bets overnight. Brier improved from 0.252 to 0.249.
  - sol_drift_v1: STAGE 1 — 19/30 Brier 0.169 BEST SIGNAL | P&L +$5.88 | 0 consec
    ⭐ MILESTONE: First Stage 1 bet fired overnight ($2.44 NO, WON +$1.48). 3 Stage 1 bets so far, 3/3 wins.
    19 total live bets. Brier 0.169 — exceptional calibration.
  - xrp_drift_v1: MICRO-LIVE — 6/30 Brier 0.351 | P&L -$2.58 | 0 consec (UNBLOCKED overnight!)
    Was blocked at 5 consec; overnight win cleared the streak. Monitor carefully.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | P&L -$18.20
    DISABLED LIVE. Paper continues for data collection. Re-evaluate at 30 bets.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" ACTIVE. Minimal bets.
    Needs 30 NO-settled bets + Brier < 0.25 before live consideration. Weeks away.

SESSION 49 WORK DONE:
  1. Overnight monitoring: bot ran 8+ hours without intervention. 20 live bets placed autonomously.
  2. sol_drift Stage 1 MILESTONE: First Stage 1 bet $2.44 fired at 00:04 UTC → WON +$1.48.
     Three Stage 1 sol_drift bets overnight: 3/3 wins, +$4.03 total. Promotion was correct.
  3. Verified single process (1 instance), all kill switch parameters clean.
  4. xrp_drift unblocked: consecutive streak cleared by overnight win.
  5. polybot-monitor scheduled task kept bot alive and betting throughout.
  6. Today: +$5.43 live P&L on 32 settled bets. Best single day since Stage 1 promotions.
  7. Session wrap-up docs updated.

PENDING TASKS (Session 50):
  1. btc_drift direction_filter validation at 30 NO-only settled bets (currently 6/30 — weeks away).
     Command: python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); print(c.execute('SELECT COUNT(*) FROM trades WHERE strategy=\"btc_drift_v1\" AND is_paper=0 AND side=\"no\" AND result IS NOT NULL AND id>=567').fetchone()[0])"
  2. xrp_drift watchdog — just unblocked overnight. Watch next 10 bets carefully.
     If Brier stays > 0.30 at 30 bets: disable live, paper-only.
  3. eth_imbalance paper watchdog — if Brier improves to < 0.25 at 30 bets, reconsider live.
  4. Re-download Kalshi Advanced Portfolio CSV (prior download was empty/BOM artifact).
  5. FOMC window: KXFEDDECISION-26MAR closes ~March 18. fomc_rate_v1 needs 5 paper bets before live.
     Monitor whether paper bet fires before March 18.
  6. Grand Rounds ~March 20 — post-GR = more development time.
  7. Expansion gate: btc_drift 49 bets, Brier 0.252. Gate technically open.
     When Matthew has bandwidth: discuss KXCPI strategy (74 open markets, episodic pre-release edge).

$125 PROFIT GOAL — UPDATED ASSESSMENT (after sol_drift Stage 1 overnight validation):
  Current all-time live P&L: -$40.09
  To reach +$125 profit = need +$165.09 cumulative from here.
  Rate: Today +$5.43 (32 bets, 56% win rate). sol_drift 3/3 overnight.
  Trajectory: At +$5/day average (volatile sol+eth days): ~33 days.
  At +$3/day (quiet days): ~55 days.
  sol_drift Stage 1 is working as expected. This IS the right strategy.

RESPONSE FORMAT RULE (permanent — Matthew's instruction):
  NEVER use markdown table syntax (| --- | --- |) in any response.
  Tables render in a different font in Claude Code UI. Plain text only, always.

SCHEDULED MONITOR:
  polybot-monitor: every 30 minutes, enabled, PID 47874, session48.log
  Runs autonomously while Matthew sleeps. Maintains live bets, detects blocking.
  If no live bet in 30 min during active trading hours: check --health immediately.

SESSION 49 SELF-CRITIQUE (objective, for next chat):
  WHAT WENT WELL:
  - sol_drift Stage 1 promotion from S48 validated immediately: 3/3 overnight wins, +$4.03
  - Correctly diagnosed "no bets for 54 min" as market conditions (not a bug). Didn't panic.
  - Verified single process, clean kill switch state, all parameters healthy.
  - Polybot-monitor scheduled task worked: bot ran 8 hours autonomously with no human intervention.
  - Completed wrap-up docs under time pressure efficiently.
  WHAT COULD BE BETTER:
  - Matthew said "use GSD and superpowers!" — I defaulted to inline edits instead of launching
    gsd:quick for the wrap-up. Inline is faster but GSD would have created better structured artifacts.
    Next time: launch gsd:quick --full for session wrap-up even under time pressure.
  - The "bot not healthy" concern at 23:54 was a market condition issue, not a bug.
    I should have immediately logged this as "expected behavior" in the monitor log without waiting for Matthew.
  - Stale open trades count growing (57 → 146) — sports_futures paper bets accumulating.
    These are harmless but should be mentioned to Matthew as a cosmetic issue.
  WHAT NEXT CHAT SHOULD DO DIFFERENTLY:
  - Run --graduation-status FIRST to see sol_drift progress toward 30 live bets.
    Target: 30 bets for formal graduation. Currently at 19.
  - Check if fomc_rate_v1 paper bet fired (KXFEDDECISION-26MAR closes March 18).
  - Do NOT rebuild Reddit research — done, in todos.md.
  - Expansion gate: btc_drift/eth_drift both qualify. When Matthew has bandwidth, bring up KXCPI.
  - Use gsd:quick for any multi-file task (even documentation), not just code.
  - Morning sessions often have crypto markets at extreme prices (80-90¢ YES) — normal during bull trends.
    Don't investigate why no bets fire during those windows — price guard is working correctly.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* Expansion gate: check status — btc_drift 49 bets, Brier 0.252 → may be time to discuss
* Grand Rounds: ~March 20, 2026. Post-Grand-Rounds = more development time
* $20 hard min bankroll — never let bot trade below this floor
* btc_daily/hourly BTC bets: already implemented as paper-only btc_daily_v1 with KXBTCD
  KXETHD/KXSOLD have 0 volume — KXBTCD is the only viable daily crypto series
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
