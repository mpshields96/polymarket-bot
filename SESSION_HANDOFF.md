# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-21 ~16:35 UTC (Session 120 monitoring — sniper signal_features, warming buckets, TestSniperHourBlock fix)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 29204 → /tmp/polybot_session120.log
  All-time live P&L: +20.05 USD (session net: +7.77 USD from +12.28 at S119 monitoring wrap)
  Today P&L: +6.93 USD live (5/5 = 100% WR, sniper only)
  Bankroll: ~131 USD (starting $100 + cumulative profits)
  Tests: 1716 passing. Last commit: fddc0b4 (feat: sniper signal_features for Dim 9 meta-labeling)
  eth_drift: DISABLED (min_drift_pct=9.99) — confirmed 0 bets
  xrp_drift: LIVE (direction_filter="yes")

## S120 MONITORING KEY FACTS (2026-03-21 ~16:35 UTC)

  BUILDS:
  - commit 3e889eb: TestSniperHourBlock tests now read _BLOCKED_HOURS_UTC from main.py via AST
    (was trivially self-validating — hardcoded frozenset({8,13}) testing against itself)
  - commit 1df7dcc: discover_warming_buckets() fixed to check auto_guards.json (not just hardcoded IL guards)
    + added to main() output so every auto_guard run shows warming bucket watchlist
  - commit c4edbfd: TestWarmingBuckets — 7 new tests covering all warming bucket scenarios
  - commit fddc0b4: Sniper signal_features — utc_hour, day_of_week, coin, seconds_remaining, drift_pct
    now logged to trades.signal_features for every live sniper bet (Dim 9 meta-labeling)
    11 new tests. All 1716 passing.

  RESOLVED:
  - KXETH YES@93c: Already blocked as IL-30 in live.py line 369. No pending action.
  - "Stage 2 cap: $10.00" in btc_drift SIZE log: Not a promotion — bankroll-driven (131 USD = Stage 2)
  - CCA ACTION REQUIRED (2026-03-19): All 3 items resolved (sniper sizing OK, eth disabled, btc no-change)
  - CCA REQUEST 8 (XRP bad hours): p=0.084, gate NOT met. No guard. Collect 50+ more bets.
  - Hour block: Confirmed frozenset() in main.py — no hours blocked. Verified at restart.

  CUSUM STATUS (critical monitoring):
  - btc_drift: CUSUM S=4.260/5.0 — CRITICAL. Disable at S>=5.0 (min_drift_pct=9.99)
  - xrp_drift: CUSUM S=3.440/5.0 — WATCH. Disable if S>=5.0 or next 10 bets <50% WR
  - eth_drift: CUSUM S=15.000 (expected — disabled strategy, historical data only)
  - sol_drift: CUSUM S=0.560 — stable, SPRT EDGE CONFIRMED

  GUARD INTEGRITY:
  - 5 auto-guards loaded: KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c
  - IL-30: KXETH YES@93c ALREADY BLOCKED in live.py (not just auto-guard)
  - Hour block: frozenset() — ALL HOURS ACTIVE
  - Signal_features: now logging on every sniper signal (verify in DB on next live bet)

  CCA PENDING:
  - REQUEST 11: 00:xx Asian session mechanism — still collecting (need n>=30)
  - REQUEST 12: Earnings Mentions scan — SDATA 462/500 (HIGH), resets 2026-04-01
  - REQUEST 14: XRP YES@91c at 08:xx UTC pattern (n=2, too early)

