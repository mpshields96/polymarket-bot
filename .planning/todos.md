## [DONE] btc_drift: add price extremes filter (min/max price guard)
**Completed:** 2026-03-01 Session 25 cont2 — tightened to 35-65¢ (commits 1a6c136 + tests). Applied to btc_lag.py too.

---

## [ ] count_trades_today() uses UTC midnight, not CST midnight
**Added:** 2026-03-01 Session 25 cont2
**Problem:** `db.count_trades_today(strategy, is_paper)` uses UTC midnight as the day boundary. The daily loss counter was already moved to CST midnight (UTC-6) in Session 25, but bet cap counting wasn't updated. This means bets from CST Feb 28 evening (00:00-06:00 UTC = 6-8 PM CST) eat into the CST March 1 daily bet cap.
**Impact observed:** btc_drift_v1 hit 10/10 UTC cap at 11:06 CST March 1. A 9.4% edge signal at 53¢ (would have passed all new quality filters) was blocked because 8/10 slots were used by CST-yesterday bets.
**Fix:** Modify `db.count_trades_today()` to accept an optional `tz_offset_hours=-6` parameter, same pattern as `daily_live_loss_usd()`. Update all callers in main.py. Write regression test.
**Effort:** ~30 min (DB query + one param, update main.py callers, 2-3 new tests)
**Priority:** Medium — causes no losses, only misses good signals when day boundary crosses CST evening
**Approval needed:** Yes — functional behavior change to bet cap logic; don't merge without Matthew's OK

---

## [ ] btc_drift: add price extremes filter (min/max price guard)
**Added:** 2026-02-28 Session 23
**Problem:** btc_drift fires at any price, including 3¢ NO / 97¢ YES. At those extremes:
  (1) The sigmoid model was NOT calibrated on extreme-probability signals — accuracy at 3¢ is unknown
  (2) Market has typically already efficiently priced in certainty; HFTs have pushed it there for a reason
  (3) 33:1 payout ratio means variance is enormous even with positive expected value
  (4) late_penalty reduces confidence but NOT edge_pct — late + extreme price still passes filter (gotcha)
**Fix:** Add `min_signal_price_cents` / `max_signal_price_cents` config params to btc_drift strategy.
  Suggested range: 10¢–90¢. Signals outside this range are skipped — model not calibrated there.
  Also consider applying late_penalty to edge_pct (not just confidence) for bets < 5 min remaining.
**Effort:** ~30 min (add guard in btc_drift.generate_signal(), update config.yaml, write tests)
**Priority:** Medium — current $5 hard cap limits damage, but this is a calibration gap.

---

## [ ] Update starting_bankroll_usd when bankroll crosses stage thresholds
**Added:** 2026-02-28 Session 23
**Problem:** `DAILY_LOSS_LIMIT_PCT × starting_bankroll_usd` is the daily loss cap. `starting_bankroll_usd` is set to $100 in config.yaml but real bankroll is ~$115 and growing. As bankroll grows the limit stays fixed at $20 — becomes increasingly conservative relative to true exposure.
**Action:** At each stage promotion, update `starting_bankroll_usd` in config.yaml risk section to match actual bankroll. Could also make it dynamic (read from DB at startup).
**When:** Do before or concurrent with Stage 2 promotion. Not urgent until bankroll > $150.
**Estimated effort:** 10 min (config.yaml one-liner + update tests that hardcode $100)

---

## [ ] Volatility-Adaptive Parameters (btc_lag / btc_drift)
**Added:** 2026-02-28 Session 22
**Observation:** All strategy parameters are static (config.yaml). On calm days (e.g. weekends), btc_lag fires 0 signals because BTC moves 0.005–0.068% vs 0.40% threshold. On high-vol days, same threshold may be too loose (noise trades). The bot doesn't know what "today's volatility regime" is.
**Current partial adaptation:** Kelly sizing already scales bet size to edge_pct per signal — higher-edge signals get bigger bets. But threshold for signal entry is fixed.
**Options:**
  - (A) Realized-vol-scaled min_edge_pct: if 1h realized vol < 0.15%/min, widen lag threshold; if > 0.5%/min, tighten it
  - (B) ATR-based reference window: widen btc_drift drift threshold on calm days, tighten on volatile days
  - (C) No change — static thresholds are intentional (wait for clean signal only)
**Decision gate:** Need 30 live bets first to know if static params are performing. Do not build until expansion gate clears.
**Estimated effort:** 1 session (add vol calculation to BinanceFeed, pass to strategies, update tests)
**Unlock condition:** 30+ live settled bets + expansion gate cleared

---

