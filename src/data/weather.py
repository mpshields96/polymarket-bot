"""
Weather forecast feed — Open-Meteo GFS + NWS ensemble.

JOB:    Fetch daily maximum temperature forecast from two free sources.
        Blend with configurable weights for a more reliable ensemble signal.
        Cache both feeds. Provide forecast_temp_f() and forecast_std_f().

DOES NOT: Make trading decisions, know about Kalshi, place orders.

SOURCES:
  Open-Meteo (https://open-meteo.com) — free, no key, GFS-based global model.
  NWS/Weather.gov (https://api.weather.gov) — free, no key, NDFD model, US-only.
    NWS requires User-Agent header per their ToS (we send our bot identifier).

ENSEMBLE:
  Default: equal-weight average (0.5 + 0.5) until we have calibration data.
  Approach: 1/MAE weighted blend per JHenzi/weatherbots methodology.
  Fallback: if one source fails, use the other at full weight.

UNCERTAINTY:
  Open-Meteo single-value forecast — uses calibrated 3.5°F std dev.
  When both sources agree (|diff| < 1°F): reduce std dev to 2.5°F (higher confidence).
  When sources diverge (|diff| > 4°F): increase std dev to 5.0°F (lower confidence).

Adapted from: NOAA/NWS probability of temperature exceedance methodology.
Reference:    jazzmine-p/weather-forecast-automated-trading (NCEI + LSTM approach)
Reference:    JHenzi/weatherbots (8-source MAE-weighted ensemble)
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
_NWS_POINTS_URL = "https://api.weather.gov/points/{lat},{lon}"
_DEFAULT_REFRESH_INTERVAL_SEC = 1800   # 30 min — forecast changes slowly
_DEFAULT_FORECAST_STD_F = 3.5          # Calibrated 1-day NWP uncertainty (°F)
_REQUEST_TIMEOUT_SEC = 10
_NWS_USER_AGENT = "polymarket-bot/1.0 (automated-trading; paper-mode)"


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


# ── NWS feed ──────────────────────────────────────────────────────────


class NWSFeed:
    """
    NOAA/NWS daily high-temperature forecast.

    Fetches from api.weather.gov (free, no key, US-only).
    Two-step process: resolve grid point → fetch forecast.
    Caches forecast URL after first resolve to avoid repeated point lookups.

    NWS requires a User-Agent per their ToS — we use our bot identifier.
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        city_name: str = "",
        forecast_std_f: float = _DEFAULT_FORECAST_STD_F,
        refresh_interval_seconds: float = _DEFAULT_REFRESH_INTERVAL_SEC,
    ):
        self._lat = latitude
        self._lon = longitude
        self.city_name = city_name
        self._forecast_std_f = forecast_std_f
        self._refresh_interval = refresh_interval_seconds

        self._forecast_url: Optional[str] = None  # resolved after first call
        self._forecast_temp_f: Optional[float] = None
        self._forecast_date: Optional[str] = None
        self._last_fetch_ts: float = 0.0

    @property
    def is_stale(self) -> bool:
        return (time.monotonic() - self._last_fetch_ts) > self._refresh_interval

    def forecast_temp_f(self) -> Optional[float]:
        return self._forecast_temp_f

    def forecast_std_f(self) -> float:
        return self._forecast_std_f

    def _resolve_forecast_url(self) -> Optional[str]:
        """Resolve lat/lon to NWS forecast URL (cached after first call)."""
        if self._forecast_url:
            return self._forecast_url
        url = _NWS_POINTS_URL.format(lat=round(self._lat, 4), lon=round(self._lon, 4))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _NWS_USER_AGENT})
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode())
            self._forecast_url = data["properties"]["forecast"]
            return self._forecast_url
        except Exception as exc:
            logger.warning("[weather/nws] Failed to resolve NWS grid point: %s", exc)
            return None

    def refresh(self) -> bool:
        """Fetch today's predicted high temperature from NWS. Blocking (~200ms)."""
        forecast_url = self._resolve_forecast_url()
        if not forecast_url:
            return False
        try:
            req = urllib.request.Request(forecast_url, headers={"User-Agent": _NWS_USER_AGENT})
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
                data = json.loads(resp.read().decode())

            periods = data.get("properties", {}).get("periods", [])
            if not periods:
                logger.warning("[weather/nws] No forecast periods returned")
                return False

            # Find the first daytime period (today's high) or tonight's period
            # NWS 12-hourly: periods[0] = today daytime, periods[1] = tonight, etc.
            daytime_periods = [p for p in periods if p.get("isDaytime", False)]
            if not daytime_periods:
                logger.warning("[weather/nws] No daytime periods in NWS forecast")
                return False

            period = daytime_periods[0]
            temp = period.get("temperature")
            unit = period.get("temperatureUnit", "F")
            if temp is None:
                return False

            # Convert to Fahrenheit if needed
            temp_f = float(temp) if unit == "F" else float(temp) * 9.0 / 5.0 + 32.0
            self._forecast_temp_f = temp_f
            self._forecast_date = period.get("startTime", "")[:10]  # "YYYY-MM-DD"
            self._last_fetch_ts = time.monotonic()

            logger.info(
                "[weather/nws] %s forecast: %.1f°F (%s)",
                self.city_name or f"({self._lat},{self._lon})",
                temp_f, period.get("name", ""),
            )
            return True

        except Exception as exc:
            logger.warning("[weather/nws] Failed to fetch NWS forecast: %s", exc)
            # Reset cached URL on error in case it changed
            self._forecast_url = None
            return False


