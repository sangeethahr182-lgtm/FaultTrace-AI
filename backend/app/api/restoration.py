from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.models.models import Feeder, LineSection, RestorationPlan, CrewDispatch, FaultPrediction
from app.api.faults import build_graph_for_feeder
from app.services.restoration import RestorationService
from app.schemas.schemas import (
    AffectedAssetsResponse, RestorationPlanResponse, RestorationGenerateRequest
)

router = APIRouter(prefix="", tags=["Restoration & Assets"])

@router.get("/assets/affected", response_model=AffectedAssetsResponse)
def get_affected_assets(
    feeder_id: str = Query(..., description="Feeder ID, e.g. F4"),
    section_id: str = Query(..., description="Suspected Line Section ID, e.g. F4-S14"),
    db: Session = Depends(get_db)
):
    graph = build_graph_for_feeder(feeder_id, db)
    service = RestorationService(db, graph)
    affected = service.calculate_affected_assets(feeder_id, section_id)
    return AffectedAssetsResponse(**affected)


@router.post("/restoration/generate", response_model=RestorationPlanResponse)
def generate_restoration_plan(
    req: RestorationGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generates step-by-step restoration advisory with:
    1. Isolation switch from graph
    2. Alternate donor feeder & tie switch
    3. Radial connectivity check
    4. Rated-capacity sum check
    5. Tie switch availability check
    6. Approximate crew dispatch point and route
    """
    pred = db.query(FaultPrediction).filter(FaultPrediction.id == req.prediction_id).first()
    if not pred:
        # Check if prediction_id is actually a feeder_id directly
        feeder = db.query(Feeder).filter(Feeder.id == req.prediction_id).first()
        if feeder:
            feeder_id = feeder.id
            target_section = req.target_section_id or "F4-S14"
        else:
            raise HTTPException(status_code=404, detail="Prediction not found")
    else:
        feeder_id = pred.feeder_id
        target_section = req.target_section_id or pred.candidate_section_id

    graph = build_graph_for_feeder(feeder_id, db)
    service = RestorationService(db, graph)
    plan_dict = service.generate_advisory_plan(
        feeder_id=feeder_id,
        suspected_section_id=target_section,
        prediction_id=pred.id if pred else None
    )

    # Persist RestorationPlan in DB
    existing_plan = db.query(RestorationPlan).filter(RestorationPlan.id == plan_dict["plan_id"]).first()
    if not existing_plan:
        db_plan = RestorationPlan(
            id=plan_dict["plan_id"],
            prediction_id=plan_dict["prediction_id"],
            feeder_id=plan_dict["feeder_id"],
            isolated_section_id=plan_dict["isolated_section"],
            isolation_switch_id=plan_dict["isolation_switch"],
            tie_switch_id=plan_dict["tie_switch_id"],
            donor_feeder_id=plan_dict["alternate_donor_feeder"],
            steps=plan_dict["steps"],
            radial_check_passed=plan_dict["radial_connectivity_check"]["passed"],
            capacity_check_passed=plan_dict["rated_capacity_sum_check"]["passed"],
            tie_availability_check_passed=plan_dict["tie_switch_availability_check"]["passed"],
            affected_dts_count=plan_dict["affected_assets"]["total_dts_count"],
            affected_consumers_count=plan_dict["affected_assets"]["estimated_consumers_outage"],
            critical_loads_details=plan_dict["affected_assets"]["critical_loads"],
            crew_dispatch_point=plan_dict["crew_dispatch"]["destination"],
            crew_route_path=plan_dict["crew_dispatch"]["route_waypoints"],
            status="GENERATED",
            disclaimer=plan_dict["disclaimer"]
        )
        db.add(db_plan)

        # Crew dispatch
        cd = CrewDispatch(
            id=f"DISP-{plan_dict['plan_id']}",
            restoration_plan_id=plan_dict["plan_id"],
            team_name=plan_dict["crew_dispatch"]["dispatch_team"],
            vehicle_callsign=plan_dict["crew_dispatch"]["vehicle"],
            current_lat=plan_dict["crew_dispatch"]["origin"]["lat"],
            current_lng=plan_dict["crew_dispatch"]["origin"]["lng"],
            destination_lat=plan_dict["crew_dispatch"]["destination"]["lat"],
            destination_lng=plan_dict["crew_dispatch"]["destination"]["lng"],
            eta_minutes=plan_dict["crew_dispatch"]["estimated_eta_minutes"],
            distance_km=plan_dict["crew_dispatch"]["distance_km"],
            status="DISPATCHED"
        )
        db.add(cd)
        db.commit()

    return RestorationPlanResponse(
        plan_id=plan_dict["plan_id"],
        feeder_id=plan_dict["feeder_id"],
        isolated_section=plan_dict["isolated_section"],
        isolation_switch=plan_dict["isolation_switch"],
        alternate_donor_feeder=plan_dict["alternate_donor_feeder"],
        tie_switch_id=plan_dict["tie_switch_id"],
        radial_connectivity_check=plan_dict["radial_connectivity_check"],
        rated_capacity_sum_check=plan_dict["rated_capacity_sum_check"],
        tie_switch_availability_check=plan_dict["tie_switch_availability_check"],
        steps=plan_dict["steps"],
        crew_dispatch=plan_dict["crew_dispatch"],
        disclaimer=plan_dict["disclaimer"]
    )


@router.get("/restoration/plans")
def list_restoration_plans(limit: int = 10, db: Session = Depends(get_db)):
    plans = db.query(RestorationPlan).order_by(RestorationPlan.created_at.desc()).limit(limit).all()
    return [
        {
            "plan_id": p.id,
            "created_at": p.created_at.isoformat(),
            "prediction_id": p.prediction_id,
            "feeder_id": p.feeder_id,
            "isolated_section": p.isolated_section_id,
            "isolation_switch": p.isolation_switch_id,
            "tie_switch_id": p.tie_switch_id,
            "donor_feeder_id": p.donor_feeder_id,
            "steps": p.steps,
            "radial_check_passed": p.radial_check_passed,
            "capacity_check_passed": p.capacity_check_passed,
            "tie_availability_check_passed": p.tie_availability_check_passed,
            "affected_dts_count": p.affected_dts_count,
            "affected_consumers_count": p.affected_consumers_count,
            "critical_loads": p.critical_loads_details,
            "crew_dispatch_point": p.crew_dispatch_point,
            "crew_route_path": p.crew_route_path,
            "status": p.status,
            "disclaimer": p.disclaimer,
            "synthetic_notice": "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"
        }
        for p in plans
    ]
