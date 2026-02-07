"""
Simple AI controller for computer opponents.
"""

import random
from typing import Optional, List

from src.models.unit import Unit, UnitType
from src.models.city import ProductionType
from src.utils.hex_utils import HexCoord, hex_distance


class AIController:
    """Simple AI that manages units and cities for non-human players."""

    def __init__(self, game_state):
        self.game_state = game_state

    def take_turn(self, player_id: int):
        """Execute a full AI turn for the given player."""
        gs = self.game_state

        # Process cities first (set production)
        self._manage_cities(player_id)

        # Then move units
        self._move_units(player_id)

    def _manage_cities(self, player_id: int):
        """Set production for cities that aren't building anything."""
        gs = self.game_state
        cities = gs.get_player_cities(player_id)
        units = gs.get_player_units(player_id)

        num_military = sum(1 for u in units if u.unit_type != UnitType.SETTLER)
        num_settlers = sum(1 for u in units if u.unit_type == UnitType.SETTLER)

        for city in cities:
            if city.current_production is not None:
                continue

            # Build settlers if we have few cities and no settlers
            if len(cities) < 3 and num_settlers == 0:
                city.set_production(ProductionType.SETTLER)
            # Build military if we have fewer than 2 per city
            elif num_military < len(cities) * 2:
                # Vary unit types
                choices = [ProductionType.WARRIOR, ProductionType.WARRIOR,
                           ProductionType.ARCHER, ProductionType.HORSEMAN]
                city.set_production(random.choice(choices))
            else:
                city.set_production(ProductionType.WARRIOR)

    def _move_units(self, player_id: int):
        """Move all units for this player."""
        gs = self.game_state
        units = list(gs.get_player_units(player_id))

        for unit in units:
            if not unit.can_move:
                continue

            if unit.unit_type == UnitType.SETTLER:
                self._move_settler(unit)
            else:
                self._move_military(unit)

    def _move_settler(self, unit: Unit):
        """Move settler toward a good city location and found city."""
        gs = self.game_state

        # Try to found city at current location
        can_found, _ = gs.can_found_city_at(unit.position)
        if can_found:
            player = gs.get_player(unit.owner_id)
            name = player.get_next_city_name() if player else "AI City"
            gs.pending_city_location = unit.position
            gs.pending_city_settler_id = unit.id
            gs.complete_found_city(name)
            return

        # Move toward unclaimed land far from existing cities
        movement_range = unit.get_movement_range(gs.game_map)
        if not movement_range:
            return

        best_coord = None
        best_score = -1

        for coord in movement_range:
            # Score: distance from nearest city (prefer far from cities)
            if gs.get_unit_at(coord):
                continue
            min_city_dist = 999
            for city in gs.cities.values():
                d = hex_distance(coord, city.position)
                min_city_dist = min(min_city_dist, d)

            score = min_city_dist
            if score > best_score:
                best_score = score
                best_coord = coord

        if best_coord:
            unit.move_to(best_coord, gs.game_map)

    def _move_military(self, unit: Unit):
        """Move military unit toward nearest enemy or explore."""
        gs = self.game_state

        # Find nearest enemy unit or city
        nearest_enemy = None
        nearest_dist = 999

        for enemy_unit in gs.units.values():
            if enemy_unit.owner_id == unit.owner_id:
                continue
            d = hex_distance(unit.position, enemy_unit.position)
            if d < nearest_dist:
                nearest_dist = d
                nearest_enemy = enemy_unit.position

        for enemy_city in gs.cities.values():
            if enemy_city.owner_id == unit.owner_id:
                continue
            d = hex_distance(unit.position, enemy_city.position)
            if d < nearest_dist:
                nearest_dist = d
                nearest_enemy = enemy_city.position

        # Try to attack adjacent enemy
        if nearest_enemy and unit.can_attack_at(nearest_enemy):
            enemy_at = gs.get_unit_at(nearest_enemy)
            if enemy_at and enemy_at.owner_id != unit.owner_id:
                gs.attack_unit(unit.id, nearest_enemy)
                return

        # Move toward nearest enemy
        movement_range = unit.get_movement_range(gs.game_map)
        if not movement_range:
            return

        if nearest_enemy:
            best_coord = None
            best_dist = 999
            for coord in movement_range:
                if gs.get_unit_at(coord):
                    continue
                d = hex_distance(coord, nearest_enemy)
                if d < best_dist:
                    best_dist = d
                    best_coord = coord

            if best_coord:
                unit.move_to(best_coord, gs.game_map)
                return

        # No enemy found — explore randomly
        valid_moves = [c for c in movement_range if not gs.get_unit_at(c)]
        if valid_moves:
            unit.move_to(random.choice(valid_moves), gs.game_map)
