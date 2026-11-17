import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.session import Base

class Substation(Base):
    __tablename__ = "substations"
    
    id = Column(String(50), primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    capacity_mva = Column(Float, default=50.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_synthetic = Column(Boolean, default=True)

    feeders = relationship("Feeder", back_populates="substation")


class Feeder(Base):
    __tablename__ = "feeders"
    
    id = Column(String(50), primary_key=True)
    substation_id = Column(String(50), ForeignKey("substations.id"), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # e.g., 'F4', 'F3'
    name = Column(String(100), nullable=False)
    voltage_kv = Column(Float, default=11.0)
    rated_capacity_amps = Column(Float, default=400.0)
    current_load_amps = Column(Float, default=180.0)
    status = Column(String(20), default="NORMAL")  # NORMAL, TRIPPED, DEGRADED, RESTORING
    is_synthetic = Column(Boolean, default=True)

    substation = relationship("Substation", back_populates="feeders")
    line_sections = relationship("LineSection", back_populates="feeder")
    switches = relationship("Switch", back_populates="feeder", foreign_keys="[Switch.feeder_id]")


class LineSection(Base):
    __tablename__ = "line_sections"
    
    id = Column(String(50), primary_key=True)  # e.g., 'F4-S1' ... 'F4-S20'
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    upstream_section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=True)
    section_order = Column(Integer, default=1)
    length_km = Column(Float, default=0.5)
    conductor_type = Column(String(50), default="Rabbit ACSR")
    rated_capacity_amps = Column(Float, default=400.0)
    start_lat = Column(Float, nullable=False)
    start_lng = Column(Float, nullable=False)
    end_lat = Column(Float, nullable=False)
    end_lng = Column(Float, nullable=False)
    has_fault_indicator = Column(Boolean, default=False)
    status = Column(String(20), default="ENERGIZED")  # ENERGIZED, FAULTED, ISOLATED, DE_ENERGIZED
    is_synthetic = Column(Boolean, default=True)

    feeder = relationship("Feeder", back_populates="line_sections")
    upstream_section = relationship("LineSection", remote_side=[id], backref="downstream_sections")
    transformers = relationship("Transformer", back_populates="line_section")
    switches = relationship("Switch", back_populates="line_section")


class Switch(Base):
    __tablename__ = "switches"
    
    id = Column(String(50), primary_key=True)  # e.g., 'AB-14', 'TS-08', 'CB-F4'
    section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=True)
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    switch_type = Column(String(30), nullable=False)  # BREAKER, AIR_BREAK, TIE_SWITCH, SECTIONALIZER
    normal_state = Column(String(10), default="CLOSED")  # CLOSED, OPEN
    current_state = Column(String(10), default="CLOSED")  # CLOSED, OPEN
    adjacent_feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=True)  # for TIE_SWITCH
    rated_current_amps = Column(Float, default=400.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    is_synthetic = Column(Boolean, default=True)

    feeder = relationship("Feeder", foreign_keys=[feeder_id], back_populates="switches")
    adjacent_feeder = relationship("Feeder", foreign_keys=[adjacent_feeder_id])
    line_section = relationship("LineSection", back_populates="switches")


class Transformer(Base):
    __tablename__ = "transformers"
    
    id = Column(String(50), primary_key=True)  # e.g., 'DT-14'
    section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=False)
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    code = Column(String(50), nullable=False)
    capacity_kva = Column(Float, default=250.0)
    current_load_kva = Column(Float, default=140.0)
    peak_load_kva = Column(Float, default=220.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(20), default="ENERGIZED")  # ENERGIZED, DE_ENERGIZED
    is_synthetic = Column(Boolean, default=True)

    line_section = relationship("LineSection", back_populates="transformers")
    consumers = relationship("Consumer", back_populates="transformer")
    critical_loads = relationship("CriticalLoad", back_populates="transformer")


class Consumer(Base):
    __tablename__ = "consumers"
    
    id = Column(String(50), primary_key=True)
    transformer_id = Column(String(50), ForeignKey("transformers.id"), nullable=False)
    consumer_number = Column(String(50), unique=True, nullable=False)
    category = Column(String(30), default="DOMESTIC")  # DOMESTIC, COMMERCIAL, INDUSTRIAL, ESSENTIAL
    sanctioned_load_kw = Column(Float, default=3.0)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String(20), default="CONNECTED")  # CONNECTED, OUTAGE
    is_synthetic = Column(Boolean, default=True)

    transformer = relationship("Transformer", back_populates="consumers")


