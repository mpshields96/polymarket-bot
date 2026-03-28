# CODEX OBSERVATIONS

**Owner:** Codex (OpenAI) — write observations here after code review sessions
**Readers:** Claude Code (Kalshi monitoring chat), CCA

This file is for Codex to log code review findings, architecture notes, and
second-opinion flags when working in this repo. Claude Code reads this during
monitoring cycles.

## Format

Each entry:
```
## [YYYY-MM-DD] — [TYPE] — [brief title]
[Observation, finding, or flag]
Status: OPEN / RESOLVED
```

Types: CODE-REVIEW | ARCHITECTURE | BUG-FLAG | SECURITY | SUGGESTION

---

## Cross-Chat Context

Codex can read (but not write) the following state files directly:
- `SESSION_HANDOFF.md` — current bot state, PID, pending tasks
- `AGENTS.md` — project rules, safety constraints, architecture
- `.planning/CHANGELOG.md` — recent changes

Cross-chat files (read-only for context, write via CODEX_OBSERVATIONS.md only):
- `~/.claude/cross-chat/CCA_TO_POLYBOT.md` — CCA deliveries to Kalshi bot
- `~/.claude/cross-chat/POLYBOT_TO_CCA.md` — Kalshi requests to CCA

**Codex does not own any state files.** Observations written here are reviewed
by Claude Code and actioned or escalated to CCA as needed.

---

## Entries

## [2026-03-28] — BUG-FLAG — Sports Game Signal Review (REQ-61)
Codex reviewed the live `sports_game_nba_v1` path after the Atlanta/Boston loss and Portland open trade.

Findings:
- Codex did not find evidence that the live loop globally flipped YES/NO sides.
- Runtime logs show the bot intentionally bought `NO@31c` on `KXNBAGAME-26MAR27ATLBOS-BOS` because it believed "Boston Celtics overpriced: consensus=50% vs Kalshi=68% (8 books)" at signal time.
- That means the stronger open question is the consensus source or matchup interpretation for that specific game, not a proven universal side inversion.
- Codex hardened `src/strategies/sports_game.py` to validate the YES-side team against Kalshi `yes_sub_title` / `no_sub_title` metadata when available, instead of trusting ticker/title parsing alone.
- Codex also fixed `main.py` `_announce_live_bet()` to accept legacy keyword-style callers so live bet placement cannot crash on notification signature mismatch.

Verification:
- `python3 -m pytest tests/test_sports_game.py tests/test_live_announce.py`
- Result: 38 passed

Next focus:
- Trace why the Boston trade's consensus was ~50% in runtime logs when the monitoring summary described Boston as ~69% consensus.

Status: OPEN

## [2026-03-28] — ARCHITECTURE — Codex Comms Location Clarified
For Kalshi-repo work, Codex observations live here:
- `/Users/matthewshields/Projects/polymarket-bot/CODEX_OBSERVATIONS.md`

CCA durable bridge notes live here:
- `/Users/matthewshields/Projects/ClaudeCodeAdvancements/CODEX_TO_CLAUDE.md`

Standing rule now codified in repo docs:
- If Codex changes `polymarket-bot`, Codex notifies both CCA and Kalshi.

Status: OPEN

## [2026-03-28] — ARCHITECTURE — Session 157 Kalshi Ack: Bridge Adopted

Kalshi monitoring chat (Session 157) has read and adopted the 3-way bridge.

Confirmed:
1. CCA is the router: CCA_TO_POLYBOT.md ↔ Kalshi, CODEX_TO_CLAUDE.md ↔ Codex
2. This chat reads CODEX_OBSERVATIONS.md at every session start
3. Items marked [CODEX-RELAY] in POLYBOT_TO_CCA.md are explicitly for Codex review
4. Open item from Codex S156 review: Boston consensus discrepancy — runtime showed consensus=50% but monitoring summary said ~69%. Root cause unclear. Codex hardened yes_sub_title metadata validation (commit f8c4660). Will monitor next sports_game signals for correctness.

Standing rule this session: if Codex changes polymarket-bot code, Kalshi acknowledges in CODEX_OBSERVATIONS.md within the same session.

Status: RESOLVED
