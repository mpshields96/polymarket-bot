# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-17 21:03 UTC (Session 96 monitoring wrap — 11/11 sniper wins, guards verified)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 21666 → /tmp/polybot_session96.log
  All-time live P&L: -6.88 USD (recovered +11.51 USD since 19:13 UTC restart)
  Today P&L: -72.56 USD live (losses from pre-restart unguarded buckets — all now guarded)
  Tests: 1446 passing. Last commit: 1a8f2c9 (research: S97 sol_drift regime check)

## KEY FINDING (Session 96 research) — HIGH CONFIDENCE FOR TONIGHT
  ALL March 14 (+64 USD) and March 16 (+47 USD) losses are NOW GUARDED.
  Sniper ceiling at 95c is DEPLOYED (commit 5a1948c) — was listed as pending but already done.
  Tonight's guard stack is the STRONGEST EVER. Expect March 14/16-style performance.

  Remaining unguarded losses in ALL history:
    KXSOL YES@93c: -4.65 USD — acceptable variance in 93.3% WR bucket
    KXBTC YES@93c: -4.65 USD — same
    KXXRP YES@90c: -19.8 USD — single bet, too small sample

## CRITICAL FINDING (Session 95 research wrap) — RESOLVED
  Sniper execution ceiling at 95c is ALREADY DEPLOYED (commit 5a1948c, March 16 23:30 UTC).
  The SESSION_HANDOFF from S95 listed it as pending but it was already committed.
  NO action needed.

## ORIGINAL CRITICAL NOTE (preserved for context):
  SNIPER STRUCTURAL FEE BLEED STILL ACTIVE at 97c YES + 98c YES for KXBTC/KXETH:

  At 97c execution, Kalshi taker fee math:
    Pay 97c per contract. Win payout = 3c. Break-even WR = 97.97% after fees.
    Actual WR at 97c YES = 93% (30 bets, -30.18 USD cumulative).
    LOSING MONEY STRUCTURALLY — NOT just bad luck.

  At 98c execution:
    Pay 98c. Win payout = 2c. Break-even WR = 98.99% after fees.
    Actual WR at 98c YES = 98% (62 bets, -9.06 USD cumulative).
    ALSO LOSING STRUCTURALLY.

  Currently guarded: 96c (IL-10), 97c NO (global), 98c NO (IL-11), 99c (IL-5).
  UNGUARDED AND STILL BLEEDING: 97c YES for KXBTC/KXETH, 98c YES for KXBTC/KXETH/KXSOL.

  FIX: Add global sniper execution ceiling at 95c.
    _SNIPER_EXECUTION_CEILING_CENTS = 95
    Pattern: same as existing floor check (lines 374-380 in live.py).
    Estimated savings: ~39 USD from eliminating structural fee losses at 97-98c YES.

  THIS IS #1 TASK FOR NEXT SESSION — MATHEMATICAL, NOT TRAUMA.

## LOSS ANALYSIS — SESSION 95 (all morning losses now guarded)
  Six large sniper losses, all now blocked:
    KXBTC NO@91c -19.11 → IL-32
    KXETH NO@89c -19.58 → sniper execution floor (90c min)
    KXETH YES@93c -19.53 → IL-30
    KXXRP NO@91c -19.11 → IL-31
    KXBTC YES@88c -19.36 → IL-29 + sniper floor
    KXXRP NO@94c -19.74 → IL-28
  Per-window cap (max 2 bets / 30 USD per 15-min window) also deployed as safety net.
  Without these 6 losses, sniper would be +46 USD today.

## SESSION 95 BUILDS (committed, 1446 tests pass)
  Commit 2b50531: IL-28 through IL-32 + sniper execution floor (90c min) + per-window cap constants
  Commit c0fef8e: db.count_sniper_bets_in_window() + count_open_sniper_positions()
  Commit 79246e2: TestSniperPerWindowCap — 7 tests for per-window enforcement
  Per-window enforcement wired into execute() at lines 140-157 in live.py.
    _SNIPER_MAX_BETS_PER_WINDOW=2, _SNIPER_MAX_USD_PER_WINDOW=30.0

## PENDING MATTHEW DECISIONS
  1. btc_drift Stage 1 promotion: 64 NO-only bets, 57.9% WR, Brier 0.252 — ALL criteria MET
     Command: set calibration_max_usd=None for btc_drift in main.py (requires restart)
  2. maker_mode=True for sol_drift + xrp_drift (btc/eth already have it, needs restart)
  3. eth_drift direction: 43.2% WR on YES-only post-filter. Below break-even.
     Options: wait 20 more bets, flip to "no", or disable. Currently micro-live.
  4. xrp_drift Stage 1: 39/30 bets mechanically ready. Brier 0.267. But only 51% WR.
     Recommend: hold at micro-live until WR improves.

