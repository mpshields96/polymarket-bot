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

## Code patterns
- Every module has `load_from_env()` or `load_from_config()` factory at bottom
- Stolen code gets `# Adapted from: https://github.com/...` at top of file
- Attribution for all refs: kalshi-btc, poly-apex, poly-gabagool, poly-official

## Workflow
- User runs with bypass permissions active — no confirmation needed
- Proactively invoke superpowers:* skills and sc:* commands without being asked
- Surface CHECKPOINT_N.md docs and wait for "continue" before next phase
- 59/59 tests must pass before any commit
