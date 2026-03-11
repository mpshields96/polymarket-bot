# SKILLS REFERENCE — polymarket-bot
# Complete map of available skills/commands with token costs and polymarket-bot use cases.
# Updated: 2026-03-10 (Session 44) — community-sourced additions from r/ClaudeCode + r/vibecoding
# ══════════════════════════════════════════════════════════════

## QUICK DECISION MATRIX — first match wins

| Situation | Skill | Cost |
|-----------|-------|------|
| Designing/building something NEW, approach unclear | `superpowers:brainstorm` | Expensive |
| About to write ANY implementation code | `superpowers:TDD` | Free |
| Design approved — multi-file plan needed | `superpowers:write-plan` | Low |
| Plan approved — ready to execute | `superpowers:execute-plan` or `gsd:execute-phase` | Expensive |
| Bug to diagnose | `superpowers:systematic-debugging` | Free |
| Claiming work is done | `superpowers:verification-before-completion` | Free |
| Start of formal multi-session phase (5+ tasks, 4+ subsystems) | `gsd:discuss-phase` → `gsd:plan-phase` → `gsd:execute-phase` | Expensive |
| One-off fix, small feature | `gsd:quick` | Low |
| Pre-live strategy audit | `sc:analyze --focus security` | Low |
| Need test coverage report | `sc:test` or `gsd:add-tests` | Low |
| Bug resists 2+ inline attempts | `gsd:debug` or `sc:troubleshoot --think` | Medium |
| New brownfield project/major feature audit | `gsd:map-codebase` | Expensive (once) |
| Session START (once only) | `gsd:health` + `gsd:progress` | Free |
| Session END | `wrap-up` | Free |
| Idea or issue surfaces | `gsd:add-todo` | Free |

---

## TOKEN COST TIERS

| Tier | Tokens | What it means |
|------|--------|---------------|
| Free | 0-2k | Inline markdown instructions, no sub-agent |
| Low | 5-15k | CLI tool or single lightweight operation |
| Medium | 20-60k | One focused agent or deep analysis |
| Expensive | 100-150k | Multi-agent orchestration — use sparingly |

**Budget: 50% of 5-hour window per session. Each expensive skill = ~15-25% of budget.**

---

## SUPERPOWERS (obra/superpowers) — Community-rated #1 plugin

### THE #1 SKILL: superpowers:brainstorm
Community verdict across r/ClaudeCode, r/vibecoding, r/AI_agents: single most useful skill.
- Forces Claude to ask clarifying questions BEFORE writing any code
- Explores alternatives, presents design in sections for validation
- Saves design document before implementation begins
- Prevents "built the wrong thing" failures

### TIER 1 — Use on nearly every coding task

| Skill | Command | Trigger | What it does |
|-------|---------|---------|-------------|
| brainstorm | `superpowers:brainstorm` | Before building anything new | Socratic Q&A → design doc → prevents wrong-direction builds |
| TDD | auto-triggers | Before ANY implementation code | RED-GREEN-REFACTOR cycle. Write failing test first. MANDATORY. |
| write-plan | `superpowers:write-plan` | After design approved, before multi-file work | Breaks work into 2-5 min tasks with exact file paths + verification |
| execute-plan | `superpowers:execute-plan` | Plan approved and saved | Dispatches fresh subagent per task, 2-stage review per task |
| verification-before-completion | auto-triggers | Before marking any work done | Multi-layer validation before closing a task |

### TIER 2 — Context-dependent

| Skill | Command | Trigger | What it does |
|-------|---------|---------|-------------|
| systematic-debugging | auto-triggers | Bug investigation | 4-phase root cause: reproduce → isolate → identify → verify fix |
| deep-investigation | auto-triggers | Complex cascading failures | Dependency chain analysis, tracing system interactions |
| using-git-worktrees | auto-triggers | After design approval (complex work) | Isolated workspace on new branch, clean test baseline |
| skill-creator | `anthropic-skills:skill-creator` | Teaching Claude domain-specific patterns | Feed it a technical doc → Claude writes project-specific skills |

### SLEEPER: skill-creator
Give Claude a technical book or reference doc: "Read this, internalize it, write the new skills
you learned." Claude builds domain-specific skills (Kalshi API patterns, SQLite workflows,
risk management rules). This is how Superpowers self-extends into your specific domain.
Directly applicable: feed it KALSHI_BOT_COMPLETE_REFERENCE.pdf.

---

## GSD (get-shit-done) — Community workflow backbone

### THE CORE WORKFLOW: discuss → plan → execute → verify
- Each phase runs in a FRESH context window (200k clean tokens)
- Zero accumulated conversation history per execution
- Each completed task gets its own atomic git commit
- Verification agent checks codebase against phase goals after execution

### TIER 1 — The core four (in order for formal phases)

