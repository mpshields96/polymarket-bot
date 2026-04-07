# 25 USD/Day Income Map — Phase 9 Design
# Written by CCA Chat 38C (S269)
# Status: DESIGN — gap analysis for Kalshi chat to execute against

---

## Current Honest P&L Baseline (pre-overhaul)

| Strategy | All-Time | April CST | Daily Avg | Status |
|----------|----------|-----------|-----------|--------|
| daily_sniper_v1 (BTC) | +$118.70 | +$67.12 | ~$7-10 (uncapped) | LIVE (now capped) |
| sports_game_nhl_v1 | +$33.66 | +$33.66 | ~$8 (tiny sample) | LIVE |
| eth_daily_sniper_v1 | −$4.11 | −$4.11 | −$0.55 | DISABLED |
| sports_game_nba_v1 | −$19.67 | −$19.67 | negative | DISABLED pending investigation |
| sports_game_mlb_v1 | −$2.99 | −$2.99 | negative | wiring/bug issues |

**Effective daily income today: ~$3-7 (BTC sniper capped, NBA off, MLB bug)**
**Gap to $25: ~$18-22/day**

---

## Source-by-Source Analysis

### Source 1: BTC Daily Sniper (KXBTCD)

**Edge:** FLB at 90-93c near-expiry. Strongest confirmed edge in the book.
**After cap (Kelly-derived — see SNIPER_LIMITS_RATIONALE.md):**
- Cap: $5/bet, 10 bets/day
- Conservative (95.8% WR): **$2.64/day**
- Optimistic (99% WR, confirmed at 500+ bets): **$4.40/day**

**Gap:** Sniper alone cannot reach $25/day at safe caps. This is correct and intentional.
Do not raise caps to compensate for gaps elsewhere.

**Growth path:** After 500 live bets confirm 99% WR → recalculate → potentially $7-10/day at higher N.

---

### Source 2: Sports Game (MLB/NHL/NBA — post Sharp Score + efficiency feed)

**Edge:** FLB in binary outcome markets where bookmaker consensus diverges from Kalshi price.
SPRT lambda=+6.139 (statistically significant edge confirmed).

**Current state:** NHL 100% WR (4 bets), MLB -100% (2 bets, bugs present), NBA disabled.

**After overhaul (Chats 44-45 wired):**
- Bug fixes: in-game betting, date sort, horizon guard
- Sharp Score filter (sports_math.py already delivered S165)
- Efficiency feed (Chat 38B delivered — Kalshi wires in Chat 45)
- Net expected bets/day: 5-10 filtered bets across MLB/NHL (basketball playoffs April 19+)

**Expected daily income (post-fix, $3/bet, 60% WR on filtered bets at 55c avg buy):**
- EV per bet at 55c: 0.60 × ($3 × 0.45/0.55) − 0.40 × $3 = $1.47 − $1.20 = $0.27/bet
- At 8 bets/day: **$2.16/day (near-term)**
- At $5/bet: **$3.60/day**

**NBA Playoffs (April 19+):** 4 games/night, higher volume, stronger sharp consensus.
Estimated additional $2-3/day once wired and validated.

**Near-term target (pre-playoffs): $2-4/day**
**Post-playoffs (April 19+): $4-7/day**

---

### Source 3: In-Play Sports Sniper (NBA/NHL/MLB — NEW, Chat 46 design)

**Edge:** FLB at 90c+ near game end — same mechanism as UCL soccer_sniper (paper-validated S165).
Near-expiry markets are best calibrated; 90c+ prices systematically underpriced by 2-5%.

**Why this is the gap-filler:**
- 15-20 NBA/NHL/MLB games/day (regular season)
- ~20-30% of games end with one side at 90c+ in final minutes
- Expected 3-6 triggers/day (conservative), 10-15 triggers/day (optimistic)

**Design (see Chat 46 for full spec):**
- Trigger: `expected_expiration_time − now < 25 min` AND Kalshi price ≥ 90c
- Side: buy the favored side (YES or NO per price)
- Size: $3-5/bet initially (paper → live after 20 bets)
- Dedup: one bet per market (already in place)

**Expected daily income:**
- Conservative (5 triggers/day, $3/bet, 95% WR at 91c avg):
  5 × (0.95 × $0.30 − 0.05 × $3) = 5 × $0.135 = **$0.68/day**
- Mid (10 triggers/day, $3/bet):
  10 × $0.135 = **$1.35/day**
- Optimistic (15 triggers/day, $5/bet, 97% WR):
  15 × (0.97 × $0.495 − 0.03 × $5) = 15 × $0.330 = **$4.95/day**

**IMPORTANT:** At $3/bet and modest trigger rate, this is NOT a $5-8/day source on its own.
It becomes meaningful at $5/bet AND high trigger volume (15+/day) AND confirmed WR.

**Path to $5-8/day:** Paper 20 bets → live at $3 → paper 20 more → raise to $5 → paper 20 → live at $5.
With 15 triggers/day at $5: **$3.96-4.95/day**. Add soccer in-play: +$1-2/day.

