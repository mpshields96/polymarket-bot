# SESSION HANDOFF — polymarket-bot
# Feed this file + CLAUDE.md to any new Claude session to resume.
# Last updated: 2026-03-01 20:30 UTC (Session 27 — REAL BACKTEST COMPLETE, CRITICAL FINDINGS)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

Bot is **RUNNING** — PID 6225, log at /tmp/polybot_session25.log
Check: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"`

**1 strategy LIVE** (real money): **btc_lag_v1 only**
**9 strategies paper**: btc_drift_v1 (demoted), eth_lag_v1 (demoted), eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
Test count: **603/603 ✅**

Latest commits (most recent first):
- ecce5be — feat(quick-4): Kalshi real-price backtest using actual YES candlestick data
- 0bc9161 — docs: session 26 handoff — research complete, kalshi_real_backtest.py building
- f3e08ae — research: Kalshi calibration deep-dive + real backtest framework (Session 26)

## ⚠️ REAL BACKTEST FINDINGS — READ BEFORE ANY LIVE DECISIONS (Session 27)

**Scripts: `scripts/kalshi_real_backtest.py` + `scripts/real_backtest_results.md`**

### What We Tested
Used Kalshi's free historical candlestick API (1-min YES OHLCV) + Binance.US klines.
Simulated btc_lag at 30s poll intervals with REAL Kalshi prices (not hardcoded 50¢).

### Results: Two Runs Told Different Stories

**30-day run** (Jan 30 - Mar 1, 300 sampled markets):
- BTC >= 0.40% in 60s: **6 signals** (2.0% of windows)
- Directional accuracy: **66.7%**
- Avg Kalshi YES price at signal time: **49.5¢** (NOT priced in — 50¢ assumption valid)
- Mean actual edge: **13.5%**

**5-day run** (Feb 24 - Mar 1, 467 markets — most recent):
- BTC >= 0.40% in 60s: **0 signals** (44 BTC moves, ALL blocked by price guard)
- Direct investigation: BTC +0.47% at 17:10 UTC → Kalshi jumped to YES=94¢ IN SAME MINUTE

### The Critical Interpretation

**btc_lag worked in January but stopped working in February/March.**

Confirmed mechanism via manual trace (Feb 25 17:10 window):
- 17:09 UTC: Kalshi YES=51¢ (market neutral)
- BTC moves +0.473% at 17:10 UTC
- 17:10 UTC: Kalshi YES IMMEDIATELY jumps to 94¢ — HFTs priced it in within 1 minute
- Our 30s poll detects the BTC move but Kalshi is already at 94¢ → Gate 2 blocks bet

### What This Means for btc_lag

- The lag that the strategy relies on is **disappearing** as Kalshi matures
- Jan 2026: some lag existed (6/300 windows = 2% hit rate)
- Feb 24 - Mar 1 2026: zero detectable lag in 467 windows
- Our 2 live wins (trades 64, 91) likely happened in early windows before the market tightened
- Trade 91 (YES@80¢) would be BLOCKED by current 35-65¢ guard anyway

### Decision for Next Session

**Matthew needs to decide**: given only $11.15 before hard stop, should btc_lag be demoted to paper?
- Arguments FOR demoting: real backtest shows 0 signals in last 5 days; losing $11.15 closes account
- Arguments AGAINST: 30-day shows some signals exist; 2-hour soft stop still protecting capital
- Bot is currently in soft stop — no live bets firing regardless

**See `scripts/real_backtest_results.md` for full output.**

═══════════════════════════════════════════════════

## KILL SWITCH STATUS (2026-03-01 18:50 UTC)

⛔ **2-HOUR SOFT STOP ACTIVE** — restarted 12:44 CST (18:44 UTC), cooling until ~14:44 CST (20:44 UTC).
- Live bets BLOCKED until ~14:44 CST
- Paper bets CONTINUE uninterrupted (30 settled today, +$209.96)
- Daily live losses today (CST March 1): **$15.12** / $20.00 limit (75.6% — $4.88 remaining)
- All-time net live P&L: **-$18.85** (62.8% of $30 hard stop — ⚠️ only $11.15 until hard stop)
- Consecutive loss streak: **4** (soft stop active — resets when cooling ends)
- ⚠️ --report "today" uses UTC dates — shows CST-yesterday losses too. Use kill switch logs for true CST daily figure.

## P&L STATUS (2026-03-01 18:50 UTC) — COMPLETE LIVE TRADE HISTORY

