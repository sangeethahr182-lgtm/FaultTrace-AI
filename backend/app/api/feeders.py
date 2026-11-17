from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.models.models import Feeder, LineSection, Transformer, Switch, CriticalLoad, Substation
from app.schemas.schemas import FeederSummary, FeederTopology, TopologyNode, TopologyEdge

router = APIRouter(prefix="/feeders", tags=["Feeders"])

@router.get("", response_model=List[FeederSummary])
def list_feeders(db: Session = Depends(get_db)):
    feeders = db.query(Feeder).all()
    return [
        FeederSummary(
            id=f.id,
            code=f.code,
            name=f.name,
            voltage_kv=f.voltage_kv,
            rated_capacity_amps=f.rated_capacity_amps,
            current_load_amps=f.current_load_amps,
            status=f.status,
            is_synthetic=f.is_synthetic
        )
        for f in feeders
    ]

@router.get("/{feeder_id}/topology", response_model=FeederTopology)
def get_feeder_topology(feeder_id: str, db: Session = Depends(get_db)):
    feeder = db.query(Feeder).filter(Feeder.id == feeder_id).first()
    if not feeder:
        raise HTTPException(status_code=404, detail=f"Feeder {feeder_id} not found")

    substation = db.query(Substation).filter(Substation.id == feeder.substation_id).first()
    sections = db.query(LineSection).filter(LineSection.feeder_id == feeder_id).order_by(LineSection.section_order).all()
    dts = db.query(Transformer).filter(Transformer.feeder_id == feeder_id).all()
    switches = db.query(Switch).filter(Switch.feeder_id == feeder_id).all()
    
    # Critical loads attached to this feeder's DTs
    dt_ids = [d.id for d in dts]
    critical_loads = db.query(CriticalLoad).filter(CriticalLoad.transformer_id.in_(dt_ids)).all() if dt_ids else []
    dt_to_critical = {cl.transformer_id: cl.name for cl in critical_loads}

    nodes: List[TopologyNode] = []
    edges: List[TopologyEdge] = []

    # 1. Substation Node
    if substation:
        nodes.append(TopologyNode(
            id=substation.id,
            label=substation.name,
            type="SUBSTATION",
            status="NORMAL",
            lat=substation.latitude,
            lng=substation.longitude,
            metadata={"capacity_mva": substation.capacity_mva}
        ))

    # 2. Feeder Breaker Switch
    breaker = next((s for s in switches if s.switch_type == "BREAKER"), None)
    if breaker and substation:
        nodes.append(TopologyNode(
            id=breaker.id,
            label=f"Feeder Breaker {feeder.code}",
            type="BREAKER",
            status=breaker.current_state,
            lat=breaker.latitude,
            lng=breaker.longitude,
            metadata={"rated_amps": breaker.rated_current_amps}
        ))
        edges.append(TopologyEdge(
            source=substation.id,
            target=breaker.id,
            label="Bus Tie",
            type="LINE",
            status="CLOSED"
        ))

    # 3. Line Sections
    for sec in sections:
        nodes.append(TopologyNode(
            id=sec.id,
            label=sec.id,
            type="SECTION",
            status=sec.status,
            lat=sec.end_lat,
            lng=sec.end_lng,
            metadata={
                "length_km": sec.length_km,
                "conductor": sec.conductor_type,
                "has_fault_indicator": sec.has_fault_indicator,
                "start_coords": [sec.start_lat, sec.start_lng],
                "end_coords": [sec.end_lat, sec.end_lng]
            }
        ))

        parent = sec.upstream_section_id
        if not parent and breaker:
            parent = breaker.id
        elif not parent and substation:
            parent = substation.id

        if parent:
            edges.append(TopologyEdge(
                source=parent,
                target=sec.id,
                label=f"{sec.length_km}km",
                type="LINE",
                length_km=sec.length_km,
                status="CLOSED" if sec.status != "ISOLATED" else "OPEN"
            ))

    # 4. Transformers
    for dt in dts:
        is_crit = dt.id in dt_to_critical
        nodes.append(TopologyNode(
            id=dt.id,
            label=f"{dt.id} ({dt_to_critical[dt.id]})" if is_crit else dt.id,
            type="CRITICAL_LOAD" if is_crit else "TRANSFORMER",
            status=dt.status,
            lat=dt.latitude,
            lng=dt.longitude,
            metadata={
                "capacity_kva": dt.capacity_kva,
                "current_load_kva": dt.current_load_kva,
                "section_id": dt.section_id,
                "is_critical": is_crit,
                "critical_name": dt_to_critical.get(dt.id)
            }
        ))
        edges.append(TopologyEdge(
            source=dt.section_id,
            target=dt.id,
            type="SERVICE_DROP",
            status="CLOSED" if dt.status == "ENERGIZED" else "DE_ENERGIZED"
        ))

    # 5. Air-Break & Tie Switches
    for sw in switches:
        if sw.switch_type != "BREAKER":
            nodes.append(TopologyNode(
                id=sw.id,
                label=f"{sw.id} ({sw.switch_type})",
                type="SWITCH",
                status=sw.current_state,
                lat=sw.latitude,
                lng=sw.longitude,
                metadata={
                    "switch_type": sw.switch_type,
                    "normal_state": sw.normal_state,
                    "current_state": sw.current_state,
                    "adjacent_feeder_id": sw.adjacent_feeder_id
                }
            ))
            if sw.section_id:
                edges.append(TopologyEdge(
                    source=sw.section_id,
                    target=sw.id,
                    type="SWITCH",
                    status=sw.current_state
                ))

    return FeederTopology(
        feeder_id=feeder.id,
        feeder_code=feeder.code,
        substation_name=substation.name if substation else "Substation",
        nodes=nodes,
        edges=edges
    )
