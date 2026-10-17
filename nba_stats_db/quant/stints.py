"""
stints.py - Lineup Stint Compression from Possession Tables.

Compresses hundreds of thousands of possession events (~250k/season) into continuous
lineup stint intervals (~32k/season) where the 10 players on court remain unchanged.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence
import polars as pl

from ..possession.state_machine import PossessionEvent


@dataclass
class Stint:
    """Represents a continuous stint of possessions with 10 fixed players on court."""
    game_id: str
    period: int
    off_team_id: int
    def_team_id: int
    off_players: List[int]
    def_players: List[int]
    possessions: int
    points: int
    duration_seconds: float = 0.0

    @property
    def points_per_100(self) -> float:
        if self.possessions == 0:
            return 0.0
        return (self.points / self.possessions) * 100.0


class StintAggregator:
    """Aggregates raw possession records into compressed stint intervals."""

    @staticmethod
    def compress_possessions(possessions: Sequence[PossessionEvent]) -> List[Stint]:
        """
        Compresses sequential possession events into stints.
        A new stint begins whenever substitutions occur or the period ends.
        """
        if not possessions:
            return []

        stints: List[Stint] = []
        cur_game = possessions[0].game_id
        cur_period = possessions[0].period
        cur_off_team = possessions[0].off_team_id
        cur_def_team = possessions[0].def_team_id
        cur_off = tuple(sorted(possessions[0].off_players))
        cur_def = tuple(sorted(possessions[0].def_players))
        cur_poss_cnt = 0
        cur_pts = 0
        start_clock = possessions[0].clock_seconds
        last_clock = possessions[0].clock_seconds

        for p in possessions:
            off_tuple = tuple(sorted(p.off_players))
            def_tuple = tuple(sorted(p.def_players))

            # Check if stint boundary reached
            is_same_stint = (
                p.game_id == cur_game
                and p.period == cur_period
                and p.off_team_id == cur_off_team
                and p.def_team_id == cur_def_team
                and off_tuple == cur_off
                and def_tuple == cur_def
            )

            if is_same_stint:
                cur_poss_cnt += 1
                cur_pts += p.pts
                last_clock = p.clock_seconds
            else:
                # Flush previous stint
                duration = abs(start_clock - last_clock)
                stints.append(
                    Stint(
                        game_id=cur_game,
                        period=cur_period,
                        off_team_id=cur_off_team,
                        def_team_id=cur_def_team,
                        off_players=list(cur_off),
                        def_players=list(cur_def),
                        possessions=cur_poss_cnt,
                        points=cur_pts,
                        duration_seconds=round(duration, 2),
                    )
                )

                # Initialize next stint
                cur_game = p.game_id
                cur_period = p.period
                cur_off_team = p.off_team_id
                cur_def_team = p.def_team_id
                cur_off = off_tuple
                cur_def = def_tuple
                cur_poss_cnt = 1
                cur_pts = p.pts
                start_clock = p.clock_seconds
                last_clock = p.clock_seconds

        # Flush final stint
        if cur_poss_cnt > 0:
            duration = abs(start_clock - last_clock)
            stints.append(
                Stint(
                    game_id=cur_game,
                    period=cur_period,
                    off_team_id=cur_off_team,
                    def_team_id=cur_def_team,
                    off_players=list(cur_off),
                    def_players=list(cur_def),
                    possessions=cur_poss_cnt,
                    points=cur_pts,
                    duration_seconds=round(duration, 2),
                )
            )

        return stints

    @staticmethod
    def compress_dataframe(df: pl.DataFrame) -> List[Stint]:
        """Compresses a Polars DataFrame of possessions into Stints."""
        if len(df) == 0:
            return []

        rows = df.to_dicts()
        # Adapt rows to possession events if necessary
        events = [
            PossessionEvent(
                game_id=r["game_id"],
                season=r["season"],
                period=r["period"],
                possession_id=r["possession_id"],
                clock_seconds=r["clock_seconds"],
                off_team_id=r["off_team_id"],
                def_team_id=r["def_team_id"],
                off_players=r["off_players"],
                def_players=r["def_players"],
                off_mask=r["off_mask"],
                def_mask=r["def_mask"],
                pts=r["pts"],
                possession_result=r["possession_result"],
            )
            for r in rows
        ]
        return StintAggregator.compress_possessions(events)
