"""
Strategy Analyzer — Self-learning pattern detector.

Adapted from YoYo self-evolving agent architecture (CCA Session 12).
Queries the live DB, detects win/loss patterns, generates actionable insights,
and writes them to data/strategy_insights.json for session startup consumption.

JOB: Replace guesswork at session start with data-backed recommendations.

USAGE:
    python scripts/strategy_analyzer.py              # full analysis + save insights
    python scripts/strategy_analyzer.py --no-save    # print only, don't save
    python scripts/strategy_analyzer.py --brief      # 5-line summary (for session startup)

MINIMUM SAMPLE SIZES (safety gate — no insight generated with fewer bets):
    Sniper: 30 bets per bucket
    Drift: 20 bets per strategy
    Direction filter: 20 bets
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "polybot.db"
INSIGHTS_PATH = Path(__file__).parent.parent / "data" / "strategy_insights.json"
REFLECTION_PATH = Path(__file__).parent.parent / "data" / "session_reflection.md"

# Sniper quality benchmark thresholds
SNIPER_QUALITY_WIN_RATE = 0.95   # crypto sniper hits 95-99% WR
SNIPER_WATCH_WIN_RATE = 0.90     # worth monitoring
FUNDING_TARGET_USD = 125.0

# Minimum sample sizes before any insight is generated
MIN_SNIPER_BUCKET = 30
MIN_DRIFT_STRATEGY = 20
MIN_DIRECTION = 20

# ── Known active guards (mirrors live.py) ────────────────────────────────────
# Format: (price_cents, side, ticker_prefix)  OR  (price_cents, side, None) for all-asset guards
# Update this whenever a guard is added/removed in live.py.
# Purpose: prevent strategy_analyzer from flagging already-guarded paths as "Guard candidates".
_KNOWN_GUARDS: list[tuple] = [
    # Global price guards (all assets)
    (96, "yes", None),   # IL-10: 96c both sides
    (96, "no", None),    # IL-10: 96c both sides
    (97, "no", None),    # IL-10: 97c NO
    (98, "no", None),    # IL-11: 98c NO
    (99, "yes", None),   # IL-5: 99c/1c
    (99, "no", None),    # IL-5: 99c/1c
    # Per-asset guards
    (94, "yes", "KXXRP"),  # IL-10A: XRP YES@94c
    (95, "yes", "KXXRP"),  # IL-20: XRP YES@95c
    (97, "yes", "KXXRP"),  # IL-10B: XRP YES@97c
    (98, "yes", "KXXRP"),  # IL-23: XRP YES@98c
    (92, "no",  "KXXRP"),  # IL-21: XRP NO@92c
    (94, "yes", "KXSOL"),  # IL-10C: SOL YES@94c
    (97, "yes", "KXSOL"),  # IL-19: SOL YES@97c
    (92, "no",  "KXSOL"),  # IL-22: SOL NO@92c
    (95, "no",  "KXSOL"),  # IL-24: SOL NO@95c
    (97, "no",  "KXXRP"),  # IL-25: XRP NO@97c (also covered by global IL-10)
    (98, "no",  "KXXRP"),  # IL-26: XRP NO@98c (also covered by global IL-11)
    (96, "yes", "KXSOL"),  # IL-27: SOL YES@96c (also covered by global IL-10)
]


def _is_guarded(price_cents: int, side: str, ticker_prefix: str = "") -> bool:
    """Return True if this price/side/ticker combination is already guarded in live.py."""
    for gp, gs, gt in _KNOWN_GUARDS:
        if gp == price_cents and gs == side:
            if gt is None or (ticker_prefix and gt in ticker_prefix):
                return True
    return False


def _load_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ──────────────────────────────────────────────────────────
# SNIPER ANALYSIS
# ──────────────────────────────────────────────────────────

def analyze_sniper(conn: sqlite3.Connection) -> dict:
    """Per-bucket profitability for expiry_sniper_v1."""
    rows = conn.execute("""
        SELECT
            CASE
                WHEN price_cents <= 5  THEN '01-05'
                WHEN price_cents <= 10 THEN '06-10'
                WHEN price_cents <= 89 THEN '11-89'
                WHEN price_cents <= 94 THEN '90-94'
                WHEN price_cents  = 95 THEN '95'
                WHEN price_cents  = 96 THEN '96'
                WHEN price_cents  = 97 THEN '97'
                WHEN price_cents  = 98 THEN '98'
                WHEN price_cents >= 99 THEN '99+'
            END as bucket,
            COUNT(*) as bets,
            SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd,
            ROUND(AVG(ABS(pnl_cents)) / 100.0, 3) as avg_abs_pnl
        FROM trades
        WHERE strategy='expiry_sniper_v1'
          AND is_paper=0
          AND result IS NOT NULL
        GROUP BY bucket
        ORDER BY bucket DESC
    """).fetchall()

    buckets = {}
    insights = []
    for r in rows:
        bk = r["bucket"]
        bets = r["bets"]
        wins = r["wins"]
        pnl = r["pnl_usd"]
        wr = wins / bets if bets else 0.0
        buckets[bk] = {
            "bets": bets,
            "win_rate": round(wr, 4),
            "pnl_usd": pnl,
            "avg_abs_pnl": r["avg_abs_pnl"],
        }
        if bets >= MIN_SNIPER_BUCKET:
            status = "PROFITABLE" if pnl > 0 else "LOSING"
            insights.append({
                "bucket": bk,
                "status": status,
                "bets": bets,
                "win_rate": round(wr, 4),
                "pnl_usd": pnl,
                "recommendation": (
                    f"Bucket {bk}c: {status} ({bets} bets, {wr:.0%} WR, {pnl:+.2f} USD)"
                ),
            })

    # Time-of-day analysis
    tod_rows = conn.execute("""
        SELECT
            CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as hour,
            COUNT(*) as bets,
            SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
        FROM trades
        WHERE strategy='expiry_sniper_v1'
          AND is_paper=0
          AND result IS NOT NULL
        GROUP BY hour
        ORDER BY pnl_usd DESC
    """).fetchall()

    worst_hours = [
        {"hour": r["hour"], "pnl_usd": r["pnl_usd"], "bets": r["bets"]}
        for r in tod_rows
        if r["pnl_usd"] < 0 and r["bets"] >= 10
    ]

    best_hours = [
        {"hour": r["hour"], "pnl_usd": r["pnl_usd"], "bets": r["bets"]}
        for r in tod_rows
        if r["pnl_usd"] > 0 and r["bets"] >= 10
    ][:5]

    return {
        "buckets": buckets,
        "insights": insights,
        "time_of_day": {
            "best_hours": best_hours,
            "worst_hours": worst_hours,
        },
    }


def detect_guard_gaps(conn: sqlite3.Connection, min_bets: int = 5) -> list[dict]:
    """
    Find unguarded price/side/ticker combos with negative EV (WR below break-even price).

    Only surfaces paths NOT already in _KNOWN_GUARDS.
    Uses last 30 days of data to focus on current market conditions.
    Returns list of guard gap candidates with stats.
    """
    thirty_days_ago = time.time() - 30 * 24 * 3600
    rows = conn.execute("""
        SELECT
            price_cents,
            side,
            substr(ticker, 1, 5) as series,
            COUNT(*) as bets,
            SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
        FROM trades
        WHERE strategy='expiry_sniper_v1'
          AND is_paper=0
          AND result IS NOT NULL
          AND created_at > ?
        GROUP BY price_cents, side, series
        HAVING bets >= ?
        ORDER BY pnl_usd ASC
    """, (thirty_days_ago, min_bets)).fetchall()

    gaps = []
    for r in rows:
        price = r["price_cents"]
        side = r["side"]
        series = r["series"]
        bets = r["bets"]
        wins = r["wins"]
        pnl = r["pnl_usd"]
        wr = wins / bets if bets else 0.0

        # WR needed to break even at this price (YES-equivalent)
        yes_equiv = price if side == "yes" else (100 - price)
        be_wr = yes_equiv / 100.0

        # Skip if already guarded
        if _is_guarded(price, side, series):
            continue

        # Only flag if below break-even WR and net negative P&L
        if wr < be_wr and pnl < 0:
            gaps.append({
                "price_cents": price,
                "side": side,
                "series": series,
                "bets": bets,
                "win_rate": round(wr, 4),
                "break_even_wr": round(be_wr, 4),
                "pnl_usd": pnl,
                "shortfall_pct": round((be_wr - wr) * 100, 1),
            })

    return gaps


# ──────────────────────────────────────────────────────────
# DRIFT ANALYSIS
# ──────────────────────────────────────────────────────────

def analyze_drift(conn: sqlite3.Connection) -> dict:
    """Win rate, direction filter, and trend for all drift strategies."""
    drift_strategies = [
        "btc_drift_v1", "eth_drift_v1", "sol_drift_v1", "xrp_drift_v1"
    ]
    results = {}

    for strat in drift_strategies:
        # Overall stats
        overall = conn.execute("""
            SELECT
                COUNT(*) as bets,
                SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
                ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd,
                ROUND(
                    1.0 - (SUM(pnl_cents * pnl_cents) * 1.0) /
                    (COUNT(*) * 10000.0), 4
                ) as brier_approx
            FROM trades
            WHERE strategy=?
              AND is_paper=0
              AND result IS NOT NULL
        """, (strat,)).fetchone()

        bets = overall["bets"]
        if bets == 0:
            results[strat] = {"status": "NO_DATA"}
            continue

        wins = overall["wins"]
        wr = wins / bets

        # Direction breakdown (yes vs no bets)
        dir_rows = conn.execute("""
            SELECT side,
                   COUNT(*) as bets,
                   SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
                   ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
            FROM trades
            WHERE strategy=?
              AND is_paper=0
              AND result IS NOT NULL
            GROUP BY side
        """, (strat,)).fetchall()

        direction = {}
        for r in dir_rows:
            direction[r["side"]] = {
                "bets": r["bets"],
                "win_rate": round(r["wins"] / r["bets"], 4) if r["bets"] else 0,
                "pnl_usd": r["pnl_usd"],
            }

        # Recent trend (last 20 bets)
        recent = conn.execute("""
            SELECT
                COUNT(*) as bets,
                SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
                ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
            FROM (
                SELECT * FROM trades
                WHERE strategy=?
                  AND is_paper=0
                  AND result IS NOT NULL
                ORDER BY settled_at DESC
                LIMIT 20
            )
        """, (strat,)).fetchone()

        recent_wr = (recent["wins"] / recent["bets"]) if recent["bets"] else 0
        trend = "IMPROVING" if recent_wr > wr and recent["bets"] >= 10 else (
            "DECLINING" if recent_wr < wr - 0.05 and recent["bets"] >= 10 else "STABLE"
        )

        # Insight generation
        insight = None
        if bets >= MIN_DRIFT_STRATEGY:
            if wr >= 0.55:
                insight = f"{strat}: HEALTHY — {bets} live bets, {wr:.0%} WR, {overall['pnl_usd']:+.2f} USD"
            elif wr < 0.50:
                insight = f"{strat}: UNDERPERFORMING — {wr:.0%} WR below 50c break-even. Trend={trend}"
            else:
                insight = f"{strat}: NEUTRAL — {bets} live bets, {wr:.0%} WR, {overall['pnl_usd']:+.2f} USD"

            # Direction filter insight
            if bets >= MIN_DIRECTION:
                yes_d = direction.get("yes", {})
                no_d = direction.get("no", {})
                yes_wr = yes_d.get("win_rate", 0)
                no_wr = no_d.get("win_rate", 0)
                yes_bets = yes_d.get("bets", 0)
                no_bets = no_d.get("bets", 0)
                if yes_bets >= MIN_DIRECTION and no_bets >= MIN_DIRECTION:
                    spread = abs(yes_wr - no_wr)
                    if spread >= 0.10:
                        better = "yes" if yes_wr > no_wr else "no"
                        insight += f" [DIRECTION: filter to '{better}' side — {spread:.0%} spread]"

        results[strat] = {
            "bets": bets,
            "win_rate": round(wr, 4),
            "pnl_usd": overall["pnl_usd"],
            "direction": direction,
            "recent_trend": trend,
            "recent_bets": recent["bets"],
            "recent_win_rate": round(recent_wr, 4),
            "recent_pnl_usd": recent["pnl_usd"],
            "insight": insight,
        }

    return results


# ──────────────────────────────────────────────────────────
# STRATEGY GRADUATION STATUS
# ──────────────────────────────────────────────────────────

def graduation_status(conn: sqlite3.Connection) -> dict:
    """Check if any strategy is approaching graduation threshold (30 live bets)."""
    strategies = [
        "btc_drift_v1", "eth_drift_v1", "sol_drift_v1", "xrp_drift_v1",
        "eth_orderbook_imbalance_v1",
    ]
    status = {}
    for strat in strategies:
        row = conn.execute("""
            SELECT COUNT(*) as bets
            FROM trades
            WHERE strategy=? AND is_paper=0 AND result IS NOT NULL
        """, (strat,)).fetchone()
        bets = row["bets"]
        pct = min(1.0, bets / 30.0)
        status[strat] = {
            "live_bets": bets,
            "graduation_pct": round(pct * 100, 1),
            "needs": max(0, 30 - bets),
            "ready": bets >= 30,
        }
    return status


# ──────────────────────────────────────────────────────────
# OVERALL SUMMARY
# ──────────────────────────────────────────────────────────

def overall_summary(conn: sqlite3.Connection) -> dict:
    """All-time and recent P&L summary."""
    row = conn.execute("""
        SELECT
            COUNT(*) as bets,
            SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
        FROM trades
        WHERE is_paper=0 AND result IS NOT NULL
    """).fetchone()

    # Use midnight UTC explicitly (time.mktime() interprets as local time → wrong TZ offset)
    today_ts = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp()
    today = conn.execute("""
        SELECT
            COUNT(*) as bets,
            SUM(CASE WHEN side=result THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(pnl_cents) / 100.0, 2) as pnl_usd
        FROM trades
        WHERE is_paper=0 AND result IS NOT NULL AND settled_at >= ?
    """, (today_ts,)).fetchone()

    return {
        "all_time": {
            "bets": row["bets"] or 0,
            "win_rate": round(row["wins"] / row["bets"], 4) if row["bets"] else 0,
            "pnl_usd": row["pnl_usd"] or 0.0,
        },
        "today": {
            "bets": today["bets"] or 0,
            "win_rate": round(today["wins"] / today["bets"], 4) if today["bets"] else 0,
            "pnl_usd": today["pnl_usd"] or 0.0,
        },
        "target_usd": 125.0,
        "remaining_usd": round(125.0 - (row["pnl_usd"] or 0), 2),  # remaining = target - current_pnl
    }


# ──────────────────────────────────────────────────────────
# SNIPER QUALITY BENCHMARK
# ──────────────────────────────────────────────────────────

def sniper_quality_benchmark(sniper: dict, drift: dict, summary: dict) -> dict:
    """
    Rate each strategy against the crypto sniper benchmark.

    Crypto sniper is the gold standard:
      - Win rate: 91-99% WR (bucket-dependent)
      - Mechanism: structural (near-expiry FLB, price certainty before close)
      - Scale: 15+ bets/day, settled in 15 min, 20 USD/bet

    Scoring tiers:
      GOLD  — matches sniper quality (WR >= 95%, structural mechanism, validated 50+ bets)
      WATCH — approaching sniper (WR >= 90%, structural hypothesis)
      CALIBRATION — promising but insufficient data
      BELOW — not approaching sniper quality
    """
    all_time_pnl = summary["all_time"]["pnl_usd"]
    funding_gap = round(FUNDING_TARGET_USD - all_time_pnl, 2)

    strategies = {}

    # Crypto expiry sniper — reference benchmark
    sniper_buckets = sniper.get("buckets", {})
    core_bucket = sniper_buckets.get("90-94", {})
    core_wr = core_bucket.get("win_rate", 0)
    core_bets = core_bucket.get("bets", 0)
    strategies["crypto_sniper"] = {
        "tier": "GOLD",
        "win_rate": core_wr,
        "bets": core_bets,
        "pnl_usd": sniper_buckets.get("90-94", {}).get("pnl_usd", 0),
        "mechanism": "structural — near-expiry price certainty (FLB at 90c+)",
        "daily_capacity_usd": 300,
        "note": "REFERENCE BENCHMARK — do not modify guard stack without evidence",
    }

    # Drift strategies — score against benchmark
    for strat, data in drift.items():
        if data.get("status") == "NO_DATA" or data.get("bets", 0) == 0:
            strategies[strat] = {"tier": "CALIBRATION", "bets": 0, "note": "no data"}
            continue
        wr = data.get("win_rate", 0)
        bets = data.get("bets", 0)
        pnl = data.get("pnl_usd", 0)
        if wr >= SNIPER_QUALITY_WIN_RATE and bets >= 50:
            tier = "GOLD"
        elif wr >= SNIPER_WATCH_WIN_RATE and bets >= 20:
            tier = "WATCH"
        elif bets >= 20:
            tier = "BELOW"
        else:
            tier = "CALIBRATION"
        strategies[strat] = {
            "tier": tier,
            "win_rate": wr,
            "bets": bets,
            "pnl_usd": pnl,
            "gap_to_sniper": round(SNIPER_QUALITY_WIN_RATE - wr, 4),
        }

    # Soccer sniper — known candidate (paper mode)
    strategies["soccer_sniper_v1"] = {
        "tier": "CALIBRATION",
        "win_rate": None,
        "bets": 0,  # paper calibration, live 0
        "mechanism": "structural — FLB mid-game (market 10% reversal, true 3-5%)",
        "note": "needs 3+ paper wins before live — UCL March 31/April 1",
    }

    return {
        "funding_gap_usd": funding_gap,
        "funding_pct": round(min(1.0, all_time_pnl / FUNDING_TARGET_USD) * 100, 1),
        "strategies": strategies,
        "gold_strategies": [k for k, v in strategies.items() if v["tier"] == "GOLD"],
        "watch_strategies": [k for k, v in strategies.items() if v["tier"] == "WATCH"],
    }


# ──────────────────────────────────────────────────────────
# SESSION REFLECTION GENERATOR
# ──────────────────────────────────────────────────────────

def generate_reflection(
    sniper: dict,
    drift: dict,
    grad: dict,
    summary: dict,
    benchmark: dict,
    guard_gaps: list | None = None,
) -> str:
    """
    Generate a structured session-start reflection markdown document.

    Replaces manual Claude summarization with data-driven pattern output.
    Written to data/session_reflection.md — read at session start.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Session Reflection — auto-generated {now}",
        "# Read this at session start. Do NOT edit manually — regenerated each session.",
        "",
    ]

    # ── Funding status
    at = summary["all_time"]
    td = summary["today"]
    gap = benchmark["funding_gap_usd"]
    pct = benchmark["funding_pct"]
    lines += [
        "## FUNDING STATUS",
        f"  All-time: {at['pnl_usd']:+.2f} USD of +{FUNDING_TARGET_USD:.0f} USD goal ({pct:.1f}% complete)",
        f"  Today:    {td['pnl_usd']:+.2f} USD ({td['bets']} settled, {td['win_rate']:.0%} WR)",
        f"  Remaining: {gap:.2f} USD to goal",
        "",
    ]

    # ── Sniper engine health
    core = sniper.get("buckets", {}).get("90-94", {})
    core_wr = core.get("win_rate", 0)
    core_bets = core.get("bets", 0)
    core_pnl = core.get("pnl_usd", 0)
    health = "HEALTHY" if core_wr >= 0.93 else ("WATCH" if core_wr >= 0.90 else "DEGRADED")
    lines += [
        "## SNIPER ENGINE HEALTH",
        f"  Core 90-94c bucket: {core_bets} bets, {core_wr:.1%} WR, {core_pnl:+.2f} USD — {health}",
    ]
    # Watch buckets — distinguish guarded vs unguarded vs partial
    for bk, data in sniper.get("buckets", {}).items():
        if data["bets"] >= 10 and data["pnl_usd"] < 0:
            try:
                bk_price = int(bk.split("+")[0].split("-")[0])
            except (ValueError, AttributeError):
                bk_price = None
            yes_guarded = bk_price and _is_guarded(bk_price, "yes", "")
            no_guarded = bk_price and _is_guarded(bk_price, "no", "")
            if yes_guarded and no_guarded:
                lines.append(f"  GUARDED (historical losses expected): {bk}c bucket — guards active in live.py")
            elif yes_guarded or no_guarded:
                which = "NO" if no_guarded else "YES"
                open_side = "YES" if no_guarded else "NO"
                lines.append(
                    f"  PARTIAL GUARD: {bk}c bucket — {which} side guarded, "
                    f"{open_side} side open ({data['bets']} bets, {data['win_rate']:.0%} WR, {data['pnl_usd']:+.2f} USD). "
                    f"Check guard-gap section for live exposure."
                )
            else:
                lines.append(f"  WATCH: {bk}c bucket negative ({data['bets']} bets, {data['win_rate']:.0%} WR, {data['pnl_usd']:+.2f} USD)")
    lines.append("")

    # ── Direction filter status
    lines.append("## DIRECTION FILTER STATUS")
    for strat, data in drift.items():
        if data.get("status") == "NO_DATA":
            continue
        direction = data.get("direction", {})
        yes_d = direction.get("yes", {})
        no_d = direction.get("no", {})
        yes_wr = yes_d.get("win_rate", 0)
        no_wr = no_d.get("win_rate", 0)
        yes_bets = yes_d.get("bets", 0)
        no_bets = no_d.get("bets", 0)
        spread = abs(yes_wr - no_wr)
        better = "yes" if yes_wr > no_wr else "no"
        if yes_bets >= 10 and no_bets >= 10 and spread >= 0.10:
            action = f"ADD filter='{better}'" if data["bets"] < 30 else f"filter='{better}' confirmed"
            lines.append(
                f"  {strat}: YES {yes_bets}b {yes_wr:.0%} | NO {no_bets}b {no_wr:.0%} "
                f"| spread {spread:.0%} → {action}"
            )
        elif data.get("bets", 0) > 0:
            lines.append(
                f"  {strat}: {data['bets']} bets, {data['win_rate']:.0%} WR — "
                f"({'insufficient direction data' if min(yes_bets, no_bets) < 10 else 'no significant spread'})"
            )
    lines.append("")

    # ── Graduation alerts
    lines.append("## GRADUATION STATUS")
    for strat, data in grad.items():
        bets = data["live_bets"]
        if data["ready"]:
            lines.append(f"  {strat}: {bets}/30 — GRADUATED (eval complete)")
        elif bets >= 25:
            lines.append(f"  {strat}: {bets}/30 — IMMINENT ({data['needs']} bet(s) to eval)")
        else:
            lines.append(f"  {strat}: {bets}/30")
    lines.append("")

    # ── Sniper quality benchmark
    lines.append("## SNIPER QUALITY BENCHMARK")
    lines.append(f"  Gold standard: crypto_sniper 95%+ WR structural mechanism")
    bm_strats = benchmark.get("strategies", {})
    for name, data in bm_strats.items():
        tier = data.get("tier", "?")
        wr = data.get("win_rate")
        wr_str = f"{wr:.0%}" if wr is not None else "no data"
        bets = data.get("bets", 0)
        note = data.get("note", "")
        lines.append(f"  [{tier}] {name}: {wr_str} WR, {bets} bets{f' — {note}' if note else ''}")
    lines.append("")

    # ── Guard gap section — surfaces unguarded negative-EV paths
    if guard_gaps:
        lines.append("## UNGUARDED NEGATIVE-EV PATHS (ACTION REQUIRED)")
        for gap_item in guard_gaps[:5]:
            lines.append(
                f"  *** {gap_item['series']} {gap_item['side'].upper()}@{gap_item['price_cents']}c: "
                f"{gap_item['bets']} bets, {gap_item['win_rate']:.0%} WR "
                f"(need {gap_item['break_even_wr']:.0%}), {gap_item['pnl_usd']:+.2f} USD — "
                f"{gap_item['shortfall_pct']:.1f}pp below break-even — ADD GUARD"
            )
        lines.append("")
    else:
        lines.append("## GUARD GAP STATUS")
        lines.append("  No unguarded negative-EV paths found (last 30 days, 5+ bets). Guard stack clean.")
        lines.append("")

    # ── Top 3 actions
    lines.append("## TOP ACTIONS FOR THIS SESSION")
    actions = []
    # Unguarded negative-EV paths are top priority
    if guard_gaps:
        for gap_item in guard_gaps[:2]:
            actions.append(
                f"ADD GUARD: {gap_item['series']} {gap_item['side'].upper()}@{gap_item['price_cents']}c "
                f"({gap_item['bets']} bets, {gap_item['win_rate']:.0%} WR, {gap_item['pnl_usd']:+.2f} USD)"
            )
    # Graduation imminent?
    for strat, data in grad.items():
        if 28 <= data["live_bets"] < 30:
            actions.append(f"XRP graduation IMMINENT — {data['needs']} bet(s) left, add direction_filter at 30")
        elif data["live_bets"] == 30 and not data["ready"]:
            actions.append(f"{strat} at 30 bets — run direction filter eval NOW")
    # Funding milestone?
    if gap <= 20:
        actions.append(f"MILESTONE: {gap:.2f} USD from +125 USD goal — monitor closely")
    for i, action in enumerate(actions[:3], 1):
        lines.append(f"  {i}. {action}")
    if not actions:
        lines.append("  No urgent actions — maintain monitoring cadence")
    lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────

