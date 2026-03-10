# CODEBASE AUDIT — KEEP / STRIP / REBUILD
## Against: KALSHI_BOT_COMPLETE_REFERENCE.pdf
## Date: 2026-03-10 | Session 44 Overhaul | Auditor: Claude Sonnet 4.6
## Bot state during audit: STOPPED | 923/923 tests | data/polybot.db | 111 settled live trades

---

## PROMPT 1 AUDIT — PASS/FAIL

| Check | Result | Detail |
|---|---|---|
| Kalshi API version | ✅ PASS | Using v2: `trading-api.kalshi.com/trade-api/v2` — current version |
| Python version | ✅ PASS | Python 3.13.5 (requires 3.11+) |
| Hardcoded credentials | ✅ PASS | All secrets via `os.getenv()` from `.env` — none hardcoded in source |
| Deprecated endpoints | ✅ PASS | No v1 Kalshi endpoints found; Polymarket endpoints confirmed working 2026-03 |
| `kalshi-python` SDK | ℹ️ NOTE | Not installed — using direct REST (by design, more control) |

**Note on VA WiFi blocks:** `docs.kalshi.com` WebFetch returned socket close error. `edgedesk.net` content
not available in HTML form. These are documentation sources only — did not block audit execution.
Both URLs logged for retry when on better WiFi. Kalshi WebSocket documentation confirmed via WebSearch
fallback (ticker channel exists at `wss://trading-api/v1/ws`, public, no auth required).

---

## PROMPT 2 AUDIT — KEEP / STRIP / REBUILD

