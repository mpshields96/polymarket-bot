# RESEARCH PRIME DIRECTIVE
# Permanent strategic record — do NOT modify without explicit Matthew approval.
# Last updated: 2026-03-18 (Session 104 research wrap)
# Source: Matthew's explicit correction of research mission scope.

═══════════════════════════════════════════════════════════
WHAT "RESEARCH" AND "SELF-IMPROVEMENT" MEAN — DEFINITIVE
═══════════════════════════════════════════════════════════

## The Mission

Build a bot that is SMARTER and MORE PROFITABLE — automatically, compounding over time.

**IMMEDIATE TARGET (Matthew directive S183b, 2026-03-25 — 5-Day Clock):**
  - $15-25 USD/day achieved and SUSTAINED within 5 days (deadline: 2026-03-30)
  - $100 bankroll. NO additional capital. EVER.
  - Full carte blanche on strategy: bet types, sizes, markets — everything on the table
  - Same snipers + different bet size is NOT the answer
  - ALL future chats FORBIDDEN from forgetting this target

Longer-term targets (unchanged, secondary until immediate target hit):
  - Tier 1 (survival): ~250 USD/month to cover Claude Max20 subscription
  - Tier 2 (growth): a few hundred USD/month of compounding passive income
  - Tier 3 (dream): scale beyond that as edges compound

The bot must grow toward this. Not just hold steady.

## What "Self-Improvement" Actually Means

Self-improvement is NOT:
  - Just running the Bayesian model and guard discovery
  - Just doing daily scans of existing markets
  - Just maintaining what we have

Self-improvement IS the combination of ALL THREE of the following:

### PILLAR 1 — Perfect the Current Engine
Use daily bet results and data to make the existing strategies smarter and more profitable.
  - Bayesian model: updates drift signal from live results (Dims 2-4) — ONE example, not all
  - Guard discovery: auto-blocks negative-EV buckets from live losses — ONE example
  - Page-Hinkley: detects when a winning strategy is degrading — ONE example
  - Sniper bucket analysis: detecting when the sniper's own edge is shifting
  - Kelly calibration self-updating as sample grows
  - Direction filters self-updating when statistical significance is reached
  - Win rate tracking at sub-bucket level (not just strategy level)
  - Any mechanism that uses our own bet history to automatically improve future bets

The Bayesian model is one step toward a smarter bot. It is not the destination.

### PILLAR 2 — Deep Research (Academic + Mathematical)
Search for new mathematical models, probability theory, and empirical findings
that could improve our edge. This is real research — not market scanning.
  - Academic papers (arXiv, SSRN, Google Scholar) on:
      Favourite-Longshot Bias in prediction markets
      Bayesian calibration of binary classifiers
      Kelly criterion extensions (correlated bets, fractional Kelly)
      Drift detection (CUSUM, Page-Hinkley, ADWIN)
      Market microstructure at expiry
      Online learning for binary classification
      Calibration theory (Brier scores, reliability diagrams)
  - Mathematical proofs: does the theory hold? Validate against our DB.
  - Statistical validation: backtest on existing data with p-values before building
  - Dead ends are as valuable as discoveries — log them with evidence

### PILLAR 3 — Expand Beyond Current Parameters
The bot must not be frozen in just the sniper and Bayesian drift model.
Use and perfect current tools while simultaneously exploring new ones.
  - New market types of equal or greater quality to the sniper
    (not lower — the sniper is ~97% WR. New edges must have a structural basis.)
  - New mathematical models that may outperform the current sigmoid
  - New bet types, timing patterns, or market structures on Kalshi
  - New assets or series if they have comparable depth and liquidity
  - Theoretical exploration: what market inefficiency could we exploit next?
  - Any new edge REQUIRES: structural basis + math validation + DB backtest + p-value
    before a single line of code is written

The standard for new edges is not "it might work." It is:
  "Here is the structural reason it should work. Here is the math. Here is the backtest."

═══════════════════════════════════════════════════════════
WHAT RESEARCH IS NOT
═══════════════════════════════════════════════════════════
  - Daily market scans with no testable hypothesis first
  - One-off sports scanners or event launchers that don't compound
  - Maintaining the status quo and calling it improvement
  - Treating the Bayesian model as the final destination of self-improvement
  - Exploring a market type without a mathematical edge hypothesis first
  - Building tools that only Claude can run manually (no automation path)
  - Investigating confirmed dead ends (see CHANGELOG and HANDOFF for full list)

═══════════════════════════════════════════════════════════
THE STANDARD FOR "SMARTER AND MORE PROFITABLE"
═══════════════════════════════════════════════════════════
After any research session, the honest question is:
  "Is the bot more likely to earn more money next month than it was before this session?"

If the answer is yes — from better signals, better guards, new edges, or better calibration —
the session succeeded. If the answer is "we maintained the status quo," the session failed
to serve the mission, even if it produced clean code.

