"""
tests/test_sports_clv.py — Unit tests for sports_clv.py

Covers: calculate_clv, clv_grade, log_clv_snapshot, read_clv_log,
        clv_summary (gate + verdicts), print_clv_report, _implied_prob_from_cents.
"""

import sys
import os
import csv
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "strategies"))

from sports_clv import (
    calculate_clv,
    clv_grade,
    log_clv_snapshot,
    read_clv_log,
    clv_summary,
    print_clv_report,
    CLV_GATE,
    _implied_prob_from_cents,
)


# ---------------------------------------------------------------------------
# _implied_prob_from_cents
# ---------------------------------------------------------------------------

def test_implied_prob_midpoint():
    assert round(_implied_prob_from_cents(50), 3) == 0.5


def test_implied_prob_43():
    assert round(_implied_prob_from_cents(43), 3) == 0.43


def test_implied_prob_clamp_high():
    # 100 cents must clamp below 1.0
    assert _implied_prob_from_cents(100) < 1.0
    assert _implied_prob_from_cents(100) == 0.999


def test_implied_prob_clamp_low():
    assert _implied_prob_from_cents(0) == 0.001


# ---------------------------------------------------------------------------
# calculate_clv
# ---------------------------------------------------------------------------

def test_clv_beat_close():
    # Bet at 48 when close was 55 → beat the close
    clv = calculate_clv(50, 55, 48)
    assert round(clv, 4) == 0.07


def test_clv_even():
    assert calculate_clv(50, 50, 50) == 0.0


def test_clv_missed_close():
    # Bet at 48 when close was 45 → didn't beat close
    clv = calculate_clv(50, 45, 48)
    assert round(clv, 4) == -0.03


def test_clv_open_price_ignored():
    # open_price should not affect the result
    assert calculate_clv(10, 55, 48) == calculate_clv(90, 55, 48)


def test_clv_returns_float():
    assert isinstance(calculate_clv(50, 55, 48), float)


# ---------------------------------------------------------------------------
# clv_grade
# ---------------------------------------------------------------------------

def test_grade_excellent():
    assert clv_grade(0.03) == "EXCELLENT"


def test_grade_excellent_at_boundary():
    assert clv_grade(0.02) == "EXCELLENT"


def test_grade_good():
    assert clv_grade(0.01) == "GOOD"


def test_grade_good_at_boundary():
    assert clv_grade(0.005) == "GOOD"


def test_grade_neutral():
    assert clv_grade(0.002) == "NEUTRAL"


def test_grade_neutral_at_zero():
    assert clv_grade(0.0) == "NEUTRAL"


def test_grade_poor():
    assert clv_grade(-0.01) == "POOR"


def test_grade_poor_large_negative():
    assert clv_grade(-0.99) == "POOR"


# ---------------------------------------------------------------------------
# log_clv_snapshot + read_clv_log
# ---------------------------------------------------------------------------

def _tmp_csv():
    f = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    f.close()
    os.unlink(f.name)  # delete so _ensure_csv creates it fresh
    return f.name


def test_log_snapshot_creates_file():
    path = _tmp_csv()
    try:
        row = log_clv_snapshot("KXNHLGAME-TEST-EDM", "yes", 52, 50, 57, log_path=path)
        assert os.path.exists(path)
        assert row["event_id"] == "KXNHLGAME-TEST-EDM"
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_log_snapshot_grade_valid():
    path = _tmp_csv()
    try:
        row = log_clv_snapshot("KXTEST", "yes", 50, 48, 55, log_path=path)
        assert row["grade"] in ("EXCELLENT", "GOOD", "NEUTRAL", "POOR")
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_log_snapshot_clv_pct_stored_as_percentage():
    # CLV of 0.07 decimal should be stored as 7.0 pct
    path = _tmp_csv()
    try:
        row = log_clv_snapshot("KXTEST", "yes", 50, 48, 55, log_path=path)
        # bet=48, close=55 → clv=0.07 → stored as 7.0
        assert row["clv_pct"] == round(0.07 * 100, 4)
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_read_clv_log_empty_when_no_file():
    entries = read_clv_log(log_path="/tmp/nonexistent_clv_test_xyz.csv")
    assert entries == []


