# BLOCKERS — Items needing Matthew
# Updated in real time by kill_switch.py. Surface at every checkpoint.
# Note: "Auth failure halt" entries are written automatically when auth fails.
# They are expected if .env / kalshi_private_key.pem are not yet set up.
═══════════════════════════════════════════════════

## BLOCKER: Kalshi 401 — Key ID does not match PEM
Severity: CRITICAL
Need: KALSHI_API_KEY_ID in .env does not match the kalshi_private_key.pem on disk.
Check:
  1. Go to kalshi.com → Settings → API
  2. Find the API key whose .pem you downloaded
  3. The "Key ID" shown is the SHORT alphanumeric string (not the .pem contents)
     It looks like: a1b2c3d4-1234-5678-abcd-ef0123456789  (UUID format)
  4. That Key ID must exactly match KALSHI_API_KEY_ID in .env
Fix:
  - Open .env (VS Code: open -a "Visual Studio Code" .env)
  - Replace KALSHI_API_KEY_ID with the correct Key ID from Kalshi dashboard
  - Run: python main.py --verify
  - Should show: ✅ Authenticated request — Balance: $X.XX (demo)
Status: OPEN — Matthew needs to correct Key ID in .env

═══════════════════════════════════════════════════
# Resolved blockers:

## RESOLVED: Binance.com WebSocket geo-blocked (HTTP 451)
Fix applied: Switched to wss://stream.binance.us:9443 in config.yaml, verify.py, binance.py

## RESOLVED: config.yaml missing 'storage' section
Fix applied: Added storage: db_path: data/polybot.db

## RESOLVED: kill_switch.lock blocking startup
Fix applied: Reset via echo "RESET" | python main.py --reset-killswitch
