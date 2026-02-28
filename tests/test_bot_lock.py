"""
Tests for bot startup lock — prevents multiple instances from running simultaneously.

Covers:
    _acquire_bot_lock: bot.pid checks (stale, live, permission denied, corrupt)
    _scan_for_duplicate_main_processes: pgrep-based orphan detection
    Integration: acquire exits if a duplicate process is found via pgrep
"""

import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ── Import the functions under test ──────────────────────────────────────

# We import at function scope below so we can monkeypatch _PID_FILE cleanly.


# ── Helpers ──────────────────────────────────────────────────────────────


def _make_pgrep_result(pids: list[int]) -> MagicMock:
    """Create a mock subprocess result as if pgrep returned the given PIDs."""
    mock = MagicMock()
    mock.stdout = "\n".join(str(p) for p in pids) + ("\n" if pids else "")
    mock.returncode = 0 if pids else 1
    return mock


# ── _scan_for_duplicate_main_processes ───────────────────────────────────


class TestScanForDuplicateProcesses:
    """Tests for the pgrep-based orphan instance detection."""

    def test_no_other_processes_returns_empty(self):
        """pgrep returns only our own PID → no duplicates."""
        import main as main_mod
        own_pid = os.getpid()
        with patch("subprocess.run", return_value=_make_pgrep_result([own_pid])):
            result = main_mod._scan_for_duplicate_main_processes()
        assert result == []

    def test_other_process_found_returns_their_pid(self):
        """pgrep returns another PID → detected as duplicate."""
        import main as main_mod
        other_pid = 99999
        own_pid = os.getpid()
        with patch("subprocess.run", return_value=_make_pgrep_result([own_pid, other_pid])):
            result = main_mod._scan_for_duplicate_main_processes()
        assert result == [other_pid]

    def test_multiple_other_processes_returns_all(self):
        """pgrep returns multiple other PIDs → all returned."""
        import main as main_mod
        other_pids = [11111, 22222, 33333]
        own_pid = os.getpid()
        with patch("subprocess.run", return_value=_make_pgrep_result([own_pid] + other_pids)):
            result = main_mod._scan_for_duplicate_main_processes()
        assert set(result) == set(other_pids)

    def test_pgrep_not_found_returns_empty(self):
        """If pgrep is unavailable (FileNotFoundError), silently returns empty."""
        import main as main_mod
        with patch("subprocess.run", side_effect=FileNotFoundError("pgrep not found")):
            result = main_mod._scan_for_duplicate_main_processes()
        assert result == []

    def test_pgrep_empty_output_returns_empty(self):
        """pgrep returns nothing (no matching processes) → no duplicates."""
        import main as main_mod
        with patch("subprocess.run", return_value=_make_pgrep_result([])):
            result = main_mod._scan_for_duplicate_main_processes()
        assert result == []

    def test_pgrep_called_with_correct_pattern(self):
        """Verify pgrep is called searching for python main.py processes."""
        import main as main_mod
        own_pid = os.getpid()
        with patch("subprocess.run", return_value=_make_pgrep_result([own_pid])) as mock_run:
            main_mod._scan_for_duplicate_main_processes()
        call_args = mock_run.call_args
        cmd = call_args[0][0]  # first positional arg is the command list
        assert "pgrep" in cmd[0]
        # Should search for main.py pattern
        assert any("main.py" in arg for arg in cmd)

    def test_own_pid_excluded_from_results(self):
        """Our own PID must never appear in the result list."""
        import main as main_mod
        own_pid = os.getpid()
        with patch("subprocess.run", return_value=_make_pgrep_result([own_pid])):
            result = main_mod._scan_for_duplicate_main_processes()
        assert own_pid not in result

    def test_corrupt_pgrep_output_returns_empty(self):
        """If pgrep output contains non-integer lines, skip them gracefully."""
        import main as main_mod
        mock = MagicMock()
        mock.stdout = "not-a-pid\n12345abc\n"
        with patch("subprocess.run", return_value=mock):
            result = main_mod._scan_for_duplicate_main_processes()
        assert result == []


# ── _acquire_bot_lock with duplicate scan ────────────────────────────────


class TestAcquireBotLockWithProcessScan:
    """Tests that _acquire_bot_lock exits when duplicate processes exist."""

    @pytest.fixture(autouse=True)
    def temp_pid_file(self, tmp_path, monkeypatch):
        """Route _PID_FILE to a temp location so tests don't touch bot.pid."""
        import main as main_mod
        fake_pid_file = tmp_path / "test_bot.pid"
        monkeypatch.setattr(main_mod, "_PID_FILE", fake_pid_file)
        yield fake_pid_file
        if fake_pid_file.exists():
            fake_pid_file.unlink()

    def test_exits_when_duplicate_process_found(self, temp_pid_file):
        """If _scan_for_duplicate_main_processes returns PIDs, _acquire_bot_lock exits."""
        import main as main_mod
        other_pid = 77777
        with patch.object(main_mod, "_scan_for_duplicate_main_processes", return_value=[other_pid]):
            with pytest.raises(SystemExit):
                main_mod._acquire_bot_lock()

    def test_no_exit_when_no_duplicates(self, temp_pid_file):
        """If no duplicates found, _acquire_bot_lock proceeds and writes PID file."""
        import main as main_mod
        with patch.object(main_mod, "_scan_for_duplicate_main_processes", return_value=[]):
            result = main_mod._acquire_bot_lock()
        assert temp_pid_file.exists()
        assert int(temp_pid_file.read_text().strip()) == os.getpid()

    def test_exits_when_pid_file_has_live_pid(self, temp_pid_file, monkeypatch):
        """Existing bot.pid with a live PID → sys.exit (existing check)."""
        import main as main_mod
        fake_pid = 11111
        temp_pid_file.write_text(str(fake_pid))
        # Simulate the process being alive
        with patch("os.kill", return_value=None):  # os.kill(pid, 0) doesn't raise → alive
            with patch.object(main_mod, "_scan_for_duplicate_main_processes", return_value=[]):
                with pytest.raises(SystemExit):
                    main_mod._acquire_bot_lock()

    def test_proceeds_when_pid_file_has_stale_pid(self, temp_pid_file):
        """Existing bot.pid with dead PID → overwrite (stale, safe)."""
        import main as main_mod
        temp_pid_file.write_text("99999999")  # Very high PID unlikely to exist
        with patch("os.kill", side_effect=ProcessLookupError()):
            with patch.object(main_mod, "_scan_for_duplicate_main_processes", return_value=[]):
                result = main_mod._acquire_bot_lock()
        assert int(temp_pid_file.read_text().strip()) == os.getpid()
