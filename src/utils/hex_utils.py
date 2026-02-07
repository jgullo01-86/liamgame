"""
Hexagonal grid utilities using axial coordinates (q, r).
Uses pointy-top hexagons.
"""

import math
from typing import Tuple, List, Set
from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class HexCoord:
    """Axial coordinate for a hexagon."""
    q: int
    r: int

    def __add__(self, other: 'HexCoord') -> 'HexCoord':
        return HexCoord(self.q + other.q, self.r + other.r)

    def __sub__(self, other: 'HexCoord') -> 'HexCoord':
        return HexCoord(self.q - other.q, self.r - other.r)

    def __hash__(self):
        return hash((self.q, self.r))

    def to_tuple(self) -> Tuple[int, int]:
        return (self.q, self.r)

    @staticmethod
    def from_tuple(t: Tuple[int, int]) -> 'HexCoord':
        return HexCoord(t[0], t[1])

    @property
    def s(self) -> int:
        """Third cube coordinate (q + r + s = 0)."""
        return -self.q - self.r


# Direction vectors for the 6 neighbors of a hex (pointy-top)
HEX_DIRECTIONS = [
    HexCoord(1, 0),   # East
    HexCoord(1, -1),  # Northeast
    HexCoord(0, -1),  # Northwest
    HexCoord(-1, 0),  # West
    HexCoord(-1, 1),  # Southwest
    HexCoord(0, 1),   # Southeast
]


def hex_neighbor(coord: HexCoord, direction: int) -> HexCoord:
    """Get the neighbor hex in the given direction (0-5)."""
    return coord + HEX_DIRECTIONS[direction % 6]


def hex_neighbors(coord: HexCoord) -> List[HexCoord]:
    """Get all 6 neighboring hexes."""
    return [coord + d for d in HEX_DIRECTIONS]


def hex_distance(a: HexCoord, b: HexCoord) -> int:
    """Calculate the distance between two hexes in hex steps."""
    diff = a - b
    return (abs(diff.q) + abs(diff.q + diff.r) + abs(diff.r)) // 2


def hex_to_pixel(coord: HexCoord, hex_size: float) -> Tuple[float, float]:
    """
    Convert axial hex coordinates to pixel coordinates.
    Returns the center point of the hex.
    """
    x = hex_size * (math.sqrt(3) * coord.q + math.sqrt(3) / 2 * coord.r)
    y = hex_size * (3 / 2 * coord.r)
    return (x, y)


def pixel_to_hex(x: float, y: float, hex_size: float) -> HexCoord:
    """
    Convert pixel coordinates to axial hex coordinates.
    Uses rounding to find the nearest hex.
    """
    q = (math.sqrt(3) / 3 * x - 1 / 3 * y) / hex_size
    r = (2 / 3 * y) / hex_size
    return hex_round(q, r)


def hex_round(q: float, r: float) -> HexCoord:
    """Round fractional hex coordinates to the nearest hex."""
    s = -q - r

    rq = round(q)
    rr = round(r)
    rs = round(s)

    q_diff = abs(rq - q)
    r_diff = abs(rr - r)
    s_diff = abs(rs - s)

    if q_diff > r_diff and q_diff > s_diff:
        rq = -rr - rs
    elif r_diff > s_diff:
        rr = -rq - rs
    # else: rs = -rq - rr (not needed)

    return HexCoord(int(rq), int(rr))


def hex_corners(center: Tuple[float, float], hex_size: float) -> List[Tuple[float, float]]:
    """
    Get the 6 corner points of a hex given its center.
    Returns points for a pointy-top hexagon.
    """
    corners = []
    for i in range(6):
        angle = math.pi / 180 * (60 * i - 30)  # Pointy-top: start at -30 degrees
        corner_x = center[0] + hex_size * math.cos(angle)
        corner_y = center[1] + hex_size * math.sin(angle)
        corners.append((corner_x, corner_y))
    return corners


def hex_range(center: HexCoord, radius: int) -> Set[HexCoord]:
    """Get all hexes within a given radius of the center hex."""
    results = set()
    for q in range(-radius, radius + 1):
        for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1):
            results.add(center + HexCoord(q, r))
    return results


def hex_ring(center: HexCoord, radius: int) -> List[HexCoord]:
    """Get all hexes exactly at the given radius from center."""
    if radius == 0:
        return [center]

    results = []
    # Start at the hex to the east and go around
    current = center + HexCoord(radius, 0)

    for i in range(6):
        for _ in range(radius):
            results.append(current)
            current = hex_neighbor(current, (i + 2) % 6)

    return results


def hex_line(start: HexCoord, end: HexCoord) -> List[HexCoord]:
    """Get all hexes in a line from start to end."""
    n = hex_distance(start, end)
    if n == 0:
        return [start]

    results = []
    for i in range(n + 1):
        t = i / n
        q = start.q + (end.q - start.q) * t
        r = start.r + (end.r - start.r) * t
        results.append(hex_round(q, r))

    return results


def is_valid_hex(coord: HexCoord, map_width: int, map_height: int) -> bool:
    """Check if a hex coordinate is within map bounds."""
    # For offset storage, we need to check both q and converted row
    if coord.q < 0 or coord.q >= map_width:
        return False

    # Calculate the row index for this hex
    row = coord.r + coord.q // 2
    if row < 0 or row >= map_height:
        return False

    return True


# =============================================================================
# 3D Coordinate Functions (for Ursina)
# =============================================================================

def hex_to_world_3d(coord: HexCoord, hex_size: float, height: float = 0.0) -> Tuple[float, float, float]:
    """
    Convert axial hex coordinates to 3D world coordinates.
    Returns (x, y, z) where Y is up (Ursina convention).
    The hex grid is laid out in the XZ plane.
    Uses FLAT-TOP hex layout.
    """
    # Flat-top hex layout in XZ plane
    x = hex_size * (3 / 2 * coord.q)
    z = hex_size * (math.sqrt(3) * (coord.r + coord.q / 2))
    y = height
    return (x, y, z)


def hex_corners_3d(hex_size: float) -> List[Tuple[float, float]]:
    """
    Get the 6 corner points of a hex in local XZ coordinates (for mesh generation).
    Returns points for a FLAT-TOP hexagon centered at origin.
    """
    corners = []
    for i in range(6):
        angle = math.pi / 180 * (60 * i)  # Flat-top: start at 0 degrees
        x = hex_size * math.cos(angle)
        z = hex_size * math.sin(angle)
        corners.append((x, z))
    return corners