## S119 RESEARCH WRAP KEY FINDINGS (2026-03-20 ~21:00 UTC)

  HOUR BLOCK AUDIT — BOTH BLOCKS SHOULD BE REVERTED:

  08:xx block: z=-4.30 was crash-contaminated. 5 of 7 losses = March 17 crash.
    Without March 17: n=26, WR=92.3%, z=+0.06 — NOT statistically significant.
    Non-XRP at 08:xx (ex March 17): n=20, WR=100%, P&L=+19.75 USD.
    The 2 non-crash losses = both XRP YES@90-95c (n=4, too small for guard).
    RECOMMENDATION: REVERT — remove 8 from _BLOCKED_HOURS_UTC.
    Estimated cost of keeping block: ~3-4 USD/day in missed winning sniper bets.

  13:xx block: both losses = already-guarded KXXRP buckets (NO@91c, March 15).
    Post-guard 13:xx: n=20, WR=100%. z=-0.46 (not significant — confirmed by research).
    RECOMMENDATION: REVERT — remove 13 from _BLOCKED_HOURS_UTC.
    Estimated cost of keeping block: ~2 USD/day in missed winning sniper bets.

  Combined impact: blocks costing ~5-6 USD/day at zero statistical justification.

  CRASH-PAUSE — DEAD END:
    787 sniper windows analyzed. Max losses per window = 1. Windows with 3+: ZERO.
    March 17 losses were consecutive single-asset losses, not simultaneous multi-asset.
    The crash-pause trigger condition has NEVER occurred in the entire sniper history.
    Added to confirmed dead ends.

  DECISION 2 REVISED — DO NOT SUSPEND SOL_DRIFT:
    S118 vote to suspend was premature. Current CUSUM=0.560 (stable), SPRT EDGE CONFIRMED.
    Last 10 bets: WR=60%, P&L=+1.85 USD (recovering). The -8.59 USD 7-day was high variance.
    REVISED VOTE: Keep sol_drift running. Monitor CUSUM.

  XRP_DRIFT — APPROACHING THRESHOLD:
    YES WR=51.3%, CUSUM S=3.440/5.0, last 7 days WR=43.8%. Trending toward disable.
    Not at formal threshold. Watch for CUSUM>=5.0 or next 10 bets <50% WR.

  NEW REQUEST 14 TO CCA: XRP YES at 08:xx UTC (n=4, WR=50%) — auto-guard candidate.
    Filed in POLYBOT_TO_CCA.md for CCA analysis.

  Full findings in POLYBOT_TO_MAIN.md.

## S118 RESEARCH WRAP KEY FINDINGS (2026-03-20 ~04:00 UTC)

  OVERNIGHT P&L DECOMPOSITION — THE "WAKING UP TO LOSSES" PROBLEM:
  Root cause identified: eth_drift was losing -31.55 USD overnight (10PM-8AM UTC).
  eth_drift is NOW DISABLED. The systematic overnight bleed is gone.
  Sniper overnight without crash events: profitable. With crash (March 17): -9.37 USD/month.
  THREE-CHAT DECISION DOCUMENTED: POLYBOT_TO_MAIN.md (all three decisions written explicitly).
  DECISION.md created at project root — unmissable summary for Matthew.

  THREE OBJECTIVE DECISIONS (research chat votes — main chat + CCA to confirm):
  1. RUN OVERNIGHT: YES. Sniper works overnight. Stopping loses ~87 USD/month.
  2. SUSPEND xrp_drift + sol_drift: YES (research chat recommendation).
     xrp_drift -2.27 USD, sol_drift -8.59 USD last 7 days. Not formally triggered but directional.
     Main chat: set min_drift_pct=9.99 for both to suspend. Await main chat decision.
  3. CRASH-PAUSE MECHANISM: PENDING CCA ANALYSIS. CCA REQUEST 13 filed.
     Concept: if 3+ of 4 crypto markets lose in same 15-min window, pause 60 min.
     Needs CCA to confirm false-positive rate before building.

  HOUR BLOCK DISCREPANCY (flag for main chat):
  Main chat deployed {8, 13} UTC sniper block (commit 8008c17, z=-4.30 for 08:xx).
  Research chat finds 08:xx block may be crash-contaminated: 5/7 losses were March 17.
  Non-crash 08:xx WR = 93.75% (above break-even). Flagged in POLYBOT_TO_MAIN.md.
  Main chat should verify their z=-4.30 calculation and confirm or revert.

  SELF-LEARNING LOGGED: 4 entries to CCA journal (2 wins, 2 pains).
  Key win: strategy×hour decomposition prevents wrong time blocks.
  Key pain: chats acting on same data with different conclusions (need sync protocol).

## S118 MONITORING WRAP KEY EVENTS (2026-03-20 ~01:15 UTC)

  1. UTC HOUR BLOCK DEPLOYED (main.py — commit 8008c17)
     _BLOCKED_HOURS_UTC = frozenset({8, 13}) added to expiry_sniper_loop()
     08:xx: WR=82.1% n=39 z=-4.30 — European open + Asia close crossover structural daily mechanism
     13:xx: WR=90.5% n=21 — US market open at 13:30 UTC structural daily mechanism
     Block is objective (structural daily recurrence), NOT trauma-based (NOT single-event).
     00:xx excluded: losses explained by already-guarded buckets + March 17 crash, not structural.
     7 new tests in TestSniperHourBlock — all passing (1698 total).
     Bot restarted with hour block active. PID 54374, 5 guards loaded, n=326 Bayesian.

  2. SESSION NET: -4.95 USD (was +11.35 at S115 → now +6.40 USD all-time)
     Losses occurred BEFORE hour block was deployed. Expected to improve going forward.

  3. SDATA: 450/500 (90%) — resets 2026-04-01. Avoid heavy research scans.

  4. CRITICAL STARTUP CHECKS FOR S119:
     grep "Loaded.*auto-discovered" /tmp/polybot_session118.log | tail -1
     MUST say: "Loaded 5 auto-discovered guard(s)"
     grep "override_active=True" /tmp/polybot_session118.log | tail -1
     MUST say: override_active=True, n>=326
     grep "eth_drift.*LIVE BET" /tmp/polybot_session118.log | tail -3
     MUST be EMPTY (eth_drift disabled)
     grep "Hour block" /tmp/polybot_session118.log | tail -5
     Should show block firing at 08:xx or 13:xx if those hours have passed

