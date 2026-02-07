"""
2D UI overlay for Ursina using Ursina's UI system.
"""

from ursina import Entity, Text, Button, color, camera
from typing import Optional, Callable
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState, GamePhase
from config import COLORS


class UIOverlay:
    """2D UI overlay manager."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state

        # Callbacks
        self.on_end_turn: Optional[Callable] = None
        self.on_found_city: Optional[Callable] = None

        self._setup_ui()

    def _setup_ui(self):
        """Create UI elements."""
        # Top bar background
        self.top_bar = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgb(40, 40, 50),
            scale=(2, 0.08),
            position=(0, 0.46)
        )

        # Turn counter
        self.turn_label = Text(
            parent=camera.ui,
            text='Turn 1',
            position=(-0.85, 0.47),
            scale=1.5,
            color=color.white
        )

        # Civilization label
        self.civ_label = Text(
            parent=camera.ui,
            text='',
            position=(-0.55, 0.47),
            scale=1.0,
            color=color.white
        )

        # Gold label
        self.gold_label = Text(
            parent=camera.ui,
            text='Gold: 0',
            position=(0.1, 0.47),
            scale=1.0,
            color=color.rgb(255, 215, 0)
        )

        # Science label
        self.science_label = Text(
            parent=camera.ui,
            text='Science: 0',
            position=(0.35, 0.47),
            scale=1.0,
            color=color.rgb(100, 200, 255)
        )

        # End Turn button
        self.end_turn_button = Button(
            parent=camera.ui,
            text='End Turn',
            scale=(0.12, 0.045),
            position=(0.82, 0.46),
            color=color.rgb(60, 80, 100),
            highlight_color=color.rgb(80, 100, 120),
            on_click=self._on_end_turn_click
        )

        # Found City button (hidden by default)
        self.found_city_button = Button(
            parent=camera.ui,
            text='Found City (B)',
            scale=(0.14, 0.045),
            position=(0.65, 0.46),
            color=color.rgb(60, 100, 60),
            highlight_color=color.rgb(80, 120, 80),
            on_click=self._on_found_city_click
        )
        self.found_city_button.visible = False

        # Bottom bar background
        self.bottom_bar = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgb(40, 40, 50),
            scale=(2, 0.10),
            position=(0, -0.45)
        )

        # Unit info labels
        self.unit_name_label = Text(
            parent=camera.ui,
            text='No unit selected',
            position=(-0.85, -0.42),
            scale=1.3,
            color=color.white
        )

        self.unit_stats_label = Text(
            parent=camera.ui,
            text='Click a unit to select it',
            position=(-0.85, -0.46),
            scale=0.9,
            color=color.light_gray
        )

        # Terrain info (right side)
        self.terrain_label = Text(
            parent=camera.ui,
            text='',
            position=(0.85, -0.43),
            scale=0.9,
            color=color.light_gray,
            origin=(1, 0)
        )

        # Controls hint
        self.controls_label = Text(
            parent=camera.ui,
            text='WASD: Pan | Q/E: Rotate | Scroll: Zoom | Right-drag: Orbit',
            position=(0, -0.48),
            scale=0.7,
            color=color.gray,
            origin=(0, 0)
        )

    def _on_end_turn_click(self):
        if self.on_end_turn:
            self.on_end_turn()

    def _on_found_city_click(self):
        if self.on_found_city:
            self.on_found_city()

    def update(self):
        """Update UI each frame."""
        gs = self.game_state

        # Turn
        self.turn_label.text = f'Turn {gs.turn_number}'

        # Civilization
        player = gs.current_player
        if player:
            if player.civilization:
                self.civ_label.text = f'{player.civilization.name}'
            else:
                self.civ_label.text = player.name

            # Resources
            self.gold_label.text = f'Gold: {player.gold}'
            self.science_label.text = f'Science: {player.science}'

        # Unit info
        unit = gs.selected_unit
        if unit:
            unit_type_name = unit.unit_type.value.title()
            self.unit_name_label.text = f'{unit_type_name}'
            self.unit_stats_label.text = (
                f'Movement: {unit.movement_remaining:.1f}/{unit.max_movement}  |  '
                f'Strength: {unit.strength}'
            )

            # Show/hide found city button
            if unit.can_found_city:
                can_found, reason = gs.can_found_city_at(unit.position)
                self.found_city_button.visible = True
                if can_found:
                    self.found_city_button.color = color.rgb(60, 100, 60)
                else:
                    self.found_city_button.color = color.rgb(80, 80, 80)
            else:
                self.found_city_button.visible = False
        else:
            city = gs.selected_city
            if city:
                self.unit_name_label.text = f'{city.name}'
                self.unit_stats_label.text = f'Population: {city.population}'
                self.found_city_button.visible = False
            else:
                self.unit_name_label.text = 'No selection'
                self.unit_stats_label.text = 'Click a unit or city to select'
                self.found_city_button.visible = False

        # Terrain info
        if gs.hovered_hex:
            tile = gs.game_map.get_tile(gs.hovered_hex)
            if tile:
                cost_str = str(tile.movement_cost) if tile.movement_cost else 'Impassable'
                self.terrain_label.text = f'{tile.terrain.value.title()} (Move: {cost_str})'
            else:
                self.terrain_label.text = ''
        else:
            self.terrain_label.text = ''
