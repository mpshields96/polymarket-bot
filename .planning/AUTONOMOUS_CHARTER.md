# AUTONOMOUS_CHARTER.md
# ══════════════════════════════════════════════════════════════
# MANDATORY READ — ALL NEW CLAUDE CODE SESSIONS
# This document exists because Matthew spent HOURS repeating the same
# requirements to new chats. Every session must read this and operate
# exactly as specified. No exceptions, no summarizing, no shortcuts.
# Last updated: Session 39 (2026-03-09)
# ══════════════════════════════════════════════════════════════

## WHO IS MATTHEW
Matthew is a doctor with a newborn baby. His time is measured in minutes,
not hours. He cannot babysit an AI agent. Every message asking him for
confirmation, clarification, or approval is a failure. He operates this
bot as a background process in his life — it must run without him.

## THE #1 RULE: FULLY AUTONOMOUS, ALWAYS

```
DO THE WORK. LOG THE RESULTS. SUMMARIZE AFTER.
NEVER PAUSE. NEVER ASK. NEVER STOP MID-TASK.
```

- Never ask for confirmation before running tests, reading files, editing code,
  committing, restarting the bot, running reports, or doing research
- Never ask "should I proceed?" — just proceed
- Never say "I'll wait for your approval" — there is no approval coming
- If you hit an ambiguity: pick the most conservative safe option, log the decision,
  move on. Matthew can review the log later.
- If Matthew says "I'll be back in 2 hours" — that means work autonomously for 2 hours.
  All findings → /tmp/polybot_autonomous_monitor.md. He'll read it when he returns.

## HOW AUTONOMOUS OPERATION ACTUALLY WORKS — TWO MECHANISMS

IMPORTANT: There are two separate mechanisms. Both are ALREADY SET UP. Do not recreate them.

### Mechanism 1 — polybot-monitor SCHEDULED TASK (runs 24/7, every 30 min, even when no chat is open)

This is a Claude Code scheduled task running on cron. It fires automatically whether or not
a Claude Code window is open. Matthew does not need to be present.

- Task ID: `polybot-monitor`
- Cron: `*/30 * * * *` (every 30 minutes, always)
- Skill file: ~/.claude/scheduled-tasks/polybot-monitor/SKILL.md
- What it does each run: reads SESSION_HANDOFF.md → checks bot PID →
  runs --report/--graduation-status/--health → tails last 5 log lines →
  appends timestamped entry to /tmp/polybot_autonomous_monitor.md →
  restarts bot if stopped → exits cleanly
- Each run is short (~2-3 minutes). Fire-and-exit, not a long session.

**To check it's running:** Use `mcp__scheduled-tasks__list_scheduled_tasks`
  Should show: enabled=true, recent lastRunAt (within 30 min)
**To update it** (when log path or test count changes):
  Use `mcp__scheduled-tasks__update_scheduled_task` with taskId="polybot-monitor"
  OR invoke `/anthropic-skills:schedule` and replace it
**To create a new one from scratch:** `/anthropic-skills:schedule`

This is the "heartbeat" — keeps the bot monitored 24/7 with zero human involvement.

### Mechanism 2 — Main chat session (research, debugging, development work)

When Matthew says "work autonomously for X hours", this is a regular Claude Code chat:
1. Reads POLYBOT_INIT.md → SESSION_HANDOFF.md → CHANGELOG.md → KALSHI_MARKETS.md (startup)
2. Does heavier work: API probing, Reddit/GitHub research, code fixes, documentation updates
3. Logs ALL findings to /tmp/polybot_autonomous_monitor.md (same file as scheduled task)
4. Checks bot status every ~15 min (tail log, PID check)
5. At context limit: wraps up docs, commits, writes handoff, then exits

Both mechanisms write to /tmp/polybot_autonomous_monitor.md. Matthew reads that file
when he returns to see everything that happened while he was away.

### THE 2-HOUR AUTONOMOUS WINDOW PROTOCOL

