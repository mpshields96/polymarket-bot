# Copy Trading Research — Session 30
# Researched: 2026-03-01 (autonomous session while Matthew away)
# Goal: find top trader sources, open-source repos, Kalshi feasibility

══════════════════════════════════════════════════════════════
## KALSHI COPY TRADING — VERDICT: NOT FEASIBLE VIA PUBLIC API
══════════════════════════════════════════════════════════════

### Why it's blocked

Kalshi's public trade API (`GET /trade-api/v2/trades`) returns ANONYMOUS trade data.
- No username, member ID, or any identifying info per trade
- You can filter by ticker and timestamp, but NOT by member/user
- There is no `data-api.kalshi.com/trades?user=X` equivalent
- Portfolio/fills (`/portfolio/fills`) requires auth — returns YOUR fills only, not others'

Confirmed from docs.kalshi.com/api-reference/market/get-trades:
  Response fields: trade_id, ticker, count, yes_price, no_price, taker_side, created_time
  No user attribution whatsoever.

### Leaderboard visibility

- Leaderboard exists at kalshi.com/social/leaderboard
- Users are opted OUT by default — many top traders aren't visible
- No API to query leaderboard data or get specific member's trade history
- Third-party copy trading service exists (see digitaljournal.com PR) but unclear
  if they use OAuth account sharing or some unofficial mechanism

### Conclusion

