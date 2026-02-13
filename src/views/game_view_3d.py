"""
Main 3D game view using Ursina — builds map, handles hover/selection overlays.
"""

from ursina import Entity, mouse, color, load_texture
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder
from typing import Dict, Optional, Set
import math
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState
from src.views.hex_mesh import HexTile3D
from src.utils.hex_utils import HexCoord, hex_to_world_3d
from config import HEX_3D_SIZE, TERRAIN_HEIGHTS


def _color_entity(entity, c):
    """Apply color via Panda3D set_color for Ursina 7 compatibility."""
    if hasattr(c, 'r'):
        r, g, b = c.r, c.g, c.b
        a = getattr(c, 'a', 1)
        # Ursina color.rgb() stores 0-255 values, Panda3D set_color needs 0-1
        if r > 1 or g > 1 or b > 1:
            r, g, b = r / 255, g / 255, b / 255
        if a > 1:
            a = a / 255
        entity.set_color(r, g, b, a)
    return entity


class GameView3D:
    """Main 3D view manager — builds hex map with terrain decorations."""

    # Shared meshes (created once, reused for all decorations)
    _cone_mesh = None
    _cylinder_mesh = None

    @classmethod
    def _get_cone_mesh(cls):
        if cls._cone_mesh is None:
            cls._cone_mesh = Cone()
        return cls._cone_mesh

    @classmethod
    def _get_cylinder_mesh(cls):
        if cls._cylinder_mesh is None:
            cls._cylinder_mesh = Cylinder()
        return cls._cylinder_mesh

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.hex_tiles: Dict[HexCoord, HexTile3D] = {}
        self.hovered_tile: Optional[HexTile3D] = None
        self.movement_range_tiles: Set[HexCoord] = set()
        self.attack_range_tiles: Set[HexCoord] = set()
        self._decorations = []
        self._map_built = False
        self._textures = {}
        self._frame_count = 0
        self._water_tiles: list = []

    def _load_textures(self):
        """Load terrain textures."""
        try:
            self._textures = {
                'grass': load_texture('assets/textures/grass.png'),
                'water': load_texture('assets/textures/water.png'),
                'sand': load_texture('assets/textures/sand.png'),
                'rock': load_texture('assets/textures/rock.png'),
                'snow': load_texture('assets/textures/snow.png'),
                'dirt': load_texture('assets/textures/dirt.png'),
            }
        except Exception:
            self._textures = {}

    def build_map(self):
        """Create 3D hex tiles and terrain decorations for all map tiles."""
        if self._map_built:
            return

        self._load_textures()
        print("Building hex map with terrain decorations...")

        for tile in self.game_state.game_map:
            hex_tile = HexTile3D(
                coord=tile.coord,
                terrain_type=tile.terrain.value,
                elevation=tile.elevation
            )
            self.hex_tiles[tile.coord] = hex_tile

            # Add terrain decorations
            self._add_terrain_decorations(tile, hex_tile)

        # Cache water tile coords for efficient shimmer updates
        self._water_tiles = [
            coord for coord, tile in self.hex_tiles.items()
            if tile.terrain_type in ('ocean', 'coast')
        ]

        self._map_built = True
        print(f"Built {len(self.hex_tiles)} hex tiles ({len(self._water_tiles)} water)")

    def _add_decoration(self, entity):
        """Add a decoration entity (lighting enabled for 3D depth)."""
        self._decorations.append(entity)

    def _add_terrain_decorations(self, tile, hex_tile: HexTile3D):
        """Add minimal 3D features — textures handle most terrain visuals."""
        terrain = tile.terrain.value
        x, _, z = hex_to_world_3d(tile.coord, HEX_3D_SIZE, 0)
        h = hex_tile.terrain_height

        # Mountains: add a subtle peak cone for 3D effect
        if terrain == 'mountains':
            peak = Entity(
                model=self._get_cone_mesh(),
                position=(x, h + 0.8, z),
                scale=(HEX_3D_SIZE * 0.3, 1.5, HEX_3D_SIZE * 0.3)
            )
            _color_entity(peak, color.rgb(160, 155, 145))
            self._add_decoration(peak)

        # Forest: add a couple small canopy bumps for subtle 3D depth
        elif terrain == 'forest':
            for _ in range(2):
                fx = x + random.uniform(-1.2, 1.2)
                fz = z + random.uniform(-1.2, 1.2)
                canopy = Entity(
                    model='sphere',
                    position=(fx, h + 0.3, fz),
                    scale=(random.uniform(0.6, 1.0), 0.4, random.uniform(0.6, 1.0))
                )
                _color_entity(canopy, color.rgb(random.randint(40, 70), random.randint(120, 160), random.randint(30, 50)))
                self._add_decoration(canopy)

    def update(self):
        """Called every frame by Ursina."""
        self._update_hover()
        self._update_movement_range()
        self._update_water_shimmer()

    def _update_water_shimmer(self):
        """Apply a subtle brightness ripple to water tiles."""
        self._frame_count += 1
        if self._frame_count % 10 != 0:
            return

        for coord in self._water_tiles:
            tile = self.hex_tiles[coord]
            # Skip tiles that have an active overlay (highlight, movement, attack)
            if tile._is_highlighted or tile._is_in_movement_range or tile._is_attack_target:
                continue
            phase = coord.q * 0.3 + coord.r * 0.5
            brightness = 1.0 + 0.1 * math.sin(self._frame_count * 0.05 + phase)
            tile.setColorScale(brightness, brightness, brightness + 0.05, 1)

    def _update_hover(self):
        """Update hovered tile highlight."""
        if self.hovered_tile:
            self.hovered_tile.highlight(False)
            self.hovered_tile = None

        if mouse.hovered_entity and isinstance(mouse.hovered_entity, HexTile3D):
            self.hovered_tile = mouse.hovered_entity
            self.hovered_tile.highlight(True)
            self.game_state.hovered_hex = self.hovered_tile.coord
        else:
            self.game_state.hovered_hex = None

    def _update_movement_range(self):
        """Update movement range and attack range overlays."""
        # Clear old overlays
        for coord in self.movement_range_tiles:
            if coord in self.hex_tiles:
                self.hex_tiles[coord].set_movement_range(False)
        self.movement_range_tiles.clear()

        for coord in self.attack_range_tiles:
            if coord in self.hex_tiles:
                self.hex_tiles[coord].set_attack_target(False)
        self.attack_range_tiles.clear()

        # Show movement/attack range for selected unit
        unit = self.game_state.selected_unit
        if unit and unit.can_move:
            movement_range = self.game_state.get_movement_range(unit.id)
            for coord in movement_range.keys():
                # Check if there's an enemy here — show as attack target
                target_unit = self.game_state.get_unit_at(coord)
                if target_unit and target_unit.owner_id != unit.owner_id:
                    if coord in self.hex_tiles:
                        self.hex_tiles[coord].set_attack_target(True)
                        self.attack_range_tiles.add(coord)
                elif coord in self.hex_tiles:
                    self.hex_tiles[coord].set_movement_range(True)
                    self.movement_range_tiles.add(coord)

            # Show ranged attack targets beyond movement range
            if unit.attack_range > 1:
                from src.utils.hex_utils import hex_range
                attack_hexes = hex_range(unit.position, unit.attack_range)
                for coord in attack_hexes:
                    if coord == unit.position or coord in movement_range:
                        continue
                    target_unit = self.game_state.get_unit_at(coord)
                    if target_unit and target_unit.owner_id != unit.owner_id:
                        if coord in self.hex_tiles:
                            self.hex_tiles[coord].set_attack_target(True)
                            self.attack_range_tiles.add(coord)

    def get_clicked_hex(self) -> Optional[HexCoord]:
        """Get the hex coordinate that was clicked."""
        if mouse.hovered_entity and isinstance(mouse.hovered_entity, HexTile3D):
            return mouse.hovered_entity.coord
        return None

    def get_terrain_height(self, coord: HexCoord) -> float:
        """Get the terrain height at a coordinate."""
        if coord in self.hex_tiles:
            return self.hex_tiles[coord].terrain_height
        return 0.0
