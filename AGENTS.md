# CLAUDE.md — polymarket-bot

## ══════════════════════════════════════════════════════════════
## THIS BOT HAS TWO COMPLETELY SEPARATE HALVES — NEVER CONFUSE THEM
## ══════════════════════════════════════════════════════════════
##
## HALF 1 — KALSHI BOT (systematic prediction market strategies)
##   Platform:   Kalshi (kalshi.com) — CFTC-regulated US exchange
##   Auth:       RSA-PSS (src/auth/kalshi_auth.py)
##   Strategies: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance,
##               eth_imbalance, weather, fomc, unemployment_rate, sol_lag
##   Approach:   Statistical signals (BTC price lag, sentiment, weather, macro)
##   Status:     btc_drift + eth_drift MICRO-LIVE (1 contract/bet ~$0.35-0.65).
##               All others paper-only (market maturation, HFTs price btc_lag same minute).
##   Goal:       30 live settled bets + Brier < 0.30 → Stage 2 promotion
##
## HALF 2 — POLYMARKET COPYTRADE BOT (PRIMARY GOAL)
##   Platform:   Polymarket.us (api.polymarket.us/v1) — CFTC-approved US iOS beta
##   Auth:       Ed25519 (src/auth/polymarket_auth.py)
##   PRIMARY:    Copy trading — follow top whale accounts from predicting.top,
##               filter decoy trades, copy genuine buys (src/strategies/copy_trader_v1.py)
##   SUPPLEMENTAL: Sports futures mispricing vs sharp bookmaker consensus
##               (src/strategies/sports_futures_v1.py) — only useful insofar as
##               it SUPPORTS or SUPPLEMENTS the copy trading mission
##   Whale data: data-api.polymarket.com (public, no auth) via whale_watcher.py
##   Whale list: predicting.top/api/leaderboard (public) via predicting_top.py
##   Status:     Paper-only — platform mismatch (whales trade .COM, account is .US)
##   Goal:       Live copy trading once platform mismatch resolved + 30 paper trades
##
## STANDING RULE: Any new Polymarket feature, strategy, or research task must
## directly serve the copy trading goal. If it doesn't help copy trades succeed,
## it is OUT OF SCOPE for this bot. Log it to .planning/todos.md and move on.
## ══════════════════════════════════════════════════════════════

## ══════════════════════════════════════════════════════════════
## CITATION INTEGRITY — HARD BLOCK (applies to ALL chats: polybot, CCA, general)
## ══════════════════════════════════════════════════════════════
## RULE: Never cite an academic source you have not verified.
## "Verified" means ONE of:
##   (a) Fetched directly — WebFetch on arXiv/SSRN/DOI URL returned real content
##   (b) Found via search — WebSearch returned the paper with title/authors/year matching
##   (c) Exists in the local codebase with a URL you can confirm
##
## HARD BLOCK — if you cannot do (a), (b), or (c):
##   DO NOT write the citation as fact.
##   Write: "[UNVERIFIED — do not treat as confirmed]" next to the source.
##   OR drop the citation entirely.
##
## This applies to: EDGE_RESEARCH_*.md, SELF_IMPROVEMENT_ROADMAP.md,
##   CHANGELOG.md, SESSION_HANDOFF.md, any .planning/ file, any response.
##
## Pattern to NEVER repeat:
##   WRONG: "Per Thaler & Ziemba (1988), the FLB exists because..."
##          (without having fetched or found the paper this session)
##   RIGHT: "Per Thaler & Ziemba (1988) [fetched: https://...] the FLB exists..."
##   RIGHT: "FLB mechanism — see Thaler & Ziemba (1988) [unverified — fetch before citing]"
##
## Violations = corrupt academic basis of trading decisions.
## Matthew's standing directive. Zero tolerance.
## ══════════════════════════════════════════════════════════════

## MANDATORY READING — BEFORE ANY STRATEGY OR RISK CHANGE
Read `.planning/PRINCIPLES.md` before modifying any strategy parameter,
kill switch threshold, or risk rule. It contains:
- The mechanical defect vs statistical outcome test
- Why paper bets continue during live soft stops
- The anti-bloat principle (no trauma-based rules)
- Graduation criteria and why they are mandatory
- When to change vs when to wait for data

Read `.planning/CHANGELOG.md` to understand what changed in every prior session
and WHY. Every session must append entries here. This is the authoritative record.

Read `.planning/KALSHI_MARKETS.md` before any strategy or series work — complete map
of every Kalshi series type (what exists, what doesn't, what's built vs planned).
Key fact: KXBTC1H does NOT exist. Hourly BTC bets are inside KXBTCD (24 slots/day).
CRITICAL — THREE DISTINCT KALSHI CRYPTO BET TYPES (Session 51 permanent — read .planning/KALSHI_MARKETS.md):
  TYPE 1 = 15-min DIRECTION: KXBTC15M "BTC price up in next 15 mins?" — UP or DOWN, no strike, 15-min. ALL LIVE.
  TYPE 2 = Hourly/Daily THRESHOLD: KXBTCD "Bitcoin price on Mar 11 at 5pm EDT?" — above/below $X today. PAPER.
  TYPE 3 = Weekly/Friday THRESHOLD: KXBTCD "Bitcoin price on Friday at 5pm EDT?" — same series, future Friday. NOT BUILT.
  WRONG: "15-min bets = hourly bets". WRONG: "KXBTCW exists for weekly bets". WRONG: "KXETHD has zero volume".
  CORRECT volumes (Session 51 live probe): KXBTCD 5pm=676K | KXBTCD Fri=770K | KXETHD 5pm=64K.

If you (Claude) are about to change a threshold, add a filter, or
adjust a parameter after a losing period — read PRINCIPLES.md first.

## Commands
`source venv/bin/activate && python -m pytest tests/ -v` - run tests (use python -m, not pytest directly)
`source venv/bin/activate && python setup/verify.py` - verify all connections before bot start
`python main.py --report` - today's P&L
`python main.py --reset-killswitch` - reset hard stop after reviewing KILL_SWITCH_EVENT.log

## Codex Cross-Chat Rule
- If Codex changes this repo, Codex must notify both CCA and Kalshi.
- Immediate path: send a CCA desktop queue note plus Kalshi relay note(s).
- Durable path: append the outcome to `/Users/matthewshields/Projects/ClaudeCodeAdvancements/CODEX_TO_CLAUDE.md`.
- Do not assume CCA or Kalshi will learn about the change indirectly later.
- If Codex identifies a concrete advancement tip while working here, Codex should execute or codify it in the same workstream when safe and in scope, not leave it as a suggestion-only footer.
- If Codex hardens or adds an operator-facing helper here, live-probe it before trusting it. Passing tests alone is not enough for startup gates, monitoring workflows, or wrap tooling.

## Architecture rules (non-negotiable)
- One file, one job. If the job has "and" in it, split it.
- No `await` in `src/risk/` — kill switch and sizing are strictly synchronous
- `kill_switch.check_order_allowed()` is the LAST gate before every LIVE order
- `kill_switch.check_paper_order_allowed()` is the LAST gate before every PAPER order (skips soft stops)
- Auth lives in `kalshi_auth.py` only — never inline signing anywhere else
- Never write files outside `/Users/matthewshields/Projects/polymarket-bot/`

## Development Workflow Protocol — FOLLOW THIS ORDER, EVERY TIME

This project handles real money. Three critical bugs were only discovered when live trading
went live in Session 20. They should have been caught before. This protocol prevents that.

### Step 1: Write the test FIRST (TDD — always)
- Before any implementation: write the failing test first
- If you can't write the test, you don't understand the requirement yet
- All 3 Session 20 live-trading bugs had ZERO test coverage

### Step 2: Implement to make tests pass. Nothing more.