```json
{
  "KEEP": {
    "verdict": "These files align with reference architecture and should not be changed.",
    "files": [
      {
        "file": "src/auth/kalshi_auth.py",
        "reason": "RSA-PSS signing matches reference exactly. KALSHI-ACCESS-KEY header correct. v2 path signing correct. All keys loaded from .env — no hardcoding.",
        "reference_alignment": "Phase 1 kalshi_client.py auth requirement — met."
      },
      {
        "file": "src/platforms/kalshi.py",
        "reason": "REST client on trade-api/v2. Rate limiting with exponential backoff (2s, 4s, 8s). Custom KalshiAPIError exceptions. get_markets(), place_order() pattern correct. limit orders only enforced.",
        "reference_alignment": "Phase 1 kalshi_client.py — fully implemented."
      },
      {
        "file": "src/risk/kill_switch.py",
        "reason": "Kill switch structure is correct: daily loss, consecutive losses, hourly rate, hard stop on bankroll floor. Hard stop cancels all open orders before halting (reference requirement met). SQLite kill_switch_events log exists.",
        "flag": "DAILY LOSS CAP IS DISABLED (lines 187-189 commented out). Reference says $25/day kill is mandatory. This is a deliberate Matthew decision (Session 42) but creates risk. Logged separately.",
        "reference_alignment": "Phase 4 risk_manager.py — kill switch architecture correct, daily cap disabled."
      },
      {
        "file": "src/execution/live.py",
        "reason": "Limit orders only. DRY_RUN equivalent via LIVE_TRADING env var + --live CLI flag. calibration_max_usd cap for micro-live. Execution-time price guard (35-65¢). Canceled order detection before DB write.",
        "reference_alignment": "Phase 6 executor.py — fully implemented with extra safeguards."
      },
      {
        "file": "src/execution/paper.py",
        "reason": "Paper trading simulator. DRY_RUN equivalent. Immediate simulated fill at entry price — matches reference Phase 8 paper gate behavior.",
        "reference_alignment": "Phase 8 paper trading gate — implemented."
      },
      {
        "file": "src/risk/sizing.py",
        "reason": "Kelly Criterion (0.25x fractional) with stage-based caps. Stage 1: $5 max. Stage 2: $10 max. Stage 3: $15 max. SizeResult dataclass with limiting_factor field for calibration tracking.",
        "reference_alignment": "Reference Kelly Criterion requirement — met. Reference $5 Stage 1 cap — met."
      },
      {
        "file": "src/strategies/btc_drift.py",
        "reason": "Core edge detection: sigmoid probability model vs Kalshi market price. Edge = |model_prob - market_price|. min_edge_pct filter. late_penalty gate (fixed Session 44). Price guard 35-65¢. direction_filter for YES bias removal.",
        "reference_alignment": "Phase 2 edge_detector.py intent — correct approach, calibration improving."
      },
      {
        "file": "src/strategies/fomc_rate.py",
        "reason": "Reference doc Section 6.4 explicitly calls out Fed Funds futures + FOMC as 'most credible systematic edge on Kalshi for non-HFT operators.' We have this built and paper-active.",
        "reference_alignment": "Section 6.4 economic data edge — correctly implemented."
      },
      {
        "file": "src/strategies/unemployment_rate.py",
        "reason": "Same class as FOMC — BLS releases, Cleveland Fed data, information edge. Reference validates this category.",
        "reference_alignment": "Section 6.4 employment edge — correctly implemented."
      },
      {
        "file": "src/data/fred.py",
        "reason": "FRED API for economic data. Feeds FOMC + unemployment strategies. Free API, accurate, machine-readable. Exactly the pattern reference recommends.",
        "reference_alignment": "Section 6.4 data source — correctly implemented."
      },
      {
        "file": "src/strategies/weather_forecast.py",
        "reason": "Reference Section 6.3 explicitly describes weather markets: 'NWS provides machine-readable probability distributions that are more accurate than Kalshi prices on thinly traded weather markets.' We have this built.",
        "reference_alignment": "Section 6.3 weather edge — correctly implemented."
      },
      {
        "file": "src/data/weather.py",
        "reason": "NWS + Open-Meteo feeds. Free, machine-readable, correct data sources per reference.",
        "reference_alignment": "Section 6.3 NWS data source — correctly implemented."
      },
      {
        "file": "src/data/binance.py",
        "reason": "WebSocket-based BTC price feed (~40 updates/min). Auto-reconnect. Stale detection at 35s. Correct architecture for the price feed component.",
        "flag": "Single feed only (Binance.US). Reference requires dual feed (Binance + Coinbase median). See REBUILD.",
        "reference_alignment": "Phase 1 price_feed.py — partially implemented."
      },
      {
        "file": "src/db.py",
        "reason": "SQLite persistence layer. CREATE TABLE IF NOT EXISTS pattern. _migrate() for incremental schema changes. Synchronous for speed. Core structure is correct.",
        "flag": "Missing 4 tax fields from reference Section 4.4. See REBUILD.",
        "reference_alignment": "Phase 3 logger.py — partially implemented."
      },
      {
        "file": "src/dashboard.py",
        "reason": "Streamlit dashboard exists. Reads from SQLite. Shows P&L, trades, kill switch status. Satisfies reference Phase 7 requirement.",
        "flag": "Dashboard uses hardcoded DAILY_LOSS_LIMIT_USD=20.0 and CONSECUTIVE_LOSS_LIMIT=4 (not from config). These are stale vs current values (daily cap disabled, consecutive=8).",
        "reference_alignment": "Phase 7 dashboard.py — partially implemented."
      },
      {
        "file": "src/auth/polymarket_auth.py",
        "reason": "Ed25519 auth for Polymarket.US. Infrastructure is correct and should be kept — regulatory gate for Polymarket.COM may open in 2026.",
        "flag": "Currently blocked by platform mismatch. Keep in codebase but not in active execution path.",
        "reference_alignment": "Platform-agnostic code goal — correct (reference Section 3.2)."
      },
      {
        "file": "src/platforms/polymarket.py",
        "reason": "Polymarket.US REST client. Confirmed working endpoints. Order placement built. Keep for when regulatory gate opens.",
        "flag": "Same as auth — blocked, keep infrastructure.",
        "reference_alignment": "Platform-agnostic code goal — correct (reference Section 3.2)."
      }
    ]
  },

  "STRIP": {
    "verdict": "These components have no evidence of edge, consume engineering/API/cost resources, and contradict either the reference architecture or our own live data. Recommend disabling from execution path. Do NOT delete code until Matthew approves — just exclude from main.py task scheduling.",
    "components": [
      {
        "component": "copy_trader_v1.py + whale_watcher.py + predicting_top.py (copy trading stack)",
        "reason": "BLOCKED permanently by platform mismatch (confirmed Session 34 + re-confirmed Session 44). predicting.top whales trade .COM (politics/crypto). Our account is .US (sports only). No API to close this gap. Reference doc Section 9 on copy trading: '87.3% of users lost money. Top whales use multi-wallet rotation to evade copiers within weeks.' 0 live trades from this stack.",
        "live_evidence": "0 matched .US copy trades after 10+ sessions of operation.",
        "action": "Remove from asyncio.gather() in main.py. Keep files for future regulatory gate. Add BLOCKED comment at top of each file.",
        "api_cost_saved": "~30 Polymarket API calls/poll cycle eliminated."
      },
      {
        "component": "sports_futures_v1.py + odds_api.py (sports bookmaker arb)",
        "reason": "Reference Section 5.2: 'A practitioner built a Kalshi sports bot, won over 66% of trades, and STILL LOST MONEY because fees consumed the edge.' Our own data: 0 profitable live sports bets. SDATA API costs 500 credits/month for zero revenue. Reference classifies sports as 'cautionary category' with HFT-level competition.",
        "live_evidence": "0 live sports trades placed. Sports strategy ran paper-only for 10+ sessions with unclear signal quality.",
        "action": "Disable sports_futures_v1 loop from main.py. SDATA quota has been burning for sports data with zero return. Remove odds_api calls from main execution path.",
        "cost_saved": "500 SDATA credits/month = reduced API spend."
      },
      {
        "component": "eth_orderbook_imbalance (live trading only — keep strategy code)",
        "reason": "Brier score 0.360 (above 0.30 graduation threshold AND above reference's 0.20 live-trading gate). -$14.68 all-time live P&L. Getting WORSE over time (was 0.300 at bet 10, now 0.360 at bet 12). signal_scaling=0.5 fix applied Session 44 but has not had time to prove itself.",
        "live_evidence": "12 live bets, 40% win rate, Brier 0.360, -$14.68.",
        "action": "Disable live trading for eth_orderbook_imbalance (set calibration_max_usd=0.01 back to force micro-live, or disable completely). Keep running paper to continue collecting data. Decision point: if Brier doesn't improve to <0.30 by bet 22, disable.",
        "reference_alignment": "Reference Brier gate: must be below 0.20 for live. Ours is 0.360. Not live-ready by reference standard."
      },
      {
        "component": "sports_game.py (game-by-game sports skeleton)",
        "reason": "Skeleton strategy never activated in production. Zero live bets. Zero paper bets. No edge validation. Sports category is already marked as cautionary. Dead code consuming test surface.",
        "action": "Remove from main.py. Can keep file with DISABLED comment.",
        "live_evidence": "0 bets, 0 sessions active."
      },
      {
        "component": "crypto_daily.py (KXBTCD/KXETHD/KXSOLD loops)",
        "reason": "Daily crypto markets have very low volume. Loops run but produce 0 live bets per session. Debug-level logging means evaluation is invisible in production log. These loops exist but produce no output.",
        "action": "NOT stripping — keep running, they're cheap (5-min poll) and may accumulate data over time. Just note: all activity is at DEBUG level, appearing silent.",
        "flag": "This is NOT a strip — just documentation that it appears silent but is running."
      }
    ]
  },

  "REBUILD": {
    "verdict": "These have the right intent but wrong/incomplete implementation per reference. Implement in priority order.",
    "items": [
      {
        "priority": 1,
        "component": "Kalshi fee calculator — explicit pre-trade fee check",
        "current_state": "Fee is tracked implicitly via settlement pnl_cents (net). No pre-trade fee check exists. Signals can pass the edge threshold without verifying they survive Kalshi taker fees.",
        "reference_requirement": "Phase 2: 'Return a trade signal only if edge > 0.04 (4 cents) after subtracting estimated fee.' Fee formula: ceil(0.07 * contracts * price * (1-price) * 100) in cents.",
        "rebuild_plan": "New file: src/risk/fee_calculator.py. Function: kalshi_taker_fee_cents(contracts, price_cents) -> int. Integrate into signal generation path: verify edge_pct survives fee_pct before returning signal.",
        "estimated_impact": "LOW-MEDIUM — at our 5% min_edge_pct and 35-65¢ price range, fees are ~1.5-2.5 cents/contract. With 7-15 contracts at $5 cap, total fee = 10-37 cents. May filter a few borderline signals.",
        "test_requirement": "test_fee_formula_matches_kalshi_official(), test_no_signal_when_fee_exceeds_edge()"
      },
      {
        "priority": 2,
        "component": "POLL_INTERVAL_SEC — reduce from 30s to 10s",
        "current_state": "POLL_INTERVAL_SEC=30 means strategies check markets every 30 seconds. Average latency from BTC move to signal generation: 15 seconds. Maximum: 30 seconds.",
        "reference_requirement": "Phase 1: 'WebSocket feed (not REST polling)' — reference wants event-driven. Our near-term achievable: reduce poll interval as immediate improvement.",
        "rebuild_plan": "Change POLL_INTERVAL_SEC = 30 to POLL_INTERVAL_SEC = 10 in main.py. Phase 2 (next session): implement asyncio.Event-based trigger from BinanceFeed. At 10s: avg latency 5s vs current 15s. At event-driven: avg latency 1-3s.",
        "api_impact": "6 loops × 1 get_markets / 10s = 0.6 req/s (within 20 req/s Basic tier limit).",
        "test_requirement": "No new tests needed — behavior unchanged, just faster."
      },
      {
        "priority": 3,
        "component": "SQLite schema — add 4 missing tax fields from reference Section 4.4",
        "current_state": "Missing: exit_price_cents, kalshi_fee_cents, gross_profit_cents, tax_basis_usd. Current pnl_cents is net (after fees) but gross and fee components are not stored separately.",
        "reference_requirement": "Section 4.4: every trade must log kalshi_fee, gross_profit, net_profit, tax_basis separately for tax reconstruction.",
        "rebuild_plan": "Add to db.py _migrate(): ALTER TABLE trades ADD COLUMN exit_price_cents INTEGER; ALTER TABLE trades ADD COLUMN kalshi_fee_cents INTEGER; ALTER TABLE trades ADD COLUMN gross_profit_cents INTEGER; ALTER TABLE trades ADD COLUMN tax_basis_usd REAL. Existing rows get NULL (acceptable — historical trades pre-date requirement). New trades: executor.py populates these at settlement.",
        "test_requirement": "test_schema_has_required_tax_fields(), test_migration_is_idempotent()"
      },
      {
        "priority": 4,
        "component": "Dashboard — stale hardcoded constants",
        "current_state": "src/dashboard.py has DAILY_LOSS_LIMIT_USD=20.0 and CONSECUTIVE_LOSS_LIMIT=4. Current values: daily loss cap DISABLED, consecutive_loss_limit=8.",
        "rebuild_plan": "Read these values from config.yaml or kill_switch.py constants rather than hardcoding. Or at minimum update to match current values and add a comment noting they must match kill_switch.py.",
        "test_requirement": "Manual verification — no automated test for Streamlit display."
      },
      {
        "priority": 5,
        "component": "Price feed — add Coinbase as secondary BTC source",
        "current_state": "Single Binance.US WebSocket feed. Reference requires dual feed (Binance + Coinbase) with median of both. If Binance.US drops, bot runs blind.",
        "reference_requirement": "Phase 1 price_feed.py: 'Pulls live BTC spot price from Binance AND Coinbase public REST APIs simultaneously, returns the median of both.'",
        "rebuild_plan": "Add CoinbaseFeed class (or polling via REST since Coinbase Advanced Trade has a free REST API). Run as backup. If Binance stale: fall back to Coinbase. If both stale: PriceFeedError.",
        "estimated_effort": "1-2 hours. Lower priority than poll interval reduction since Binance.US has been stable.",
        "test_requirement": "test_falls_back_to_coinbase_on_binance_stale()"
      },
      {
        "priority": 6,
        "component": "Brier gate — tighten from 0.30 to 0.20 for Stage 2 promotion",
        "current_state": "Current threshold: Brier < 0.30 for Stage 1 promotion. Reference says Brier < 0.20 required for live trading. Our best strategy (sol_drift) is at 0.151 ✅. btc_drift at 0.251 ❌ by reference standard. eth_drift at 0.255 ❌ by reference standard.",
        "rebuild_plan": "Do NOT retroactively disable current live strategies — they're already live and the 0.30 threshold is our deliberate PRINCIPLES.md-defined gate. INSTEAD: set Brier < 0.20 as the Stage 2 promotion requirement. This makes Stage 2 ($10 cap) harder to reach, which is appropriate given reference's conservative framing.",
        "action": "Update docs/GRADUATION_CRITERIA.md to set Brier < 0.20 as Stage 2 gate (currently Stage 2 gate unspecified). No code change needed."
      }
    ]
  }
}
```

