"""
Guard retirement check — Dimension 5 of SELF_IMPROVEMENT_ROADMAP.md

JOB:    At session start, check whether any IL-guarded sniper buckets have
        accumulated enough post-guard paper data to qualify for retirement.
        A guard should be retired only when the bucket demonstrates it is no
        longer negative-EV — i.e., post-guard WR > break-even + safety margin,
        with statistical significance.

        "Post-guard" means: paper bets placed in a guarded bucket AFTER the guard
        was added. Since we don't store a guard-added timestamp in the DB, we use
        ALL paper bets in the bucket as an approximation (paper data predates the
        guard for many buckets, but the guard was added because the live WR was bad;
        any improvement in the paper series post-guard would show up here).

RUNS:   python3 scripts/guard_retirement_check.py
        Exit code 0 = no retirements flagged (normal), 1 = retirement recommended

RETIREMENT CRITERIA (all must be met):
    1. n_paper_bets >= MIN_BETS_FOR_RETIREMENT (50)
    2. win_rate >= break_even_wr + RETIREMENT_MARGIN (2pp safety buffer)
    3. One-sided binomial p-value < P_VALUE_THRESHOLD (0.05)
       H0: p = historical_wr (bucket is still bad)
       H1: p > historical_wr (bucket has recovered)

DOES NOT:
    - Modify live.py, main.py, or any production code
    - Remove guards automatically (human confirmation required)
    - Block or modify current bet execution

WHY HUMAN SIGN-OFF:
    Guard retirement is the reverse of guard addition: it returns a previously-blocked
    bucket to live trading. The statistical bar is deliberately higher than guard addition.
    A false positive (retiring a good guard) re-exposes us to a structural loss.
"""

from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"

# Gate thresholds
MIN_BETS_FOR_RETIREMENT = 50      # minimum post-guard paper bets
RETIREMENT_MARGIN = 0.02          # WR must exceed break_even by at least this
P_VALUE_THRESHOLD = 0.05          # one-sided binomial test significance level


# ── Break-even WR formula ─────────────────────────────────────────────────

def _break_even_wr(price_cents: int, side: str = "yes") -> float:
    """
    Compute break-even win rate for a sniper bet at price_cents.

    In Kalshi, price_cents is always the cost of the specific contract purchased:
      - YES@91c: you pay 91c, win 9c net of fee → break-even ≈ 91.6%
      - NO@91c: you pay 91c, win 9c net of fee → break-even ≈ 91.6%
    The break-even formula is identical regardless of YES or NO side.

    Kalshi taker fee = 7% of gross profit.
    break_even = cost / (cost + net_payout)
               = P / (P + (100-P) * (1 - 0.07))
    """
    if price_cents <= 0 or price_cents >= 100:
        return float("nan")

    fee_rate = 0.07
    gross_payout = 100 - price_cents       # cents won per contract before fee
    net_payout = gross_payout * (1.0 - fee_rate)
    break_even = price_cents / (price_cents + net_payout)
    return break_even


# ── Binomial one-sided p-value ────────────────────────────────────────────

def _binomial_pvalue(n: int, wins: int, p_null: float) -> float:
    """
    One-sided binomial p-value for H1: p > p_null.
    P(X >= wins | X ~ Binomial(n, p_null))

    Uses the exact binomial CDF (sum of PMF terms).
    Returns 1.0 if n == 0.
    """
    if n == 0:
        return 1.0

    # P(X >= wins) = 1 - P(X <= wins - 1)
    # P(X <= k) = sum_{i=0}^{k} C(n,i) * p^i * (1-p)^{n-i}
    cdf_below = 0.0
    log_p = math.log(p_null) if p_null > 0 else -1e300
    log_1mp = math.log(1.0 - p_null) if p_null < 1 else -1e300

    # Use log-space to avoid overflow for large n
    log_n_choose_0 = 0.0
    for i in range(wins):  # sum from 0 to wins-1
        # log C(n,i) computed iteratively
        if i == 0:
            log_c = 0.0
        else:
            log_c = log_c + math.log(n - i + 1) - math.log(i)
        log_pmf = log_c + i * log_p + (n - i) * log_1mp
        cdf_below += math.exp(log_pmf)

    p_value = 1.0 - cdf_below
    return max(0.0, min(1.0, p_value))


# ── Retirement candidate check ────────────────────────────────────────────

