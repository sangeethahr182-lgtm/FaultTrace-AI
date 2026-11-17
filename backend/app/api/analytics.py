import os
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config import settings
from app.models.models import SCADAEvent, Complaint, WeatherObservation, Feeder
from app.schemas.schemas import MLMetricsResponse

router = APIRouter(prefix="/analytics", tags=["Analytics & Model Evaluation"])

@router.get("/metrics", response_model=MLMetricsResponse)
def get_model_metrics():
    """
    Returns actual measured ML metrics from model train/test run.
    Evaluated with scenario-based split to prevent data leakage.
    Includes calibration error (ECE), calibration curve, and baseline comparisons.
    """
    metrics_file = os.path.join(settings.MODEL_DIR, "metrics.json")
    if not os.path.exists(metrics_file):
        raise HTTPException(
            status_code=404,
            detail="Model metrics report not found. Please run the training script: python -m scripts.train_model"
        )
    
    with open(metrics_file, "r") as f:
        data = json.load(f)

    return MLMetricsResponse(**data)


@router.get("/trends")
def get_operational_trends(db: Session = Depends(get_db)):
    """
    Aggregates operational trends from synthetic events and complaint logs.
    """
    # Complaints by category
    complaints = db.query(Complaint).all()
    cat_counts = {}
    source_counts = {}
    for c in complaints:
        cat_counts[c.category] = cat_counts.get(c.category, 0) + 1
        source_counts[c.source] = source_counts.get(c.source, 0) + 1

    # Weather vs Fault Correlation synthetic scatter points
    weather_corr_points = [
        {"rainfall_mm": 5.2, "wind_gust_kmh": 14.0, "fault_rate": 0.05, "label": "Clear/Mild"},
        {"rainfall_mm": 18.4, "wind_gust_kmh": 32.0, "fault_rate": 0.38, "label": "Moderate Rain"},
        {"rainfall_mm": 38.6, "wind_gust_kmh": 48.0, "fault_rate": 0.88, "label": "Severe Storm (F4 Incident)"},
        {"rainfall_mm": 52.0, "wind_gust_kmh": 62.0, "fault_rate": 0.94, "label": "High Storm"},
    ]

    # Section historical risk
    section_risks = [
        {"section_id": "F4-S14", "fault_count": 5, "risk_category": "HIGH (Dense Vegetation / Tree Overhang)"},
        {"section_id": "F4-S5", "fault_count": 3, "risk_category": "MEDIUM (Branch Junction)"},
        {"section_id": "F4-S10", "fault_count": 2, "risk_category": "MEDIUM (Hospital Sub-feeder)"},
        {"section_id": "F4-S13", "fault_count": 2, "risk_category": "MEDIUM (Switching Point)"},
        {"section_id": "F4-S1", "fault_count": 1, "risk_category": "LOW (Underground Conductor)"},
    ]

    return {
        "synthetic_notice": settings.SYNTHETIC_DATA_BANNER,
        "complaints_by_category": [{"category": k, "count": v} for k, v in cat_counts.items()],
        "complaints_by_source": [{"source": k, "count": v} for k, v in source_counts.items()],
        "weather_vs_fault": weather_corr_points,
        "section_historical_risks": section_risks
    }
