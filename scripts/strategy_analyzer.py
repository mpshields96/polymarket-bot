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

# Minimum sample sizes before any insight is generated
MIN_SNIPER_BUCKET = 30
MIN_DRIFT_STRATEGY = 20
MIN_DIRECTION = 20


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

    today_ts = time.mktime(time.strptime(
        datetime.now(timezone.utc).strftime("%Y-%m-%d"), "%Y-%m-%d"
    ))
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
# MAIN
# ──────────────────────────────────────────────────────────

def run_analysis(save: bool = True, brief: bool = False) -> dict:
    conn = _load_db()

    sniper = analyze_sniper(conn)
    drift = analyze_drift(conn)
    grad = graduation_status(conn)
    summary = overall_summary(conn)

    conn.close()

    insights = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "sniper": sniper,
        "drift": drift,
        "graduation": grad,
        "top_recommendations": _generate_recommendations(sniper, drift, grad, summary),
    }

    if save:
        INSIGHTS_PATH.write_text(json.dumps(insights, indent=2))

    if brief:
        _print_brief(insights)
    else:
        _print_full(insights)

    return insights


def _generate_recommendations(sniper, drift, grad, summary) -> list[str]:
    recs = []

    # Sniper bucket summary
    profitable = [
        b for b, v in sniper.get("buckets", {}).items()
        if v["pnl_usd"] > 0 and v["bets"] >= MIN_SNIPER_BUCKET
    ]
    losing = [
        b for b, v in sniper.get("buckets", {}).items()
        if v["pnl_usd"] < 0 and v["bets"] >= MIN_SNIPER_BUCKET
    ]
    if profitable:
        recs.append(f"SNIPER: Profitable buckets: {', '.join(profitable)}c")
    if losing:
        recs.append(f"SNIPER: Losing buckets (guards recommended): {', '.join(losing)}c")

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
        status = "PROFITABLE" if data["pnl_usd"] > 0 else "LOSING  "
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
    args = parser.parse_args()

    run_analysis(save=not args.no_save, brief=args.brief)


if __name__ == "__main__":
    main()