ALL 21 LIVE TRADES (chronological):
```
  64  02/28 15:46  btc_lag_v1    NO@48¢  $3.36  +$3.50  run=+$3.50  ✅
  67  02/28 16:46  btc_drift_v1  YES@63¢ $4.41  -$4.41  run=-$0.91  ❌
  70  02/28 17:08  btc_drift_v1  NO@33¢  $4.95  +$9.75  run=+$8.84  ✅ (extreme odds — now blocked)
  74  02/28 17:32  btc_drift_v1  NO@34¢  $4.76  +$8.96  run=+$17.80 ✅ (extreme odds — now blocked)
  75  02/28 17:46  btc_drift_v1  NO@26¢  $4.94  -$4.94  run=+$12.86 ❌ (extreme odds — now blocked)
  78  02/28 18:05  btc_drift_v1  NO@35¢  $4.90  +$8.82  run=+$21.68 ✅
  80  02/28 18:19  btc_drift_v1  NO@57¢  $4.56  +$3.28  run=+$24.96 ✅
  81  02/28 18:34  btc_drift_v1  YES@37¢ $4.81  -$4.81  run=+$20.15 ❌
  83  02/28 18:47  btc_drift_v1  NO@50¢  $5.00  -$5.00  run=+$15.15 ❌
  85  02/28 19:01  btc_drift_v1  YES@21¢ $4.83  -$4.83  run=+$10.32 ❌ (extreme odds — now blocked)
  86  02/28 19:38  btc_drift_v1  NO@3¢   $4.98  -$4.98  run=+$5.34  ❌ (extreme odds — now blocked)
  88  02/28 19:47  btc_drift_v1  NO@28¢  $4.76  -$4.76  run=+$0.58  ❌ (extreme odds — now blocked)
  90  02/28 19:54  eth_lag_v1    NO@2¢   $4.98  -$4.98  run=-$4.40  ❌ (2¢ bet — price guard blocked now)
  91  02/28 20:00  btc_lag_v1    YES@80¢ $2.40  +$0.57  run=-$3.83  ✅
  92  02/28 20:01  eth_lag_v1    YES@74¢ $3.70  +$1.25  run=-$2.58  ✅
  94  02/28 20:15  eth_lag_v1    YES@56¢ $2.80  -$2.80  run=-$5.38  ❌
  96  02/28 20:17  btc_drift_v1  NO@65¢  $3.25  +$1.65  run=-$3.73  ✅ (at 65¢ boundary)
 110  03/01 10:35  btc_drift_v1  YES@58¢ $2.90  -$2.90  run=-$6.63  ❌
 113  03/01 10:46  btc_drift_v1  YES@21¢ $4.41  -$4.41  run=-$11.04 ❌ (extreme odds — now blocked)
 118  03/01 11:46  btc_drift_v1  YES@44¢ $3.96  -$3.96  run=-$15.00 ❌
 121  03/01 12:19  btc_drift_v1  NO@55¢  $3.85  -$3.85  run=-$18.85 ❌
```

- **Bankroll:** $79.76 (started at $100)
- **All-time live P&L:** -$18.85 (21 settled live bets, 8W/13L = 38%)
- **btc_lag_v1 only:** 2W/0L, +$4.07 (trades 64, 91) — THE SIGNAL THAT WORKS
- **btc_drift_v1:** 6W/13L (including extreme-odds wins that are now blocked)
- **All-time paper P&L:** +$233.59

## THE CORE PROBLEM — READ BEFORE TOUCHING ANYTHING

btc_drift was demoted to paper because the live vs backtest gap is too large to be variance.

**Pattern identified (Session 25 close):**
- btc_drift detects BTC drifting X% from 15-min window open → bets on continuation
- In live Kalshi markets: BTC mean-reverts more than it continues at 15-min timescale
- Market makers (Jane St, Jump, Susquehanna) ALREADY PRICE IN expected reversion
- When we buy at 40-55¢, the market is saying "we know it drifted, we expect it to snap back"
- Our model is fighting sophisticated counterparties with the same data + more

**Why it looked like it worked early:**
- Early wins (trades 70, 74, 78) were at extreme odds (NO@33-34¢) — lottery tickets that hit
- 33¢ bet that wins → pays $3 per dollar. 3 in a row = big profit, masked the underlying failure
- Now those extreme-price bets are blocked (35-65¢ guard) → remaining bets are coin flips

**What btc_lag does differently:**
- Fires only on SUDDEN EXTREME moves: ±0.40% in 60 seconds
- Momentum breakouts at this scale are less predictable for market makers
- 2W/0L live record — this is the real edge

