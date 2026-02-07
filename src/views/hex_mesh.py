"""
3D Hex prism mesh generation for Ursina.
"""

from ursina import Entity, Mesh, Vec3, color
from typing import List, Tuple, Optional
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import HEX_3D_SIZE, HEX_3D_HEIGHT, TERRAIN_HEIGHTS, TERRAIN_COLORS_3D
from src.utils.hex_utils import HexCoord, hex_to_world_3d, hex_corners_3d

# Cache the hex mesh so we only create it once
_cached_hex_mesh = None


def get_hex_mesh() -> Mesh:
    """Get or create the shared hex prism mesh."""
    global _cached_hex_mesh
    if _cached_hex_mesh is None:
        _cached_hex_mesh = create_hex_prism_mesh()
    return _cached_hex_mesh


def create_hex_prism_mesh(hex_size: float = HEX_3D_SIZE, prism_height: float = HEX_3D_HEIGHT) -> Mesh:
    """Create a hexagonal prism mesh in the XZ plane."""
    corners = hex_corners_3d(hex_size)

    vertices = []
    triangles = []
    uvs = []
    normals = []

    # Top face
    top_start = 0
    for x, z in corners:
        vertices.append(Vec3(x, 0, z))
        normals.append(Vec3(0, 1, 0))
        uvs.append((x / hex_size * 0.5 + 0.5, z / hex_size * 0.5 + 0.5))

    center_idx = len(vertices)
    vertices.append(Vec3(0, 0, 0))
    normals.append(Vec3(0, 1, 0))
    uvs.append((0.5, 0.5))

    for i in range(6):
        next_i = (i + 1) % 6
        triangles.extend([center_idx, top_start + i, top_start + next_i])

    # Bottom face
    bottom_start = len(vertices)
    for x, z in corners:
        vertices.append(Vec3(x, -prism_height, z))
        normals.append(Vec3(0, -1, 0))
        uvs.append((x / hex_size * 0.5 + 0.5, z / hex_size * 0.5 + 0.5))

    bottom_center_idx = len(vertices)
    vertices.append(Vec3(0, -prism_height, 0))
    normals.append(Vec3(0, -1, 0))
    uvs.append((0.5, 0.5))

    for i in range(6):
        next_i = (i + 1) % 6
        triangles.extend([bottom_center_idx, bottom_start + next_i, bottom_start + i])

    # Side faces
    for i in range(6):
        next_i = (i + 1) % 6
        x1, z1 = corners[i]
        x2, z2 = corners[next_i]
        mid_x = (x1 + x2) / 2
        mid_z = (z1 + z2) / 2
        length = math.sqrt(mid_x**2 + mid_z**2)
        if length > 0:
            normal = Vec3(mid_x / length, 0, mid_z / length)
        else:
            normal = Vec3(1, 0, 0)

        side_start = len(vertices)
        vertices.extend([
            Vec3(x1, 0, z1),
            Vec3(x2, 0, z2),
            Vec3(x2, -prism_height, z2),
            Vec3(x1, -prism_height, z1),
        ])
        normals.extend([normal] * 4)
        uvs.extend([(0, 1), (1, 1), (1, 0), (0, 0)])

        triangles.extend([side_start, side_start + 1, side_start + 2])
        triangles.extend([side_start, side_start + 2, side_start + 3])

    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, normals=normals)


class HexTile3D(Entity):
    """A single 3D hex tile entity with proper hexagonal shape."""

    def __init__(self, coord: HexCoord, terrain_type: str, elevation: float = 0.0, **kwargs):
        self.coord = coord
        self.terrain_type = terrain_type

        base_height = TERRAIN_HEIGHTS.get(terrain_type, 0.0)
        if terrain_type == 'mountains':
            base_height = 0.6 + elevation * 0.3

        self.terrain_height = base_height

        x, y, z = hex_to_world_3d(coord, HEX_3D_SIZE, base_height)

        rgb = TERRAIN_COLORS_3D.get(terrain_type, (128, 128, 128))
        tile_color = color.rgb(rgb[0], rgb[1], rgb[2])

        # Use actual hex mesh
        hex_mesh = get_hex_mesh()

        # Scale Y for taller prisms on elevated terrain
        y_scale = 1.0 + abs(base_height) * 2

        super().__init__(
            model=hex_mesh,
            color=tile_color,
            position=(x, base_height, z),
            scale=(1, y_scale, 1),
            collider='box',
            **kwargs
        )

        self._base_color = tile_color
        self._is_highlighted = False
        self._is_in_movement_range = False
        self._is_attack_target = False

    def highlight(self, on: bool = True):
        self._is_highlighted = on
        self._update_color()

    def set_movement_range(self, in_range: bool = True):
        self._is_in_movement_range = in_range
        self._update_color()

    def set_attack_target(self, is_target: bool = True):
        self._is_attack_target = is_target
        self._update_color()

    def _update_color(self):
        if self._is_attack_target:
            self.color = color.rgb(255, 100, 100)
        elif self._is_in_movement_range:
            self.color = color.rgb(100, 255, 100)
        elif self._is_highlighted:
            self.color = color.rgb(255, 255, 150)
        else:
            self.color = self._base_color
