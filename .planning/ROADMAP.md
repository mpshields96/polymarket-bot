# Roadmap — polymarket-bot
# Last updated: 2026-03-01 (Session 28)
#
# CONTEXT: Sessions 1-28 summary
# - Built 10-strategy Kalshi bot, graduated btc_lag to live
# - Live record: -$18.85 (21 bets). Root cause: market orders against Jane St / Susquehanna HFTs
#   on a maturing platform. Signal IS valid (66.7% accuracy at real Kalshi prices, 13.5% edge)
#   but opportunity frequency shrinking toward 0 as KXBTC15M matures (0 signals last 5 days).
# - All strategies demoted to paper. Bankroll: $79.76. No live bets firing.
# - Polymarket.us retail API credentials wired. Phase 5.1 complete (auth + REST client, 645 tests).
#   CRITICAL FINDING (2026-03-01): Polymarket.us currently has ONLY sports markets (5032 total,
#   all NBA/NFL/NHL/NCAA). NO crypto/BTC prediction markets exist on this platform as of this date.
#   The "Bitcoin Up or Down 15-min" market assumption in the original Phase 5 plan was WRONG.
#   Polymarket.us is a new platform (CFTC approved Dec 2025) still in sports-only launch phase.
# - Phase 5 plan revised: build sports strategy OR wait for crypto markets to launch.

═══════════════════════════════════════════════════════════════

## ✅ COMPLETE — Phases 1-4 (Kalshi Foundation)

All core infrastructure built and validated:
- 10 strategy loops (btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance,
  eth_imbalance, weather_forecast, fomc_rate, unemployment_rate, sol_lag)
- Kill switch (daily + lifetime + consecutive loss limits, all persist across restarts)
- Kelly sizing, paper/live separation, graduation criteria, PID lock, asyncio trade lock
- 645/645 tests passing
- Live trading enabled and tested (21 live bets, lessons learned)
- Real backtest framework: scripts/kalshi_real_backtest.py (uses Kalshi free candlestick API)

Key lesson: btc_lag signal is valid. Kalshi execution (market orders, maturing market) is the problem.

### Phase 04.2: Paper Data Collection ✅ COMPLETE
- PaperExecutor with configurable adverse slippage model (1-tick default)
- `--graduation-status` CLI command (8-strategy Brier progress table)
- Settlement result normalization (.lower()) in kalshi.py `_parse_market()`
- `docs/SETTLEMENT_MAPPING.md` — WIN/LOSS field logic documented
- Plan: `.planning/phases/04.2-paper-data-collection/04.2-01-PLAN.md`

═══════════════════════════════════════════════════════════════

## 🔄 CURRENT — Phase 5: Polymarket Integration

> Goal: Build Polymarket.us trading capability alongside existing Kalshi bot.
> Architecture: One bot process, two platform loops running concurrently in asyncio.

### Phase 5.1 — Polymarket Auth + REST Client ✅ COMPLETE (Session 28)
**Status:** Done
**Delivered:**
- `src/auth/polymarket_auth.py` — Ed25519 signing (19 tests)
- `src/platforms/polymarket.py` — REST client with markets/orderbook/positions/activities (23 tests)
- `setup/verify.py` — Polymarket auth [12] + API connectivity [13] checks
- Credentials in `.env` (POLYMARKET_KEY_ID + POLYMARKET_SECRET_KEY)
- 645/645 tests passing

**Critical API findings (discovered via live exploration):**
- Base URL: https://api.polymarket.us/v1
- Auth works: Ed25519(secret_key).sign(timestamp_ms + METHOD + path)
- ⚠️  PLATFORM IS SPORTS-ONLY as of 2026-03-01 (5032 markets, all NBA/NFL/NHL/NCAA)
- NO BTC/ETH/crypto prediction markets exist yet — original Phase 5 assumption was wrong
- Rate limit: 60 req/min confirmed
- Prices: 0.0-1.0 scale (not cents like Kalshi)
- Orderbook: GET /v1/markets/{identifier}/book (bids + asks)

---

### Phase 5.2 — Sports Strategy on Polymarket
**Status:** Not started (blocked on architecture decision — see below)
**Goal:** Build a sports edge strategy using sports data feed vs Polymarket.us game lines.

⚠️  ARCHITECTURE DECISION NEEDED before building:
Option A — Wait for crypto markets on Polymarket.us (timeline unknown)
Option B — Build sports strategy now using Polymarket.us game markets
Option C — One bot, two platforms (Kalshi crypto + Polymarket sports running concurrently)

Option C is the recommended architecture (see DUAL-PLATFORM ARCHITECTURE section below).

**If proceeding with Option C (sports on Polymarket):**
- [ ] `src/strategies/sports_moneyline.py` — compare Polymarket odds vs sports data feed sharp lines
      Signal: Polymarket price deviates >5pp from sharp consensus → fade/follow
      Data: sports data feed (h2h, pinnacle + bet365 as reference) — 500 credit cap
