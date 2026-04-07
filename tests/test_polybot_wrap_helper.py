"""Tests for scripts/polybot_wrap_helper.py."""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


def _get_module():
    spec = importlib.util.spec_from_file_location(
        "polybot_wrap_helper",
        Path(__file__).parent.parent / "scripts" / "polybot_wrap_helper.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_get_visibility_gate_reads_cached_report(tmp_path) -> None:
    mod = _get_module()
    report_path = tmp_path / "kalshi_visibility_report.json"
    report_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-04-06T15:00:00+00:00",
                "sports": {
                    "same_day_gate": {
                        "ok": False,
                        "status": "FAIL",
                        "reason": "1 same-day sports market is open in skipped series: KXUFCFIGHT",
                    }
                },
            }
        )
    )

    with patch.object(mod, "VISIBILITY_REPORT_JSON", report_path):
        gate = mod.get_visibility_gate(
            now=datetime(2026, 4, 6, 15, 30, tzinfo=timezone.utc)
        )

    assert gate["status"] == "FAIL"
    assert gate["reason"] == "1 same-day sports market is open in skipped series: KXUFCFIGHT"
    assert gate["timestamp_display"] == "2026-04-06 15:00 UTC"


def test_get_visibility_gate_rejects_corrupt_cached_report(tmp_path) -> None:
    mod = _get_module()
    report_path = tmp_path / "kalshi_visibility_report.json"
    report_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-04-07T03:09:23.159456+00:00",
                "exchange": {"open_markets": 466879, "open_events": 10000, "open_series": 1},
                "coverage": {
                    "open_series_count": 1,
                    "uncovered_open_series_top": [
                        {"series": "UNKNOWN", "total_volume": 987657234}
                    ],
                },
                "sports": {
                    "same_day_gate": {
                        "ok": True,
                        "status": "PASS",
                        "reason": "No same-day sports markets are open.",
                    }
                },
            }
        )
    )

    with patch.object(mod, "VISIBILITY_REPORT_JSON", report_path):
        gate = mod.get_visibility_gate(
            now=datetime(2026, 4, 7, 3, 30, tzinfo=timezone.utc)
        )

    assert gate["status"] == "UNKNOWN"
    assert "corrupt" in gate["reason"].lower()


def test_generate_main_chat_prompt_includes_visibility_gate_summary() -> None:
    mod = _get_module()

    text = mod.generate_main_chat_prompt(
        session_num=167,
        pid=0,
        pid_status="STOPPED",
        pnl={
            "alltime": 129.91,
            "today": -1.81,
            "today_wins": 14,
            "today_bets": 16,
            "today_wr": 87.5,
        },
        git={"hash": "321ef74", "msg": "add kalshi visibility gate to overhaul workflow", "test_count": 2167},
        strats={},
        cusum=["all stable"],
        guard_count=11,
        visibility_gate={
            "status": "FAIL",
            "reason": "1 same-day sports market is open in skipped series: KXUFCFIGHT",
            "timestamp_display": "2026-04-06 15:00 UTC",
        },
        grade="B",
        wins="shipped visibility gate",
        losses="startup state still stale",
    )

    assert "OVERHAUL STATUS: INCOMPLETE" in text
    assert "blocked by visibility gate FAIL" in text
    assert "Latest visibility gate: FAIL" in text
    assert "2026-04-06 15:00 UTC" in text
    assert "KXUFCFIGHT" in text
    assert "PRIORITY 1: close overhaul blockers" in text
    assert "Do not restart or expand just because useful components exist." in text


def test_generate_main_chat_prompt_uses_auto_guard_count_from_dict() -> None:
    mod = _get_module()

    text = mod.generate_main_chat_prompt(
        session_num=167,
        pid=0,
        pid_status="STOPPED",
        pnl={
            "alltime": 129.91,
            "today": -1.81,
            "today_wins": 14,
            "today_bets": 16,
            "today_wr": 87.5,
        },
        git={"hash": "321ef74", "msg": "add kalshi visibility gate to overhaul workflow", "test_count": 2167},
        strats={},
        cusum=["all stable"],
        guard_count={"auto": 4, "il": 19, "total": 23},
        visibility_gate={
            "status": "PASS",
            "reason": "All same-day sports markets are visible.",
            "timestamp_display": "2026-04-06 15:00 UTC",
        },
        grade="B",
        wins="shipped visibility gate",
        losses="startup state still stale",
    )

    assert "Loaded 4 auto-discovered guard(s)" in text


