import random
import datetime
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Any

class ScenarioSimulator:
    """
    Synthetic Fault Scenario Simulator for 11kV Radial Distribution Network.
    Generates realistic fault scenarios for training and evaluating XGBoost model.
    Scenario-based splitting ensures no data leakage.
    
    NOTICE: All outputs are SYNTHETIC DEMO DATA.
    """

    def __init__(self, section_ids: List[str] = None):
        self.section_ids = section_ids or [f"F4-S{i}" for i in range(1, 21)]
        # Section lengths
        self.section_lengths = {s: round(random.uniform(0.3, 0.8), 2) for s in self.section_ids}
        # Historical fault frequency (synthetic baseline)
        self.historical_freqs = {s: round(random.uniform(0.05, 0.45), 3) for s in self.section_ids}
        # Sections with Fault Current Indicators (FCIs)
        self.fci_sections = {"F4-S5", "F4-S13", "F4-S14"}

    def generate_scenario(self, scenario_id: int) -> Tuple[str, Dict[str, Any], pd.DataFrame]:
        """
        Simulates one full fault incident:
        1. Selects true faulted section
        2. Simulates weather (rain, gust, lightning)
        3. Simulates SCADA breaker trip and voltage sags
        4. Simulates consumer complaints with under-reporting noise
        5. Computes candidate section feature rows for this scenario
        """
        true_section = random.choice(self.section_ids)
        
        # Weather conditions
        is_storm = random.random() < 0.65
        rainfall_mm = round(random.uniform(15.0, 55.0) if is_storm else random.uniform(0.0, 10.0), 1)
        wind_gust_kmh = round(random.uniform(25.0, 65.0) if is_storm else random.uniform(5.0, 22.0), 1)
        lightning_strikes = random.randint(3, 25) if is_storm else random.randint(0, 2)
        
        # Breaker trip status
        breaker_tripped = 1.0

        # Simulate topology depth (S1=1, S20=7)
        sec_num = {s: int(s.split("-S")[1]) for s in self.section_ids}
        true_num = sec_num[true_section]

        rows = []
        for s in self.section_ids:
            s_num = sec_num[s]
            is_target = (s == true_section)
            is_downstream_of_fault = (s_num >= true_num)  # simplified downstream approximation

            # Downstream DTs and Consumers affected
            dt_count = max(1, 6 - (s_num // 4))
            total_consumers = dt_count * random.randint(70, 110)

            # Complaint simulation with under-reporting (20% - 50% reporting rate)
            reporting_rate = random.uniform(0.20, 0.48)
            if is_downstream_of_fault:
                expected_complaints = int(total_consumers * reporting_rate)
                complaints = max(0, int(np.random.normal(expected_complaints, expected_complaints * 0.15)))
                voltage_drop = round(random.uniform(0.85, 1.0), 3)
                spark_reports = random.randint(2, 7) if is_target else (1 if random.random() < 0.1 else 0)
            else:
                # Upstream or healthy branch: ambient false calls
                complaints = random.randint(0, 4)
                voltage_drop = round(random.uniform(0.0, 0.15), 3)
                spark_reports = 1 if random.random() < 0.03 else 0

            # FCI activation
            fci_active = 1.0 if (s in self.fci_sections and is_downstream_of_fault and random.random() < 0.92) else 0.0

            consumer_density = round(complaints / total_consumers, 4) if total_consumers > 0 else 0.0

            row = {
                "scenario_id": scenario_id,
                "section_id": s,
                "is_fault": 1 if is_target else 0,
                "complaint_count": complaints,
                "downstream_complaints": complaints,
                "consumer_outage_density": consumer_density,
                "downstream_dt_outage_count": dt_count if is_downstream_of_fault else 0,
                "voltage_drop_avg": voltage_drop,
                "breaker_tripped": breaker_tripped,
                "spark_reports": spark_reports,
                "wind_gust_kmh": wind_gust_kmh,
                "rainfall_mm": rainfall_mm,
                "lightning_strikes": lightning_strikes,
                "historical_fault_freq": self.historical_freqs[s],
                "section_length_km": self.section_lengths[s],
                "has_fault_indicator": 1.0 if s in self.fci_sections else 0.0,
                "fci_triggered": fci_active,
                "depth_from_substation": s_num
            }
            rows.append(row)

        metadata = {
            "scenario_id": scenario_id,
            "true_fault_section": true_section,
            "rainfall_mm": rainfall_mm,
            "wind_gust_kmh": wind_gust_kmh,
            "lightning_strikes": lightning_strikes,
        }
        return true_section, metadata, pd.DataFrame(rows)

    def generate_dataset(self, num_scenarios: int = 200) -> pd.DataFrame:
        all_dfs = []
        for sc_id in range(1, num_scenarios + 1):
            _, _, df_sc = self.generate_scenario(sc_id)
            all_dfs.append(df_sc)
        return pd.concat(all_dfs, ignore_index=True)
