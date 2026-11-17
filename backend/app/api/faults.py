import uuid
import datetime
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.models.models import Feeder, LineSection, Transformer, Switch, FaultPrediction, SCADAEvent
from app.graph.engine import RadialFeederGraph
from app.services.correlation import CorrelationService
from app.services.weather_service import WeatherService
from app.ml.model import FaultLocalizationModel
from app.ml.features import FEATURE_COLUMNS
from app.schemas.schemas import FaultAnalyzeRequest, FaultAnalyzeResponse, CandidateSection

router = APIRouter(prefix="/faults", tags=["Fault Intelligence"])

# Load persistent model
ml_model = FaultLocalizationModel()
_is_loaded = ml_model.load()

def build_graph_for_feeder(feeder_id: str, db: Session) -> RadialFeederGraph:
    graph = RadialFeederGraph(feeder_id)
    feeder = db.query(Feeder).filter(Feeder.id == feeder_id).first()
    if not feeder:
        return graph

    breaker = db.query(Switch).filter(Switch.feeder_id == feeder_id, Switch.switch_type == "BREAKER").first()
    if breaker:
        graph.add_substation_breaker(breaker.id, breaker.latitude, breaker.longitude, f"Breaker {feeder.code}")

    sections = db.query(LineSection).filter(LineSection.feeder_id == feeder_id).all()
    for s in sections:
        graph.add_line_section(
            section_id=s.id,
            upstream_id=s.upstream_section_id,
            length_km=s.length_km,
            rated_capacity_amps=s.rated_capacity_amps,
            start_coords=(s.start_lat, s.start_lng),
            end_coords=(s.end_lat, s.end_lng),
            conductor_type=s.conductor_type,
            has_fault_indicator=s.has_fault_indicator,
            status=s.status
        )

    transformers = db.query(Transformer).filter(Transformer.feeder_id == feeder_id).all()
    for t in transformers:
        graph.add_transformer(
            transformer_id=t.id,
            section_id=t.section_id,
            capacity_kva=t.capacity_kva,
            current_load_kva=t.current_load_kva,
            coords=(t.latitude, t.longitude),
            status=t.status
        )

    switches = db.query(Switch).filter(Switch.feeder_id == feeder_id).all()
    for sw in switches:
        if sw.switch_type != "BREAKER":
            graph.add_switch(
                switch_id=sw.id,
                section_id=sw.section_id,
                switch_type=sw.switch_type,
                normal_state=sw.normal_state,
                current_state=sw.current_state,
                coords=(sw.latitude, sw.longitude),
                adjacent_feeder_id=sw.adjacent_feeder_id,
                rated_current_amps=sw.rated_current_amps
            )

    return graph