---

## KEY DIVERGENCES FROM REFERENCE — INTENTIONAL vs. ACCIDENTAL

These are places where our bot differs from the reference document. Some are intentional
(based on 9 months of live experience), some are gaps to fix.

| Divergence | Type | Verdict |
|---|---|---|
| **Daily loss cap DISABLED** (reference: $25/day mandatory) | Intentional (Session 42) | **RISKY** — Review. Matthew disabled because cap was blocking bets. Consider re-enabling at $50-100/day given Stage 1 $5 cap (10-20 losses before trigger) |
| **Brier gate 0.30 vs reference 0.20** | Intentional (PRINCIPLES.md) | OK for Stage 1. Adopt 0.20 for Stage 2. |
| **30 live bets vs reference 200 paper bets** | Intentional (micro-live calibration) | Reasonable — at $0.35/bet micro-live, the real cost was $10-15 vs months of waiting |
| **No explicit fee check pre-signal** | Accidental gap | **FIX** — Add fee_calculator.py (Priority 1 Rebuild) |
| **Single price feed** | Accidental gap | Fix when convenient (Priority 5 Rebuild) |
| **Missing 4 tax DB fields** | Accidental gap | **FIX** — DB migration (Priority 3 Rebuild) |
| **30s poll vs event-driven** | Accidental gap | **FIX** — Reduce to 10s now, full event-driven in Tier 2 |
| **No Streamlit dashboard updates** | Stale constants | Fix stale values (Priority 4 Rebuild) |
| **Sports/copy-trade still in execution path** | Accidental (inertia) | **STRIP** — remove from main.py gather() |

