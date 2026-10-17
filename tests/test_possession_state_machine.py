"""
test_possession_state_machine.py - Comprehensive Unit & Integration Tests for the
Possession State Machine, Bitmask Indexer, and Invariant Assertions.
"""

import json
import os
import unittest
from nba_stats_db.possession.bitmask import TeamSeasonBitmaskIndexer, popcount
from nba_stats_db.possession.state_machine import (
    LineupState,
    PossessionStateMachine,
    PossessionEvent,
    parse_clock_to_seconds,
)


class TestBitmaskIndexer(unittest.TestCase):
    def setUp(self):
        self.indexer = TeamSeasonBitmaskIndexer()
        self.team_id = 1610612738  # BOS
        self.season = "2023-24"
        self.players = [1628369, 1627759, 201142, 203935, 1628401]  # Tatum, Brown, etc.

    def test_popcount_five_invariant(self):
        mask = self.indexer.create_lineup_mask(self.team_id, self.season, self.players)
        self.assertEqual(popcount(mask), 5)
        self.assertIsInstance(mask, int)

    def test_decode_lineup_mask(self):
        mask = self.indexer.create_lineup_mask(self.team_id, self.season, self.players)
        decoded = self.indexer.decode_lineup_mask(self.team_id, self.season, mask)
        self.assertEqual(sorted(decoded), sorted(self.players))

    def test_invalid_lineup_raises(self):
        # 4 players instead of 5
        with self.assertRaises(ValueError):
            self.indexer.create_lineup_mask(self.team_id, self.season, self.players[:4])

        # 6 players instead of 5
        with self.assertRaises(ValueError):
            self.indexer.create_lineup_mask(self.team_id, self.season, self.players + [999999])

    def test_wowy_algebra(self):
        p_on = [self.players[0], self.players[1]]   # Must be ON
        p_off = [self.players[2]]                   # Must be OFF
        m_on, m_off = self.indexer.create_wowy_masks(self.team_id, self.season, p_on, p_off)

        # Baseline lineup has p_on, but also has p_off -> should NOT match
        mask1 = self.indexer.create_lineup_mask(self.team_id, self.season, self.players)
        self.assertFalse(self.indexer.matches_wowy(mask1, m_on, m_off))

        # Substitute p_off with a new player 99999
        new_lineup = [self.players[0], self.players[1], self.players[3], self.players[4], 99999]
        mask2 = self.indexer.create_lineup_mask(self.team_id, self.season, new_lineup)
        self.assertTrue(self.indexer.matches_wowy(mask2, m_on, m_off))


class TestPossessionStateMachine(unittest.TestCase):
    def setUp(self):
        self.sm = PossessionStateMachine()
        self.pbp_path = "data/endpoints/LivePlayByPlay.json"
        self.box_path = "data/endpoints/LiveBoxScore.json"

    def test_clock_parsing(self):
        self.assertAlmostEqual(parse_clock_to_seconds("PT12M00.00S"), 720.0)
        self.assertAlmostEqual(parse_clock_to_seconds("PT06M43.00S"), 403.0)
        self.assertAlmostEqual(parse_clock_to_seconds("06:43"), 403.0)
        self.assertAlmostEqual(parse_clock_to_seconds(300), 300.0)

    def test_forward_scanner_quarter_starting_fives(self):
        home_team = 1610612754  # IND
        away_team = 1610612739  # CLE
        # Simulate actions where players act before being subbed in
        mock_actions = [
            # Event 1: Shot by Player 101 (home)
            {"actionType": "2pt", "subType": "made", "period": 2, "teamId": home_team, "personId": 101, "clock": "PT11M50.00S"},
            # Event 2: Foul by Player 102 (home)
            {"actionType": "foul", "period": 2, "teamId": home_team, "personId": 102, "clock": "PT11M30.00S"},
            # Event 3: Shot by Player 201 (away)
            {"actionType": "3pt", "subType": "made", "period": 2, "teamId": away_team, "personId": 201, "clock": "PT11M10.00S"},
            # Event 4: Sub for home: Player 103 comes OUT, Player 106 comes IN
            {"actionType": "substitution", "subType": "out", "period": 2, "teamId": home_team, "personId": 103, "clock": "PT10M00.00S"},
            {"actionType": "substitution", "subType": "in", "period": 2, "teamId": home_team, "personId": 106, "clock": "PT10M00.00S"},
            # Event 5: Rebound by Player 104 (home)
            {"actionType": "rebound", "period": 2, "teamId": home_team, "personId": 104, "clock": "PT09M50.00S"},
            # Event 6: Turnover by Player 105 (home)
            {"actionType": "turnover", "period": 2, "teamId": home_team, "personId": 105, "clock": "PT09M30.00S"},
        ]

        home_starters, away_starters = self.sm.resolve_period_starters(
            home_team_id=home_team,
            away_team_id=away_team,
            season="2023-24",
            period=2,
            actions=mock_actions,
        )

        # Player 101, 102, 103 (subbed out before subbed in), 104, 105 must be the 5 home starters!
        self.assertEqual(len(home_starters), 5)
        self.assertEqual(len(away_starters), 5)
        for expected_pid in [101, 102, 103, 104, 105]:
            self.assertIn(expected_pid, home_starters)
        # Player 106 was subbed IN, so must NOT be a starter
        self.assertNotIn(106, home_starters)

    def test_real_game_parsing_with_invariants(self):
        if not (os.path.exists(self.pbp_path) and os.path.exists(self.box_path)):
            self.skipTest("Sample endpoint files not present")

        with open(self.pbp_path, "r") as f:
            pbp_data = json.load(f)
        with open(self.box_path, "r") as f:
            box_data = json.load(f)

        g = box_data["game"]
        home_id = g["homeTeam"]["teamId"]
        away_id = g["awayTeam"]["teamId"]
        home_starters = [p["personId"] for p in g["homeTeam"]["players"] if p.get("starter") in ("1", 1)]
        away_starters = [p["personId"] for p in g["awayTeam"]["players"] if p.get("starter") in ("1", 1)]

        actions = pbp_data["game"]["actions"]
        game_id = pbp_data["game"]["gameId"]

        possessions = self.sm.parse_game_possessions(
            game_id=game_id,
            season="2023-24",
            home_team_id=home_id,
            away_team_id=away_id,
            actions=actions,
            box_starters={home_id: home_starters, away_id: away_starters},
        )

        self.assertGreater(len(possessions), 50, "A full game must produce over 50 possessions")

        for poss in possessions:
            # Verify popcount == 5 invariant on every single possession
            self.assertEqual(popcount(poss.off_mask), 5)
            self.assertEqual(popcount(poss.def_mask), 5)
            self.assertEqual(len(poss.off_players), 5)
            self.assertEqual(len(poss.def_players), 5)
            # Verify off_team != def_team
            self.assertNotEqual(poss.off_team_id, poss.def_team_id)
            # Points scored in possession must be non-negative and realistic
            self.assertIn(poss.pts, [0, 1, 2, 3, 4])


if __name__ == "__main__":
    unittest.main()