---

### Source 4: Economics Sniper (KXCPI/KXFED/KXUNRATE/KXGDP)

**Edge:** FLB on economic consensus releases — forecasters anchor on prior readings.
Strong academic basis (see EDGE_RESEARCH docs). High volume markets (KXCPI: 1M+).

**Volume constraint:** Monthly events only. Can't be a daily income source.
- KXCPI: ~1 event/month → 1-3 bets/event
- KXFED: ~8 meetings/year → ~0.5 events/month
- KXUNRATE: monthly → ~2 bets/month
- KXGDP: quarterly → infrequent

**Expected monthly bets:** 8-12 bets/month across all 4 markets
**At $10-15/bet (rare + high confidence):**
- EV per bet at 90c (typical economics sniper level): $0.99/bet
- Monthly income: 10 bets × $0.99 = $9.90/month = **$0.33/day averaged**

**Economics sniper is a supplement, not a primary source.**
When a KXCPI event fires (April 10), it should contribute $3-5 that day.
But daily average is only $0.33/day.

**Next economics events:**
- KXCPI April 10 (4 days) — paper bet should auto-fire when market opens
- KXFED May 7
- KXUNRATE May 2
- KXGDP April 30

---

### Source 5: Soccer In-Play (UCL/EPL/Bundesliga/La Liga)

**Edge:** UCL FLB at 90c+ confirmed (paper validation, Session 84). EPL/other leagues: same structural mechanism, volume lower.

**Seasonal constraint:** UCL QF 2nd legs April 14-15 (HIGH priority), then semi-finals.
EPL: 10 matchdays remaining through May. Bundesliga/La Liga similar.

**Expected triggers:** 3-5 UCL games remaining in competition × 2-3 90c+ triggers each = 6-15 UCL triggers total.
EPL: 1-2 triggers per matchday (only the heavily favored side hits 90c+).

**Daily averaged over season remainder:** ~0.5-1.5 bets/day
**At $3/bet, 95% WR:** $0.068-$0.204/day

**Soccer sniper is a bonus on matchdays, not daily income.**

---

## Gap Analysis — Path to $25/Day

### Today (pre-overhaul, bot off):
- BTC sniper (capped): $2.64/day
- Sports game: ~$0/day (bugs, disabled)
- Everything else: $0/day
- **Total: ~$2.64/day**
- **Gap to $25: $22.36/day**

### Phase 9 Target (post all Chat 44-52 work, late April):
| Source | Daily Target |
|--------|-------------|
| BTC sniper (10 bets/day, $5) | $3.00 - $4.40 |
| Sports game MLB/NHL (post Sharp Score) | $2.00 - $4.00 |
| Sports game NBA playoffs (April 19+) | $2.00 - $3.00 |
| In-play sports sniper (once live) | $1.35 - $3.00 |
| Economics sniper (event days only) | $0.30 - $0.50 avg |
| Soccer in-play (matchdays) | $0.20 - $0.50 avg |
| **Total Phase 9 target** | **$8.85 - $15.40/day** |

### Honest Assessment:
**$25/day is NOT achievable in April 2026 at safe caps.**

The path to $25/day requires:
1. **Bankroll growth:** Current $223. At $500 bankroll → double all sizes → double income.
   At $5/bet Kelly-correct sizing: $8.85-$15.40/day (above).
   At $10/bet (when bankroll reaches $450+): $17-31/day.

2. **Sample size to confirm WR:** 500+ live BTC bets to confirm 99% WR → then raise to 20 bets/day → $8.80/day from sniper alone.

3. **NBA playoffs:** April 19+ is the biggest near-term opportunity. 4 games/night at high volume. Estimated +$2-4/day incremental.

4. **Time:** The compounding math requires 2-3 months of consistent profits to grow bankroll from $223 → $450+.

### Realistic Milestones:
- **April 13 (overhaul complete):** $6-10/day (bugs fixed, Sharp Score wired, in-play live)
- **May 1 (post-playoffs start):** $10-15/day (NBA/NHL playoffs, raised caps)
- **June 1 (bankroll ~$350):** $12-18/day (slightly higher sizing)
- **August 1 (bankroll ~$500):** $18-25/day (Kelly-correct at grown bankroll)

**$25/day is an August 2026 target, not April. Chase it with patience, not with unsafe sizing.**

---

## What NOT To Do

1. **Do NOT raise bet sizes beyond Kelly to chase $25/day.** Ruin risk increases nonlinearly.
2. **Do NOT re-enable ETH sniper.** Wait for 50+ paper bets at ≤85c to confirm WR ≥ 92%.
3. **Do NOT bet on 1-book Odds API signals.** REQ-072 confirmed these are noise.
4. **Do NOT expand to markets without structural basis.** FLB only applies where bookmakers trade.
5. **Do NOT lower Sharp Score threshold below grade B.** Filtering exists for a reason.
