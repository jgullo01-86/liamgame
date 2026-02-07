"""
Game state model - holds all game data and logic.
"""

import json
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from src.models.map import GameMap, Tile
from src.models.unit import Unit, UnitType
from src.models.city import City, ProductionType, PRODUCTION_ITEMS
from src.utils.hex_utils import HexCoord, hex_distance, hex_range
from config import MAX_TURNS, SCORE_PER_POPULATION, SCORE_PER_CITY, SCORE_PER_UNIT, SCORE_PER_GOLD


class GamePhase(Enum):
    """Current phase of the game."""
    SETUP = 'setup'
    PLAYING = 'playing'
    NAMING_CITY = 'naming_city'
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
    color: tuple
    is_human: bool = True
    civilization: Optional[Civilization] = None
    gold: int = 0
    science: int = 0
    culture: int = 0
    cities_founded: int = 0
    is_defeated: bool = False

    def get_next_city_name(self) -> str:
        if self.civilization and self.cities_founded < len(self.civilization.city_names):
            return self.civilization.city_names[self.cities_founded]
        return f"City {self.cities_founded + 1}"

    def calculate_score(self, units: list, cities: list) -> int:
        pop = sum(c.population for c in cities)
        return int(
            pop * SCORE_PER_POPULATION +
            len(cities) * SCORE_PER_CITY +
            len(units) * SCORE_PER_UNIT +
            self.gold * SCORE_PER_GOLD
        )


def load_civilizations() -> Dict[str, Civilization]:
    try:
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


CIVILIZATIONS: Dict[str, Civilization] = {}


