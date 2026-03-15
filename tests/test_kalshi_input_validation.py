"""
Tests for input validation hardening in src/platforms/kalshi.py.

Covers:
  - _dollars_to_cents(): post-parse bounds check (SEC-1)
  - KalshiAPIError body truncation (SEC-2)
  - _fp_to_int(): parallel bounds check

These tests were added after the security audit (Session 74) identified
that _dollars_to_cents() returns unbounded values (e.g. 100000 cents from
"999.99") and that those values could flow into code paths without the
live.py 1-99 guard.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.platforms.kalshi import _dollars_to_cents, _fp_to_int, KalshiAPIError


# ── _dollars_to_cents bounds tests ───────────────────────────────────

class TestDollarsToCentsBounds:

    def test_normal_price_passes_through(self):
        assert _dollars_to_cents({"p": "0.5900"}, "p") == 59

    def test_zero_price_returns_zero(self):
        assert _dollars_to_cents({"p": "0.0000"}, "p") == 0

    def test_one_dollar_returns_100(self):
        assert _dollars_to_cents({"p": "1.0000"}, "p") == 100

    def test_out_of_bounds_high_returns_zero(self):
        # "999.99" would be 99999 cents — must be clamped to 0 (invalid)
        assert _dollars_to_cents({"p": "999.99"}, "p") == 0

    def test_out_of_bounds_negative_returns_zero(self):
        # Negative prices are invalid — must return 0
        assert _dollars_to_cents({"p": "-0.50"}, "p") == 0

    def test_nan_returns_zero(self):
        # "NaN" is not a valid price
        assert _dollars_to_cents({"p": "NaN"}, "p") == 0

    def test_infinity_returns_zero(self):
        # "inf" is not a valid price
        assert _dollars_to_cents({"p": "inf"}, "p") == 0

    def test_scientific_notation_large_returns_zero(self):
        # "1e10" would overflow — must return 0
        assert _dollars_to_cents({"p": "1e10"}, "p") == 0

    def test_missing_key_returns_zero(self):
        assert _dollars_to_cents({}, "p") == 0

    def test_fallback_key_used_when_primary_missing(self):
        assert _dollars_to_cents({}, "p", fallback_key="q", ) == 0
        assert _dollars_to_cents({"q": 59}, "p", fallback_key="q") == 59

    def test_legacy_int_cents_fallback(self):
        # Legacy integer cents field (test mocks use this)
        assert _dollars_to_cents({"yes_price": 72}, "yes_bid_dollars", fallback_key="yes_price") == 72

    def test_boundary_at_99_cents(self):
        assert _dollars_to_cents({"p": "0.9900"}, "p") == 99

    def test_boundary_at_1_cent(self):
        assert _dollars_to_cents({"p": "0.0100"}, "p") == 1

    def test_malformed_string_returns_zero(self):
        assert _dollars_to_cents({"p": "not_a_number"}, "p") == 0

    def test_empty_string_returns_zero(self):
        assert _dollars_to_cents({"p": ""}, "p") == 0


# ── _fp_to_int bounds tests ───────────────────────────────────────────

class TestFpToIntBounds:

    def test_normal_volume_passes_through(self):
        assert _fp_to_int({"v": "100.00"}, "v") == 100

    def test_zero_returns_zero(self):
        assert _fp_to_int({"v": "0.00"}, "v") == 0

    def test_missing_key_returns_zero(self):
        assert _fp_to_int({}, "v") == 0

    def test_nan_returns_zero(self):
        assert _fp_to_int({"v": "NaN"}, "v") == 0

    def test_negative_fp_returns_zero(self):
        # Negative volume/count is not valid
        assert _fp_to_int({"v": "-5.00"}, "v") == 0

    def test_large_value_returns_zero(self):
        # 1e15 contracts is not a valid count
        assert _fp_to_int({"v": "1e15"}, "v") == 0


# ── KalshiAPIError body truncation tests ─────────────────────────────

class TestKalshiAPIErrorTruncation:

    def test_short_body_preserved(self):
        err = KalshiAPIError(400, {"error": "bad request"})
        assert "bad request" in str(err)

    def test_long_body_truncated_in_str(self):
        long_body = {"error": "x" * 1000, "details": "y" * 1000}
        err = KalshiAPIError(400, long_body)
        # The string representation must not exceed a safe length
        assert len(str(err)) <= 600  # status prefix + truncated body

    def test_status_code_preserved(self):
        err = KalshiAPIError(429, {"error": "rate limited"})
        assert "429" in str(err)

    def test_attributes_preserved(self):
        body = {"error": "insufficient funds"}
        err = KalshiAPIError(403, body)
        assert err.status == 403
        assert err.body == body  # body attr unchanged — only str() is truncated

    def test_none_body_handled(self):
        # Kalshi occasionally returns non-JSON on some errors
        err = KalshiAPIError(500, None)
        assert "500" in str(err)

    def test_string_body_handled(self):
        err = KalshiAPIError(503, "Service Unavailable")
        assert "503" in str(err)
        assert len(str(err)) <= 600
