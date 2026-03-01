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
**Approach:** Compare Kalshi implied probability vs The-Odds-API moneyline (free tier, 500 req/month). If edge > 5%, bet the underpriced side.
**Files to create:** src/data/odds_api.py, src/strategies/sports_game.py, new loop in main.py
**Signal rate:** ~2 bets/day in NBA season, closes at tip-off (clean settlement)
**Data source:** https://the-odds-api.com/ (free tier covers NBA + NHL)
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
**Data source:** Odds API live scores feed (within current 20k/month budget)
**Estimated effort:** 1 session (extend existing skeleton)
**Unlock condition:** Enable sports_game_v1 first (30 live trades threshold + ODDS_API_KEY)

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

## [ ] Odds API Integration — Quota Guard + Kill Switch (FUTURE — next session)
**Added:** 2026-03-01 Session 22
**Context:** Matthew obtained The Odds API subscription (20,000 credits/month, renewed March 1 2026).
**Standing directives from Matthew:**
- **HARD CAP: 1,000 credits max for polymarket-bot** (5% of 20,000 monthly budget)
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
2. `OddsApiQuotaGuard`: tracks credits used, raises if > 1,000 credits
3. Config: `odds_api.max_monthly_credits: 1000` in config.yaml
4. Tests: test_odds_api.py with quota guard tests
5. Manual review of first 10 API responses before wiring into strategy
**API info:** https://the-odds-api.com/ | Key in .env as ODDS_API_KEY
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

## [ ] Kill Switch Event Log — Test Pollution Fix
**Added:** 2026-03-01 Session 22
**Issue:** `kill_switch._hard_stop()` writes to KILL_SWITCH_EVENT.log during pytest runs
- Tests that trigger the hard stop (record_loss × 3 → $30+ losses) write to the LIVE event log
- This creates misleading entries like "HARD STOP — $31 loss" that look like real trading events
- _write_blockers() correctly guards with `PYTEST_CURRENT_TEST` — but _hard_stop() does not
**Fix:** Add `if os.environ.get("PYTEST_CURRENT_TEST"): return` before writing to EVENT_LOG in _hard_stop()
Also: avoid writing kill_switch.lock during tests (conftest.py cleans it but better to skip)
**Priority:** Low — cosmetic issue, no trading impact
**Estimated effort:** 5 minutes + 1 test

---

## [ ] Sports Betting System — Entirely Separate Project
**Added:** 2026-03-01 Session 22
**Standing directive from Matthew:** Sports props / moneyline / spreads / totals are NOT for this bot.
- Entirely separate system from Kalshi/polymarket-bot
- Reference code: ~/ClaudeCode/agentic-sandbox-rd and titanium-v36 subdirectory
- Odds API (20,000 credits/month) is the primary data source for that system
- Do NOT mix sports betting logic into polymarket-bot
**What this means for polymarket-bot:**
- KXNBAGAME / KXNHLGAME market types: potentially still viable (these are prediction markets on game outcomes, not traditional sportsbook bets) — but Matthew wants a very solid argument before pursuing
- Required: Cite multiple r/algobetting + r/predictionmarkets + r/Kalshi posts showing comparable strategies work on prediction markets vs traditional sportsbooks
- Only pursue if Matthew explicitly approves after review of that research
**Decision gate:** Matthew must explicitly approve after research. Default is NO for sports on Kalshi bot.
