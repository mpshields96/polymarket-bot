"""
Universal Bet Intelligence Framework — scripts/bet_analytics.py

Runs on every settled live bet across all strategies.
Observation only — flags patterns, never changes config.

Academic foundation (all citations verified by CCA, Session 45):
  SPRT:   Wald (1945) Annals of Mathematical Statistics 16(2), 117-186
          Wald & Wolfowitz (1948) AMS 19(3), 326-339
  Wilson: Wilson (1927) JASA 22(158), 209-212
          Brown, Cai & DasGupta (2001) Statistical Science 16(2), 101-133
  Brier:  Brier (1950) Monthly Weather Review 78(1), 1-3
          Murphy (1973) Journal of Applied Meteorology 12(4), 595-600
  CUSUM:  Page (1954) Biometrika 41(1/2), 100-115
  FLB:    Burgi, Deng & Whelan (2024) CESifo WP 12122 — Kalshi-specific
          Page & Clemen (2013) Economic Journal 123(568), 491-513

Usage:
    python3 scripts/bet_analytics.py
    python3 scripts/bet_analytics.py --strategy expiry_sniper_v1
    python3 scripts/bet_analytics.py --min-bets 20
"""

from __future__ import annotations

import argparse
import datetime
import math
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJ = Path(__file__).parent.parent
DB_PATH = PROJ / "data" / "polybot.db"

# ── Strategy config: p0 = no-edge baseline, p1 = claimed edge ─────────────────
# Sniper: p0 based on break-even at ~92c avg price (fee-adjusted ~90% BE)
# Drift:  p0 = 50% coin flip, p1 = modest edge claim
STRATEGY_CONFIG = {
    "expiry_sniper_v1": {"p0": 0.90, "p1": 0.97, "mu_0": 0.97, "mu_1": 0.90},
    "btc_drift_v1":     {"p0": 0.50, "p1": 0.58, "mu_0": 0.58, "mu_1": 0.50},
    "eth_drift_v1":     {"p0": 0.50, "p1": 0.58, "mu_0": 0.58, "mu_1": 0.50},
    "sol_drift_v1":     {"p0": 0.50, "p1": 0.62, "mu_0": 0.62, "mu_1": 0.50},
    "xrp_drift_v1":     {"p0": 0.50, "p1": 0.58, "mu_0": 0.58, "mu_1": 0.50},
}
DEFAULT_CONFIG = {"p0": 0.50, "p1": 0.58, "mu_0": 0.58, "mu_1": 0.50}
MIN_BETS_DEFAULT = 10


# ── Wilson Score CI (Wilson 1927, Brown/Cai/DasGupta 2001) ────────────────────

def wilson_ci(n: int, k: int, z: float = 1.96) -> tuple[float, float]:
    """
    Wilson score confidence interval for a binomial proportion.
    Returns (lower, upper) at the confidence level corresponding to z.
    More accurate than normal approximation, especially at extreme win rates.
    Wilson (1927) JASA 22(158), 209-212.
    """
    if n == 0:
        return (0.0, 1.0)
    p_hat = k / n
    z2 = z * z
    center = (p_hat + z2 / (2 * n)) / (1 + z2 / n)
    margin = z * math.sqrt(p_hat * (1 - p_hat) / n + z2 / (4 * n * n)) / (1 + z2 / n)
    return (max(0.0, center - margin), min(1.0, center + margin))


# ── SPRT (Wald 1945, Wald & Wolfowitz 1948) ───────────────────────────────────

@dataclass
class SPRTResult:
    verdict: str        # "edge_confirmed" | "no_edge" | "continue"
    lambda_val: float   # cumulative log-likelihood ratio
    upper_boundary: float
    lower_boundary: float
    n_bets: int


def run_sprt(outcomes: list[int], p0: float, p1: float,
             alpha: float = 0.05, beta: float = 0.10) -> SPRTResult:
    """
    Sequential Probability Ratio Test on a sequence of binary outcomes (1=win, 0=loss).
    Tests H0: true WR = p0 vs H1: true WR = p1.
    Wald (1945) Annals of Mathematical Statistics 16(2), 117-186.

    Returns verdict after processing all outcomes. Verdict freezes once a
    boundary is crossed — further bets do not reverse the decision.
    """
    log_a = math.log((1 - beta) / alpha)       # upper boundary ~2.890
    log_b = math.log(beta / (1 - alpha))       # lower boundary ~-2.251
    log_win  = math.log(p1 / p0)
    log_loss = math.log((1 - p1) / (1 - p0))

    lam = 0.0
    frozen_verdict = "continue"

    for outcome in outcomes:
        lam += log_win if outcome == 1 else log_loss
        if frozen_verdict == "continue":
            if lam >= log_a:
                frozen_verdict = "edge_confirmed"
            elif lam <= log_b:
                frozen_verdict = "no_edge"

    return SPRTResult(
        verdict=frozen_verdict,
        lambda_val=round(lam, 4),
        upper_boundary=round(log_a, 4),
        lower_boundary=round(log_b, 4),
        n_bets=len(outcomes),
    )


