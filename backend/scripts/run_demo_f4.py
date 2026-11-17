import os
import json
import datetime
from app.database.session import SessionLocal
from app.models.models import Feeder, LineSection, Transformer, CriticalLoad, Complaint, WeatherObservation
from app.api.faults import analyze_fault
from app.api.restoration import generate_restoration_plan
from app.schemas.schemas import FaultAnalyzeRequest, RestorationGenerateRequest

def run_f4_demonstration():
    print("=" * 80)
    print("FaultTrace AI - Demo Scenario F4 End-to-End Pipeline Execution")
    print("BESCOM Power Hack 2026 - Theme 10: Distribution Operations Digital Transformation")
    print("=" * 80)

    db = SessionLocal()
    try:
        # 1. Verify Input Data
        feeder = db.query(Feeder).filter(Feeder.id == "F4").first()
        complaints_count = db.query(Complaint).filter(Complaint.section_id.in_(["F4-S14", "F4-S15", "F4-S16", "F4-S4"])).count()
        weather = db.query(WeatherObservation).order_by(WeatherObservation.timestamp.desc()).first()
        
        dts_in_pocket = db.query(Transformer).filter(Transformer.section_id.in_(["F4-S14", "F4-S15", "F4-S16"])).all()
        dt_ids = [d.id for d in dts_in_pocket]
        critical_loads = db.query(CriticalLoad).filter(CriticalLoad.transformer_id.in_(dt_ids)).all()

        print(f"\n[1. DEMO INPUT DATA INGESTED (SYNTHETIC DEMO DATA)]")
        print(f"  - Target Feeder: {feeder.code} ({feeder.name})")
        print(f"  - Feeder Status: {feeder.status}")
        print(f"  - Weather Observation: Rainfall={weather.rainfall_mm}mm, Wind Gust={weather.wind_gust_kmh}km/h")
        print(f"  - Total Ingested Complaints (15-min rolling window): {complaints_count} calls")
        print(f"  - Affected Pocket DTs: {dt_ids} (DT-12, DT-13, DT-14, DT-16)")
        print(f"  - Critical Assets: {[cl.name for cl in critical_loads]}")

        # 2. Execute Fault Analysis (NetworkX Pruning + 15-min Correlation + XGBoost + SHAP)
        print(f"\n[2. RUNNING FAULT LOCALIZATION PIPELINE]")
        analyze_req = FaultAnalyzeRequest(
            feeder_id="F4",
            lookback_minutes=30,
            weather_wind_gust=weather.wind_gust_kmh,
            weather_rainfall=weather.rainfall_mm
        )
        analysis_res = analyze_fault(analyze_req, db)

        print(f"  - Total Feeder Sections: 20")
        print(f"  - Surviving Sections after Radial-Tree Pruning: {analysis_res.pruned_candidate_count}")
        print(f"  - Explanation Engine: {analysis_res.explanation_method}")

        print(f"\n[3. RANKED CANDIDATE FAULT SECTIONS]")
        for cand in analysis_res.top_candidates[:5]:
            print(f"  Rank #{cand.rank}: Line Section {cand.section_id}")
            print(f"    Raw Model Score: {cand.raw_model_score:.4f}")
            print(f"    Model Confidence: {cand.calibrated_confidence * 100:.2f}%  [{cand.confidence_label}]")
            print(f"    Downstream Complaints: {cand.downstream_complaints} calls | Outage Density: {cand.features.get('consumer_outage_density', 0)*100:.1f}%")
            print(f"    Isolation Switch: {cand.isolation_switch} | Candidate Tie Switch: {cand.tie_switch_available}")

        top_cand = analysis_res.top_candidates[0]
        print(f"\n[4. SHAP ROOT-CAUSE FACTOR CONTRIBUTIONS (Top Candidate {top_cand.section_id})]")
        for factor in top_cand.shap_factors:
            sign = "+" if factor["shap_value"] >= 0 else ""
            print(f"  • {factor['display_name']:<32} Observed: {factor['value']:<8} SHAP: {sign}{factor['shap_value']:.4f} ({factor['impact']})")

        # 3. Generate Advisory Restoration Sequence
        print(f"\n[5. ADVISORY RESTORATION ENGINE]")
        restoration_req = RestorationGenerateRequest(
            prediction_id=analysis_res.prediction_id,
            target_section_id=top_cand.section_id
        )
        plan = generate_restoration_plan(restoration_req, db)

        print(f"  - Plan ID: {plan.plan_id}")
        print(f"  - Isolation Point: Switch {plan.isolation_switch} (Isolates {plan.isolated_section})")
        print(f"  - Alternate Donor Supply: Feeder {plan.alternate_donor_feeder} via Tie Switch {plan.tie_switch_id}")

        print(f"\n  Engineering Validation Checks (Non-Negotiable Rule 5):")
        print(f"    [CHECK 1] radial_connectivity_check:      {'PASSED' if plan.radial_connectivity_check['passed'] else 'FAILED'}")
        print(f"              Details: {plan.radial_connectivity_check['details']}")
        print(f"    [CHECK 2] rated_capacity_sum_check:       {'PASSED' if plan.rated_capacity_sum_check['passed'] else 'FAILED'}")
        print(f"              Details: {plan.rated_capacity_sum_check['details']}")
        print(f"    [CHECK 3] tie_switch_availability_check:   {'PASSED' if plan.tie_switch_availability_check['passed'] else 'FAILED'}")
        print(f"              Details: {plan.tie_switch_availability_check['details']}")

        print(f"\n  Advisory Restoration Sequence:")
        for step in plan.steps:
            print(f"    Step {step.step_number}: [{step.action_type}] Device: {step.target_device}")
            print(f"      Description: {step.description}")
            print(f"      Caveat: \"{step.safety_rule}\"")

        print(f"\n  Rapid Restoration Crew Dispatch Advisory:")
        crew = plan.crew_dispatch
        print(f"    Team: {crew['dispatch_team']} ({crew['vehicle']})")
        print(f"    Destination: {crew['destination']['section_id']} (Coordinates: {crew['destination']['lat']:.4f}, {crew['destination']['lng']:.4f})")
        print(f"    Distance: {crew['distance_km']} km | Estimated ETA: {crew['estimated_eta_minutes']} minutes")
        print(f"    Routing Note: {crew['route_type']}")

        print("\n" + "=" * 80)
        print("Demo Scenario F4 Pipeline Execution Completed Successfully!")
        print("=" * 80)

    finally:
        db.close()

if __name__ == "__main__":
    run_f4_demonstration()
