# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume work immediately.
# Last updated: 2026-03-20 ~01:15 UTC (Session 118 monitoring wrap — hour block deployed)
# ═══════════════════════════════════════════════════════════════

## BOT STATE
  Bot RUNNING PID 54374 → /tmp/polybot_session118.log
  All-time live P&L: +6.40 USD (session net: -4.95 USD from +11.35 at S115 wrap)
  Today P&L: +1.77 USD (54 settled, 89% WR)
  Bankroll: ~179.76 USD (Stage 2 sizing: max 10 USD/bet for drift)
  Tests: 1698 passing. Last commit: 8008c17 (feat: block sniper bets UTC hours 08 and 13)
  eth_drift: DISABLED (min_drift_pct=9.99) — confirmed 0 bets
  xrp_drift: UNBLOCKED (direction_filter="yes")

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

## PENDING FOR S119+

  #1 VERIFY HOUR BLOCK FIRING: grep "Hour block" /tmp/polybot_session118.log
     Watch for "Hour block: 08:xx UTC" or "Hour block: 13:xx UTC" in live log.
  #2 btc_drift CUSUM: 4.260/5.0. If S>=5.0 at session start: disable (min_drift_pct=9.99).
     SPRT lambda=-1.134. If crosses -2.251: also disable.
  #3 KXETH YES@93c warming bucket: n=9, 1 bet from auto-guard threshold.
     Run scripts/auto_guard_discovery.py at session start.
  #4 CCA REQUEST 10 RESPONSE (FLB weakening verification + overnight drift applicability):
     Check CCA_TO_POLYBOT.md. UNVERIFIED until CCA confirms.
  #5 CCA REQUEST 11 (00:xx UTC Asian session mechanism) — PENDING.
  #6 CCA REQUEST 12 (Earnings Mentions volume + edge) — NEW, PENDING.
  #7 Dim 9 accumulation: n=13 signal_features. Target n=1000. Passive.
  #8 SDATA: 450/500 (90%) — avoid heavy research scans. Resets 2026-04-01.
  #9 "Daily loss soft stop active" in --health = COSMETIC ONLY (enforcement commented out).

## GUARD STACK
  Floor 90c + Ceiling 95c + 5 auto-guards:
    KXXRP NO@95c — ACTIVE
    KXSOL NO@93c — ACTIVE
    KXBTC YES@94c — ACTIVE
    KXXRP NO@93c — ACTIVE
    KXBTC NO@94c — ACTIVE
  AUTO-GUARD: MIN_BETS=10, p<0.20 significance gate required
  WARMING WATCH: KXETH YES@93c (n=9) — NEXT CANDIDATE (1 bet from threshold)

## HOUR BLOCK (NEW — S118 monitoring wrap)
  _BLOCKED_HOURS_UTC = frozenset({8, 13}) in expiry_sniper_loop()
  08:xx: WR=82.1% n=39 z=-4.30 structural (European open daily)
  13:xx: WR=90.5% n=21 structural (US market open at 13:30 UTC daily)
  Logs: "[expiry_sniper] Hour block: 08:xx UTC — skipping poll (WR<91% historically)"
  Sleeps 60s per blocked iteration. Does NOT affect drift strategies.

## STRATEGY STANDINGS (S118 monitoring wrap)
  expiry_sniper_v1:  PRIMARY ENGINE — 797 live bets, 95.7% WR, +63.21 USD sniper-only
                     All-time BOT P&L: +6.40 USD (drift drag from early strategies)
                     Hour block active: 08:xx + 13:xx UTC
                     SPRT lambda=+16.670 EDGE CONFIRMED | CUSUM stable
  sol_drift_v1:      LIVE Stage 1 — 43 bets, 70% WR, +4.89 USD EDGE CONFIRMED
  btc_drift_v1:      MONITORING — 75 bets, 49% WR, CUSUM S=4.260/5.0 APPROACHING
                     direction_filter="no", SPRT lambda=-1.134 [collecting]
  eth_drift_v1:      DISABLED — min_drift_pct=9.99 — 0 live bets this session
  xrp_drift_v1:      LIVE — 50 bets, direction_filter="yes"
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

## RESTART COMMAND (Session 119)
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session119.log 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" — exactly 1. Then cat bot.pid.

## GOAL TRACKER
  All-time P&L: +6.40 USD live | Monthly target: 250 USD self-sustaining
  Sniper-only: +63.21 USD (bot all-time dragged by early pre-guard drift losses)
  At current sniper rate: sniper adds ~7-10 USD/day clean
  Distance to +125 USD milestone: 118.60 USD
  Highest-leverage action: Keep bot alive + let hour block compound over 08:xx/13:xx windows
