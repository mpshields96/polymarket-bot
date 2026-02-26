# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-26 (Session 4 — API fixes, bot running)
═══════════════════════════════════════════════════

## Current State

Bot starts and runs. Auth live. BTC feed live. Kalshi API connected.
Balance reads $75.00 from API correctly.

ONE open issue: trading loop runs but produces no INFO-level output.
We have not confirmed a signal has been evaluated and logged.
(Likely benign: BTC feed warm-up + market had <5 min remaining at test time)

verify.py: **18/18 ✅**

## Next Action (FIRST THING)

Run the bot and confirm the trading loop is evaluating markets:

    python main.py

Watch for ANY of these every 30s:
  - "[btc_lag] BTC move ... — skip"        ← strategy evaluated, skipped
  - "[btc_lag] Signal: BUY YES/NO ..."     ← signal fired
  - WARNING: "Failed to fetch markets"     ← API error

If NOTHING appears after 60 seconds, add DEBUG logging to diagnose:
  import logging; logging.getLogger("src").setLevel(logging.DEBUG)

## What was fixed this session

1. Kalshi API URL: trading-api.kalshi.com → api.elections.kalshi.com
2. Balance field: available_balance → balance (cents)
3. Market price fields: yes_price/no_price → yes_bid/no_bid
4. Status filter: revert 'active' mistake → keep 'open' (correct)
5. data/ directory created (DB lives there: data/polybot.db)
6. Binance.com geo-block → switched to binance.us everywhere
7. config.yaml: storage section added, demo/live URLs updated

## Component Status

| Component            | Status      | Notes                                          |
|----------------------|-------------|------------------------------------------------|
| Auth (RSA-PSS)       | ✅ Working  | $75 balance confirmed                          |
| Kalshi REST client   | ✅ Working  | api.elections.kalshi.com, field names fixed    |
| Binance.US feed      | ✅ Working  | wss://stream.binance.us:9443                   |
| BTCLagStrategy       | ✅ Tested   | 23 unit tests pass, needs live confirmation    |
| Kill switch          | ✅ Working  | Clear                                          |
| Database             | ✅ Working  | data/polybot.db                                |
| Paper executor       | ✅ Ready    | Not yet triggered                              |
| Dashboard            | ✅ Ready    | streamlit run src/dashboard.py → localhost:8501|
| Trading loop         | ⚠️ Unknown  | Runs, no confirmed signal evaluation logged    |
| Settlement loop      | ✅ Ready    | Runs, no open trades yet                       |

## Key Commands

    python main.py                    → Paper mode (default)
    python main.py --verify           → Pre-flight check
    streamlit run src/dashboard.py   → Dashboard at localhost:8501
    source venv/bin/activate && pytest tests/ -v  → 107 tests
    echo "RESET" | python main.py --reset-killswitch

## On other prediction markets (Matthew asked)

BTC is the right primary — highest volume, clearest external signal.
Once BTC paper trading shows positive edge over 7+ days:
  - Add ETH (same structure, ticker KXETH15M)
  - Fed rate / CPI / NFP markets available but need different signals

Do NOT add more markets until BTC paper trading is confirmed working.
