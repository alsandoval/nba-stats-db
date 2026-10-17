"""
test_duckdb_wowy_bench.py - Benchmarks DuckDB Vectorized With-Or-Without-You (WOWY)
bitmask query performance to guarantee sub-15ms execution over possession data.
"""

import json
import os
import time
import unittest
import polars as pl

from nba_stats_db.possession.bitmask import TeamSeasonBitmaskIndexer
from nba_stats_db.possession.state_machine import PossessionStateMachine
from nba_stats_db.possession.parquet_store import ParquetPossessionStore
from nba_stats_db.possession.olap import DuckDBPossessionEngine


class TestDuckDBWOWYBenchmark(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = "data/gold/test_possessions"
        cls.season = "2023-24"
        cls.store = ParquetPossessionStore(base_dir=cls.test_dir)
        cls.indexer = TeamSeasonBitmaskIndexer()
        cls.sm = PossessionStateMachine(indexer=cls.indexer)

        # Ingest sample game
        pbp_path = "data/endpoints/LivePlayByPlay.json"
        box_path = "data/endpoints/LiveBoxScore.json"
        if not (os.path.exists(pbp_path) and os.path.exists(box_path)):
            raise unittest.SkipTest("Sample files missing")

        with open(pbp_path, "r") as f:
            pbp_data = json.load(f)
        with open(box_path, "r") as f:
            box_data = json.load(f)

        g = box_data["game"]
        cls.home_id = g["homeTeam"]["teamId"]
        cls.away_id = g["awayTeam"]["teamId"]
        home_starters = [p["personId"] for p in g["homeTeam"]["players"] if p.get("starter") in ("1", 1)]
        away_starters = [p["personId"] for p in g["awayTeam"]["players"] if p.get("starter") in ("1", 1)]

        actions = pbp_data["game"]["actions"]
        game_id = pbp_data["game"]["gameId"]

        possessions = cls.sm.parse_game_possessions(
            game_id=game_id,
            season=cls.season,
            home_team_id=cls.home_id,
            away_team_id=cls.away_id,
            actions=actions,
            box_starters={cls.home_id: home_starters, cls.away_id: away_starters},
        )

        # Convert to polars df and replicate to scale (~50,000 to 100,000 possessions)
        base_df = cls.store.possessions_to_df(possessions)
        # Replicate 500x to simulate 75,000+ possession records
        scaled_df = pl.concat([base_df] * 500)
        s_dir = cls.store._season_dir(cls.season)
        scaled_df.write_parquet(s_dir / "bench_possessions.parquet", compression="zstd")

        cls.engine = DuckDBPossessionEngine(parquet_dir=cls.test_dir)
        cls.home_starters = home_starters

    def test_sub_15ms_wowy_execution(self):
        # Query: Home team with Starter 0 and Starter 1 ON, and Starter 2 OFF
        p_on = [self.home_starters[0], self.home_starters[1]]
        p_off = [self.home_starters[2]]

        # Warm-up run
        self.engine.query_wowy(
            season=self.season,
            team_id=self.home_id,
            on_player_ids=p_on,
            off_player_ids=p_off,
            indexer=self.indexer,
        )

        # Benchmark 10 consecutive runs
        timings = []
        for _ in range(10):
            res = self.engine.query_wowy(
                season=self.season,
                team_id=self.home_id,
                on_player_ids=p_on,
                off_player_ids=p_off,
                indexer=self.indexer,
            )
            timings.append(res["query_time_ms"])

        avg_ms = sum(timings) / len(timings)
        min_ms = min(timings)
        print(f"\n[BENCHMARK] WOWY Query over ~75,000 possessions: min={min_ms:.2f}ms, avg={avg_ms:.2f}ms")
        self.assertLess(avg_ms, 15.0, f"Average query time {avg_ms:.2f}ms exceeded 15.0ms target")

    @classmethod
    def tearDownClass(cls):
        import shutil
        if os.path.exists(cls.test_dir):
            try:
                shutil.rmtree(cls.test_dir)
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
