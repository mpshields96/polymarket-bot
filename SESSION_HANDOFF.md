# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 48 wrap-up — PID 47874, session48.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 49)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 49).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 48 wrap-up — 2026-03-11 ~04:15 CDT):
  Bot RUNNING PID 47874 → /tmp/polybot_session48.log
  sol_drift_v1 PROMOTED TO STAGE 1 (calibration_max_usd=None) this session (S48).
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

KEY STATE (Session 48 END — 2026-03-11 ~04:15 CDT):
* Bot: RUNNING (PID 47874) → /tmp/polybot_session48.log
* All-time live P&L: -$41.58 (was -$44.18 start of S48 — improved +$2.60)
* 985/985 tests passing (unchanged — code change was param removal, no new tests needed)
* Last code commits: 509cf30 (sol_drift Stage 1 promotion) + 9171436 (KALSHI_MARKETS.md)
* Consecutive losses: 0 (reset via --reset-soft-stop on clean restart)
* Today live P&L: +$3.94 (11 settled, eth_drift 4W/6 bets = strong performer)

LIVE STRATEGY STATUS (from --graduation-status at Session 48 end):
  - btc_drift_v1: STAGE 1 — 49/30 Brier 0.252 | P&L -$24.95 | 0 consec
    direction_filter="no" ACTIVE. Count NO-only settled bets — approaching 30 for analysis.
  - eth_drift_v1: STAGE 1 — 37/30 Brier 0.252 | P&L +$5.17 | 0 consec (HEALTHY)
    Best consistent earner today. Stage 1 ($5 cap).
  - sol_drift_v1: STAGE 1 (PROMOTED S48) — 16/30 Brier 0.181 BEST SIGNAL | P&L +$1.85 | 0 consec
    NOW AT $5 CAP. First Stage 1 sol_drift bet = milestone. Watch for ~$2-5 bets vs old $0.49.
    Matthew explicitly authorized early promotion (standard gate = 30 bets, user override applied).
  - xrp_drift_v1: MICRO-LIVE — 5/30 Brier 0.390 bad | P&L -$2.99 | 5 consec (BLOCKED)
    0/5 NO wins — possible systematic mean-reversion pattern (XRP rebounds after drift down).
    Per PRINCIPLES.md: need 30 bets before any parameter change. Monitor only.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | P&L -$18.20
    DISABLED LIVE (systematic 27% calibration error). Paper continues for data collection.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" ACTIVE. Very few NO-only settled bets.
    Needs 30 NO-settled bets + Brier < 0.25 before live consideration. Weeks away.

SESSION 48 WORK DONE:
  1. Bot restarted: PID 46398 dead on arrival → restarted to PID 47114 → then 47874 (after code change)
  2. sol_drift_v1 promoted to Stage 1 — main.py calibration_max_usd=None. Commit: 509cf30.
     985/985 tests pass. "STAGE 1 SOL drift" confirmed in startup log.
  3. GSD quick task #9: KALSHI_MARKETS.md updated with Session 48 weekday probe.
     KXBTCMAXW confirmed permanently dormant. KXCPI 74 open (major revision from ~1,400 vol).
     Fresh KXBTCMAXMON/KXBTCMINMON/KXBTCMAXY/KXBTCMINY volume data. Commit: 9171436.
  4. Reddit research: Confirmed our approach is correct for small capital/US restrictions.
     Arbitrage (needs .COM) and market making (needs $1000+) are not viable for us.
     FOMC "perfect forecast record" insight + maker/limit order fee savings logged to todos.md.
  5. polybot-monitor scheduled task updated: PID corrected from 46398 to 47874.
  6. Live terminal feed opened: /tmp/polybot_live_feed.sh — LIVE BET vs PAPER clearly shown.
  7. CHANGELOG.md, STATE.md, SESSION_HANDOFF.md, todos.md all updated.

PENDING TASKS (Session 49):
  1. Watch sol_drift first Stage 1 bet — should be ~$2-5 vs old ~$0.49. Verify in log.
  2. btc_drift direction_filter validation — at 30 NO-only settled bets, present data to Matthew.
     How to count: grep "LIVE BET.*btc_drift.*NO" in polybot_session*.log files.
  3. xrp_drift watchdog — at 8-10 consec losses globally, revisit (currently 5, per-strategy blocked).
  4. eth_imbalance paper watchdog — if Brier improves to < 0.25 at 30 bets, reconsider live.
  5. Re-download Kalshi Advanced Portfolio CSV (prior download was empty/BOM artifact).
  6. Grand Rounds ~March 20 — post-GR = more development time.
  7. FOMC window: KXFEDDECISION-26MAR closes ~March 18. Our fomc_rate_v1 needs 5 paper bets before live.
     Monitor whether paper bet fires before March 18.

$125 PROFIT GOAL — UPDATED ASSESSMENT (post-sol_drift Stage 1):
  Current all-time live P&L: -$41.58
  To reach +$125 profit = need +$166.58 cumulative from here.
  Previous trajectory (pre-S48): +$2-4/day → 42-84 days.
  New trajectory (post-sol_drift Stage 1): sol_drift Brier 0.181, $5/bet, ~2 bets/day.
    Expected value per sol_drift bet: ~+$1.57 (73% win × $4 payout - 27% × $5 loss)
    Combined eth_drift + sol_drift: possibly $5-8/day on volatile days.
    At $5/day average: $166.58 / $5 = ~33 days to +$125.
    At $8/day volatile days: ~21 days.
  This is the maximum achievable acceleration without violating PRINCIPLES.md.
  Reddit research confirms: for US small capital, this IS the right approach.

RESPONSE FORMAT RULE (permanent — Matthew's instruction):
  NEVER use markdown table syntax (| --- | --- |) in any response.
  Tables render in a different font in Claude Code UI. Plain text only, always.

SCHEDULED MONITOR:
  polybot-monitor: every 30 minutes, enabled, PID 47874, session48.log
  Runs autonomously while Matthew sleeps. Maintains live bets, detects blocking.
  If no live bet in 30 min during active trading hours: check --health immediately.

SESSION 48 SELF-CRITIQUE (objective, for next chat):
  WHAT WENT WELL:
  - Restarted dead bot immediately on session start (correct protocol)
  - sol_drift Stage 1 promotion was the right call given Matthew's explicit instruction
  - Reddit research confirmed our strategy is appropriate — good to have external validation
  - Live terminal feed opened as requested
  - KALSHI_MARKETS.md now has authoritative probe data
  WHAT COULD BE BETTER:
  - The polybot-monitor PID update was already done in the previous context window, then done again in this one (minor duplication)
  - Reddit searches couldn't find actual Reddit discussions — had to use web articles as proxies
    Next time: use WebFetch directly on r/Kalshi posts rather than general web search
  - The $125 goal is genuinely unachievable in 3 days. Should be communicated clearly each time, not hedged.
    The honest timeline is 21-42 days depending on volatility, with sol_drift Stage 1 now active.
  - Context window was compressed, losing some prior work detail — should do wrap-up earlier next session
  WHAT NEXT CHAT SHOULD DO DIFFERENTLY:
  - Run --health FIRST, before any other action
  - Check sol_drift first Stage 1 bet immediately — if it fired while Matthew slept, that's the big news
  - Do NOT re-do Reddit research — already done, findings in todos.md
  - EXPANSION GATE CHECK: btc_drift at 49 live bets, Brier 0.252 — expansion gate criteria met
    (30+ live trades, Brier < 0.30, no active kill switch, no silent blockers)
    Next session should present the expansion gate status to Matthew — the gate may be open to discuss KXCPI strategy

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
