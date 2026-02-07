"""
Game state model - holds all game data and logic.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from src.models.map import GameMap, Tile
from src.models.unit import Unit, UnitType
from src.models.city import City, ProductionType, PRODUCTION_ITEMS
from src.utils.hex_utils import HexCoord, hex_distance, hex_range


class GamePhase(Enum):
    """Current phase of the game."""
    SETUP = 'setup'
    PLAYING = 'playing'
    NAMING_CITY = 'naming_city'  # Waiting for player to name a city
    GAME_OVER = 'game_over'


@dataclass
class Civilization:
    """A civilization definition."""
    id: str
    name: str
    adjective: str
    leader: str
    primary_color: Tuple[int, int, int]
    secondary_color: Tuple[int, int, int]
    city_names: List[str]

    @staticmethod
    def from_dict(civ_id: str, data: dict) -> 'Civilization':
        return Civilization(
            id=civ_id,
            name=data['name'],
            adjective=data['adjective'],
            leader=data['leader'],
            primary_color=tuple(data['colors']['primary']),
            secondary_color=tuple(data['colors']['secondary']),
            city_names=data['city_names']
        )


@dataclass
class Player:
    """Player information."""
    id: int
    name: str
    color: tuple  # RGB color
    is_human: bool = True
    civilization: Optional[Civilization] = None

    # Resources
    gold: int = 0
    science: int = 0
    culture: int = 0

    # City naming
    cities_founded: int = 0

    def get_next_city_name(self) -> str:
        """Get the next auto-generated city name."""
        if self.civilization and self.cities_founded < len(self.civilization.city_names):
            return self.civilization.city_names[self.cities_founded]
        return f"City {self.cities_founded + 1}"


def load_civilizations() -> Dict[str, Civilization]:
    """Load civilization data from JSON file."""
    try:
        # Get path relative to this file
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        json_path = os.path.join(base_path, 'assets', 'data', 'civilizations.json')

        with open(json_path, 'r') as f:
            data = json.load(f)

        civs = {}
        for civ_id, civ_data in data['civilizations'].items():
            civs[civ_id] = Civilization.from_dict(civ_id, civ_data)
        return civs
    except Exception as e:
        print(f"Warning: Could not load civilizations: {e}")
        return {}


# Global civilizations cache
CIVILIZATIONS: Dict[str, Civilization] = {}


@dataclass
class GameState:
    """
    Central game state container.
    Manages all game data and provides methods for game logic.
    """
    game_map: GameMap = field(default_factory=GameMap)
    players: List[Player] = field(default_factory=list)
    units: Dict[int, Unit] = field(default_factory=dict)
    cities: Dict[int, City] = field(default_factory=dict)
    turn_number: int = 1
    current_player_index: int = 0
    phase: GamePhase = GamePhase.SETUP

    # Selection state
    selected_unit_id: Optional[int] = None
    selected_city_id: Optional[int] = None
    hovered_hex: Optional[HexCoord] = None

    # City founding state
    pending_city_location: Optional[HexCoord] = None
    pending_city_settler_id: Optional[int] = None

    # ID counters
    _next_unit_id: int = 0
    _next_city_id: int = 0

    def __post_init__(self):
        """Initialize the game state."""
        global CIVILIZATIONS
        if not CIVILIZATIONS:
            CIVILIZATIONS = load_civilizations()

        if not self.players:
            # Create default player with Rome
            civ = CIVILIZATIONS.get('rome')
            self.players.append(Player(
                id=0,
                name="Player 1",
                color=civ.primary_color if civ else (50, 150, 255),
                civilization=civ
            ))

    def initialize_game(self, map_seed: Optional[int] = None, civ_id: str = 'rome'):
        """Set up a new game."""
        global CIVILIZATIONS
        if not CIVILIZATIONS:
            CIVILIZATIONS = load_civilizations()

        # Clear existing state
        self.units.clear()
        self.cities.clear()
        self._next_unit_id = 0
        self._next_city_id = 0

        # Set player civilization
        civ = CIVILIZATIONS.get(civ_id)
        if civ and self.players:
            self.players[0].civilization = civ
            self.players[0].color = civ.primary_color
            self.players[0].cities_founded = 0

        # Generate map
        self.game_map = GameMap(seed=map_seed)

        # Create starting settler for player (instead of warrior)
        spawn = self.game_map.find_spawn_location()
        if spawn:
            self.create_unit(UnitType.SETTLER, spawn, owner_id=0)

        self.phase = GamePhase.PLAYING
        self.turn_number = 1

    def create_unit(self, unit_type: UnitType, position: HexCoord, owner_id: int = 0) -> Unit:
        """Create a new unit and add it to the game."""
        unit = Unit(
            id=self._next_unit_id,
            unit_type=unit_type,
            position=position,
            owner_id=owner_id
        )
        self.units[unit.id] = unit
        self._next_unit_id += 1
        return unit

    def remove_unit(self, unit_id: int):
        """Remove a unit from the game."""
        if unit_id in self.units:
            if self.selected_unit_id == unit_id:
                self.selected_unit_id = None
            del self.units[unit_id]

    def create_city(self, name: str, position: HexCoord, owner_id: int = 0) -> City:
        """Create a new city."""
        city = City(
            id=self._next_city_id,
            name=name,
            position=position,
            owner_id=owner_id
        )
        self.cities[city.id] = city
        self._next_city_id += 1

        # Auto-assign worked tiles
        city.auto_assign_tiles(self.game_map, list(self.cities.values()))

        # Increment player's city count
        player = self.get_player(owner_id)
        if player:
            player.cities_founded += 1

        return city

    def get_player(self, player_id: int) -> Optional[Player]:
        """Get player by ID."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    @property
    def current_player(self) -> Player:
        """Get the current player."""
        return self.players[self.current_player_index]

    @property
    def selected_unit(self) -> Optional[Unit]:
        """Get the currently selected unit."""
        if self.selected_unit_id is not None:
            return self.units.get(self.selected_unit_id)
        return None

    @property
    def selected_city(self) -> Optional[City]:
        """Get the currently selected city."""
        if self.selected_city_id is not None:
            return self.cities.get(self.selected_city_id)
        return None

    def select_unit(self, unit_id: Optional[int]):
        """Select a unit by ID."""
        # Deselect previous unit
        if self.selected_unit:
            self.selected_unit.is_selected = False

        # Deselect city when selecting unit
        self.selected_city_id = None

        self.selected_unit_id = unit_id

        # Select new
        if self.selected_unit:
            self.selected_unit.is_selected = True

    def select_city(self, city_id: Optional[int]):
        """Select a city by ID."""
        # Deselect unit when selecting city
        if self.selected_unit:
            self.selected_unit.is_selected = False
        self.selected_unit_id = None

        self.selected_city_id = city_id

    def get_unit_at(self, coord: HexCoord) -> Optional[Unit]:
        """Get unit at the given coordinates."""
        for unit in self.units.values():
            if unit.position == coord:
                return unit
        return None

    def get_city_at(self, coord: HexCoord) -> Optional[City]:
        """Get city at the given coordinates."""
        for city in self.cities.values():
            if city.position == coord:
                return city
        return None

    def get_player_units(self, player_id: int) -> List[Unit]:
        """Get all units belonging to a player."""
        return [u for u in self.units.values() if u.owner_id == player_id]

    def get_player_cities(self, player_id: int) -> List[City]:
        """Get all cities belonging to a player."""
        return [c for c in self.cities.values() if c.owner_id == player_id]

    def get_current_player_units(self) -> List[Unit]:
        """Get all units belonging to the current player."""
        return self.get_player_units(self.current_player.id)

    def get_current_player_cities(self) -> List[City]:
        """Get all cities belonging to the current player."""
        return self.get_player_cities(self.current_player.id)

    def can_found_city_at(self, coord: HexCoord) -> Tuple[bool, str]:
        """
        Check if a city can be founded at the given location.
        Returns (can_found, reason).
        """
        tile = self.game_map.get_tile(coord)
        if not tile:
            return False, "Invalid location"

        if not tile.is_passable:
            return False, "Cannot found city on impassable terrain"

        if tile.terrain.value in ('ocean', 'coast'):
            return False, "Cannot found city on water"

        # Check distance from other cities (minimum 3 hexes)
        for city in self.cities.values():
            dist = hex_distance(coord, city.position)
            if dist < 4:  # Must be at least 4 hexes apart (3 hex gap)
                return False, f"Too close to {city.name}"

        # Check if there's already a city here
        if self.get_city_at(coord):
            return False, "City already exists here"

        return True, "Valid location"

    def start_found_city(self, settler_id: int) -> bool:
        """
        Start the city founding process for a settler.
        Returns True if the settler can found a city at their current location.
        """
        settler = self.units.get(settler_id)
        if not settler or not settler.can_found_city:
            return False

        can_found, reason = self.can_found_city_at(settler.position)
        if not can_found:
            return False

        # Store pending city info
        self.pending_city_location = settler.position
        self.pending_city_settler_id = settler_id

        # Check if this is the first city (needs naming)
        player = self.get_player(settler.owner_id)
        if player and player.cities_founded == 0:
            self.phase = GamePhase.NAMING_CITY
            return True
        else:
            # Auto-name subsequent cities
            city_name = player.get_next_city_name() if player else "City"
            self.complete_found_city(city_name)
            return True

    def complete_found_city(self, name: str) -> Optional[City]:
        """Complete the city founding process with the given name."""
        if not self.pending_city_location or self.pending_city_settler_id is None:
            return None

        settler = self.units.get(self.pending_city_settler_id)
        if not settler:
            self.pending_city_location = None
            self.pending_city_settler_id = None
            self.phase = GamePhase.PLAYING
            return None

        # Create the city
        city = self.create_city(name, self.pending_city_location, settler.owner_id)

        # Remove the settler
        self.remove_unit(self.pending_city_settler_id)

        # Clear pending state
        self.pending_city_location = None
        self.pending_city_settler_id = None
        self.phase = GamePhase.PLAYING

        # Select the new city
        self.select_city(city.id)

        return city

    def cancel_found_city(self):
        """Cancel the city founding process."""
        self.pending_city_location = None
        self.pending_city_settler_id = None
        self.phase = GamePhase.PLAYING

    def set_city_production(self, city_id: int, production_type: ProductionType) -> bool:
        """Set what a city is producing."""
        city = self.cities.get(city_id)
        if not city:
            return False
        if city.owner_id != self.current_player.id:
            return False

        city.set_production(production_type)
        return True

    def move_unit(self, unit_id: int, target: HexCoord) -> bool:
        """
        Attempt to move a unit to the target position.
        Returns True if successful.
        """
        unit = self.units.get(unit_id)
        if not unit:
            return False

        if unit.owner_id != self.current_player.id:
            return False

        # Check for unit at target
        blocking_unit = self.get_unit_at(target)
        if blocking_unit:
            return False

        # Check for city at target (units can enter friendly cities)
        city_at_target = self.get_city_at(target)
        if city_at_target and city_at_target.owner_id != unit.owner_id:
            return False

        return unit.move_to(target, self.game_map)

    def end_turn(self):
        """End the current player's turn."""
        # End turn for current player's units
        for unit in self.get_current_player_units():
            unit.end_turn()

        # Process cities
        self._process_cities()

        # Move to next player (for multiplayer)
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

        # If we're back to player 1, increment turn number
        if self.current_player_index == 0:
            self.turn_number += 1
            self._start_new_turn()

    def _process_cities(self):
        """Process all cities for the current player at end of turn."""
        player = self.current_player

        for city in self.get_current_player_cities():
            events = city.process_turn(self.game_map)

            # Handle production completion
            if events['production_complete']:
                prod_type = events['production_complete']
                self._handle_production_complete(city, prod_type)

            # Accumulate resources
            yields = city.calculate_yields(self.game_map)
            player.gold += yields.gold
            player.science += yields.science

    def _handle_production_complete(self, city: City, production_type: ProductionType):
        """Handle when a city completes production."""
        if production_type == ProductionType.WARRIOR:
            # Create warrior at city location (or adjacent if blocked)
            spawn_pos = self._find_spawn_near_city(city)
            if spawn_pos:
                self.create_unit(UnitType.WARRIOR, spawn_pos, city.owner_id)

        elif production_type == ProductionType.SETTLER:
            spawn_pos = self._find_spawn_near_city(city)
            if spawn_pos:
                self.create_unit(UnitType.SETTLER, spawn_pos, city.owner_id)

    def _find_spawn_near_city(self, city: City) -> Optional[HexCoord]:
        """Find a valid spawn location near a city."""
        # Try city center first
        if not self.get_unit_at(city.position):
            return city.position

        # Try adjacent tiles
        for tile in self.game_map.get_neighbors(city.position):
            if tile.is_passable and not self.get_unit_at(tile.coord):
                return tile.coord

        return None

    def _start_new_turn(self):
        """Handle start of a new turn."""
        # Reset all units' movement
        for unit in self.units.values():
            unit.start_turn()

    def get_movement_range(self, unit_id: int) -> Dict[HexCoord, float]:
        """Get the movement range for a unit."""
        unit = self.units.get(unit_id)
        if not unit:
            return {}
        return unit.get_movement_range(self.game_map)

    def get_tile(self, coord: HexCoord) -> Optional[Tile]:
        """Get tile at coordinates."""
        return self.game_map.get_tile(coord)

    def handle_hex_click(self, coord: HexCoord) -> bool:
        """
        Handle a click on a hex.
        Returns True if the click was handled.
        """
        tile = self.get_tile(coord)
        if not tile:
            return False

        # Check if clicking on a city
        city_at_coord = self.get_city_at(coord)
        if city_at_coord and city_at_coord.owner_id == self.current_player.id:
            self.select_city(city_at_coord.id)
            return True

        # Check if clicking on a unit
        unit_at_coord = self.get_unit_at(coord)
        if unit_at_coord and unit_at_coord.owner_id == self.current_player.id:
            self.select_unit(unit_at_coord.id)
            return True

        # If we have a selected unit, try to move it
        if self.selected_unit and self.selected_unit.can_move:
            movement_range = self.get_movement_range(self.selected_unit.id)
            if coord in movement_range:
                if self.move_unit(self.selected_unit.id, coord):
                    return True

        # Clicking elsewhere deselects
        self.select_unit(None)
        self.select_city(None)
        return False
