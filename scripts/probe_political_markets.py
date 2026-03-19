"""
Political Market Probe — S113 Research

Hypothesis: Le (2026) b=1.83 near-expiry politics → 8pp edge at 90c.
Goal: Find political markets on Kalshi with volume at 90c+ near expiry.

Uses ~5-10 SDATA credits (targeted, not exhaustive).
"""

from __future__ import annotations

import asyncio
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.auth.kalshi_auth import load_from_env as load_kalshi_auth
from src.platforms.kalshi import KalshiClient


def extract_volume(market: dict) -> int:
    vol_fp = market.get("volume_fp")
    if vol_fp:
        try:
            return int(float(vol_fp))
        except (ValueError, TypeError):
            pass
    vol = market.get("volume")
    if vol is not None:
        try:
            return int(vol)
        except (ValueError, TypeError):
            pass
    return 0


def get_yes_price(market: dict) -> int:
    """Return YES price in cents (0-100)."""
    ob = market.get("yes_bid", market.get("last_price", 0))
    if isinstance(ob, (int, float)):
        return int(ob)
    return 0


def time_to_expiry_hours(market: dict) -> float | None:
    """Hours until market closes."""
    close_time = market.get("close_time") or market.get("expiration_time")
    if not close_time:
        return None
    try:
        if isinstance(close_time, str):
            # ISO format
            close_dt = datetime.fromisoformat(close_time.replace("Z", "+00:00"))
        else:
            return None
        now = datetime.now(timezone.utc)
        delta = close_dt - now
        return delta.total_seconds() / 3600
    except Exception:
        return None


