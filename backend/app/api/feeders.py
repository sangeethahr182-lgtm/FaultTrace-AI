import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.models.models import Feeder, LineSection, Transformer, Switch, CriticalLoad, Substation
from app.schemas.schemas import (
    FeederSummary, 
    FeederTopology, 
    TopologyNode, 
    TopologyEdge,
    AssetDistanceItem,
    NearestAssetResponse
)

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


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2.0) ** 2 + 
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


@router.get("/{feeder_id}/nearest-asset", response_model=NearestAssetResponse)
def get_nearest_asset_by_gps(
    feeder_id: str,
    lat: float = Query(..., description="GPS Latitude"),
    lng: float = Query(..., description="GPS Longitude"),
    db: Session = Depends(get_db)
):
    """
    Reverse GPS lookup: Finds the nearest 11kV distribution infrastructure (sections, DTs, switches, substations)
    for given GPS coordinates, with proximity distances and proximity to suspected fault span.
    """
    feeder = db.query(Feeder).filter(Feeder.id == feeder_id).first()
    if not feeder:
        raise HTTPException(status_code=404, detail=f"Feeder {feeder_id} not found")

    substation = db.query(Substation).filter(Substation.id == feeder.substation_id).first()
    sections = db.query(LineSection).filter(LineSection.feeder_id == feeder_id).all()
    transformers = db.query(Transformer).filter(Transformer.feeder_id == feeder_id).all()
    switches = db.query(Switch).filter(Switch.feeder_id == feeder_id).all()

    # Critical loads mapping
    dt_ids = [d.id for d in transformers]
    critical_loads = db.query(CriticalLoad).filter(CriticalLoad.transformer_id.in_(dt_ids)).all() if dt_ids else []
    dt_to_critical = {cl.transformer_id: cl.name for cl in critical_loads}

    items: List[AssetDistanceItem] = []

    # 1. Check Substation
    if substation:
        d_km = haversine_km(lat, lng, substation.latitude, substation.longitude)
        items.append(AssetDistanceItem(
            id=substation.id,
            label=substation.name,
            type="SUBSTATION",
            status="NORMAL",
            lat=substation.latitude,
            lng=substation.longitude,
            distance_km=round(d_km, 3),
            distance_meters=round(d_km * 1000.0, 1),
            metadata={"capacity_mva": substation.capacity_mva}
        ))

    # 2. Check Line Sections
    for sec in sections:
        # Use center/end lat/lng
        s_lat = (sec.start_lat + sec.end_lat) / 2.0 if (sec.start_lat and sec.end_lat) else (sec.end_lat or 13.048)
        s_lng = (sec.start_lng + sec.end_lng) / 2.0 if (sec.start_lng and sec.end_lng) else (sec.end_lng or 77.606)
        d_km = haversine_km(lat, lng, s_lat, s_lng)
        items.append(AssetDistanceItem(
            id=sec.id,
            label=f"Line Section {sec.id}",
            type="SECTION",
            status=sec.status,
            lat=s_lat,
            lng=s_lng,
            distance_km=round(d_km, 3),
            distance_meters=round(d_km * 1000.0, 1),
            metadata={
                "length_km": sec.length_km,
                "conductor": sec.conductor_type,
                "rated_capacity_amps": sec.rated_capacity_amps
            }
        ))

    # 3. Check Transformers
    for dt in transformers:
        is_crit = dt.id in dt_to_critical
        d_km = haversine_km(lat, lng, dt.latitude, dt.longitude)
        items.append(AssetDistanceItem(
            id=dt.id,
            label=f"{dt.id} ({dt_to_critical[dt.id]})" if is_crit else dt.id,
            type="CRITICAL_LOAD" if is_crit else "TRANSFORMER",
            status=dt.status,
            lat=dt.latitude,
            lng=dt.longitude,
            distance_km=round(d_km, 3),
            distance_meters=round(d_km * 1000.0, 1),
            is_critical=is_crit,
            metadata={
                "capacity_kva": dt.capacity_kva,
                "current_load_kva": dt.current_load_kva,
                "critical_name": dt_to_critical.get(dt.id)
            }
        ))

    # 4. Check Switches
    for sw in switches:
        d_km = haversine_km(lat, lng, sw.latitude, sw.longitude)
        items.append(AssetDistanceItem(
            id=sw.id,
            label=f"{sw.id} ({sw.switch_type})",
            type="SWITCH",
            status=sw.current_state,
            lat=sw.latitude,
            lng=sw.longitude,
            distance_km=round(d_km, 3),
            distance_meters=round(d_km * 1000.0, 1),
            metadata={
                "switch_type": sw.switch_type,
                "normal_state": sw.normal_state,
                "current_state": sw.current_state
            }
        ))

    # Sort all items by distance ascending
    items.sort(key=lambda x: x.distance_km)

    nearest = items[0] if items else None
    
    # Distance to suspected fault span (e.g. F4-S14)
    fault_sec = next((i for i in items if i.id == "F4-S14"), None)
    dist_fault_km = fault_sec.distance_km if fault_sec else None

    # Distance to Substation
    sub_item = next((i for i in items if i.type == "SUBSTATION"), None)
    dist_sub_km = sub_item.distance_km if sub_item else None

    return NearestAssetResponse(
        gps_lat=lat,
        gps_lng=lng,
        feeder_id=feeder_id,
        nearest_asset=nearest,
        distance_to_fault_span_km=dist_fault_km,
        distance_to_substation_km=dist_sub_km,
        nearby_assets=items[:6]
    )

