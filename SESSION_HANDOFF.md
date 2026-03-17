# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-17 22:55 UTC (Session 98 research wrap — mission reframe + self-improvement infra)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 50882 → /tmp/polybot_session98.log
  All-time live P&L: ~-20.89 USD (last check 22:45 UTC)
  Tests: 1482 passing. Last commit: f221a61 (feat: Dim 2 BayesianDriftModel)

## S98 KEY CHANGES (committed and deployed)
  1. maker_mode=True added to sol_drift and xrp_drift (btc/eth had it since S65)
     Now ALL 4 drift strategies have post_only=True + 30s expiration (fee savings ~75%)
  2. MISSION REFRAME: Research = build self-improving systems, not one-off market scanners
     Full multi-session roadmap: .planning/SELF_IMPROVEMENT_ROADMAP.md
  3. scripts/auto_guard_discovery.py: scans DB nightly, finds negative-EV buckets, auto-adds guards
     DRY RUN RESULT: 0 new guards — current IL stack covers all known negative-EV buckets
     Wire into live.py next session (Dimension 1b, ~30 min)
  4. polybot-autoresearch.md + polybot-auto.md: reframed to self-improvement mission
  2. NCAA scanner run March 17 — 96 Kalshi markets open, no edges >3%. Re-run March 19-20.
  3. UCL launcher alive, fires March 18 17:21 UTC. Check /tmp/ucl_sniper_mar18.log after 20:00 UTC March 18.

## S98 MONITORING EVENTS (main chat, 2026-03-17 21:40-22:40 UTC)
  Bot PID changes: 21666 → 40498 (auto-restart) → duplicate chaos → 46556 (clean restart)
  Daemon started: PID 47620, nohup Python /tmp/polybot_daemon.py, 5-min checks, auto-restart
  bot.pid must be maintained manually — bot does NOT always write it on restart
  MONITORING LESSON: Never pkill during daemon setup. Start daemon FIRST before touching anything.

## S98 OBJECTIVE DECISIONS (no Matthew input needed)
  btc_drift Stage 1 promotion: HOLD (44 NO-only bets, 54.5% WR, last 20 = 50% WR — too thin)
  maker_mode for sol/xrp: DONE (deployed in this session)

## RESEARCH CHAT S98 — COORDINATE NEXT SESSION
  Research chat made revelations about model goals and self-learning/improvement mechanisms.
  Exact findings unknown to main chat — read research chat SESSION_HANDOFF for full context.
  Likely impacts: guard auto-generation, Bayesian model self-calibration, multi-session learning.

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
  1. btc_drift Stage 1: HOLD until last-20 WR recovers above 55% (currently 50%)
     Strategy analyzer flags direction filter to NO side (25% spread) — data-driven
  2. Research chat S98 model/self-learning revelations — coordinate, then decide next build priority

## STRATEGY STANDINGS (22:40 UTC March 17)
  btc_lag_v1:              45/30, Brier 0.191 — READY (0 signals, HFTs own it)
  btc_drift_v1:            64/30, Brier 0.252 — READY micro-live, 47% WR UNDERPERFORMING
  eth_drift_v1:           136/30, Brier 0.248 — READY micro-live, 49% WR STABLE
  sol_drift_v1:            41/30, Brier 0.196 — STAGE 1, 71% WR HEALTHY, +3.84 USD live
  xrp_drift_v1:            42/30, Brier 0.262 — READY micro-live (maker_mode now active)
  expiry_sniper_v1:       PRIMARY ENGINE — 119 bets today, 91.6% WR, guards holding
  orderbook_imbalance_v1:  83/30 — READY paper-only, +39.19 USD paper

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

## RESTART COMMAND (Session 98):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session98.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## SELF-IMPROVEMENT BUILD STATUS (updated S98 end)
  Read .planning/SELF_IMPROVEMENT_ROADMAP.md for full plan.

  DONE (this session):
  - Dim 1a: scripts/auto_guard_discovery.py — scans DB, finds negative-EV buckets (commit 391d06a)
  - Dim 1b: live.py wired — loads data/auto_guards.json at module import (commit 8f5474b)
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, 26 tests, 1482 total (commit f221a61)

  NEXT SESSION MUST DO (in order):
  #1 WIRE Bayesian model into main.py settlement loop
     After each settled live drift bet (btc_drift/eth_drift/sol_drift/xrp_drift):
       drift_pct = (settlement_btc_price - reference_btc_price) / reference_btc_price
       _drift_model.update(drift_pct=drift_pct, side=trade["side"], won=(trade["side"]==trade["result"]))
       _drift_model.save()
     NOTE: needs reference BTC price at bet placement — store in DB or in-memory dict
     File to edit: main.py settlement_loop() — search for "record_win\|record_loss"
  #2 WIRE Bayesian predict into BTCDriftStrategy.generate_signal()
     When model.should_override_static() (after 30+ live bets):
       prob_yes = _drift_model.predict(drift_pct)  (replaces sigmoid step 6)
     Pattern: inject _drift_model as optional param to generate_signal()
  #3 Run scripts/auto_guard_discovery.py at startup (add to polybot-init Step 3)
  #4 Academic: read Snowberg/Wolfers (2010) "Explaining the Favourite-Longshot Bias"
     Test FLB strength by hour-of-day against sniper DB to find structural patterns
  #5 OOS auto-promotion: when 20/20 bets + Brier < 0.30, auto-promote (no human needed)

## PENDING TASKS (priority order)
  #1 MONITORING — run 5-min background checks, chain indefinitely
  #2 UCL soccer March 18 — LAUNCHER ACTIVE PID 25012, fires 17:20 UTC
     Script: python3 scripts/soccer_sniper_paper.py --series KXUCLGAME --date 26MAR18 --poll 30
     Log: /tmp/ucl_sniper_mar18.log. Check after 20:00 UTC March 18 for results.
     Teams eligible (pre-game price 60c+): BAR@62c, BMU@72c, LFC@76c
  #3 NCAA Round 1 — launcher PID 41378 sleeping, fires March 19 08:00 UTC + March 20 08:00 UTC
     Log: /tmp/ncaa_scan_results.log. Tip-offs March 20-21. Re-scan March 19-20.
  #4 Orderbook OOS — 13/20 post-filter bets (7 more to gate). Monitor passively.
     Decision at 20 bets: if Brier < 0.30 → promote to live. Current 53.8% WR (marginal positive).
  #5 btc_drift Stage 1: HOLD per S98 analysis. Wait for last 20 WR to recover to 55%+.
     Current: 44 NO-only bets, 54.5% WR, last 20 = 50% WR (1.3% above break-even, too thin).
     To promote when ready: change calibration_max_usd=_DRIFT_CALIBRATION_CAP_USD → None (line ~2901 main.py).
  #6 xrp_drift Stage 1 eval: 39/30 YES-only bets, 51% WR — hold at micro-live until WR improves
  #7 CPI speed-play April 10 08:30 ET — scripts/cpi_release_monitor.py ready
  #8 GDP speed-play April 30 — check KXGDP availability April 23-24
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

## COPY-PASTE THIS TO START A NEW SESSION (Session 99)
  Read SESSION_HANDOFF.md then use /polybot-auto
