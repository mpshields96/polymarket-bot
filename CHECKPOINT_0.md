# CHECKPOINT_0 — Intel & Architecture Review
# Date: 2026-02-25
# Gate: Human reviews before Phase 1 code begins
═══════════════════════════════════════════════════════════════════

## STATUS: READY FOR REVIEW

---

## ✅ COMPLETED THIS PHASE

- [x] .gitignore committed first (security-first)
- [x] USER_CONFIG.json written ($50 bankroll, Kalshi demo, Poly infra pending)
- [x] MASTER_LOG.md, DECISIONS.md, BLOCKERS.md, ERRORS_AND_FIXES.md initialized
- [x] SESSION_HANDOFF.md current
- [x] .claude/settings.json updated (acceptAll + deny list for dangerous commands)
- [x] Git initialized, 2 commits pushed to github.com/mpshields96/polymarket-bot
- [x] 5 reference repos cloned (kalshi-arb was 404 — deleted repo, logged)
- [x] All 5 repos fully analyzed
- [x] Titanium v36 read-only patterns extracted (architecture only, no betting logic)
- [x] INTEL.md written — what to steal, what to avoid, known bugs
- [x] ARCHITECTURE.md written — authoritative design doc for all code

---

## 📋 INTEL SUMMARY (key findings for Matthew)

### What we're stealing
| From | What | Why |
|------|------|-----|
| kalshi-btc | RSA-PSS auth (verbatim) | Battle-tested, correct, clean |
| kalshi-btc | Full async client + retry | Rate limiting + backoff built in |
| kalshi-btc | RiskManager class | Pre-trade checks, kill switch pattern |
| poly-apex | Kelly criterion + caps | Best Kelly implementation found |
| poly-gabagool | Pydantic config pattern | SecretStr prevents key logging |
| poly-official | HMAC signing (Polymarket) | Official SDK, reference quality |
| titanium-v36 | One-file-one-job architecture | Matthew's own proven pattern |

### What we're avoiding
| Bug | Where | Fix |
|-----|-------|-----|
| Query-param signing bug | kalshi-interface | Use kalshi-btc auth instead |
| Silent failures on 4xx | kalshi-interface | Use raise_for_status() pattern |
| Non-atomic file writes | poly-apex kelly.py | Use temp-file-then-rename |
| assert instead of exceptions | poly-official | Use ValueError/RuntimeError |

### kalshi-arb repo (404)
The vladmeer/kalshi-arbitrage-bot repo was deleted from GitHub. Not available.
Not a blocker — kalshi-btc covers everything we need.

---

## 🏗️ ARCHITECTURE DECISIONS LOCKED

1. **Async I/O, sync risk** — All API calls are async. Kill switch is synchronous. Non-negotiable.
2. **kill_switch.lock on disk** — Persists across restarts. Cannot be bypassed by restarting.
3. **Both env + flag for live** — LIVE_TRADING=true in .env AND --live at CLI. Both required.
4. **Polymarket built now, enabled=False** — Zero cost, ready when waitlist clears.
5. **Stage system active** — Stage 1 ($5 cap) now. Grows with bankroll + proven results.
6. **Config drives params, code enforces minimums** — Hard floors in code, not config.

---

## 🚫 BLOCKERS

None. Ready to proceed.

kalshi_private_key.pem: saved by Matthew in project folder ✓
Kalshi demo account: active, deposit accepted ✓
GitHub repo: connected, pushing successfully ✓

---

## ⏭️ PHASE 1 — What happens next (pending your approval)

1. Build full project folder structure
2. Write requirements.txt (pinned versions)
3. Write config.yaml
4. Write .env.example
5. Write setup/install.sh
6. Write src/auth/kalshi_auth.py (steal from kalshi-btc)
7. Write setup/verify.py (test Kalshi demo connection)
8. Write src/risk/kill_switch.py (steal from kalshi-btc + augment)
9. First tests: test_security.py + test_kill_switch.py
10. CHECKPOINT_1 → surface to Matthew

---

## HOW TO PROCEED

Reply **"continue"** to begin Phase 1.

Or reply with corrections/concerns before I write any code.