@router.post("/analyze", response_model=FaultAnalyzeResponse)
def analyze_fault(req: FaultAnalyzeRequest, db: Session = Depends(get_db)):
    """
    Core Fault Localization Pipeline:
    1. Loads radial tree and identifies candidates downstream of trip
    2. Radial-tree pruning using energized vs de-energized telemetry nodes
    3. 15-minute rolling window complaint & SCADA correlation
    4. XGBoost ranking & calibrated confidence
    5. SHAP TreeExplainer factor analysis
    """
    global ml_model, _is_loaded
    if not _is_loaded:
        _is_loaded = ml_model.load()
        if not _is_loaded:
            raise HTTPException(status_code=500, detail="Model artifacts not found. Please run training pipeline first.")

    feeder = db.query(Feeder).filter(Feeder.id == req.feeder_id).first()
    if not feeder:
        raise HTTPException(status_code=404, detail=f"Feeder {req.feeder_id} not found")

    graph = build_graph_for_feeder(req.feeder_id, db)
    
    # 1. Candidate sections
    all_sections = list(graph.section_nodes)
    if not all_sections:
        raise HTTPException(status_code=400, detail="No line sections defined for feeder")

    # 2. Telemetry energized vs de-energized
    energized_nodes = set([dt.id for dt in db.query(Transformer.id).filter(Transformer.status == "ENERGIZED").all()])
    deenergized_nodes = set([dt.id for dt in db.query(Transformer.id).filter(Transformer.status == "DE_ENERGIZED").all()])

    # Radial tree pruning
    pruned_candidates = graph.prune_candidates(all_sections, energized_nodes, deenergized_nodes)
    if not pruned_candidates:
        # Fallback to all sections if telemetry pruning left empty
        pruned_candidates = all_sections

    # 3. 15-minute rolling correlation centered on the feeder trip incident
    corr_service = CorrelationService(db, graph)
    now = datetime.datetime.utcnow()
    trip_event = db.query(SCADAEvent).filter(
        SCADAEvent.feeder_id == req.feeder_id,
        SCADAEvent.event_type.in_(["OVERCURRENT_TRIP", "EARTH_FAULT_TRIP", "AUTO_RECLOSE_LOCKOUT"])
    ).order_by(SCADAEvent.timestamp.desc()).first()
    latest_event = db.query(SCADAEvent).filter(SCADAEvent.feeder_id == req.feeder_id).order_by(SCADAEvent.timestamp.desc()).first()
    anchor_time = trip_event.timestamp if trip_event else (latest_event.timestamp if latest_event else now)
    corr_results = corr_service.correlate_window(anchor_time, window_minutes=req.lookback_minutes, feeder_id=req.feeder_id)

    # Weather
    weather = WeatherService.get_current_weather()
    wind_gust = req.weather_wind_gust if req.weather_wind_gust is not None else weather["wind_gust_kmh"]
    rainfall = req.weather_rainfall if req.weather_rainfall is not None else weather["rainfall_mm"]

    # 4. Feature engineering for each candidate section
    sec_objs = {s.id: s for s in db.query(LineSection).filter(LineSection.feeder_id == req.feeder_id).all()}
    
    rows = []
    for sec_id in pruned_candidates:
        sec = sec_objs.get(sec_id)
        downstream_dts = graph.get_downstream_transformers(sec_id)
        downstream_complaints = corr_results["downstream_complaints_by_sec"].get(sec_id, 0)
        direct_complaints = corr_results["direct_complaints_by_sec"].get(sec_id, 0)
        density = corr_results["consumer_density_by_sec"].get(sec_id, 0.0)
        spark_count = corr_results["spark_reports_by_sec"].get(sec_id, 0)
        
        # Downstream de-energized DT count
        dt_outages = db.query(Transformer).filter(
            Transformer.id.in_(downstream_dts),
            Transformer.status == "DE_ENERGIZED"
        ).count() if downstream_dts else 0

        sec_order = sec.section_order if sec else 1
        sec_len = sec.length_km if sec else 0.5
        has_fci = 1.0 if (sec and sec.has_fault_indicator) else 0.0

        rows.append({
            "section_id": sec_id,
            "complaint_count": direct_complaints,
            "downstream_complaints": downstream_complaints,
            "consumer_outage_density": density,
            "downstream_dt_outage_count": dt_outages,
            "voltage_drop_avg": 1.0 if (sec and sec.status in ("FAULTED", "DE_ENERGIZED")) else 0.1,
            "breaker_tripped": 1.0 if feeder.status == "TRIPPED" else 0.0,
            "spark_reports": spark_count,
            "wind_gust_kmh": wind_gust,
            "rainfall_mm": rainfall,
            "lightning_strikes": 12 if rainfall > 20 else 1,
            "historical_fault_freq": 0.25,
            "section_length_km": sec_len,
            "has_fault_indicator": has_fci,
            "fci_triggered": 1.0 if (has_fci and sec and sec.status in ("FAULTED", "DE_ENERGIZED")) else 0.0,
            "depth_from_substation": sec_order
        })

    feat_df = pd.DataFrame(rows)

    # 5. Model Inference & Calibration
    raw_scores, calib_conf = ml_model.predict_candidate_scores(feat_df)
    feat_df["raw_score"] = raw_scores
    feat_df["calib_conf"] = calib_conf

    # Rank descending
    feat_df_sorted = feat_df.sort_values(by="calib_conf", ascending=False).reset_index(drop=True)

    # 6. SHAP Explanations for top candidate
    top_row = feat_df_sorted.iloc[[0]]
    shap_factors, method_label = ml_model.explain(top_row, top_k=5)

    candidate_results: List[CandidateSection] = []
    top_candidates_json = []

    for rank_idx, r in feat_df_sorted.iterrows():
        sec_id = r["section_id"]
        # Find isolation & tie switch
        iso_sw = graph.find_isolation_switch(sec_id)
        tie_sws = graph.find_candidate_tie_switches(sec_id)
        tie_sw = tie_sws[0] if tie_sws else None

        downstream_dts = graph.get_downstream_transformers(sec_id)
        downstream_cons = corr_results["downstream_complaints_by_sec"].get(sec_id, 0)

        # For candidate section, if it's the top candidate, use the computed shap factors
        factors = shap_factors if rank_idx == 0 else []

        cand = CandidateSection(
            section_id=sec_id,
            rank=int(rank_idx + 1),
            raw_model_score=round(float(r["raw_score"]), 4),
            calibrated_confidence=round(float(r["calib_conf"]), 4),
            confidence_label="Model confidence (not a verified probability)",
            downstream_complaints=int(r["downstream_complaints"]),
            downstream_dts=len(downstream_dts),
            downstream_consumers=int(r["downstream_complaints"] * 2.8), # estimated downstream consumers
            features={k: r[k] for k in FEATURE_COLUMNS},
            shap_factors=factors,
            isolation_switch=iso_sw,
            tie_switch_available=tie_sw
        )
        candidate_results.append(cand)
        top_candidates_json.append(cand.model_dump())

    # 7. Store prediction in DB
    pred_id = f"PRED-{feeder.id}-{datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    top_cand = candidate_results[0]
    
    pred_record = FaultPrediction(
        id=pred_id,
        feeder_id=feeder.id,
        candidate_section_id=top_cand.section_id,
        raw_model_score=top_cand.raw_model_score,
        calibrated_confidence=top_cand.calibrated_confidence,
        rank=1,
        top_candidates=top_candidates_json[:5],
        shap_values=shap_factors,
        feature_snapshot=top_cand.features,
        status="PREDICTED",
        advisory_notes=f"Top candidate: {top_cand.section_id}. Confidence: {top_cand.calibrated_confidence:.4f} (Model confidence, not verified probability)."
    )
    db.add(pred_record)
    db.commit()

    return FaultAnalyzeResponse(
        prediction_id=pred_id,
        feeder_id=feeder.id,
        feeder_code=feeder.code,
        timestamp=now,
        pruned_candidate_count=len(pruned_candidates),
        top_candidates=candidate_results[:10],
        explanation_method=method_label,
        status="ANALYSIS_COMPLETE"
    )

