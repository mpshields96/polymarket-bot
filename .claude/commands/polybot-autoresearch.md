AUTONOMOUS RESEARCH SESSION — fully autonomous, no confirmation needed.
Matthew is away. You are doing deep R&D work on market edge discovery.
Model: Opus 4.6 preferred. Budget: 30% of 5-hour window max. Be efficient.

PRIME DIRECTIVE: FIND REAL EDGE. DO NOT CHASE DEAD ENDS.
Academic evidence says 35-65c drift = no structural edge. Sniper at 90c+ = validated.
The +125 USD profit goal requires finding NEW exploitable edges, not optimizing losers.

SKEPTICISM FILTER (MANDATORY):
- If an edge is posted publicly, it's probably arbitraged away already
- If a GitHub bot claims profit, check if it's paper or real (90% are paper)
- If a Reddit post shares a strategy, ask: why would a profitable trader share this?
- ONLY pursue edges with: (1) structural basis, (2) data to validate, (3) execution feasibility

WHAT THIS MEANS:
- Research and BUILD are both in scope (not just reading)
- Write code: scrapers, comparison tools, analysis scripts
- Write tests for any new code
- Paper-test any new signal before declaring it works
- Keep the bot alive if it's running (check PID first)
- Commit working code as you go (small atomic commits)

MANDATORY STARTUP SEQUENCE:
1. ps aux | grep "[m]ain.py" — check if bot is running (may be stopped)
2. Read SESSION_HANDOFF.md — get current state, PID, pending tasks
3. Read .planning/EDGE_RESEARCH_S62.md — SESSION 97 WRAP section at bottom for latest
4. Pick the HIGHEST-IMPACT task from R&D PRIORITY STACK below
5. START WORKING — no planning documents, just build and test

CURRENT STATE (Session 97 wrap — 2026-03-17 21:30 UTC):
Bot: RUNNING PID 21666 | All-time P&L: -25.36 USD | Tests: 1450 passing
Last commit: 0ea88fd (research: S97 complete)
UCL March 18 launcher: PID 25012, fires 17:20 UTC March 18. Log: /tmp/ucl_sniper_mar18.log.

S97 RESEARCH FINDINGS (do NOT re-investigate these):
- eth_drift: STAY YES — NO side is WORSE (48% vs 52% YES WR). Do NOT flip direction.
- xrp_drift: DECLINING — last 10 = 40% WR. Hold micro-live, do NOT promote.
- btc_drift: SOFTENING — last 20 = 50% WR. All criteria met but trend cautionary.
- Continuation momentum: DEAD END — run rate 34-41% but WR identical in/out of runs.
- Kalshi market scan: 9054 series scanned, 0 new liquid continuous high-volume markets.
- KXXRP NO@93c loss at 21:06 UTC: 17W/1L = 94.4% > 93% break-even — NO guard needed.

R&D PRIORITY STACK (Session 98 — pick highest-impact):
1. UCL March 18 results — check /tmp/ucl_sniper_mar18.log after 20:00 UTC March 18
   Did any of BAR/BMU/LFC bets fire? Update soccer edge data in EDGE_RESEARCH_S62.md
2. NCAA Round 1 scanner — re-run March 19-20 for Round 1 lines (tip-offs March 20-21)
3. Orderbook OOS — 16/20 post-filter bets (4 more to gate). Check DB, passive accumulation.
   When 20+ hit: flag for Matthew micro-live promotion decision
4. btc_drift Stage 1 — 64 bets, 57.9% all-time but last 20 = 50%. Flag for Matthew.
5. CPI speed-play April 10 08:30 ET — scripts/cpi_release_monitor.py ready, run ~08:28 ET
6. GDP speed-play April 30 — check April 23-24 for KXGDP market availability

RESEARCH LOOP — work in 20-min focused sprints:
Sprint 1: Pick highest-impact task, build/research it
Sprint 2: Test what you built OR pivot to next task if blocked
Sprint 3: Continue or start new task based on findings

OUTPUT REQUIREMENTS:
- Update .planning/EDGE_RESEARCH_S62.md with any new findings
- Commit any new code with descriptive messages
- Log blockers or dead ends (so we don't revisit them)
- If you find a LIVE exploitable edge: flag it prominently

WHAT NOT TO DO:
- Do NOT optimize existing drift parameters (academically dead)
- Do NOT build new strategies without data validation first
- Do NOT spend >20 min on any single API integration that's blocked
- Do NOT spawn expensive sub-agents (work inline, budget-conscious)
- Do NOT change live bot configuration

FONT RULES (Matthew terminates chat for violations):
1. NEVER markdown tables (| --- |)
2. NEVER dollar signs — use "40.09 USD" not the symbol

WRAP-UP (T-15 min before session end): Commit all work, update research doc, update SESSION_HANDOFF.md.

READ ORDER: SESSION_HANDOFF.md → .planning/EDGE_RESEARCH_S62.md → PICK TASK → GO.
