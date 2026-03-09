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

## THE 2-HOUR AUTONOMOUS WINDOW PROTOCOL

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

### MEDIUM PRIORITY: Weekly Markets (KXBTCW/KXETHW/KXSOLW)
- Confirmed to EXIST via API probe (Session 39)
- 0 open markets on Sundays (expected — markets open Monday, close Friday 5pm EDT)
- Next session on a weekday: probe again and document the market structure
- Volume unknown — confirm before building any strategy

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
- [ ] btc_drift: 30+ live settled bets ✅ (37+ met)
- [ ] Brier score < 0.30 ✅ (0.247 met)
- [ ] 2-3 weeks of live P&L data ❌ NOT MET (~2 days live)
- [ ] No kill switch events in the window ❌ NOT MET (multiple soft stops)

Next expansion candidate (when gate opens): KXXRP15M drift (same code as sol_drift, ~15 min to enable)

## BOT ARCHITECTURE SNAPSHOT (Session 39)

```
THREE MICRO-LIVE LOOPS (all ~$0.35-0.65/bet, 1 contract):
  btc_drift_v1  → KXBTC15M | 37/30 ✅ Brier 0.247 | min_drift=0.05 min_edge=0.05
  eth_drift_v1  → KXETH15M | 19/30 (11 more needed) | same thresholds
  sol_drift_v1  → KXSOL15M | 11/30 (19 more needed) | min_drift=0.15 (3x BTC)
  All share: _live_trade_lock | calibration_max_usd=0.01 | price guard 35-65¢

PAPER-ONLY (12 loops):
  btc_lag, eth_lag, sol_lag (0 signals/week — HFTs closed the lag)
  orderbook_imbalance, eth_orderbook_imbalance
  btc_daily, eth_daily, sol_daily (KXBTCD 24 hourly price-level slots)
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
- Kill switch: consecutive_loss_limit=4, daily_loss_limit=20%, NO lifetime % hard stop
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
