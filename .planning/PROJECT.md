# PROJECT.md — polymarket-bot

## What This Is

An autonomous prediction market trading bot that finds statistical edges in Kalshi markets using real-time crypto prices, weather forecasts, and macro signals. Runs 8 parallel strategy loops in paper mode, validates each against formal graduation criteria, then selectively enables live trading for proven strategies.

## Core Value

Turn data feed edges into consistent small-stakes profits on Kalshi with zero manual intervention, strict safety limits, and a traceable paper→live graduation path.

## Vision

An autonomous prediction market trading bot for Kalshi that identifies statistical edges across crypto (BTC/ETH), weather, and macro-economic markets. Starts in paper mode to validate strategies, then graduates proven strategies to live trading with strict risk controls.

## Problem

Kalshi prediction markets often misprice short-term outcomes relative to real-time data feeds (BTC price momentum, weather forecasts, FOMC signals). Retail access to these edges exists but requires automated, low-latency execution with disciplined risk management.

## Solution

8 independent strategy loops running in parallel, each comparing a live data signal (Binance prices, weather API, FRED yield curve) against Kalshi market prices, sizing bets with Kelly criterion, and enforcing hard safety limits at every order gate.

## Current Architecture

- **Runtime:** Python 3.13, asyncio, SQLite
- **Exchange:** Kalshi (demo + live), RSA-PSS auth
- **Data:** Binance.US WebSocket (BTC/ETH), Open-Meteo + NWS NDFD (weather), FRED CSV (macro)
- **Strategies:** btc_lag, eth_lag, btc_drift, eth_drift, btc_imbalance, eth_imbalance, weather_forecast, fomc_rate
- **Safety:** Kill switch, PID lock, daily bet cap, position dedup, bankroll floor, live CONFIRM gate

## Requirements

### Must Have (v1 — current)
- REQ-001: 8 concurrent strategy loops with staggered startup
- REQ-002: Paper mode with full P&L simulation
- REQ-003: Hard safety limits: $5 max bet, $20 bankroll floor, 30% total stop-loss
- REQ-004: Kill switch with BLOCKERS.md audit trail
- REQ-005: Live graduation criteria before enabling any live trading
- REQ-006: 324+ tests passing before any commit

### Should Have (v1.1)
- REQ-007: 7+ days paper data per strategy before graduation evaluation
- REQ-008: Brier score tracking per strategy (target < 0.25)
- REQ-009: Live trading for best-performing graduated strategy

### Nice to Have (v2)
- REQ-010: Entertainment/sports market strategies (4–7pp spread, less HFT competition)
- REQ-011: Market making via Avellaneda-Stoikov model
- REQ-012: Cloud deployment (Railway/Fly.io)
- REQ-013: KXUNRATE (unemployment rate PMF extraction)

## Success Criteria

- Paper mode runs 7+ days without crashes or kill-switch trips
- At least 1 strategy achieves Brier < 0.25 with 30+ settled trades
- Live mode executes first real bet under $5 without errors
- Bankroll does not drop below $20 floor in live testing

## Out of Scope

- Options, futures, or non-Kalshi exchanges
- ML/neural net models (statistical signal-based only for now)
- Multi-user or SaaS deployment
