"""
Main 3D game view using Ursina — builds map, handles hover/selection overlays.
"""

from ursina import Entity, mouse, color, load_texture
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder
from typing import Dict, Optional, Set
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState
from src.views.hex_mesh import HexTile3D
from src.utils.hex_utils import HexCoord, hex_to_world_3d
from config import HEX_3D_SIZE, TERRAIN_HEIGHTS


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

        self._map_built = True
        print(f"Built {len(self.hex_tiles)} hex tiles")

    def _add_terrain_decorations(self, tile, hex_tile: HexTile3D):
        """Add 3D terrain features on top of hex tiles."""
        terrain = tile.terrain.value
        x, _, z = hex_to_world_3d(tile.coord, HEX_3D_SIZE, 0)
        h = hex_tile.terrain_height

        if terrain == 'mountains':
            # Snow peak
            peak = Entity(
                model=self._get_cone_mesh(),
                color=color.white,
                position=(x, h + 2.0, z),
                scale=(HEX_3D_SIZE * 0.4, 3.5, HEX_3D_SIZE * 0.4)
            )
            self._decorations.append(peak)
            # Rocky base
            base = Entity(
                model=self._get_cone_mesh(),
                color=color.rgb(120, 110, 100),
                position=(x, h + 0.3, z),
                scale=(HEX_3D_SIZE * 0.7, 2.0, HEX_3D_SIZE * 0.7)
            )
            self._decorations.append(base)
            # Scattered rocks
            for _ in range(3):
                rx = x + random.uniform(-1.5, 1.5)
                rz = z + random.uniform(-1.5, 1.5)
                s = random.uniform(0.2, 0.5)
                rock = Entity(model='sphere', color=color.gray,
                              position=(rx, h + 0.2, rz), scale=(s, s * 0.6, s))
                self._decorations.append(rock)

        elif terrain == 'hills':
            hill = Entity(
                model='sphere',
                color=color.rgb(160, 140, 100),
                position=(x, h + 0.3, z),
                scale=(HEX_3D_SIZE * 0.6, 1.2, HEX_3D_SIZE * 0.6)
            )
            self._decorations.append(hill)
            for _ in range(2):
                rx = x + random.uniform(-1, 1)
                rz = z + random.uniform(-1, 1)
                rock = Entity(model='sphere', color=color.gray,
                              position=(rx, h + 0.5, rz), scale=(0.25, 0.2, 0.25))
                self._decorations.append(rock)

        elif terrain == 'forest':
            offsets = [
                (random.uniform(-1.2, -0.6), random.uniform(-1.2, -0.6)),
                (random.uniform(0.6, 1.2), random.uniform(-1.2, -0.6)),
                (random.uniform(-1.2, -0.6), random.uniform(0.6, 1.2)),
                (random.uniform(0.6, 1.2), random.uniform(0.6, 1.2)),
                (random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)),
            ]
            for dx, dz in offsets:
                tree_h = random.uniform(1.5, 2.5)
                trunk_h = random.uniform(0.4, 0.7)
                trunk = Entity(model=self._get_cylinder_mesh(), color=color.rgb(100, 70, 40),
                               position=(x + dx, h + trunk_h / 2, z + dz),
                               scale=(0.12, trunk_h, 0.12))
                foliage = Entity(model=self._get_cone_mesh(), color=color.rgb(30, 120, 30),
                                 position=(x + dx, h + trunk_h + tree_h * 0.4, z + dz),
                                 scale=(0.7, tree_h, 0.7))
                foliage2 = Entity(model=self._get_cone_mesh(), color=color.rgb(50, 150, 50),
                                  position=(x + dx, h + trunk_h + tree_h * 0.25, z + dz),
                                  scale=(0.9, tree_h * 0.65, 0.9))
                self._decorations.extend([trunk, foliage, foliage2])

        elif terrain == 'grassland':
            for _ in range(4):
                gx = x + random.uniform(-2, 2)
                gz = z + random.uniform(-2, 2)
                gh = random.uniform(0.15, 0.3)
                tuft = Entity(model='cube', color=color.rgb(120, 200, 100),
                              position=(gx, h + gh / 2 + 0.05, gz),
                              scale=(0.04, gh, 0.12),
                              rotation=(0, random.uniform(0, 360), 0))
                self._decorations.append(tuft)

        elif terrain == 'desert':
            if random.random() < 0.3:
                cx = x + random.uniform(-1, 1)
                cz = z + random.uniform(-1, 1)
                ch = random.uniform(0.6, 1.2)
                cactus = Entity(model=self._get_cylinder_mesh(), color=color.rgb(50, 140, 50),
                                position=(cx, h + ch / 2 + 0.05, cz),
                                scale=(0.15, ch, 0.15))
                self._decorations.append(cactus)
            if random.random() < 0.4:
                rx = x + random.uniform(-1.5, 1.5)
                rz = z + random.uniform(-1.5, 1.5)
                rock = Entity(model='sphere', color=color.rgb(200, 180, 140),
                              position=(rx, h + 0.1, rz),
                              scale=(random.uniform(0.2, 0.4), 0.12, random.uniform(0.2, 0.4)))
                self._decorations.append(rock)

        elif terrain == 'coast':
            if random.random() < 0.3:
                sx = x + random.uniform(-1.5, 1.5)
                sz = z + random.uniform(-1.5, 1.5)
                shell = Entity(model='sphere', color=color.white,
                               position=(sx, h + 0.05, sz), scale=(0.08, 0.04, 0.08))
                self._decorations.append(shell)

    def update(self):
        """Called every frame by Ursina."""
        self._update_hover()
        self._update_movement_range()

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
