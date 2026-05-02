"""Scrollable in-game help modal."""

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class HelpPanel(BasePanel):
    """
    Help modal panel (self-contained).
    Scrollable content area with a simple scrollbar.
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 760, 480
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)
        self.close_rect = pygame.Rect(self.rect.centerx - 100, self.rect.bottom - 50, 200, 36)

        # Scroll state
        self.scroll_y = 0

        # Layout (content viewport inside the panel)
        self.content_pad_left = 36
        self.content_pad_right = 36
        self.content_top = 70
        self.content_bottom_gap = 70  # leave room for close button row
        self.content_inner_pad = 14
        self.scrollbar_gap = 12
        self.scrollbar_width = 9

        # Tunables
        self.line_gap = 5
        self.wheel_step = 32

        # Cached scroll clamp (computed in draw where ui is available)
        self._max_scroll_cached = 0

    def open(self, *args, **kwargs) -> None:
        """Open the help modal and reset scroll state."""
        self.is_open = True
        self.scroll_y = 0
        self._max_scroll_cached = 0

    def _content_rect(self) -> pygame.Rect:
        """Return the inner content viewport (excluding title and close row)."""
        return pygame.Rect(
            self.rect.left + self.content_pad_left,
            self.rect.top + self.content_top,
            self.rect.width - self.content_pad_left - self.content_pad_right,
            self.rect.height - self.content_top - self.content_bottom_gap,
        )

    @staticmethod
    def _clamp(v: int, lo: int, hi: int) -> int:
        """Clamp integer `v` into inclusive range [lo, hi]."""
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v

    def _max_scroll(self, ui, lines: list[str]) -> int:
        """Compute maximum scroll offset for a given line list and current font."""
        content_rect = self._content_rect()
        line_h = ui.font_board.get_height() + self.line_gap
        content_h = len(lines) * line_h
        return max(0, content_h - content_rect.height)

    def handle_events(self, state, manager, events) -> bool:
        """Handle close shortcuts, click-to-close, and mouse-wheel scrolling."""
        if not self.is_open:
            return False
        for e in events:
            # Close shortcuts
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_f, pygame.K_r, pygame.K_ESCAPE):
                manager.close_modal(self)
                return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.close_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

            # Mouse wheel scrolling
            if e.type == pygame.MOUSEWHEEL:
                # pygame convention: wheel up => y=+1
                # We want content move up => scroll_y decreases
                self.scroll_y -= int(e.y * self.wheel_step)

                # Clamp using cached max (computed in draw); safe even if 0 initially
                self.scroll_y = self._clamp(int(self.scroll_y), 0, int(self._max_scroll_cached))

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render the help panel including a scrollbar when content overflows."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title="HELP")

        lines = [
            "You can use your mouse wheel to scroll the text.",
            "",
            "General Controls:",
            "    Movement: W/A/S/D or Arrow Keys",
            "    First Action: F / Left Mouse Button",
            "    Second Action: R / Right Mouse Button",
            "",
            "When not in Edit Mode:",
            "    When nothing is in the selected cell:",
            "        First Action: Place an AC here",
            "        Second Action: Mark this cell as a candidate position for optimization",
            "",
            "    When an AC is in the selected cell:",
            "        First Action: Adjust the AC settings",
            "        Second Action: Remove the AC from the map",
            "",
            "    When the selected cell is a candidate position:",
            "        First Action: Place an AC here and unmark this cell as a candidate position",
            "        Second Action: Unmark this cell as a candidate position",
            "",
            "When in Edit Mode:",
            "    First Action: Set the temperature at the selected cell",
            "    Second Action: Set the room weight for the selected cell's room",
            "",
            "View & Tools:",
            "    X-Ray Mode: X, draw a temperature heatmap overlay",
            "    Free Select Mode: M, set the selection box to follow the mouse or follow the player",
            "    Edit Mode: E, switch the function of the first/second action",
            "    Simulation: Space",
            "    Set outdoor temperature: C",
            "    Set target temperature: T",
            "    View statistics: J",
            "    Do optimization: K",
        ]

        content_rect = self._content_rect()
        max_scroll = self._max_scroll(ui, lines)
        self._max_scroll_cached = int(max_scroll)
        self.scroll_y = self._clamp(int(self.scroll_y), 0, int(max_scroll))

        # Draw a subtle frame for the scroll box
        ui.draw_content_box(surface, content_rect)

        text_rect = content_rect.inflate(-2 * self.content_inner_pad, -2 * self.content_inner_pad)
        text_rect.width -= self.scrollbar_width + self.scrollbar_gap
        if text_rect.width < 40:
            text_rect.width = 40

        # Clip to content rect (scroll box)
        old_clip = surface.get_clip()
        surface.set_clip(text_rect)

        line_h = ui.font_board.get_height() + self.line_gap
        yy = text_rect.top - self.scroll_y
        x = text_rect.left
        for t in lines:
            ui.draw_text(surface, t, (x, yy), font=ui.font_board, anchor="topleft")
            yy += line_h

        surface.set_clip(old_clip)

        # Scrollbar (only if needed)
        if max_scroll > 0:
            track_w = self.scrollbar_width
            track = pygame.Rect(
                content_rect.right - self.content_inner_pad - track_w,
                content_rect.top + self.content_inner_pad,
                track_w,
                content_rect.height - 2 * self.content_inner_pad,
            )
            pygame.draw.rect(surface, (42, 53, 63), track, border_radius=4)

            # Thumb size proportional to visible area
            visible_ratio = content_rect.height / (content_rect.height + max_scroll)
            thumb_h = max(18, int(track.height * visible_ratio))
            thumb_y = track.top + int((track.height - thumb_h) * (self.scroll_y / max_scroll))
            thumb = pygame.Rect(track.left, thumb_y, track.width, thumb_h)
            pygame.draw.rect(surface, (126, 180, 191), thumb, border_radius=4)

        ui.draw_button(surface, self.close_rect, "CLOSE (F/R)", mouse_pos=mouse_pos)
