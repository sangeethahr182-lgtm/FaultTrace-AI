from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# Common
class SyntheticBadgeMixin(BaseModel):
    synthetic_notice: str = "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"

class AdvisoryMixin(BaseModel):
    advisory_notice: str = "Advisory: requires engineering validation and operator authorisation"

# Dashboard Overview
class DashboardOverview(SyntheticBadgeMixin):
    total_feeders: int
    tripped_feeders: int
    active_faults_count: int
    total_affected_dts: int
    total_affected_consumers: int
    critical_loads_affected: int
    weather_summary: Dict[str, Any]
    recent_events: List[Dict[str, Any]]
    recent_predictions: List[Dict[str, Any]]

# Feeder & Topology
class FeederSummary(BaseModel):
    id: str
    code: str
    name: str
    voltage_kv: float
    rated_capacity_amps: float
    current_load_amps: float
    status: str
    is_synthetic: bool = True

class TopologyNode(BaseModel):
    id: str
    label: str
    type: str  # SUBSTATION, FEEDER_BREAKER, SECTION, TRANSFORMER, SWITCH, CRITICAL_LOAD
    status: str
    lat: float
    lng: float
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TopologyEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    type: str  # LINE, SWITCH, SERVICE_DROP
    length_km: Optional[float] = None
    status: str

class FeederTopology(SyntheticBadgeMixin):
    feeder_id: str
    feeder_code: str
    substation_name: str
    nodes: List[TopologyNode]
    edges: List[TopologyEdge]

# Ingestion
class EventIngestRequest(BaseModel):
    feeder_id: str
    event_type: str  # OVERCURRENT_TRIP, EARTH_FAULT_TRIP, VOLTAGE_SAG, AUTO_RECLOSE_LOCKOUT
    section_id: Optional[str] = None
    current_amps: Optional[float] = 0.0
    voltage_kv: Optional[float] = 11.0
    description: Optional[str] = None

class EventIngestResponse(SyntheticBadgeMixin):
    event_id: int
    status: str
    message: str

# Fault Analysis
class FaultAnalyzeRequest(BaseModel):
    feeder_id: str
    lookback_minutes: int = 30
    weather_wind_gust: Optional[float] = None
    weather_rainfall: Optional[float] = None

class CandidateSection(BaseModel):
    section_id: str
    rank: int
    raw_model_score: float
    calibrated_confidence: float  # Model confidence (not a verified probability)
    confidence_label: str = "Model confidence (not a verified probability)"
    downstream_complaints: int
    downstream_dts: int
    downstream_consumers: int
    features: Dict[str, Any]
    shap_factors: List[Dict[str, Any]]
    isolation_switch: Optional[str] = None
    tie_switch_available: Optional[str] = None

class FaultAnalyzeResponse(SyntheticBadgeMixin, AdvisoryMixin):
    prediction_id: str
    feeder_id: str
    feeder_code: str
    timestamp: datetime
    pruned_candidate_count: int
    top_candidates: List[CandidateSection]
    explanation_method: str  # "SHAP TreeExplainer" or "Feature Importances (SHAP Fallback)"
    status: str

# Affected Assets
class CriticalLoadDetail(BaseModel):
    id: str
    name: str
    load_type: str
    transformer_id: str
    priority_level: int
    backup_gen_kva: float
    contact_phone: str

class AffectedAssetsResponse(SyntheticBadgeMixin):
    feeder_id: str
    suspected_section_id: str
    affected_sections: List[str]
    affected_dts: List[str]
    total_dts_count: int
    estimated_consumers_outage: int
    critical_loads: List[CriticalLoadDetail]
    unserved_load_kva: float

# Advisory Restoration
class RestorationStep(BaseModel):
    step_number: int
    action_type: str  # ISOLATE, VERIFY, BACKFEED, DISPATCH
    target_device: str
    description: str
    safety_rule: str = "Advisory: requires engineering validation and operator authorisation"

class RestorationGenerateRequest(BaseModel):
    prediction_id: str
    target_section_id: Optional[str] = None

class RestorationPlanResponse(SyntheticBadgeMixin, AdvisoryMixin):
    plan_id: str
    feeder_id: str
    isolated_section: str
    isolation_switch: str
    alternate_donor_feeder: Optional[str]
    tie_switch_id: Optional[str]
    
    # Validation checks
    radial_connectivity_check: Dict[str, Any]
    rated_capacity_sum_check: Dict[str, Any]
    tie_switch_availability_check: Dict[str, Any]
    
    steps: List[RestorationStep]
    crew_dispatch: Dict[str, Any]
    disclaimer: str

# Weather
class WeatherResponse(SyntheticBadgeMixin):
    latitude: float
    longitude: float
    temperature_c: float
    rainfall_mm: float
    wind_gust_kmh: float
    wind_speed_kmh: float
    humidity_pct: float
    is_sample_weather: bool
    source_label: str

# Analytics & ML Metrics
class MLMetricsResponse(SyntheticBadgeMixin):
    model_name: str
    trained_at: str
    evaluation_split: str  # "Scenario-based train/test split (no data leakage)"
    total_scenarios_train: int
    total_scenarios_test: int
    top1_accuracy: float
    top3_accuracy: float
    roc_auc: float
    precision: float
    recall: float
    f1_score: float
    expected_calibration_error_ece: float
    calibration_method: str
    baseline_top1_accuracy: float  # Pick section with most complaints
    baseline_top3_accuracy: float
    confusion_matrix: List[List[int]]
    feature_importances: Dict[str, float]
    synthetic_training_statement: str
