import pygame
from .settings import *
from .support import opaque_bounds_rect
from .paths import asset_path

class Grass(pygame.sprite.Sprite):
    def __init__(self, topleft_pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=topleft_pos)
        self.z = LAYERS['grass']

class Floor(pygame.sprite.Sprite):
    def __init__(self, topleft_pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=topleft_pos)
        self.z = LAYERS['floor']

class Wall(pygame.sprite.Sprite):
    def __init__(self, topleft_pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft=topleft_pos)
        self.z = LAYERS['wall']

        # Hitbox: only cover non-transparent pixels (world coordinates)
        local = opaque_bounds_rect(self.image)
        self.hitbox = local.move(self.rect.topleft)

class Door(pygame.sprite.Sprite):
    def __init__(self, topleft_pos, surf_closed, surf_open, groups, collision_group, *, house_cell=None, is_open=False):
        super().__init__(groups)
        self.surf_closed = surf_closed
        self.surf_open = surf_open
        self.house_cell = house_cell

        # Precompute non-transparent bounds (local coordinates)
        self._local_hitbox_closed = opaque_bounds_rect(self.surf_closed)
        self._local_hitbox_open = opaque_bounds_rect(self.surf_open)

        self.is_open = False
        self.image = self.surf_closed
        self.rect = self.image.get_rect(topleft=topleft_pos)
        self.z = LAYERS['door']

        self.collision_group = collision_group
        self.hitbox = self._local_hitbox_closed.move(self.rect.topleft)
        self.set_open(bool(is_open))

    def set_open(self, is_open: bool):
        """Update sprite image/collision from the authoritative model state."""
        self.is_open = bool(is_open)
        old_topleft = self.rect.topleft
        self.image = self.surf_open if self.is_open else self.surf_closed
        self.rect = self.image.get_rect(topleft=old_topleft)

        if self.is_open:
            if self in self.collision_group:
                self.collision_group.remove(self)
            self.hitbox = self._local_hitbox_open.move(self.rect.topleft)
        else:
            if self not in self.collision_group:
                self.collision_group.add(self)
            self.hitbox = self._local_hitbox_closed.move(self.rect.topleft)

class AC(pygame.sprite.Sprite):
    def __init__(self, topleft_pos, groups):
        super().__init__(groups)
        self.power = 0  # -5 to 5
        self.load_images()
        self.update_image()
        self.rect = self.image.get_rect(topleft=topleft_pos)
        self.z = LAYERS['ac']

    def load_images(self):
        self.images = {}
        for i in range(-5, 6):
            self.images[i] = pygame.image.load(str(asset_path('image', 'environment', 'ac', f'{i}.bmp'))).convert_alpha()

    def update_image(self):
        self.image = self.images[self.power]

    def set_power(self, power):
        self.power = max(-5, min(5, power))
        self.update_image()

class SelectedIndicator(pygame.sprite.Sprite):
    """Selection box (placeable/interactable/editing), rendered above all."""
    _cache = {}

    def __init__(self, topleft_pos, color_name: str, groups):
        super().__init__(groups)
        self.z = LAYERS['ui']
        self._color_name = None
        self._set_image(color_name)
        self.rect = self.image.get_rect(topleft=topleft_pos)

    def _set_image(self, color_name: str):
        if color_name not in SelectedIndicator._cache:
            SelectedIndicator._cache[color_name] = pygame.image.load(
                str(asset_path('image', 'ui', 'selected', f'{color_name}.bmp'))
            ).convert_alpha()
        self.image = SelectedIndicator._cache[color_name]

    def set_state(self, topleft_pos, color_name: str):
        """Move and change color."""
        if self._color_name != color_name:
            self._set_image(color_name)
            self._color_name = color_name
        self.rect.topleft = topleft_pos

class CandidateIndicator(pygame.sprite.Sprite):
    """AC candidate marker (blue). Must render below SelectedIndicator."""
    _surf = None

    def __init__(self, topleft_pos, groups):
        super().__init__(groups)
        self.z = LAYERS['ac']  # below UI selection box
        if CandidateIndicator._surf is None:
            CandidateIndicator._surf = pygame.image.load(
                str(asset_path('image', 'ui', 'selected', 'blue.bmp'))
            ).convert_alpha()
        self.image = CandidateIndicator._surf
        self.rect = self.image.get_rect(topleft=topleft_pos)
