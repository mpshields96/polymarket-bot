"""
Domain Knowledge Scanner — LLM-based probability estimation for Kalshi markets.

JOB:    Enumerate open politics/economics/geopolitics markets on Kalshi,
        ask Claude Haiku for a probability estimate on each, compare to
        Kalshi market price, and log edges for calibration tracking.

USAGE:
    source venv/bin/activate
    python scripts/domain_knowledge_scanner.py                    # scan all categories
    python scripts/domain_knowledge_scanner.py --category politics # politics only
    python scripts/domain_knowledge_scanner.py --min-edge 0.10    # 10% minimum edge
    python scripts/domain_knowledge_scanner.py --dry-run           # use cached data
    python scripts/domain_knowledge_scanner.py --calibration       # show calibration stats

OUTPUT:
    Saves results to data/domain_knowledge_scans.jsonl (append-only).
    Prints edge opportunities sorted by absolute edge size.

API BUDGET:
    Kalshi: free (no quota)
    Anthropic (Haiku): ~$0.01 per market evaluation (~$0.50/day for 50 markets)
    Total per scan: ~$0.10-0.50 depending on market count

PHASE 1: Data accumulation (this script). Paper trading after 50+ calibrated estimates.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from src.platforms.kalshi import KalshiClient, Market

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────���─────────────────────

# Model for probability estimation (Haiku = cheap, fast, good enough for calibration)
LLM_MODEL = "claude-haiku-4-5-20251001"
LLM_MAX_TOKENS = 512

# Categories to scan: series_ticker prefixes
CATEGORY_SERIES = {
    "politics": [
        # No specific series — scan broadly and filter by title keywords
    ],
    "economics": [
        "KXFEDDECISION", "KXCPI",
    ],
}

# Title keywords for broad category matching (used when no series_ticker filter)
CATEGORY_KEYWORDS = {
    "politics": [
        "president", "senate", "congress", "election", "republican", "democrat",
        "trump", "biden", "governor", "mayor", "party", "vote", "impeach",
        "nomination", "primary", "poll", "approve", "approval", "mention",
        "say", "tweet", "executive order", "veto", "legislation", "bill",
        "tariff", "sanction",
    ],
    "economics": [
        "fed", "fomc", "rate", "cpi", "inflation", "gdp", "unemployment",
        "jobs", "nonfarm", "payroll", "recession", "shutdown", "debt ceiling",
        "treasury", "yield", "interest rate",
    ],
    "geopolitics": [
        "ukraine", "russia", "china", "taiwan", "ceasefire", "invasion",
        "nato", "iran", "israel", "war", "conflict", "sanctions",
        "nuclear", "missile", "peace", "treaty",
    ],
}

# Minimum volume to consider (filter out dead markets)
MIN_VOLUME = 10

# Output file
DATA_DIR = Path(__file__).parent.parent / "data"
SCAN_FILE = DATA_DIR / "domain_knowledge_scans.jsonl"

# Kalshi fee rate for edge calculation
KALSHI_FEE_RATE = 0.07


# ── Data classes ──────────���────────────────���──────────────────────────────

@dataclass
class ScanResult:
    """One market scanned with LLM probability estimate."""
    timestamp: str
    market_ticker: str
    market_title: str
    event_ticker: str
    category: str
    kalshi_yes_cents: int
    kalshi_no_cents: int
    llm_probability: float  # 0.0 to 1.0 (YES probability)
    llm_confidence: str     # "high", "medium", "low"
    llm_reasoning: str
    edge_yes: float         # llm_prob - kalshi_yes_price (positive = buy YES)
    edge_no: float          # (1-llm_prob) - kalshi_no_price
    volume: int
    close_time: str


# ── LLM probability estimation ───────���────────────────────────────────────

def build_probability_prompt(market_title: str, yes_price: int, no_price: int) -> str:
    """Build the prompt for probability estimation.

    Deliberately does NOT show the Kalshi price to avoid anchoring bias.
    """
    return f"""You are a calibrated probability estimator. Given a prediction market question,
estimate the probability that the outcome resolves YES.

RULES:
- Give your probability as a decimal between 0.00 and 1.00
- Be calibrated: if you say 0.70, it should happen ~70% of the time
- Consider base rates, current evidence, and historical patterns
- If you're uncertain, say so — don't default to 0.50
- Your confidence level reflects how much information you have, not how certain the outcome is

MARKET QUESTION: {market_title}

