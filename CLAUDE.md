# CLAUDE.md — polymarket-bot

## Commands
`source venv/bin/activate && python -m pytest tests/ -v` - run tests (use python -m, not pytest directly)
`source venv/bin/activate && python setup/verify.py` - verify all connections before bot start
`python main.py --report` - today's P&L
`python main.py --reset-killswitch` - reset hard stop after reviewing KILL_SWITCH_EVENT.log

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
- **RESTART PROCEDURE — use pkill not kill**: `kill $(cat bot.pid)` only kills the most recent instance; orphaned old instances keep running and place duplicate trades. Always restart with: `pkill -f "python main.py"; sleep 3; rm -f bot.pid; echo "CONFIRM" | nohup python main.py --live >> /tmp/polybot_session21.log 2>&1 &` — then verify with `ps aux | grep "[m]ain.py"` (should be exactly 1 process).
- **Paper/live separation** (fixed Session 21): `has_open_position()` and `count_trades_today()` now pass `is_paper` filter. Live daily cap counts live bets only. Paper bets no longer eat into live quota.
- 540/540 tests must pass before any commit (count updates each session)
- **`confidence` field in Signal is computed but never consumed** (not used in sizing, kill switch, or main.py). It's a dead field — low priority to wire in or remove.
- **eth_drift uses BTCDriftStrategy internally** — logs say `[btc_drift]` and "BTC=ETH_price". Cosmetic only. `btc_feed=eth_feed` in main.py call is correct.
- **settlement_loop uses `paper_exec.settle()` for live trades too** — logs say `[paper] Settled` even for live trades. Cosmetic only; P&L math and DB update are correct.
- **late_penalty in btc_drift reduces `confidence` but NOT `edge_pct`** — so late-reference signals still show high edge_pct. Capped at $5 hard max anyway, so no real money impact.
- **btc_drift has no price extremes filter** — fires at 3¢/97¢ even though sigmoid was calibrated on near-50¢ data. At extremes the model is extrapolating; HFTs have usually priced in certainty for good reason. Fix: add min_signal_price_cents=10 / max_signal_price_cents=90. See .planning/todos.md.
- **`--status`, `--report`, `--graduation-status`** all bypass bot PID lock — safe while live
- **`--report`**: now shows per-strategy breakdown (bets, W/L, P&L, live/paper emoji)
- **`scripts/notify_midnight.sh`**: midnight UTC daily P&L Reminders notifier — start once with `& echo $! > /tmp/polybot_midnight.pid`
- **unemployment_rate_v1**: uses `math.erfc` for normal CDF (no scipy). Shares fred_feed with fomc_loop.
- **KXUNRATE markets**: open ~2 days before BLS release. No open markets outside that window = expected.
- **Sports markets on Kalshi**: KXNBA/KXMLB are season-winner markets (illiquid, months to settle) — not suitable. KXNBAGAME/KXNHLGAME are game-by-game winners (skeleton built, disabled).
- **eth_lag min_edge_pct**: 0.04 as of Session 20 (was 0.08). LIVE — same rationale as btc_lag sweep.
- **`_FIRST_RUN_CONFIRMED` in live.py**: module-level global that triggers `input()` on first execution. When stdin is piped, gets "" ≠ "CONFIRM" → returns None silently. Fixed in Session 20: main.py sets `_live_exec_mod._FIRST_RUN_CONFIRMED = True` after startup confirmation.
- **`kalshi_payout(yes_price_cents, side)` always expects YES price** — for NO-side signals, convert: `yes_for_payout = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)`. Bug fixed in Session 20.
- **`live.py` `strategy_name` parameter**: was hardcoded as "btc_lag". Now passed as `strategy.name` from trading_loop. Fixed in Session 20.
- **`src/execution/live.py` has ZERO unit tests** — highest priority testing gap. Before adding any new live strategy, write integration tests for this file.
- **`calculate_size()` signature requires `payout_per_dollar`, NOT `price_cents`** — paper loops (weather/fomc/unemployment) had this bug (Session 22). Always compute `payout = kalshi_payout(yes_price, side)` first, then pass `payout_per_dollar=payout`. Bug pattern: `calculate_size(price_cents=..., ...)` raises TypeError silently caught by outer except. Regression tests in TestPaperLoopSizingCallSignature.
- **Stage promotion is gated on Kelly calibration, not just bankroll** — bankroll crossed $100 (Stage 2 threshold) but Stage 2 ($10 max/bet) requires 30+ live settled bets with `limiting_factor=="kelly"` + Brier < 0.25 on live bets. See docs/GRADUATION_CRITERIA.md v1.1 Stage Promotion section. Do NOT raise bet cap yet.
- **Kelly sizing is invisible at Stage 1** — $5 cap always binds before Kelly; we can't evaluate Kelly calibration until Stage 2+ where bet can be between $5 and $10. Don't trust Kelly for promotion decisions until ~30 live settled bets at Stage 2.
- **Volatility × Kelly interaction** — static signal thresholds (min_edge_pct) mean no signals on calm days; Kelly scales bet size with edge within the stage cap. Both are intentional. See .planning/todos.md "Volatility-Adaptive Parameters" for future roadmap item (don't build yet).
- **`calculate_size()` returns a `SizeResult` dataclass, NOT a float** — paper loops must extract `.recommended_usd` before passing to `paper_exec.execute(size_usd=...)`. Pattern: `_trade_usd = min(_size_result.recommended_usd, _HARD_CAP)`. Bug fixed Session 22 in weather/fomc/unemployment loops. Regression tests in TestPaperLoopSizeExtraction.
- **strategy `_min_edge_pct` must be passed to `calculate_size(min_edge_pct=...)`** — default is 8%, but btc_lag fires at 4% and btc_drift at 5%. Without this, valid 4-7.9% edge signals are silently dropped. Bug fixed Session 22 (4ae55bd). Pattern: `_strat_min_edge = getattr(strategy, '_min_edge_pct', 0.08)`. Regression tests in TestStrategyMinEdgePropagation.
- **KILL_SWITCH_EVENT.log is polluted by test runs** — `_hard_stop()` writes to the live event log even during pytest. Events timestamped during tests look like real trading stops. Root cause: no `PYTEST_CURRENT_TEST` guard (unlike `_write_blockers()`). Fix logged in .planning/todos.md. Don't be alarmed by mysterious hard stops that don't match DB data.
- **Price range guard applies to ALL lag strategies (Session 23 cont'd)**: btc_lag/eth_lag/sol_lag share `_MIN_SIGNAL_PRICE_CENTS=10` and `_MAX_SIGNAL_PRICE_CENTS=90` guard in btc_lag.py. btc_drift.py has its own identical guard. eth_lag placed NO@2¢ live bet (trade_id=90) AFTER btc_drift was fixed — always check sibling strategies for same pattern.
- **Daily loss counter DID NOT persist across restarts** (fixed Session 23 cont'd): on restart, `_daily_loss_usd` reset to 0 in memory, bypassing the daily limit. Fix: `db.daily_live_loss_usd()` queries settled losses since midnight UTC; `kill_switch.restore_daily_loss()` seeds the counter; called from main.py on startup. Consecutive loss counter intentionally resets (restart = manual soft stop override).
- **Paper-during-softkill (Session 23)**: Soft stops (daily loss, consecutive losses, hourly rate) block LIVE bets only. Paper data collection continues uninterrupted during soft kills. `check_paper_order_allowed()` is used in all paper paths; only hard stops + bankroll floor block paper trades. btc_lag/eth_lag/btc_drift live paths still use `check_order_allowed()` (all stops apply).
- **Kill switch thresholds (Session 23)**: consecutive_loss_limit=4 (was 5), daily_loss_limit=20% ($20 on $100 bankroll, was 15%). Both updated in `src/risk/kill_switch.py` constants.
- **KXBTC1H does NOT exist** — Kalshi has no hourly BTC/ETH price-direction markets. Only 15-min series: KXBTC15M, KXETH15M, KXSOL15M, KXXRP15M, KXBNB15M, KXBCH15M. Confirmed by probing all 8,719 Kalshi series (Session 23).
- **sol_lag_v1** (Session 23): paper-only KXSOL15M loop, SOL feed at `wss://stream.binance.us:9443/ws/solusdt@bookTicker`, min_btc_move_pct=0.8 (SOL ~3x more volatile than BTC). Reuses BTCLagStrategy with name_override="sol_lag_v1".
- **Odds API — 1,000 credit hard cap for this bot** — Matthew has 20,000/month total (renewed March 1). polymarket-bot is capped at 5% (1,000 credits). Implement OddsApiQuotaGuard before ANY API call. Sports props/moneyline/spreads are for a SEPARATE system (see .planning/todos.md). Do not mix.

## Code patterns
- Every module has `load_from_env()` or `load_from_config()` factory at bottom
- Stolen code gets `# Adapted from: https://github.com/...` at top of file
- Attribution for all refs: kalshi-btc, poly-apex, poly-gabagool, poly-official

## Session startup (do this automatically, no prompting Matthew)
1. Read `SESSION_HANDOFF.md` — get current state + exact next action
2. Read `POLYBOT_INIT.md` → CURRENT STATUS section — confirm what works
3. Announce what you found in 2-3 lines, then proceed
4. Do NOT ask setup questions — the project is fully built, auth works, tests pass

Current project state (updated each session):
- 559/559 tests passing, verify.py 18/26 (8 graduation WARNs — advisory, non-critical)
- 10 trading loops: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate, sol_lag
- **3 strategies LIVE: btc_lag_v1 + eth_lag_v1 + btc_drift_v1** ($5 max/bet)
- Latest commit: a43a1cf — daily loss persistence fix
- Kill switch: consecutive loss limit = 4 (was 5), daily loss limit = 20% ($20, was 15%)
- Paper-during-softkill: check_paper_order_allowed() in all paper loops — soft stops block live only
- Price range guard 10-90¢: active on BOTH btc_drift.py AND btc_lag.py (applied to all 3 lag strategies)
- Daily loss counter restored from DB on restart — prevents mid-session restart from bypassing daily limit
- 7 paper strategies → calibration data collection (including new sol_lag_v1 paper loop)
- Bot running: PID in bot.pid, log at /tmp/polybot.log (stable symlink) or /tmp/polybot_session21.log
- Restart: `kill -9 $(cat bot.pid); sleep 2; rm -f bot.pid && echo "CONFIRM" | nohup /Users/matthewshields/Projects/polymarket-bot/venv/bin/python main.py --live >> /tmp/polybot_session21.log 2>&1 &`
  (ALWAYS use full venv python path + pkill — never `kill $(cat bot.pid)` and never bare `python`)

## Workflow — ALWAYS AUTONOMOUS (Matthew's standing directive, never needs repeating)
- **Bypass permissions ACTIVE — operate fully autonomously at all times**
- **Never ask for confirmation** on: running tests, reading files, editing code, committing, restarting the bot, running reports, researching
- **Do the work first, summarize after** — Matthew is a doctor with a new baby, no time for back-and-forth
- **Security first, always**: never expose .env / API keys / pem files; never run untrusted code; never modify system files outside the project directory
- **Never break the bot**: before any restart or config change, confirm the current bot is running or stopped; always verify single instance after restart
- Two parallel Claude Code chats may run simultaneously — keep framework overhead ≤10-15% per chat
- 540/540 tests must pass before any commit (count updates each session)
- **Before ANY new live strategy: complete all 6 steps of Development Workflow Protocol above**
- **Graduation → live promotion**: when `--graduation-status` shows READY FOR LIVE, run the full Step 5 pre-live audit checklist before flipping `live_executor_enabled=True` in main.py. Session 20 lost 2 hours of live bets to silent bugs found only after going live — catch them in Step 5 first.
- **EXPANSION GATE (Matthew's standing directive)**: Do NOT build new strategy types until current live strategies are producing solid, consistent results. Hard gate: btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks of live P&L data + no kill switch events + no silent blockers. Until then: log ideas to .planning/todos.md only. Do not build.
- **After ANY bug fix: write regression test immediately, check sibling code**
- **Priority #1: write tests for live.py before adding features**

## Context Handoff Protocol — MANDATORY when approaching token limit
When context is near limit, BEFORE stopping:
1. `python main.py --report` + `python main.py --graduation-status` → capture output
2. `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo running` → confirm bot alive
3. Update SESSION_HANDOFF.md: bot PID, log path, last commit, pending tasks, mid-flight work
4. Update this file's "Current project state" section (test count, commit hash, strategies live)
5. `git add -A && git commit -m "docs: session handoff $(date +%Y-%m-%d)"` + git push
6. Output a self-contained copy-paste prompt for the new chat that picks up at the exact second
7. The new-chat prompt must include: bot PID, log path, last commit, next concrete action

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
