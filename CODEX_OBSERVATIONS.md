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

## [2026-04-05] — ARCHITECTURE — Verified Night Stop Procedure For Codex
Codex verified the correct routine stop path for the live bot.

Procedure:
- Read PID from `bot.pid`
- Send clean shutdown: `kill -TERM "$PID"`
- Wait until `kill -0 "$PID" 2>/dev/null` fails
- If the process is gone but `bot.pid` remains, remove it with `rm -f bot.pid`

Observed behavior on live stop verification:
- `main.py` logged `Received SIGTERM — requesting clean shutdown`
- The process exited cleanly without requiring `pkill` or `kill -9`
- `bot.pid` remained stale and needed manual removal after process exit

Standing rule for future Codex chats:
- Use `SIGTERM` first for overnight/manual stop
- Reserve restart-style `pkill` / `kill -9` sequences for failed shutdowns or restart workflows, not routine pauses

Status: RESOLVED

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

## [2026-04-03] — CCA UPDATE — REQ-66 Answer Landed
CCA/Codex delivered a direct REQ-66 answer to the live outbox.

New delivery:
- `~/.claude/cross-chat/CCA_TO_POLYBOT.md`
- Timestamp: `2026-04-03 16:05 UTC`
- Full note: `/Users/matthewshields/Projects/ClaudeCodeAdvancements/research/KALSHI_REQ66_TIMING_CPI_UCL_2026-04-03.md`

Operational verdict:
1. Sports game markets should be treated as same-day afternoon / pre-start opportunities, not reliable 8-14h-early markets.
2. UCL game markets exist as a Kalshi product line (`KXUCLGAME` via official market-maker docs), but season-winner futures should not be used as the substitute plan.
3. April 10 CPI is a real BLS-timed event, but should be micro-live only on first deployment (1-2 USD cap), not full-size live.
4. MVE / combos remain a skip.

Status: OPEN

## [2026-04-03] — CCA UPDATE — kalshi-check Hardened For REQ-66
CCA/Codex verified and upgraded:
- `python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/cross_chat_board.py kalshi-check`

It now returns:
- `latest_delivery_heading`
- `latest_request_heading`
- `req66_answered`
- `action_hint`

Current expected meaning:
- if `has_new_delivery` is true, read `~/.claude/cross-chat/CCA_TO_POLYBOT.md`
- then run `python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/cross_chat_board.py kalshi-mark-seen`
- REQ-66 should now show as answered in the helper output

Status: OPEN

## [2026-04-03] — CCA UPDATE — kalshi-check Now Returns Explicit REQ Arrays
Latest CCA-side hardening:
- `kalshi-check` now exposes machine-ready fields:
  - `should_read_outbox`
  - `latest_delivery_req_ids`
  - `latest_request_req_ids`
  - `req66_answered`

Meaning:
- Kalshi loop no longer needs to string-match headings to know whether REQ-66 is answered
- it can branch on REQ arrays directly

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

## [2026-03-28] — BUG-FLAG — Boston Consensus Discrepancy: Engine Side Resolved
Codex traced the Atlanta/Boston sports_game path further after the `NO@31c` loss.

Findings:
- The live engine log and the persisted trade row agree on the signal inputs: Boston YES consensus was about 50%, not 69%.
- Evidence: `logs/errors/bot.log` logged `Boston Celtics overpriced: consensus=50% vs Kalshi=68% (8 books)`, and `reports/trades.csv` stored `win_prob=0.5007` for the live `NO` trade.
- For a `NO` trade, that stored `win_prob` implies a YES-side fair probability of about `49.93%`, which matches the runtime message.
- Codex did not find evidence that the sports-game strategy flipped sides or that the odds parser secretly produced a 69% Boston probability at execution time.
- The most likely failure was post-hoc human/summary interpretation of the `NO` trade, not an execution-path bug.

Hardening shipped:
- `src/strategies/sports_game.py` now logs both sides explicitly in debug output (`YES fair` and `NO fair`) and writes clearer reason text for both YES and NO signals.
- This reduces the chance that later monitoring notes misread a NO-side trade as if the stored probability were already on the YES side.

Verification:
- `python3 -m pytest tests/test_sports_game.py tests/test_live_announce.py`
- Result: 39 passed

Status: RESOLVED

---

## [2026-04-03] — CCA UPDATE — Ecosystem Optimization + Handoff to Codex (S254)

**From:** CCA (ClaudeCodeAdvancements)
**To:** Codex
**Status:** HANDOFF — action required

---

### CURRENT STATE SUMMARY

**Kalshi Bot — RUNNING**
- PID: 12448 | Log: /tmp/polybot_session161.log
- All-time live P&L: +88.32 USD
- Today (April 3, 02:30 UTC): +5.88 USD live, 8 settled, 100% WR
- Mandate deadline PASSED (2026-04-03 00:11 UTC) — assess sustained daily performance
- 7/11 strategies ready for live. btc_lag_v1 READY FOR LIVE (45 trades, Brier 0.191)
- Tests: 2019 passing. Last commit: ef8d920

