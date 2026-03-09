# SKILLS REFERENCE — polymarket-bot
# Complete map of available skills/commands with token costs and polymarket-bot use cases.
# Updated: 2026-03-09 | Read this before starting any session.
# ══════════════════════════════════════════════════════════════

## TOKEN COST TIERS

| Tier | Tokens | What it means |
|------|--------|---------------|
| Free | 0-2k | Inline markdown instructions, no sub-agent |
| Low | 5-15k | CLI tool or single lightweight operation |
| Medium | 20-60k | One focused agent or deep analysis |
| Expensive | 100-150k | Multi-agent orchestration — use sparingly |

**Budget: 50% of 5-hour window per session. Each expensive skill = ~5-10% of budget.**

---

## TIER FREE — Use always, no cost penalty

| Skill | What it does | polymarket-bot use case |
|-------|-------------|------------------------|
| `gsd:add-todo` | Capture idea/task as structured todo | Any bug/idea that surfaces mid-session |
| `gsd:check-todos` | List all pending todos | Session start — see what's queued |
| `gsd:health` | Diagnose planning directory health | Session start only (once) |
| `gsd:progress` | Show current phase + next action | Session start only (once) |
| `wrap-up` | Session end checklist (tests, commit, docs) | Every session end — never skip |
| `titanium-context-monitor` | Warn before hitting context limit | Use when session is running long |

---

## TIER LOW — Default workhorse (~5-15k tokens each)

| Skill | What it does | polymarket-bot use case |
|-------|-------------|------------------------|
| `gsd:quick` | Atomic task with commit + STATE.md tracking | Bug fixes, small features — 90% of coding work |
| `gsd:quick --full` | Same + plan-checker + verifier | Higher-risk changes: kill_switch, live.py, main.py |
| `gsd:insert-phase` | Insert urgent work between phases | When something can't wait for next milestone |
| `sc:analyze` | Code quality/security/architecture scan | Pre-live audit on any strategy before promotion |
| `sc:analyze --focus security` | Security-specific scan | Before any new live strategy goes hot |
| `sc:analyze --focus testing` | Find coverage gaps | Identify untested paths (live.py had ZERO tests) |
| `sc:explain` | Clear explanation of code/concepts | Understanding kill_switch state machine, live.py flow |
| `sc:explain --think` | Deep explanation with structured analysis | Complex asyncio interactions, concurrency bugs |
| `sc:git` | Intelligent commit messages + git ops | When commits need better messages than ad-hoc |
| `sc:document` | Generate docs for a specific component | Document kill_switch state machine, live.py execution flow |
| `sc:test` | Run tests with coverage analysis | After any implementation — see gaps, not just pass/fail |
| `sc:help` | List all SuperClaude commands | Reference lookup |
| `sc:estimate` | Dev estimates for features | Planning time cost before committing to a feature |

---

## TIER MEDIUM — Use when the task warrants it (~20-60k tokens each)

| Skill | What it does | polymarket-bot use case |
|-------|-------------|------------------------|
| `sc:troubleshoot` | Systematic diagnosis: code/deploys/system | When `gsd:debug` feels overkill but `--health` isn't enough |
| `sc:troubleshoot --think` | Deep structured diagnosis | Kill switch state machine bugs, asyncio race conditions |
| `sc:improve` | Systematic code quality improvements | Polish btc_drift.py after calibration changes |
| `sc:improve --loop` | Iterative refinement with validation | Refactor live.py or kill_switch.py cleanly |
| `sc:research` | Deep web research with adaptive planning | Kalshi API changes, new market types, competitor strategy research |
| `sc:workflow` | Implementation workflow from requirements | Planning XRP drift or NBA game winner strategy |
| `sc:design` | Architecture + API design with specs | Designing a new platform integration (e.g., Polymarket.com when it opens) |
| `sc:spec-panel` | Multi-expert spec review | Validate a new strategy spec before building |
| `sc:business-panel` | Multi-expert business analysis | Expansion gate decisions, bankroll sizing strategy |
| `gsd:add-tests` | Generate tests for completed phase/feature | Close test coverage gaps — critical for live.py |
| `gsd:debug` | Systematic debugging with persistent state | When a bug resists 2+ inline attempts |
| `gsd:discuss-phase` | Gather context before planning | When approach is genuinely ambiguous |
| `anthropic-skills:schedule` | Create scheduled monitoring tasks | Build an autonomous monitoring cron that outlasts Claude sessions |
| `sc:analyze --think-hard` | Deep architectural analysis (~10k tokens) | Full execution path audit before Stage 2 promotion |

