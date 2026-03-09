---
created: 2026-02-28T07:54:11.180Z
title: Add slippage model to paper executor
area: trading
files:
  - src/execution/paper.py
---

## Problem

`PaperExecutor` fills orders at the exact limit price with no slippage. In real Kalshi markets, the fill price may be worse than limit due to bid/ask spread movement, especially in thin markets. This makes paper P&L systematically optimistic — a strategy that looks profitable in paper may underperform in live.

Current behavior (src/execution/paper.py): fill_price = order.limit_price, pnl calculated from that exact price.

## Solution

Add a configurable slippage model to PaperExecutor:
- Default: fill at limit price ± 1 tick (0.01) in adverse direction (conservative)
- Config: `paper_slippage_ticks: 1` in config.yaml under [risk] or [paper]
- Slippage applies to both YES and NO fills (adverse: YES fills higher, NO fills higher)
- Must not affect live executor (LiveExecutor fills at actual exchange prices)
- Update graduation P&L tracking to use slippage-adjusted fills