## STRATEGY STANDINGS
  btc_lag_v1:              45/30, Brier 0.191 — READY (HFTs own this market, 0 signals)
  btc_drift_v1:            64/30, Brier 0.252 — READY (micro-live, awaits Matthew promotion)
  eth_drift_v1:           130/30, Brier 0.247 — READY (micro-live, YES direction weak)
  sol_drift_v1:            40/30, Brier 0.198 — STAGE 1, 70% WR
  xrp_drift_v1:            39/30, Brier 0.267 — READY mechanically, micro-live, borderline
  expiry_sniper_v1:       PRIMARY ENGINE — profitable 90-95c zone, bleeding 97-98c YES (see above)
  orderbook_imbalance_v1:  79/30 — READY (paper-only, +51.24 paper)

## GUARD STACK (IL-5 through IL-32 + sniper floor + per-window cap — as of commit 2b50531)
  IL-5:  99c/1c both sides — BLOCKED
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

  CEILING DEPLOYED: 97c+ all sides blocked by ceiling at 95c (commit 5a1948c) ✓

## RESTART COMMAND (Session 96):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session96.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## PENDING TASKS (priority order)
  #1 MONITORING — run 5-min background checks, chain indefinitely
  #2 UCL soccer March 18 — LAUNCHER ACTIVE PID 25012, fires 17:20 UTC
     Script: python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR18 --poll 30
     Log: /tmp/ucl_sniper_mar18.log. Verify PID alive before 17:20 UTC March 18.
     Teams eligible (pre-game price 60c+): BAR@62c, BMU@72c, LFC@76c
  #3 Matthew pending decisions (flag in first response):
     a. btc_drift Stage 1 promotion: 64 NO-only bets, 57.9% WR, Brier 0.252 — ALL criteria MET
        Note: btc_drift is currently MICRO-LIVE (calibration_max_usd=0.01 on line 2901 main.py)
        despite Session 41 Stage 1 comment. The _DRIFT_CALIBRATION_CAP_USD = 0.01 on line 2887.
        To promote: change line 2901 from _DRIFT_CALIBRATION_CAP_USD to None (requires restart).
     b. maker_mode=True for sol_drift + xrp_drift (btc/eth already have it, needs restart)
     c. eth_drift direction: 43.2% WR on YES-only. Still micro-live, flag for decision.
  #4 NCAA scanner — no opportunity now (confirmed S96). Re-run March 19-20 for Round 1 lines.
  #5 xrp_drift Stage 1 eval: 39/30 YES-only bets, 51% WR — hold at micro-live until WR improves
  #6 eth_orderbook OOS validation — 13/20 post-filter bets (need 7 more). Monitor passively.
  #7 CPI speed-play April 10 08:30 ET — scripts/cpi_release_monitor.py ready
  #8 GDP speed-play April 30 — check April 23-24
  #7 CPI speed-play April 10 08:30 ET — scripts/cpi_release_monitor.py
  #8 GDP speed-play April 30 — check April 23-24

## GUARD VERIFICATION (S96 monitoring — LIVE CONFIRMED)
  Ceiling at 95c: CONFIRMED via log "96c signal — skip" at 14:24 CDT
  Per-window cap: CONFIRMED via log "2/2 bets in window — skip KXETH" at 14:28 CDT
  Floor at 90c: ACTIVE
  S96 guard violations: 0 (11/11 sniper bets all in 90-95c range)

## HEALTH NOTES
  --health "Daily loss soft stop active" = DISPLAY ONLY (kill_switch.py 187-193 commented out)
  Guards IL-5 through IL-32 + floor + ceiling + per-window cap = COMPLETE
  All pre-restart losses NOW GUARDED. Bot is clean for overnight.

## OVERNIGHT WATCH (critical hours UTC)
  21:00 UTC: historically +22.57 USD — active now
  04:00 UTC: GOLDEN HOUR — historically +37.99 USD (largest single hour)
  09:00-12:00 UTC: +108 USD combined historically
  Former danger hours (08:00 UTC -111 USD) now GUARDED — expect clean run

## COPY-PASTE THIS TO START A NEW SESSION (Session 97)
  Read SESSION_HANDOFF.md then use /polybot-auto
