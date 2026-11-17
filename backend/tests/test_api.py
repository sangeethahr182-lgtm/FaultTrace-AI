import os
import pytest
from app.database.session import SessionLocal
from app.main import root, health
from app.api.dashboard import get_dashboard_overview
from app.api.feeders import list_feeders, get_feeder_topology
from app.api.weather import get_weather
from app.api.analytics import get_model_metrics, get_operational_trends
from app.api.events import ingest_event, upload_dataset, DataUploadPayload
from app.schemas.schemas import EventIngestRequest

os.environ["ENABLE_LIVE_WEATHER"] = "false"

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    yield db
    db.close()

def test_root_endpoint():
    res = root()
    assert "SYNTHETIC DEMO DATA" in res["synthetic_notice"]
    assert "Advisory" in res["advisory_disclaimer"]

def test_health_endpoint():
    res = health()
    assert res["status"] == "healthy"
    assert res["synthetic_data"] is True
    assert res["advisory_mode"] is True

def test_dashboard_overview_endpoint(db_session):
    overview = get_dashboard_overview(db_session)
    assert overview.total_feeders >= 1
    assert overview.tripped_feeders >= 1
    assert "SYNTHETIC DEMO DATA" in overview.synthetic_notice
    assert overview.weather_summary["temperature_c"] > 0

def test_feeders_and_topology_endpoint(db_session):
    feeders = list_feeders(db_session)
    assert len(feeders) >= 1
    assert any(f.code == "F4" for f in feeders)

    topo = get_feeder_topology("F4", db_session)
    assert len(topo.nodes) >= 20
    assert len(topo.edges) >= 15
    assert any(n.id == "F4-S14" for n in topo.nodes)
    assert any(n.id == "TS-08" for n in topo.nodes)

def test_weather_endpoint():
    w = get_weather()
    assert "SYNTHETIC DEMO DATA" in w.synthetic_notice
    assert w.wind_gust_kmh > 0
    assert w.is_sample_weather is True  # fallback badge test

def test_analytics_metrics_endpoint():
    m = get_model_metrics()
    assert m.top1_accuracy >= 0.8
    assert m.expected_calibration_error_ece >= 0.0
    assert "SYNTHETIC DEMO DATA" in m.synthetic_training_statement

def test_analytics_trends_endpoint(db_session):
    trends = get_operational_trends(db_session)
    assert "complaints_by_category" in trends
    assert "weather_vs_fault" in trends
    assert "section_historical_risks" in trends

def test_event_ingest_and_data_upload(db_session):
    ingest_req = EventIngestRequest(
        feeder_id="F4",
        event_type="VOLTAGE_SAG",
        current_amps=320.0,
        voltage_kv=8.5,
        description="Transient voltage sag test"
    )
    res = ingest_event(ingest_req, db_session)
    assert res.status == "INGESTED"

    upload_payload = DataUploadPayload(
        dataset_type="complaints",
        filename="test_dataset.csv",
        content="id,timestamp,category\n1,2026-11-17T10:00:00,NO_POWER"
    )
    upload_res = upload_dataset(upload_payload)
    assert upload_res["status"] == "VALIDATED_AND_STAGED"
    assert upload_res["total_records"] == 1
