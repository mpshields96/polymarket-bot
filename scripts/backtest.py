"""
scripts/backtest.py — Calibration backtest for btc_drift and btc_lag strategies.

Compresses ~30 days of BTC price history into a 2-3 minute run.
Replaces the need for 7 days of live paper trading for initial calibration.

DATA SOURCES:
  Binance.US REST API (no auth): 1-min BTCUSDT klines for the last N days.
  No Kalshi API calls — settlement is approximated from BTC price direction.

SETTLEMENT PROXY:
  KXBTC15M "YES" settles when BTC ends the 15-min window above the reference
  price (the BTC price at market open). This matches both strategies' logic.
  Note: actual Kalshi settlement may use a slightly different reference price;
  treat these results as directional calibration, not exact P&L simulation.

WHAT THIS TELLS YOU:
  - Signal coverage: what % of 15-min windows would trigger a signal
  - Directional accuracy: when the model predicted YES/NO, was it correct?
  - Brier score: probability calibration (0.25 = coin flip, lower = better)
  - Calibration table: are the model's confidence levels accurate?

USAGE:
  source venv/bin/activate && python scripts/backtest.py
  python scripts/backtest.py --days 60            (look back further)
  python scripts/backtest.py --sensitivity 800    (test different params)
  python scripts/backtest.py --strategy lag       (btc_lag only)
  python scripts/backtest.py --strategy both      (both strategies)
"""

from __future__ import annotations

import argparse
import asyncio
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Default parameters (match config.yaml) ────────────────────────────

_DEFAULT_DAYS = 30
_DEFAULT_SENSITIVITY = 800.0        # Calibrated from 30d backtest (was 300)
_DEFAULT_MIN_DRIFT_PCT = 0.05       # 0.05% drift from open required
_DEFAULT_TIME_WEIGHT = 0.7
_DEFAULT_MIN_MINUTES_REMAINING = 3.0
_WINDOW_MIN = 15                    # Kalshi 15-minute markets
_POLL_INTERVAL_MIN = 0.5            # Simulate 30s polling (0.5 min)

# btc_lag defaults (match config.yaml strategy.btc_lag)
_DEFAULT_LAG_MIN_BTC_MOVE_PCT = 0.4       # BTC must move this % in 60s
_DEFAULT_LAG_SENSITIVITY = 15.0           # Cents of implied Kalshi move per 1% BTC
_DEFAULT_LAG_MIN_EDGE_PCT = 0.08          # 8% edge minimum
_DEFAULT_LAG_ASSUMED_MARKET_PRICE = 50    # Assume neutral 50¢ (no Kalshi historical data)
_LAG_WINDOW_SECONDS = 60                  # 60s rolling window for BTC move detection

# Binance.US public REST (no auth required)
_KLINES_URL = "https://api.binance.us/api/v3/klines"
_SYMBOL = "BTCUSDT"
_INTERVAL = "1m"
_MAX_KLINES_PER_REQUEST = 1000      # Binance.US limit


# ── Probability model (mirrors src/strategies/btc_drift.py) ───────────

def _prob_yes(
    pct_from_open: float,
    time_remaining_frac: float,
    sensitivity: float,
    time_weight: float,
) -> float:
    """
    Sigmoid-based probability estimate, time-adjusted.
    Mirrors BTCDriftStrategy.generate_signal() math exactly.
    """
    raw_prob = 1.0 / (1.0 + math.exp(-sensitivity * pct_from_open))
    time_factor = max(0.0, min(1.0, 1.0 - time_remaining_frac))
    blend = 1.0 - time_weight + time_weight * time_factor
    prob = 0.5 + (raw_prob - 0.5) * blend
    return max(0.01, min(0.99, prob))


# ── Binance.US klines fetching ─────────────────────────────────────────

