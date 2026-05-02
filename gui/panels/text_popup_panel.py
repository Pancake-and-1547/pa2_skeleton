"""gui.panels.text_popup_panel

Scrollable text popup modal.

Dependencies and collaboration:
- Depends on pygame for event handling and drawing.
- Uses BasePanel for modal lifecycle.
- Collaborates with PanelManager (`manager`) for close/back actions.
- Uses Overlay/UI renderer (`ui`) for text wrapping and fonts.

Maintenance notes:
- This panel stores raw text and performs wrapping in draw to match the active font.
"""

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class TextPopupPanel(BasePanel):
    """
    Scrollable text popup modal.
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 900, 600
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.title = ""
        self.text = ""
        self.scroll_y = 0

        self.close_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.back_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)

    def set_content(self, *, title: str, text: str, scroll_y: int = 0) -> None:
        """Set title/text content and optionally a starting scroll offset."""
        self.title = str(title)
        self.text = str(text)
        self.scroll_y = int(scroll_y)

    def close(self) -> None:
        """Close the popup and reset scroll and stored content."""
        super().close()
        self.title = ""
        self.text = ""
        self.scroll_y = 0

    def handle_events(self, state, manager, events) -> bool:
        """Handle mouse-wheel scrolling and close/back shortcuts."""
        if not self.is_open:
            return False

        for e in events:
            if e.type == pygame.MOUSEWHEEL:
                self.scroll_y -= int(e.y * 28)
                self.scroll_y = max(0, self.scroll_y)
                return True

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_f:
                    manager.close_modal(self)
                    return True
                if e.key == pygame.K_r:
                    manager.close_modal(self)
                    return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.close_rect.collidepoint(e.pos) or self.back_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render the popup and draw wrapped text clipped to the content area."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=self.title)

        content_rect = pygame.Rect(self.rect.left + 24, self.rect.top + 78, self.rect.width - 48, self.rect.height - 140)
        ui.draw_content_box(surface, content_rect)

        lines = ui.wrap_lines(self.text, ui.font_board, content_rect.width - 10)
        old_clip = surface.get_clip()
        surface.set_clip(content_rect)

        y = content_rect.top + 6 - self.scroll_y
        for ln in lines:
            ui.draw_text(surface, ln, (content_rect.left + 5, y), font=ui.font_board, anchor="topleft")
            y += ui.font_board.get_height()

        surface.set_clip(old_clip)

        def draw_btn(rect: pygame.Rect, label: str):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos)

        draw_btn(self.close_rect, "Close (F)")
        draw_btn(self.back_rect, "Back (R)")
