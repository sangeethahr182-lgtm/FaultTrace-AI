import os
import json
import random
import datetime
from sqlalchemy.orm import Session
from app.database.session import SessionLocal, engine, Base
from app.models.models import (
    Substation, Feeder, LineSection, Switch, Transformer,
    Consumer, CriticalLoad, SCADAEvent, Complaint, WeatherObservation
)

SYNTHETIC_BANNER = "SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10"

def seed_database():
    print(f"[{SYNTHETIC_BANNER}] Initializing database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # 1. Substations
        sub1 = Substation(
            id="SUB-01",
            code="HEB-66-11",
            name="Hebbal 66/11kV Substation (Synthetic Demo)",
            capacity_mva=50.0,
            latitude=13.0358,
            longitude=77.5970,
            is_synthetic=True
        )
        db.add(sub1)
        db.flush()

        # 2. Feeders
        feeders_data = [
            {"id": "F4", "code": "F4", "name": "11kV Manyata Tech Park Feeder (Synthetic)", "rated": 400.0, "load": 210.0, "status": "TRIPPED"},
            {"id": "F3", "code": "F3", "name": "11kV Nagawara Feeder (Synthetic)", "rated": 400.0, "load": 160.0, "status": "NORMAL"},
            {"id": "F1", "code": "F1", "name": "11kV RT Nagar Feeder (Synthetic)", "rated": 400.0, "load": 190.0, "status": "NORMAL"},
            {"id": "F2", "code": "F2", "name": "11kV Sahakar Nagar Feeder (Synthetic)", "rated": 400.0, "load": 175.0, "status": "NORMAL"},
        ]
        for f in feeders_data:
            db.add(Feeder(
                id=f["id"],
                substation_id=sub1.id,
                code=f["code"],
                name=f["name"],
                voltage_kv=11.0,
                rated_capacity_amps=f["rated"],
                current_load_amps=f["load"],
                status=f["status"],
                is_synthetic=True
            ))
        db.flush()

        # 3. Line Sections for F4 (F4-S1 .. F4-S20)
        # Topology:
        # Trunk: S1 -> S2 -> S3 -> S4 -> S5
        # Branch A: S5 -> S6 -> S7 -> S8 -> S9 -> S10
        # Trunk cont: S5 -> S11 -> S12 -> S13
        # Branch B (Fault zone): S13 -> S14 -> S15 -> S16 (Connects to Tie Switch TS-08)
        # Branch C: S13 -> S17 -> S18 -> S19 -> S20

        # Base coordinate starting at Substation
        base_lat, base_lng = 13.0358, 77.5970
        sections_hierarchy = [
            ("F4-S1", None, 0.4, 0.002, 0.001),
            ("F4-S2", "F4-S1", 0.5, 0.004, 0.002),
            ("F4-S3", "F4-S2", 0.5, 0.006, 0.003),
            ("F4-S4", "F4-S3", 0.4, 0.008, 0.004),
            ("F4-S5", "F4-S4", 0.6, 0.010, 0.005),  # Major branch point with AB-05
            
            # Branch A
            ("F4-S6", "F4-S5", 0.5, 0.011, 0.003),
            ("F4-S7", "F4-S6", 0.4, 0.012, 0.002),
            ("F4-S8", "F4-S7", 0.5, 0.013, 0.001),
            ("F4-S9", "F4-S8", 0.4, 0.014, 0.000),
            ("F4-S10", "F4-S9", 0.5, 0.015, -0.001),  # Near Hospital DT-08

            # Trunk cont
            ("F4-S11", "F4-S5", 0.6, 0.012, 0.007),
            ("F4-S12", "F4-S11", 0.5, 0.014, 0.009),
            ("F4-S13", "F4-S12", 0.5, 0.016, 0.011),  # Major branch point with AB-11

            # Branch B (Target Fault Zone F4-S14)
            ("F4-S14", "F4-S13", 0.7, 0.018, 0.013),  # Protected by AB-14
            ("F4-S15", "F4-S14", 0.5, 0.020, 0.014),  # DT-14 with Water Pump
            ("F4-S16", "F4-S15", 0.6, 0.022, 0.016),  # Terminal with Tie Switch TS-08 to F3

            # Branch C
            ("F4-S17", "F4-S13", 0.5, 0.016, 0.014),
            ("F4-S18", "F4-S17", 0.4, 0.017, 0.016),
            ("F4-S19", "F4-S18", 0.5, 0.018, 0.018),
            ("F4-S20", "F4-S19", 0.4, 0.019, 0.020),
        ]

        section_objs = {}
        for idx, (sec_id, parent_id, length_km, dlat, dlng) in enumerate(sections_hierarchy, start=1):
            s_lat = base_lat + dlat - 0.002
            s_lng = base_lng + dlng - 0.001
            e_lat = base_lat + dlat
            e_lng = base_lng + dlng
            
            # Status: If in branch B (S14, S15, S16), mark as DE_ENERGIZED due to fault
            status = "DE_ENERGIZED" if sec_id in ("F4-S14", "F4-S15", "F4-S16") else "ENERGIZED"
            if sec_id == "F4-S14":
                status = "FAULTED"

            sec = LineSection(
                id=sec_id,
                feeder_id="F4",
                upstream_section_id=parent_id,
                section_order=idx,
                length_km=length_km,
                conductor_type="Rabbit ACSR",
                rated_capacity_amps=400.0,
                start_lat=round(s_lat, 6),
                start_lng=round(s_lng, 6),
                end_lat=round(e_lat, 6),
                end_lng=round(e_lng, 6),
                has_fault_indicator=(sec_id in ("F4-S5", "F4-S13", "F4-S14")),
                status=status,
                is_synthetic=True
            )
            db.add(sec)
            section_objs[sec_id] = sec
        db.flush()

        # Sections for F3 (adjacent donor feeder)
        f3_s1 = LineSection(
            id="F3-S1", feeder_id="F3", upstream_section_id=None, section_order=1,
            length_km=0.8, conductor_type="Rabbit ACSR", rated_capacity_amps=400.0,
            start_lat=13.0358, start_lng=77.5970, end_lat=13.0380, end_lng=77.6050,
            has_fault_indicator=False, status="ENERGIZED", is_synthetic=True
        )
        f3_s2 = LineSection(
            id="F3-S2", feeder_id="F3", upstream_section_id="F3-S1", section_order=2,
            length_km=1.2, conductor_type="Rabbit ACSR", rated_capacity_amps=400.0,
            start_lat=13.0380, start_lng=77.6050, end_lat=13.0450, end_lng=77.6150,
            has_fault_indicator=False, status="ENERGIZED", is_synthetic=True
        )
        db.add_all([f3_s1, f3_s2])
        db.flush()

        # 4. Switches
        switches_data = [
            # Feeder breakers
            Switch(id="CB-F4", section_id="F4-S1", feeder_id="F4", switch_type="BREAKER", normal_state="CLOSED", current_state="OPEN", latitude=13.0358, longitude=77.5970, is_synthetic=True),
            Switch(id="CB-F3", section_id="F3-S1", feeder_id="F3", switch_type="BREAKER", normal_state="CLOSED", current_state="CLOSED", latitude=13.0358, longitude=77.5970, is_synthetic=True),
            
            # Air Break Switches on F4
            Switch(id="AB-05", section_id="F4-S5", feeder_id="F4", switch_type="AIR_BREAK", normal_state="CLOSED", current_state="CLOSED", latitude=13.0458, longitude=77.6020, is_synthetic=True),
            Switch(id="AB-11", section_id="F4-S11", feeder_id="F4", switch_type="AIR_BREAK", normal_state="CLOSED", current_state="CLOSED", latitude=13.0478, longitude=77.6040, is_synthetic=True),
            Switch(id="AB-14", section_id="F4-S14", feeder_id="F4", switch_type="AIR_BREAK", normal_state="CLOSED", current_state="CLOSED", latitude=13.0538, longitude=77.6100, is_synthetic=True),
            
            # Tie Switch connecting F4-S16 to F3-S2
            Switch(id="TS-08", section_id="F4-S16", feeder_id="F4", switch_type="TIE_SWITCH", normal_state="OPEN", current_state="OPEN", adjacent_feeder_id="F3", rated_current_amps=400.0, latitude=13.0578, longitude=77.6130, is_synthetic=True),
        ]
        db.add_all(switches_data)
        db.flush()

        # 5. Distribution Transformers (DTs)
        # We need DT-12, DT-13, DT-14, DT-16 in the downstream zone of F4-S14, totaling ~380 consumers
        # and DT-14 hosting District Water Pump #3
        dt_configs = [
            ("DT-01", "F4-S1", 250.0, 110.0, 13.0378, 77.5980, 85, "ENERGIZED"),
            ("DT-02", "F4-S2", 250.0, 95.0, 13.0398, 77.5990, 75, "ENERGIZED"),
            ("DT-03", "F4-S4", 315.0, 140.0, 13.0438, 77.6010, 110, "ENERGIZED"),
            ("DT-04", "F4-S5", 250.0, 100.0, 13.0458, 77.6020, 80, "ENERGIZED"),
            ("DT-05", "F4-S6", 250.0, 85.0, 13.0468, 77.6000, 70, "ENERGIZED"),
            ("DT-06", "F4-S8", 250.0, 90.0, 13.0488, 77.5980, 75, "ENERGIZED"),
            ("DT-07", "F4-S9", 315.0, 130.0, 13.0498, 77.5970, 100, "ENERGIZED"),
            ("DT-08", "F4-S10", 500.0, 240.0, 13.0508, 77.5960, 45, "ENERGIZED"),  # Hospital
            ("DT-09", "F4-S11", 250.0, 105.0, 13.0478, 77.6040, 85, "ENERGIZED"),
            ("DT-10", "F4-S12", 250.0, 95.0, 13.0498, 77.6060, 80, "ENERGIZED"),
            ("DT-11", "F4-S13", 315.0, 120.0, 13.0518, 77.6080, 95, "ENERGIZED"),
            
            # --- FAULT ZONE (Downstream of F4-S14) ---
            # Total consumers = 95 + 90 + 105 + 90 = 380 consumers!
            ("DT-12", "F4-S14", 250.0, 110.0, 13.0538, 77.6100, 95, "DE_ENERGIZED"),
            ("DT-13", "F4-S14", 250.0, 105.0, 13.0545, 77.6105, 90, "DE_ENERGIZED"),
            ("DT-14", "F4-S15", 315.0, 130.0, 13.0558, 77.6110, 105, "DE_ENERGIZED"), # Water Pump #3
            ("DT-16", "F4-S16", 250.0, 95.0, 13.0578, 77.6130, 90, "DE_ENERGIZED"),   # Near TS-08
            
            # Branch C DTs
            ("DT-17", "F4-S17", 250.0, 90.0, 13.0518, 77.6110, 75, "ENERGIZED"),
            ("DT-18", "F4-S18", 250.0, 80.0, 13.0528, 77.6130, 65, "ENERGIZED"),
            ("DT-19", "F4-S19", 250.0, 85.0, 13.0538, 77.6150, 70, "ENERGIZED"),
            ("DT-20", "F4-S20", 315.0, 115.0, 13.0548, 77.6170, 95, "ENERGIZED"),
        ]

        consumer_count = 0
        for dt_id, sec_id, cap, load, lat, lng, num_cons, status in dt_configs:
            dt = Transformer(
                id=dt_id,
                section_id=sec_id,
                feeder_id="F4",
                code=f"TR-{dt_id}",
                capacity_kva=cap,
                current_load_kva=load if status == "ENERGIZED" else 0.0,
                peak_load_kva=cap * 0.85,
                latitude=lat,
                longitude=lng,
                status=status,
                is_synthetic=True
            )
            db.add(dt)
            db.flush()

            # Seed synthetic consumers
            is_outage = (status == "DE_ENERGIZED")
            for c_idx in range(num_cons):
                consumer_count += 1
                c_lat = lat + random.uniform(-0.0005, 0.0005)
                c_lng = lng + random.uniform(-0.0005, 0.0005)
                cat = "DOMESTIC" if c_idx < num_cons - 10 else ("COMMERCIAL" if c_idx < num_cons - 2 else "ESSENTIAL")
                db.add(Consumer(
                    id=f"CON-{consumer_count:05d}",
                    transformer_id=dt_id,
                    consumer_number=f"BES-{random.randint(10000000, 99999999)}",
                    category=cat,
                    sanctioned_load_kw=round(random.uniform(2.0, 6.0), 1),
                    latitude=round(c_lat, 6),
                    longitude=round(c_lng, 6),
                    status="OUTAGE" if is_outage else "CONNECTED",
                    is_synthetic=True
                ))

        # 6. Critical Loads (Hospital on DT-08, Water Pump #3 on DT-14)
        cl1 = CriticalLoad(
            id="CL-01",
            transformer_id="DT-08",
            name="Lifeline General Hospital (Synthetic)",
            load_type="HOSPITAL",
            sanctioned_load_kw=150.0,
            priority_level=1,
            backup_gen_kva=125.0,
            contact_phone="+91-80-2345-6789",
            is_synthetic=True
        )
        cl2 = CriticalLoad(
            id="CL-02",
            transformer_id="DT-14",
            name="District Water Pump #3 (Synthetic)",
            load_type="WATER_PUMP",
            sanctioned_load_kw=80.0,
            priority_level=1,
            backup_gen_kva=0.0,
            contact_phone="+91-80-2456-7890",
            is_synthetic=True
        )
        db.add_all([cl1, cl2])
        db.flush()

        # 7. Demo Scenario F4 Ingestion (Heavy Rain, 48 km/h Gust, 142 Complaints)
        # SCADA Event: Feeder Overcurrent/Earth-Fault Trip on F4
        now = datetime.datetime.utcnow()
        scada_trip = SCADAEvent(
            timestamp=now - datetime.timedelta(minutes=12),
            feeder_id="F4",
            section_id="F4-S14",
            event_type="OVERCURRENT_TRIP",
            current_amps=680.0,  # Fault current surge
            voltage_kv=0.0,
            description="Feeder F4 Breaker CB-F4 Tripped on Phase-B Earth Fault / Overcurrent",
            is_synthetic=True
        )
        db.add(scada_trip)

        # Weather Observation: Heavy rain, 48 km/h wind gust
        weather_obs = WeatherObservation(
            timestamp=now - datetime.timedelta(minutes=15),
            temperature_c=22.4,
            rainfall_mm=38.6,  # Heavy rainfall
            wind_gust_kmh=48.0, # 48 km/h gust requirement
            wind_speed_kmh=29.0,
            humidity_pct=94.0,
            lightning_strikes=14,
            is_synthetic_fallback=True
        )
        db.add(weather_obs)

        # 142 Synthetic Complaints concentrated in the affected outage pocket:
        # DT-12, DT-13, DT-14, DT-16 (and a few ambient scattered calls)
        affected_dts = ["DT-12", "DT-13", "DT-14", "DT-16"]
        complaints_list = []
        for i in range(142):
            call_time = now - datetime.timedelta(minutes=random.randint(1, 15), seconds=random.randint(0, 59))
            # 85% of complaints come from the faulted downstream pocket
            if random.random() < 0.88:
                chosen_dt = random.choice(affected_dts)
                sec_id = "F4-S14" if chosen_dt in ("DT-12", "DT-13") else ("F4-S15" if chosen_dt == "DT-14" else "F4-S16")
                cat = "NO_POWER"
                if i < 8:
                    cat = "SPARK_REPORTED"
                    desc = "Severe tree branch spark observed on 11kV conductor near section S14"
                elif i < 15:
                    cat = "VOLTAGE_FLUCTUATION"
                    desc = "Lights dimmed drastically before total blackout"
                else:
                    desc = "Sudden complete power cut reported via 1912 IVRS"
            else:
                # Ambient noise complaints elsewhere
                chosen_dt = random.choice(["DT-04", "DT-07", "DT-11"])
                sec_id = "F4-S4"
                cat = "VOLTAGE_FLUCTUATION"
                desc = "Momentary voltage dip during thunderclap"

            c = Complaint(
                timestamp=call_time,
                transformer_id=chosen_dt,
                section_id=sec_id,
                category=cat,
                source=random.choice(["IVRS", "APP", "CALL_CENTER", "SMS"]),
                description=desc,
                is_verified=False,
                is_synthetic=True
            )
            complaints_list.append(c)

        db.add_all(complaints_list)
        db.commit()

        print(f"[{SYNTHETIC_BANNER}] Seed completed successfully:")
        print(f"  - 1 Substation (SUB-01)")
        print(f"  - 4 Feeders (F4, F3, F1, F2)")
        print(f"  - 20 Line Sections on F4 (F4-S1 .. F4-S20)")
        print(f"  - 6 Switches (including CB-F4, AB-05, AB-11, AB-14, TS-08)")
        print(f"  - 20 Distribution Transformers (DT-01 .. DT-20)")
        print(f"  - {consumer_count} Synthetic Consumers (~380 in fault pocket DT-12, 13, 14, 16)")
        print(f"  - 2 Critical Loads (Hospital on DT-08, Water Pump #3 on DT-14)")
        print(f"  - 1 SCADA Trip Event on F4")
        print(f"  - 1 Weather record: 38.6mm rain, 48 km/h wind gust")
        print(f"  - 142 Synthetic Complaints generated in 15-min rolling window")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
