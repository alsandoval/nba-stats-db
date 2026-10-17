"""
test_rapm_engine.py - Tests for Stint Compression and Sparse Matrix Ridge RAPM Solver.
"""

import time
import unittest
import numpy as np

from nba_stats_db.possession.state_machine import PossessionEvent
from nba_stats_db.quant.stints import Stint, StintAggregator
from nba_stats_db.quant.rapm import RAPMEngine, RAPMResult


class TestRAPMEngine(unittest.TestCase):
    def setUp(self):
        # Generate synthetic possession events with 20 players (2 teams of 10)
        self.team1 = 1610612738  # BOS
        self.team2 = 1610612747  # LAL
        self.team1_players = list(range(1001, 1011))
        self.team2_players = list(range(2001, 2011))

        self.possessions = []
        clock = 720.0
        # Create 1000 synthetic possessions across varying lineups
        for i in range(1000):
            # Pick 5 from team1, 5 from team2
            off_p = self.team1_players[:5] if (i // 50) % 2 == 0 else self.team1_players[2:7]
            def_p = self.team2_players[:5] if (i // 70) % 2 == 0 else self.team2_players[3:8]
            pts = 2 if i % 2 == 0 else (3 if i % 5 == 0 else 0)

            self.possessions.append(
                PossessionEvent(
                    game_id="0022300001",
                    season="2023-24",
                    period=1,
                    possession_id=i + 1,
                    clock_seconds=clock,
                    off_team_id=self.team1,
                    def_team_id=self.team2,
                    off_players=off_p,
                    def_players=def_p,
                    off_mask=(1 << 5) - 1,
                    def_mask=(1 << 5) - 1,
                    pts=pts,
                    possession_result="TEST",
                )
            )
            clock = max(0.0, clock - 15.0)

    def test_stint_compression(self):
        stints = StintAggregator.compress_possessions(self.possessions)
        self.assertGreater(len(stints), 0)
        self.assertLess(len(stints), len(self.possessions))

        total_poss_in_stints = sum(s.possessions for s in stints)
        self.assertEqual(total_poss_in_stints, len(self.possessions))
        total_pts_in_stints = sum(s.points for s in stints)
        self.assertEqual(total_pts_in_stints, sum(p.pts for p in self.possessions))

    def test_rapm_sparse_solver_speed_and_invariants(self):
        stints = StintAggregator.compress_possessions(self.possessions)
        engine = RAPMEngine(lambda_reg=500.0)

        # Fit without priors
        result = engine.fit(stints)

        self.assertIsInstance(result, RAPMResult)
        # Verify solver timing converges in well under 1.5 seconds target
        self.assertLess(result.solve_time_sec, 1.5, f"Solve took {result.solve_time_sec}s, expected <= 1.5s")

        # Verify all active players received ORAPM, DRAPM, and RAPM
        for pid in result.orapm.keys():
            self.assertIn(pid, result.drapm)
            self.assertIn(pid, result.rapm)
            # Total RAPM = ORAPM + DRAPM
            self.assertAlmostEqual(
                result.rapm[pid],
                result.orapm[pid] + result.drapm[pid],
                places=2
            )

    def test_bayesian_prior_regularization(self):
        stints = StintAggregator.compress_possessions(self.possessions)
        engine = RAPMEngine(lambda_reg=1000.0)

        # Test player 1001 with strong positive offensive prior (+6.0)
        target_pid = self.team1_players[0]
        priors = {target_pid: (6.0, 1.5)}

        result_with_priors = engine.fit(stints, priors=priors)
        result_without_priors = engine.fit(stints, priors=None)

        # The prior must shift ORAPM higher towards +6.0
        self.assertGreater(
            result_with_priors.orapm[target_pid],
            result_without_priors.orapm[target_pid]
        )


if __name__ == "__main__":
    unittest.main()
