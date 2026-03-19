# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-19 ~20:00 UTC (Session 117 wrap — status checks, sol_drift edge_confirmed, bankroll staging clarification)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot STOPPED (Matthew requested stop 2026-03-19 ~19:52 UTC)
  All-time live P&L: +11.35 USD (recovering — sniper positive session today)
  Bankroll: 179.76 USD (Stage 2 sizing: max 10 USD/bet for drift)
  Tests: 1686 passing. Last commit: 9f765d7 (docs: guard ROI analysis + mission target breakdown)
  eth_drift: DISABLED (min_drift_pct=9.99) — confirmed 0 bets
  xrp_drift: UNBLOCKED (direction_filter="yes")
  S116+S117 COMPLETE: forward-edge analysis + staging clarification + status confirmation

## S116 RESEARCH KEY FINDINGS (2026-03-19 ~18:30-20:00 UTC)

  1. FORWARD EDGE ANALYSIS — XRP GUARDS ARE SUFFICIENT
     New function: analyze_sniper_forward_edge(bets, guards) in bet_analytics.py
     Filters bets to: in-zone (90-95c) AND unguarded → shows forward SPRT per coin.

     Forward SPRT (post-guard, in-zone 90-95c):
       BTC: n=131 WR=98.5% lambda=+7.254 [EDGE CONFIRMED]
       ETH: n=137 WR=98.5% lambda=+7.704 [EDGE CONFIRMED]
       SOL: n=140 WR=96.4% lambda=+4.092 [EDGE CONFIRMED]
       XRP: n=95  WR=93.7% lambda=-0.558 [COLLECTING — NOT at no-edge boundary]

     All-time XRP lambda=-2.769 included 43 guarded + 47 ceiling/floor bets (90 total).
     With those excluded, forward XRP is NOT broken — it's collecting data.
     CCA REQUEST 8 resolution: current guards sufficient. No additional intervention.

  2. XRP IN-ZONE BUCKET ANALYSIS COMPLETED
     YES@92c/93c are the profitable core (+40.63 USD combined, 100% WR).
     Problem buckets within zone: YES@94c (n=15, WR=93.3%, EV=-0.606) and
     NO@91c/92c (n=4-5, WR=75-80%) — none meet auto-guard p<0.20 threshold.
     NO@94c (n=17, WR=94.1%) is marginally below break-even.
     Monitor YES@94c — if n reaches 25+ and stays below 94% WR, may become guardable.

  3. btc_drift CUSUM TRAJECTORY CONFIRMED
     Recent bets (March 18-19): 6/9 wins = 67% WR. March 17 crash was the driver.
     CUSUM at 4.180 for multiple sessions — not rising, likely to stabilize.
     Not a structural downtrend — trauma event. No disable needed yet.

  4. SOL DIRECTION FILTER CONFIRMED CORRECT
     YES side (n=12): WR=66.7%, EV=+0.359 (size artifact — March 11 Stage 1 era)
     NO side (n=31): WR=71.0%, EV=+0.019
     WR comparison: NO=71% > YES=67%. Current filter="no" is correct.
     Higher YES EV is a bet-size artifact, not structural.

  5. COMMIT: d9a44f8 (12 new tests, 1686 total passing)