| Skill | Command | When | What it does |
|-------|---------|------|-------------|
| discuss-phase | `gsd:discuss-phase N` | Start of EVERY formal phase, before planning | Code-aware Q&A. Analyzes source files. Captures decisions before planning. |
| plan-phase | `gsd:plan-phase N` | After discuss, before execute | 4 parallel research agents → atomic XML plans (max 3 tasks each) |
| execute-phase | `gsd:execute-phase N` | After plan approved | Wave-based parallel execution. Each task = fresh Claude session + git commit. |
| verify-work | `gsd:verify-work N` | After execute completes | Guided UAT. Fails auto-create fix plans. Re-run execute to apply. |

### TIER 1 — Daily workhorse

| Skill | Command | When | What it does |
|-------|---------|------|-------------|
| quick | `gsd:quick` | 90% of coding work — one-off fixes, small features | Atomic commit + STATE.md tracking. Skip optional agents. |
| quick --full | `gsd:quick --full` | Higher-risk changes (kill_switch, live.py, main.py) | Same + plan-checker + verifier |
| quick --discuss | `gsd:quick --discuss` | When approach needs clarification first | Gathers context before quick task |

### TIER 2 — Power user

| Skill | Command | When | What it does |
|-------|---------|------|-------------|
| map-codebase | `gsd:map-codebase` | FIRST command on existing project; before major feature | 4 parallel agents → ARCHITECTURE.md + CONCERNS.md. Keep/strip/rebuild audit. |
| add-todo | `gsd:add-todo` | ANY idea or issue surfaces mid-session | Captures as structured todo immediately |
| health | `gsd:health` | Session START only (once) | Diagnose planning directory health |
| progress | `gsd:progress` | Session START only (once) | Current phase + next action |
| add-tests | `gsd:add-tests` | After completing a feature | Generate tests based on UAT criteria |
| debug | `gsd:debug` | Bug resists 2+ inline attempts | Persistent debug state across context resets |
| new-milestone | `gsd:new-milestone` | Starting new version (e.g., Stage 2 unlock) | Define → build → ship cycle for next milestone |
| insert-phase | `gsd:insert-phase` | Urgent work that can't wait | Insert as decimal phase (e.g., 45.1) between existing phases |

---

## SUPERCLAUDE (sc:*) — SuperClaude plugin

### TIER LOW — Use freely

| Skill | When | polymarket-bot use case |
|-------|------|------------------------|
| `sc:analyze` | Pre-live audit, architecture review | Full execution path before any strategy goes live |
| `sc:analyze --focus security` | Before any live promotion | Catches hardcoded values, kill switch bypass patterns |
| `sc:analyze --focus testing` | After implementation | Find uncovered paths (live.py was 0% in Session 20) |
| `sc:analyze --think` | Deep architectural analysis | kill_switch state machine, asyncio flow |
| `sc:explain` | Understanding complex code | kill_switch mechanics, live.py execution flow |
| `sc:explain --think` | Deep structured explanation | Complex asyncio interactions, concurrency bugs |
| `sc:git` | Clean commit messages | Better than ad-hoc when commit matters |
| `sc:document` | Generating component docs | kill_switch state machine, live.py execution flow |
| `sc:test` | Coverage report after implementation | See gaps, not just pass/fail |
| `sc:estimate` | Planning time before committing | Cost estimation before starting a feature |

### TIER MEDIUM

| Skill | When | polymarket-bot use case |
|-------|------|------------------------|
| `sc:troubleshoot` | Systematic diagnosis | When `gsd:debug` feels overkill but `--health` isn't enough |
| `sc:troubleshoot --think` | Deep structured diagnosis | Kill switch state machine bugs, asyncio race conditions |
| `sc:improve` | Code quality improvements | Polish btc_drift.py after calibration changes |
| `sc:improve --loop` | Iterative refinement | Refactor live.py or kill_switch.py cleanly |
| `sc:research` | Deep web research | Kalshi API changes, new market types, competitor strategy |
| `sc:workflow` | Implementation workflow from requirements | Planning new strategy before gsd:plan-phase |
| `sc:design` | Architecture + API design | New platform integration (Polymarket.com when it opens) |
| `sc:business-panel` | Multi-expert business analysis | Expansion gate decisions, bankroll sizing |

### TIER EXPENSIVE

| Skill | When | polymarket-bot use case |
|-------|------|------------------------|
| `sc:spawn` | Meta-orchestration across multiple agents | Complex multi-system refactors |
| `sc:task` | Multi-agent workflow for complex tasks | Equivalent to gsd:execute-phase for non-GSD work |

---

## SUPERCLAUDE FLAGS — Stack on any /sc:* command

| Flag | Effect | When to use |
|------|--------|-------------|
| `--think` | Structured analysis ~4k tokens | Any multi-component analysis |
| `--think-hard` | Deep analysis ~10k tokens | Architecture decisions, kill switch redesign |
| `--focus security` | Security-targeted scan | Before any live promotion |
| `--focus testing` | Testing-targeted scan | After implementation, find gaps |
| `--focus performance` | Performance-targeted scan | If asyncio latency becomes a problem |
| `--loop` | Iterative improvement cycles | Polish passes on strategy code |
| `--validate` | Pre-execution risk assessment | Any change to live.py, kill_switch.py |
| `--safe-mode` | Maximum validation | Production-impacting changes |
| `--uc` / `--ultracompressed` | 30-50% token reduction | When context is getting full |