# ── Brier Score + Murphy Decomposition (Brier 1950, Murphy 1973) ──────────────

@dataclass
class BrierResult:
    score: float            # lower = better; 0 = perfect
    reliability: float      # lower = better; miscalibration
    resolution: float       # higher = better; spread from base rate
    uncertainty: float      # fixed by data; base rate variance
    n_bets: int


def brier_score(prices: list[float], outcomes: list[int],
                n_bins: int = 10) -> BrierResult:
    """
    Brier score with Murphy (1973) decomposition.
    prices: predicted probability (0.0-1.0), outcomes: 1=win, 0=loss.
    BS = REL - RES + UNC. Perfect calibration: REL = 0.
    Brier (1950) Monthly Weather Review 78(1), 1-3.
    Murphy (1973) Journal of Applied Meteorology 12(4), 595-600.
    """
    n = len(prices)
    if n == 0:
        return BrierResult(0.0, 0.0, 0.0, 0.0, 0)

    bs = sum((p - o) ** 2 for p, o in zip(prices, outcomes)) / n
    overall_wr = sum(outcomes) / n

    # Bin by predicted probability
    bin_size = 1.0 / n_bins
    bins: dict[int, list] = {i: [] for i in range(n_bins)}
    for p, o in zip(prices, outcomes):
        b = min(int(p / bin_size), n_bins - 1)
        bins[b].append((p, o))

    rel = 0.0
    res = 0.0
    for b_data in bins.values():
        if not b_data:
            continue
        n_k = len(b_data)
        mean_p = sum(x[0] for x in b_data) / n_k
        wr_k   = sum(x[1] for x in b_data) / n_k
        rel += n_k * (mean_p - wr_k) ** 2
        res += n_k * (wr_k - overall_wr) ** 2

    rel /= n
    res /= n
    unc = overall_wr * (1 - overall_wr)

    return BrierResult(
        score=round(bs, 4),
        reliability=round(rel, 4),
        resolution=round(res, 4),
        uncertainty=round(unc, 4),
        n_bets=n,
    )


# ── CUSUM Changepoint Detection (Page 1954) ───────────────────────────────────

@dataclass
class CUSUMResult:
    alert: bool
    statistic: float    # current S value; alert fires when S > h
    threshold: float    # h
    n_since_reset: int  # bets since last reset (how long current trend)


def run_cusum(outcomes: list[int], mu_0: float, mu_1: float,
              h: float = 5.0) -> CUSUMResult:
    """
    Page's CUSUM for detecting a downward shift from mu_0 to mu_1.
    Page (1954) Biometrika 41(1/2), 100-115.
    k = (mu_0 - mu_1) / 2  (allowance parameter)
    S_i = max(0, S_{i-1} + (mu_0 - x_i - k))
    Alert when S_i > h.
    """
    k = (mu_0 - mu_1) / 2
    s = 0.0
    n_since_reset = 0

    for outcome in outcomes:
        s = max(0.0, s + (mu_0 - outcome - k))
        if s == 0.0:
            n_since_reset = 0
        n_since_reset += 1

    return CUSUMResult(
        alert=s > h,
        statistic=round(s, 4),
        threshold=h,
        n_since_reset=n_since_reset,
    )


# ── Le (2026) Calibration Adjusted Edge ────────────────────────────────────────
# Le (2026) arXiv:2602.19520 — 292M trades across 327K Kalshi/Polymarket contracts.
# Recalibration formula: true_prob = p^b / (p^b + (1-p)^b)
# b = domain-specific calibration slope (>1 = favorites underpriced, <1 = overpriced)
# Verified by CCA Session 111. Full findings in .planning/EDGE_RESEARCH_S111.md.

