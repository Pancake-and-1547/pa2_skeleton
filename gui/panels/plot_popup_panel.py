"""gui.panels.plot_popup_panel

Modal popup for displaying a pre-rendered plot surface.

Dependencies and collaboration:
- Depends on pygame for event types and drawing.
- Uses BasePanel for the modal interface.
- Collaborates with PanelManager (`manager`) for modal lifecycle.
- The displayed content is a pygame.Surface typically produced by
    `gui.support.figure_to_surface(...)` (via PanelManager.show_plot_popup).

Maintenance notes:
- This module intentionally does not depend on matplotlib; conversion happens upstream.
"""

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class PlotPopupPanel(BasePanel):
    """
    Plot popup modal showing a pygame.Surface.
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 900, 600
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.title = ""
        self.surface = None

        self.close_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.back_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)

    def set_content(self, *, title: str, surface) -> None:
        """Set the popup title and the surface to blit into the content area."""
        self.title = str(title)
        self.surface = surface

    def close(self) -> None:
        """Close the popup and release references to the content surface."""
        super().close()
        self.title = ""
        self.surface = None

    def handle_events(self, state, manager, events) -> bool:
        """Close the modal on F/R or on button click."""
        if not self.is_open:
            return False

        for e in events:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_f, pygame.K_r):
                manager.close_modal(self)
                return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.close_rect.collidepoint(e.pos) or self.back_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render popup chrome and blit the provided plot surface."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=self.title)

        content_rect = pygame.Rect(self.rect.left + 24, self.rect.top + 78, self.rect.width - 48, self.rect.height - 140)
        ui.draw_content_box(surface, content_rect)

        if self.surface is not None:
            surf_rect = self.surface.get_rect(center=content_rect.center)
            surface.blit(self.surface, surf_rect)

        def draw_btn(rect: pygame.Rect, label: str):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_btn(self.close_rect, "Close (F)")
        draw_btn(self.back_rect, "Back (R)")