Kalshi copy trading is fundamentally different from Polymarket:
- Polymarket is on-chain → all trades are public blockchain data
- Kalshi is a centralized exchange → trade data is private by design
- UNLESS Kalshi adds a social/copy-trading feature with explicit opt-in
  (the leaderboard feature exists but doesn't expose trade-level data publicly)

DO NOT build Kalshi copy trading infrastructure. The data doesn't exist publicly.
Log this as closed. Focus 100% on Polymarket.COM.

══════════════════════════════════════════════════════════════
## POLYMARKET.COM — THE RIGHT PLATFORM FOR COPY TRADING
══════════════════════════════════════════════════════════════

### Why .COM not .US

Our existing auth (Ed25519, api.polymarket.us) only covers:
- Sports-only: NBA/NFL/NHL/NCAA (launched Dec 2025, CFTC approval)
- No crypto, no politics, no culture

The whales we're tracking (predicting.top leaderboard) trade on polymarket.COM:
- Full market suite: politics, crypto, sports, culture, economics, geopolitics, entertainment
- ALL the high-value markets are here (BTC/ETH 15-min, US elections, etc.)

Our current `data-api.polymarket.com` reads are already from .COM data.
We're reading .COM signals but can only execute on .US (sports only).

### What's needed for .COM trading

1. **Matthew creates a polymarket.com account** (personal, with Polygon/MetaMask wallet)
2. **Polygon wallet**: USDC.e required in funder address for BUY orders
3. **Auth**: ECDSA secp256k1 (Ethereum signing) via py-clob-client
4. **py-clob-client**: `pip install py-clob-client` (v0.29.0, Dec 2025, MIT)
   - Endpoint: https://clob.polymarket.com
   - Chain ID: 137 (Polygon mainnet)
   - Signature types: 0=EOA (standard), 1=proxy/email, 2=gnosis safe
   - API creds: derived via `client.create_or_derive_api_creds()`
5. **Order type**: GTC is supported (but USE FOK/IOC — never GTC, never be a liquidity provider)

Quick setup (3 steps):
```python
from py_clob_client.client import ClobClient
# 1. Init with private key
client = ClobClient("https://clob.polymarket.com", key=PRIVATE_KEY, chain_id=137)
# 2. Set API credentials
client.set_api_creds(client.create_or_derive_api_creds())
# 3. Place order
order_args = OrderArgs(token_id=TOKEN_ID, price=0.65, size=10, side=BUY)
order = client.create_and_post_order(order_args)
```

### Order safety rule (HARDCODED when built)
- FOK/IOC ONLY — never GTC
- Never be a liquidity provider (maker)
- Always use `time_in_force=FOK` in order args

══════════════════════════════════════════════════════════════
## OPEN SOURCE REPOS — EVALUATED FOR ADOPTION
══════════════════════════════════════════════════════════════

### HIGH VALUE — worth reviewing in detail

1. **discountry/polymarket-trading-bot** (Python)
   - Flash Crash Strategy: monitors 15-min Up/Down markets for sudden probability drops
   - Gasless transactions via Builder Program
   - Real-time WebSocket, encrypted private key storage
   - 89 unit tests, asyncio — SIMILAR ARCHITECTURE TO OURS
   - Auth: MetaMask private key + Safe address + Builder API creds
   - WORTH REVIEWING: Flash Crash is a legit signal we haven't built

2. **ent0n29/polybot** (Python)
   - Arbitrage strategy for Polymarket Up/Down binaries
   - Planning a "fund mirroring" product layer (AWARE) — not yet built
   - Auth: private key + API key/secret/passphrase
   - WORTH REVIEWING: arbitrage implementation details

3. **Now-Or-Neverr/polymarket-trading-bot** (TypeScript/Node.js)
   - Copy trading + arbitrage, risk management controls
   - Uses `TRADER_ADDRESSES` config to follow specific traders
   - WORTH REVIEWING: how they handle copy trade dedup and signal filtering

4. **Polymarket/agents** (Python — Official)
   - AI agent framework (LLM-based), not a strategy
   - Uses OpenAI + Polygon private key
   - NOT useful for our approach (we're signal-based not AI-based)

### WHALE TRACKING SERVICES (external, not repos)

- **Polywhaler** (polywhaler.com) — tracks $10k+ trades in real-time, free
- **PolyTrack** (polytrackhq.app) — leaderboards, P&L tracking, real-time alerts
- **PolyWatch** (polywatch.tech) — free real-time trade alerts
- **PolyxBot** (Telegram) — AI whale tracking bot
- **Polycule** (Telegram) — group trading, copy trading, wallet tracking
- **PolyFocus** (Telegram) — copy trading with multi-chain wallet support

These are competitors/references. Our approach (predicting.top + data-api) is already
comparable to what these services do.

══════════════════════════════════════════════════════════════
## TOP TRADERS TO STUDY
══════════════════════════════════════════════════════════════

These are .COM traders with documented track records:
- **WindWalk3** — $1.1M+ profit, primarily politics/RFK (single bet $1.1M win)
- **Erasmus** — $1.3M+ profit, political markets, polling-based methodology
- **HyperLiquid0xb** — $1.4M+ profit, sports focus, baseball specialist
- **aenews** — Rank 1 on predicting.top, smart_score 79.2, wins 278/459 (60.6%)

All these wallets are trackable via data-api.polymarket.com.
aenews is already in our whale list (rank 1 from predicting.top).

══════════════════════════════════════════════════════════════
## POLYMARKET ECOSYSTEM RESOURCES
══════════════════════════════════════════════════════════════

Reddit:
- r/polymarket (50K+ members) — main community, market analysis, trade ideas
- r/predictionmarkets — broader PM discussion (Kalshi, Polymarket, Manifold)
- r/Kalshi — Kalshi specific

Whale tracking tools (already built, public):
- polywhaler.com — real-time large trade alerts
- polymarketanalytics.com — discovery + performance metrics
- unusualwhales.com/predictions — unusual position tracking

Data APIs (all public, no auth):
- data-api.polymarket.com — trades + positions per wallet (WE USE THIS ✅)
- gamma-api.polymarket.com — market metadata, indexed on-chain data
- polymarket.com/leaderboard — public leaderboard (monthly/overall profit)

Useful GitHub topics:
- github.com/topics/polymarket
- github.com/harish-garg/Awesome-Polymarket-Tools (curated list)

══════════════════════════════════════════════════════════════
## ACTION ITEMS FOR NEXT SESSION
══════════════════════════════════════════════════════════════

1. DECISION: Matthew — polymarket.com account + Polygon wallet?
   This is the single gate for full copy trading. Everything else is ready.

2. RESEARCH: Review discountry/polymarket-trading-bot Flash Crash strategy
   Could be a supplemental signal for .US sports markets and eventually .COM crypto

3. RESEARCH: Review ent0n29/polybot arbitrage implementation
   Complete-set arbitrage on Up/Down binaries could work on .COM

4. PASS: Kalshi copy trading — not feasible. Closed.

5. IMPLEMENT (when .COM decision is YES):
   - pip install py-clob-client
   - PolymarketCOMAuth: ECDSA secp256k1 wrapper (similar to our Ed25519 but for ETH)
   - PolymarketCOMClient: wraps clob.polymarket.com with FOK/IOC enforcement
   - Wire copy_trader_v1 signals → .COM executor (FOK, $5 cap)
