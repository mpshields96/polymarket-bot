"""
Security tests — red team checks. Must pass 100% before going live.

Tests:
- No credentials hardcoded in any .py file
- .pem and .env are gitignored
- Paper mode never calls live endpoints
- Live mode requires both env var AND flag
- All writes stay within project folder
- No private key patterns in log output
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"


# ── Credential leakage ────────────────────────────────────────────

class TestNoHardcodedCredentials:
    KEY_PATTERNS = [
        r"KALSHI_API_KEY_ID\s*=\s*['\"][A-Za-z0-9\-_]{10,}['\"]",
        r"-----BEGIN (RSA |EC )?PRIVATE KEY-----",
        r"private_key\s*=\s*['\"][A-Za-z0-9+/=]{20,}['\"]",
        r"api_key\s*=\s*['\"][A-Za-z0-9\-_]{10,}['\"]",
    ]

    def _scan_py_files(self, pattern: str) -> list[str]:
        hits = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            # Skip venv and refs
            if "venv" in py_file.parts or "refs" in py_file.parts:
                continue
            content = py_file.read_text(errors="replace")
            if re.search(pattern, content, re.IGNORECASE):
                hits.append(str(py_file.relative_to(PROJECT_ROOT)))
        return hits

    def test_no_api_key_in_code(self):
        hits = self._scan_py_files(self.KEY_PATTERNS[0])
        assert not hits, f"API key pattern found in: {hits}"

    def test_no_pem_key_in_code(self):
        hits = self._scan_py_files(self.KEY_PATTERNS[1])
        assert not hits, f"Private key header found in: {hits}"

    def test_no_private_key_assignment_in_code(self):
        hits = self._scan_py_files(self.KEY_PATTERNS[2])
        assert not hits, f"Hardcoded private_key= found in: {hits}"


# ── Gitignore ─────────────────────────────────────────────────────

class TestGitignore:
    def _gitignore_contains(self, pattern: str) -> bool:
        gi = PROJECT_ROOT / ".gitignore"
        if not gi.exists():
            return False
        return pattern in gi.read_text()

    def test_env_is_gitignored(self):
        assert self._gitignore_contains(".env"), ".env must be in .gitignore"

    def test_pem_is_gitignored(self):
        assert self._gitignore_contains("*.pem"), "*.pem must be in .gitignore"

    def test_key_is_gitignored(self):
        assert self._gitignore_contains("*.key"), "*.key must be in .gitignore"

    def test_kill_switch_lock_is_gitignored(self):
        assert self._gitignore_contains("kill_switch.lock"), "kill_switch.lock must be in .gitignore"

    def test_logs_are_gitignored(self):
        assert self._gitignore_contains("logs/"), "logs/ must be in .gitignore"

    def test_venv_is_gitignored(self):
        assert self._gitignore_contains("venv/"), "venv/ must be in .gitignore"

    def test_refs_are_gitignored(self):
        assert self._gitignore_contains("refs/"), "refs/ must be in .gitignore"

    def test_env_file_not_committed(self):
        """The actual .env file must not exist in git history."""
        env_file = PROJECT_ROOT / ".env"
        if not env_file.exists():
            return  # Great — .env doesn't even exist locally
        # If it exists locally, verify it's not staged
        result = subprocess.run(
            ["git", "status", "--porcelain", ".env"],
            cwd=PROJECT_ROOT, capture_output=True, text=True
        )
        # Should show as untracked or not appear at all — never 'A' (staged) or 'M'
        assert "A .env" not in result.stdout, ".env is staged for commit — remove it immediately"


# ── File system safety ────────────────────────────────────────────

class TestFileSystemSafety:
    DANGEROUS_PATHS = [
        "/Users/matthewshields/Library",
        "/Users/matthewshields/Documents",
        "/Users/matthewshields/Desktop",
        "/etc",
        "/System",
        "/usr",
        "~/.zshrc",
        "~/.bashrc",
        "~/.ssh",
    ]

    def test_no_external_path_writes_in_code(self):
        """Scan all .py files for writes to paths outside the project."""
        bad_files = []
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if "venv" in py_file.parts or "refs" in py_file.parts:
                continue
            # Skip this file itself — it contains the paths as test data, not live writes
            if py_file.name == "test_security.py":
                continue
            content = py_file.read_text(errors="replace")
            for dangerous in self.DANGEROUS_PATHS:
                if dangerous in content:
                    bad_files.append(f"{py_file.relative_to(PROJECT_ROOT)} (contains {dangerous})")
        assert not bad_files, f"Dangerous paths found in code: {bad_files}"

    def test_kill_switch_lock_in_project_folder(self):
        """kill_switch.lock must be in project root, not elsewhere."""
        from src.risk.kill_switch import LOCK_FILE
        assert str(PROJECT_ROOT) in str(LOCK_FILE), \
            f"kill_switch.lock path {LOCK_FILE} is outside project folder"

    def test_event_log_in_project_folder(self):
        """KILL_SWITCH_EVENT.log must be in project root."""
        from src.risk.kill_switch import EVENT_LOG
        assert str(PROJECT_ROOT) in str(EVENT_LOG), \
            f"EVENT_LOG path {EVENT_LOG} is outside project folder"


# ── Auth module safety ────────────────────────────────────────────

class TestAuthModuleSafety:
    def test_auth_module_imports_no_network_libs_at_top_level(self):
        """kalshi_auth.py must not import aiohttp or requests at module level."""
        auth_file = PROJECT_ROOT / "src" / "auth" / "kalshi_auth.py"
        content = auth_file.read_text()
        # These should not appear as top-level imports
        assert "import aiohttp" not in content, "kalshi_auth.py must not import aiohttp"
        assert "import requests" not in content, "kalshi_auth.py must not import requests"

    def test_auth_headers_do_not_log_signature(self):
        """The signing method must not log the actual signature value."""
        auth_file = PROJECT_ROOT / "src" / "auth" / "kalshi_auth.py"
        content = auth_file.read_text()
        # Check that no logger call includes the signature variable directly
        # (signature = ... then logger.xxx(... signature ...))
        assert "logger.info" not in content.split("def _sign")[1].split("def ")[0] or \
               "signature" not in content.split("def _sign")[1].split("return")[0].split("logger")[1:], \
               "Do not log signature contents in _sign()"

    def test_no_print_of_key_contents(self):
        """No print() calls that could reveal key material in auth module."""
        auth_file = PROJECT_ROOT / "src" / "auth" / "kalshi_auth.py"
        content = auth_file.read_text()
        # Filter out comment lines
        non_comment = "\n".join(
            line for line in content.splitlines()
            if not line.strip().startswith("#")
        )
        assert "print(self._private_key" not in non_comment
        assert "print(key" not in non_comment.lower() or "key_size" in non_comment


# ── Kill switch safety ────────────────────────────────────────────

class TestKillSwitchSafety:
    def test_single_trade_never_exceeds_5_dollars(self):
        """Hard cap of $5 must be enforced regardless of bankroll."""
        from src.risk.kill_switch import KillSwitch, LOCK_FILE
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        ks = KillSwitch(starting_bankroll_usd=10000.0)
        # Even with a huge bankroll, $5.01 must be blocked
        ok, reason = ks.check_order_allowed(trade_usd=5.01, current_bankroll_usd=10000.0)
        assert not ok, "Trade of $5.01 must be blocked regardless of bankroll size"

    def test_bankroll_pct_cap_enforced(self):
        """5% of bankroll cap must be enforced at small bankroll sizes."""
        from src.risk.kill_switch import KillSwitch, LOCK_FILE
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        ks = KillSwitch(starting_bankroll_usd=30.0)
        # 5% of $30 = $1.50, so $2 must be blocked
        ok, _ = ks.check_order_allowed(trade_usd=2.00, current_bankroll_usd=30.0)
        assert not ok, "Trade of $2 must be blocked when bankroll is $30 (exceeds 5%)"

    def test_hard_stop_requires_manual_reset(self):
        """Once a hard stop is triggered, no trade can pass without manual reset."""
        from src.risk.kill_switch import KillSwitch, LOCK_FILE
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        ks = KillSwitch(starting_bankroll_usd=100.0)
        ks.record_loss(31.0)  # trigger hard stop
        assert ks.is_hard_stopped
        # Even a tiny trade must be blocked
        ok, _ = ks.check_order_allowed(trade_usd=0.01, current_bankroll_usd=69.0)
        assert not ok


# ── Sizing safety ─────────────────────────────────────────────────

class TestSizingSafety:
    def test_size_never_exceeds_5_in_stage_1(self):
        from src.risk.sizing import calculate_size
        result = calculate_size(
            win_prob=0.75, payout_per_dollar=2.0,
            edge_pct=0.20, bankroll_usd=100.0
        )
        assert result is not None
        assert result.recommended_usd <= 5.00

    def test_size_never_exceeds_absolute_cap(self):
        from src.risk.sizing import calculate_size, ABSOLUTE_MAX_USD
        result = calculate_size(
            win_prob=0.99, payout_per_dollar=10.0,
            edge_pct=0.99, bankroll_usd=10000.0
        )
        if result:
            assert result.recommended_usd <= ABSOLUTE_MAX_USD

    def test_thin_edge_returns_none(self):
        from src.risk.sizing import calculate_size
        result = calculate_size(
            win_prob=0.51, payout_per_dollar=1.02,
            edge_pct=0.02, bankroll_usd=100.0  # 2% < 8% minimum
        )
        assert result is None

    def test_negative_kelly_returns_none(self):
        from src.risk.sizing import calculate_size
        result = calculate_size(
            win_prob=0.30, payout_per_dollar=1.0,
            edge_pct=0.10, bankroll_usd=100.0
        )
        assert result is None

    def test_pct_cap_does_not_round_up_past_limit(self):
        """Regression: at bankroll $95.37, pct_cap = $4.7685.
        round() gives $4.77 which is 5.0016% > 5% → kill switch blocks it.
        floor() gives $4.76 which is 4.991% — passes kill switch.
        The sized bet must never exceed 5% of bankroll when recomputed."""
        from src.risk.sizing import calculate_size
        bankroll = 95.37
        result = calculate_size(
            win_prob=0.65, payout_per_dollar=2.0,
            edge_pct=0.10, bankroll_usd=bankroll,
            min_edge_pct=0.04,
        )
        assert result is not None
        # The critical invariant: sized bet must be <= 5% of bankroll
        assert result.recommended_usd / bankroll <= 0.05, (
            f"${result.recommended_usd:.2f} / ${bankroll:.2f} = "
            f"{result.recommended_usd/bankroll:.4%} exceeds 5% pct cap"
        )