def run_analysis(save: bool = True, brief: bool = False, reflect: bool = False) -> dict:
    conn = _load_db()

    sniper = analyze_sniper(conn)
    drift = analyze_drift(conn)
    grad = graduation_status(conn)
    summary = overall_summary(conn)
    benchmark = sniper_quality_benchmark(sniper, drift, summary)
    guard_gaps = detect_guard_gaps(conn)  # unguarded negative-EV paths only

    conn.close()

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "sniper": sniper,
        "drift": drift,
        "graduation": grad,
        "benchmark": benchmark,
        "guard_gaps": guard_gaps,
        "top_recommendations": _generate_recommendations(sniper, drift, grad, summary, guard_gaps),
    }

    if save:
        INSIGHTS_PATH.write_text(json.dumps(insights, indent=2))

    if reflect:
        reflection_text = generate_reflection(sniper, drift, grad, summary, benchmark, guard_gaps)
        REFLECTION_PATH.write_text(reflection_text)
        print(reflection_text)
    elif brief:
        _print_brief(insights)
    else:
        _print_full(insights)

    return insights


def _generate_recommendations(sniper, drift, grad, summary, guard_gaps=None) -> list[str]:
    recs = []

    # Sniper bucket summary — only flag buckets with ACTIVE (unguarded) losses
    profitable = [
        b for b, v in sniper.get("buckets", {}).items()
        if v["pnl_usd"] > 0 and v["bets"] >= MIN_SNIPER_BUCKET
    ]
    # Buckets with negative PnL from historical data (pre-guard era)
    losing_all = [
        b for b, v in sniper.get("buckets", {}).items()
        if v["pnl_usd"] < 0 and v["bets"] >= MIN_SNIPER_BUCKET
    ]
    # Only flag as "needs guard" if detect_guard_gaps found unguarded negative-EV paths
    # within that bucket's price range
    guard_gap_prices = {str(g["price_cents"]) for g in (guard_gaps or [])}
    losing_needs_guard = [b for b in losing_all if b in guard_gap_prices]
    losing_already_guarded = [b for b in losing_all if b not in losing_needs_guard]

    if profitable:
        recs.append(f"SNIPER: Profitable buckets: {', '.join(profitable)}c")
    if losing_already_guarded:
        recs.append(f"SNIPER: Guarded buckets (historical losses blocked): {', '.join(losing_already_guarded)}c")
    if losing_needs_guard:
        recs.append(f"SNIPER: Losing buckets (guards recommended): {', '.join(losing_needs_guard)}c")

    # Drift strategies
    for strat, data in drift.items():
        if data.get("status") == "NO_DATA":
            continue
        if data.get("insight"):
            recs.append(data["insight"])

    # Graduation alerts
    for strat, data in grad.items():
        if 25 <= data["live_bets"] < 30:
            recs.append(f"GRADUATION WATCH: {strat} at {data['live_bets']}/30 — {data['needs']} bets to evaluation")

    # Profit target
    remaining = summary.get("remaining_usd", 0)
    if remaining > 0:
        recs.append(f"TARGET: {remaining:.2f} USD remaining to reach +125 USD all-time goal")

    return recs


