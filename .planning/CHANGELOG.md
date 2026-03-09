# POLYMARKET-BOT CHANGELOG
# Permanent session-by-session log. NEVER TRUNCATE OLD ENTRIES.
# ALL future Claude sessions MUST append their changes here at session end.
# This file is the authoritative record of what changed, why, and when.
# Format: ## Session N — YYYY-MM-DD — [theme]
#          ### Changed: list of files + what changed
#          ### Why: rationale (especially for parameter changes)
#          ### Lessons learned (optional)
# ══════════════════════════════════════════════════════════════

## Session 1–16 — 2025 — Foundation build
### Changed: Full system built from scratch
- src/auth/kalshi_auth.py — RSA-PSS signing
- src/platforms/kalshi.py — REST client
- src/data/binance.py — BTC/ETH/SOL feeds (Binance.US only)
- src/strategies/btc_lag.py — 4-gate momentum strategy
- src/strategies/btc_drift.py — sigmoid probability model
- src/risk/kill_switch.py — all hard stops (synchronous)
- src/risk/sizing.py — Kelly + stage caps
- src/execution/paper.py, live.py — paper + live executors
- src/db.py — SQLite trades/bankroll/events
- src/dashboard.py — Streamlit UI
### Why: Initial system. All strategies paper-only until statistical edge confirmed.

---

## Session 17–22 — 2026-01 — Live trading launch + bug fixes
### Changed
- main.py — btc_lag, eth_lag, btc_drift enabled live (all demoted back to paper by Session 26-27)
- 3 critical bugs fixed (Session 20):
  1. strategy_name hardcoded "btc_lag" in live.py — now passed as strategy.name
  2. kalshi_payout() given NO price instead of YES price for NO-side bets
  3. _FIRST_RUN_CONFIRMED module global triggered double-CONFIRM on restart
- src/risk/kill_switch.py — consecutive_loss_limit=4, daily_loss_limit=20%
- src/risk/sizing.py — min_edge_pct must be passed to calculate_size() (default 8% dropped btc_lag 4% signals)
### Why: Live trading exposed silent bugs with zero test coverage. See CLAUDE.md Gotchas.

---

## Session 23 — 2026-01 — Sol lag + paper-during-softkill
### Changed
- src/strategies/sol_lag_v1.py — KXSOL15M, Binance.US SOL feed, min_move=0.8%
- main.py — sol_lag_loop wired
- src/risk/kill_switch.py — check_paper_order_allowed() added (soft stops skip paper)
- src/db.py — daily_live_loss_usd(), restore_daily_loss() — counter persists across restarts
- main.py — restore_daily_loss() seeded on startup
### Why: Daily loss counter reset to 0 on restart, bypassing daily limit. Paper bets should continue during soft kills to keep data flowing.

---

## Session 24 — 2026-01 — Lifetime loss persist + asyncio race fix
### Changed
- src/db.py — all_time_live_loss_usd() — net P&L basis (not gross)
- src/risk/kill_switch.py — restore_realized_loss() persists lifetime loss counter across restarts
- main.py — asyncio.Lock (_live_trade_lock) wraps check→execute→record atomically across all live loops
### Why: Two live loops could both pass check_order_allowed() before either called record_trade(), exceeding hourly limit by 1. Lock fixes race.

---

## Session 25 — 2026-02 — Consecutive loss persist + price guard + threshold raise
### Changed
- src/db.py — current_live_consecutive_losses() — walks settled trades newest-first
- src/risk/kill_switch.py — restore_consecutive_losses(n), seeds on startup, fires 2hr cooling if n >= 4
- src/strategies/btc_drift.py, btc_lag.py, orderbook_imbalance.py — _MIN_SIGNAL_PRICE_CENTS=35, _MAX_SIGNAL_PRICE_CENTS=65 (price range guard)
- config.yaml — btc_drift: min_edge_pct 0.05→0.08, min_drift_pct 0.05→0.10 (PREMATURE — see Session 35)
### Why (threshold raise): Only ~12 live trades at time of tightening. VIOLATED PRINCIPLES.md standard of 30+ data points. This was a statistical-outcome reaction, not a mechanical defect fix.
### Lesson: The Session 25 threshold tightening was itself done without the required 30 data points. By PRINCIPLES.md, it should not have been made. Do NOT re-tighten until 30+ live settled bets + Brier score computed.

---

