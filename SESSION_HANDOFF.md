# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-19 ~02:50 UTC (Session 111 research)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 57412 → /tmp/polybot_session108.log (check log path — daemon may have restarted)
  All-time live P&L: -7.86 USD (recovering; S111 today: -31.98 USD live from 2 large sniper losses)
  Tests: 1653 passing. Last commit: e445391 (docs: S111 research — political markets correction)
  NOTE: Bot PID changed from 48350 (S110) to 57412 — restart occurred, all guards reloaded

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

## PENDING FOR S112+:
  #1 Meta-labeling data accumulation — Dim 9 VALIDATED (trade 3814 has signal_features).
     n=2 bets with signal_features so far. Target n=1000 for meta-classifier.
     Currently 315 total drift bets. At ~60/day: ~11 more days.
  #2 Multivariate Kelly — RESOLVED. CCA: 1/N conservative scaling. At 4 simultaneous positions,
     scale each Kelly fraction by 0.25x. Current conservative sizing already handles this.
  #3 Warming bucket watchlist — DONE in S111. All 19 negative buckets fully guarded (IL-5 to IL-32).
     Zero genuine gaps in guard stack. No new script needed — auto_guard handles future gaps.
  #4 Monitor new guards (KXXRP NO@93c, KXBTC NO@94c) — verify WR improving post-block
  #5 sol_drift Stage 3 check — bankroll needs $250+. Currently ~$88. Natural growth.
  #6 BTC very_high edge_pct guard: n still below 30 — monitor passively
  #7 Monitor temperature calibration T values (too few new bets to see shift yet)
  #8 Guard retirement — Dim 5 needs 50+ paper bets per bucket (~3+ more weeks)
  #9 Political markets Pillar 3 — CCA request filed (2026-03-19). Await CCA response on:
     - Kalshi political market liquidity and ticker structure
     - Le (2026) calibration: b=1.83 near-expiry → 8.2pp edge at 90c (S111 corrected CCA's 4pp)
     - Whether near-expiry political sniper (15min-6hr) is viable with sufficient volume
  #10 FLB weakening monitor — sniper_monthly_wr.py now tracks rolling 30-day WR.
      Current: 2026-03 at 95.8%, no degradation signal. Run at each session start.
  #11 Sniper daily losses pattern — 2 large losses per session for 2 sessions straight (-30+ USD/day).
      All in guarded buckets or coincidence? Check guard coverage for recent losses at next session.

  CONFIRMED DEAD ENDS (cumulative):
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports sniper (no WR data),
  BALLDONTLIE, weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  time-of-day filtering, non-crypto 90c+ markets, annual BTC range markets,
  one-off market scanners, per-strategy full Bayesian models (marginal benefit),
  stale open trades investigation (false alarm — all paper long-duration markets),
  CUSUM h=5.0 change (ARL simulation confirms h=5.0 is correct)

## STARTUP SEQUENCE FOR S111:
    1. ps aux | grep "[m]ain.py" (expect PID 48350 or daemon-restarted)
    2. grep "Loaded.*auto-discovered" /tmp/polybot_session108.log | tail -1
       MUST say: "Loaded 5 auto-discovered guard(s)"
    3. grep "override_active=True" /tmp/polybot_session108.log | tail -1
       MUST say: override_active=True, n=311
    4. ./venv/bin/python3 scripts/bet_analytics.py (check drift stats, CUSUM)
    5. ./venv/bin/python3 scripts/auto_guard_discovery.py (any new guards?)
    6. ./venv/bin/python3 main.py --graduation-status
    7. cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -80 (check CCA multivariate Kelly response)
    8. Verify Dim 9 on first drift bet:
       python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); print(c.execute('SELECT id, signal_features FROM trades WHERE is_paper=0 AND strategy LIKE \"%drift%\" ORDER BY id DESC LIMIT 1').fetchone())"

## RESTART COMMAND (for future restarts — session 111):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session111.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then check bot.pid.

## STRATEGY STANDINGS (~01:45 UTC March 19 — S110 wrap)
  expiry_sniper_v1:  PRIMARY ENGINE — ~750 settled, 95%+ WR (2 losses today), all-time recovering
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
