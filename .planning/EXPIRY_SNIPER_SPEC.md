# EXPIRY_SNIPER_SPEC.md — Kalshi High-Probability Expiry Sniping Strategy
# Researched Session 53/54 — 2026-03-11
# Source: processoverprofit.blog V6 + V7 Kalshi bot, Reddit r/PredictionMarkets post,
#         commenter analysis, NightShark documentation, Session 53 EV research
# ══════════════════════════════════════════════════════════════════════════════════

## OVERVIEW — WHAT THIS STRATEGY DOES

"Expiry sniping" = enter a 15-min Kalshi binary near the END of its window
when momentum has ALREADY established a strong directional price (90c+).
You're not predicting the direction — you're collecting premium on a near-certainty.

Academic basis: **Favorite-longshot bias** (Snowberg & Wolfers, CEPR)
  → Humans systematically undervalue heavy favorites in binary outcomes
  → A 90c market closes YES MORE OFTEN than 90% of the time
  → Edge = the underpricing of near-certain outcomes

This is a COMPLEMENTARY strategy to btc_drift:
  - btc_drift fires at 35-65c (neutral zone — momentum plays)
  - expiry_sniper fires at 90c+ (high confidence zone — harvest premium)
  - These two strategies almost NEVER conflict — they operate in opposite price zones
  - When btc_drift is blocked by price guard (bearish/bullish extremes), expiry_sniper FIRES

## ORIGINAL STRATEGY — PROCESSOVERPROFIT V7 (reconstructed from blog, 2026-03-11)

Source: https://code.processoverprofit.blog/docs/youtube-code/video-7-kalshi-bot-v2
Security warning: DO NOT use their NightShark/JavaScript code — see SECURITY ANALYSIS below.
This spec reconstructs the LOGIC ONLY using our own clean API implementation.

### Core Parameters

  triggerPoint   = 90    (c) — enter when YES or NO price exceeds 90c
  exitPoint      = 40    (c) — stop-loss: exit if price drops below 40c while in position
  triggerMinute  = 14    (min) — only enter when ≤14 minutes remain in the 15-min window
                                  NOTE: 14 min = 1 min into a 15-min window (from expiry end)
                                  In absolute terms: enter only in the LAST MINUTE of the window

### Entry Logic (complete)

  WAIT: until remaining_seconds <= (15 * 60) - (triggerMinute * 60)
  ACTUALLY: triggerMinute=14 means "at least 14 minutes remaining" → enter at minute 1 or 2

  CORRECTION (from re-reading): isXMinRemaining(14) is TRUE when ≤14 minutes remain
  So entry window = any point where ≤14 min remain AND price > 90c AND no position

  Entry conditions (ALL must be true):
    1. remaining_time <= 14 * 60 seconds (≤14 min left in 15-min window)
    2. is5SecBeforeQuarter() == FALSE (not within 5s of window close)
    3. position == 0 (no open position in this window)
    4. YES price > 90c → enter YES (UP)
       OR NO price > 90c → enter NO (DOWN)
       (whichever side is above 90c — there can only be one at a time since YES+NO≈100)

  Time check function:
    is5SecBeforeQuarter() → TRUE when (minute % 15 == 14) AND (second >= 55)
    Blocks entry in final 5 seconds when settlement is imminent

### Exit / Stop-Loss Logic

  While in position, continuously monitor:
    - If YES position AND YES price drops below 40c → STOP LOSS (exit immediately)
    - If NO position AND NO price drops below 40c → STOP LOSS (exit immediately)
    - If is5SecBeforeQuarter() → HARD EXIT (let it settle, no more action)

  DoubleExitCheck(): verify stop-loss condition is STILL true before executing
    Prevents false exits from momentary price blips during OCR reads

### Order Execution

  Retry loop: 4 iterations, 4000ms sleep between attempts
  Position confirmation: wait until position_qty > 0 (confirms fill)
  Monitoring loop: 50ms polling interval while position is open
  Skip if position already exists (prevents duplicate entries)

### V6 vs V7 Comparison (evolutionary context)

  V6 (video-6-Kalshi-15-Min):           V7 (video-7-kalshi-bot-v2):
    triggerPoint = 85                      triggerPoint = 90 (stricter)
    exitPoint = NONE                       exitPoint = 40 (stop-loss added)
    triggerMinute = NONE (any time)        triggerMinute = 14 (time filter added)
    skip_last = 60 seconds                 is5SecBeforeQuarter() (hard exit)
    polling = 100-1000ms exponential       polling = 50-4000ms

  V7 improvements: higher entry threshold + stop-loss + time filter = better EV + risk mgmt

