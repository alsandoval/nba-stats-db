"""
quant - Quantitative Modeling Engine for Antigravity NBA Analytics Platform.

Modules:
1. stints: Lineup Stint Compression from Possession Parquet Tables.
2. rapm: Sparse Matrix Ridge RAPM with Bayesian Priors (scipy.sparse.csc_matrix).
3. shot_model: XGBoost Expected Effective Field Goal % (xeFG%) and SMOE.
4. win_probability: Real-Time Game Win Probability Model.
"""

from .stints import StintAggregator, Stint
from .rapm import RAPMEngine, RAPMResult
from .shot_model import XGBExpectedShotModel
from .win_probability import XGBWinProbabilityModel

__all__ = [
    "StintAggregator",
    "Stint",
    "RAPMEngine",
    "RAPMResult",
    "XGBExpectedShotModel",
    "XGBWinProbabilityModel",
]