async def _fetch_klines_chunk(
    session: aiohttp.ClientSession,
    start_ms: int,
    end_ms: int,
) -> List[Tuple[int, float]]:
    """
    Fetch up to _MAX_KLINES_PER_REQUEST 1-min candles from Binance.US.

    Returns list of (open_time_ms, close_price) tuples.
    """
    params = {
        "symbol": _SYMBOL,
        "interval": _INTERVAL,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": _MAX_KLINES_PER_REQUEST,
    }
    async with session.get(_KLINES_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"Binance.US klines error {resp.status}: {text[:200]}")
        data = await resp.json()

    # data = [[open_time_ms, open, high, low, close, volume, close_time_ms, ...], ...]
    return [(int(row[0]), float(row[4])) for row in data]   # (open_time_ms, close_price)


async def fetch_all_klines(
    session: aiohttp.ClientSession,
    days: int,
    progress: bool = True,
) -> Dict[int, float]:
    """
    Fetch all 1-min candles for the last `days` days.

    Returns dict: {open_time_ms: close_price}
    Batches API calls to stay under the 1000-per-request limit.
    """
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - days * 24 * 60 * 60 * 1000

    all_candles: Dict[int, float] = {}
    current_ms = start_ms
    batch_ms = _MAX_KLINES_PER_REQUEST * 60 * 1000  # 1000 minutes per batch

    total_batches = math.ceil((now_ms - start_ms) / batch_ms)
    fetched = 0

    while current_ms < now_ms:
        end_ms = min(current_ms + batch_ms - 1, now_ms)
        chunk = await _fetch_klines_chunk(session, current_ms, end_ms)
        for ts, price in chunk:
            all_candles[ts] = price
        fetched += 1
        if progress:
            pct = fetched / total_batches * 100
            print(f"\r  Fetching BTC history: {pct:.0f}% ({fetched}/{total_batches} batches)", end="", flush=True)
        if chunk:
            current_ms = chunk[-1][0] + 60_000  # next minute
        else:
            break

    if progress:
        print()  # newline after progress bar

    return all_candles


def _price_at(candles: Dict[int, float], target_ms: int, tolerance_ms: int = 90_000) -> Optional[float]:
    """
    Return the candle close price at or near target_ms.
    Searches within ±tolerance_ms for the nearest candle.
    """
    # Try exact match first
    if target_ms in candles:
        return candles[target_ms]

    # Find nearest candle within tolerance
    best_diff = tolerance_ms + 1
    best_price: Optional[float] = None
    for ts, price in candles.items():
        diff = abs(ts - target_ms)
        if diff < best_diff:
            best_diff = diff
            best_price = price
    return best_price if best_diff <= tolerance_ms else None


# ── btc_lag fee helper (mirrors src/strategies/btc_lag.py) ────────────

def _lag_fee_pct(price_cents: int) -> float:
    p = price_cents / 100.0
    return 0.07 * p * (1.0 - p)


# ── btc_lag window simulation ─────────────────────────────────────────

