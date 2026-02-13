#!/usr/bin/env python3
"""
Civilization Deluxe - A 4X Strategy Game (3D Ursina Version)
Main entry point — wires up MainMenu, GameView3D, OrbitCamera, UnitManager3D, UIOverlay, and AI.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ursina import Ursina, Entity, Text, Color, window, color, DirectionalLight, AmbientLight, camera, Vec3, destroy

from src.models.game_state import GameState, GamePhase
from src.views.game_view_3d import GameView3D
from src.views.unit_renderer import UnitManager3D
from src.views.ui_overlay import UIOverlay
from src.views.camera_controller import OrbitCamera
from src.views.main_menu import MainMenu
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

        # Game state — not initialized until New Game
        self._game_started = False
        self.game_state = None
        self.view = None
        self.orbit_camera = None
        self.unit_manager = None
        self.ui = None
        self.ai = None
        self._last_selected_city_id = None
        self._last_selected_unit_id = None

        # Show main menu
        self.main_menu = MainMenu()
        self.main_menu.on_new_game = self._start_new_game
        self.main_menu.on_how_to_play = self._menu_how_to_play
        self.main_menu.on_quit = self._quit_game

        # Help overlay shown from main menu (before game starts)
        self._menu_help_overlay = None

        # Create controller entity for update/input binding
        self.controller = Entity()
        self.controller.update = self.update
        self.controller.input = self.input

    def _setup_lighting(self):
        AmbientLight(color=Color(140/255, 140/255, 150/255, 1))
        sun = DirectionalLight()
        sun.look_at(Vec3(-1, -2, -1))

    def _setup_atmosphere(self):
        """Set up sky color and distance fog for gameplay."""
        from panda3d.core import Fog
        window.color = Color(135/255, 185/255, 230/255, 1)
        fog = Fog("scene_fog")
        fog.set_color(135/255, 185/255, 230/255)
        fog.set_exp_density(0.008)
        self.app.render.set_fog(fog)

    def _menu_how_to_play(self):
        """Show help overlay from main menu context (standalone, no UIOverlay needed)."""
        if self._menu_help_overlay:
            return  # Already showing

        # Hide main menu while help is showing
        self.main_menu.hide()

        elements = []

        def _c(r, g, b, a=255):
            return Color(r / 255, g / 255, b / 255, a / 255)

        bg = Entity(parent=camera.ui, model='quad', color=_c(0, 0, 0, 180),
                    scale=(2, 1), position=(0, 0), z=0.05)
        panel = Entity(parent=camera.ui, model='quad', color=_c(25, 28, 40, 230),
                       scale=(1.3, 0.75), position=(0, 0), z=0.04)
        title = Text(parent=camera.ui, text='How to Play', position=(0, 0.30),
                     origin=(0, 0), scale=2.5, color=_c(255, 215, 0))
        controls_title = Text(parent=camera.ui, text='CONTROLS', position=(-0.38, 0.22),
                              origin=(-0.5, 0), scale=1.2, color=color.white)
        controls_text = Text(parent=camera.ui, text=(
            'WASD / Arrows    Pan camera\n'
            'Q / E            Rotate camera\n'
            'Middle-drag      Pan camera\n'
            'Right-drag       Orbit camera\n'
            'Scroll wheel     Zoom in/out\n'
            'Left click       Select / Move / Attack\n'
            'B                Found city (settler)\n'
            'Space            Next unit\n'
            'Enter            End turn\n'
            'C                Reset camera\n'
            'ESC              Deselect / Menu\n'
            'H                Help screen'
        ), position=(-0.38, 0.16), origin=(-0.5, 0.5), scale=0.85, color=color.light_gray)
        gameplay_title = Text(parent=camera.ui, text='GAMEPLAY', position=(0.15, 0.22),
                              origin=(-0.5, 0), scale=1.2, color=color.white)
        gameplay_text = Text(parent=camera.ui, text=(
            '1. Select your Settler and press B\n'
            '   to found your first city.\n\n'
            '2. Click your city to choose what\n'
            '   to build (Warriors, Archers, etc.)\n\n'
            '3. Select units, then click green\n'
            '   tiles to move them.\n\n'
            '4. Click red tiles to attack enemies!\n\n'
            '5. Build more cities to grow your\n'
            '   empire. Eliminate opponents to win!'
        ), position=(0.15, 0.16), origin=(-0.5, 0.5), scale=0.85, color=color.light_gray)
        legend = Text(parent=camera.ui, text=(
            'Green tiles = movement range    Red tiles = attack targets'
        ), position=(0, -0.25), origin=(0, 0), scale=0.9, color=_c(150, 200, 150))
        close_hint = Text(parent=camera.ui, text='Press H or ESC to close',
                          position=(0, -0.33), origin=(0, 0), scale=0.9, color=color.gray)

        elements = [bg, panel, title, controls_title, controls_text,
                    gameplay_title, gameplay_text, legend, close_hint]
        self._menu_help_overlay = elements

    def _start_new_game(self):
        """Initialize and start a new game."""
        # Destroy main menu
        self.main_menu.destroy()

        # Close any menu help overlay
        if self._menu_help_overlay:
            for el in self._menu_help_overlay:
                destroy(el)
            self._menu_help_overlay = None

        # Initialize game state with AI
        self.game_state = GameState()
        self.game_state.initialize_game(ai_count=AI_PLAYER_COUNT)

        # Set up atmosphere (sky + fog)
        self._setup_atmosphere()

        # Build the 3D hex map
        self.view = GameView3D(self.game_state)
        self.view.build_map()

        # Set up orbital camera
        self.orbit_camera = OrbitCamera()

        # Center camera on starting unit
        units = self.game_state.get_current_player_units()
        if units:
            x, _, z = hex_to_world_3d(units[0].position, HEX_3D_SIZE, 0)
            self.orbit_camera.set_target(x, z)

        # Unit manager
        self.unit_manager = UnitManager3D(self.game_state, view_3d=self.view)

        # UI overlay (with camera ref for minimap)
        self.ui = UIOverlay(self.game_state, orbit_camera=self.orbit_camera)
        self.ui.on_end_turn = self._handle_end_turn
        self.ui.on_found_city = self._handle_found_city
        self.ui.on_set_production = self._handle_set_production

        # AI controller
        self.ai = AIController(self.game_state)
        self.game_state.ai_controller = self.ai

        # Initial sync
        self.unit_manager.sync_all()

        # Track selection changes for camera follow
        self._last_selected_city_id = None
        self._last_selected_unit_id = None

        self._game_started = True

        print(f"Game started! You are {self.game_state.current_player.name}")
        if self.game_state.current_player.civilization:
            print(f"Civilization: {self.game_state.current_player.civilization.name}")
        print(f"Players: {len(self.game_state.players)} ({AI_PLAYER_COUNT} AI)")

    def _quit_game(self):
        sys.exit()

    def update(self):
        """Update game each frame."""
        if not self._game_started:
            return

        # Update camera
        self.orbit_camera.update()

        # Update view (hover highlights, movement range)
        self.view.update()

        # Sync unit/city 3D entities
        self.unit_manager.sync_all()

        # Update UI
        self.ui.update()

        # Track selected unit (camera only moves on explicit user action, not auto-select)
        unit = self.game_state.selected_unit
        if not unit:
            self._last_selected_unit_id = None

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
        # If game hasn't started, only handle menu-level help dismiss
        if not self._game_started:
            if key == 'escape' or key == 'h':
                if self._menu_help_overlay:
                    for el in self._menu_help_overlay:
                        destroy(el)
                    self._menu_help_overlay = None
                    self.main_menu.show()
            return

        # Camera input always works (scroll wheel, middle mouse, etc.)
        self.orbit_camera.input(key)

        # H / F1 toggles help overlay (works anytime during gameplay)
        if key == 'h' or key == 'f1':
            self.ui.toggle_help()
            return

        # Block all other game input while help or escape menu is open
        if self.ui._help_visible or self.ui._escape_menu_visible:
            if key == 'escape':
                if self.ui._help_visible:
                    self.ui._hide_help()
                elif self.ui._escape_menu_visible:
                    self.ui._hide_escape_menu()
            return

        # Don't process game input during naming or game over
        if self.game_state.phase == GamePhase.NAMING_CITY:
            return
        if self.game_state.phase == GamePhase.GAME_OVER:
            return

        if key == 'left mouse down':
            # Check minimap click first
            if self.ui.handle_minimap_click():
                return
            coord = self.view.get_clicked_hex()
            if coord:
                self.game_state.handle_hex_click(coord)

        elif key == 'escape':
            # ESC priority chain:
            # 1. Production picker open? → close it
            # 2. Unit/city selected? → deselect
            # 3. Nothing selected → show escape/pause menu
            if self.ui._production_buttons:
                self.ui._clear_production_picker()
            elif self.game_state.selected_unit or self.game_state.selected_city:
                self.game_state.select_unit(None)
                self.game_state.select_city(None)
                self.ui._clear_production_picker()
            else:
                self.ui.toggle_escape_menu()

        elif key == 'return' or key == 'enter':
            self._handle_end_turn()

        elif key == 'b':
            unit = self.game_state.selected_unit
            if unit and unit.can_found_city:
                self._handle_found_city()

        elif key == 'c':
            self.orbit_camera.reset()
            # Re-center on selected unit if one exists
            unit = self.game_state.selected_unit
            if unit:
                x, _, z = hex_to_world_3d(unit.position, HEX_3D_SIZE, 0)
                self.orbit_camera.set_target(x, z)

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

    game = GameApp()
    game.run()


if __name__ == "__main__":
    main()
