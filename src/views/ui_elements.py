"""
UI elements for the game interface.
"""

import pygame
from typing import Tuple, Optional, Callable, List
from dataclasses import dataclass, field

from config import COLORS


@dataclass
class Button:
    """A clickable button UI element."""
    rect: pygame.Rect
    text: str
    callback: Optional[Callable] = None
    color: Tuple[int, int, int] = field(default_factory=lambda: COLORS['ui_button'])
    hover_color: Tuple[int, int, int] = field(default_factory=lambda: COLORS['ui_button_hover'])
    text_color: Tuple[int, int, int] = field(default_factory=lambda: COLORS['ui_button_text'])
    font_size: int = 16
    is_hovered: bool = False
    is_enabled: bool = True
    visible: bool = True

    def __post_init__(self):
        self._font = None

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    def draw(self, surface: pygame.Surface):
        """Draw the button."""
        if not self.visible:
            return

        # Background
        bg_color = self.hover_color if self.is_hovered and self.is_enabled else self.color
        if not self.is_enabled:
            bg_color = tuple(c // 2 for c in self.color)

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=4)
        pygame.draw.rect(surface, (100, 100, 100), self.rect, width=1, border_radius=4)

        # Text
        text_color = self.text_color if self.is_enabled else (100, 100, 100)
        text_surface = self.font.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle mouse events. Returns True if button was clicked."""
        if not self.is_enabled or not self.visible:
            return False

        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.callback:
                    self.callback()
                return True

        return False


class Panel:
    """A rectangular panel for UI grouping."""

    def __init__(
        self,
        rect: pygame.Rect,
        color: Tuple[int, int, int] = None,
        alpha: int = 220
    ):
        self.rect = rect
        self.color = color if color else COLORS['ui_bar']
        self.alpha = alpha
        self._surface = None
        self.visible = True

    def draw(self, surface: pygame.Surface):
        """Draw the panel."""
        if not self.visible:
            return

        if self._surface is None or self._surface.get_size() != self.rect.size:
            self._surface = pygame.Surface(self.rect.size, pygame.SRCALPHA)

        self._surface.fill((*self.color, self.alpha))
        surface.blit(self._surface, self.rect.topleft)

        # Border
        pygame.draw.rect(surface, (60, 60, 70), self.rect, width=1)


class Label:
    """A text label UI element."""

    def __init__(
        self,
        position: Tuple[int, int],
        text: str = "",
        color: Tuple[int, int, int] = None,
        font_size: int = 16,
        anchor: str = "topleft"  # topleft, center, topright, etc.
    ):
        self.position = position
        self.text = text
        self.color = color if color else COLORS['ui_text']
        self.font_size = font_size
        self.anchor = anchor
        self._font = None
        self._cached_surface = None
        self._cached_text = None
        self.visible = True

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    def set_text(self, text: str):
        """Update the label text."""
        self.text = text

    def draw(self, surface: pygame.Surface):
        """Draw the label."""
        if not self.text or not self.visible:
            return

        # Cache rendered text
        if self._cached_text != self.text or self._cached_surface is None:
            self._cached_surface = self.font.render(self.text, True, self.color)
            self._cached_text = self.text

        # Position based on anchor
        rect = self._cached_surface.get_rect()
        setattr(rect, self.anchor, self.position)

        surface.blit(self._cached_surface, rect)


class ProgressBar:
    """A progress bar UI element."""

    def __init__(
        self,
        rect: pygame.Rect,
        max_value: float = 100,
        current_value: float = 100,
        bg_color: Tuple[int, int, int] = (40, 40, 50),
        fill_color: Tuple[int, int, int] = (80, 180, 80),
        border_color: Tuple[int, int, int] = (100, 100, 100)
    ):
        self.rect = rect
        self.max_value = max_value
        self.current_value = current_value
        self.bg_color = bg_color
        self.fill_color = fill_color
        self.border_color = border_color
        self.visible = True

    def set_value(self, value: float):
        """Set the current value."""
        self.current_value = max(0, min(value, self.max_value))

    @property
    def percentage(self) -> float:
        """Get the current percentage."""
        if self.max_value == 0:
            return 0
        return self.current_value / self.max_value

    def draw(self, surface: pygame.Surface):
        """Draw the progress bar."""
        if not self.visible:
            return

        # Background
        pygame.draw.rect(surface, self.bg_color, self.rect)

        # Fill
        fill_width = int(self.rect.width * self.percentage)
        if fill_width > 0:
            fill_rect = pygame.Rect(
                self.rect.x, self.rect.y,
                fill_width, self.rect.height
            )
            pygame.draw.rect(surface, self.fill_color, fill_rect)

        # Border
        pygame.draw.rect(surface, self.border_color, self.rect, width=1)


class TextInput:
    """A text input field."""

    def __init__(
        self,
        rect: pygame.Rect,
        placeholder: str = "",
        max_length: int = 32,
        font_size: int = 20
    ):
        self.rect = rect
        self.text = ""
        self.placeholder = placeholder
        self.max_length = max_length
        self.font_size = font_size
        self.active = True
        self.cursor_visible = True
        self.cursor_timer = 0
        self._font = None
        self.visible = True

    @property
    def font(self) -> pygame.font.Font:
        if self._font is None:
            self._font = pygame.font.Font(None, self.font_size)
        return self._font

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle keyboard events. Returns True if event was handled."""
        if not self.active or not self.visible:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
                return True
            elif event.key == pygame.K_RETURN:
                return True  # Signal completion
            elif event.unicode and len(self.text) < self.max_length:
                # Only allow printable characters
                if event.unicode.isprintable():
                    self.text += event.unicode
                    return True

        return False

    def update(self, dt: float):
        """Update cursor blink."""
        self.cursor_timer += dt
        if self.cursor_timer >= 500:  # Blink every 500ms
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

    def draw(self, surface: pygame.Surface):
        """Draw the text input."""
        if not self.visible:
            return

        # Background
        pygame.draw.rect(surface, (30, 30, 40), self.rect)
        border_color = (100, 150, 255) if self.active else (80, 80, 90)
        pygame.draw.rect(surface, border_color, self.rect, width=2)

        # Text or placeholder
        if self.text:
            text_surface = self.font.render(self.text, True, COLORS['ui_text'])
        else:
            text_surface = self.font.render(self.placeholder, True, (100, 100, 120))

        # Center vertically, left-align with padding
        text_rect = text_surface.get_rect(midleft=(self.rect.x + 10, self.rect.centery))
        surface.blit(text_surface, text_rect)

        # Cursor
        if self.active and self.cursor_visible:
            cursor_x = text_rect.right + 2
            cursor_y1 = self.rect.centery - 10
            cursor_y2 = self.rect.centery + 10
            pygame.draw.line(surface, COLORS['ui_text'], (cursor_x, cursor_y1), (cursor_x, cursor_y2), 2)


