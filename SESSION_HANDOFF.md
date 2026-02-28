# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 20 — btc_lag 0.06→0.04, eth_lag now LIVE, Odds API noted)
═══════════════════════════════════════════════════

## Current State

btc_lag_v1 + eth_lag_v1 → LIVE MODE ($75 starting bankroll, $5 max/bet)
7 other strategies → paper mode. All code pushed to GitHub main.
412/412 tests passing. Paper P&L today: +$37.07 (11/12 wins).

## Session 20 changes (2026-02-28)
- btc_lag min_edge_pct: 0.06 → 0.04 (~8 live signals/day, 77.1% acc)
- eth_lag: promoted to LIVE (same executor path as btc_lag, same threshold)
- Odds API: user has 20,000 req/month subscription; 5-10% budget (~1,000-2,000 req/mo) allocated for sports strategy
- Sports strategy roadmap logged: .planning/todos.md (KXNBAGAME/KXNHLGAME vs The-Odds-API)
- Bot restarted with PID 88507, CONFIRM accepted, live_confirmed=True

Loop stagger (seconds):
   0s → [trading]        btc_lag_v1                 — LIVE, crypto momentum, min_edge=0.04
   7s → [eth_trading]    eth_lag_v1                 — LIVE, ETH momentum, min_edge=0.04
  15s → [drift]          btc_drift_v1               — BTC drift from open, paper
  22s → [eth_drift]      eth_drift_v1               — ETH drift, paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — VPIN-lite depth ratio, paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — ETH orderbook, paper
  43s → [weather]        weather_forecast_v1        — HIGHNY vs ensemble forecast, paper, 5-min poll
  51s → [fomc]           fomc_rate_v1               — KXFEDDECISION vs yield curve, paper, 30-min poll
  58s → [unemployment]   unemployment_rate_v1       — KXUNRATE vs FRED UNRATE, paper, 30-min poll ← NEW

verify.py: **18/26** (8 graduation WARNs — advisory only, never blocks startup)
Tests: **412/412 ✅** (was 346, +66 new in Session 19)

## What was done this session (Session 19)

1. **Graduation criteria**: removed min_days requirement from all strategies — 30 real trades
   is now the only volume gate. Test updated. Commit: e999d6c

2. **--status CLI command**: `python main.py --status` — works while bot is live (bypasses
   PID lock). Shows: BTC/ETH mid-price (Binance.US REST), bankroll, pending bets, today P&L
   (paper + live), all-time P&L, last 10 trades. 20 new tests. Commit: ab72b61

3. **unemployment_rate_v1** (9th loop, 58s stagger):
   - FRED UNRATE series: 4.3% (trending down from 4.5 → 4.4 → 4.3)
   - Active in 7-day window before each BLS Employment Situation release
   - Next BLS release: March 7, 2026 → strategy active NOW (Feb 28 → Mar 7)
   - KXUNRATE markets not open yet — will open ~March 5
   - Linear trend extrapolation + uncertainty band (±0.2pp) + normal CDF model
   - math.erfc used (no scipy dependency)
   - FREDSnapshot extended: unrate_latest, unrate_prior, unrate_prior2 fields (backward-compat)
   - Shared fred_feed between fomc_loop and unemployment_loop
   - 46 new tests. Commits: d38f20d, 15307cf

4. **15-min Reminders notifier**: fixed duplicate process issue (was 2x → 1x), flat 15-min
   interval (was 15→30 escalating). PID at /tmp/polybot_notify.pid

5. **Sports/entertainment markets research**: KXNBA + KXMLB have 30 open markets each
   but are season-winner markets (months to settlement, illiquid). Not suitable for our
   strategy. Spread advantage was likely Polymarket-specific, not Kalshi.

6. **btc_lag backtest sweep**: 0.08=84.1%/1.5/day | 0.06=77.9%/3/day | 0.04=77.1%/8/day.
   Lowered btc_lag min_edge_pct 0.08→0.06 on 2026-02-28 (commit 38d1a7b).
   Also lowered eth_lag 0.08→0.06 (same rationale, paper-only, commit 7c2ef43).

7. **--report + lock bypass**: per-strategy breakdown added. --report and --graduation-status
   now bypass PID lock (same as --status). Midnight P&L notifier: scripts/notify_midnight.sh.
   (commit 697db57)

## Next Action (FIRST THING)

Bot is running with 9 loops active.

If stopped, restart with:
    source venv/bin/activate && python main.py --live
    # Type CONFIRM at the prompt

    # Also restart notifiers if needed:
    kill $(cat /tmp/polybot_notify.pid) 2>/dev/null; /tmp/polybot_notify_v3.sh & echo $! > /tmp/polybot_notify.pid
    # For midnight P&L notifier (run once, persists):
    scripts/notify_midnight.sh & echo $! > /tmp/polybot_midnight.pid

🔴 LIVE: btc_lag_v1. BTC calm today — few live signals.
📋 PAPER: 8 other strategies. Today: 9/10 wins, +$29.63 paper P&L.

### NEXT SESSION GOALS

1. **Reddit link**: user has a Chrome plugin to read Reddit URLs. URL to read:
   https://www.reddit.com/r/ClaudeCode/comments/1qxvobt/ive_used_ai_to_write_100_of_my_code_for_1_year_as/

