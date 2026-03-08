# Copy Trading Research
# Last updated: Session 31 (2026-03-08)
# Covers: Kalshi feasibility, Polymarket.COM path, ecosystem tools, top traders

══════════════════════════════════════════════════════════════
## KALSHI COPY TRADING — CONFIRMED INFEASIBLE
══════════════════════════════════════════════════════════════

Kalshi's public trade API (`GET /market/get-trades`) returns ANONYMOUS trade data:
- Response fields: trade_id, ticker, count, yes_price, no_price, taker_side, created_time
- No username, member ID, or any identifying info per trade
- Portfolio/fills (`/portfolio/fills`) requires auth — returns YOUR fills only
- Leaderboard exists at kalshi.com/social/leaderboard but no trade-level API for it
- Users are opted OUT by default — many top traders aren't even visible

**Why this is fundamentally different from Polymarket:**
- Polymarket is on-chain → all trades are public blockchain data
- Kalshi is a CFTC-regulated centralized exchange → trade data is private by design

**Verdict:** Dead end. DO NOT build Kalshi copy trading infrastructure. Closed.

══════════════════════════════════════════════════════════════
## POLYMARKET.COM — THE RIGHT PLATFORM FOR COPY TRADING
══════════════════════════════════════════════════════════════

### Platform split (critical — never confuse these)

| | polymarket.US | polymarket.COM |
|---|---|---|
| Auth | Ed25519 (we have this) | ECDSA secp256k1 (Ethereum wallet) |
| Markets | Sports only (NBA/NFL/NHL) | Full: politics, crypto, sports, culture, economics |
| Where whales are | No | YES |
| Public trade data | No | Via data-api.polymarket.com (public, no auth) |
| Status | We have credentials | Need new account + Polygon wallet from Matthew |

### What's needed for .COM trading

1. **Matthew creates a polymarket.com account** (Polygon/MetaMask wallet)
2. **Polygon wallet**: USDC.e required in funder address for BUY orders
3. **Auth**: ECDSA secp256k1 via py-clob-client
4. **py-clob-client**: `pip install py-clob-client` (v0.29.0, Dec 2025, MIT)
   - Endpoint: https://clob.polymarket.com, Chain ID: 137 (Polygon mainnet)
5. **Order type**: FOK/IOC ONLY — never GTC, never be a liquidity provider

### Public APIs (confirmed working, no auth)
- `data-api.polymarket.com/trades?user={proxy_wallet}` — whale trade history (WE USE THIS)
- `data-api.polymarket.com/activity` — all activity, filterable by type + user (BETTER?)
- `data-api.polymarket.com/positions?user={proxy_wallet}` — open positions
- `gamma-api.polymarket.com/markets` — full market catalog

Note: QuickNode copy-trade tutorial uses `/activity` endpoint (not `/trades`) for real-time
monitoring. May have better timing than /trades. Worth testing in whale_watcher.py.

══════════════════════════════════════════════════════════════
## TOP TRADERS (verified 2026)
══════════════════════════════════════════════════════════════

| Name | P&L | Specialty | Notes |
|---|---|---|---|
| HyperLiquid0xb | $1.4M | Sports | Largest single win $755k |
| Erasmus | $1.3M | Politics | $95k single win, polling edge |
| 1j59y6nk | $1.4M | Games/Sports | $90k single win |
| WindWalk3 | $1.1M | Politics (RFK) | All-in directional |
| BAdiosB | $141k | Mispricing arb | 90.8% win rate, 11.3% ROI |
| Axios | n/a | Mention markets | 96% win rate niche |
| aenews | #1 predicting.top | Mixed | smart_score 79.2, 278/459 (60.6%) |

Trader archetypes (useful for filtering which whales to follow):
- Quant Fund: 2000+ trades, 58% win rate (volume-based, safe to copy size-scaled)
- Political Insider: 87 trades, 71% win rate (information edge — copy fast or not at all)
- Sports Pro: 421 trades, 61% win rate (most overlap with our .US sports markets)
- Mispricing Arb: BAdiosB style — 11.3% ROI impressive, probably exploiting inefficiencies

