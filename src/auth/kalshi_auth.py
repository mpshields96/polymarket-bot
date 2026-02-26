"""
Kalshi RSA-PSS authentication.

This module ONLY handles signing and header generation.
It does NOT make HTTP calls, know about markets, or touch config.

Signing logic adapted from:
# Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

logger = logging.getLogger(__name__)

# Never log the key itself — only log that it was loaded
_KEY_LOAD_CONFIRMED = "Kalshi private key loaded (path={path}, key_size={bits} bits)"


class KalshiAuth:
    """
    RSA-PSS signer for Kalshi API requests.

    Every Kalshi request needs three headers:
      KALSHI-ACCESS-KEY:       your API key ID
      KALSHI-ACCESS-TIMESTAMP: unix timestamp in milliseconds (string)
      KALSHI-ACCESS-SIGNATURE: base64(RSA-PSS-SHA256(timestamp + METHOD + path))

    The signed message is: str(timestamp_ms) + METHOD.upper() + path_without_query
    """

    def __init__(self, api_key_id: str, private_key_path: str):
        if not api_key_id:
            raise ValueError("KALSHI_API_KEY_ID is empty — check your .env file")
        if not private_key_path:
            raise ValueError("KALSHI_PRIVATE_KEY_PATH is empty — check your .env file")

        self._api_key_id = api_key_id
        self._private_key = self._load_key(private_key_path)

    @staticmethod
    def _load_key(path: str) -> rsa.RSAPrivateKey:
        """Load RSA private key from PEM file. Never logs key contents."""
        key_path = Path(path)
        if not key_path.exists():
            raise FileNotFoundError(
                f"Kalshi private key not found at: {key_path.resolve()}\n"
                "Save your downloaded key as kalshi_private_key.pem in the project folder."
            )
        with open(key_path, "rb") as f:
            key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )
        key_size = key.key_size  # type: ignore[union-attr]
        logger.info(_KEY_LOAD_CONFIRMED.format(path=key_path.name, bits=key_size))
        return key  # type: ignore[return-value]

    def _sign(self, timestamp_ms: str, method: str, path: str) -> str:
        """
        RSA-PSS sign: timestamp_ms + METHOD + path_without_query_string.

        Adapted from: https://github.com/Bh-Ayush/Kalshi-CryptoBot
        """
        path_clean = path.split("?")[0]  # strip query params — do NOT include them
        message = (timestamp_ms + method.upper() + path_clean).encode("utf-8")
        signature = self._private_key.sign(  # type: ignore[union-attr]
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")

    def headers(self, method: str, path: str) -> dict[str, str]:
        """
        Return auth headers for a Kalshi request.

        Args:
            method: HTTP method e.g. "GET", "POST"
            path:   Full API path e.g. "/trade-api/v2/markets"
                    Query string is stripped before signing.

        Returns:
            Dict of headers to merge into the request.
        """
        ts = str(int(time.time() * 1000))
        sig = self._sign(ts, method, path)
        return {
            "KALSHI-ACCESS-KEY": self._api_key_id,
            "KALSHI-ACCESS-SIGNATURE": sig,
            "KALSHI-ACCESS-TIMESTAMP": ts,
            "Content-Type": "application/json",
        }

    @property
    def key_id(self) -> str:
        return self._api_key_id


def load_from_env() -> KalshiAuth:
    """
    Create KalshiAuth from environment variables.
    Fails loudly if credentials are missing or malformed.
    Call this once at startup.
    """
    key_id = os.getenv("KALSHI_API_KEY_ID", "").strip()
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "").strip()

    if not key_id or key_id == "YOUR_KEY_ID_HERE":
        raise RuntimeError(
            "KALSHI_API_KEY_ID not set in .env\n"
            "Copy .env.example → .env and fill in your Kalshi API key ID."
        )
    if not key_path:
        raise RuntimeError(
            "KALSHI_PRIVATE_KEY_PATH not set in .env\n"
            "Set it to the path of your kalshi_private_key.pem file."
        )

    return KalshiAuth(api_key_id=key_id, private_key_path=key_path)