---

## BLOCKED URLs (VA WiFi) — RETRY LATER

These URLs returned errors due to network restrictions and should be retried on better WiFi:

1. `https://docs.kalshi.com/websockets/websocket-connection` — Kalshi WebSocket API docs
   (Needed for: full WebSocket implementation spec, channel names, auth format)
   **Confirmed via WebSearch:** `wss://trading-api/v1/ws` with `ticker` public channel exists.

2. `https://www.edgedesk.net/p/november-cpi-the-cleveland-fed-says-the-market-is-wrong` — CPI edge case study
   (Needed for: specific pre-release CPI window edge sizing)

3. `https://www.federalreserve.gov/econres/feds/files/2026010pap.pdf` — Fed paper on Kalshi macro markets
   (Needed for: academic validation of FOMC/CPI edge strategies)

---

## IMPLEMENTATION TIMELINE (next chat executes)

| Priority | Change | Effort | Risk |
|---|---|---|---|
| 1 | Add `src/risk/fee_calculator.py` + tests | 30 min | LOW |
| 2 | Change `POLL_INTERVAL_SEC` 30→10 | 5 min | LOW |
| 3 | Add 4 tax columns via `_migrate()` | 30 min | LOW |
| 4 | Fix dashboard stale constants | 15 min | LOW |
| 5 | Remove strip items from main.py gather() | 30 min | MEDIUM (need Matthew approval) |
| 6 | Add Coinbase backup feed | 2 hours | MEDIUM |
| 7 | Full event-driven WebSocket trigger | 4 hours | MEDIUM-HIGH |

