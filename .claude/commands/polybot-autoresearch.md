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
2. Read SESSION_HANDOFF.md — get current state
3. Read .planning/EDGE_RESEARCH_S62.md — know what's already been found
4. Pick the HIGHEST-IMPACT research task from the R&D roadmap (Section 9)
5. START WORKING — no planning documents, just build and test

R&D PRIORITY STACK (from EDGE_RESEARCH_S62.md Section 9):
1. BALLDONTLIE API integration — free, includes Kalshi+Pinnacle in one call
2. Kalshi-vs-Pinnacle price comparison scanner (use the-odds-api we already have)
3. Limit order execution test on one strategy (sniper = easiest candidate)
4. FOMC/CPI strategy activation (already built, 0 bets placed!)
5. Weather ensemble approach (GFS data is free from NOAA)
6. NCAA March Madness pricing analysis (happening RIGHT NOW)

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