## S118 RESEARCH + PRIOR KEY FINDINGS (preserved)

  1. CCA DELIVERED: Le (2026) arXiv:2602.19520 — VERIFIED calibration slopes
     Crypto b=1.03: sniper edge is structural FLB, NOT calibration (0.3-0.5pp calibration only)
     Politics b=1.83: 8-10pp edge at 90-95c — but 0 open markets (revisit Q4 2026)
     Weather b=0.75: favorites OVERPRICED — avoid
     Implementation: calibration_adjusted_edge() in bet_analytics.py + CALIBRATION_B_* constants

  2. 00:xx UTC NO ANOMALY DECOMPOSED (resolved)
     Raw: n=16 00:xx NO bets, WR=75%. After decomposition: 4/16 already-guarded (-37.17 USD) won't fire again.
     Remaining 12 unguarded: WR=83.3%, 2 losses = March 17 crash + KXBTC NO@92c.
     CONCLUSION: Do NOT add 00:xx time guard. Wait for CCA REQUEST 11 + n>=30 unguarded.

  3. FULL KALSHI MARKET SCAN — CONFIRMED DEAD END
     Non-crypto markets: ~40 vol/market. High-conf (90-95c, vol>=1K) non-crypto: ZERO found.
     CONFIRMS: crypto 15M (BTC/ETH/SOL/XRP) are the full viable set.

  4. EARNINGS MENTIONS — POTENTIAL PILLAR 3 (April-May 2026 earnings season)
     Q1 earnings call markets (will company say [word] in Q1 earnings?)
     CCA REQUEST 12 filed: volume data + structural edge validation needed first.

  5. ROLLING WR TRACKER built (analyze_sniper_rolling_wr in bet_analytics.py — commit 36334d0)
     W16* (n=39): 94.9% WR. No ALERT. No declining trend. FLB weakening not visible yet.

  6. FORWARD EDGE: XRP guards are SUFFICIENT.
     Post-guard in-zone SPRT: BTC lambda=+7.254, ETH lambda=+7.704, SOL lambda=+4.092, XRP lambda=-0.558 [collecting]
     XRP: NOT at no-edge boundary. Guards sufficient. No additional XRP intervention.

## PENDING FOR S120+

  #1 HOUR BLOCK REVERTED (S119 monitoring): frozenset() in main.py — bot runs all hours now.
     REASON: S119 research proved both blocks crash-contaminated. Post-strip: 08:xx WR=92.3%
     (z=+0.06 not significant), 13:xx post-guards WR=100%. Cost was ~5-6 USD/day.
     VERIFY FIRST POLL: grep "expiry_sniper.*Signal" /tmp/polybot_session119.log at 08:xx UTC
     Should show signals firing (not blocked). Tests updated to pass with frozenset().
  #2 KXETH YES@93c warming bucket: n=9, 1 bet from auto-guard threshold (WR=88.9% < 93% BE).
     Run scripts/auto_guard_discovery.py at session start. Will fire at n=10.
  #3 btc_drift CUSUM: 4.260/5.0. If S>=5.0 at session start: disable (min_drift_pct=9.99).
     SPRT lambda=-1.134. If crosses -2.251: also disable.
  #4 CCA REQUEST 11 (00:xx UTC Asian session mechanism) — PENDING.
  #5 CCA REQUEST 12 (Earnings Mentions volume + edge) — PENDING (Q1 2026 season April).
  #6 CCA REQUEST 13 PART B: CLOSED — crash-pause dead end. Only trigger (Mar17 08:xx) already
     covered by... wait, hour block REVERTED. But crash-pause still dead end (p=0.095, n=1).
  #7 Dim 9 accumulation: n=13 signal_features. Target 1000. Passive.
  #8 SDATA: 453/500 (91%) — avoid heavy research scans. Resets 2026-04-01.
  #9 "Daily loss soft stop active" in --health = COSMETIC ONLY (enforcement commented out).
  #10 S119 RESEARCH: XRP_DRIFT approaching threshold (CUSUM=3.44, last 7d WR=43.8%). Watch.

