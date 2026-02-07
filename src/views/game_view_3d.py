"""
Main 3D game view using Ursina.
"""

from ursina import Entity, mouse
from typing import Dict, Optional, Set
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState
from src.views.hex_mesh import HexTile3D
from src.utils.hex_utils import HexCoord


class GameView3D:
    """Main 3D view manager."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.hex_tiles: Dict[HexCoord, HexTile3D] = {}
        self.hovered_tile: Optional[HexTile3D] = None
        self.movement_range_tiles: Set[HexCoord] = set()

        # Will be set up after map generation
        self._map_built = False

    def build_map(self):
        """Create 3D entities for all map tiles."""
        if self._map_built:
            return

        for tile in self.game_state.game_map:
            hex_tile = HexTile3D(
                coord=tile.coord,
                terrain_type=tile.terrain.value,
                elevation=tile.elevation
            )
            self.hex_tiles[tile.coord] = hex_tile

        self._map_built = True

    def update(self):
        """Called every frame by Ursina."""
        self._update_hover()
        self._update_movement_range()

    def _update_hover(self):
        """Update hovered tile highlight."""
        # Clear previous hover
        if self.hovered_tile:
            self.hovered_tile.highlight(False)
            self.hovered_tile = None

        # Check if mouse is over a hex tile
        if mouse.hovered_entity and isinstance(mouse.hovered_entity, HexTile3D):
            self.hovered_tile = mouse.hovered_entity
            self.hovered_tile.highlight(True)
            self.game_state.hovered_hex = self.hovered_tile.coord
        else:
            self.game_state.hovered_hex = None

    def _update_movement_range(self):
        """Update movement range overlay."""
        # Clear old movement range
        for coord in self.movement_range_tiles:
            if coord in self.hex_tiles:
                self.hex_tiles[coord].set_movement_range(False)
        self.movement_range_tiles.clear()

        # Get new movement range if a unit is selected
        unit = self.game_state.selected_unit
        if unit and unit.can_move:
            movement_range = self.game_state.get_movement_range(unit.id)
            for coord in movement_range.keys():
                if coord in self.hex_tiles:
                    self.hex_tiles[coord].set_movement_range(True)
                    self.movement_range_tiles.add(coord)

    def get_clicked_hex(self) -> Optional[HexCoord]:
        """Get the hex coordinate that was clicked, if any."""
        if mouse.hovered_entity and isinstance(mouse.hovered_entity, HexTile3D):
            return mouse.hovered_entity.coord
        return None

    def get_terrain_height(self, coord: HexCoord) -> float:
        """Get the terrain height at a coordinate."""
        if coord in self.hex_tiles:
            return self.hex_tiles[coord].terrain_height
        return 0.0