## [ ] Sports Game Strategy (KXNBAGAME / KXNHLGAME)
**Added:** 2026-02-28 Session 20
**Series:** KXNBAGAME (38 markets, up to 1.35M vol, 1-2¢ spread), KXNHLGAME (48 markets, up to 108K vol, 1-4¢ spread). KXMLBGAME unusable pre-season (54¢ spread).
**Approach:** Compare Kalshi implied probability vs sports data feed moneyline (free tier, 500 req/month). If edge > 5%, bet the underpriced side.
**Files to create:** src/data/odds_api.py, src/strategies/sports_game.py, new loop in main.py
**Signal rate:** ~2 bets/day in NBA season, closes at tip-off (clean settlement)
**Data source:** https://sports-data-feed.com/ (free tier covers NBA + NHL)
**Estimated effort:** 1 session (new data feed + strategy + loop)
**Unlock condition:** 30 live trades collected on current 3 live strategies

---

## [ ] CPI / Inflation Release Strategy
**Added:** 2026-02-28 Session 21
**Source:** Reddit r/Kalshi + prediction market research
**Rationale:** Kalshi has economic data release markets. Markets with advance data (CPI estimates from Cleveland Fed NowCast) vs Kalshi price = structural edge. Bad CPI surprises have asymmetric market reaction (overshoots expected). Algo traders who process data before market update it have 10-20s edge window.
**Series to target:** KXCPI* (CPI Y/Y, M/M) — check Kalshi API for active series
**Data source:** Cleveland Fed CPI NowCast (free, no key), BLS press release
**Approach:** Similar to fomc_rate_v1 — fetch CPI consensus + NowCast before release. Compare to Kalshi price. If edge > 5%, bet toward NowCast. Hold through release.
**Signal rate:** ~12 releases/year (monthly CPI + core CPI)
**Estimated effort:** 1 session (new data feed + strategy, reuse fomc_loop structure)
**Unlock condition:** After current strategies stable and 30+ live trades

---

## [DECISION GATE] Phase 5.2 — Polymarket Copy Trading Architecture
**Added:** 2026-03-01 Session 29
**Status:** BLOCKED — one decision required before any code is written

### Confirmed facts (live API probing, Session 29):
- `data-api.polymarket.com` — 100% public, zero auth, no meaningful rate limit
  - `/trades?user={proxy_wallet}` — full trade history per wallet
  - `/positions?user={proxy_wallet}` — open positions with avg price, P&L, endDate
  - `/trades` (no user param) — last N global trades across all markets
  - Fields for decoy filter all present: size, price, timestamp, endDate, cashPnl
- `gamma-api.polymarket.com` — 100% public, full market catalog (crypto + politics + sports)
  - BTC Up/Down 5-min AND 15-min markets CONFIRMED LIVE on polymarket.com
  - SOL, ETH, XRP Up/Down also active
- `predicting.top/api/leaderboard?limit=179` — 100% public, returns 144 whale proxy addresses
  - Proxy wallet format matches data-api exactly — no scraping needed
  - Fields: name, wallet, additional_wallets, smart_score, twitter, stats
- `polymarket.com` vs `polymarket.us` — COMPLETELY SEPARATE SYSTEMS
  - polymarket.us: Ed25519 auth (our existing keys) — sports-only for US iOS users
  - polymarket.com: ECDSA secp256k1 (Ethereum) auth via py-clob-client — full platform

### The single gate question: polymarket.com account with Polygon wallet?
**Path A (RECOMMENDED): Create polymarket.com account**
  - Full crypto + politics platform (BTC/ETH/SOL 15-min markets, elections, geopolitics)
  - New auth: ECDSA via `Polymarket/py-clob-client` (Python, MIT licensed)
  - New file: `src/auth/polymarket_clob_auth.py`
  - Capital requirement: USDC deposit to Polygon wallet
  - Order safety: FOK/IOC only — NEVER GTC (hardcoded constant prevents liquidity provision)
  - Effort: 1-2 sessions for auth + copy_trader_v1 strategy (paper first)

**Path B: Cross-platform signal filtering (no new account)**
  - Use .com whale data as a confirmation filter for .us sports bets
  - Mismatched execution context — whale trades .com, we execute .us, prices differ
  - No new credentials needed but signal quality is degraded

**Path C: Intelligence-only (read only, no new execution)**
  - Build whale poll loop, feed confidence score as gate on existing strategies
  - Kalshi KXBTC15M near-zero signals regardless of filtering — unblocks nothing

