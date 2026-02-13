"""
3D unit and city rendering for Ursina.
Uses hex_to_world_3d for proper hex grid positioning.
Units and cities rendered as billboard sprites.
"""

from ursina import Entity, Text, color, Vec3, load_texture, Color

from typing import Dict, List
import sys
import os
import math
import time as _time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.unit import Unit, UnitType
from src.models.city import City
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


# Player colors
PLAYER_COLORS = [
    color.rgb(50, 120, 255),   # Player 1 - Blue
    color.rgb(220, 50, 50),    # Player 2 - Red
    color.rgb(255, 200, 50),   # Player 3 - Gold
    color.rgb(180, 50, 220),   # Player 4 - Purple
]


def get_player_color(owner_id: int):
    return PLAYER_COLORS[owner_id % len(PLAYER_COLORS)]


# Sprite file mapping for each unit type (frame 1, frame 2 for walk animation)
UNIT_SPRITES = {
    UnitType.WARRIOR: ('assets/textures/units/warrior_1.png', 'assets/textures/units/warrior_2.png'),
    UnitType.SETTLER: ('assets/textures/units/settler_1.png', 'assets/textures/units/settler_2.png'),
    UnitType.SCOUT: ('assets/textures/units/scout_1.png', 'assets/textures/units/scout_2.png'),
    UnitType.ARCHER: ('assets/textures/units/archer_1.png', 'assets/textures/units/archer_2.png'),
    UnitType.HORSEMAN: ('assets/textures/units/horseman_1.png', 'assets/textures/units/horseman_2.png'),
}

# City sprite mapping by population tier
CITY_SPRITES = {
    'village': 'assets/textures/cities/city_village.png',  # pop 1-2
    'town': 'assets/textures/cities/city_town.png',        # pop 3-4
    'city': 'assets/textures/cities/city_city.png',        # pop 5+
}