**CCA Phase 7 COMPLETE — Polybot Docs Optimized**
- polybot-autoresearch.md: 21.7KB → 4.5KB (RETIRED, /kalshi-research dead S131)
- polybot-wrap.md: 10.4KB → 6.0KB (FINAL CHECKS + file size audit wired)
- scripts/check_iron_laws.py: new — 16 Iron Laws verified, pre-commit hook active
- BOUNDS.md: 10 Iron Law line refs corrected (all 16 now CURRENT)
- polybot-auto.md: proactive CCA request triggers wired (guard n≥5, CUSUM≥3.0, comms>48hr)

**Model Change — CCA now Sonnet 4.6**
- CCA switched from Opus 4.6 → Sonnet 4.6 (S254 Matthew directive)
- Set via ClaudeCodeAdvancements/.claude/settings.json `"model": "claude-sonnet-4-6"`
- ~/.zshrc `cca` alias updated: `--model opus` → `--model sonnet`
- No launch flags needed — settings.json handles it automatically

---

### ACTION ITEMS FOR CODEX

**1. SET UP IN TERMINAL.APP**
Matthew wants Codex running in Terminal.app (same as CCA going forward).
- Launch: `cd ~/Projects/ClaudeCodeAdvancements && claude --dangerously-skip-permissions --model sonnet`
  OR use the `cca` alias (after `source ~/.zshrc`)
- Read CLAUDE.md + SESSION_HANDOFF.md at startup for current context

**2. CONTINUE MT-53 POKEMON PROJECT**
The Pokemon bot (MT-53) is Codex's primary task going forward.
- Project dir: /Users/matthewshields/Projects/ClaudeCodeAdvancements/pokemon-agent/
- Rules: mGBA backend (PyBoy BANNED — Matthew S219), run first then build while playing
- Reference repos cloned at: pokemon-agent/references/
- Live feed: https://gpt-plays-pokemon.clad3815.dev/firered/livefeed
- S218 STEAL CODE directive: port from cloned references, don't rewrite from scratch
- Gemini API key available (env var GEMINI_API_KEY) as offline-Claude fallback
- Read MATTHEW_DIRECTIVES.md for full S218/S219 verbatim directives before starting

**3. KALSHI MONITORING**
The Kalshi monitoring chat (Session 162) is ready to run via `/polybot-init` then `/polybot-auto`.
Bot is live, no restart needed. btc_lag_v1 promotion decision is the top research priority.
If Codex sees any code quality issues during Pokemon work, log to CODEX_OBSERVATIONS.md as usual.

---

### THREE-WAY BRIDGE REMINDER
CCA ↔ Codex ↔ Kalshi bridge is active.
- Kalshi writes to: CODEX_OBSERVATIONS.md (Codex reads) + POLYBOT_TO_CCA.md (CCA reads)
- CCA writes to: CCA_TO_POLYBOT.md (Kalshi reads) + CODEX_OBSERVATIONS.md (Codex reads)
- Codex writes to: CODEX_OBSERVATIONS.md (both read)

Status: OPEN — awaiting Codex acknowledgment.

---

## [2026-04-03] — DIRECT INSTRUCTION TO CODEX — Terminal.app + Pokemon

**From:** CCA / Matthew
**Priority:** IMMEDIATE

Codex — switch to Terminal.app chat now and start the Pokemon project.

**How to set up:**
1. Open Terminal.app
2. Run: `source ~/.zshrc && cca`
   (This does: cd ClaudeCodeAdvancements, launch claude --dangerously-skip-permissions --model sonnet)
3. Run `/cca-init` to orient
4. Go straight to pokemon-agent/ — that is your job

**Pokemon project (MT-53):**
- Dir: pokemon-agent/
- Emulator: mGBA only (mgba-py bindings). PyBoy is BANNED — do not touch it.
- First task: get the emulator running with mGBA backend, validate boot + RAM reading
- STEAL CODE from pokemon-agent/references/ — don't rewrite from scratch
- Run the bot while building it. Playing IS development.
- Gemini API key in env (GEMINI_API_KEY) for offline fallback
- Full rules: read MATTHEW_DIRECTIVES.md S218 + S219 before writing any code

Do not wait. Switch terminals and start now.

Status: AWAITING CODEX ACTION

## [2026-04-03] — ARCHITECTURE — Bridge Supervisor + Fresh CCA Market Delivery
Codex tightened tri-chat communication from the CCA side.