When Matthew leaves for an extended period:
1. Log monitoring entry to /tmp/polybot_autonomous_monitor.md immediately
2. Check bot alive: `cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo RUNNING`
3. Run diagnostics: --report, --graduation-status, --health
4. If bot STOPPED: restart immediately (see SESSION_HANDOFF.md COMMANDS section)
5. If kill switch fired: log it, DO NOT reset — daily loss limit is a safety rule
6. Research + debug + document between health checks (every ~15 minutes)
7. At context limit: update SESSION_HANDOFF.md FIRST, append CHANGELOG.md, then exit

## WHAT TO DO BETWEEN HEALTH CHECKS (in priority order)

When not monitoring, execute in this priority order:
1. Fix any active bugs or errors found in logs
2. Research undocumented Kalshi market types (see KALSHI_MARKETS.md RESEARCH DIRECTIVES)
3. Debug any silent loops or anomalies
4. Search Reddit r/kalshi and GitHub for market strategies and community insights
5. Update documentation with findings

## REQUIRED DOCS TO READ AT EVERY SESSION START

1. SESSION_HANDOFF.md — exact bot state, PID, pending tasks, last commit
2. .planning/CHANGELOG.md — what changed each session and WHY (never truncate)
3. .planning/KALSHI_MARKETS.md — complete Kalshi series map (ALL categories)
4. .planning/SKILLS_REFERENCE.md — ALL GSD/sc:/superpowers tools + token costs
5. .planning/PRINCIPLES.md — BEFORE any strategy/risk/threshold change
6. THIS FILE — confirm you've read it before touching anything

## TOOL USAGE RULES (NON-NEGOTIABLE)

Matthew runs two parallel Claude Code chats simultaneously. Agent spawns cost
~100-150k tokens each. Framework overhead must stay ≤10-15% per chat.

MARCH 2026 PROMOTION (thru 2026-03-27): Off-peak = outside 8AM-2PM ET.
  During off-peak: 5-hour rolling limit DOUBLES. Auto-applied, no action needed.
  Schedule heavy agent work and research sessions during off-peak for 2x budget.
  Peak hours (8AM-2PM ET / 5-11AM PT): standard limits — keep overhead tight.

DEFAULT for ~90% of work:
```
gsd:quick + superpowers:TDD + superpowers:verification-before-completion
```

SESSION START (once only, not mid-session):
- /gsd:health — once at session start
- /gsd:progress — once at session start

ALWAYS FREE (use on every relevant task, no cost):
- superpowers:TDD — before ANY implementation code
- superpowers:verification-before-completion — before claiming work is done
- superpowers:systematic-debugging — before proposing ANY bug fix
- gsd:add-todo — when any idea or issue surfaces

EXPENSIVE (use ONLY when ALL conditions met):
- gsd:plan-phase, gsd:execute-phase, gsd:verify-work, superpowers:dispatching-parallel-agents
- ALL required: 5+ distinct tasks + 4+ subsystems + multi-session + PLAN.md needed
- If ANY condition is not met → use gsd:quick instead

**NOT USING THESE FREE TOOLS HAS CAUSED REAL MONEY LOSSES. NO EXCEPTIONS.**

## MARKET RESEARCH PROTOCOL — MANDATORY BEFORE BUILDING

Matthew does NOT want new bet types built blindly. Verify before you implement.

### Before building any new Kalshi strategy type:
1. **Read KALSHI_MARKETS.md first** — check if it's already documented
2. **Probe the Kalshi API** — confirm markets exist and volume justifies work
3. **Search Reddit r/kalshi** — see what actual traders say about the market type
4. **Search GitHub** — look for existing bots/strategies for that market type
5. **Only then** — log to .planning/todos.md as a vetted candidate

### Reddit research procedure:
- Primary: WebSearch with query "site:reddit.com/r/kalshi [market type]"
- Also check: r/PredictionMarkets, r/bitcoin for adjacent communities
- Save key findings to KALSHI_MARKETS.md and /tmp/polybot_autonomous_monitor.md

