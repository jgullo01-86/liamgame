"""
3D Hex prism mesh generation for Ursina.
"""

from ursina import Entity, Mesh, Vec3, color
from typing import List, Tuple, Optional
import math
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import HEX_3D_SIZE, HEX_3D_HEIGHT, TERRAIN_HEIGHTS, TERRAIN_COLORS_3D
from src.utils.hex_utils import HexCoord, hex_to_world_3d, hex_corners_3d


def create_hex_prism_mesh(hex_size: float = HEX_3D_SIZE, prism_height: float = HEX_3D_HEIGHT) -> Mesh:
    """
    Create a hexagonal prism mesh.
    The hex is in the XZ plane, prism extends down in -Y.
    """
    corners = hex_corners_3d(hex_size)

    vertices = []
    triangles = []
    uvs = []
    normals = []

    # Top face vertices (Y = 0)
    top_start = 0
    for x, z in corners:
        vertices.append(Vec3(x, 0, z))
        normals.append(Vec3(0, 1, 0))
        uvs.append((x / hex_size * 0.5 + 0.5, z / hex_size * 0.5 + 0.5))

    # Top face triangles (fan from center)
    # Add center vertex
    center_idx = len(vertices)
    vertices.append(Vec3(0, 0, 0))
    normals.append(Vec3(0, 1, 0))
    uvs.append((0.5, 0.5))

    for i in range(6):
        next_i = (i + 1) % 6
        triangles.extend([center_idx, top_start + i, top_start + next_i])

    # Bottom face vertices (Y = -prism_height)
    bottom_start = len(vertices)
    for x, z in corners:
        vertices.append(Vec3(x, -prism_height, z))
        normals.append(Vec3(0, -1, 0))
        uvs.append((x / hex_size * 0.5 + 0.5, z / hex_size * 0.5 + 0.5))

    # Bottom center
    bottom_center_idx = len(vertices)
    vertices.append(Vec3(0, -prism_height, 0))
    normals.append(Vec3(0, -1, 0))
    uvs.append((0.5, 0.5))

    for i in range(6):
        next_i = (i + 1) % 6
        triangles.extend([bottom_center_idx, bottom_start + next_i, bottom_start + i])

    # Side faces (6 quads, each as 2 triangles)
    for i in range(6):
        next_i = (i + 1) % 6

        # Calculate outward normal for this side
        x1, z1 = corners[i]
        x2, z2 = corners[next_i]
        mid_x = (x1 + x2) / 2
        mid_z = (z1 + z2) / 2
        length = math.sqrt(mid_x**2 + mid_z**2)
        if length > 0:
            normal = Vec3(mid_x / length, 0, mid_z / length)
        else:
            normal = Vec3(1, 0, 0)

        # Add 4 vertices for this quad
        side_start = len(vertices)
        vertices.extend([
            Vec3(x1, 0, z1),                    # top left
            Vec3(x2, 0, z2),                    # top right
            Vec3(x2, -prism_height, z2),        # bottom right
            Vec3(x1, -prism_height, z1),        # bottom left
        ])
        normals.extend([normal] * 4)
        uvs.extend([(0, 1), (1, 1), (1, 0), (0, 0)])

        # Two triangles for the quad
        triangles.extend([side_start, side_start + 1, side_start + 2])
        triangles.extend([side_start, side_start + 2, side_start + 3])

    return Mesh(vertices=vertices, triangles=triangles, uvs=uvs, normals=normals)


class HexTile3D(Entity):
    """A single 3D hex tile entity."""

    def __init__(self, coord: HexCoord, terrain_type: str, elevation: float = 0.0, **kwargs):
        self.coord = coord
        self.terrain_type = terrain_type

        # Calculate height based on terrain
        base_height = TERRAIN_HEIGHTS.get(terrain_type, 0.0)

        # Mountains can have variable height based on elevation
        if terrain_type == 'mountains':
            base_height = 0.6 + elevation * 0.3  # Range 0.6 to 0.9

        self.terrain_height = base_height

        # Get world position
        x, y, z = hex_to_world_3d(coord, HEX_3D_SIZE, base_height)

        # Get color (already in 0-255 range)
        rgb = TERRAIN_COLORS_3D.get(terrain_type, (128, 128, 128))
        tile_color = color.rgb(rgb[0], rgb[1], rgb[2])

        # Use cube for now - we'll make proper hexes later
        # Scale based on hex size, with height varying by terrain
        tile_height = HEX_3D_HEIGHT + abs(base_height) * 2
        super().__init__(
            model='cube',
            color=tile_color,
            position=(x, base_height, z),
            scale=(HEX_3D_SIZE * 0.95, tile_height, HEX_3D_SIZE * 0.85),
            **kwargs
        )

        self._base_color = tile_color
        self._is_highlighted = False
        self._is_in_movement_range = False

    def highlight(self, on: bool = True):
        """Toggle highlight state."""
        self._is_highlighted = on
        self._update_color()

    def set_movement_range(self, in_range: bool = True):
        """Toggle movement range indicator."""
        self._is_in_movement_range = in_range
        self._update_color()

    def _update_color(self):
        """Update color based on state."""
        if self._is_in_movement_range:
            # Green tint for movement range
            self.color = color.rgb(100, 255, 100)
        elif self._is_highlighted:
            # Yellow tint for hover
            self.color = color.rgb(255, 255, 150)
        else:
            self.color = self._base_color
