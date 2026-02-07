"""
3D unit and city rendering for Ursina.
Uses hex_to_world_3d for proper hex grid positioning.
"""

from ursina import Entity, Text, color, Vec3
from ursina.models.procedural.cone import Cone
from ursina.models.procedural.cylinder import Cylinder

# Shared meshes (created once)
_cone_mesh = None
_cylinder_mesh = None

def _get_cone():
    global _cone_mesh
    if _cone_mesh is None:
        _cone_mesh = Cone()
    return _cone_mesh

def _get_cylinder():
    global _cylinder_mesh
    if _cylinder_mesh is None:
        _cylinder_mesh = Cylinder()
    return _cylinder_mesh
from typing import Dict, Optional, List
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.unit import Unit, UnitType
from src.models.city import City
from src.utils.hex_utils import HexCoord, hex_to_world_3d
from config import HEX_3D_SIZE, TERRAIN_HEIGHTS

# Player colors
PLAYER_COLORS = [
    color.rgb(50, 120, 255),   # Player 1 - Blue
    color.rgb(220, 50, 50),    # Player 2 - Red
    color.rgb(255, 200, 50),   # Player 3 - Gold
    color.rgb(180, 50, 220),   # Player 4 - Purple
]


def get_player_color(owner_id: int):
    return PLAYER_COLORS[owner_id % len(PLAYER_COLORS)]


