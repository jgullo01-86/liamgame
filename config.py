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
HEX_3D_HEIGHT = 0.5  # Base prism height

# Terrain heights (Y-axis offset from base)
TERRAIN_HEIGHTS = {
    'ocean': -0.3,
    'coast': -0.1,
    'grassland': 0.0,
    'plains': 0.0,
    'desert': 0.0,
    'forest': 0.0,
    'hills': 0.3,
    'mountains': 0.6,  # Base height, peaks can be up to 0.9
}

# Terrain 3D colors (RGB 0-255) - brighter for visibility
TERRAIN_COLORS_3D = {
    'grassland': (100, 180, 80),    # Bright green
    'plains': (200, 180, 100),      # Tan/wheat
    'desert': (230, 210, 150),      # Sandy yellow
    'hills': (160, 140, 100),       # Brown
    'mountains': (140, 135, 130),   # Gray
    'forest': (60, 120, 60),        # Dark green
    'coast': (120, 200, 240),       # Light blue
    'ocean': (70, 130, 200),        # Deep blue
}

# 3D Camera settings
CAMERA_3D_DISTANCE = 20  # Closer default view
CAMERA_3D_ANGLE = 55  # Steeper angle to see map better
CAMERA_3D_ZOOM_MIN = 8
CAMERA_3D_ZOOM_MAX = 60
CAMERA_3D_PAN_SPEED = 0.5
CAMERA_3D_ROTATE_SPEED = 100