def _print_brief(insights: dict):
    print("\n=== STRATEGY INSIGHTS (brief) ===")
    summary = insights["summary"]
    print(f"  All-time: {summary['all_time']['pnl_usd']:+.2f} USD ({summary['all_time']['win_rate']:.0%} WR, {summary['all_time']['bets']} bets)")
    print(f"  Today:    {summary['today']['pnl_usd']:+.2f} USD ({summary['today']['win_rate']:.0%} WR, {summary['today']['bets']} bets)")
    print(f"  Target:   {summary['remaining_usd']:.2f} USD to +125 USD goal")
    print()
    for rec in insights["top_recommendations"][:5]:
        print(f"  - {rec}")
    print()


def _print_full(insights: dict):
    print("\n" + "=" * 64)
    print("STRATEGY ANALYZER — SELF-LEARNING INSIGHTS")
    print(f"Generated: {insights['generated_at']}")
    print("=" * 64)

    summary = insights["summary"]
    print(f"\nOVERALL PERFORMANCE")
    print(f"  All-time: {summary['all_time']['bets']} bets | {summary['all_time']['win_rate']:.1%} WR | {summary['all_time']['pnl_usd']:+.2f} USD")
    print(f"  Today:    {summary['today']['bets']} bets | {summary['today']['win_rate']:.1%} WR | {summary['today']['pnl_usd']:+.2f} USD")
    print(f"  Target:   {summary['remaining_usd']:.2f} USD remaining to +125 USD goal")

    print("\nSNIPER BUCKETS (expiry_sniper_v1)")
    for bucket, data in sorted(insights["sniper"]["buckets"].items(), reverse=True):
        bk_price = int(bucket) if bucket.isdigit() else 0
        is_fully_guarded = (
            _is_guarded(bk_price, "yes", "") and _is_guarded(bk_price, "no", "")
        ) if bk_price else False
        if data["pnl_usd"] > 0:
            status = "PROFITABLE"
        elif is_fully_guarded:
            status = "GUARDED  "
        else:
            status = "LOSING   "
        flag = "*" if data["bets"] >= MIN_SNIPER_BUCKET else " "
        print(f"  {flag}{bucket}c: {data['bets']:3d} bets | {data['win_rate']:.0%} WR | {data['pnl_usd']:+7.2f} USD  [{status}]")
    print("  (* = enough data for insight)")

    print("\nDRIFT STRATEGIES")
    for strat, data in insights["drift"].items():
        if data.get("status") == "NO_DATA":
            print(f"  {strat}: NO DATA")
            continue
        print(f"  {strat}: {data['bets']} bets | {data['win_rate']:.0%} WR | {data['pnl_usd']:+.2f} USD | trend={data['recent_trend']}")
        direction = data.get("direction", {})
        for side, d in direction.items():
            print(f"    {side}: {d['bets']} bets | {d['win_rate']:.0%} WR | {d['pnl_usd']:+.2f} USD")

    print("\nGRADUATION STATUS")
    for strat, data in insights["graduation"].items():
        bar = "=" * int(data["graduation_pct"] / 5)
        ready = " READY" if data["ready"] else f" ({data['needs']} to go)"
        print(f"  {strat}: [{bar:<20}] {data['graduation_pct']:.0f}%{ready}")

    print("\nTOP RECOMMENDATIONS")
    for i, rec in enumerate(insights["top_recommendations"], 1):
        print(f"  {i}. {rec}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Strategy self-learning analyzer")
    parser.add_argument("--no-save", action="store_true", help="Print only, don't save to file")
    parser.add_argument("--brief", action="store_true", help="5-line summary for session startup")
    parser.add_argument(
        "--reflect",
        action="store_true",
        help="Generate session reflection document (data/session_reflection.md) — use at session start",
    )
    args = parser.parse_args()

    run_analysis(save=not args.no_save, brief=args.brief, reflect=args.reflect)


if __name__ == "__main__":
    main()
