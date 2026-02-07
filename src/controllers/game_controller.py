"""
Main game controller - handles game logic and coordinates between model and view.
"""

import pygame
from typing import Optional

from src.models.game_state import GameState, GamePhase
from src.models.city import ProductionType
from src.views.game_view import GameView
from src.controllers.input_handler import InputHandler
from config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, GAME_TITLE


class GameController:
    """
    Main controller coordinating game logic, view, and input.
    """

    def __init__(self):
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Initialize MVC components
        self.game_state = GameState()
        self.view = GameView(self.screen, self.game_state)
        self.input_handler = InputHandler()

        # Set up callbacks
        self._setup_callbacks()

        # Game control
        self.running = False
        self.paused = False

    def _setup_callbacks(self):
        """Set up input callbacks."""
        self.input_handler.on_quit = self._handle_quit
        self.input_handler.on_hex_click = self._handle_hex_click
        self.input_handler.on_hex_hover = self._handle_hex_hover

        # View callbacks
        self.view.set_end_turn_callback(self._handle_end_turn)
        self.view.set_found_city_callback(self._handle_found_city_button)
        self.view.on_found_city = self._handle_city_name_confirmed
        self.view.on_cancel_found_city = self._handle_city_name_cancelled
        self.view.on_set_production = self._handle_set_production

    def start_new_game(self, map_seed: Optional[int] = None, civ_id: str = 'rome'):
        """Start a new game."""
        self.game_state.initialize_game(map_seed=map_seed, civ_id=civ_id)

        # Center camera on starting unit
        units = self.game_state.get_current_player_units()
        if units:
            self.view.center_camera_on_hex(units[0].position)

    def run(self):
        """Main game loop."""
        self.running = True

        while self.running:
            # Process events
            for event in pygame.event.get():
                # Let view handle UI events first
                if self.view.handle_event(event):
                    continue

                # Handle keyboard shortcuts
                if event.type == pygame.KEYDOWN:
                    if self._handle_keyboard_shortcut(event.key):
                        continue

                # Then input handler
                actions = self.input_handler.process_event(event)

                if actions.get('quit'):
                    self.running = False

                if actions.get('deselect'):
                    self.game_state.select_unit(None)
                    self.game_state.select_city(None)

            # Update continuous input
            input_state = self.input_handler.update()

            # Move camera (only when not in dialog)
            if self.game_state.phase == GamePhase.PLAYING:
                if input_state.camera_dx != 0 or input_state.camera_dy != 0:
                    self.view.camera.move(input_state.camera_dx, input_state.camera_dy)

            # Update game state (for animations, AI, etc.)
            self._update()

            # Render
            self.view.update()
            self.view.draw()

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

    def _handle_keyboard_shortcut(self, key: int) -> bool:
        """Handle keyboard shortcuts. Returns True if handled."""
        if self.game_state.phase == GamePhase.NAMING_CITY:
            return False  # Let dialog handle input

        # B = Found City (when settler selected)
        if key == pygame.K_b:
            unit = self.game_state.selected_unit
            if unit and unit.can_found_city:
                self._handle_found_city_button()
                return True

        # Enter = End Turn
        if key == pygame.K_RETURN:
            if self.game_state.phase == GamePhase.PLAYING:
                self._handle_end_turn()
                return True

        # Space = Select next unit
        if key == pygame.K_SPACE:
            self._select_next_unit()
            return True

        return False

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
        self.view.center_camera_on_hex(next_unit.position)

    def _update(self):
        """Update game logic each frame."""
        pass

    def _handle_quit(self):
        """Handle quit event."""
        self.running = False

    def _handle_hex_click(self, screen_x: int, screen_y: int):
        """Handle click on the map."""
        if self.game_state.phase != GamePhase.PLAYING:
            return

        coord = self.view.screen_to_hex(screen_x, screen_y)
        if coord:
            self.game_state.handle_hex_click(coord)

    def _handle_hex_hover(self, screen_x: int, screen_y: int):
        """Handle mouse hover over map."""
        coord = self.view.screen_to_hex(screen_x, screen_y)
        self.game_state.hovered_hex = coord

    def _handle_end_turn(self):
        """Handle end turn button click."""
        if self.game_state.phase != GamePhase.PLAYING:
            return

        self.game_state.end_turn()

    def _handle_found_city_button(self):
        """Handle the Found City button click."""
        unit = self.game_state.selected_unit
        if not unit or not unit.can_found_city:
            return

        can_found, reason = self.game_state.can_found_city_at(unit.position)
        if not can_found:
            return

        # Start the founding process
        if self.game_state.start_found_city(unit.id):
            # If it's the first city, show naming dialog
            if self.game_state.phase == GamePhase.NAMING_CITY:
                player = self.game_state.current_player
                default_name = player.get_next_city_name() if player else "Capital"
                self.view.show_city_naming_dialog(default_name)

    def _handle_city_name_confirmed(self, name: str):
        """Handle city name confirmation from dialog."""
        self.game_state.complete_found_city(name)

    def _handle_city_name_cancelled(self):
        """Handle city naming cancelled."""
        self.game_state.cancel_found_city()

    def _handle_set_production(self, city_id: int, production_type: ProductionType):
        """Handle production selection for a city."""
        self.game_state.set_city_production(city_id, production_type)
