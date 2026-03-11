"""
Export all Kalshi settled trades to CSV for tax/accounting purposes.

Pulls from /portfolio/settlements (outcome + payout per market) and
/portfolio/fills (entry price + timestamp per fill) and joins them by ticker.

Usage:
    cd /path/to/polymarket-bot
    source venv/bin/activate
    LIVE_TRADING=true python3 scripts/export_kalshi_settlements.py

Output: reports/kalshi_settlements.csv
"""

from __future__ import annotations

import asyncio
import csv
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from src.platforms.kalshi import load_from_env as kalshi_load


# ── Data fetching ─────────────────────────────────────────────────────────────


async def fetch_all_settlements(client) -> List[Dict[str, Any]]:
    """Cursor-paginate through /portfolio/settlements until exhausted."""
    settlements: List[Dict] = []
    cursor: str | None = None
    page = 0
    while True:
        params: Dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = await client._get("/portfolio/settlements", params=params)
        # Kalshi may return "settlements" or "portfolio_settlements" — try both
        batch = data.get("settlements") or data.get("portfolio_settlements") or []
        settlements.extend(batch)
        page += 1
        print(f"  Settlements page {page}: {len(batch)} records (running total: {len(settlements)})")
        cursor = data.get("cursor")
        if not cursor or not batch:
            break
    return settlements


async def fetch_all_fills(client) -> List[Dict[str, Any]]:
    """Cursor-paginate through /portfolio/fills until exhausted."""
    fills: List[Dict] = []
    cursor: str | None = None
    page = 0
    while True:
        params: Dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        data = await client._get("/portfolio/fills", params=params)
        batch = data.get("fills", [])
        fills.extend(batch)
        page += 1
        print(f"  Fills page {page}: {len(batch)} records (running total: {len(fills)})")
        cursor = data.get("cursor")
        if not cursor or not batch:
            break
    return fills


# ── Data processing ───────────────────────────────────────────────────────────


def index_fills_by_ticker(fills: List[Dict]) -> Dict[str, Dict]:
    """
    Group fills by ticker. Returns one summary dict per ticker with:
      - side: "yes" or "no"
      - entry_time: ISO timestamp of earliest fill
      - avg_entry_price_cents: weighted average entry price
      - fill_count: number of individual fills
    """
    grouped: Dict[str, List[Dict]] = {}
    for f in fills:
        ticker = f.get("ticker") or f.get("market_ticker") or ""
        grouped.setdefault(ticker, []).append(f)

    result: Dict[str, Dict] = {}
    for ticker, ticker_fills in grouped.items():
        ticker_fills.sort(key=lambda x: x.get("created_time", ""))
        earliest = ticker_fills[0]
        side = earliest.get("side", "")

        total_contracts = sum(f.get("count", 0) for f in ticker_fills)
        if side == "yes":
            total_price_weighted = sum(
                f.get("yes_price", 0) * f.get("count", 0) for f in ticker_fills
            )
        else:
            total_price_weighted = sum(
                f.get("no_price", 0) * f.get("count", 0) for f in ticker_fills
            )

        avg_price = (
            round(total_price_weighted / total_contracts, 1)
            if total_contracts > 0 else 0.0
        )

        result[ticker] = {
            "side": side,
            "entry_time": earliest.get("created_time", ""),
            "avg_entry_price_cents": avg_price,
            "fill_count": len(ticker_fills),
        }
    return result


