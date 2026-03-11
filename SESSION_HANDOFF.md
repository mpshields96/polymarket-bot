# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 47 — btc_daily direction_filter + eth_imbalance disabled)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 48)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 48).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ BOT STATE (Session 47 end state):
  Bot RUNNING PID 42593 → /tmp/polybot_session47.log
  Restarted with --reset-soft-stop (cleared consecutive counter from DB=11 to 0)
  eth_imbalance now PAPER-ONLY (was live). btc_daily now direction_filter="no" (contrarian).

RESTART COMMAND (session48.log) — ONLY IF NEEDED:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session48.log 2>&1 &
  sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
Verify: ps aux | grep "[m]ain.py" | wc -l should show 1 (exactly one process).

DIAGNOSTICS AFTER RESTART:
  source venv/bin/activate && python3 main.py --health
  source venv/bin/activate && python3 main.py --report
  source venv/bin/activate && python3 main.py --graduation-status

If --health shows "HARD STOP": DO NOT RESTART. Log it. Wait for Matthew.
"Daily loss soft stop active" = DISPLAY ONLY (lines 187-189 kill_switch.py commented out).
"Consecutive loss cooling" = clears on restart.

---

KEY STATE (Session 47 END — 2026-03-11 ~21:00 CDT):
* Bot: RUNNING (PID 42593) → /tmp/polybot_session47.log
* All-time live P&L: -$41.83 (improved +$4.41 from -$46.24 at session start)
* 985/985 tests passing (+5 direction_filter tests added this session)
* Last code commit: 38962be (direction_filter + eth_imbalance disable)
* Consecutive losses: 0 (reset via --reset-soft-stop)

LIVE STRATEGY STATUS (from --graduation-status at session end):
  - btc_drift_v1: STAGE 1 — 48/30 Brier 0.253 | P&L -$25.73 | 3 consec losses
    direction_filter="no" ACTIVE. DECISION POINT at 30 NO-only settled bets.
  - eth_drift_v1: STAGE 1 — 33/30 Brier 0.254 | P&L +$6.11 | 0 consec losses (healthy!)
  - sol_drift_v1: MICRO-LIVE — 15/30 Brier 0.184 BEST SIGNAL | P&L +$1.44 | 2 consec losses
  - xrp_drift_v1: MICRO-LIVE — 5/30 Brier 0.390 bad | P&L -$2.99 | 5 consec (per-strategy BLOCKED)
  - eth_orderbook_imbalance_v1: PAPER-ONLY AS OF SESSION 47 | 15/30 Brier 0.337 | P&L -$18.20
    DISABLED LIVE: systematic 27% calibration error (model 67% win, actual 33%). Paper continues.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — effectively dead
  - btc_daily_v1: PAPER-ONLY — direction_filter="no" ACTIVE. ~0 settled bets at filter.
    Paper-only, needs 30 bets + Brier < 0.25 before live consideration.

SESSION 47 WORK DONE:
  1. src/strategies/crypto_daily.py: direction_filter param added
     - direction_filter="no": fires on upward drift, always bets NO (contrarian)
     - Rationale: btc_daily paper shows 27% YES win rate (same HFT pattern as btc_drift)
  2. main.py: btc_daily direction_filter="no", eth_imbalance live_executor_enabled=False
  3. tests/test_crypto_daily.py: 5 new TestDirectionFilter tests (985/985 passing)
  4. Security fix: removed shebang from scripts/export_kalshi_settlements.py (test false positive)
  5. Bot restarted PID 42593 with --reset-soft-stop

PENDING TASKS (next session — Session 48):
  1. Monitor btc_daily paper bets — direction_filter="no" hypothesis needs 30 settled bets
  2. btc_drift direction_filter validation — at 30 NO-only settled bets, present data to Matthew
  3. xrp_drift watchdog — at 10 consec losses globally (currently 0 after reset), revisit
  4. eth_imbalance paper watchdog — if Brier improves to < 0.25 at 30 bets, reconsider live
  5. Brier gate docs update (low priority): docs/GRADUATION_CRITERIA.md
  6. Re-download Kalshi Advanced Portfolio CSV (prior download empty/BOM)
  7. Grand Rounds ~March 20 — post-GR = more development time

NEXT SESSION PRIORITIES (Session 48):
  1. ⚠️ CHECK BOT HEALTH FIRST — python3 main.py --health
     If bot is running fine (PID 42593 alive): DO NOT RESTART
  2. Run diagnostics: --report, --graduation-status, --health
  3. Watch for live bets from btc_drift (3 consec, cooling not active) and sol_drift (2 consec)
  4. eth_drift (0 consec) is healthy — should see regular bets
  5. btc_daily paper accumulation — count NO-side bets, track Brier

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* Expansion gate: DO NOT build new strategies until drift validates
* Grand Rounds: ~March 20, 2026. Post-Grand-Rounds = more time to work on the bot.
* $20 max loss tolerance — prioritize not losing money
* btc_daily/hourly BTC bets: already implemented as paper-only btc_daily_v1 with KXBTCD
  KXETHD/KXSOLD have 0 volume — KXBTCD is the only viable daily crypto series