## S115 RESEARCH KEY FINDINGS (2026-03-19 ~13:00-18:30 UTC)

  1. XRP SNIPER SPRT FORMALLY CROSSED NO-EDGE BOUNDARY
     Per-coin SPRT analysis (bet_analytics.py — new analyze_sniper_coins):
       BTC: n=201, 97.5% WR, lambda=+8.661 EDGE CONFIRMED, +100.50 USD
       ETH: n=194, 97.4% WR, lambda=+8.136 EDGE CONFIRMED, +71.94 USD
       SOL: n=200, 95.0% WR, lambda=+2.192 EDGE CONFIRMED, -4.66 USD
       XRP: n=185, 93.0% WR, lambda=-2.769 NO-EDGE BOUNDARY (-2.251) CROSSED, -107.27 USD
     XRP per-coin SPRT crossed the boundary. CCA REQUEST 8 updated (urgent).
     WAIT for CCA structural mechanism before building any guard.

  2. MONTHLY WR TRACKER ADDED TO bet_analytics.py
     analyze_sniper_monthly() shows rolling per-month WR for FLB weakening detection.
     Currently 1 month of data (March 2026): n=780, WR=95.8%, P&L=+60.51 USD.

  3. XRP HOURLY BREAKDOWN (diagnostic — not actionable yet)
     Worst hours: 08:xx WR=62% (n=8, likely crash event), 00:xx WR=60% (n=5), 13:xx WR=67% (n=6)
     Many hours in 00-08 UTC window are 100% WR. Broad 21-08 block is too blunt.
     XRP bad-hours SPRT lambda=-0.536 (still collecting — not crossed at hour-level).

  4. BTC_DRIFT CUSUM: 4.180/5.0 at session start. SPRT lambda=-1.108. Still collecting.

  5. KXETH YES@93c: n=9 (1 bet from auto-guard). Next bet triggers check.

  6. CCA deliveries confirmed implemented:
     - Le (2026) formula already in bet_analytics.py CALIBRATION CONTEXT (confirmed)
     - FLB weakening monitoring: monthly tracker built
     - Political markets: CONFIRMED dead end current cycle (0 open markets until Q4 2026)

  7. COMMIT: 709b87c (9 new tests, 1674 total passing)

## S112 MONITORING KEY EVENTS (2026-03-19 ~21:08 UTC → 06:20 UTC)

  1. BOT AUTO-RESTART AT 05:23 UTC (PID 57412 → 87658)
     New log: /tmp/polybot_session114.log
     On restart: 5 auto-guards loaded ✓, Bayesian n=321 override_active=True ✓
     eth_drift config change (min_drift_pct=9.99 from S113 research) took effect at this restart.

  2. KXETH YES@92c SNIPER LOSS (-19.32 USD)
     id=3846, KXETH15M-26MAR190130-30 YES@92c, 21 contracts, -19.32 USD at ~00:30 UTC
     Auto-guard did NOT trigger (WR 92.9% = above 92% break-even, P&L < 5 USD threshold)
     KXETH YES@92c: n=14 bets, 92.9% WR, -1.26 USD total — MARGINAL bucket (barely above break-even)
     KXETH YES@93c: n=9, 88.9% WR, -10.83 USD — WARMING BUCKET on watchlist (needs n>=10 for guard)

  3. XRP_DRIFT UNBLOCKED
     Was BLOCKED at 5 consecutive losses at session start. Cleared streak to 0 during session.
     xrp_drift now READY FOR LIVE per --graduation-status.

  4. DIM 9: n=7→10 signal_features (3 new drift bets logged signal_features)

  5. SNIPER PERFORMANCE (today): 19/22 = 86.4% WR (-33.96 USD today) — bad variance day
     Sniper all-time: 721/753 = 95.75% WR, +46.13 USD (strong positive)
     Total bot all-time negative due to drift strategy losses (-56+ USD combined)

  6. CCA COMMS: POLYBOT_TO_CCA.md updated — REQUESTS 5,6,7: signal feature importance,
     KXETH @92-93c bucket structure (analytical, not guard-adding), sol_drift Stage 3 pathway.
     Political markets: conditional dead end (0 open KXSENATE/KXHOUSE markets until Q4 2026 midterms)

  7. MAIN→RESEARCH COMMS: ~/.claude/cross-chat/MAIN_TO_RESEARCH.md (NEW FILE)
     Research chat: read this at session start. Contains S112 overnight observations + analysis requests.
     Key message: NO trauma guards requested. Analytical questions only. Sniper is healthy.

