# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 47 Part 2 wrap-up — clean restart PID 46398, session48.log)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 48)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 48).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 47 wrap-up — 2026-03-10 ~22:38 CDT):
  Bot RUNNING PID 46398 → /tmp/polybot_session48.log
  Clean restart performed at 22:38 CDT with --reset-soft-stop
  eth_imbalance PAPER-ONLY (live_executor_enabled=False). btc_daily direction_filter="no".
  DualPriceFeed active (Coinbase fallback for Binance.US cold starts — normal).

CHECK BOT HEALTH FIRST (Session 48 start):
  ps aux | grep "[m]ain.py" | wc -l        (should be 1)
  cat bot.pid                               (should be 46398)
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

KEY STATE (Session 47 Part 2 END — 2026-03-10 ~22:38 CDT):
* Bot: RUNNING (PID 46398) → /tmp/polybot_session48.log
* All-time live P&L: -$44.18
* 985/985 tests passing (unchanged from Session 47 Part 1)
* Last code commit: 38962be (direction_filter + eth_imbalance disable — Session 47 Part 1)
* Consecutive losses: 0 (reset via --reset-soft-stop on clean restart)
* Today live P&L: +$1.34 (10 settled, 60% win rate)

LIVE STRATEGY STATUS (from --graduation-status at Session 47 Part 2 end):
  - btc_drift_v1: STAGE 1 — 49/30 Brier 0.252 | P&L -$24.95 | 0 consec
    direction_filter="no" ACTIVE. ~29 NO-only settled bets since activation.
    DECISION POINT at 30 NO-only settled bets.
  - eth_drift_v1: STAGE 1 — 36/30 Brier 0.253 | P&L +$2.57 | 0 consec (HEALTHY)
    Best live performer. Stage 1 ($5 cap). Watch for steady bets.
  - sol_drift_v1: MICRO-LIVE — 16/30 Brier 0.181 BEST SIGNAL | P&L +$1.85 | 0 consec
    NEEDS 14 MORE BETS to graduate to Stage 1. Graduation = 10x bet size on best signal.
    This is the highest-priority milestone for profitability.
  - xrp_drift_v1: MICRO-LIVE — 5/30 Brier 0.390 bad | P&L -$2.99 | 5 consec (BLOCKED)
    0/5 NO wins — possible systematic mean-reversion pattern (XRP rebounds after drift down).
    Per PRINCIPLES.md: need 30 bets before any parameter change. Monitor only.
  - eth_orderbook_imbalance_v1: PAPER-ONLY | 15/30 Brier 0.337 | P&L -$18.20
    DISABLED LIVE (systematic 27% calibration error). Paper continues for data collection.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — dead strategy
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" ACTIVE. ~1 NO bet settled since activation.
    Needs 30 NO-settled bets + Brier < 0.25 before live consideration. 2-4 weeks out.

SESSION 47 PART 1 WORK DONE (code changes):
  1. src/strategies/crypto_daily.py: direction_filter param added
  2. main.py: btc_daily direction_filter="no", eth_imbalance live_executor_enabled=False
  3. tests/test_crypto_daily.py: 5 new TestDirectionFilter tests (985/985 passing)
  4. Security fix: removed shebang from scripts/export_kalshi_settlements.py
  5. Bot restarted PID 42593 with --reset-soft-stop

SESSION 47 PART 2 WORK DONE (monitoring + analysis):
  1. Full logic/coding audit of all strategy types — confirmed all guards working correctly
  2. Monitored trades 849 (-$2.64 L), 855 (+$1.32 W), 863 (+$0.78 W btc_drift NO), 864 (+$0.41 W sol_drift)
  3. Read KALSHI_BOT_COMPLETE_REFERENCE.pdf — answered bet size question
     CONCLUSION: Do NOT raise bet sizes. Brier gate in reference doc = <0.20 at 100+ bets.
     Current eth_drift Brier = 0.253 at 36 bets. Bankroll ~$53 below scaling floor ($200+).
     Path to more income = promote sol_drift to Stage 1 (14 more bets needed).
  4. Identified xrp_drift 0/5 win pattern — possible XRP mean-reversion, need 30 bets to act
  5. Clean restart to PID 46398 → session48.log

