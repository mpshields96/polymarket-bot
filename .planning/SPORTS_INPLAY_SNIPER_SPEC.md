# Sports In-Play Sniper — Design Spec
# Written by CCA Chat 46 (S269)
# Owner: CCA designs. Kalshi chat implements.

---

## The Opportunity

UCL soccer_sniper (built S164) validates the FLB in-play thesis: near-expiry prices at 90c+
are systematically underpriced by 2-5% because markets overestimate reversal probability.

UCL fires ~8 times/month (8 games). NBA/NHL/MLB have 15-25 games/day.
Same FLB mechanism. Vastly more volume.

**Expected daily triggers:** 5-15 (conservative) to 20+ (all sports, all thresholds met)
**Income at $3/bet, 95% WR:** $0.68-2.03/day → ramp to $5/bet → $1.13-3.38/day

---

## Strategy Spec

### File
`src/strategies/sports_inplay_sniper.py` — mirrors `soccer_sniper.py` architecture exactly.

### Target Series
```python
ELIGIBLE_SERIES = {
    "KXNBAGAME",   # NBA — 15+ games/day, 2.5h game
    "KXNHLGAME",   # NHL — 15+ games/night, 3h game
    "KXMLBGAME",   # MLB — 10+ games/day, 3h game
    # NOT KXUCLGAME — covered by soccer_sniper already
    # NOT KXNCAABGAME — too small volume, different FLB structure
}
```

### Timing Logic (different from soccer)

Soccer: game_start = expected_expiration_time − 3h, entry window = last 90 min
Sports: timing varies by game type. Use same approach — no game clock API.

```python
# NBA: 2.5h average game → game_start ≈ exp_time - 2.5h
# NHL: 2.5h average game → game_start ≈ exp_time - 2.5h  
# MLB: 3.0h average game → game_start ≈ exp_time - 3.0h
# Conservative: treat all as 3h game. Entry window = last 45 min.

_SERIES_GAME_DURATION_HOURS = {
    "KXNBAGAME": 2.5,
    "KXNHLGAME": 2.5,
    "KXMLBGAME": 3.0,
}
_INPLAY_WINDOW_MINUTES = 45  # fire only in last 45 min (configurable)
_PRICE_FLOOR = 0.90          # same as soccer_sniper

def _get_series_key(ticker: str) -> str:
    """Extract series prefix from ticker e.g. KXNBAGAME-26APR07... → KXNBAGAME"""
    for s in ELIGIBLE_SERIES:
        if ticker.startswith(s):
            return s
    return ""

def _get_expected_expiration(market: Market) -> Optional[datetime]:
    """Same as soccer_sniper — pull expected_expiration_time from market.raw"""
    raw_exp = market.raw.get("expected_expiration_time", "")
    if not raw_exp:
        return None
    try:
        return datetime.fromisoformat(raw_exp.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None

def generate_signal(market: Market, now: datetime) -> Optional[Signal]:
    series_key = _get_series_key(market.ticker)
    if not series_key:
        return None
    
    exp_time = _get_expected_expiration(market)
    if not exp_time:
        return None
    
    game_duration_h = _SERIES_GAME_DURATION_HOURS[series_key]
    game_start_est = exp_time - timedelta(hours=game_duration_h)
    
    # Gate 1: Game must have started
    if now < game_start_est:
        return None
    
    # Gate 2: Must be in last N minutes (avoid betting on games about to start)
    seconds_remaining = (exp_time - now).total_seconds()
    if seconds_remaining > _INPLAY_WINDOW_MINUTES * 60 or seconds_remaining <= 0:
        return None
    
    # Gate 3: Price threshold
    yes_price = market.yes_bid  # last traded yes price
    no_price = market.no_bid   # last traded no price
    
    if yes_price >= _PRICE_FLOOR:
        return Signal(side="YES", confidence=yes_price, reason=f"FLB in-play {series_key} YES@{yes_price:.2f}")
    elif no_price >= _PRICE_FLOOR:
        return Signal(side="NO", confidence=no_price, reason=f"FLB in-play {series_key} NO@{no_price:.2f}")
    
    return None
```

### Parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `price_floor` | 0.90 | UCL soccer_sniper validated at 88-93c; conservative 90c for first run |
| `inplay_window_minutes` | 45 | Last 45 min of game → most reliable FLB signal |
| `max_bets_per_day` | 10 | Soft cap during paper validation |
| `stake_usd` | 2.00 | Start at UCL soccer_sniper sizing; ramp after 20-bet validation |
| `paper_mode` | True | MUST be paper initially. Validate 20+ bets before live. |
| `live_gate` | WR ≥ 93% on 20 paper bets | Same gate as soccer_sniper |

### Dedup Rules

1. One bet per game (same `game_key` as `sports_game_loop`)
2. Skip if an open `sports_game` bet already exists for this market
3. Skip if we already have an `in_play` bet for this ticker

```python
# In the loop, before placing:
if ticker in self._bet_tickers_today:
    continue
if self._has_open_sports_bet(ticker):  # check DB for open sports_game bet on same game
    continue
```

### Loop Architecture

Follows `soccer_sniper_loop` exactly. Scan every 60 seconds (not every loop tick).

```python
async def sports_inplay_sniper_loop(
    kalshi_client,
    db_session,
    *,
    stake_usd: float = 2.0,
    paper: bool = True,
    price_floor: float = 0.90,
    inplay_window_minutes: int = 45,
    max_bets_per_day: int = 10,
):
    strategy = SportsInplaySniper(
        stake_usd=stake_usd,
        paper=paper,
        price_floor=price_floor,
        inplay_window_minutes=inplay_window_minutes,
        max_bets_per_day=max_bets_per_day,
    )
    ...
```

Wire in `main.py` alongside `soccer_sniper_loop`:
```python
asyncio.create_task(sports_inplay_sniper_loop(
    kalshi_client=client,
    db_session=session,
    stake_usd=2.0,
    paper=True,
))
```

---

## Key Differences from soccer_sniper.py

| Aspect | soccer_sniper | sports_inplay_sniper |
|--------|--------------|---------------------|
| Series | KXUCLGAME only | KXNBAGAME + KXNHLGAME + KXMLBGAME |
| Game duration | Fixed 90 min football | Variable (2.5-3h estimated) |
| Price floor | 88c | 90c (more conservative) |
| Entry window | Last 90 min | Last 45 min |
| Dedup | One per ticker | One per ticker + skip if open sports_game bet |
| Expected triggers | 0.5/day (UCL only) | 5-15/day |

---

## Edge Validation Plan

**Paper phase (do not skip):**
1. Deploy at 90c floor, 45-min window, $2/bet
2. Run 20 bets minimum (expect ~1-2 weeks given 5-10 triggers/day)
3. Track: WR, avg entry price, avg payout, breakdown by series
4. If WR ≥ 93% → raise to 50c floor, 60-min window (collect more data)
5. If WR ≥ 93% after 40 bets total → go live at $2/bet

**Expected WR range:** 93-97% (UCL paper validated at 95%+ per Session 84)
**Failure mode:** WR < 90% → lower price floor to 88c OR shorten window to 30 min

---

## Income Projection

| Scenario | Triggers/day | Stake | WR | EV/bet | Daily |
|----------|-------------|-------|-----|--------|-------|
| Conservative paper | 5 | $2 | 93% | $0.04 | $0.18 |
| Live start | 10 | $2 | 95% | $0.10 | $1.00 |
| Live ramp | 10 | $5 | 95% | $0.25 | $2.50 |
| Full deployment | 15 | $5 | 95% | $0.25 | $3.75 |

**Honest gap assessment:** This is a $1-4/day source at maturity, not $5-8/day.
To fill the $25/day gap, we need it alongside sports_game AND BTC sniper AND economics.