2. **Paper data accumulation**: strategies need 30 real trades to graduate. Check daily
   with `python main.py --graduation-status`. btc_drift fires most — watch it first.

4. **Entertainment strategy research**: need to find Kalshi short-term sports/entertainment
   markets (game-by-game, not season-winner). KXNBA/KXMLB are season markets. May need
   to browse kalshi.com to find relevant series tickers.

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | api.elections.kalshi.com                       |
| Kalshi REST client           | ✅ Working  | result field .lower() normalized               |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| BTCLagStrategy               | ✅ LIVE     | btc_lag_v1, 0s stagger, 77.9% at 6% threshold  |
| BTCDriftStrategy             | ✅ Running  | btc_drift_v1, paper, sensitivity=800           |
| ETH lag strategy             | ✅ Running  | eth_lag_v1, paper, 7s stagger                  |
| ETH drift strategy           | ✅ Running  | eth_drift_v1, paper                            |
| Orderbook imbalance (BTC)    | ✅ Running  | paper, 29s stagger                             |
| Orderbook imbalance (ETH)    | ✅ Running  | paper, 36s stagger                             |
| WeatherForecastStrategy      | ✅ Running  | ENSEMBLE (Open-Meteo + NWS), paper             |
| FOMCRateStrategy             | ✅ Running  | paper, 30-min poll, active March 5–19          |
| UnemploymentRateStrategy     | ✅ NEW      | paper, 30-min poll, active Feb 28 – Mar 7      |
| --status/--report/--grad     | ✅ Working  | all bypass PID lock, safe while bot is live    |
| PaperExecutor                | ✅ Working  | 1-tick adverse slippage                        |
| Position deduplication       | ✅ Working  | db.has_open_position() on all 9 loops          |
| Daily bet cap                | ✅ Working  | 5 bets/strategy/day                            |
| Kill switch                  | ✅ Working  | Shared by all 9 loops                          |
| Graduation reporter          | ✅ Working  | python main.py --graduation-status             |
| Reminders notifier (15-min)  | ✅ Working  | /tmp/polybot_notify_v3.sh, flat 15-min         |
| Midnight P&L notifier        | ✅ NEW      | scripts/notify_midnight.sh, UTC midnight       |

## Key Commands

    python main.py --live                      → Start bot (9 loops + settlement)
    python main.py --status                    → Live status (works while bot running)
    python main.py --graduation-status         → Graduation progress table
    python main.py --report                    → Today's P&L (per-strategy breakdown, works while live)
    scripts/notify_midnight.sh & echo $! > /tmp/polybot_midnight.pid  → Start midnight notifier
    python setup/verify.py                     → Pre-flight (18/26, 8 advisory WARNs)
    streamlit run src/dashboard.py             → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 412 tests
    echo "RESET" | python main.py --reset-killswitch
    kill $(cat /tmp/polybot_notify.pid)        → Stop notifier
    /tmp/polybot_notify_v3.sh & echo $! > /tmp/polybot_notify.pid  → Start notifier

## Signal calibration

  btc_lag / eth_lag:
    min_edge_pct: 0.08 — needs ~0.65% BTC move in 60s (binding constraint)
    In calm markets: 0-1 signals/day — expected, not a bug
    30-day backtest: 84.1% accuracy, 44 signals/30 days

  btc_drift / eth_drift:
    min_drift_pct: 0.05, min_edge_pct: 0.05, sensitivity: 800
    Fires most frequently — hits 5/day cap
    30-day backtest: 69.1% accuracy, Brier=0.2178 (STRONG)

  unemployment_rate_v1:
    UNRATE trend: 4.5 → 4.4 → 4.3 (improving/decreasing)
    forecast: ~4.2% for March BLS release
    Active: Feb 28 → Mar 7, then Mar 13 → Apr 3, etc.
    KXUNRATE markets open ~2 days before each BLS release

  fomc_rate:
    Active March 5–19 (next meeting March 19)

## Graduation thresholds (setup/verify.py _GRAD) — min_days REMOVED

  All strategies: 30 trades, Brier < 0.30, < 4 consecutive losses
  fomc_rate: 5 trades (fires ~8x/year)
  No day minimums — 30 real trades is the only volume gate

## Known Kalshi market series (confirmed open)

  KXBTC15M    — BTC 15-min price (0.17pp spread, HFT-heavy)
  KXETH15M    — ETH 15-min price (0.17pp spread, HFT-heavy)
  KXFEDDECISION — Fed rate decision (active near FOMC meetings)
  HIGHNY      — NYC daily high temp (weekdays only)
  KXUNRATE    — Unemployment rate (opens ~2 days before BLS release)
  KXNBA-26-*  — NBA 2026 season winner (30 markets, season-long, illiquid)
  KXMLB-26-*  — MLB 2026 season winner (30 markets, season-long, illiquid)

## Research findings — next strategies to consider

1. ✅ Weather ensemble (HIGHNY) — paper running
2. ✅ FOMC/Fed rate markets — paper running
3. ✅ Orderbook imbalance — paper running
4. ✅ Unemployment rate (KXUNRATE) — paper running, active now
5. ⬜ Short-term sports markets — need to find game-by-game Kalshi tickers
6. ⬜ Market making (Avellaneda-Stoikov) — nikhilnd/kalshi-market-making: 20.3% in 1 day
7. ⬜ btc_lag sensitivity tuning — lower min_edge_pct 0.08→0.06 if backtest holds
