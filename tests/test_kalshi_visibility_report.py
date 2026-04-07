"""Tests for scripts/kalshi_visibility_report.py."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.kalshi_visibility_report import (
    build_visibility_report,
    canonicalize_series_ticker,
    evaluate_same_day_sports_gate,
    format_visibility_report,
)


def test_canonicalize_series_ticker_normalizes_known_aliases() -> None:
    assert canonicalize_series_ticker("KXNCAAMBGAME") == "KXNCAABGAME"
    assert canonicalize_series_ticker("KXBUNGAME") == "KXBUNDESLIGAGAME"
    assert canonicalize_series_ticker("KXNBAGAME") == "KXNBAGAME"


def test_build_visibility_report_combines_audit_scout_and_edge_views() -> None:
    audit_report = {
        "timestamp": "2026-04-06T12:00:00+00:00",
        "total_series": 5,
        "total_open_events": 8,
        "total_open_markets": 7,
        "series_breakdown": [
            {
                "series": "KXNBAGAME",
                "market_count": 2,
                "total_volume": 150000,
                "category": "sports",
                "sample_title": "Knicks at Bulls Winner?",
            },
            {
                "series": "KXNCAAMBGAME",
                "market_count": 1,
                "total_volume": 80000,
                "category": "sports",
                "sample_title": "Duke at UNC Winner?",
            },
            {
                "series": "KXUFCFIGHT",
                "market_count": 1,
                "total_volume": 90000,
                "category": "sports_or_other",
                "sample_title": "UFC Main Event",
            },
            {
                "series": "KXCPI",
                "market_count": 1,
                "total_volume": 200000,
                "category": "economics",
                "sample_title": "CPI April",
            },
            {
                "series": "KXSENATE2026",
                "market_count": 2,
                "total_volume": 500000,
                "category": "politics",
                "sample_title": "Senate control 2026",
            },
        ],
        "category_rollup": {},
    }
    all_markets = [
        {
            "series_ticker": "KXNBAGAME",
            "ticker": "KXNBAGAME-26APR061900NYKCHI-NYK",
            "close_time": "2026-04-06T23:00:00Z",
            "title": "Knicks at Bulls Winner?",
        },
        {
            "series_ticker": "KXNBAGAME",
            "ticker": "KXNBAGAME-26APR071900LALGSW-LAL",
            "close_time": "2026-04-07T23:00:00Z",
            "title": "Lakers at Warriors Winner?",
        },
        {
            "series_ticker": "KXNCAAMBGAME",
            "ticker": "KXNCAAMBGAME-26APR061830DUKEUNC-DUKE",
            "close_time": "2026-04-06T22:30:00Z",
            "title": "Duke at UNC Winner?",
        },
        {
            "series_ticker": "KXUFCFIGHT",
            "ticker": "KXUFCFIGHT-26APR06MAIN",
            "close_time": "2026-04-06T21:00:00Z",
            "title": "UFC Main Event",
        },
        {
            "series_ticker": "KXCPI",
            "ticker": "KXCPI-26APR10",
            "close_time": "2026-04-10T13:30:00Z",
            "title": "CPI April",
        },
        {
            "series_ticker": "KXSENATE2026",
            "ticker": "KXSENATE2026-DEM",
            "close_time": "2026-11-03T06:00:00Z",
            "title": "Senate control 2026",
        },
        {
            "series_ticker": "KXSENATE2026",
            "ticker": "KXSENATE2026-GOP",
            "close_time": "2026-11-03T06:00:00Z",
            "title": "Senate control 2026",
        },
    ]
    scout_candidates = [
        {
            "series": "KXSENATE2026",
            "ticker": "KXSENATE2026-DEM",
            "volume": 500000,
            "category": "politics",
            "close_time": "2026-11-03T06:00:00Z",
            "title": "Senate control 2026",
        },
        {
            "series": "KXUFCFIGHT",
            "ticker": "KXUFCFIGHT-26APR06MAIN",
            "volume": 90000,
            "category": "sports_or_other",
            "close_time": "2026-04-06T21:00:00Z",
            "title": "UFC Main Event",
        },
    ]
    edge_scan = {
        "sports_scanned": ["basketball_nba", "icehockey_nhl"],
        "total_matched": 4,
        "total_with_edge": 1,
    }

    report = build_visibility_report(
        audit_report=audit_report,
        all_markets=all_markets,
        scout_candidates=scout_candidates,
        edge_scan_result=edge_scan,
        now=datetime(2026, 4, 6, 15, 0, tzinfo=timezone.utc),
    )

    assert report["exchange"]["open_markets"] == 7
    assert report["coverage"]["open_series_count"] == 5
    assert report["coverage"]["covered_open_series_count"] == 3
    assert report["coverage"]["live_bot_visible_series_count"] == 2
    assert report["sports"]["same_day_market_count"] == 3
    assert report["sports"]["days_out_market_count"] == 1
    assert report["sports"]["same_day_visible_market_count"] == 2
    assert report["sports"]["same_day_skipped_market_count"] == 1
    assert report["sports"]["same_day_skipped_series"] == ["KXUFCFIGHT"]
    assert report["sports"]["same_day_gate"]["ok"] is False
    assert report["sports"]["same_day_gate"]["status"] == "FAIL"
    assert report["sports"]["edge_scan"]["series_scanned"] == ["KXNBAGAME", "KXNHLGAME"]
    assert report["non_sports_candidates"][0]["series"] == "KXSENATE2026"


def test_format_visibility_report_mentions_core_sections() -> None:
    report = {
        "timestamp": "2026-04-06T12:00:00+00:00",
        "exchange": {"open_markets": 7, "open_events": 8, "open_series": 5},
        "coverage": {
            "covered_open_series_count": 3,
            "uncovered_open_series_count": 2,
            "live_bot_visible_series_count": 2,
            "live_bot_visible_series": ["KXNBAGAME", "KXNCAABGAME"],
            "uncovered_open_series_top": [{"series": "KXSENATE2026", "total_volume": 500000}],
        },
        "sports": {
            "same_day_market_count": 3,
            "days_out_market_count": 1,
            "same_day_visible_market_count": 2,
            "same_day_skipped_market_count": 1,
            "same_day_visible_series": ["KXNBAGAME", "KXNCAABGAME"],
            "same_day_skipped_series": ["KXUFCFIGHT"],
            "same_day_gate": {
                "ok": False,
                "status": "FAIL",
                "reason": "1 same-day sports market is open in skipped series: KXUFCFIGHT",
            },
            "edge_scan": {
                "series_scanned": ["KXNBAGAME"],
                "total_matched": 4,
                "total_with_edge": 1,
            },
        },
        "non_sports_candidates": [
            {"series": "KXSENATE2026", "volume": 500000, "category": "politics"},
        ],
    }

    text = format_visibility_report(report)

    assert "Kalshi Visibility Report" in text
    assert "Covered vs Uncovered" in text
    assert "Same-Day Sports" in text
    assert "Non-Sports Candidates" in text
    assert "Gate: FAIL" in text
    assert "KXSENATE2026" in text


def test_evaluate_same_day_sports_gate_passes_when_all_same_day_sports_are_visible() -> None:
    gate = evaluate_same_day_sports_gate(
        {
            "same_day_market_count": 4,
            "same_day_visible_market_count": 4,
            "same_day_skipped_market_count": 0,
            "same_day_skipped_series": [],
        }
    )

    assert gate["ok"] is True
    assert gate["status"] == "PASS"
    assert "All 4 same-day sports markets" in gate["reason"]