class Dialog:
    """A modal dialog box."""

    def __init__(
        self,
        rect: pygame.Rect,
        title: str = "",
        buttons: List[Tuple[str, Callable]] = None
    ):
        self.rect = rect
        self.title = title
        self.visible = False
        self.panel = Panel(rect, alpha=240)

        # Title label
        self.title_label = Label(
            position=(rect.centerx, rect.y + 20),
            text=title,
            font_size=24,
            anchor="midtop"
        )

        # Buttons
        self.buttons: List[Button] = []
        if buttons:
            button_width = 100
            button_height = 30
            total_width = len(buttons) * button_width + (len(buttons) - 1) * 10
            start_x = rect.centerx - total_width // 2

            for i, (text, callback) in enumerate(buttons):
                btn_rect = pygame.Rect(
                    start_x + i * (button_width + 10),
                    rect.bottom - 50,
                    button_width,
                    button_height
                )
                self.buttons.append(Button(rect=btn_rect, text=text, callback=callback))

    def show(self):
        """Show the dialog."""
        self.visible = True

    def hide(self):
        """Hide the dialog."""
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events. Returns True if event was consumed."""
        if not self.visible:
            return False

        for button in self.buttons:
            if button.handle_event(event):
                return True

        # Block events from passing through
        if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if hasattr(event, 'pos') and self.rect.collidepoint(event.pos):
                return True

        return False

    def draw(self, surface: pygame.Surface):
        """Draw the dialog."""
        if not self.visible:
            return

        # Dim background
        dim_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        dim_surface.fill((0, 0, 0, 150))
        surface.blit(dim_surface, (0, 0))

        # Panel
        self.panel.draw(surface)

        # Title
        self.title_label.draw(surface)

        # Buttons
        for button in self.buttons:
            button.draw(surface)


class CityNamingDialog(Dialog):
    """Dialog for naming a new city."""

    def __init__(self, screen_width: int, screen_height: int, on_confirm: Callable[[str], None], on_cancel: Callable[[], None]):
        width = 400
        height = 180
        rect = pygame.Rect(
            (screen_width - width) // 2,
            (screen_height - height) // 2,
            width,
            height
        )

        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        super().__init__(rect, "Name Your Capital City")

        # Text input
        self.text_input = TextInput(
            rect=pygame.Rect(rect.x + 50, rect.y + 70, width - 100, 36),
            placeholder="Enter city name...",
            max_length=24
        )

        # Override buttons
        self.buttons = [
            Button(
                rect=pygame.Rect(rect.centerx - 110, rect.bottom - 50, 100, 30),
                text="Found City",
                callback=self._confirm
            ),
            Button(
                rect=pygame.Rect(rect.centerx + 10, rect.bottom - 50, 100, 30),
                text="Cancel",
                callback=self._cancel
            )
        ]

    def _confirm(self):
        """Confirm city name."""
        name = self.text_input.text.strip()
        if name:
            self.hide()
            self.on_confirm(name)

    def _cancel(self):
        """Cancel city founding."""
        self.hide()
        self.on_cancel()

    def show(self, default_name: str = ""):
        """Show dialog with optional default name."""
        self.text_input.text = default_name
        self.text_input.active = True
        super().show()

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events."""
        if not self.visible:
            return False

        # Handle text input
        if self.text_input.handle_event(event):
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                self._confirm()
            return True

        # Handle buttons
        for button in self.buttons:
            if button.handle_event(event):
                return True

        # Handle escape
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._cancel()
            return True

        return super().handle_event(event)

    def update(self, dt: float):
        """Update dialog animations."""
        if self.visible:
            self.text_input.update(dt)

    def draw(self, surface: pygame.Surface):
        """Draw the dialog."""
        if not self.visible:
            return

        super().draw(surface)
        self.text_input.draw(surface)


