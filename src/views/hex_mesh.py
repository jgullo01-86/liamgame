"""
3D Hex prism mesh generation for Ursina — uses UV-mapped textures with vertex color bevel.
"""

from ursina import Entity, Mesh, Vec3, color, Color, load_texture
from typing import List, Tuple
import math
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import HEX_3D_SIZE, HEX_3D_HEIGHT, TERRAIN_HEIGHTS, TERRAIN_COLORS_3D
from src.utils.hex_utils import HexCoord, hex_to_world_3d, hex_corners_3d

# Terrain type -> texture file mapping
TERRAIN_TEXTURES = {
    'grassland': 'assets/textures/grassland.png',
    'plains': 'assets/textures/plains.png',
    'desert': 'assets/textures/desert.png',
    'hills': 'assets/textures/hills.png',
    'mountains': 'assets/textures/mountains.png',
    'forest': 'assets/textures/forest.png',
    'coast': 'assets/textures/coast.png',
    'ocean': 'assets/textures/ocean.png',
}


def create_colored_hex_mesh(rgb_tuple: Tuple[int, int, int],
                            hex_size: float = HEX_3D_SIZE,
                            prism_height: float = HEX_3D_HEIGHT) -> Mesh:
    """Create a hexagonal prism mesh with UV coordinates and vertex color bevel.

    Top face uses white vertex colors (full texture brightness) with darker outer
    corners for a bevel effect. Side/bottom faces use rgb_tuple vertex colors.
    UV coordinates map the hex top face onto the center of the texture.
    """
    corners = hex_corners_3d(hex_size)
    r, g, b = rgb_tuple[0] / 255, rgb_tuple[1] / 255, rgb_tuple[2] / 255

    vertices = []
    triangles = []
    vert_colors = []
    uvs = []

    # === Top face with 3-zone bevel ===

    # Outer corner vertices (darker white — bevel edge)
    corner_start = 0
    for i, (x, z) in enumerate(corners):
        vertices.append(Vec3(x, 0, z))
        vert_colors.append((0.6, 0.6, 0.6, 1))
        # UV: map position to center of texture square
        u = 0.5 + x / (hex_size * 2)
        v = 0.5 + z / (hex_size * 2)
        uvs.append((u, v))

    # Inner ring vertices at 82% radius (bright white — main tile surface)
    inner_start = len(vertices)
    inner_ratio = 0.82
    for i, (x, z) in enumerate(corners):
        ix, iz = x * inner_ratio, z * inner_ratio
        vertices.append(Vec3(ix, 0, iz))
        vert_colors.append((1.0, 1.0, 1.0, 1))
        u = 0.5 + ix / (hex_size * 2)
        v = 0.5 + iz / (hex_size * 2)
        uvs.append((u, v))

    # Center vertex (bright white)
    center_idx = len(vertices)
    vertices.append(Vec3(0, 0, 0))
    vert_colors.append((1.0, 1.0, 1.0, 1))
    uvs.append((0.5, 0.5))

    # Triangulate: center fan to inner ring
    for i in range(6):
        triangles.extend([center_idx, inner_start + i, inner_start + (i + 1) % 6])

    # Triangulate: inner ring to outer corners (bevel strip)
    for i in range(6):
        ni = (i + 1) % 6
        triangles.extend([inner_start + i, corner_start + i, corner_start + ni])
        triangles.extend([inner_start + i, corner_start + ni, inner_start + ni])

    # Bottom face — darker, no meaningful UV
    bottom_start = len(vertices)
    dr, dg, db = r * 0.4, g * 0.4, b * 0.4
    for x, z in corners:
        vertices.append(Vec3(x, -prism_height, z))
        vert_colors.append((dr, dg, db, 1))
        uvs.append((0, 0))
    bottom_center = len(vertices)
    vertices.append(Vec3(0, -prism_height, 0))
    vert_colors.append((dr, dg, db, 1))
    uvs.append((0, 0))

    for i in range(6):
        triangles.extend([bottom_center, bottom_start + (i + 1) % 6, bottom_start + i])

    # Side faces — gradient from brighter top to darker bottom, no meaningful UV
    for i in range(6):
        ni = (i + 1) % 6
        x1, z1 = corners[i]
        x2, z2 = corners[ni]
        side_start = len(vertices)

        top_shade = 0.8
        bot_shade = 0.45

        vertices.extend([
            Vec3(x1, 0, z1), Vec3(x2, 0, z2),
            Vec3(x2, -prism_height, z2), Vec3(x1, -prism_height, z1),
        ])
        vert_colors.extend([
            (r * top_shade, g * top_shade, b * top_shade, 1),
            (r * top_shade, g * top_shade, b * top_shade, 1),
            (r * bot_shade, g * bot_shade, b * bot_shade, 1),
            (r * bot_shade, g * bot_shade, b * bot_shade, 1),
        ])
        uvs.extend([(0, 0), (0, 0), (0, 0), (0, 0)])
        triangles.extend([side_start, side_start + 1, side_start + 2])
        triangles.extend([side_start, side_start + 2, side_start + 3])

    return Mesh(vertices=vertices, triangles=triangles, colors=vert_colors, uvs=uvs)


