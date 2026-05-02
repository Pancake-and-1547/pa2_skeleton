"""Transition animation state for the GUI runtime."""

from typing import Callable, Optional

import pygame

from .settings import SCREEN_WIDTH, SCREEN_HEIGHT


class TransitionState:
    """Fade overlay used to mask heavy blocking tasks."""

    def __init__(self) -> None:
        self.is_active: bool = False
        self.alpha: float = 0.0
        self.phase: Optional[str] = None

        self._task_done: bool = False
        self._task: Optional[Callable[[], None]] = None
        self.label: str = "Loading..."
        self.speed: float = 520.0

    def start(self, task: Optional[Callable[[], None]] = None, label: str = "Loading...") -> None:
        self.is_active = True
        self.phase = "in"
        self.alpha = 0.0
        self._task_done = False
        self._task = task
        self.label = label

    def update(self, dt: float) -> None:
        if not self.is_active:
            return

        if self.phase == "in":
            self.alpha = min(255.0, self.alpha + self.speed * float(dt))
            if self.alpha >= 255.0 and not self._task_done:
                self._task_done = True
                if callable(self._task):
                    self._task()
                self.phase = "out"
        elif self.phase == "out":
            self.alpha = max(0.0, self.alpha - self.speed * float(dt))
            if self.alpha <= 0.0:
                self.is_active = False
                self.phase = None
                self._task = None

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        if not self.is_active:
            return

        fade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        fade.fill((0, 0, 0, 255))

        text_surf = font.render(self.label, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        fade.blit(text_surf, text_rect)

        fade.set_alpha(int(self.alpha))
        surface.blit(fade, (0, 0))