## EV MATHEMATICS

  Setup:
    Enter at 90c YES (or NO). Cost = 90c. Payout if WIN = 100c. Net profit = 10c.

  With stop-loss at 40c:
    If price hits 40c before expiry → exit. Loss = 90c - 40c = 50c.
    Win: +10c | Loss: -50c
    Breakeven win rate = 50 / (50 + 10) = 83.3%

  Without stop-loss (let expire):
    Win: +10c | Loss: -90c
    Breakeven win rate = 90 / (90 + 10) = 90.0% exactly

  Claimed win rate: ~90% at 90c threshold (favorite-longshot bias)

  With stop-loss: EV = 0.90 * 10 - 0.10 * 50 = 9 - 5 = +4c per 90c bet = +4.4% ROI
  Without stop-loss: EV = 0.90 * 10 - 0.10 * 90 = 9 - 9 = 0 (breakeven at exactly 90%)

  STOP-LOSS RISK (from Reddit commenter): At 40c with 1 min left in a moving Kalshi
  15-min market, the orderbook is THIN. The "40c exit" may not fill. Slippage risk is
  asymmetric — you exit at 35c, 30c, even 20c if market is illiquid.

  RECOMMENDATION: Start WITHOUT stop-loss to measure actual win rate. If win rate < 87%,
  add stop-loss only if orderbook depth confirms fills are available at 40c+ consistently.

## COMMENTER ENHANCEMENTS (Reddit, 2026-03-11)

  From commenter on original Reddit post:

  1. VARIABLE BET SIZING: "This is not profitable long term without variable bet sizing"
     → We already have Kelly criterion in calculate_size()
     → Kelly will naturally size up when edge is large (90c = high confidence = smaller Kelly
        since payout is 10c on 90c stake = poor Kelly ratio vs btc_drift at 55c)
     → Our Kelly is the CORRECT fix for their flat-sizing weakness

  2. MINIMUM COIN DELTA THRESHOLD: "minimum coin delta threshold (0.1% per coin)"
     → This is our existing min_drift_pct concept applied to expiry sniping
     → Require underlying crypto moved >= 0.1% from window OPEN before entering
     → Filters out "stuck at 90c because no trading activity" vs "reached 90c via momentum"
     → Maps to: min_drift_pct = 0.001 (0.1%) for expiry_sniper

  3. STOP-LOSS LIQUIDITY RISK: "stop-loss has liquidity risks if you're not careful"
     → As noted in EV math above — 40c stop may not fill in thin markets
     → Kalshi 15-min markets thin out in final 2 minutes; spread widens
     → Our approach: track fill prices in DB, measure actual slippage, add stop-loss
        only if empirical data shows fills close to 40c

  4. STRATEGY NAME: "the concept is called 'expiry sniping'"
     → This is an established trading concept: enter near expiry on high-probability outcome

## ORIGINAL AUTHOR'S TOOLCHAIN (DO NOT USE)

  Two components in the original bot:

  A. NightShark (Windows-only desktop app, screen automation)
     - User "records" screen regions using a visual snipping tool
     - Each region = area[N] in scripts (indexed from 1)
     - read_areas() → refreshes all mapped regions via OCR screenshot
     - toNumber(area[N]) → strips "$", ",", "%" → returns float
     - Blank region → returns 0 (edge case risk)
     - Scripts run on Windows only — NOT available on macOS/Linux

  B. JavaScript HUD (browser-injected overlay)
     - Reads DOM via data-testid selectors from Kalshi's web UI
     - Displays YES/NO prices + time remaining in floating HTML element
     - State stored in window.__KALSHI_HUD_STATE__ and localStorage
     - Executes clicks: "Review" button → "Submit" button (2-step Kalshi order flow)

  Area array mapping for V7 Kalshi bot:
    area[1] = UP (YES) price in cents (e.g., "90" → 90.0)
    area[2] = DOWN (NO) price in cents (e.g., "10" → 10.0)
    area[3] = Remaining time / session timer (seconds remaining or HHMMSS format)
    area[4] = Position quantity (0 = no position, >0 = active position)