def build_rows(
    settlements: List[Dict],
    fills_by_ticker: Dict[str, Dict],
) -> List[Dict]:
    """
    Join settlements with fill summary. One row per settled market.

    P&L formula:
      net_pnl = revenue_usd - total_cost_usd - fee_usd

    Notes:
      - no_total_cost / yes_total_cost are in CENTS (divide by 100)
      - revenue is in DOLLARS already
      - fee_cost is in DOLLARS already (e.g. "0.0700")
    """
    rows = []
    for s in settlements:
        ticker = s.get("ticker", "")
        fill_info = fills_by_ticker.get(ticker, {})

        market_result = s.get("market_result", "")
        no_count: int = s.get("no_count", 0)
        yes_count: int = s.get("yes_count", 0)
        no_total_cost_cents: int = s.get("no_total_cost", 0)
        yes_total_cost_cents: int = s.get("yes_total_cost", 0)
        revenue_cents: float = float(s.get("revenue", 0))
        revenue: float = revenue_cents / 100.0   # API returns cents, convert to USD
        fee_usd: float = float(s.get("fee_cost", 0))

        # Determine which side we were on (fills are authoritative)
        side = fill_info.get("side", "")
        if not side:
            if yes_count > 0 and no_count == 0:
                side = "yes"
            elif no_count > 0 and yes_count == 0:
                side = "no"
            elif yes_count > 0 and no_count > 0:
                side = "mixed"
            else:
                side = "unknown"

        if side == "yes":
            contracts = yes_count
            total_cost_usd = yes_total_cost_cents / 100.0
        elif side == "no":
            contracts = no_count
            total_cost_usd = no_total_cost_cents / 100.0
        else:
            contracts = yes_count + no_count
            total_cost_usd = (yes_total_cost_cents + no_total_cost_cents) / 100.0

        won = (
            (side == "yes" and market_result == "yes")
            or (side == "no" and market_result == "no")
        )
        net_pnl_usd = revenue - total_cost_usd - fee_usd

        rows.append({
            "ticker": ticker,
            "event_ticker": s.get("event_ticker", ""),
            "entry_time": fill_info.get("entry_time", ""),
            "settled_time": s.get("settled_time", ""),
            "market_result": market_result,
            "our_side": side,
            "contracts": contracts,
            "avg_entry_price_cents": fill_info.get("avg_entry_price_cents", ""),
            "total_cost_usd": round(total_cost_usd, 4),
            "revenue_usd": round(revenue, 4),
            "fee_usd": round(fee_usd, 4),
            "net_pnl_usd": round(net_pnl_usd, 4),
            "won": "yes" if won else "no",
        })

    rows.sort(key=lambda r: r.get("settled_time", ""))
    return rows


# ── Main ──────────────────────────────────────────────────────────────────────


async def main() -> None:
    print("=" * 50)
    print("Kalshi Settlements Export")
    print("=" * 50)

    # Force live mode so we hit the real portfolio endpoint
    os.environ["LIVE_TRADING"] = "true"

    client = kalshi_load()
    await client.start()

    try:
        print("\n[1/4] Fetching settlements...")
        settlements = await fetch_all_settlements(client)
        print(f"  → {len(settlements)} total settlements")

        print("\n[2/4] Fetching fills...")
        fills = await fetch_all_fills(client)
        print(f"  → {len(fills)} total fills")

        print("\n[3/4] Joining data...")
        fills_by_ticker = index_fills_by_ticker(fills)
        rows = build_rows(settlements, fills_by_ticker)
        print(f"  → {len(rows)} rows built")

        print("\n[4/4] Writing CSV...")
        output_path = PROJECT_ROOT / "reports" / "kalshi_settlements.csv"
        output_path.parent.mkdir(exist_ok=True)

        fieldnames = [
            "ticker",
            "event_ticker",
            "entry_time",
            "settled_time",
            "market_result",
            "our_side",
            "contracts",
            "avg_entry_price_cents",
            "total_cost_usd",
            "revenue_usd",
            "fee_usd",
            "net_pnl_usd",
            "won",
        ]
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"  → Saved to {output_path}")

        # Summary
        total_cost = sum(r["total_cost_usd"] for r in rows)
        total_revenue = sum(r["revenue_usd"] for r in rows)
        total_fees = sum(r["fee_usd"] for r in rows)
        total_pnl = sum(r["net_pnl_usd"] for r in rows)
        wins = sum(1 for r in rows if r["won"] == "yes")
        losses = len(rows) - wins

        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        print(f"  Total settled bets : {len(rows)}")
        print(f"  Wins / Losses      : {wins} / {losses}")
        if len(rows) > 0:
            print(f"  Win rate           : {wins / len(rows) * 100:.1f}%")
        print(f"  Total cost basis   : ${total_cost:.2f}")
        print(f"  Total revenue      : ${total_revenue:.2f}")
        print(f"  Total fees paid    : ${total_fees:.2f}")
        print(f"  Net P&L            : ${total_pnl:.2f}")
        print("=" * 50)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