# Domain calibration slopes from Le (2026):
CALIBRATION_B_CRYPTO  = 1.03   # crypto 15-min markets — near-perfect calibration
CALIBRATION_B_FINANCE = 1.10   # financial markets — slight favorite underpricing
CALIBRATION_B_POLITICS_LONG = 1.31  # politics 1+ week horizon — large mispricing
CALIBRATION_B_POLITICS_EXPIRY = 1.83  # politics near-expiry — MASSIVE mispricing
CALIBRATION_B_SPORTS_LONG = 1.74  # sports 1+ month — large mispricing
CALIBRATION_B_WEATHER = 0.75    # weather <48h — favorites OVERPRICED (avoid!)


def calibration_adjusted_edge(price: float, b: float) -> tuple[float, float]:
    """
    Compute true probability and edge in percentage points from market price
    using Le (2026) recalibration formula.

    Args:
        price: market price as fraction (0.0-1.0)
        b:     domain calibration slope (Le 2026 arXiv:2602.19520)

    Returns:
        (true_prob, edge_pp) where edge_pp is in percentage points
        Positive edge_pp = favorable (true prob > market price)
        Negative edge_pp = unfavorable (market is overpriced for favorites)

    Formula: true_prob = p^b / (p^b + (1-p)^b)
    When b=1.0: true_prob == price (perfectly calibrated, zero edge)
    When b>1.0: true_prob > price for p > 0.5 (favorites underpriced)
    When b<1.0: true_prob < price for p > 0.5 (favorites overpriced)
    """
    p = price
    pb = p ** b
    qb = (1 - p) ** b
    true_prob = pb / (pb + qb)
    edge_pp = (true_prob - p) * 100.0
    return (true_prob, edge_pp)


# ── Data loading ───────────────────────────────────────────────────────────────

def load_bets(db_path: Path, strategy: str | None = None) -> dict[str, list[dict]]:
    """Load all settled live bets, grouped by strategy."""
    conn = sqlite3.connect(str(db_path))
    q = """
        SELECT strategy, price_cents, side, result, pnl_cents, win_prob
        FROM trades
        WHERE is_paper = 0 AND result IS NOT NULL
    """
    params: list = []
    if strategy:
        q += " AND strategy = ?"
        params.append(strategy)
    q += " ORDER BY settled_at ASC"
    rows = conn.execute(q, params).fetchall()
    conn.close()

    grouped: dict[str, list[dict]] = {}
    for row in rows:
        strat = row[0]
        if strat not in grouped:
            grouped[strat] = []
        grouped[strat].append({
            "price_cents": row[1],
            "side": row[2],
            "result": row[3],
            "won": row[2] == row[3],
            "pnl_cents": row[4] or 0,
            "win_prob": float(row[5]) if row[5] is not None else None,
        })
    return grouped


# ── Report ─────────────────────────────────────────────────────────────────────

def analyze_strategy(name: str, bets: list[dict], min_bets: int = MIN_BETS_DEFAULT) -> None:
    """Run all four tests on one strategy and print results."""
    n = len(bets)
    k = sum(1 for b in bets if b["won"])
    pnl = sum(b["pnl_cents"] for b in bets) / 100
    outcomes = [1 if b["won"] else 0 for b in bets]
    prices = [b["price_cents"] / 100 for b in bets]

    cfg = STRATEGY_CONFIG.get(name, DEFAULT_CONFIG)
    p0, p1 = cfg["p0"], cfg["p1"]
    mu_0, mu_1 = cfg["mu_0"], cfg["mu_1"]

    wr = k / n if n else 0.0
    ci_lo, ci_hi = wilson_ci(n, k)

    print(f"\n{'─'*55}")
    print(f"  {name}")
    print(f"{'─'*55}")
    print(f"  Bets: {n}  |  WR: {wr*100:.1f}%  |  P&L: {pnl:+.2f} USD")
    print(f"  Wilson 95% CI: [{ci_lo*100:.1f}%, {ci_hi*100:.1f}%]")

    if n < min_bets:
        print(f"  Insufficient bets for SPRT/CUSUM (need {min_bets}, have {n})")
        return

    # SPRT — Wald 1945
    sprt = run_sprt(outcomes, p0, p1)
    verdict_label = {
        "edge_confirmed": "EDGE CONFIRMED",
        "no_edge":        "NO EDGE DETECTED",
        "continue":       "collecting data",
    }[sprt.verdict]
    print(f"  SPRT (Wald 1945):  {verdict_label}  "
          f"[lambda={sprt.lambda_val:+.3f}, bounds={sprt.lower_boundary:.3f}/{sprt.upper_boundary:.3f}]")

    # CUSUM — Page 1954
    cusum = run_cusum(outcomes, mu_0, mu_1)
    cusum_label = "DRIFT ALERT" if cusum.alert else "stable"
    print(f"  CUSUM (Page 1954): {cusum_label}  "
          f"[S={cusum.statistic:.3f}, threshold={cusum.threshold}]")

    # Brier Score — Brier 1950 / Murphy 1973
    brier = brier_score(prices, outcomes)
    # For drift strategies, use win_prob if available (model's predicted prob)
    win_probs = [b["win_prob"] for b in bets if b["win_prob"] is not None]
    if len(win_probs) >= min_bets:
        wp_outcomes = [1 if b["won"] else 0 for b in bets if b["win_prob"] is not None]
        brier = brier_score(win_probs, wp_outcomes)
        print(f"  Brier (1950):      {brier.score:.4f}  "
              f"[REL={brier.reliability:.4f} RES={brier.resolution:.4f}]  "
              f"(using model win_prob)")
    else:
        print(f"  Brier (1950):      {brier.score:.4f}  "
              f"[REL={brier.reliability:.4f} RES={brier.resolution:.4f}]  "
              f"(using purchase price)")

    # Flag if SPRT says no edge
    if sprt.verdict == "no_edge":
        print(f"  *** SPRT: strategy has statistically NO edge at p0={p0}, p1={p1} ***")
    if cusum.alert:
        print(f"  *** CUSUM: win rate has shifted downward — review recent bets ***")