@dataclass
class GameState:
    """Central game state container."""
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

    # Events (cleared each frame, read by UI)
    events: List[str] = field(default_factory=list)

    # Victory state
    victory_player: Optional[int] = None
    victory_type: Optional[str] = None

    # AI controller reference (set externally)
    ai_controller: object = None

    def __post_init__(self):
        global CIVILIZATIONS
        if not CIVILIZATIONS:
            CIVILIZATIONS = load_civilizations()

        if not self.players:
            civ = CIVILIZATIONS.get('rome')
            self.players.append(Player(
                id=0,
                name="Player 1",
                color=civ.primary_color if civ else (50, 150, 255),
                civilization=civ
            ))

    def initialize_game(self, map_seed: Optional[int] = None, civ_id: str = 'rome',
                        ai_count: int = 1):
        """Set up a new game with human + AI players."""
        global CIVILIZATIONS
        if not CIVILIZATIONS:
            CIVILIZATIONS = load_civilizations()

        self.units.clear()
        self.cities.clear()
        self._next_unit_id = 0
        self._next_city_id = 0
        self.events = []
        self.victory_player = None
        self.victory_type = None

        # Set player civilization
        civ = CIVILIZATIONS.get(civ_id)
        if civ and self.players:
            self.players[0].civilization = civ
            self.players[0].color = civ.primary_color
            self.players[0].cities_founded = 0
            self.players[0].is_defeated = False

        # Generate map
        self.game_map = GameMap(seed=map_seed)

        # Create starting settler for human player
        spawn = self.game_map.find_spawn_location()
        if spawn:
            self.create_unit(UnitType.SETTLER, spawn, owner_id=0)
            # Also give a warrior
            warrior_spawn = self._find_nearby_spawn(spawn)
            if warrior_spawn:
                self.create_unit(UnitType.WARRIOR, warrior_spawn, owner_id=0)

        # Create AI players
        ai_civ_ids = [k for k in CIVILIZATIONS.keys() if k != civ_id]
        random.shuffle(ai_civ_ids)

        for i in range(min(ai_count, len(ai_civ_ids))):
            ai_civ = CIVILIZATIONS[ai_civ_ids[i]]
            ai_player = Player(
                id=len(self.players),
                name=f"{ai_civ.name}",
                color=ai_civ.primary_color,
                is_human=False,
                civilization=ai_civ
            )
            self.players.append(ai_player)

            # Find spawn far from human
            ai_spawn = self.game_map.find_spawn_location_far_from(spawn)
            if ai_spawn:
                self.create_unit(UnitType.SETTLER, ai_spawn, owner_id=ai_player.id)
                ai_warrior_spawn = self._find_nearby_spawn(ai_spawn)
                if ai_warrior_spawn:
                    self.create_unit(UnitType.WARRIOR, ai_warrior_spawn, owner_id=ai_player.id)

        self.phase = GamePhase.PLAYING
        self.turn_number = 1

    def _find_nearby_spawn(self, near: HexCoord) -> Optional[HexCoord]:
        """Find a passable tile near the given coordinate."""
        for tile in self.game_map.get_neighbors(near):
            if tile.is_passable and not self.get_unit_at(tile.coord):
                return tile.coord
        return None

    def create_unit(self, unit_type: UnitType, position: HexCoord, owner_id: int = 0) -> Unit:
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
        if unit_id in self.units:
            if self.selected_unit_id == unit_id:
                self.selected_unit_id = None
            del self.units[unit_id]

    def create_city(self, name: str, position: HexCoord, owner_id: int = 0) -> City:
        player = self.get_player(owner_id)
        is_capital = player.cities_founded == 0 if player else False

        city = City(
            id=self._next_city_id,
            name=name,
            position=position,
            owner_id=owner_id,
            is_capital=is_capital
        )
        self.cities[city.id] = city
        self._next_city_id += 1

        city.auto_assign_tiles(self.game_map, list(self.cities.values()))

        if player:
            player.cities_founded += 1

        return city

    def get_player(self, player_id: int) -> Optional[Player]:
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def selected_unit(self) -> Optional[Unit]:
        if self.selected_unit_id is not None:
            return self.units.get(self.selected_unit_id)
        return None

    @property
    def selected_city(self) -> Optional[City]:
        if self.selected_city_id is not None:
            return self.cities.get(self.selected_city_id)
        return None

    def select_unit(self, unit_id: Optional[int]):
        if self.selected_unit:
            self.selected_unit.is_selected = False
        self.selected_city_id = None
        self.selected_unit_id = unit_id
        if self.selected_unit:
            self.selected_unit.is_selected = True

    def select_city(self, city_id: Optional[int]):
        if self.selected_unit:
            self.selected_unit.is_selected = False
        self.selected_unit_id = None
        self.selected_city_id = city_id

    def get_unit_at(self, coord: HexCoord) -> Optional[Unit]:
        for unit in self.units.values():
            if unit.position == coord:
                return unit
        return None

    def get_units_at(self, coord: HexCoord) -> List[Unit]:
        return [u for u in self.units.values() if u.position == coord]

    def get_city_at(self, coord: HexCoord) -> Optional[City]:
        for city in self.cities.values():
            if city.position == coord:
                return city
        return None

    def get_player_units(self, player_id: int) -> List[Unit]:
        return [u for u in self.units.values() if u.owner_id == player_id]

    def get_player_cities(self, player_id: int) -> List[City]:
        return [c for c in self.cities.values() if c.owner_id == player_id]

    def get_current_player_units(self) -> List[Unit]:
        return self.get_player_units(self.current_player.id)

    def get_current_player_cities(self) -> List[City]:
        return self.get_player_cities(self.current_player.id)

    def can_found_city_at(self, coord: HexCoord) -> Tuple[bool, str]:
        tile = self.game_map.get_tile(coord)
        if not tile:
            return False, "Invalid location"
        if not tile.is_passable:
            return False, "Cannot found city on impassable terrain"
        if tile.terrain.value in ('ocean', 'coast'):
            return False, "Cannot found city on water"
        for city in self.cities.values():
            dist = hex_distance(coord, city.position)
            if dist < 4:
                return False, f"Too close to {city.name}"
        if self.get_city_at(coord):
            return False, "City already exists here"
        return True, "Valid location"

    def start_found_city(self, settler_id: int) -> bool:
        settler = self.units.get(settler_id)
        if not settler or not settler.can_found_city:
            return False
        can_found, reason = self.can_found_city_at(settler.position)
        if not can_found:
            return False
        self.pending_city_location = settler.position
        self.pending_city_settler_id = settler_id
        player = self.get_player(settler.owner_id)
        if player and player.cities_founded == 0:
            self.phase = GamePhase.NAMING_CITY
            return True
        else:
            city_name = player.get_next_city_name() if player else "City"
            self.complete_found_city(city_name)
            return True

    def complete_found_city(self, name: str) -> Optional[City]:
        if not self.pending_city_location or self.pending_city_settler_id is None:
            return None
        settler = self.units.get(self.pending_city_settler_id)
        if not settler:
            self.pending_city_location = None
            self.pending_city_settler_id = None
            self.phase = GamePhase.PLAYING
            return None
        city = self.create_city(name, self.pending_city_location, settler.owner_id)
        self.remove_unit(self.pending_city_settler_id)
        self.pending_city_location = None
        self.pending_city_settler_id = None
        self.phase = GamePhase.PLAYING
        self.select_city(city.id)
        self.events.append(f"{city.name} founded!")
        return city

    def cancel_found_city(self):
        self.pending_city_location = None
        self.pending_city_settler_id = None
        self.phase = GamePhase.PLAYING

    def set_city_production(self, city_id: int, production_type: ProductionType) -> bool:
        city = self.cities.get(city_id)
        if not city:
            return False
        if city.owner_id != self.current_player.id:
            return False
        city.set_production(production_type)
        return True

    def move_unit(self, unit_id: int, target: HexCoord) -> bool:
        unit = self.units.get(unit_id)
        if not unit:
            return False
        if unit.owner_id != self.current_player.id:
            return False

        # Check for enemy unit at target — trigger combat
        target_unit = self.get_unit_at(target)
        if target_unit and target_unit.owner_id != unit.owner_id:
            return self.attack_unit(unit.id, target)

        # Check for enemy city at target — capture it
        city_at_target = self.get_city_at(target)
        if city_at_target and city_at_target.owner_id != unit.owner_id:
            return self._capture_city(unit, city_at_target)

        # Normal movement — block if friendly unit there
        if target_unit:
            return False

        return unit.move_to(target, self.game_map)

    def attack_unit(self, attacker_id: int, target_coord: HexCoord) -> bool:
        """Attack an enemy unit at the target coordinate."""
        attacker = self.units.get(attacker_id)
        if not attacker:
            return False

        defender = self.get_unit_at(target_coord)
        if not defender or defender.owner_id == attacker.owner_id:
            return False

        if not attacker.can_attack_at(target_coord):
            return False

        result = attacker.attack(defender, self.game_map)

        if result['killed']:
            defender_name = defender.name
            self.remove_unit(defender.id)
            self.events.append(f"{attacker.name} destroyed {defender_name}!")

            # Move attacker to defender's position for melee kills
            if attacker.attack_range <= 1 and result['attacker_alive']:
                attacker.position = target_coord
        else:
            self.events.append(f"{attacker.name} hit {defender.name} for {result['damage']} damage!")

        # Check if attacker died from counter-damage
        if not result['attacker_alive']:
            self.remove_unit(attacker_id)
            self.events.append(f"{attacker.name} was destroyed in combat!")

        self._check_victory()
        return True

    def _capture_city(self, attacker: Unit, city: City) -> bool:
        """Capture an enemy city."""
        old_owner = self.get_player(city.owner_id)
        new_owner = self.get_player(attacker.owner_id)

        city.owner_id = attacker.owner_id
        city.population = max(1, city.population - 1)
        attacker.position = city.position
        attacker.movement_remaining = 0

        self.events.append(f"{city.name} captured by {new_owner.name if new_owner else 'unknown'}!")

        self._check_victory()
        return True

    def end_turn(self):
        """End the current player's turn."""
        self.events.clear()

        # End turn for current player's units
        for unit in self.get_current_player_units():
            unit.end_turn()

        # Process cities
        self._process_cities()

        # Move to next player
        self.current_player_index = (self.current_player_index + 1) % len(self.players)

        # Skip defeated players
        attempts = 0
        while self.current_player.is_defeated and attempts < len(self.players):
            self.current_player_index = (self.current_player_index + 1) % len(self.players)
            attempts += 1

        # If back to player 0 (or wrapped), new turn
        if self.current_player_index == 0:
            self.turn_number += 1
            self._start_new_turn()
            self._check_score_victory()

        # AI takes turn automatically
        if not self.current_player.is_human and self.phase == GamePhase.PLAYING:
            self._run_ai_turn()

    def _run_ai_turn(self):
        """Run AI turn for current (non-human) player."""
        if self.ai_controller:
            self.ai_controller.take_turn(self.current_player.id)
        # Auto-advance to next player
        self.end_turn()

    def _process_cities(self):
        player = self.current_player
        for city in self.get_current_player_cities():
            events = city.process_turn(self.game_map)
            if events['production_complete']:
                prod_type = events['production_complete']
                self._handle_production_complete(city, prod_type)
            if events['grew']:
                self.events.append(f"{city.name} grew to pop {city.population}!")
            yields = city.calculate_yields(self.game_map)
            player.gold += yields.gold
            player.science += yields.science

    def _handle_production_complete(self, city: City, production_type: ProductionType):
        unit_type_map = {
            ProductionType.WARRIOR: UnitType.WARRIOR,
            ProductionType.SETTLER: UnitType.SETTLER,
            ProductionType.SCOUT: UnitType.SCOUT,
            ProductionType.ARCHER: UnitType.ARCHER,
            ProductionType.HORSEMAN: UnitType.HORSEMAN,
        }
        unit_type = unit_type_map.get(production_type)
        if unit_type:
            spawn_pos = self._find_spawn_near_city(city)
            if spawn_pos:
                self.create_unit(unit_type, spawn_pos, city.owner_id)
                self.events.append(f"{city.name} produced a {unit_type.value.title()}!")

    def _find_spawn_near_city(self, city: City) -> Optional[HexCoord]:
        if not self.get_unit_at(city.position):
            return city.position
        for tile in self.game_map.get_neighbors(city.position):
            if tile.is_passable and not self.get_unit_at(tile.coord):
                return tile.coord
        return None

    def _start_new_turn(self):
        for unit in self.units.values():
            unit.start_turn()

    def _check_victory(self):
        """Check for domination victory (all enemy capitals captured)."""
        if self.phase == GamePhase.GAME_OVER:
            return

        for player in self.players:
            if player.is_defeated:
                continue
            # Check if player lost all cities and units
            player_cities = self.get_player_cities(player.id)
            player_units = self.get_player_units(player.id)
            if not player_cities and not player_units:
                player.is_defeated = True
                self.events.append(f"{player.name} has been eliminated!")

        # Check if only one player remains
        active_players = [p for p in self.players if not p.is_defeated]
        if len(active_players) == 1:
            self.victory_player = active_players[0].id
            self.victory_type = "Domination"
            self.phase = GamePhase.GAME_OVER
            self.events.append(f"{active_players[0].name} wins by Domination!")

    def _check_score_victory(self):
        """Check for score victory at max turns."""
        if self.turn_number > MAX_TURNS and self.phase != GamePhase.GAME_OVER:
            best_player = None
            best_score = -1
            for player in self.players:
                if player.is_defeated:
                    continue
                units = self.get_player_units(player.id)
                cities = self.get_player_cities(player.id)
                score = player.calculate_score(units, cities)
                if score > best_score:
                    best_score = score
                    best_player = player

            if best_player:
                self.victory_player = best_player.id
                self.victory_type = "Score"
                self.phase = GamePhase.GAME_OVER
                self.events.append(f"{best_player.name} wins by Score ({best_score})!")

    def get_movement_range(self, unit_id: int) -> Dict[HexCoord, float]:
        unit = self.units.get(unit_id)
        if not unit:
            return {}
        return unit.get_movement_range(self.game_map)

    def get_tile(self, coord: HexCoord) -> Optional[Tile]:
        return self.game_map.get_tile(coord)

    def handle_hex_click(self, coord: HexCoord) -> bool:
        """Handle a click on a hex."""
        tile = self.get_tile(coord)
        if not tile:
            return False

        # If we have a selected unit, check for attack on enemy
        if self.selected_unit and self.selected_unit.can_move:
            unit_at_coord = self.get_unit_at(coord)
            if unit_at_coord and unit_at_coord.owner_id != self.current_player.id:
                if self.selected_unit.can_attack_at(coord):
                    return self.attack_unit(self.selected_unit.id, coord)

            # Check for enemy city capture
            city_at_coord = self.get_city_at(coord)
            if city_at_coord and city_at_coord.owner_id != self.current_player.id:
                movement_range = self.get_movement_range(self.selected_unit.id)
                if coord in movement_range:
                    return self._capture_city(self.selected_unit, city_at_coord)

        # Check if clicking on own city
        city_at_coord = self.get_city_at(coord)
        if city_at_coord and city_at_coord.owner_id == self.current_player.id:
            self.select_city(city_at_coord.id)
            return True

        # Check if clicking on own unit
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
