"""Tests for scripts/polybot_wrap_helper.py."""

from __future__ import annotations

import importlib.util
import json
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
        gate = mod.get_visibility_gate()

    assert gate["status"] == "FAIL"
    assert gate["reason"] == "1 same-day sports market is open in skipped series: KXUFCFIGHT"
    assert gate["timestamp_display"] == "2026-04-06 15:00 UTC"


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

    assert "Latest visibility gate: FAIL" in text
    assert "2026-04-06 15:00 UTC" in text
    assert "KXUFCFIGHT" in text


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

    assert "Visibility gate: FAIL @ 2026-04-06 15:00 UTC" in text
    assert "KXUFCFIGHT" in text