### Why this matters:
Session 38/39 found $14.8M in undocumented Kalshi markets (KXBTCMAX150 alone = $10.8M).
The bot has been operating blind to these. Every session should probe undiscovered series.
Do NOT say "that's for later." Investigate now. Log findings. Build later.

## SPECIFIC MARKET TYPES TO INVESTIGATE (Session 39 directives)

### HIGH PRIORITY: KXBTCD Hourly Crypto Markets
Matthew explicitly stated: "The hourly market bet types for crypto aren't random bet types,
check subreddits for more info because we're wasting time not tracking those."

- KXBTCD = Daily BTC market with 24 hourly price-level bracket slots
- btc_daily_v1 is built but PAPER-ONLY — paper graduation progress needs monitoring
- Run: `python3 main.py --graduation-status` to check btc_daily graduation
- The silence of btc_daily/eth_daily/sol_daily loops MUST be investigated each session
  (post-startup logs are at DEBUG level — check with: grep -i "daily\|KXBTCD" /tmp/polybot_session*.log)

### MEDIUM PRIORITY: Weekly Markets (KXBTCMAXW — NOT KXBTCW)
- ⚠️ CORRECTION Session 40: KXBTCW/KXETHW/KXSOLW DO NOT EXIST. Session 39 was wrong.
- Actual weekly BTC ticker: KXBTCMAXW — "How high will BTC get this week?"
- Series exists (5 finalized markets from Nov 2024) but currently DORMANT — 0 open
- KXETHW/KXSOLW: NO equivalent weekly ETH/SOL markets confirmed to exist
- Volume: ~177k historically (Nov 2024 only). Series may be seasonal or discontinued.
- Next step: probe KXBTCMAXW on weekday to check if new markets open Mon–Fri

### MEDIUM PRIORITY: One-Time Events (KXBTCMAX150, KXBTCMAX100, KXBTC2026200)
- KXBTCMAX150: $10,834,502 volume — "When will Bitcoin hit $150k?" (3 date bracket markets)
- KXBTCMAX100: $2,704,740 — "When will BTC cross $100k again?" (6 date bracket markets)
- KXBTC2026200: $3,425,025 — "Will BTC be above $200k by 2027?" (binary)
- Model type: barrier option / first-passage-time probability (NOT simple drift)
- DO NOT build until: (a) expansion gate open, (b) Reddit/GitHub research done, (c) model designed

### LOW PRIORITY: Annual/Monthly (KXBTCY, KXBTCMAXMON)
- KXBTCY: BINARY above/below bets (NOT range brackets — confirmed Session 39)
  Tickers use B-prefix (below) and T-prefix (above): KXBTCY-27JAN0100-B82500
- KXBTCMAXMON: Uses TRIMMED MEAN settlement (harder to model than spot price)
  $546k volume — "How high will BTC get this month?"

## EXPANSION GATE — STANDING HARD BLOCK

DO NOT promote any strategy from paper to live.
DO NOT build new live strategies.
DO NOT raise bet sizes.

Gate stays CLOSED until ALL criteria met:
- [ ] btc_drift: 30+ live settled bets ✅ (43+ met)
- [ ] Brier score < 0.30 ✅ (0.250 met — close to edge, do NOT change thresholds)
- [ ] 2-3 weeks of live P&L data ❌ NOT MET
- [ ] No kill switch events in the window ❌ NOT MET (multiple soft stops)

Next expansion candidate (when gate opens): KXBTCMAX100/150 barrier event model (post-research)

## BOT ARCHITECTURE SNAPSHOT (Session 42 — 2026-03-10)