# ── Ensemble feed ──────────────────────────────────────────────────────


class EnsembleWeatherFeed:
    """
    MAE-weighted ensemble of multiple weather feeds.

    Default: equal-weight blend of Open-Meteo + NWS (0.5 + 0.5).
    Adapts uncertainty based on source agreement:
      - Sources agree (|diff| < 1°F)  → std_dev 2.5°F (more confident)
      - Sources diverge (|diff| > 4°F) → std_dev 5.0°F (less confident)
      - Otherwise: std_dev from config (default 3.5°F)

    Falls back gracefully: if one source fails, uses the other at full weight.

    Exposes the same interface as WeatherFeed (drop-in replacement).
    """

    def __init__(
        self,
        open_meteo: WeatherFeed,
        nws: NWSFeed,
        weights: tuple = (0.5, 0.5),
        forecast_std_f: float = _DEFAULT_FORECAST_STD_F,
        city_name: str = "",
    ):
        self._open_meteo = open_meteo
        self._nws = nws
        self._weights = weights  # (open_meteo_weight, nws_weight)
        self._base_std_f = forecast_std_f
        self.city_name = city_name
        self._forecast_temp_f: Optional[float] = None
        self._forecast_std_f: float = forecast_std_f
        self._last_fetch_ts: float = 0.0

    @property
    def is_stale(self) -> bool:
        return self._open_meteo.is_stale and self._nws.is_stale

    def forecast_temp_f(self) -> Optional[float]:
        return self._forecast_temp_f

    def forecast_std_f(self) -> float:
        return self._forecast_std_f

    def forecast_date(self) -> Optional[str]:
        return self._open_meteo.forecast_date()

    def refresh(self) -> bool:
        """Refresh both sources and compute weighted ensemble. Blocking."""
        om_ok = self._open_meteo.refresh() if self._open_meteo.is_stale else True
        nws_ok = self._nws.refresh() if self._nws.is_stale else True

        om_temp = self._open_meteo.forecast_temp_f()
        nws_temp = self._nws.forecast_temp_f()

        if om_temp is None and nws_temp is None:
            logger.warning("[weather/ensemble] Both sources failed — no forecast available")
            return False

        if om_temp is not None and nws_temp is not None:
            # Both available: weighted blend
            w_om, w_nws = self._weights
            total_w = w_om + w_nws
            self._forecast_temp_f = (w_om * om_temp + w_nws * nws_temp) / total_w

            diff = abs(om_temp - nws_temp)
            if diff < 1.0:
                self._forecast_std_f = max(2.5, self._base_std_f - 1.0)   # agreement → tighter
            elif diff > 4.0:
                self._forecast_std_f = min(6.0, self._base_std_f + 1.5)   # disagreement → wider
            else:
                self._forecast_std_f = self._base_std_f

            logger.info(
                "[weather/ensemble] %s blended: %.1f°F (OM=%.1f NWS=%.1f diff=%.1f std=%.1f)",
                self.city_name, self._forecast_temp_f, om_temp, nws_temp,
                diff, self._forecast_std_f,
            )
        elif om_temp is not None:
            # Only Open-Meteo available
            self._forecast_temp_f = om_temp
            self._forecast_std_f = self._base_std_f + 0.5   # single source → slightly wider
            logger.info("[weather/ensemble] NWS unavailable, using Open-Meteo: %.1f°F", om_temp)
        else:
            # Only NWS available
            self._forecast_temp_f = nws_temp
            self._forecast_std_f = self._base_std_f + 0.5
            logger.info("[weather/ensemble] Open-Meteo unavailable, using NWS: %.1f°F", nws_temp)

        self._last_fetch_ts = time.monotonic()
        return True


# ── Factory ───────────────────────────────────────────────────────────


def load_nyc_weather_from_config() -> EnsembleWeatherFeed:
    """
    Build EnsembleWeatherFeed (Open-Meteo + NWS) for NYC from config.yaml.

    Returns an ensemble feed that blends both sources with equal weights.
    Falls back gracefully if either source is unavailable.
    """
    import yaml

    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        logger.warning("config.yaml not found, using WeatherFeed NYC defaults")
        return EnsembleWeatherFeed(
            open_meteo=WeatherFeed(**CITY_NYC),
            nws=NWSFeed(latitude=CITY_NYC["latitude"], longitude=CITY_NYC["longitude"],
                        city_name="NYC"),
            city_name="NYC",
        )

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
    std_f = w.get("forecast_std_f", _DEFAULT_FORECAST_STD_F)
    refresh_sec = w.get("refresh_interval_seconds", _DEFAULT_REFRESH_INTERVAL_SEC)

    open_meteo = WeatherFeed(
        **city_params,
        forecast_std_f=std_f,
        refresh_interval_seconds=refresh_sec,
    )
    nws = NWSFeed(
        latitude=city_params["latitude"],
        longitude=city_params["longitude"],
        city_name=city_params.get("city_name", city.upper()),
        forecast_std_f=std_f,
        refresh_interval_seconds=refresh_sec,
    )
    return EnsembleWeatherFeed(
        open_meteo=open_meteo,
        nws=nws,
        forecast_std_f=std_f,
        city_name=city_params.get("city_name", city.upper()),
    )
