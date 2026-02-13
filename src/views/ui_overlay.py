"""
2D UI overlay for Ursina — HUD, buttons, notifications, production picker, victory screen,
help overlay, and escape/pause menu.
"""

from ursina import Entity, Text, Button, Color, color, camera, destroy, mouse, load_texture
from typing import Optional, Callable, List
import sys
import os
import math
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.models.game_state import GameState, GamePhase
from src.models.city import ProductionType, PRODUCTION_ITEMS
from src.utils.hex_utils import hex_to_world_3d
from config import COLORS, MAX_TURNS, MAP_WIDTH, MAP_HEIGHT, HEX_3D_SIZE, TERRAIN_COLORS_3D


def _c(r, g, b, a=255):
    """Create a Color with 0-255 values normalized to 0-1 for Panda3D."""
    return Color(r / 255, g / 255, b / 255, a / 255)


class UIOverlay:
    """2D UI overlay manager with combat info, production picker, notifications,
    help overlay, and escape menu."""

    def __init__(self, game_state: GameState, orbit_camera=None):
        self.game_state = game_state
        self.orbit_camera = orbit_camera
        self.on_end_turn: Optional[Callable] = None
        self.on_found_city: Optional[Callable] = None
        self.on_set_production: Optional[Callable] = None

        self._notifications: List[dict] = []
        self._production_buttons: List[Entity] = []
        self._victory_shown = False

        self._help_visible = False
        self._help_elements: List[Entity] = []
        self._escape_menu_visible = False
        self._escape_menu_elements: List[Entity] = []

        self._unit_panel_elements: List = []
        self._last_panel_unit_id = None

        # Minimap state
        self._mm_dots: List[Entity] = []
        self._mm_viewport: List[Entity] = []
        self._mm_explored_count = 0  # Track exploration changes for texture rebuild

        self._setup_ui()
        self._build_minimap()

    def _setup_ui(self):
        # Top bar background
        self.top_bar = Entity(parent=camera.ui, model='quad', color=_c(25, 28, 38),
                              scale=(2, 0.065), position=(0, 0.465))

        # Turn counter — prominently on the left
        self.turn_label = Text(parent=camera.ui, text='Turn 1/100', position=(-0.84, 0.467),
                               scale=1.4, color=color.white, origin=(-0.5, 0))

        # Civilization name
        self.civ_label = Text(parent=camera.ui, text='', position=(-0.45, 0.467),
                              scale=1.0, color=color.light_gray, origin=(-0.5, 0))

        # Gold (with per-turn income)
        self.gold_label = Text(parent=camera.ui, text='Gold: 0', position=(0.15, 0.467),
                               scale=1.1, color=_c(255, 215, 0), origin=(-0.5, 0))

        # Science
        self.science_label = Text(parent=camera.ui, text='Science: 0', position=(0.45, 0.467),
                                  scale=1.0, color=_c(100, 200, 255), origin=(-0.5, 0))

        # End Turn button — far right, bigger, with key hint
        self.end_turn_button = Button(
            parent=camera.ui, text='End Turn', scale=(0.13, 0.05),
            position=(0.82, 0.465), color=_c(40, 100, 55),
            highlight_color=_c(60, 130, 75),
            on_click=self._on_end_turn_click
        )

        # Found City button — BELOW the top bar, contextual
        self.found_city_button = Button(
            parent=camera.ui, text='Found City (B)', scale=(0.13, 0.04),
            position=(0.82, 0.40), color=_c(60, 100, 60),
            highlight_color=_c(80, 120, 80),
            on_click=self._on_found_city_click
        )
        self.found_city_button.visible = False

        # Bottom bar
        self.bottom_bar = Entity(parent=camera.ui, model='quad', color=_c(30, 30, 40),
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

        # Controls hint (with H for help)
        self.controls_label = Text(
            parent=camera.ui,
            text='WASD: Pan | Q/E: Rotate | Scroll: Zoom | Click: Select/Move/Attack | H: Help',
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
                color=_c(50, 70, 90),
                highlight_color=_c(70, 90, 110),
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
            color=_c(100, 50, 50),
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
        Entity(parent=camera.ui, model='quad', color=_c(0, 0, 0, 200),
               scale=(2, 2), position=(0, 0))

        if winner and winner.id == 0:
            title_text = "VICTORY!"
            title_color = _c(255, 215, 0)
        else:
            title_text = "DEFEAT"
            title_color = _c(200, 50, 50)

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

    # -------------------------------------------------------------------------
    # Help overlay
    # -------------------------------------------------------------------------

    def toggle_help(self):
        if self._help_visible:
            self._hide_help()
        else:
            self._show_help()

    def _show_help(self):
        self._help_visible = True

        # Full-screen backdrop
        bg = Entity(parent=camera.ui, model='quad', color=_c(0, 0, 0, 180),
                    scale=(2, 1), position=(0, 0), z=0.05)

        # Dark content panel
        panel = Entity(parent=camera.ui, model='quad', color=_c(25, 28, 40, 230),
                       scale=(1.3, 0.75), position=(0, 0), z=0.04)

        # Title
        title = Text(parent=camera.ui, text='How to Play', position=(0, 0.30),
                     origin=(0, 0), scale=2.5, color=_c(255, 215, 0))

        # Left column — Controls
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
            'H                This help screen'
        ), position=(-0.38, 0.16), origin=(-0.5, 0.5), scale=0.85, color=color.light_gray)

        # Right column — Gameplay
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

        # Legend
        legend = Text(parent=camera.ui, text=(
            'Green tiles = movement range    Red tiles = attack targets'
        ), position=(0, -0.25), origin=(0, 0), scale=0.9, color=_c(150, 200, 150))

        # Close hint
        close_hint = Text(parent=camera.ui, text='Press H or ESC to close',
                          position=(0, -0.33), origin=(0, 0), scale=0.9, color=color.gray)

        self._help_elements = [bg, panel, title, controls_title, controls_text,
                               gameplay_title, gameplay_text, legend, close_hint]

    def _hide_help(self):
        for el in self._help_elements:
            destroy(el)
        self._help_elements.clear()
        self._help_visible = False

    # -------------------------------------------------------------------------
    # Escape / pause menu
    # -------------------------------------------------------------------------

    def toggle_escape_menu(self):
        if self._escape_menu_visible:
            self._hide_escape_menu()
        else:
            self._show_escape_menu()

    def _show_escape_menu(self):
        self._escape_menu_visible = True

        bg = Entity(parent=camera.ui, model='quad', color=_c(0, 0, 0, 160),
                    scale=(2, 1), position=(0, 0), z=0.05)

        panel = Entity(parent=camera.ui, model='quad', color=_c(35, 35, 50),
                       scale=(0.35, 0.35), position=(0, 0.02), z=0.04)

        title = Text(parent=camera.ui, text='PAUSED', position=(0, 0.14),
                     origin=(0, 0), scale=2.2, color=color.white)

        resume_btn = Button(parent=camera.ui, text='Resume', scale=(0.22, 0.05),
                            position=(0, 0.04), color=_c(50, 90, 50),
                            highlight_color=_c(70, 120, 70),
                            on_click=self._hide_escape_menu)

        help_btn = Button(parent=camera.ui, text='How to Play', scale=(0.22, 0.05),
                          position=(0, -0.04), color=_c(50, 70, 100),
                          highlight_color=_c(70, 90, 120),
                          on_click=lambda: (self._hide_escape_menu(), self.toggle_help()))

        quit_btn = Button(parent=camera.ui, text='Quit to Desktop', scale=(0.22, 0.05),
                          position=(0, -0.12), color=_c(100, 50, 50),
                          highlight_color=_c(120, 70, 70),
                          on_click=self._quit_game)

        self._escape_menu_elements = [bg, panel, title, resume_btn, help_btn, quit_btn]

    def _hide_escape_menu(self):
        for el in self._escape_menu_elements:
            destroy(el)
        self._escape_menu_elements.clear()
        self._escape_menu_visible = False

    def _quit_game(self):
        import sys
        sys.exit()

    # -------------------------------------------------------------------------
    # Unit action panel (left side)
    # -------------------------------------------------------------------------

    def _show_unit_panel(self, unit):
        """Show contextual unit info panel on left side."""
        self._hide_unit_panel()

        # Panel background
        panel = Entity(parent=camera.ui, model='quad', color=_c(20, 25, 35, 220),
                       scale=(0.28, 0.35), position=(-0.74, 0))
        self._unit_panel_elements.append(panel)

        # Unit name + type
        title = Text(parent=camera.ui, text=unit.name.upper(),
                     position=(-0.86, 0.14), origin=(-0.5, 0),
                     scale=1.5, color=_c(255, 215, 0))
        self._unit_panel_elements.append(title)

        # Stats
        stats_lines = [
            f'HP: {unit.health}/100',
            f'Movement: {unit.movement_remaining:.0f}/{unit.max_movement}',
            f'Strength: {unit.strength}',
            f'Range: {unit.attack_range}',
        ]

        y = 0.08
        for line in stats_lines:
            t = Text(parent=camera.ui, text=line, position=(-0.86, y),
                     origin=(-0.5, 0), scale=0.9, color=color.light_gray)
            self._unit_panel_elements.append(t)
            y -= 0.04

        # Separator line
        sep = Entity(parent=camera.ui, model='quad', color=_c(100, 100, 120),
                     scale=(0.22, 0.001), position=(-0.74, y + 0.01))
        self._unit_panel_elements.append(sep)
        y -= 0.03

        # Actions header
        actions_title = Text(parent=camera.ui, text='ACTIONS', position=(-0.86, y),
                             origin=(-0.5, 0), scale=1.0, color=color.white)
        self._unit_panel_elements.append(actions_title)
        y -= 0.04

        # Available actions based on unit state
        if unit.can_move:
            action = Text(parent=camera.ui,
                         text='Click green tiles to move',
                         position=(-0.86, y), origin=(-0.5, 0),
                         scale=0.8, color=_c(100, 255, 100))
            self._unit_panel_elements.append(action)
            y -= 0.035

            action2 = Text(parent=camera.ui,
                          text='Click red tiles to attack',
                          position=(-0.86, y), origin=(-0.5, 0),
                          scale=0.8, color=_c(255, 100, 100))
            self._unit_panel_elements.append(action2)
            y -= 0.035
        else:
            action = Text(parent=camera.ui,
                         text='No moves remaining',
                         position=(-0.86, y), origin=(-0.5, 0),
                         scale=0.8, color=_c(150, 150, 150))
            self._unit_panel_elements.append(action)
            y -= 0.035

        if unit.can_found_city:
            action = Text(parent=camera.ui,
                         text='Press B to found city',
                         position=(-0.86, y), origin=(-0.5, 0),
                         scale=0.8, color=_c(255, 200, 50))
            self._unit_panel_elements.append(action)
            y -= 0.035

        # Keyboard shortcuts
        y -= 0.02
        shortcuts = Text(parent=camera.ui,
                        text='Space: Next unit | ESC: Deselect',
                        position=(-0.86, y), origin=(-0.5, 0),
                        scale=0.7, color=color.gray)
        self._unit_panel_elements.append(shortcuts)

    def _hide_unit_panel(self):
        for el in self._unit_panel_elements:
            destroy(el)
        self._unit_panel_elements.clear()
        self._last_panel_unit_id = None

    # -------------------------------------------------------------------------
    # Minimap
    # -------------------------------------------------------------------------

    def _build_minimap(self):
        """Generate terrain texture and create minimap UI elements."""
        # World coordinate ranges
        self._world_x_max = HEX_3D_SIZE * 1.5 * (MAP_WIDTH - 1)
        self._world_z_max = HEX_3D_SIZE * math.sqrt(3) * ((MAP_HEIGHT - 1) + (MAP_WIDTH - 1) / 2.0)

        # Minimap UI dimensions (match map aspect ratio)
        map_aspect = self._world_x_max / self._world_z_max  # ~0.7, taller than wide
        self._mm_h = 0.26
        self._mm_w = self._mm_h * map_aspect
        self._mm_x = 0.88 - self._mm_w / 2  # Right-aligned
        self._mm_y = -0.36 + self._mm_h / 2  # Just above bottom bar

        # Image dimensions for texture
        self._mm_img_h = 220
        self._mm_img_w = int(self._mm_img_h * map_aspect)
        self._mm_tex_version = 0
        self._mm_tex_path = os.path.join(tempfile.gettempdir(), f'civdeluxe_minimap_0.png')

        # Generate initial terrain texture (with fog of war)
        self._regenerate_minimap_texture()

        # Background panel
        self._mm_bg = Entity(parent=camera.ui, model='quad', color=_c(10, 12, 20, 220),
                             scale=(self._mm_w + 0.015, self._mm_h + 0.015),
                             position=(self._mm_x, self._mm_y), z=0.03)

        # Terrain quad
        mm_tex = load_texture(self._mm_tex_path)
        self._mm_quad = Entity(parent=camera.ui, model='quad', texture=mm_tex,
                               scale=(self._mm_w, self._mm_h),
                               position=(self._mm_x, self._mm_y), z=0.02)
        self._mm_quad.setLightOff()

        # Border lines (top, bottom, left, right)
        border_c = _c(100, 120, 160, 220)
        bw = 0.002
        hw, hh = self._mm_w / 2, self._mm_h / 2
        Entity(parent=camera.ui, model='quad', color=border_c,
               scale=(self._mm_w + bw, bw), position=(self._mm_x, self._mm_y + hh), z=0.015)
        Entity(parent=camera.ui, model='quad', color=border_c,
               scale=(self._mm_w + bw, bw), position=(self._mm_x, self._mm_y - hh), z=0.015)
        Entity(parent=camera.ui, model='quad', color=border_c,
               scale=(bw, self._mm_h), position=(self._mm_x - hw, self._mm_y), z=0.015)
        Entity(parent=camera.ui, model='quad', color=border_c,
               scale=(bw, self._mm_h), position=(self._mm_x + hw, self._mm_y), z=0.015)

        # Viewport rectangle (4 edges — bright white)
        for _ in range(4):
            edge = Entity(parent=camera.ui, model='quad', color=_c(255, 255, 255, 240),
                          scale=(0.001, 0.001), position=(0, 0), z=0.005)
            self._mm_viewport.append(edge)

    def _regenerate_minimap_texture(self):
        """Regenerate the minimap terrain image with fog of war."""
        from PIL import Image, ImageDraw

        fog_color = (18, 22, 32, 255)
        img = Image.new('RGBA', (self._mm_img_w, self._mm_img_h), fog_color)
        draw = ImageDraw.Draw(img)

        # Larger dot radius so hexes fill the minimap with no gaps
        r = max(3, int(self._mm_img_w / MAP_WIDTH * 0.8))

        explored_count = 0
        for tile in self.game_state.game_map:
            x, _, z = hex_to_world_3d(tile.coord, HEX_3D_SIZE, 0)
            px = int(x / self._world_x_max * (self._mm_img_w - 1))
            py = int((1.0 - z / self._world_z_max) * (self._mm_img_h - 1))

            if tile.explored:
                tc = TERRAIN_COLORS_3D.get(tile.terrain.value, (100, 100, 100))
                explored_count += 1
            else:
                tc = fog_color[:3]
            draw.ellipse([px - r, py - r, px + r, py + r], fill=tc)

        img.save(self._mm_tex_path)
        self._mm_explored_count = explored_count

    def _world_to_minimap(self, wx, wz):
        """Convert world coordinates to minimap UI position."""
        nx = wx / self._world_x_max  # 0 to 1
        nz = wz / self._world_z_max  # 0 to 1
        mx = self._mm_x - self._mm_w / 2 + nx * self._mm_w
        my = self._mm_y - self._mm_h / 2 + nz * self._mm_h  # z+ = up on minimap
        return mx, my

    def _minimap_to_world(self, mx, my):
        """Convert minimap UI position to world coordinates."""
        nx = (mx - (self._mm_x - self._mm_w / 2)) / self._mm_w
        nz = (my - (self._mm_y - self._mm_h / 2)) / self._mm_h
        wx = nx * self._world_x_max
        wz = nz * self._world_z_max
        return wx, wz

    def handle_minimap_click(self):
        """Check if left click hit the minimap; if so, pan camera there. Returns True if consumed."""
        if not self.orbit_camera:
            return False

        mx, my = mouse.position.x, mouse.position.y
        hw, hh = self._mm_w / 2, self._mm_h / 2

        if (self._mm_x - hw <= mx <= self._mm_x + hw and
                self._mm_y - hh <= my <= self._mm_y + hh):
            wx, wz = self._minimap_to_world(mx, my)
            self.orbit_camera.set_target(wx, wz)
            return True
        return False

    def _update_minimap(self):
        """Update unit/city dots, fog of war, and viewport rectangle on the minimap."""
        # Check if exploration changed — regenerate texture if so
        explored_now = sum(1 for t in self.game_state.game_map if t.explored)
        if explored_now != self._mm_explored_count:
            self._mm_tex_version = getattr(self, '_mm_tex_version', 0) + 1
            self._mm_tex_path = os.path.join(
                tempfile.gettempdir(), f'civdeluxe_minimap_{self._mm_tex_version}.png')
            self._regenerate_minimap_texture()
            self._mm_quad.texture = load_texture(self._mm_tex_path)

        # Clear old dots
        for dot in self._mm_dots:
            destroy(dot)
        self._mm_dots.clear()

        # Draw city dots (slightly larger)
        for city_id, city in self.game_state.cities.items():
            x, _, z = hex_to_world_3d(city.position, HEX_3D_SIZE, 0)
            mx, my = self._world_to_minimap(x, z)
            player = self.game_state.get_player(city.owner_id)
            if player and player.color:
                pc = _c(player.color[0], player.color[1], player.color[2])
            else:
                pc = _c(200, 200, 200)
            dot = Entity(parent=camera.ui, model='quad', color=pc,
                         scale=(0.008, 0.008), position=(mx, my), z=0.003)
            dot.setLightOff()
            self._mm_dots.append(dot)

        # Draw unit dots (only on explored tiles)
        for unit_id, unit in self.game_state.units.items():
            tile = self.game_state.game_map.get_tile(unit.position)
            if tile and not tile.explored:
                continue  # Don't show enemy units in fog
            x, _, z = hex_to_world_3d(unit.position, HEX_3D_SIZE, 0)
            mx, my = self._world_to_minimap(x, z)
            player = self.game_state.get_player(unit.owner_id)
            if player and player.color:
                pc = _c(player.color[0], player.color[1], player.color[2])
            else:
                pc = _c(200, 200, 200)
            dot = Entity(parent=camera.ui, model='quad', color=pc,
                         scale=(0.006, 0.006), position=(mx, my), z=0.002)
            dot.setLightOff()
            self._mm_dots.append(dot)

        # Update viewport rectangle
        if self.orbit_camera and self._mm_viewport:
            tx, tz = self.orbit_camera.get_target()
            vw, vh = self.orbit_camera.get_viewport_size()

            x1, y1 = self._world_to_minimap(tx - vw / 2, tz - vh / 2)
            x2, y2 = self._world_to_minimap(tx + vw / 2, tz + vh / 2)

            # Clamp to minimap bounds
            hw, hh = self._mm_w / 2, self._mm_h / 2
            x1 = max(self._mm_x - hw, min(self._mm_x + hw, x1))
            x2 = max(self._mm_x - hw, min(self._mm_x + hw, x2))
            y1 = max(self._mm_y - hh, min(self._mm_y + hh, y1))
            y2 = max(self._mm_y - hh, min(self._mm_y + hh, y2))

            rect_w = max(0.01, x2 - x1)
            rect_h = max(0.01, y2 - y1)
            cx = (x1 + x2) / 2
            cy = (y1 + y2) / 2
            bw = 0.003  # Thicker viewport lines

            # Top edge
            self._mm_viewport[0].position = (cx, y2)
            self._mm_viewport[0].scale = (rect_w + bw, bw)
            # Bottom edge
            self._mm_viewport[1].position = (cx, y1)
            self._mm_viewport[1].scale = (rect_w + bw, bw)
            # Left edge
            self._mm_viewport[2].position = (x1, cy)
            self._mm_viewport[2].scale = (bw, rect_h)
            # Right edge
            self._mm_viewport[3].position = (x2, cy)
            self._mm_viewport[3].scale = (bw, rect_h)

    # -------------------------------------------------------------------------
    # Per-frame update
    # -------------------------------------------------------------------------

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

            # Calculate income from all cities
            gold_income = 0
            sci_income = 0
            for city in self.game_state.get_current_player_cities():
                yields = city.calculate_yields(self.game_state.game_map)
                gold_income += yields.gold
                sci_income += yields.science

            self.gold_label.text = f'Gold: {player.gold} (+{gold_income})'
            self.science_label.text = f'Sci: {player.science} (+{sci_income})'

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
                    _c(60, 100, 60) if can_found else _c(80, 80, 80)
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

        # Unit action panel
        if unit:
            # Only rebuild panel if unit changed or health/movement changed
            panel_key = (unit.id, int(unit.health), int(unit.movement_remaining))
            if panel_key != self._last_panel_unit_id:
                self._show_unit_panel(unit)
                self._last_panel_unit_id = panel_key
        else:
            if self._unit_panel_elements:
                self._hide_unit_panel()

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
                color=_c(255, 255, 100, int(alpha * 255))
            )
            self._notification_texts.append(t)

        # Update minimap dots and viewport
        self._update_minimap()
