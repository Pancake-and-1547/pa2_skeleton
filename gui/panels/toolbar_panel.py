"""gui.panels.toolbar_panel

Always-visible toolbar panel.

Primary responsibility:
- Provide quick-access toggles and shortcuts for common modes (help, xray, select,
    edit, run) and for opening modals (outdoor temp, target temp, stats, optimization).

Dependencies and collaboration:
- Depends on pygame for key/mouse events and drawing.
- Uses BasePanel as a common interface, but is not modal (always open).
- Collaborates with GameState (`state`) through explicit mode-toggle methods so
    mode side effects remain centralized.
- Collaborates with PanelManager (`manager`) to open/close modals.

Design constraints:
- This panel should use GameState mode methods so heatmap invalidation and future
    mode policy stay centralized.
"""

import pygame

from .base_panel import BasePanel


class ToolbarPanel(BasePanel):
    """
    Global toolbar panel (always drawn, always eligible to receive input).

    Design note:
    - Do NOT rely on GameState storing panel stack state.
    - Use GameState mode methods rather than mutating flags directly.
    """

    def __init__(self) -> None:
        super().__init__()
        self.is_open = True  # Always visible

        self.rect = pygame.Rect(16, 120, 240, 340)

        x, y, w, h, g = self.rect.left + 10, self.rect.top + 10, self.rect.width - 20, 28, 8
        self.btn_help = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_xray = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_select = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_edit = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_run = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_outdoor = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_target = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_stats = pygame.Rect(x, y, w, h)
        y += h + g
        self.btn_opt = pygame.Rect(x, y, w, h)

    @staticmethod
    def _hit(rect: pygame.Rect, pos) -> bool:
        """Safely test if a position is inside a rect (guards against bad event data)."""
        try:
            return rect.collidepoint(pos)
        except Exception:
            return False

    @staticmethod
    def _toggle_modal(manager, panel, *, state=None) -> None:
        """Open or close a modal from the toolbar, preserving state-aware opens."""
        if panel.is_open:
            manager.close_modal(panel)
            return
        if state is None:
            manager.open_modal(panel)
            return
        manager.open_modal(panel, state=state)

    def handle_events(self, state, manager, events) -> bool:
        """Handle hotkeys and mouse clicks for toolbar buttons."""
        if not self.is_open:
            return False

        consumed = False
        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_h:
                    if not manager.help_panel.is_open:
                        manager.open_modal(manager.help_panel)
                    else:
                        manager.close_modal(manager.help_panel)
                    consumed = True

                elif e.key == pygame.K_x:
                    state.toggle_xray_mode()
                    consumed = True

                elif e.key == pygame.K_m:
                    state.toggle_free_select_mode()
                    consumed = True

                elif e.key == pygame.K_e:
                    state.toggle_edit_mode()
                    consumed = True

                elif e.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                    # Toggle sprint mode on Shift press (matches original behavior)
                    state.toggle_run_mode()
                    consumed = True

                elif e.key == pygame.K_c:
                    self._toggle_modal(manager, manager.outdoor_temp_panel, state=state)
                    consumed = True

                elif e.key == pygame.K_t:
                    self._toggle_modal(manager, manager.target_temp_panel, state=state)
                    consumed = True

                elif e.key == pygame.K_j:
                    self._toggle_modal(manager, manager.stats_panel)
                    consumed = True

                elif e.key == pygame.K_k:
                    self._toggle_modal(manager, manager.optimization_panel)
                    consumed = True

            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self._hit(self.btn_help, e.pos):
                    if not manager.help_panel.is_open:
                        manager.open_modal(manager.help_panel)
                    else:
                        manager.close_modal(manager.help_panel)
                    consumed = True

                elif self._hit(self.btn_xray, e.pos):
                    state.toggle_xray_mode()
                    consumed = True

                elif self._hit(self.btn_select, e.pos):
                    state.toggle_free_select_mode()
                    consumed = True

                elif self._hit(self.btn_edit, e.pos):
                    state.toggle_edit_mode()
                    consumed = True

                elif self._hit(self.btn_run, e.pos):
                    state.toggle_run_mode()
                    consumed = True

                elif self._hit(self.btn_outdoor, e.pos):
                    self._toggle_modal(manager, manager.outdoor_temp_panel, state=state)
                    consumed = True

                elif self._hit(self.btn_target, e.pos):
                    self._toggle_modal(manager, manager.target_temp_panel, state=state)
                    consumed = True

                elif self._hit(self.btn_stats, e.pos):
                    self._toggle_modal(manager, manager.stats_panel)
                    consumed = True

                elif self._hit(self.btn_opt, e.pos):
                    self._toggle_modal(manager, manager.optimization_panel)
                    consumed = True

        return consumed

    def draw(self, state, manager, surface, mouse_pos, ui) -> None:
        """Render the toolbar with active-state highlighting."""
        if not self.is_open:
            return

        ui.draw_panel_bg(surface, self.rect, title=None)

        xray = bool(getattr(state, "xray_mode", False))
        free_select = bool(getattr(state, "free_select_mode", False))
        edit_mode = bool(getattr(state, "edit_mode", False))
        run_mode = bool(getattr(state, "run_mode", False))

        help_open = bool(manager.help_panel.is_open)
        outdoor_open = bool(manager.outdoor_temp_panel.is_open)
        target_open = bool(manager.target_temp_panel.is_open)
        stats_open = bool(manager.stats_panel.is_open)
        opt_open = bool(manager.optimization_panel.is_open)

        def draw_button(rect: pygame.Rect, label: str, active: bool):
            ui.draw_button(surface, rect, label, mouse_pos=mouse_pos, active=active)

        draw_button(self.btn_help, "HELP (H)", help_open)
        draw_button(self.btn_xray, "XRAY (X)", xray)
        draw_button(self.btn_select, "SELECT (M)", free_select)
        draw_button(self.btn_edit, "EDIT (E)", edit_mode)
        draw_button(self.btn_run, "RUN (Shift)", run_mode)
        draw_button(self.btn_outdoor, "OUTDOOR (C)", outdoor_open)
        draw_button(self.btn_target, "TARGET (T)", target_open)
        draw_button(self.btn_stats, "STATS (J)", stats_open)
        draw_button(self.btn_opt, "OPT (K)", opt_open)
