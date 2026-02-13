"""
Orbital camera controller for 3D view.
"""

from ursina import camera, mouse, held_keys, Vec3, time, window
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import (
    CAMERA_3D_DISTANCE, CAMERA_3D_ANGLE,
    CAMERA_3D_ZOOM_MIN, CAMERA_3D_ZOOM_MAX,
    CAMERA_3D_PAN_SPEED, CAMERA_3D_ROTATE_SPEED,
    CAMERA_3D_EDGE_SCROLL_MARGIN, CAMERA_3D_EDGE_SCROLL_SPEED,
    CAMERA_3D_MIDDLE_PAN_SENSITIVITY
)


class OrbitCamera:
    """
    Orbital camera that orbits around a target point.
    - WASD: Pan target point
    - Mouse drag (right button): Rotate orbit
    - Scroll wheel: Zoom in/out
    """

    def __init__(self):
        # Target point (what camera looks at)
        self.target_x = 0.0
        self.target_z = 0.0

        # Orbit parameters
        self.distance = CAMERA_3D_DISTANCE
        self.angle_horizontal = 0.0  # Rotation around Y axis (degrees)
        self.angle_vertical = CAMERA_3D_ANGLE  # Angle from horizontal (degrees)

        # Smoothing
        self._smooth_target_x = 0.0
        self._smooth_target_z = 0.0
        self._smooth_distance = CAMERA_3D_DISTANCE
        self._smooth_angle_h = 0.0
        self._smooth_angle_v = CAMERA_3D_ANGLE

        # Input state
        self._last_mouse_pos = None
        self._middle_drag_active = False
        self._middle_last_pos = None

        self._update_camera_position()

    def reset(self):
        """Reset camera angle and zoom to defaults (preserves map position)."""
        self.distance = CAMERA_3D_DISTANCE
        self.angle_horizontal = 0.0
        self.angle_vertical = CAMERA_3D_ANGLE
        self._smooth_distance = self.distance
        self._smooth_angle_h = self.angle_horizontal
        self._smooth_angle_v = self.angle_vertical
        self._update_camera_position()

    def set_target(self, x: float, z: float):
        """Set the camera target point."""
        self.target_x = x
        self.target_z = z
        self._smooth_target_x = x
        self._smooth_target_z = z
        self._update_camera_position()

    def get_target(self):
        """Return current camera target (x, z)."""
        return (self.target_x, self.target_z)

    def get_viewport_size(self):
        """Return approximate world-space (width, height) visible in ortho mode."""
        fov = self._smooth_distance
        aspect = window.aspect_ratio if window.aspect_ratio else 1.78
        v_rad = math.radians(self._smooth_angle_v)
        # In ortho, fov is vertical extent; ground plane projection stretches by 1/sin(angle)
        return (fov * aspect, fov / max(math.sin(v_rad), 0.3))

    def update(self):
        """Update camera each frame."""
        dt = time.dt

        # Handle WASD panning
        pan_speed = CAMERA_3D_PAN_SPEED * self.distance * 0.1

        # Calculate pan direction based on camera rotation
        angle_rad = math.radians(self.angle_horizontal)
        forward_x = math.sin(angle_rad)
        forward_z = math.cos(angle_rad)
        right_x = math.cos(angle_rad)
        right_z = -math.sin(angle_rad)

        if held_keys['w'] or held_keys['up arrow']:
            self.target_x += forward_x * pan_speed * dt * 60
            self.target_z += forward_z * pan_speed * dt * 60
        if held_keys['s'] or held_keys['down arrow']:
            self.target_x -= forward_x * pan_speed * dt * 60
            self.target_z -= forward_z * pan_speed * dt * 60
        if held_keys['a'] or held_keys['left arrow']:
            self.target_x -= right_x * pan_speed * dt * 60
            self.target_z -= right_z * pan_speed * dt * 60
        if held_keys['d'] or held_keys['right arrow']:
            self.target_x += right_x * pan_speed * dt * 60
            self.target_z += right_z * pan_speed * dt * 60

        # Handle Q/E rotation
        if held_keys['q']:
            self.angle_horizontal -= CAMERA_3D_ROTATE_SPEED * dt
        if held_keys['e']:
            self.angle_horizontal += CAMERA_3D_ROTATE_SPEED * dt

        # Handle mouse rotation (right mouse button drag)
        if mouse.right:
            if self._last_mouse_pos is not None:
                dx = mouse.x - self._last_mouse_pos[0]
                dy = mouse.y - self._last_mouse_pos[1]

                self.angle_horizontal -= dx * CAMERA_3D_ROTATE_SPEED
                self.angle_vertical += dy * CAMERA_3D_ROTATE_SPEED * 0.5

                # Clamp vertical angle
                self.angle_vertical = max(10, min(80, self.angle_vertical))

            self._last_mouse_pos = (mouse.x, mouse.y)
        else:
            self._last_mouse_pos = None

        # Middle mouse button panning
        if self._middle_drag_active:
            if self._middle_last_pos is not None:
                dx = mouse.x - self._middle_last_pos[0]
                dy = mouse.y - self._middle_last_pos[1]

                pan_factor = CAMERA_3D_MIDDLE_PAN_SENSITIVITY * self.distance * 0.01
                self.target_x -= (right_x * dx + forward_x * dy) * pan_factor
                self.target_z -= (right_z * dx + forward_z * dy) * pan_factor

            self._middle_last_pos = (mouse.x, mouse.y)

        # Smooth interpolation
        smooth_factor = min(1.0, dt * 10)
        self._smooth_target_x += (self.target_x - self._smooth_target_x) * smooth_factor
        self._smooth_target_z += (self.target_z - self._smooth_target_z) * smooth_factor
        self._smooth_distance += (self.distance - self._smooth_distance) * smooth_factor
        self._smooth_angle_h += (self.angle_horizontal - self._smooth_angle_h) * smooth_factor
        self._smooth_angle_v += (self.angle_vertical - self._smooth_angle_v) * smooth_factor

        self._update_camera_position()

    def _update_camera_position(self):
        """Update camera position and rotation — orthographic isometric view."""
        # Orthographic projection for flat 2D look (like Call to Power)
        camera.orthographic = True
        camera.fov = self._smooth_distance  # fov controls zoom in ortho mode

        # Calculate camera position in orbit
        h_rad = math.radians(self._smooth_angle_h)
        v_rad = math.radians(self._smooth_angle_v)

        # Position relative to target (far enough to see everything)
        orbit_dist = 100
        y = math.sin(v_rad) * orbit_dist
        horizontal_dist = math.cos(v_rad) * orbit_dist

        x = self._smooth_target_x - math.sin(h_rad) * horizontal_dist
        z = self._smooth_target_z - math.cos(h_rad) * horizontal_dist

        camera.position = Vec3(x, y, z)
        camera.look_at(Vec3(self._smooth_target_x, 0, self._smooth_target_z))

    def input(self, key):
        """Handle discrete input events."""
        # Middle mouse button tracking
        if key == 'middle mouse down':
            self._middle_drag_active = True
            self._middle_last_pos = (mouse.x, mouse.y)
        elif key == 'middle mouse up':
            self._middle_drag_active = False
            self._middle_last_pos = None

        # Scroll wheel
        if key == 'scroll up':
            self.distance *= 0.9
            self.distance = max(CAMERA_3D_ZOOM_MIN, self.distance)
        elif key == 'scroll down':
            self.distance *= 1.1
            self.distance = min(CAMERA_3D_ZOOM_MAX, self.distance)
