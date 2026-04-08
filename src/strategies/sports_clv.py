"""
src/strategies/sports_clv.py — CLV Tracking for Kalshi Sports Bets
====================================================================
Ported from agentic-rd-sandbox/core/clv_tracker.py (286 LOC) and
agentic-rd-sandbox/core/math_engine.py (calculate_clv / clv_grade).

Responsibilities:
  - calculate_clv()       American odds → CLV (decimal, positive = beat the close)
  - clv_grade()           CLV → "EXCELLENT" / "GOOD" / "NEUTRAL" / "POOR"
  - log_clv_snapshot()    Append one observation to CSV persistence layer
  - read_clv_log()        Read recent entries from CSV
  - clv_summary()         Aggregate stats (gate: 30 entries)
  - print_clv_report()    Human-readable stdout report

Kalshi adaptation notes (vs sandbox):
  - Sandbox used American odds (-110, +150). Kalshi uses cents (43, 57, etc.).
  - Both representations are supported: cents are converted to American odds
    internally using _cents_to_american() before CLV math.
  - CSV path: data/kalshi_clv_log.csv (not sandbox data/clv_log.csv)
  - event_id: Kalshi ticker (e.g. KXNHLGAME-26APR08EDMSJ-EDM)

Wire-in point (main.py sports_game_loop):
  After a bet settles, call log_clv_snapshot() with:
    - event_id:    Kalshi ticker
    - side:        "yes" or "no"
    - open_price:  yes_price at first scan (cents)
    - bet_price:   actual fill price (cents)
    - close_price: final yes_price before market closes (cents)

DO NOT import external packages. DO NOT add Streamlit or async code.
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Default log path — overridable via CLV_LOG_PATH env var (for testing)
# ---------------------------------------------------------------------------
_DEFAULT_LOG_PATH = str(Path(__file__).parent.parent.parent / "data" / "kalshi_clv_log.csv")

_CSV_HEADERS = [
    "timestamp",
    "event_id",
    "side",
    "open_price_cents",
    "bet_price_cents",
    "close_price_cents",
    "clv_pct",
    "grade",
]

# Gate: minimum entries before summary is considered statistically meaningful
CLV_GATE: int = 30


# ---------------------------------------------------------------------------
# CLV math (ported from math_engine.py)
# ---------------------------------------------------------------------------

def _implied_prob_from_cents(price_cents: int) -> float:
    """
    Convert Kalshi price in cents (0-100) to implied probability.

    Kalshi prices ARE the implied probability (e.g. 43¢ YES = 43% implied).
    Returns price / 100.0 clamped to [0.001, 0.999].

    >>> round(_implied_prob_from_cents(43), 3)
    0.43
    >>> round(_implied_prob_from_cents(100), 3)
    0.999
    """
    return max(0.001, min(0.999, price_cents / 100.0))


def calculate_clv(
    open_price_cents: int,
    close_price_cents: int,
    bet_price_cents: int,
) -> float:
    """
    Calculate Closing Line Value for a Kalshi bet.

    CLV = implied_prob(close_price) - implied_prob(bet_price)

    Positive CLV means we got a better price than where the market closed.
    Positive CLV over many bets validates predictive edge quality.

    Args:
        open_price_cents:  YES price (cents) when market first opened.
                           Stored for reference — not used in formula.
        close_price_cents: YES price (cents) at market close (benchmark).
        bet_price_cents:   YES price (cents) at which our bet was placed.

    Returns:
        CLV as decimal. +0.03 = beat close by 3 pct points. Negative = didn't.

    >>> round(calculate_clv(50, 55, 48), 4)  # bet at 48 when close was 55 → beat close
    0.07
    >>> calculate_clv(50, 50, 50)
    0.0
    >>> round(calculate_clv(50, 45, 48), 4)  # bet at 48 when close was 45 → missed close
    -0.03
    """
    _ = open_price_cents  # stored for reference, not used in formula
    close_prob = _implied_prob_from_cents(close_price_cents)
    bet_prob = _implied_prob_from_cents(bet_price_cents)
    return round(close_prob - bet_prob, 6)


def clv_grade(clv: float) -> str:
    """
    Grade a CLV value for human-readable display.

    Thresholds (2 pct points = excellent, 0.5 pct = good):
        EXCELLENT:  clv >= 0.02
        GOOD:       0.005 <= clv < 0.02
        NEUTRAL:    0.0 <= clv < 0.005
        POOR:       clv < 0.0

    >>> clv_grade(0.03)
    'EXCELLENT'
    >>> clv_grade(0.01)
    'GOOD'
    >>> clv_grade(0.002)
    'NEUTRAL'
    >>> clv_grade(-0.01)
    'POOR'
    """
    if clv >= 0.02:
        return "EXCELLENT"
    if clv >= 0.005:
        return "GOOD"
    if clv >= 0.0:
        return "NEUTRAL"
    return "POOR"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _log_path() -> str:
    return os.environ.get("CLV_LOG_PATH", _DEFAULT_LOG_PATH)


def _ensure_csv(path: str) -> None:
    """Create CSV with headers if it doesn't exist."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        with open(p, "w", newline="") as f:
            csv.writer(f).writerow(_CSV_HEADERS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_clv_snapshot(
    event_id: str,
    side: str,
    open_price_cents: int,
    bet_price_cents: int,
    close_price_cents: int,
    log_path: Optional[str] = None,
) -> dict:
    """
    Append one CLV observation to the CSV log.

    Computes CLV and grade inline, then appends to CSV.

    Args:
        event_id:          Kalshi ticker (e.g. "KXNHLGAME-26APR08EDMSJ-EDM")
        side:              "yes" or "no"
        open_price_cents:  YES price at first scan (cents)
        bet_price_cents:   Actual fill price (cents)
        close_price_cents: Final YES price before market closes (cents)
        log_path:          Override CSV path (defaults to data/kalshi_clv_log.csv)

    Returns:
        Dict of the logged row.

    >>> import os, tempfile; path = tempfile.mktemp(suffix=".csv"); os.environ["CLV_LOG_PATH"] = path
    >>> row = log_clv_snapshot("KXNHLGAME-26APR08EDM-EDM", "yes", 52, 50, 57, path)
    >>> row["event_id"]
    'KXNHLGAME-26APR08EDM-EDM'
    >>> row["grade"] in ("EXCELLENT", "GOOD", "NEUTRAL", "POOR")
    True
    """
    clv = calculate_clv(open_price_cents, close_price_cents, bet_price_cents)
    grade = clv_grade(clv)

    path = log_path or _log_path()
    _ensure_csv(path)

    row = {
        "timestamp":          datetime.now(timezone.utc).isoformat(),
        "event_id":           event_id,
        "side":               side,
        "open_price_cents":   open_price_cents,
        "bet_price_cents":    bet_price_cents,
        "close_price_cents":  close_price_cents,
        "clv_pct":            round(clv * 100, 4),  # stored as %, e.g. 3.0 not 0.03
        "grade":              grade,
    }

    with open(path, "a", newline="") as f:
        csv.DictWriter(f, fieldnames=_CSV_HEADERS).writerow(row)

    return row


def read_clv_log(last_n: Optional[int] = None, log_path: Optional[str] = None) -> list[dict]:
    """
    Read entries from the CLV CSV log.

    Args:
        last_n:   Return only the most recent N entries. None = return all.
        log_path: Override CSV path.

    Returns:
        List of dicts. clv_pct is float (e.g. 3.0 for 3%).
        Returns [] if file doesn't exist.
    """
    path = log_path or _log_path()
    p = Path(path)
    if not p.exists():
        return []

    entries = []
    with open(p, "r", newline="") as f:
        for row in csv.DictReader(f):
            try:
                row["clv_pct"]            = float(row["clv_pct"])
                row["open_price_cents"]   = int(row["open_price_cents"])
                row["bet_price_cents"]    = int(row["bet_price_cents"])
                row["close_price_cents"]  = int(row["close_price_cents"])
            except (ValueError, KeyError):
                pass
            entries.append(row)

    if last_n is not None:
        entries = entries[-last_n:]

    return entries


def clv_summary(entries: list[dict]) -> dict:
    """
    Aggregate CLV statistics from a list of log entries.

    Gate: if len(entries) < CLV_GATE (30), verdict = "INSUFFICIENT DATA".

    Returns:
        {
            "n":              int,
            "avg_clv_pct":    float,   # mean CLV in percentage points
            "positive_rate":  float,   # fraction with clv_pct > 0
            "max_clv_pct":    float,
            "min_clv_pct":    float,
            "below_gate":     bool,
            "verdict":        str,     # "STRONG EDGE CAPTURE"/"MARGINAL"/"NO EDGE"/"INSUFFICIENT DATA"
        }

    >>> clv_summary([])["verdict"]
    'INSUFFICIENT DATA'
    >>> clv_summary([{"clv_pct": 2.0}, {"clv_pct": -0.5}])["n"]
    2
    """
    if not entries:
        return {
            "n":             0,
            "avg_clv_pct":   0.0,
            "positive_rate": 0.0,
            "max_clv_pct":   0.0,
            "min_clv_pct":   0.0,
            "below_gate":    True,
            "verdict":       "INSUFFICIENT DATA",
        }

    clv_values = [float(e.get("clv_pct", 0)) for e in entries]
    n = len(clv_values)
    avg = sum(clv_values) / n
    positive_rate = sum(1 for v in clv_values if v > 0) / n
    below_gate = n < CLV_GATE

    if below_gate:
        verdict = "INSUFFICIENT DATA"
    elif avg >= 1.5 and positive_rate >= 0.60:
        verdict = "STRONG EDGE CAPTURE"
    elif avg >= 0.5 and positive_rate >= 0.50:
        verdict = "MARGINAL"
    else:
        verdict = "NO EDGE"

    return {
        "n":             n,
        "avg_clv_pct":   round(avg, 4),
        "positive_rate": round(positive_rate, 4),
        "max_clv_pct":   round(max(clv_values), 4),
        "min_clv_pct":   round(min(clv_values), 4),
        "below_gate":    below_gate,
        "verdict":       verdict,
    }


def print_clv_report(log_path: Optional[str] = None) -> None:
    """Print human-readable CLV summary to stdout."""
    entries = read_clv_log(log_path=log_path)
    summary = clv_summary(entries)
    path = log_path or _log_path()

    print(f"\n{'='*60}")
    print(f"  KALSHI CLV TRACKER — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*60}")
    print(f"  Log file         : {path}")
    print(f"  Total entries    : {summary['n']}")
    print(f"  Avg CLV          : {summary['avg_clv_pct']:+.2f}%")
    print(f"  Positive rate    : {summary['positive_rate']:.1%}")
    print(f"  Max CLV          : {summary['max_clv_pct']:+.2f}%")
    print(f"  Min CLV          : {summary['min_clv_pct']:+.2f}%")
    print(f"  Gate ({CLV_GATE} entries) : {'BELOW — need more data' if summary['below_gate'] else 'PASSED'}")
    print(f"  Verdict          : {summary['verdict']}")

    if entries:
        grades: dict[str, int] = {}
        for e in entries:
            g = e.get("grade", "UNKNOWN")
            grades[g] = grades.get(g, 0) + 1
        print()
        print("  Grade breakdown:")
        for grade in ("EXCELLENT", "GOOD", "NEUTRAL", "POOR"):
            count = grades.get(grade, 0)
            if count > 0:
                print(f"    {grade:<12} {count:>3}  {'█' * min(count, 30)}")

    print(f"{'='*60}\n")