Items 1-4 are safe to implement autonomously. Items 5-7 require Matthew's sign-off.

---

*Audit complete. Reference doc read: KALSHI_BOT_COMPLETE_REFERENCE.pdf (16 pages, 48,069 chars).*
*Codebase analyzed: 33 Python files, 923 tests, 111 settled live trades.*
*Generated: Session 44 autonomous overhaul, 2026-03-10.*

---

## UPDATE — Session 44 Late (2026-03-10 ~15:00 CDT)

### Reference Doc Full Read — Critical Divergences from Hard Constraints

After reading the full PDF (not just prompts 1 and 2), the following **NEVER VIOLATE** constraints from Section 1
are confirmed gaps:

| Hard Constraint | Current Status | Action Required |
|---|---|---|
| `$25 daily loss kill switch` | **DISABLED** Session 42 | Matthew must decide: re-enable or formally document override |
| `Brier < 0.20` before live capital | btc_drift=0.251 (LIVE), eth_drift=0.255 (LIVE) | Accept divergence OR add hard gate |
| `200+ paper trades` before live | Went live at 30 | Irreversible for existing strategies; enforce for new ones |
| `DRY_RUN=true` until gates cleared | Never used DRY_RUN flag | Our `is_paper` flag is equivalent |
| Fill-status poll every 10s + 60s cancel | Not implemented | PLANNED — see todos.md |

### Section 4.4 Tax Fields — FIXED (commit a350152)
All 4 required tax fields (`exit_price_cents`, `kalshi_fee_cents`, `gross_profit_cents`, `tax_basis_usd`)
now populated on every settlement call. Fee formula updated from `round` → `ceil` for Section 3.3 compliance.
9 regression tests added. 952/952 tests passing.

### Matthew's Strategic Decisions Needed (before restart)
1. **Daily loss cap**: Reference doc says $25/day is a NEVER VIOLATE hard constraint. It was disabled
   Session 42. Do you want to re-enable it? (Bot was bleeding $24/day — that's why it was disabled.)
2. **Strip sign-off**: copy_trader_v1.py, sports_futures_v1.py, eth_orderbook_imbalance live trading —
   all confirmed OUT OF SCOPE by reference doc. Ready to remove from execution path on your approval.
3. **Kalshi CSV comparison**: When you download and share the CSV, we'll compare against our DB to
   validate P&L tracking accuracy and catch any settlement discrepancies.
