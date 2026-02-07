#!/usr/bin/env python3
"""
Civilization Deluxe - A 4X Strategy Game (3D Ursina Version)
Main entry point
"""

import sys
import os
import random

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ursina import Ursina, Entity, window, color, DirectionalLight, AmbientLight, camera, Vec3, load_texture

from src.models.game_state import GameState, GamePhase
from src.views.game_view_3d import GameView3D
from src.views.unit_renderer import UnitManager3D
from src.views.ui_overlay import UIOverlay
from src.utils.hex_utils import hex_to_world_3d, HexCoord
from config import GAME_TITLE, SCREEN_WIDTH, SCREEN_HEIGHT, HEX_3D_SIZE, MAP_WIDTH, MAP_HEIGHT


class GameApp:
    """Main game application."""

    def __init__(self):
        # Create Ursina app
        self.app = Ursina(
            title=GAME_TITLE,
            development_mode=False,
            borderless=False,
        )
        window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        window.color = color.light_gray

        # Set up lighting
        self._setup_lighting()

        # Initialize game state
        self.game_state = GameState()
        self.game_state.initialize_game()

        # Create hex tiles directly (bypassing GameView3D for now)
        self.view = None
        self.hex_tiles = {}

        # Load textures
        print("Loading textures...")
        textures = {
            'grass': load_texture('assets/textures/grass.png'),
            'water': load_texture('assets/textures/water.png'),
            'sand': load_texture('assets/textures/sand.png'),
            'rock': load_texture('assets/textures/rock.png'),
            'snow': load_texture('assets/textures/snow.png'),
            'dirt': load_texture('assets/textures/dirt.png'),
        }

        # Map terrain types to textures and colors
        terrain_textures = {
            'grassland': textures['grass'],
            'plains': textures['sand'],
            'desert': textures['sand'],
            'hills': textures['dirt'],
            'mountains': textures['rock'],
            'forest': textures['grass'],
            'coast': textures['sand'],
            'ocean': textures['water'],
        }

        # Fallback colors (tint the textures)
        terrain_colors = {
            'grassland': color.white,
            'plains': color.white,
            'desert': color.orange,
            'hills': color.white,
            'mountains': color.white,
            'forest': color.white,
            'coast': color.azure,
            'ocean': color.white,
        }

        # Terrain base heights
        terrain_heights = {
            'ocean': -1,
            'coast': -0.3,
            'grassland': 0,
            'plains': 0,
            'desert': 0,
            'forest': 0,
            'hills': 1,
            'mountains': 2,
        }

        # Create tiles using simple grid layout
        print(f"Creating map tiles with textures and 3D features...")
        tile_count = 0
        tile_size = 5

        for tile in self.game_state.game_map:
            coord = tile.coord
            terrain_type = tile.terrain.value

            # Simple grid positioning
            x = coord.q * tile_size
            z = coord.r * tile_size

            tile_texture = terrain_textures.get(terrain_type)
            tile_color = terrain_colors.get(terrain_type, color.white)
            height = terrain_heights.get(terrain_type, 0)

            # Base tile with texture
            tile_entity = Entity(
                model='cube',
                texture=tile_texture,
                color=tile_color,
                position=(x, height / 2, z),
                scale=(tile_size * 0.95, 1, tile_size * 0.95)
            )
            self.hex_tiles[coord] = tile_entity

            # Add 3D features based on terrain type
            if terrain_type == 'mountains':
                # Add a snow-capped mountain peak (main peak)
                Entity(
                    model='cone',
                    texture=textures['snow'],
                    position=(x, height + 2.5, z),
                    scale=(tile_size * 0.5, 5, tile_size * 0.5)
                )
                # Add rocky base
                Entity(
                    model='cone',
                    texture=textures['rock'],
                    position=(x, height + 0.5, z),
                    scale=(tile_size * 0.8, 2.5, tile_size * 0.8)
                )
                # Add scattered rocks around the mountain
                for i in range(4):
                    rx = x + random.uniform(-1.5, 1.5)
                    rz = z + random.uniform(-1.5, 1.5)
                    rock_scale = random.uniform(0.3, 0.6)
                    Entity(
                        model='sphere',
                        texture=textures['rock'],
                        position=(rx, height + 0.3, rz),
                        scale=(rock_scale, rock_scale * 0.7, rock_scale)
                    )

            elif terrain_type == 'hills':
                # Add rounded hill with dirt texture
                Entity(
                    model='sphere',
                    texture=textures['dirt'],
                    position=(x, height + 0.5, z),
                    scale=(tile_size * 0.7, 1.5, tile_size * 0.7)
                )
                # Add some rocks on hills
                for i in range(2):
                    rx = x + random.uniform(-1, 1)
                    rz = z + random.uniform(-1, 1)
                    Entity(
                        model='sphere',
                        texture=textures['rock'],
                        position=(rx, height + 0.8, rz),
                        scale=(0.3, 0.25, 0.3)
                    )

            elif terrain_type == 'forest':
                # Add trees with variation
                tree_positions = [
                    (random.uniform(-1.2, -0.8), random.uniform(-1.2, -0.8)),
                    (random.uniform(0.8, 1.2), random.uniform(-1.2, -0.8)),
                    (random.uniform(-1.2, -0.8), random.uniform(0.8, 1.2)),
                    (random.uniform(0.8, 1.2), random.uniform(0.8, 1.2)),
                    (random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)),
                ]
                for dx, dz in tree_positions:
                    tree_height = random.uniform(2.0, 3.0)
                    trunk_height = random.uniform(0.6, 1.0)
                    # Tree trunk
                    Entity(
                        model='cylinder',
                        color=color.brown,
                        position=(x + dx, height + trunk_height / 2, z + dz),
                        scale=(0.15, trunk_height, 0.15)
                    )
                    # Tree foliage (multiple layers for fuller look)
                    Entity(
                        model='cone',
                        color=color.green,
                        position=(x + dx, height + trunk_height + tree_height * 0.5, z + dz),
                        scale=(0.8, tree_height, 0.8)
                    )
                    # Second layer of foliage
                    Entity(
                        model='cone',
                        color=color.lime,
                        position=(x + dx, height + trunk_height + tree_height * 0.3, z + dz),
                        scale=(1.0, tree_height * 0.7, 1.0)
                    )

            elif terrain_type == 'grassland':
                # Add grass tufts (small vertical planes)
                for i in range(6):
                    gx = x + random.uniform(-1.8, 1.8)
                    gz = z + random.uniform(-1.8, 1.8)
                    grass_height = random.uniform(0.2, 0.4)
                    # Simple grass tuft using thin cube
                    Entity(
                        model='cube',
                        color=color.lime,
                        position=(gx, height + grass_height / 2 + 0.5, gz),
                        scale=(0.05, grass_height, 0.15),
                        rotation=(0, random.uniform(0, 360), 0)
                    )

            elif terrain_type == 'desert':
                # Add occasional cacti and rocks
                if random.random() < 0.3:  # 30% chance of cactus
                    cx = x + random.uniform(-1, 1)
                    cz = z + random.uniform(-1, 1)
                    cactus_height = random.uniform(0.8, 1.5)
                    # Main cactus body
                    Entity(
                        model='cylinder',
                        color=color.green,
                        position=(cx, height + cactus_height / 2 + 0.5, cz),
                        scale=(0.2, cactus_height, 0.2)
                    )
                    # Cactus arm
                    if random.random() < 0.5:
                        Entity(
                            model='cylinder',
                            color=color.green,
                            position=(cx + 0.3, height + cactus_height * 0.6 + 0.5, cz),
                            scale=(0.12, 0.4, 0.12)
                        )
                # Add desert rocks
                if random.random() < 0.4:
                    rx = x + random.uniform(-1.5, 1.5)
                    rz = z + random.uniform(-1.5, 1.5)
                    Entity(
                        model='sphere',
                        texture=textures['sand'],
                        position=(rx, height + 0.6, rz),
                        scale=(random.uniform(0.2, 0.4), 0.15, random.uniform(0.2, 0.4))
                    )

            elif terrain_type == 'coast':
                # Add beach props - shells and driftwood
                if random.random() < 0.3:
                    sx = x + random.uniform(-1.5, 1.5)
                    sz = z + random.uniform(-1.5, 1.5)
                    Entity(
                        model='sphere',
                        color=color.white,
                        position=(sx, height + 0.55, sz),
                        scale=(0.1, 0.05, 0.1)
                    )

            tile_count += 1

        print(f"Created {tile_count} tiles with textures")

        # Calculate map center (q=0..39, so center is q=20, r varies)
        # Map spans roughly x: 0-195, z: -50 to 100
        map_center_x = 20 * tile_size  # q=20 -> x=100
        map_center_z = 10 * tile_size  # roughly middle z

        # Camera setup - start centered on map, zoomed out to see most of it
        camera.position = Vec3(map_center_x, 150, map_center_z - 80)
        camera.rotation_x = 50
        camera.fov = 60
        print(f"Camera centered on map at ({map_center_x}, 150, {map_center_z - 80})")

        # Create unit manager for 3D units and cities
        self.unit_manager = UnitManager3D(self.game_state, view_3d=None, tile_size=tile_size)
        self.ui = UIOverlay(self.game_state)

        # Set up callbacks
        self.ui.on_end_turn = self._handle_end_turn
        self.ui.on_found_city = self._handle_found_city

        # Initial unit sync - creates 3D models for starting units
        self.unit_manager.sync_all()
        print(f"Created {len(self.unit_manager.unit_entities)} unit(s) and {len(self.unit_manager.city_entities)} city/cities")

        # Create controller entity for update/input
        self.controller = Entity()
        self.controller.update = self.update
        self.controller.input = self.input

    def _setup_lighting(self):
        """Set up scene lighting."""
        # Ambient light
        AmbientLight(color=color.white)
        # Sun light from above-right
        sun = DirectionalLight()
        sun.look_at(Vec3(-1, -2, -1))

    def _center_on_start(self):
        """Center camera on starting unit."""
        units = self.game_state.get_current_player_units()
        if units:
            x, y, z = hex_to_world_3d(units[0].position, HEX_3D_SIZE, 0)
            print(f"Starting unit at hex {units[0].position}, world pos ({x:.1f}, {y:.1f}, {z:.1f})")

    def update(self):
        """Update game each frame."""
        from ursina import held_keys, time

        # Camera movement with WASD
        speed = 50 * time.dt
        if held_keys['w'] or held_keys['up arrow']:
            camera.position += Vec3(0, 0, speed)
        if held_keys['s'] or held_keys['down arrow']:
            camera.position += Vec3(0, 0, -speed)
        if held_keys['a'] or held_keys['left arrow']:
            camera.position += Vec3(-speed, 0, 0)
        if held_keys['d'] or held_keys['right arrow']:
            camera.position += Vec3(speed, 0, 0)

        # Zoom with Q/E keys
        if held_keys['q']:
            camera.y = max(10, camera.y - 50 * time.dt)
        if held_keys['e']:
            camera.y = min(400, camera.y + 50 * time.dt)

        if self.view:
            self.view.update()
        if self.unit_manager:
            self.unit_manager.sync_all()
        self.ui.update()

    def input(self, key):
        """Handle input events."""
        # Don't process game input during naming phase
        if self.game_state.phase == GamePhase.NAMING_CITY:
            return

        if self.game_state.phase != GamePhase.PLAYING:
            return

        if key == 'left mouse down':
            if self.view:
                coord = self.view.get_clicked_hex()
                if coord:
                    self.game_state.handle_hex_click(coord)

        elif key == 'escape':
            self.game_state.select_unit(None)
            self.game_state.select_city(None)

        elif key == 'return' or key == 'enter':
            self._handle_end_turn()

        elif key == 'b':
            unit = self.game_state.selected_unit
            if unit and unit.can_found_city:
                self._handle_found_city()

        elif key == 'space':
            self._select_next_unit()

    def _handle_end_turn(self):
        """Handle end turn action."""
        if self.game_state.phase == GamePhase.PLAYING:
            self.game_state.end_turn()

    def _handle_found_city(self):
        """Handle found city action."""
        unit = self.game_state.selected_unit
        if unit and unit.can_found_city:
            can_found, _ = self.game_state.can_found_city_at(unit.position)
            if can_found:
                # For now, auto-name cities (including the first one)
                player = self.game_state.current_player
                name = player.get_next_city_name() if player else "City"
                self.game_state.start_found_city(unit.id)
                # If it went to NAMING_CITY phase, complete it with auto-name
                if self.game_state.phase == GamePhase.NAMING_CITY:
                    self.game_state.complete_found_city(name)

    def _select_next_unit(self):
        """Select the next unit with movement remaining."""
        units = self.game_state.get_current_player_units()
        movable = [u for u in units if u.can_move]
        if not movable:
            return

        current = self.game_state.selected_unit
        if current and current in movable:
            idx = movable.index(current)
            next_unit = movable[(idx + 1) % len(movable)]
        else:
            next_unit = movable[0]

        self.game_state.select_unit(next_unit.id)
        x, y, z = hex_to_world_3d(next_unit.position, HEX_3D_SIZE, 0)
        # Move camera to look at the unit
        camera.position = Vec3(x, 40, z - 30)

    def run(self):
        """Run the game."""
        self.app.run()


def main():
    """Main entry point."""
    print("Starting Civilization Deluxe (3D)...")
    print()
    print("Controls:")
    print("  - WASD / Arrow keys: Pan camera")
    print("  - Q/E: Rotate camera")
    print("  - Right mouse drag: Orbit camera")
    print("  - Scroll wheel: Zoom in/out")
    print("  - Left click: Select/Move units")
    print("  - B: Found city (settler)")
    print("  - Space: Next unit with movement")
    print("  - Enter: End turn")
    print("  - ESC: Deselect")
    print()

    game = GameApp()
    game.run()


if __name__ == "__main__":
    main()
