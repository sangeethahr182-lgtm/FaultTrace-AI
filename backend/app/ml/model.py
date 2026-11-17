import os
import json
import joblib
from typing import Tuple, List, Dict, Any, Optional
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from app.ml.features import FEATURE_COLUMNS
from app.ml.calibration import PlattCalibrator
from app.ml.explainer import ModelExplainer
from app.config import settings

class FaultLocalizationModel:
    """
    XGBoost Fault Localization Classifier.
    Ranks candidate line sections following feeder trip events.
    Notice: Trained on SYNTHETIC DEMO DATA.
    """

    def __init__(self):
        self.model = XGBClassifier(
            n_estimators=120,
            max_depth=4,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            eval_metric="logloss",
            random_state=42
        )
        self.calibrator = PlattCalibrator()
        self.explainer = None
        self.is_trained = False

    def fit(self, X_train: pd.DataFrame, y_train: np.ndarray, X_val: pd.DataFrame = None, y_val: np.ndarray = None):
        X_tr = X_train[FEATURE_COLUMNS]
        self.model.fit(X_tr, y_train)
        self.is_trained = True
        self.explainer = ModelExplainer(self.model)

        # Fit calibrator on validation fold if present
        if X_val is not None and y_val is not None and len(y_val) > 0:
            raw_val_scores = self.model.predict_proba(X_val[FEATURE_COLUMNS])[:, 1]
            self.calibrator.fit(raw_val_scores, y_val)

    def predict_candidate_scores(self, X_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Returns: (raw_scores, calibrated_confidences)
        """
        if not self.is_trained:
            raise RuntimeError("Model is not trained or loaded yet.")
        
        X_mat = X_df[FEATURE_COLUMNS]
        raw_scores = self.model.predict_proba(X_mat)[:, 1]
        calibrated_conf = self.calibrator.calibrate(raw_scores)
        return raw_scores, calibrated_conf

    def explain(self, candidate_row: pd.DataFrame, top_k: int = 5):
        if self.explainer is None:
            self.explainer = ModelExplainer(self.model)
        return self.explainer.explain_candidate(candidate_row, top_k=top_k)

    def save(self, output_dir: str = None):
        out_dir = output_dir or settings.MODEL_DIR
        os.makedirs(out_dir, exist_ok=True)
        joblib.dump(self.model, os.path.join(out_dir, "xgboost_fault_model.joblib"))
        joblib.dump(self.calibrator, os.path.join(out_dir, "calibrator.joblib"))
        with open(os.path.join(out_dir, "features.json"), "w") as f:
            json.dump({"features": FEATURE_COLUMNS}, f, indent=2)

    def load(self, model_dir: str = None):
        m_dir = model_dir or settings.MODEL_DIR
        model_path = os.path.join(m_dir, "xgboost_fault_model.joblib")
        calibrator_path = os.path.join(m_dir, "calibrator.joblib")

        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.is_trained = True
            self.explainer = None  # Lazy load explainer
            if os.path.exists(calibrator_path):
                self.calibrator = joblib.load(calibrator_path)
            return True
        return False
