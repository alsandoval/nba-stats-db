"""
rapm.py - High-Performance Sparse Matrix Ridge RAPM Solver with Bayesian Priors.

Formulation:
  min_beta sum_s w_s * (y_s - mu - X_s beta)^2 + lambda * ||beta - beta_prior||^2

Where:
  - X_s has +1 for the 5 offensive players, and -1 for the 5 defensive players.
  - Positive ORAPM = player elevates team scoring.
  - Positive DRAPM = player suppresses opponent scoring.
  - Total RAPM = ORAPM + DRAPM (net points per 100 possessions above league average).
  - Uses scipy.sparse.csc_matrix for fast sparse linear solves (<= 1.5s convergence).
"""

from dataclasses import dataclass
import logging
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from .stints import Stint

logger = logging.getLogger(__name__)


@dataclass
class RAPMResult:
    """Stores solved RAPM coefficients and diagnostic metrics."""
    orapm: Dict[int, float]
    drapm: Dict[int, float]
    rapm: Dict[int, float]
    possessions_played: Dict[int, int]
    league_avg_eff: float
    stint_count: int
    player_count: int
    solve_time_sec: float


class RAPMEngine:
    """
    Solves Regularized Adjusted Plus-Minus using sparse linear systems and Ridge regression.
    """

    def __init__(self, lambda_reg: float = 1200.0):
        self.lambda_reg = float(lambda_reg)

    def fit(
        self,
        stints: Sequence[Stint],
        priors: Optional[Dict[int, Tuple[float, float]]] = None,
        min_possessions: int = 1,
    ) -> RAPMResult:
        """
        Fits Regularized Adjusted Plus-Minus on compressed lineup stints.
        
        Args:
            stints: Sequence of Stint objects.
            priors: Optional dict mapping player_id -> (off_prior, def_prior).
            min_possessions: Minimum possessions a stint must have to be included.
            
        Returns:
            RAPMResult containing ORAPM, DRAPM, Total RAPM, and solver timing.
        """
        start_time = time.perf_counter()

        filtered_stints = [s for s in stints if s.possessions >= min_possessions]
        if not filtered_stints:
            raise ValueError("No valid stints available for RAPM regression.")

        # Collect unique players and total possessions
        player_poss: Dict[int, int] = {}
        for s in filtered_stints:
            for p in s.off_players:
                player_poss[p] = player_poss.get(p, 0) + s.possessions
            for p in s.def_players:
                player_poss[p] = player_poss.get(p, 0) + s.possessions

        player_ids = sorted(list(player_poss.keys()))
        p_count = len(player_ids)
        player_to_idx = {pid: i for i, pid in enumerate(player_ids)}

        num_stints = len(filtered_stints)
        total_pts = sum(s.points for s in filtered_stints)
        total_poss = sum(s.possessions for s in filtered_stints)
        league_avg_eff = (total_pts / total_poss) * 100.0 if total_poss > 0 else 114.0

        # Construct sparse design matrix X in coordinate (COO) format
        # Each stint has 5 offensive players (+1) and 5 defensive players (-1)
        row_indices = []
        col_indices = []
        data_values = []
        y_vec = np.zeros(num_stints, dtype=np.float64)
        w_vec = np.zeros(num_stints, dtype=np.float64)

        for s_idx, s in enumerate(filtered_stints):
            y_vec[s_idx] = s.points_per_100 - league_avg_eff
            w_vec[s_idx] = float(s.possessions)

            # 5 Offensive players -> +1.0
            for pid in s.off_players:
                if pid in player_to_idx:
                    row_indices.append(s_idx)
                    col_indices.append(player_to_idx[pid])
                    data_values.append(1.0)

            # 5 Defensive players -> -1.0 (subtraction so positive DRAPM = defensive stop)
            for pid in s.def_players:
                if pid in player_to_idx:
                    row_indices.append(s_idx)
                    col_indices.append(p_count + player_to_idx[pid])
                    data_values.append(-1.0)

        # Build CSC sparse matrix (S x 2P)
        num_cols = 2 * p_count
        X = sp.csc_matrix(
            (data_values, (row_indices, col_indices)),
            shape=(num_stints, num_cols),
            dtype=np.float64,
        )

        # Diagonal weight matrix W (possession counts)
        W = sp.diags(w_vec, shape=(num_stints, num_stints), dtype=np.float64)

        # Prior vector beta_prior (length 2P)
        beta_prior = np.zeros(num_cols, dtype=np.float64)
        if priors:
            for pid, (off_p, def_p) in priors.items():
                if pid in player_to_idx:
                    idx = player_to_idx[pid]
                    beta_prior[idx] = float(off_p)
                    beta_prior[p_count + idx] = float(def_p)

        # Normal equations: (X^T W X + lambda I) beta = X^T W y + lambda beta_prior
        XtW = X.T @ W
        XtWX = XtW @ X
        reg_I = sp.eye(num_cols, dtype=np.float64) * self.lambda_reg
        A = (XtWX + reg_I).tocsc()

        rhs = XtW @ y_vec + (self.lambda_reg * beta_prior)

        # Solve sparse symmetric positive definite linear system
        beta_hat = spla.spsolve(A, rhs)

        # Extract ORAPM and DRAPM
        orapm_dict: Dict[int, float] = {}
        drapm_dict: Dict[int, float] = {}
        rapm_dict: Dict[int, float] = {}

        for pid, idx in player_to_idx.items():
            o_val = float(beta_hat[idx])
            d_val = float(beta_hat[p_count + idx])
            orapm_dict[pid] = round(o_val, 3)
            drapm_dict[pid] = round(d_val, 3)
            rapm_dict[pid] = round(o_val + d_val, 3)

        elapsed = time.perf_counter() - start_time
        logger.info(
            "Solved RAPM for %d players over %d stints in %.3f seconds",
            p_count, num_stints, elapsed
        )

        return RAPMResult(
            orapm=orapm_dict,
            drapm=drapm_dict,
            rapm=rapm_dict,
            possessions_played=player_poss,
            league_avg_eff=round(league_avg_eff, 2),
            stint_count=num_stints,
            player_count=p_count,
            solve_time_sec=round(elapsed, 4),
        )
