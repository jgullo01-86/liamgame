"""
Simple AI controller for computer opponents.
"""

import random
from typing import Optional, List

from src.models.unit import Unit, UnitType
from src.models.city import ProductionType
from src.utils.hex_utils import HexCoord, hex_distance


class AIController:
    """AI that manages units and cities for non-human players."""

    def __init__(self, game_state):
        self.game_state = game_state

    def take_turn(self, player_id: int):
        """Execute a full AI turn for the given player."""
        gs = self.game_state

        # Process cities first (set production)
        self._manage_cities(player_id)

        # Then move units (settlers first so they found cities ASAP)
        units = list(gs.get_player_units(player_id))
        settlers = [u for u in units if u.unit_type == UnitType.SETTLER and u.can_move]
        military = [u for u in units if u.unit_type != UnitType.SETTLER and u.can_move]

        for unit in settlers:
            self._move_settler(unit)

        for unit in military:
            # Re-check can_move in case unit was removed during another's combat
            if unit.id in gs.units and unit.can_move:
                self._move_military(unit)

    def _manage_cities(self, player_id: int):
        """Actively manage city production each turn."""
        gs = self.game_state
        cities = gs.get_player_cities(player_id)
        units = gs.get_player_units(player_id)

        num_military = sum(1 for u in units if u.unit_type not in (UnitType.SETTLER, UnitType.SCOUT))
        num_settlers = sum(1 for u in units if u.unit_type == UnitType.SETTLER)
        # Expand early: get 2nd city after first warrior, 3rd city later
        need_settler = num_settlers == 0 and (
            (len(cities) < 2 and num_military >= 1) or
            (len(cities) < 3 and num_military >= 3)
        )

        for city in cities:
            # Decide what this city should build
            if need_settler and city.current_production != ProductionType.SETTLER:
                # Switch one city to settler production
                city.set_production(ProductionType.SETTLER)
                need_settler = False
            elif not need_settler and city.current_production == ProductionType.SETTLER:
                # Don't need settler anymore — switch to military
                self._set_military_production(city, num_military, len(cities))
            elif city.current_production is None:
                # City is idle — build military
                self._set_military_production(city, num_military, len(cities))
            # Otherwise keep building what we're building

    def _set_military_production(self, city, num_military: int, num_cities: int):
        """Pick a military unit to produce."""
        choices = [
            ProductionType.WARRIOR,
            ProductionType.WARRIOR,
            ProductionType.ARCHER,
            ProductionType.ARCHER,
            ProductionType.HORSEMAN,
        ]
        city.set_production(random.choice(choices))

    def _move_settler(self, unit: Unit):
        """Move settler toward a good city location and found city."""
        gs = self.game_state

        # Try to found city at current location first
        can_found, _ = gs.can_found_city_at(unit.position)
        if can_found:
            player = gs.get_player(unit.owner_id)
            name = player.get_next_city_name() if player else "AI City"
            gs.pending_city_location = unit.position
            gs.pending_city_settler_id = unit.id
            gs.complete_found_city(name)
            return

        # Move toward best city location in range
        movement_range = unit.get_movement_range(gs.game_map)
        if not movement_range:
            return

        best_coord = None
        best_score = -999

        for coord in movement_range:
            if gs.get_unit_at(coord):
                continue

            # Can we found a city here?
            can_found, _ = gs.can_found_city_at(coord)
            if can_found:
                # Great spot — found immediately if we can get there
                best_coord = coord
                best_score = 1000
                break

            # Otherwise score by distance from nearest city (prefer moderate distance)
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
            # After moving, try to found city at new position
            can_found, _ = gs.can_found_city_at(unit.position)
            if can_found:
                player = gs.get_player(unit.owner_id)
                name = player.get_next_city_name() if player else "AI City"
                gs.pending_city_location = unit.position
                gs.pending_city_settler_id = unit.id
                gs.complete_found_city(name)

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
            # Prioritize cities slightly (worth attacking)
            if d - 1 < nearest_dist:
                nearest_dist = d - 1
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
                # After moving, try to attack if now in range
                if unit.id in gs.units and unit.can_move and nearest_enemy:
                    if unit.can_attack_at(nearest_enemy):
                        enemy_at = gs.get_unit_at(nearest_enemy)
                        if enemy_at and enemy_at.owner_id != unit.owner_id:
                            gs.attack_unit(unit.id, nearest_enemy)
                return

        # No enemy found — explore toward center or random
        valid_moves = [c for c in movement_range if not gs.get_unit_at(c)]
        if valid_moves:
            # Bias toward map center for exploration
            center = HexCoord(20, 15)
            valid_moves.sort(key=lambda c: hex_distance(c, center))
            # Pick from top 3 closest to center with some randomness
            choices = valid_moves[:min(3, len(valid_moves))]
            unit.move_to(random.choice(choices), gs.game_map)