**The honest self-critique:**
Claude spent Session 25 tuning btc_drift parameters (edge 5→8%, drift 0.05→0.10%, price guard 10-90→35-65)
instead of questioning whether the core signal was valid. Matthew correctly identified this as builder bias.
The logic error: "drift exists → drift continues" is not a valid assumption at 15-min BTC timescales.

## WHAT THE NEXT SESSION SHOULD DO

### Priority 1: Don't touch btc_drift (paper-collecting data)
It's paper-only now. Let it run. Don't touch it. When 30+ paper trades settle with Brier < 0.25, revisit.

### Priority 2: Focus on btc_lag_v1
The only live strategy. Needs ±0.40% BTC spike in 60s. Rare in calm markets, powerful when it fires.
After cooling ends (~14:44 CST = 20:44 UTC), btc_lag is the only thing placing live bets.

### Priority 3: Audit btc_lag model rigorously
Before trusting btc_lag blindly (it's 2/2 but tiny sample):
- Look at HOW it won trades 64 and 91 — were those genuine momentum plays or lucky timing?
- Check: does btc_lag have the same mean-reversion risk as btc_drift at shorter timescales?
- The key difference btc_lag should have: 60s momentum is more reliable than 15-min drift

### Priority 4: Monitor bankroll carefully
- $79.76 bankroll, $11.15 before hard stop ($30 lifetime loss)
- Daily limit: $4.88 remaining on CST March 1 (resets at midnight CST = 06:00 UTC March 2)
- After cooling: btc_lag places $3-4 bets, max 2-3 more losses before daily limit hit
- If bankroll drops below $70: re-evaluate entire live strategy approach

### Priority 5: Polymarket retail API (pending from Matthew)
Matthew said he'd provide credentials. Wire into py-clob-client auth when ready.

## START QUESTIONING: Things the next session should probe

The next Claude session should start from a position of healthy skepticism:

1. **btc_lag 2/2 sample size**: Is 2 wins proof it works, or just lucky? Look at the actual signals that fired. Were they high-confidence or marginal?
2. **Paper P&L reliability**: Paper shows +$233. BUT eth_orderbook_imbalance_v1 shows +$239 from 12 paper bets = $20/bet avg profit. Paper sizing is NOT the same as live ($5 cap). Paper numbers are misleading as live proxy.
3. **Is btc_lag fundamentally different from btc_drift?** Both detect BTC moves and bet on continuation. btc_lag uses 60-sec window vs btc_drift's 15-min drift. Are they really different signals? Probe this.
4. **Is the edge real or bid-ask spread?** Kalshi's 17¢ spread eats into any edge. At 40¢ bet, the spread is 17/40 = 42% of the bet price. Do we actually have edge after the spread?

## WHAT NOT TO DO

1. **DO NOT build new strategies** — expansion gate in effect, bankroll shrinking
2. **DO NOT re-promote btc_drift** until 30+ paper trades + Brier < 0.25
3. **DO NOT change kill switch thresholds** — deliberately set
4. **DO NOT add more filters** — been there, doesn't fix the fundamental signal problem
5. **DO NOT panic-trade** — cooling period is protecting capital, let it run

## RESTART COMMAND (if bot is stopped)

```bash
cd /Users/matthewshields/Projects/polymarket-bot
kill -9 $(cat bot.pid) 2>/dev/null; sleep 3; rm -f bot.pid
echo "CONFIRM" > /tmp/polybot_confirm.txt
nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session26.log 2>&1 &
sleep 8 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep | grep -v zsh
```

## Loop stagger (reference)

```
   0s → [trading]        btc_lag_v1                 — LIVE ← ONLY LIVE STRATEGY
   7s → [eth_trading]    eth_lag_v1                 — PAPER (demoted 2026-03-01)
  15s → [drift]          btc_drift_v1               — PAPER (demoted 2026-03-01)
  22s → [eth_drift]      eth_drift_v1               — paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper
  43s → [weather]        weather_forecast_v1        — paper (no HIGHNY weekends)
  51s → [fomc]           fomc_rate_v1               — paper (active March 5-19)
  58s → [unemployment]   unemployment_rate_v1       — paper (active until March 7)
  65s → [sol_lag]        sol_lag_v1                 — paper
```

## Key Commands

```bash
tail -f /tmp/polybot_session25.log                                       → Watch bot
source venv/bin/activate && python main.py --report                      → Today's P&L
source venv/bin/activate && python main.py --graduation-status           → Paper progress
source venv/bin/activate && python main.py --status                      → Live snapshot
source venv/bin/activate && python -m pytest tests/ -q                   → 603 tests
```