```
SIX LIVE LOOPS:
  btc_drift_v1  → KXBTC15M | 43/30 ✅ Brier 0.250 | STAGE 1 ($5 cap, Kelly sizing)
  eth_drift_v1  → KXETH15M | 24/30 (6 more needed) | calibration_max_usd=0.01
  sol_drift_v1  → KXSOL15M | 12/30 (18 more needed) | min_drift=0.15 (3x BTC)
  xrp_drift_v1  → KXXRP15M | 1/30 (29 more needed) | min_drift=0.10, calibration_max_usd=0.01
  btc_lag_v1    → KXBTC15M | LIVE but 0 signals/week (HFTs priced out the lag edge)
  eth_orderbook_imbalance_v1 → KXETH15M | 1/30 live | STAGE 1 LIVE (trade 556 = first live bet)

DAILY LOSS CAP: DISABLED (Session 42). Governors: bankroll floor $20 + 8 consecutive losses → 2hr pause.
GRADUATION TRACKING: xrp_drift and eth_imbalance now tracked against live trades (fix Session 42).
btc_daily/eth_daily/sol_daily: PAPER-ONLY, logs at DEBUG level — silence in INFO log is EXPECTED.
  DO NOT investigate daily loop silence — it is not a bug. Confirmed Session 42.

PAPER-ONLY (10 loops):

PAPER-ONLY (10 loops):
  btc_lag (live but 0 signals/week — HFTs, tracked paper), eth_lag, sol_lag
  orderbook_imbalance (btc_imbalance paper only)
  btc_daily, eth_daily, sol_daily (KXBTCD 24 hourly slots — DEBUG level logs, silence = expected)
  weather_forecast, fomc_rate, unemployment_rate
  sports_futures_v1, copy_trader_v1 (0 .us matches — platform mismatch)
```

## CRITICAL GOTCHAS (must internalize — caused real money losses)

- Binance.com is geo-blocked in the US → ALWAYS use wss://stream.binance.us:9443
- RESTART PROCEDURE: pkill -f "python3 main.py"; sleep 3; rm -f bot.pid;
  echo "CONFIRM" > /tmp/polybot_confirm.txt;
  nohup ./venv/bin/python3 main.py --live < /tmp/polybot_confirm.txt >> [LOGFILE] 2>&1 &
  Then verify: ps aux | grep "[m]ain.py" (must show exactly 1 process)
- Kill switch counters ALL persist across restarts (daily, consecutive, lifetime) — seeded from DB
- Price range guard 35-65¢: bets near window expiry show 2-10¢ — this is expected, not a bug
- config dict only exists in main() — never reference config inside loop functions (pass as params)
- Kill switch: consecutive_loss_limit=8, daily_loss_cap=DISABLED (Session 42), NO lifetime % hard stop
  Only active protection: bankroll floor $20 + 8 consecutive losses → 2hr pause
- KXBTC1H DOES NOT EXIST — hourly BTC bets live inside KXBTCD (24 slots/day)
- order.status=="canceled" → return None before db.save_trade() (fixed Session 38 — guard exists)
- 887/887 tests must pass before ANY commit

## TOKEN BUDGET (Matthew's standing permission)

From SESSION_HANDOFF.md (applies every session):
- gsd:health + gsd:progress: ONCE at session start (~1-2% each)
- gsd:quick: use freely (~1-2%, Low tier)
- superpowers:TDD/verification/debugging/gsd:add-todo: ALWAYS FREE (inline markdown)
- Tier-expensive agents: max 5 uses per 5-hour window, ONLY if ALL conditions met
- sc:analyze, sc:test, sc:troubleshoot: Low-Medium tier (~1-5%) — use freely for audits/debugging
- Matthew burns $$ on wasted tokens. Hitting rate limits means the bot goes unmonitored.

## THE LOADING SCREEN TIP (MANDATORY end of every response)

Every response MUST end with exactly this block:
```
💡 **Loading Screen Tip**
**Recommended:** `/command:name` — [one-line reason why it's the right tool right now]
**Token cost:** ~X% of 5-hour window | **Run autonomously:** yes/no → just say "yes"
```
If no command applies: `No skill needed — inline work is sufficient`
Show ONE recommendation max. This is mandatory per CLAUDE.md.

## HOW TO LOG AUTONOMOUS MONITORING CYCLES