def test_read_clv_log_returns_all_rows():
    path = _tmp_csv()
    try:
        for i in range(5):
            log_clv_snapshot(f"KXTEST-{i}", "yes", 50, 48 + i, 55, log_path=path)
        entries = read_clv_log(log_path=path)
        assert len(entries) == 5
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_read_clv_log_last_n():
    path = _tmp_csv()
    try:
        for i in range(10):
            log_clv_snapshot(f"KXTEST-{i}", "yes", 50, 48, 55, log_path=path)
        entries = read_clv_log(last_n=3, log_path=path)
        assert len(entries) == 3
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_read_clv_log_parses_numeric_types():
    path = _tmp_csv()
    try:
        log_clv_snapshot("KXTEST", "yes", 52, 50, 57, log_path=path)
        entries = read_clv_log(log_path=path)
        assert isinstance(entries[0]["clv_pct"], float)
        assert isinstance(entries[0]["open_price_cents"], int)
        assert isinstance(entries[0]["bet_price_cents"], int)
        assert isinstance(entries[0]["close_price_cents"], int)
    finally:
        if os.path.exists(path):
            os.unlink(path)


# ---------------------------------------------------------------------------
# clv_summary
# ---------------------------------------------------------------------------

def test_summary_empty_returns_insufficient():
    s = clv_summary([])
    assert s["verdict"] == "INSUFFICIENT DATA"
    assert s["n"] == 0


def test_summary_below_gate():
    entries = [{"clv_pct": 2.0}, {"clv_pct": -0.5}]
    s = clv_summary(entries)
    assert s["below_gate"] is True
    assert s["verdict"] == "INSUFFICIENT DATA"
    assert s["n"] == 2


def test_summary_strong_edge_capture():
    # 30 entries with high avg CLV and 70% positive rate
    entries = [{"clv_pct": 2.5}] * 21 + [{"clv_pct": -0.1}] * 9  # 21/30 = 70%, avg=1.72
    s = clv_summary(entries)
    assert s["n"] == 30
    assert s["below_gate"] is False
    assert s["verdict"] == "STRONG EDGE CAPTURE"


def test_summary_marginal():
    # avg=0.8, positive_rate=0.60
    entries = [{"clv_pct": 1.5}] * 18 + [{"clv_pct": -0.5}] * 12  # 18/30=60%, avg=0.7
    s = clv_summary(entries)
    assert s["verdict"] in ("MARGINAL", "NO EDGE")


def test_summary_no_edge():
    entries = [{"clv_pct": -0.5}] * 30
    s = clv_summary(entries)
    assert s["verdict"] == "NO EDGE"
    assert s["positive_rate"] == 0.0


def test_summary_positive_rate_calculation():
    entries = [{"clv_pct": 1.0}] * 15 + [{"clv_pct": -1.0}] * 15
    s = clv_summary(entries)
    assert round(s["positive_rate"], 4) == 0.5


def test_summary_min_max():
    entries = [{"clv_pct": v} for v in [1.0, -2.0, 5.0, 0.5]] + [{"clv_pct": 0.0}] * 26
    s = clv_summary(entries)
    assert s["max_clv_pct"] == 5.0
    assert s["min_clv_pct"] == -2.0


# ---------------------------------------------------------------------------
# print_clv_report (smoke — just confirm it doesn't crash)
# ---------------------------------------------------------------------------

def test_print_clv_report_no_file(capsys):
    print_clv_report(log_path="/tmp/nonexistent_clv_test_xyz.csv")
    out = capsys.readouterr().out
    assert "KALSHI CLV TRACKER" in out
    assert "INSUFFICIENT DATA" in out


def test_print_clv_report_with_data(capsys):
    path = _tmp_csv()
    try:
        for i in range(5):
            log_clv_snapshot(f"KXTEST-{i}", "yes", 50, 48, 55, log_path=path)
        print_clv_report(log_path=path)
        out = capsys.readouterr().out
        assert "KALSHI CLV TRACKER" in out
        assert "Total entries" in out
    finally:
        if os.path.exists(path):
            os.unlink(path)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
