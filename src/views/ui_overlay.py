"""
2D UI overlay for Ursina — HUD, buttons, notifications, production picker, victory screen.
"""

from ursina import Entity, Text, Button, color, camera, destroy
from typing import Optional, Callable, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState, GamePhase
from src.models.city import ProductionType, PRODUCTION_ITEMS
from config import COLORS, MAX_TURNS


class UIOverlay:
    """2D UI overlay manager with combat info, production picker, and notifications."""

    def __init__(self, game_state: GameState):
        self.game_state = game_state
        self.on_end_turn: Optional[Callable] = None
        self.on_found_city: Optional[Callable] = None
        self.on_set_production: Optional[Callable] = None

        self._notifications: List[dict] = []
        self._production_buttons: List[Entity] = []
        self._victory_shown = False

        self._setup_ui()

    def _setup_ui(self):
        # Top bar
        self.top_bar = Entity(parent=camera.ui, model='quad', color=color.rgb(30, 30, 40),
                              scale=(2, 0.08), position=(0, 0.46))

        self.turn_label = Text(parent=camera.ui, text='Turn 1', position=(-0.88, 0.47),
                               scale=1.5, color=color.white)
        self.civ_label = Text(parent=camera.ui, text='', position=(-0.65, 0.47),
                              scale=1.0, color=color.white)
        self.gold_label = Text(parent=camera.ui, text='Gold: 0', position=(0.1, 0.47),
                               scale=1.0, color=color.rgb(255, 215, 0))
        self.science_label = Text(parent=camera.ui, text='Science: 0', position=(0.35, 0.47),
                                  scale=1.0, color=color.rgb(100, 200, 255))

        # End Turn button
        self.end_turn_button = Button(
            parent=camera.ui, text='End Turn', scale=(0.12, 0.045),
            position=(0.82, 0.46), color=color.rgb(60, 80, 100),
            highlight_color=color.rgb(80, 100, 120),
            on_click=self._on_end_turn_click
        )

        # Found City button
        self.found_city_button = Button(
            parent=camera.ui, text='Found City (B)', scale=(0.14, 0.045),
            position=(0.65, 0.46), color=color.rgb(60, 100, 60),
            highlight_color=color.rgb(80, 120, 80),
            on_click=self._on_found_city_click
        )
        self.found_city_button.visible = False

        # Bottom bar
        self.bottom_bar = Entity(parent=camera.ui, model='quad', color=color.rgb(30, 30, 40),
                                 scale=(2, 0.12), position=(0, -0.44))

        self.unit_name_label = Text(parent=camera.ui, text='No unit selected',
                                    position=(-0.88, -0.40), scale=1.3, color=color.white)
        self.unit_stats_label = Text(parent=camera.ui, text='Click a unit to select it',
                                     position=(-0.88, -0.44), scale=0.9, color=color.light_gray)
        self.health_label = Text(parent=camera.ui, text='',
                                 position=(-0.88, -0.48), scale=0.9, color=color.light_gray)

        # Terrain info
        self.terrain_label = Text(parent=camera.ui, text='', position=(0.88, -0.41),
                                  scale=0.9, color=color.light_gray, origin=(1, 0))

        # Controls hint
        self.controls_label = Text(
            parent=camera.ui,
            text='WASD: Pan | Q/E: Rotate | Scroll: Zoom | Click: Select/Move/Attack',
            position=(0, -0.48), scale=0.7, color=color.gray, origin=(0, 0)
        )

        # Notification area (above bottom bar)
        self._notification_texts: List[Text] = []

    def _on_end_turn_click(self):
        if self.on_end_turn:
            self.on_end_turn()

    def _on_found_city_click(self):
        if self.on_found_city:
            self.on_found_city()

    def show_notification(self, text: str):
        """Show a floating notification."""
        self._notifications.append({'text': text, 'timer': 3.0})

    def show_production_picker(self, city_id: int):
        """Show production picker for a city."""
        self._clear_production_picker()

        items = list(PRODUCTION_ITEMS.values())
        y_start = 0.15
        for i, item in enumerate(items):
            btn = Button(
                parent=camera.ui,
                text=f"{item.name} ({item.cost})",
                scale=(0.2, 0.04),
                position=(0, y_start - i * 0.05),
                color=color.rgb(50, 70, 90),
                highlight_color=color.rgb(70, 90, 110),
                tooltip=Text(text=item.description),
            )
            prod_type = item.type
            btn.on_click = lambda pt=prod_type: self._on_production_select(city_id, pt)
            self._production_buttons.append(btn)

        # Title
        title = Text(parent=camera.ui, text='Choose Production:',
                     position=(0, y_start + 0.04), origin=(0, 0),
                     scale=1.2, color=color.white)
        self._production_buttons.append(title)

        # Cancel button
        cancel = Button(
            parent=camera.ui, text='Cancel', scale=(0.1, 0.035),
            position=(0, y_start - len(items) * 0.05 - 0.02),
            color=color.rgb(100, 50, 50),
            on_click=self._clear_production_picker
        )
        self._production_buttons.append(cancel)

    def _on_production_select(self, city_id: int, prod_type: ProductionType):
        if self.on_set_production:
            self.on_set_production(city_id, prod_type)
        self._clear_production_picker()

    def _clear_production_picker(self):
        for btn in self._production_buttons:
            destroy(btn)
        self._production_buttons.clear()

    def show_victory_screen(self):
        """Show victory/defeat screen."""
        if self._victory_shown:
            return
        self._victory_shown = True

        gs = self.game_state
        winner = gs.get_player(gs.victory_player) if gs.victory_player is not None else None

        # Overlay
        Entity(parent=camera.ui, model='quad', color=color.rgba(0, 0, 0, 200),
               scale=(2, 2), position=(0, 0))

        if winner and winner.id == 0:
            title_text = "VICTORY!"
            title_color = color.rgb(255, 215, 0)
        else:
            title_text = "DEFEAT"
            title_color = color.rgb(200, 50, 50)

        Text(parent=camera.ui, text=title_text, position=(0, 0.15),
             origin=(0, 0), scale=4, color=title_color)

        victory_desc = f"{gs.victory_type} Victory" if gs.victory_type else "Game Over"
        if winner:
            victory_desc += f" - {winner.name}"
            if winner.civilization:
                victory_desc += f" ({winner.civilization.name})"
        Text(parent=camera.ui, text=victory_desc, position=(0, 0.05),
             origin=(0, 0), scale=1.5, color=color.white)

        Text(parent=camera.ui, text=f"Turn {gs.turn_number}", position=(0, -0.02),
             origin=(0, 0), scale=1.0, color=color.light_gray)

    def update(self):
        """Update UI each frame."""
        from ursina import time
        gs = self.game_state

        # Victory screen
        if gs.phase == GamePhase.GAME_OVER:
            self.show_victory_screen()
            return

        # Turn info
        self.turn_label.text = f'Turn {gs.turn_number}/{MAX_TURNS}'

        # Player info
        player = gs.current_player
        if player:
            civ_name = player.civilization.name if player.civilization else player.name
            self.civ_label.text = civ_name
            self.gold_label.text = f'Gold: {player.gold}'
            self.science_label.text = f'Science: {player.science}'

        # Unit/city info
        unit = gs.selected_unit
        if unit:
            unit_type_name = unit.unit_type.value.title()
            self.unit_name_label.text = f'{unit_type_name}'
            self.unit_stats_label.text = (
                f'Move: {unit.movement_remaining:.0f}/{unit.max_movement}  |  '
                f'Str: {unit.strength}  |  Range: {unit.attack_range}'
            )
            self.health_label.text = f'HP: {unit.health}/100'

            if unit.can_found_city:
                can_found, reason = gs.can_found_city_at(unit.position)
                self.found_city_button.visible = True
                self.found_city_button.color = (
                    color.rgb(60, 100, 60) if can_found else color.rgb(80, 80, 80)
                )
            else:
                self.found_city_button.visible = False
        else:
            city = gs.selected_city
            if city:
                prod_name = city.current_production.value.title() if city.current_production else "None"
                prod_item = PRODUCTION_ITEMS.get(city.current_production)
                prod_progress = ""
                if prod_item:
                    prod_progress = f" ({city.stored_production}/{prod_item.cost})"

                self.unit_name_label.text = f'{city.name} (Pop {city.population})'
                self.unit_stats_label.text = f'Building: {prod_name}{prod_progress}'
                self.health_label.text = 'Click city again to change production'
                self.found_city_button.visible = False
            else:
                self.unit_name_label.text = 'No selection'
                self.unit_stats_label.text = 'Click a unit or city to select'
                self.health_label.text = ''
                self.found_city_button.visible = False

        # Terrain info
        if gs.hovered_hex:
            tile = gs.game_map.get_tile(gs.hovered_hex)
            if tile:
                cost_str = str(tile.movement_cost) if tile.movement_cost else 'Impassable'
                enemy_unit = gs.get_unit_at(gs.hovered_hex)
                enemy_info = ""
                if enemy_unit and enemy_unit.owner_id != gs.current_player.id:
                    enemy_info = f" | Enemy {enemy_unit.name} HP:{enemy_unit.health}"
                self.terrain_label.text = f'{tile.terrain.value.title()} (Move: {cost_str}){enemy_info}'
            else:
                self.terrain_label.text = ''
        else:
            self.terrain_label.text = ''

        # Process game state events as notifications
        for event_text in gs.events:
            self.show_notification(event_text)
        gs.events.clear()

        # Update notifications
        dt = time.dt
        for notif in self._notifications[:]:
            notif['timer'] -= dt
            if notif['timer'] <= 0:
                self._notifications.remove(notif)

        # Render notifications
        for t in self._notification_texts:
            destroy(t)
        self._notification_texts.clear()

        for i, notif in enumerate(self._notifications[-5:]):
            alpha = min(1.0, notif['timer'])
            t = Text(
                parent=camera.ui,
                text=notif['text'],
                position=(0, -0.30 + i * 0.035),
                origin=(0, 0),
                scale=1.0,
                color=color.rgba(255, 255, 100, int(alpha * 255))
            )
            self._notification_texts.append(t)