- [ ] `src/execution/polymarket_paper.py` — paper executor for Polymarket orders
- [ ] `polymarket_sports_loop()` in main.py — polls open Polymarket game markets
- [ ] Paper first: 30+ settled trades + Brier < 0.25 before any live orders
- sports data feed quota guard: MUST be implemented before any API call (500 credit max for this bot)

**If waiting for crypto markets:**
- Monitor Polymarket.us product updates
- Infrastructure is ready — just need to add the market type when it launches

---

### Phase 5.3 — Paper Graduation on Polymarket
**Status:** Not started (blocked by 5.2)
**Goal:** 30+ settled Polymarket paper trades, Brier < 0.25.

---

### Phase 5.4 — Live Promotion on Polymarket
**Status:** Not started (blocked by 5.3)
- Full Step 5 pre-live audit (CLAUDE.md Development Workflow Protocol)
- Bankroll gate: do NOT go live until bankroll > $90 (currently $79.76)

═══════════════════════════════════════════════════════════════

## DUAL-PLATFORM ARCHITECTURE (recommended approach)

Running Kalshi + Polymarket simultaneously in one bot process is the right design.
asyncio handles concurrency natively — adding a Polymarket loop costs ~0 overhead.

**One process, multiple platform loops:**
```
main.py asyncio event loop
├── Kalshi loops (paper-only, collecting calibration data)
│   ├── btc_lag_loop()
│   ├── eth_lag_loop()
│   ├── btc_drift_loop()
│   └── ... (7 more)
└── Polymarket loops (new, paper-first)
    └── polymarket_sports_loop()  ← Phase 5.2
```

**Why one process:**
- Shared kill switch (one daily P&L limit across all bets)
- Shared bankroll tracking (one SQLite DB)
- Shared risk limits (Kelly sizing uses total bankroll, not per-platform)
- Simpler ops (one PID, one log file, one restart command)

**Risks of one process:**
- A crash in a new Polymarket loop can kill Kalshi loops
- Mitigation: wrap each loop in try/except at the top level (already done for Kalshi loops)
- Rate limit budgets must be tracked separately per platform

**Alternative (two separate bots):** Only justified if platforms need different bankrolls,
different kill switches, or different risk profiles. Not needed now.

═══════════════════════════════════════════════════════════════

## 📋 QUEUED — Phase 6: Signal Enhancement

> Unlock: Phase 5.3 complete (30+ Polymarket paper trades, Brier < 0.25)

### Phase 6.1 — Funding Rate Filter
Use Binance perp funding rate as a direction filter for btc_lag.
- Extremely positive funding (>0.1%/8h): longs overcrowded → skip YES bets
- Extremely negative funding (<-0.1%/8h): shorts overcrowded → skip NO bets
- Data: Binance.US REST funding rate endpoint (no auth required)
- Expected: reduces losing bets in mean-reversion windows

### Phase 6.2 — Volatility-Adaptive Thresholds
Scale min_btc_move_pct with recent realized vol. Already in todos.md. Just needs gate to clear.

### Phase 6.3 — Kalshi ↔ Polymarket Spread Arb (Opportunistic)
When same BTC window prices diverge >3pp across platforms: bet both sides for locked profit.
Requires both platforms live simultaneously. Note: Polymarket taker fee eats margin on one leg.

═══════════════════════════════════════════════════════════════

## 📋 QUEUED — Phase 7: Market Expansion

> Unlock: Phase 6 complete + bankroll > $150 + 60+ live trades across both platforms

### Phase 7.1 — Sports Game Strategy (NBA/NHL)
Kalshi KXNBAGAME/KXNHLGAME vs sports data feed moneyline. See todos.md for full spec.

### Phase 7.2 — Tail Mispricing Strategy
Short <15¢ contracts via limit orders. Well-documented academic edge: markets overprice tails.
5¢ contract wins ~2% not 5% — short via limit = positive EV, no directional signal needed.

### Phase 7.3 — 5-Minute Markets
Polymarket 5-min BTC/ETH/SOL. Same signal, more opportunities, higher noise.
Test only after 15-min validated on Polymarket.

═══════════════════════════════════════════════════════════════

## EXPANSION GATE (updated 2026-03-01)

Previous gate (obsolete): btc_drift 30+ live trades + Brier < 0.30. btc_drift is demoted.

**Current gate — do NOT build Phase 6+ until ALL true:**
- [ ] Polymarket btc_lag paper: 30+ settled trades + Brier < 0.25
- [ ] Bankroll > $90 (currently $79.76)
- [ ] No kill switch events for 7+ consecutive days
- [ ] No active blockers or silent failures in logs

═══════════════════════════════════════════════════════════════

## KALSHI STATUS (as of 2026-03-01)

All 10 strategies paper-only. Bot running (PID 9282, log /tmp/polybot_session27.log).
Collecting paper calibration data passively — this is not wasted, it builds Brier history.

Re-promote btc_lag to Kalshi live only when:
- 30-day rolling signal count > 5/month (currently ~0 in last 5 days — market maturing)
- AND bankroll > $90
- AND Polymarket version is live (proof signal works before re-enabling Kalshi)