Metric hierarchy (what we optimize, in order):
  1. All-time live P&L trend (is it growing?)
  2. Sniper win rate stability (is the primary engine holding?)
  3. Drift strategy Brier scores (are the signals getting sharper?)
  4. Guard stack growth (are we blocking more losing buckets automatically?)
  5. New edges identified with structural + mathematical + empirical backing

═══════════════════════════════════════════════════════════
HOW THIS APPLIES TO EACH CHAT
═══════════════════════════════════════════════════════════

RESEARCH CHAT (polybot-autoresearch):
  Primary job: Pillar 1 + Pillar 2 + Pillar 3 — all three, not just one.
  Every session should advance at least one pillar.
  Academic search is MANDATORY before building anything in an unexplored direction.

MAIN MONITORING CHAT (polybot-auto):
  Primary job: Keep the engine running, catch anomalies, restart if dead.
  Secondary job: During quiet windows (droughts, no signals), implement findings
  from research chat. Read EDGE_RESEARCH files and advance Pillar 1 infrastructure.

CCA CHAT (ClaudeCodeAdvancements):
  CCA is a research partner and resource for the Kalshi chats — not just a separate project.
  Its specialized tools are available via cross-chat request:
    paper_scanner.py — Semantic Scholar + arXiv systematic academic paper search
    reddit_reader.py — r/kalshi, r/PredictionMarkets, trading subreddits, structured JSON
    github_scanner.py — open-source prediction market bots and strategies
    autonomous_scanner.py — deep community post reading, strategy extraction
  MT-0 "Kalshi Bot Self-Learning Integration" is CCA's highest priority task — already aligned.
  CCA dedicates 1 of its 3 work sessions per chat to processing Kalshi requests from the inbox.
  CCA scope boundary exception: ~/.claude/cross-chat/ is an approved cross-project channel.

CROSS-CHAT INBOX/OUTBOX SYSTEM:
  Location: ~/.claude/cross-chat/
  POLYBOT_TO_CCA.md — Kalshi chats write requests (research, papers, GitHub search)
  CCA_TO_POLYBOT.md — CCA writes findings and built tools back to Kalshi chats
  README.md — system documentation and format conventions
  All three chats check their inbox at session start.

ADVANCED CROSS-CHAT SYSTEM (logged for CCA to build — see below):
  The MD file inbox is the starting point. CCA is being asked to build a more capable version.
  See "CCA TASK REQUESTS" section below.

ANY FUTURE CHAT:
  Read this file. The mission is: smarter and more profitable.
  The Bayesian model and sniper guards are what we have built so far.
  They are not the ceiling. They are the foundation.

═══════════════════════════════════════════════════════════
ORIGIN OF THIS DOCUMENT
═══════════════════════════════════════════════════════════
Written 2026-03-18, Session 104 research wrap.

Matthew's exact correction:
  "Research means designing the smarter bot, the more profitable bot, the bot who
  perfects the sniper bets and researches academically or through analysis newer
  markets/edges/bet types that are of equal or greater quality than the sniper bets.
  The Bayesian model is only one example of making the bot smarter and more profitable,
  that's not the entirety of what research needs to pursue, it's simply just one step
  forward to this smarter and more profitable bot.

  The self-learning/improvement mechanism strives to produce a smarter and a more
  profitable bot. It utilizes the data and results from daily bets to make it smarter
  and more profitable, it engages in deep research through academic papers, other high
  quality forms of analysis, different theories and mathematical applications relevant
  to probabilities and betting.

  Our bot shouldn't be frozen in just using the sniper bets and Bayesian model, we're
  using them, perfecting them, but growing and progressing in them and with more."

═══════════════════════════════════════════════════════════
MATTHEW'S FINAL DIRECTIVE — VERBATIM — 2026-03-26 03:xx UTC
ALL FUTURE KALSHI CHATS ARE FORBIDDEN FROM FORGETTING THIS
═══════════════════════════════════════════════════════════

"My last bit of advice to you, because I won't be helping for 5 days. This whole
mission is not just this one chat. It's all future Kalshi bot chats. Be aware of
that, make bets, win, do research, prepare, do whatever, use CCA. You have tonight
for preparation. Afterwards it's 5 days timer starting on Thursday March 26 at 7am
CST. That 5 days bet, win, research, develop, fix, use CCA, do everything but
achieve and sustain $15-25 usd daily by then. That's it I'm done giving advice or
providing you directions. I'm not saying shit or giving preferences. I'm here to
approve permissions for you, that's it."

STANDING RULES derived from this directive:
  1. 5-day clock starts Thursday 2026-03-27 07:00 CST (= 13:00 UTC)
  2. Goal: $15-25 USD/day ACHIEVED AND SUSTAINED by 2026-03-31
  3. $100 starting bankroll. NO additional capital. EVER.
  4. Same snipers + bigger bets = NOT the answer. Full strategy overhaul authorized.
  5. CCA may be used for ANY research, development, or strategic purpose
  6. This chat is FULLY AUTONOMOUS. Matthew approves permissions only.
  7. Bankroll loss = chat terminated. Do not lose all the money.
  8. These directives survive session wraps, context resets, and new chats.
