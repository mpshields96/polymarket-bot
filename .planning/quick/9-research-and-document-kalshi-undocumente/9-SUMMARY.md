---
phase: quick-9
plan: 9
subsystem: documentation
tags: [kalshi-markets, research, probe, documentation]
dependency_graph:
  requires: []
  provides: [updated-kalshi-markets-reference]
  affects: [future-strategy-research, session-handoff]
tech_stack:
  added: []
  patterns: []
key_files:
  created: []
  modified:
    - .planning/KALSHI_MARKETS.md
decisions:
  - KXBTCMAXW confirmed permanently dormant on a weekday (Tue Mar 11). Remove from probe rotation permanently.
  - KXCPI reclassified from "low freq" to "moderate activity — revisit post expansion gate" (74 open markets, not ~1,400 vol as previously estimated).
metrics:
  duration: 3 minutes
  completed: 2026-03-11
---

# Quick Task 9: Session 48 Kalshi Market Probe — KALSHI_MARKETS.md Update

One-liner: Updated KALSHI_MARKETS.md with Session 48 weekday probe confirming KXBTCMAXW permanently dormant and reclassifying KXCPI to moderate activity (74 open markets found vs prior ~1,400 vol estimate).

## What Was Done

Documentation-only update. No code changes. All work was targeted edits to .planning/KALSHI_MARKETS.md with 8 distinct changes.

## Files Changed

.planning/KALSHI_MARKETS.md — 108 lines added, 16 lines modified

## Key Findings Documented

KXBTCMAXW (conclusively dormant):
  Prior status: "dormant on Sunday, probe on weekdays"
  Session 48 finding: 0 open markets on Tuesday March 11, 2026
  New status: CONFIRMED PERMANENTLY DORMANT — not a weekend artifact
  Action: Removed from active probe rotation. Do not build. Do not probe further.

KXBTCMAXMON (fresh March 2026 data):
  6 open markets. Top strikes by volume:
    $85,000 strike: vol=59,629 (highest vol strike)
    $82,500 strike: vol=55,387
    $87,500 strike: vol=35,821
  Strikes clustered around current BTC price (~$83k). Near-ATM most liquid.

KXBTCMINMON (fresh March 2026 data):
  8 open markets. Top strikes by volume:
    $65,000 floor: vol=112,301 (highest vol)
    $62,500 floor: vol=109,027
    $60,000 floor: vol=67,491
  Total ~500k+ vol across 8 markets. More liquid than KXBTCMAXMON.
  Market pricing meaningful downside tail risk to $60-65k range.

KXBTCMAXY (Session 48 pricing update):
  7 open markets. Key finding:
    $100k strike: vol=602,841 — highest single-market vol in the series, most tradeable
    $110k strike: vol=244,704
    $150k strike: vol=184,334
  $100k is the focal strike. 600k vol = very liquid for an annual market.

KXBTCMINY (Session 48 data):
  5 open markets. Top strikes by volume:
    $40k floor: vol=207,278 (highest vol)
    $45k floor: vol=184,689
    $50k floor: vol=184,789
  ~200k vol per floor level. Market assigns meaningful probability to BTC dipping to $40-50k in 2026.

KXCPI — MAJOR REVISION:
  Prior estimate: ~1,400 total volume (low freq, skip)
  Session 48 finding: 74 open markets
  Sample: KXCPI-26MAR-T1.0 vol=78, KXCPI-26MAR-T0.9 vol=97
  Individual market volumes remain low (tens to hundreds per market) but 74 open markets
  shows this is a much more active series than previously believed.
  New classification: "moderate activity — revisit signal feasibility after expansion gate opens"
  This is the most significant intelligence update in this probe.

KXFEDDECISION: 80 open confirmed — no change (still active, largest Kalshi market).
KXRATECUTCOUNT: 21 open confirmed — active.
  Top: KXRATECUTCOUNT-26DEC31-T8 vol=119,207, T9 vol=98,432.
  Market concentrated at T8/T9 boundary (1-3 rate cuts expected in 2026).
KXPCE: 0 open — confirmed still dormant.
KXJOLTS: 0 open — confirmed still dormant.
KXUNRATE: 0 open — outside BLS release window (expected, normal).

## Macro Market Hierarchy (Updated Session 48)

KXFEDDECISION (23.4M) > KXRATECUTCOUNT (1.5M+) > KXGDP (208k) > KXCPI (74 mkts, low per-mkt vol) > KXUNRATE (opens near BLS) > KXPAYROLLS (1.6k) > KXPCE/KXJOLTS (0 = dormant)

## Deviations from Plan

None — plan executed exactly as written. All 8 changes applied in order.

## Commits

9171436 docs(quick-9): update KALSHI_MARKETS.md with Session 48 weekday probe findings

## Next Research

Post expansion gate:
  KXCPI signal feasibility study — 74 open markets warrants more analysis of per-market
  liquidity and whether a FOMC-style signal can be adapted for CPI print prediction.

  KXBTCMAX100 barrier model (Tier 2) — first-passage-time GBM pricing vs market odds.
  KXBTCMAX100 DEC 2026 at ~41c (BTC ~$83k needs +19% to $100k) may be mispriced.
  Research order: barrier option model → paper validation → Brier gate → live.

  KXBTCMINY downside model — $40-50k floor at 200k vol each suggests retail edge
  may exist in pricing extreme downside BTC scenarios vs realized vol distribution.

## Self-Check: PASSED

.planning/quick/9-research-and-document-kalshi-undocumente/9-SUMMARY.md — FOUND
commit 9171436 — FOUND
