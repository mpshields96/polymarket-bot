# MASTER ROADMAP — polymarket-bot
# Last updated: Session 31 (2026-03-08)
# Purpose: Self-contained handoff. New chat can resume from the SECOND this one stopped.
#
# ═══════════════════════════════════════════════════════════════

## WHERE WE ARE RIGHT NOW

Bot: RUNNING (PID 53490, log /tmp/polybot_session31.log)
Mode: LIVE (--live flag, CONFIRM given at startup)
Tests: 758/758 passing
Bankroll: $79.76 | Lifetime live P&L: -$18.85 | Hard stop margin: $11.15

btc_drift MICRO-LIVE: $1.00 cap, 3/day, kill switch applies
  - 2hr cooling active (consecutive_losses=4 restored from DB)
  - Cooling expires ~15:19 UTC 2026-03-08
  - After that: real $1.00 bets will fire on btc_drift signals

All other 9 Kalshi strategies: PAPER-ONLY
Polymarket copy_trade_loop: RUNNING (paper-only, 5-min poll, 144 whales)

Restart (live mode):
  pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null
  sleep 3; rm -f bot.pid
  echo "CONFIRM" > /tmp/polybot_confirm.txt
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session31.log 2>&1 &
  sleep 10 && cat bot.pid && ps aux | grep "[m]ain.py" | grep -v grep

═══════════════════════════════════════════════════════════════

## MISSION (never changes)

PRIMARY: Profitable copy trading on Polymarket following top whale accounts.
SECONDARY: Kalshi systematic strategies (BTC/ETH/SOL price direction) if edge is proven.

The TWO HALVES are independent. Never let one break the other.

═══════════════════════════════════════════════════════════════

## CURRENT GOALS — IN PRIORITY ORDER

### GOAL 1: Prove btc_drift has real edge (Active — Micro-Live Phase)

Status: 2hr cooling → then live bets fire at $1.00 cap
What we need: 30 real settled bets + Brier < 0.30
Expected timeline: 1-2 weeks at current signal frequency (~3/day cap)
Gate to pass: DO NOT raise calibration_max_usd until 30+ bets + Brier computed
Watch command: tail -f /tmp/polybot_session31.log | grep --line-buffered "drift\|LIVE\|Trade executed\|Kill switch"

Paper data was MISLEADING (+$226 paper vs -$22 live) because:
1. Paper slippage only 1-2¢ vs real Kalshi BTC spreads 2-3¢
2. No fill queue — paper assumes instant fill
3. No counterparty (Jane St / Susquehanna reprice within seconds)

Micro-live replaces fake paper with real data at penny stakes.

### GOAL 2: Activate Polymarket copy trading on .COM (Blocked on Matthew)

Status: BLOCKED — single gate is Matthew creating polymarket.com account + Polygon wallet

What's built:
- whale_watcher.py: reads .COM whale trades (data-api.polymarket.com, public)
- predicting_top.py: fetches 144 whale wallets from predicting.top leaderboard
- copy_trader_v1.py: 6 decoy filters + Signal generator
- copy_trade_loop: runs in main.py, polls every 5 min (paper-only today)

What's missing to go live on .COM:
1. Matthew: polymarket.com account + Polygon wallet + USDC.e deposit
2. Claude: ECDSA secp256k1 auth + py-clob-client integration in src/auth/ + src/platforms/
3. Claude: POST /v1/orders via py-clob-client (FOK/IOC only — never GTC)
4. Paper validation: 30 paper copy trades before live

Monitoring notes:
- Watch copy_trade_loop for signal generation: grep "copy_trade" in log
- Top traders to monitor: HyperLiquid0xb ($1.4M), Erasmus ($1.3M), BAdiosB (90.8% win rate)
- Decoy risk: some top traders run multiple wallets to confuse copiers — our 6 decoy filters address this

### GOAL 3: Evaluate Kalshi strategy signal health