def simulate_window_lag(
    candles: Dict[int, float],
    window_start_ms: int,
    min_btc_move_pct: float = _DEFAULT_LAG_MIN_BTC_MOVE_PCT,
    lag_sensitivity: float = _DEFAULT_LAG_SENSITIVITY,
    min_edge_pct: float = _DEFAULT_LAG_MIN_EDGE_PCT,
    assumed_market_price: int = _DEFAULT_LAG_ASSUMED_MARKET_PRICE,
    min_minutes_remaining: float = _DEFAULT_MIN_MINUTES_REMAINING,
) -> Optional[Dict]:
    """
    Simulate btc_lag on a single 15-min window.

    Logic: slide a 60-second window across the 15-min period (every 30s).
    When BTC moves more than min_btc_move_pct in those 60 seconds AND the
    implied Kalshi edge clears min_edge_pct, a signal fires.

    Limitation: We don't have actual Kalshi prices, so we assume the market
    is always at assumed_market_price (default 50¢). The real edge depends
    on whether Kalshi lagged the BTC move, which we can't measure in backtest.
    This tests: when BTC has a large 60s momentum move, does it continue
    through the end of the 15-min window?

    Returns result dict or None if no signal fired.
    """
    window_end_ms = window_start_ms + _WINDOW_MIN * 60 * 1000

    # Settlement: BTC above reference at window end?
    reference = _price_at(candles, window_start_ms)
    if reference is None or reference <= 0:
        return None
    final_price = _price_at(candles, window_end_ms)
    if final_price is None:
        return None
    outcome = 1 if final_price > reference else 0

    # Slide 60s window starting at T+1min (need 60s of price history)
    t_min = 1.0
    lag_window_min = _LAG_WINDOW_SECONDS / 60.0

    while t_min <= (_WINDOW_MIN - min_minutes_remaining):
        current_ms = window_start_ms + int(t_min * 60 * 1000)
        prev_ms = window_start_ms + int((t_min - lag_window_min) * 60 * 1000)

        current_price = _price_at(candles, current_ms)
        prev_price = _price_at(candles, prev_ms)

        if current_price is None or prev_price is None or prev_price <= 0:
            t_min += _POLL_INTERVAL_MIN
            continue

        btc_move_pct = (current_price - prev_price) / prev_price * 100  # e.g. 0.65

        # Gate 1: must meet minimum BTC move
        if abs(btc_move_pct) < min_btc_move_pct:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Gate 2: implied edge must clear floor
        implied_lag_cents = abs(btc_move_pct) * lag_sensitivity
        fee = _lag_fee_pct(assumed_market_price)
        edge_pct = (implied_lag_cents / 100.0) - fee

        if edge_pct < min_edge_pct:
            t_min += _POLL_INTERVAL_MIN
            continue

        # Signal: side follows momentum direction
        side = "yes" if btc_move_pct > 0 else "no"
        minutes_remaining = _WINDOW_MIN - t_min

        # win_prob mirrors btc_lag.py formula
        win_prob = min(0.85, (assumed_market_price / 100.0) + (implied_lag_cents / 100.0) * 0.8)

        return {
            "btc_move_pct": btc_move_pct,
            "side": side,
            "implied_lag_cents": implied_lag_cents,
            "edge_pct": edge_pct,
            "win_prob": win_prob,
            "prob_yes": win_prob if side == "yes" else 1.0 - win_prob,
            "minutes_remaining": minutes_remaining,
            "time_elapsed_min": t_min,
            "outcome": outcome,
        }

    return None


