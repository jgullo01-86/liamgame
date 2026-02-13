from ursina import Entity, Text, Button, Color, color, camera, destroy
from typing import Optional, Callable, List


def _c(r, g, b, a=255):
    """Create a Color with 0-255 values normalized to 0-1 for Panda3D."""
    return Color(r / 255, g / 255, b / 255, a / 255)


class MainMenu:
    """Full-screen main menu overlay for Civilization Deluxe."""

    def __init__(self):
        self.visible: bool = True
        self.on_new_game: Optional[Callable] = None
        self.on_how_to_play: Optional[Callable] = None
        self.on_quit: Optional[Callable] = None
        self._elements: List = []

        self._build()

    def _build(self):
        """Create all menu UI elements."""

        # Full-screen dark overlay
        overlay = Entity(
            parent=camera.ui,
            model='quad',
            color=_c(15, 18, 28, 240),
            scale=(2, 2),
            z=0.1
        )
        self._elements.append(overlay)

        # Title
        title = Text(
            text='CIVILIZATION DELUXE',
            parent=camera.ui,
            origin=(0, 0),
            position=(0, 0.22),
            scale=3.5,
            color=_c(218, 165, 32)
        )
        self._elements.append(title)

        # Subtitle
        subtitle = Text(
            text='A 4X Strategy Game',
            parent=camera.ui,
            origin=(0, 0),
            position=(0, 0.14),
            scale=1.2,
            color=_c(180, 180, 190)
        )
        self._elements.append(subtitle)

        # Decorative line below subtitle
        line = Entity(
            parent=camera.ui,
            model='quad',
            color=_c(218, 165, 32),
            scale=(0.3, 0.001),
            position=(0, 0.10)
        )
        self._elements.append(line)

        # New Game button
        btn_new_game = Button(
            text='New Game',
            parent=camera.ui,
            position=(0, 0.02),
            scale=(0.25, 0.055),
            color=_c(50, 90, 50),
            highlight_color=_c(70, 120, 70),
            on_click=self._on_new_game_click
        )
        self._elements.append(btn_new_game)

        # How to Play button
        btn_how_to_play = Button(
            text='How to Play',
            parent=camera.ui,
            position=(0, -0.06),
            scale=(0.25, 0.055),
            color=_c(50, 70, 100),
            highlight_color=_c(70, 90, 130),
            on_click=self._on_how_to_play_click
        )
        self._elements.append(btn_how_to_play)

        # Quit button
        btn_quit = Button(
            text='Quit',
            parent=camera.ui,
            position=(0, -0.14),
            scale=(0.25, 0.055),
            color=_c(100, 50, 50),
            highlight_color=_c(130, 70, 70),
            on_click=self._on_quit_click
        )
        self._elements.append(btn_quit)

        # Version text at the bottom
        version = Text(
            text='v1.0',
            parent=camera.ui,
            origin=(0, 0),
            position=(0, -0.45),
            scale=0.8,
            color=color.gray
        )
        self._elements.append(version)

    def _on_new_game_click(self):
        if self.on_new_game:
            self.on_new_game()

    def _on_how_to_play_click(self):
        if self.on_how_to_play:
            self.on_how_to_play()

    def _on_quit_click(self):
        if self.on_quit:
            self.on_quit()

    def show(self):
        """Make all menu elements visible."""
        self.visible = True
        for element in self._elements:
            element.visible = True

    def hide(self):
        """Make all menu elements invisible."""
        self.visible = False
        for element in self._elements:
            element.visible = False

    def destroy(self):
        """Destroy all menu elements and clear the list."""
        for element in self._elements:
            destroy(element)
        self._elements.clear()
        self.visible = False
