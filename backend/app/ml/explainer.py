import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple
from app.ml.features import FEATURE_COLUMNS, FEATURE_DISPLAY_NAMES

class ModelExplainer:
    """
    Explainability engine using SHAP TreeExplainer with graceful fallback
    to XGBoost feature importances.
    Initializes lazily to prevent module-import slowdowns.
    Never invents explanations.
    """

    def __init__(self, model):
        self.model = model
        self.tree_explainer = None
        self._init_attempted = False

    def _ensure_explainer(self):
        if not self._init_attempted:
            self._init_attempted = True
            try:
                import shap
                self.tree_explainer = shap.TreeExplainer(self.model)
            except Exception:
                self.tree_explainer = None

    def explain_candidate(
        self,
        candidate_features: pd.DataFrame,
        top_k: int = 5
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Calculates feature contributions for a candidate section.
        Returns: (shap_factors_list, explanation_method_string)
        """
        self._ensure_explainer()
        X = candidate_features[FEATURE_COLUMNS].copy()

        if self.tree_explainer is not None:
            try:
                shap_vals = self.tree_explainer.shap_values(X)
                # Handle binary classification shapes
                if isinstance(shap_vals, list) and len(shap_vals) == 2:
                    sv = shap_vals[1][0]
                elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 2:
                    sv = shap_vals[0]
                elif isinstance(shap_vals, np.ndarray) and len(shap_vals.shape) == 3:
                    sv = shap_vals[0, :, 1]
                else:
                    sv = np.array(shap_vals).flatten()[:len(FEATURE_COLUMNS)]

                factors = []
                for idx, col in enumerate(FEATURE_COLUMNS):
                    val = float(X[col].iloc[0])
                    s_val = float(sv[idx])
                    factors.append({
                        "feature": col,
                        "display_name": FEATURE_DISPLAY_NAMES.get(col, col),
                        "value": val,
                        "shap_value": round(s_val, 4),
                        "impact": "INCREASES_FAULT_RISK" if s_val > 0 else "DECREASES_FAULT_RISK"
                    })

                factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
                return factors[:top_k], "SHAP TreeExplainer"

            except Exception:
                pass

        # Fallback to model feature importances
        factors = []
        try:
            importances = self.model.feature_importances_
            for idx, col in enumerate(FEATURE_COLUMNS):
                val = float(X[col].iloc[0])
                imp = float(importances[idx]) if idx < len(importances) else 0.0
                factors.append({
                    "feature": col,
                    "display_name": FEATURE_DISPLAY_NAMES.get(col, col),
                    "value": val,
                    "shap_value": round(imp, 4),
                    "impact": "GLOBAL_IMPORTANCE"
                })
            factors.sort(key=lambda x: x["shap_value"], reverse=True)
            return factors[:top_k], "Feature Importances (SHAP Fallback)"
        except Exception as e:
            return [], f"Failed to compute explanations: {str(e)}"
