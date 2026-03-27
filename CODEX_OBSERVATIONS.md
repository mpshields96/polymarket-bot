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

(no entries yet)
