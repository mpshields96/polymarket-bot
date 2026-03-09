---
created: 2026-03-10T13:44:00.000Z
title: Add execution-time price guard to live executor
area: execution
files:
  - src/execution/live.py
  - src/strategies/btc_drift.py
---

## Problem

`live.py` places orders at the **current market price** fetched at execution time, not
the price at signal generation time. This causes two failure modes:

1. **Large slippage**: Signal generated at YES=59¢ (passes 35-65¢ guard), but by the
   time the Kalshi API call arrives (asyncio overhead + BTC repricing), market moved to
   YES=84¢. Order fills at 84¢ — 25¢ adverse slippage, completely outside the guard range.

2. **Price guard bypass**: btc_drift's 35-65¢ guard is checked at signal time only.
   By the time the order is placed, the market can be at 84¢ (way outside guard).

**Observed in session 37 (2026-03-10 08:39 CDT):**
```
08:39:16 Signal: BUY YES @ 59¢ | edge_yes=11.5%  ← guard passes (59¢ in range)
08:39:16 Placing order: BUY YES 1 contracts @ 84¢  ← execution price = 84¢ (outside range!)
```

The same pattern explains why some bets appear at 66¢, 68¢, 69¢, 73¢ — signal within
range at generation time, but market moved before API call.

## Root cause

In `live.py`, the order price is fetched from the current Kalshi orderbook at execution
time, not taken from `signal.price_cents`. The asyncio loop introduces 0.1-1s latency
during which HFTs can reprice significantly.

## Solution

Add a max-slippage check in `live.py` before placing the order:

```python
# After fetching current market price, before placing order:
EXECUTION_MAX_PRICE = 65  # cents
EXECUTION_MIN_PRICE = 35  # cents
MAX_SLIPPAGE_CENTS = 10   # reject if execution price > 10¢ from signal price

execution_yes_price = <fetched current price>
signal_yes_price = signal.price_cents if signal.side == "yes" else (100 - signal.price_cents)

if not (EXECUTION_MIN_PRICE <= execution_yes_price <= EXECUTION_MAX_PRICE):
    logger.warning("[live] Execution price %d¢ outside guard — rejecting (signal was %d¢)",
                   execution_yes_price, signal_yes_price)
    return None

slippage = abs(execution_yes_price - signal_yes_price)
if slippage > MAX_SLIPPAGE_CENTS:
    logger.warning("[live] Slippage %d¢ exceeds max %d¢ — rejecting",
                   slippage, MAX_SLIPPAGE_CENTS)
    return None
```

## Test to write

```python
def test_live_executor_rejects_execution_price_outside_guard():
    # Signal at 55¢, market moves to 80¢ by execution time
    # live.py should reject and return None

def test_live_executor_rejects_excessive_slippage():
    # Signal at 55¢, execution price at 67¢ (12¢ slippage > 10¢ max)
    # live.py should reject
```

## Impact

**High priority** — currently placing real bets at 84¢ when strategy calibrated on 35-65¢
signals. At 84¢, expected value is very different from the calibrated model. This is
corrupting the live Brier score.