## SECURITY ANALYSIS — WHY WE BUILD OUR OWN

  JavaScript HUD RISKS:
  - Runs in same browser session as authenticated Kalshi.com
  - Has full access to session cookies, localStorage, IndexedDB
  - Can read auth tokens, make API calls on your behalf
  - Unknown author code runs AS YOU — same permissions as if you typed it
  - We NEVER use browser-injected JavaScript from unknown sources

  NightShark RISKS (lower but real):
  - Windows-only (not applicable on macOS — our deployment)
  - Screen OCR: misreads can cause wrong entry/exit at wrong prices
  - Race conditions: read_areas() between reads can lead to stale data
  - No connection to our DB, kill_switch, risk management
  - Single point of failure — no retry/error handling at our level

  OUR APPROACH: 100% clean Python via Kalshi REST API
  - Same auth (RSA-PSS kalshi_auth.py) — already working
  - Same market probing (kalshi.py get_markets) — already working
  - Same execution (live.py execute()) — already working
  - Same kill switch (kill_switch.check_order_allowed()) — mandatory
  - Same DB recording (db.save_trade()) — already working
  - Full signal logging, Brier tracking, graduation system

## CLEAN IMPLEMENTATION SPEC — FOR THE NEW ACTIVE CHAT

### New Strategy Class: ExpirySniper

File: src/strategies/expiry_sniper.py

```python
class ExpirySniperSignal(NamedTuple):
    side: str           # "yes" or "no"
    price_cents: float  # current YES price in cents
    yes_price: float    # same (for consistency with other strategies)
    seconds_remaining: int
    min_drift_met: bool # whether underlying coin moved >= min_drift_pct

class ExpirySniperStrategy:
    name = "expiry_sniper_v1"

    # Core V7 parameters
    TRIGGER_PRICE_CENTS = 90.0      # enter when YES or NO >= this
    STOP_LOSS_CENTS = None          # None = no stop-loss (start without)
    MAX_SECONDS_REMAINING = 14 * 60 # 840s = 14 min remaining
    HARD_SKIP_SECONDS = 5           # don't enter in final 5s of window

    # Our enhancement (commenter's coin delta threshold)
    MIN_DRIFT_PCT = 0.001           # 0.1% underlying coin move since window open

    # Price guard: INVERTED from btc_drift (we WANT extreme prices here)
    # This strategy explicitly targets >= 90c (the opposite of btc_drift 35-65c)
    MIN_SIGNAL_PRICE_CENTS = 87.0   # slight buffer below 90c for market fluctuation

    def generate_signal(
        self,
        current_yes_price: float,    # current YES price from Kalshi API (cents)
        seconds_remaining: int,       # seconds until window closes
        coin_drift_pct: float,       # % move of underlying crypto since window open
    ) -> Optional[ExpirySniperSignal]:

        # Time guard: only enter when window is nearly closed
        if seconds_remaining > self.MAX_SECONDS_REMAINING:
            return None
        if seconds_remaining <= self.HARD_SKIP_SECONDS:
            return None

        # Coin delta filter (commenter's enhancement)
        if abs(coin_drift_pct) < self.MIN_DRIFT_PCT:
            return None  # price at 90c without momentum = stale/HFT noise

        # Determine which side is at trigger price
        current_no_price = 100.0 - current_yes_price

        if current_yes_price >= self.TRIGGER_PRICE_CENTS:
            # YES side is at 90c+ — bet YES
            return ExpirySniperSignal(
                side="yes",
                price_cents=current_yes_price,
                yes_price=current_yes_price,
                seconds_remaining=seconds_remaining,
                min_drift_met=True,
            )
        elif current_no_price >= self.TRIGGER_PRICE_CENTS:
            # NO side is at 90c+ — bet NO
            return ExpirySniperSignal(
                side="no",
                price_cents=current_yes_price,  # always YES price for payout calc
                yes_price=current_yes_price,
                seconds_remaining=seconds_remaining,
                min_drift_met=True,
            )

        return None
```

### New Trading Loop: expiry_sniper_loop()

File: main.py (add alongside existing drift loops)

```python
async def expiry_sniper_loop(
    strategy: ExpirySniperStrategy,
    btc_feed: BinancePriceFeed,        # reuse existing feed
    kalshi_client: KalshiClient,
    db: Database,
    kill_switch: KillSwitch,
    live_executor_enabled: bool = False,  # START FALSE — paper only
    paper_exec: PaperExecutor = None,
    trade_lock: asyncio.Lock = None,
    calibration_max_usd: Optional[float] = 0.01,  # micro-live initially
):
    """
    Expiry sniping loop for KXBTC15M/KXETH15M/KXSOL15M/KXXRP15M
    Targets near-expiry contracts at 90c+ YES or NO price.
    Entry: last 14 minutes of window, one side >= 90c, coin moved >= 0.1%
    Exit: let settle (no stop-loss initially), or stop-loss at 40c if empirical data supports
    """
```

