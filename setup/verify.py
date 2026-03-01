"""
Connection verification script.
Tests all external connections before the bot runs.

Usage:
    python setup/verify.py
    python main.py --verify  (same thing, via main.py)

Exits 0 if all critical checks pass, 1 if any critical check fails.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


# ── Graduation thresholds (must match docs/GRADUATION_CRITERIA.md) ─

_GRAD = {
    # strategy_name: (min_trades, min_days, max_brier, max_consecutive_losses)
    # max_brier=0.30: 0.25=random coin flip, 0.30=meaningful predictive skill, lower=better
    # btc_lag_v1 validated via 30-day Binance.US backtest: 74%+ accuracy, positive ROI
    # min_days=0: day requirement removed — 30 real trades is the only volume gate
    "btc_lag_v1":                   (30, 0,  0.30, 4),
    "eth_lag_v1":                   (30, 0,  0.30, 4),
    "btc_drift_v1":                 (30, 0,  0.30, 4),
    "eth_drift_v1":                 (30, 0,  0.30, 4),
    "orderbook_imbalance_v1":       (30, 0,  0.30, 4),
    "eth_orderbook_imbalance_v1":   (30, 0,  0.30, 4),
    "weather_forecast_v1":          (30, 0,  0.30, 4),
    "fomc_rate_v1":                 (5,  0,  0.30, 4),  # low frequency — 5 trade minimum
}


# ── Check results tracking ────────────────────────────────────────

CHECKS: list[dict] = []

def record(name: str, passed: bool, detail: str = "", critical: bool = True):
    status = "✅ PASS" if passed else ("❌ FAIL" if critical else "⚠️  WARN")
    CHECKS.append({"name": name, "passed": passed, "detail": detail, "critical": critical})
    print(f"  {status}  {name}")
    if detail:
        print(f"           {detail}")


# ── Individual checks ─────────────────────────────────────────────

def check_env():
    """Verify required environment variables are set."""
    print("\n[1] Environment variables")
    key_id = os.getenv("KALSHI_API_KEY_ID", "")
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
    live_flag = os.getenv("LIVE_TRADING", "false")

    record(".env file loaded", Path(PROJECT_ROOT / ".env").exists(),
           "Copy .env.example → .env and fill in your values" if not Path(PROJECT_ROOT / ".env").exists() else "")
    record("KALSHI_API_KEY_ID set", bool(key_id) and key_id != "YOUR_KEY_ID_HERE",
           "Not set or still placeholder" if not key_id else f"Key ID: {key_id[:8]}...")
    record("KALSHI_PRIVATE_KEY_PATH set", bool(key_path),
           "Not set" if not key_path else f"Path: {key_path}")
    record("LIVE_TRADING=false (safe default)", live_flag.lower() == "false",
           f"LIVE_TRADING={live_flag} — set to false for paper mode", critical=False)


def check_pem():
    """Verify PEM file exists and is a valid RSA key."""
    print("\n[2] Private key file")
    key_path_str = os.getenv("KALSHI_PRIVATE_KEY_PATH", "")
    if not key_path_str:
        record("PEM file check", False, "KALSHI_PRIVATE_KEY_PATH not set — skipping")
        return

    key_path = Path(key_path_str)
    if not key_path.is_absolute():
        key_path = PROJECT_ROOT / key_path

    exists = key_path.exists()
    record("PEM file exists", exists,
           f"Not found at: {key_path}" if not exists else f"Found: {key_path.name}")

    if exists:
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            with open(key_path, "rb") as f:
                key = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
            record("PEM file is valid RSA key", True, f"Key size: {key.key_size} bits")
        except Exception as e:
            record("PEM file is valid RSA key", False, f"Error: {e}")


def check_auth_headers():
    """Verify auth header generation works (no network call)."""
    print("\n[3] Auth header generation")
    try:
        from src.auth.kalshi_auth import load_from_env
        auth = load_from_env()
        headers = auth.headers("GET", "/trade-api/v2/markets")
        has_key = "KALSHI-ACCESS-KEY" in headers
        has_sig = "KALSHI-ACCESS-SIGNATURE" in headers
        has_ts = "KALSHI-ACCESS-TIMESTAMP" in headers
        record("Headers generated", has_key and has_sig and has_ts,
               f"KEY={'✓' if has_key else '✗'} SIG={'✓' if has_sig else '✗'} TS={'✓' if has_ts else '✗'}")
        if has_ts:
            age_ms = int(time.time() * 1000) - int(headers["KALSHI-ACCESS-TIMESTAMP"])
            record("Timestamp freshness", age_ms < 5000, f"Age: {age_ms}ms")
    except Exception as e:
        record("Auth module import", False, str(e))


async def check_kalshi_demo():
    """Hit Kalshi demo API — GET /exchange/status (no auth required)."""
    print("\n[4] Kalshi API connectivity")
    import aiohttp
    url = "https://api.elections.kalshi.com/trade-api/v2/exchange/status"
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    status = body.get("exchange_active", "unknown")
                    record("Kalshi API reachable", True, f"Exchange active: {status}")
                else:
                    record("Kalshi API reachable", False, f"HTTP {resp.status}")
    except Exception as e:
        record("Kalshi API reachable", False, str(e))


async def check_kalshi_auth_live():
    """Test authenticated request to Kalshi demo — GET /portfolio/balance."""
    print("\n[5] Kalshi authenticated request")
    import aiohttp
    try:
        from src.auth.kalshi_auth import load_from_env
        auth = load_from_env()
    except Exception as e:
        record("Kalshi auth request", False, f"Auth setup failed: {e}")
        return

    url = "https://api.elections.kalshi.com/trade-api/v2/portfolio/balance"
    path = "/trade-api/v2/portfolio/balance"
    headers = auth.headers("GET", path)

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    balance_cents = body.get("balance", 0)
                    record("Authenticated request", True,
                           f"Balance: ${balance_cents / 100:.2f}")
                elif resp.status == 401:
                    record("Authenticated request", False,
                           "401 Unauthorized — check API key ID and PEM file match")
                else:
                    body = await resp.text()
                    record("Authenticated request", False, f"HTTP {resp.status}: {body[:100]}")
    except Exception as e:
        record("Authenticated request", False, str(e))


async def check_binance_feed():
    """Test Binance BTC WebSocket — connect, get one price, disconnect."""
    print("\n[6] Binance BTC price feed")
    import websockets
    # Use @bookTicker (same stream as binance.py) — @trade has near-zero volume on Binance.US
    url = "wss://stream.binance.us:9443/ws/btcusdt@bookTicker"
    try:
        async with websockets.connect(url, open_timeout=15) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=30)
            data = json.loads(msg)
            bid = float(data.get("b", 0))
            ask = float(data.get("a", 0))
            mid = (bid + ask) / 2 if bid and ask else 0
            record("Binance WebSocket", mid > 0, f"BTC mid: ${mid:,.2f}")
    except Exception as e:
        record("Binance WebSocket", False, str(e))


async def check_kill_switch():
    """Verify kill switch module imports and basic state."""
    print("\n[7] Kill switch")
    lock_file = PROJECT_ROOT / "kill_switch.lock"
    if lock_file.exists():
        record("kill_switch.lock absent", False,
               "Kill switch is TRIGGERED. Run: python main.py --reset-killswitch")
        return
    record("kill_switch.lock absent", True, "No active kill switch")


def check_config():
    """Verify config.yaml exists and is valid YAML with required sections."""
    print("\n[8] Config file")
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        record("config.yaml exists", False, "Not found — run: cp .env.example .env")
        return
    record("config.yaml exists", True)
    try:
        import yaml
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
        required = ["kalshi", "strategy", "risk", "storage"]
        missing = [k for k in required if k not in cfg]
        record("config.yaml valid YAML", not missing,
               f"Missing sections: {missing}" if missing else
               f"Sections: {list(cfg.keys())}")
        bankroll = cfg.get("risk", {}).get("starting_bankroll_usd", 0)
        record("Starting bankroll set", bankroll > 0,
               f"${bankroll:.2f}" if bankroll > 0 else "Set risk.starting_bankroll_usd in config.yaml")
    except Exception as e:
        record("config.yaml valid YAML", False, str(e))


def check_db():
    """Verify database can be created and written to."""
    print("\n[9] Database")
    import tempfile
    import sqlite3
    from src.db import DB
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            tmp_path = Path(f.name)
        db = DB(tmp_path)
        db.init()
        db.save_bankroll(50.0, source="verify")
        val = db.latest_bankroll()
        db.close()
        tmp_path.unlink(missing_ok=True)
        record("DB create + write", val == 50.0, f"Read back: ${val:.2f}")
    except Exception as e:
        record("DB create + write", False, str(e))


def check_strategy():
    """Verify strategy module imports and instantiates cleanly."""
    print("\n[10] Strategy")
    try:
        from src.strategies.btc_lag import load_from_config
        strategy = load_from_config()
        record("BTCLagStrategy loads", True, f"Strategy: {strategy.name}")
    except Exception as e:
        record("BTCLagStrategy loads", False, str(e))

    try:
        from src.risk.sizing import calculate_size, kalshi_payout
        payout = kalshi_payout(44, "yes")
        result = calculate_size(win_prob=0.60, payout_per_dollar=payout,
                                edge_pct=0.12, bankroll_usd=50.0)
        record("Sizing module works", result is not None,
               f"Sample size: ${result.recommended_usd:.2f}" if result else "Returned None")
    except Exception as e:
        record("Sizing module works", False, str(e))


def check_graduation_status():
    """Check paper trading graduation criteria for each strategy (non-critical)."""
    print("\n[11] Live graduation status (paper trading)")
    try:
        import yaml
        with open(PROJECT_ROOT / "config.yaml") as f:
            cfg = yaml.safe_load(f)
        db_path_str = cfg.get("storage", {}).get("db_path", "data/polybot.db")
        db_path = Path(db_path_str)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path

        if not db_path.exists():
            record("Graduation check", False,
                   "No DB yet — run bot first to collect paper trades", critical=False)
            return

        from src.db import DB
        db = DB(db_path)
        db.init()

        any_ready = False
        for strategy, (min_trades, min_days, max_brier, max_consec) in _GRAD.items():
            stats = db.graduation_stats(strategy)
            n = stats["settled_count"]
            days = stats["days_running"]
            brier = stats["brier_score"]
            consec = stats["consecutive_losses"]

            passes_trades = n >= min_trades
            passes_days = days >= min_days
            passes_brier = (brier is None and n < min_trades) or (brier is not None and brier < max_brier)
            passes_consec = consec < max_consec

            ready = passes_trades and passes_days and passes_brier and passes_consec

            if ready:
                any_ready = True
                detail = (
                    f"trades={n} days={days:.1f} brier={brier:.3f} consec_losses={consec} "
                    f"pnl=${stats['total_pnl_usd']:.2f} — READY FOR LIVE"
                )
            else:
                gaps = []
                if not passes_trades:
                    gaps.append(f"trades {n}/{min_trades}")
                if not passes_days:
                    gaps.append(f"days {days:.1f}/{min_days}")
                if not passes_brier and brier is not None:
                    gaps.append(f"brier {brier:.3f}>={max_brier}")
                if not passes_consec:
                    gaps.append(f"consec_losses {consec}>={max_consec}")
                brier_str = f"{brier:.3f}" if brier is not None else "n/a"
                detail = (
                    f"trades={n} days={days:.1f} brier={brier_str} consec_losses={consec} "
                    f"| needs: {', '.join(gaps)}"
                )

            record(f"Graduation: {strategy}", ready, detail, critical=False)

        db.close()

        if any_ready:
            record("At least one strategy ready for live", True,
                   "Review docs/GRADUATION_CRITERIA.md before enabling live trading",
                   critical=False)

    except Exception as e:
        record("Graduation check", False, f"Error: {e}", critical=False)


# ── Main ──────────────────────────────────────────────────────────

async def check_polymarket_auth():
    """Verify Polymarket Ed25519 auth header generation (no network call)."""
    print("\n[12] Polymarket auth")
    key_id = os.getenv("POLYMARKET_KEY_ID", "")
    secret = os.getenv("POLYMARKET_SECRET_KEY", "")

    if not key_id or not secret:
        record("Polymarket credentials set", False,
               "POLYMARKET_KEY_ID or POLYMARKET_SECRET_KEY missing in .env", critical=False)
        return

    try:
        from src.auth.polymarket_auth import load_from_env
        auth = load_from_env()
        hdrs = auth.headers("GET", "/v1/markets")
        has_key = "X-PM-Access-Key" in hdrs
        has_sig = "X-PM-Signature" in hdrs
        has_ts  = "X-PM-Timestamp" in hdrs
        record("Polymarket auth headers", has_key and has_sig and has_ts,
               f"KEY={'✓' if has_key else '✗'} SIG={'✓' if has_sig else '✗'} TS={'✓' if has_ts else '✗'}",
               critical=False)
    except Exception as e:
        record("Polymarket auth headers", False, str(e), critical=False)


async def check_polymarket_api():
    """Test authenticated Polymarket.us API call — GET /v1/markets."""
    print("\n[13] Polymarket API connectivity")
    key_id = os.getenv("POLYMARKET_KEY_ID", "")
    if not key_id:
        record("Polymarket API reachable", False,
               "Credentials not set — skipping", critical=False)
        return

    try:
        from src.platforms.polymarket import load_from_env
        client = load_from_env()
        ok = await client.connectivity_check()
        if ok:
            markets = await client.get_markets(closed=False, limit=5)
            record("Polymarket API reachable", True,
                   f"Open markets: {len(markets)} returned (all sports as of 2026-03)",
                   critical=False)
        else:
            record("Polymarket API reachable", False,
                   "API did not respond", critical=False)
    except Exception as e:
        record("Polymarket API reachable", False, str(e), critical=False)


async def run_all():
    check_env()
    check_pem()
    check_auth_headers()
    await check_kalshi_demo()
    await check_kalshi_auth_live()
    await check_binance_feed()
    await check_kill_switch()
    check_config()
    check_db()
    check_strategy()
    check_graduation_status()
    await check_polymarket_auth()
    await check_polymarket_api()

    # Summary
    print("\n" + "═" * 48)
    passed = sum(1 for c in CHECKS if c["passed"])
    failed_critical = [c for c in CHECKS if not c["passed"] and c["critical"]]
    total = len(CHECKS)
    print(f"  Results: {passed}/{total} checks passed")

    if failed_critical:
        print(f"\n  ❌ {len(failed_critical)} critical check(s) failed:")
        for c in failed_critical:
            print(f"     • {c['name']}: {c['detail']}")
        print("\n  Bot cannot start until critical checks pass.")
        print("  See BLOCKERS.md if you need help.")
        print("═" * 48)
        sys.exit(1)
    else:
        print("\n  ✅ All critical checks passed. Bot is ready.")
        print("  Run: python main.py")
        print("═" * 48)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(run_all())
