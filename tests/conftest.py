"""
conftest.py — session-level fixtures shared across all test files.

Ensures kill_switch.lock is always clean at the start and end of a test run,
even if a previous run was interrupted (Ctrl+C, SIGKILL, etc.).
"""

import pytest
from src.risk.kill_switch import LOCK_FILE


@pytest.fixture(scope="session", autouse=True)
def clean_lock_file_at_session_start():
    """
    Remove any stale kill_switch.lock at the start of a test session.

    Without this, an interrupted previous test run can leave a lock file
    that causes `python main.py` to refuse startup after `pytest`.
    """
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
    yield
    # Also clean up at session end for good measure
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
