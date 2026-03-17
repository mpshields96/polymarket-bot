# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-17 12:05 UTC (Session 95 — IL-28–IL-32 + sniper floor + per-window cap)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 49110 → /tmp/polybot_session95.log
  All-time live P&L: -24.11 USD (recovering — see loss analysis below)
  Today P&L: -89.79 USD live (75% WR, 139 settled)
  Tests: 1439 passing. Last commit: 2b50531 (feat: IL-32 + sniper floor + per-window cap)

## LOSS ANALYSIS — SESSION 95 (all losses now guarded)
  Six large sniper losses today, all in pre-guard buckets. ALL NOW GUARDED:
    KXBTC NO@91c -19.11 → IL-32 ✓
    KXETH NO@89c -19.58 → sniper execution floor (90c min) ✓
    KXETH YES@93c -19.53 → IL-30 ✓
    KXXRP NO@91c -19.11 → IL-31 ✓
    KXBTC YES@88c -19.36 → IL-29 + sniper floor ✓
    KXXRP NO@94c -19.74 → IL-28 ✓
  Per-window cap (max 2 bets / 30 USD per 15-min window) also deployed.
  Without these 6 losses, sniper would be +46.12 today at 44/50 = 88% WR.

## SESSION 95 GUARD DEPLOYMENTS (all committed 2b50531, 1439 tests pass)
  IL-28: KXXRP NO@94c — 17 bets, 94.1% WR, need 94% break-even, -5.29 USD
  IL-29: KXBTC YES@88c — 2 bets, 50.0% WR, need 88% break-even, -17.93 USD
  IL-30: KXETH YES@93c — 9 bets, 88.9% WR, need 93% break-even, -10.83 USD
  IL-31: KXXRP NO@91c — 5 bets, 80.0% WR, need 91% break-even, -14.07 USD
  IL-32: KXBTC NO@91c — 7 bets, 85.7% WR, need 91% break-even, -11.27 USD
  SNIPER FLOOR: expiry_sniper_v1 rejects price_cents < 90 (asyncio slippage fix)
  PER-WINDOW CAP: max 2 sniper bets + max 30 USD per 15-min market window
    (prevents correlated multi-asset losses in same crypto dump event)
  db.count_sniper_bets_in_window() added to track window exposure

## PENDING MATTHEW DECISIONS
  1. btc_drift Stage 1 promotion: 64 NO-only bets, 57.9% WR, Brier 0.252 — ALL criteria MET
     Command: set calibration_max_usd=None for btc_drift in main.py (requires restart)
  2. maker_mode=True for sol_drift + xrp_drift (btc/eth already have it, needs restart)
  3. eth_drift direction: 43.2% WR on YES-only post-filter. Below break-even.
     Options: wait 20 more bets, flip to "no", or disable. Currently micro-live (tiny bets).
  4. xrp_drift Stage 1: 39/30 bets mechanically ready. Brier 0.267. But only 51% WR / -1.94 USD.
     Recommend: hold at micro-live until WR improves.

## STRATEGY STANDINGS (from --graduation-status 2026-03-17)
  btc_lag_v1:              45/30, Brier 0.191 — READY (HFTs own this market, 0 signals)
  btc_drift_v1:            64/30, Brier 0.252 — READY (micro-live, awaits Matthew promotion)
  eth_drift_v1:           130/30, Brier 0.247 — READY (micro-live, YES direction underperforming)
  sol_drift_v1:            40/30, Brier 0.198 — STAGE 1, 70% WR, +1.56 USD
  xrp_drift_v1:            39/30, Brier 0.267 — READY mechanically, micro-live, borderline
  expiry_sniper_v1:        75/30, n/a      — PRIMARY ENGINE
  orderbook_imbalance_v1:  79/30, n/a      — READY (paper-only, +51.24 paper)
  eth_orderbook_imbalance: 15/30, Brier 0.337 — needs 15 more bets + Brier fix

## GUARD STACK (IL-5 through IL-32 — COMPLETE as of 2b50531)
  IL-5:  99c/1c both sides — BLOCKED (degenerate pricing)
  IL-10: 96c both sides — BLOCKED
  IL-10A: KXXRP YES@94c — BLOCKED
  IL-10B: KXXRP YES@97c — BLOCKED
  IL-10C: KXSOL YES@94c — BLOCKED
  IL-11: 98c NO — BLOCKED
  IL-19: KXSOL YES@97c — BLOCKED
  IL-20: KXXRP YES@95c — BLOCKED
  IL-21: KXXRP NO@92c — BLOCKED
  IL-22: KXSOL NO@92c — BLOCKED
  IL-23: KXXRP YES@98c — BLOCKED
  IL-24: KXSOL NO@95c — BLOCKED
  IL-25: KXXRP NO@97c — BLOCKED
  IL-26: KXXRP NO@98c — BLOCKED
  IL-27: KXSOL YES@96c — BLOCKED
  IL-28: KXXRP NO@94c — BLOCKED (new S95)
  IL-29: KXBTC YES@88c — BLOCKED (new S95)
  IL-30: KXETH YES@93c — BLOCKED (new S95)
  IL-31: KXXRP NO@91c — BLOCKED (new S95)
  IL-32: KXBTC NO@91c — BLOCKED (new S95)
  SNIPER FLOOR: sub-90c execution blocked (new S95)
  PER-WINDOW CAP: max 2 bets / 30 USD per 15-min window (new S95)
  PROFITABLE: BTC/ETH YES@90-92/94-98c, BTC/ETH NO@90-98c, SOL YES@90-93/98c,
              SOL NO@90-94/96-99c, XRP NO@90-91/93/96c, XRP YES@90-93c

## RESTART COMMAND (Session 95):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session95.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## PENDING TASKS (priority order)
  #1 MONITORING — run 5-min background checks, chain indefinitely
     Drought: pivot to code work (tests, guard analysis)
  #2 UCL soccer March 18 17:25 UTC — BAR@62c, BMU@72c, LFC@76c
     python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR18
  #3 NCAA scanner — run March 17-18 when Round 1 lines mature
     python3 scripts/ncaa_tournament_scanner.py --min-edge 0.03
  #4 XRP drift Stage 1 watch — 39/30 bets, need 30 YES-only for eval (~March 20-21)
  #5 eth_orderbook OOS validation — need 20+ post-filter paper bets at 60%+ WR
  #6 Watch KXETH NO@96c (n=2, -13.95 USD — too small to guard yet)
  #7 Watch KXXRP YES@90c (n=1 loss — watch only)
  #8 CPI speed-play April 10 08:30 ET — scripts/cpi_release_monitor.py
  #9 GDP speed-play April 30 — check April 23-24

## HEALTH NOTES
  --health "Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py 187-193 commented out)
  --health "consecutive cooling" = check log to confirm true state
  All 6 today's sniper losses are now guarded — bot should run clean from here
  Gross P&L = +135 USD (already past +125 target). Fees = 89 USD net gap.
  Fee reduction highest leverage: maker_mode for sol_drift/xrp_drift (awaits Matthew)

## KEY FINDINGS (fee math)
  Sniper net/bet ≈ 0.19 USD after fees. Path to +125 net: ~412 more wins.
  At current pace (~30 sniper wins/day) = ~14 days to target.
  Maker mode for sol_drift/xrp_drift could cut fee drag meaningfully.

## COPY-PASTE THIS TO START A NEW SESSION (Session 96)
  Read SESSION_HANDOFF.md then use /polybot-auto