---

## COMMUNITY CONSENSUS STACK (r/ClaudeCode, March 2026)

**Plugins (4):**
1. `obra/superpowers` — core workflow discipline (TDD, debugging, brainstorm)
2. Language Server (pyright for Python) — type checking inline
3. `commit-commands` — clean git commit messages
4. `pr-review-toolkit` — code review before merge

**MCPs (2 — keep it to 2, more kills context budget):**
1. Context7 — live version-specific API docs (prevents broken auth patterns, deprecated endpoints)
2. Sequential Thinking — structured reasoning for complex tasks

**GSD + Superpowers combined workflow:**
```
/gsd:discuss-phase → /superpowers:brainstorm →
Superpowers TDD → /gsd:execute-phase → /gsd:verify-work
```

**Key insight (906 upvotes):** "Keep CLAUDE.md short (~1K context). Use Skills for 'context on demand'.
Ensure skill descriptions contain your trigger keywords or skills won't activate."

---

## CONTEXT7 — WHY IT MATTERS FOR THIS PROJECT

Context7 pulls live, version-specific library documentation into Claude's context before
generating any API client code. For projects using external APIs (Kalshi, Binance, Streamlit),
Claude's training data on API specifics is often outdated. Context7 prevents:
- Broken auth patterns (Kalshi RSA-PSS format changes)
- Deprecated endpoints (we already hit one in Session 44 audit)
- Wrong parameter names on first attempt

Install: `claude mcp add context7 -- npx -y @upstash/context7-mcp@latest`

---

## POLYMARKET-BOT PLAYBOOK — Right skill for each situation

| Situation | Best skill | Why |
|-----------|-----------|-----|
| Quick bug fix or small feature | `gsd:quick` | Atomic commit, 90% of work |
| New design/architecture needed | `superpowers:brainstorm` | Prevents wrong-direction builds |
| About to write code | `superpowers:TDD` | Failing test first, always |
| Multi-file work ready to start | `superpowers:write-plan` | Exact tasks with file paths |
| Change to live.py or kill_switch | `gsd:quick --full` + `sc:analyze --focus security` | Higher risk path |
| Pre-live audit for new strategy | `sc:analyze --think` | Checklist from CLAUDE.md §Step 5 |
| Bug resists inline diagnosis | `gsd:debug` or `sc:troubleshoot --think` | Persistent state helps |
| Want to understand complex code | `sc:explain --think` | Better than reading alone |
| Need tests for a module | `gsd:add-tests` or `sc:test` | Close coverage gaps fast |
| New strategy planning (formal phase) | `gsd:discuss-phase` → `gsd:plan-phase` | Discuss first |
| Kalshi API/market research | `sc:research` | Web + doc synthesis |
| **Statistical performance analysis of live bets** | **`sc:analyze --think`** | **Directional bias, Brier trends, price bucket analysis — MUCH better than manual SQL** |
| **Before claiming any analysis is complete** | **`superpowers:verification-before-completion`** | **Free — validates findings, catches missed edge cases** |
| Session start | `gsd:health` + `gsd:progress` (once each) | Check state before work |
| Session end | `wrap-up` | Never skip — updates handoff |
| Context limit approaching | `titanium-context-monitor` → `wrap-up` | Save state before forced stop |
| New milestone (Stage 2 unlock) | `gsd:new-milestone` | Proper ceremony |
| Domain-specific skill creation | `anthropic-skills:skill-creator` | Feed it reference docs |
| **Capturing multiple pending items at once** | **`gsd:add-todo` (multiple times)** | **FREE — should be used for EVERY pending item, not just one** |

---

## SKILLS TO START USING NOW (not yet in our workflow)

1. **`superpowers:brainstorm`** — Use before designing any new module. The community calls this the #1 skill. We've been skipping it and building directly from vague requirements.
2. **`superpowers:write-plan`** — After design, before multi-file implementation. Creates exact task list with file paths. We've been doing this informally.
3. **`sc:analyze --focus security`** — Run before every live promotion. We caught 3 bugs in Session 20 post-live. This catches them pre-live.
4. **`sc:test`** — Surfaces coverage % per module. We'd have seen live.py at 0% earlier.
5. **`gsd:add-tests`** — Generate tests for completed features. eth_drift and sol_drift live paths need more coverage.
6. **`gsd:debug`** — Use when a bug takes more than 2 inline attempts. Persistent state across context resets = valuable.
7. **`anthropic-skills:skill-creator`** — Feed it KALSHI_BOT_COMPLETE_REFERENCE.pdf to build Kalshi-specific skills.
8. **`sc:research`** — Use before building any new market type (CPI, KXBTCD hourly, barrier options).
9. **`titanium-context-monitor`** — Check before starting expensive work; saves the session if context runs low.
10. **`wrap-up`** — We've been doing manual session close. This automates the ritual.