### Key Integration Points

1. MARKET TIMING: Need to track window boundaries
   - KXBTC15M windows open at :00, :15, :30, :45 of each hour
   - "seconds_remaining" = time until next :X5 mark
   - Use existing Kalshi market get_events() to find current active market

2. COIN DRIFT: Track price at window open
   - Store btc_price_at_window_open each time a new 15-min window starts
   - drift_pct = (current_price - open_price) / open_price
   - Reuse existing BinancePriceFeed (already streaming @bookTicker)

3. POSITION CHECK: Before entry, verify no open expiry_sniper position
   - db.has_open_position(strategy_name="expiry_sniper_v1", market_ticker=...)
   - Critical: one position per window, never stack

4. KILL SWITCH: Mandatory at every order path
   - kill_switch.check_order_allowed() for live
   - kill_switch.check_paper_order_allowed() for paper

5. PAYOUT CALCULATION:
   - At 90c YES: payout = kalshi_payout(yes_price=90, side="yes") = 100/90 = 1.111
   - At 90c NO: payout = kalshi_payout(yes_price=10, side="no") = 100/90 = 1.111
   - Same payout ratio regardless of direction

6. KELLY SIZING:
   - At 90c, Kelly fraction = (p - q/b) where p=win_prob, q=1-p, b=payout-1
   - If p=0.90, b=0.111: Kelly = (0.90 - 0.10/0.111) = 0.90 - 0.90 = 0.00
   - Kelly says DON'T BET at exactly breakeven (win_rate = 90%, payout = 10c on 90c)
   - At 91%+ win rate: Kelly becomes positive → Kelly-correct to size up
   - Implication: we must FIRST establish our actual win rate via paper trading
   - Use calibration_max_usd=0.01 (micro-live) during calibration phase

7. STRATEGY NAME: "expiry_sniper_v1"
   - DB, graduation status, kill switch all keyed on strategy name
   - Add to --graduation-status display
   - Add tests in tests/test_expiry_sniper.py

### Implementation Order

PAPER PHASE (build + validate):
  1. tests/test_expiry_sniper.py — write tests first (TDD)
  2. src/strategies/expiry_sniper.py — strategy class
  3. main.py — expiry_sniper_loop() paper-only
  4. Run for 30 paper bets — measure actual win rate
  5. If win rate >= 90%: Kelly will allow live sizing
  6. If win rate < 85%: investigate before going live

LIVE PHASE GATE (30 paper bets + Brier < 0.30 + win rate >= 88%):
  1. Pre-live audit checklist (CLAUDE.md Step 5)
  2. Set calibration_max_usd=0.01 for micro-live calibration
  3. After 30 live bets: evaluate win rate + Brier + Kelly calibration
  4. Stage 2 gate: same criteria as other strategies (30 live + Kelly dominant + Brier < 0.25)

## WHAT NOT TO DO

  - Do NOT add stop-loss before empirical data on win rate exists
    (stop-loss only helps if win rate is near the 83.3% breakeven, not at 90%+)
  - Do NOT raise triggerPoint above 90c without data
    (95c = even better EV but VERY few opportunities; 90c is the sweet spot)
  - Do NOT lower triggerPoint below 88c without data
    (88c payout = 100/88 = 1.136, but win rate needs to be > 88% to profit)
  - Do NOT disable min_drift_pct filter
    (90c without momentum = "market maker sitting at 90c" = different risk profile)
  - Do NOT stack with btc_drift or confuse with btc_drift
    (completely different market condition — btc_drift = 35-65c, expiry_sniper = 87-100c)
  - Do NOT use the original NightShark scripts or JavaScript HUD from the blog
    (security risk — runs in browser session with access to your Kalshi auth cookies)
  - Do NOT apply the 35-65c price guard to this strategy
    (that guard is for btc_drift only — expiry_sniper intentionally targets 90c+)

