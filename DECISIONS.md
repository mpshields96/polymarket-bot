# DECISIONS LOG
# Every fork in the road. What we chose and why.
═══════════════════════════════════════════════════

## Kalshi-only launch, Polymarket infra built now
Options: A) Kalshi only, no Poly code yet | B) Build both now, Poly inactive
Chosen: B
Reason: Matthew is on Polymarket waitlist. Building infra now means zero ramp-up when access arrives. Zero cost since it stays disabled.
Source: USER_CONFIG.json Q5 discussion
Reversible: Yes — delete src/platforms/polymarket.py and src/strategies/whale_copy.py

## Demo/paper mode as default
Options: A) Paper only | B) Demo (Kalshi sandbox) | C) Both
Chosen: B — Kalshi demo environment
Reason: Kalshi demo is functionally identical to prod. Free. Real behavior. Better than pure simulation.
Source: POLYBOT_INIT.md security rules
Reversible: Change config.yaml kalshi.mode: live (requires human action)

## Stage-based bet sizing included
Options: A) Flat $5 cap forever | B) Stage system that scales with bankroll
Chosen: B
Reason: At $50 Matthew is Stage 1 ($5 cap). Stage system activates naturally as bankroll grows. No downside.
Source: Bloat version Section 6, Matthew confirmed
Reversible: Yes — remove sizing.py stage logic, replace with flat cap

## CHECKPOINT_0 intel gate before writing bot code
Options: A) Skip intel, build directly | B) Read reference repos first
Chosen: B
Reason: Reference repos contain working RSA-PSS auth and kill switch patterns. Reading them prevents copying known bugs and saves hours.
Source: Bloat version Section 3, objectively agreed
Reversible: N/A — just a process gate

## RSA-PSS auth strategy
Options: A) Build from scratch | B) Steal from refs/kalshi-btc
Chosen: B
Reason: Working implementation already exists. Attribution comment added. Building from scratch risks signing bugs.
Source: POLYBOT_INIT.md Section 5
Reversible: Yes — rewrite src/auth/kalshi_auth.py

