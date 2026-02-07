"""
Unit model for game units (warriors, settlers, etc.)
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Set, TYPE_CHECKING
from enum import Enum
import heapq

from src.utils.hex_utils import HexCoord, hex_neighbors, hex_distance

if TYPE_CHECKING:
    from src.models.map import GameMap, Tile

from config import DEFAULT_MOVEMENT_POINTS


class UnitType(Enum):
    """Types of units in the game."""
    WARRIOR = 'warrior'
    SETTLER = 'settler'  # For Phase 2
    SCOUT = 'scout'      # Future


@dataclass
class UnitStats:
    """Base stats for a unit type."""
    name: str
    movement_points: int
    strength: int
    icon: str  # Character to display
    can_found_city: bool = False  # Whether this unit can found cities


# Unit type definitions
UNIT_STATS: Dict[UnitType, UnitStats] = {
    UnitType.WARRIOR: UnitStats(
        name="Warrior",
        movement_points=2,
        strength=8,
        icon="W"
    ),
    UnitType.SETTLER: UnitStats(
        name="Settler",
        movement_points=2,
        strength=0,
        icon="S",
        can_found_city=True
    ),
    UnitType.SCOUT: UnitStats(
        name="Scout",
        movement_points=3,
        strength=5,
        icon="!"
    ),
}


@dataclass
class Unit:
    """A single unit on the map."""
    id: int
    unit_type: UnitType
    position: HexCoord
    owner_id: int = 0  # Player ID (0 = player 1)
    movement_remaining: float = field(default=0.0)
    health: int = 100
    is_selected: bool = False

    def __post_init__(self):
        """Initialize movement points on creation."""
        if self.movement_remaining == 0.0:
            self.movement_remaining = self.stats.movement_points

    @property
    def stats(self) -> UnitStats:
        """Get the stats for this unit type."""
        return UNIT_STATS[self.unit_type]

    @property
    def name(self) -> str:
        return self.stats.name

    @property
    def max_movement(self) -> int:
        return self.stats.movement_points

    @property
    def strength(self) -> int:
        return self.stats.strength

    @property
    def icon(self) -> str:
        return self.stats.icon

    @property
    def can_move(self) -> bool:
        """Check if unit has any movement remaining."""
        return self.movement_remaining > 0

    @property
    def can_found_city(self) -> bool:
        """Check if this unit can found a city."""
        return self.stats.can_found_city

    def start_turn(self):
        """Reset unit state at the start of a turn."""
        self.movement_remaining = self.max_movement

    def end_turn(self):
        """Handle end of turn for this unit."""
        pass  # Future: healing, fortification bonuses, etc.

    def get_movement_range(self, game_map: 'GameMap') -> Dict[HexCoord, float]:
        """
        Calculate all tiles this unit can move to with current movement points.
        Returns dict mapping coordinates to the movement cost to reach them.
        Uses Dijkstra's algorithm for pathfinding.
        """
        if not self.can_move:
            return {}

        # Priority queue: (cost, coord)
        frontier = [(0.0, self.position)]
        costs: Dict[HexCoord, float] = {self.position: 0.0}

        while frontier:
            current_cost, current = heapq.heappop(frontier)

            if current_cost > costs.get(current, float('inf')):
                continue

            # Check all neighbors
            for neighbor_tile in game_map.get_neighbors(current):
                if not neighbor_tile.is_passable:
                    continue

                move_cost = neighbor_tile.movement_cost
                new_cost = current_cost + move_cost

                # Only include if we can reach it with remaining movement
                if new_cost <= self.movement_remaining:
                    if neighbor_tile.coord not in costs or new_cost < costs[neighbor_tile.coord]:
                        costs[neighbor_tile.coord] = new_cost
                        heapq.heappush(frontier, (new_cost, neighbor_tile.coord))

        # Remove starting position from results
        if self.position in costs:
            del costs[self.position]

        return costs

    def get_path_to(self, target: HexCoord, game_map: 'GameMap') -> Optional[List[HexCoord]]:
        """
        Find the shortest path to the target tile.
        Returns None if no path exists or target is out of range.
        """
        movement_range = self.get_movement_range(game_map)

        if target not in movement_range:
            return None

        # Reconstruct path using A* for efficiency
        # (though our map is small enough that it doesn't matter much)
        return self._find_path(self.position, target, game_map)

    def _find_path(self, start: HexCoord, end: HexCoord, game_map: 'GameMap') -> Optional[List[HexCoord]]:
        """A* pathfinding from start to end."""
        frontier = [(0, start)]
        came_from: Dict[HexCoord, Optional[HexCoord]] = {start: None}
        cost_so_far: Dict[HexCoord, float] = {start: 0}

        while frontier:
            _, current = heapq.heappop(frontier)

            if current == end:
                break

            for neighbor_tile in game_map.get_neighbors(current):
                if not neighbor_tile.is_passable:
                    continue

                new_cost = cost_so_far[current] + neighbor_tile.movement_cost

                if neighbor_tile.coord not in cost_so_far or new_cost < cost_so_far[neighbor_tile.coord]:
                    cost_so_far[neighbor_tile.coord] = new_cost
                    priority = new_cost + hex_distance(neighbor_tile.coord, end)
                    heapq.heappush(frontier, (priority, neighbor_tile.coord))
                    came_from[neighbor_tile.coord] = current

        # Reconstruct path
        if end not in came_from:
            return None

        path = []
        current = end
        while current is not None:
            path.append(current)
            current = came_from[current]

        path.reverse()
        return path[1:]  # Exclude starting position

    def move_to(self, target: HexCoord, game_map: 'GameMap') -> bool:
        """
        Move unit to target position.
        Returns True if move was successful.
        """
        movement_range = self.get_movement_range(game_map)

        if target not in movement_range:
            return False

        cost = movement_range[target]
        self.movement_remaining -= cost
        self.position = target
        return True

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Unit):
            return self.id == other.id
        return False
