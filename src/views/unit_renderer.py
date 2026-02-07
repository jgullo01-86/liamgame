"""
3D unit and city rendering for Ursina.
Enhanced with detailed low-poly 3D models.
"""

from ursina import Entity, Text, color, Vec3
from typing import Dict, Optional, List
import sys
import os
import random
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.unit import Unit, UnitType
from src.models.city import City
from src.utils.hex_utils import HexCoord, hex_to_world_3d
from config import HEX_3D_SIZE, TERRAIN_HEIGHTS, COLORS


# Player colors for civilizations
PLAYER_COLORS = [
    color.blue,      # Player 1
    color.red,       # Player 2 / AI
    color.yellow,    # Player 3
    color.magenta,   # Player 4
]


def get_player_color(owner_id: int):
    """Get player color by ID."""
    return PLAYER_COLORS[owner_id % len(PLAYER_COLORS)]


class Unit3D(Entity):
    """3D representation of a game unit with detailed model."""

    def __init__(self, unit: Unit, terrain_height: float, current_player_id: int, tile_size: float = 5, **kwargs):
        self.unit = unit
        self._terrain_height = terrain_height
        self._current_player_id = current_player_id
        self._tile_size = tile_size
        self._parts: List[Entity] = []

        # Get world position using simple grid (matching main.py)
        x = unit.position.q * tile_size
        z = unit.position.r * tile_size
        y = terrain_height + 0.5

        # Create empty parent entity
        super().__init__(
            position=(x, y, z),
            **kwargs
        )

        # Get player color
        self._player_color = get_player_color(unit.owner_id)
        self._base_color = self._player_color
        self._is_selected = False

        # Build the unit model based on type
        if unit.unit_type == UnitType.WARRIOR:
            self._build_warrior()
        elif unit.unit_type == UnitType.SETTLER:
            self._build_settler()
        else:  # Scout
            self._build_scout()

        # Selection ring (initially hidden)
        self._selection_ring = Entity(
            parent=self,
            model='circle',
            color=color.yellow,
            scale=(1.5, 1.5, 1.5),
            rotation_x=90,
            position=(0, -0.3, 0),
            visible=False
        )

    def _build_warrior(self):
        """Build a warrior unit - soldier with shield and sword."""
        # Body (torso)
        body = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(0, 0.4, 0),
            scale=(0.4, 0.6, 0.25)
        )
        self._parts.append(body)

        # Head
        head = Entity(
            parent=self,
            model='sphere',
            color=color.peach,
            position=(0, 0.85, 0),
            scale=(0.25, 0.25, 0.25)
        )
        self._parts.append(head)

        # Helmet
        helmet = Entity(
            parent=self,
            model='sphere',
            color=color.gray,
            position=(0, 0.95, 0),
            scale=(0.28, 0.15, 0.28)
        )
        self._parts.append(helmet)

        # Shield (on left arm)
        shield = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(-0.35, 0.4, 0),
            scale=(0.08, 0.5, 0.4)
        )
        self._parts.append(shield)

        # Shield emblem (lighter color)
        emblem = Entity(
            parent=self,
            model='cube',
            color=color.white,
            position=(-0.38, 0.4, 0),
            scale=(0.02, 0.2, 0.2)
        )
        self._parts.append(emblem)

        # Sword (on right side)
        sword_handle = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            position=(0.3, 0.3, 0),
            scale=(0.06, 0.15, 0.06)
        )
        self._parts.append(sword_handle)

        sword_blade = Entity(
            parent=self,
            model='cube',
            color=color.light_gray,
            position=(0.3, 0.55, 0),
            scale=(0.04, 0.4, 0.04)
        )
        self._parts.append(sword_blade)

        # Legs
        for side in [-0.12, 0.12]:
            leg = Entity(
                parent=self,
                model='cube',
                color=color.brown,
                position=(side, -0.1, 0),
                scale=(0.12, 0.4, 0.12)
            )
            self._parts.append(leg)

    def _build_settler(self):
        """Build a settler unit - civilian with wagon/cart."""
        # Body
        body = Entity(
            parent=self,
            model='cube',
            color=color.orange,
            position=(0, 0.35, 0),
            scale=(0.35, 0.5, 0.25)
        )
        self._parts.append(body)

        # Head
        head = Entity(
            parent=self,
            model='sphere',
            color=color.peach,
            position=(0, 0.75, 0),
            scale=(0.22, 0.22, 0.22)
        )
        self._parts.append(head)

        # Hat
        hat = Entity(
            parent=self,
            model='cylinder',
            color=color.brown,
            position=(0, 0.9, 0),
            scale=(0.25, 0.1, 0.25)
        )
        self._parts.append(hat)

        # Cart behind settler
        cart_body = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            position=(0, 0.2, -0.5),
            scale=(0.6, 0.35, 0.5)
        )
        self._parts.append(cart_body)

        # Cart wheels
        for wx in [-0.35, 0.35]:
            wheel = Entity(
                parent=self,
                model='cylinder',
                color=color.dark_gray,
                position=(wx, 0.05, -0.5),
                scale=(0.15, 0.05, 0.15),
                rotation_z=90
            )
            self._parts.append(wheel)

        # Supplies on cart
        for i in range(3):
            supply = Entity(
                parent=self,
                model='cube',
                color=color.white if i % 2 == 0 else color.yellow,
                position=(random.uniform(-0.15, 0.15), 0.45, -0.5 + random.uniform(-0.1, 0.1)),
                scale=(0.15, 0.15, 0.15)
            )
            self._parts.append(supply)

        # Flag with player color
        flag_pole = Entity(
            parent=self,
            model='cylinder',
            color=color.brown,
            position=(0.25, 0.6, -0.5),
            scale=(0.03, 0.6, 0.03)
        )
        self._parts.append(flag_pole)

        flag = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(0.4, 0.85, -0.5),
            scale=(0.3, 0.2, 0.02)
        )
        self._parts.append(flag)

    def _build_scout(self):
        """Build a scout unit - fast moving explorer."""
        # Body (leaner)
        body = Entity(
            parent=self,
            model='cube',
            color=color.lime,
            position=(0, 0.35, 0),
            scale=(0.3, 0.45, 0.2)
        )
        self._parts.append(body)

        # Head
        head = Entity(
            parent=self,
            model='sphere',
            color=color.peach,
            position=(0, 0.7, 0),
            scale=(0.2, 0.2, 0.2)
        )
        self._parts.append(head)

        # Hood/cloak
        hood = Entity(
            parent=self,
            model='cone',
            color=color.olive,
            position=(0, 0.75, -0.05),
            scale=(0.25, 0.2, 0.25)
        )
        self._parts.append(hood)

        # Bow on back
        bow = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            position=(0, 0.4, -0.18),
            scale=(0.4, 0.03, 0.03),
            rotation_z=20
        )
        self._parts.append(bow)

        # Legs (running pose)
        leg1 = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            position=(-0.08, -0.05, 0.1),
            scale=(0.1, 0.35, 0.1),
            rotation_x=-20
        )
        self._parts.append(leg1)

        leg2 = Entity(
            parent=self,
            model='cube',
            color=color.brown,
            position=(0.08, -0.05, -0.1),
            scale=(0.1, 0.35, 0.1),
            rotation_x=20
        )
        self._parts.append(leg2)

    def update_position(self, terrain_height: float):
        """Update unit position when it moves."""
        self._terrain_height = terrain_height
        x = self.unit.position.q * self._tile_size
        z = self.unit.position.r * self._tile_size
        y = terrain_height + 0.5
        self.position = Vec3(x, y, z)

    def set_selected(self, selected: bool):
        """Set selection state."""
        self._is_selected = selected
        self._selection_ring.visible = selected

        # Highlight all parts when selected
        if selected:
            for part in self._parts:
                if part.color == self._player_color:
                    part.color = color.yellow
        else:
            for part in self._parts:
                if part.color == color.yellow:
                    part.color = self._player_color

    def update_display(self):
        """Update display based on unit state."""
        if self.unit.is_selected != self._is_selected:
            self.set_selected(self.unit.is_selected)