def print_report_lag(
    results: List[Dict],
    no_signal_count: int,
    total_windows: int,
    days: int,
    min_btc_move_pct: float,
    min_edge_pct: float,
):
    """Print btc_lag backtest results."""
    total_signals = len(results)
    if total_signals == 0:
        print("\n  ⚠️  No btc_lag signals fired.")
        print(f"  BTC needed to move >{min_btc_move_pct:.2f}% in 60s with edge>{min_edge_pct:.0%}")
        print(f"  At lag_sensitivity=15, need ~{(min_edge_pct + 0.0175) * 100 / 15:.2f}% BTC move to clear fee.")
        return

    wins = sum(1 for r in results if r["outcome"] == (1 if r["side"] == "yes" else 0))
    win_rate = wins / total_signals
    brier = _brier_score(results)
    coverage = total_signals / max(1, total_windows) * 100

    avg_move = sum(abs(r["btc_move_pct"]) for r in results) / total_signals
    avg_edge = sum(r["edge_pct"] for r in results) / total_signals

    width = 60
    print()
    print("=" * width)
    print(f"  BTC LAG STRATEGY — CALIBRATION BACKTEST")
    print(f"  Period: last {days} days | Min BTC move: {min_btc_move_pct:.2f}% in 60s")
    print(f"  Min edge: {min_edge_pct:.0%} | Lag sensitivity: {_DEFAULT_LAG_SENSITIVITY:.0f}")
    print(f"  Caveat: assumes Kalshi market always at 50¢ (no historical Kalshi prices)")
    print("=" * width)
    print()
    print(f"  15-min windows evaluated: {total_windows:,}")
    print(f"  Signals fired:            {total_signals:,}  ({coverage:.1f}% coverage)")
    print(f"  Windows with no signal:   {no_signal_count:,}")
    print()
    print(f"  Directional accuracy:     {win_rate:.1%}  ({'above' if win_rate > 0.5 else 'AT or below'} coin flip)")
    print(f"  Brier score:              {brier:.4f}  (0.25 = coin flip)")
    print(f"  Avg BTC move at signal:   ±{avg_move:.3f}%  in 60s")
    print(f"  Avg implied edge:         {avg_edge:.1%}  (before fill slippage)")
    print()
    print("  CALIBRATION TABLE:")
    print(_calibration_table(results))
    print()

    # Key insight about this strategy vs institutions
    if coverage < 5.0:
        freq_note = f"Signals fire {coverage:.1f}% of windows (~{int(total_signals/days)}/day)."
    else:
        freq_note = f"Signals fire {coverage:.1f}% of windows ({int(total_signals/days)}/day avg)."

    if win_rate >= 0.60 and brier < 0.22:
        rec = "✅ STRONG directional edge on momentum continuation."
    elif win_rate >= 0.54 and brier < 0.24:
        rec = "✅ GOOD — Thin edge exists. Collect live paper data before going live."
    elif win_rate >= 0.50:
        rec = "⚠️  MARGINAL — Slight momentum bias but may not survive fees."
    else:
        rec = "❌ NO EDGE — Momentum reversal dominates. Strategy needs rethink."

    print(f"  {freq_note}")
    print(f"  RECOMMENDATION: {rec}")
    print()
    print(f"  ⚠️  WARNING: Finance/BTC markets have 0.17pp maker-taker gap.")
    print(f"  Institutional HFTs (Susquehanna, Jump) price these markets in ms.")
    print(f"  Real fill prices may be significantly worse than this backtest assumes.")
    print("=" * width)
    print()


# ── btc_drift window simulation ────────────────────────────────────────

def simulate_window(
    candles: Dict[int, float],
    window_start_ms: int,
    sensitivity: float,
    time_weight: float,
    min_drift_pct: float,
    min_minutes_remaining: float,
) -> Optional[Dict]:
    """
    Simulate btc_drift on a single 15-min window.

    Returns a result dict with keys:
        prob_yes: float         Model's probability at first signal
        side: str               "yes" | "no" (predicted direction)
        drift_pct: float        BTC drift at signal time
        minutes_remaining: float
        time_elapsed_min: float Minutes elapsed when signal fired
        outcome: int            1 if YES won, 0 if NO won, None if no outcome
    Or None if no signal fired in this window.
    """
    window_end_ms = window_start_ms + _WINDOW_MIN * 60 * 1000

    # Reference price: BTC at market open
    reference = _price_at(candles, window_start_ms)
    if reference is None or reference <= 0:
        return None

    # Actual settlement: is final BTC price > reference?
    final_price = _price_at(candles, window_end_ms)
    if final_price is None:
        return None
    outcome = 1 if final_price > reference else 0

    # Simulate polling at 30s intervals starting at T+0.5min
    t_min = _POLL_INTERVAL_MIN
    while t_min <= (_WINDOW_MIN - min_minutes_remaining):
        current_ms = window_start_ms + int(t_min * 60 * 1000)
        current_price = _price_at(candles, current_ms)
        if current_price is None:
            t_min += _POLL_INTERVAL_MIN
            continue

        pct_from_open = (current_price - reference) / reference

        # Gate 1: must have minimum drift
        if abs(pct_from_open) < (min_drift_pct / 100.0):
            t_min += _POLL_INTERVAL_MIN
            continue

        # Gates passed — compute probability
        minutes_remaining = _WINDOW_MIN - t_min
        time_remaining_frac = minutes_remaining / _WINDOW_MIN

        prob = _prob_yes(pct_from_open, time_remaining_frac, sensitivity, time_weight)
        side = "yes" if pct_from_open > 0 else "no"

        return {
            "prob_yes": prob,
            "side": side,
            "drift_pct": pct_from_open * 100,
            "minutes_remaining": minutes_remaining,
            "time_elapsed_min": t_min,
            "outcome": outcome,
        }

    return None  # No signal in this window