Status: All 10 paper-only — collecting calibration data

Strategy health as of Session 31:
- btc_lag_v1: Brier 0.191 (excellent), BUT ~0 signals in last 5+ days → HFTs pricing Kalshi same minute
- btc_drift_v1: Moving to micro-live; 12 live bets so far, Brier TBD
- eth_drift_v1: 41 paper trades, looks "ready" by count but P&L -$35.47 and only 1.1 days real data → DO NOT PROMOTE
- All others: collecting calibration data, not near graduation

Re-promote gate for ANY strategy:
- 30+ settled bets
- Brier < 0.30 (confirmed on real data, not just paper)
- Bankroll > $90
- No active kill switch events
- 2-3 weeks of signal history showing consistent frequency

═══════════════════════════════════════════════════════════════

## NEAR-TERM TASKS (next 1-2 sessions)

Priority 1 — Micro-live monitoring:
  - [ ] Watch first btc_drift live bets after 15:19 UTC cooling expires
  - [ ] Verify kill switch handles them correctly (record_win/record_loss wired for live path)
  - [ ] After 30 bets: run --graduation-status, compute Brier manually

Priority 2 — Matthew decides on .COM:
  - [ ] Matthew: create polymarket.com account (MetaMask/Polygon wallet)
  - [ ] After yes: Claude adds ECDSA auth + py-clob-client to src/auth/ + src/platforms/
  - [ ] After yes: Claude wires .COM order execution to copy_trade_loop

Priority 3 — paper_slippage_ticks calibration:
  - [ ] After 30+ btc_drift real bets: compare paper fill prices vs real fill prices
  - [ ] Adjust paper_slippage_ticks if gap remains (currently 2, may need to go higher)

Priority 4 — /activity endpoint test:
  - [ ] Low-risk: probe data-api.polymarket.com/activity vs /trades for latency difference
  - [ ] No auth required, no code changes to production paths
  - [ ] Could improve copy trade timing by 5-15 seconds per signal

═══════════════════════════════════════════════════════════════

## FUTURE CONSIDERATIONS (log here, don't build)

These are ideas waiting for the expansion gate to clear (btc_drift 30+ live + Brier < 0.30):

1. polymarket.COM ECDSA auth + py-clob-client integration
   - Once Matthew has account: ~2-3 sessions to build and test
   - FOK/IOC orders only — never GTC, never provide liquidity

2. /activity endpoint for whale tracking (lower latency than /trades)
   - data-api.polymarket.com/activity?user={proxy_wallet}&limit=5
   - Worth a 30-min probe when time allows

3. btc_lag re-promotion (IF signal frequency recovers)
   - Brier 0.191 = strong signal quality
   - Only re-promote if: 30-day signal count > 5/month AND bankroll > $90
   - Check monthly: grep "btc_lag.*signal" logs

4. eth_drift promotion (DO NOT until real data)
   - Current "41 trades ready" is based on 1.1 days of paper data — statistically useless
   - Need 30 calendar days of paper data minimum before evaluating

5. Whale list filtering (future work)
   - 144 whales, but only ~30% trade on .COM in markets useful to us
   - Filter for political/crypto specialists over sports-only traders
   - Prioritize: Erasmus (politics), HyperLiquid0xb (sports), BAdiosB (mispricing arb)

6. Kelly calibration at Stage 2
   - Stage 1 ($5 cap) always binds before Kelly — can't evaluate Kelly calibration here
   - Stage 2 ($10 cap) lets Kelly actually influence sizing
   - Don't evaluate Kelly performance until Stage 2 + 30+ live bets