def load_sniper_detail(db_path: Path) -> list[dict]:
    """Load sniper bets with ticker and timestamp for per-coin and monthly analysis."""
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        """
        SELECT ticker, price_cents, side, result, pnl_cents, settled_at
        FROM trades
        WHERE is_paper = 0 AND strategy = 'expiry_sniper_v1' AND result IS NOT NULL
        ORDER BY settled_at ASC
        """
    ).fetchall()
    conn.close()
    return [
        {
            "ticker": row[0],
            "price_cents": row[1],
            "side": row[2],
            "result": row[3],
            "won": row[2] == row[3],
            "pnl_cents": row[4] or 0,
            "settled_at": row[5],
        }
        for row in rows
    ]


# Coin prefix → display label
_COIN_PREFIXES = {
    "KXBTC": "BTC",
    "KXETH": "ETH",
    "KXSOL": "SOL",
    "KXXRP": "XRP",
}


def analyze_sniper_coins(bets: list[dict]) -> None:
    """Per-coin sniper breakdown — Wilson CI + SPRT per coin (S115)."""
    from collections import defaultdict

    coins: dict[str, list[dict]] = defaultdict(list)
    for b in bets:
        for prefix, label in _COIN_PREFIXES.items():
            if b["ticker"].startswith(prefix):
                coins[label].append(b)
                break

    if not coins:
        return

    print(f"\n{'─'*55}")
    print("  SNIPER PER-COIN BREAKDOWN (S115)")
    print(f"{'─'*55}")
    cfg = STRATEGY_CONFIG["expiry_sniper_v1"]
    p0, p1 = cfg["p0"], cfg["p1"]

    for label in ["BTC", "ETH", "SOL", "XRP"]:
        cbets = coins.get(label, [])
        n = len(cbets)
        if n == 0:
            print(f"  {label}: no bets")
            continue
        k = sum(1 for b in cbets if b["won"])
        pnl = sum(b["pnl_cents"] for b in cbets) / 100
        wr = k / n
        ci_lo, ci_hi = wilson_ci(n, k)
        print(
            f"  {label}: n={n} WR={wr*100:.1f}% CI=[{ci_lo*100:.1f}%,{ci_hi*100:.1f}%]"
            f" P&L={pnl:+.2f} USD"
        )
        if n >= MIN_BETS_DEFAULT:
            outcomes = [1 if b["won"] else 0 for b in cbets]
            sprt = run_sprt(outcomes, p0, p1)
            print(f"  SPRT lambda={sprt.lambda_val:+.3f} [{sprt.verdict}]")
            # Flag if lambda crossed the no-edge boundary
            # (frozen verdict may be stale if coin underperformed after initial confirmation)
            if sprt.lambda_val < -2.251:
                print(
                    f"  *** {label}: lambda crossed no-edge boundary (-2.251)"
                    f" — underperforms sniper edge claim ***"
                )