## Session 26–27 — 2026-02 — Demotion + backtest framework
### Changed
- main.py — btc_lag, eth_lag, btc_drift all demoted from live to paper
- src/backtesting/ — real backtest framework built
### Why: HFTs matured — Kalshi prices now move same minute as BTC price moves. btc_lag Brier=0.191 (strong model) but ~0 signals/week. Market too efficient for lag strategies. btc_drift demoted for calibration reset.

---

## Session 28 — 2026-02 — Polymarket Phase 5.1
### Changed
- src/auth/polymarket_auth.py — Ed25519 signing for polymarket.US
- src/platforms/polymarket.py — REST client for api.polymarket.us/v1
- setup/verify.py — +12 Polymarket auth + connectivity checks
### Why: Polymarket.US is sports-only (NBA/NFL/NHL/NCAA). No crypto markets on .us. Ed25519 auth confirmed working.
### Architecture FINAL: Matthew is US-based iOS user → polymarket.US only. polymarket.COM is geo-restricted for US users (no VPN, no .COM needed). Do NOT revisit unless Matthew explicitly opens that door.

---

## Session 29 — 2026-02 — Polymarket Phase 5.2 (copy trading + sports futures)
### Changed
- src/strategies/copy_trader_v1.py — 6 decoy filters, Signal generation (29 tests)
- src/strategies/sports_futures_v1.py — bookmaker consensus mispricing (25 tests)
- main.py — copy_trade_loop and sports_futures_loop wired
### Why: Copy trading is PRIMARY goal. Sports futures is supplemental only insofar as it supports copy trading mission.

---

## Session 30 — 2026-02 — predicting.top API bugs fixed
### Changed
- src/data/predicting_top.py — two API response shape bugs fixed (wrapper + smart_score nesting)
### Why: predicting.top changed response format without notice (already happened twice). Added assertion on len(whales) > 0 after load.

---

## Session 31 — 2026-02 — btc_drift micro-live + $233 anomaly fix
### Changed
- main.py — btc_drift promoted to micro-live (calibration_max_usd=0.01 → always 1 contract ~$0.35-0.65)
- src/strategies/orderbook_imbalance.py — added 35-65¢ price range guard (was MISSING, caused $233 phantom paper P&L)
- config.yaml — paper_slippage_ticks 1→2
### Why: orderbook_imbalance bet NO@2¢ (extrapolating far from calibration range). Price guard prevents this on ALL strategies. Micro-live: 1 real contract/bet collects Brier data without meaningful financial risk.

---

## Session 32 — 2026-02 — Paper calibration fixes + architecture finalized
### Changed
- config.yaml — paper_slippage_ticks 2→3, paper_fill_probability=0.85
- src/db.py — signal_price_cents column added (pre-slippage price for calibration analysis)
- CLAUDE.md + MEMORY.md — Loading screen tip rule added (mandatory end-of-response format)
### Why: Paper P&L was optimistically biased — 2¢ slippage and 100% fill are too optimistic vs real 2-3¢ spread + 15% no-fill rate. Fixed to match observed Kalshi BTC market conditions.

---

## Session 33 — 2026-03 — CryptoDailyStrategy + quota guard
### Changed
- src/strategies/crypto_daily.py — KXBTCD/KXETHD/KXSOLD hourly slots (30 tests)
- main.py — 3 daily loops wired (btc_daily, eth_daily, sol_daily)
- src/data/odds_api.py — _QuotaGuard, 500/mo cap, persisted to data/sdata_quota.json
- config.yaml — btc_drift max_daily_bets 3→20 (calibration speed-up)
- main.py — ODDS_API_KEY → SDATA_KEY (vendor name removed from code)
### Why: Sports data feed has 500 credit/month hard cap. _QuotaGuard enforces it automatically.

---

## Session 34 — 2026-03 — POST /v1/orders confirmed + lifetime stop removed
### Changed
- src/platforms/polymarket.py — place_order() implemented (OrderIntent, TimeInForce, PolymarketOrderResult)
- config.yaml — btc_drift max_daily_bets: unlimited (removed 20/day cap)
- src/risk/kill_switch.py — 30% lifetime hard stop REMOVED. _realized_loss_usd is display-only.
- src/strategies/copy_trader_v1.py — check_paper_order_allowed() bug fixed (no-args TypeError)
### Why: POST /v1/orders JSON format confirmed: {marketSlug, intent, type, price:{value,currency}, quantity, tif}. Response: {"id": "...", "executions": []}. is_filled = len(executions) > 0. Lifetime hard stop removed — daily limit (20%) + $20 bankroll floor are the governors.
### Critical finding: predicting.top whales trade on polymarket.COM (politics/crypto/culture). Our account is polymarket.US (sports-only). 0 whale signals match .US markets. STRATEGIC DECISION NEEDED.

