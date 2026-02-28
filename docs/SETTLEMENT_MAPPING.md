# Settlement Result Field Mapping

## Kalshi API -> settlement_loop -> DB

Field: `market.result` from GET /trade-api/v2/markets/{ticker}
Values: "yes" | "no" (lowercase, normalized in kalshi.py `_parse_market()`)

Normalization: `result = (m.get("result") or "").lower() or None`
This ensures settlement is robust to any Kalshi API casing changes.

WIN condition: `market.result == trade["side"]`

Examples:
- Bet YES, market settles "yes" -> WIN
- Bet NO, market settles "no" -> WIN (NO-side bet)
- Bet YES, market settles "no" -> LOSS
- Bet NO, market settles "yes" -> LOSS

## Verified in tests

See tests/test_paper_executor.py :: TestSettlementResultMapping

## PnL formula (src/execution/paper.py)

WIN:  pnl = (100 - fill_price_cents) * count - fees
LOSS: pnl = -fill_price_cents * count
Fees: 0.07 * P * (1-P) per contract, wins only (Kalshi standard fee)

## Settlement loop flow (main.py)

```
settlement_loop()
  -> db.get_open_trades()           # trades with result IS NULL
  -> kalshi.get_market(ticker)      # fetches current market state
  -> if market.status == "finalized" and market.result:
       paper_exec.settle(
           trade_id=trade["id"],
           result=market.result,    # already lowercase from kalshi.py
           fill_price_cents=trade["price_cents"],
           side=trade["side"],
           count=trade["count"],
       )
       kill_switch.record_win() or record_loss()
```

## Gotcha: NO-side bets

`db.win_rate()` compares `result == side` (NOT `result == "yes"`).
- Betting NO and getting result=="no" is a WIN (result == side == "no")
- See test_db.py :: TestWinRate :: test_win_rate_correct_for_no_side_wins
