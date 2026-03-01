# SESSION HANDOFF — polymarket-bot
# Feed this file + POLYBOT_INIT.md to any new Claude session to resume.
# Last updated: 2026-03-01 (Session 23 — 515 tests, CSV export, hourly expansion is next task)
═══════════════════════════════════════════════════

## EXACT CURRENT STATE — READ THIS FIRST

The bot is **running right now** in background.
PID: **7396** (stored in `bot.pid`)
Log: `tail -f /tmp/polybot.log` (stable symlink → /tmp/polybot_session21.log)

**3 strategies LIVE** (real money): btc_lag_v1, eth_lag_v1, btc_drift_v1
**6 strategies paper**: eth_drift, btc_imbalance, eth_imbalance, weather, fomc, unemployment_rate
Test count: **515/515 ✅**
Latest commit: **ca4e1cf** — auto-export trades to reports/trades.csv on settlement

## DO NOT restart the bot unless it's stopped
Check first:
```
cat bot.pid && kill -0 $(cat bot.pid) 2>/dev/null && echo "running" || echo "stopped"
```

If stopped, restart:
```
bash scripts/restart_bot.sh
```

## P&L Status (as of 2026-03-01 19:10 UTC)
- **Bankroll:** ~$115
- **Live P&L today:** +$2.29 (4 settled live: 2W 2L)
- **All-time live:** +$15.15 (9 settled: 5W 4L)
- **All-time paper:** +$27.02
- **All-time win rate:** 67%
- **⚠️ WATCH:** 2 consecutive live losses (id=81, id=83). Kill switch trips at 5. Trade 85 is open (YES@21¢).

### Live bets breakdown (all-time):
| id | Strategy | Side | Cost | Result | P&L |
|----|----------|------|------|--------|-----|
| 64 | btc_lag | NO @48¢ | $3.36 | WON | +$3.50 |
| 67 | btc_drift | YES @63¢ | $4.41 | LOST | -$4.41 |
| 70 | btc_drift | NO @33¢ | $4.95 | WON | +$9.75 |
| 74 | btc_drift | NO @34¢ | $4.76 | WON | +$8.96 |
| 75 | btc_drift | NO @26¢ | $4.94 | LOST | -$4.94 |
| 78 | btc_drift | NO @35¢ | $4.90 | WON | +$8.82 |
| 80 | btc_drift | NO @57¢ | $4.56 | WON | +$3.28 |
| 81 | btc_drift | YES @37¢ | $4.81 | LOST | -$4.81 |
| 83 | btc_drift | NO @50¢ | $5.00 | LOST | -$5.00 |
| 85 | btc_drift | YES @21¢ | $4.83 | OPEN | — |

## Graduation Progress (2026-03-01 19:10 UTC)
| Strategy              | Trades | Status                        |
|-----------------------|--------|-------------------------------|
| btc_lag_v1            | 43/30  | READY FOR LIVE (already live) |
| btc_drift_v1          | 9/30   | 21 more (already live)        |
| eth_drift_v1          | 14/30  | 16 more needed (paper)        |
| eth_orderbook_v1      | 7/30   | 23 more needed (paper)        |
| orderbook_imbalance   | 2/30   | 28 more needed (paper)        |
| eth_lag_v1            | 0/30   | calm market (expected)        |
| weather_forecast_v1   | 0/30   | weekday HIGHNY only           |
| fomc_rate_v1          | 0/5    | active March 5-19             |

## What changed in Session 23 (2026-03-01)

### Tests: 507 → 515 (+8)
- tests/test_db.py: TestExportTradesCsv (8 tests for CSV export)

### New: Trade CSV export (ca4e1cf)
- `db.export_trades_csv(path)` — dumps all trades to CSV with human timestamps, pnl_usd, won flag
- Auto-exports to `reports/trades.csv` after every settlement poll
- `--export-trades` CLI flag (bypasses bot lock, safe while live)
- `reports/trades.csv` committed to GitHub — new chats can read it directly without running Python
- 85 trades currently in CSV (9 live, 76 paper)

