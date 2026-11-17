import os
import json
import datetime
import numpy as np
import pandas as pd
from sklearn.metrics import (
    precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
)
from app.services.simulator import ScenarioSimulator
from app.ml.features import FEATURE_COLUMNS
from app.ml.model import FaultLocalizationModel
from app.ml.calibration import compute_ece
from app.config import settings

def run_training_pipeline():
    print("=" * 70)
    print("FaultTrace AI - ML Training Pipeline (Scenario-Split)")
    print("SYNTHETIC DEMO DATA - BESCOM Power Hack 2026 Theme 10")
    print("=" * 70)

    # 1. Generate synthetic scenario dataset
    simulator = ScenarioSimulator()
    total_scenarios = 250
    print(f"Generating {total_scenarios} synthetic fault scenarios...")
    df = simulator.generate_dataset(num_scenarios=total_scenarios)
    print(f"Dataset generated: {len(df)} candidate section rows across {total_scenarios} scenarios.")

    # 2. Scenario-based Train / Val / Test split (NO DATA LEAKAGE)
    scenario_ids = np.array(sorted(df["scenario_id"].unique()))
    np.random.seed(42)
    np.random.shuffle(scenario_ids)

    n_train = int(len(scenario_ids) * 0.70)
    n_val = int(len(scenario_ids) * 0.14)
    
    train_ids = set(scenario_ids[:n_train])
    val_ids = set(scenario_ids[n_train:n_train + n_val])
    test_ids = set(scenario_ids[n_train + n_val:])

    train_df = df[df["scenario_id"].isin(train_ids)].copy()
    val_df = df[df["scenario_id"].isin(val_ids)].copy()
    test_df = df[df["scenario_id"].isin(test_ids)].copy()

    print(f"Scenario Split:")
    print(f"  - Train: {len(train_ids)} scenarios ({len(train_df)} rows)")
    print(f"  - Validation: {len(val_ids)} scenarios ({len(val_df)} rows)")
    print(f"  - Test: {len(test_ids)} scenarios ({len(test_df)} rows)")

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df["is_fault"].values

    X_val = val_df[FEATURE_COLUMNS]
    y_val = val_df["is_fault"].values

    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df["is_fault"].values

    # 3. Fit XGBoost Model & Calibrator
    print("\nTraining XGBoost model...")
    fault_model = FaultLocalizationModel()
    fault_model.fit(X_train, y_train, X_val, y_val)

    # 4. Predict on Test Set
    raw_test_scores, calib_test_conf = fault_model.predict_candidate_scores(X_test)
    y_pred_binary = (calib_test_conf >= 0.5).astype(int)

    # Classification Metrics
    prec = float(precision_score(y_test, y_pred_binary, zero_division=0))
    rec = float(recall_score(y_test, y_pred_binary, zero_division=0))
    f1 = float(f1_score(y_test, y_pred_binary, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, calib_test_conf))
    cm = confusion_matrix(y_test, y_pred_binary).tolist()

    # Calibration ECE
    ece, calib_curve = compute_ece(y_test, calib_test_conf, n_bins=10)

    # 5. Top-1 and Top-3 Scenario-level Localisation Accuracy
    # Evaluate model vs Baseline heuristic ("Pick section with most downstream complaints")
    model_top1_hits = 0
    model_top3_hits = 0
    baseline_top1_hits = 0
    baseline_top3_hits = 0
    total_test_scenarios = len(test_ids)

    test_df_eval = test_df.copy()
    test_df_eval["model_score"] = calib_test_conf

    for sc_id in test_ids:
        sc_data = test_df_eval[test_df_eval["scenario_id"] == sc_id]
        true_rows = sc_data[sc_data["is_fault"] == 1]
        if len(true_rows) == 0:
            continue
        true_sec = true_rows.iloc[0]["section_id"]

        # Model Ranking
        ranked_by_model = sc_data.sort_values(by="model_score", ascending=False)["section_id"].tolist()
        if ranked_by_model[0] == true_sec:
            model_top1_hits += 1
        if true_sec in ranked_by_model[:3]:
            model_top3_hits += 1

        # Baseline Ranking (by downstream complaints)
        ranked_by_baseline = sc_data.sort_values(by="downstream_complaints", ascending=False)["section_id"].tolist()
        if ranked_by_baseline[0] == true_sec:
            baseline_top1_hits += 1
        if true_sec in ranked_by_baseline[:3]:
            baseline_top3_hits += 1

    top1_acc = round(model_top1_hits / total_test_scenarios, 4)
    top3_acc = round(model_top3_hits / total_test_scenarios, 4)
    base_top1_acc = round(baseline_top1_hits / total_test_scenarios, 4)
    base_top3_acc = round(baseline_top3_hits / total_test_scenarios, 4)

    # Feature Importances
    importances = fault_model.model.feature_importances_
    feat_imp = {col: round(float(imp), 4) for col, imp in zip(FEATURE_COLUMNS, importances)}
    # Sort feature importances
    feat_imp_sorted = dict(sorted(feat_imp.items(), key=lambda item: item[1], reverse=True))

    print("\n--- ACTUAL MEASURED METRICS (TEST SET) ---")
    print(f"Top-1 Localisation Accuracy: {top1_acc * 100:.1f}%  (Baseline: {base_top1_acc * 100:.1f}%)")
    print(f"Top-3 Localisation Accuracy: {top3_acc * 100:.1f}%  (Baseline: {base_top3_acc * 100:.1f}%)")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall: {rec:.4f}")
    print(f"F1 Score: {f1:.4f}")
    print(f"Expected Calibration Error (ECE): {ece:.4f}")
    print(f"Calibration Method: {fault_model.calibrator.method_applied}")
    print(f"Confusion Matrix [TN, FP], [FN, TP]: {cm}")

    # 6. Save Model Artifacts
    print(f"\nPersisting model artifacts to {settings.MODEL_DIR}...")
    fault_model.save()

    # 7. Persist Metrics JSON
    metrics_report = {
        "model_name": "XGBoost Radial Fault Localization Classifier",
        "trained_at": datetime.datetime.utcnow().isoformat(),
        "evaluation_split": "Scenario-based train/validation/test split (no data leakage across scenarios)",
        "total_scenarios_train": len(train_ids),
        "total_scenarios_val": len(val_ids),
        "total_scenarios_test": total_test_scenarios,
        "total_test_rows": len(test_df),
        "top1_accuracy": top1_acc,
        "top3_accuracy": top3_acc,
        "baseline_top1_accuracy": base_top1_acc,
        "baseline_top3_accuracy": base_top3_acc,
        "roc_auc": round(roc_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "expected_calibration_error_ece": ece,
        "calibration_method": fault_model.calibrator.method_applied,
        "calibration_curve": calib_curve,
        "confusion_matrix": cm,
        "feature_importances": feat_imp_sorted,
        "synthetic_training_statement": (
            "NOTICE: The model is trained and evaluated on SYNTHETIC DEMO DATA generated by the "
            "FaultTrace AI distribution simulator. These metrics validate the end-to-end data processing, "
            "graph-feature correlation, and ML ranking pipeline; they do NOT measure real-world BESCOM accuracy."
        )
    }

    metrics_file = os.path.join(settings.MODEL_DIR, "metrics.json")
    with open(metrics_file, "w") as f:
        json.dump(metrics_report, f, indent=2)

    print(f"Metrics saved to {metrics_file}")
    print("=" * 70)
    return metrics_report

if __name__ == "__main__":
    run_training_pipeline()
