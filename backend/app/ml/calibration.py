import numpy as np
from typing import Dict, List, Tuple, Any
from sklearn.linear_model import LogisticRegression

def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> Tuple[float, List[Dict[str, float]]]:
    """
    Computes Expected Calibration Error (ECE) and calibration curve points.
    ECE = sum_{m=1}^M (|B_m| / N) * |acc(B_m) - conf(B_m)|
    """
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    curve_points = []
    n = len(y_true)

    if n == 0:
        return 0.0, []

    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        # In bin indices
        in_bin = (y_prob >= bin_lower) & (y_prob < bin_upper if i < n_bins - 1 else y_prob <= bin_upper)
        prop_in_bin = np.mean(in_bin)

        if np.sum(in_bin) > 0:
            accuracy_in_bin = float(np.mean(y_true[in_bin]))
            confidence_in_bin = float(np.mean(y_prob[in_bin]))
            ece += np.abs(accuracy_in_bin - confidence_in_bin) * prop_in_bin

            curve_points.append({
                "bin_midpoint": round((bin_lower + bin_upper) / 2.0, 3),
                "bin_lower": round(bin_lower, 2),
                "bin_upper": round(bin_upper, 2),
                "mean_confidence": round(confidence_in_bin, 4),
                "mean_accuracy": round(accuracy_in_bin, 4),
                "sample_count": int(np.sum(in_bin))
            })
        else:
            curve_points.append({
                "bin_midpoint": round((bin_lower + bin_upper) / 2.0, 3),
                "bin_lower": round(bin_lower, 2),
                "bin_upper": round(bin_upper, 2),
                "mean_confidence": round((bin_lower + bin_upper) / 2.0, 3),
                "mean_accuracy": 0.0,
                "sample_count": 0
            })

    return round(float(ece), 4), curve_points


class PlattCalibrator:
    """
    Platt Scaling Calibrator (logistic regression on raw decision scores).
    Only applied if validation split size is sufficient; otherwise reports uncalibrated.
    """
    def __init__(self, min_samples_threshold: int = 80):
        self.min_samples_threshold = min_samples_threshold
        self.calibrator = LogisticRegression(C=1.0, solver='lbfgs')
        self.is_fitted = False
        self.method_applied = "Uncalibrated (insufficient validation samples)"

    def fit(self, raw_scores: np.ndarray, y_val: np.ndarray):
        if len(y_val) >= self.min_samples_threshold and len(np.unique(y_val)) > 1:
            X = raw_scores.reshape(-1, 1)
            self.calibrator.fit(X, y_val)
            self.is_fitted = True
            self.method_applied = "Platt Scaling (Logistic Sigmoid)"
        else:
            self.is_fitted = False
            self.method_applied = f"Uncalibrated (sample count {len(y_val)} < threshold {self.min_samples_threshold})"

    def calibrate(self, raw_scores: np.ndarray) -> np.ndarray:
        if self.is_fitted:
            X = raw_scores.reshape(-1, 1)
            # Probability of positive class
            return self.calibrator.predict_proba(X)[:, 1]
        # Return raw clipped scores if uncalibrated
        return np.clip(raw_scores, 0.0, 1.0)