@router.get("/predictions")
def list_predictions(limit: int = 20, db: Session = Depends(get_db)):
    preds = db.query(FaultPrediction).order_by(FaultPrediction.created_at.desc()).limit(limit).all()
    return [
        {
            "id": p.id,
            "created_at": p.created_at.isoformat(),
            "feeder_id": p.feeder_id,
            "candidate_section_id": p.candidate_section_id,
            "raw_model_score": p.raw_model_score,
            "calibrated_confidence": p.calibrated_confidence,
            "confidence_label": "Model confidence (not a verified probability)",
            "rank": p.rank,
            "top_candidates": p.top_candidates,
            "shap_values": p.shap_values,
            "status": p.status,
            "advisory_notes": p.advisory_notes
        }
        for p in preds
    ]

@router.get("/{prediction_id}")
def get_prediction_detail(prediction_id: str, db: Session = Depends(get_db)):
    pred = db.query(FaultPrediction).filter(FaultPrediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(status_code=404, detail="Prediction not found")
    return {
        "id": pred.id,
        "created_at": pred.created_at.isoformat(),
        "feeder_id": pred.feeder_id,
        "candidate_section_id": pred.candidate_section_id,
        "raw_model_score": pred.raw_model_score,
        "calibrated_confidence": pred.calibrated_confidence,
        "confidence_label": "Model confidence (not a verified probability)",
        "rank": pred.rank,
        "top_candidates": pred.top_candidates,
        "shap_values": pred.shap_values,
        "feature_snapshot": pred.feature_snapshot,
        "status": pred.status,
        "advisory_notes": pred.advisory_notes,
        "synthetic_notice": "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"
    }
