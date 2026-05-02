"""Camera group for drawing world-space sprites onto the virtual screen."""

import pygame
from .settings import SCREEN_WIDTH, SCREEN_HEIGHT


class CameraGroup(pygame.sprite.Group):
    """
    Camera group that draws sprites with an offset.

    - world coords: sprite.rect.topleft
    - screen coords: world - offset
    
    Collaboration notes:
    - Level typically adds *all* visible sprites into this group under key "all".
    - Draw ordering uses an ad-hoc `z` attribute on sprites (not pygame layers).
    """

    def __init__(self):
        """Create an empty camera group with zero offset."""
        super().__init__()
        self.offset = pygame.math.Vector2()

    def custom_draw(self, player, target_surface):
        """
        Draw all sprites into target_surface using camera offset.

        Args:
            player: The player sprite; its rect center anchors the camera.
            target_surface: The surface to draw to (typically the virtual surface).

        Side effects:
        - Updates `self.offset` each call based on player position.
        """
        self.offset.x = player.rect.centerx - SCREEN_WIDTH / 2
        self.offset.y = player.rect.centery - SCREEN_HEIGHT / 2

        # NOTE: Sprites use "z" for draw order (not "layer").
        for spr in sorted(self.sprites(), key=lambda s: getattr(s, "z", 0)):
            if not hasattr(spr, "rect"):
                continue
            offset_pos = spr.rect.topleft - self.offset
            target_surface.blit(spr.image, offset_pos)

    def screen_to_world(self, screen_pos):
        """Convert a virtual/screen position (x, y) into world coordinates."""
        sx, sy = screen_pos
        return (float(sx + self.offset.x), float(sy + self.offset.y))

    def world_to_screen(self, world_pos):
        """Convert world coordinates (x, y) into virtual/screen coordinates."""
        wx, wy = world_pos
        return (float(wx - self.offset.x), float(wy - self.offset.y))
