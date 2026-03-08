"""
Probe POST /v1/orders on polymarket.us to discover order body schema.

Purpose: POST /v1/orders format is the single remaining unknown blocking live
copy trading on polymarket.us. This script sends intentionally minimal/malformed
requests and reads the validation errors to discover the required fields and format.

This script NEVER places a real order. All requests are designed to fail validation
so we can read the error responses which name the required fields.

Run once: source venv/bin/activate && python scripts/probe_polymarket_orders.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

import requests
from dotenv import load_dotenv

# Load .env FIRST before any src imports
load_dotenv()

# Add project root to path so src/ imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.auth.polymarket_auth import load_from_env
from src.platforms.polymarket import PolymarketClient

_BASE_URL = "https://api.polymarket.us"
_API_PREFIX = "/v1"


def _print_separator(label: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")


def probe_a_empty_body(auth) -> None:
    """
    PROBE A — Empty body POST to /v1/orders.
    Expected: validation error naming required fields.
    """
    _print_separator("PROBE A — Empty body POST /v1/orders")

    path = "/v1/orders"
    headers = auth.headers("POST", path)
    url = f"{_BASE_URL}{path}"

    print(f"URL: {url}")
    print(f"Body: {{}}")
    print()

    try:
        resp = requests.post(url, headers=headers, json={}, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print(f"Response body:\n{resp.text}")
    except Exception as e:
        print(f"Request exception: {e}")


def probe_b_minimal_json(auth) -> None:
    """
    PROBE B — Minimal plausible JSON body POST to /v1/orders.
    Expected: field-name errors confirming JSON is accepted vs protobuf.
    """
    _print_separator("PROBE B — Minimal JSON body POST /v1/orders")

    path = "/v1/orders"
    headers = auth.headers("POST", path)
    url = f"{_BASE_URL}{path}"

    body = {
        "marketId": "probe-test",
        "side": "YES",
        "price": 0.5,
        "size": 1,
    }

    print(f"URL: {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print()

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print(f"Response body:\n{resp.text}")
    except Exception as e:
        print(f"Request exception: {e}")


def probe_b2_protobuf_style(auth) -> None:
    """
    PROBE B2 — Alternative field names more common in CLOB/Polymarket.
    Tests tokenId, side (BUY/SELL), feeRateBps, nonce, expiration pattern.
    """
    _print_separator("PROBE B2 — Alternative field names (tokenId, BUY/SELL style)")

    path = "/v1/orders"
    headers = auth.headers("POST", path)
    url = f"{_BASE_URL}{path}"

    body = {
        "tokenId": "probe-test-token",
        "side": "BUY",
        "price": "0.50",
        "size": "10.00",
        "orderType": "FOK",
    }

    print(f"URL: {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print()

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print(f"Response body:\n{resp.text}")
    except Exception as e:
        print(f"Request exception: {e}")


def probe_b3_buy_sell_style(auth) -> None:
    """
    PROBE B3 — BUY/SELL + identifier style (common in Polymarket.us sports markets).
    """
    _print_separator("PROBE B3 — BUY/SELL + identifier field names")

    path = "/v1/orders"
    headers = auth.headers("POST", path)
    url = f"{_BASE_URL}{path}"

    body = {
        "identifier": "probe-test-identifier",
        "action": "BUY",
        "price": 0.5,
        "amount": 1.0,
        "type": "FOK",
    }

    print(f"URL: {url}")
    print(f"Body: {json.dumps(body, indent=2)}")
    print()

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        print(f"HTTP Status: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print(f"Response body:\n{resp.text}")
    except Exception as e:
        print(f"Request exception: {e}")


async def probe_c_activities(auth) -> None:
    """
    PROBE C — GET /portfolio/activities to inspect past order field shapes.
    """
    _print_separator("PROBE C — GET /portfolio/activities (inspect past order shapes)")

    client = PolymarketClient(auth=auth)

    try:
        activities = await client.get_activities(limit=10)
        print(f"Number of activities returned: {len(activities)}")
        print()

        if not activities:
            print("No activities found in account.")
        else:
            for i, act in enumerate(activities, 1):
                print(f"--- Activity {i} ---")
                print(json.dumps(act, indent=2, default=str))
                print()
    except Exception as e:
        print(f"Activities request exception: {e}")


async def probe_c_positions(auth) -> None:
    """
    PROBE C2 — GET /portfolio/positions to see position shape for context.
    """
    _print_separator("PROBE C2 — GET /portfolio/positions (context)")

    client = PolymarketClient(auth=auth)

    try:
        positions = await client.get_positions()
        print(f"Positions response keys: {list(positions.keys())}")
        print()

        if positions:
            print(json.dumps(positions, indent=2, default=str))
        else:
            print("No positions data returned.")
    except Exception as e:
        print(f"Positions request exception: {e}")


async def main() -> None:
    print("=" * 60)
    print("  Polymarket.us POST /v1/orders Schema Probe")
    print("  Purpose: Discover order body format from validation errors")
    print("  NOTE: This script intentionally sends malformed requests.")
    print("        No real orders will be placed.")
    print("=" * 60)

    # Load auth credentials
    try:
        auth = load_from_env()
        print(f"\nAuth loaded: key_id={auth.key_id[:8]}...")
    except Exception as e:
        print(f"\nFATAL: Could not load Polymarket auth: {e}")
        print("Check POLYMARKET_KEY_ID and POLYMARKET_SECRET_KEY in .env")
        sys.exit(1)

    # Run synchronous probes (A, B, B2, B3)
    probe_a_empty_body(auth)
    probe_b_minimal_json(auth)
    probe_b2_protobuf_style(auth)
    probe_b3_buy_sell_style(auth)

    # Run async probes (C, C2)
    await probe_c_activities(auth)
    await probe_c_positions(auth)

    print("\n" + "=" * 60)
    print("  === PROBE COMPLETE ===")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