class Unit3D(Entity):
    """3D unit rendered as a billboard sprite with health bar and smooth movement."""

    # Class-level texture cache to avoid loading the same sprite multiple times
    _sprite_cache = {}

    @classmethod
    def _get_sprite(cls, path):
        if path not in cls._sprite_cache:
            cls._sprite_cache[path] = load_texture(path)
        return cls._sprite_cache[path]

    def __init__(self, unit: Unit, terrain_height: float, current_player_id: int, civ_id: str = 'rome', **kwargs):
        self.unit = unit
        self._terrain_height = terrain_height
        self._current_player_id = current_player_id
        self._civ_id = civ_id

        x, _, z = hex_to_world_3d(unit.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5

        super().__init__(position=(x, y, z), **kwargs)

        self._move_target = Vec3(x, y, z)
        self._is_moving = False
        self._anim_frame = 0
        self._anim_timer = 0.0

        self._player_color = get_player_color(unit.owner_id)
        self._is_selected = False

        # Load sprite textures
        sprites = UNIT_SPRITES.get(unit.unit_type, UNIT_SPRITES[UnitType.WARRIOR])
        self._sprite_tex_1 = self._get_sprite(sprites[0])
        self._sprite_tex_2 = self._get_sprite(sprites[1])

        # Create billboard sprite quad
        self._sprite = Entity(
            parent=self,
            model='quad',
            texture=self._sprite_tex_1,
            scale=(6.75, 6.75),
            billboard=True,
            position=(0, 3.0, 0),
        )
        self._sprite.setLightOff()
        # Enable transparency for the sprite background
        self._sprite.set_transparency(True)

        # Player color base disk on ground
        self._base_disk = Entity(
            parent=self, model='circle',
            scale=(1.5, 1.5, 1.5), rotation_x=90, position=(0, -0.4, 0)
        )
        _color_entity(self._base_disk, self._player_color)
        self._base_disk.setLightOff()

        # Selection ring
        self._selection_ring = Entity(
            parent=self, model='circle',
            scale=(1.8, 1.8, 1.8), rotation_x=90, position=(0, -0.35, 0),
            visible=False
        )
        _color_entity(self._selection_ring, color.yellow)
        self._selection_ring.setLightOff()

        # Health bar
        self._health_bg = Entity(
            parent=self, model='cube',
            position=(0, 3.2, 0), scale=(1.2, 0.1, 0.08), billboard=True
        )
        _color_entity(self._health_bg, color.rgb(60, 60, 60))
        self._health_bg.setLightOff()
        self._health_bar = Entity(
            parent=self, model='cube',
            position=(0, 3.2, 0.01), scale=(1.2, 0.08, 0.06), billboard=True
        )
        _color_entity(self._health_bar, color.rgb(50, 200, 50))
        self._health_bar.setLightOff()

        # Initialize last_time for animation timing
        self._last_time = _time.time()

    def update_position(self, terrain_height: float):
        """Update unit position with smooth animation."""
        self._terrain_height = terrain_height
        x, _, z = hex_to_world_3d(self.unit.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5
        target = Vec3(x, y, z)

        # Only start animation when the target hex changes (avoid restarting every frame)
        if (self._move_target - target).length() > 0.05:
            self._move_target = target
            self._is_moving = True
            self._sprite.texture = self._sprite_tex_2  # Show walking frame immediately
            self.animate_position(target, duration=0.3, curve=lambda t: t)
        elif self._is_moving:
            # Check if we've arrived
            if (self.position - target).length() < 0.05:
                self.position = target
                self._is_moving = False

    def set_selected(self, selected: bool):
        self._is_selected = selected
        self._selection_ring.visible = selected
        if selected:
            self._sprite.color = Color(1.2, 1.2, 1.0, 1)  # Slight bright tint
        else:
            self._sprite.color = Color(1, 1, 1, 1)  # Normal

    def update_display(self):
        """Update health bar, selection, and walk animation."""
        if self.unit.is_selected != self._is_selected:
            self.set_selected(self.unit.is_selected)

        # Health bar
        hp_pct = max(0, self.unit.health / 100.0)
        self._health_bar.scale_x = 1.2 * hp_pct
        if hp_pct > 0.6:
            _color_entity(self._health_bar, color.rgb(50, 200, 50))
        elif hp_pct > 0.3:
            _color_entity(self._health_bar, color.rgb(200, 200, 50))
        else:
            _color_entity(self._health_bar, color.rgb(200, 50, 50))
        self._health_bg.visible = self.unit.health < 100
        self._health_bar.visible = self.unit.health < 100

        # Walk animation — cycle frames when moving
        now = _time.time()
        if self._is_moving:
            self._anim_timer += now - self._last_time
            if self._anim_timer > 0.18:  # Switch frame every 0.18s
                self._anim_frame = 1 - self._anim_frame  # Toggle 0/1
                self._sprite.texture = self._sprite_tex_2 if self._anim_frame else self._sprite_tex_1
                self._anim_timer = 0.0
        else:
            # Idle — always show frame 1, subtle bob
            self._sprite.texture = self._sprite_tex_1
            self._anim_frame = 0
            self._anim_timer = 0.0
            bob = math.sin(now * 2.0 + self.unit.id * 1.7) * 0.04
            self.y = self._terrain_height + 0.5 + bob

        self._last_time = now


class City3D(Entity):
    """City rendered as a billboard sprite that upgrades with population."""

    # Class-level texture cache
    _sprite_cache = {}

    @classmethod
    def _get_sprite(cls, path):
        if path not in cls._sprite_cache:
            cls._sprite_cache[path] = load_texture(path)
        return cls._sprite_cache[path]

    @staticmethod
    def _get_tier(population):
        if population >= 5:
            return 'city'
        elif population >= 3:
            return 'town'
        else:
            return 'village'

    def __init__(self, city: City, terrain_height: float, player_color, **kwargs):
        self.city = city
        self._terrain_height = terrain_height

        if isinstance(player_color, tuple):
            self._player_color = color.rgb(player_color[0], player_color[1], player_color[2])
        else:
            self._player_color = player_color

        x, _, z = hex_to_world_3d(city.position, HEX_3D_SIZE, 0)
        y = terrain_height + 0.5

        super().__init__(position=(x, y, z), **kwargs)

        # Load all tier textures
        self._tier_textures = {
            tier: self._get_sprite(path) for tier, path in CITY_SPRITES.items()
        }
        self._current_tier = self._get_tier(city.population)

        # Billboard sprite
        self._sprite = Entity(
            parent=self,
            model='quad',
            texture=self._tier_textures[self._current_tier],
            scale=(8.0, 8.0),
            billboard=True,
            position=(0, 3.5, 0),
        )
        self._sprite.setLightOff()
        self._sprite.set_transparency(True)

        # Player color base disk on ground
        self._base_disk = Entity(
            parent=self, model='circle',
            scale=(2.5, 2.5, 2.5), rotation_x=90, position=(0, -0.4, 0)
        )
        _color_entity(self._base_disk, self._player_color)
        self._base_disk.setLightOff()

        # City name label
        self._name_text = Text(
            text=city.name, parent=self, position=(0, 7.5, 0),
            origin=(0, 0), scale=20, billboard=True,
            color=color.white, background=True
        )

        # Population badge
        self._pop_bg = Entity(
            parent=self, model='circle',
            position=(0, 6.8, 0), scale=0.5, billboard=True
        )
        _color_entity(self._pop_bg, self._player_color)
        self._pop_bg.setLightOff()
        self._pop_text = Text(
            text=str(city.population), parent=self, position=(0, 6.8, 0.01),
            origin=(0, 0), scale=15, billboard=True, color=color.white
        )

        # Capital star
        if city.is_capital:
            self._capital_star = Entity(
                parent=self, model='diamond',
                position=(0, 8.2, 0), scale=0.35, billboard=True
            )
            _color_entity(self._capital_star, color.rgb(255, 215, 0))
            self._capital_star.setLightOff()

    def update_display(self):
        self._name_text.text = self.city.name
        self._pop_text.text = str(self.city.population)

        # Switch sprite tier if population changed
        new_tier = self._get_tier(self.city.population)
        if new_tier != self._current_tier:
            self._current_tier = new_tier
            self._sprite.texture = self._tier_textures[new_tier]


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
            player = self.game_state.get_player(unit.owner_id)
            civ_id = player.civilization.id if player and player.civilization else 'rome'
            self.unit_entities[unit_id] = Unit3D(unit, terrain_height, current_player_id, civ_id=civ_id)

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