---

## Session 35 — 2026-03 — Kill switch lessons + --health command + sports min_books
### Changed
- main.py — --health diagnostic command (6 sections: kill switch state, last live bet + elapsed, open trades, bot PID, SDATA quota, recent events)
- main.py — no-live-bets watchdog (WARNING at 24hr, CRITICAL at 72hr, max once/hr per live loop)
- src/strategies/sports_futures_v1.py — min_books: int = 2 parameter (filter 1-source signals)
- tests/test_sports_futures.py — 4 regression tests for min_books filter
- KILL_SWITCH_LESSONS.md — CREATED: lessons from the 7-day silent kill switch episode (Lesson 1-7)
### Why: Bot was silently blocked by a stale kill switch for 7 days with no external indicator. --health surfaces all known silent failure modes. min_books=2 prevents low-confidence 1-bookmaker signals from reaching paper/live paths.
### Lesson: KILL_SWITCH_LESSONS.md documents every pattern of silent failure found in this system. Read it before investigating "why are there no live bets?"

---

## Session 36 — 2026-03-08 — btc_drift threshold restore + eth_drift micro-live + CHANGELOG created
### Changed
- config.yaml — btc_drift: min_drift_pct 0.10→0.05, min_edge_pct 0.08→0.05 (RESTORED to original Session 22 values)
- main.py — eth_drift: live_executor_enabled=False → live_mode (micro-live enabled)
- main.py — eth_drift: max_daily_bets=0, trade_lock=_live_trade_lock, calibration_max_usd=_DRIFT_CALIBRATION_CAP_USD
- .planning/CHANGELOG.md — CREATED (this file). Permanent session log per Matthew's standing directive.
- CLAUDE.md — updated test count, project state, gotchas
- PRINCIPLES.md — note added about Session 25 threshold raise being a PRINCIPLES.md violation
- SESSION_HANDOFF.md — updated for session 36
### Why (threshold restore): Session 25 raised btc_drift thresholds from 0.05/0.05 → 0.10/0.08. This was done with only ~12 live trades, violating PRINCIPLES.md's own 30-data-point standard. The result: 1 live bet/day, making calibration take weeks instead of days. Signals with 5-8% edge were firing in logs but being rejected by the 8% floor. Math: at 0.05% drift with sensitivity=800 → raw_prob≈0.599 → edge≈8.1% YES edge. Restoring original thresholds → ~8-15 signals/day, reaching 30 bets in 2-4 days.
### Why (eth_drift live): btc_drift already has 12/30 live bets. eth_drift has 62+ paper trades at the SAME thresholds (0.05/0.05). Adding eth_drift micro-live doubles data collection rate. Same 1-contract cap (~$0.35-0.65/bet). Both strategies governed by shared daily loss limit.
### Test count: 869/869

---

## Session 36 (cont) — 2026-03-08 — sol_drift_v1 micro-live added
### Changed
- src/strategies/btc_drift.py: load_sol_drift_from_config() added
- main.py: sol_drift_task wired — live_mode, calibration_max_usd=0.01, trade_lock shared, stagger 29s
- config.yaml: sol_drift section — min_drift_pct=0.15 (3x btc_drift), min_edge_pct=0.05, sensitivity=800
- btc_imbalance stagger shifted 29s→36s to make room
### Why: Three concurrent drift loops (BTC+ETH+SOL) maximize calibration data rate at minimal financial risk ($0.35-0.65/bet). SOL ~3x more volatile than BTC → min_drift_pct scaled 3x (0.15%) to maintain same edge quality bar. Combined expected signal rate: 15-25/day.
### Test count: 869/869 | Commit: 11ff825

---

## Session 36 (cont2) — 2026-03-09 — KALSHI_MARKETS.md full live re-probe
### Changed
- .planning/KALSHI_MARKETS.md — COMPLETE REWRITE based on live API probe
  - All series confirmed/denied via get_markets() against trading-api.kalshi.com
  - NEW categories added: Player Props (KXNBAPTS/AST/REB/3PT/2D/3D, KXNHLPTS/AST)
  - NEW categories added: MLB game winners (KXMLBGAME), Parlays (KXMVE*), Oscars (KXMVEOSCARS)
  - Volume data added for every series (BTC15M=103k, ETH15M=9.4k, SOL15M=4.2k, XRP15M=5.9k)
  - KXXRPD confirmed exists (but near-zero volume)
  - KXBNB15M, KXBCH15M, KXBNBD, KXBCHD all confirmed inactive (no open markets)
  - KXCPI confirmed exists (~1,400 volume)
  - Expansion roadmap added: XRP drift → game winners → KXNBA3D → CPI → MLB season
