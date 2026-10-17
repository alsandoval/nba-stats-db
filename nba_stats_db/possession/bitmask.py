"""
bitmask.py - 64-bit Team-Season Bitmask Indexer and WOWY (With-Or-Without-You) Algebra.

Enables vectorized sub-15ms lineup filtering over hundreds of thousands of possessions:
    MATCH = (off_mask & M_on == M_on) AND (off_mask & M_off == 0)
"""

import json
import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

logger = logging.getLogger(__name__)


def popcount(x: int) -> int:
    """Calculates number of set bits (Hamming weight) of an integer."""
    return bin(x).count("1")


class TeamSeasonBitmaskIndexer:
    """
    Manages deterministic 64-bit integer bitmasks for NBA lineups per team-season.
    
    Each NBA team per season carries at most ~18-22 unique players.
    Using a 64-bit unsigned integer (UINT64), each player maps to bit index k in [0, 63].
    A 5-man lineup mask always satisfies popcount(mask) == 5.
    """

    def __init__(self, registry_file: Optional[str] = None):
        # Key: f"{team_id}:{season}" -> {player_id: bit_index}
        self.team_season_registry: Dict[str, Dict[int, int]] = {}
        # Key: f"{team_id}:{season}" -> {bit_index: player_id}
        self.reverse_registry: Dict[str, Dict[int, int]] = {}
        self.registry_file = registry_file
        if registry_file:
            self.load_registry(registry_file)

    def _key(self, team_id: int, season: str) -> str:
        return f"{team_id}:{season}"

    def register_player(self, team_id: int, season: str, player_id: int) -> int:
        """
        Registers a player to a team-season roster and returns their bit index (0-63).
        If already registered, returns the existing bit index.
        """
        key = self._key(team_id, season)
        if key not in self.team_season_registry:
            self.team_season_registry[key] = {}
            self.reverse_registry[key] = {}

        player_map = self.team_season_registry[key]
        if player_id in player_map:
            return player_map[player_id]

        bit_index = len(player_map)
        if bit_index >= 64:
            raise OverflowError(
                f"Team {team_id} for season {season} exceeded 64 players (max UINT64 capacity)."
            )

        player_map[player_id] = bit_index
        self.reverse_registry[key][bit_index] = player_id
        return bit_index

    def register_roster(self, team_id: int, season: str, player_ids: Sequence[int]) -> None:
        """Registers a list of player IDs for a team-season."""
        for pid in sorted(player_ids):
            self.register_player(team_id, season, pid)

    def get_bit_index(self, team_id: int, season: str, player_id: int) -> int:
        """Returns the bit index for a player, registering them if absent."""
        return self.register_player(team_id, season, player_id)

    def create_lineup_mask(
        self, team_id: int, season: str, player_ids: Sequence[int], enforce_five: bool = True
    ) -> int:
        """
        Converts an array of 5 player IDs into a 64-bit UINT64 bitmask.
        Enforces invariant: popcount(mask) == 5 if enforce_five=True.
        """
        unique_ids = set(player_ids)
        if enforce_five and len(unique_ids) != 5:
            raise ValueError(
                f"Lineup for team {team_id} must have exactly 5 distinct players. Got {len(unique_ids)}: {player_ids}"
            )

        mask = 0
        for pid in unique_ids:
            bit_idx = self.get_bit_index(team_id, season, pid)
            mask |= 1 << bit_idx

        if enforce_five:
            assert (
                popcount(mask) == 5
            ), f"Invariant violation: popcount(mask) must be 5, got {popcount(mask)}"

        return mask

    def decode_lineup_mask(self, team_id: int, season: str, mask: int) -> List[int]:
        """Decodes a 64-bit mask back to a sorted list of player IDs."""
        key = self._key(team_id, season)
        if key not in self.reverse_registry:
            return []

        rev_map = self.reverse_registry[key]
        player_ids = []
        for bit_idx in range(64):
            if (mask >> bit_idx) & 1:
                if bit_idx in rev_map:
                    player_ids.append(rev_map[bit_idx])
                else:
                    logger.warning("Unmapped bit index %d for %s", bit_idx, key)

        return sorted(player_ids)

    def create_wowy_masks(
        self,
        team_id: int,
        season: str,
        on_player_ids: Sequence[int],
        off_player_ids: Sequence[int],
    ) -> Tuple[int, int]:
        """
        Creates (M_on, M_off) bitmasks for With-Or-Without-You (WOWY) filtering.
        
        Filter rule:
            (lineup_mask & M_on == M_on) and (lineup_mask & M_off == 0)
        """
        m_on = 0
        for pid in on_player_ids:
            bit_idx = self.get_bit_index(team_id, season, pid)
            m_on |= 1 << bit_idx

        m_off = 0
        for pid in off_player_ids:
            bit_idx = self.get_bit_index(team_id, season, pid)
            m_off |= 1 << bit_idx

        # Invariant: a player cannot be simultaneously ON and OFF
        if (m_on & m_off) != 0:
            raise ValueError("Overlapping players found in ON and OFF requirements")

        return m_on, m_off

    def matches_wowy(self, lineup_mask: int, m_on: int, m_off: int) -> bool:
        """Evaluates whether a lineup mask satisfies WOWY constraints."""
        return ((lineup_mask & m_on) == m_on) and ((lineup_mask & m_off) == 0)

    def export_registry(self) -> Dict[str, Any]:
        """Exports the registry to a JSON-serializable dictionary."""
        return {
            "team_season_registry": {
                k: {str(pid): bit for pid, bit in v.items()}
                for k, v in self.team_season_registry.items()
            }
        }

    def save_registry(self, filepath: str) -> None:
        """Saves player bit mappings to a JSON file."""
        with open(filepath, "w") as f:
            json.dump(self.export_registry(), f, indent=2)

    def load_registry(self, filepath: str) -> None:
        """Loads player bit mappings from a JSON file."""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            reg = data.get("team_season_registry", {})
            for k, player_dict in reg.items():
                self.team_season_registry[k] = {int(p): int(b) for p, b in player_dict.items()}
                self.reverse_registry[k] = {int(b): int(p) for p, b in player_dict.items()}
        except Exception as e:
            logger.warning("Could not load bitmask registry from %s: %s", filepath, e)
