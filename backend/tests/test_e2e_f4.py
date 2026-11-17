import os
import pytest
from app.database.session import SessionLocal
from app.api.faults import analyze_fault
from app.api.restoration import generate_restoration_plan
from app.schemas.schemas import FaultAnalyzeRequest, RestorationGenerateRequest

os.environ["ENABLE_LIVE_WEATHER"] = "false"

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_e2e_f4_fault_localization_and_restoration(db_session):
    """
    End-to-End Test for Demo Scenario F4:
    1. Triggers real ML & Graph pipeline on Feeder F4 (heavy rain, 48 km/h gust, 142 complaints)
    2. Asserts pipeline returns a dynamically ranked list (NO hardcoded confidence assertion)
    3. Asserts top candidate is returned with SHAP factors or feature importances
    4. Triggers advisory restoration plan generation
    5. Asserts AB-14 isolation, TS-08 back-feed check, and crew routing near that span
    """
    # 1. Trigger Fault Analysis
    req = FaultAnalyzeRequest(
        feeder_id="F4",
        lookback_minutes=30,
        weather_wind_gust=48.0,
        weather_rainfall=38.6
    )
    res = analyze_fault(req, db_session)

    # Dynamic computation asserts
    assert res.feeder_id == "F4"
    assert res.pruned_candidate_count > 0
    assert len(res.top_candidates) > 0

    top_candidate = res.top_candidates[0]
    print(f"\n[E2E F4 Pipeline] Top Candidate Identified: {top_candidate.section_id}")
    print(f"[E2E F4 Pipeline] Model Score: {top_candidate.raw_model_score}")
    print(f"[E2E F4 Pipeline] Model Confidence: {top_candidate.calibrated_confidence} ({top_candidate.confidence_label})")
    print(f"[E2E F4 Pipeline] Explanation Method: {res.explanation_method}")

    # Rule 6: Confidence label check
    assert top_candidate.confidence_label == "Model confidence (not a verified probability)"
    
    # Assert F4-S14 or immediate adjacent section in fault pocket is top ranked
    assert top_candidate.section_id in ("F4-S14", "F4-S15", "F4-S16")
    
    # Rule 7: Explanations check
    assert len(top_candidate.shap_factors) > 0
    assert res.explanation_method in ("SHAP TreeExplainer", "Feature Importances (SHAP Fallback)")

    # 2. Trigger Advisory Restoration Generation
    restoration_req = RestorationGenerateRequest(
        prediction_id=res.prediction_id,
        target_section_id=top_candidate.section_id
    )
    plan = generate_restoration_plan(restoration_req, db_session)

    print(f"[E2E F4 Pipeline] Plan ID: {plan.plan_id}")
    print(f"[E2E F4 Pipeline] Isolation Switch: {plan.isolation_switch}")
    print(f"[E2E F4 Pipeline] Tie Switch: {plan.tie_switch_id}")
    print(f"[E2E F4 Pipeline] Alternate Donor: {plan.alternate_donor_feeder}")

    # Assert real switch names from graph
    assert plan.isolation_switch == "AB-14"
    assert plan.tie_switch_id == "TS-08"
    assert plan.alternate_donor_feeder == "F3"

    # Assert implemented engineering checks
    assert plan.radial_connectivity_check["passed"] is True
    assert plan.rated_capacity_sum_check["passed"] is True
    assert plan.tie_switch_availability_check["passed"] is True

    # Assert advisory safety rule on every step
    for step in plan.steps:
        assert "Advisory: requires engineering validation and operator authorisation" in step.safety_rule

    # Assert crew dispatch
    crew = plan.crew_dispatch
    assert crew["destination"]["section_id"] == top_candidate.section_id
    assert crew["distance_km"] > 0
    assert "route_waypoints" in crew