**Decision needed from Matthew:** "Do you want to create a polymarket.com account + Polygon wallet?"
  If yes → Path A: 1-2 sessions, new auth, copy_trader_v1, paper-first
  If no  → Path C for now, revisit when .us expands beyond sports

### What can be built NOW regardless of decision (zero risk):
- `src/data/whale_watcher.py` — poll loop for data-api.polymarket.com (reads only, no trading)
- `src/data/predicting_top.py` — fetch/cache whale watchlist from predicting.top API
- DB schema: `whale_trades` table (log all whale activity for replay/backtesting)
This is pure read infrastructure. No execution. No credentials needed. Safe to build immediately.

---

## [ ] Cross-Market Arbitrage (Kalshi ↔ Polymarket)
**Added:** 2026-02-28 Session 21
**Source:** Prediction market research — same event priced on two markets with different liquidity = temporary spread opportunities
**Rationale:** Kalshi and Polymarket sometimes price the same event differently (e.g. Fed rate decision, major sports). If spread > fees, bet the underpriced side on each.
**Risk:** Requires Polymarket integration (CLOB API, USDC wallet on Polygon). Complex.
**Estimated effort:** 2-3 sessions (Polymarket data feed + cross-market signal + dual execution)
**Unlock condition:** Low priority — only after all current strategies at 30+ live trades

---

## [ ] In-Game / Live Sports Trading
**Added:** 2026-02-28 Session 21
**Source:** Reddit research — Kalshi has in-play markets (re-entry/exit on score changes)
**Note:** sports_game_v1 skeleton already built (Session 20) but disabled. Expand to support live score feeds.
**Data source:** sports data feed live scores feed (within current 20k/month budget)
**Estimated effort:** 1 session (extend existing skeleton)
**Unlock condition:** Enable sports_game_v1 first (30 live trades threshold + SDATA_KEY)

---

## [ ] Personal Expertise Markets (Finance/Medical)
**Added:** 2026-02-28 Session 21
**Source:** Reddit consensus — domain expertise is the most durable edge on Kalshi
**Matthew's edge:** Medical/healthcare markets (FDA approvals, drug trial outcomes, public health data). Also macro/financial markets (yield curve, Fed policy).
**Kalshi series to explore:** KXFDA* (FDA decisions), KXHEALTH* (health metrics), KXPOP* (demographics)
**Approach:** Manual signal review → systematic model once pattern validated
**Estimated effort:** Research session first (no code), then 1 session per series
**Unlock condition:** After current strategies stable

---

## [ ] Code Quality — `confidence` Field Wiring
**Added:** 2026-02-28 Session 21
**Issue:** Signal.confidence is computed in every strategy but never consumed downstream (not used in sizing, kill switch, or main.py). Dead field.
**Options:** (A) Wire confidence into Kelly sizing as a multiplier (lower confidence = smaller bet). (B) Remove from Signal dataclass and all strategy files.
**Recommendation:** Option A — use confidence as a Kelly multiplier: `kelly_fraction *= signal.confidence`. Would naturally reduce bet size for late-reference and low-certainty signals.
**Estimated effort:** 0.5 session (sizing.py + test updates)
**Priority:** Low — current $5 hard cap means impact is minimal

---

## [ ] Code Quality — Log Label Cosmetic Fixes
**Added:** 2026-02-28 Session 21
**Issues (cosmetic only, not functional):**
- eth_drift uses BTCDriftStrategy internally → logs say `[btc_drift]` and "BTC=ETH_price"
- settlement_loop uses paper_exec.settle() for live trades → logs say `[paper] Settled` even for live trades
**Fix:** (A) Refactor BTCDriftStrategy to accept a configurable name for log labels. (B) Add mode-aware settle logging in settlement_loop.
**Estimated effort:** 0.5 session
**Priority:** Very low — cosmetic only

---

## [ ] Restart Hardening — venv Python Path
**Added:** 2026-02-28 Session 21
**Issue:** Restart commands with `python` or `nohup python` fail if venv not active. Always need full path: `/Users/matthewshields/Projects/polymarket-bot/venv/bin/python`
**Fix:** Add a `scripts/restart_bot.sh` shell script that encodes the correct path, log path, and CONFIRM pipe. Single command to restart safely.
**Estimated effort:** 5 minutes
**Priority:** Low — restart is infrequent

---

## [x] Live bet announcement (DONE Session 21)
- _announce_live_bet(): banner log + Reminders notification on every live order confirmation
- 7 tests in tests/test_live_announce.py

---

