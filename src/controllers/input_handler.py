"""
Input handler for keyboard and mouse events.
"""

import pygame
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from config import CAMERA_SPEED


@dataclass
class InputState:
    """Current state of input devices."""
    # Keyboard
    keys_pressed: set = field(default_factory=set)

    # Mouse
    mouse_x: int = 0
    mouse_y: int = 0
    mouse_buttons: tuple = (False, False, False)

    # Camera movement
    camera_dx: float = 0.0
    camera_dy: float = 0.0


class InputHandler:
    """Handles all input processing."""

    def __init__(self):
        self.state = InputState()

        # Callbacks
        self.on_hex_click: Optional[Callable[[int, int], None]] = None
        self.on_hex_hover: Optional[Callable[[int, int], None]] = None
        self.on_quit: Optional[Callable[[], None]] = None

        # Key bindings for camera movement
        self.camera_keys = {
            pygame.K_LEFT: (-CAMERA_SPEED, 0),
            pygame.K_RIGHT: (CAMERA_SPEED, 0),
            pygame.K_UP: (0, -CAMERA_SPEED),
            pygame.K_DOWN: (0, CAMERA_SPEED),
            pygame.K_a: (-CAMERA_SPEED, 0),
            pygame.K_d: (CAMERA_SPEED, 0),
            pygame.K_w: (0, -CAMERA_SPEED),
            pygame.K_s: (0, CAMERA_SPEED),
        }

    def process_event(self, event: pygame.event.Event) -> Dict[str, Any]:
        """
        Process a single pygame event.
        Returns dict of actions to be handled by controller.
        """
        actions = {}

        if event.type == pygame.QUIT:
            actions['quit'] = True
            if self.on_quit:
                self.on_quit()

        elif event.type == pygame.KEYDOWN:
            self.state.keys_pressed.add(event.key)

            # Special key actions
            if event.key == pygame.K_ESCAPE:
                actions['deselect'] = True

        elif event.type == pygame.KEYUP:
            self.state.keys_pressed.discard(event.key)

        elif event.type == pygame.MOUSEMOTION:
            self.state.mouse_x, self.state.mouse_y = event.pos
            actions['mouse_move'] = event.pos

            if self.on_hex_hover:
                self.on_hex_hover(event.pos[0], event.pos[1])

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                actions['left_click'] = event.pos

                if self.on_hex_click:
                    self.on_hex_click(event.pos[0], event.pos[1])

            elif event.button == 3:  # Right click
                actions['right_click'] = event.pos

        elif event.type == pygame.MOUSEBUTTONUP:
            pass  # Handle drag end if needed

        return actions

    def update(self) -> InputState:
        """
        Update continuous input state (held keys, etc.)
        Returns the current input state.
        """
        # Calculate camera movement from held keys
        self.state.camera_dx = 0.0
        self.state.camera_dy = 0.0

        for key in self.state.keys_pressed:
            if key in self.camera_keys:
                dx, dy = self.camera_keys[key]
                self.state.camera_dx += dx
                self.state.camera_dy += dy

        return self.state

    def is_key_pressed(self, key: int) -> bool:
        """Check if a key is currently pressed."""
        return key in self.state.keys_pressed

    def get_mouse_position(self) -> tuple:
        """Get current mouse position."""
        return (self.state.mouse_x, self.state.mouse_y)
