#!/usr/bin/env python3
"""Unified Kalshi visibility report composed from existing scanners."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.audit_all_kalshi_markets import (
    build_audit_report,
    fetch_all_events,
    fetch_all_markets,
    fetch_all_series,
)
from scripts.edge_scanner import SPORT_MAP, run_scan
from scripts.kalshi_series_scout import COVERED_SERIES, select_candidates
from src.platforms.kalshi import load_from_env as kalshi_load_from_env

REPORT_TZ = ZoneInfo("America/Chicago")
CACHE_MAX_AGE_MINUTES = 180
SERIES_ALIASES = {
    "KXNCAAMBGAME": "KXNCAABGAME",
    "KXBUNGAME": "KXBUNDESLIGAGAME",
    "KXSERGAME": "KXSERIEAGAME",
    "KXLALGAME": "KXLALIGAGAME",
    "KXL1GAME": "KXLIGUE1GAME",
}


def canonicalize_series_ticker(series_ticker: str) -> str:
    """Normalize stale or shorthand series aliases to the canonical ticker."""
    return SERIES_ALIASES.get((series_ticker or "").upper(), (series_ticker or "").upper())


def _is_sports_category(category: str) -> bool:
    return "sport" in (category or "").lower()


def _parse_market_close_time(market: dict) -> datetime | None:
    close_time = market.get("close_time")
    if not close_time:
        return None
    try:
        return datetime.fromisoformat(close_time.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_report_timestamp(raw_timestamp: str | None) -> datetime | None:
    if not raw_timestamp:
        return None
    try:
        return datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _validate_cached_report(report: dict) -> str | None:
    sports = report.get("sports", {})
    if not isinstance(sports.get("same_day_gate"), dict):
        return "Cached visibility report missing same_day_gate."

    exchange = report.get("exchange", {})
    coverage = report.get("coverage", {})
    open_markets = int(exchange.get("open_markets", 0) or 0)
    open_series = int(coverage.get("open_series_count", exchange.get("open_series", 0)) or 0)
    uncovered = coverage.get("uncovered_open_series_top") or []

    if (
        open_markets >= 1000
        and open_series == 1
        and uncovered
        and (uncovered[0].get("series") or "").upper() == "UNKNOWN"
    ):
        return (
            "Cached visibility report appears corrupt "
            "(single UNKNOWN series dominates the exchange snapshot). "
            "Rebuild with --refresh-live before relying on it."
        )

    return None


def load_cached_visibility_report(
    path: Path,
    max_age_minutes: int = CACHE_MAX_AGE_MINUTES,
    now: datetime | None = None,
) -> tuple[dict | None, str | None]:
    """Load a cached report if it is fresh and structurally usable."""
    if not path.exists():
        return None, (
            "No cached visibility report. "
            "Run scripts/kalshi_visibility_report.py --refresh-live before strategy planning."
        )

    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"Cached visibility report unreadable: {exc}"

    now = now or datetime.now(timezone.utc)
    report_ts = _parse_report_timestamp(report.get("timestamp"))
    if report_ts is None:
        return None, "Cached visibility report missing a usable timestamp."

    age = now - report_ts.astimezone(timezone.utc)
    if age > timedelta(minutes=max_age_minutes) or (
        report_ts.astimezone(REPORT_TZ).date() != now.astimezone(REPORT_TZ).date()
    ):
        return None, (
            "Cached visibility report is stale "
            f"({int(age.total_seconds() // 60)} minutes old). "
            "Run scripts/kalshi_visibility_report.py --refresh-live before strategy planning."
        )

    validation_error = _validate_cached_report(report)
    if validation_error:
        return None, validation_error

    return report, None


def build_unavailable_visibility_report(reason: str, now: datetime | None = None) -> dict:
    """Build a fail-closed report when no trustworthy cached snapshot exists."""
    now = now or datetime.now(timezone.utc)
    return {
        "timestamp": now.isoformat(),
        "exchange": {
            "open_markets": 0,
            "open_events": 0,
            "open_series": 0,
        },
        "coverage": {
            "open_series_count": 0,
            "covered_open_series_count": 0,
            "covered_open_series": [],
            "uncovered_open_series_count": 0,
            "uncovered_open_series_top": [],
            "live_bot_visible_series_count": 0,
            "live_bot_visible_series": [],
        },
        "sports": {
            "same_day_market_count": 0,
            "days_out_market_count": 0,
            "same_day_visible_market_count": 0,
            "same_day_skipped_market_count": 0,
            "same_day_visible_series": [],
            "same_day_skipped_series": [],
            "edge_scan": _edge_scan_summary(None),
            "same_day_gate": {
                "ok": False,
                "status": "UNKNOWN",
                "reason": reason,
            },
        },
        "non_sports_candidates": [],
    }


def _canonical_series_rows(series_breakdown: list[dict]) -> list[dict]:
    combined: dict[str, dict] = {}
    for row in series_breakdown:
        canonical = canonicalize_series_ticker(row.get("series", ""))
        existing = combined.get(canonical)
        if not existing:
            combined[canonical] = {
                **row,
                "series": canonical,
            }
            continue

        existing["market_count"] += row.get("market_count", 0)
        existing["total_volume"] += row.get("total_volume", 0)
        existing["near_50c_count"] += row.get("near_50c_count", 0)
        existing["sample_title"] = existing.get("sample_title") or row.get("sample_title", "")
        if not existing.get("category"):
            existing["category"] = row.get("category", "")
        if row.get("avg_spread", -1) >= 0 and existing.get("avg_spread", -1) >= 0:
            existing["avg_spread"] = round((existing["avg_spread"] + row["avg_spread"]) / 2, 1)
        elif existing.get("avg_spread", -1) < 0:
            existing["avg_spread"] = row.get("avg_spread", -1)

    rows = list(combined.values())
    rows.sort(key=lambda row: row.get("total_volume", 0), reverse=True)
    return rows


def _live_bot_visible_game_series() -> set[str]:
    return {
        canonicalize_series_ticker(series)
        for series in COVERED_SERIES
        if "GAME" in canonicalize_series_ticker(series)
    }


def _covered_series_set() -> set[str]:
    covered = {canonicalize_series_ticker(series) for series in COVERED_SERIES}
    # Planned research lanes like UFC should not be counted as already visible today.
    covered.discard("KXUFCFIGHT")
    return covered


def _edge_scan_summary(edge_scan_result: dict | None) -> dict:
    if not edge_scan_result:
        return {
            "series_scanned": [],
            "total_matched": 0,
            "total_with_edge": 0,
        }

    sports_scanned = set(edge_scan_result.get("sports_scanned", []))
    series_scanned = sorted(
        canonicalize_series_ticker(series)
        for series, odds_key in SPORT_MAP.items()
        if odds_key in sports_scanned
    )
    return {
        "series_scanned": series_scanned,
        "total_matched": edge_scan_result.get("total_matched", 0),
        "total_with_edge": edge_scan_result.get("total_with_edge", 0),
    }


def evaluate_same_day_sports_gate(sports_summary: dict) -> dict:
    """Return an operational pass/fail verdict for same-day sports visibility."""
    same_day_market_count = sports_summary.get("same_day_market_count", 0)
    visible_market_count = sports_summary.get("same_day_visible_market_count", 0)
    skipped_market_count = sports_summary.get("same_day_skipped_market_count", 0)
    skipped_series = sports_summary.get("same_day_skipped_series", [])

    if same_day_market_count == 0:
        return {
            "ok": True,
            "status": "PASS",
            "reason": "No same-day sports markets are open.",
        }

    if visible_market_count == 0:
        detail = ", ".join(skipped_series) or "unknown series"
        return {
            "ok": False,
            "status": "FAIL",
            "reason": f"No same-day sports markets are visible to the bot. Open series: {detail}",
        }

    if skipped_market_count > 0:
        detail = ", ".join(skipped_series) or "unknown series"
        noun = "market is" if skipped_market_count == 1 else "markets are"
        return {
            "ok": False,
            "status": "FAIL",
            "reason": f"{skipped_market_count} same-day sports {noun} open in skipped series: {detail}",
        }

    return {
        "ok": True,
        "status": "PASS",
        "reason": f"All {same_day_market_count} same-day sports markets belong to visible series.",
    }


def build_visibility_report(
    audit_report: dict,
    all_markets: list[dict],
    scout_candidates: list[dict],
    edge_scan_result: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Combine audit, scout, and edge outputs into one authoritative report."""
    now = now or datetime.now(timezone.utc)
    today_local = now.astimezone(REPORT_TZ).date()

    covered_series = _covered_series_set()
    visible_game_series = _live_bot_visible_game_series()
    series_rows = _canonical_series_rows(audit_report.get("series_breakdown", []))
    category_lookup = {
        row["series"]: row.get("category", "")
        for row in series_rows
    }

    open_series = [row["series"] for row in series_rows]
    covered_open_series = [series for series in open_series if series in covered_series]
    uncovered_open_series = [row for row in series_rows if row["series"] not in covered_series]
    live_bot_visible_series = [series for series in open_series if series in visible_game_series]

    same_day_market_count = 0
    days_out_market_count = 0
    same_day_visible_market_count = 0
    same_day_skipped_market_count = 0
    same_day_visible_series: set[str] = set()
    same_day_skipped_series: set[str] = set()

    for market in all_markets:
        canonical_series = canonicalize_series_ticker(market.get("series_ticker", ""))
        category = category_lookup.get(canonical_series, "")
        if not _is_sports_category(category):
            continue

        close_dt = _parse_market_close_time(market)
        if not close_dt:
            continue
        close_local = close_dt.astimezone(REPORT_TZ).date()

        if close_local == today_local:
            same_day_market_count += 1
            if canonical_series in visible_game_series:
                same_day_visible_market_count += 1
                same_day_visible_series.add(canonical_series)
            else:
                same_day_skipped_market_count += 1
                same_day_skipped_series.add(canonical_series)
        elif close_local > today_local:
            days_out_market_count += 1

    non_sports_candidates = []
    seen_candidates: set[str] = set()
    for candidate in scout_candidates:
        canonical_series = canonicalize_series_ticker(candidate.get("series", ""))
        if canonical_series in seen_candidates:
            continue
        if _is_sports_category(candidate.get("category", "")):
            continue
        seen_candidates.add(canonical_series)
        non_sports_candidates.append({
            **candidate,
            "series": canonical_series,
        })

    sports_summary = {
        "same_day_market_count": same_day_market_count,
        "days_out_market_count": days_out_market_count,
        "same_day_visible_market_count": same_day_visible_market_count,
        "same_day_skipped_market_count": same_day_skipped_market_count,
        "same_day_visible_series": sorted(same_day_visible_series),
        "same_day_skipped_series": sorted(same_day_skipped_series),
        "edge_scan": _edge_scan_summary(edge_scan_result),
    }
    sports_summary["same_day_gate"] = evaluate_same_day_sports_gate(sports_summary)

    return {
        "timestamp": audit_report.get("timestamp") or now.isoformat(),
        "exchange": {
            "open_markets": audit_report.get("total_open_markets", 0),
            "open_events": audit_report.get("total_open_events", 0),
            "open_series": len(series_rows),
        },
        "coverage": {
            "open_series_count": len(series_rows),
            "covered_open_series_count": len(covered_open_series),
            "covered_open_series": covered_open_series,
            "uncovered_open_series_count": len(uncovered_open_series),
            "uncovered_open_series_top": uncovered_open_series[:10],
            "live_bot_visible_series_count": len(live_bot_visible_series),
            "live_bot_visible_series": live_bot_visible_series,
        },
        "sports": sports_summary,
        "non_sports_candidates": non_sports_candidates[:10],
    }