class City3D(Entity):
    """3D representation of a city with buildings."""

    def __init__(self, city: City, terrain_height: float, player_color, tile_size: float = 5, **kwargs):
        self.city = city
        self._terrain_height = terrain_height
        self._tile_size = tile_size
        self._parts: List[Entity] = []

        # Get world position using simple grid
        x = city.position.q * tile_size
        z = city.position.r * tile_size
        y = terrain_height + 0.5

        # Store player color
        if isinstance(player_color, tuple):
            self._player_color = color.rgb(player_color[0], player_color[1], player_color[2])
        else:
            self._player_color = player_color

        super().__init__(
            position=(x, y, z),
            **kwargs
        )

        # Build city based on population
        self._build_city()

        # City name label (billboard text)
        self._name_text = Text(
            text=city.name,
            parent=self,
            position=(0, 3, 0),
            origin=(0, 0),
            scale=20,
            billboard=True,
            color=color.white,
            background=True
        )

        # Population badge
        self._pop_bg = Entity(
            parent=self,
            model='circle',
            color=self._player_color,
            position=(0, 2.5, 0),
            scale=(0.4, 0.4, 0.4),
            rotation_x=90
        )

        self._pop_text = Text(
            text=str(city.population),
            parent=self,
            position=(0, 2.5, 0.01),
            origin=(0, 0),
            scale=15,
            billboard=True,
            color=color.white
        )

    def _build_city(self):
        """Build city structures based on population."""
        pop = self.city.population

        # City center / town hall (always present)
        center = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(0, 0.4, 0),
            scale=(1.2, 0.8, 1.2)
        )
        self._parts.append(center)

        # Town hall roof
        roof = Entity(
            parent=self,
            model='cone',
            color=color.brown,
            position=(0, 1, 0),
            scale=(1.4, 0.6, 1.4)
        )
        self._parts.append(roof)

        # Tower on town hall
        tower = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(0, 1.2, 0),
            scale=(0.3, 0.6, 0.3)
        )
        self._parts.append(tower)

        # Tower top
        tower_top = Entity(
            parent=self,
            model='cone',
            color=color.brown,
            position=(0, 1.7, 0),
            scale=(0.4, 0.4, 0.4)
        )
        self._parts.append(tower_top)

        # Flag on tower
        flag_pole = Entity(
            parent=self,
            model='cylinder',
            color=color.brown,
            position=(0, 2.1, 0),
            scale=(0.03, 0.4, 0.03)
        )
        self._parts.append(flag_pole)

        flag = Entity(
            parent=self,
            model='cube',
            color=self._player_color,
            position=(0.15, 2.2, 0),
            scale=(0.25, 0.15, 0.02)
        )
        self._parts.append(flag)

        # Add houses based on population
        house_positions = [
            (-1.2, 0, -0.8), (1.2, 0, -0.8),
            (-1.2, 0, 0.8), (1.2, 0, 0.8),
            (-0.6, 0, -1.4), (0.6, 0, -1.4),
            (-0.6, 0, 1.4), (0.6, 0, 1.4),
        ]

        num_houses = min(pop, len(house_positions))
        for i in range(num_houses):
            hx, hy, hz = house_positions[i]
            self._add_house(hx, hz)

        # Add walls if population >= 3
        if pop >= 3:
            self._add_walls()

        # Add farms outside if population >= 2
        if pop >= 2:
            self._add_farms()

    def _add_house(self, x: float, z: float):
        """Add a small house at the given position."""
        # House body
        house = Entity(
            parent=self,
            model='cube',
            color=color.white,
            position=(x, 0.25, z),
            scale=(0.5, 0.5, 0.5)
        )
        self._parts.append(house)

        # House roof
        roof = Entity(
            parent=self,
            model='cone',
            color=color.orange,
            position=(x, 0.65, z),
            scale=(0.6, 0.35, 0.6)
        )
        self._parts.append(roof)

        # Chimney (some houses)
        if random.random() > 0.5:
            chimney = Entity(
                parent=self,
                model='cube',
                color=color.brown,
                position=(x + 0.15, 0.75, z),
                scale=(0.1, 0.25, 0.1)
            )
            self._parts.append(chimney)

    def _add_walls(self):
        """Add city walls."""
        wall_color = color.gray

        # Four wall segments
        walls = [
            (0, 0.2, -2, 3.5, 0.4, 0.15),   # North
            (0, 0.2, 2, 3.5, 0.4, 0.15),    # South
            (-1.75, 0.2, 0, 0.15, 0.4, 4),  # West
            (1.75, 0.2, 0, 0.15, 0.4, 4),   # East
        ]

        for wx, wy, wz, sx, sy, sz in walls:
            wall = Entity(
                parent=self,
                model='cube',
                color=wall_color,
                position=(wx, wy, wz),
                scale=(sx, sy, sz)
            )
            self._parts.append(wall)

        # Corner towers
        for tx, tz in [(-1.75, -2), (1.75, -2), (-1.75, 2), (1.75, 2)]:
            tower = Entity(
                parent=self,
                model='cylinder',
                color=wall_color,
                position=(tx, 0.35, tz),
                scale=(0.25, 0.7, 0.25)
            )
            self._parts.append(tower)

            tower_top = Entity(
                parent=self,
                model='cone',
                color=color.brown,
                position=(tx, 0.85, tz),
                scale=(0.35, 0.3, 0.35)
            )
            self._parts.append(tower_top)

    def _add_farms(self):
        """Add farm fields outside the city."""
        farm_positions = [(-2.5, -2.5), (2.5, -2.5), (-2.5, 2.5), (2.5, 2.5)]

        for fx, fz in farm_positions[:min(2, self.city.population - 1)]:
            # Farm field (flat green square)
            field = Entity(
                parent=self,
                model='cube',
                color=color.lime,
                position=(fx, 0.01, fz),
                scale=(1.2, 0.02, 1.2)
            )
            self._parts.append(field)

            # Crop rows
            for row in range(3):
                crops = Entity(
                    parent=self,
                    model='cube',
                    color=color.yellow,
                    position=(fx, 0.1, fz - 0.4 + row * 0.4),
                    scale=(0.8, 0.15, 0.1)
                )
                self._parts.append(crops)

    def update_display(self):
        """Update display based on city state."""
        self._name_text.text = self.city.name
        self._pop_text.text = str(self.city.population)