def analyze_sniper_monthly(bets: list[dict]) -> None:
    """Rolling monthly WR for FLB weakening detection (CCA S115 — Whelan VoxEU)."""
    from collections import defaultdict

    months: dict[str, list[int]] = defaultdict(list)  # key → [won, ...]
    month_pnl: dict[str, float] = defaultdict(float)
    for b in bets:
        if b["settled_at"] is None:
            continue
        dt = datetime.datetime.fromtimestamp(b["settled_at"], tz=datetime.timezone.utc)
        key = dt.strftime("%Y-%m")
        months[key].append(1 if b["won"] else 0)
        month_pnl[key] += b["pnl_cents"] / 100

    if not months:
        return

    print(f"\n{'─'*55}")
    print("  SNIPER MONTHLY WR — FLB weakening detection")
    print("  (Whelan VoxEU March 2026: some evidence of FLB weakening in 2025)")
    print(f"{'─'*55}")
    for m in sorted(months.keys()):
        outcomes = months[m]
        n = len(outcomes)
        k = sum(outcomes)
        wr = k / n
        ci_lo, ci_hi = wilson_ci(n, k)
        pnl = month_pnl[m]
        print(
            f"  {m}: n={n:4d} WR={wr*100:.1f}% CI=[{ci_lo*100:.1f}%,{ci_hi*100:.1f}%]"
            f" P&L={pnl:+.2f} USD"
        )
    if len(months) < 2:
        print("  (Only 1 month of data — trend detection requires 2+ months)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Universal bet analytics — SPRT, Wilson CI, Brier, CUSUM"
    )
    parser.add_argument("--db", default=str(DB_PATH))
    parser.add_argument("--strategy", default=None, help="Filter to one strategy")
    parser.add_argument("--min-bets", type=int, default=MIN_BETS_DEFAULT)
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"ERROR: DB not found: {db_path}", file=sys.stderr)
        return 1

    all_bets = load_bets(db_path, strategy=args.strategy)
    if not all_bets:
        print("No settled live bets found.")
        return 0

    print("=" * 55)
    print("  BET ANALYTICS — SPRT / Wilson CI / Brier / CUSUM")
    print("  Wald 1945 | Wilson 1927 | Brier 1950 | Page 1954")
    print("=" * 55)

    # Sniper first, then drift strategies by bet count
    order = ["expiry_sniper_v1", "sol_drift_v1", "btc_drift_v1",
             "xrp_drift_v1", "eth_drift_v1"]
    shown = set()
    for name in order:
        if name in all_bets:
            analyze_strategy(name, all_bets[name], args.min_bets)
            shown.add(name)
    for name, bets in all_bets.items():
        if name not in shown:
            analyze_strategy(name, bets, args.min_bets)

    # ── Per-coin sniper breakdown + monthly WR (S115) ─────────────────────────
    sniper_detail = load_sniper_detail(db_path)
    if sniper_detail:
        analyze_sniper_coins(sniper_detail)
        analyze_sniper_monthly(sniper_detail)

    # ── Le (2026) calibration analysis — sniper context ──────────────────────
    print(f"\n{'─'*55}")
    print("  CALIBRATION CONTEXT (Le 2026 arXiv:2602.19520)")
    print(f"{'─'*55}")
    print("  Domain calibration slopes (b) from 292M trades:")
    print()

    sniper_prices = [0.90, 0.92, 0.93, 0.94, 0.95]
    for p in sniper_prices:
        tp_crypto, edge_crypto = calibration_adjusted_edge(p, CALIBRATION_B_CRYPTO)
        tp_politics, edge_politics = calibration_adjusted_edge(p, CALIBRATION_B_POLITICS_EXPIRY)
        print(
            f"  {int(p*100)}c:  "
            f"crypto b=1.03 → true={tp_crypto*100:.1f}% (+{edge_crypto:.1f}pp)  |  "
            f"politics b=1.83 → true={tp_politics*100:.1f}% (+{edge_politics:.1f}pp)"
        )

    print()
    print("  Interpretation:")
    print("  Sniper edge at 90-95c is ~0.3-0.5pp from calibration alone.")
    print("  Observed 95.8% WR vs ~93% break-even = ~2.8pp gross edge.")
    print("  Sniper edge = structural FLB + liquidity premium, NOT calibration.")
    print("  Politics near-expiry: 8-10pp calibration edge vs sniper 0.3pp.")
    print("  (See .planning/EDGE_RESEARCH_S111.md for full Pillar 3 analysis)")
    print()

    print(f"\n{'─'*55}")
    print("  Observation only. No config changes made.")
    print(f"{'─'*55}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
