from fastapi import APIRouter
from app.services.weather_service import WeatherService
from app.schemas.schemas import WeatherResponse

router = APIRouter(prefix="/weather", tags=["Weather"])

@router.get("", response_model=WeatherResponse)
def get_weather():
    """
    Returns current weather from Open-Meteo API, or falls back to synthetic weather
    with explicit 'using sample weather' badge indicator.
    """
    data = WeatherService.get_current_weather()
    return WeatherResponse(**data)
