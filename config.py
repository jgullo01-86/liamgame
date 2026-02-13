"""
Configuration constants for Civilization Deluxe
"""

# Window settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "Civilization Deluxe"

# Map settings
MAP_WIDTH = 40  # Number of hexes horizontally
MAP_HEIGHT = 30  # Number of hexes vertically

# Hex settings (pointy-top hexagons)
HEX_SIZE = 32  # Distance from center to corner
HEX_WIDTH = HEX_SIZE * 2
HEX_HEIGHT = HEX_SIZE * 1.732  # sqrt(3) * size

# Camera settings
CAMERA_SPEED = 10
CAMERA_EDGE_MARGIN = 50

# Colors
COLORS = {
    # UI Colors
    'background': (20, 20, 30),
    'ui_bar': (40, 40, 50),
    'ui_text': (220, 220, 220),
    'ui_button': (60, 80, 100),
    'ui_button_hover': (80, 100, 120),
    'ui_button_text': (255, 255, 255),

    # Selection colors
    'hex_highlight': (255, 255, 100, 100),
    'hex_selected': (100, 200, 255, 150),
    'movement_range': (100, 255, 100, 80),

    # Terrain colors
    'grassland': (86, 152, 72),
    'plains': (170, 160, 90),
    'desert': (210, 190, 130),
    'hills': (140, 120, 80),
    'mountains': (120, 110, 100),
    'forest': (50, 100, 50),
    'coast': (100, 180, 220),
    'ocean': (50, 100, 180),

    # Unit colors
    'unit_friendly': (50, 150, 255),
    'unit_enemy': (255, 80, 80),
}

# Terrain movement costs (None = impassable)
TERRAIN_MOVEMENT_COSTS = {
    'grassland': 1,
    'plains': 1,
    'desert': 1,
    'hills': 2,
    'mountains': None,  # Impassable
    'forest': 2,
    'coast': 1,
    'ocean': None,  # Impassable for land units
}

# Unit settings
DEFAULT_MOVEMENT_POINTS = 2

# Combat settings
TERRAIN_DEFENSE_BONUS = {
    'hills': 0.25,
    'forest': 0.50,
    'mountains': 0.75,
}
COMBAT_RANDOMNESS = 0.3  # +/- 30% random factor

# Victory settings
MAX_TURNS = 100  # Score victory after this many turns
SCORE_PER_POPULATION = 10
SCORE_PER_CITY = 50
SCORE_PER_UNIT = 5
SCORE_PER_GOLD = 0.1

# AI settings
AI_PLAYER_COUNT = 1  # Number of AI opponents

# UI settings
TOP_BAR_HEIGHT = 40
BOTTOM_BAR_HEIGHT = 80
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 30

# =============================================================================
# 3D Settings (Ursina)
# =============================================================================

# 3D Hex settings
HEX_3D_SIZE = 3.0  # Base size in world units (increased for visibility)
HEX_3D_HEIGHT = 0.08  # Very thin prism — flat tiles like Call to Power

# Terrain heights (Y-axis offset from base) — nearly flat, slight variation
TERRAIN_HEIGHTS = {
    'ocean': -0.08,
    'coast': -0.04,
    'grassland': 0.0,
    'plains': 0.0,
    'desert': 0.0,
    'forest': 0.0,
    'hills': 0.06,
    'mountains': 0.12,
}

# Terrain 3D colors (RGB 0-255) - bright, saturated strategy game palette
TERRAIN_COLORS_3D = {
    'grassland': (110, 185, 70),      # Bright green
    'plains': (205, 185, 105),        # Golden wheat
    'desert': (230, 205, 140),        # Warm sand
    'hills': (160, 140, 100),         # Earthy brown
    'mountains': (155, 145, 135),     # Warm gray
    'forest': (55, 140, 55),          # Forest green (brighter)
    'coast': (75, 160, 210),          # Tropical blue
    'ocean': (45, 95, 170),           # Rich blue
}

# 3D Camera settings
CAMERA_3D_DISTANCE = 35  # Default FOV in ortho mode (lower = more zoomed in)
CAMERA_3D_ANGLE = 55  # Isometric angle (degrees from horizontal)
CAMERA_3D_ZOOM_MIN = 10  # Min FOV (most zoomed in)
CAMERA_3D_ZOOM_MAX = 80  # Max FOV (most zoomed out)
CAMERA_3D_PAN_SPEED = 0.5
CAMERA_3D_ROTATE_SPEED = 100
CAMERA_3D_EDGE_SCROLL_MARGIN = 0.02
CAMERA_3D_EDGE_SCROLL_SPEED = 0.3
CAMERA_3D_MIDDLE_PAN_SENSITIVITY = 50.0
