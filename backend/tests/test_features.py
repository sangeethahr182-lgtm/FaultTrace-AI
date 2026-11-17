import pytest
import pandas as pd
from app.ml.features import FEATURE_COLUMNS, extract_feature_matrix
from app.services.simulator import ScenarioSimulator

def test_feature_columns_structure():
    assert "complaint_count" in FEATURE_COLUMNS
    assert "consumer_outage_density" in FEATURE_COLUMNS
    assert "voltage_drop_avg" in FEATURE_COLUMNS
    assert "breaker_tripped" in FEATURE_COLUMNS
    assert "wind_gust_kmh" in FEATURE_COLUMNS
    assert "rainfall_mm" in FEATURE_COLUMNS
    assert "historical_fault_freq" in FEATURE_COLUMNS
    assert "downstream_dt_outage_count" in FEATURE_COLUMNS

def test_scenario_simulator_generation():
    sim = ScenarioSimulator()
    true_sec, meta, df = sim.generate_scenario(scenario_id=1)
    
    assert true_sec.startswith("F4-S")
    assert meta["scenario_id"] == 1
    assert len(df) == 20
    assert "is_fault" in df.columns
    assert df["is_fault"].sum() == 1  # exactly one true target fault section

    # Verify extracted matrix matches required columns
    feat_matrix = extract_feature_matrix(df)
    assert feat_matrix.shape == (20, len(FEATURE_COLUMNS))