def format_visibility_report(report: dict) -> str:
    """Render the structured report as concise markdown."""
    same_day_gate = report["sports"].get("same_day_gate") or evaluate_same_day_sports_gate(report["sports"])
    lines = [
        f"# Kalshi Visibility Report — {report['timestamp'][:10]}",
        "",
        "## Exchange Snapshot",
        f"- Open markets: {report['exchange']['open_markets']}",
        f"- Open events: {report['exchange']['open_events']}",
        f"- Open series: {report['exchange']['open_series']}",
        "",
        "## Covered vs Uncovered",
        f"- Covered open series: {report['coverage']['covered_open_series_count']}",
        f"- Live-bot-visible series today: {report['coverage']['live_bot_visible_series_count']}",
        f"- Uncovered open series: {report['coverage']['uncovered_open_series_count']}",
        f"- Live bot visible: {', '.join(report['coverage']['live_bot_visible_series']) or 'none'}",
        "",
        "Top uncovered open series:",
    ]

    for row in report["coverage"]["uncovered_open_series_top"][:5]:
        lines.append(
            f"- {row['series']} — {row.get('total_volume', 0):,} volume"
        )

    lines += [
        "",
        "## Same-Day Sports",
        f"- Same-day markets: {report['sports']['same_day_market_count']}",
        f"- Days-out markets: {report['sports']['days_out_market_count']}",
        f"- Same-day visible markets: {report['sports'].get('same_day_visible_market_count', 0)}",
        f"- Same-day skipped markets: {report['sports'].get('same_day_skipped_market_count', 0)}",
        f"- Gate: {same_day_gate['status']} — {same_day_gate['reason']}",
        f"- Same-day visible series: {', '.join(report['sports']['same_day_visible_series']) or 'none'}",
        f"- Same-day skipped series: {', '.join(report['sports']['same_day_skipped_series']) or 'none'}",
        "",
        "## Edge Scanner Coverage",
        f"- Series scanned: {', '.join(report['sports']['edge_scan']['series_scanned']) or 'none'}",
        f"- Matched to odds: {report['sports']['edge_scan']['total_matched']}",
        f"- With edge: {report['sports']['edge_scan']['total_with_edge']}",
        "",
        "## Non-Sports Candidates",
    ]

    if report["non_sports_candidates"]:
        for candidate in report["non_sports_candidates"]:
            lines.append(
                f"- {candidate['series']} — {candidate.get('volume', 0):,} volume [{candidate.get('category', 'unknown')}]"
            )
    else:
        lines.append("- none")

    return "\n".join(lines)


