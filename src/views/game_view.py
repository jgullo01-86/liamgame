"""
Main game view - handles rendering the game.
"""

import pygame
from typing import Tuple, Optional, Dict, List, Callable
import math

from src.models.game_state import GameState, GamePhase
from src.models.map import TerrainType, Tile
from src.models.unit import Unit
from src.models.city import City
from src.views.ui_elements import Button, Panel, Label, CityPanel, CityNamingDialog
from src.utils.hex_utils import HexCoord, hex_to_pixel, pixel_to_hex, hex_corners
from config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HEX_SIZE, COLORS,
    TOP_BAR_HEIGHT, BOTTOM_BAR_HEIGHT, BUTTON_WIDTH, BUTTON_HEIGHT
)


class Camera:
    """Camera for panning around the map."""

    def __init__(self, screen_width: int, screen_height: int):
        self.x = 0.0
        self.y = 0.0
        self.screen_width = screen_width
        self.screen_height = screen_height

    def move(self, dx: float, dy: float):
        """Move the camera by the given offset."""
        self.x += dx
        self.y += dy

    def world_to_screen(self, world_x: float, world_y: float) -> Tuple[float, float]:
        """Convert world coordinates to screen coordinates."""
        return (world_x - self.x, world_y - self.y + TOP_BAR_HEIGHT)

    def screen_to_world(self, screen_x: float, screen_y: float) -> Tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        return (screen_x + self.x, screen_y + self.y - TOP_BAR_HEIGHT)

    def center_on(self, world_x: float, world_y: float):
        """Center the camera on a world position."""
        self.x = world_x - self.screen_width / 2
        self.y = world_y - (self.screen_height - TOP_BAR_HEIGHT - BOTTOM_BAR_HEIGHT) / 2