### Why: Session 36 re-probe revealed 5 entire market categories previously unknown to bot:
  player props (6 series), MLB game winners, parlay markets (KXMVE*), Oscars, CPI confirmation.
  Matthew's standing directive: stop steering with a blindfold — complete market knowledge required.
  All future sessions must read KALSHI_MARKETS.md before any strategy work.

---

## Session 36 (cont3) — 2026-03-09 — report bug fix + ecosystem research + docs hardened
### Changed
- main.py print_report(): fixed is_paper classification bug.
  Was: "🔴 if ANY of today's bets for this strategy are live" — mixing pre/post-restart bets.
  Now: groups by (strategy, is_paper) pairs. Two rows on transition days (📋 + 🔴). Correct.
  Old data always preserved. is_paper column on each trade = permanent source of truth.
- CLAUDE.md Gotchas: Kalshi copy trading note expanded with API doc evidence + third-party platforms
- CLAUDE.md Gotchas: --report split-row behavior documented so future chats never misread report
- CLAUDE.md Current state: rewritten for 3 live drift loops, report fix, Session 36 research
- MEMORY.md: Complete rewrite (was 217 lines, over limit, multiple stale facts). Now:
  mandatory reading order, Kalshi market ecosystem, copy trading research, report fix behavior
- Kalshi copy trading research (Session 36): Confirmed via API docs that public endpoints return
  zero trader attribution. Third-party platforms (Duel.trade, FORCASTR, kalshitradingbot.net) exist
  but source unknown. All GitHub Kalshi bots use statistical edge. Closed permanently.
### Why (report bug): P&L and bet counts were misleading on strategy-transition days.
  Fixed so live history and paper history are always cleanly separated and accurate.
### Why (MEMORY.md rewrite): Future chats must never need to re-research what's been confirmed.
  Every session must update MEMORY.md if anything changed. 200-line limit enforced.
### Test count: 869/869

---

## Session 36 (cont4) — 2026-03-09 — session close-out: GSD health + todos + verification
### Changed
- .planning/ROADMAP.md: added Phase 04.2 entry under Phases 1-4 COMPLETE block.
  GSD tool expected `## Phase NN.N:` heading with colon — parseInt("04.2")=4 bug in GSD verify.cjs,
  worked around by using exact `### Phase 04.2:` format so roadmapPhases.has("04.2") = true.
- .planning/todos/completed/: moved 2 stale 2026-02-28 todos (slippage model, settlement verify).
  Both were completed in Sessions 31+35. Pending queue is now empty.
### Why: GSD health W007 was the only degraded signal at session start. Fixed so future sessions
  start clean. Stale todos removed to prevent confusion about actual pending work.
### Verification evidence
- 869/869 tests: CONFIRMED PASSING (python3 -m pytest tests/ -q → 869 passed in 2.24s)
- GSD health: HEALTHY (0 errors, 0 warnings, 0 info)
- Bot PID 74462: RUNNING (kill -0 confirmed)
- Today's P&L: +$3.68 (live: +$2.32, paper: +$1.36). All-time live: -$16.53 (improving).
- btc_drift live settled: 12/30. eth_drift live: ~3. sol_drift live: ~2.
### Test count: 869/869 | Commit: e904715

---

## Session 37 (autonomous) — 2026-03-09/10 — overnight monitoring + bug discovery
### Changed
- SESSION_HANDOFF.md: updated btc_drift live settled count from 12 to 22 (accurate as of 00:30 CDT).
  Also documented graduation_stats() bug discovered during audit.
### Bug discovered (NOT FIXED — needs Matthew's review next session)
- graduation_stats() in src/db.py only queries is_paper=1. For live strategies (btc_drift, eth_drift,
  sol_drift), this means --graduation-status shows paper bet counts, not live bet counts.
- Actual live settled counts: btc_drift=22/30, eth_drift=4, sol_drift=3.
- --graduation-status incorrectly showed btc_drift at 12/30.
- Fix needed: add is_paper param to graduation_stats(), update print_graduation_status() to
  use is_paper=False for live strategies. Reporting bug only — no trading impact.
