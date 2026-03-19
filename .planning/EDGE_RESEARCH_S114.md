# EDGE_RESEARCH_S114.md — Session 114 Research + Monitoring Findings
# Date: 2026-03-19
# Session type: Research (overnight) → Monitoring (daytime)
# Grade: C — monitoring solid, overnight window evidence strengthened, no new tools built

## SESSION OVERVIEW

This session started as a research session continuing from S113 but pivoted to overnight
monitoring per Matthew's directive. The primary research output was empirical confirmation
of the 05-09 UTC high-risk window and successful verification that eth_drift disable
is working.

## KEY FINDING 1 — 05-09 UTC HIGH-RISK WINDOW CONFIRMED (2 data points)

Both losses on 2026-03-19 fell inside or adjacent to the 05-09 UTC window:

  Loss 1: KXETH YES@92c settled 05:30 UTC → -19.32 USD (placed by OLD bot ~05:21 UTC)
  Loss 2: KXSOL YES@93c settled 09:15 UTC → -19.53 USD (placed by NEW bot ~09:00 UTC)

Post-09:30 UTC: 21 consecutive wins, 100% WR, +19.67 USD.

Combined with S113 analysis:
  Sleep hours 00-08 UTC all-time: WR=92.0%, -99.19 USD
  The March 17 correlated crash (08:xx UTC, ~97 USD loss) dominates the all-time number.
  WITHOUT crash event: overnight CI [88.9%, 94.7%] overlaps break-even (92.5%).

Status: NOT yet at 4-condition standard for a formal guard or sizing change.
  - Structural basis: plausible (European open transition, Asian session close)
  - Math validation: 2 recent catastrophic examples but n=1 truly catastrophic event
  - DB backtest: confirmed negative EV in 00-08 UTC window all-time
  - p-value: SPRT boundary NOT crossed for time-of-day filter specifically

NEXT STEP: CCA REQUEST 4 (academic backing for overnight drift effect in crypto markets).
If CCA finds strong structural basis → implement partial Kelly reduction for 05-09 UTC window.
This is the highest-priority open research question.

## KEY FINDING 2 — ETH_DRIFT DISABLE CONFIRMED WORKING

Monitored 83+ cycles (6+ hours post-restart). Zero eth_drift bets post-restart.
config.yaml min_drift_pct=9.99 is a reliable disable mechanism.

eth_drift status at wrap:
  All-time: 165+ bets, 46.5% WR, -26+ USD. SPRT lambda=-3.811 (NO EDGE confirmed).
  CUSUM S=14.460 (DRIFT ALERT far beyond threshold of 5.0).
  Re-enable criteria: 30+ new bets with SPRT edge_confirmed + new direction_filter.

## KEY FINDING 3 — MONITOR SCRIPT TIMEZONE BUG

The overnight monitor script (/tmp/polybot_overnight_monitor.sh) has a bug:
BOT_START is computed from `ps -p $PID -o lstart=` which returns LOCAL time (CDT = UTC-5).
The `date -j` command on macOS may interpret this as local time correctly, but the result
produced incorrect since-restart P&L readings (showed +9.09 USD when actual was -10.23 USD).

The script counted 24 settled bets at +9.09 USD by missing the two big losses:
  - 05:30 UTC KXETH loss (-19.32) was attributed to pre-restart by the script
  - 09:15 UTC KXSOL loss (-19.53) may also have been missed depending on the computed restart epoch

Fix needed: use a hardcoded restart epoch from bot.pid creation time, or verify the
macOS date -j timezone handling.

IMPLICATION: The monitor script PnL readings are not reliable for since-restart accounting.
Use direct DB queries with explicit UTC timestamps for accurate P&L attribution.

## KEY FINDING 4 — DAYTIME SNIPER PERFORMANCE (POST-09:30 UTC)

After the 09:15 UTC loss, 21 consecutive wins through 12:27 UTC:
  09:16 → 12:16 UTC: all wins, 100% WR, +19.67 USD
  Price range: 90c to 95c (all within sniper zone)
  Assets: BTC, ETH, SOL — all performing

This is consistent with S113 finding that DAY hours (09-21 UTC) are the strong window.

## TOOLS BUILT

None new. Session pivoted to monitoring before research tools could be built.
Monitor script bug documented above (not fixed — needs careful UTC timestamp handling).

## CCA REQUESTS FILED THIS SESSION

  REQUEST 4 (URGENT) — Overnight/Time-of-Day academic research
    Filed S113/S114. Needs academic papers on:
    1. Intraday volatility patterns in crypto markets (00-08 UTC vs 09-21 UTC)
    2. Prediction market liquidity by time-of-day (15-min binary market thinning overnight)
    3. Evidence that drift signals perform worse in Asian session
    4. Optimal partial Kelly for overnight vs daytime given different EV estimates

  REQUEST 5 (NORMAL) — Kalshi Leaderboard Market Analysis
    What market categories do Kalshi weekly/monthly/daily leaderboard leaders trade?
    Research: economics (CPI/GDP/FOMC), tech/science, politics, crypto, sports
    Specific tickers worth probing for volume + near-expiry + 90c+ structure

## DEAD ENDS CONFIRMED THIS SESSION

  Political markets (current cycle) — DEAD END until Q4 2026 midterms
    0 open KXSENATE/KXHOUSE/KXPRES markets. 20,000+ March Madness KXMVE markets dominate.
    Math is sound (b=1.83 = 14x crypto edge at 90c) but no markets to trade.
    Revisit: before 2026 midterms or major political event.