def _is_retirement_candidate(
    n: int,
    wins: int,
    break_even_wr: float,
    historical_wr: float,
) -> tuple[bool, str]:
    """
    Check whether a bucket passes all retirement gates.
    Returns (is_candidate, status_message).
    """
    if n == 0:
        return False, f"WARMING UP — 0 paper bets (need {MIN_BETS_FOR_RETIREMENT})"

    wr = wins / n
    threshold_wr = break_even_wr + RETIREMENT_MARGIN

    # Gate 1: minimum sample size
    if n < MIN_BETS_FOR_RETIREMENT:
        remaining = MIN_BETS_FOR_RETIREMENT - n
        return False, (
            f"WARMING UP — n={n}, WR={wr:.1%} "
            f"({remaining} more bets needed to evaluate)"
        )

    # Gate 2: WR above threshold
    if wr < threshold_wr:
        gap = threshold_wr - wr
        return False, (
            f"BELOW THRESHOLD — n={n}, WR={wr:.1%} "
            f"(need {threshold_wr:.1%}, gap={gap:.1%})"
        )

    # Gate 3: statistical significance (one-sided: H0 = bucket still bad)
    p_val = _binomial_pvalue(n=n, wins=wins, p_null=historical_wr)
    if p_val >= P_VALUE_THRESHOLD:
        return False, (
            f"BORDERLINE — n={n}, WR={wr:.1%} >= threshold {threshold_wr:.1%} "
            f"but p={p_val:.3f} >= {P_VALUE_THRESHOLD} — not yet significant"
        )

    return True, (
        f"READY FOR RETIREMENT — n={n}, WR={wr:.1%}, "
        f"threshold={threshold_wr:.1%}, p={p_val:.4f}"
    )


# ── Guard registry ────────────────────────────────────────────────────────
# Each entry mirrors the corresponding IL guard in src/execution/live.py.
# Fields:
#   guard_id:        IL-## identifier for cross-referencing live.py
#   ticker_contains: ticker prefix to match ("KXXRP", "KXBTC", etc.)
#   side:            "yes" or "no"
#   price_cents:     price in cents
#   historical_wr:   WR when guard was added (H0 for retirement test)
#   break_even_wr:   computed break-even WR at this price (use _break_even_wr())
#   n_at_guard:      sample size when guard was originally added
GUARD_REGISTRY: list[dict] = [
    {
        "guard_id": "IL-10A",
        "ticker_contains": "KXXRP",
        "side": "yes",
        "price_cents": 94,
        "historical_wr": 0.933,
        "break_even_wr": _break_even_wr(94, "yes"),
        "n_at_guard": 15,
        "notes": "XRP YES@94c — below fee-adjusted break-even",
    },
    {
        "guard_id": "IL-20",
        "ticker_contains": "KXXRP",
        "side": "yes",
        "price_cents": 95,
        "historical_wr": 0.900,
        "break_even_wr": _break_even_wr(95, "yes"),
        "n_at_guard": 10,
        "notes": "XRP YES@95c — BTC/ETH/SOL YES@95c remain profitable",
    },
    {
        "guard_id": "IL-10B",
        "ticker_contains": "KXXRP",
        "side": "yes",
        "price_cents": 97,
        "historical_wr": 0.833,
        "break_even_wr": _break_even_wr(97, "yes"),
        "n_at_guard": 6,
        "notes": "XRP YES@97c — above ceiling 95c, also below break-even",
    },
    {
        "guard_id": "IL-10C",
        "ticker_contains": "KXSOL",
        "side": "yes",
        "price_cents": 94,
        "historical_wr": 0.917,
        "break_even_wr": _break_even_wr(94, "yes"),
        "n_at_guard": 12,
        "notes": "SOL YES@94c — same structural notch as XRP",
    },
    {
        "guard_id": "IL-19",
        "ticker_contains": "KXSOL",
        "side": "yes",
        "price_cents": 97,
        "historical_wr": 0.875,
        "break_even_wr": _break_even_wr(97, "yes"),
        "n_at_guard": 8,
        "notes": "SOL YES@97c — above ceiling 95c, below break-even",
    },
    {
        "guard_id": "IL-21",
        "ticker_contains": "KXXRP",
        "side": "no",
        "price_cents": 92,
        "historical_wr": 0.750,
        "break_even_wr": _break_even_wr(92, "no"),
        "n_at_guard": 4,
        "notes": "XRP NO@92c — asymmetric payout, wins 1.40 USD, loses 19 USD",
    },
    {
        "guard_id": "IL-22",
        "ticker_contains": "KXSOL",
        "side": "no",
        "price_cents": 92,
        "historical_wr": 0.670,
        "break_even_wr": _break_even_wr(92, "no"),
        "n_at_guard": 3,
        "notes": "SOL NO@92c — same asymmetric pattern as IL-21",
    },
    {
        "guard_id": "IL-23",
        "ticker_contains": "KXXRP",
        "side": "yes",
        "price_cents": 98,
        "historical_wr": 0.909,
        "break_even_wr": _break_even_wr(98, "yes"),
        "n_at_guard": 11,
        "notes": "XRP YES@98c — above ceiling, EV negative due to fee math",
    },
    {
        "guard_id": "IL-24",
        "ticker_contains": "KXSOL",
        "side": "no",
        "price_cents": 95,
        "historical_wr": 0.938,
        "break_even_wr": _break_even_wr(95, "no"),
        "n_at_guard": 16,
        "notes": "SOL NO@95c — BTC/ETH/XRP NO@95c profitable, SOL below break-even",
    },
    {
        "guard_id": "IL-25",
        "ticker_contains": "KXXRP",
        "side": "no",
        "price_cents": 97,
        "historical_wr": 0.750,
        "break_even_wr": _break_even_wr(97, "no"),
        "n_at_guard": 4,
        "notes": "XRP NO@97c — high-price XRP NO = structurally negative EV",
    },
    {
        "guard_id": "IL-26",
        "ticker_contains": "KXXRP",
        "side": "no",
        "price_cents": 98,
        "historical_wr": 0.800,
        "break_even_wr": _break_even_wr(98, "no"),
        "n_at_guard": 5,
        "notes": "XRP NO@98c — mirrors XRP YES@98c (IL-23)",
    },
    {
        "guard_id": "IL-27",
        "ticker_contains": "KXSOL",
        "side": "yes",
        "price_cents": 96,
        "historical_wr": 0.670,
        "break_even_wr": _break_even_wr(96, "yes"),
        "n_at_guard": 3,
        "notes": "SOL YES@96c — above ceiling, extreme payout asymmetry",
    },
    {
        "guard_id": "IL-28",
        "ticker_contains": "KXXRP",
        "side": "no",
        "price_cents": 94,
        "historical_wr": 0.941,
        "break_even_wr": _break_even_wr(94, "no"),
        "n_at_guard": 17,
        "notes": "XRP NO@94c — fee-adjusted break-even ~94.4%, actual 94.1%",
    },
    {
        "guard_id": "IL-30",
        "ticker_contains": "KXETH",
        "side": "yes",
        "price_cents": 93,
        "historical_wr": 0.889,
        "break_even_wr": _break_even_wr(93, "yes"),
        "n_at_guard": 9,
        "notes": "ETH YES@93c — loss pocket, ETH YES@92c and 94c both fine",
    },
    {
        "guard_id": "IL-31",
        "ticker_contains": "KXXRP",
        "side": "no",
        "price_cents": 91,
        "historical_wr": 0.800,
        "break_even_wr": _break_even_wr(91, "no"),
        "n_at_guard": 5,
        "notes": "XRP NO@91c — correlated loss window with IL-30",
    },
    {
        "guard_id": "IL-32",
        "ticker_contains": "KXBTC",
        "side": "no",
        "price_cents": 91,
        "historical_wr": 0.857,
        "break_even_wr": _break_even_wr(91, "no"),
        "n_at_guard": 7,
        "notes": "BTC NO@91c — 85.7% WR vs 91% break-even",
    },
]