### Observations (no code changes)
- Bot healthy: PID 74462 running, kill switch clean, daily loss 6%, last live bet 4 min before session start.
- All 3 drift loops evaluating every 30s, price guard correctly skipping near-expiry markets (3-15¢).
- 869/869 tests: CONFIRMED PASSING (autonomous verification)
- sports_futures_v1: 54 paper bets placed, 0 settled — expected (non-KX tickers, settlement loop ignores them)
### Test count: 869/869 | No new commits (docs update only)

---

## Session 37 (autonomous, cont) — 2026-03-10 02:09 CDT — SHUTDOWN + MILESTONE
### Milestone reached
- btc_drift_v1: 30 live settled bets. Brier = 0.2526 (computed from live trades, win_prob all present).
  Brier < 0.30 threshold MET. Trade count gate MET.
  EXPANSION GATE still CLOSED: 2 criteria unmet:
    (1) 2-3 weeks live P&L data (currently ~1 day)
    (2) No kill switch events — soft stop fired 01:49 CDT (5 consecutive losses, 2hr cooling)
  Matthew must review these before enabling XRP drift or Stage 2 promotion.
### Kill switch event
- 01:49 CDT soft stop fired: 5 consecutive losses → 2hr cooling. Correct behavior, left alone.
  Daily loss at shutdown: $3.60/$16.70 (22% of limit — safe).
  Hard stop: CLEAR. Cooling expires 03:49 CDT.
### Overnight monitoring summary
- Bot ran cleanly 23:23 CDT - 02:09 CDT (shutdown). 3 live loops active throughout.
- Total live bets placed overnight: ~14 (btc), ~13 (eth), ~8 (sol) drift bets across session.
- Price guard observation: sol_drift + btc_drift occasionally placing bets 1-4¢ outside 35-65¢ range.
  Pattern: signal generated at valid price, market moves ~1-4¢ during asyncio queue delay.
  Not a risk issue at $0.33-0.66 bet sizes. Worth Matthew's review for code robustness.
- sports_futures_v1: 97 paper bets, 0 settled (expected — non-KX tickers, settlement loop ignores)
- 869/869 tests: CONFIRMED PASSING
### Changed
- SESSION_HANDOFF.md: complete rewrite of P&L section + expansion gate status table + kill switch state
- .planning/CHANGELOG.md: this entry
### Test count: 869/869

---

## Session 37 — Autonomous Window 2 (2026-03-09 08:24–09:22 CDT)
### Context
65-minute autonomous monitoring window while Matthew at clinic. Bot restarted PID 90027 at session start.
No code changes permitted (autonomous mode rules). Two todos filed, one git cleanup done.

### Events
- **Kill switch soft stop fired at 09:04 CDT** — 4 consecutive losses, 2hr cooling.
  Correct behavior. Bot remained running; paper loops unaffected. Soft stop expires ~11:02 CDT.
- **sol_drift valid signal blocked at 09:21 CDT** — BUY YES @57¢, edge=8.7%.
  Kill switch correctly blocked it during cooling period. Price would have been in range.
- **No code errors** — all loops evaluating normally throughout session.

### Bugs documented (NOT fixed — await conscious session)
1. **live.py execution-time price guard (HIGH PRIORITY)**
   - Signal at 59¢ filled at 84¢ in prior window (asyncio latency + HFT repricing)
   - Todo filed: .planning/todos/pending/2026-03-10-add-execution-time-price-guard-to-live-executor.md
2. **graduation_stats() is_paper=1 hardcoded (LOW)**
   - --graduation-status shows paper counts for live strategies (reporting-only bug)
   - Todo filed: .planning/todos/pending/2026-03-09-fix-graduation-stats-to-query-live-bets-for-live-strategies.md

### Git cleanup
- Staged deletion of stale pending/ todo files (moved to completed/ in Session 36 but not committed):
  - .planning/todos/pending/2026-02-28-add-slippage-model-to-paper-executor.md
  - .planning/todos/pending/2026-02-28-verify-settlement-result-from-kalshi-api-directly.md

### P&L at window close
- Today live: +$2.73 | All-time live: -$16.12
- btc_drift 11/18 (61%), eth_drift 10/17 (59%), sol_drift 8/10 (80%)
- btc_drift: 30 live settled ✅ | Brier: 0.2526 ✅ | Expansion gate: still CLOSED (2 criteria unmet)

### State at close
- Bot: RUNNING PID 90027 | Kill switch: soft stop active until ~11:02 CDT
- Daily loss: $6.30/$16.44 (38%) | Hard stop: CLEAR

### Test count: 869/869

---

