# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-28 (Session 20 — btc_drift LIVE, eth_lag LIVE, split caps)
═══════════════════════════════════════════════════

## Current State

btc_lag_v1 + eth_lag_v1 + btc_drift_v1 → LIVE MODE ($75 starting bankroll, $5 max/bet)
6 other strategies → paper mode. All code pushed to GitHub main (0f6bae7).
440/440 tests passing.

## Session 20 changes (2026-02-28)

1. **btc_lag + eth_lag min_edge_pct**: 0.06 → 0.04 (~8 live signals/day, 77.1% acc)
2. **eth_lag**: promoted to LIVE (same executor path as btc_lag)
3. **btc_drift_v1**: promoted to LIVE (69.1% accuracy, Brier 0.22, fires ~96% of windows)
4. **Split live/paper daily caps**: max_daily_bets_live=10, max_daily_bets_paper=35
   - Live cap: 10/day per strategy (tax management)
   - Paper cap: 35/day per strategy (graduate in 1 day — needs 30 trades)
5. **sports_game_v1 skeleton**: odds_api.py + sports_game.py + 28 tests (DISABLED until ODDS_API_KEY)
   - User has 20,000 req/month Odds API subscription, renews March 1
   - Will NOT wire into main.py until live results are confirmed first
6. **Odds API budget**: 1,000-2,000 req/mo (5-10% of 20k subscription)

Loop stagger (seconds):
   0s → [trading]        btc_lag_v1                 — LIVE, crypto momentum, min_edge=0.04
   7s → [eth_trading]    eth_lag_v1                 — LIVE, ETH momentum, min_edge=0.04
  15s → [drift]          btc_drift_v1               — LIVE, BTC drift from open, min_edge=0.05
  22s → [eth_drift]      eth_drift_v1               — paper, ETH drift
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper, VPIN-lite depth ratio
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper, ETH orderbook
  43s → [weather]        weather_forecast_v1        — paper, HIGHNY vs ensemble forecast, 5-min poll
  51s → [fomc]           fomc_rate_v1               — paper, KXFEDDECISION vs yield curve, 30-min poll
  58s → [unemployment]   unemployment_rate_v1       — paper, KXUNRATE vs FRED UNRATE, 30-min poll

verify.py: **18/26** (8 graduation WARNs — advisory only, never blocks startup)
Tests: **440/440 ✅** (was 412, +28 new in Session 20 for sports_game skeleton)

## Next Action (FIRST THING)

Bot is running. PID in bot.pid.

If stopped, restart with:
    rm -f bot.pid && source venv/bin/activate && echo "CONFIRM" | nohup python main.py --live >> /tmp/polybot_session20.log 2>&1 &

## What was done this session (Session 19 → context, fully done)

1. **Graduation criteria**: min_days removed. 30 real trades is the only volume gate.
2. **--status CLI command**: bypass PID lock, works while bot is live.
3. **unemployment_rate_v1**: 9th loop, 58s stagger, active Feb 28 – Mar 7.
4. **btc_lag backtest sweep**: 0.08=84.1%/1.5/day | 0.06=77.9%/3/day | 0.04=77.1%/8/day.

## Component Status

| Component                    | Status      | Notes                                          |
|------------------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)               | ✅ Working  | api.elections.kalshi.com                       |
| Kalshi REST client           | ✅ Working  | result field .lower() normalized               |
| Binance.US BTC feed          | ✅ Working  | @bookTicker, ~100 ticks/min                    |
| Binance.US ETH feed          | ✅ Working  | @bookTicker, ethusdt stream                    |
| BTCLagStrategy               | ✅ LIVE     | btc_lag_v1, 0s stagger, 77.1% at 4% threshold  |
| BTCDriftStrategy             | ✅ LIVE     | btc_drift_v1, 15s stagger, 69.1% acc, Brier 0.22 |
| ETH lag strategy             | ✅ LIVE     | eth_lag_v1, 7s stagger                        |
| ETH drift strategy           | ✅ Running  | eth_drift_v1, paper, 22s stagger              |
| Orderbook imbalance (BTC)    | ✅ Running  | paper, 29s stagger                            |
| Orderbook imbalance (ETH)    | ✅ Running  | paper, 36s stagger                            |
| WeatherForecastStrategy      | ✅ Running  | ENSEMBLE (Open-Meteo + NWS), paper            |
| FOMCRateStrategy             | ✅ Running  | paper, 30-min poll, active March 5–19         |
| UnemploymentRateStrategy     | ✅ Running  | paper, 30-min poll, active Feb 28 – Mar 7     |
| sports_game_v1 skeleton      | ✅ Built    | DISABLED, ODDS_API_KEY needed, wired in March |
| --status/--report/--grad     | ✅ Working  | all bypass PID lock, safe while bot is live   |
| PaperExecutor                | ✅ Working  | 1-tick adverse slippage                       |
| LiveExecutor                 | ✅ Working  | btc_lag + eth_lag + btc_drift all LIVE        |
| Position deduplication       | ✅ Working  | db.has_open_position() on all 9 loops         |
| Daily bet caps               | ✅ Working  | live=10/day, paper=35/day per strategy        |
| Kill switch                  | ✅ Working  | Shared by all 9 loops                         |
| Graduation reporter          | ✅ Working  | python main.py --graduation-status            |