## [ ] sports data feed Integration — Quota Guard + Kill Switch (FUTURE — next session)
**Added:** 2026-03-01 Session 22
**Context:** Matthew obtained sports data feed subscription (20,000 credits/month, renewed March 1 2026).
**Standing directives from Matthew:**
- **HARD CAP: 500 credits max for polymarket-bot** (5% of 20,000 monthly budget)
- Before ANY API call: implement a quota counter + hard stop (like kill_switch but for API credits)
- Sports props / moneyline / spreads / totals are NOT for Kalshi bot (different system)
- Do NOT confuse with titanium-v36 / agentic-sandbox-rd project (entirely separate sports betting system)
- Reference code at ~/ClaudeCode/agentic-sandbox-rd (READ ONLY for reference, not this session)
**What OddsAPI CAN help with in Kalshi bot:**
- FOMC/macro market calibration: cross-reference Fed futures odds vs KXFEDDECISION prices
- Potentially: BTC volatility implied vols from derivatives markets (if covered by API)
- NOT: sports game props, moneyline, spreads — those are separate system
**Implementation requirements (before first API call):**
1. `src/data/odds_api.py` — OddsApiClient with rate counter and quota enforcement
2. `QuotaGuard`: tracks credits used, raises if > 500 credits
3. Config: `odds_api.max_monthly_credits: 1000` in config.yaml
4. Tests: test_odds_api.py with quota guard tests
5. Manual review of first 10 API responses before wiring into strategy
**API info:** https://sports-data-feed.com/ | Key in .env as SDATA_KEY
**Estimated effort:** 0.5 session (quota guard only) + 1 session (FOMC calibration feature)
**Unlock condition:** After expansion gate clears (30+ live trades on btc_drift, ~4-6 weeks)

---

