#!/usr/bin/env python3
"""
Civilization Deluxe - A 4X Strategy Game (3D Ursina Version)
Main entry point — wires up GameView3D, OrbitCamera, UnitManager3D, UIOverlay, and AI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ursina import Ursina, Entity, window, color, DirectionalLight, AmbientLight, camera, Vec3

from src.models.game_state import GameState, GamePhase
from src.views.game_view_3d import GameView3D
from src.views.unit_renderer import UnitManager3D
from src.views.ui_overlay import UIOverlay
from src.views.camera_controller import OrbitCamera
from src.controllers.ai_controller import AIController
from src.utils.hex_utils import hex_to_world_3d
from config import (GAME_TITLE, SCREEN_WIDTH, SCREEN_HEIGHT, HEX_3D_SIZE,
                    MAP_WIDTH, MAP_HEIGHT, AI_PLAYER_COUNT)


class GameApp:
    """Main game application."""

    def __init__(self):
        self.app = Ursina(
            title=GAME_TITLE,
            development_mode=False,
            borderless=False,
        )
        window.size = (SCREEN_WIDTH, SCREEN_HEIGHT)
        window.color = color.rgb(20, 25, 35)

        self._setup_lighting()

        # Initialize game state with AI
        self.game_state = GameState()
        self.game_state.initialize_game(ai_count=AI_PLAYER_COUNT)

        # Build the 3D hex map using GameView3D (proper hex tiles!)
        self.view = GameView3D(self.game_state)
        self.view.build_map()

        # Set up orbital camera
        self.orbit_camera = OrbitCamera()

        # Center camera on starting unit
        units = self.game_state.get_current_player_units()
        if units:
            x, _, z = hex_to_world_3d(units[0].position, HEX_3D_SIZE, 0)
            self.orbit_camera.set_target(x, z)

        # Unit manager (uses view for terrain heights)
        self.unit_manager = UnitManager3D(self.game_state, view_3d=self.view)

        # UI overlay
        self.ui = UIOverlay(self.game_state)
        self.ui.on_end_turn = self._handle_end_turn
        self.ui.on_found_city = self._handle_found_city
        self.ui.on_set_production = self._handle_set_production

        # AI controller
        self.ai = AIController(self.game_state)
        self.game_state.ai_controller = self.ai

        # Initial sync
        self.unit_manager.sync_all()

        # Track city selection for production picker
        self._last_selected_city_id = None

        # Create controller entity for update/input binding
        self.controller = Entity()
        self.controller.update = self.update
        self.controller.input = self.input

        print(f"Game started! You are {self.game_state.current_player.name}")
        if self.game_state.current_player.civilization:
            print(f"Civilization: {self.game_state.current_player.civilization.name}")
        print(f"Players: {len(self.game_state.players)} ({AI_PLAYER_COUNT} AI)")

    def _setup_lighting(self):
        AmbientLight(color=color.rgb(180, 180, 200))
        sun = DirectionalLight()
        sun.look_at(Vec3(-1, -2, -1))

    def update(self):
        """Update game each frame."""
        # Update camera
        self.orbit_camera.update()

        # Update view (hover highlights, movement range)
        self.view.update()

        # Sync unit/city 3D entities
        self.unit_manager.sync_all()

        # Update UI
        self.ui.update()

        # Check if selected city changed — show production picker
        city = self.game_state.selected_city
        if city and city.id != self._last_selected_city_id:
            if city.owner_id == self.game_state.current_player.id:
                self.ui.show_production_picker(city.id)
            self._last_selected_city_id = city.id
        elif not city:
            self._last_selected_city_id = None

    def input(self, key):
        """Handle input events."""
        # Camera input (scroll wheel, etc.)
        self.orbit_camera.input(key)

        # Don't process game input during naming or game over
        if self.game_state.phase == GamePhase.NAMING_CITY:
            return
        if self.game_state.phase == GamePhase.GAME_OVER:
            return

        if key == 'left mouse down':
            coord = self.view.get_clicked_hex()
            if coord:
                self.game_state.handle_hex_click(coord)

        elif key == 'escape':
            self.game_state.select_unit(None)
            self.game_state.select_city(None)
            self.ui._clear_production_picker()

        elif key == 'return' or key == 'enter':
            self._handle_end_turn()

        elif key == 'b':
            unit = self.game_state.selected_unit
            if unit and unit.can_found_city:
                self._handle_found_city()

        elif key == 'space':
            self._select_next_unit()

    def _handle_end_turn(self):
        if self.game_state.phase == GamePhase.PLAYING:
            self.game_state.end_turn()

    def _handle_found_city(self):
        unit = self.game_state.selected_unit
        if unit and unit.can_found_city:
            can_found, _ = self.game_state.can_found_city_at(unit.position)
            if can_found:
                player = self.game_state.current_player
                name = player.get_next_city_name() if player else "City"
                self.game_state.start_found_city(unit.id)
                if self.game_state.phase == GamePhase.NAMING_CITY:
                    self.game_state.complete_found_city(name)

    def _handle_set_production(self, city_id: int, prod_type):
        self.game_state.set_city_production(city_id, prod_type)

    def _select_next_unit(self):
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
        x, _, z = hex_to_world_3d(next_unit.position, HEX_3D_SIZE, 0)
        self.orbit_camera.set_target(x, z)

    def run(self):
        self.app.run()


def main():
    print("=" * 50)
    print("  CIVILIZATION DELUXE")
    print("=" * 50)
    print()
    print("Controls:")
    print("  WASD / Arrows  : Pan camera")
    print("  Q / E          : Rotate camera")
    print("  Scroll wheel   : Zoom in/out")
    print("  Right-drag     : Orbit camera")
    print("  Left click     : Select / Move / Attack")
    print("  B              : Found city (settler)")
    print("  Space          : Next unit")
    print("  Enter          : End turn")
    print("  ESC            : Deselect")
    print()
    print("  Green tiles = movement range")
    print("  Red tiles   = enemy (click to attack!)")
    print()

    game = GameApp()
    game.run()


if __name__ == "__main__":
    main()