7. OddsApiQuotaGuard for sports_futures_v1
   - 1,000 credit hard cap (5% of Matthew's 20,000/month total)
   - sports_futures_v1 is supplemental — implement guard before enabling

═══════════════════════════════════════════════════════════════

## ISSUES TO MONITOR PROACTIVELY

### Risk 1: Lifetime loss hard stop is close
  Current: -$18.85 of -$30 limit (11.15 remaining, 62.8% used)
  If btc_drift loses 12 consecutive $1.00 bets → hard stop fires
  Mitigation: 3/day cap + kill switch cooling applied — can't blow up in one day
  Watch: lifetime_loss in logs after every settled bet

### Risk 2: Kill switch cooling fires immediately on restart
  Cause: consecutive_losses=4 (at limit) is restored from DB on startup
  If bot is restarted mid-streak with 4 consecutive losses, it immediately enters 2hr cooling
  This is correct behavior. Don't panic and don't disable it.
  Resolution: wait out the cooling, or verify manually that the losing streak was real

### Risk 3: eth_orderbook_imbalance paper P&L misleading
  The $233 paper anomaly (NO@2¢ bet) was fixed in Session 31.
  BUT: paper P&L is still structurally optimistic for ALL strategies.
  Do not use paper P&L as primary graduation signal — use Brier score + trade count.

### Risk 4: btc_drift win_prob floor at 0.51
  When sigmoid model returns ≤0.50 confidence, floor clamps to 0.51 → bet still fires
  Early data (3W/5L = 38% at floor bets) showed floor bets are PROFITABLE (NO bets at 26-35¢ with favorable payout)
  Do not touch until 30+ settled live bets + Brier computed. See PRINCIPLES.md.

### Risk 5: polymarket.com security
  py-clob-client requires ETH private key
  Key must NEVER appear in logs, commits, or any file outside .env
  When implementing .COM auth: use same .env pattern as Kalshi key
  Malicious GitHub repos exist that steal private keys (Dec 2025 incident documented in copy_trading_research.md)
  Study reference repos, adapt patterns — never run third-party code with real keys

### Risk 6: Odds API credit burn
  sports_futures_v1 is built but not enabled
  1,000 credit hard cap — add OddsApiQuotaGuard before ANY call to Odds API
  Violation = wasting Matthew's quota on a supplemental strategy

### Risk 7: predicting.top API format changes
  Already bit us twice (Session 30): response wrapper change + smart_score nesting
  Add a schema-hash check or assertion on API response shape before parsing
  If leaderboard returns 0 whales: check API format before assuming list is empty

═══════════════════════════════════════════════════════════════

## HARD CONSTRAINTS (cannot be overridden by anyone, including Matthew)

From PRINCIPLES.md — violation = system degradation, not improvement:

1. NEVER change strategy parameters after a losing stretch without 30+ data points
2. NEVER add a filter because of a single bad trade — that's trauma-based rule accumulation
3. NEVER promote a strategy live without: 30 settled bets + Brier computed + bankroll > $90
4. NEVER run third-party code with our keys
5. NEVER place GTC orders on Polymarket — FOK/IOC only
6. NEVER exceed $20/week in real bets during micro-live calibration phase
7. NEVER run two bot instances simultaneously
8. NEVER change kill switch thresholds without 30+ data points AND PRINCIPLES.md review
9. TDD always: write the test first, then implement. If you can't write the test, you don't understand the requirement.

═══════════════════════════════════════════════════════════════

## WHAT THE BOT IS ACTUALLY DOING (executive summary)

KALSHI HALF: 10 strategies watching BTC/ETH/SOL/weather/macro price markets.
Only btc_drift is placing real (micro-live $1.00) bets. Others collecting paper data.
Paper data is calibration, not revenue. Paper P&L is optimistic — don't trust the number.

POLYMARKET HALF: Whale watcher polls 144 top traders every 5 min.
Generates copy-trade signals when decoy filters pass.
Currently paper-only — can't execute on .COM without ECDSA auth.
Single gate to live: Matthew creates polymarket.com account.

Combined: ~$3/day in real capital at risk (3 × $1 btc_drift bets max).
Real trading capital preserved. Calibration data accumulating.

═══════════════════════════════════════════════════════════════