## [ ] Copytrade / Polymarket Access Research
**Added:** 2026-03-01 Session 22
**Context:** Matthew mentioned copytrade feature on Polymarket + potential VPN access.
**Research needed:**
- Does Polymarket have a copytrade feature (copy another trader's positions)?
- Is Polymarket accessible via VPN from the US without ToS violation?
- Are there Polymarket API SDKs that would allow programmatic trading?
- Cross-market arb: Kalshi vs Polymarket on same event (BTC price, FOMC, etc.)
**Sources to check:**
- r/Kalshi, r/predictionmarkets, r/algobetting
- Polymarket docs: https://docs.polymarket.com
- Polymarket API: Gamma API + CLOB API
**Decision gate:** Do not build until current strategies stable. Research only.
**Estimated effort:** 0.5 session research, then assess

---

## [DONE] Kill Switch Event Log — Test Pollution Fix
**Completed:** Session 35 — already fixed in `_hard_stop()` at line 454 of kill_switch.py.
`PYTEST_CURRENT_TEST` guard returns early before writing EVENT_LOG or lock file.

---

## [ ] Sports Betting System — Entirely Separate Project
**Added:** 2026-03-01 Session 22
**Standing directive from Matthew:** Sports props / moneyline / spreads / totals are NOT for this bot.
- Entirely separate system from Kalshi/polymarket-bot
- Reference code: ~/ClaudeCode/agentic-sandbox-rd and titanium-v36 subdirectory
- sports data feed (20,000 credits/month) is the primary data source for that system
- Do NOT mix sports betting logic into polymarket-bot
**What this means for polymarket-bot:**
- KXNBAGAME / KXNHLGAME market types: potentially still viable (these are prediction markets on game outcomes, not traditional sportsbook bets) — but Matthew wants a very solid argument before pursuing
- Required: Cite multiple r/algobetting + r/predictionmarkets + r/Kalshi posts showing comparable strategies work on prediction markets vs traditional sportsbooks
- Only pursue if Matthew explicitly approves after review of that research
**Decision gate:** Matthew must explicitly approve after research. Default is NO for sports on Kalshi bot.

---

## [ ] Polymarket US Copy Trading — Future Roadmap Item
**Added:** 2026-03-01 Session 25
**Deep research completed:** Session 25 cont (API research agent)

**UPDATED STATUS — Phase 0 is essentially already done:**

**Arc browser fix (immediate):**
Matthew's $60 account is on the US beta at **`polymarket.us`** (not polymarket.com).
Open `polymarket.us` in Arc — that's where the US beta lives. polymarket.com is the
international platform which doesn't know about the US beta account.

**API infrastructure — fully documented, no reverse engineering needed:**
- Official Python SDK: `py-clob-client` v0.34.6 (pip install py-clob-client), maintained by Polymarket
- CLOB trading API: `https://clob.polymarket.com` (same endpoint for US and international)
- Gamma market data: `https://gamma-api.polymarket.com`
- Data API (public): `https://data-api.polymarket.com` (positions, activity, leaderboard)
- Runs on Polygon (chain_id=137)

**Authentication (two-level):**
- L1: EIP-712 wallet signature — for Google/email login use signature_type=1 (Magic wallet)
- L2: apiKey + secret + passphrase → HMAC-SHA256 signed requests
- Generate credentials at `polymarket.us/developer` after identity verification
- Headers: POLY_ADDRESS, POLY_API_KEY, POLY_PASSPHRASE, POLY_SIGNATURE, POLY_TIMESTAMP

**Copy trading data endpoints (public, no auth):**
- Leaderboard: `GET https://data-api.polymarket.com/v1/builders/leaderboard?timePeriod=MONTH&limit=50`
- Wallet positions: `GET https://data-api.polymarket.com/positions?user=<wallet_address>`
- Wallet activity: `GET https://data-api.polymarket.com/activity?user=<wallet_address>`
- Orderbook: `GET https://clob.polymarket.com/book?token_id=<tokenId>`

**What's needed before building:**
1. Open `polymarket.us` in Arc, confirm account/balance shows
2. Go to `polymarket.us/developer` → generate API credentials (apiKey + secret + passphrase)
3. `pip install py-clob-client` in new repo
4. Test connection: `ClobClient("https://clob.polymarket.com", key=<wallet_key>, chain_id=137, signature_type=1)`
5. That's it — no Charles Proxy needed, no API discovery, full docs exist

**Architecture (confirmed from research):**
```
polymarket-copytrade/          # SEPARATE REPO from polymarket-bot
├── src/auth/poly_auth.py      # py-clob-client wrapper (L1→L2 creds)
├── src/data/leaderboard.py    # data-api.polymarket.com/v1/builders/leaderboard
├── src/data/positions.py      # data-api.polymarket.com/positions?user=<wallet>
├── src/data/markets.py        # gamma-api.polymarket.com markets
├── src/strategies/copy.py     # filter + sizing logic
├── src/risk/kill_switch.py    # same pattern as Kalshi
├── src/execution/poly_exec.py # py-clob-client order placement
└── src/db.py                  # SQLite (copied trades, P&L)
```

**Decision gate:** Do NOT build until (a) Kalshi btc_drift at 30+ live trades + Brier < 0.30
and (b) 2-3 weeks of stable live P&L. Until then: credentials setup only (no code).

---
## [RESEARCH] KXFEDDECISION strategy improvement (fomc_rate_v1)
**Added:** Session 40 (2026-03-09)
**Priority:** Medium — post-gate research
**Volume:** $23.4M (largest Kalshi market by far, CORRECTED from 4,700)

**Current state:** fomc_rate_v1 uses FRED yield curve spread (DGS2-DFF) as signal.
Paper-only. Has not placed any trades recently.

**Research finding (Session 40):** CME FedWatch vs Kalshi arbitrage is the key edge.
- Near FOMC meeting: Kalshi is already efficient (near-perfect day-before accuracy per NBER paper)
- 2-4 WEEKS before meeting: CME FedWatch often diverges from Kalshi pricing
- The "54% spread" example (Feb 2026): CME=90% hold, Kalshi priced cut possibility much higher
- This spread = the edge window for fomc_rate_v1

**Proposed improvement:**
1. Add CME FedWatch scraper: fetch implied probability from cmegroup.com/markets/interest-rates/cme-fedwatch-tool
2. Compare CME implied probability vs Kalshi KXFEDDECISION H0/C25 for each meeting
3. When spread > threshold (e.g., 5%): take position in Kalshi market
4. Signal fires only 2+ weeks before meeting (where spread is largest)
5. Fee structure note: KXFEDDECISION uses quadratic_with_maker_fees — model this in sizing

**DO NOT BUILD:** Until expansion gate opens + fomc_rate_v1 has 5+ paper trades per FOMC cycle.
**Action:** Log here, revisit after btc_drift/eth_drift/sol_drift graduate.

---
## [RESEARCH] Barrier event strategy: KXBTCMAX100 / KXBTCMAX150 (first-passage-time model)
**Added:** Session 42 (2026-03-10)
**Priority:** Medium-High — post-expansion-gate research
**Volume:** KXBTCMAX100=$2.7M (5 open mkts) | KXBTCMAX150=$10.8M (3 open mkts)

**Market structure:**
- "When will BTC cross $100k again?" — date-bracketed barrier events (MAR/MAY/JUNE/SEP/DEC 2026)
- "When will BTC hit $150k?" — date-bracketed (MAR/APR/MAY 2026 now, very low odds)
- Settlement: YES if BTC touches the barrier level before the date deadline

**Pricing model needed:**
- NOT simple drift (σ√T) — this is a first-passage-time probability
- Correct formula: P(τ ≤ T | S_0 = current_price, K = barrier)
  = Φ((-ln(K/S) + μT)/(σ√T)) + (S/K)^(2μ/σ²) × Φ((-ln(K/S) - μT)/(σ√T))
  Where μ=drift (log), σ=realized vol (log), Φ=normal CDF
- Input data: Binance.US 30-day realized vol + drift (already in backtest.py)

**Session 42 probe data (BTC ~$82k, Tuesday Mar 10):**
- KXBTCMAX100 DEC 2026: Kalshi prices at 41/42c → GBM should give ~40-45% first-passage-time
- KXBTCMAX100 JUNE 2026: 21/22c → GBM gives lower? Need to compute to see if edge exists
- KXBTCMAX150 MAY 2026: 4/5c → BTC needs +83% in 12 weeks, GBM says ~1-2%? Possible edge.

**Reddit/GitHub research (Session 42):**
- NO open-source bots or strategy posts for barrier event markets found
- Markets appear algorithmically underexplored (HFTs focus on 15-min direction, not barriers)
- Potential first-mover edge for a first-passage-time model

**Spread quality:**
- KXBTCMAX100: ~1c spread on 15-42c markets → tradeable (3-7% effective spread)
- KXBTCMAX150: ~1c spread on 2-5c markets → wide effective spread (20-50%), harder

**DO NOT BUILD:** Until (a) expansion gate opens (btc_drift 30+ live + Brier + 2+ weeks P&L),
(b) first-passage-time model coded + backtested, (c) paper traded 10+ signals.
**Next step when gate opens:** Code GBM first-passage-time formula, compare vs KXBTCMAX100 DEC pricing.

---
## [RESEARCH] KXBTCMAXW weekly BTC max — CLOSED (confirmed dormant)
**Added:** Session 42 (2026-03-10)
**Priority:** DO NOT BUILD — series inactive
**Finding:** 0 open markets on Tuesday Mar 10 (and Sunday Mar 9). Was seasonal Nov 2024.
**Conclusion:** KXBTCMAXW is a discontinued or seasonal series. Not worth building for.
**Action:** Archive this research item. Do not revisit unless new open markets appear.


---
## [RESEARCH] KXNASDAQ100Y — Annual Nasdaq range markets (same model as KXBTCMAXY)
**Added:** Session 42 (2026-03-10)
**Priority:** Low — post-gate research, well after crypto graduate
**Volume:** $516,451 total (top market $467,972) — decent annual market

**Market structure:** "Will Nasdaq be above X by Dec 31, 2026?"
  - Same barrier option structure as KXBTCMAXY (annual max)
  - 5 open markets with T33000 (33k threshold) at 2/6c
  - Priced very low suggesting Nasdaq is significantly above previous targets

**Why interesting:** Same model as KXBTCMAXY. If/when we build annual BTC max pricing,
reuse for KXNASDAQ100Y. Different underlying (Nasdaq vs BTC) but identical market structure.
Input data: Binance.US equivalent = would need a Nasdaq data feed (Yahoo Finance or FRED).

**DO NOT BUILD:** Gate closed. Log for post-expansion roadmap only.
**Next step:** After building KXBTCMAXY model, evaluate reuse for KXNASDAQ100Y.


---
## [CONFIRMED DORMANT] KXBTCMAXW — Weekly BTC Max series
**Confirmed:** Session 43 (2026-03-10) — probed on weekday, 0 markets ANY status
**Previous note:** Session 39 error listed as dormant; Session 40 re-noted
**Action:** Confirmed dead. Remove from future research priority. If it ever reopens, KALSHI_MARKETS.md update needed.

---
## [RESEARCH] KXCPI — Monthly CPI direction markets
**Added:** Session 43 (2026-03-10)
**Volume:** 6,729 total (50 open markets) — VERY LOW LIQUIDITY
**Structure:** "Will CPI rise more than X% in month Y?" — binary over monthly BLS release
  - Near-mid markets (30-70¢): 14 markets available for Aug/Sep/Oct/Nov 2026
  - Best: KXCPI-26SEP-T0.2 (49¢), KXCPI-26AUG-T0.2 (42¢), KXCPI-26JUN-T0.2 (59¢)
**Why potentially interesting:** CPI monthly release is predictable event window. FRED data
feeds already built (fred_feed.py used by fomc/unemployment). Could reuse similar approach.
**Blocker:** Volume 6.7k total (vs KXFEDDECISION 23.4M). Max 50 contracts/bet with no market impact = ~$25 max position. Not worth engineering effort given low liquidity.
**DO NOT BUILD:** Gate closed + insufficient volume. Low priority even post-gate.
**Note:** KXPCE (PCE inflation, similar to CPI) and KXJOLTS (job openings) both have 0 open markets.

---
## [CONFIRMED] KXNASDAQ100Y — Updated volume
**Session 43 probe:** 30 open markets, 773,906 total vol (up from 516k estimate)
**All markets:** Extreme prices only — YES=2-10¢ or 88-97¢. Zero near mid-price.
**Assessment:** High volume but completely unsuitable for signal-based trading. All markets
have strong directional conviction (Nasdaq is far above/below the strike prices). Market
has efficiently priced these. DO NOT BUILD any signal strategy for KXNASDAQ100Y — there
is no near-50¢ market to exploit with a signal edge.

---
## [RESEARCH] Market-making strategy on Kalshi 15-min markets
**Added:** Session 43 (2026-03-10) — found during autonomous research
**Source:** github.com/nikhilnd/kalshi-market-making (QuantSC project)
**Strategy:** Post resting YES/NO bids symmetric around a probability model.
  Uses Cauchy distribution for S&P 500, calibrated via MLE from historical data.
  Inventory control: adjust spread based on position (skew quotes to reduce inventory risk).
  Result: earns the bid-ask spread passively WITHOUT needing to predict direction.
**Why interesting:** Fundamentally different from our directional approach. 
  Market-making earns the spread on EVERY window, not just when signals fire.
  Spread on 15-min BTC markets is typically 2-4¢ — $0.02-0.04/contract.
  At 50 contracts/bet with 96 windows/day: could generate $96-192/day if fills are consistent.
  Key risk: adverse selection (market moves against you before cancel). 
  Need Cauchy/sigmoid model calibrated to BTC 15-min windows (same data we already have).
**Prerequisites:**
  - Expansion gate must be open
  - Write API calls are rate-limited (5/sec on Kalshi) — order management within limits
  - Need cancel+replace logic (different from current taker-only approach)
  - Kalshi WebSocket API for real-time orderbook (current client may need extension)
**Implementation sketch:**
  1. Use existing BTC drift sigmoid model as probability estimate
  2. Post YES bid at P-spread/2, YES ask at P+spread/2
  3. Adjust spread based on current inventory (positive → lower bid, higher ask)
  4. Cancel and re-quote every 30s or on significant price move
  5. Position limit: 20-40 contracts per window
**DO NOT BUILD:** Gate closed. Post-gate candidate #2 after KXBTCMAX100/150.

---

## [ ] FOMC March 18 Window — Promote fomc_rate_v1 to Live (Time-Sensitive)
**Added:** Session 48 (2026-03-11) via Reddit/research
**Urgency:** KXFEDDECISION-26MAR closes March 18. Next Fed decision ~March 18-19.
**Context:** Fortune (Jan 2026): "Kalshi maintains perfect forecast record on Fed rate decisions,
beating professional forecasters." KXFEDDECISION at 23.4M volume (LARGEST Kalshi market).
Our fomc_rate_v1 paper strategy fires when yield curve signal fires ~8x/year.
**Gap:** fomc_rate_v1 has 0/5 paper trades. Per PRINCIPLES.md, 5 trades min before live.
Cannot promote in time for March 18 window at current 0 settled paper bets.
**Action for future:** When KXFEDDECISION-26MAR closes March 18, check if paper bet placed.
If fomc_rate_v1 paper bets accumulate before June FOMC (June 17-18), consider promoting to live.
The window is short (2 days pre-decision). When it fires, the edge is substantial.
**Priority:** Medium — next window June 2026

---

## [ ] Maker (Limit) Orders — Reduced Taker Fees on Drift Strategies
**Added:** Session 48 (2026-03-11) via market research
**CORRECTED Session 50 (2026-03-11):** Kalshi DOES charge maker fees (changed April 2025).
Taker fee: 0.07 × C × P × (1-P). Maker fee: 0.0175 × C × P × (1-P). Makers pay 25% of taker rate.
At 50¢ price: taker = 1.75¢/contract, maker = 0.44¢/contract. Saving: 1.31¢/contract.
For 5 USD bet (10 contracts at 50¢): taker fee = 17.5¢, maker fee = 4.4¢. Savings: 13.1¢/bet.
~10 live bets/day × 13.1¢ = ~$1.31/day savings. Over 3 days = ~$4. Meaningful but not game-changing.
**ADVERSE SELECTION RISK:** Limit orders fill only when market moves against you (adverse selection).
When your 48¢ bid fills, conditions have typically worsened. This offsets part of the fee advantage.
For momentum signals (drift), timing matters — missed fill = missed signal. Real implementation risk.
**Tradeoff:** 75% fee savings vs fill uncertainty + adverse selection + implementation complexity.
**Assessment:** Net benefit unclear without simulation. Defer until after expansion gate.
**Unlock:** After expansion gate clears + simulation confirms net positive after adverse selection.
**DO NOT BUILD YET:** Log only.

---

## [CONFIRMED DEAD END] Polymarket.COM Sub-$1 Arbitrage (US Users Blocked)
**Added:** Session 48 (2026-03-11) via CoinDesk Feb 2026 research
**Finding:** A bot executed 8,894 trades on Polymarket 5-minute BTC/ETH markets where
YES+NO briefly summed to <$1 due to thin liquidity. Generated ~$150,000. ~$16.80/trade
at ~$1,000 deployed capital per round-trip.
**Why we cannot replicate:** Polymarket.COM is geo-restricted for US users. Our account is
Polymarket.US (sports-only). These were .COM 5-min crypto markets.
Within Kalshi alone, YES+NO always = exactly $1.00 — no internal arb possible.
**Status:** Permanently closed for our setup. Archived so we don't waste time revisiting.

---

## [PRIORITY — Session 50 finding] sol_drift direction_filter="no" — STRONG SIGNAL
**Discovered:** 2026-03-11 Session 50 directional analysis

**Data (19 settled live bets):**
- YES bets: 9 bets, 5/9 wins (55.6%), P&L +0.04 USD (barely breakeven)
- NO bets:  10 bets, 10/10 wins (100%), P&L +5.84 USD (ALL profits from NO side)

**Statistical significance:**
- P(10/10 NO wins if 50-50) = (0.5)^10 = 0.001 — extraordinary
- Pattern mirrors btc_drift which got direction_filter="no" at Session 43 (20 YES, 23 NO, p=3.7%)
- SOL evidence is STRONGER statistically than btc_drift was at filter decision time

**Hypothesis:** SOL's downward drift predicts NO outcomes reliably; upward drift is noisy
(higher volatility, more mean-reversion on up-moves than down-moves for SOL)

**Action needed (NOT autonomous — requires Matthew sign-off):**
- Apply direction_filter="no" to sol_drift_v1 in main.py (2-line change, identical to btc_drift)
- Wait until 15+ YES bets for fuller data, OR decide now given extraordinary evidence
- If filter applied: after 30 NO-only settled bets, re-evaluate same as btc_drift protocol

**Precedent:** btc_drift direction_filter="no" changed main.py line only:
  `trading_loop(strategy=sol_strategy, ..., direction_filter="no")`

**XRP drift note (opposite pattern):**
- YES: 1/1 (100%), NO: 0/5 (0%) — XRP seems to do opposite of sol
- Too few bets (6 total) to conclude. Document only, do not act yet.
- Likely mean-reversion pattern already noted in CLAUDE.md gotchas.

**Gate:** 19/30 bets. Wait for Matthew's explicit authorization before implementing.


---

## [ ] KXCPI strategy — RESEARCH NOTE (Session 50, 2026-03-11)
**Current KXCPI market state (pulled from Kalshi API 14:15 UTC):**
- 30 open KXCPI markets total across 5 CPI dates
- KXCPI-26MAR: 5 markets, total vol=2229 (best near-term volume)
- KXCPI-26NOV: 7 markets, total vol=1590
- Volume per market is low (52-965) — suitable for paper, borderline for live

**Cleveland Fed Nowcast (2026-03-11):**
- March 2026 MoM CPI: 0.47% (YoY: 2.87%)
- Core CPI MoM: 0.20%

**Potential edge detected:**
- KXCPI-26MAR-T0.6 (Will March MoM >= 0.6%?): YES=40c
- With Nowcast at 0.47% and typical uncertainty ~0.15%: P(CPI >= 0.6%) ≈ 19%
- Market is pricing 40% → OVERPRICED YES side → potential NO edge
- If edge is real: BET NO on KXCPI-26MAR-T0.6 (currently 60c NO bid)

**Why not build now:**
- Expansion gate IS technically open (btc_drift 49 bets, Brier 0.252)
- But "when Matthew has bandwidth" per Session 49 handoff
- Requires: FRED/Nowcast data feed integration, CPI series parser, new strategy file
- Timeline: ~3-4 hours to build + test. March CPI closes April 10-11. 30 days.
- Recommended: discuss with Matthew, then build if desired

**Data source:** Cleveland Fed Nowcast updates daily at https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting

