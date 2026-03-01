# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 29 — Phase 5.2 sports_futures_v1 built)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 9282, log at /tmp/polybot_session27.log (was running at session start, verify)
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**ALL 10 strategies PAPER-ONLY** — no live bets firing
Test count: **713/713 ✅**
Last commit: **5749ce9** — feat: Phase 5.2 sports_futures_v1 — Odds API championship futures + signal generator (713 tests)

Latest commits (most recent first):
- 5749ce9 — feat: Phase 5.2 sports_futures_v1 — Odds API championship futures + signal generator (713 tests)
- cb9ebc8 — feat: Phase 5.2 read infrastructure — whale watcher + predicting.top client (688 tests)
- 5f338bb — feat: Phase 5.1 Polymarket auth + REST client (645 tests)
- c1f43d3 — docs: session 28 final handoff

═══════════════════════════════════════════════════

## SESSION 29 WORK COMPLETED

### Phase 5.2 read infrastructure + sports_futures_v1 signal generator

**Files created (Session 29, two commits):**
- `src/data/predicting_top.py` — WhaleAccount + PredictingTopClient (predicting.top public API)
- `src/data/whale_watcher.py` — WhaleTrade + WhalePosition + WhaleDataClient (data-api.polymarket.com)
- `src/data/odds_api.py` — Extended with ChampionshipOdds dataclass + _fetch_outrights() + get_nba/nhl/ncaab_championship()
- `src/strategies/sports_futures_v1.py` — normalize_team_name() + SportsFuturesStrategy.scan_for_signals()
- Tests: test_predicting_top.py (15), test_whale_watcher.py (28), test_sports_futures.py (25) = 68 new tests

**Key architecture facts confirmed via live probing:**
- data-api.polymarket.com: fully public (no auth), returns trades + positions for any wallet
- predicting.top/api/leaderboard: public, returns 144 whale wallets in proxy address format
- Polymarket.us /v1/markets: 200 open markets — ALL season-winner futures (NBA Champion, NHL Hart, NCAA)
- Game-by-game markets NOT available on .us yet — copy trading deferred until .us expands
- Odds API: basketball_nba_championship_winner, icehockey_nhl_championship_winner, basketball_ncaab_championship_winner all working

**Sports futures strategy logic:**
- Compare PM yes_price to Odds API sharp consensus (vig-removed avg across Pinnacle/DraftKings/FanDuel)
- BUY YES if PM < odds_prob - 5% | BUY NO if PM > odds_prob + 5%
- normalize_team_name() bridges "Thunder" (PM) ↔ "Oklahoma City Thunder" (Odds API)
- PAPER ONLY until POST /v1/orders protobuf format confirmed

**Odds API key added to .env** (1,000 credit hard cap enforced — see CLAUDE.md)

═══════════════════════════════════════════════════

## CRITICAL POLYMARKET.US FINDING — THIS CHANGES PHASE 5

**Polymarket.us is SPORTS-ONLY as of 2026-03-01.**

Discovered via live API exploration (Session 28, systematic endpoint probe):
- Total markets: 5,032 — ALL are NBA/NFL/NHL/NCAA sports
- NO crypto prediction markets exist (no BTC/ETH 15-min up/down, nothing)
- The original Phase 5 assumption ("Bitcoin Up or Down — 15 Minutes" on Polymarket.us) was WRONG
- The platform launched December 2025 (CFTC approval) in sports-only mode
- Timeline for crypto markets: unknown — could be months or never on the US platform

**Confirmed working API endpoints:**
```
GET  /v1/markets                     — list markets (all sports)
GET  /v1/markets?closed=false        — open markets only
GET  /v1/markets/{identifier}/book   — orderbook (bids/asks, 0.0-1.0 price scale)
GET  /v1/portfolio/positions         — current holdings
GET  /v1/portfolio/activities        — deposit/trade history
POST /v1/orders                      — create order (format requires "market metadata" — TBD)
```

