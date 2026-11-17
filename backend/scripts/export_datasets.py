import os
import csv
import json
from app.database.session import SessionLocal
from app.models.models import Feeder, LineSection, Transformer, Switch, Consumer, SCADAEvent, Complaint, WeatherObservation

SYNTHETIC_HEADER = "# SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10\n# All records are simulated for algorithmic demonstration. No access to real BESCOM infrastructure.\n"

def export_datasets():
    db = SessionLocal()
    dataset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")
    os.makedirs(dataset_dir, exist_ok=True)

    # 1. Topology JSON
    feeders = db.query(Feeder).all()
    sections = db.query(LineSection).all()
    dts = db.query(Transformer).all()
    switches = db.query(Switch).all()

    topology_export = {
        "_notice": "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10",
        "feeders": [{"id": f.id, "code": f.code, "name": f.name, "capacity_amps": f.rated_capacity_amps} for f in feeders],
        "line_sections": [{
            "id": s.id, "feeder_id": s.feeder_id, "upstream_id": s.upstream_section_id,
            "length_km": s.length_km, "rated_capacity_amps": s.rated_capacity_amps,
            "start_coords": [s.start_lat, s.start_lng], "end_coords": [s.end_lat, s.end_lng],
            "has_fault_indicator": s.has_fault_indicator, "status": s.status
        } for s in sections],
        "transformers": [{
            "id": t.id, "section_id": t.section_id, "capacity_kva": t.capacity_kva,
            "coords": [t.latitude, t.longitude], "status": t.status
        } for t in dts],
        "switches": [{
            "id": sw.id, "section_id": sw.section_id, "switch_type": sw.switch_type,
            "normal_state": sw.normal_state, "current_state": sw.current_state,
            "coords": [sw.latitude, sw.longitude], "adjacent_feeder_id": sw.adjacent_feeder_id
        } for sw in switches]
    }

    with open(os.path.join(dataset_dir, "synthetic_network_topology.json"), "w") as f:
        json.dump(topology_export, f, indent=2)

    # 2. SCADA events CSV
    scada_events = db.query(SCADAEvent).all()
    with open(os.path.join(dataset_dir, "synthetic_scada_events.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["# SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"])
        writer.writerow(["id", "timestamp", "feeder_id", "section_id", "event_type", "current_amps", "voltage_kv", "description"])
        for e in scada_events:
            writer.writerow([e.id, e.timestamp.isoformat(), e.feeder_id, e.section_id, e.event_type, e.current_amps, e.voltage_kv, e.description])

    # 3. Complaints CSV
    complaints = db.query(Complaint).all()
    with open(os.path.join(dataset_dir, "synthetic_consumer_complaints.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["# SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"])
        writer.writerow(["id", "timestamp", "transformer_id", "section_id", "category", "source", "description"])
        for c in complaints:
            writer.writerow([c.id, c.timestamp.isoformat(), c.transformer_id, c.section_id, c.category, c.source, c.description])

    # 4. Weather CSV
    weather_obs = db.query(WeatherObservation).all()
    with open(os.path.join(dataset_dir, "synthetic_weather_observations.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["# SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"])
        writer.writerow(["id", "timestamp", "temperature_c", "rainfall_mm", "wind_gust_kmh", "wind_speed_kmh", "humidity_pct", "lightning_strikes"])
        for w in weather_obs:
            writer.writerow([w.id, w.timestamp.isoformat(), w.temperature_c, w.rainfall_mm, w.wind_gust_kmh, w.wind_speed_kmh, w.humidity_pct, w.lightning_strikes])

    db.close()
    print("Exported synthetic datasets to backend/datasets/")

if __name__ == "__main__":
    export_datasets()
