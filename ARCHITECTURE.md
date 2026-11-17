# FaultTrace AI – System Architecture
**BESCOM Power Hack 2026 – Theme 10: Digital Transformation of BESCOM Distribution Operations**

> **SYNTHETIC DEMO DATA NOTICE**  
> All data utilized in FaultTrace AI (substations, 11kV feeders, line sections, distribution transformers, consumer meters, complaints, SCADA events, and coordinates) is **100% SYNTHETIC DEMO DATA**. FaultTrace AI has no access to BESCOM production SCADA, GIS, AMI, or consumer databases. Synthetic models and mock coordinates represent illustrative distribution topology for algorithmic demonstration only.

> **ADVISORY NOTICE**  
> FaultTrace AI is an **Advisory Decision-Support System only**. The system never executes remote switching and never declares an electrical distribution network "safe". Every restoration step is explicitly labeled: **"Advisory: requires engineering validation and operator authorisation"**.

---

## 1. High-Level Data Flow

```mermaid
flowchart TD
    subgraph Data Sources [Data Sources - Synthetic Demo Data]
        SCADA[Synthetic SCADA Events\nTrip, Lockout, Voltage]
        Complaints[Synthetic Consumer Complaints\nIVRS, SMS, App 15-min Window]
        Weather[Open-Meteo API\nwith Sample Weather Fallback]
        GIS[Synthetic Network Topology\nSubstations, Feeders, DTs, Switches]
    end

    subgraph Core Engine [FaultTrace AI Core Backend Engine]
        DB[(Database: SQLite / PostgreSQL)]
        GraphEngine[NetworkX Radial Graph Engine\nDownstream Traversal & Pruning]
        FeatureEng[Feature Engineering Service\n15-min Rolling Correlation]
        XGBoostModel[XGBoost Classifier + SHAP TreeExplainer\nScenario-Split ML Pipeline]
        RestorationEngine[Advisory Restoration Engine\nCapacity & Radial Checks]
    end

    subgraph API Layer [FastAPI REST Endpoints]
        API_Overview["/api/dashboard/overview"]
        API_Feeders["/api/feeders & /topology"]
        API_Faults["/api/faults/analyze & /predictions"]
        API_Assets["/api/assets/affected"]
        API_Restoration["/api/restoration/generate & /plans"]
        API_Analytics["/api/analytics/metrics"]
    end

    subgraph Frontend [React 18 Control-Room UI]
        UI_Overview[Control Room Overview]
        UI_Fault[Fault Intelligence & SHAP]
        UI_Map[Leaflet GIS Network Map]
        UI_Restoration[Advisory Restoration & Crew Dispatch]
        UI_Data[Data Management & Simulator Ingest]
        UI_Analytics[Model Calibration & Operational Trends]
    end

    Data Sources --> DB
    DB --> GraphEngine
    DB --> FeatureEng
    Weather --> FeatureEng
    GraphEngine --> FeatureEng
    FeatureEng --> XGBoostModel
    XGBoostModel --> RestorationEngine
    GraphEngine --> RestorationEngine
    RestorationEngine --> DB
    DB --> API Layer
    API Layer --> Frontend
```

---

## 2. Component Architecture

### A. Graph Engine (`app.graph.engine`)
- **Radial Tree Representation**: Models feeders as directed and undirected graphs from Substation Breakers down to Line Sections, Air-Break (AB) Switches, Distribution Transformers (DTs), and Consumers.
- **Radial Tree Pruning**:
  - Eliminates candidate fault sections where telemetry indicates downstream devices remain energized (an upstream section cannot be opened/faulted if power reaches downstream nodes on the same radial path).
  - Traverses tree downstream from tripped feeder breakers to isolate candidate fault sections.
- **Topology Verification Checks**:
  - `radial_connectivity_check`: Verifies no closed cycles are introduced when closing tie-switches.
  - `rated_capacity_sum_check`: Validates that transferred downstream DT load does not exceed the emergency rated capacity of the donor feeder or tie-switch.
  - `tie_switch_availability_check`: Checks that candidate tie-switches are currently open, functional, and inter-connected to energized adjacent feeders.

### B. Machine Learning Pipeline (`app.ml`)
- **Simulator (`simulator.py`)**: Generates ground-truth fault scenarios with realistic physical distributions (heavy rain, wind gusts, consumer call lag, under-reporting noise, voltage sags).
- **Scenario-based Train/Test Split**: Prevents data leakage by splitting full fault incidents rather than individual rows.
- **Ranking Model (`model.py`)**: XGBoost classifier trained on synthetic feature vectors.
- **Model Confidence & Calibration (`calibration.py`)**:
  - Raw scores transformed into calibrated probabilities via Platt scaling / Isotonic regression when validation sample size allows.
  - Reports Expected Calibration Error (ECE), ROC-AUC, Precision, Recall, F1, Top-1 and Top-3 Section Localisation Accuracy.
  - Compared against the operational baseline ("Pick section with highest downstream complaints").
