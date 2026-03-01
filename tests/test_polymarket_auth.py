"""
Tests for Polymarket Ed25519 auth module.

Covers:
- Key loading from raw bytes and base64
- Signature format and reproducibility
- Header generation (correct keys, timestamp freshness)
- load_from_env() failure modes
- Signature is verifiable with corresponding public key
"""

from __future__ import annotations

import base64
import os
import time

import pytest

# ── helpers ───────────────────────────────────────────────────────


def _make_test_key_b64() -> str:
    """Generate a fresh Ed25519 key pair and return secret key as base64."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    pk = Ed25519PrivateKey.generate()
    # Export seed (32 bytes) + public key (32 bytes) → 64 bytes → base64
    seed = pk.private_bytes_raw()  # 32 bytes
    pub = pk.public_key().public_bytes_raw()  # 32 bytes
    return base64.b64encode(seed + pub).decode()


_TEST_KEY_B64 = _make_test_key_b64()
_TEST_KEY_ID  = "test-key-id-0000-0000-0000"


# ── PolymarketAuth unit tests ─────────────────────────────────────


class TestPolymarketAuth:
    def test_loads_from_64_byte_b64_key(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        assert auth.key_id == _TEST_KEY_ID

    def test_loads_from_32_byte_b64_key(self):
        """Seed-only (32-byte) keys are also valid."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        seed = Ed25519PrivateKey.generate().private_bytes_raw()
        seed_b64 = base64.b64encode(seed).decode()
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=seed_b64)
        assert auth.key_id == _TEST_KEY_ID

    def test_raises_on_empty_key_id(self):
        from src.auth.polymarket_auth import PolymarketAuth
        with pytest.raises(ValueError, match="key_id"):
            PolymarketAuth(key_id="", secret_key_b64=_TEST_KEY_B64)

    def test_raises_on_empty_secret(self):
        from src.auth.polymarket_auth import PolymarketAuth
        with pytest.raises(ValueError, match="secret_key"):
            PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64="")

    def test_raises_on_invalid_base64(self):
        from src.auth.polymarket_auth import PolymarketAuth
        with pytest.raises(Exception):
            PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64="not_valid_base64!!!")

    def test_raises_on_wrong_key_size(self):
        """Keys that are neither 32 nor 64 bytes should fail."""
        from src.auth.polymarket_auth import PolymarketAuth
        bad_b64 = base64.b64encode(b"\x00" * 16).decode()
        with pytest.raises(ValueError, match="16"):
            PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=bad_b64)

    def test_headers_returns_three_required_keys(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("GET", "/markets")
        assert "X-PM-Access-Key" in hdrs
        assert "X-PM-Timestamp" in hdrs
        assert "X-PM-Signature" in hdrs

    def test_access_key_matches_key_id(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("GET", "/markets")
        assert hdrs["X-PM-Access-Key"] == _TEST_KEY_ID

    def test_timestamp_is_unix_ms(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        before = int(time.time() * 1000)
        hdrs = auth.headers("GET", "/markets")
        after = int(time.time() * 1000)
        ts = int(hdrs["X-PM-Timestamp"])
        assert before <= ts <= after, f"Timestamp {ts} not in [{before}, {after}]"

    def test_signature_is_valid_base64(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("GET", "/markets")
        # Should not raise
        decoded = base64.b64decode(hdrs["X-PM-Signature"])
        assert len(decoded) == 64  # Ed25519 signature is always 64 bytes

    def test_signature_is_verifiable(self):
        """Signature must verify against the public key."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("POST", "/order")
        ts = hdrs["X-PM-Timestamp"]
        sig_bytes = base64.b64decode(hdrs["X-PM-Signature"])
        message = f"{ts}POST/order".encode("utf-8")
        # Re-derive public key from same b64
        raw = base64.b64decode(_TEST_KEY_B64)
        pk = Ed25519PrivateKey.from_private_bytes(raw[:32])
        pub = pk.public_key()
        # verify() raises if invalid — no exception means valid
        pub.verify(sig_bytes, message)

    def test_method_is_uppercased_in_signature(self):
        """Lowercase 'get' and 'GET' should produce the same signature."""
        from src.auth.polymarket_auth import PolymarketAuth
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        # We can't compare sigs directly (timestamp differs), but we can verify
        # both are valid signatures over the uppercased message
        hdrs_upper = auth.headers("GET", "/markets")
        hdrs_lower = auth.headers("get", "/markets")
        raw = base64.b64decode(_TEST_KEY_B64)
        pub = Ed25519PrivateKey.from_private_bytes(raw[:32]).public_key()
        # Both should verify — meaning both used the uppercased method
        for hdrs in [hdrs_upper, hdrs_lower]:
            ts = hdrs["X-PM-Timestamp"]
            sig = base64.b64decode(hdrs["X-PM-Signature"])
            pub.verify(sig, f"{ts}GET/markets".encode())

    def test_query_string_stripped_from_signature(self):
        """Signature must cover /markets not /markets?foo=bar."""
        from src.auth.polymarket_auth import PolymarketAuth
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("GET", "/markets?foo=bar&baz=1")
        ts = hdrs["X-PM-Timestamp"]
        sig = base64.b64decode(hdrs["X-PM-Signature"])
        raw = base64.b64decode(_TEST_KEY_B64)
        pub = Ed25519PrivateKey.from_private_bytes(raw[:32]).public_key()
        # Must verify against path WITHOUT query string
        pub.verify(sig, f"{ts}GET/markets".encode())

    def test_content_type_header_included(self):
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        hdrs = auth.headers("GET", "/markets")
        assert hdrs.get("Content-Type") == "application/json"

    def test_different_calls_produce_different_timestamps(self):
        """Two consecutive calls should have non-decreasing timestamps."""
        from src.auth.polymarket_auth import PolymarketAuth
        auth = PolymarketAuth(key_id=_TEST_KEY_ID, secret_key_b64=_TEST_KEY_B64)
        h1 = auth.headers("GET", "/markets")
        h2 = auth.headers("GET", "/markets")
        assert int(h2["X-PM-Timestamp"]) >= int(h1["X-PM-Timestamp"])


# ── load_from_env tests ───────────────────────────────────────────


class TestLoadFromEnv:
    def test_raises_when_key_id_missing(self, monkeypatch):
        monkeypatch.delenv("POLYMARKET_KEY_ID", raising=False)
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", _TEST_KEY_B64)
        from importlib import reload
        import src.auth.polymarket_auth as mod
        with pytest.raises(RuntimeError, match="POLYMARKET_KEY_ID"):
            mod.load_from_env()

    def test_raises_when_secret_missing(self, monkeypatch):
        monkeypatch.setenv("POLYMARKET_KEY_ID", _TEST_KEY_ID)
        monkeypatch.delenv("POLYMARKET_SECRET_KEY", raising=False)
        from importlib import reload
        import src.auth.polymarket_auth as mod
        with pytest.raises(RuntimeError, match="POLYMARKET_SECRET_KEY"):
            mod.load_from_env()

    def test_raises_when_key_id_placeholder(self, monkeypatch):
        monkeypatch.setenv("POLYMARKET_KEY_ID", "YOUR_KEY_ID_HERE")
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", _TEST_KEY_B64)
        import src.auth.polymarket_auth as mod
        with pytest.raises(RuntimeError, match="POLYMARKET_KEY_ID"):
            mod.load_from_env()

    def test_loads_successfully_with_valid_env(self, monkeypatch):
        monkeypatch.setenv("POLYMARKET_KEY_ID", _TEST_KEY_ID)
        monkeypatch.setenv("POLYMARKET_SECRET_KEY", _TEST_KEY_B64)
        import src.auth.polymarket_auth as mod
        auth = mod.load_from_env()
        assert auth.key_id == _TEST_KEY_ID