---

## TIER EXPENSIVE — Conditional only (~100-150k tokens each)

Only when ALL conditions: 5+ tasks, 4+ subsystems, multi-session work, PLAN.md needed.

| Skill | What it does | polymarket-bot use case |
|-------|-------------|------------------------|
| `gsd:plan-phase` | Create detailed PLAN.md with verification | XRP drift build, NBA game winner, Polymarket.com integration |
| `gsd:execute-phase` | Execute all plans in a phase with waves | Same — always pair with plan-phase |
| `gsd:map-codebase` | Parallel mapper agents → structured analysis docs | **Run once** when starting a new major feature to map affected subsystems |
| `gsd:verify-work` | Verifier agent for phase completion | End of milestone only, not quick tasks |
| `sc:spawn` | Meta-orchestration across multiple agents | Complex multi-system refactors |
| `sc:task` | Multi-agent workflow for complex tasks | Equivalent to gsd:execute-phase for non-GSD work |
| `gsd:new-milestone` | Start new milestone cycle | After graduating to Stage 2 ($10 bets) |

---

## SUPERCLAUDE FLAGS — Stack on any /sc:* command

These modify behavior without adding much cost. Use freely.

| Flag | Effect | When to use |
|------|--------|-------------|
| `--think` | Structured analysis ~4k tokens | Any multi-component analysis |
| `--think-hard` | Deep analysis ~10k tokens | Architecture decisions, kill switch redesign |
| `--focus security` | Security-targeted | Before any live promotion |
| `--focus testing` | Testing-targeted | After implementation, find gaps |
| `--focus performance` | Performance-targeted | If asyncio latency becomes a problem |
| `--loop` | Iterative improvement cycles | Polish passes on strategy code |
| `--validate` | Pre-execution risk assessment | Any change to live.py, kill_switch.py |
| `--safe-mode` | Maximum validation | Production-impacting changes |
| `--uc` / `--ultracompressed` | 30-50% token reduction | When context is getting full |
| `--token-efficient` | Symbol-enhanced comms | Long sessions approaching budget |

---

## POLYMARKET-BOT PLAYBOOK — Right skill for each situation

| Situation | Best skill | Why |
|-----------|-----------|-----|
| Quick bug fix or small feature | `gsd:quick` | Atomic commit, 90% of work |
| Change to live.py or kill_switch | `gsd:quick --full` + `sc:analyze --focus security` | Higher risk path |
| Pre-live audit for new strategy | `sc:analyze --think` | Checklist from CLAUDE.md §Step 5 |
| Bug resists inline diagnosis | `gsd:debug` or `sc:troubleshoot --think` | Persistent state helps |
| Want to understand complex code | `sc:explain --think` | Better than reading alone |
| Need tests for a module | `gsd:add-tests` or `sc:test` | Close coverage gaps fast |
| New strategy planning (XRP drift) | `sc:workflow` → `gsd:plan-phase` | Workflow first, then plan |
| Kalshi API research | `sc:research` | Web + doc synthesis |
| Strategy calibration analysis | Inline SQL + Python (no skill needed) | Already fast with direct DB |
| Session end | `wrap-up` | Never skip — updates handoff |
| Context limit approaching | `titanium-context-monitor` → `wrap-up` | Save state before forced stop |
| New milestone (Stage 2 unlock) | `gsd:new-milestone` | Proper ceremony |

---

## SKILLS TO START USING NOW (not yet in our workflow)

These are currently unused but directly applicable:

1. **`sc:analyze --focus security`** — Run before every live promotion. We caught 3 bugs in Session 20 post-live. This catches them pre-live.
2. **`sc:test`** — Surfaces coverage % per module. We'd have seen live.py at 0% earlier.
3. **`gsd:add-tests`** — Generate tests for completed features. eth_drift and sol_drift live paths need more coverage.
4. **`wrap-up`** — We've been doing manual session close. This automates the ritual.
5. **`gsd:debug`** — Use when a bug takes more than 2 inline attempts. Persistent state across context resets = valuable.
6. **`sc:troubleshoot --think`** — Better structured root cause analysis for kill_switch/asyncio issues.
7. **`anthropic-skills:schedule`** — Replace the polybot-monitor cron with a proper scheduled skill.
8. **`sc:research`** — Use before building any new market type (NBA props, CPI, XRP drift params).
9. **`sc:improve --loop`** — Polish passes on btc_drift.py after recalibration.
10. **`titanium-context-monitor`** — Check before starting expensive work; saves the session if context runs low.