class CriticalLoad(Base):
    __tablename__ = "critical_loads"
    
    id = Column(String(50), primary_key=True)
    transformer_id = Column(String(50), ForeignKey("transformers.id"), nullable=False)
    name = Column(String(100), nullable=False)  # e.g. 'District Water Pump #3', 'Lifeline Hospital'
    load_type = Column(String(50), nullable=False)  # HOSPITAL, WATER_PUMP, OXYGEN_PLANT, EMERGENCY
    sanctioned_load_kw = Column(Float, default=75.0)
    priority_level = Column(Integer, default=1)  # 1 = Highest
    backup_gen_kva = Column(Float, default=0.0)
    contact_phone = Column(String(30), default="+91-80-2222-0000")
    is_synthetic = Column(Boolean, default=True)

    transformer = relationship("Transformer", back_populates="critical_loads")


class SCADAEvent(Base):
    __tablename__ = "scada_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=True)
    event_type = Column(String(50), nullable=False)  # OVERCURRENT_TRIP, EARTH_FAULT_TRIP, AUTO_RECLOSE_LOCKOUT, VOLTAGE_SAG
    current_amps = Column(Float, default=0.0)
    voltage_kv = Column(Float, default=11.0)
    description = Column(String(255), nullable=True)
    is_synthetic = Column(Boolean, default=True)


class Complaint(Base):
    __tablename__ = "complaints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    consumer_id = Column(String(50), ForeignKey("consumers.id"), nullable=True)
    transformer_id = Column(String(50), ForeignKey("transformers.id"), nullable=True)
    section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=True)
    category = Column(String(50), default="NO_POWER")  # NO_POWER, VOLTAGE_FLUCTUATION, SPARK_REPORTED
    source = Column(String(30), default="IVRS")  # IVRS, APP, CALL_CENTER, SMS
    description = Column(String(255), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_synthetic = Column(Boolean, default=True)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    temperature_c = Column(Float, default=26.0)
    rainfall_mm = Column(Float, default=0.0)
    wind_gust_kmh = Column(Float, default=10.0)
    wind_speed_kmh = Column(Float, default=8.0)
    humidity_pct = Column(Float, default=70.0)
    lightning_strikes = Column(Integer, default=0)
    is_synthetic_fallback = Column(Boolean, default=True)


class FaultPrediction(Base):
    __tablename__ = "fault_predictions"
    
    id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    candidate_section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=False)
    raw_model_score = Column(Float, nullable=False)
    calibrated_confidence = Column(Float, nullable=False)  # Model confidence (not a verified probability)
    rank = Column(Integer, default=1)
    top_candidates = Column(JSON, nullable=True)  # Ranked list of candidate sections with scores
    shap_values = Column(JSON, nullable=True)  # SHAP waterfall breakdown
    feature_snapshot = Column(JSON, nullable=True)
    status = Column(String(30), default="PREDICTED")  # PREDICTED, INVESTIGATING, CONFIRMED, CLEARED
    advisory_notes = Column(Text, nullable=True)


class RestorationPlan(Base):
    __tablename__ = "restoration_plans"
    
    id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    prediction_id = Column(String(50), ForeignKey("fault_predictions.id"), nullable=True)
    feeder_id = Column(String(50), ForeignKey("feeders.id"), nullable=False)
    isolated_section_id = Column(String(50), ForeignKey("line_sections.id"), nullable=False)
    isolation_switch_id = Column(String(50), nullable=True)
    tie_switch_id = Column(String(50), nullable=True)
    donor_feeder_id = Column(String(50), nullable=True)
    steps = Column(JSON, nullable=False)  # Advisory restoration sequence steps
    radial_check_passed = Column(Boolean, default=True)
    capacity_check_passed = Column(Boolean, default=True)
    tie_availability_check_passed = Column(Boolean, default=True)
    affected_dts_count = Column(Integer, default=0)
    affected_consumers_count = Column(Integer, default=0)
    critical_loads_details = Column(JSON, nullable=True)
    crew_dispatch_point = Column(JSON, nullable=True)
    crew_route_path = Column(JSON, nullable=True)
    status = Column(String(30), default="GENERATED")  # GENERATED, OPERATOR_REVIEW, DISPATCHED, COMPLETED
    disclaimer = Column(String(255), default="Advisory: requires engineering validation and operator authorisation")


class CrewDispatch(Base):
    __tablename__ = "crew_dispatches"
    
    id = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    restoration_plan_id = Column(String(50), ForeignKey("restoration_plans.id"), nullable=False)
    team_name = Column(String(50), nullable=False)
    vehicle_callsign = Column(String(50), default="BESCOM-VAN-12")
    current_lat = Column(Float, nullable=False)
    current_lng = Column(Float, nullable=False)
    destination_lat = Column(Float, nullable=False)
    destination_lng = Column(Float, nullable=False)
    eta_minutes = Column(Integer, default=20)
    distance_km = Column(Float, default=3.5)
    status = Column(String(30), default="DISPATCHED")  # DISPATCHED, EN_ROUTE, ON_SITE, RESOLVED
