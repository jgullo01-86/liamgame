"""
Game map model with procedural terrain generation using Perlin noise.
"""

import random
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Tuple
from enum import Enum

from src.utils.hex_utils import HexCoord, hex_neighbors, is_valid_hex
from config import TERRAIN_MOVEMENT_COSTS, MAP_WIDTH, MAP_HEIGHT


# Simple Perlin-like noise implementation (value noise with interpolation)
def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _fade(t: float) -> float:
    return t * t * t * (t * (t * 6 - 15) + 10)


class SimpleNoise:
    """Simple value noise generator."""

    def __init__(self, seed: int = 0):
        self.seed = seed
        random.seed(seed)
        self.perm = list(range(256))
        random.shuffle(self.perm)
        self.perm += self.perm  # Double for wrapping

    def _hash(self, xi: int, yi: int) -> float:
        """Get a pseudo-random value for grid point."""
        n = self.perm[(self.perm[xi % 256] + yi) % 256]
        return n / 255.0

    def noise2d(self, x: float, y: float) -> float:
        """Generate 2D noise value in range [0, 1]."""
        xi = int(math.floor(x)) & 255
        yi = int(math.floor(y)) & 255

        xf = x - math.floor(x)
        yf = y - math.floor(y)

        u = _fade(xf)
        v = _fade(yf)

        # Get values at corners
        aa = self._hash(xi, yi)
        ab = self._hash(xi, yi + 1)
        ba = self._hash(xi + 1, yi)
        bb = self._hash(xi + 1, yi + 1)

        # Bilinear interpolation
        x1 = _lerp(aa, ba, u)
        x2 = _lerp(ab, bb, u)
        return _lerp(x1, x2, v)

    def octave_noise(self, x: float, y: float, octaves: int = 4, persistence: float = 0.5) -> float:
        """Generate multi-octave noise."""
        total = 0.0
        frequency = 1.0
        amplitude = 1.0
        max_value = 0.0

        for _ in range(octaves):
            total += self.noise2d(x * frequency, y * frequency) * amplitude
            max_value += amplitude
            amplitude *= persistence
            frequency *= 2.0

        return total / max_value


class TerrainType(Enum):
    """Terrain types with their properties."""
    GRASSLAND = 'grassland'
    PLAINS = 'plains'
    DESERT = 'desert'
    HILLS = 'hills'
    MOUNTAINS = 'mountains'
    FOREST = 'forest'
    COAST = 'coast'
    OCEAN = 'ocean'


@dataclass
class Tile:
    """Represents a single hex tile on the map."""
    coord: HexCoord
    terrain: TerrainType
    elevation: float = 0.0
    moisture: float = 0.0
    explored: bool = False  # Fog of war — explored by nearby units
    visible: bool = True    # Currently visible

    @property
    def movement_cost(self) -> Optional[int]:
        """Get movement cost for this tile. None means impassable."""
        return TERRAIN_MOVEMENT_COSTS.get(self.terrain.value)

    @property
    def is_passable(self) -> bool:
        """Check if units can move through this tile."""
        cost = self.movement_cost
        return cost is not None

    def __hash__(self):
        return hash(self.coord)


