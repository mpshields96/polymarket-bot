"""
scripts/test_deribit_dvol.py — Validate Deribit DVOL API accessibility and output.

Purpose:
  1. Confirm Deribit DVOL API is reachable from US IP (no geo-block).
  2. Fetch current BTC DVOL.
  3. Print: DVOL, daily expected move %, hourly sigma.
  4. Cross-check with BTC spot from Binance.US for sanity.

RESEARCH/DIAGNOSTIC ONLY. No trading, no bot interaction.
Run: source venv/bin/activate && python scripts/test_deribit_dvol.py
"""

import sys
import math
import requests

# Deribit DVOL endpoint — BTC USD Volatility Index
# Public API, no authentication required
DERIBIT_DVOL_URL = "https://www.deribit.com/api/v2/public/get_volatility_index_data"
DERIBIT_INDEX_URL = "https://www.deribit.com/api/v2/public/get_index_price"

# Binance.US BTC spot (for sanity check)
BINANCE_US_SPOT_URL = "https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT"

TIMEOUT_SEC = 10


def fetch_deribit_dvol() -> float:
    """Fetch current BTC DVOL from Deribit public API.

    Returns the current DVOL value (annualized vol, e.g. 57.3 = 57.3%).
    Raises on any error.
    """
    # Primary endpoint: get_volatility_index_data for current value
    # We use get_index_price with index_name=btc_usdv to get current DVOL
    params = {"index_name": "btc_usdv"}
    response = requests.get(DERIBIT_INDEX_URL, params=params, timeout=TIMEOUT_SEC)
    response.raise_for_status()
    data = response.json()

    if "result" not in data:
        raise ValueError(f"Unexpected response: {data}")

    dvol = data["result"]["index_price"]
    return float(dvol)


def fetch_binance_spot() -> float:
    """Fetch current BTC spot from Binance.US."""
    response = requests.get(BINANCE_US_SPOT_URL, timeout=TIMEOUT_SEC)
    response.raise_for_status()
    data = response.json()
    return float(data["price"])


def dvol_to_daily_sigma(dvol: float) -> float:
    """DVOL (annualized %) → daily 1-sigma move (%)."""
    return dvol / math.sqrt(365)


def dvol_to_hourly_sigma(dvol: float) -> float:
    """DVOL (annualized %) → hourly 1-sigma move (%)."""
    return dvol / math.sqrt(8760)


def main() -> None:
    print("=" * 60)
    print("Deribit DVOL API Validation")
    print("=" * 60)

    # 1. Fetch DVOL
    print("\n[1] Fetching Deribit BTC DVOL...")
    try:
        dvol = fetch_deribit_dvol()
        print(f"    Status: OK (no geo-block from US IP)")
        print(f"    Current DVOL: {dvol:.1f}")
        print(f"    Daily expected move (1-sigma): {dvol_to_daily_sigma(dvol):.2f}%")
        print(f"    Hourly expected move (1-sigma): {dvol_to_hourly_sigma(dvol):.3f}%")
    except requests.exceptions.ConnectionError as e:
        print(f"    Status: CONNECTION ERROR — possible geo-block or network issue")
        print(f"    Error: {e}")
        print("\n    Trying fallback DVOL endpoint...")
        try:
            # Fallback: volatility index data endpoint
            params = {
                "currency": "BTC",
                "start_timestamp": 0,
                "end_timestamp": 9999999999999,
                "resolution": "1D",
            }
            resp = requests.get(DERIBIT_DVOL_URL, params=params, timeout=TIMEOUT_SEC)
            resp.raise_for_status()
            print(f"    Fallback endpoint reachable: {resp.status_code}")
        except Exception as e2:
            print(f"    Fallback also failed: {e2}")
            print("\nCONCLUSION: Deribit appears geo-blocked from this IP.")
            print("Alternative: use Binance.US options IV or hardcode sigma from DVOL.")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"    HTTP Error: {e}")
        if "451" in str(e) or "403" in str(e):
            print("    CONCLUSION: Deribit is geo-restricted from US IP.")
        sys.exit(1)
    except Exception as e:
        print(f"    Unexpected error: {type(e).__name__}: {e}")
        sys.exit(1)

    # 2. Fetch BTC spot for sanity check
    print("\n[2] Fetching BTC spot from Binance.US (sanity check)...")
    try:
        spot = fetch_binance_spot()
        print(f"    BTC spot: {spot:,.0f} USD")
    except Exception as e:
        print(f"    Failed to fetch spot (non-critical): {e}")
        spot = None

    # 3. Sample N(d2) calculations for common KXBTCD scenarios
    if spot is not None:
        print(f"\n[3] Sample KXBTCD fair values at BTC = {spot:,.0f}, DVOL = {dvol:.1f}:")
        print(f"    (Strike, Hours) → N(d2)")

        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            from src.strategies.crypto_daily_threshold import fair_prob_above_strike

            scenarios = [
                (spot * 0.97, 2.0, "3% OTM, 2hr"),
                (spot * 0.99, 2.0, "1% OTM, 2hr"),
                (spot, 2.0, "ATM, 2hr"),
                (spot * 1.01, 2.0, "1% ITM, 2hr"),
                (spot * 1.03, 2.0, "3% ITM, 2hr"),
                (spot * 0.99, 6.0, "1% OTM, 6hr"),
                (spot, 6.0, "ATM, 6hr"),
                (spot * 1.01, 6.0, "1% ITM, 6hr"),
            ]

            for strike, hours, label in scenarios:
                p = fair_prob_above_strike(spot=spot, strike=strike, hours_remaining=hours, dvol=dvol)
                print(f"    {label:20s} strike={strike:,.0f}  P(YES)={p:.3f} ({p*100:.1f}c)")
        except ImportError as e:
            print(f"    Could not import strategy module: {e}")

    # 4. Summary
    print("\n[4] Summary:")
    print(f"    Deribit DVOL API: ACCESSIBLE from US IP")
    print(f"    Current DVOL: {dvol:.1f} (annualized BTC implied vol)")
    print(f"    Daily 1-sigma: {dvol_to_daily_sigma(dvol):.2f}%")
    print(f"    Hourly 1-sigma: {dvol_to_hourly_sigma(dvol):.3f}%")
    print(f"    Note: DVOL converts directly to sigma for N(d2) calculation.")
    print(f"    Use in fair_prob_above_strike(spot, strike, hours, dvol={dvol:.1f})")
    print("\nDone.")


if __name__ == "__main__":
    main()