# ── Report generation ─────────────────────────────────────────────────

def _brier_score(results: List[Dict]) -> float:
    """Brier Score = mean((prob_yes - outcome)^2). Lower is better; 0.25 = coin flip."""
    if not results:
        return 0.0
    return sum((r["prob_yes"] - r["outcome"]) ** 2 for r in results) / len(results)


def _calibration_table(results: List[Dict]) -> str:
    """
    Bucket predictions by probability and compare to actual win rate.
    A well-calibrated model has actual_win_rate ≈ predicted_prob.
    """
    buckets = {
        "0.50-0.55": (0.50, 0.55),
        "0.55-0.60": (0.55, 0.60),
        "0.60-0.65": (0.60, 0.65),
        "0.65-0.70": (0.65, 0.70),
        "0.70-0.75": (0.70, 0.75),
        "0.75-0.80": (0.75, 0.80),
        "0.80-0.90": (0.80, 0.90),
        "0.90+":     (0.90, 1.00),
    }

    lines = [
        f"  {'Pred P(win)':>12}  {'N signals':>9}  {'Actual win%':>11}  {'Calibrated?':>12}",
        "  " + "-" * 54,
    ]

    for label, (lo, hi) in buckets.items():
        # Count signals where the "winning" side had this prob range
        bucket_results = []
        for r in results:
            win_prob = r["prob_yes"] if r["side"] == "yes" else (1.0 - r["prob_yes"])
            if lo <= win_prob < hi:
                actual_won = 1 if r["outcome"] == (1 if r["side"] == "yes" else 0) else 0
                bucket_results.append(actual_won)

        if len(bucket_results) < 3:
            lines.append(f"  {label:>12}  {'<3 signals':>9}  {'—':>11}  {'':>12}")
            continue

        actual_pct = sum(bucket_results) / len(bucket_results) * 100
        mid_pred = (lo + hi) / 2 * 100
        diff = actual_pct - mid_pred
        calibrated = "✅ Good" if abs(diff) < 10 else ("📈 Overshoot" if diff < 0 else "📉 Undershoot")
        lines.append(
            f"  {label:>12}  {len(bucket_results):>9}  {actual_pct:>10.1f}%  {calibrated:>12}"
        )

    return "\n".join(lines)


