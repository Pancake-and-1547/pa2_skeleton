import pygame
from .settings import *
from .support import *
from .paths import asset_path

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, group, collision_sprites):
        super().__init__(group)

        self.input_enabled = True
        self.state = None

        self.import_assets()
        self.status = 'down_idle'
        self.frame_index = 0

        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(center=pos)
        self.z = LAYERS['main']

        self.direction = pygame.math.Vector2()
        self.pos = pygame.math.Vector2(self.rect.center)
        self.run_speed = 500
        self.walk_speed = 300
        self.speed = self.walk_speed

        self.hitbox = self.rect.copy().inflate((-126, -90))
        self.collision_sprites = collision_sprites

    def import_assets(self):
        self.animations = {
            'up': [], 'down': [], 'left': [], 'right': [],
            'right_idle': [], 'left_idle': [], 'up_idle': [], 'down_idle': []
        }

        for animation in self.animations.keys():
            full_path = asset_path('image', 'character', animation)
            self.animations[animation] = import_folder(full_path)

    def animate(self, dt):
        self.frame_index += 4 * dt
        self.image = self.animations[self.status][int(self.frame_index) % len(self.animations[self.status])]

    def input(self):
        if not self.input_enabled:
            self.direction.x = 0
            self.direction.y = 0
            return

        keys = pygame.key.get_pressed()

        self.direction.y = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.direction.y += -1
            self.status = 'up'
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.direction.y += 1
            self.status = 'down'

        self.direction.x = 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.direction.x += 1
            self.status = 'right'
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.direction.x += -1
            self.status = 'left'

        # run mode is read from shared state 
        run_mode = self.state.run_mode
        self.speed = self.run_speed if run_mode else self.walk_speed

    def get_status(self):
        if self.direction.magnitude() == 0:
            self.status = self.status.split('_')[0] + '_idle'

    def get_target_pos(self):
        return self.rect.center + PLAYER_TOOL_OFFSET[self.status.split('_')[0]]

    def collision(self, direction):
        for sprite in self.collision_sprites.sprites():
            if sprite.hitbox.colliderect(self.hitbox):
                if direction == 'horizontal':
                    if self.direction.x > 0:
                        self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0:
                        self.hitbox.left = sprite.hitbox.right
                    self.rect.centerx = self.hitbox.centerx
                    self.pos.x = self.hitbox.centerx

                if direction == 'vertical':
                    if self.direction.y > 0:
                        self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0:
                        self.hitbox.top = sprite.hitbox.bottom
                    self.rect.centery = self.hitbox.centery
                    self.pos.y = self.hitbox.centery

    def move(self, dt):
        if self.direction.magnitude() > 0:
            self.direction = self.direction.normalize()

        self.pos.x += self.direction.x * self.speed * dt
        self.hitbox.centerx = round(self.pos.x)
        self.rect.centerx = self.hitbox.centerx
        self.collision('horizontal')

        self.pos.y += self.direction.y * self.speed * dt
        self.hitbox.centery = round(self.pos.y)
        self.rect.centery = self.hitbox.centery
        self.pos.y = self.hitbox.centery
        self.collision('vertical')

    def update(self, dt):
        self.input()
        self.get_status()
        self.move(dt)
        self.animate(dt)