PENDING TASKS (Session 48):
  1. ⚡ HIGHEST PRIORITY: Watch sol_drift — 16/30 live bets. At 30 = Stage 1 promotion.
     Stage 1 = $5 cap vs current $0.49 = 10x bet size on best signal (Brier 0.181).
  2. Monitor btc_drift NO-only hits 30 → present direction_filter validation to Matthew
  3. xrp_drift watchdog — at 8-10 consec losses globally, revisit (currently 5, per-strategy blocked)
  4. eth_imbalance paper watchdog — if Brier improves to < 0.25 at 30 bets, reconsider live
  5. Brier gate docs update (low priority): docs/GRADUATION_CRITERIA.md
     Reference doc gate = <0.20 at 100+ bets; current code gate = <0.25 at 30 bets. Update.
  6. Re-download Kalshi Advanced Portfolio CSV (prior download empty/BOM)
  7. Grand Rounds ~March 20 — post-GR = more development time

NEXT SESSION PRIORITIES (Session 48 — AUTONOMOUS OPERATION):
  1. Check bot health (PID 46398, session48.log). If dead: restart per command above.
  2. Run --health, --report, --graduation-status
  3. sol_drift is #1 priority — count live settled bets. At 30: run Step 5 pre-live audit
     for Stage 1 promotion (remove calibration_max_usd from sol_drift in main.py)
  4. If no live bets for 30+ minutes: check --health immediately (bot may be blocked)
  5. polybot-monitor scheduled task runs every 30 min — use it for autonomous monitoring

$125 PROFIT GOAL — OBJECTIVE ASSESSMENT:
  Current all-time live P&L: -$44.18
  To reach +$125 profit from today = need +$169.18 cumulative from here.
  Realistic daily P&L at current bet sizes: +$1-8 on good volatile days, +$0-3 on calm days.
  At $2-4/day average = 42-84 days to +$125. NOT achievable in "a few days" at current sizing.

  The ONE lever that changes this materially:
  sol_drift graduation to Stage 1: 14 more live bets needed (~7-14 trading days).
  sol_drift Brier 0.181 (best), currently $0.49/bet → Stage 1 = $5/bet.
  At 73% estimated win rate, $5 cap, ~2 bets/day: ~$1.50-3/day from sol_drift alone.
  Combined with eth_drift (~$1-4/day): possibly $3-7/day total.
  Even at $5/day: $125 takes ~25 days.

  HONEST TRUTH: The bot is not broken and is improving. The math requires either more bet
  frequency (more volatile days = more signals) or sol_drift graduation. Nothing else
  changes the trajectory without violating PRINCIPLES.md (no size raises before Brier gate).

RESPONSE FORMAT RULE (permanent — Matthew's instruction):
  NEVER use markdown table syntax (| --- | --- |) in any response.
  Tables render in a different font in Claude Code UI. Plain text only, always.

SCHEDULED MONITOR:
  polybot-monitor: every 30 minutes, enabled, PID 46398, session48.log
  Runs autonomously while Matthew sleeps. Maintains live bets, detects blocking.
  If no live bet in 30 min during active trading hours: check --health immediately.

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* Expansion gate: DO NOT build new strategies until drift validates
* Grand Rounds: ~March 20, 2026. Post-Grand-Rounds = more development time
* $20 hard min bankroll — never let bot trade below this floor
* btc_daily/hourly BTC bets: already implemented as paper-only btc_daily_v1 with KXBTCD
  KXETHD/KXSOLD have 0 volume — KXBTCD is the only viable daily crypto series
* FONT FORMAT: plain text only. Never use markdown table syntax | --- |. Ever.
