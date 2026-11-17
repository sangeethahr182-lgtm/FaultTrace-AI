import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import SCADAEvent, Complaint, LineSection, Transformer, Consumer
from app.graph.engine import RadialFeederGraph

class CorrelationService:
    """
    15-minute rolling window correlation service.
    Correlates SCADA breaker/recloser trip events with consumer IVRS/App/Call complaints,
    mapping complaints across the feeder radial graph to candidate sections.
    """

    def __init__(self, db: Session, graph: RadialFeederGraph):
        self.db = db
        self.graph = graph

    def correlate_window(
        self,
        event_time: datetime.datetime,
        window_minutes: int = 15,
        feeder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extracts complaints in [event_time - window_minutes, event_time + window_minutes]
        and maps them across line sections.
        """
        start_time = event_time - datetime.timedelta(minutes=window_minutes)
        end_time = event_time + datetime.timedelta(minutes=window_minutes)

        query = self.db.query(Complaint).filter(
            Complaint.timestamp >= start_time,
            Complaint.timestamp <= end_time
        )
        complaints = query.all()

        # Map transformers to sections
        dts = self.db.query(Transformer).all()
        dt_to_section = {dt.id: dt.section_id for dt in dts}

        # Count direct complaints per section
        direct_complaints_by_sec: Dict[str, int] = {}
        spark_reports_by_sec: Dict[str, int] = {}
        voltage_complaints_by_sec: Dict[str, int] = {}

        for c in complaints:
            sec_id = c.section_id
            if not sec_id and c.transformer_id:
                sec_id = dt_to_section.get(c.transformer_id)

            if sec_id:
                direct_complaints_by_sec[sec_id] = direct_complaints_by_sec.get(sec_id, 0) + 1
                if c.category in ("SPARK_REPORTED", "SOUND_EXPLOSION"):
                    spark_reports_by_sec[sec_id] = spark_reports_by_sec.get(sec_id, 0) + 1
                elif c.category == "VOLTAGE_FLUCTUATION":
                    voltage_complaints_by_sec[sec_id] = voltage_complaints_by_sec.get(sec_id, 0) + 1

        # For every section in the radial graph, calculate downstream aggregated complaints
        downstream_complaints_by_sec: Dict[str, int] = {}
        consumer_density_by_sec: Dict[str, float] = {}

        for sec_id in self.graph.section_nodes:
            downstream_secs = self.graph.get_downstream_sections(sec_id)
            total_downstream_complaints = sum(direct_complaints_by_sec.get(s, 0) for s in downstream_secs)
            downstream_complaints_by_sec[sec_id] = total_downstream_complaints

            # Calculate downstream consumers
            downstream_dts = self.graph.get_downstream_transformers(sec_id)
            total_consumers = self.db.query(Consumer).filter(Consumer.transformer_id.in_(downstream_dts)).count() if downstream_dts else 0
            
            density = (total_downstream_complaints / total_consumers) if total_consumers > 0 else 0.0
            consumer_density_by_sec[sec_id] = round(density, 4)

        return {
            "window_start": start_time.isoformat(),
            "window_end": end_time.isoformat(),
            "total_complaints_in_window": len(complaints),
            "direct_complaints_by_sec": direct_complaints_by_sec,
            "downstream_complaints_by_sec": downstream_complaints_by_sec,
            "consumer_density_by_sec": consumer_density_by_sec,
            "spark_reports_by_sec": spark_reports_by_sec,
            "voltage_complaints_by_sec": voltage_complaints_by_sec,
        }
