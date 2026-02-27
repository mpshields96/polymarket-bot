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
- `config.yaml` series ticker must be `KXBTC15M` (not `btc_15min`) — wrong value returns 0 markets silently at DEBUG
- All `generate_signal()` skip paths log at DEBUG — trading loop appears silent when no signal fires (expected)
- **Binance.US `@trade` stream has near-zero BTC volume** — always use `@bookTicker` (mid-price = (bid+ask)/2, ~100 ticks/min)
- `tests/conftest.py` auto-cleans `kill_switch.lock` at session start/end — after interrupted test runs the lock won't block `main.py`
- `kill_switch._write_blockers()` skips BLOCKERS.md write when `PYTEST_CURRENT_TEST` env var is set — prevents test runs from polluting BLOCKERS.md
- Never run diagnostic scripts in background without an explicit kill after N seconds — unattended loops burn API credits/quota
- `bot.pid` is written at startup and removed on clean shutdown — prevents dual instances; if it exists after a crash, delete it before restarting
- The binding constraint for a signal is `min_edge_pct` (8%), NOT `min_btc_move_pct` — need ~0.65% BTC in 60s at current settings
- `settlement_loop` must pass `kill_switch` and call `record_win()`/`record_loss()` — otherwise consecutive-loss and total-loss hard stops are dead code
- Live mode requires BOTH `--live` flag AND `LIVE_TRADING=true` in .env; then user must type `CONFIRM` at runtime prompt — all three gates required
- `PermissionError` from `os.kill(pid, 0)` means the process IS alive under a different user — not stale; exit on `PermissionError`, skip on `ProcessLookupError`
- `_STALE_THRESHOLD_SEC = 35.0` in binance.py — Binance.US @bookTicker can be silent 10-30s; 10s threshold causes false stale signals
- 117/117 tests must pass before any commit (was 107 → +5 settlement → +5 PYTEST guard + dashboard path)

## Code patterns
- Every module has `load_from_env()` or `load_from_config()` factory at bottom
- Stolen code gets `# Adapted from: https://github.com/...` at top of file
- Attribution for all refs: kalshi-btc, poly-apex, poly-gabagool, poly-official

## Session startup (do this automatically, no prompting Matthew)
1. Read `SESSION_HANDOFF.md` — get current state + exact next action
2. Read `POLYBOT_INIT.md` → CURRENT STATUS section — confirm what works
3. Announce what you found in 2-3 lines, then ask "Ready to continue?" or just proceed
4. Do NOT ask setup questions — the project is fully built, auth works, tests pass

Current project state (updated each session):
- 117/117 tests passing, verify.py 18/18
- Trading loop confirmed: evaluates KXBTC15M every 30s, no signal yet (needs ~0.65% BTC in 60s)
- All critical safety fixes applied (kill switch wired, live CONFIRM prompt, PID lock)
- Paper mode only — LIVE_TRADING=false in .env
- GitHub: main branch, all sessions 1-9 committed (bf60715)
- Next action: `python main.py` → watch for first `[btc_lag] Signal:` log line

## Workflow
- User runs with bypass permissions active — no confirmation needed
- Proactively invoke superpowers:* skills and sc:* commands without being asked
- Matthew is a doctor with a new baby — keep explanations short, do the work autonomously
- Do NOT ask for confirmation on routine operations (running tests, reading files, updating docs)
- Surface CHECKPOINT_N.md docs and wait for "continue" before next phase
- 117/117 tests must pass before any commit