def _load_cached_edge_scan(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as handle:
        return json.load(handle)


async def generate_visibility_report(
    min_volume: int = 50_000,
    edge_mode: str = "cached",
    min_edge: float = 0.02,
) -> dict:
    """Fetch live Kalshi data and build the unified report."""
    client = kalshi_load_from_env()
    await client.start()

    try:
        all_series = await fetch_all_series(client)
        all_events = await fetch_all_events(client)
        all_markets = await fetch_all_markets(client)
    finally:
        await client.close()

    audit_report = build_audit_report(all_series, all_events, all_markets)
    scout_candidates = select_candidates(all_markets, min_volume=min_volume)

    edge_scan_result = None
    if edge_mode == "cached":
        edge_scan_result = _load_cached_edge_scan(Path("data/edge_scan_results.json"))
    elif edge_mode == "live":
        scan_result = await run_scan(min_edge=min_edge)
        edge_scan_result = {
            "sports_scanned": scan_result.sports_scanned,
            "total_matched": scan_result.total_matched,
            "total_with_edge": scan_result.total_with_edge,
        }

    return build_visibility_report(
        audit_report=audit_report,
        all_markets=all_markets,
        scout_candidates=scout_candidates,
        edge_scan_result=edge_scan_result,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one authoritative Kalshi visibility report")
    parser.add_argument("--output", default=None, help="Markdown output path")
    parser.add_argument("--json-output", default="data/kalshi_visibility_report.json", help="JSON output path")
    parser.add_argument("--min-volume", type=int, default=50_000, help="Scout minimum volume threshold")
    parser.add_argument(
        "--edge-mode",
        choices=["cached", "live", "skip"],
        default="cached",
        help="Use cached edge scan, run live edge scan, or skip edge integration",
    )
    parser.add_argument("--min-edge", type=float, default=0.02, help="Minimum edge threshold for live edge scan")
    parser.add_argument(
        "--refresh-live",
        action="store_true",
        help="Explicitly rebuild the report from live Kalshi API data. Default path is cache-only and startup-safe.",
    )
    parser.add_argument(
        "--cache-max-age-minutes",
        type=int,
        default=CACHE_MAX_AGE_MINUTES,
        help="Maximum age for cached visibility data before startup treats it as stale.",
    )
    parser.add_argument(
        "--strict-same-day-sports",
        action="store_true",
        help="Exit non-zero if same-day sports markets are open in series the bot cannot currently see",
    )
    args = parser.parse_args()

    json_path = Path(args.json_output)
    if args.refresh_live:
        report = asyncio.run(
            generate_visibility_report(
                min_volume=args.min_volume,
                edge_mode=args.edge_mode,
                min_edge=args.min_edge,
            )
        )
    else:
        report, cache_reason = load_cached_visibility_report(
            json_path,
            max_age_minutes=args.cache_max_age_minutes,
        )
        if report is None:
            report = build_unavailable_visibility_report(cache_reason or "Visibility cache unavailable.")

    markdown = format_visibility_report(report)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as handle:
        json.dump(report, handle, indent=2, default=str)

    output = args.output or f".planning/KALSHI_VISIBILITY_REPORT_{datetime.now().strftime('%Y-%m-%d')}.md"
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as handle:
        handle.write(markdown + "\n")

    print(markdown)
    print(f"\nJSON saved to {json_path}")
    print(f"Markdown saved to {output_path}")

    if args.strict_same_day_sports and not report["sports"]["same_day_gate"]["ok"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
