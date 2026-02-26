# SESSION HANDOFF — polymarket-bot
# Feed this file to any new Claude session to resume.
# Last updated: 2026-02-25 (Phase 3 complete — all systems built)
═══════════════════════════════════════════════════

## Current state: PHASE 3 COMPLETE

All three phases of the initial build are done.
The bot is in paper/demo mode. Kalshi auth has NOT been verified with real keys yet.

### Phase completion
- Phase 1: Foundation — auth, kill switch, risk system — 59/59 tests ✅
- Phase 2: Core — Kalshi client, Binance feed, BTC lag strategy, execution, main loop ✅
- Phase 3: Ops layer — Streamlit dashboard, settlement polling loop ✅

### Component status

| Component        | Status   | Notes                                      |
|-----------------|----------|--------------------------------------------|
| Kill switch      | TESTED   | 59/59 tests pass, committed                |
| Sizing (Kelly)   | TESTED   | Stage-based caps verified                  |
| Kalshi client    | BUILT    | Not yet verified against live demo API     |
| BTC feed         | BUILT    | Binance WebSocket, auto-reconnect          |
| BTC lag strategy | BUILT    | 4-condition gate: move, lag, time, edge    |
| Paper executor   | BUILT    | Orderbook-implied fill, DB writes          |
| Live executor    | BUILT    | 3-layer guard: env + CLI + CONFIRM prompt  |
| Settlement loop  | BUILT    | Background async task, polls every 60s     |
| Dashboard        | BUILT    | Streamlit @ localhost:8501, read-only      |
| DB               | BUILT    | SQLite, all tables auto-created on init    |

## Next action

**Matthew needs to:**
1. Set up `.env` file with `KALSHI_API_KEY_ID` and path to `kalshi_private_key.pem`
2. Run: `python main.py --verify`
3. If verify passes: run paper mode for 7+ days — `python main.py`
4. Monitor: `streamlit run src/dashboard.py` → http://127.0.0.1:8501
5. After 7+ days positive paper P&L → discuss going live

**Open blocker: KALSHI AUTH NOT YET VERIFIED**
See BLOCKERS.md for details.

## To resume a Claude session

Feed Claude this file AND POLYBOT_INIT.md.
Say: "We are resuming the polymarket-bot project. Read SESSION_HANDOFF.md and POLYBOT_INIT.md first, then continue."

## Key commands

```bash
source venv/bin/activate && python main.py          # Paper mode
python main.py --verify                              # Test connections
python main.py --report                              # Print P&L summary
python main.py --reset-killswitch                    # Reset after hard stop
streamlit run src/dashboard.py                       # Open dashboard
python -m pytest tests/ -v                          # Run all tests
```

## File manifest

```
src/auth/kalshi_auth.py        — RSA-PSS signing
src/platforms/kalshi.py        — Kalshi REST client
src/data/binance.py            — BTC WebSocket feed
src/strategies/base.py         — Signal + BaseStrategy
src/strategies/btc_lag.py      — Primary strategy
src/risk/kill_switch.py        — All hard stops
src/risk/sizing.py             — Kelly + stage caps
src/db.py                      — SQLite persistence
src/execution/paper.py         — Paper executor
src/execution/live.py          — Live executor (3 guards)
src/dashboard.py               — Streamlit UI
main.py                        — CLI + async loop + settlement
setup/verify.py                — 7-check pre-flight
config.yaml                    — All config
.env.example                   — Template (user fills .env)
requirements.txt               — All dependencies
tests/test_kill_switch.py      — Kill switch tests
tests/test_security.py         — Security/path tests
CHECKPOINT_1.md                — Phase 1 gate (committed)
CHECKPOINT_2.md                — Phase 2 gate (committed)
CHECKPOINT_3.md                — Phase 3 gate
BLOCKERS.md                    — Open items for Matthew
SESSION_HANDOFF.md             — This file
POLYBOT_INIT.md                — Build instructions + progress
```

## Known limitations

1. AUTH NOT VERIFIED — Kalshi demo auth needs testing with Matthew's real keys
2. BTC series ticker: KXBTC15M — verify Kalshi ticker format when running
3. Settlement statuses "finalized"/"settled" — confirm against actual Kalshi API response
4. No WebSocket feed for real-time Kalshi prices — REST polling only (acceptable for 15-min markets)