## Session 38 — 2026-03-09 (home restart + security fixes)
### Context
Matthew returned home from work. Work wifi caused Kalshi + Binance disconnects at ~16:44 CDT
(bot recovered automatically). Clean restart on home wifi to fresh session38 log.

### Changed
1. **sports_futures_v1.py: logging ValueError fix**
   - `%.1%%` → `%.1f%%` in two logger.info calls (lines 332, 355)
   - Was: `ValueError: unsupported format character '%'` every time a NO/YES signal was skipped
   - Spamming the log but not crashing the bot. Commit: b6e32ae

2. **live.py: canceled order guard (security fix — Session 37 sc:analyze finding)**
   - Added `if order.status == "canceled": log warning + return None` before `db.save_trade()`
   - Kalshi returns status="canceled" when no liquidity or market closes mid-execution
   - Was: canceled orders recorded as real live bets → corrupted calibration + graduation counters
   - Now: phantom trades never reach DB. "resting" status (GTC orders) still recorded normally.
   - 2 new tests in TestExecuteOrderStatusGuard. Commits: 6127cea (RED), 9009fa8 (GREEN)

3. **CLAUDE.md Gotchas section: updated**
   - Stale "live.py has ZERO unit tests" → corrected to reflect TestExecutionPriceGuard + TestExecuteOrderStatusGuard
   - Added bullet documenting the canceled order guard and regression tests

4. **Autonomous session todos filed:**
   - SKILLS_REFERENCE.md created (.planning/SKILLS_REFERENCE.md) — full skill/command map
   - Todo: update POLYBOT_INIT.md with sc:analyze findings + SKILLS_REFERENCE.md
   - Todo: monitor btc_drift YES vs NO win rate asymmetry (BUY YES 35.7% vs BUY NO 55%)
   - gsd:add-todo workflow used for both captures

### P&L at session close
- Bankroll: ~$84.33 | All-time live: -$13.99
- Kill switch: CLEAR — daily $6.30/$20 (32%), consecutive 0/4, hard stop CLEAR
- Live bet confirmed: trade_id=446 btc_drift YES@36¢ (status=executed)
- Paper bets confirmed: sports_futures placed trade_ids 443-445 (NBA/NHL futures)

### Expansion gate
STILL CLOSED. Two criteria unmet: (1) 2-3 weeks live data, (2) no kill switch events.
Do not build XRP drift yet.

### Pending todos (3):
1. LOW — graduation_stats() shows paper counts for live strategies
2. MONITOR — btc_drift YES vs NO win rate asymmetry (re-evaluate after 30 more clean bets)
3. DOCS — Update POLYBOT_INIT.md with sc:analyze security findings + SKILLS_REFERENCE.md link

### Test count: 882/882 | Bot: PID 96757, log /tmp/polybot_session38.log

## Session 38 — Close-out (2026-03-09 ~18:00 CDT)

### graduation_stats() is_paper param fix
- WHY: --graduation-status was showing paper bet counts for live strategies
  (btc_drift showed 12, was querying all trades including is_paper=1)
- FIX: graduation_stats(strategy, is_paper: Optional[bool] = True) in src/db.py
  Both SQL queries now add WHERE is_paper = ? when is_paper is not None
- CALLERS UPDATED: print_graduation_status() in main.py passes is_paper=False for live strategies
  _LIVE_STRATEGIES = {"btc_drift_v1", "eth_drift_v1", "sol_drift_v1"} in setup/verify.py
- sol_drift_v1 ADDED to _GRAD (was missing entirely since Session 36 — never tracked)
- RESULT: btc_drift 12→37 ✅, eth_drift 0→19, sol_drift not tracked→11
- Tests: 5 new tests (TestGraduationStatsIsPaperParam). Commit: 2fab9e6, 82c90c7

### POLYBOT_INIT.md full update (Session 31 → Session 38)
- WHY: CURRENT STATUS was 7 sessions out of date (758 tests, old PID, wrong strategies, stale P&L)
- WHAT: Full rewrite of CURRENT STATUS section with accurate Session 38 state
  + Autonomous ops guide (monitoring protocol, development work, security rules, tools cheatsheet)
  + KXBTCD hourly bets expansion roadmap entry
  + SKILLS_REFERENCE.md reference added to mandatory reading
  + Gotcha #24 (live.py security findings) + Gotcha #25 (SKILLS_REFERENCE link) added
- MANDATORY FILES updated: SESSION_HANDOFF.md, CHANGELOG.md, KALSHI_MARKETS.md, MEMORY.md

