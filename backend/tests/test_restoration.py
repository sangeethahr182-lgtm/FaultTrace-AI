import pytest
from app.database.session import SessionLocal
from app.services.restoration import RestorationService
from app.api.faults import build_graph_for_feeder

@pytest.fixture
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_affected_assets_calculation(db_session):
    graph = build_graph_for_feeder("F4", db_session)
    service = RestorationService(db_session, graph)
    
    # Calculate affected assets for suspected fault on F4-S14
    affected = service.calculate_affected_assets("F4", "F4-S14")
    
    assert affected["feeder_id"] == "F4"
    assert affected["suspected_section_id"] == "F4-S14"
    assert "F4-S14" in affected["affected_sections"]
    assert "F4-S15" in affected["affected_sections"]
    assert "F4-S16" in affected["affected_sections"]
    
    # Affected DTs should include DT-12, DT-13, DT-14, DT-16
    assert "DT-14" in affected["affected_dts"]
    
    # Critical loads should identify District Water Pump #3 on DT-14
    crit_names = [cl["name"] for cl in affected["critical_loads"]]
    assert any("District Water Pump #3" in name for name in crit_names)

def test_advisory_restoration_plan_generation(db_session):
    graph = build_graph_for_feeder("F4", db_session)
    service = RestorationService(db_session, graph)
    
    plan = service.generate_advisory_plan("F4", "F4-S14")
    
    # Isolation switch must be the real switch AB-14 from the graph
    assert plan["isolation_switch"] == "AB-14"
    # Tie switch must be TS-08 to Feeder F3
    assert plan["tie_switch_id"] == "TS-08"
    assert plan["alternate_donor_feeder"] == "F3"
    
    # Check that checks are named exactly and present
    assert "radial_connectivity_check" in plan
    assert "rated_capacity_sum_check" in plan
    assert "tie_switch_availability_check" in plan
    assert plan["radial_connectivity_check"]["passed"] is True
    assert plan["rated_capacity_sum_check"]["passed"] is True
    
    # Verify advisory safety disclaimer on every step
    for step in plan["steps"]:
        assert "Advisory: requires engineering validation and operator authorisation" in step["safety_rule"]
    
    # Verify crew dispatch
    crew = plan["crew_dispatch"]
    assert crew["destination"]["section_id"] == "F4-S14"
    assert crew["distance_km"] > 0
    assert "Approximate" in crew["route_type"]