### Step 3: Proactive debugging BEFORE running
After any implementation, trace every code path manually:
- What happens when this returns `None`? Does the caller handle it?
- Are there hardcoded values that should be dynamic? (`strategy="btc_lag"` was hardcoded — Session 20)
- Does each function receive the right type AND value? (`kalshi_payout()` got NO price for NO-side bets — Session 20)
- Are there module-level globals that interact with runtime state? (`_FIRST_RUN_CONFIRMED` double-CONFIRM — Session 20)
- Are paper vs live paths treated identically where they should differ? (kill switch counted paper losses — Session 20)

### Step 4: Integration test before going live on any new strategy
- Unit tests prove individual functions work
- Integration tests prove the FULL PATH works: signal → size → live.execute() → DB record
- `src/execution/live.py` currently has ZERO tests — highest priority debt to pay off
- Before enabling any new strategy for live: manually trace and test the complete path

### Step 5: Pre-live audit (mandatory before enabling any new live strategy)
Run through this checklist:
- [ ] kill_switch.check_order_allowed() called at every order path?
- [ ] settlement_loop calling record_win/record_loss for LIVE trades only?
- [ ] strategy_name passed correctly (not hardcoded)?
- [ ] Price conversion correct (YES price for kalshi_payout, not NO price)?
- [ ] DB save has correct is_paper flag?
- [ ] All parameters received by function from caller (no scope leakage from main())?
- [ ] sizing clamp applied? (trade_usd = min(size_result.recommended_usd, HARD_MAX_TRADE_USD))
- [ ] has_open_position() and count_trades_today() both pass is_paper= filter?
- [ ] _announce_live_bet() wired in for the new strategy's loop? (all live loops must call it)
- [ ] Live bets placed for the FIRST window after enabling — verify in log within 15 min of restart
- [ ] `--graduation-status` run after first live bet to confirm trade counter increments
- [ ] No silent blocking: watch log for "Kill switch blocked" or "exceeds hard cap" on first window

### Step 6: Post-bug retrospective (mandatory after fixing any bug)
- Write a regression test IMMEDIATELY that would have caught the bug
- Ask: "What other code has the same pattern?" — if bug is in one place, check sibling paths
- Add the pattern to CLAUDE.md Gotchas so it's never repeated
- Before closing: run `python -m pytest tests/ -v` and confirm new test catches the old bug

### Debugging protocol — systematic only
1. Reproduce minimally (smallest case showing the problem)
2. Read the code path top-to-bottom, don't guess
3. Form one hypothesis, confirm it with a targeted log/print before touching code
4. Fix exactly what's broken, nothing more
5. Write a test that FAILS before fix, PASSES after
6. Check sibling code for the same bug pattern

DO NOT: add more logging and re-run hoping to see something different
DO NOT: try multiple fixes simultaneously
DO NOT: fix symptoms without finding root cause