### KALSHI_MARKETS.md — major taxonomy expansion
- WHY: Matthew's kalshi.com Crypto tab screenshot confirmed MULTIPLE undocumented categories:
  Hourly (8), Weekly (8), Monthly (11), Annual (8), One Time (14) — with $14.8M volume on
  single "When will Bitcoin hit $150k?" market. DOGE markets (6) never documented.
- WHAT: Added Categories 2B/2C/2D/2E (Weekly/Monthly/Annual/One-Time crypto price markets)
  Added DOGE to Category 2A table
  Updated expansion roadmap with Tier 1/2/3 structure
  Added RESEARCH DIRECTIVES section with API probe commands + Reddit/GitHub search tasks
- WHY MATTERS: We have been building strategies for $103K/window markets while ignoring
  $14.8M markets. Research directives mandatory for new sessions.
- Full Kalshi top-nav categories documented as undocumented: Politics, Culture, Climate,
  Economics, Mentions, Companies, Financials, Tech & Science

### P&L at session close
- Bankroll: ~$84.33 | All-time live: -$13.37 | P&L today (live): +$5.48 (winning day!)
- btc_drift 14/21 wins, eth_drift 12/19 wins, sol_drift 9/11 wins
- Kill switch: CLEAR — daily $6.30/$16.88 (37%), consecutive 0/4
- SDATA: 53/500 (11%)

### Expansion gate
STILL CLOSED. Two criteria unmet: (1) 2-3 weeks live data, (2) no kill switch events.
Next expansion = KXXRP15M drift after gate opens.

### Pending todos (0): All cleared this session.

### Test count: 887/887 | Bot: PID 96757, log /tmp/polybot_session38.log

---

## Session 39 — 2026-03-09 ~17:00–19:00 CDT (autonomous, Matthew washing dishes/mowing)

### Context
Fully autonomous 2-hour session. Matthew left. Bot was running PID 96757. Three micro-live
drift loops active (btc/eth/sol). Three paper daily loops active (KXBTCD/KXETHD/KXSOLD).

### Changed

1. **.planning/AUTONOMOUS_CHARTER.md — CREATED (new file)**
   - WHY: Matthew's explicit demand — exhausted re-explaining autonomous operation requirements
     to every new Claude chat session. "For the love of fucking god, document this."
   - WHAT: Complete permanent mandate for ALL new chats:
     * Full autonomous operation rules (never ask, never pause, work first then summarize)
     * 2-hour autonomous window protocol (monitor every 15 min, log to /tmp)
     * Market research protocol — REDDIT/GITHUB VERIFY BEFORE BUILDING ANYTHING
     * Tool usage rules (Free/Low/Expensive tiers, 75% token budget cap)
     * Expansion gate details, bot architecture snapshot, critical gotchas
     * Monitoring cycle log format, context handoff protocol
     * ACKNOWLEDGMENT REQUIREMENT: all new sessions must confirm receipt
   - ADDED TO: SESSION_HANDOFF.md mandatory reading list (STEP 1 position 2)
   - ADDED TO: MEMORY.md (AUTONOMOUS_CHARTER.md section at top of preferences)

2. **.planning/KALSHI_MARKETS.md — major addition (Session 39 API probe findings)**
   - WHY: Multiple undocumented series confirmed via Kalshi API + events endpoint + website research
   - WHAT added:
     * KXBTCATH ("When will Bitcoin hit a new ATH?"): Series confirmed on Kalshi website.
       0 open markets via API — likely resolved YES when BTC hit $109k in Jan 2026.
       Action: Monitor monthly for new markets opening.
     * KXBTCMAX100 current pricing (BTC ~$84k): DEC 2026 at 38¢, SEP at 27¢, MAY at 14¢
     * KXBTCMAXY current pricing: $100k threshold at 36¢ (7 markets, $2.2M vol)
     * KXBTCMINY current pricing: $40k floor at 35¢, $50k at 57¢ (market says 57% BTC dips below $50k)
     * KXBTCMAX150 current state: 4¢ on "BTC hits $150k by June" ($10.8M total open)
     * All discovery confirmed via asyncio Kalshi client + events endpoint pagination
   - CATEGORIES 2B/2C/2D/2E: no structural changes, data points updated with live pricing

3. **polybot-monitor scheduled task UPDATED (/.claude/scheduled-tasks/polybot-monitor/SKILL.md)**
   - WHY: Was pointing to session36.log (hardcoded), had stale test count (869 → 887),
     only tracked btc_drift graduation (missed eth_drift and sol_drift)
   - WHAT: Dynamically finds log (ls -t /tmp/polybot_session*.log | head -1),
     tracks all 3 drift loops, handles soft/hard stop distinction, 887 test count