def test_generate_main_chat_prompt_alive_bot_avoids_hardcoded_stopped_warning() -> None:
    mod = _get_module()

    text = mod.generate_main_chat_prompt(
        session_num=167,
        pid=84187,
        pid_status="ALIVE",
        pnl={
            "alltime": 129.91,
            "today": 3.09,
            "today_wins": 4,
            "today_bets": 4,
            "today_wr": 100.0,
        },
        git={"hash": "321ef74", "msg": "add kalshi visibility gate to overhaul workflow", "test_count": 2167},
        strats={},
        cusum=["all stable"],
        guard_count={"auto": 4, "il": 19, "total": 23},
        visibility_gate={
            "status": "UNKNOWN",
            "reason": "No cached visibility report. Run scripts/kalshi_visibility_report.py before strategy planning.",
            "timestamp_display": "missing",
        },
        grade="B",
        wins="shipped visibility gate",
        losses="startup state still stale",
    )

    assert "Bot may still be running. Verify PID/log freshness before any restart." in text
    assert "Bot is STOPPED. Run restart command first." not in text


def test_generate_handoff_bot_state_includes_visibility_gate_summary() -> None:
    mod = _get_module()

    text = mod.generate_handoff_bot_state(
        session_num=167,
        pid=0,
        pid_status="STOPPED",
        pnl={
            "alltime": 129.91,
            "today": -1.81,
            "today_wins": 14,
            "today_bets": 16,
            "today_wr": 87.5,
        },
        git={"hash": "321ef74", "msg": "add kalshi visibility gate to overhaul workflow", "test_count": 2167},
        strats={},
        grade="B",
        wins="shipped visibility gate",
        losses="startup state still stale",
        visibility_gate={
            "status": "FAIL",
            "reason": "1 same-day sports market is open in skipped series: KXUFCFIGHT",
            "timestamp_display": "2026-04-06 15:00 UTC",
        },
    )

    assert "OVERHAUL STATUS: INCOMPLETE" in text
    assert "blocked by visibility gate FAIL" in text
    assert "Visibility gate: FAIL @ 2026-04-06 15:00 UTC" in text
    assert "KXUFCFIGHT" in text


def test_summarize_overhaul_status_flags_missing_visibility_report() -> None:
    mod = _get_module()

    status = mod.summarize_overhaul_status(
        {
            "status": "UNKNOWN",
            "reason": "No cached visibility report. Run scripts/kalshi_visibility_report.py before strategy planning.",
            "timestamp_display": "missing",
        }
    )

    assert status["status"] == "INCOMPLETE"
    assert "blocked by visibility gate UNKNOWN @ missing" in status["summary"]
    assert "No cached visibility report" in status["summary"]


def test_update_session_resume_replaces_legacy_prompt_format(tmp_path) -> None:
    mod = _get_module()
    resume_path = tmp_path / "SESSION_RESUME.md"
    resume_path.write_text(
        "SESSION RESUME — auto-updated by /polybot-wrap at session end.\n"
        "Do NOT edit manually. Read by /polybot-init at session start.\n\n"
        "═══════════════════════════════════════════════════\n"
        "MAIN CHAT PROMPT — SESSION 161 (2026-04-02)\n"
        "═══════════════════════════════════════════════════\n\n"
        "--- SESSION 161 START ---\n"
        "Go. Restart the bot. Make money today.\n"
        "--- END SESSION 161 PROMPT ---\n"
    )

    new_block = (
        "--- MAIN CHAT (Session 168 — monitoring + research combined PERMANENTLY) ---\n"
        "OVERHAUL STATUS: INCOMPLETE — blocked by visibility gate UNKNOWN @ missing: No cached visibility report.\n"
        "--- END MAIN CHAT PROMPT ---"
    )

    with patch.object(mod, "SESSION_RESUME", resume_path):
        assert mod.update_session_resume(new_block) is True

    content = resume_path.read_text()
    assert "MAIN CHAT PROMPT — SESSION 161" not in content
    assert "Go. Restart the bot. Make money today." not in content
    assert new_block in content
