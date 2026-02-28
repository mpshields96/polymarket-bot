"""
Open-Meteo weather forecast feed.

JOB:    Fetch daily maximum temperature forecast from Open-Meteo's free API.
        Cache the forecast for a configurable interval (default 30 min).
        Provide forecast_temp_f() and forecast_std_f() to strategy callers.

DOES NOT: Make trading decisions, know about Kalshi, place orders.

API:    https://open-meteo.com/en/docs — completely free, no key needed.
        Uses standard GFS-based forecast model.
        Uncertainty (std_dev_f) is configurable — Open-Meteo single-value forecast
        doesn't expose ensemble spread directly, so we use a calibrated default
        of 3.5°F for 1-day ahead (typical NWP daily high MAE for major US cities).

Adapted from: NOAA/NWS probability of temperature exceedance methodology.
Reference:    jazzmine-p/weather-forecast-automated-trading (NCEI + LSTM approach)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
_DEFAULT_REFRESH_INTERVAL_SEC = 1800   # 30 min — forecast changes slowly
_DEFAULT_FORECAST_STD_F = 3.5          # Calibrated 1-day NWP uncertainty (°F)
_REQUEST_TIMEOUT_SEC = 10


# ── City presets ──────────────────────────────────────────────────────


CITY_NYC = {"latitude": 40.71, "longitude": -74.01, "timezone": "America/New_York", "city_name": "NYC"}
CITY_CHI = {"latitude": 41.88, "longitude": -87.63, "timezone": "America/Chicago",  "city_name": "CHI"}
CITY_LA  = {"latitude": 34.05, "longitude": -118.24, "timezone": "America/Los_Angeles", "city_name": "LA"}
CITY_PHX = {"latitude": 33.45, "longitude": -112.07, "timezone": "America/Phoenix", "city_name": "PHX"}
CITY_DAL = {"latitude": 32.78, "longitude": -96.80,  "timezone": "America/Chicago",  "city_name": "DAL"}


class WeatherFeed:
    """
    Daily temperature forecast from Open-Meteo.

    Fetches tomorrow's predicted daily maximum temperature via HTTPS (synchronous).
    Auto-refreshes after refresh_interval_seconds.

    Usage (synchronous refresh — caller decides when to refresh):
        feed = WeatherFeed(**CITY_NYC)
        feed.refresh()               # blocks ~100ms
        temp = feed.forecast_temp_f()  # float, °F
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        city_name: str = "",
        forecast_std_f: float = _DEFAULT_FORECAST_STD_F,
        refresh_interval_seconds: float = _DEFAULT_REFRESH_INTERVAL_SEC,
    ):
        self._lat = latitude
        self._lon = longitude
        self._tz = timezone
        self.city_name = city_name
        self._forecast_std_f = forecast_std_f
        self._refresh_interval = refresh_interval_seconds

        self._forecast_temp_f: Optional[float] = None
        self._forecast_date: Optional[str] = None   # "YYYY-MM-DD"
        self._last_fetch_ts: float = 0.0

    # ── Public interface ──────────────────────────────────────────────

    @property
    def is_stale(self) -> bool:
        """True if no data has been fetched yet or cache has expired."""
        return (time.monotonic() - self._last_fetch_ts) > self._refresh_interval

    def forecast_temp_f(self) -> Optional[float]:
        """Return the forecasted daily max temperature in °F, or None if not yet fetched."""
        return self._forecast_temp_f

    def forecast_std_f(self) -> float:
        """Return the uncertainty (standard deviation) of the forecast in °F."""
        return self._forecast_std_f

    def forecast_date(self) -> Optional[str]:
        """Return the date the forecast is for, as 'YYYY-MM-DD'."""
        return self._forecast_date

    def refresh(self) -> bool:
        """
        Fetch the latest forecast from Open-Meteo. Blocking (~100ms).

        Returns True on success, False on any error (stale data is retained).
        """
        url = (
            f"{_OPEN_METEO_URL}"
            f"?latitude={self._lat}"
            f"&longitude={self._lon}"
            f"&daily=temperature_2m_max"
            f"&temperature_unit=fahrenheit"
            f"&timezone={self._tz}"
            f"&forecast_days=2"   # today + tomorrow
        )

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "polymarket-bot/1.0"})
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode())

            temps = data["daily"]["temperature_2m_max"]   # list of floats
            dates = data["daily"]["time"]                  # list of "YYYY-MM-DD"

            if not temps or len(temps) < 1:
                logger.warning("[weather] Open-Meteo returned no temperature data")
                return False

            # Use tomorrow's forecast if available (index 1), else today (index 0)
            idx = 1 if len(temps) > 1 else 0
            self._forecast_temp_f = float(temps[idx])
            self._forecast_date = dates[idx]
            self._last_fetch_ts = time.monotonic()

            logger.info(
                "[weather] %s forecast: %.1f°F for %s",
                self.city_name or f"({self._lat},{self._lon})",
                self._forecast_temp_f,
                self._forecast_date,
            )
            return True

        except Exception as exc:
            logger.warning("[weather] Failed to fetch Open-Meteo forecast: %s", exc)
            return False


# ── Factory ───────────────────────────────────────────────────────────


def load_nyc_weather_from_config() -> WeatherFeed:
    """Build WeatherFeed for NYC from config.yaml strategy.weather section."""
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using WeatherFeed NYC defaults")
        return WeatherFeed(**CITY_NYC)

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    w = cfg.get("strategy", {}).get("weather", {})
    city = w.get("city", "nyc").lower()

    city_map = {
        "nyc": CITY_NYC, "new_york": CITY_NYC, "new york": CITY_NYC,
        "chi": CITY_CHI, "chicago": CITY_CHI,
        "la": CITY_LA, "los_angeles": CITY_LA,
        "phx": CITY_PHX, "phoenix": CITY_PHX,
        "dal": CITY_DAL, "dallas": CITY_DAL,
    }
    city_params = city_map.get(city, CITY_NYC)

    return WeatherFeed(
        **city_params,
        forecast_std_f=w.get("forecast_std_f", _DEFAULT_FORECAST_STD_F),
        refresh_interval_seconds=w.get("refresh_interval_seconds", _DEFAULT_REFRESH_INTERVAL_SEC),
    )
