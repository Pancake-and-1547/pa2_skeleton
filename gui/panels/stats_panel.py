"""Modal menu for statistics and plot actions."""

import pygame

from .base_panel import BasePanel
from ..settings import SCREEN_WIDTH, SCREEN_HEIGHT


class StatsPanel(BasePanel):
    """
    Statistics modal panel (self-contained).

    - Owns its own rects and click logic.
    - Opens popups by calling manager.show_text_popup / manager.show_plot_popup.
    - Does NOT rely on Overlay registering buttons.
    """

    def __init__(self) -> None:
        super().__init__()
        w, h = 800, 480
        self.rect = pygame.Rect((SCREEN_WIDTH - w) // 2, (SCREEN_HEIGHT - h) // 2, w, h)

        y, btn_h, gap = self.rect.top + 100, 40, 10
        self.btn_room_stats = pygame.Rect(self.rect.left + 40, y, w - 80, btn_h)
        y += btn_h + gap
        self.btn_time_series_stats = pygame.Rect(self.rect.left + 40, y, w - 80, btn_h)
        y += btn_h + gap
        self.btn_heatmap = pygame.Rect(self.rect.left + 40, y, w - 80, btn_h)
        y += btn_h + gap
        self.btn_room_cmp = pygame.Rect(self.rect.left + 40, y, w - 80, btn_h)
        y += btn_h + gap
        self.btn_time_series_plot = pygame.Rect(self.rect.left + 40, y, w - 80, btn_h)

        self.close_rect = pygame.Rect(self.rect.centerx - 100, self.rect.bottom - 50, 200, 36)

    def handle_events(self, state, manager, events) -> bool:
        """Handle shortcut keys and button clicks to run statistics functions."""
        if not self.is_open:
            return False

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_f, pygame.K_r, pygame.K_j):
                    manager.close_modal(self)
                    return True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.close_rect.collidepoint(e.pos):
                    manager.close_modal(self)
                    return True

                if self.btn_room_stats.collidepoint(e.pos):
                    data = state.engine.compute_room_statistics()
                    manager.show_text_popup("compute_room_statistics()", str(data))
                    return True

                if self.btn_time_series_stats.collidepoint(e.pos):
                    data = state.engine.compute_time_series_statistics()
                    manager.show_text_popup("compute_time_series_statistics()", str(data))
                    return True

                if self.btn_heatmap.collidepoint(e.pos):
                    fig = state.engine.plot_temperature_heatmap()
                    manager.show_plot_popup("plot_temperature_heatmap()", fig)
                    return True

                if self.btn_room_cmp.collidepoint(e.pos):
                    fig = state.engine.plot_room_comparison()
                    manager.show_plot_popup("plot_room_comparison()", fig)
                    return True

                if self.btn_time_series_plot.collidepoint(e.pos):
                    fig = state.engine.plot_time_series()
                    manager.show_plot_popup("plot_time_series()", fig)
                    return True

        return False

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Draw the menu of available statistics/plotting actions."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title="STATISTICS (J)")

        rows = [
            (self.btn_room_stats, "compute_room_statistics", "Per-room stats (dict)."),
            (self.btn_time_series_stats, "compute_time_series_statistics", "History-based stats (dict)."),
            (self.btn_heatmap, "plot_temperature_heatmap", "Current temp heatmap (Figure)."),
            (self.btn_room_cmp, "plot_room_comparison", "Room comparison (Figure)."),
            (self.btn_time_series_plot, "plot_time_series", "History time series (Figure)."),
        ]

        for btn_rect, label, desc in rows:
            hover = btn_rect.collidepoint(mouse_pos)
            ui.draw_button(surface, btn_rect, "", mouse_pos=mouse_pos)

            ui.draw_text(surface, label, (btn_rect.left + 15, btn_rect.centery - 8), font=ui.font_btn, anchor="midleft")
            ui.draw_text(
                surface,
                desc,
                (btn_rect.left + 15, btn_rect.centery + 10),
                font=ui.font_panel_hint,
                anchor="midleft",
                color=ui.colors["muted"] if hasattr(ui, "colors") else (200, 200, 200),
            )

        ui.draw_button(surface, self.close_rect, "Close (F/R)", mouse_pos=mouse_pos)
