"""
shot_model.py - XGBoost Expected Effective Field Goal % (xeFG%) and Shot-Making Over Expected (SMOE).

Formulation:
  p_hat = P(Shot Made | shot_distance, shot_x, shot_y, shot_angle, period, clock_seconds, is_3pt, is_corner_3)
  Expected Points = val * p_hat  (val in {2, 3})
  xeFG% = (val * p_hat) / 2
  SMOE = eFG% - xeFG%
"""

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import polars as pl
import xgboost as xgb


def extract_shot_features(
    shot_x: Sequence[float],
    shot_y: Sequence[float],
    shot_dist: Sequence[float],
    period: Sequence[int],
    clock_seconds: Sequence[float],
    is_3pt: Sequence[int],
) -> np.ndarray:
    """Extracts geometric and situational feature matrix for shot modeling."""
    n = len(shot_x)
    features = np.zeros((n, 7), dtype=np.float32)

    for i in range(n):
        x = float(shot_x[i]) if shot_x[i] is not None and not math.isnan(shot_x[i]) else 0.0
        y = float(shot_y[i]) if shot_y[i] is not None and not math.isnan(shot_y[i]) else 15.0
        dist = float(shot_dist[i]) if shot_dist[i] is not None and not math.isnan(shot_dist[i]) else math.sqrt(x*x + y*y)
        p = int(period[i]) if period[i] is not None else 1
        clk = float(clock_seconds[i]) if clock_seconds[i] is not None else 360.0
        is_three = int(is_3pt[i]) if is_3pt[i] is not None else (1 if dist >= 23.75 else 0)

        # Corner 3: |x| >= 22.0 and y <= 9.25
        is_corner = 1 if (abs(x) >= 22.0 and y <= 9.25) else 0
        angle = math.degrees(math.atan2(y, x + 1e-5))

        features[i, 0] = dist
        features[i, 1] = x
        features[i, 2] = y
        features[i, 3] = angle
        features[i, 4] = float(p)
        features[i, 5] = clk
        features[i, 6] = float(is_corner)

    return features


class XGBExpectedShotModel:
    """
    XGBoost model estimating expected shot conversion probabilities and SMOE.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names = [
            "shot_distance",
            "shot_x",
            "shot_y",
            "shot_angle",
            "period",
            "clock_seconds",
            "is_corner_3",
        ]
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def _init_default_classifier(self) -> xgb.XGBClassifier:
        return xgb.XGBClassifier(
            n_estimators=120,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
        )

    def fit(
        self,
        shot_x: Sequence[float],
        shot_y: Sequence[float],
        shot_dist: Sequence[float],
        period: Sequence[int],
        clock_seconds: Sequence[float],
        is_3pt: Sequence[int],
        made: Sequence[int],
    ) -> Dict[str, float]:
        """Trains the XGBoost shot model on observed shot outcomes."""
        X = extract_shot_features(shot_x, shot_y, shot_dist, period, clock_seconds, is_3pt)
        y = np.array(made, dtype=np.int32)

        self.model = self._init_default_classifier()
        self.model.fit(X, y)

        # Evaluate train logloss
        preds = self.model.predict_proba(X)[:, 1]
        eps = 1e-7
        preds = np.clip(preds, eps, 1 - eps)
        logloss = -float(np.mean(y * np.log(preds) + (1 - y) * np.log(1 - preds)))

        return {
            "train_samples": len(y),
            "logloss": round(logloss, 4),
            "mean_expected_pct": round(float(np.mean(preds)), 4),
            "observed_pct": round(float(np.mean(y)), 4),
        }

    def predict_proba(
        self,
        shot_x: Sequence[float],
        shot_y: Sequence[float],
        shot_dist: Sequence[float],
        period: Sequence[int],
        clock_seconds: Sequence[float],
        is_3pt: Sequence[int],
    ) -> np.ndarray:
        """Returns P(make) for each shot."""
        X = extract_shot_features(shot_x, shot_y, shot_dist, period, clock_seconds, is_3pt)
        if self.model is not None:
            return self.model.predict_proba(X)[:, 1]

        # Prior distribution fallback if model is un-fitted:
        # Rim (<4 ft): ~65%; Short mid (4-14): ~43%; Long mid: ~40%; 3PT: ~36.5%
        probs = np.zeros(len(shot_dist), dtype=np.float32)
        for i, d in enumerate(shot_dist):
            dist = float(d) if d is not None and not math.isnan(d) else 15.0
            if dist <= 4.0:
                probs[i] = 0.65 - 0.02 * dist
            elif dist <= 14.0:
                probs[i] = 0.44 - 0.005 * (dist - 4)
            elif is_3pt[i]:
                # Corner 3 has higher percentage than above-the-break
                x = shot_x[i] if shot_x[i] is not None else 0.0
                y = shot_y[i] if shot_y[i] is not None else 10.0
                if abs(x) >= 22.0 and y <= 9.25:
                    probs[i] = 0.395
                else:
                    probs[i] = 0.360
            else:
                probs[i] = 0.40 - 0.004 * (dist - 14)
        return probs

    def evaluate_shots(
        self,
        shot_x: Sequence[float],
        shot_y: Sequence[float],
        shot_dist: Sequence[float],
        period: Sequence[int],
        clock_seconds: Sequence[float],
        is_3pt: Sequence[int],
        made: Sequence[int],
    ) -> Dict[str, Any]:
        """
        Computes expected effective field goal % (xeFG%) and Shot-Making Over Expected (SMOE).
        """
        p_hat = self.predict_proba(shot_x, shot_y, shot_dist, period, clock_seconds, is_3pt)
        n = len(p_hat)
        if n == 0:
            return {"x_efg_pct": 0.0, "actual_efg_pct": 0.0, "smoe": 0.0, "shots_analyzed": 0}

        # Actual eFG% = (FGM + 0.5 * 3PM) / FGA
        fgm = sum(made)
        three_pm = sum(m for m, three in zip(made, is_3pt) if three and m)
        actual_efg = (fgm + 0.5 * three_pm) / n

        # xeFG% = sum( (val * p_hat) / 2 ) / n
        expected_points = np.zeros(n, dtype=np.float64)
        for i in range(n):
            val = 3.0 if is_3pt[i] else 2.0
            expected_points[i] = val * p_hat[i]

        expected_efg = float(np.sum(expected_points) / (2.0 * n))
        smoe = actual_efg - expected_efg

        return {
            "shots_analyzed": n,
            "actual_efg_pct": round(actual_efg, 4),
            "x_efg_pct": round(expected_efg, 4),
            "smoe": round(smoe, 4),
            "expected_points_per_shot": round(float(np.mean(expected_points)), 3),
            "actual_points_per_shot": round(float((fgm * 2 + three_pm) / n), 3),
        }

    def save(self, filepath: Union[str, Path]) -> None:
        """Saves trained XGBoost shot model to JSON."""
        if self.model is None:
            raise ValueError("Cannot save an unfitted model.")
        self.model.save_model(str(filepath))

    def load(self, filepath: Union[str, Path]) -> None:
        """Loads trained XGBoost model from JSON."""
        self.model = self._init_default_classifier()
        self.model.load_model(str(filepath))
