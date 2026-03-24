# What Self-Learning Actually Means — Standing Directive
# Matthew's explicit directive, S129 (2026-03-24)
# "Smarter, smoother, more capable, more accurate, more innovative,
#  better critical thinking."

## What Self-Learning IS

Self-learning means the bot gets objectively better at its core function
over time without human intervention. The measure is P&L and win rate —
not lines of code, not analytical modules, not report volume.

Concrete examples of REAL self-learning:
- Bayesian posterior: observes every settled bet → adjusts Kelly fraction automatically.
  NEXT bet is more accurately sized. No human needed. This is the model.
- Auto-guard discovery: statistical test fires → bucket blocked automatically.
  NEXT bet in that bucket never happens. No report, no human, no wait. This is the model.
- CUSUM triggering a guard: not flagging it for review, actually blocking it.
  The system defends itself.
- Signal threshold adaptation: calibration data feeds back into minimum edge_pct.
  If a price zone is systematically mispriced, the threshold for betting there adjusts.
- Feature weighting: Dim 9 signal_features eventually teaches the bot WHICH windows
  to skip — not via a rule, via learned probability.

## What Self-Learning IS NOT

- A reporting pipeline that generates dashboards requiring human interpretation
- A 256-bucket analysis tool that produces a markdown report
- More analytical modules bolted onto the outside of a working system
- Flags and proposals waiting for human review before taking effect
- Complexity layered on complexity — "a Gundam fighter with 50 million attachments"

The test: does the bot make a better bet NEXT time, automatically?
If the answer is "only after a human reads a report and acts on it," it's not self-learning.

## The Right Approach

### Passive (runs automatically, changes behavior)
1. Bayesian posterior (EXISTS) — Kelly fraction updates on every settlement
2. Auto-guard discovery (EXISTS) — fires automatically at p < 0.20, n >= 10
3. CUSUM per bucket → auto-guard wire-up (PARTIAL — CUSUM runs but needs to trigger guard automatically, not just report)
4. Calibration feedback → signal threshold adjustment (NOT YET BUILT)

### Active (runs periodically, informs human decisions)
Analysis tools are appropriate ONLY for decisions that genuinely require human judgment:
- Disabling a strategy (requires structural basis + data + p-value + review)
- Changing a core parameter (requires 30+ bets + Matthew approval)
- Identifying entirely new edges (requires research, can't be automated)

Analysis that flags things already handled by automated guards = noise, not signal.

## What to Build vs What NOT to Build

BUILD:
- Wire CUSUM trigger → auto-guard directly (no intermediate report needed)
- Calibration bias → adjust minimum bet threshold per price zone automatically
- Signal feature importance → weight signals by learned historical accuracy
- Anything that makes the next bet better without human involvement

DO NOT BUILD:
- More report generators
- More analysis pipelines with more charts and tables
- Modules that require reading and manual action
- Anything that makes the codebase more complex without making the bot smarter

## The North Star

One sentence: after N bets, is the bot winning more often and losing less?
Not: after N sessions, is the analysis richer?
Not: after N months, is the codebase more sophisticated?

The Bayesian posterior is the proof of concept. It's invisible, automatic, and it works.
Every self-learning feature should aspire to that standard.

## The kalshi_self_learning.py Assessment (honest)

What was built in S129: an analysis and reporting tool, not a self-learning system.
It gives useful snapshots (calibration bias, bucket health, Kelly comparison).
But it does not change bot behavior — it generates reports for human review.

That is useful as analysis infrastructure. It is NOT the self-learning goal.
The self-learning goal is: wire the outputs back into the bot's decision-making automatically.
Until that wire exists, it is a dashboard. Useful, but not the target.

Immediate next step to make it real self-learning:
  CUSUM S >= 5.0 in any bucket → auto_guard fires without human involvement.
  That's one wire. That converts a reporting feature into actual self-learning.