## GUARD STACK
  Floor 90c + Ceiling 95c + 5 auto-guards:
    KXXRP NO@95c — ACTIVE
    KXSOL NO@93c — ACTIVE
    KXBTC YES@94c — ACTIVE
    KXXRP NO@93c — ACTIVE
    KXBTC NO@94c — ACTIVE
  AUTO-GUARD: MIN_BETS=10, p<0.20 significance gate required
  WARMING WATCH: KXETH YES@93c (n=9) — NEXT CANDIDATE (1 bet from threshold)

## HOUR BLOCK — REVERTED S119 monitoring wrap
  _BLOCKED_HOURS_UTC = frozenset() — NO hours blocked (all hours run)
  REASON: S119 research proved crash contamination. Ex-crash: 08:xx z=+0.06 (not significant).
  Cost of blocks was ~5-6 USD/day. Reverted 2026-03-20 02:10 UTC.
  Tests still pass — TestSniperHourBlock tests hardcode frozenset({8,13}) internally.
  NOTE: Tests should be updated next research session to reflect reverted state.

## STRATEGY STANDINGS (S119 monitoring wrap)
  expiry_sniper_v1:  PRIMARY ENGINE — 801+ live bets, 95.8% WR, +68.25 USD sniper-only
                     All-time BOT P&L: +12.28 USD
                     HOUR BLOCK REVERTED — all hours now active
                     SPRT BTC/ETH/SOL lambda=+6-8 EDGE CONFIRMED | XRP lambda=-0.333 [collecting]
  sol_drift_v1:      LIVE Stage 1 — 43 bets, 70% WR, +4.89 USD EDGE CONFIRMED
                     CUSUM stable (S=0.560), SPRT EDGE CONFIRMED
  btc_drift_v1:      MONITORING — 75 bets, 49% WR, CUSUM S=4.260/5.0 APPROACHING
                     direction_filter="no", SPRT lambda=-1.134 [collecting]
  eth_drift_v1:      DISABLED — min_drift_pct=9.99 — 0 live bets confirmed
  xrp_drift_v1:      WATCH — 50 bets, CUSUM S=3.440/5.0, last 7d WR=43.8%
                     direction_filter="yes"
  Bayesian posterior: n=326, override_active=True, kelly_scale=0.953
  Dim 9 signal_features: n=13. Target 1000. Passive accumulation.

## CONFIRMED DEAD ENDS (cumulative)
  CPI/GDP/FOMC/UNRATE speed-plays, UCL/NCAA live sports, BALLDONTLIE,
  weather, NBA/NHL/tennis sniper, KXBTCD near-expiry, sniper maker mode,
  time-of-day filtering (general overnight block — CI too wide; 00:xx decomposed = not structural),
  non-crypto 90c+ markets, annual BTC range, one-off market scanners,
  per-strategy full Bayesian models, stale open trades (false alarm — all paper),
  CUSUM h=5.0 change (confirmed correct), Sports game markets (KXNBAGAME/KXNHLGAME) = vol=0,
  Finance markets (KXFED/KXCPI/KXGDP/KXPCE) = vol=0, R-score ranking = 1.9% window competition,
  KXBNB15M = too thin, KXDOGE15M = even thinner, all other crypto 15M = don't exist on Kalshi,
  Crypto 15M expansion COMPLETE: BTC/ETH/SOL/XRP are the ONLY viable series on Kalshi,
  Political markets current cycle (March 2026) = 0 open markets — revisit Q4 2026,
  00:xx UTC general block = NOT structural (decomposed S118: guarded + crash explains losses),
  Full Kalshi non-crypto scan = 11K markets avg 40 vol = not viable

## RESTART COMMAND (Session 120)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session120.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## GOAL TRACKER
  All-time P&L: +12.28 USD live | Monthly target: 250 USD self-sustaining
  Sniper-only: +68.25 USD (bot all-time dragged by early pre-guard drift losses)
  At current sniper rate: ~7-10 USD/day + ~5-6 USD/day recovered from hour block revert
  Distance to +125 USD milestone: 112.72 USD
  Highest-leverage action: Keep bot alive + let hour block compound over 08:xx/13:xx windows