Respond in this exact JSON format (no markdown, no backticks):
{{"probability": 0.XX, "confidence": "high/medium/low", "reasoning": "1-2 sentence explanation"}}"""


async def estimate_probability(
    anthropic_client,
    market_title: str,
    yes_price: int,
    no_price: int,
) -> Dict:
    """Ask Claude Haiku for a probability estimate on a market."""
    prompt = build_probability_prompt(market_title, yes_price, no_price)

    try:
        response = anthropic_client.messages.create(
            model=LLM_MODEL,
            max_tokens=LLM_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        text = response.content[0].text.strip()

        # Parse JSON response
        # Handle potential markdown wrapping
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(text)
        prob = float(result.get("probability", 0.5))
        # Clamp to valid range
        prob = max(0.01, min(0.99, prob))

        return {
            "probability": prob,
            "confidence": result.get("confidence", "medium"),
            "reasoning": result.get("reasoning", ""),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response for: %s", market_title)
        return {
            "probability": 0.5,
            "confidence": "low",
            "reasoning": f"Parse error: {text[:100]}",
            "input_tokens": 0,
            "output_tokens": 0,
        }
    except Exception as e:
        logger.error("LLM call failed for %s: %s", market_title, e)
        return {
            "probability": 0.5,
            "confidence": "low",
            "reasoning": f"Error: {str(e)[:100]}",
            "input_tokens": 0,
            "output_tokens": 0,
        }


# ���─ Market fetching ──���─────────────────────���─────────────────────────────

def categorize_market(title: str) -> Optional[str]:
    """Categorize a market by title keywords. Returns category or None."""
    title_lower = title.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in title_lower:
                return category
    return None


async def fetch_target_markets(
    client: KalshiClient,
    category_filter: Optional[str] = None,
) -> List[Market]:
    """Fetch open markets in target categories."""
    all_markets = []
    cursor = None
    page = 0

    while True:
        page += 1
        markets = await client.get_markets(status="open", limit=100, cursor=cursor)
        if not markets:
            break
        all_markets.extend(markets)
        # Pagination: check if we got a full page
        if len(markets) < 100:
            break
        # Use the last market's ticker as a cursor hint
        # (actual cursor handling depends on API response)
        cursor = None  # Kalshi pagination via cursor in response
        if page >= 20:  # Safety limit: 2000 markets max
            break

    # Filter by category
    filtered = []
    for m in all_markets:
        cat = categorize_market(m.title)
        if cat is None:
            continue
        if category_filter and cat != category_filter:
            continue
        if m.volume < MIN_VOLUME:
            continue
        # Skip extreme prices (not interesting for edge detection)
        if m.yes_price <= 3 or m.yes_price >= 97:
            continue
        filtered.append((m, cat))

    return filtered


# ── Edge calculation ─────────────────────────────────────────────────────

def calculate_edge(llm_prob: float, kalshi_price_cents: int) -> float:
    """Calculate edge: LLM probability minus Kalshi implied probability.

    Positive edge on YES side means LLM thinks YES is more likely than Kalshi price implies.
    Accounts for Kalshi taker fee.
    """
    kalshi_implied = kalshi_price_cents / 100.0
    fee = KALSHI_FEE_RATE * kalshi_implied * (1 - kalshi_implied)
    return llm_prob - kalshi_implied - fee


# ── Calibration analysis ─────────────���──────────────────────────────────

def analyze_calibration(scan_file: Path) -> None:
    """Analyze calibration of past LLM estimates vs resolved markets."""
    if not scan_file.exists():
        print("No scan data found.")
        return

    scans = []
    with open(scan_file) as f:
        for line in f:
            if line.strip():
                scans.append(json.loads(line))

    total = len(scans)
    print(f"\n=== Domain Knowledge Scanner Calibration ===")
    print(f"Total scans: {total}")

    if total == 0:
        return

    # Group by confidence level
    by_confidence = {}
    for s in scans:
        conf = s.get("llm_confidence", "unknown")
        by_confidence.setdefault(conf, []).append(s)

    print(f"\nBy confidence level:")
    for conf, items in sorted(by_confidence.items()):
        avg_prob = sum(i["llm_probability"] for i in items) / len(items)
        avg_edge_yes = sum(i["edge_yes"] for i in items) / len(items)
        print(f"  {conf}: {len(items)} scans, avg_prob={avg_prob:.2f}, avg_edge_yes={avg_edge_yes:+.2f}")

    # Group by category
    by_category = {}
    for s in scans:
        cat = s.get("category", "unknown")
        by_category.setdefault(cat, []).append(s)

    print(f"\nBy category:")
    for cat, items in sorted(by_category.items()):
        edges = [abs(i["edge_yes"]) for i in items]
        avg_edge = sum(edges) / len(edges)
        high_edge = sum(1 for e in edges if e > 0.10)
        print(f"  {cat}: {len(items)} scans, avg_abs_edge={avg_edge:.2f}, high_edge(>10%)={high_edge}")

    # Edge distribution
    all_edges = [s["edge_yes"] for s in scans]
    print(f"\nEdge distribution (YES side):")
    print(f"  Mean: {sum(all_edges)/len(all_edges):+.3f}")
    print(f"  >10% edge: {sum(1 for e in all_edges if e > 0.10)}")
    print(f"  >5% edge:  {sum(1 for e in all_edges if e > 0.05)}")
    print(f"  <-5% edge: {sum(1 for e in all_edges if e < -0.05)}")


# ── Main scan loop ───────────────��───────────────────────────────────────

async def run_scan(
    category_filter: Optional[str] = None,
    min_edge: float = 0.05,
    dry_run: bool = False,
) -> List[ScanResult]:
    """Run the full domain knowledge scan."""

    # Initialize Kalshi client
    from src.auth.kalshi_auth import load_from_env as load_kalshi_auth
    auth = load_kalshi_auth()
    client = KalshiClient(auth)
    await client.connect()

    # Initialize Anthropic client
    anthropic_client = None
    if not dry_run:
        try:
            from anthropic import Anthropic
            anthropic_client = Anthropic()
        except ImportError:
            print("Error: pip install anthropic")
            await client.close()
            return []
        except Exception as e:
            print(f"Error initializing Anthropic: {e}")
            await client.close()
            return []

    try:
        # Fetch markets
        print("Fetching open markets...")
        markets_with_cats = await fetch_target_markets(client, category_filter)
        print(f"Found {len(markets_with_cats)} markets in target categories")

        if not markets_with_cats:
            print("No markets found. Try a different category or check Kalshi API.")
            return []

        results: List[ScanResult] = []
        total_input_tokens = 0
        total_output_tokens = 0

        for i, (market, category) in enumerate(markets_with_cats):
            if dry_run:
                # Dry run: show markets without LLM calls
                print(f"  [{i+1}/{len(markets_with_cats)}] {market.ticker}: "
                      f"{market.title[:60]}... YES@{market.yes_price}c vol={market.volume}")
                continue

            # Rate limit: 1 call per second (Anthropic rate limit friendly)
            if i > 0:
                await asyncio.sleep(1.0)

            # Get LLM estimate
            est = await estimate_probability(
                anthropic_client, market.title, market.yes_price, market.no_price,
            )

            total_input_tokens += est.get("input_tokens", 0)
            total_output_tokens += est.get("output_tokens", 0)

            # Calculate edges
            edge_yes = calculate_edge(est["probability"], market.yes_price)
            edge_no = calculate_edge(1 - est["probability"], market.no_price)

            result = ScanResult(
                timestamp=datetime.now(timezone.utc).isoformat(),
                market_ticker=market.ticker,
                market_title=market.title,
                event_ticker=market.event_ticker,
                category=category,
                kalshi_yes_cents=market.yes_price,
                kalshi_no_cents=market.no_price,
                llm_probability=est["probability"],
                llm_confidence=est["confidence"],
                llm_reasoning=est["reasoning"],
                edge_yes=round(edge_yes, 4),
                edge_no=round(edge_no, 4),
                volume=market.volume,
                close_time=market.close_time,
            )
            results.append(result)

            # Print progress
            edge_str = f"{edge_yes:+.1%}" if abs(edge_yes) > abs(edge_no) else f"{edge_no:+.1%}(NO)"
            marker = " ***" if abs(edge_yes) > min_edge or abs(edge_no) > min_edge else ""
            print(
                f"  [{i+1}/{len(markets_with_cats)}] {market.ticker}: "
                f"Kalshi={market.yes_price}c LLM={est['probability']:.0%} "
                f"edge={edge_str} [{est['confidence']}]{marker}"
            )

        if dry_run:
            return []

        # Save results
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(SCAN_FILE, "a") as f:
            for r in results:
                f.write(json.dumps(asdict(r)) + "\n")

        # Summary
        print(f"\n=== Scan Complete ===")
        print(f"Markets scanned: {len(results)}")
        print(f"Tokens: {total_input_tokens:,} in + {total_output_tokens:,} out")

        # Show top edges
        by_edge = sorted(results, key=lambda r: abs(r.edge_yes), reverse=True)
        top = [r for r in by_edge if abs(r.edge_yes) > min_edge]
        if top:
            print(f"\nEdge opportunities (>{min_edge:.0%}):")
            for r in top[:10]:
                side = "YES" if r.edge_yes > 0 else "NO"
                edge = r.edge_yes if r.edge_yes > 0 else r.edge_no
                print(
                    f"  {r.market_ticker}: {r.market_title[:50]}..."
                    f" | {side}@{r.kalshi_yes_cents if side=='YES' else r.kalshi_no_cents}c"
                    f" edge={edge:+.1%} [{r.llm_confidence}]"
                )
        else:
            print(f"\nNo edges >{min_edge:.0%} found this scan.")

        return results

    finally:
        await client.close()


# ── CLI ───────��───────────────────────��──────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Domain Knowledge Scanner")
    parser.add_argument(
        "--category", choices=["politics", "economics", "geopolitics"],
        help="Scan only this category",
    )
    parser.add_argument(
        "--min-edge", type=float, default=0.05,
        help="Minimum edge to highlight (default: 0.05 = 5%%)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List markets without making LLM calls",
    )
    parser.add_argument(
        "--calibration", action="store_true",
        help="Show calibration analysis of past scans",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.calibration:
        analyze_calibration(SCAN_FILE)
        return

    results = asyncio.run(run_scan(
        category_filter=args.category,
        min_edge=args.min_edge,
        dry_run=args.dry_run,
    ))

    if results:
        print(f"\nResults appended to {SCAN_FILE}")
        print(f"Total scans in file: {sum(1 for _ in open(SCAN_FILE))}")


if __name__ == "__main__":
    main()