class Unit3D(Entity):
    """3D unit with health bar and smooth movement."""

    def __init__(self, unit: Unit, terrain_height: float, current_player_id: int, **kwargs):
        self.unit = unit
        self._terrain_height = terrain_height
        self._current_player_id = current_player_id
        self._parts: List[Entity] = []

        x, _, z = hex_to_world_3d(unit.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5

        super().__init__(position=(x, y, z), **kwargs)

        self._player_color = get_player_color(unit.owner_id)
        self._base_color = self._player_color
        self._is_selected = False

        # Build model
        builders = {
            UnitType.WARRIOR: self._build_warrior,
            UnitType.SETTLER: self._build_settler,
            UnitType.SCOUT: self._build_scout,
            UnitType.ARCHER: self._build_archer,
            UnitType.HORSEMAN: self._build_horseman,
        }
        builders.get(unit.unit_type, self._build_warrior)()

        # Selection ring
        self._selection_ring = Entity(
            parent=self, model='circle', color=color.yellow,
            scale=(1.5, 1.5, 1.5), rotation_x=90, position=(0, -0.3, 0),
            visible=False
        )

        # Health bar
        self._health_bg = Entity(
            parent=self, model='cube', color=color.rgb(60, 60, 60),
            position=(0, 1.3, 0), scale=(0.8, 0.08, 0.08), billboard=True
        )
        self._health_bar = Entity(
            parent=self, model='cube', color=color.rgb(50, 200, 50),
            position=(0, 1.3, 0.01), scale=(0.8, 0.06, 0.06), billboard=True
        )

    def _build_warrior(self):
        body = Entity(parent=self, model='cube', color=self._player_color,
                      position=(0, 0.4, 0), scale=(0.4, 0.6, 0.25))
        head = Entity(parent=self, model='sphere', color=color.peach,
                      position=(0, 0.85, 0), scale=0.25)
        helmet = Entity(parent=self, model='sphere', color=color.gray,
                        position=(0, 0.95, 0), scale=(0.28, 0.15, 0.28))
        shield = Entity(parent=self, model='cube', color=self._player_color,
                        position=(-0.35, 0.4, 0), scale=(0.08, 0.5, 0.4))
        sword = Entity(parent=self, model='cube', color=color.light_gray,
                       position=(0.3, 0.55, 0), scale=(0.04, 0.4, 0.04))
        for side in [-0.12, 0.12]:
            Entity(parent=self, model='cube', color=color.brown,
                   position=(side, -0.1, 0), scale=(0.12, 0.4, 0.12))
        self._parts.extend([body, head, helmet, shield, sword])

    def _build_settler(self):
        body = Entity(parent=self, model='cube', color=color.orange,
                      position=(0, 0.35, 0), scale=(0.35, 0.5, 0.25))
        head = Entity(parent=self, model='sphere', color=color.peach,
                      position=(0, 0.75, 0), scale=0.22)
        hat = Entity(parent=self, model=_get_cylinder(), color=color.brown,
                     position=(0, 0.9, 0), scale=(0.25, 0.1, 0.25))
        cart = Entity(parent=self, model='cube', color=color.brown,
                      position=(0, 0.2, -0.5), scale=(0.6, 0.35, 0.5))
        flag = Entity(parent=self, model='cube', color=self._player_color,
                      position=(0.4, 0.85, -0.5), scale=(0.3, 0.2, 0.02))
        self._parts.extend([body, head, hat, cart, flag])

    def _build_scout(self):
        body = Entity(parent=self, model='cube', color=color.lime,
                      position=(0, 0.35, 0), scale=(0.3, 0.45, 0.2))
        head = Entity(parent=self, model='sphere', color=color.peach,
                      position=(0, 0.7, 0), scale=0.2)
        hood = Entity(parent=self, model=_get_cone(), color=color.olive,
                      position=(0, 0.75, -0.05), scale=(0.25, 0.2, 0.25))
        bow = Entity(parent=self, model='cube', color=color.brown,
                     position=(0, 0.4, -0.18), scale=(0.4, 0.03, 0.03), rotation_z=20)
        self._parts.extend([body, head, hood, bow])

    def _build_archer(self):
        body = Entity(parent=self, model='cube', color=self._player_color,
                      position=(0, 0.4, 0), scale=(0.35, 0.55, 0.22))
        head = Entity(parent=self, model='sphere', color=color.peach,
                      position=(0, 0.82, 0), scale=0.23)
        hood = Entity(parent=self, model=_get_cone(), color=color.rgb(60, 80, 60),
                      position=(0, 0.9, 0), scale=(0.28, 0.2, 0.28))
        # Longbow
        bow_body = Entity(parent=self, model='cube', color=color.brown,
                          position=(-0.3, 0.5, 0), scale=(0.04, 0.7, 0.04))
        bow_string = Entity(parent=self, model='cube', color=color.white,
                            position=(-0.28, 0.5, 0), scale=(0.01, 0.6, 0.01))
        # Quiver on back
        quiver = Entity(parent=self, model=_get_cylinder(), color=color.brown,
                        position=(0.1, 0.5, -0.15), scale=(0.08, 0.35, 0.08),
                        rotation_x=15)
        # Arrow tips sticking out
        Entity(parent=self, model=_get_cone(), color=color.light_gray,
               position=(0.1, 0.75, -0.15), scale=(0.03, 0.08, 0.03))
        self._parts.extend([body, head, hood, bow_body, bow_string, quiver])

    def _build_horseman(self):
        # Horse body
        horse = Entity(parent=self, model='cube', color=color.rgb(139, 90, 43),
                       position=(0, 0.25, 0), scale=(0.35, 0.35, 0.7))
        # Horse head
        horse_head = Entity(parent=self, model='cube', color=color.rgb(139, 90, 43),
                            position=(0, 0.4, 0.4), scale=(0.2, 0.25, 0.2),
                            rotation_x=-30)
        # Horse legs
        for lx, lz in [(-0.15, -0.25), (0.15, -0.25), (-0.15, 0.25), (0.15, 0.25)]:
            Entity(parent=self, model='cube', color=color.rgb(120, 75, 35),
                   position=(lx, -0.05, lz), scale=(0.08, 0.3, 0.08))
        # Rider body
        rider = Entity(parent=self, model='cube', color=self._player_color,
                       position=(0, 0.6, 0), scale=(0.3, 0.4, 0.2))
        # Rider head
        rider_head = Entity(parent=self, model='sphere', color=color.peach,
                            position=(0, 0.9, 0), scale=0.2)
        # Lance
        lance = Entity(parent=self, model=_get_cylinder(), color=color.brown,
                       position=(0.25, 0.7, 0.2), scale=(0.03, 0.8, 0.03),
                       rotation_x=-20)
        lance_tip = Entity(parent=self, model=_get_cone(), color=color.light_gray,
                           position=(0.25, 1.15, 0.35), scale=(0.06, 0.15, 0.06))
        self._parts.extend([horse, horse_head, rider, rider_head, lance, lance_tip])

    def update_position(self, terrain_height: float):
        """Update unit position with smooth animation."""
        self._terrain_height = terrain_height
        x, _, z = hex_to_world_3d(self.unit.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5
        target = Vec3(x, y, z)

        # Animate movement smoothly
        if (self.position - target).length() > 0.1:
            self.animate_position(target, duration=0.3)
        else:
            self.position = target

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._selection_ring.visible = selected
        if selected:
            for part in self._parts:
                if part.color == self._player_color:
                    part.color = color.yellow
        else:
            for part in self._parts:
                if part.color == color.yellow:
                    part.color = self._player_color

    def update_display(self):
        """Update health bar and selection state."""
        if self.unit.is_selected != self._is_selected:
            self.set_selected(self.unit.is_selected)

        # Update health bar
        hp_pct = max(0, self.unit.health / 100.0)
        self._health_bar.scale_x = 0.8 * hp_pct

        # Health bar color
        if hp_pct > 0.6:
            self._health_bar.color = color.rgb(50, 200, 50)
        elif hp_pct > 0.3:
            self._health_bar.color = color.rgb(200, 200, 50)
        else:
            self._health_bar.color = color.rgb(200, 50, 50)

        # Hide health bar if full
        self._health_bg.visible = self.unit.health < 100
        self._health_bar.visible = self.unit.health < 100


class City3D(Entity):
    """3D city with buildings scaled by population."""

    def __init__(self, city: City, terrain_height: float, player_color, **kwargs):
        self.city = city
        self._terrain_height = terrain_height
        self._parts: List[Entity] = []

        x, _, z = hex_to_world_3d(city.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5

        if isinstance(player_color, tuple):
            self._player_color = color.rgb(player_color[0], player_color[1], player_color[2])
        else:
            self._player_color = player_color

        super().__init__(position=(x, y, z), **kwargs)

        self._build_city()

        # City name label
        self._name_text = Text(
            text=city.name, parent=self, position=(0, 3, 0),
            origin=(0, 0), scale=20, billboard=True,
            color=color.white, background=True
        )

        # Population badge
        self._pop_bg = Entity(
            parent=self, model='circle', color=self._player_color,
            position=(0, 2.5, 0), scale=0.4, rotation_x=90
        )
        self._pop_text = Text(
            text=str(city.population), parent=self, position=(0, 2.5, 0.01),
            origin=(0, 0), scale=15, billboard=True, color=color.white
        )

        # Capital star
        if city.is_capital:
            Entity(parent=self, model='diamond', color=color.rgb(255, 215, 0),
                   position=(0, 3.5, 0), scale=0.3, billboard=True)

    def _build_city(self):
        pop = self.city.population

        # Town hall
        center = Entity(parent=self, model='cube', color=self._player_color,
                        position=(0, 0.4, 0), scale=(1.2, 0.8, 1.2))
        roof = Entity(parent=self, model=_get_cone(), color=color.brown,
                      position=(0, 1, 0), scale=(1.4, 0.6, 1.4))
        tower = Entity(parent=self, model='cube', color=self._player_color,
                       position=(0, 1.2, 0), scale=(0.3, 0.6, 0.3))
        tower_top = Entity(parent=self, model=_get_cone(), color=color.brown,
                           position=(0, 1.7, 0), scale=(0.4, 0.4, 0.4))
        flag = Entity(parent=self, model='cube', color=self._player_color,
                      position=(0.15, 2.2, 0), scale=(0.25, 0.15, 0.02))
        self._parts.extend([center, roof, tower, tower_top, flag])

        # Houses
        positions = [
            (-1.2, -0.8), (1.2, -0.8), (-1.2, 0.8), (1.2, 0.8),
            (-0.6, -1.4), (0.6, -1.4), (-0.6, 1.4), (0.6, 1.4),
        ]
        for i in range(min(pop, len(positions))):
            hx, hz = positions[i]
            house = Entity(parent=self, model='cube', color=color.white,
                           position=(hx, 0.25, hz), scale=(0.5, 0.5, 0.5))
            h_roof = Entity(parent=self, model=_get_cone(), color=color.orange,
                            position=(hx, 0.65, hz), scale=(0.6, 0.35, 0.6))
            self._parts.extend([house, h_roof])

        if pop >= 3:
            self._add_walls()
        if pop >= 2:
            self._add_farms()

    def _add_walls(self):
        wall_color = color.gray
        walls = [
            (0, 0.2, -2, 3.5, 0.4, 0.15),
            (0, 0.2, 2, 3.5, 0.4, 0.15),
            (-1.75, 0.2, 0, 0.15, 0.4, 4),
            (1.75, 0.2, 0, 0.15, 0.4, 4),
        ]
        for wx, wy, wz, sx, sy, sz in walls:
            wall = Entity(parent=self, model='cube', color=wall_color,
                          position=(wx, wy, wz), scale=(sx, sy, sz))
            self._parts.append(wall)

        for tx, tz in [(-1.75, -2), (1.75, -2), (-1.75, 2), (1.75, 2)]:
            t = Entity(parent=self, model=_get_cylinder(), color=wall_color,
                       position=(tx, 0.35, tz), scale=(0.25, 0.7, 0.25))
            tt = Entity(parent=self, model=_get_cone(), color=color.brown,
                        position=(tx, 0.85, tz), scale=(0.35, 0.3, 0.35))
            self._parts.extend([t, tt])

    def _add_farms(self):
        positions = [(-2.5, -2.5), (2.5, -2.5)]
        for fx, fz in positions[:min(2, self.city.population - 1)]:
            field = Entity(parent=self, model='cube', color=color.lime,
                           position=(fx, 0.01, fz), scale=(1.2, 0.02, 1.2))
            self._parts.append(field)
            for row in range(3):
                crops = Entity(parent=self, model='cube', color=color.yellow,
                               position=(fx, 0.1, fz - 0.4 + row * 0.4),
                               scale=(0.8, 0.15, 0.1))
                self._parts.append(crops)

    def update_display(self):
        self._name_text.text = self.city.name
        self._pop_text.text = str(self.city.population)


class UnitManager3D:
    """Manages all 3D unit and city entities."""

    def __init__(self, game_state, view_3d=None):
        self.game_state = game_state
        self.view_3d = view_3d
        self.unit_entities: Dict[int, Unit3D] = {}
        self.city_entities: Dict[int, City3D] = {}

    def get_terrain_height(self, coord: HexCoord) -> float:
        if self.view_3d:
            return self.view_3d.get_terrain_height(coord)
        tile = self.game_state.game_map.get_tile(coord)
        if tile:
            return TERRAIN_HEIGHTS.get(tile.terrain.value, 0)
        return 0

    def sync_units(self):
        current_player_id = self.game_state.current_player.id if self.game_state.current_player else 0
        current_ids = set(self.game_state.units.keys())
        existing_ids = set(self.unit_entities.keys())

        for unit_id in existing_ids - current_ids:
            self.unit_entities[unit_id].disable()
            del self.unit_entities[unit_id]

        for unit_id in current_ids - existing_ids:
            unit = self.game_state.units[unit_id]
            terrain_height = self.get_terrain_height(unit.position)
            self.unit_entities[unit_id] = Unit3D(unit, terrain_height, current_player_id)

        for unit_id in current_ids & existing_ids:
            unit = self.game_state.units[unit_id]
            entity = self.unit_entities[unit_id]
            terrain_height = self.get_terrain_height(unit.position)
            entity.update_position(terrain_height)
            entity.update_display()

    def sync_cities(self):
        current_ids = set(self.game_state.cities.keys())
        existing_ids = set(self.city_entities.keys())

        for city_id in existing_ids - current_ids:
            self.city_entities[city_id].disable()
            del self.city_entities[city_id]

        for city_id in current_ids - existing_ids:
            city = self.game_state.cities[city_id]
            terrain_height = self.get_terrain_height(city.position)
            player = self.game_state.get_player(city.owner_id)
            if player and player.civilization:
                p_color = player.civilization.primary_color
            else:
                p_color = get_player_color(city.owner_id)
            self.city_entities[city_id] = City3D(city, terrain_height, p_color)

        for city_id in current_ids & existing_ids:
            self.city_entities[city_id].update_display()

    def sync_all(self):
        self.sync_units()
        self.sync_cities()
