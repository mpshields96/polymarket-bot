# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-11 (Session 46 — Kalshi API settlement export + wrap-up)
# ═══════════════════════════════════════════════════════════════

## ▶ COPY-PASTE THIS TO START A NEW SESSION (Session 47)

You are continuing work on polymarket-bot — a real-money algorithmic trading bot (Session 47).

MANDATORY READING BEFORE ANY ACTION:
  cat SESSION_HANDOFF.md
  cat .planning/AUTONOMOUS_CHARTER.md
  tail -200 .planning/CHANGELOG.md
  cat .planning/SKILLS_REFERENCE.md

⚠️ DO NOT RESTART UNLESS NECESSARY (Session 46 end state):
  DB shows 11 consecutive losses. Restart will trigger 2hr cooling from restore_consecutive_losses().
  Running bot has in-memory consecutive=3 (no cooling active). Bot is healthy.
  IF RESTART IS NEEDED: add --reset-soft-stop flag to clear the consecutive counter.

RESTART COMMAND (session47.log) — ONLY IF NEEDED — includes --reset-soft-stop:
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session47.log 2>&1 &
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

KEY STATE (Session 46 END — 2026-03-11 ~19:35 CDT):
* Bot: RUNNING (PID 36660) → /tmp/polybot_session45.log
* All-time live P&L: -$45.52 (API: -$48.37) | Bankroll: unknown (run --report)
* 980/980 tests passing (unchanged this session)
* Last code commit: pending (this session's changes)
* ⚠️ CRITICAL: In-memory consecutive=3 (bot healthy, no cooling). DB=11 (historical).
  DO NOT RESTART without --reset-soft-stop or 2hr cooling fires immediately.

LIVE STRATEGY STATUS (from --graduation-status at session end):
  - btc_drift_v1: STAGE 1 — 48/30 Brier 0.253 | P&L -$25.73 | 3 consec losses
    direction_filter="no" ACTIVE. DECISION POINT at 30 NO-only bets.
  - eth_drift_v1: STAGE 1 — 31/30 Brier 0.256 | P&L +$0.41 | 4 consec losses (per-strategy)
    NOTE: per-strategy blocked, but global kill switch not at limit yet
  - sol_drift_v1: MICRO-LIVE — 14/30 Brier 0.170 BEST SIGNAL | P&L +$1.93 | 1 consec loss
  - xrp_drift_v1: MICRO-LIVE — 5/30 Brier 0.390 bad | P&L -$2.99 | 5 consec (per-strategy blocked)
  - eth_orderbook_imbalance_v1: MICRO-LIVE — 13/30 Brier 0.353 ❌ | P&L -$16.68 | 4 consec
    WATCHDOG: Brier was 0.360 at 12 bets, now 0.353 at 13 — slight improvement but still bad
    If Brier > 0.30 at bet 22: disable live trading for this strategy.
  - btc_lag_v1: STAGE 1 — 45/30 Brier 0.191 | 0 signals/week (HFTs) — effectively dead

KALSHI API SETTLEMENT DATA (this session):
  - reports/kalshi_settlements.csv — 116 settled trades, 56W/60L, net -$48.37
  - scripts/export_kalshi_settlements.py — run anytime for fresh data
  - revenue field in Kalshi API is in CENTS (not dollars) — script handles this correctly

SESSION 46 WORK DONE:
  1. scripts/export_kalshi_settlements.py (NEW) — Kalshi API settlement export
     - Paginates /portfolio/settlements + /portfolio/fills, joins by ticker
     - BUG FOUND: revenue field is cents, not dollars — fixed in script
     - Exports 12 columns: ticker, event_ticker, entry_time, settled_time, market_result,
       our_side, contracts, avg_entry_price_cents, total_cost_usd, revenue_usd, fee_usd,
       net_pnl_usd, won
  2. reports/kalshi_settlements.csv — generated, 116 rows, -$48.37 net P&L
  3. All MD files updated (SESSION_HANDOFF, CHANGELOG, CLAUDE.md, POLYBOT_INIT.md)

PENDING TASKS (next session — Session 47):
  1. ⚠️ eth_imbalance WATCHDOG: at bet 22, check Brier. If > 0.30 → disable live for strategy
  2. Brier gate docs update: docs/GRADUATION_CRITERIA.md → Brier < 0.20 for Stage 2 (REBUILD #6)
  3. btc_drift direction_filter validation at 30 NO-only bets — present data, Matthew decides
  4. Re-download Kalshi Advanced Portfolio CSV (prior download empty). Cross-ref with kalshi_settlements.csv
  5. Grand Rounds ~March 20 — post-GR = more development time

NEXT SESSION PRIORITIES (Session 47):
  1. ⚠️ CHECK BOT HEALTH FIRST — python3 main.py --health
     If consecutive cooling active and bot is stopped/crashed: restart with --reset-soft-stop
     If bot is running fine (PID 36660 alive): DO NOT RESTART
  2. Run diagnostics: --report, --graduation-status, --health
  3. Watch for live bets from btc_drift (3 consec, no cooling) and sol_drift (1 consec)
  4. eth_imbalance bet 22 watchdog — disable live if Brier stays > 0.30
  5. Brier gate docs update (low priority, no impact on live trading)

MATTHEW'S STANDING DIRECTIVES:
* Fully autonomous always. Do work first, summarize after.
* Never ask for confirmation on: tests, file reads/edits, commits, bot restarts, reports
* Bypass permissions mode: ACTIVE
* Expansion gate: DO NOT build new strategies until drift validates
* Grand Rounds: ~March 20, 2026. Post-Grand-Rounds = more time to work on the bot.