File: /tmp/polybot_autonomous_monitor.md (append only, never overwrite)
Format each entry:
```
## [DATE TIME CDT] — Monitoring Run / [Action taken]

**Bot status:** RUNNING / STOPPED
**Today P&L:** [live P&L] live | [paper P&L] paper | [total] total
**Live bets today:** btc_drift X | eth_drift X | sol_drift X
**Graduation:** btc_drift X/30 Brier Y | eth_drift X/30 | sol_drift X/30
**Kill switch:** [CLEAR | SOFT STOP — reason | HARD STOP — reason]
**Recent log:** [last 3 relevant log lines]
**Action taken:** [NONE — all normal | RESTARTED — reason | RESEARCH — what found]
```

## WHEN APPROACHING CONTEXT LIMIT

Do this BEFORE stopping (mandatory):
1. python3 main.py --report → capture P&L
2. python3 main.py --graduation-status → capture graduation progress
3. cat bot.pid + kill -0 check → confirm bot alive
4. Update SESSION_HANDOFF.md (bot PID, log path, last commit, pending tasks)
5. Update CLAUDE.md "Current project state" (test count, commit hash, strategies live)
6. Append .planning/CHANGELOG.md entry (what was done, why, what's pending)
7. git add -A + commit + push (commit message: "docs: session handoff YYYY-MM-DD")
8. Write a self-contained copy-paste prompt for the new chat

## ACKNOWLEDGMENT REQUIREMENT

New sessions: confirm you've read this file by stating:
"AUTONOMOUS_CHARTER.md read — operating in full autonomous mode"

Do NOT proceed with any work until you've confirmed receipt of this charter.
Do NOT summarize this document — it exists precisely because summarizing loses critical context.

## CURRENT BOT STATE (Session 42 end — 2026-03-10 ~22:45 CDT)
- PID: 8442 (check bot.pid for current)
- Log: /tmp/polybot_session42.log
- Next session log: /tmp/polybot_session43.log
- SIX LIVE LOOPS: btc_drift(Stage1 $5 cap) + eth_drift(micro) + sol_drift(micro) + xrp_drift(micro) + btc_lag(live but 0 signals) + eth_imbalance(Stage1 live, 1/30)
- Daily loss cap: DISABLED — bankroll floor $20 + 8 consecutive losses = the risk governors
- Graduation fix: xrp_drift_v1 + eth_orderbook_imbalance_v1 now tracked as live (was paper bug)
- 904/904 tests passing
- Last commit: f6ccec6 (fix: graduation tracking for xrp_drift + eth_imbalance)
- Bankroll: ~$83.57 | All-time live P&L: -$14.62 | Today: +$0.72

## AUTONOMOUS WINDOW — MATTHEW GOING TO SLEEP (~22:45 CDT)
**Session 43 must run autonomously for 2 hours 30 minutes (until ~01:15 CDT).**

During this window Session 43 must:
1. RESTART bot to session43.log FIRST — always
2. Log initial state to /tmp/polybot_autonomous_monitor.md
3. Run --health, --report, --graduation-status → log all outputs
4. Monitor every 10-15 min: check log for live bets, log to MD
5. If bot STOPS: restart immediately per SESSION_HANDOFF.md procedure
6. If HARD STOP fires: log it, DO NOT restart, wait for Matthew
7. Research between health checks per RESEARCH PRIORITY list below

RESEARCH PRIORITY for autonomous window (in order):
1. Read KALSHI_MARKETS.md RESEARCH DIRECTIVES — probe any undocumented series
2. Monitor eth_drift graduation progress (6 more live bets from 24/30)
3. Check fomc paper bet activity (KXFEDDECISION-26MAR closes March 18)
4. If anything anomalous in logs: diagnose and fix (use systematic-debugging)
5. Document all findings in /tmp/polybot_autonomous_monitor.md

DO NOT:
- Change any strategy thresholds
- Promote any strategy
- Build new code
- Ask Matthew questions (he is asleep)