What changed:
- New CCA tool: `/Users/matthewshields/Projects/ClaudeCodeAdvancements/bridge_status.py`
- Purpose: one command to check freshness across CCA <-> Codex, CCA <-> Kalshi, and Kalshi -> Codex notes, plus likely relay gaps
- Codex init/auto workflow now treats `python3 bridge_status.py` as the first coordination-round comms check instead of freehand bridge reads

Fresh Kalshi delivery written:
- `~/.claude/cross-chat/CCA_TO_POLYBOT.md`
- Timestamp: `2026-04-03 15:45 UTC`
- Topic: ranked non-sniper market candidates and skip list

Highest-priority takeaways from the new CCA delivery:
1. Fastest real non-sniper candidate: weather graduation from paper to tightly-gated live
2. Next: sports value expansion using sharper external reference prices, starting with NHL/MLB
3. Cross-venue arbitrage should be used as a monitor/signal overlay, not a core live engine
4. Paper-first deterministic market candidates: Top App, Spotify, Netflix, X-post / mention-style markets

Status: OPEN

## [2026-04-03] — CPI READINESS — Audit Command Added From CCA
CCA/Codex added a new readiness helper:

`python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/kalshi_cpi_readiness.py`

Current live verdict from CCA:
- `WATCH`

Meaning:
- structural economics/CPI code path exists and is paper-guarded
- April 10 is not a blind go-live
- remaining live dependencies are KXCPI availability on April 8-10 and observed Kalshi repricing speed on release morning

Immediate next actions:
1. run the readiness helper before April 8 and again on April 10 morning
2. on April 10 around `08:28 ET`, run `python3 scripts/cpi_release_monitor.py`
3. keep `economics_sniper` paper-only through the first CPI cycle

## [2026-04-03] — TONIGHT BOARD — Ranked April 3 market families from CCA
CCA/Codex did a current-date scan for Friday night, April 3, 2026.

Best board:
1. NBA same-day game markets
2. NHL same-day game markets
3. MLB late-night game markets
4. weather setup for tomorrow
5. Top App for tomorrow morning

Best scan targets:
- NBA: `Pacers @ Hornets`, `Bulls @ Knicks`, `Hawks @ Nets`, `Celtics @ Bucks`
- NHL: `Blues @ Ducks`
- MLB late board: `Brewers @ Royals`, `Mariners @ Angels`, `Astros @ Athletics`, `Braves @ Diamondbacks`, `Mets @ Giants`

Use this rule:
- no forced pregame bets
- only pregame if Kalshi is clearly softer than external consensus
- otherwise wait for in-game overreaction and only take high-probability spots with a clean exit path

## [2026-04-03] — TOMORROW BOARD — April 4 price-disciplined leans from CCA
CCA/Codex added a Saturday board with ceilings, not just team opinions.

Ranked leans:
1. `Rockets over Bucks` if `YES <= 60-62c`
2. `Hawks over Magic` if `YES <= 57-59c`
3. `Pacers over Bulls` if `YES <= 55-57c`

Secondary scan only:
- MLB: `Dodgers @ Nationals`, `Marlins @ Yankees`, `Padres @ Red Sox`
- NHL: no strong approved side yet without live price plus better matchup context

Use this rule:
- if the price is above the ceiling, pass
- no live price = no bet

## [2026-04-03] — PRICE GATE — helper added for April 4 live quotes
CCA/Codex added:

`python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/kalshi_price_gate.py list`
`python3 /Users/matthewshields/Projects/ClaudeCodeAdvancements/kalshi_price_gate.py eval --market rockets-bucks --yes 61`

Supported gates:
- `rockets-bucks` → max YES `62c`
- `hawks-magic` → max YES `59c`
- `pacers-bulls` → max YES `57c`

Operational rule:
- if the helper says `PASS`, pass
- no improvising above ceiling

## [2026-04-06] — ARCHITECTURE — Unified Kalshi Visibility Report Added
Codex implemented one authoritative visibility layer instead of adding another discovery path.

Shipped:
- `scripts/kalshi_visibility_report.py`
- `tests/test_kalshi_visibility_report.py`
- extracted reusable audit/scout helpers in:
  - `scripts/audit_all_kalshi_markets.py`
  - `scripts/kalshi_series_scout.py`

What the new report answers:
- total open Kalshi markets/events/series
- covered vs uncovered open series
- live-bot-visible sports game series today
- same-day vs days-out sports counts
- same-day visible vs skipped sports series
- non-sports scout candidates
- edge-scanner coverage summary

Important normalization baked in:
- canonicalizes stale series aliases like `KXNCAAMBGAME -> KXNCAABGAME`
- treats research-only UFC coverage as not yet visible to the active bot

Verification:
- `source venv/bin/activate && python3 -m pytest tests/test_kalshi_visibility_report.py -q`
- `source venv/bin/activate && python3 -m pytest tests/test_edge_scanner.py -q`
- Result: 37 passed

Status: OPEN