- **Explainability (`explainer.py`)**:
  - TreeExplainer generates exact feature impact SHAP values (waterfall/bar breakdown).
  - Graceful fallback to global feature importances if SHAP calculation encounters memory or feature shape constraints.

### C. Advisory Restoration Engine (`app.services.restoration`)
- Calculates affected critical loads (hospitals, water pumping stations, oxygen plants).
- Computes restoration priority score based on critical asset weights, consumer count, and unserved energy.
- Determines physical isolation points (e.g., open Air-Break Switch AB-14).
- Determines load transfer via Tie Switches (e.g., TS-08 to Feeder F3).
- Generates step-by-step operator advisory instructions with mandatory safety caveats.
- Computes approximate crew dispatch coordinates and route to the faulted span.

---

## 3. Database Schema (`app.models`)

1. **`substations`**: Substation ID, code, name, capacity MVA, latitude, longitude, synthetic flag.
2. **`feeders`**: Feeder ID, substation ID, code (e.g. F4), voltage kV (11kV), rated capacity A, current load A, status.
3. **`line_sections`**: Section ID (e.g. F4-S14), feeder ID, upstream section ID, length km, conductor type, rated capacity A, coordinates path, has_fault_indicator.
4. **`switches`**: Switch ID, section ID, type (`BREAKER`, `AIR_BREAK`, `TIE_SWITCH`), normal state (`CLOSED`/`OPEN`), current state, adjacent feeder ID (for tie switches), synthetic coordinates.
5. **`transformers`**: DT ID (e.g. DT-14), section ID, rated capacity kVA, peak load kVA, latitude, longitude, status (`ENERGIZED`/`DE_ENERGIZED`).
6. **`consumers`**: Consumer account ID, transformer ID, category (`DOMESTIC`, `COMMERCIAL`, `INDUSTRIAL`, `ESSENTIAL`), sanctioned load kW, synthetic coordinates.
7. **`critical_loads`**: Critical load ID, transformer ID, name (e.g. "District Water Pump #3"), priority level (1-5), backup generator available, contact number.
8. **`scada_events`**: Event ID, timestamp, feeder ID, section ID, event type (`OVERCURRENT_TRIP`, `EARTH_FAULT_TRIP`, `AUTO_RECLOSE_LOCKOUT`, `VOLTAGE_SAG`), current A, voltage kV, status.
9. **`complaints`**: Complaint ID, timestamp, consumer ID, transformer ID, section ID, category, verified status.
10. **`weather_observations`**: ID, timestamp, temperature C, rainfall mm, wind gust kmh, lightning strike count, is_synthetic_fallback.
11. **`fault_predictions`**: Prediction ID, timestamp, feeder ID, candidate section ID, model score, calibrated confidence, rank, shap_values (JSON), status.
12. **`restoration_plans`**: Plan ID, prediction ID, feeder ID, isolated section ID, tie_switch_id, advisory steps (JSON), capacity check passed, radial check passed, crew dispatch point (JSON), status.
13. **`crew_dispatches`**: Dispatch ID, plan ID, crew team name, vehicle ID, target coordinates, estimated ETA mins, status.

---

## 4. API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/dashboard/overview` | Feeder health, active faults, total affected consumers, 24h summary |
| `GET` | `/api/feeders` | List all 11kV feeders with real-time status and metrics |
| `GET` | `/api/feeders/{id}/topology` | Graph nodes & edges for GIS/topology rendering (sections, DTs, switches) |
| `POST` | `/api/events/ingest` | Ingest synthetic SCADA trips or AMI outage alerts |
| `POST` | `/api/data/upload` | Upload synthetic CSV/JSON datasets with validation |
| `POST` | `/api/faults/analyze` | Run NetworkX pruning + XGBoost ranking + SHAP explanation |
| `GET` | `/api/faults/predictions` | Retrieve recent fault localization predictions |
| `GET` | `/api/faults/{id}` | Detailed fault analysis with SHAP waterfall & candidate sections |
| `GET` | `/api/assets/affected` | Affected DTs, consumers, and critical loads for a fault |
| `POST` | `/api/restoration/generate` | Generate advisory isolation, tie-switch backfeed, and crew route |
| `GET` | `/api/restoration/plans` | List active advisory restoration plans |
| `GET` | `/api/weather` | Current weather (Open-Meteo or synthetic fallback badge) |
| `GET` | `/api/analytics/metrics` | Model evaluation report (ECE, ROC-AUC, F1, Top-1/Top-3, baseline) |

---

## 5. Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.0, Pydantic v2, NetworkX, XGBoost, Scikit-Learn, SHAP, SQLite / PostgreSQL.
- **Frontend**: React 18, Vite, Tailwind CSS, Leaflet, React-Leaflet, Recharts, Lucide Icons.
- **Deployment**: Local execution via Python venv & Vite dev server, plus containerized multi-service `docker-compose.yml`.
