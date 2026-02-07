"""
Unit model for game units (warriors, settlers, scouts, archers, horsemen).
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List, Set, TYPE_CHECKING
from enum import Enum
import heapq
import random

from src.utils.hex_utils import HexCoord, hex_neighbors, hex_distance

if TYPE_CHECKING:
    from src.models.map import GameMap, Tile

from config import DEFAULT_MOVEMENT_POINTS, TERRAIN_DEFENSE_BONUS, COMBAT_RANDOMNESS


class UnitType(Enum):
    """Types of units in the game."""
    WARRIOR = 'warrior'
    SETTLER = 'settler'
    SCOUT = 'scout'
    ARCHER = 'archer'
    HORSEMAN = 'horseman'


@dataclass
class UnitStats:
    """Base stats for a unit type."""
    name: str
    movement_points: int
    strength: int
    icon: str
    can_found_city: bool = False
    attack_range: int = 1  # 1 = melee, 2+ = ranged


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
    UnitType.ARCHER: UnitStats(
        name="Archer",
        movement_points=2,
        strength=6,
        icon="A",
        attack_range=2
    ),
    UnitType.HORSEMAN: UnitStats(
        name="Horseman",
        movement_points=4,
        strength=7,
        icon="H"
    ),
}


@dataclass
class Unit:
    """A single unit on the map."""
    id: int
    unit_type: UnitType
    position: HexCoord
    owner_id: int = 0
    movement_remaining: float = field(default=0.0)
    health: int = 100
    is_selected: bool = False

    def __post_init__(self):
        """Initialize movement points on creation."""
        if self.movement_remaining == 0.0:
            self.movement_remaining = self.stats.movement_points

    @property
    def stats(self) -> UnitStats:
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
    def attack_range(self) -> int:
        return self.stats.attack_range

    @property
    def can_move(self) -> bool:
        return self.movement_remaining > 0

    @property
    def can_found_city(self) -> bool:
        return self.stats.can_found_city

    @property
    def is_alive(self) -> bool:
        return self.health > 0

    def start_turn(self):
        """Reset unit state at the start of a turn."""
        self.movement_remaining = self.max_movement
        # Heal 10 HP per turn if not at full health
        if self.health < 100:
            self.health = min(100, self.health + 10)

    def end_turn(self):
        """Handle end of turn for this unit."""
        pass

    def attack(self, defender: 'Unit', game_map: 'GameMap') -> dict:
        """
        Attack another unit. Returns combat result dict.
        """
        if self.strength <= 0:
            return {'damage': 0, 'killed': False}

        # Base damage
        rand_factor = 1.0 + random.uniform(-COMBAT_RANDOMNESS, COMBAT_RANDOMNESS)
        base_damage = self.strength * rand_factor

        # Defender terrain bonus
        defender_tile = game_map.get_tile(defender.position)
        defense_bonus = 0.0
        if defender_tile:
            defense_bonus = TERRAIN_DEFENSE_BONUS.get(defender_tile.terrain.value, 0.0)

        # Health modifier (weaker units do less damage)
        attacker_health_mod = self.health / 100.0
        defender_health_mod = defender.health / 100.0

        # Calculate damage
        effective_defense = defender.strength * (1 + defense_bonus) * defender_health_mod * 0.5
        damage = max(1, int(base_damage * attacker_health_mod - effective_defense))

        # Apply damage
        defender.health -= damage
        killed = defender.health <= 0

        # Attacker takes counter-damage (reduced) for melee attacks
        if self.attack_range <= 1 and defender.strength > 0 and not killed:
            counter_rand = 1.0 + random.uniform(-COMBAT_RANDOMNESS, COMBAT_RANDOMNESS)
            counter_damage = max(1, int(defender.strength * counter_rand * defender_health_mod * 0.3))
            self.health -= counter_damage

        # Use all remaining movement
        self.movement_remaining = 0

        return {
            'damage': damage,
            'killed': killed,
            'attacker_alive': self.health > 0,
        }

    def can_attack_at(self, target_coord: HexCoord) -> bool:
        """Check if this unit can attack a target at the given coordinate."""
        if self.strength <= 0 or not self.can_move:
            return False
        dist = hex_distance(self.position, target_coord)
        return dist <= self.attack_range

    def get_movement_range(self, game_map: 'GameMap') -> Dict[HexCoord, float]:
        """
        Calculate all tiles this unit can move to with current movement points.
        Uses Dijkstra's algorithm.
        """
        if not self.can_move:
            return {}

        frontier = [(0.0, self.position)]
        costs: Dict[HexCoord, float] = {self.position: 0.0}

        while frontier:
            current_cost, current = heapq.heappop(frontier)

            if current_cost > costs.get(current, float('inf')):
                continue

            for neighbor_tile in game_map.get_neighbors(current):
                if not neighbor_tile.is_passable:
                    continue

                move_cost = neighbor_tile.movement_cost
                new_cost = current_cost + move_cost

                if new_cost <= self.movement_remaining:
                    if neighbor_tile.coord not in costs or new_cost < costs[neighbor_tile.coord]:
                        costs[neighbor_tile.coord] = new_cost
                        heapq.heappush(frontier, (new_cost, neighbor_tile.coord))

        if self.position in costs:
            del costs[self.position]

        return costs

    def get_path_to(self, target: HexCoord, game_map: 'GameMap') -> Optional[List[HexCoord]]:
        """Find shortest path to target."""
        movement_range = self.get_movement_range(game_map)
        if target not in movement_range:
            return None
        return self._find_path(self.position, target, game_map)

    def _find_path(self, start: HexCoord, end: HexCoord, game_map: 'GameMap') -> Optional[List[HexCoord]]:
        """A* pathfinding."""
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

        if end not in came_from:
            return None

        path = []
        current = end
        while current is not None:
            path.append(current)
            current = came_from[current]

        path.reverse()
        return path[1:]

    def move_to(self, target: HexCoord, game_map: 'GameMap') -> bool:
        """Move unit to target position."""
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
