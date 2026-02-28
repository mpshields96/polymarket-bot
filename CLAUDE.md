# CLAUDE.md — polymarket-bot

## Commands
`source venv/bin/activate && python -m pytest tests/ -v` - run tests (use python -m, not pytest directly)
`source venv/bin/activate && python setup/verify.py` - verify all connections before bot start
`python main.py --report` - today's P&L
`python main.py --reset-killswitch` - reset hard stop after reviewing KILL_SWITCH_EVENT.log

## Architecture rules (non-negotiable)
- One file, one job. If the job has "and" in it, split it.
- No `await` in `src/risk/` — kill switch and sizing are strictly synchronous
- `kill_switch.check_order_allowed()` is the LAST gate before every order
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
- 485/485 tests must pass before any commit (count updates each session)
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
- 440/440 tests passing, verify.py 18/26 (8 graduation WARNs — advisory, non-critical)
- 9 trading loops: btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
- **3 strategies LIVE: btc_lag_v1 + eth_lag_v1 + btc_drift_v1** ($75 bankroll, $5 max/bet)
- 6 other strategies → paper mode collecting calibration data
- Session 20: eth_lag LIVE, btc_drift LIVE, 4 live-trading bugs found+fixed, first live bet placed
- GitHub: main branch, latest commit: 188d01c
- Bot running: PID in bot.pid, log at /tmp/polybot_session20.log
- Restart: `pkill -f "python main.py"; sleep 3; rm -f bot.pid && echo "CONFIRM" | nohup python main.py --live >> /tmp/polybot_session21.log 2>&1 &`
  (NOTE: use pkill not kill — `kill $(cat bot.pid)` leaves orphaned old instances running)

## Workflow
- User runs with bypass permissions active — no confirmation needed
- Matthew is a doctor with a new baby — keep explanations short, do the work autonomously
- Do NOT ask for confirmation on routine operations (running tests, reading files, updating docs)
- Two parallel Claude Code chats may run simultaneously — keep framework overhead ≤10-15% per chat
- 485/485 tests must pass before any commit (count updates each session)
- **Before ANY new live strategy: complete all 6 steps of Development Workflow Protocol above**
- **After ANY bug fix: write regression test immediately, check sibling code**
- **Priority #1: write tests for live.py before adding features**

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