class CityPanel:
    """Panel showing city information and production options."""

    def __init__(self, screen_width: int, screen_height: int):
        self.width = 300
        self.height = 400
        self.rect = pygame.Rect(
            screen_width - self.width - 10,
            60,  # Below top bar
            self.width,
            self.height
        )
        self.panel = Panel(self.rect, alpha=230)
        self.visible = False

        # Labels will be positioned relative to panel
        self._setup_labels()

        # Production buttons
        self.production_buttons: List[Button] = []

    def _setup_labels(self):
        """Set up label positions."""
        x = self.rect.x + 15
        y = self.rect.y + 15

        self.city_name_label = Label(
            position=(x, y),
            text="",
            font_size=24,
            anchor="topleft"
        )

        self.population_label = Label(
            position=(x, y + 35),
            text="",
            font_size=18,
            anchor="topleft"
        )

        self.yields_label = Label(
            position=(x, y + 60),
            text="",
            font_size=16,
            anchor="topleft"
        )

        self.food_progress_label = Label(
            position=(x, y + 85),
            text="",
            font_size=14,
            anchor="topleft"
        )

        self.production_header = Label(
            position=(x, y + 120),
            text="Production:",
            font_size=18,
            anchor="topleft"
        )

        self.current_production_label = Label(
            position=(x, y + 145),
            text="",
            font_size=16,
            anchor="topleft"
        )

        self.production_progress_label = Label(
            position=(x, y + 165),
            text="",
            font_size=14,
            anchor="topleft"
        )

        self.choose_production_label = Label(
            position=(x, y + 195),
            text="Choose Production:",
            font_size=16,
            anchor="topleft"
        )

    def update_city(self, city, game_map, on_production_click: Callable):
        """Update panel with city information."""
        from src.models.city import PRODUCTION_ITEMS, ProductionType, get_growth_threshold, CityYields

        if not city:
            self.visible = False
            return

        self.visible = True

        # Update labels
        self.city_name_label.set_text(city.name)
        self.population_label.set_text(f"Population: {city.population}")

        # Calculate yields
        yields = city.calculate_yields(game_map)
        food_surplus = city.get_food_surplus(game_map)
        surplus_text = f"+{food_surplus}" if food_surplus >= 0 else str(food_surplus)

        self.yields_label.set_text(
            f"Food: {yields.food} ({surplus_text})  Prod: {yields.production}  Gold: {yields.gold}"
        )

        # Food progress
        growth_threshold = get_growth_threshold(city.population)
        self.food_progress_label.set_text(
            f"Growth: {city.stored_food}/{growth_threshold}"
        )

        # Current production
        if city.current_production:
            item = PRODUCTION_ITEMS.get(city.current_production)
            if item:
                self.current_production_label.set_text(f"Building: {item.name}")
                self.production_progress_label.set_text(
                    f"Progress: {city.stored_production}/{item.cost}"
                )
            else:
                self.current_production_label.set_text("None")
                self.production_progress_label.set_text("")
        else:
            self.current_production_label.set_text("None selected")
            self.production_progress_label.set_text("")

        # Production buttons
        self.production_buttons = []
        button_y = self.rect.y + 230
        button_height = 35

        for prod_type in ProductionType:
            item = PRODUCTION_ITEMS.get(prod_type)
            if item:
                is_current = city.current_production == prod_type
                btn_color = (60, 100, 60) if is_current else COLORS['ui_button']

                btn = Button(
                    rect=pygame.Rect(self.rect.x + 15, button_y, self.width - 30, button_height),
                    text=f"{item.name} ({item.cost} prod)",
                    color=btn_color,
                    callback=lambda pt=prod_type: on_production_click(pt)
                )
                self.production_buttons.append(btn)
                button_y += button_height + 5

    def handle_event(self, event: pygame.event.Event) -> bool:
        """Handle events. Returns True if consumed."""
        if not self.visible:
            return False

        for button in self.production_buttons:
            if button.handle_event(event):
                return True

        # Block clicks on panel
        if event.type == pygame.MOUSEBUTTONDOWN:
            if hasattr(event, 'pos') and self.rect.collidepoint(event.pos):
                return True

        return False

    def draw(self, surface: pygame.Surface):
        """Draw the city panel."""
        if not self.visible:
            return

        self.panel.draw(surface)

        self.city_name_label.draw(surface)
        self.population_label.draw(surface)
        self.yields_label.draw(surface)
        self.food_progress_label.draw(surface)
        self.production_header.draw(surface)
        self.current_production_label.draw(surface)
        self.production_progress_label.draw(surface)
        self.choose_production_label.draw(surface)

        for button in self.production_buttons:
            button.draw(surface)