## PRIORITY STACK FOR S115

  1. HIGHEST: Check CCA_TO_POLYBOT.md for REQUEST 4 + REQUEST 5 responses
     If REQUEST 4 returns academic backing → implement overnight partial Kelly or window filter
  2. btc_drift CUSUM: was 4.020 entering session. Check current level.
     If S >= 5.0: formal investigation needed (SPRT boundary check + direction_filter re-eval)
  3. WARMING BUCKETS: KXETH YES@93c at n=9 approaching n=10 guard threshold.
     Check if n>=10 and WR < 92.5% at session start.
  4. META-LABELING (Dim 9): n~10+ signal_features. Target n=1000. Passive.
  5. GUARD RETIREMENT (Dim 5): needs 50+ paper bets/bucket. Passive.

## KEY FINDING 5 — XRP SNIPER IS THE PRIMARY P&L DRAG (CRITICAL)

From 776 live sniper bets, comprehensive multi-parameter analysis:

BY COIN:
  BTC: n=198  WR=97.5%  PnL=+96.72 USD  EV=+0.488/bet
  ETH: n=193  WR=97.4%  PnL=+71.10 USD  EV=+0.368/bet
  SOL: n=200  WR=95.0%  PnL=-4.66 USD   EV=-0.023/bet
  XRP: n=185  WR=93.0%  PnL=-107.27 USD EV=-0.580/bet

BTC+ETH+SOL sniper all-time: +163.16 USD. XRP alone: -107.27 USD.

XRP TIME-OF-DAY SPLIT:
  GOOD (09-20 UTC): n=79   WR=97.5%  EV=+0.321/bet  PnL=+25.35 USD
  BAD (21-08 UTC):  n=106  WR=89.6%  EV=-1.251/bet  PnL=-132.62 USD

Wilson CI for XRP bad hours (n=106, WR=89.6%): [82.3%, 94.1%]
Break-even for avg XRP sniper price (~93c): 93.1%
Upper CI bound (94.1%) just barely above break-even — approaching statistical significance.

XRP BY SIDE:
  XRP NO:  n=91  WR=91.2%  EV=-0.881/bet  PnL=-80.20 USD (guards on @93c+@95c — still bad)
  XRP YES: n=94  WR=94.7%  EV=-0.288/bet  PnL=-27.07 USD

08:xx UTC WILSON CI BY COIN:
  XRP @ 08:xx: n=7   WR=57.1%  CI=[25.0%,84.2%] — formally BELOW break-even
  BTC @ 08:xx: n=12  WR=83.3%  CI=[55.2%,95.3%] — includes break-even (crash-artifact dominated)
  ETH @ 08:xx: n=11  WR=81.8%  CI=[52.3%,94.9%] — includes break-even (crash-artifact dominated)
  SOL @ 08:xx: n=9   WR=100.0% — fine

SOL YES EV=-0.172/bet (-19.98 USD). SOL NO EV=+0.182/bet. Direction asymmetry may be structural.

STREAK ANALYSIS (all 776 sniper bets):
  Max loss streak: 3 (excellent — we never had 4+ consecutive losses)
  Max win streak: 96 consecutive wins
  Total losses: 33 (vs expected 39 at 95% WR — actually outperforming expectation)

CONCLUSION:
  The overnight problem is NOT that sniper stops working at night.
  The overnight problem is specifically XRP sniper in off-peak hours (21-08 UTC).
  BTC+ETH+SOL are fine overnight except at 08:xx UTC (which may be one-event-dominated).
  The OVERNIGHT GUARD, if justified, should be XRP-specific and time-windowed.

4-CONDITION CHECK FOR XRP BAD HOURS GUARD:
  1. Structural basis: PLAUSIBLE (XRP high Asia-Pacific trading volume, EU open transition)
  2. Math validation: YES (n=106 at EV=-1.251/bet meets the math threshold)
  3. DB backtest: CONFIRMED above
  4. p-value: APPROACHING (Wilson CI upper barely > break-even, SPRT not computed yet)

STATUS: NOT YET AT 4-CONDITION STANDARD. CCA REQUEST 8 filed for formal analysis.
Do NOT add guard until CCA returns SPRT confirmation + academic structural basis.

## KEY FINDING 6 — MARKET CONDITIONS NON-STATIONARITY (NEW RESEARCH DIRECTION)

The bot currently has zero market conditions awareness. It fires at 90-95c regardless of:
- Current BTC realized volatility
- Whether the crypto market is trending vs ranging
- Correlation between assets (which caused March 17 crash)
- News/event risk (FOMC, crypto regulation)
- Time since last correlated crash event

CCA REQUEST 9 filed for: regime detection methods, FLB stability under volatility,
volatility-conditioned Kelly sizing, correlation guard design.
This is the foundation for Dim 10 (market conditions awareness) — future build, not current.

## SNIPER STATE AT WRAP

  All-time bot P&L: -4.59 USD (was -13.08 at session start — recovered +8.49 during daytime)
  Sniper-only all-time: strongly positive (+46 USD before drift drag)
  Today: 59 settled, 46W (78%), -27.5 USD (dominated by two overnight losses)
  Active auto-guards: 5 (KXXRP NO@95c, KXSOL NO@93c, KXBTC YES@94c, KXXRP NO@93c, KXBTC NO@94c)
  0 guard failures this session
