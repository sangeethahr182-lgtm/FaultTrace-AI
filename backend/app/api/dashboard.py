from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Feeder, Transformer, Consumer, CriticalLoad, SCADAEvent, FaultPrediction
from app.services.weather_service import WeatherService
from app.schemas.schemas import DashboardOverview

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/overview", response_model=DashboardOverview)
def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Returns real-time operational overview.
    Every single number is computed dynamically from the database.
    """
    total_feeders = db.query(Feeder).count()
    tripped_feeders = db.query(Feeder).filter(Feeder.status == "TRIPPED").count()
    active_faults_count = db.query(FaultPrediction).filter(FaultPrediction.status.in_(["PREDICTED", "INVESTIGATING"])).count()
    
    # If no fault predictions recorded yet, count tripped feeders as active faults
    if active_faults_count == 0 and tripped_feeders > 0:
        active_faults_count = tripped_feeders

    total_affected_dts = db.query(Transformer).filter(Transformer.status == "DE_ENERGIZED").count()
    total_affected_consumers = db.query(Consumer).filter(Consumer.status == "OUTAGE").count()
    
    # Critical loads on de-energized DTs
    de_energized_dt_ids = [dt.id for dt in db.query(Transformer.id).filter(Transformer.status == "DE_ENERGIZED").all()]
    critical_loads_affected = db.query(CriticalLoad).filter(CriticalLoad.transformer_id.in_(de_energized_dt_ids)).count() if de_energized_dt_ids else 0

    # Weather
    weather = WeatherService.get_current_weather()

    # Recent SCADA events
    recent_events_query = db.query(SCADAEvent).order_by(SCADAEvent.timestamp.desc()).limit(5).all()
    recent_events = [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "feeder_id": e.feeder_id,
            "section_id": e.section_id,
            "event_type": e.event_type,
            "current_amps": e.current_amps,
            "voltage_kv": e.voltage_kv,
            "description": e.description,
        }
        for e in recent_events_query
    ]

    # Recent Predictions
    recent_preds_query = db.query(FaultPrediction).order_by(FaultPrediction.created_at.desc()).limit(5).all()
    recent_preds = [
        {
            "id": p.id,
            "created_at": p.created_at.isoformat(),
            "feeder_id": p.feeder_id,
            "candidate_section_id": p.candidate_section_id,
            "raw_model_score": p.raw_model_score,
            "calibrated_confidence": p.calibrated_confidence,
            "status": p.status,
        }
        for p in recent_preds_query
    ]

    return DashboardOverview(
        total_feeders=total_feeders,
        tripped_feeders=tripped_feeders,
        active_faults_count=active_faults_count,
        total_affected_dts=total_affected_dts,
        total_affected_consumers=total_affected_consumers,
        critical_loads_affected=critical_loads_affected,
        weather_summary=weather,
        recent_events=recent_events,
        recent_predictions=recent_preds
    )
