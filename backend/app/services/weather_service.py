import os
import requests
from typing import Dict, Any
from app.config import settings

class WeatherService:
    """
    Fetches real-time weather from Open-Meteo API with automatic fast fallback
    to synthetic demo weather data when offline or in sandbox.
    """
    _cached_weather = None

    @classmethod
    def get_current_weather(cls, lat: float = settings.DEFAULT_LATITUDE, lng: float = settings.DEFAULT_LONGITUDE) -> Dict[str, Any]:
        # Fast toggle for offline/sandbox test execution (default to false to avoid DNS blocking)
        enable_network = os.getenv("ENABLE_LIVE_WEATHER", "false").lower() in ("true", "1")

        if enable_network and not cls._cached_weather:
            params = {
                "latitude": lat,
                "longitude": lng,
                "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_gusts_10m",
                "timezone": "auto"
            }
            try:
                # Fast connection and read timeout (0.4s connect, 0.6s read)
                resp = requests.get(settings.OPEN_METEO_API_URL, params=params, timeout=(0.4, 0.6))
                if resp.status_code == 200:
                    data = resp.json().get("current", {})
                    cls._cached_weather = {
                        "latitude": lat,
                        "longitude": lng,
                        "temperature_c": float(data.get("temperature_2m", 26.0)),
                        "rainfall_mm": float(data.get("precipitation", 0.0)),
                        "wind_gust_kmh": float(data.get("wind_gusts_10m", 12.0)),
                        "wind_speed_kmh": float(data.get("wind_speed_10m", 8.0)),
                        "humidity_pct": float(data.get("relative_humidity_2m", 65.0)),
                        "is_sample_weather": False,
                        "source_label": "Live Open-Meteo API",
                        "synthetic_notice": settings.SYNTHETIC_DATA_BANNER
                    }
                    return cls._cached_weather
            except Exception:
                pass

        # Graceful fallback: Synthetic Storm Weather Record
        return {
            "latitude": lat,
            "longitude": lng,
            "temperature_c": 22.4,
            "rainfall_mm": 38.6,  # Heavy rain
            "wind_gust_kmh": 48.0, # 48 km/h gust
            "wind_speed_kmh": 29.0,
            "humidity_pct": 94.0,
            "is_sample_weather": True,
            "source_label": "Synthetic Weather Sample (Open-Meteo Fallback)",
            "synthetic_notice": settings.SYNTHETIC_DATA_BANNER
        }