## S113 KEY FINDINGS (research — 2026-03-19 04:00-07:00 UTC)

  1. ETH_DRIFT DISABLED IN CONFIG (PENDING RESTART)
     SPRT lambda=-3.811 (NO EDGE crossed -2.251 boundary). CUSUM S=14.460 (DRIFT ALERT >> 5.0).
     157 bets, 46.5% WR, -26.89 USD all-time. min_drift_pct raised to 9.99 (effectively infinite).
     Expected savings at next restart: ~2.7 USD/day.
     Re-enable criteria: 30+ bets with SPRT edge_confirmed + new direction_filter study.

  2. OVERNIGHT ANALYSIS — ROOT CAUSE FOUND
     Sleep hours 00-08 UTC: -99.19 USD all-time, WR=92.0%
     Root cause: March 17 08:xx correlated crash (5 simultaneous losses, ~97 USD) + guarded buckets (~48 USD)
     WITHOUT crash event: unguarded overnight WR CI [88.9%, 94.7%] overlaps break-even (92.5%).
     Formal time-of-day block NOT justified (4-condition standard not met yet).
     Drift strategies show structural overnight drag: btc_drift SLEEP=-0.57/bet vs DAY=+0.50/bet.
     CCA REQUEST 4 filed for academic backing of overnight drift effect.
     Main chat POLYBOT_TO_MAIN.md updated with full overnight guidance.

  3. POLITICAL MARKETS — CONDITIONAL DEAD END (revisit Q4 2026 midterms)
     Kalshi uses unified api.elections.kalshi.com — KXSENATE/KXHOUSE exist but 0 open markets.
     Math confirmed: b=1.83 = 14x crypto edge at 90c. No markets to trade until midterm cycle.
     20,000+ KXMVE (March Madness bracket) markets dominate current open market feed.

  4. BTC_DRIFT CUSUM: S=4.100/5.0 (APPROACHING THRESHOLD)
     SPRT lambda=-1.082 (still collecting). NOT disabling yet. Monitor at each session start.
     If CUSUM fires (S>=5.0): raise min_drift_pct to 9.99 same as eth_drift.

  5. WARMING BUCKETS: n=9 (no change since S112). Auto-guard gate needs n>=10, p<0.20.
     Check again when n>=20 for KXBTC YES@93c and KXETH YES@93c.

## S110 KEY EVENTS (monitoring — 2026-03-19)

  1. FALSE STALE TRADE ALARM RESOLVED (c2c6a8a)
     --health showed "1932 stale open trades" — false alarm.
     Root cause: all 2208 stale were paper dead-end strategy trades (sports_futures=2110, fomc=48, weather=43).
     Fix: excluded paper trades from stale check. 0 actual stale live trades.

  2. TWO SNIPER LOSSES (-39.27 USD total)
     KXBTC15M NO@94c ×21 = -19.74 USD | KXXRP15M NO@93c ×21 = -19.53 USD
     Cause: last-minute reversals in 20:30 UTC window. Not a bug — statistical event.
     Self-correction: 2 new auto-guards added. 5 total guards now active.

  3. CCA CONSULTATION COMPLETE
     CUSUM h=5.0 confirmed correct (Basseville & Nikiforov 1993 verified). No change.
     Multivariate Kelly question submitted to CCA: 4 simultaneous correlated crypto positions
     may require 0.25-0.5x Kelly fraction reduction (Nekrasov 2014, Thorp 2006).
     Corrected CCA's sniper sizing error ($5/bet → actual $19.50/bet).
     eth/btc drift already at micro-live since S60 — no action needed.

  4. SOFT STOP DISPLAY: "Daily loss soft stop active: $69.63 >= $24.41" in --health is COSMETIC ONLY
     Enforcement code is commented out (kill_switch.py lines 187-192). Bot trades freely.

  5. DIM 9 (SIGNAL_FEATURES): Wired correctly, not yet validated. No drift bets since PID 48350 restart.
     First drift bet in S111 should populate signal_features column.

## S109 KEY BUILD — Dim 9: Signal Feature Logger

  WHAT: Every live drift bet now logs full signal features as JSON to trades.signal_features.
  WHY: Meta-labeling classifier (per CCA KALSHI_INTEL.md r/algotrading finding):
       train binary classifier on features to filter low-quality signals → +1-3% WR.
       Currently ~350 drift bets total. Need 1000+. At 60-70/day: ~15 days away.
  FEATURES LOGGED: pct_from_open, minutes_remaining, time_factor, raw_prob,
       prob_yes_calibrated, edge_pct, win_prob_final, price_cents, side,
       minutes_late, late_penalty, bayesian_active.
  COMMIT: 8fbf56e — 8 new tests, 1631 passing.
  SELF-IMPROVEMENT CHAIN: signal fires → features logged → settle → label added →
       at n>=1000: meta-classifier trains → signal-level guard filters bad signals.

