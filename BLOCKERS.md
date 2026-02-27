# BLOCKERS — Items needing Matthew
# Updated in real time by kill_switch.py. Surface at every checkpoint.
# Note: "Auth failure halt" entries are written automatically when auth fails.
# They are expected if .env / kalshi_private_key.pem are not yet set up.
═══════════════════════════════════════════════════

# No open blockers. Auth working, verify.py 18/18 ✅.

═══════════════════════════════════════════════════
# Resolved blockers:

## RESOLVED: Kalshi 401 — Key ID does not match PEM
Fix applied: Correct Key ID set in .env. verify.py 18/18 passing. Balance $75 confirmed.

## RESOLVED: Binance.com WebSocket geo-blocked (HTTP 451)
Fix applied: Switched to wss://stream.binance.us:9443 in config.yaml, verify.py, binance.py

## RESOLVED: Binance.US @trade stream zero volume
Fix applied: Switched to @bookTicker stream (~100 ticks/min). btc_move_pct() returning real values.

## RESOLVED: config.yaml missing 'storage' section
Fix applied: Added storage: db_path: data/polybot.db

## RESOLVED: kill_switch.lock blocking startup
Fix applied: Reset via echo "RESET" | python main.py --reset-killswitch
             + tests/conftest.py now cleans lock at test session start/end automatically.

## NOTE: Auth failure halt entries (auto-appended by kill_switch.py)
kill_switch.py appends "Auth failure halt" entries when 3 consecutive Kalshi auth failures
occur. This fires during diagnostic scripts and --verify runs that make real API calls.
FIXED 2026-02-27: kill_switch._write_blockers() now skips write when PYTEST_CURRENT_TEST
is set, so test runs no longer pollute this file.