def print_report(
    results: List[Dict],
    no_signal_count: int,
    total_windows: int,
    days: int,
    sensitivity: float,
    min_drift_pct: float,
):
    total_signals = len(results)
    if total_signals == 0:
        print("\n  ⚠️  No signals fired in the backtest period.")
        print(f"  Try reducing --min-drift-pct (current: {min_drift_pct:.2f}%)")
        return

    wins = sum(1 for r in results if r["outcome"] == (1 if r["side"] == "yes" else 0))
    win_rate = wins / total_signals
    brier = _brier_score(results)
    coverage = total_signals / max(1, total_windows) * 100

    avg_drift = sum(abs(r["drift_pct"]) for r in results) / total_signals
    avg_prob = sum(
        r["prob_yes"] if r["side"] == "yes" else 1.0 - r["prob_yes"]
        for r in results
    ) / total_signals

    width = 60
    print()
    print("=" * width)
    print(f"  BTC DRIFT STRATEGY — CALIBRATION BACKTEST")
    print(f"  Period: last {days} days | Sensitivity: {sensitivity:.0f}")
    print(f"  Min drift: {min_drift_pct:.2f}% from market open")
    print("=" * width)
    print()
    print(f"  15-min windows evaluated: {total_windows:,}")
    print(f"  Signals fired:            {total_signals:,}  ({coverage:.1f}% coverage)")
    print(f"  Windows with no signal:   {no_signal_count:,}")
    print()
    print(f"  Directional accuracy:     {win_rate:.1%}  ({'above' if win_rate > 0.5 else 'AT or below'} coin flip)")
    print(f"  Brier score:              {brier:.4f}  (0.25 = coin flip, lower = better)")
    print(f"  Avg win probability:      {avg_prob:.1%}  (model's confidence at signal time)")
    print(f"  Avg drift at signal:      ±{avg_drift:.3f}%  from market open")
    print()
    print("  CALIBRATION TABLE:")
    print("  (predicted P(win) vs actual win rate — good = within ±10%)")
    print(_calibration_table(results))
    print()

    # Recommendation
    if win_rate >= 0.60 and brier < 0.22:
        recommendation = "✅ STRONG — Model shows real directional edge. Enable paper mode confidently."
    elif win_rate >= 0.54 and brier < 0.24:
        recommendation = "✅ GOOD — Edge exists but thin. Collect more live paper data before going live."
    elif win_rate >= 0.50:
        recommendation = "⚠️  MARGINAL — Slight edge but may not survive fees. Do NOT go live yet."
    else:
        recommendation = "❌ NO EDGE — Model is wrong more than chance. Review sensitivity/drift settings."

    print(f"  RECOMMENDATION: {recommendation}")
    print()
    print(f"  At current settings (min_edge_pct=5%), a win rate > 55% is needed")
    print(f"  to be profitable after Kalshi fees (~1.75¢ per $1 at 50¢ market).")
    print("=" * width)
    print()


