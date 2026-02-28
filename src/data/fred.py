"""
FRED (Federal Reserve Economic Data) feed.

JOB:    Fetch key economic indicators from the St. Louis Fed FRED API.
        Provides: current fed funds rate, 2-year treasury yield, CPI trend.
        These are the inputs for the FOMC rate decision strategy.

DOES NOT: Make trading decisions, know about Kalshi, place orders.

API:    https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES}
        Completely free, no API key required for CSV endpoint.
        Updated once per business day (approx 4:15pm ET).

KEY SERIES:
    DFF      — Effective Federal Funds Rate (daily, %)
    DGS2     — 2-Year Treasury Constant Maturity Rate (daily, %)
    CPIAUCSL — CPI for All Urban Consumers (monthly, index level)
    UNRATE   — Unemployment Rate (monthly, %)

SIGNAL LOGIC (for FOMCRateStrategy):
    yield_spread = DGS2 - DFF
    If yield_spread < -0.25% → market pricing net cuts → cut-biased
    If yield_spread > +0.25% → market pricing net hikes → hike-biased
    Else → hold-biased

    CPI trend (last 3 months): acceleration → hold-biased; deceleration → cut-biased
"""

from __future__ import annotations

import csv
import io
import logging
import time
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

_FRED_CSV_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
_REQUEST_TIMEOUT_SEC = 10
_DEFAULT_REFRESH_INTERVAL_SEC = 3600   # 1 hour — FRED updates once per day
_LOOKBACK_ROWS = 5                     # How many rows to read from end of CSV


# ── Data container ────────────────────────────────────────────────────


@dataclass
class FREDSnapshot:
    """Latest values from FRED economic indicators."""
    fed_funds_rate: float          # DFF: current effective fed funds rate (%)
    yield_2yr: float               # DGS2: 2-year Treasury yield (%)
    cpi_latest: float              # CPIAUCSL: latest monthly CPI index
    cpi_prior: float               # CPIAUCSL: prior month CPI (for trend)
    cpi_prior2: float              # CPIAUCSL: 2 months ago (for trend confirmation)
    fetched_at: datetime           # UTC timestamp of last successful fetch

    @property
    def yield_spread(self) -> float:
        """2yr yield minus fed funds rate. Negative = market expects cuts."""
        return self.yield_2yr - self.fed_funds_rate

    @property
    def cpi_mom_latest(self) -> float:
        """Month-over-month CPI change: latest vs prior (percentage points)."""
        if self.cpi_prior == 0:
            return 0.0
        return (self.cpi_latest - self.cpi_prior) / self.cpi_prior * 100.0

    @property
    def cpi_mom_prior(self) -> float:
        """Month-over-month CPI change: prior vs prior2."""
        if self.cpi_prior2 == 0:
            return 0.0
        return (self.cpi_prior - self.cpi_prior2) / self.cpi_prior2 * 100.0

    @property
    def cpi_accelerating(self) -> bool:
        """True if CPI month-over-month change is rising (inflation re-accelerating)."""
        return self.cpi_mom_latest > self.cpi_mom_prior


# ── Feed class ────────────────────────────────────────────────────────


class FREDFeed:
    """
    FRED economic indicator feed.

    Fetches DFF, DGS2, and CPIAUCSL from the FRED CSV endpoint.
    Caches for refresh_interval_seconds (default 1 hour).
    Synchronous HTTP calls (~200ms each) — not async.

    Usage:
        feed = FREDFeed()
        feed.refresh()
        snap = feed.snapshot()
        print(snap.yield_spread, snap.cpi_accelerating)
    """

    def __init__(self, refresh_interval_seconds: float = _DEFAULT_REFRESH_INTERVAL_SEC):
        self._refresh_interval = refresh_interval_seconds
        self._snapshot: Optional[FREDSnapshot] = None
        self._last_fetch_ts: float = 0.0

    @property
    def is_stale(self) -> bool:
        return (time.monotonic() - self._last_fetch_ts) > self._refresh_interval

    def snapshot(self) -> Optional[FREDSnapshot]:
        return self._snapshot

    def refresh(self) -> bool:
        """
        Fetch all series from FRED. Returns True on success.
        On partial failure, uses cached value for missing series.
        """
        try:
            dff = self._fetch_latest("DFF")
            dgs2 = self._fetch_latest("DGS2")
            cpi_rows = self._fetch_last_n("CPIAUCSL", 3)

            if dff is None or dgs2 is None or len(cpi_rows) < 3:
                logger.warning("[fred] Incomplete FRED data — dff=%s dgs2=%s cpi_rows=%d",
                               dff, dgs2, len(cpi_rows))
                return False

            self._snapshot = FREDSnapshot(
                fed_funds_rate=dff,
                yield_2yr=dgs2,
                cpi_latest=cpi_rows[0],
                cpi_prior=cpi_rows[1],
                cpi_prior2=cpi_rows[2],
                fetched_at=datetime.now(timezone.utc),
            )
            self._last_fetch_ts = time.monotonic()

            logger.info(
                "[fred] DFF=%.2f%% DGS2=%.2f%% spread=%.2f%% | "
                "CPI mom=%.3f%% (was %.3f%%) %s",
                dff, dgs2, self._snapshot.yield_spread,
                self._snapshot.cpi_mom_latest,
                self._snapshot.cpi_mom_prior,
                "↑ accel" if self._snapshot.cpi_accelerating else "↓ decel",
            )
            return True

        except Exception as exc:
            logger.warning("[fred] Refresh failed: %s", exc)
            return False

    # ── Private helpers ───────────────────────────────────────────────

    def _fetch_csv(self, series_id: str) -> list[tuple[str, float]]:
        """Fetch FRED CSV series and return list of (date, value) pairs, newest first."""
        url = f"{_FRED_CSV_BASE}{series_id}"
        req = urllib.request.Request(url, headers={"User-Agent": "polymarket-bot/1.0"})
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
            content = resp.read().decode("utf-8")

        rows = []
        reader = csv.reader(io.StringIO(content))
        next(reader)   # skip header
        for row in reader:
            if len(row) < 2 or row[1].strip() in (".", ""):
                continue   # FRED uses "." for missing values
            try:
                rows.append((row[0], float(row[1])))
            except ValueError:
                continue

        return list(reversed(rows))   # newest first

    def _fetch_latest(self, series_id: str) -> Optional[float]:
        """Return the most recent non-missing value for a FRED series."""
        try:
            rows = self._fetch_csv(series_id)
            if not rows:
                return None
            return rows[0][1]
        except Exception as exc:
            logger.warning("[fred] Failed to fetch %s: %s", series_id, exc)
            return None

    def _fetch_last_n(self, series_id: str, n: int) -> list[float]:
        """Return the last N non-missing values for a FRED series (newest first)."""
        try:
            rows = self._fetch_csv(series_id)
            return [v for _, v in rows[:n]]
        except Exception as exc:
            logger.warning("[fred] Failed to fetch %s: %s", series_id, exc)
            return []


# ── Factory ───────────────────────────────────────────────────────────


def load_from_config() -> FREDFeed:
    """Build FREDFeed from config.yaml strategy.fomc section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return FREDFeed()

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    fomc = cfg.get("strategy", {}).get("fomc", {})
    return FREDFeed(
        refresh_interval_seconds=fomc.get("fred_refresh_interval_seconds", _DEFAULT_REFRESH_INTERVAL_SEC),
    )
