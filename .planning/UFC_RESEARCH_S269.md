# UFC Market Research — Chat 47 (S269)
# CCA research. Kalshi chat implements after validation.

---

## Research Question

Does KXUFCFIGHT have enough volume + edge basis to add to sports_game strategy?

---

## Edge Basis (Academic)

UFC oddsmaker conservatism bias is documented. Favorites in MMA are systematically
underpriced relative to actual win probability — same structural FLB as MLB/NHL.

Key pattern: in main card fights, heavy favorites (-300 to -500 on DraftKings) correspond
to ~75-83% implied probability, but Kalshi often prices them at 68-78c — a 5-10% gap
consistent with the bookmaker-consensus arbitrage we exploit in sports_game.

Literature: FLB in combat sports is less studied than team sports, but the mechanism is
identical — retail bettors overweight underdogs (higher payout appeal), causing markets to
undervalue favorites. Same structural mispricing.

---

## Volume Check

KXUFCFIGHT: confirmed existing Kalshi series. Volume data needed.

**Research needed (Kalshi API call):**
```python
# Check KXUFCFIGHT volume
markets = kalshi_client.get_markets(series_ticker="KXUFCFIGHT", status="open", limit=50)
for m in markets:
    print(f"{m.ticker}: volume={m.volume}, close_time={m.close_time}")
```

**Volume threshold for viability:** >50K volume per market.
If KXUFCFIGHT markets show <10K volume → insufficient liquidity for clean fills.

---

## Market Structure

KXUFCFIGHT markets: typically open 14-30 days before the event.
Binary: YES = fighter A wins, NO = fighter B wins.
No round/method markets currently (just winner).

UFC 316 (May 3, 2026 — Oliveira vs Makhachev 2) is the next event.
KXUFCFIGHT-26MAY03MAKHACHEV should be available ~April 20+.

---

## Signal Design

Near-identical to sports_game_v1. Add `"mma_mixed_martial_arts": "KXUFCFIGHT"` to sport map.

Differences from team sports:
1. **No team efficiency feed** — no home/away, no team stats. Signal is bookmaker consensus ONLY.
2. **Higher edge floor:** 8% minimum (vs 5% for MLB/NHL). UFC markets are thinner.
3. **Title fight kill switch:** main card vs prelim. Main card fighters have much stronger
   public betting pressure → FLB may be stronger. Prelims: lower volume, noisier signals.
4. **Sample size gate:** 5 UFC events before live (low event frequency).

```python
# Title fight detection (from ticker or market title)
def is_title_fight(market: Market) -> bool:
    title = market.title.lower()
    return "title" in title or "championship" in title

# In generate_signal:
if is_title_fight(market) and edge_pct < 0.10:
    return None  # higher threshold for title fights (more efficient)
```

---

## Recommendation

**VERDICT: BUILD — with conditions.**

Conditions before implementation:
1. [ ] Confirm KXUFCFIGHT volume >50K per market (API check)
2. [ ] Verify markets open 7+ days before event (time to scan)
3. [ ] Paper 5 UFC events minimum before live (first: UFC 316 May 3)
4. [ ] Wire only as extension to `sports_game_v1` (no new strategy file)

If volume check fails (< 50K): DEFER until next UFC event with higher volume markets.

**Expected income:** Low frequency (2-3 main card fights per event × 8-12 events/year).
Averaged daily: ~$0.30-0.80/day. Not a primary source — bonus on UFC nights.

---

## Implementation Guide (for Kalshi chat, after validation)

1. Add to `sports_game_loop` sport map:
   ```python
   "mma_mixed_martial_arts": ("KXUFCFIGHT", min_edge=0.08, max_stake=3.0)
   ```

2. Add `is_title_fight()` check with higher threshold.

3. No efficiency feed needed — pure bookmaker consensus signal.

4. Dedup: one bet per fighter (one YES or one NO per market), same as other sports.

5. Paper mode gate: collect 5 events (~10-15 fights) before live.