async def probe_political_markets(client: KalshiClient):
    now = datetime.now(timezone.utc)
    print(f"\nPolitical Market Probe — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Step 1: Check known political series tickers
    political_series = [
        "KXPRES",
        "KXELECTION",
        "KXSENATE",
        "KXCONGRESS",
        "KXGOV",
        "KXHOUSE",
        "KXPRESAPPROVAL",
        "KXPRESIDENT",
        "KXVOTE",
        "KXPOLLS",
        "KXTRUMP",
        "KXBIDEN",
        "KXHARRIS",
        "KXPRIMARY",
        "KXCABINET",
        "KXSUPREMECOURT",
        "KXPRESDEM",
        "KXPRESREP",
    ]

    print("\nStep 1: Probe known political series tickers...")
    found_series = []
    for ticker in political_series:
        try:
            data = await client._get(f"/series/{ticker}")
            series = data.get("series", {})
            if series:
                found_series.append(series)
                title = series.get("title", "?")
                print(f"  FOUND: {ticker} — {title}")
        except Exception:
            pass  # 404 = doesn't exist

    if not found_series:
        print("  No direct-match series found. Trying category search...")

    # Step 2: Search markets with category/tag filter for politics
    print("\nStep 2: Fetch open markets by category...")
    political_markets = []

    # Try category-based search
    for category_hint in ["politics", "political", "election", "government"]:
        try:
            params = {"limit": 200, "status": "open"}
            data = await client._get("/markets", params=params)
            markets = data.get("markets", [])
            # Filter by ticker or title containing political keywords
            for m in markets:
                ticker = m.get("ticker", "").lower()
                title = m.get("title", "").lower()
                if any(k in ticker or k in title for k in [
                    "elect", "presid", "senate", "congress", "house", "gov",
                    "trump", "harris", "biden", "vote", "prim", "cabinet",
                    "political", "democrat", "republican", "party", "poll",
                    "approval", "ballot", "inaug", "executive"
                ]):
                    political_markets.append(m)
            break  # only need one pass
        except Exception as e:
            print(f"  Markets fetch error: {e}")

    # Deduplicate by ticker
    seen = set()
    unique_markets = []
    for m in political_markets:
        t = m.get("ticker", "")
        if t not in seen:
            seen.add(t)
            unique_markets.append(m)

    print(f"\nFound {len(unique_markets)} political-themed open markets.")

    if not unique_markets:
        print("\nStep 3: Full open market scan for political content...")
        # Paginate all open markets and filter
        all_markets = []
        cursor = None
        page = 0
        while page < 10:
            page += 1
            params = {"limit": 1000, "status": "open"}
            if cursor:
                params["cursor"] = cursor
            try:
                data = await client._get("/markets", params=params)
                batch = data.get("markets", [])
                all_markets.extend(batch)
                cursor = data.get("cursor", "")
                print(f"  Page {page}: {len(batch)} markets (total: {len(all_markets)})")
                if not batch or not cursor:
                    break
            except Exception as e:
                print(f"  Error: {e}")
                break

        for m in all_markets:
            ticker = m.get("ticker", "").lower()
            title = m.get("title", "").lower()
            subtitle = m.get("subtitle", "").lower()
            text = ticker + " " + title + " " + subtitle
            if any(k in text for k in [
                "elect", "presid", "senate", "congress", "house", "gov",
                "trump", "harris", "biden", "vote", "prim", "cabinet",
                "democrat", "republican", "party", "poll",
                "approval", "ballot", "inaug", "executive", "tariff",
                "legislation", "bill", "act ", "policy", "political"
            ]):
                unique_markets.append(m)

        print(f"  Political markets after full scan: {len(unique_markets)}")

    # Step 3: Analyze 90c+ near-expiry candidates
    print("\nStep 3: Analyze 90c+ near-expiry political markets...")
    print("-" * 60)

    sniper_candidates = []  # 90c+, < 24h
    all_high_prob = []      # 90c+, any horizon

    volume_by_bucket = defaultdict(list)

    for m in unique_markets:
        ticker = m.get("ticker", "")
        title = m.get("title", "")
        yes_price = get_yes_price(m)
        vol = extract_volume(m)
        tte = time_to_expiry_hours(m)

        # Track all
        price_bucket = f"{(yes_price // 10) * 10}c"
        volume_by_bucket[price_bucket].append(vol)

        if yes_price >= 90:
            all_high_prob.append({
                "ticker": ticker,
                "title": title,
                "yes_price": yes_price,
                "vol": vol,
                "tte_hours": tte,
            })
            if tte is not None and tte <= 24:
                sniper_candidates.append({
                    "ticker": ticker,
                    "title": title,
                    "yes_price": yes_price,
                    "vol": vol,
                    "tte_hours": round(tte, 1),
                })

    # Also check NO side (YES price < 10 = NO at 90c+)
    for m in unique_markets:
        yes_price = get_yes_price(m)
        if yes_price <= 10:  # NO is 90c+
            no_price = 100 - yes_price
            vol = extract_volume(m)
            tte = time_to_expiry_hours(m)
            all_high_prob.append({
                "ticker": m.get("ticker", ""),
                "title": m.get("title", "") + " [NO]",
                "yes_price": no_price,
                "vol": vol,
                "tte_hours": tte,
            })
            if tte is not None and tte <= 24:
                sniper_candidates.append({
                    "ticker": m.get("ticker", "") + "_NO",
                    "title": m.get("title", "") + " [NO]",
                    "yes_price": no_price,
                    "vol": vol,
                    "tte_hours": round(tte, 1),
                })

    print(f"\nAll 90c+ political markets: {len(all_high_prob)}")
    for m in sorted(all_high_prob, key=lambda x: -x["vol"])[:20]:
        tte_str = f"{m['tte_hours']:.1f}h" if m["tte_hours"] is not None else "?"
        print(f"  {m['ticker']:40s} {m['yes_price']}c  vol={m['vol']:8,}  tte={tte_str}  {m['title'][:50]}")

    print(f"\nNear-expiry (<24h) 90c+ candidates: {len(sniper_candidates)}")
    for m in sorted(sniper_candidates, key=lambda x: -x["vol"])[:20]:
        print(f"  {m['ticker']:40s} {m['yes_price']}c  vol={m['vol']:8,}  tte={m['tte_hours']}h  {m['title'][:50]}")

    # Step 4: Volume distribution summary
    print("\nStep 4: Volume distribution by price bucket (political markets)")
    print("-" * 60)
    for bucket in sorted(volume_by_bucket.keys(), reverse=True):
        vols = volume_by_bucket[bucket]
        if vols:
            avg_vol = sum(vols) / len(vols)
            max_vol = max(vols)
            print(f"  {bucket:5s}: n={len(vols):3d}  avg_vol={avg_vol:8,.0f}  max_vol={max_vol:10,}")

    # Step 5: FLB edge calculation for political markets
    print("\nStep 5: FLB edge at key price levels (Le 2026, b=1.83)")
    print("-" * 60)
    b = 1.83  # politics near-expiry calibration slope
    for p_market in [0.90, 0.92, 0.93, 0.94, 0.95, 0.97]:
        p_true = (p_market ** b) / (p_market ** b + (1 - p_market) ** b)
        edge_pp = (p_true - p_market) * 100
        break_even = 1 / p_market
        # Simplified: fee ~2c per bet
        net_edge_pp = edge_pp - 2  # rough fee subtraction
        print(f"  {int(p_market*100)}c:  true_prob={p_true:.3f}  edge={edge_pp:.1f}pp  "
              f"net_after_2c_fee={net_edge_pp:.1f}pp")

    print("\nStep 6: Comparison — crypto vs politics FLB edge")
    print("-" * 60)
    b_crypto = 1.03
    for p_market in [0.90, 0.93, 0.95]:
        p_true_crypto = (p_market ** b_crypto) / (p_market ** b_crypto + (1 - p_market) ** b_crypto)
        p_true_politics = (p_market ** b) / (p_market ** b + (1 - p_market) ** b)
        print(f"  {int(p_market*100)}c:  crypto edge={100*(p_true_crypto - p_market):.1f}pp  "
              f"politics edge={100*(p_true_politics - p_market):.1f}pp  "
              f"ratio={((p_true_politics - p_market)/(p_true_crypto - p_market)):.0f}x")

    print("\n" + "=" * 60)
    print("CONCLUSION")
    print("=" * 60)

    if sniper_candidates:
        print(f"VIABLE: {len(sniper_candidates)} political markets at 90c+ within 24h.")
        print("Political sniper IS worth investigating if volume >= 1000 contracts.")
        high_vol = [m for m in sniper_candidates if m["vol"] >= 1000]
        print(f"High-volume (>= 1000 contracts): {len(high_vol)}")
        if high_vol:
            print("RECOMMENDATION: Political sniper is FEASIBLE — write to CCA for strategy design.")
        else:
            print("RECOMMENDATION: Volume too low for meaningful fills at current time.")
            print("  Note: Check again near major political events.")
    elif all_high_prob:
        print(f"CONDITIONAL: {len(all_high_prob)} political markets at 90c+ exist but none near expiry.")
        print("  These markets may approach expiry in future. Political sniper needs time-based trigger.")
        print("  Check again for markets expiring in <24h around political events.")
    else:
        print("NOT VIABLE: No political markets found at 90c+ on Kalshi.")
        print("  This may be due to current market cycle (2026 — between major elections).")
        print("  Political markets are episodic, not continuous series like crypto.")
        print("  RECOMMENDATION: Revisit before 2026 midterms or next major political event.")

    return sniper_candidates, all_high_prob, unique_markets


async def main():
    auth = load_kalshi_auth()
    client = KalshiClient(
        auth=auth,
        base_url="https://trading-api.kalshi.com/trade-api/v2",
    )
    await client.start()
    try:
        candidates, high_prob, all_political = await probe_political_markets(client)

        # Save raw data for analysis
        import json
        output = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sniper_candidates_90c_24h": candidates,
            "all_90c_markets": high_prob,
            "total_political_markets_found": len(all_political),
        }
        with open("data/political_market_probe_s113.json", "w") as f:
            json.dump(output, f, indent=2)
        print("\nRaw data saved to data/political_market_probe_s113.json")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
