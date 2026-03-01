"""
Polymarket.us Ed25519 authentication.

This module ONLY handles signing and header generation.
It does NOT make HTTP calls, know about markets, or touch config.

Signing spec (from iOS API creation screen):
  Message:   str(timestamp_ms) + METHOD.upper() + path_without_query
  Algorithm: Ed25519
  Headers:   X-PM-Access-Key, X-PM-Timestamp, X-PM-Signature

Secret key format: base64-encoded Ed25519 private key.
  - 64 bytes (seed + public key): use first 32 bytes as seed
  - 32 bytes (seed only): use directly
"""

from __future__ import annotations

import base64
import logging
import os
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

logger = logging.getLogger(__name__)

_KEY_LOAD_CONFIRMED = "Polymarket Ed25519 key loaded (key_id={key_id}, key_bytes={n})"


class PolymarketAuth:
    """
    Ed25519 signer for Polymarket.us retail API requests.

    Every request needs three headers:
      X-PM-Access-Key:  your API key ID (UUID)
      X-PM-Timestamp:   unix timestamp in milliseconds (string)
      X-PM-Signature:   base64(Ed25519.sign(timestamp_ms + METHOD + path))

    The signed message is: str(timestamp_ms) + METHOD.upper() + path_without_query
    Body is NOT included in the signature (unlike some other exchanges).
    """

    def __init__(self, key_id: str, secret_key_b64: str):
        if not key_id:
            raise ValueError("key_id is empty — check your .env file")
        if not secret_key_b64:
            raise ValueError("secret_key_b64 is empty — check your .env file")

        self._key_id = key_id
        self._private_key = self._load_key(key_id, secret_key_b64)

    @staticmethod
    def _load_key(key_id: str, secret_key_b64: str) -> Ed25519PrivateKey:
        """
        Load Ed25519 private key from base64-encoded bytes.

        Accepts:
          - 64-byte keys (seed + public key concatenated) — takes first 32 bytes
          - 32-byte keys (seed only)

        Raises ValueError for any other size.
        """
        raw = base64.b64decode(secret_key_b64)
        n = len(raw)

        if n == 64:
            seed = raw[:32]
        elif n == 32:
            seed = raw
        else:
            raise ValueError(
                f"Ed25519 key must be 32 or 64 bytes after base64 decode, got {n}. "
                "Check POLYMARKET_SECRET_KEY in your .env file."
            )

        key = Ed25519PrivateKey.from_private_bytes(seed)
        logger.info(_KEY_LOAD_CONFIRMED.format(key_id=key_id[:8] + "...", n=n))
        return key

    def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
        """
        Ed25519 sign: timestamp_ms + METHOD + path_without_query_string.

        Returns base64-encoded 64-byte signature.
        """
        path_clean = path.split("?")[0]  # strip query params — do NOT include them
        message = (timestamp_ms + method.upper() + path_clean).encode("utf-8")
        signature = self._private_key.sign(message)
        return base64.b64encode(signature).decode("utf-8")

    def headers(self, method: str, path: str) -> dict[str, str]:
        """
        Return auth headers for a Polymarket.us request.

        Args:
            method: HTTP method e.g. "GET", "POST"
            path:   Full API path e.g. "/markets"
                    Query string is stripped before signing.

        Returns:
            Dict of headers to merge into the request.
        """
        ts = str(int(time.time() * 1000))
        sig = self._sign(ts, method, path)
        return {
            "X-PM-Access-Key": self._key_id,
            "X-PM-Timestamp": ts,
            "X-PM-Signature": sig,
            "Content-Type": "application/json",
        }

    @property
    def key_id(self) -> str:
        return self._key_id


def load_from_env() -> PolymarketAuth:
    """
    Create PolymarketAuth from environment variables.
    Fails loudly if credentials are missing or malformed.
    Call this once at startup.
    """
    key_id = os.getenv("POLYMARKET_KEY_ID", "").strip()
    secret_key = os.getenv("POLYMARKET_SECRET_KEY", "").strip()

    if not key_id or key_id == "YOUR_KEY_ID_HERE":
        raise RuntimeError(
            "POLYMARKET_KEY_ID not set in .env\n"
            "Create an API key at polymarket.us → Profile → API Keys."
        )
    if not secret_key:
        raise RuntimeError(
            "POLYMARKET_SECRET_KEY not set in .env\n"
            "Copy the secret key shown once at API key creation time."
        )

    return PolymarketAuth(key_id=key_id, secret_key_b64=secret_key)