class UnitManager3D:
    """Manages all 3D unit and city entities."""

    def __init__(self, game_state, view_3d=None, tile_size: float = 5):
        self.game_state = game_state
        self.view_3d = view_3d
        self.tile_size = tile_size
        self.unit_entities: Dict[int, Unit3D] = {}
        self.city_entities: Dict[int, City3D] = {}

        # Terrain height lookup (use simple heights based on terrain type)
        self.terrain_heights = {
            'ocean': -1,
            'coast': -0.3,
            'grassland': 0,
            'plains': 0,
            'desert': 0,
            'forest': 0,
            'hills': 1,
            'mountains': 2,
        }

    def get_terrain_height(self, coord: HexCoord) -> float:
        """Get terrain height at a coordinate."""
        if self.view_3d:
            return self.view_3d.get_terrain_height(coord)

        # Fallback: look up from game map
        tile = self.game_state.game_map.get_tile(coord)
        if tile:
            return self.terrain_heights.get(tile.terrain.value, 0)
        return 0

    def sync_units(self):
        """Synchronize 3D entities with game state units."""
        current_player_id = self.game_state.current_player.id if self.game_state.current_player else 0

        # Get current unit IDs
        current_ids = set(self.game_state.units.keys())
        existing_ids = set(self.unit_entities.keys())

        # Remove deleted units
        for unit_id in existing_ids - current_ids:
            self.unit_entities[unit_id].disable()
            del self.unit_entities[unit_id]

        # Add new units
        for unit_id in current_ids - existing_ids:
            unit = self.game_state.units[unit_id]
            terrain_height = self.get_terrain_height(unit.position)
            self.unit_entities[unit_id] = Unit3D(
                unit, terrain_height, current_player_id, self.tile_size
            )

        # Update existing units
        for unit_id in current_ids & existing_ids:
            unit = self.game_state.units[unit_id]
            entity = self.unit_entities[unit_id]
            terrain_height = self.get_terrain_height(unit.position)
            entity.update_position(terrain_height)
            entity.update_display()

    def sync_cities(self):
        """Synchronize 3D entities with game state cities."""
        current_ids = set(self.game_state.cities.keys())
        existing_ids = set(self.city_entities.keys())

        # Remove deleted cities
        for city_id in existing_ids - current_ids:
            self.city_entities[city_id].disable()
            del self.city_entities[city_id]

        # Add new cities
        for city_id in current_ids - existing_ids:
            city = self.game_state.cities[city_id]
            terrain_height = self.get_terrain_height(city.position)

            # Get player color
            player = self.game_state.get_player(city.owner_id)
            if player and player.civilization:
                player_color = player.civilization.colors[0]
            else:
                player_color = get_player_color(city.owner_id)

            self.city_entities[city_id] = City3D(
                city, terrain_height, player_color, self.tile_size
            )

        # Update existing cities
        for city_id in current_ids & existing_ids:
            self.city_entities[city_id].update_display()

    def sync_all(self):
        """Sync both units and cities."""
        self.sync_units()
        self.sync_cities()
