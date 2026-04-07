# Phase 9 Wrap + Phase 10 Planning Template
# Written by CCA Chat 52 (S269)
# Fill in after Chats 44-51 complete. Compare actual vs planned.

---

## Phase 9 Audit Checklist

### Layer 1 — Bot Calibration (Chat 44)
- [ ] BUG 1 in-game betting guard live — commit hash: ___
- [ ] Game-date sort live — commit hash: ___
- [ ] 24h horizon guard live — commit hash: ___
- [ ] NCAAB confirmed (KXNCAABGAME verified) — result: ___
- [ ] balance_check.py working — output sample: ___

### Layer 2 — Signal Quality (Chats 38B-43, 45-46)
- [ ] sports_math.py wired into sports_game_loop — commit hash: ___
- [ ] Sharp Score filter active — 20-bet paper WR before vs after: ___
- [ ] In-play sports sniper deployed (paper) — chat 46 done: ___
- [ ] sports_inplay_sniper_loop firing on NBA/NHL/MLB: ___

### Layer 3 — Market Expansion (Chats 47-49)
- [ ] UFC research done — verdict BUILD/DEFER: ___
- [ ] kalshi_series_scout.py deployed — first report date: ___
- [ ] Economics sniper live (KXCPI April 10 bet result): ___

### Layer 4 — Session Intelligence (Chats 50-51)
- [ ] KALSHI_INIT_CHECKLIST.md in use — Kalshi chat confirmed reading: ___
- [ ] PreCompact/PostCompact hooks wired in Kalshi project: ___
- [ ] ACTIVE_DIRECTIVES.md rewritten at last session start: ___
- [ ] SESSION_HANDOFF.md in new numbered format: ___
- [ ] /polybot-init updated to run checklist: ___
- [ ] /polybot-auto updated with 3rd-cycle CCA check: ___

---

## Phase 9 P&L Impact Measurement

### Baseline (pre-overhaul, 7 days before S268):
- Daily P&L: ___ USD/day (fill from DB)
- Strategies live: BTC sniper + sports_game
- Win rate: ___

### Post-overhaul (7 days after full deployment):
- Daily P&L: ___ USD/day (fill from DB)
- Strategies live: BTC + sports + in-play + economics
- Win rate: ___
- Delta: ___ USD/day improvement
- Profit concentration in top strategy: ___%
- Negative-day rate: ___ / 7
- Median CST daily P&L: ___

### Target vs Actual:
| Source | Projected (INCOME_MAP_S269) | Actual | Delta |
|--------|-----------------------------|--------|-------|
| BTC sniper | $3-4/day | ___ | ___ |
| Sports game | $2-4/day | ___ | ___ |
| In-play sniper | $0-1/day (paper) | ___ | ___ |
| Economics | $0.33/day avg | ___ | ___ |
| **Total** | **$6-10/day** | ___ | ___ |

---

## Phase 10 Planning Template (fill in based on Phase 9 gaps)

### Carry-forward items from Phase 9 (anything incomplete):
1. ___
2. ___

### New gaps identified during Phase 9:
1. ___
2. ___

### Phase 10 structure (template — adapt based on gaps):

**Layer 1 — Sports Math Phase 2-3 (if not done in Phase 8):**
- Efficiency feed Phase 2 (injury_data.py — Chat 39)
- PDO/RLM Phase 3 (Chat 40-41)
- NHL goalie data Phase 4 (Chat 42)

**Layer 2 — In-Play Sniper Hardening:**
- 20-bet paper validation complete → live promotion at $2/bet
- WR confirmation → raise to $5/bet
- Add soccer leagues to sniper (if UCL validates)

**Layer 3 — NBA Playoff Strategy:**
- April 19 playoffs open → monitor KXNBAGAME volume spike
- Validate sports_game WR on playoff games (different FLB structure?)
- Consider playoff-specific threshold adjustments

**Layer 4 — Economics Full Suite:**
- KXCPI live (April 10 validates)
- KXFED wire for May 7 meeting
- KXUNRATE wire for May 2 release
- KXGDP wire for April 30

**Phase 10 income target:** $12-18/day
**Phase 10 condition:** Complete if Phase 9 achieved ≥ $8/day. Skip if not.

---

## Go/No-Go for Phase 10

**GO if:**
- Phase 9 daily income ≥ $8/day (above current baseline)
- No active bleeding strategies
- Bot running stably for 7 days post-overhaul
- Top-strategy profit concentration < 80% OR clear second-engine progress is visible

**NO-GO if:**
- Phase 9 income < $6/day (overhaul underperformed)
- In-play sniper paper WR < 90% (thesis not validated)
- Major bug discovered that needs another calibration round
- One strategy still contributes >80% of trailing profit with no real second engine

**NO-GO action:** Write Phase 9.5 (targeted fixes) instead of Phase 10.