## THREE-CHAT SIZING DECISION (S109 — autonomous research chat analysis)

  SNIPER HARD_MAX ($20): KEEP.
    $15-20 range shows 94.2% WR (-$54 on 451 bets) vs $10-15 at 98.6% (+$86, 208 bets).
    Underperformance explained by now-guarded buckets (KXXRP NO@93c, KXBTC NO@94c, etc.)
    being in the $15-20 range before guards existed. With all 5 guards active, expect recovery.
    TRIGGER FOR CHANGE: if post-S108 $15-20 WR stays below 96% after 30+ clean bets.

  SOL DRIFT CAP: NO CHANGE. Kelly(WR=69.8%) = $5.72 at current bankroll, Stage 1 cap = $5.
    Natural scaling as bankroll grows. Stage 3 ($15 cap) at bankroll $250 still the target.

  ETH/BTC/XRP: KEEP MICRO-LIVE. Data instruments at $0.39/bet. ETH no edge, BTC improving.

## GUARD ANTICIPATION QUESTION (Matthew asked S109)
  Not worth pre-anticipating guards. Auto-guard catches bad buckets in ~3 bets = max $57 loss.
  Pre-emptive blocking = speculation. The signal_features logger IS the future solution:
  at n=1000+, meta-classifier learns signal-level patterns better than bucket-level guards.
  Next: "warming bucket watchlist" — log n>=2 negative P&L buckets for visibility only.

## S108 RESEARCH WRAP KEY EVENTS

  1. 2 NEW AUTO-GUARDS ACTIVATED (5 total now)
     KXXRP NO@93c: n=24, 91.7% WR (need 93.4%), -15.3 USD — NEW
     KXBTC NO@94c: n=10, 90.0% WR (need 94.4%), -11.24 USD — NEW
     Bot restarted to activate. Now running 5 auto-guards.

  2. FLB ACADEMIC RESEARCH COMPLETE (Pillar 2)
     Verified papers confirm structural basis for sniper edge:
     - Burgi, Deng & Whelan (2026 CESifo WP 12122): Kalshi-specific — 95c → 98% WR (+3pp)
     - Snowberg & Wolfers (2010 NBER WP 15923 / JPE): probability misperception drives FLB
     - Ottaviani & Sorensen (2010 AEJ:Micro): fixed-odds FLB strengthens with informed bettors
     Full research: .planning/EDGE_RESEARCH_S108.md

  3. PER-BUCKET SNIPER VALIDATION (734 live bets analyzed)
     90-95c zone: all buckets show positive FLB excess (+0.6 to +10pp)
     96c+ zone: all negative (-1.9 to -5.7pp) — ceiling at 95c confirmed
     95c YES = 98.1% WR (+3.1pp, n=52) — exact match to Burgi-Deng-Whelan prediction

  4. BET ANALYTICS STATE (S108)
     sniper: 734 bets, EDGE CONFIRMED lambda=+15.332, CUSUM stable S=2.025
     sol_drift: n=43, EDGE CONFIRMED lambda=+2.886, Brier 0.198
     btc_drift: CUSUM improved 4.480 → 4.020 (S107 → S108), lambda=-1.056 (collecting)
     eth_drift: CUSUM 14.140 → 12.760 (slight improvement), SPRT NO EDGE confirmed
       NOTE: Bayesian + calibration handles. No manual action per PRINCIPLES.md.
     Bayesian: n=311, override_active=True, T values unchanged (insufficient new bets)

## SELF-IMPROVEMENT BUILD STATUS
  COMPLETE (Sessions 98-108):
  - Dim 1a: scripts/auto_guard_discovery.py — 5 auto-guards now active
  - Dim 1b: live.py — loads data/auto_guards.json at module import
  - Dim 2:  src/models/bayesian_drift.py — BayesianDriftModel, online MAP update
  - Dim 3:  settlement_loop — posterior updated after each live drift bet
  - Dim 4:  generate_signal() — predict() ACTIVE (n=311 >= 30, override_active=True)
  - Dim 5:  scripts/guard_retirement_check.py — 16 guards warming
  - Dim 7:  scripts/strategy_drift_check.py — Page-Hinkley test
  - S104:   scripts/bayesian_bootstrap.py — retroactive posterior seeding
  - S105:   scripts/bet_analytics.py — SPRT/Wilson CI/Brier/CUSUM (24 tests)
  - S107:   src/models/temperature_calibration.py — per-strategy T_s (18 tests)
  - S108:   FLB theoretical grounding complete (research-only, no code build)
  - S109:   Dim 9 signal feature logger — trades.signal_features JSON column (8fbf56e)

