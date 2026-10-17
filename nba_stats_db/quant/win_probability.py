"""
win_probability.py - Real-Time NBA Game Win Probability Model using XGBoost.

Evaluates:
  P(Home Team Wins | score_margin, seconds_remaining, period, possession_home, margin_velocity)

Based on Bill James & Stern / Winston Markov volatility models:
  margin_velocity = score_margin / sqrt(seconds_remaining + 1)
"""

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import xgboost as xgb


def extract_win_prob_features(
    score_margin: Sequence[int],
    seconds_remaining: Sequence[float],
    period: Sequence[int],
    possession_home: Sequence[int],
) -> np.ndarray:
    """Constructs tabular feature matrix for real-time win probability evaluation."""
    n = len(score_margin)
    features = np.zeros((n, 5), dtype=np.float32)

    for i in range(n):
        margin = float(score_margin[i])
        sec_rem = max(0.0, float(seconds_remaining[i]))
        p = float(period[i])
        poss_home = float(possession_home[i])
        # Volatility standardized lead
        margin_velocity = margin / math.sqrt(sec_rem + 1.0)

        features[i, 0] = margin
        features[i, 1] = sec_rem
        features[i, 2] = p
        features[i, 3] = poss_home
        features[i, 4] = margin_velocity

    return features


def analytical_win_prob_prior(
    score_margin: float,
    seconds_remaining: float,
    possession_home: int = 1,
    home_court_advantage: float = 2.5,
) -> float:
    """
    Continuous Brownian motion sigmoid prior for win probability.
    
    Standard deviation of an NBA game (~2880s) is ~12.5 points.
    Volatility at time t: sigma(t) = 12.5 * sqrt(t / 2880)
    """
    sec = max(0.0, seconds_remaining)
    if sec <= 0.0:
        if score_margin > 0:
            return 1.0
        elif score_margin < 0:
            return 0.0
        return 0.5

    # Home court advantage decays as time elapses
    decayed_hca = home_court_advantage * (sec / 2880.0)
    # Possession value adjustment (~1.1 points for having the ball)
    poss_adj = 1.1 if possession_home == 1 else -1.1

    adj_margin = score_margin + decayed_hca + poss_adj
    sigma_t = max(1.2, 12.5 * math.sqrt(sec / 2880.0))

    # Standard normal / logistic cumulative link
    z = adj_margin / sigma_t
    prob = 1.0 / (1.0 + math.exp(-1.7 * z))
    return float(np.clip(prob, 0.001, 0.999))


class XGBWinProbabilityModel:
    """
    Evaluates real-time win probability using XGBoost with Brownian motion prior fallback.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[xgb.XGBClassifier] = None
        self.feature_names = [
            "score_margin",
            "seconds_remaining",
            "period",
            "possession_home",
            "margin_velocity",
        ]
        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def _init_default_classifier(self) -> xgb.XGBClassifier:
        return xgb.XGBClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.07,
            subsample=0.85,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
        )

    def fit(
        self,
        score_margin: Sequence[int],
        seconds_remaining: Sequence[float],
        period: Sequence[int],
        possession_home: Sequence[int],
        home_won: Sequence[int],
    ) -> Dict[str, float]:
        """Trains the XGBoost classifier on historical game state snapshots."""
        X = extract_win_prob_features(score_margin, seconds_remaining, period, possession_home)
        y = np.array(home_won, dtype=np.int32)

        self.model = self._init_default_classifier()
        self.model.fit(X, y)

        preds = self.model.predict_proba(X)[:, 1]
        eps = 1e-7
        preds = np.clip(preds, eps, 1 - eps)
        logloss = -float(np.mean(y * np.log(preds) + (1 - y) * np.log(1 - preds)))

        return {
            "train_samples": len(y),
            "logloss": round(logloss, 4),
            "mean_win_prob": round(float(np.mean(preds)), 4),
        }

    def predict_win_probability(
        self,
        score_margin: float,
        seconds_remaining: float,
        period: int = 1,
        possession_home: int = 1,
    ) -> float:
        """Returns P(Home Team Wins) in [0.0, 1.0]."""
        if seconds_remaining <= 0:
            if score_margin > 0:
                return 1.0
            elif score_margin < 0:
                return 0.0
            return 0.5

        if self.model is not None:
            X = extract_win_prob_features(
                [score_margin], [seconds_remaining], [period], [possession_home]
            )
            return float(self.model.predict_proba(X)[0, 1])

        return analytical_win_prob_prior(
            score_margin=score_margin,
            seconds_remaining=seconds_remaining,
            possession_home=possession_home,
        )

    def compute_game_timeline(
        self,
        game_states: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Evaluates continuous win probability across all actions of a game.
        """
        timeline = []
        for state in game_states:
            margin = state.get("score_margin", 0)
            sec_rem = state.get("seconds_remaining", 0.0)
            period = state.get("period", 1)
            poss_home = 1 if state.get("possession_team_id") == state.get("home_team_id") else 0

            wp = self.predict_win_probability(
                score_margin=margin,
                seconds_remaining=sec_rem,
                period=period,
                possession_home=poss_home,
            )
            timeline.append({
                "period": period,
                "seconds_remaining": sec_rem,
                "score_margin": margin,
                "home_score": state.get("home_score", 0),
                "away_score": state.get("away_score", 0),
                "home_win_prob": round(wp, 4),
                "away_win_prob": round(1.0 - wp, 4),
            })
        return timeline

    def save(self, filepath: Union[str, Path]) -> None:
        """Saves trained win probability model to file."""
        if self.model is None:
            raise ValueError("Cannot save an unfitted model.")
        self.model.save_model(str(filepath))

    def load(self, filepath: Union[str, Path]) -> None:
        """Loads trained win probability model from file."""
        self.model = self._init_default_classifier()
        self.model.load_model(str(filepath))