class HexTile3D(Entity):
    """A single 3D hex tile entity with UV-mapped texture and vertex color bevel."""

    # Class-level texture cache to avoid loading the same file many times
    _texture_cache = {}

    def __init__(self, coord: HexCoord, terrain_type: str, elevation: float = 0.0, **kwargs):
        self.coord = coord
        self.terrain_type = terrain_type

        base_height = TERRAIN_HEIGHTS.get(terrain_type, 0.0)
        if terrain_type == 'mountains':
            base_height = 0.12 + elevation * 0.04

        self.terrain_height = base_height

        x, y, z = hex_to_world_3d(coord, HEX_3D_SIZE, base_height)

        rgb = TERRAIN_COLORS_3D.get(terrain_type, (128, 128, 128))

        # Per-hex color variation for organic look (deterministic via coord hash)
        rng = random.Random(hash((coord.q, coord.r)))
        r_var, g_var, b_var = rng.randint(-10, 10), rng.randint(-10, 10), rng.randint(-10, 10)
        brightness = 5 if base_height > 0 else (-5 if base_height < 0 else 0)
        rgb = (
            max(0, min(255, rgb[0] + r_var + brightness)),
            max(0, min(255, rgb[1] + g_var + brightness)),
            max(0, min(255, rgb[2] + b_var + brightness)),
        )

        # Each tile gets its own mesh with vertex colors and UVs baked in
        hex_mesh = create_colored_hex_mesh(rgb)

        # Flat tiles — no Y exaggeration
        y_scale = 1.0

        super().__init__(
            model=hex_mesh,
            position=(x, base_height, z),
            scale=(1, y_scale, 1),
            collider='box',
            **kwargs
        )

        # Load and apply terrain texture
        tex_path = TERRAIN_TEXTURES.get(terrain_type)
        if tex_path:
            if tex_path not in HexTile3D._texture_cache:
                HexTile3D._texture_cache[tex_path] = load_texture(tex_path)
            self.texture = HexTile3D._texture_cache[tex_path]

        # Disable lighting so texture + vertex colors show at full brightness
        self.setLightOff()

        self._is_highlighted = False
        self._is_in_movement_range = False
        self._is_attack_target = False

        # Movement/attack overlay (circle fits hex shape better than quad)
        self._overlay = Entity(
            parent=self, model='circle', rotation_x=90,
            scale=(HEX_3D_SIZE * 1.7, HEX_3D_SIZE * 1.7),
            position=(0, 0.15, 0),  # Slightly above tile surface
            visible=False
        )
        self._overlay.setLightOff()

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
        """Use setColorScale to tint vertex colors and show overlay for highlights."""
        if self._is_attack_target:
            self.setColorScale(1.2, 0.6, 0.6, 1)
            self._overlay.visible = True
            self._overlay.color = Color(1, 0.2, 0.2, 0.4)  # Bright red, semi-transparent
        elif self._is_in_movement_range:
            self.setColorScale(0.8, 1.2, 0.8, 1)
            self._overlay.visible = True
            self._overlay.color = Color(0.2, 1, 0.3, 0.4)  # Bright green, semi-transparent
        elif self._is_highlighted:
            self.setColorScale(1.3, 1.3, 1.0, 1)
            self._overlay.visible = False
        else:
            self.setColorScale(1, 1, 1, 1)
            self._overlay.visible = False