class GameMap:
    """
    The game map containing all tiles.
    Uses axial coordinates for hex grid.
    """

    def __init__(self, width: int = MAP_WIDTH, height: int = MAP_HEIGHT, seed: Optional[int] = None):
        self.width = width
        self.height = height
        self.seed = seed if seed is not None else random.randint(0, 999999)
        self.tiles: Dict[HexCoord, Tile] = {}

        self._generate_map()

    def _generate_map(self):
        """Generate the map using Perlin noise for terrain."""
        random.seed(self.seed)

        # Create noise generators
        elevation_noise = SimpleNoise(self.seed)
        moisture_noise = SimpleNoise(self.seed + 1000)

        # Generation parameters
        elevation_scale = 0.1
        moisture_scale = 0.08

        # Thresholds for terrain types (adjusted for more land)
        ocean_threshold = 0.25
        coast_threshold = 0.32
        mountain_threshold = 0.82
        hill_threshold = 0.68
        forest_moisture = 0.58
        desert_moisture = 0.28

        for q in range(self.width):
            for r_offset in range(self.height):
                # Convert offset coordinates to axial
                r = r_offset - q // 2

                coord = HexCoord(q, r)

                # Generate elevation using our noise
                elevation = elevation_noise.octave_noise(
                    q * elevation_scale,
                    r_offset * elevation_scale,
                    octaves=4,
                    persistence=0.5
                )

                # Generate moisture
                moisture = moisture_noise.octave_noise(
                    q * moisture_scale,
                    r_offset * moisture_scale,
                    octaves=3,
                    persistence=0.5
                )

                # Add island-like falloff at edges
                edge_distance = self._edge_distance(q, r_offset)
                elevation = elevation * edge_distance

                # Determine terrain type based on elevation and moisture
                terrain = self._determine_terrain(
                    elevation, moisture,
                    ocean_threshold, coast_threshold,
                    mountain_threshold, hill_threshold,
                    forest_moisture, desert_moisture
                )

                tile = Tile(
                    coord=coord,
                    terrain=terrain,
                    elevation=elevation,
                    moisture=moisture
                )
                self.tiles[coord] = tile

        # Post-process: ensure coasts are next to ocean
        self._process_coasts()

    def _edge_distance(self, q: int, r: int) -> float:
        """Calculate distance factor from map edges (for continent-style generation)."""
        # Normalize coordinates to [0, 1]
        nx = q / self.width
        ny = r / self.height

        # Distance from center (0.5, 0.5)
        dx = abs(nx - 0.5) * 2
        dy = abs(ny - 0.5) * 2

        # Softer falloff - only affects very edges
        edge_factor = 1 - (max(dx, dy) ** 3)
        return max(0.2, min(1.0, edge_factor + 0.3))

    def _determine_terrain(
        self, elevation: float, moisture: float,
        ocean_threshold: float, coast_threshold: float,
        mountain_threshold: float, hill_threshold: float,
        forest_moisture: float, desert_moisture: float
    ) -> TerrainType:
        """Determine terrain type based on elevation and moisture."""

        if elevation < ocean_threshold:
            return TerrainType.OCEAN
        elif elevation < coast_threshold:
            return TerrainType.COAST
        elif elevation > mountain_threshold:
            return TerrainType.MOUNTAINS
        elif elevation > hill_threshold:
            return TerrainType.HILLS
        else:
            # Land terrain based on moisture
            if moisture < desert_moisture:
                return TerrainType.DESERT
            elif moisture > forest_moisture:
                return TerrainType.FOREST
            elif moisture > 0.4:
                return TerrainType.GRASSLAND
            else:
                return TerrainType.PLAINS

    def _process_coasts(self):
        """Ensure coast tiles are adjacent to ocean."""
        coast_tiles = [t for t in self.tiles.values() if t.terrain == TerrainType.COAST]

        for tile in coast_tiles:
            neighbors = self.get_neighbors(tile.coord)
            has_ocean = any(n.terrain == TerrainType.OCEAN for n in neighbors)
            has_land = any(n.terrain not in (TerrainType.OCEAN, TerrainType.COAST) for n in neighbors)

            if not has_ocean:
                # Convert inland "coast" to plains
                tile.terrain = TerrainType.PLAINS
            elif not has_land:
                # Coast surrounded by ocean becomes ocean
                tile.terrain = TerrainType.OCEAN

    def get_tile(self, coord: HexCoord) -> Optional[Tile]:
        """Get tile at the given coordinates."""
        return self.tiles.get(coord)

    def get_neighbors(self, coord: HexCoord) -> List[Tile]:
        """Get all neighboring tiles."""
        neighbors = []
        for neighbor_coord in hex_neighbors(coord):
            tile = self.get_tile(neighbor_coord)
            if tile:
                neighbors.append(tile)
        return neighbors

    def is_valid_coord(self, coord: HexCoord) -> bool:
        """Check if coordinate is within map bounds."""
        return coord in self.tiles

    def get_passable_neighbors(self, coord: HexCoord) -> List[Tile]:
        """Get neighboring tiles that units can move to."""
        return [t for t in self.get_neighbors(coord) if t.is_passable]

    def find_spawn_location(self) -> Optional[HexCoord]:
        """Find a suitable spawn location for a unit (passable land tile)."""
        land_tiles = [
            t for t in self.tiles.values()
            if t.is_passable and t.terrain not in (TerrainType.OCEAN, TerrainType.COAST)
        ]
        if land_tiles:
            center_q = self.width // 2
            center_r = self.height // 2 - center_q // 2
            center = HexCoord(center_q, center_r)
            land_tiles.sort(key=lambda t: abs(t.coord.q - center.q) + abs(t.coord.r - center.r))
            return random.choice(land_tiles[:max(1, len(land_tiles) // 4)]).coord
        return None

    def find_spawn_location_far_from(self, avoid: HexCoord) -> Optional[HexCoord]:
        """Find a spawn location far from the given coordinate."""
        from src.utils.hex_utils import hex_distance
        land_tiles = [
            t for t in self.tiles.values()
            if t.is_passable and t.terrain not in (TerrainType.OCEAN, TerrainType.COAST)
        ]
        if land_tiles:
            # Sort by distance from avoid point (farthest first)
            land_tiles.sort(key=lambda t: hex_distance(t.coord, avoid), reverse=True)
            # Pick from the farthest quarter
            far_tiles = land_tiles[:max(1, len(land_tiles) // 4)]
            return random.choice(far_tiles).coord
        return None

    def __iter__(self):
        """Iterate over all tiles."""
        return iter(self.tiles.values())