# ── Database query ────────────────────────────────────────────────────────

def _query_paper_bets(ticker_contains: str, side: str, price_cents: int) -> tuple[int, int]:
    """Query paper bets for a bucket. Returns (n, wins)."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            """
            SELECT COUNT(*), SUM(CASE WHEN side=result THEN 1 ELSE 0 END)
            FROM trades
            WHERE ticker LIKE ?
              AND side = ?
              AND price_cents = ?
              AND is_paper = 1
              AND result IS NOT NULL
              AND strategy = 'expiry_sniper_v1'
            """,
            (f"%{ticker_contains}%", side, price_cents),
        ).fetchone()
        conn.close()
        n = row[0] or 0
        wins = row[1] or 0
        return n, wins
    except Exception:
        return 0, 0


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 60)
    print("  GUARD RETIREMENT CHECK — Dim 5")
    print("=" * 60)

    retirement_candidates = []
    warming_up = []

    for guard in sorted(GUARD_REGISTRY, key=lambda g: g["guard_id"]):
        n, wins = _query_paper_bets(
            ticker_contains=guard["ticker_contains"],
            side=guard["side"],
            price_cents=guard["price_cents"],
        )
        wr = wins / n if n > 0 else 0.0
        is_candidate, status_msg = _is_retirement_candidate(
            n=n,
            wins=wins,
            break_even_wr=guard["break_even_wr"],
            historical_wr=guard["historical_wr"],
        )

        wr_str = f"{wr:.1%}" if n > 0 else "  n/a"
        print(
            f"  {guard['guard_id']:8s} "
            f"{guard['ticker_contains']:8s} {guard['side'].upper():4s}@{guard['price_cents']:2d}c "
            f"n={n:4d}  WR={wr_str}  "
            f"break-even={guard['break_even_wr']:.1%}"
        )
        print(f"           {status_msg}")

        if is_candidate:
            retirement_candidates.append(guard)
        else:
            warming_up.append(guard)

    print()
    print(f"  Summary: {len(retirement_candidates)} retirement candidate(s), "
          f"{len(warming_up)} warming up / not ready")
    print()

    if retirement_candidates:
        print("  RETIREMENT CANDIDATE(S) — HUMAN SIGN-OFF REQUIRED:")
        for g in retirement_candidates:
            print(f"    → {g['guard_id']}: {g['ticker_contains']} "
                  f"{g['side'].upper()}@{g['price_cents']}c — {g['notes']}")
        print()
        print("  ACTION REQUIRED:")
        print("  1. Review full historical data: python3 main.py --graduation-status")
        print("  2. Confirm WR is stable (not a lucky streak on small n)")
        print("  3. Remove the corresponding IL guard from src/execution/live.py")
        print("  4. Add comment documenting WHY the guard was retired")
        print("  5. Restart bot and monitor first 10 live bets in that bucket")
        print("=" * 60)
        return 1

    print("  No guards ready for retirement. Continue accumulating paper data.")
    print("  Run again when a bucket reaches 50+ paper bets.")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
