import pandas as pd
from typing import List, Dict, Any

FEATURE_COLUMNS = [
    "complaint_count",
    "downstream_complaints",
    "consumer_outage_density",
    "downstream_dt_outage_count",
    "voltage_drop_avg",
    "breaker_tripped",
    "spark_reports",
    "wind_gust_kmh",
    "rainfall_mm",
    "lightning_strikes",
    "historical_fault_freq",
    "section_length_km",
    "has_fault_indicator",
    "fci_triggered",
    "depth_from_substation"
]

FEATURE_DISPLAY_NAMES = {
    "complaint_count": "Direct Complaints",
    "downstream_complaints": "Downstream Complaints Sum",
    "consumer_outage_density": "Consumer Outage Density",
    "downstream_dt_outage_count": "Downstream DT Outage Count",
    "voltage_drop_avg": "Average Voltage Drop",
    "breaker_tripped": "Feeder Breaker Trip Flag",
    "spark_reports": "Acoustic / Spark Reports",
    "wind_gust_kmh": "Wind Gust Speed (km/h)",
    "rainfall_mm": "Precipitation Rate (mm)",
    "lightning_strikes": "Lightning Strike Count",
    "historical_fault_freq": "Historical Fault Rate",
    "section_length_km": "Section Length (km)",
    "has_fault_indicator": "Fault Current Indicator Present",
    "fci_triggered": "FCI Triggered Status",
    "depth_from_substation": "Distance Depth from Substation"
}

def extract_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Extracts strictly the model feature columns."""
    for col in FEATURE_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0
    return df[FEATURE_COLUMNS].copy()
