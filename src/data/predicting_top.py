"""
predicting.top leaderboard client.

JOB:    Fetch top Polymarket trader proxy wallets from predicting.top.
        Returns WhaleAccount list for use by whale_watcher.py.

DOES NOT: Execute trades, know about strategies, touch kill switch.

API facts confirmed via live probing 2026-03-01:
  GET https://predicting.top/api/leaderboard?limit=N
  Returns JSON array, no auth required.
  144/179 traders have wallet addresses in proxy format (matches data-api.polymarket.com).
  Fields: name, wallet, additional_wallets, wallet_count, smart_score, twitter, pfp,
          stats, join_date, polymarket_profile, kalshi_profile

Rate limit: Unknown — treat conservatively. Call at most once per session startup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)

_BASE_URL = "https://predicting.top/api/leaderboard"
_DEFAULT_LIMIT = 50
_DEFAULT_TIMEOUT_SEC = 10.0


@dataclass
class WhaleAccount:
    """
    A top Polymarket trader tracked by predicting.top.

    proxy_wallet is the address format expected by data-api.polymarket.com.
    all_wallets includes the primary wallet plus any additional_wallets —
    useful for multi-wallet traders who split positions.
    """

    name: str
    proxy_wallet: str          # primary wallet — use with data-api /trades?user=
    all_wallets: List[str]     # primary + additional_wallets
    smart_score: float
    twitter: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "WhaleAccount":
        """Parse one entry from the predicting.top leaderboard response."""
        primary = d.get("wallet") or ""
        additional = d.get("additional_wallets") or []
        all_wallets = [w for w in ([primary] + list(additional)) if w]

        twitter = d.get("twitter") or None  # normalise empty string to None

        return cls(
            name=str(d.get("name", "")),
            proxy_wallet=primary,
            all_wallets=all_wallets,
            smart_score=float(d.get("smart_score", 0.0)),
            twitter=twitter,
            raw=d,
        )


class PredictingTopClient:
    """
    Async HTTP client for predicting.top leaderboard.

    No auth required. Call get_leaderboard() at session startup to seed
    the whale watchlist. Returns [] on any error so callers degrade gracefully.
    """

    def __init__(self, timeout_sec: float = _DEFAULT_TIMEOUT_SEC):
        self._timeout = aiohttp.ClientTimeout(total=timeout_sec)

    async def get_leaderboard(self, limit: int = _DEFAULT_LIMIT) -> List[WhaleAccount]:
        """
        Fetch top traders from predicting.top.

        Args:
            limit: max number of traders to return (default 50, max observed 179)

        Returns:
            List of WhaleAccount objects with non-empty proxy wallets.
            Empty list on any network or parse error.
        """
        url = f"{_BASE_URL}?limit={limit}"
        try:
            async with aiohttp.ClientSession(timeout=self._timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "[predicting_top] HTTP %d fetching leaderboard",
                            resp.status,
                        )
                        return []
                    data = await resp.json()
        except Exception as exc:
            logger.warning("[predicting_top] Fetch error: %s", exc)
            return []

        if not isinstance(data, list):
            logger.warning("[predicting_top] Unexpected response type: %s", type(data))
            return []

        accounts = []
        skipped = 0
        for entry in data:
            try:
                acct = WhaleAccount.from_dict(entry)
                if not acct.proxy_wallet:
                    skipped += 1
                    continue
                accounts.append(acct)
            except Exception as exc:
                logger.debug("[predicting_top] Skipping malformed entry: %s", exc)
                skipped += 1

        logger.info(
            "[predicting_top] Loaded %d whale accounts (%d skipped, no wallet)",
            len(accounts),
            skipped,
        )
        return accounts


def load_from_env() -> PredictingTopClient:
    """
    Create PredictingTopClient. No credentials required — public API.
    Factory follows project convention.
    """
    return PredictingTopClient()
