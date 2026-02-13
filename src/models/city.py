"""
City model for managing cities, production, and growth.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from enum import Enum

from src.utils.hex_utils import HexCoord, hex_range, hex_distance

if TYPE_CHECKING:
    from src.models.map import GameMap, Tile


class ProductionType(Enum):
    """Types of things a city can produce."""
    WARRIOR = 'warrior'
    SETTLER = 'settler'
    SCOUT = 'scout'
    ARCHER = 'archer'
    HORSEMAN = 'horseman'


@dataclass
class ProductionItem:
    """An item that can be produced."""
    type: ProductionType
    name: str
    cost: int
    description: str


# Production items available
PRODUCTION_ITEMS: Dict[ProductionType, ProductionItem] = {
    ProductionType.WARRIOR: ProductionItem(
        type=ProductionType.WARRIOR,
        name="Warrior",
        cost=25,
        description="Melee fighter. Strength 8."
    ),
    ProductionType.SCOUT: ProductionItem(
        type=ProductionType.SCOUT,
        name="Scout",
        cost=15,
        description="Fast explorer. Strength 5, 3 moves."
    ),
    ProductionType.ARCHER: ProductionItem(
        type=ProductionType.ARCHER,
        name="Archer",
        cost=35,
        description="Ranged attacker. Strength 6, range 2."
    ),
    ProductionType.HORSEMAN: ProductionItem(
        type=ProductionType.HORSEMAN,
        name="Horseman",
        cost=40,
        description="Fast cavalry. Strength 7, 4 moves."
    ),
    ProductionType.SETTLER: ProductionItem(
        type=ProductionType.SETTLER,
        name="Settler",
        cost=60,
        description="Founds new cities. Cannot attack."
    ),
}


@dataclass
class CityYields:
    """Resource yields for a city."""
    food: int = 0
    production: int = 0
    gold: int = 0
    science: int = 0

    def __add__(self, other: 'CityYields') -> 'CityYields':
        return CityYields(
            food=self.food + other.food,
            production=self.production + other.production,
            gold=self.gold + other.gold,
            science=self.science + other.science
        )

    def __iadd__(self, other: 'CityYields') -> 'CityYields':
        self.food += other.food
        self.production += other.production
        self.gold += other.gold
        self.science += other.science
        return self


# Terrain yields
TERRAIN_YIELDS: Dict[str, CityYields] = {
    'grassland': CityYields(food=2, production=0, gold=0, science=0),
    'plains': CityYields(food=1, production=1, gold=0, science=0),
    'desert': CityYields(food=0, production=0, gold=1, science=0),
    'hills': CityYields(food=0, production=2, gold=0, science=0),
    'mountains': CityYields(food=0, production=0, gold=0, science=0),
    'forest': CityYields(food=1, production=1, gold=0, science=0),
    'coast': CityYields(food=1, production=0, gold=1, science=0),
    'ocean': CityYields(food=1, production=0, gold=0, science=0),
}

# Growth thresholds by population
def get_growth_threshold(population: int) -> int:
    """Calculate food needed to grow to next population level."""
    return 10 + (population - 1) * 5  # 10, 15, 20, 25, ...


# Food consumed per population per turn
FOOD_CONSUMPTION_PER_POP = 2


@dataclass
class City:
    """A city on the map."""
    id: int
    name: str
    position: HexCoord
    owner_id: int = 0
    population: int = 1
    is_capital: bool = False

    # Resources
    stored_food: int = 0
    stored_production: int = 0

    # Production (defaults to Warrior so cities are never idle)
    current_production: Optional[ProductionType] = field(default_factory=lambda: ProductionType.WARRIOR)

    # Worked tiles (automatically selected)
    worked_tiles: Set[HexCoord] = field(default_factory=set)

    # Territory (tiles owned by this city)
    territory: Set[HexCoord] = field(default_factory=set)

    def __post_init__(self):
        """Initialize city territory."""
        if not self.territory:
            self.territory = self._calculate_initial_territory()
        if not self.worked_tiles:
            self.worked_tiles = {self.position}  # Always work the city center

    def _calculate_initial_territory(self) -> Set[HexCoord]:
        """Calculate initial territory (1-hex radius)."""
        return hex_range(self.position, 1)

    def get_workable_tiles(self) -> Set[HexCoord]:
        """Get all tiles that could be worked (within 3 hexes)."""
        return hex_range(self.position, 3)

    def get_max_worked_tiles(self) -> int:
        """Maximum tiles that can be worked (population + 1 for city center)."""
        return self.population + 1

    def calculate_yields(self, game_map: 'GameMap') -> CityYields:
        """Calculate total yields from all worked tiles."""
        # City center always provides a base yield
        total = CityYields(food=2, production=3, gold=1, science=0)

        for coord in self.worked_tiles:
            tile = game_map.get_tile(coord)
            if tile:
                terrain_yield = TERRAIN_YIELDS.get(tile.terrain.value, CityYields())
                total += terrain_yield

        return total

    def get_food_surplus(self, game_map: 'GameMap') -> int:
        """Calculate food surplus after consumption."""
        yields = self.calculate_yields(game_map)
        consumption = self.population * FOOD_CONSUMPTION_PER_POP
        return yields.food - consumption

    def auto_assign_tiles(self, game_map: 'GameMap', other_cities: List['City'] = None):
        """
        Automatically assign the best tiles to work.
        Prioritizes food for growth, then production.
        """
        other_cities = other_cities or []

        # Get tiles we could work (within 3 hexes, not worked by other cities)
        other_worked = set()
        for city in other_cities:
            if city.id != self.id:
                other_worked.update(city.worked_tiles)

        workable = self.get_workable_tiles()
        available = []

        for coord in workable:
            if coord in other_worked:
                continue
            tile = game_map.get_tile(coord)
            if tile and tile.is_passable:  # Can't work mountains/ocean
                available.append(coord)

        # Score tiles (prioritize food, then production, then gold)
        def tile_score(coord: HexCoord) -> tuple:
            tile = game_map.get_tile(coord)
            if not tile:
                return (0, 0, 0, 0)
            yields = TERRAIN_YIELDS.get(tile.terrain.value, CityYields())
            # Priority: food (for growth), production, gold, science
            # City center gets a bonus
            center_bonus = 10 if coord == self.position else 0
            return (center_bonus, yields.food, yields.production, yields.gold)

        # Sort by score descending
        available.sort(key=tile_score, reverse=True)

        # Assign the best tiles up to our limit
        max_tiles = self.get_max_worked_tiles()
        self.worked_tiles = set(available[:max_tiles])

        # Always include city center
        self.worked_tiles.add(self.position)

    def process_turn(self, game_map: 'GameMap') -> Dict:
        """
        Process end of turn for this city.
        Returns dict with events (growth, production complete, etc.)
        """
        events = {
            'grew': False,
            'starving': False,
            'production_complete': None,
        }

        yields = self.calculate_yields(game_map)

        # Food processing
        food_surplus = self.get_food_surplus(game_map)
        self.stored_food += food_surplus

        # Check for starvation
        if self.stored_food < 0:
            self.stored_food = 0
            if self.population > 1:
                self.population -= 1
                events['starving'] = True

        # Check for growth
        growth_threshold = get_growth_threshold(self.population)
        if self.stored_food >= growth_threshold:
            self.stored_food -= growth_threshold
            self.population += 1
            events['grew'] = True
            # Re-assign tiles after growth
            self.auto_assign_tiles(game_map)

        # Production processing
        if self.current_production:
            self.stored_production += yields.production
            item = PRODUCTION_ITEMS.get(self.current_production)
            if item and self.stored_production >= item.cost:
                self.stored_production -= item.cost
                events['production_complete'] = self.current_production
                # Keep building the same thing (auto-repeat)

        return events

    def set_production(self, production_type: ProductionType):
        """Set what the city is producing."""
        if production_type != self.current_production:
            self.current_production = production_type
            # Don't reset stored production - it carries over

    def get_production_turns_remaining(self) -> Optional[int]:
        """Get turns until current production completes."""
        if not self.current_production:
            return None
        item = PRODUCTION_ITEMS.get(self.current_production)
        if not item:
            return None
        remaining = item.cost - self.stored_production
        # Would need yields to calculate, return None for now
        return None

    def expand_territory(self):
        """Expand city territory by one ring (called on growth)."""
        current_radius = 1
        for coord in self.territory:
            dist = hex_distance(self.position, coord)
            current_radius = max(current_radius, dist)

        if current_radius < 3:  # Max territory radius
            new_territory = hex_range(self.position, current_radius + 1)
            self.territory.update(new_territory)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, City):
            return self.id == other.id
        return False