class GameView:
    """Main view class for rendering the game."""

    def __init__(self, screen: pygame.Surface, game_state: GameState):
        self.screen = screen
        self.game_state = game_state
        self.camera = Camera(SCREEN_WIDTH, SCREEN_HEIGHT)

        # Callbacks
        self.on_found_city: Optional[Callable[[str], None]] = None
        self.on_cancel_found_city: Optional[Callable[[], None]] = None
        self.on_set_production: Optional[Callable[[int, any], None]] = None

        # UI elements
        self._setup_ui()

        # Rendering caches
        self._hex_surface_cache: Dict[TerrainType, pygame.Surface] = {}
        self._build_hex_cache()

        # Frame timing for animations
        self._last_frame_time = pygame.time.get_ticks()

    def _setup_ui(self):
        """Set up UI elements."""
        # Top bar
        self.top_bar = Panel(pygame.Rect(0, 0, SCREEN_WIDTH, TOP_BAR_HEIGHT))

        # Turn counter label
        self.turn_label = Label(
            position=(10, TOP_BAR_HEIGHT // 2),
            text="Turn 1",
            font_size=20,
            anchor="midleft"
        )

        # Civilization/Leader label
        self.civ_label = Label(
            position=(100, TOP_BAR_HEIGHT // 2),
            text="",
            font_size=16,
            anchor="midleft"
        )

        # Resource labels
        self.gold_label = Label(
            position=(350, TOP_BAR_HEIGHT // 2),
            text="Gold: 0",
            font_size=18,
            anchor="midleft"
        )

        self.science_label = Label(
            position=(480, TOP_BAR_HEIGHT // 2),
            text="Science: 0",
            font_size=18,
            anchor="midleft"
        )

        # End turn button
        self.end_turn_button = Button(
            rect=pygame.Rect(
                SCREEN_WIDTH - BUTTON_WIDTH - 10,
                (TOP_BAR_HEIGHT - BUTTON_HEIGHT) // 2,
                BUTTON_WIDTH,
                BUTTON_HEIGHT
            ),
            text="End Turn",
            font_size=18
        )

        # Found city button (only visible when settler selected)
        self.found_city_button = Button(
            rect=pygame.Rect(
                SCREEN_WIDTH - BUTTON_WIDTH * 2 - 20,
                (TOP_BAR_HEIGHT - BUTTON_HEIGHT) // 2,
                BUTTON_WIDTH,
                BUTTON_HEIGHT
            ),
            text="Found City",
            font_size=16
        )
        self.found_city_button.visible = False

        # Bottom bar
        self.bottom_bar = Panel(pygame.Rect(
            0, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT,
            SCREEN_WIDTH, BOTTOM_BAR_HEIGHT
        ))

        # Unit info labels
        self.unit_name_label = Label(
            position=(10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 15),
            text="",
            font_size=22,
            anchor="topleft"
        )

        self.unit_stats_label = Label(
            position=(10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 40),
            text="",
            font_size=16,
            anchor="topleft"
        )

        self.unit_action_label = Label(
            position=(10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 60),
            text="",
            font_size=14,
            anchor="topleft",
            color=(150, 200, 150)
        )

        self.terrain_label = Label(
            position=(SCREEN_WIDTH - 10, SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + 15),
            text="",
            font_size=16,
            anchor="topright"
        )

        # City panel
        self.city_panel = CityPanel(SCREEN_WIDTH, SCREEN_HEIGHT)

        # City naming dialog
        self.city_naming_dialog = CityNamingDialog(
            SCREEN_WIDTH, SCREEN_HEIGHT,
            on_confirm=self._on_city_name_confirmed,
            on_cancel=self._on_city_name_cancelled
        )

    def _on_city_name_confirmed(self, name: str):
        """Handle city name confirmation."""
        if self.on_found_city:
            self.on_found_city(name)

    def _on_city_name_cancelled(self):
        """Handle city naming cancelled."""
        if self.on_cancel_found_city:
            self.on_cancel_found_city()

    def _build_hex_cache(self):
        """Pre-render hex surfaces for each terrain type."""
        for terrain_type in TerrainType:
            surface = pygame.Surface((HEX_SIZE * 2 + 4, int(HEX_SIZE * 1.8) + 4), pygame.SRCALPHA)

            # Get hex corners centered in the surface
            center = (HEX_SIZE + 2, int(HEX_SIZE * 0.9) + 2)
            corners = hex_corners(center, HEX_SIZE)

            # Fill color
            color = COLORS.get(terrain_type.value, (100, 100, 100))
            pygame.draw.polygon(surface, color, corners)

            # Outline
            pygame.draw.polygon(surface, (40, 40, 40), corners, width=1)

            self._hex_surface_cache[terrain_type] = surface

    def set_end_turn_callback(self, callback):
        """Set the callback for the end turn button."""
        self.end_turn_button.callback = callback

    def set_found_city_callback(self, callback):
        """Set the callback for the found city button."""
        self.found_city_button.callback = callback

    def center_camera_on_hex(self, coord: HexCoord):
        """Center the camera on a hex coordinate."""
        world_x, world_y = hex_to_pixel(coord, HEX_SIZE)
        self.camera.center_on(world_x, world_y)

    def screen_to_hex(self, screen_x: int, screen_y: int) -> Optional[HexCoord]:
        """Convert screen coordinates to hex coordinates."""
        # Check if in map area (not in UI bars)
        if screen_y < TOP_BAR_HEIGHT or screen_y > SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT:
            return None

        world_x, world_y = self.camera.screen_to_world(screen_x, screen_y)
        return pixel_to_hex(world_x, world_y, HEX_SIZE)

    def show_city_naming_dialog(self, default_name: str = ""):
        """Show the city naming dialog."""
        self.city_naming_dialog.show(default_name)

    def update(self):
        """Update the view state."""
        # Calculate delta time for animations
        current_time = pygame.time.get_ticks()
        dt = current_time - self._last_frame_time
        self._last_frame_time = current_time

        # Update dialogs
        self.city_naming_dialog.update(dt)

        # Update turn label
        self.turn_label.set_text(f"Turn {self.game_state.turn_number}")

        # Update civ label
        player = self.game_state.current_player
        if player.civilization:
            self.civ_label.set_text(f"{player.civilization.leader} of {player.civilization.name}")
        else:
            self.civ_label.set_text(player.name)

        # Update resource labels
        self.gold_label.set_text(f"Gold: {player.gold}")
        self.science_label.set_text(f"Science: {player.science}")

        # Update unit info and found city button
        unit = self.game_state.selected_unit
        if unit:
            self.unit_name_label.set_text(f"{unit.name}")
            self.unit_stats_label.set_text(
                f"Movement: {unit.movement_remaining:.1f}/{unit.max_movement}  |  "
                f"Strength: {unit.strength}  |  Health: {unit.health}%"
            )

            # Check if settler can found city
            if unit.can_found_city:
                can_found, reason = self.game_state.can_found_city_at(unit.position)
                self.found_city_button.visible = True
                self.found_city_button.is_enabled = can_found
                if can_found:
                    self.unit_action_label.set_text("Press 'Found City' or B to establish a city here")
                else:
                    self.unit_action_label.set_text(f"Cannot found city: {reason}")
            else:
                self.found_city_button.visible = False
                self.unit_action_label.set_text("")
        else:
            self.unit_name_label.set_text("No unit selected")
            self.unit_stats_label.set_text("Click a unit to select it")
            self.unit_action_label.set_text("")
            self.found_city_button.visible = False

        # Update city panel
        city = self.game_state.selected_city
        if city:
            self.city_panel.update_city(
                city,
                self.game_state.game_map,
                on_production_click=lambda pt: self._on_production_selected(city.id, pt)
            )
            self.unit_name_label.set_text(f"City: {city.name}")
            self.unit_stats_label.set_text(f"Population: {city.population}")
            self.unit_action_label.set_text("")
        else:
            self.city_panel.visible = False

        # Update terrain info for hovered hex
        hovered = self.game_state.hovered_hex
        if hovered:
            tile = self.game_state.get_tile(hovered)
            if tile:
                cost_str = str(tile.movement_cost) if tile.movement_cost else "Impassable"
                self.terrain_label.set_text(
                    f"{tile.terrain.value.title()} (Move cost: {cost_str})"
                )
            else:
                self.terrain_label.set_text("")
        else:
            self.terrain_label.set_text("")

    def _on_production_selected(self, city_id: int, production_type):
        """Handle production selection in city panel."""
        if self.on_set_production:
            self.on_set_production(city_id, production_type)

    def draw(self):
        """Draw the entire game view."""
        # Clear screen
        self.screen.fill(COLORS['background'])

        # Draw map
        self._draw_map()

        # Draw city territories
        self._draw_city_territories()

        # Draw movement range overlay
        self._draw_movement_range()

        # Draw cities
        self._draw_cities()

        # Draw units
        self._draw_units()

        # Draw hex highlight
        self._draw_hex_highlight()

        # Draw UI
        self._draw_ui()

        # Draw city panel
        self.city_panel.draw(self.screen)

        # Draw dialogs (on top of everything)
        self.city_naming_dialog.draw(self.screen)

    def _draw_map(self):
        """Draw all visible tiles."""
        for tile in self.game_state.game_map:
            self._draw_hex(tile)

    def _draw_hex(self, tile: Tile):
        """Draw a single hex tile."""
        # Get screen position
        world_x, world_y = hex_to_pixel(tile.coord, HEX_SIZE)
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

        # Skip if off screen
        if (screen_x < -HEX_SIZE * 2 or screen_x > SCREEN_WIDTH + HEX_SIZE * 2 or
            screen_y < TOP_BAR_HEIGHT - HEX_SIZE * 2 or
            screen_y > SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + HEX_SIZE * 2):
            return

        # Get cached surface
        hex_surface = self._hex_surface_cache.get(tile.terrain)
        if hex_surface:
            # Center the hex surface on the position
            draw_x = screen_x - hex_surface.get_width() / 2
            draw_y = screen_y - hex_surface.get_height() / 2
            self.screen.blit(hex_surface, (draw_x, draw_y))

    def _draw_city_territories(self):
        """Draw territory overlays for cities."""
        for city in self.game_state.cities.values():
            player = self.game_state.get_player(city.owner_id)
            if not player:
                continue

            # Use player color with low alpha
            color = (*player.color, 40)

            for coord in city.territory:
                if coord == city.position:
                    continue  # Skip city center

                world_x, world_y = hex_to_pixel(coord, HEX_SIZE)
                screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

                corners = hex_corners((screen_x, screen_y), HEX_SIZE - 1)
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                pygame.draw.polygon(overlay, color, corners)
                self.screen.blit(overlay, (0, 0))

    def _draw_movement_range(self):
        """Draw movement range overlay for selected unit."""
        unit = self.game_state.selected_unit
        if not unit or not unit.can_move:
            return

        movement_range = self.game_state.get_movement_range(unit.id)

        for coord, cost in movement_range.items():
            world_x, world_y = hex_to_pixel(coord, HEX_SIZE)
            screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

            # Draw highlight overlay
            corners = hex_corners((screen_x, screen_y), HEX_SIZE - 2)

            # Create semi-transparent surface
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(overlay, COLORS['movement_range'], corners)
            self.screen.blit(overlay, (0, 0))

    def _draw_cities(self):
        """Draw all cities."""
        for city in self.game_state.cities.values():
            self._draw_city(city)

    def _draw_city(self, city: City):
        """Draw a single city."""
        world_x, world_y = hex_to_pixel(city.position, HEX_SIZE)
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

        # Skip if off screen
        if (screen_x < -HEX_SIZE * 2 or screen_x > SCREEN_WIDTH + HEX_SIZE * 2 or
            screen_y < TOP_BAR_HEIGHT - HEX_SIZE * 2 or
            screen_y > SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + HEX_SIZE * 2):
            return

        player = self.game_state.get_player(city.owner_id)
        color = player.color if player else (150, 150, 150)

        # City base (larger circle)
        radius = int(HEX_SIZE * 0.7)

        # Selection highlight
        if self.game_state.selected_city and self.game_state.selected_city.id == city.id:
            pygame.draw.circle(self.screen, (255, 255, 100), (int(screen_x), int(screen_y)), radius + 5, width=3)

        # City circle
        pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), radius)
        pygame.draw.circle(self.screen, (30, 30, 30), (int(screen_x), int(screen_y)), radius, width=2)

        # City icon (building shape)
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            pygame.Rect(int(screen_x - 6), int(screen_y - 8), 12, 16)
        )
        pygame.draw.polygon(
            self.screen,
            (255, 255, 255),
            [
                (int(screen_x), int(screen_y - 14)),
                (int(screen_x - 8), int(screen_y - 8)),
                (int(screen_x + 8), int(screen_y - 8))
            ]
        )

        # City name and population
        font = pygame.font.Font(None, 16)
        name_surface = font.render(f"{city.name}", True, (255, 255, 255))
        name_rect = name_surface.get_rect(center=(int(screen_x), int(screen_y + radius + 12)))

        # Background for name
        bg_rect = name_rect.inflate(6, 2)
        pygame.draw.rect(self.screen, (30, 30, 30, 200), bg_rect)
        self.screen.blit(name_surface, name_rect)

        # Population badge
        pop_font = pygame.font.Font(None, 18)
        pop_surface = pop_font.render(str(city.population), True, (255, 255, 255))
        pop_rect = pop_surface.get_rect(center=(int(screen_x + radius - 2), int(screen_y - radius + 2)))

        pygame.draw.circle(self.screen, (50, 50, 50), pop_rect.center, 10)
        pygame.draw.circle(self.screen, color, pop_rect.center, 10, width=2)
        self.screen.blit(pop_surface, pop_rect)

    def _draw_units(self):
        """Draw all units."""
        for unit in self.game_state.units.values():
            self._draw_unit(unit)

    def _draw_unit(self, unit: Unit):
        """Draw a single unit."""
        world_x, world_y = hex_to_pixel(unit.position, HEX_SIZE)
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

        # Skip if off screen
        if (screen_x < -HEX_SIZE or screen_x > SCREEN_WIDTH + HEX_SIZE or
            screen_y < TOP_BAR_HEIGHT - HEX_SIZE or
            screen_y > SCREEN_HEIGHT - BOTTOM_BAR_HEIGHT + HEX_SIZE):
            return

        # Offset if there's a city here
        city_at_pos = self.game_state.get_city_at(unit.position)
        if city_at_pos:
            screen_x += HEX_SIZE * 0.4
            screen_y += HEX_SIZE * 0.3

        # Unit circle
        radius = int(HEX_SIZE * 0.5)
        color = COLORS['unit_friendly'] if unit.owner_id == self.game_state.current_player.id else COLORS['unit_enemy']

        # Selection ring
        if unit.is_selected:
            pygame.draw.circle(self.screen, (255, 255, 100), (int(screen_x), int(screen_y)), radius + 4, width=3)

        # Main circle
        pygame.draw.circle(self.screen, color, (int(screen_x), int(screen_y)), radius)
        pygame.draw.circle(self.screen, (30, 30, 30), (int(screen_x), int(screen_y)), radius, width=2)

        # Unit icon/letter
        font = pygame.font.Font(None, int(HEX_SIZE * 0.8))
        icon_surface = font.render(unit.icon, True, (255, 255, 255))
        icon_rect = icon_surface.get_rect(center=(int(screen_x), int(screen_y)))
        self.screen.blit(icon_surface, icon_rect)

        # Movement indicator (dots below unit)
        if unit.can_move:
            indicator_y = int(screen_y + radius + 8)
            for i in range(int(unit.movement_remaining)):
                dot_x = int(screen_x - (unit.max_movement - 1) * 4 + i * 8)
                pygame.draw.circle(self.screen, (100, 255, 100), (dot_x, indicator_y), 3)

    def _draw_hex_highlight(self):
        """Draw highlight on hovered hex."""
        hovered = self.game_state.hovered_hex
        if not hovered:
            return

        tile = self.game_state.get_tile(hovered)
        if not tile:
            return

        world_x, world_y = hex_to_pixel(hovered, HEX_SIZE)
        screen_x, screen_y = self.camera.world_to_screen(world_x, world_y)

        corners = hex_corners((screen_x, screen_y), HEX_SIZE - 1)

        # Determine highlight color based on context
        unit = self.game_state.selected_unit
        if unit and unit.can_move:
            movement_range = self.game_state.get_movement_range(unit.id)
            if hovered in movement_range:
                color = (100, 255, 100, 150)  # Green for valid move
            else:
                color = (255, 100, 100, 100)  # Red for invalid
        else:
            color = COLORS['hex_highlight']

        # Draw highlight
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        pygame.draw.polygon(overlay, color, corners)
        pygame.draw.polygon(overlay, (255, 255, 255, 150), corners, width=2)
        self.screen.blit(overlay, (0, 0))

    def _draw_ui(self):
        """Draw UI elements."""
        # Top bar
        self.top_bar.draw(self.screen)
        self.turn_label.draw(self.screen)
        self.civ_label.draw(self.screen)
        self.gold_label.draw(self.screen)
        self.science_label.draw(self.screen)
        self.end_turn_button.draw(self.screen)
        self.found_city_button.draw(self.screen)

        # Bottom bar
        self.bottom_bar.draw(self.screen)
        self.unit_name_label.draw(self.screen)
        self.unit_stats_label.draw(self.screen)
        self.unit_action_label.draw(self.screen)
        self.terrain_label.draw(self.screen)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle UI events. Returns True if event was consumed."""
        # Handle dialogs first (they're modal)
        if self.city_naming_dialog.handle_event(event):
            return True

        # Handle city panel
        if self.city_panel.handle_event(event):
            return True

        # Handle buttons
        if self.end_turn_button.handle_event(event):
            return True

        if self.found_city_button.handle_event(event):
            return True

        return False
