# BLOCKERS — Items needing Matthew
# Updated in real time by kill_switch.py. Surface at every checkpoint.
# Note: "Auth failure halt" entries are written automatically when auth fails.
# They are expected if .env / kalshi_private_key.pem are not yet set up.
# All auth failure entries below consolidate to the single blocker at the top.
═══════════════════════════════════════════════════

## BLOCKER: Kalshi auth not yet verified
Severity: CRITICAL
Need: Bot has not been run against the live demo API yet.
      Kalshi auth will fail until keys are set up.
Check:
  1. Do you have a .env file with KALSHI_API_KEY_ID set?
  2. Is kalshi_private_key.pem in the project root?
  3. Run: python main.py --verify
Fix: If auth fails, re-download the .pem from Kalshi dashboard,
     confirm KALSHI_API_KEY_ID matches the key shown in Kalshi Settings → API.
     See setup instructions in POLYBOT_INIT.md → KALSHI AUTH section.
Status: OPEN — needs Matthew to set up .env + .pem then run --verify

═══════════════════════════════════════════════════
# Resolved blockers are moved below this line:
# (none yet)