Decoy risk note: Some top traders actively use multiple wallets + swapped handles to confuse
copiers. Our existing decoy filters (size, timing, position age) are the defense.

══════════════════════════════════════════════════════════════
## ECOSYSTEM TOOLS (2026)
══════════════════════════════════════════════════════════════

### Free copy trading / whale tracking
- **Stand.trade** — advanced terminal, tracks and copies whales, free
- **Polycule** — Telegram bot, 1% fee, sub-second fills
- **PolyTracker** (Telegram) — wallet monitoring, real-time alerts
- **Polylerts** — free Telegram bot, up to 15 wallets
- **Whale Tracker Livid** — $50k+ portfolio wallets, free tier has 1hr delay
- **PolyScope** — free real-time monitoring, smart trader activity
- **Polywhaler** (polywhaler.com) — real-time $10k+ trade alerts

### Open source Python repos (study only, never run with our keys)
1. **Twiztidbonez/Polymarket-copytrade-bot** — copy whale activity (Feb 2026)
2. **discountry/polymarket-trading-bot** — Flash Crash strategy, 89 tests, asyncio ⭐
3. **Now-Or-Neverr/polymarket-trading-bot** — copy trading + arbitrage (TypeScript)
4. **dev-protocol/polymarket-copy-bot** — copy trading impl
5. **CarlosIbCu/polymarket-kalshi-btc-arbitrage-bot** — cross-platform arb (Rust)
6. **aarora4/Awesome-Prediction-Market-Tools** — curated tool list

### Security warning (CRITICAL)
December 2025: malicious code found in popular GitHub bots stealing private keys.
Some bots request unlimited USDC spending approval on setup.
**Rule: NEVER run third-party code with our keys. Study repos, adapt patterns only.**

══════════════════════════════════════════════════════════════
## WHY OTHER BOTS SHIP FASTER
══════════════════════════════════════════════════════════════

Most "quick" copy trading bots are:
1. Simple wrappers: poll data-api → if whale bought → post same order via py-clob-client
2. Zero risk management (no kill switch, no Kelly sizing, no position limits)
3. No statistical framework (no edge calc, no Brier scoring, no decoy filtering)
4. Often selling a product/service — not serious algorithmic implementations

They ship in a weekend because they have <200 lines of real logic.

Our bot has:
- 10 calibrated strategies with signal edge metrics
- Kill switch with 3 persistent counters (daily/lifetime/consecutive loss)
- Kelly sizing with stage progression
- Decoy filter (6 filters on copy_trader_v1)
- 754 unit tests

Tradeoff: those bots blow up on bad whale streaks, decoy trades, or market regime changes.
Ours has guardrails. The extra build time is the price of not losing your stack.

══════════════════════════════════════════════════════════════
## NEXT ACTIONS
══════════════════════════════════════════════════════════════

1. **GATE: Matthew — create polymarket.com account + Polygon wallet + USDC.e deposit**
   This is the SINGLE blocker for live copy trading on .COM.

2. **Investigate /activity endpoint** in whale_watcher.py
   - data-api.polymarket.com/activity vs /trades — is latency better?
   - Low risk: public endpoint, no auth, no code changes to production paths

3. **Filter whale list for .COM market specialists**
   - 144 whales currently tracked; filter for political/crypto focus over sports-only
   - Prioritize whales with .COM trade history in politics + crypto

4. **Study discountry/polymarket-trading-bot Flash Crash strategy**
   - 89 tests, asyncio, similar architecture to ours
   - Flash Crash = sudden probability drop in 15-min market = potential signal

5. **Kalshi copy trading — CLOSED**
   No public user attribution. Cannot be built. Do not revisit unless Kalshi adds
   an opt-in social trading API.