## Key Commands

    python main.py --live                      → Start bot (9 loops + settlement)
    python main.py --status                    → Live status (works while bot running)
    python main.py --graduation-status         → Graduation progress table
    python main.py --report                    → Today's P&L (per-strategy breakdown, works while live)
    python setup/verify.py                     → Pre-flight (18/26, 8 advisory WARNs)
    streamlit run src/dashboard.py             → Dashboard at localhost:8501
    source venv/bin/activate && python -m pytest tests/ -v  → 440 tests
    echo "RESET" | python main.py --reset-killswitch

## Signal calibration

  btc_lag / eth_lag (LIVE):
    min_edge_pct: 0.04 — needs ~0.40% BTC move in 60s (binding constraint)
    In calm markets: 0 signals/day — expected, not a bug
    Backtest: 77.1% accuracy, ~8 signals/day (30-day average includes volatile days)

  btc_drift (LIVE):
    min_drift_pct: 0.05, min_edge_pct: 0.05, sensitivity: 800
    Fires on ~96% of 15-min windows — generates live bets in ALL market conditions
    30-day backtest: 69.1% accuracy, Brier=0.2178 (STRONG)
    Risk bounded: daily loss limit 15% of bankroll = ~$11 before auto-halt

  eth_drift (paper):
    Same model as btc_drift but on ETH. Paper until eth calibration runs.

  unemployment_rate_v1:
    UNRATE trend: 4.5 → 4.4 → 4.3 (improving/decreasing)
    forecast: ~4.2% for March BLS release
    Active: Feb 28 → Mar 7, then Mar 13 → Apr 3, etc.
    KXUNRATE markets open ~2 days before each BLS release

  fomc_rate:
    Active March 5–19 (next meeting March 19)

## Graduation thresholds — min_days REMOVED

  All strategies: 30 trades, Brier < 0.30, < 4 consecutive losses
  fomc_rate: 5 trades (fires ~8x/year)
  No day minimums — 30 real trades is the only volume gate

## Known Kalshi market series (confirmed open)

  KXBTC15M    — BTC 15-min price (0.17pp spread, HFT-heavy)
  KXETH15M    — ETH 15-min price (0.17pp spread, HFT-heavy)
  KXFEDDECISION — Fed rate decision (active near FOMC meetings)
  HIGHNY      — NYC daily high temp (weekdays only)
  KXUNRATE    — Unemployment rate (opens ~2 days before BLS release)
  KXNBAGAME   — NBA game-by-game winner (38 markets, 1.35M volume, 1-2¢ spread) ← sports skeleton ready
  KXNHLGAME   — NHL game-by-game winner (48 markets) ← sports skeleton ready

## Research findings — next strategies to consider

1. ✅ Weather ensemble (HIGHNY) — paper running
2. ✅ FOMC/Fed rate markets — paper running
3. ✅ Orderbook imbalance — paper running
4. ✅ Unemployment rate (KXUNRATE) — paper running, active now
5. ⬜ Sports markets (KXNBAGAME/KXNHLGAME) — skeleton built, wire after live results in
6. ⬜ Market making (Avellaneda-Stoikov) — nikhilnd/kalshi-market-making: 20.3% in 1 day
7. ⬜ Polymarket whale_copy — waitlist, activate when off waitlist