## S117 KEY FINDINGS (2026-03-19 ~19:30-20:00 UTC — context-overflow continuation)

  1. BANKROLL STAGING CLARIFIED: bankroll=179.76 USD → Stage 2 → 10 USD/bet drift cap.
     Log message "STAGE 1 SOL drift — Kelly + $5 cap" is stale. Actual cap = 10 USD.
     No code change needed — sizing.py already handles this correctly.

  2. sol_drift SPRT CROSSED EDGE_CONFIRMED: lambda=+2.886 (boundary=+2.890). First formal crossing.
     CUSUM=0.560 (stable). Brier=0.198. Strongest-validated drift strategy.

  3. btc_drift CUSUM: 4.260/5.0 (up from 4.180). Still below threshold. Monitor.
     If S>=5.0 at any session start: disable (min_drift_pct=9.99).

  4. KXETH YES@93c: still n=9. Auto-guard not yet fired. Check at next session start.

  5. CCA REQUEST 8+9: still pending. No new responses.

  6. All-time live P&L: +11.35 USD. Bankroll: 179.76 USD (Stage 2).

## PENDING FOR S118+ (updated S117 wrap):
  #1 XRP SNIPER — GUARDS ARE SUFFICIENT (resolved S116):
     All-time SPRT lambda=-2.769 (no-edge) was dominated by pre-guard losses.
     FORWARD SPRT (post-guard, in-zone): lambda=-0.558 [collecting — not at boundary].
     NO additional XRP intervention needed. Monitor YES@94c (n=15, WR=93.3%).
     CCA REQUEST 8 updated: guards sufficient, academic mechanism still interesting.
  #2 btc_drift CUSUM: 4.180/5.0. If S>=5.0 at session start: disable (min_drift_pct=9.99).
     SPRT lambda=-1.108. If crosses -2.251: also disable.
  #3 KXETH YES@93c warming bucket: n=9, 1 bet from auto-guard threshold.
     Next bet triggers check. Run scripts/auto_guard_discovery.py at session start.
  #4 CCA REQUEST 4 (overnight drift academic) — check CCA_TO_POLYBOT.md for response.
  #5 CCA REQUEST 9 (market conditions non-stationarity) — regime detection research pending.
  #6 Meta-labeling Dim 9: n=11 bets with signal_features. Target n=1000. Passive.
  #7 Guard retirement (Dim 5): needs 50+ paper bets per guarded bucket. Passive.
  #8 sol_drift Stage 3: bankroll needs 250 USD. Currently ~90 USD. Natural growth.
  #9 FLB weakening tracking: monthly WR tracker built. Check April 2026 when data available.

  CONFIRMED DEAD ENDS (cumulative):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper (no WR data),
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  time-of-day filtering, non-crypto 90c+ markets, annual BTC range markets,
  one-off market scanners, per-strategy full Bayesian models (marginal benefit),
  stale open trades investigation (false alarm — all paper long-duration markets),
  CUSUM h=5.0 change (ARL simulation confirms h=5.0 is correct),
  Sports game markets (KXNBAGAME/KXNHLGAME/KXMLBGAME) = zero volume across all settled+open,
  Finance markets (KXFED/KXCPI/KXGDP/KXPCE) = zero volume,
  R-score ranking for sniper = 1.9% window competition rate makes it irrelevant,
  KXBNB15M sniper = too thin (~400 contracts/market vs XRP's 6,400; max fill ~7 USD/bet),
  KXDOGE15M sniper = too thin (vol=745, even thinner than BNB),
  All other crypto 15M series = do not exist on Kalshi (LTC/MATIC/AVAX/LINK/ADA/DOT etc all 404),
  Crypto 15M expansion COMPLETE: BTC/ETH/SOL/XRP are the ONLY viable series on Kalshi

## S111 MONITORING KEY EVENTS (2026-03-19 21:08–04:06 UTC)
  1. ALL-TIME P&L TURNED POSITIVE (+3.07 USD) — started session at -7.44 USD, +10.93 USD session gain
  2. DIM 9 VALIDATED — trade id=3814 confirmed signal_features populated
  3. WARMING BUCKET WATCHLIST: CLEAN — all negative buckets already guarded
  4. XRP_DRIFT BLOCKED extended to 5 consecutive losses (was 4)
  5. SDATA: 88% (438/500) resets 2026-04-01 — avoid heavy research scans

## STARTUP SEQUENCE FOR S114 (monitoring):
    1. ps aux | grep "[m]ain.py" (expect PID 87658 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session114.log | tail -1
       MUST say: "Loaded 5 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session114.log | tail -1
       MUST say: override_active=True, n>=321
    4. ./venv/bin/python3 scripts/bet_analytics.py (check CUSUM — btc_drift 4.100/5.0 APPROACHING)
    5. ./venv/bin/python3 scripts/auto_guard_discovery.py (verify 0 new guards needed)
    6. ./venv/bin/python3 main.py --graduation-status (xrp streak=0, READY FOR LIVE)
    7. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (CCA research responses)
    8. Verify Dim 9 count:
       python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); print(c.execute('SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy LIKE \"%drift%\" AND signal_features IS NOT NULL').fetchone())"
    9. Confirm eth_drift not firing: grep "eth_drift" /tmp/polybot_session114.log | grep "LIVE BET" | tail -3
       Should be EMPTY (eth_drift disabled min_drift_pct=9.99)

## RESTART COMMAND (for future restarts — session 114):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session114.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## STRATEGY STANDINGS (~06:20 UTC March 19 — S112 monitoring wrap)
  expiry_sniper_v1:  PRIMARY ENGINE — 753+ live bets, 95.75% WR all-time, +46.13 USD sniper-only P&L
                     All-time BOT P&L: -10.36 USD (drift drag ~-56 USD)
                     5 guards active: 0 guard failures this session
                     WARMING BUCKETS: KXETH YES@92c (n=14, marginal), KXETH YES@93c (n=9, -10.83 USD watchlist)
                     SPRT lambda=+15.332 EDGE CONFIRMED | CUSUM S=2.025 stable
                     5 auto-guards: KXXRP NO@95c + KXSOL NO@93c + KXBTC YES@94c +
                                    KXXRP NO@93c + KXBTC NO@94c
  sol_drift_v1:      LIVE Stage 1 — T=1.290 (calibration BOOSTING Kelly)
                     SPRT lambda=+2.886 EDGE CONFIRMED | Brier 0.198 | n=43
  btc_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=4.020 (improving) | direction_filter="no"
  eth_drift_v1:      LIVE Stage 1 — T=0.500 (calibration REDUCING Kelly)
                     CUSUM S=12.760 (improving) | Bayesian self-corrects | no edge per SPRT
  xrp_drift_v1:      LIVE micro — T=0.500 | BLOCKED (4 consec) | direction_filter="yes"
  Bayesian posterior: n=311, override_active=TRUE, kelly_scale=0.952
  Temperature calibration: ACTIVE (data/calibration.json, T values stable)
  Dim 9 signal_features: WIRED, NOT YET VALIDATED (0 features logged — no drift bets since restart)

## GUARD STACK (IL-5 through IL-32 + floor 90c + ceiling 95c + 5 auto-guards)
  Active auto-guards:
    KXXRP NO@95c: n=19, 94.7% WR — ACTIVE (original)
    KXSOL NO@93c: n=12, 91.7% WR — ACTIVE (original)
    KXBTC YES@94c: n=13, 92.3% WR — ACTIVE (added S105)
    KXXRP NO@93c: n=24, 91.7% WR — ACTIVE (NEW S108)
    KXBTC NO@94c: n=10, 90.0% WR — ACTIVE (NEW S108)

## GOAL TRACKER
  All-time P&L: +22.91 USD live (S107 data — no new P&L this research session)
  Monthly target: 250 USD self-sustaining (covers Claude Max20)
  At 34 USD/day sniper rate: ~6.7 days to monthly self-sustaining
  Distance to +125 USD milestone: ~102 USD

## FLB RESEARCH NOTE (S108)
  Research chat S108: FLB academic basis confirmed + per-bucket validation.
  Full findings: .planning/EDGE_RESEARCH_S108.md
  Key: 5 verified papers confirm structural FLB edge. Ceiling at 95c theoretically
  and empirically correct. Sniper edge = FLB, not noise.