**Price convention:** 0.0-1.0 (NOT cents like Kalshi — multiply by 100 for comparison)
**Auth:** Ed25519(secret_key[:32]).sign(f"{timestamp_ms}{METHOD}{/path}") — body NOT signed

**Architecture decision pending for Phase 5.2:**
- Option A: Wait for crypto markets to launch on Polymarket.us (timeline unknown)
- Option B: Build sports moneyline strategy (Polymarket.us game markets vs The-Odds-API sharp lines)
- Option C (recommended): Both — build sports now, add crypto when markets launch
- ROADMAP.md updated with full dual-platform architecture spec

═══════════════════════════════════════════════════

## P&L STATUS (2026-03-01 ~21:05 UTC — Session 28 end)

```
python main.py --report output:
  Trades today:        56  (settled: 54)
  Wins:                17  (rate: 31%)
  P&L live:        $-31.71  (16 settled) ← these are from BEFORE Session 27 demotion decisions
  P&L paper:       $194.27  (38 settled)

  All-time live:   -$18.85  (21 settled, 8W/13L = 38%)
  All-time paper: +$217.90
  Bankroll:         $79.76
```

**NOTE on "today's" live P&L:** The $-31.71 live today represents trades placed EARLIER on March 1 UTC
when btc_drift/eth_lag were still live. Session 27 demoted all strategies to paper. No new live trades
will fire from this point forward unless something is re-promoted. The $-31.71 does NOT reflect
activity after the demotion. All-time live is the correct figure: -$18.85.

═══════════════════════════════════════════════════

## GRADUATION STATUS (2026-03-01 21:05 UTC)

```
Strategy           Trades  Days  Brier  Streak   P&L    Status
btc_lag_v1          43/30  30.8  0.191       0  +$12.72  READY FOR LIVE ← Brier 0.191 is STRONG
eth_lag_v1           0/30   0.0    n/a       0   $0.00   needs 30 more trades
btc_drift_v1         8/30   1.1    n/a       4   +$6.90  BLOCKED (4 consec losses)
eth_drift_v1        41/30   1.1    n/a       3  -$27.15  READY FOR LIVE (DO NOT PROMOTE — see warning)
orderbook_imb_v1     4/30   1.0    n/a       3  -$10.58  needs 26 more
eth_orderbook_v1    13/30   1.1    n/a       2 +$236.01  needs 17 more
weather_v1           0/30   0.0    n/a       0   $0.00   needs 30 more
fomc_rate_v1         0/5    0.0    n/a       0   $0.00   needs 5 more
```

**⚠️ CRITICAL: Do NOT re-promote btc_lag_v1 or eth_drift_v1 to live yet.**

btc_lag_v1 READY FOR LIVE per criteria BUT:
- Real backtest shows 0 signals in last 5 days on Kalshi (HFTs now price within same minute)
- Promoting live with 0 signal frequency = bot sits idle burning nothing, but signal edge questionable
- Gate: re-promote btc_lag Kalshi live ONLY when 30-day rolling signal count > 5/month AND bankroll > $90

eth_drift_v1 "READY FOR LIVE" BUT:
- 41 trades in only 1.1 days = paper loop firing too fast on synthetic paper markets
- Paper P&L is -$27.15 (negative edge)
- Only 1.1 days of data — not statistically meaningful
- DO NOT PROMOTE. Let it run 30+ days with stable Brier before considering.

═══════════════════════════════════════════════════

## KILL SWITCH STATUS

All strategies paper-only. Kill switch is NOT active (no lock file).
- Daily loss counter: seeded from DB on startup ✅
- Lifetime loss counter: seeded from DB on startup ✅
- Consecutive loss counter: seeded from DB on startup ✅
All three counters persist across restarts.