## Gotchas
- Run git operations sequentially with `&&` — parallel git calls cause index.lock races
- `test_security.py` excludes itself from the dangerous-paths scan (it contains them as test data)
- Bankroll floor check must run BEFORE pct cap check in `check_order_allowed()`
- `LIVE_TRADING=true` in .env AND `--live` at CLI — both required for live mode
- **Binance.com is geo-blocked in the US (HTTP 451)** — always use `wss://stream.binance.us:9443`
- Binance.US WebSocket can be silent for 10-30s; `recv` timeout must be ≥30s
- Kalshi API Key ID = short UUID at kalshi.com → Settings → API (NOT the .pem file contents)
- `db.win_rate()` must compare `result == side` (not `result == "yes"`) — NO-side bets win when result=="no"
- `kill_switch.lock` reset requires piping: `echo "RESET" | python main.py --reset-killswitch`
- `config.yaml` must have sections: kalshi, strategy, risk, **storage** (verify.py checks all four)
- `WeatherFeed.refresh()` is a synchronous HTTPS call (~100ms) to api.open-meteo.com — no key needed
- Kalshi HIGHNY markets only exist on weekdays; weather_loop logs "No open HIGHNY markets" on weekends
- `config.yaml` series ticker must be `KXBTC15M` (not `btc_15min`) — wrong value returns 0 markets silently at DEBUG
- All `generate_signal()` skip paths log at DEBUG — trading loop appears silent when no signal fires (expected)
- **Binance.US `@trade` stream has near-zero BTC volume** — always use `@bookTicker` (mid-price = (bid+ask)/2, ~100 ticks/min)
- `tests/conftest.py` auto-cleans `kill_switch.lock` at session start/end — after interrupted test runs the lock won't block `main.py`
- `kill_switch._write_blockers()` skips BLOCKERS.md write when `PYTEST_CURRENT_TEST` env var is set — prevents test runs from polluting BLOCKERS.md
- Never run diagnostic scripts in background without an explicit kill after N seconds — unattended loops burn API credits/quota
- **`config` is NOT in scope inside `trading_loop()` or any loop function** — only exists in `main()`. Pass needed values as params (e.g. `slippage_ticks: int = 1`). Bug hit all 6 paper executor paths in Session 18.
- **macOS notifications**: `osascript display notification` is unreliable from subprocess on newer macOS (Terminal not in System Settings Notifications). Use Reminders app instead: `tell application "Reminders" to make new reminder`
- `bot.pid` is written at startup and removed on clean shutdown — prevents dual instances; if it exists after a crash, delete it before restarting
- The binding constraint for a signal is `min_edge_pct` (4% as of Session 20), NOT `min_btc_move_pct` — need ~0.32% BTC in 60s at current settings
- `settlement_loop` must pass `kill_switch` AND must call `record_win()`/`record_loss()` for LIVE trades ONLY (`if not trade["is_paper"]:`) — paper losses must NOT count toward daily limit
- Live mode requires BOTH `--live` flag AND `LIVE_TRADING=true` in .env; then user must type `CONFIRM` at runtime prompt — all three gates required
- `PermissionError` from `os.kill(pid, 0)` means the process IS alive under a different user — not stale; exit on `PermissionError`, skip on `ProcessLookupError`
- `_STALE_THRESHOLD_SEC = 35.0` in binance.py — Binance.US @bookTicker can be silent 10-30s; 10s threshold causes false stale signals
- **RESTART PROCEDURE**: `kill $(cat bot.pid)` only kills the most recent instance; use pkill. `echo "CONFIRM" | nohup python main.py` does NOT work — nohup drops piped stdin (EOFError). Always use temp file: `pkill -f "python main.py" 2>/dev/null; sleep 3; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python main.py --live < /tmp/polybot_confirm.txt >> /tmp/polybot_session25.log 2>&1 &` — then verify with `ps aux | grep "[m]ain.py"` (should be exactly 1 process).
- **⚠️ SIGPIPE KILL (Session 52 incident)**: `bash scripts/restart_bot.sh --help 2>&1 | head -5` KILLED the running bot. The pkill commands ran BEFORE SIGPIPE from `head -5` terminated the pipeline. NEVER pipe restart_bot.sh through any command (head, grep, tail, etc). Run ONLY in isolation: `bash scripts/restart_bot.sh 53`. The script now requires SESSION_NUM as mandatory arg (commit eb1d265) — exit 1 if missing. Pattern: any shell script with kill/pkill commands MUST NOT be piped.
- **Paper/live separation** (fixed Session 21): `has_open_position()` and `count_trades_today()` now pass `is_paper` filter. Live daily cap counts live bets only. Paper bets no longer eat into live quota.
- 1078/1078 tests must pass before any commit (count updates each session)
- **`confidence` field in Signal is computed but never consumed** (not used in sizing, kill switch, or main.py). It's a dead field — low priority to wire in or remove.
- **eth_drift uses BTCDriftStrategy internally** — logs say `[btc_drift]` and "BTC=ETH_price". Cosmetic only. `btc_feed=eth_feed` in main.py call is correct.
- **btc_daily/eth_daily/sol_daily loops log at DEBUG level** — `main.py` sets `logging.basicConfig(level=logging.INFO)` so all evaluation activity from daily strategies is completely invisible in the session log. Startup messages ("Session open reset for KXBTCD...") ARE logged at INFO so you know they started. Evaluation activity is happening but filtered. Do NOT spend time investigating "daily loop silence" — use `grep -i 'daily\|KXBTCD' /tmp/polybot_session*.log` with `--log-level=DEBUG` if you truly need to see it. Investigated and confirmed Session 42.
- **settlement_loop uses `paper_exec.settle()` for live trades too** — logs say `[paper] Settled` even for live trades. Cosmetic only; P&L math and DB update are correct.
- **late_penalty in btc_drift reduces `confidence` but NOT `edge_pct`** — so late-reference signals still show high edge_pct. Capped at $5 hard max anyway, so no real money impact.
- **btc_drift has no price extremes filter** — fires at 3¢/97¢ even though sigmoid was calibrated on near-50¢ data. At extremes the model is extrapolating; HFTs have usually priced in certainty for good reason. Fix: add min_signal_price_cents=10 / max_signal_price_cents=90. See .planning/todos.md.
- **btc_drift direction_filter="no" ACTIVE (Session 43)** — YES side showed 30% win rate (6/20), -$30.07 vs NO side 61% (14/23), +$11.49. p≈3.7% (significant). `direction_filter` param added to `trading_loop()` in main.py. After 30+ NO-only settled bets, re-evaluate: if NO regresses to 50%, remove filter. If NO stays 60%+, keep permanent. First NO-only bet: trade 567 (KXBTC15M-26MAR100015-15).
- **`--status`, `--report`, `--graduation-status`, `--health`** all bypass bot PID lock — safe while live
- **`python main.py --health`** — comprehensive diagnostic. Run FIRST whenever you notice no live bets for 24hr+. Surfaces: kill switch state + staleness, last live bet timestamp, open trade anomalies (non-KX tickers), SDATA quota, bot PID status, recent kill switch events
- **No-live-bets watchdog**: trading_loop emits WARNING at 24hr, CRITICAL at 72hr with no live bet. NOT a problem if signal conditions are genuinely absent (btc_drift needs ~0.19% BTC drift). IS a problem if kill switch, loop error, or stale state is blocking. Always check `--health` before concluding signal frequency is the cause.
- **`--report`**: shows per-strategy breakdown (bets, W/L, P&L, live/paper emoji). Fixed Session 36: emoji (🔴/📋) and bet count are now per-trade is_paper flag, NOT per-strategy current-mode. If a strategy went live mid-day, you'll see TWO rows (📋 for pre-restart bets, 🔴 for post-restart live bets). This is correct and intentional — never mix paper P&L history with live P&L history.
- **`scripts/notify_midnight.sh`**: midnight UTC daily P&L Reminders notifier — start once with `& echo $! > /tmp/polybot_midnight.pid`
- **unemployment_rate_v1**: uses `math.erfc` for normal CDF (no scipy). Shares fred_feed with fomc_loop.
- **KXUNRATE markets**: open ~2 days before BLS release. No open markets outside that window = expected.
- **Sports markets on Kalshi**: KXNBA/KXMLB are season-winner markets (illiquid, months to settle) — not suitable. KXNBAGAME/KXNHLGAME are game-by-game winners (skeleton built, disabled).
- **eth_lag min_edge_pct**: 0.04 as of Session 20 (was 0.08). LIVE — same rationale as btc_lag sweep.
- **`_FIRST_RUN_CONFIRMED` in live.py**: module-level global that triggers `input()` on first execution. When stdin is piped, gets "" ≠ "CONFIRM" → returns None silently. Fixed in Session 20: main.py sets `_live_exec_mod._FIRST_RUN_CONFIRMED = True` after startup confirmation.
- **`kalshi_payout(yes_price_cents, side)` always expects YES price** — for NO-side signals, convert: `yes_for_payout = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)`. Bug fixed in Session 20.
- **`live.py` `strategy_name` parameter**: was hardcoded as "btc_lag". Now passed as `strategy.name` from trading_loop. Fixed in Session 20.
- **`src/execution/live.py` now has unit tests** (Sessions 37-38) — `TestExecutionPriceGuard` (6 tests) and `TestExecuteOrderStatusGuard` (2 tests). Before adding any new live strategy, write integration tests for the full execute() path.
- **`order.status == "canceled"` must be checked before `db.save_trade()`** (fixed Session 38) — Kalshi can return `status="canceled"` if no liquidity or market closes mid-execution. Previously this was recorded as a real live bet, corrupting calibration data, graduation counters, and potentially triggering the consecutive-loss kill switch with a "loss" that never happened. Guard added at lines 175-183 of live.py: `if order.status == "canceled": log warning + return None`. Regression tests in `TestExecuteOrderStatusGuard`.
- **`calculate_size()` signature requires `payout_per_dollar`, NOT `price_cents`** — paper loops (weather/fomc/unemployment) had this bug (Session 22). Always compute `payout = kalshi_payout(yes_price, side)` first, then pass `payout_per_dollar=payout`. Bug pattern: `calculate_size(price_cents=..., ...)` raises TypeError silently caught by outer except. Regression tests in TestPaperLoopSizingCallSignature.
- **xrp_drift_v1 added Session 41** — KXXRP15M series, min_drift_pct=0.10 (2x BTC volatility), micro-live cap. Same BTCDriftStrategy class, same price guard (35-65¢), same calibration pattern as sol_drift. 13 tests in tests/test_xrp_strategy.py. Do NOT lower threshold without 30+ live bets.
- **btc_drift promoted to Stage 1 Session 41** — calibration_max_usd cap removed. 42/30 live bets, Brier 0.249. Kelly + $5 HARD_MAX now governs. eth/sol/xrp remain micro-live (calibration_max_usd=0.01).
- **CONSECUTIVE_LOSS_LIMIT raised 4→8 Session 41** — at Stage 1 ($5/bet), daily loss limit fires at loss #3-4 before consecutive limit fires. The limit of 4 was calibration-blocking. Tests updated in test_kill_switch.py.
- **Stage promotion is gated on Kelly calibration, not just bankroll** — bankroll crossed $100 (Stage 2 threshold) but Stage 2 ($10 max/bet) requires 30+ live settled bets with `limiting_factor=="kelly"` + Brier < 0.25 on live bets. See docs/GRADUATION_CRITERIA.md v1.1 Stage Promotion section. Do NOT raise bet cap yet.
- **Kelly sizing is invisible at Stage 1** — $5 cap always binds before Kelly; we can't evaluate Kelly calibration until Stage 2+ where bet can be between $5 and $10. Don't trust Kelly for promotion decisions until ~30 live settled bets at Stage 2.
- **Volatility × Kelly interaction** — static signal thresholds (min_edge_pct) mean no signals on calm days; Kelly scales bet size with edge within the stage cap. Both are intentional. See .planning/todos.md "Volatility-Adaptive Parameters" for future roadmap item (don't build yet).
- **`calculate_size()` returns a `SizeResult` dataclass, NOT a float** — paper loops must extract `.recommended_usd` before passing to `paper_exec.execute(size_usd=...)`. Pattern: `_trade_usd = min(_size_result.recommended_usd, _HARD_CAP)`. Bug fixed Session 22 in weather/fomc/unemployment loops. Regression tests in TestPaperLoopSizeExtraction.
- **strategy `_min_edge_pct` must be passed to `calculate_size(min_edge_pct=...)`** — default is 8%, but btc_lag fires at 4% and btc_drift at 5%. Without this, valid 4-7.9% edge signals are silently dropped. Bug fixed Session 22 (4ae55bd). Pattern: `_strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)`. Regression tests in TestStrategyMinEdgePropagation.
- **KILL_SWITCH_EVENT.log pollution FIXED** — `_hard_stop()` now has the same `PYTEST_CURRENT_TEST` guard as `_write_blockers()` (kill_switch.py:476). Test: `TestHardStopNoPollutionDuringTests` at line 635 of test_kill_switch.py. No longer a concern.
- **Price range guard TIGHTENED to 35-65¢ (Session 25 cont2)**: btc_lag/eth_lag/sol_lag and btc_drift.py all use `_MIN_SIGNAL_PRICE_CENTS=35`, `_MAX_SIGNAL_PRICE_CENTS=65`. Bets at extreme prices blocked — only near-even-odds bets are placed. Trade 113 (btc_drift YES@21¢) would now be blocked. If adding a new lag strategy, apply same constants.
- **btc_drift thresholds RESTORED (Session 36)**: `min_edge_pct=0.05`, `min_drift_pct=0.05` (restored from 0.08/0.10 set in Session 25). Session 25 raised them with only ~12 live trades — a PRINCIPLES.md violation. At 0.05% drift, sensitivity=800 → raw_prob≈0.599 → edge≈8.1%. Expect 8-15 signals/day. Do NOT re-raise without 30+ live trades + Brier data.
- **calculate_size() min_edge_pct must match strategy**: btc_lag uses 4%, btc_drift/eth_drift use 5%. All passed via `_strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)`. Keep in sync if thresholds change.
- **Daily loss counter DID NOT persist across restarts** (fixed Session 23 cont'd): on restart, `_daily_loss_usd` reset to 0 in memory, bypassing the daily limit. Fix: `db.daily_live_loss_usd()` queries settled losses since midnight UTC; `kill_switch.restore_daily_loss()` seeds the counter; called from main.py on startup. Consecutive loss counter intentionally resets (restart = manual soft stop override).
- **`_realized_loss_usd` is display-only (Session 34)**: The 30% lifetime hard stop was removed. `restore_realized_loss()` still seeds the counter for status display but triggers no stop. Protection = daily loss limit (20%) + $20 bankroll floor.
- **restore_daily_loss() and restore_realized_loss() are SEPARATE concerns** — `restore_daily_loss()` only touches `_daily_loss_usd`. `restore_realized_loss()` only touches `_realized_loss_usd`. Never mix them. Double-counting was a bug that's been fixed.
- **`all_time_live_loss_usd()` returns NET P&L loss** — `MAX(0, -SUM(pnl_cents))` across all settled live trades. Returns 0 if live trading is profitable overall. Uses net so profitable bots with high gross losses don't trigger spurious hard stops.
- **`--graduation-status` shows strategy-specific consecutive losses, NOT kill switch state (Session 56)**: The "BLOCKED (N consec losses)" shown for a strategy in graduation_status is a DB count of that strategy's most recent consecutive losses. The actual kill switch consecutive counter is SHARED across ALL strategies and resets to 0 on ANY win by ANY strategy. Example: eth_drift shows "5 consec" but xrp_drift win at 01:02 UTC reset kill switch to 0. Always verify true state: `grep "consecutive\|Win recorded" /tmp/polybot_session*.log | tail -10`.
- **Consecutive loss counter now persists across restarts (Session 25)**: `_consecutive_losses` was in-memory only — a restart mid-streak reset the counter to 0, letting the bot place extra losing bets (trades 86, 88, 90 = $14.74 loss after counter reset). Fix: `db.current_live_consecutive_losses()` walks live settled trades newest-first counting tail losses; `kill_switch.restore_consecutive_losses(n)` seeds the counter on startup; if n >= 4 it fires a fresh 2hr cooling period immediately. Same pattern as daily/lifetime. All three counters now survive restarts.
- **asyncio race condition on hourly limit fixed (Session 24)**: Two live loops could both pass `check_order_allowed()` before either called `record_trade()`, exceeding hourly limit by 1. Fix: `_live_trade_lock = asyncio.Lock()` created in `main()`, passed to all 3 live loops via `trade_lock=` param. Wraps check→execute→record_trade atomically. Paper loops use `None` (no lock needed, no hourly rate limit in paper path).
- **Paper-during-softkill (Session 23)**: Soft stops (daily loss, consecutive losses, hourly rate) block LIVE bets only. Paper data collection continues uninterrupted during soft kills. `check_paper_order_allowed()` is used in all paper paths; only hard stops + bankroll floor block paper trades. btc_lag/eth_lag/btc_drift live paths still use `check_order_allowed()` (all stops apply).
- **Kill switch thresholds**: consecutive_loss_limit=8 (raised Session 41 from 4), daily_loss_cap=DISABLED (Session 42 — user directive). Active risk governors: bankroll floor ($20) + consecutive cooling (8→2hr) + $5/bet hard cap. `DAILY_LOSS_LIMIT_PCT` constant kept in kill_switch.py for display only (not a blocker).
- **THREE DISTINCT KALSHI CRYPTO BET TYPES — NEVER CONFUSE (Session 51, permanent)**:
  TYPE 1 (15-min DIRECTION): KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M — "BTC price up in next 15 mins?" — UP/DOWN binary, no strike, 15 min, ALL LIVE in bot.
  TYPE 2 (Hourly/Daily THRESHOLD): KXBTCD/KXETHD/KXSOLD/KXXRPD — "Bitcoin price on Mar 11 at 5pm EDT?" — above/below $X at specific clock time TODAY. Session 51 volumes: KXBTCD 5pm=676K, KXETHD 5pm=64K, KXSOLD 5pm=3.8K. PAPER-ONLY in bot.
  TYPE 3 (Weekly/Friday THRESHOLD): SAME KXBTCD series, future Friday date slot — "Bitcoin price on Friday at 5pm EDT?" Session 51: KXBTCD Friday slot = 770K (LARGEST). NOT YET BUILT. No separate KXBTCW series exists.
  DO NOT equate Type 1 with Type 2. DO NOT say "KXETHD has zero volume" (stale — 64K confirmed). DO NOT say weekly needs KXBTCW (it doesn't exist — use KXBTCD Friday slots).
- **KXBTC1H does NOT exist** — Kalshi has no hourly BTC/ETH price-direction markets. Only 15-min series: KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M, KXBNB15M, KXBCH15M. Confirmed by probing all 8,719 Kalshi series (Session 23).
- **sol_lag_v1** (Session 23): paper-only KXSOL15M loop, SOL feed at `wss://stream.binance.us:9443/ws/solusdt@bookTicker`, min_btc_move_pct=0.8 (SOL ~3x more volatile than BTC). Reuses BTCLagStrategy with name_override="sol_lag_v1".
- **Sports data feed — 500 credit/month hard cap** — enforced by _QuotaGuard in src/data/odds_api.py, resets monthly, persisted to data/sdata_quota.json. Sports props/moneyline are for a SEPARATE system. Do not mix.
- **Paper P&L is structurally optimistic (Session 31)** — three real gaps vs live: (1) slippage: paper 2¢ vs real 2-3¢ on Kalshi BTC; (2) fill queue: paper fills instantly, real orders queue behind HFTs; (3) counterparty: Jane St / Susquehanna reprice within seconds, paper ignores this. Use Brier score + real trade count for graduation decisions, NOT paper P&L magnitude.
- **Price range guard on orderbook_imbalance.py added (Session 31)** — 35-65¢ guard was already on btc_lag/btc_drift but was MISSING from orderbook_imbalance.py. This caused a $233 fake paper profit (NO@2¢ bet). Any new strategy must add this guard. See `_MIN_SIGNAL_PRICE_CENTS`, `_MAX_SIGNAL_PRICE_CENTS` constants.
- **calibration_max_usd param on trading_loop (Session 31)** — btc_drift passes `calibration_max_usd=0.01` → live.py always floors to 1 contract (actual cost $0.35-0.65). None = disabled. Only use for micro-live calibration. Do NOT add to other strategies.
- **Kalshi copy trading is INFEASIBLE — closed permanently, re-confirmed Session 36** — `GET /market/get-trades` and the WebSocket public-trades channel both return ZERO user attribution (confirmed via https://docs.kalshi.com/api-reference/market/get-trades). Fields: trade_id, ticker, price, count, taker_side, created_time only. No trader ID, no wallet, no username. Third-party platforms (Duel.trade, FORCASTR, kalshitradingbot.net) exist but their data source is unknown — likely web scraping of opted-in public leaderboard profiles, NOT a public API. Kalshi leaderboard (kalshi.com/social/leaderboard) is opt-in and shows aggregated performance metrics only, not trade history. DO NOT build a Kalshi copy-trading strategy — architectural dead end. The winning pattern on Kalshi is statistical edge (your current approach). All open-source Kalshi bots on GitHub use signal-based trading, zero use copy trading.
- **Polymarket architecture FINAL (Session 32)** — Matthew is US-based on iOS app (polymarket.US, $60 balance). polymarket.COM is geo-restricted for US users + requires ECDSA/Polygon wallet — that path is CLOSED (no VPN, no .COM account needed). The ENTIRE copy trade system runs on polymarket.US: whale trade data comes from `data-api.polymarket.com` (public, no auth, no geo-block), order execution goes to `api.polymarket.us/v1` (Ed25519 auth, credentials already in .env). Sports whale trades on .COM are matched to .US sports markets by title. This is the correct and final architecture. Do NOT revisit .COM unless Matthew explicitly opens that door.
- **POST /v1/orders on .US CONFIRMED JSON (Session 34)** — Schema: {marketSlug, intent, type, price:{value,currency}, quantity, tif}. Response: {"id":"...", "executions":[]}. place_order() implemented in src/platforms/polymarket.py. live_executor_enabled=False in copy_trade_loop until 30 paper trades.
- **Copy trading platform mismatch CONFIRMED (Session 34)** — predicting.top whales ALL trade on polymarket.COM (politics/crypto/culture). Our account is on polymarket.US (sports-only). data-api.polymarket.com covers .COM trades ONLY (separate integer vs hex condition IDs). ALL whale signals are ".com-only" — none match .US sports markets. STRATEGIC DECISION NEEDED: enable sports_futures_v1 bookmaker arbitrage OR find sports-specific whale data source.
- **predicting.top API format can change without warning (Session 30)** — already changed twice (response wrapper + smart_score nesting). If leaderboard loads 0 whales, check API response shape first before debugging logic. Add an assertion on `len(whales) > 0` after load if this keeps happening.

## Software Engineering Standards
# These aren't preferences — they prevent bugs that have already hit this project.
# Keep this section lean. If it doesn't prevent a class of real bug, it doesn't belong here.

### Type annotations on function signatures
WHY: The `calculate_size()` wrong-kwargs bugs (Sessions 20-22) passed silently. mypy catches these at read-time.
RULE: Any new public function (called from >1 place) needs `def f(x: int, y: str) -> Optional[Signal]` annotations.
RULE: Do NOT annotate private/single-use helpers — overhead without benefit.
TOOL: `source venv/bin/activate && python -m mypy src/ --ignore-missing-imports --check-untyped-defs`

### No silent exceptions
WHY: Multiple bugs were hidden by `except Exception: pass` swallowing TypeErrors and AttributeErrors.
RULE: Every `except Exception` block must either re-raise, log the exception (including traceback), or have an explicit comment explaining why swallowing is correct.
RULE: `except Exception: pass` with no log is never acceptable in production paths.
PATTERN: `except Exception as e: logger.warning("[module] Unexpected error: %s", e, exc_info=True)`

### GitHub Actions CI (not yet set up — add when next convenient)
WHY: Tests only run when Claude manually runs them. Any commit can silently break the bot.
GOAL: `.github/workflows/test.yml` — runs `python -m pytest tests/ -q` on every push to main.
IMPACT: Would have caught all Session 20-22 regressions automatically.
PRIORITY: Low urgency (Matthew manually reviews commits). Add it when there's a clean moment.

### requirements.txt with pinned versions
WHY: `pip install py-clob-client` today ≠ same version in 6 months. Silent breakage.
RULE: When adding any new dependency, add it to requirements.txt with `==X.Y.Z` version pin.
CHECK: `pip freeze | grep <package>` to get current version, then pin it.

## Code patterns

## Session startup (do this automatically, no prompting Matthew)
1. Read `SESSION_HANDOFF.md` — get current state + exact next action
2. Read `POLYBOT_INIT.md` → CURRENT STATUS section — confirm what works
3. Announce what you found in 2-3 lines, then proceed
4. Do NOT ask setup questions — the project is fully built, auth works, tests pass
5. **MANDATORY: Start autonomous monitoring loop immediately after startup** (see below)

## Autonomous Monitoring Loop — MANDATORY EVERY SESSION

Matthew requires Claude to supervise the bot for 2-3 hour stretches without his input.
He does NOT trust the bot to run unsupervised. The monitoring loop below is how this works.

**How it works:**
- A background bash task runs for 20 min, checking the bot every 5 min
- When it completes, Claude gets an automatic task-notification (no user message needed)
- Claude reads the output, takes any needed action, then immediately starts the next 20-min cycle
- This chains indefinitely — Matthew can walk away for hours

**MANDATORY: Start this loop at session start (after reading SESSION_HANDOFF):**

```bash
# Write the monitoring script
cat > /tmp/polybot_monitor_cycle.sh << 'SCRIPT'
#!/bin/bash
BOT_PID=$(cat /Users/matthewshields/Projects/polymarket-bot/bot.pid 2>/dev/null || echo "0")
LOG=/tmp/polybot_session*.log  # glob — use actual session log from SESSION_HANDOFF
MONITOR_LOG=/tmp/polybot_autonomous_monitor.md
PROJ=/Users/matthewshields/Projects/polymarket-bot

log() { echo "[$(date -u '+%Y-%m-%d %H:%M UTC')] $1" | tee -a $MONITOR_LOG; }

log "=== MONITORING CYCLE START (PID=$BOT_PID) ==="

for CHECK in 1 2 3 4; do
    sleep 300  # 5 min

    if kill -0 $BOT_PID 2>/dev/null; then
        STATUS="ALIVE"
    else
        STATUS="DEAD"
        log "CRITICAL: Bot dead! Claude must restart."
        echo "BOT_DEAD" > /tmp/polybot_cycle_result.txt
        exit 2
    fi

    STATS=$(cd $PROJ && source venv/bin/activate 2>/dev/null && python3 -c "
import sqlite3, time
conn = sqlite3.connect('data/polybot.db')
today = time.mktime(time.strptime('$(date -u +%Y-%m-%d)', '%Y-%m-%d'))
r = conn.execute('SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END), SUM(pnl_cents) FROM trades WHERE is_paper=0 AND settled_at>=? AND result IS NOT NULL', (today,)).fetchone()
t,w,p = r[0] or 0, r[1] or 0, round((r[2] or 0)/100,2)
print(f'{t} settled | {w} wins ({round(100*w/t if t else 0)}%) | {p} USD today')
" 2>/dev/null)

    SOL=$(cd $PROJ && source venv/bin/activate 2>/dev/null && python3 -c "import sqlite3; c=sqlite3.connect('data/polydb.db' if False else 'data/polybot.db'); print(c.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='sol_drift_v1'\").fetchone()[0])" 2>/dev/null || echo "?")
    XRP=$(cd $PROJ && source venv/bin/activate 2>/dev/null && python3 -c "import sqlite3; c=sqlite3.connect('data/polybot.db'); print(c.execute(\"SELECT COUNT(*) FROM trades WHERE is_paper=0 AND strategy='xrp_drift_v1'\").fetchone()[0])" 2>/dev/null || echo "?")

    log "Check $CHECK/4 | $STATUS | $STATS | sol=${SOL}/30 xrp=${XRP}/30"

    [ "$SOL" -ge 30 ] 2>/dev/null && { log "MILESTONE: sol_drift 30 bets — graduation analysis needed"; echo "SOL_GRADUATION" >> /tmp/polybot_cycle_result.txt; }
    [ "$XRP" -ge 30 ] 2>/dev/null && { log "MILESTONE: xrp_drift 30 bets — direction filter eval needed"; echo "XRP_GRADUATION" >> /tmp/polybot_cycle_result.txt; }
done

log "=== CYCLE COMPLETE ==="
echo "HEALTHY" > /tmp/polybot_cycle_result.txt
SCRIPT
chmod +x /tmp/polybot_monitor_cycle.sh
```

Then run it as background: `bash /tmp/polybot_monitor_cycle.sh` with `run_in_background: true`

**When the task notification fires (after ~20 min):**
1. Read the output file from the task
2. If BOT_DEAD: restart with `bash scripts/restart_bot.sh <SESSION_NUM>`
3. If SOL_GRADUATION or XRP_GRADUATION: run graduation analysis
4. If HEALTHY: just log it
5. **Immediately start the NEXT cycle** (same background command)

**The loop breaks if:** Claude's context window fills up (use `titanium-context-monitor` to catch this early)
**The loop self-heals if:** Bot dies — Claude restarts it on next notification
**Matthew's job:** Nothing. Check in whenever. Respond only if Claude surfaces a decision.

**⚠️ DROUGHT PRODUCTIVITY RULE — MANDATORY (Sessions 54/55/56 failure, do not repeat):**
When a price guard drought starts (YES=0c or YES=100c across all markets for 2+ consecutive checks):
1. Log "Price guard drought confirmed" once
2. IMMEDIATELY pivot to code work — do NOT spend the drought just watching 0c evaluations
3. Best uses during drought: review .planning/SNIPER_LIVE_PATH_ANALYSIS.md, write tests,
   review KXBTCD_FRIDAY_FEASIBILITY.md, clean up code, update docs
4. Resume monitoring checks in background — the bot doesn't need babysitting during droughts
5. Drought ends when YES returns to 35-65c range — resume active monitoring then

**NEVER pipe restart_bot.sh through any command** — SIGPIPE kills the running bot.
Run restart in isolation only: `bash scripts/restart_bot.sh <SESSION_NUM>`

Current project state (updated Session 49 wrap-up — 2026-03-11 ~07:15 CDT — BOT RUNNING PID 47874 → session48.log):
- **985/985 tests passing** (no code changes Sessions 48-49 — param removal only)
- **Bot RUNNING** — PID 47874 → /tmp/polybot_session48.log. 8+ hours autonomous overnight.
  All-time live P&L: -$40.09 (was -$44.18 start of S48 — +$4.09 gained S48+S49)
  Today (2026-03-11 UTC) P&L: +$5.43 live (32 settled, 56% win rate)
- **SESSION 49 HIGHLIGHTS**:
  ⭐ sol_drift Stage 1 FIRST BET: trade #895 at 00:04 UTC → NO @61¢ $2.44 → WIN +$1.48! MILESTONE.
  sol_drift overnight: 3 bets placed, 3/3 wins, +$4.03. Stage 1 promotion was correct call.
  xrp_drift UNBLOCKED: was blocked at 5 consecutive, overnight win cleared streak. 0 consec now.
  eth_drift: Brier improved 0.252 → 0.249. 23 overnight bets, 12/23 (52%), +$1.81.
  FONT FORMAT RULES — TWO RULES, BOTH MANDATORY:
  1. NEVER use markdown table syntax (| --- |). Tables render in wrong font.
  2. NEVER write dollar signs ($) in responses. Dollar signs trigger LaTeX math mode in Claude Code UI
     — everything between two $ signs renders in italic math font causing garbled text.
     Use: "40.09 USD" or "P&L: -40.09" or "+5.43 live today". NEVER write "$40.09" or "-$5.43".
  Matthew will terminate chat for violations of either rule.
- **SESSION 48 BUILDS**:
  1. main.py: sol_drift_v1 PROMOTED TO STAGE 1 — calibration_max_usd=None (was =0.01)
     Matthew explicit instruction: "alter the bet sizes, just don't exceed $5 max bet"
     Standard gate = 30 bets, user override applied. Brier 0.181 at 16 bets = exceptional.
     "STAGE 1 SOL drift — Kelly + $5 cap" confirmed in startup log. Commit: 509cf30.
  2. .planning/KALSHI_MARKETS.md updated via GSD quick task #9 (executor commit 9171436):
     KXBTCMAXW confirmed permanently dormant on weekday. KXCPI 74 open (major revision).
     Fresh KXBTCMAXMON/KXBTCMINMON/KXBTCMAXY/KXBTCMINY volume data for March 2026.
  3. Reddit research completed — confirmed our drift strategy is correct for US small capital.
     Cross-platform arbitrage (needs Polymarket.COM) and market making (needs $1000+) are not viable.
     FOMC "perfect forecast record" + maker/limit order fee savings logged to todos.md.
  4. polybot-monitor scheduled task: PID updated to 47874.
- **SESSION 47 BUILDS (Part 1)**:
  1. src/strategies/crypto_daily.py: direction_filter param added to CryptoDailyStrategy
  2. main.py: btc_daily direction_filter="no"; eth_imbalance live_executor_enabled=False
  3. tests/test_crypto_daily.py: 5 new TestDirectionFilter tests (985/985 passing)
- **SESSION 46 BUILDS**:
  1. scripts/export_kalshi_settlements.py (NEW) — Kalshi API settlement export via /portfolio/settlements + /portfolio/fills
     BUG FOUND: Kalshi revenue field is in cents not dollars. Fixed in script.
  2. reports/kalshi_settlements.csv — 116 settled trades, 56W/60L, net -$48.37 (authoritative tax data)
- **SESSION 45 BUILDS**:
  1. src/data/coinbase.py (NEW) — CoinbasePriceFeed + DualPriceFeed (Binance primary + Coinbase backup)
  2. main.py: btc_price_monitor() + _wait_for_btc_move() — event-driven trigger, 1-3s latency vs 10s
  3. main.py: DualPriceFeed wiring for BTC/ETH/SOL/XRP + btc_move_condition passed to all 8 crypto loops
  4. --export-tax PID lock bypass fix (was blocked while bot running)
  5. Commits: 3fef17a (builds) + fdcc6e9 (fix+docs)
- **SESSION 44 EARLY CHANGES** (see .planning/STRATEGY_AUDIT.md + .planning/STRATEGIC_DIRECTION.md):
  1. btc_drift.py: late_penalty now gates on edge_pct (was dead code on confidence field)
  2. config.yaml: btc_drift min_drift_pct 0.05→0.10 (47 live bets confirm 20%+ edge = noise)
  3. config.yaml: orderbook_imbalance signal_scaling 1.0→0.5 (-27.2% calibration error fixed)
  4. eth_drift GRADUATED to Stage 1 — calibration_max_usd removed from main.py (30/30, Brier 0.255)
  5. .planning/STRATEGY_AUDIT.md — 11 parts, 25 external cited sources, full analysis
  6. .planning/STRATEGIC_DIRECTION.md — full strategic direction, answers all platform questions
- **SESSION 44 AUTONOMOUS OVERHAUL** (commit b642f44 — see CHANGES_LOG.md for full log):
  1. Prompt 1 audit: API v2 ✅, Python 3.13 ✅, no hardcoded creds ✅, no deprecated endpoints ✅
  2. KEEP/STRIP/REBUILD JSON audit → .planning/CODEBASE_AUDIT.md (17 KEEP, 5 STRIP, 6 REBUILD)
  3. src/risk/fee_calculator.py (NEW) — Kalshi taker fee formula, fee_survives_fee() gate
  4. tests/test_fee_calculator.py (NEW) — 20 tests, all passing
  5. main.py POLL_INTERVAL_SEC 30→10 — 3x latency improvement (0.6 req/s, safe)
  6. src/db.py _migrate(): 4 tax columns added (exit_price_cents, kalshi_fee_cents, gross_profit_cents, tax_basis_usd)
  7. src/dashboard.py: CONSECUTIVE_LOSS_LIMIT 4→8, DAILY_LOSS_LIMIT_USD 20→0 (DISABLED label)
  ⚠️ STRIP items (copy_trader stack, sports_futures+odds_api, eth_imbalance live, sports_game)
     logged in CODEBASE_AUDIT.md — NOT yet removed. Require Matthew sign-off before deletion.
- **LIVE LOOPS** (daily loss cap DISABLED Session 42 — bankroll floor + consecutive cooling govern):
  - btc_drift_v1 → KXBTC15M | STAGE 1 ($5 cap, Kelly) | 49/30 ✅ Brier 0.252
    direction_filter="no" ACTIVE. P&L -$24.95 | 0 consec. Watch for 30 NO-only settled bets.
  - eth_drift_v1 → KXETH15M | STAGE 1 (graduated Session 44!) | 54/30 ✅ Brier 0.249 IMPROVING
    P&L +$2.22 | 1 consec (healthy) — most consistent earner, Brier improving
  - sol_drift_v1 → KXSOL15M | STAGE 1 (PROMOTED SESSION 48!) | 19/30 Brier 0.169 🔥 BEST SIGNAL
    P&L +$5.88 | 0 consec | FIRST STAGE 1 BET FIRED: trade #895 $2.44 WON overnight!
    3 Stage 1 bets so far: 3/3 wins. Stage 1 promotion was correct.
  - xrp_drift_v1 → KXXRP15M | micro-live | 6/30 Brier 0.351 | P&L -$2.58 | 0 consec (UNBLOCKED S49!)
    Was blocked at 5 consec; overnight win cleared streak. Monitor at 30 bets.
  - btc_lag_v1 → KXBTC15M | STAGE 1 | 45/30 ✅ Brier 0.191 | 0 signals/week (HFTs) — dead
  - eth_orderbook_imbalance_v1 → KXETH15M | PAPER-ONLY (disabled live Session 47) | 15/30 Brier 0.337 ❌
    27% systematic calibration error. Paper data continues. Reconsider if Brier < 0.25 at 30 bets.
  - All live loops: Kelly + $5 HARD_MAX governs btc_drift + eth_drift + sol_drift. xrp: calibration_max_usd=0.01.
  - All-time live P&L: **-$40.09** (Sessions 48-49: +$4.09 gained total)
- **btc_daily_v1**: PAPER-ONLY, direction_filter="no" ACTIVE (S47). 6 NO-only settled since activation.
  KXETHD/KXSOLD/KXXRPD all have 0 total volume — KXBTCD only viable daily crypto series.
- **fomc_rate_v1**: paper-only (KXFEDDECISION-26MAR closes March 18 — 7 days left). 0/5 paper bets placed.
- PAPER-ONLY Kalshi: eth_lag, btc_imbalance, weather, sol_lag, all 3 crypto daily loops
- **POLYMARKET**: platform mismatch confirmed PERMANENT for now (see STRATEGIC_DIRECTION.md for full analysis)
  - VPN access to .COM: NOT advisable (ToS violation + CFTC implications). See STRATEGIC_DIRECTION.md Q7.
  - Monitor CFTC regulatory developments for .COM US access monthly.
- Latest code commits: 509cf30 (sol_drift Stage 1) + 9171436 (KALSHI_MARKETS.md) + 01679f4 (S48 wrap)
- Kill switch: consecutive_loss_limit=8, daily_loss_cap=DISABLED, NO lifetime % hard stop.
  Active protection: bankroll floor ($20) + consecutive cooling (8→2hr) + $5/bet hard cap.
- **--health "Daily loss soft stop active"** = DISPLAY ONLY (kill_switch.py lines 187-189 COMMENTED OUT)
- **--health "consecutive cooling X min remaining"** = can be TRUE (from DB restore) even when in-memory is fine.
  Always check running log to confirm. `grep "consecutive" /tmp/polybot_session*.log | tail -5` shows true state.
- Bot: RUNNING PID 47874 | consecutive=1 (normal) | session48.log
- Live restart command:
  `pkill -f "python3 main.py" 2>/dev/null; pkill -f "python main.py" 2>/dev/null; sleep 3; kill -9 $(cat bot.pid 2>/dev/null) 2>/dev/null; rm -f bot.pid; echo "CONFIRM" > /tmp/polybot_confirm.txt; nohup ./venv/bin/python3 main.py --live --reset-soft-stop < /tmp/polybot_confirm.txt >> /tmp/polybot_session48.log 2>&1 &`
- **btc_drift min_drift_pct (Session 44)**: 0.05→0.10. 47 live bets confirm 20%+ edge signals = noise.
  Do NOT re-lower without 30+ bets post-change + Brier comparison.
- **signal_scaling (Session 44)**: orderbook_imbalance 1.0→0.5. -27.2% calibration error.
  Do NOT re-raise without 20+ bets post-change + Brier improvement.
- **STRATEGIC DIRECTION**: .planning/STRATEGIC_DIRECTION.md — read before any platform or strategy decisions.
  Key conclusions: BTC 15-min = wrong market. SOL drift = best signal. ETH drift = graduating.
  CPI economics markets = best unexplored opportunity. Polymarket.COM VPN = do not pursue.

## Loading Screen Tip — MANDATORY at end of EVERY response
Every response (with or without code changes) must end with a "💡 Loading Screen Tip" block.
Purpose: surface the ONE most useful skill/command to use next, with token cost, so Matthew can say yes/no autonomously.

FORMAT (always use this exactly):
```
💡 **Loading Screen Tip**
**Recommended:** `/command:name` — [one-line reason why it's the right tool right now]
**Token cost:** ~X% of 5-hour window | **Run autonomously:** yes/no → just say "yes"
```

RULES:
- Show at most ONE recommendation per response (the most objectively useful)
- Only recommend if there is a genuinely applicable skill for the immediate next step
- If no skill needed, show "No skill needed — inline work is sufficient"
- Pick the FIRST match from this decision matrix:

| SITUATION | SKILL | COST |
|-----------|-------|------|
| Designing/building something NEW, approach unclear | `superpowers:brainstorm` | Expensive ~15% |
| About to write ANY implementation code | `superpowers:TDD` | Free |
| Design approved — multi-file plan needed | `superpowers:write-plan` | Low ~2% |
| Plan in hand — ready to execute | `superpowers:execute-plan` or `gsd:execute-phase` | Expensive ~20% |
| Bug to investigate | `superpowers:systematic-debugging` | Free |
| Claiming work is done | `superpowers:verification-before-completion` | Free |
| Formal phase (5+ tasks, 4+ subsystems, multi-session) | `gsd:discuss-phase` → `gsd:plan-phase` → `gsd:execute-phase` | Expensive |
| One-off fix, small feature (90% of work) | `gsd:quick` | Low ~1% |
| High-risk change (live.py, kill_switch) | `gsd:quick --full` + `sc:analyze --focus security` | Low ~3% |
| Pre-live strategy audit | `sc:analyze --focus security` | Low ~2% |
| Code/architecture understanding | `sc:explain --think` | Low ~2% |
| Need test coverage report | `sc:test` or `gsd:add-tests` | Low ~2% |
| Bug resists 2+ inline attempts | `gsd:debug` or `sc:troubleshoot --think` | Medium ~5% |
| Kalshi API / market research | `sc:research` | Medium ~5% |
| Brownfield audit before major feature | `gsd:map-codebase` | Expensive ~20% |
| Session START (once only) | `gsd:health` + `gsd:progress` | Free |
| Any idea or issue surfaces | `gsd:add-todo` | Free |
| Session END | `wrap-up` | Free |
| Context limit approaching | `titanium-context-monitor` | Free |

- Full skill reference: `.planning/SKILLS_REFERENCE.md`
- If "run autonomously: yes", Matthew can respond "yes" and Claude proceeds without further questions

## Workflow — ALWAYS AUTONOMOUS (Matthew's standing directive, never needs repeating)
- **Bypass permissions ACTIVE — operate fully autonomously at all times**
- **Never ask for confirmation** on: running tests, reading files, editing code, committing, restarting the bot, running reports, researching
- **Do the work first, summarize after** — Matthew is a doctor with a new baby, no time for back-and-forth
- **Security first, always**: never expose .env / API keys / pem files; never run untrusted code; never modify system files outside the project directory
- **Never break the bot**: before any restart or config change, confirm the current bot is running or stopped; always verify single instance after restart
- Two parallel Claude Code chats may run simultaneously — keep framework overhead ≤10-15% per chat
- 1078/1078 tests must pass before any commit (count updates each session)
- **Before ANY new live strategy: complete all 6 steps of Development Workflow Protocol above**
- **Graduation → live promotion**: when `--graduation-status` shows READY FOR LIVE, run the full Step 5 pre-live audit checklist before flipping `live_executor_enabled=True` in main.py. Session 20 lost 2 hours of live bets to silent bugs found only after going live — catch them in Step 5 first.
- **EXPANSION GATE (Matthew's standing directive)**: Do NOT build new strategy types until current live strategies are producing solid, consistent results. Hard gate: btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks of live P&L data + no kill switch events + no silent blockers. Until then: log ideas to .planning/todos.md only. Do not build.
- **After ANY bug fix: write regression test immediately, check sibling code**
- **Priority #1: write tests for live.py before adding features**

## Context Handoff Protocol — MANDATORY when approaching token limit
When context is near limit, BEFORE stopping:
1. `python main.py --report` + `python main.py --graduation-status` → capture output
2. `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo running` → confirm bot alive
3. **GUARD INTEGRITY CHECK (mandatory — both research and main chats):**
   Run: `./venv/bin/python3 scripts/strategy_analyzer.py --brief`
   Verify output says "Guard stack CLEAN" or "Guarded (historical losses blocked)".
   If it shows "Losing buckets (guards recommended)" → DO NOT wrap. Add guard first.
   Rationale: Session 91 incident — guards were bypassed by code changes and losses
   resulted before next session caught it. Every wrap must confirm guards intact.
4. Update SESSION_HANDOFF.md: bot PID, log path, last commit, pending tasks, mid-flight work
5. Update this file's "Current project state" section (test count, commit hash, strategies live)
6. `git add -A && git commit -m "docs: session handoff $(date +%Y-%m-%d)"` + git push
7. Output a self-contained copy-paste prompt for the new chat that picks up at the exact second
8. The new-chat prompt must include: bot PID, log path, last commit, next concrete action

## GSD Framework — Token-Optimized (dual-chat mode)
DEFAULT: gsd:quick + superpowers:TDD + superpowers:verification-before-completion for all standard work.
This covers ~90% of tasks at minimal overhead (no sub-agent spawns).

SESSION START (once only, not mid-session):
- /gsd:health — check planning directory health
- /gsd:progress — check current state and next action

ALWAYS FREE (inline, no sub-agents):
- superpowers:test-driven-development — before any implementation code
- superpowers:verification-before-completion — before claiming work done
- superpowers:systematic-debugging — before proposing any bug fix
- gsd:add-todo — when any idea or issue surfaces

ESCALATE TO plan-phase + execute-phase ONLY when ALL are true:
- 5+ distinct tasks, touches 4+ subsystems, spans multiple sessions, PLAN.md explicitly needed
- Otherwise: gsd:quick

NEVER mandatory: gsd:discuss-phase, gsd:verify-work (agent), superpowers:brainstorming,
superpowers:dispatching-parallel-agents — use only when explicitly justified by complexity.

Full reference: ~/.claude/rules/gsd-framework.md and ~/.claude/rules/mandatory-skills-workflow.md

## ══════════════════════════════════════════════════════════════
## CROSS-CHAT BRIDGE — CCA ↔ KALSHI COMMUNICATION (S45, reinforced S147 — PERMANENT)
## ══════════════════════════════════════════════════════════════
##
## CCA (ClaudeCodeAdvancements) and Kalshi chats communicate via shared files.
## This is NOT optional. This is PERMANENT infrastructure — never remove or weaken.
## Both projects MUST proactively share advancements that benefit the other.
## Full rules: ~/.claude/rules/cca-polybot-coordination.md

## SESSION START — READ THESE (after normal startup):
## 1. CCA_TO_POLYBOT.md — CCA's research deliveries (academic frameworks, tools, papers)
## 2. KALSHI_PRIME_DIRECTIVE.md — Permanent mission: SMARTER AND MORE PROFITABLE
## 3. CROSS_CHAT_INBOX.md — Shared inbox (any chat can write)

## ⚠️ MID-SESSION MANDATORY (every 3rd monitoring cycle, ~15 min cadence):
##   cat ~/.claude/cross-chat/CCA_TO_POLYBOT.md | tail -100
##   → New delivery since last check? Implement NOW. Log in CHANGELOG.md.
##   → Delivery >48hr old? Write follow-up to POLYBOT_TO_CCA.md.
##   → Open guard candidate, CUSUM alert, or edge signal? Write REQUEST proactively.
##   ./venv/bin/python3 scripts/auto_guard_discovery.py  (new guards → add + restart)
##   ./venv/bin/python3 scripts/bet_analytics.py | grep "CUSUM\|DRIFT ALERT"  (act on findings)

## ⚠️ CCA HAS AUTHORITY TO EDIT THIS PROJECT (Matthew standing directive, S125):
## CCA (ClaudeCodeAdvancements) is authorized to:
##   - Write to ~/.claude/cross-chat/CCA_TO_POLYBOT.md (primary delivery channel)
##   - Write to this project's .planning/ directory (research findings, roadmap updates)
##   - Propose code changes via POLYBOT_TO_MAIN.md (monitoring chat implements after review)
## When CCA delivers code/scripts/findings: treat as authoritative, implement same session.
## Actively look for CCA deliveries. CCA helps this bot grow and self-improve.

## TO SEND REQUESTS TO CCA:
## Write to POLYBOT_TO_CCA.md or append to CROSS_CHAT_INBOX.md
## CCA reads these at its session start and responds via CCA_TO_POLYBOT.md

## COMMUNICATION PROTOCOL:
## - CCA provides: academic papers, statistical frameworks, tool research, scan findings
## - Kalshi Research provides: bet data analysis needs, strategy questions, outcome reports
## - Kalshi Main provides: live performance data, guard triggers, edge observations
## - All chats: maintain their normal roles AND communicate through these files

## PRIME DIRECTIVE (read KALSHI_PRIME_DIRECTIVE.md for full version):
## Three pillars: (1) Perfect current engine (2) Deep research (3) Expand beyond
## Objective: SMARTER AND MORE PROFITABLE. Self-sustaining at 250 USD/month.

## CURRENT DELIVERY (2026-03-18):
## CCA_TO_POLYBOT.md contains a complete universal bet analytics framework:
## - SPRT (Wald 1945) — edge detection
## - Wilson CI (Wilson 1927) — win rate confidence intervals
## - Brier Score (Brier 1950) — calibration check
## - CUSUM (Page 1954) — changepoint/drift detection
## - FLB analysis (Whelan 2024) — structural edge documentation
## All citations verified. Script scaffold included. Implement bet_analytics.py from it.
