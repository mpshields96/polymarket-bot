# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 28 — PHASE 5.1 COMPLETE, POLYMARKET WIRED)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 9282, log at /tmp/polybot_session27.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**ALL 10 strategies PAPER-ONLY** — no live bets firing
Test count: **645/645 ✅**
Last commit: **5f338bb** — feat: Phase 5.1 Polymarket auth + REST client (645 tests)

Latest commits (most recent first):
- 5f338bb — feat: Phase 5.1 Polymarket auth + REST client (645 tests)
- b8f9947 — docs: update POLYBOT_INIT.md (Sessions 23-25)
- 6824c31 — docs: session 25 final handoff — btc_drift demoted, btc_lag only live
- 9da4941 — feat: demote btc_drift_v1 to paper-only (live record 7W/12L)

═══════════════════════════════════════════════════

## SESSION 28 WORK COMPLETED

### Phase 5.1 — Polymarket.us Auth + REST Client
Everything built and tested. 42 new tests written (TDD, all passing).

**Files created:**
- `src/auth/polymarket_auth.py` — Ed25519 signing module (19 tests)
- `src/platforms/polymarket.py` — Async REST client (23 tests)
- `tests/test_polymarket_auth.py` — Auth unit tests
- `tests/test_polymarket_client.py` — REST client unit tests

**verify.py additions:**
- Check [12]: Polymarket auth headers (Ed25519 key loads + signs correctly)
- Check [13]: Polymarket API live connectivity (GET /v1/markets returns data)
- Both pass as ⚠️ WARN (non-critical) — correct, Polymarket is secondary platform

**Credentials wired in .env:**
- POLYMARKET_KEY_ID=2cc84e44-f5f6-44dc-9bc7-15ff7ebc517c
- POLYMARKET_SECRET_KEY=64-byte Ed25519 key (base64, confirmed working)

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

### Priority 1: Architecture Decision on Phase 5.2

Before writing any code, decide: Option A (wait for crypto) or Option B/C (build sports strategy).

**If Option B/C (sports):**
- Read `.planning/ROADMAP.md` Phase 5.2 spec
- `src/strategies/sports_moneyline.py` using The-Odds-API vs Polymarket.us
- MUST implement OddsApiQuotaGuard first (1,000 credit hard cap for this bot)
- Paper-first: 30+ settled trades + Brier < 0.25 before live
- See CLAUDE.md Gotchas: "Odds API — 1,000 credit hard cap for this bot"

**If Option A (wait):**
- No code to write
- Let Kalshi paper loops collect Brier data passively
- Monitor Polymarket.us for new market categories

### Priority 2: DO NOT re-promote any live strategies yet
- Bankroll $79.76 — too close to hard stop for experimental live trades
- btc_lag Kalshi signal frequency is near-zero right now
- Wait for bankroll > $90 before any live promotion

### Priority 3: Watch eth_orderbook_imbalance_v1
It has +$236 paper P&L across 13 trades in 1.1 days. That's suspiciously high.
Before trusting it: audit whether the paper executor is simulating fills correctly.
$236 on $65 bankroll-equivalent paper sizing suggests something is off with fill simulation.

### Priority 4: Real backtest findings context
(Keep in mind for every decision)
- btc_lag: 0 signals in last 5 days (Jan-Feb had lag; Mar has near-zero lag)
- HFTs price KXBTC15M within same 1-min candle as BTC moves
- The signal is valid but the execution venue (Kalshi) has matured to near-zero alpha
- Polymarket.us could be better — if/when crypto markets launch

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