Consecutive loss threshold: 4 | Daily loss limit: 20% = $15.95 (on $79.76 bankroll)
Hard stop threshold: 30% lifetime = $30 total loss → $18.85 lost → $11.15 remaining

═══════════════════════════════════════════════════

## NEXT SESSION PRIORITY ORDER

### Priority 1: Wire sports_futures_v1 into a paper loop in main.py

sports_futures_v1 signal generator is complete and tested. Next: add a paper loop that:
1. Polls Polymarket.us GET /v1/markets (filtered to futures, active, not closed)
2. Polls Odds API get_nba/nhl/ncaab_championship() (6-hr cache, low quota)
3. Calls strategy.scan_for_signals() and paper-executes any signals
4. Logs signals to DB with is_paper=True, strategy="sports_futures_v1"
5. DO NOT attempt live execution until POST /v1/orders format is confirmed

**QUOTA GUARD: Implement OddsApiQuotaGuard BEFORE wiring into main.py loop**
Hard cap: 1,000 credits/month for this bot. Protect the global quota.

### Priority 2: Confirm POST /v1/orders format on Polymarket.us
- iOS app network capture (Proxyman/Charles on iPhone) is the most reliable path
- Fields needed: marketSideId/identifier, amount (proto format), order type (FOK/IOC)
- Until confirmed: ALL Polymarket execution stays paper-only
- **NEVER use GTC orders** — becomes liquidity provider, risk of adverse fill

### Priority 3: Copy trading infrastructure (deferred until .us expands)
- predicting.top + whale_watcher are built and tested
- Game-by-game markets NOT on .us yet — polling data-api.polymarket.com has no execution venue
- Re-evaluate when .us adds NBA game markets

### Priority 4: DO NOT re-promote any Kalshi live strategies
- Bankroll $79.76 — close to hard stop ($11 remaining margin before 30% lifetime stop)
- btc_lag signal frequency near-zero
- Wait for bankroll > $90 before any live promotion

═══════════════════════════════════════════════════

## RESTART COMMAND (Session 28 — all paper, no --live needed)

**Paper mode restart (current state):**
```bash
cd /Users/matthewshields/Projects/polymarket-bot
pkill -f "python main.py" 2>/dev/null; sleep 3; rm -f bot.pid
nohup ./venv/bin/python main.py >> /tmp/polybot_session29.log 2>&1 &
sleep 5 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
```

**Live mode restart (when re-enabling live — requires explicit decision):**
```bash
cd /Users/matthewshields/Projects/polymarket-bot
pkill -f "python main.py" 2>/dev/null; sleep 3; rm -f bot.pid
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session29.log 2>&1 &
sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep
```

## Key Commands

```bash
tail -f /tmp/polybot_session27.log                                    → Watch current bot
source venv/bin/activate && python main.py --report                   → Today's P&L
source venv/bin/activate && python main.py --graduation-status        → Paper progress
source venv/bin/activate && python main.py --status                   → Live snapshot
source venv/bin/activate && python -m pytest tests/ -q                → 645 tests
source venv/bin/activate && python setup/verify.py                    → Full connectivity check (now 29 checks)
```

## Loop stagger (current — all paper)

```
   0s → [trading]        btc_lag_v1                 — PAPER (was live, demoted Session 27)
   7s → [eth_trading]    eth_lag_v1                 — PAPER (demoted Session 25)
  15s → [drift]          btc_drift_v1               — PAPER (demoted Session 25)
  22s → [eth_drift]      eth_drift_v1               — PAPER
  29s → [btc_imbalance]  orderbook_imbalance_v1     — PAPER
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — PAPER
  43s → [weather]        weather_forecast_v1        — PAPER (no HIGHNY on weekends)
  51s → [fomc]           fomc_rate_v1               — PAPER (next window: March 5-19)
  58s → [unemployment]   unemployment_rate_v1       — PAPER (active until ~March 7)
  65s → [sol_lag]        sol_lag_v1                 — PAPER
```