## COMPARISON WITH OUR EXISTING APPROACH

  Our btc_drift:                          Expiry sniper:
  - Price zone: 35-65c (neutral)          - Price zone: 87-100c (near-certain)
  - Signal: BTC price movement lag        - Signal: time + price threshold reached
  - Typical edge: 5-10%                   - Typical edge: 0-4.4% (narrow but reliable)
  - Kelly fraction: 10-25% of bankroll    - Kelly fraction: 0-5% (near-breakeven)
  - Signals/day: 8-15 (when in range)     - Signals/day: 2-8 (rarer, need high price)
  - Brier calibration: 0.246-0.249        - Unknown until paper phase

  Summary: btc_drift = better Kelly properties, expiry_sniper = higher absolute win rate
  Best combined use: run both simultaneously, they never conflict on price zone

## EXPANSION GATE STATUS

  Gate criteria (CLAUDE.md): btc_drift at 30+ live trades + Brier < 0.30 + 2-3 weeks P&L
  Status check:
  - btc_drift: 53/30 ✅, Brier 0.249 < 0.30 ✅
  - eth_drift: 75/30 ✅, Brier 0.246 < 0.30 ✅
  - Live P&L history: many weeks of data ✅
  - No active kill switch events: 0 consecutive at Session 53 end ✅

  VERDICT: Expansion gate IS met for building paper-only implementation.
  Paper phase can begin. Live phase requires separate 30-bet paper validation.

  NOTE: Paper build must not affect live bot operation.
  Implementation: new loop added to main.py, new strategy file, new tests.
  No changes to existing btc_drift/eth_drift/sol_drift/xrp_drift loops.

## PROMPT FOR NEW ACTIVE CHAT

Copy-paste this block when starting implementation work:

---
You are continuing work on polymarket-bot (Session 54+).

TASK: Implement expiry_sniper_v1 strategy in paper-only mode.
This is a new Kalshi 15-min binary sniping strategy that enters when
YES or NO price reaches 90c+ in the final 14 minutes of a window.

MANDATORY: Read SESSION_HANDOFF.md and .planning/EXPIRY_SNIPER_SPEC.md first.
The SPEC file has complete parameters, integration points, implementation order,
security analysis, and EV math.

CRITICAL CONSTRAINTS:
1. Live bot is running (PID in bot.pid) — do NOT restart unless directed
2. Paper-only first — set live_executor_enabled=False + calibration_max_usd=0.01
3. TDD — write tests/test_expiry_sniper.py before any implementation code
4. No changes to existing btc_drift/eth_drift/sol_drift/xrp_drift loops
5. Strategy class: ExpirySniperStrategy in src/strategies/expiry_sniper.py
6. Use existing auth, kill_switch, db, BinancePriceFeed infrastructure
7. Run full test suite (1003+ tests must pass) before any commit

START WITH: Write tests/test_expiry_sniper.py with at minimum:
  - TestExpirySniperSignal: entry conditions, time guard, price guard, drift filter
  - TestExpirySniperNoEntry: all cases where signal should NOT fire
  - TestExpirySniperPayout: Kelly fraction calculations at 90c+
Then implement the strategy to make tests pass.
---

## IMPLEMENTATION RISK ASSESSMENT

  LOW RISK:
  - New paper-only loop, completely isolated from live loops
  - Uses existing auth/API/DB infrastructure
  - No changes to risk management
  - Additive — only adds new code, doesn't modify existing code

  MEDIUM RISK:
  - Window timing logic (tracking 15-min windows) = new code type for this codebase
  - coin_drift tracking from window open = need to store per-window state

  MITIGATIONS:
  - Window boundary detection: use existing Kalshi market get_events() response
    (each market has created_time and close_time)
  - Per-window state: dictionary keyed on market_ticker, cleared at each new window
  - All state in-process only (no new DB tables needed until going live)

## RESEARCH STATUS

  ✅ V6 strategy fully documented (blog page extracted 2026-03-11)
  ✅ V7 strategy fully documented (blog page extracted 2026-03-11)
  ✅ NightShark read_areas() mechanics confirmed (OCR screen capture, area[1-4])
  ✅ toNumber() mechanics confirmed (strips $,%, returns float, blank=0)
  ✅ Security analysis complete (JavaScript HUD = browser access risk)
  ✅ EV math complete (breakeven analysis, stop-loss impact)
  ✅ Commenter enhancements incorporated (Kelly, min_drift, stop-loss caution)
  ✅ Integration plan with existing bot complete
  ✅ Implementation order established (paper first, 30 bets, then live gate)
  ✅ Expansion gate verified as MET for building paper implementation
  ✅ Area array mapping confirmed: [1]=YES, [2]=NO, [3]=time, [4]=position
