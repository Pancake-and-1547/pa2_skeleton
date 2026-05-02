from pygame.math import Vector2

# Screen
SCREEN_WIDTH =  1600
SCREEN_HEIGHT = 720
TILE_SIZE = 64

LAYERS = {
    'grass': 0,
    'floor': 1,
    'wall': 2,
    'door': 3,
    'ac': 4,
    'main': 5,
    'ui': 6,  # Top-most layer (selection boxes, UI overlays)
}

# Temperature ranges for grass types
TEMPERATURE_RANGES = {
    'universe': (-float('inf'), -40),
    'winter': (-40, 0),
    'fall': (0, 13),
    'spring': (13, 26),
    'summer': (26, 40),
    'heaven': (40, float('inf'))
}

def get_grass_type(temperature):
    """Get grass type based on temperature."""
    for grass_type, (min_temp, max_temp) in TEMPERATURE_RANGES.items():
        if min_temp < temperature <= max_temp:
            return grass_type
    return 'spring'

PLAYER_TOOL_OFFSET = {
    'left': Vector2(-50, 5),
    'right': Vector2(50, 5),
    'up': Vector2(0, -35),
    'down': Vector2(0, 50)
}