### Research: Hourly BTC/ETH expansion (NOT YET BUILT)
- Kalshi has hourly + weekly BTC/ETH markets beyond 15-min
- Same lag/drift logic applies with recalibrated parameters
- SOL 15-min markets may also exist
- Cross-platform arbitrage (Polymarket ↔ Kalshi) is separate, needs Polymarket access
- **This is the #1 next task** — see KEY PRIORITIES below

## KEY PRIORITIES FOR NEXT SESSION

**#1 — BUILD: Hourly BTC/ETH strategy (paper mode)**
Matthew's directive: expand crypto bet types before any other market category.
Steps:
1. Query Kalshi API to confirm hourly BTC ticker (likely KXBTC1H or similar)
2. Calibrate parameters: hourly window needs higher min_btc_move_pct + wider edge threshold
3. Build `btc_lag_hourly_v1` following same pattern as btc_lag.py (TDD — write tests first)
4. Build `eth_lag_hourly_v1` (ETH factory, same pattern)
5. Wire both as paper-only loops in main.py (10s stagger after existing loops)
6. Monitor paper results for 30 trades before any live consideration

**#2 — WATCH: consecutive loss streak**
- 2 consecutive live losses right now (id=81, id=83). Trade 85 open (YES@21¢).
- Kill switch trips at 5. If streak hits 3-4, review btc_drift signal quality.
- No action needed until streak reaches 4 — then pause and audit.

**#3 — NO Stage 2 promotion yet**
- Bankroll ~$115, but Kelly calibration requires 30+ live bets with limiting_factor=="kelly"
- Do NOT raise bet size to $10

**#4 — eth_drift approaching graduation (14/30)**
- Run Step 5 pre-live audit when it hits 30 trades

**#5 — FOMC active March 5**
- KXFEDDECISION markets open ~March 5 for March 19 meeting

## Odds API — Standing Directives (never needs repeating)
- OddsAPI: 20,000 credits/month, renewed March 1
- **HARD CAP: 1,000 credits max for polymarket-bot**
- Sports props/moneyline/totals = ENTIRELY SEPARATE project — NOT for Kalshi bot
- Before ANY credit use: implement quota guard first
- See .planning/todos.md for full roadmap

## Loop stagger (what's running right now)
```
   0s → [trading]        btc_lag_v1                 — LIVE
   7s → [eth_trading]    eth_lag_v1                 — LIVE
  15s → [drift]          btc_drift_v1               — LIVE
  22s → [eth_drift]      eth_drift_v1               — paper
  29s → [btc_imbalance]  orderbook_imbalance_v1     — paper
  36s → [eth_imbalance]  eth_orderbook_imbalance_v1 — paper
  43s → [weather]        weather_forecast_v1        — paper
  51s → [fomc]           fomc_rate_v1               — paper, active March 5-19
  58s → [unemployment]   unemployment_rate_v1       — paper, active Feb 28 – Mar 7
```

## Key Commands
```
tail -f /tmp/polybot.log                                     → Watch live bot (always open)
source venv/bin/activate && python main.py --report          → Today's P&L
source venv/bin/activate && python main.py --graduation-status → Graduation progress
source venv/bin/activate && python main.py --status          → Live status snapshot
source venv/bin/activate && python main.py --export-trades   → Refresh reports/trades.csv
source venv/bin/activate && python -m pytest tests/ -q       → 515 tests
bash scripts/restart_bot.sh                                  → Safe restart
cat reports/trades.csv                                       → All trades (committed to git)
```

## AUTONOMOUS OPERATION — STANDING DIRECTIVE (never needs repeating)
- Operate fully autonomously at all times. Never ask for confirmation.
- Security: never expose .env/keys/pem; never modify system files outside project dir.
- Never break the bot: confirm running/stopped before restart; verify single instance after.
- Expansion order: (1) perfect live/paper, (2) hourly crypto next, (3) graduate paper→live with Step 5 audit.
- Framework overhead: ≤10-15% of 5-hour token limit total. Use gsd:quick only when multi-step tracking needed. No sub-agents unless 5-condition threshold met.

## Context handoff: new chat reads POLYBOT_INIT.md first, then this file, then proceeds.
