"""gui.panels.confirm_popup_panel

Generic confirmation modal.

Primary responsibility:
- Present a title + multi-line message and ask the user to Accept or Cancel.

Dependencies and collaboration:
- Depends on pygame for event handling and geometry.
- Uses BasePanel as the shared panel interface.
- Uses PanelManager (`manager`) to manage modal lifecycle via `close_modal`.

Coupling notes:
- The accept action is a callback (`on_accept`) supplied by the caller. This callback
    should be fast and side-effect safe; if it performs heavy work, schedule it via
    GameState.run_with_transition from the caller.
"""

from typing import Callable, Optional

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class ConfirmPopupPanel(BasePanel):
    """
    Confirm modal popup: Accept(F) / Cancel(R).
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 800, 380
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        self.title = ""
        self.text = ""
        self.on_accept: Optional[Callable[[], None]] = None # a callback function when accepted

        self.accept_rect = pygame.Rect(self.rect.centerx - 160, self.rect.bottom - 50, 150, 36)
        self.cancel_rect = pygame.Rect(self.rect.centerx + 10, self.rect.bottom - 50, 150, 36)

    def set_content(self, *, title: str, text: str, on_accept: Callable[[], None]) -> None:
        """Populate modal content.

        Args:
            title: Panel title.
            text: Body text (will be wrapped by UI renderer).
            on_accept: Callback invoked only if the user accepts.
        """
        self.title = str(title)
        self.text = str(text)
        self.on_accept = on_accept

    def close(self) -> None:
        """Close the modal and clear the stored callback/text."""
        super().close()
        self.title = ""
        self.text = ""
        self.on_accept = None

    def _accept(self, manager):
        """Close the modal and then invoke the accept callback (if any)."""
        cb = self.on_accept
        manager.close_modal(self)
        if callable(cb):
            cb()

    def handle_events(self, state, manager, events) -> bool:
        """Consume keyboard/mouse events for accept/cancel."""
        if not self.is_open:
            return False

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_f:
                    self._accept(manager)
                    return True
                if e.key == pygame.K_r:
                    manager.close_modal(self)
                    return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.accept_rect.collidepoint(e.pos):
                    self._accept(manager)
                    return True
                if self.cancel_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render the modal dialog and action buttons."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=self.title)

        content_rect = pygame.Rect(self.rect.left + 24, self.rect.top + 78, self.rect.width - 48, self.rect.height - 140)
        ui.draw_content_box(surface, content_rect)

        lines = ui.wrap_lines(self.text, ui.font_board, content_rect.width - 10)
        y = content_rect.top + 6
        for ln in lines:
            ui.draw_text(surface, ln, (content_rect.left + 5, y), font=ui.font_board, anchor="topleft")
            y += ui.font_board.get_height()

        def draw_btn(rect: pygame.Rect, label: str):
            variant = "primary" if "ACCEPT" in label else "default"
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos, variant=variant)

        draw_btn(self.accept_rect, "ACCEPT (F)")
        draw_btn(self.cancel_rect, "CANCEL (R)")
