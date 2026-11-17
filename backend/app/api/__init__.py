from app.api.dashboard import router as dashboard_router
from app.api.feeders import router as feeders_router
from app.api.events import router as events_router
from app.api.faults import router as faults_router
from app.api.restoration import router as restoration_router
from app.api.weather import router as weather_router
from app.api.analytics import router as analytics_router

__all__ = [
    "dashboard_router",
    "feeders_router",
    "events_router",
    "faults_router",
    "restoration_router",
    "weather_router",
    "analytics_router",
]