4. **SESSION_HANDOFF.md — updated mid-session**
   - WHY: State was stale (Session 38 close-out, 5+ hours ago)
   - WHAT: Added AUTONOMOUS_CHARTER.md to mandatory reading list (STEP 1),
     updated KEY STATE (P&L, graduation counts, kill switch), Session 39 work summary
   - Correction: All-time live P&L now -$13.87 (was -$13.37)

5. **MEMORY.md — AUTONOMOUS_CHARTER.md reference added**
   - WHY: Memory is loaded into every session; charter location must be memorized
   - WHAT: New section at top of User Preferences: "AUTONOMOUS_CHARTER.md — MANDATORY READ"

### Investigation findings (no code changes)

6. **KXETH15M LIQUIDITY CRISIS IDENTIFIED — eth_drift slippage analysis**
   - Session 39 observation: 8+ slippage/guard rejections vs 2 successful placements since restart
   - Typical slippage pattern: signal 43-57¢ → execution 29-71¢ (14-18¢ move on single-contract order!)
   - Volume context: KXBTC15M ~103k contracts/window vs KXETH15M ~9.4k (11x difference)
   - KXSOL15M ~4.2k (25x less liquid than BTC) — similar rejection patterns
   - This is EXPECTED from volume differential, NOT a bug. Guards are protecting correctly.
   - Implication: eth_drift and sol_drift graduation will be SLOWER than btc_drift due to rejections.
     Many signals generated, few executed due to thin order books on small-cap 15-min markets.
   - Action taken: NONE — guards are working correctly. Documented for next session awareness.

7. **Daily loops confirmed ACTIVE (btc_daily/eth_daily/sol_daily)**
   - Were "silent" in log but confirmed paper bets ARE being placed:
     btc_daily: 5 paper bets today (2/5 wins, -$4.38), eth_daily: 4 paper bets (0/4, -$11.53)
   - Silence = all logging after session-open reset is at DEBUG level only (not INFO)
   - Debug how to view: grep -i "daily\|kxbtcd" /tmp/polybot_session*.log
   - eth_daily 0/4 (-$11.53) paper performance is poor but paper only — no action needed

8. **Reddit/GitHub research on KXBTCD hourly markets + barrier option strategies**
   - GitHub: Found multiple Kalshi BTC trading bots (Bh-Ayush/Kalshi-CryptoBot trades 15min+1hr,
     OctagonAI/kalshi-deep-trading-bot, ryanfrigo/kalshi-ai-trading-bot, arbitrage bots)
   - Key insight from GitHub: community consensus — edge requires information advantage over HFTs.
     Statistical edge (our current approach) is the correct path. Copy trading on Kalshi: impossible.
   - KXBTCMAX150 settlement: trimmed mean (top/bottom 20% removed) of BRTI 60-second windows.
     Any strategy needs to account for trimmed mean settlement, not spot price.
   - Reddit research: limited direct r/kalshi results (Reddit blocked WebFetch). WebSearch found
     confirmation that "hourly" category on Kalshi IS KXBTCD (24 daily slots) — same series.
     No separate KXBTC1H series. Matthew's "hourly bet types" = KXBTCD structure (already built).
   - Reddit/GitHub agent running in background for deeper research (may complete in next session)

### Kill switch event (historical, not new)
- HARD STOP from 2026-03-01 shows in --health log — this is a HISTORICAL event, not active
- Current status: CLEAR. Daily $7.23/$20 (36%), consecutive 2/4. Bot actively placing bets.

### P&L at session mid-point (18:35 CDT)
- Today live: +$4.98 (54 settled bets) | Paper: -$5.46
- btc_drift 38/30 ✅ Brier 0.247 | eth_drift 21/30 (9 more) | sol_drift 11/30 (19 more)
- Kill switch: CLEAR | consecutive 2/4 | daily $7.23/$20.00 (36%)
- All-time live P&L: -$13.87 | Bankroll: ~$83.35 est.

### Expansion gate
STILL CLOSED. Two criteria unmet: (1) 2-3 weeks live data, (2) no kill switch events in window.
Next expansion = KXXRP15M drift. Do NOT promote eth_orderbook_imbalance (paper READY, gate CLOSED).

### Pending todos (none filed this session — all work done inline)
AUTONOMOUS_CHARTER.md research todos are captured in the charter itself.

### Test count: 887/887 (unchanged — no code changes this session, docs only)
### Commits this session: None yet (docs only — will commit at session end)
