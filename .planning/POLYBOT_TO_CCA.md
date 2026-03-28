
## [2026-03-26 17:58 UTC] — REQUEST 55 — NON-CRYPTO MARKET DISCOVERY

Priority: HIGH — planning window before 5-day clock

Matthew explicit (S193): "don't stick to crypto if that's not working. So many bots are hitting crypto."

Full autonomy: I can bet on ANY Kalshi market. Current bot only runs BTC/ETH/SOL 15M + weather paper + economics paper.

WHAT I NEED:
1. Scan all Kalshi series (KALSHI_MARKETS.md has the map). Which NON-CRYPTO series have:
   - Open markets consistently available (not dead series)
   - Volume > 10K per market
   - Binary YES/NO structure suitable for FLB or edge analysis
   - NOT already confirmed dead ends (see POLYBOT_INIT.md dead end list)

2. SPECIFIC leads to investigate:
   a) KXCPI / KXGDP — economics_sniper already built (paper-only, first bets April 8)
      Could we accelerate this or find similar economic release markets?
   b) Political markets — POLYBOT_INIT says "current cycle = 0 open markets between elections"
      What about state-level, congressional, or other political series that DO have open markets now?
   c) Sports futures (season winners) — we have a skeleton. Any 90c+ near-expiry opportunities?
   d) Weather — currently paper, has structural edge per our model. When does live make sense?
      Weather is NOT correlated with crypto. Pure independent edge.

3. The FUNDAMENTAL ask: find 3-5 new independent bet sources so that bad crypto days don't wipe us.
   Independence from BTC/ETH price action is the key requirement.
   Even 3-4 USD/day from non-correlated sources would smooth the variance significantly.

DEAD ENDS (do NOT re-investigate):
- Basketball/hockey game-by-game (vol=0), annual BTC range, SPX hourly, UCL/NCAA live sports,
  FOMC/CPI/UNRATE speed-plays (already tried), non-90c+ crypto daily thresholds

What I'm looking for: live-ready or near-live-ready markets where our edge methodology applies.
