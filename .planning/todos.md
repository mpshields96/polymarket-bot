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