# ── Main ──────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser(
        description="Backtest btc_drift and btc_lag against historical BTC data"
    )
    parser.add_argument("--days", type=int, default=_DEFAULT_DAYS,
                        help=f"Days of history to analyze (default: {_DEFAULT_DAYS})")
    parser.add_argument("--sensitivity", type=float, default=None,
                        help=f"Sigmoid sensitivity for btc_drift (default: from config.yaml or {_DEFAULT_SENSITIVITY})")
    parser.add_argument("--min-drift-pct", type=float, default=None,
                        help=f"Minimum BTC drift %% to signal (default: from config.yaml or {_DEFAULT_MIN_DRIFT_PCT})")
    parser.add_argument("--strategy", choices=["drift", "lag", "both"], default="drift",
                        help="Which strategy to backtest (default: drift)")
    args = parser.parse_args()

    # Load config if available
    try:
        import yaml
        with open(PROJECT_ROOT / "config.yaml") as f:
            cfg = yaml.safe_load(f)
        drift_cfg = cfg.get("strategy", {}).get("btc_drift", {})
        lag_cfg = cfg.get("strategy", {}).get("btc_lag", {})
        sensitivity = args.sensitivity or drift_cfg.get("sensitivity", _DEFAULT_SENSITIVITY)
        min_drift_pct = args.min_drift_pct or drift_cfg.get("min_drift_pct", _DEFAULT_MIN_DRIFT_PCT)
        time_weight = drift_cfg.get("time_weight", _DEFAULT_TIME_WEIGHT)
        min_minutes_remaining = drift_cfg.get("min_minutes_remaining", _DEFAULT_MIN_MINUTES_REMAINING)
        lag_min_move = lag_cfg.get("min_btc_move_pct", _DEFAULT_LAG_MIN_BTC_MOVE_PCT)
        lag_sensitivity = lag_cfg.get("lag_sensitivity", _DEFAULT_LAG_SENSITIVITY)
        lag_min_edge = lag_cfg.get("min_edge_pct", _DEFAULT_LAG_MIN_EDGE_PCT)
    except Exception:
        sensitivity = args.sensitivity or _DEFAULT_SENSITIVITY
        min_drift_pct = args.min_drift_pct or _DEFAULT_MIN_DRIFT_PCT
        time_weight = _DEFAULT_TIME_WEIGHT
        min_minutes_remaining = _DEFAULT_MIN_MINUTES_REMAINING
        lag_min_move = _DEFAULT_LAG_MIN_BTC_MOVE_PCT
        lag_sensitivity = _DEFAULT_LAG_SENSITIVITY
        lag_min_edge = _DEFAULT_LAG_MIN_EDGE_PCT

    run_drift = args.strategy in ("drift", "both")
    run_lag = args.strategy in ("lag", "both")

    strategies_str = {"drift": "btc_drift", "lag": "btc_lag", "both": "btc_drift + btc_lag"}[args.strategy]
    print()
    print(f"  Backtesting {strategies_str} against {args.days} days of BTCUSDT history...")
    print(f"  Data source: Binance.US 1-min klines (public, no auth)")
    if run_drift:
        print(f"  [drift] sensitivity={sensitivity:.0f}, min_drift={min_drift_pct:.2f}%, time_weight={time_weight:.1f}")
    if run_lag:
        print(f"  [lag]   min_btc_move={lag_min_move:.2f}%, lag_sensitivity={lag_sensitivity:.0f}, min_edge={lag_min_edge:.0%}")
    print()

    # Fetch historical data
    async with aiohttp.ClientSession() as session:
        try:
            candles = await fetch_all_klines(session, days=args.days)
        except Exception as e:
            print(f"\n  ❌ Failed to fetch Binance.US klines: {e}")
            print("  Check your internet connection. Binance.US requires no auth.")
            sys.exit(1)

    print(f"  Fetched {len(candles):,} 1-min candles ({args.days} days)")

    # Align to 15-min window boundaries (UTC :00, :15, :30, :45)
    now_ms = max(candles.keys()) if candles else 0
    start_ms = min(candles.keys()) if candles else 0

    window_size_ms = _WINDOW_MIN * 60 * 1000
    aligned_start = ((start_ms // window_size_ms) + 1) * window_size_ms

    windows = []
    ws = aligned_start
    while ws + window_size_ms <= now_ms:
        windows.append(ws)
        ws += window_size_ms

    print(f"  Evaluating {len(windows):,} market windows ({_WINDOW_MIN}-min each)...")
    print()

    # Simulate each window
    drift_results: List[Dict] = []
    drift_no_signal = 0
    lag_results: List[Dict] = []
    lag_no_signal = 0

    for i, window_start in enumerate(windows):
        if run_drift:
            result = simulate_window(
                candles=candles,
                window_start_ms=window_start,
                sensitivity=sensitivity,
                time_weight=time_weight,
                min_drift_pct=min_drift_pct,
                min_minutes_remaining=min_minutes_remaining,
            )
            if result is not None:
                drift_results.append(result)
            else:
                drift_no_signal += 1

        if run_lag:
            result_lag = simulate_window_lag(
                candles=candles,
                window_start_ms=window_start,
                min_btc_move_pct=lag_min_move,
                lag_sensitivity=lag_sensitivity,
                min_edge_pct=lag_min_edge,
                min_minutes_remaining=_DEFAULT_MIN_MINUTES_REMAINING,
            )
            if result_lag is not None:
                lag_results.append(result_lag)
            else:
                lag_no_signal += 1

        if (i + 1) % 500 == 0:
            pct = (i + 1) / len(windows) * 100
            print(f"\r  Simulating: {pct:.0f}% ({i+1}/{len(windows)} windows)", end="", flush=True)

    print(f"\r  Simulating: 100% ({len(windows)}/{len(windows)} windows)     ")

    if run_drift:
        print_report(
            results=drift_results,
            no_signal_count=drift_no_signal,
            total_windows=len(windows),
            days=args.days,
            sensitivity=sensitivity,
            min_drift_pct=min_drift_pct,
        )

    if run_lag:
        print_report_lag(
            results=lag_results,
            no_signal_count=lag_no_signal,
            total_windows=len(windows),
            days=args.days,
            min_btc_move_pct=lag_min_move,
            min_edge_pct=lag_min_edge,
        )


if __name__ == "__main__":
    asyncio.run(main())
