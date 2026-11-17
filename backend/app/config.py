import os
from typing import Optional

class Settings:
    PROJECT_NAME: str = "FaultTrace AI - Decision Support System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    SYNTHETIC_DATA_BANNER: str = "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"
    ADVISORY_DISCLAIMER: str = "Advisory: requires engineering validation and operator authorisation"
    
    # SQLite default fallback so it runs out-of-the-box without Docker
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./faulttrace.db")
    
    # Weather config
    OPEN_METEO_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    DEFAULT_LATITUDE: float = 12.9716  # Synthetic Bengaluru reference coordinate
    DEFAULT_LONGITUDE: float = 77.5946
    
    # Model Artifacts
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    MODEL_DIR: str = os.path.join(BASE_DIR, "ml_artifacts")

settings = Settings()
