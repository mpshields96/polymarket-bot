"""
Tests for polybot_comm.py — send_outcome_report and parse_research_priorities.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


def _get_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "polybot_comm",
        Path(__file__).parent.parent / "scripts" / "polybot_comm.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── send_outcome_report ──────────────────────────────────────────────────────

class TestSendOutcomeReport:
    def test_writes_valid_jsonl(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            msg_id = mod.send_outcome_report("UPDATE-33", "profitable", profit_cents=500, bet_count=15)
        lines = queue.read_text().strip().split("\n")
        assert len(lines) == 1
        msg = json.loads(lines[0])
        assert msg["category"] == "outcome_report"
        assert msg["sender"] == "km"
        assert msg["target"] == "cca"
        body = json.loads(msg["body"])
        assert body["delivery_id"] == "UPDATE-33"
        assert body["status"] == "profitable"
        assert body["profit_cents"] == 500
        assert body["bet_count"] == 15

    def test_returns_msg_id(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            msg_id = mod.send_outcome_report("UPDATE-1", "pending")
        assert msg_id.startswith("msg_")

    def test_invalid_status_raises(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            with pytest.raises(ValueError, match="status must be one of"):
                mod.send_outcome_report("UPDATE-1", "unknown_status")

    def test_optional_fields_absent_when_not_provided(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            mod.send_outcome_report("UPDATE-5", "pending")
        msg = json.loads(queue.read_text().strip())
        body = json.loads(msg["body"])
        assert "profit_cents" not in body
        assert "bet_count" not in body
        assert "notes" not in body

    def test_appends_multiple_messages(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            mod.send_outcome_report("UPDATE-1", "profitable")
            mod.send_outcome_report("UPDATE-2", "unprofitable")
        lines = queue.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_all_valid_statuses_accepted(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        for status in ("profitable", "unprofitable", "rejected", "pending"):
            with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
                mod.send_outcome_report("UPDATE-X", status)

    def test_notes_included_when_provided(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            mod.send_outcome_report("UPDATE-3", "profitable", notes="great result")
        body = json.loads(json.loads(queue.read_text().strip())["body"])
        assert body["notes"] == "great result"


# ── parse_research_priorities ────────────────────────────────────────────────

class TestParseResearchPriorities:
    def _make_priority_msg(self, category: str, score: float, recommendation: str = "") -> str:
        body = {
            "category": category,
            "score": score,
            "recommendation": recommendation or f"Prioritize {category}",
            "total_deliveries": 10,
            "profitable_count": 7,
        }
        msg = {
            "id": f"msg_{category}",
            "sender": "cca",
            "target": "km",
            "subject": f"Research priority: {category}",
            "body": json.dumps(body),
            "priority": "normal",
            "category": "research_priority",
            "status": "unread",
            "created_at": "2026-03-25T00:00:00Z",
        }
        return json.dumps(msg, separators=(",", ":"))

    def test_returns_empty_when_queue_missing(self, tmp_path):
        mod = _get_module()
        missing = tmp_path / "nonexistent.jsonl"
        with patch.object(mod, "CROSS_CHAT_QUEUE", missing):
            result = mod.parse_research_priorities()
        assert result == []

    def test_parses_single_priority(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        queue.write_text(self._make_priority_msg("guards", 0.9, "Build more guards") + "\n")
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            result = mod.parse_research_priorities()
        assert len(result) == 1
        assert result[0]["category"] == "guards"
        assert result[0]["score"] == 0.9

    def test_sorted_by_score_descending(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        lines = [
            self._make_priority_msg("guards", 0.5),
            self._make_priority_msg("signals", 0.9),
            self._make_priority_msg("calibration", 0.7),
        ]
        queue.write_text("\n".join(lines) + "\n")
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            result = mod.parse_research_priorities()
        scores = [p["score"] for p in result]
        assert scores == sorted(scores, reverse=True)

    def test_ignores_non_cca_priority_messages(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        # outcome_report from km (not a priority from cca)
        other_msg = json.dumps({
            "id": "msg_other", "sender": "km", "target": "cca",
            "category": "outcome_report", "status": "unread",
            "body": "{}", "created_at": "2026-03-25T00:00:00Z",
        })
        queue.write_text(other_msg + "\n" + self._make_priority_msg("signals", 0.9) + "\n")
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            result = mod.parse_research_priorities()
        assert len(result) == 1
        assert result[0]["category"] == "signals"

    def test_deduplicates_by_category_keeps_last(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        # Two guards priorities — last should win
        lines = [
            self._make_priority_msg("guards", 0.5),
            self._make_priority_msg("guards", 0.8),  # later one
        ]
        queue.write_text("\n".join(lines) + "\n")
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            result = mod.parse_research_priorities()
        assert len(result) == 1
        assert result[0]["score"] == 0.8

    def test_ignores_malformed_lines(self, tmp_path):
        mod = _get_module()
        queue = tmp_path / "queue.jsonl"
        queue.write_text("not json\n" + self._make_priority_msg("signals", 0.9) + "\n")
        with patch.object(mod, "CROSS_CHAT_QUEUE", queue):
            result = mod.parse_research_priorities()
        assert len(result) == 1
